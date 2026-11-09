# mojo-colormath

`mojo-colormath` is a Mojo implementation of the compute-heavy core of
[colormath](https://github.com/gtaylor/python-colormath): color-space conversion
and CIE delta-E. Its Python modules mirror the upstream names and signatures for
the covered subset, while array entry points amortize the Python/FFI cost across
large color collections.

```python
from mojocolormath.color_conversions import convert_color, convert_color_array
from mojocolormath.color_diff import delta_e_cie2000
from mojocolormath.color_objects import LabColor, sRGBColor

red_lab = convert_color(sRGBColor(1.0, 0.0, 0.0), LabColor)
distance = delta_e_cie2000(red_lab, LabColor(50.0, 20.0, 30.0))

labs = convert_color_array(
    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    sRGBColor,
    LabColor,
)
print(red_lab, distance)
print(labs)
```

## Coverage

The listed object constructors, attribute names, `get_value_tuple`, RGB helpers,
`convert_color`, and scalar delta-E signatures follow colormath 3.0.0.

| area | covered |
| --- | --- |
| color objects | `LabColor`, `LuvColor`, `LCHabColor`, `LCHuvColor`, `XYZColor`, `xyYColor`, `sRGBColor` |
| conversion | every path among the covered objects, including D50/D65 Bradford adaptation and 2°/10° reference whites |
| color difference | CIE76, CIE94, CIEDE2000, and CMC through both `color_diff` and vector-to-matrix `color_diff_matrix` |
| batch extension | `convert_color_array(colors, source_cs, target_cs, ...)` for contiguous or array-like `(n, 3)` input |

Not covered are spectral colors and density, Adobe/Apple/other RGB working
spaces, HSL/HSV, CMY/CMYK, IPT, custom conversion graph registration, and
non-Bradford adaptation. Unsupported routes fail explicitly rather than
silently falling back to Python.

The test suite compares all four delta-E kernels, every direct conversion edge,
representative multi-edge paths, and every listed reference white with the real
conda-forge `colormath==3.0.0`. CIEDE2000 is additionally checked against the
published Sharma test pairs. Empty, non-contiguous, SIMD-remainder, threaded,
and dtype-boundary cases are covered explicitly.

## Install and run

```bash
pixi install
pixi run build
pixi run test
pixi run bench
```

`pixi run build` creates `dist/libmojo-colormath.so`. Imports also rebuild a
missing or stale library when a Mojo compiler is available. A packaged
deployment can set `MOJOCOLORMATH_LIB=/absolute/path/to/libmojo-colormath.so`
to use a prebuilt library.

## Performance

Measured with `pixi run bench` on an Intel Xeon E5-2697 v4 at 2.30 GHz,
Linux 6.8.0-147-generic x86-64, against colormath 3.0.0 (VERIFY phase, 2026-11-09;
see `bench/verify.md` for the full audit and repeat-run spread):

| case | mojo-colormath | colormath 3.0.0 | result |
| --- | ---: | ---: | ---: |
| CIE76, 1M Lab pairs | 3.11 ms | 52.83 ms | 16.99x faster |
| CIE94, 1M Lab pairs | 14.14 ms | 193.02 ms | 13.65x faster |
| CIEDE2000, 1M Lab pairs | 20.80 ms | 636.61 ms | 30.61x faster |
| CMC(2:1), 1M Lab pairs | 14.85 ms | 181.51 ms | 12.22x faster |
| Lab to XYZ, 100k colors | 1.11 ms | 995.13 ms | 896.51x faster |
| sRGB to Lab, 50k colors | 9.12 ms | 1352.70 ms | 148.27x faster |
| Lab to XYZ, 20k scalar calls | 22.16 ms | 194.79 ms | 8.79x faster |

The delta-E rows compare the same vector-to-matrix API and identical NumPy
inputs. Conversion batching is an extension: upstream exposes one color object
per call, so those rows include its unavoidable object and dispatch overhead.
That distinction matters. The common scalar Lab-to-XYZ route stays in Python
to avoid NumPy and FFI setup, while `convert_color_array` uses Mojo for batch
work.

No GPU path is included. CIEDE2000 is arithmetically plausible on a GPU,
but the profiled CPU implementation was already faster than upstream before
the optimization pass and therefore was outside the stated target set. The
only eligible benchmark was scalar Lab-to-XYZ, whose object-heavy workload
is not suitable for GPU execution.

## How it works

The batch numerical kernels live in one Mojo compilation unit. Python owns
input and output NumPy arrays, reuses already C-contiguous `float64` inputs
without copying, and passes their addresses and row count through `ctypes`.
Other ordinary numeric inputs are converted to packed `float64`; wider
floating-point arrays are rejected instead of silently narrowed.
The C ABI exports take buffer addresses as 64-bit `Int` values and reconstruct
`UnsafePointer[Float64, AnyOrigin[mut=True]]` inside Mojo.

Colors use row-major, array-of-structures layout:
`[c0_0, c0_1, c0_2, c1_0, c1_1, c1_2, ...]`. Mojo does not allocate or retain
memory. Exports validate non-empty buffer addresses and counts before pointer
construction, return a status code, and Python raises on any rejected call.
Each batch conversion edge writes into a caller-owned `(n, 3)` result;
multi-edge routes chain those arrays in Python. Delta-E writes one `float64`
per input Lab triplet. CIEDE2000 uses SIMD with a scalar remainder and a
thresholded, bounded thread pool for large independent chunks. Scalar Lab to
XYZ stays in Python to avoid NumPy allocation and FFI overhead.

## License

MIT
