"""Scalar delta-E API matching upstream colormath."""

from . import color_diff_matrix
from .color_objects import LabColor


def _lab(color):
    if color.__class__.__name__ != "LabColor":
        raise ValueError("Delta E functions can only be used with two LabColor objects.")
    return color.get_value_tuple()


def delta_e_cie1976(color1, color2):
    return float(color_diff_matrix.delta_e_cie1976(_lab(color1), [_lab(color2)])[0])


def delta_e_cie1994(
    color1, color2, K_L=1, K_C=1, K_H=1, K_1=0.045, K_2=0.015
):
    return float(
        color_diff_matrix.delta_e_cie1994(
            _lab(color1),
            [_lab(color2)],
            K_L=K_L,
            K_C=K_C,
            K_H=K_H,
            K_1=K_1,
            K_2=K_2,
        )[0]
    )


def delta_e_cie2000(color1, color2, Kl=1, Kc=1, Kh=1):
    return float(
        color_diff_matrix.delta_e_cie2000(
            _lab(color1), [_lab(color2)], Kl=Kl, Kc=Kc, Kh=Kh
        )[0]
    )


def delta_e_cmc(color1, color2, pl=2, pc=1):
    return float(
        color_diff_matrix.delta_e_cmc(_lab(color1), [_lab(color2)], pl=pl, pc=pc)[0]
    )
