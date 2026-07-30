import numpy as np
import pytest

from colormath.color_conversions import convert_color as upstream_convert
from colormath.color_objects import (
    LabColor as UpLab,
    LCHabColor as UpLCHab,
    LCHuvColor as UpLCHuv,
    LuvColor as UpLuv,
    sRGBColor as UpsRGB,
    xyYColor as UpxyY,
    XYZColor as UpXYZ,
)

from mojocolormath.color_conversions import convert_color, convert_color_array
from mojocolormath import color_constants
from mojocolormath._lib import check_status, lib
from mojocolormath.color_objects import (
    LabColor,
    LCHabColor,
    LCHuvColor,
    LuvColor,
    sRGBColor,
    xyYColor,
    XYZColor,
)


PAIRS = [
    (LabColor(63.2, 18.1, -42.7, illuminant="d50"), UpLab, XYZColor, UpXYZ),
    (XYZColor(0.31, 0.42, 0.19, illuminant="d50"), UpXYZ, LabColor, UpLab),
    (XYZColor(0.31, 0.42, 0.19, illuminant="d65"), UpXYZ, LuvColor, UpLuv),
    (LuvColor(61.0, 22.0, -31.0, illuminant="d65"), UpLuv, XYZColor, UpXYZ),
    (LabColor(63.2, 18.1, -42.7), UpLab, LCHabColor, UpLCHab),
    (LCHabColor(63.2, 46.4, 293.0), UpLCHab, LabColor, UpLab),
    (LuvColor(63.2, 18.1, -42.7), UpLuv, LCHuvColor, UpLCHuv),
    (LCHuvColor(63.2, 46.4, 293.0), UpLCHuv, LuvColor, UpLuv),
    (XYZColor(0.31, 0.42, 0.19), UpXYZ, xyYColor, UpxyY),
    (xyYColor(0.337, 0.422, 0.61), UpxyY, XYZColor, UpXYZ),
    (sRGBColor(0.2, 0.7, 0.4), UpsRGB, XYZColor, UpXYZ),
    (XYZColor(0.31, 0.42, 0.19, illuminant="d50"), UpXYZ, sRGBColor, UpsRGB),
]


@pytest.mark.parametrize("ours,up_source,our_target,up_target", PAIRS)
def test_direct_conversion_upstream_parity(ours, up_source, our_target, up_target):
    theirs_in = up_source(
        *ours.get_value_tuple(),
        **(
            {"observer": ours.observer, "illuminant": ours.illuminant}
            if hasattr(ours, "observer")
            else {}
        ),
    )
    actual = convert_color(ours, our_target)
    expected = upstream_convert(theirs_in, up_target)
    assert np.allclose(
        actual.get_value_tuple(), expected.get_value_tuple(), rtol=2e-9, atol=2e-9
    )
    if hasattr(expected, "illuminant"):
        assert actual.observer == expected.observer
        assert actual.illuminant == expected.illuminant


@pytest.mark.parametrize(
    "our_target,up_target",
    [
        (XYZColor, UpXYZ),
        (LabColor, UpLab),
        (LuvColor, UpLuv),
        (LCHabColor, UpLCHab),
        (LCHuvColor, UpLCHuv),
        (xyYColor, UpxyY),
    ],
)
def test_srgb_conversion_paths_upstream_parity(our_target, up_target):
    ours = sRGBColor(0.91, 0.23, 0.47)
    theirs = UpsRGB(0.91, 0.23, 0.47)
    actual = convert_color(ours, our_target)
    expected = upstream_convert(theirs, up_target)
    assert np.allclose(
        actual.get_value_tuple(), expected.get_value_tuple(), rtol=1e-8, atol=1e-8
    )


def test_target_illuminant_upstream_parity():
    ours = convert_color(
        sRGBColor(0.11, 0.42, 0.86), LabColor, target_illuminant="d50"
    )
    theirs = upstream_convert(
        UpsRGB(0.11, 0.42, 0.86), UpLab, target_illuminant="d50"
    )
    assert ours.illuminant == theirs.illuminant == "d50"
    assert np.allclose(
        ours.get_value_tuple(), theirs.get_value_tuple(), rtol=1e-8, atol=1e-8
    )


def test_scalar_lab_to_xyz_linear_branch_upstream_parity():
    ours = LabColor(1.0, 0.0, 0.0, illuminant="d50")
    theirs = UpLab(1.0, 0.0, 0.0, illuminant="d50")
    actual = convert_color(ours, XYZColor)
    expected = upstream_convert(theirs, UpXYZ)
    assert np.allclose(
        actual.get_value_tuple(), expected.get_value_tuple(), rtol=2e-9, atol=2e-9
    )


@pytest.mark.parametrize(
    "our_source,up_source,our_target,up_target,illuminant",
    [
        (LabColor, UpLab, XYZColor, UpXYZ, "d50"),
        (XYZColor, UpXYZ, LuvColor, UpLuv, "d65"),
        (LuvColor, UpLuv, LCHabColor, UpLCHab, "d50"),
        (sRGBColor, UpsRGB, LabColor, UpLab, "d65"),
        (LabColor, UpLab, sRGBColor, UpsRGB, "d50"),
    ],
)
def test_batch_conversion_matches_upstream_objects(
    our_source, up_source, our_target, up_target, illuminant
):
    rng = np.random.default_rng(19)
    if our_source is sRGBColor:
        values = rng.uniform(0.02, 0.98, (50, 3))
    elif our_source is XYZColor:
        values = rng.uniform(0.02, 0.9, (50, 3))
    else:
        values = np.column_stack(
            (rng.uniform(5, 95, 50), rng.uniform(-60, 60, 50), rng.uniform(-60, 60, 50))
        )
    actual = convert_color_array(
        values,
        our_source,
        our_target,
        illuminant=illuminant,
    )
    expected = []
    for value in values:
        kwargs = (
            {}
            if up_source is UpsRGB
            else {"observer": "2", "illuminant": illuminant}
        )
        result = upstream_convert(up_source(*value, **kwargs), up_target)
        expected.append(result.get_value_tuple())
    assert np.allclose(actual, expected, rtol=5e-9, atol=1e-7)


def test_round_trips():
    rng = np.random.default_rng(91)
    lab = np.column_stack(
        (rng.uniform(5, 95, 1000), rng.uniform(-80, 80, 1000), rng.uniform(-80, 80, 1000))
    )
    xyz = convert_color_array(lab, LabColor, XYZColor, illuminant="d50")
    restored = convert_color_array(xyz, XYZColor, LabColor, illuminant="d50")
    assert np.allclose(restored, lab, atol=2e-4)

    rgb = rng.uniform(0, 1, (1000, 3))
    xyz = convert_color_array(rgb, sRGBColor, XYZColor)
    restored = convert_color_array(xyz, XYZColor, sRGBColor, illuminant="d65")
    assert np.allclose(restored, rgb, atol=2e-5)


def test_rgb_helpers_and_upscaled_constructor():
    color = sRGBColor(18, 52, 86, is_upscaled=True)
    assert color.get_value_tuple() == pytest.approx((18 / 255, 52 / 255, 86 / 255))
    assert color.get_upscaled_value_tuple() == (18, 52, 86)
    assert color.get_rgb_hex() == "#123456"
    assert sRGBColor.new_from_rgb_hex("#123456").get_value_tuple() == pytest.approx(
        color.get_value_tuple()
    )


def test_array_shape_validation():
    with pytest.raises(ValueError, match="shape"):
        convert_color_array(np.zeros((4, 4)), LabColor, XYZColor)


def test_empty_and_noncontiguous_batch_inputs():
    empty = convert_color_array(np.empty((0, 3)), LabColor, XYZColor)
    assert empty.shape == (0, 3)
    values = np.arange(30, dtype=np.float32).reshape(10, 3)[::2]
    actual = convert_color_array(values, LabColor, XYZColor)
    expected = np.array(
        [
            upstream_convert(UpLab(*row), UpXYZ).get_value_tuple()
            for row in values
        ]
    )
    assert np.allclose(actual, expected, rtol=2e-9, atol=2e-9)


def test_extended_precision_batch_is_not_silently_narrowed():
    if np.dtype(np.longdouble).itemsize <= np.dtype(np.float64).itemsize:
        pytest.skip("long double is not wider than float64 on this platform")
    with pytest.raises(TypeError, match="narrow"):
        convert_color_array(
            np.zeros((1, 3), dtype=np.longdouble), LabColor, XYZColor
        )


@pytest.mark.parametrize(
    "observer,illuminant",
    [
        (observer, illuminant)
        for observer, whites in color_constants.ILLUMINANTS.items()
        for illuminant in whites
    ],
)
def test_all_reference_whites_upstream_parity(observer, illuminant):
    values = np.array([[7.0, -3.0, 8.0], [50.0, 20.0, -30.0], [92.0, 4.0, 2.0]])
    actual = convert_color_array(
        values, LabColor, XYZColor, observer=observer, illuminant=illuminant
    )
    expected = [
        upstream_convert(
            UpLab(*row, observer=observer, illuminant=illuminant), UpXYZ
        ).get_value_tuple()
        for row in values
    ]
    assert np.allclose(actual, expected, rtol=2e-9, atol=2e-9)


def test_ffi_rejects_null_nonempty_buffers_and_python_surfaces_status():
    status = lib().mcm_cart_to_lch(0, 0, 1)
    assert status != 0
    with pytest.raises(RuntimeError, match="rejected"):
        check_status(status, "mcm_cart_to_lch")
