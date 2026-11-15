# Run summary — 2026-11-13, `ts-aggac-60`

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| TS-AGGAC-60 (PandasTa #96) — port tsfresh's `agg_autocorrelation(f_agg='mean', maxlag=10)` on 60 returns as `ts_aggac_60` | **PASS** | 4 (REVISE, REVISE, PASS, PASS) | 12 | Gate E, run by the launcher; then a receipt session |

## What shipped

`TS_AGGAC_60_10` (statistics) — the MEAN of the lag-1..lag-10
autocorrelations of the trailing 60 simple returns, in tsfresh's
normalisation. Dimensionless, invariant to any affine map of the returns,
bounded in **[-0.310043, +0.915798]** with the two ends deliberately
asymmetric (a window cannot be negative at ten lags at once).

Files:

* `pandas_ta/statistics/ts_aggac_60.py` — new
* `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py` (`Category`),
  `pandas_ta/core.py` — the other wiring touch points
* `tests/test_ts_aggac_60.py` — new, 167 passed / 2 skipped
* `docs/TsAggac60Measured.md`, `docs/measure_ts_aggac_60.py` — new
* `README.md` (329 / 337 / statistics 38), `docs/IndicatorDictionary.md`
  (regenerated), `docs/MLCompanionContract.md` (674 tagged / 316 `SF`),
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 329)
* `docs/reviews/auto-2026-11-13-ts-aggac-60/` — this folder

## Gates

| gate | state |
|---|---|
| A correctness | Done. Both published spellings of the source agree to 3.469e-17; the retyped adjusted `acf` is bit-exact against the installed statsmodels; the module is 5.7e-15 from the source applied window by window and 2.4e-15 from an exact `Fraction` oracle; an alternating window reads bit-exact 0 at an even `maxlag`; the eigenvector bounds are attained to 6.7e-16; five open readings and the screen prototype are priced. |
| B causality | Done. Real module 0/35 on three frames; eight mutants 35/35 on each. A ninth, `centered_span`, is live and caught 0/35 on clean frames and 13/35 where the trust test fires — disclosed, not buried. |
| C reachability | Synthetic only: 1,440 of 1,500 on five frames, all distinct and non-zero. Real-data counts are owed with Gate E. |
| D scale-free | Done. Bit-identical at x8/x64 on three frames and at `length` 12/20/250; masks identical and 9.5e-15 at x10/x3.7; invariant to an affine map of the RETURNS; `0 < fires < n` on every frame. |
| E attribution | **OWED.** No ledger row, and `test_gate_e_is_owed_and_has_no_ledger_row_yet` asserts there is none. The launcher runs `gate_e_overlap.py`; a receipt session records the row. |
| F suites | Module 167 passed / 2 skipped, and the same with numpy's AVX-512/AVX2/FMA3 kernels disabled. Full suite 3 failed / 6,884 passed / 85 skipped — the two `CLAUDE.md` Known breaks plus the owed Gate E row. |

## Three things a reader should not miss

1. **It is BLIND to a seasonality whose period divides `maxlag`.** Paths
   repeating every 2, 5 or 10 bars read medians of +0.000000 / +0.000008 /
   +0.000067 where the lag-1 column reads -1.0000 / -0.5872 / -0.5674. That
   is the `f_agg='mean'` aggregation the issue specifies, not a port defect.
2. **At a short `length` the bias can flip the sign.** On a 20,000-bar AR(1)
   path with `phi` = +0.50, population value +0.0999, the median reads
   +0.1054 / +0.0871 / +0.0431 at `length` 1000 / 200 / 60 and **-0.0514** at
   `length` 20.
3. **tsfresh would FABRICATE a 0.0 where this column reports NaN.**
   `agg_autocorrelation`'s `var < 1e-10` branch returns the mean of zeros,
   and 0.0 is an ordinary reading of this column — on a sigma = 1e-6 walk it
   fabricates 240 zeros where this module reads a normal ±0.066.

## What a later session owes

Listed in `docs/TsAggac60Measured.md`, *What a later session owes this file*:
the Gate E verdict with its band, pooled max \|rho\|, comparator, `n` and
per-frame max median; the ledger row; the real-data reachability counts; the
replacement of the owed-row test; and, if the run is STRUCK, the revert with
this receipt kept.
