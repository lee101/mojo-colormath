"""ctypes bridge to the compiled Mojo kernels."""

from __future__ import annotations

import ctypes
import os
import subprocess
from typing import Any

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB_PATH = os.environ.get("MOJOCOLORMATH_LIB") or os.path.join(
    ROOT, "dist", "libmojo-colormath.so"
)

I = ctypes.c_int64
STATUS = ctypes.c_int32
F = ctypes.c_double

_SIGNATURES = {
    "mcm_delta_e_cie1976": ([I, I, I, I], STATUS),
    "mcm_delta_e_cie1994": ([I, I, I, I, F, F, F, F, F], STATUS),
    "mcm_delta_e_cie2000": ([I, I, I, I, F, F, F], STATUS),
    "mcm_delta_e_cmc": ([I, I, I, I, F, F], STATUS),
    "mcm_lab_to_xyz": ([I, I, I, F, F, F], STATUS),
    "mcm_xyz_to_lab": ([I, I, I, F, F, F], STATUS),
    "mcm_xyz_to_luv": ([I, I, I, F, F, F], STATUS),
    "mcm_luv_to_xyz": ([I, I, I, F, F, F], STATUS),
    "mcm_cart_to_lch": ([I, I, I], STATUS),
    "mcm_lch_to_cart": ([I, I, I], STATUS),
    "mcm_xyz_to_xyy": ([I, I, I], STATUS),
    "mcm_xyy_to_xyz": ([I, I, I], STATUS),
    "mcm_srgb_to_xyz": ([I, I, I], STATUS),
    "mcm_xyz_to_srgb": ([I, I, I], STATUS),
    "mcm_transform3": ([I, I, I, I], STATUS),
}


def _build_if_needed() -> None:
    if os.environ.get("MOJOCOLORMATH_LIB"):
        if not os.path.exists(LIB_PATH):
            raise RuntimeError(f"MOJOCOLORMATH_LIB does not exist: {LIB_PATH}")
        return
    source = os.path.join(ROOT, "src", "colormath.mojo")
    stale = not os.path.exists(LIB_PATH) or os.path.getmtime(LIB_PATH) < os.path.getmtime(source)
    if stale:
        subprocess.run(
            ["bash", os.path.join(ROOT, "build", "build.sh")],
            cwd=ROOT,
            check=True,
        )


_loaded: ctypes.CDLL | None = None


def lib() -> ctypes.CDLL:
    global _loaded
    if _loaded is None:
        _build_if_needed()
        _loaded = ctypes.CDLL(LIB_PATH)
        for name, (argtypes, restype) in _SIGNATURES.items():
            fn = getattr(_loaded, name)
            fn.argtypes = argtypes
            fn.restype = restype
    return _loaded


def _reject_narrowing(values: Any) -> None:
    if not isinstance(values, np.ndarray):
        return
    dtype = values.dtype
    if dtype.kind == "c":
        raise TypeError("complex color values are not supported")
    if dtype.kind == "f" and dtype.itemsize > np.dtype(np.float64).itemsize:
        raise TypeError(f"refusing to narrow {dtype} color values to float64")


def f64_triplets(values) -> tuple[np.ndarray, bool]:
    _reject_narrowing(values)
    arr = np.asarray(values, dtype=np.float64)
    scalar = arr.ndim == 1
    if scalar:
        if arr.shape != (3,):
            raise ValueError("expected one color with shape (3,)")
        arr = arr.reshape(1, 3)
    elif arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError("expected colors with shape (n, 3)")
    arr = np.ascontiguousarray(arr)
    if arr.size and arr.strides != (arr.shape[1] * arr.itemsize, arr.itemsize):
        raise RuntimeError("internal error: color buffer is not packed")
    return arr, scalar


def addr(array: np.ndarray) -> int:
    address = int(array.ctypes.data)
    if array.size and address == 0:
        raise RuntimeError("NumPy returned a null address for a non-empty buffer")
    return address


def check_status(status: int, symbol: str) -> None:
    if status != 0:
        raise RuntimeError(f"Mojo kernel {symbol} rejected its buffer arguments")


def unary3(symbol: str, values, *params) -> np.ndarray:
    src, scalar = f64_triplets(values)
    result = np.empty_like(src)
    if len(src):
        status = getattr(lib(), symbol)(addr(src), addr(result), len(src), *params)
        check_status(status, symbol)
    return result[0] if scalar else result
