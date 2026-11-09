# VERIFY — bench/verify.md

Second VERIFY pass, performed 2026-11-09. The README was assumed to overstate
until reproduced. All numbers below were measured in this session; no number
from a prior session was reused. The prior VERIFY pass (commit `82610dd`)
had already corrected the README to a canonical `pixi run bench` run; this
pass re-checked those figures against fresh measurements.

## Commands run, in order

- `pixi run build && pixi run test` — green. Build succeeded (deprecation
  warnings only); 99 passed in 0.97 s.
- `pixi run bench` — one full run (canonical run for corrections below).
- Three further full runs of `pixi run python bench/bench.py` for the 20%
  reproduction check. Four runs total this pass.

## Environment (this session)

- Machine: `Intel(R) Xeon(R) CPU E5-2697 v4 @ 2.30GHz;
  Linux-6.8.0-147-generic-x86_64-with-glibc2.39` (printed by `bench/bench.py`).
- Upstream: `colormath==3.0.0` via pixi (`pixi.toml` pins `colormath ==3.0.0`).

## What was reproduced

Rule: a figure that does not reproduce within 20% of the README value is
corrected in the README to the number measured in this session.

Canonical `pixi run bench` output (verbatim):

| case | mojo-colormath | colormath 3.0.0 | result |
| --- | ---: | ---: | ---: |
| CIE76, 1M Lab pairs | 3.56 ms | 66.43 ms | 18.64x faster |
| CIE94, 1M Lab pairs | 14.24 ms | 217.73 ms | 15.29x faster |
| CIEDE2000, 1M Lab pairs | 19.00 ms | 673.70 ms | 35.47x faster |
| CMC(2:1), 1M Lab pairs | 15.06 ms | 182.34 ms | 12.11x faster |
| Lab to XYZ, 100k colors | 1.29 ms | 1070.96 ms | 827.59x faster |
| sRGB to Lab, 50k colors | 9.25 ms | 1582.15 ms | 171.06x faster |
| Lab to XYZ, 20k scalar calls | 21.98 ms | 208.46 ms | 9.48x faster |

Per-row check of the prior README (before this pass) against the four
this-session runs:

| case | prior README mojo / upstream / result | this-session range (4 runs) | verdict |
| --- | --- | --- | --- |
| CIE76, 1M Lab pairs | 3.11 / 52.83 / 16.99x | mojo 3.22–3.56; upstream 61.81–66.43 | **Upstream 52.83 ms not reproduced** — all 4 runs 17–26% higher. Corrected to canonical 66.43 ms; result 18.66x. |
| CIE94, 1M Lab pairs | 14.14 / 193.02 / 13.65x | mojo 14.04–15.32; upstream 204.79–217.73 | Upstream 6–13% low vs all runs; within 20% but corrected to canonical 217.73 ms (the measured value); result 15.29x. |
| CIEDE2000, 1M Lab pairs | 20.80 / 636.61 / 30.61x | mojo 19.00–21.37; upstream 582.82–678.70 | Reproduced within 20%. Corrected to canonical run (19.00 / 673.70); result 35.47x. |
| CMC(2:1), 1M Lab pairs | 14.85 / 181.51 / 12.22x | mojo 13.44–15.25; upstream 171.07–248.44 | Reproduced in 3 of 4 runs; one run (248.44 ms) spiked +37%. Corrected to canonical 15.06 / 182.34; result 12.11x. |
| Lab to XYZ, 100k colors | 1.11 / 995.13 / 896.51x | mojo 1.06–1.29; upstream 926.31–1070.96 | Reproduced within 20%. Corrected to canonical 1.29 / 1070.96; result 830.20x. |
| sRGB to Lab, 50k colors | 9.12 / 1352.70 / 148.27x | mojo 9.04–9.64; upstream 1261.08–1582.15 | Reproduced within 20%. Corrected to canonical 9.25 / 1582.15; result 171.06x. |
| Lab to XYZ, 20k scalar calls | 22.16 / 194.79 / 8.79x | mojo 21.98–22.76; upstream 177.61–208.46 | Reproduced within 20%. Corrected to canonical 21.98 / 208.46; result 9.48x. |

Corrections applied: the README table now shows only the canonical
`pixi run bench` numbers from this session. The one figure that failed the
20% test (CIE76 upstream 52.83 ms) is replaced by 66.43 ms. No row was
removed. No row is or was slower than upstream — all 7 rows are "faster" in
every one of the 4 runs, so there was no slower-row to preserve; the rule
about not hiding slower rows did not trigger.

Note: upstream wall time varies ±15–25% run to run on this machine (e.g.
CMC 171–248 ms), so any single number is a sample, not a stable constant.
The spread above is the honest uncertainty.

## What could not be reproduced

- The exact prior README figures (e.g. CIE76 upstream 52.83 ms, which is
  17–26% below every this-session run). Exact reproduction of a prior
  session's single run is not possible and is not claimed; the table now
  carries this session's canonical numbers.
- Nothing else failed: all 7 cases ran, all comparisons executed, and
  direction and magnitude agree with the prior README.

## Fairness checks (bench/bench.py)

The benchmark file was read in full. Findings:

1. **Same input, both sides.** Delta-E rows: both sides receive the identical
   `reference` array and `(1_000_000, 3)` `samples` array (same variable,
   `default_rng(42)`). Conversion rows: upstream loops operate over objects
   pre-constructed from the same `lab_values` / `rgb_values` arrays. Scalar
   row: both sides convert pre-constructed scalar objects with the same
   values, 20,000 times each.
2. **No skipped work on one side.** Delta-E outputs verified same shape
   `(1_000_000,)` and values equal (max abs diff 2.8e-14 CIE76, 4.3e-14
   CIE94, 3.1e-12 CIEDE2000, 8.5e-14 CMC — scratch check this session,
   not committed). Conversions return full `(100000, 3)` / `(50000, 3)`
   arrays; row-0 checked against upstream scalar conversion and matches.
   Scalar row materializes 20,000 results on both sides (list
   comprehensions, no early exit). `timeit` re-invokes each function 3
   times and takes the best; neither side caches across iterations.
3. **Known caveat (disclosed in README, confirmed):** conversion-batching
   rows compare a batch Mojo entry point against upstream's per-object API,
   so they include upstream's unavoidable object/dispatch overhead. The
   README states this explicitly; the scalar Lab→XYZ row is the
   like-for-like comparison. No benchmark change was made.
4. **Multithreading note:** mojo CIEDE2000 uses a `ThreadPoolExecutor`
   (up to 16 workers, threshold 65,536 pairs) for large inputs; upstream
   is single-threaded (`python/mojocolormath/color_diff_matrix.py`).
   This is an implementation property of the port, not a benchmark
   artifact, but matters when comparing against single-threaded upstream.
   It is visible in the canonical numbers (mojo ~19 ms vs single-thread
   raw kernel an order of magnitude slower per prior analysis).

## Test parity (`git log -p -- tests/`)

- Only two commits ever touched `tests/`: `151392e` (initial creation of
  all three test files) and `d3bcee3` (accel pass). `git log -p --all --
  tests/` shows **no removed assertions and no loosened tolerances** —
  every `-` line is a `---` header; the only change after creation adds
  one test (`test_scalar_lab_to_xyz_rejects_unsupported_rgb_type`) and one
  import.
- Current tolerances match the initial commit: `tests/test_color_diff.py`
  uses 1e-13–2e-12 on upstream-parity `allclose`; `tests/test_conversions.py`
  uses 2e-9/1e-8 on direct conversion parity and 5e-9/1e-7 on batch parity.
  The Sharma published-vectors check (34 vectors, `abs=5e-5`) is present.
- No restoration was needed. `git log --all --oneline` confirms no later
  commit modified `tests/`.
- Test suite result this session: 99 passed.

## What was changed

- `README.md` performance table: corrected to this session's canonical
  `pixi run bench` numbers (CIE76 upstream 52.83 → 66.43 ms was the only
  figure failing the 20% test; the rest were updated to the measured
  canonical values). No other README wording changed.
- `bench/verify.md`: this file (rewritten for this second pass).
- No source code was changed. No test file was changed.

## Verification state at end of this phase

- `pixi run build && pixi run test`: re-run after the README edits, build
  OK (warnings only), 99 passed.
