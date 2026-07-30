"""Color objects matching colormath's covered classes and constructor signatures."""

from __future__ import annotations

import math

from . import color_constants
from .color_exceptions import InvalidIlluminantError, InvalidObserverError


class ColorBase:
    VALUES: list[str] = []
    _through_rgb_type = None

    def get_value_tuple(self):
        return tuple(getattr(self, name) for name in self.VALUES)

    def __str__(self):
        values = " ".join(f"{name}:{getattr(self, name):.4f}" for name in self.VALUES)
        return f"{self.__class__.__name__} ({values})"

    def __repr__(self):
        values = ",".join(f"{name}={getattr(self, name)!r}" for name in self.VALUES)
        return f"{self.__class__.__name__}({values})"


class IlluminantMixin:
    def set_observer(self, observer):
        observer = str(observer)
        if observer not in color_constants.OBSERVERS:
            raise InvalidObserverError(observer)
        self.observer = observer

    def set_illuminant(self, illuminant):
        illuminant = illuminant.lower()
        if illuminant not in color_constants.ILLUMINANTS[self.observer]:
            raise InvalidIlluminantError(illuminant)
        self.illuminant = illuminant

    def get_illuminant_xyz(self, observer=None, illuminant=None):
        observer = self.observer if observer is None else str(observer)
        illuminant = self.illuminant if illuminant is None else illuminant.lower()
        try:
            x, y, z = color_constants.ILLUMINANTS[observer][illuminant]
        except KeyError as exc:
            raise InvalidIlluminantError(illuminant) from exc
        return {"X": x, "Y": y, "Z": z}


class _IlluminantColor(IlluminantMixin, ColorBase):
    def _set_metadata(self, observer, illuminant):
        self.observer = None
        self.illuminant = None
        self.set_observer(observer)
        self.set_illuminant(illuminant)


class LabColor(_IlluminantColor):
    VALUES = ["lab_l", "lab_a", "lab_b"]

    def __init__(self, lab_l, lab_a, lab_b, observer="2", illuminant="d50"):
        self.lab_l = float(lab_l)
        self.lab_a = float(lab_a)
        self.lab_b = float(lab_b)
        self._set_metadata(observer, illuminant)


class LuvColor(_IlluminantColor):
    VALUES = ["luv_l", "luv_u", "luv_v"]

    def __init__(self, luv_l, luv_u, luv_v, observer="2", illuminant="d50"):
        self.luv_l = float(luv_l)
        self.luv_u = float(luv_u)
        self.luv_v = float(luv_v)
        self._set_metadata(observer, illuminant)


class LCHabColor(_IlluminantColor):
    VALUES = ["lch_l", "lch_c", "lch_h"]

    def __init__(self, lch_l, lch_c, lch_h, observer="2", illuminant="d50"):
        self.lch_l = float(lch_l)
        self.lch_c = float(lch_c)
        self.lch_h = float(lch_h)
        self._set_metadata(observer, illuminant)


class LCHuvColor(LCHabColor):
    pass


class XYZColor(_IlluminantColor):
    VALUES = ["xyz_x", "xyz_y", "xyz_z"]

    @classmethod
    def _from_validated(cls, xyz_x, xyz_y, xyz_z, observer, illuminant):
        color = cls.__new__(cls)
        color.xyz_x = xyz_x
        color.xyz_y = xyz_y
        color.xyz_z = xyz_z
        color.observer = observer
        color.illuminant = illuminant
        return color

    def __init__(self, xyz_x, xyz_y, xyz_z, observer="2", illuminant="d50"):
        self.xyz_x = float(xyz_x)
        self.xyz_y = float(xyz_y)
        self.xyz_z = float(xyz_z)
        self._set_metadata(observer, illuminant)

    def apply_adaptation(self, target_illuminant, adaptation="bradford"):
        if adaptation.lower() != "bradford":
            raise ValueError("only Bradford adaptation is supported")
        if self.illuminant != target_illuminant.lower():
            from .color_conversions import _adapt_array

            values = _adapt_array(
                self.get_value_tuple(),
                self.observer,
                self.illuminant,
                target_illuminant,
            )
            self.xyz_x, self.xyz_y, self.xyz_z = values
            self.set_illuminant(target_illuminant)


class xyYColor(_IlluminantColor):
    VALUES = ["xyy_x", "xyy_y", "xyy_Y"]

    def __init__(self, xyy_x, xyy_y, xyy_Y, observer="2", illuminant="d50"):
        self.xyy_x = float(xyy_x)
        self.xyy_y = float(xyy_y)
        self.xyy_Y = float(xyy_Y)
        self._set_metadata(observer, illuminant)


class BaseRGBColor(ColorBase):
    VALUES = ["rgb_r", "rgb_g", "rgb_b"]

    def __init__(self, rgb_r, rgb_g, rgb_b, is_upscaled=False):
        scale = 255.0 if is_upscaled else 1.0
        self.rgb_r = float(rgb_r) / scale
        self.rgb_g = float(rgb_g) / scale
        self.rgb_b = float(rgb_b) / scale
        self.is_upscaled = is_upscaled

    def _clamp_rgb_coordinate(self, coord):
        return min(max(coord, 0.0), 1.0)

    @property
    def clamped_rgb_r(self):
        return self._clamp_rgb_coordinate(self.rgb_r)

    @property
    def clamped_rgb_g(self):
        return self._clamp_rgb_coordinate(self.rgb_g)

    @property
    def clamped_rgb_b(self):
        return self._clamp_rgb_coordinate(self.rgb_b)

    def get_upscaled_value_tuple(self):
        return tuple(int(math.floor(0.5 + value * 255)) for value in self.get_value_tuple())

    def get_rgb_hex(self):
        return "#%02x%02x%02x" % self.get_upscaled_value_tuple()

    @classmethod
    def new_from_rgb_hex(cls, hex_str):
        value = hex_str.strip().removeprefix("#")
        if len(value) != 6:
            raise ValueError(f"input #{value} is not in #RRGGBB format")
        return cls(*(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)))


class sRGBColor(BaseRGBColor):
    rgb_gamma = 2.2
    native_illuminant = "d65"
