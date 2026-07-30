"""Benchmark Mojo kernels against colormath 3.0.0 on identical inputs."""

from __future__ import annotations

import math
import os
import platform
import time

import numpy as np
from colormath import color_diff_matrix as upstream_diff
from colormath.color_conversions import convert_color as upstream_convert
from colormath.color_objects import LabColor as UpLab
from colormath.color_objects import sRGBColor as UpRGB
from colormath.color_objects import XYZColor as UpXYZ

from mojocolormath import color_diff_matrix as mojo_diff
from mojocolormath.color_conversions import (
    convert_color as mojo_convert,
    convert_color_array,
)
from mojocolormath.color_objects import LabColor, sRGBColor, XYZColor


def timeit(function, repeat=3):
    best = math.inf
    for _ in range(repeat):
        start = time.perf_counter()
        function()
        best = min(best, time.perf_counter() - start)
    return best


def cpu_name():
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def main():
    rng = np.random.default_rng(42)
    reference = np.array([52.3, 31.7, -42.1])
    samples = np.ascontiguousarray(
        np.column_stack(
            (
                rng.uniform(0, 100, 1_000_000),
                rng.uniform(-128, 128, 1_000_000),
                rng.uniform(-128, 128, 1_000_000),
            )
        )
    )

    cases = [
        (
            "CIE76, 1M Lab pairs",
            lambda: mojo_diff.delta_e_cie1976(reference, samples),
            lambda: upstream_diff.delta_e_cie1976(reference, samples),
        ),
        (
            "CIE94, 1M Lab pairs",
            lambda: mojo_diff.delta_e_cie1994(reference, samples),
            lambda: upstream_diff.delta_e_cie1994(reference, samples),
        ),
        (
            "CIEDE2000, 1M Lab pairs",
            lambda: mojo_diff.delta_e_cie2000(reference, samples),
            lambda: upstream_diff.delta_e_cie2000(reference, samples),
        ),
        (
            "CMC(2:1), 1M Lab pairs",
            lambda: mojo_diff.delta_e_cmc(reference, samples),
            lambda: upstream_diff.delta_e_cmc(reference, samples),
        ),
    ]

    lab_values = np.ascontiguousarray(
        np.column_stack(
            (
                rng.uniform(5, 95, 100_000),
                rng.uniform(-70, 70, 100_000),
                rng.uniform(-70, 70, 100_000),
            )
        )
    )
    upstream_labs = [UpLab(*row, illuminant="d50") for row in lab_values]
    cases.append(
        (
            "Lab to XYZ, 100k colors",
            lambda: convert_color_array(
                lab_values, LabColor, XYZColor, illuminant="d50"
            ),
            lambda: [upstream_convert(color, UpXYZ) for color in upstream_labs],
        )
    )

    rgb_values = np.ascontiguousarray(rng.uniform(0, 1, (50_000, 3)))
    upstream_rgbs = [UpRGB(*row) for row in rgb_values]
    cases.append(
        (
            "sRGB to Lab, 50k colors",
            lambda: convert_color_array(rgb_values, sRGBColor, LabColor),
            lambda: [upstream_convert(color, UpLab) for color in upstream_rgbs],
        )
    )

    mojo_scalar = LabColor(52.3, 31.7, -42.1)
    upstream_scalar = UpLab(52.3, 31.7, -42.1)
    cases.append(
        (
            "Lab to XYZ, 20k scalar calls",
            lambda: [mojo_convert(mojo_scalar, XYZColor) for _ in range(20_000)],
            lambda: [
                upstream_convert(upstream_scalar, UpXYZ) for _ in range(20_000)
            ],
        )
    )

    mojo_diff.delta_e_cie2000(reference, samples[:1])
    rows = []
    for name, mojo_fn, upstream_fn in cases:
        mojo_seconds = timeit(mojo_fn)
        upstream_seconds = timeit(upstream_fn)
        speedup = upstream_seconds / mojo_seconds
        outcome = (
            f"{speedup:.2f}x faster"
            if speedup >= 1.0
            else f"{1.0 / speedup:.2f}x slower"
        )
        rows.append((name, mojo_seconds * 1000, upstream_seconds * 1000, outcome))

    print(f"Machine: {cpu_name()}; {platform.platform()}")
    print()
    print("| case | mojo-colormath | colormath 3.0.0 | result |")
    print("| --- | ---: | ---: | ---: |")
    for name, mojo_ms, upstream_ms, outcome in rows:
        print(f"| {name} | {mojo_ms:.2f} ms | {upstream_ms:.2f} ms | {outcome} |")


if __name__ == "__main__":
    main()
