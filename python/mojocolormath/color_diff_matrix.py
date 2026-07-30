"""Vector-to-matrix delta-E functions, accelerated by Mojo."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from ._lib import addr, check_status, f64_triplets, lib

_CIE2000_PARALLEL_THRESHOLD = 65_536
_CIE2000_MAX_WORKERS = min(16, max(1, (os.cpu_count() or 1) // 2))
_CIE2000_EXECUTOR = ThreadPoolExecutor(
    max_workers=_CIE2000_MAX_WORKERS,
    thread_name_prefix="mojocolormath",
)


def _inputs(lab_color_vector, lab_color_matrix):
    if isinstance(lab_color_vector, np.ndarray):
        dtype = lab_color_vector.dtype
        if dtype.kind == "c":
            raise TypeError("complex Lab values are not supported")
        if dtype.kind == "f" and dtype.itemsize > np.dtype(np.float64).itemsize:
            raise TypeError(f"refusing to narrow {dtype} Lab values to float64")
    vector = np.ascontiguousarray(lab_color_vector, dtype=np.float64)
    if vector.shape != (3,):
        raise ValueError("lab_color_vector must have shape (3,)")
    matrix, scalar = f64_triplets(lab_color_matrix)
    result = np.empty(len(matrix), dtype=np.float64)
    return vector, matrix, result, scalar


def delta_e_cie1976(lab_color_vector, lab_color_matrix):
    vector, matrix, result, _ = _inputs(lab_color_vector, lab_color_matrix)
    if len(matrix):
        status = lib().mcm_delta_e_cie1976(
            addr(vector), addr(matrix), addr(result), len(matrix)
        )
        check_status(status, "mcm_delta_e_cie1976")
    return result


def delta_e_cie1994(
    lab_color_vector,
    lab_color_matrix,
    K_L=1,
    K_C=1,
    K_H=1,
    K_1=0.045,
    K_2=0.015,
):
    vector, matrix, result, _ = _inputs(lab_color_vector, lab_color_matrix)
    if len(matrix):
        status = lib().mcm_delta_e_cie1994(
            addr(vector),
            addr(matrix),
            addr(result),
            len(matrix),
            K_L,
            K_C,
            K_H,
            K_1,
            K_2,
        )
        check_status(status, "mcm_delta_e_cie1994")
    return result


def delta_e_cie2000(lab_color_vector, lab_color_matrix, Kl=1, Kc=1, Kh=1):
    vector, matrix, result, _ = _inputs(lab_color_vector, lab_color_matrix)
    function = lib().mcm_delta_e_cie2000
    count = len(matrix)
    if count == 0:
        return result
    if count < _CIE2000_PARALLEL_THRESHOLD or _CIE2000_MAX_WORKERS == 1:
        status = function(
            addr(vector), addr(matrix), addr(result), count, Kl, Kc, Kh
        )
        check_status(status, "mcm_delta_e_cie2000")
        return result

    workers = min(
        _CIE2000_MAX_WORKERS,
        (count + _CIE2000_PARALLEL_THRESHOLD - 1)
        // _CIE2000_PARALLEL_THRESHOLD,
    )
    chunk_size = (count + workers - 1) // workers
    futures = []
    for start in range(0, count, chunk_size):
        chunk_count = min(chunk_size, count - start)
        futures.append(
            _CIE2000_EXECUTOR.submit(
                function,
                addr(vector),
                addr(matrix) + start * matrix.strides[0],
                addr(result) + start * result.strides[0],
                chunk_count,
                Kl,
                Kc,
                Kh,
            )
        )
    for future in futures:
        check_status(future.result(), "mcm_delta_e_cie2000")
    return result


def delta_e_cmc(lab_color_vector, lab_color_matrix, pl=2, pc=1):
    vector, matrix, result, _ = _inputs(lab_color_vector, lab_color_matrix)
    if len(matrix):
        status = lib().mcm_delta_e_cmc(
            addr(vector), addr(matrix), addr(result), len(matrix), pl, pc
        )
        check_status(status, "mcm_delta_e_cmc")
    return result
