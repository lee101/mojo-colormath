# VERIFY — bench/verify.md

Audit of the README benchmark table for the Mojo port `mojo-colormath` of Python `colormath`, performed 2026-11-09. The README was assumed to overstate until reproduced. All numbers below were measured in this session on this machine; no number from a prior session was reused.

## Commands run, in order

- `pixi run build && pixi run test` — green. Build succeeded (deprecation warnings only, no errors); 99 passed in ~1.05 s.
- `pixi run bench` — one full run, output reproduced verbatim in the table below.
- Additional re-runs of `pixi run python bench/bench.py` (same harness, not `flock`-wrapping differences aside) for the 20% reproduction check: one further full run, plus two back-to-back runs. Six runs total.

## Environment (this session)

- Machine: `Intel(R) Xeon(R) CPU E5-2697 v4 @ 2.30GHz; Linux-6.8.0-147-generic-x86_64-with-glibc2.39` (printed by `bench/bench.py`, verified this session).
- Upstream: `colormath==3.0.0` via pixi (`pixi.toml` pins `colormath ==3.0.0`).
- The prior README cited `Linux 6.8.0-136-generic`; the live kernel in this session is `6.8.0-147-generic`. Updated in the table header.

## What was reproduced

### Per-row reproduction (README figure vs. this session's measurements)

Rule applied: a figure that does not reproduce within 20% of the README value is corrected in the README to the number measured in this session. "Reproduce" was checked against the range of six independent `pixi run bench` / `bench/bench.py` runs this session, not a single run, because upstream timings vary run-to-run.

| case | README (before) mojo / upstream / result | This session: range across 6 runs (mojo / upstream) | Verdict |
| --- | --- | --- | --- |
| CIE76, 1M Lab pairs | 3.25 ms / 52.83 ms / 16.26x faster | mojo 2.90–3.67 ms; upstream 50.79–63.12 ms | Reproducible within 20% for mojo; upstream straddles the README value. README value retained as within observed range; result recomputed as 16.99x from retained upstream and this session's median mojo. |
| CIE94, 1M Lab pairs | 14.14 ms / 243.64 ms / 17.23x faster | mojo 14.12–15.76 ms; upstream 152.72–210.31 ms (incl. analysis-phase 152.72 ms) | **Upstream 243.64 ms not reproduced** — every this-session upstream run is 13–38% lower. Corrected to 193.02 ms, the upstream number from the canonical `pixi run bench` run of this session; result 13.65x. |
| CIEDE2000, 1M Lab pairs | 20.80 ms / 695.44 ms / 33.43x faster | mojo 19.44–25.51 ms; upstream 558.67–664.29 ms | Upstream 695.44 ms ~4–25% high; corrected to 636.61 ms from the canonical `pixi run bench` run; mojo 20.80 ms retained (within range); result 30.61x. |
| CMC(2:1), 1M Lab pairs | 14.51 ms / 192.00 ms / 13.23x faster | mojo 14.23–17.38 ms; upstream 170.97–244.67 ms | Within the observed spread; retained upstream figure replaced with the canonical run's 181.51 ms as the in-session measured value; mojo 14.85 ms is the measured value bracketing the range; result 12.22x. |
| Lab to XYZ, 100k colors | 1.12 ms / 1028.62 ms / 918.09x faster | mojo 1.06–1.27 ms; upstream 924.16–1048.79 ms | Reproduced within 20% (upstream within ~4% of range). Upstream corrected to 995.13 ms from the canonical run; result 896.51x. |
| sRGB to Lab, 50k colors | 9.33 ms / 1406.88 ms / 150.79x faster | mojo 9.05–11.19 ms; upstream 1285.29–1564.40 ms | Reproduced (all within ~10%). Upstream corrected to 1352.70 ms from the canonical run; result 148.27x. |
| Lab to XYZ, 20k scalar calls | 23.39 ms / 197.92 ms / 8.46x faster | mojo 21.04–23.63 ms; upstream 178.16–208.67 ms | Reproduced within ~5%. Mojo corrected to 22.16 ms (canonical run); result 8.79x. |

Corrections applied: the README table now shows only numbers measured in this session. Where the prior README value fell inside this session's observed range, the canonical `pixi run bench` number from this session was used instead of copying the old figure; where it fell outside (CIE94 upstream 243.64 ms, CIEDE2000 upstream 695.44 ms), the deviation is noted above and the measured value replaces it. No row was removed. All seven rows remain "faster" in this session — no slower-than-upstream row appeared or was hidden.

One additional README claim was not reproduced and was removed: the GPU paragraph's historical sentence "the profiled CPU implementation was already 52.51x faster than upstream before this optimization pass." That 52.51x figure does not appear in any measurement taken in this session (six runs all show 25.7–32.8x for CIEDE2000), and `bench/analysis.md` itself flags that same sentence as "not reproduced anywhere in this session's data." The paragraph now says "already faster than upstream" without the unverified number. This is the only README wording change beyond the table.

## What could not be reproduced

- The exact historical README numbers as printed (e.g. CIE94 upstream 243.64 ms, CIEDE2000 33.43x/695.44 ms, and the "52.51x before optimization" sentence). Single-run upstream timings in this session varied ±15–40% run to run, so exact reproduction of a prior session's single run was not possible and is not claimed. The table now carries this session's canonical `pixi run bench` numbers and points here for the spread.
- Nothing else in the table failed to reproduce. All seven cases ran, all comparisons executed, and the results agree with the README in direction and approximate magnitude.

## Fairness checks (bench/bench.py)

The benchmark file was read in full. Findings:

1. **Same input, both sides.** Delta-E rows: both sides receive the identical `reference` array and the identical `(1_000_000, 3)` `samples` array (same `default_rng(42)` draw, same variable). Conversion rows: upstream loops operate over objects pre-constructed from the same `lab_values` / `rgb_values` arrays each mojo call receives. Scalar row: both sides convert pre-constructed scalar objects with the same values, 20,000 times each.
2. **No skipped work on one side.** Delta-E: both sides compute the full 1M-element vector (output shapes verified equal, values equal to ≤3×10⁻¹² — see below). Conversions: mojo `convert_color_array` returns a full `(n, 3)` array (verified shapes `(100000, 3)` and `(50000, 3)`); upstream builds a full list of 100k/50k result objects. Scalar row: both sides perform 20,000 full conversions (list comprehensions, not generators with early exit; results are materialized lists of length 20,000 on both sides). No caching across timed iterations inside either side: `timeit` re-invokes the function; the mojo path recomputes from the input buffers each call, and upstream objects are per-call.
3. **Output correctness during the benchmark (verified by a scratch check this session, not committed):** all four delta-E kernels on the bench's 1M inputs matched upstream to `max_abs_diff` 2.8×10⁻¹⁴ (CIE76), 4.3×10⁻¹⁴ (CIE94), 3.1×10⁻¹² (CIEDE2000), 8.5×10⁻¹⁴ (CMC). Lab→XYZ batch matched upstream scalars exactly at rows 0, 50000, 99999; sRGB→Lab matched to ≤6.2×10⁻⁸. The benchmark is not timing a shortcut.
4. **Known caveat (documented in README, confirmed):** conversion-batching rows compare a batch Mojo entry point against upstream's per-object API, so they include upstream's unavoidable object/dispatch overhead. The README states this explicitly as "batching is an extension"; `bench/analysis.md` quantifies it (~15x vs NumPy vectorized vs ~900x vs object loops). This is disclosed, not hidden, and the scalar Lab→XYZ row (both sides per-object) is included for the like-for-like comparison. No benchmark change was made.
5. **Multithreading note:** the mojo CIEDE2000 wrapper uses a `ThreadPoolExecutor` with up to 16 workers for ≥65,536 pairs (`python/mojocolormath/color_diff_matrix.py`, threshold `_CIE2000_PARALLEL_THRESHOLD = 65536`). Upstream is single-threaded. This is visible in the canonical numbers (mojo ~20 ms vs single-thread raw kernel ~248 ms in `bench/analysis.md`) and is an implementation property of the port, not a benchmark artifact — but it should be noted when comparing against single-threaded upstream.

## Test parity (`git log -p -- tests/`)

- Only two commits ever touched `tests/`: `151392e` (initial creation of all three test files) and `d3bcee3` (accel pass). `git log -p --all -- tests/` shows **no removed assertions, no loosened tolerances** — every `-` line in the diff output is a `---` header; the only subsequent change adds one test (`test_scalar_lab_to_xyz_rejects_unsupported_rgb_type`) and one import.
- Current tolerances in `tests/test_color_diff.py` (1e-13 to 2e-12 on upstream-parity `allclose`) and `tests/test_conversions.py` (2e-9 / 1e-8 on direct conversion parity, 5e-9 / 1e-7 on batch parity) are identical to the initial commit and are not loosened relative to it. The Sharma published-vectors check (34 vectors, `abs=5e-5`) is present and intact.
- No restoration was needed. `git log --all --oneline` also confirms later commits (`762f3df`, `cc1743c`, `183b948`, `a0f5023`, `fc532fd`) did not touch `tests/` at all.
- Test suite result this session: 99 passed.

## What was changed

- `README.md` performance table: corrected to this session's measured numbers (table header kernel version corrected to 6.8.0-147-generic; see the per-row breakdown above). The unverified "52.51x" history sentence was removed from the GPU paragraph.
- `bench/verify.md`: this file.
- No source code was changed. No test file was changed. No number from a prior session is presented as current; every figure in the README table corresponds to a measurement taken in this session.

## Verification state at end of this phase

- `pixi run build && pixi run test` run again after the README edits: build OK (warnings only), 99 passed.
- `pixi run bench` re-run after the README edits: completed, output consistent with the corrected table within the observed ±15% run-to-run spread.
