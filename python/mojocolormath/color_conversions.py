"""Conversions among the color spaces covered by this port."""

from __future__ import annotations

from collections import deque
from functools import lru_cache

import numpy as np

from . import color_constants
from ._lib import addr, check_status, f64_triplets, lib, unary3
from .color_exceptions import UndefinedConversionError
from .color_objects import (
    BaseRGBColor,
    ColorBase,
    LabColor,
    LCHabColor,
    LCHuvColor,
    LuvColor,
    sRGBColor,
    xyYColor,
    XYZColor,
)

_BRADFORD = np.array(
    (
        (0.8951, 0.2664, -0.1614),
        (-0.7502, 1.7135, 0.0367),
        (0.0389, -0.0685, 1.0296),
    ),
    dtype=np.float64,
)


def _white(observer, illuminant):
    return color_constants.ILLUMINANTS[str(observer)][illuminant.lower()]


def _adapt_array(values, observer, source_illuminant, target_illuminant):
    source = source_illuminant.lower()
    target = target_illuminant.lower()
    array, scalar = f64_triplets(values)
    if source == target:
        copied = array.copy()
        return copied[0] if scalar else copied
    source_response = _BRADFORD @ np.asarray(_white(observer, source))
    target_response = _BRADFORD @ np.asarray(_white(observer, target))
    matrix = np.ascontiguousarray(
        np.linalg.pinv(_BRADFORD)
        @ np.diag(target_response / source_response)
        @ _BRADFORD,
        dtype=np.float64,
    )
    result = np.empty_like(array)
    status = lib().mcm_transform3(addr(array), addr(result), addr(matrix), len(array))
    check_status(status, "mcm_transform3")
    return result[0] if scalar else result


def _convert_kernel(symbol, values, observer=None, illuminant=None):
    if observer is None:
        return unary3(symbol, values)
    return unary3(symbol, values, *_white(observer, illuminant))


def Lab_to_XYZ(cobj, *args, **kwargs):
    l = cobj.lab_l
    a = cobj.lab_a
    b = cobj.lab_b
    y = (l + 16.0) / 116.0
    x = a / 500.0 + y
    z = y - b / 200.0
    x3 = x * x * x
    y3 = y * y * y
    z3 = z * z * z
    epsilon = 216.0 / 24389.0
    offset = 16.0 / 116.0
    x = x3 if x3 > epsilon else (x - offset) / 7.787
    y = y3 if y3 > epsilon else (y - offset) / 7.787
    z = z3 if z3 > epsilon else (z - offset) / 7.787
    wx, wy, wz = color_constants.ILLUMINANTS[cobj.observer][cobj.illuminant]
    return XYZColor._from_validated(
        wx * x,
        wy * y,
        wz * z,
        cobj.observer,
        cobj.illuminant,
    )


def XYZ_to_Lab(cobj, *args, **kwargs):
    values = _convert_kernel(
        "mcm_xyz_to_lab", cobj.get_value_tuple(), cobj.observer, cobj.illuminant
    )
    return LabColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def XYZ_to_Luv(cobj, *args, **kwargs):
    values = _convert_kernel(
        "mcm_xyz_to_luv", cobj.get_value_tuple(), cobj.observer, cobj.illuminant
    )
    return LuvColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def Luv_to_XYZ(cobj, *args, **kwargs):
    values = _convert_kernel(
        "mcm_luv_to_xyz", cobj.get_value_tuple(), cobj.observer, cobj.illuminant
    )
    return XYZColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def Lab_to_LCHab(cobj, *args, **kwargs):
    values = _convert_kernel("mcm_cart_to_lch", cobj.get_value_tuple())
    return LCHabColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def LCHab_to_Lab(cobj, *args, **kwargs):
    values = _convert_kernel("mcm_lch_to_cart", cobj.get_value_tuple())
    return LabColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def Luv_to_LCHuv(cobj, *args, **kwargs):
    values = _convert_kernel("mcm_cart_to_lch", cobj.get_value_tuple())
    return LCHuvColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def LCHuv_to_Luv(cobj, *args, **kwargs):
    values = _convert_kernel("mcm_lch_to_cart", cobj.get_value_tuple())
    return LuvColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def XYZ_to_xyY(cobj, *args, **kwargs):
    values = _convert_kernel("mcm_xyz_to_xyy", cobj.get_value_tuple())
    return xyYColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def xyY_to_XYZ(cobj, *args, **kwargs):
    values = _convert_kernel("mcm_xyy_to_xyz", cobj.get_value_tuple())
    return XYZColor(*values, observer=cobj.observer, illuminant=cobj.illuminant)


def RGB_to_XYZ(cobj, target_illuminant=None, *args, **kwargs):
    if not isinstance(cobj, sRGBColor):
        raise UndefinedConversionError(cobj.__class__, XYZColor)
    values = _convert_kernel("mcm_srgb_to_xyz", cobj.get_value_tuple())
    illuminant = cobj.native_illuminant
    if target_illuminant is not None and target_illuminant.lower() != illuminant:
        values = _adapt_array(values, "2", illuminant, target_illuminant)
        illuminant = target_illuminant.lower()
    return XYZColor(*values, observer="2", illuminant=illuminant)


def XYZ_to_RGB(cobj, target_rgb=sRGBColor, *args, **kwargs):
    if target_rgb is None:
        target_rgb = sRGBColor
    if target_rgb is not sRGBColor:
        raise UndefinedConversionError(XYZColor, target_rgb)
    values = cobj.get_value_tuple()
    if cobj.illuminant != "d65":
        values = _adapt_array(values, cobj.observer, cobj.illuminant, "d65")
    return sRGBColor(*_convert_kernel("mcm_xyz_to_srgb", values))


_EDGES = {
    LabColor: [(XYZColor, Lab_to_XYZ), (LCHabColor, Lab_to_LCHab)],
    XYZColor: [
        (LabColor, XYZ_to_Lab),
        (LuvColor, XYZ_to_Luv),
        (xyYColor, XYZ_to_xyY),
        (sRGBColor, XYZ_to_RGB),
    ],
    LuvColor: [(XYZColor, Luv_to_XYZ), (LCHuvColor, Luv_to_LCHuv)],
    LCHabColor: [(LabColor, LCHab_to_Lab)],
    LCHuvColor: [(LuvColor, LCHuv_to_Luv)],
    xyYColor: [(XYZColor, xyY_to_XYZ)],
    sRGBColor: [(XYZColor, RGB_to_XYZ)],
}


@lru_cache(maxsize=None)
def _path(source, target):
    if source is target:
        return []
    queue = deque([(source, [])])
    seen = {source}
    while queue:
        current, path = queue.popleft()
        for next_type, function in _EDGES.get(current, []):
            next_path = path + [function]
            if next_type is target:
                return next_path
            if next_type not in seen:
                seen.add(next_type)
                queue.append((next_type, next_path))
    raise UndefinedConversionError(source, target)


def convert_color(
    color,
    target_cs,
    through_rgb_type=sRGBColor,
    target_illuminant=None,
    *args,
    **kwargs,
):
    if color.__class__ is LabColor and target_cs is XYZColor:
        if through_rgb_type is not sRGBColor:
            raise UndefinedConversionError(color.__class__, target_cs)
        return Lab_to_XYZ(color)
    if isinstance(target_cs, str) or not isinstance(target_cs, type):
        raise ValueError("target_cs parameter must be a Color object.")
    if not issubclass(target_cs, ColorBase):
        raise ValueError("target_cs parameter must be a Color object.")
    if through_rgb_type is not sRGBColor:
        raise UndefinedConversionError(color.__class__, target_cs)
    converted = color
    for function in _path(color.__class__, target_cs):
        converted = function(
            converted,
            target_rgb=target_cs if issubclass(target_cs, BaseRGBColor) else sRGBColor,
            target_illuminant=target_illuminant,
            *args,
            **kwargs,
        )
    return converted


def convert_color_array(
    colors,
    source_cs,
    target_cs,
    *,
    observer="2",
    illuminant=None,
    target_illuminant=None,
):
    """Convert an ``(n, 3)`` array in one call per conversion edge."""
    array, scalar = f64_triplets(colors)
    current = source_cs
    current_illuminant = (
        "d65" if source_cs is sRGBColor else (illuminant or "d50").lower()
    )
    for function in _path(source_cs, target_cs):
        if function is Lab_to_XYZ:
            array = _convert_kernel(
                "mcm_lab_to_xyz", array, observer, current_illuminant
            )
        elif function is XYZ_to_Lab:
            array = _convert_kernel(
                "mcm_xyz_to_lab", array, observer, current_illuminant
            )
        elif function is XYZ_to_Luv:
            array = _convert_kernel(
                "mcm_xyz_to_luv", array, observer, current_illuminant
            )
        elif function is Luv_to_XYZ:
            array = _convert_kernel(
                "mcm_luv_to_xyz", array, observer, current_illuminant
            )
        elif function in (Lab_to_LCHab, Luv_to_LCHuv):
            array = _convert_kernel("mcm_cart_to_lch", array)
        elif function in (LCHab_to_Lab, LCHuv_to_Luv):
            array = _convert_kernel("mcm_lch_to_cart", array)
        elif function is XYZ_to_xyY:
            array = _convert_kernel("mcm_xyz_to_xyy", array)
        elif function is xyY_to_XYZ:
            array = _convert_kernel("mcm_xyy_to_xyz", array)
        elif function is RGB_to_XYZ:
            array = _convert_kernel("mcm_srgb_to_xyz", array)
            current_illuminant = "d65"
            if target_illuminant is not None:
                array = _adapt_array(
                    array, observer, current_illuminant, target_illuminant
                )
                current_illuminant = target_illuminant.lower()
        elif function is XYZ_to_RGB:
            if current_illuminant != "d65":
                array = _adapt_array(array, observer, current_illuminant, "d65")
            array = _convert_kernel("mcm_xyz_to_srgb", array)
            current_illuminant = "d65"
        current = next_type = {
            Lab_to_XYZ: XYZColor,
            XYZ_to_Lab: LabColor,
            XYZ_to_Luv: LuvColor,
            Luv_to_XYZ: XYZColor,
            Lab_to_LCHab: LCHabColor,
            LCHab_to_Lab: LabColor,
            Luv_to_LCHuv: LCHuvColor,
            LCHuv_to_Luv: LuvColor,
            XYZ_to_xyY: xyYColor,
            xyY_to_XYZ: XYZColor,
            RGB_to_XYZ: XYZColor,
            XYZ_to_RGB: sRGBColor,
        }[function]
    return array[0] if scalar else array
