# Signal-to-Noise Ratio — measured (`ttr_snr_20`)

PandasTa issue #149. Source: R TTR (GPL-2.0), `SNR.R: abs(Cl - lag(Cl, n)) / ATR(n)`. Per
CLAUDE.md ("Library code (R TTR, GPL-2.0): existence, not evidence"), TTR is not installed,
vendored or run as an oracle here — `SNR.R`'s own source is NOT in this worktree; the formula
is recalled from the issue text, not read off TTR's code.

**Status: Gates A, B, D cleared (measured below). Gate C synthetic only (real-data counts
owed). Gate E: pending, run by issue-solver after this session.** `ttr_snr_20` is wired into
`Category["volatility"]`, so `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally until the launcher's Gate E run and a later receipt session record the ledger
row — expected, per the porting rules, not a defect of this port.

Shipped: `pandas_ta/volatility/ttr_snr_20.py`, one column `TTR_SNR_{length}` (default
`TTR_SNR_20`). Tests: `tests/test_ttr_snr_20.py` (21). Numbers: `python docs/measure_ttr_snr_20.py`
and `python docs/measure_ttr_snr_20_cpu.py`. Environment: Python 3.11.2, pandas 2.3.3,
numpy 1.26.4. Measured 2026-11-23.

## The one Gate-A decision the source formula does not spell out

`SNR.R` calls `ATR(HLC, n)`, not a specific smoothing. TTR's own `ATR()` default smooths with
Wilder's recursion (`wilder=TRUE` passed internally); this fork's own `atr()` default is
`mamode="rma"`, explicitly **not** Wilder's smoothing (`atr.py`'s own docstring says so). So
`ttr_snr_20` calls `atr(..., mamode="wrma")` explicitly — this fork's name for Wilder's
smoothing — to match the SOURCE formula's `ATR(n)`, not this package's own `atr()` default.
Picking the default `rma` instead would be a different column: not measured here (out of
scope — the port's job is to match the cited source, not catalogue every alternative), but it
is the kind of silent substitution Gate A exists to catch, so it is named rather than left
implicit.

`n = 20` is the issue's own fixed parameter ("TTR has no default"), hence the module name.

## The source formula is already scale-free

Unlike most of this fork's ports (`pfe`, `tf_median_absdiff_20`, …), no log-return or percent
conversion was needed: both the numerator (a price difference) and the denominator (an ATR,
itself built from price differences) carry one power of price, so their ratio is dimensionless
as written.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (independent oracle; no TTR source line cited — `SNR.R` is not in this worktree) | A scalar Python loop that reimplements Wilder's SMA-seeded ATR recursion from scratch (not imported from the module) agrees with the shipped column on 1,180 of 1,180 compared bars of a 1,200-bar synthetic OHLC walk, max\|diff\| 1.24e-14 (floating-point rounding only). A 5-bar hand-derived window (`test_hand_derived_window_is_exact`) pins three bars' exact values by arithmetic. |
| B Causality | pass | 31-offset future-perturbation sweep (`range(40, 1100, 35)`, past the 20-bar warm-up): real module leaks at 0 of 31. Two mutants (`importlib`-read source, `exec`'d in memory): the final `move / atr_val` write shifted 10 bars earlier, and the close read into `move` taken one bar forward (`close.shift(-1)` instead of `close`). Both are live (differ from the real module) and both are caught at 31 of 31 offsets on the one base/perturbation frame pair tested. |
| C Reachability | synthetic only | 1,200-bar OHLC walk (seed 11, σ=0.02): 1,180 of 1,200 finite (20-bar warm-up), 1,180 non-zero, 1,180 distinct values, range [0.0092, 11.666], mean 3.453. **Real-data counts owed** (the Gate E run supplies them). |
| D Scale-free | pass | ×8 / ×64 bit-identical on all 1,180 fired bars with matching NaN masks (both legs are price-scale quantities, and `k*a / k*b == a / b` exactly under a power-of-two `k` in IEEE float — no subtraction of rescaled values loses the exactness here because `true_range`'s diffs and `wilder_rma`'s weighted sums are each individually scale-invariant under a power-of-two rescale). ×10 / ×3.7 within 1.954e-14 absolute / 4.86e-13 relative. `0 < 1,180 < 1,200` fires, 1,180 distinct values (non-constant). Re-run clean with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_ttr_snr_20_cpu.py`): same 21/21 tests pass: no exact bit-count or Spearman digit beyond a stated tolerance is pinned, so the CPU-variant kernels on a GitHub runner cannot break this suite. |
| E Attribution | **pending** | run by issue-solver after this session, via `gate_e_overlap.py run --module pandas_ta.volatility.ttr_snr_20`. |
| F Suites | this repo only (per the porting rules, the launcher runs both whole suites) | `python -m pytest -q tests/test_ttr_snr_20.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: **165 passed, 7 skipped.** (`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails on its own, naming `ttr_snr_20` as the indicator owed a row — expected, not a finding; see Status above.) Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## A frozen price series does not read `0 / 0`

A totally flat series (`high == low == close` constant from bar 0) has `move == 0` and `TR == 0`
on every bar, but `true_range`'s own `non_zero_range` helper already adds a float epsilon
(`sflt.epsilon`, ≈2.22e-16) to a degenerate zero high-low range — existing behaviour of a
dependency this module calls, not something added here. Measured: ATR settles at exactly
2.220446049250313e-16 (one float64 ulp) and `move` is exactly 0.0, so the ratio reads a clean
`0.0`, never NaN. A 30-bar freeze following a volatile 30-bar lead-in behaves the same way for
a different reason: Wilder's recursion decays the ATR toward zero by a factor of ~0.95 per
frozen bar, which is not enough half-lives in 30 bars to reach exact 0, so the ratio is again a
clean 0.0 on the frozen tail, never NaN. Both cases are pinned by
`test_a_totally_flat_series_reads_zero_not_nan` and
`test_frozen_after_a_volatile_run_decays_but_does_not_reach_exactly_zero`.

No ternary or zero-guard is in the source formula, so none is added in this module; the
zero-safety is inherited from `true_range`.

## Wiring counts, read back

`Category` total 380 (was 379), `Category["volatility"]` 39 (was 38). README headline and the
`volatility (39)` row updated; `docs/IndicatorDictionary.md` regenerated (`382` indicators
probed, 1 new SF-tagged row); `docs/MLCompanionContract.md`'s running SF tally updated 358 → 359
(725 tagged columns total, was 724); `CATEGORY_TOTAL` 380 and `CATEGORY_BUCKETS["volatility"]` 39
in `tests/test_altport2_ports.py`.

## To close

1. Run Gate E on the port: `gate_e_overlap.py run --module pandas_ta.volatility.ttr_snr_20
   --name ttr_snr_20`, then `python docs/gate_e_ledger.py record <run dir> --measured
   YYYY-MM-DD`, filling in this file's Gate E row and Gate C's real-data counts.
2. Apply CLAUDE.md's thresholds (SHIP / DISCLOSE / DISCLOSE_GAP / STRUCK). On a revert: remove
   the module, its wiring, and its tests; keep this file as the receipt.
3. Both whole suites, in clean worktrees (per the porting rules, run by the launcher).
