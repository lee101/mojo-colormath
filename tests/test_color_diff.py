import numpy as np
import pytest

from colormath import color_diff_matrix as upstream

from mojocolormath import color_diff_matrix as mojo
from mojocolormath.color_diff import (
    delta_e_cie1976,
    delta_e_cie1994,
    delta_e_cie2000,
    delta_e_cmc,
)
from mojocolormath.color_objects import LabColor, XYZColor


@pytest.fixture(scope="module")
def lab_data():
    rng = np.random.default_rng(27)
    reference = np.array([52.3, 31.7, -42.1])
    samples = np.column_stack(
        (
            rng.uniform(0, 100, 2000),
            rng.uniform(-128, 128, 2000),
            rng.uniform(-128, 128, 2000),
        )
    )
    return reference, samples


def test_cie1976_upstream_parity(lab_data):
    reference, samples = lab_data
    assert np.allclose(
        mojo.delta_e_cie1976(reference, samples),
        upstream.delta_e_cie1976(reference, samples),
        rtol=1e-13,
        atol=1e-13,
    )


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"K_L": 2, "K_C": 0.8, "K_H": 1.2, "K_1": 0.048, "K_2": 0.014},
    ],
)
def test_cie1994_upstream_parity(lab_data, params):
    reference, samples = lab_data
    assert np.allclose(
        mojo.delta_e_cie1994(reference, samples, **params),
        upstream.delta_e_cie1994(reference, samples, **params),
        rtol=2e-13,
        atol=2e-13,
    )


@pytest.mark.parametrize("params", [{}, {"Kl": 2, "Kc": 0.8, "Kh": 1.2}])
def test_cie2000_upstream_parity(lab_data, params):
    reference, samples = lab_data
    assert np.allclose(
        mojo.delta_e_cie2000(reference, samples, **params),
        upstream.delta_e_cie2000(reference, samples, **params),
        rtol=2e-12,
        atol=2e-12,
    )


def test_cie2000_simd_tail_upstream_parity():
    rng = np.random.default_rng(312)
    reference = np.array([41.2, -17.5, 63.1])
    for length in range(1, 34):
        samples = rng.uniform((-10, -128, -128), (110, 128, 128), (length, 3))
        assert np.allclose(
            mojo.delta_e_cie2000(reference, samples),
            upstream.delta_e_cie2000(reference, samples),
            rtol=2e-12,
            atol=2e-12,
        )


def test_cie2000_parallel_threshold_upstream_parity():
    rng = np.random.default_rng(711)
    reference = np.array([54.1, 27.3, -38.9])
    samples = rng.uniform(
        (-10, -128, -128),
        (110, 128, 128),
        (mojo._CIE2000_PARALLEL_THRESHOLD + 3, 3),
    )
    assert np.allclose(
        mojo.delta_e_cie2000(reference, samples),
        upstream.delta_e_cie2000(reference, samples),
        rtol=2e-12,
        atol=2e-12,
    )


@pytest.mark.parametrize("params", [{}, {"pl": 1, "pc": 1}])
def test_cmc_upstream_parity(lab_data, params):
    reference, samples = lab_data
    assert np.allclose(
        mojo.delta_e_cmc(reference, samples, **params),
        upstream.delta_e_cmc(reference, samples, **params),
        rtol=2e-13,
        atol=2e-13,
    )


SHARMA_VECTORS = [
    ((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
    ((50, 3.1571, -77.2803), (50, 0, -82.7485), 2.8615),
    ((50, 2.8361, -74.0200), (50, 0, -82.7485), 3.4412),
    ((50, -1.3802, -84.2814), (50, 0, -82.7485), 1.0000),
    ((50, -1.1848, -84.8006), (50, 0, -82.7485), 1.0000),
    ((50, -0.9009, -85.5211), (50, 0, -82.7485), 1.0000),
    ((50, 0, 0), (50, -1, 2), 2.3669),
    ((50, -1, 2), (50, 0, 0), 2.3669),
    ((50, 2.49, -0.001), (50, -2.49, 0.0009), 7.1792),
    ((50, 2.49, -0.001), (50, -2.49, 0.0010), 7.1792),
    ((50, 2.49, -0.001), (50, -2.49, 0.0011), 7.2195),
    ((50, 2.49, -0.001), (50, -2.49, 0.0012), 7.2195),
    ((50, -0.001, 2.49), (50, 0.0009, -2.49), 4.8045),
    ((50, -0.001, 2.49), (50, 0.0010, -2.49), 4.8045),
    ((50, -0.001, 2.49), (50, 0.0011, -2.49), 4.7461),
    ((50, 2.5, 0), (50, 0, -2.5), 4.3065),
    ((50, 2.5, 0), (73, 25, -18), 27.1492),
    ((50, 2.5, 0), (61, -5, 29), 22.8977),
    ((50, 2.5, 0), (56, -27, -3), 31.9030),
    ((50, 2.5, 0), (58, 24, 15), 19.4535),
    ((50, 2.5, 0), (50, 3.1736, 0.5854), 1.0000),
    ((50, 2.5, 0), (50, 3.2972, 0), 1.0000),
    ((50, 2.5, 0), (50, 1.8634, 0.5757), 1.0000),
    ((50, 2.5, 0), (50, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


@pytest.mark.parametrize("first,second,expected", SHARMA_VECTORS)
def test_ciede2000_published_vectors(first, second, expected):
    actual = mojo.delta_e_cie2000(first, [second])[0]
    assert actual == pytest.approx(expected, abs=5e-5)


def test_scalar_delta_e_api():
    first = LabColor(50, 2.6772, -79.7751)
    second = LabColor(50, 0, -82.7485)
    assert delta_e_cie1976(first, second) > 0
    assert delta_e_cie1994(first, second) > 0
    assert delta_e_cie2000(first, second) == pytest.approx(2.04245968)
    assert delta_e_cmc(first, second) > 0


def test_scalar_delta_e_rejects_non_lab():
    with pytest.raises(ValueError, match="LabColor"):
        delta_e_cie2000(LabColor(50, 0, 0), XYZColor(0.1, 0.2, 0.3))


def test_matrix_shape_validation():
    with pytest.raises(ValueError, match="shape"):
        mojo.delta_e_cie2000([50, 0, 0], np.zeros((2, 4)))


@pytest.mark.parametrize(
    "function",
    [
        mojo.delta_e_cie1976,
        mojo.delta_e_cie1994,
        mojo.delta_e_cie2000,
        mojo.delta_e_cmc,
    ],
)
def test_empty_matrix_is_safe(function):
    result = function([50, 0, 0], np.empty((0, 3)))
    assert result.shape == (0,)
    assert result.dtype == np.float64


def test_noncontiguous_and_float32_inputs_are_normalized(lab_data):
    reference, samples = lab_data
    noncontiguous = samples.astype(np.float32)[::2]
    result = mojo.delta_e_cie2000(reference.astype(np.float32), noncontiguous)
    expected = upstream.delta_e_cie2000(
        reference.astype(np.float32).astype(np.float64),
        noncontiguous.astype(np.float64),
    )
    assert np.allclose(result, expected, rtol=2e-12, atol=2e-12)


def test_extended_precision_is_not_silently_narrowed():
    if np.dtype(np.longdouble).itemsize <= np.dtype(np.float64).itemsize:
        pytest.skip("long double is not wider than float64 on this platform")
    with pytest.raises(TypeError, match="narrow"):
        mojo.delta_e_cie2000(
            np.array([50, 0, 0], dtype=np.longdouble),
            np.zeros((1, 3)),
        )
    with pytest.raises(TypeError, match="narrow"):
        mojo.delta_e_cie2000(
            [50, 0, 0],
            np.zeros((1, 3), dtype=np.longdouble),
        )
