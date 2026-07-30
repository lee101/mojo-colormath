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
Linux 6.8.0-136-generic x86-64, against colormath 3.0.0:

| case | mojo-colormath | colormath 3.0.0 | result |
| --- | ---: | ---: | ---: |
| CIE76, 1M Lab pairs | 3.99 ms | 75.72 ms | 18.98x faster |
| CIE94, 1M Lab pairs | 13.69 ms | 218.03 ms | 15.92x faster |
| CIEDE2000, 1M Lab pairs | 26.05 ms | 693.71 ms | 26.63x faster |
| CMC(2:1), 1M Lab pairs | 19.51 ms | 264.83 ms | 13.57x faster |
| Lab to XYZ, 100k colors | 1.15 ms | 1034.15 ms | 902.81x faster |
| sRGB to Lab, 50k colors | 9.35 ms | 1531.90 ms | 163.77x faster |
| Lab to XYZ, 20k scalar calls | 41.46 ms | 192.02 ms | 4.63x faster |

The delta-E rows compare the same vector-to-matrix API and identical NumPy
inputs. Conversion batching is an extension: upstream exposes one color object
per call, so those rows include its unavoidable object and dispatch overhead.
That distinction matters. The common scalar Lab-to-XYZ route stays in Python
to avoid NumPy and FFI setup, while `convert_color_array` uses Mojo for batch
work.

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
