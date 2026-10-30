# Median Absolute Deviation of HL2 — measured (`median_ad_hl2`)

Source: jesse (MIT), `median_ad.py`, computing `scipy.stats.median_abs_deviation(hl2, window=5)`.
Found by the 2026-10-24 library catalog screen, round 2 (`docs/issues/screen/ind_screen_r2.py`,
candidate `j_median_ad_5`). Issue #119.

**Status: Gates A, B, C, D cleared. Gate E pending, run by issue-solver after this
session. Gate F (this repo): green except the three pre-existing known failures
(below) — no new failure.**

Shipped: `pandas_ta/statistics/median_ad_hl2.py`, one column `MEDIANAD_HL2_<length>`
(default `MEDIANAD_HL2_5`). Tests: `tests/test_median_ad_hl2.py` (11). Numbers below are
printed by `python docs/measure_median_ad_hl2.py` and
`python docs/measure_median_ad_hl2_gate_a.py`, except the suite counts in Gate F.
Environment: pandas 2.3.3, numpy 1.26.4, Python 3.12. Measured 2026-10-30.

## What the prototype computes, and what this port keeps

The issue's source citation names `scipy.stats.median_abs_deviation` (newer scipy function,
default `scale=1.0`) — not `scipy.stats.median_absolute_deviation` (the older, deprecated
function in the same package whose default `scale=1.4826` rescales to a normal-consistent
estimator). The round-2 prototype computes the **unscaled** statistic:

```
MAD[t] = median(|HL2[t-4..t] - median(HL2[t-4..t])|)
```

with no `1.4826` factor. This port reproduces that, over a rolling window of `length`
bars (default 5), then divides by `close` for the issue's "scale-free form: /close".

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass, against the SOURCE FORMULA, not the prototype | `median_ad_hl2` matches `scipy.stats.median_abs_deviation(window, scale=1.0)` applied per-window in an independent loop, bit-for-bit (max abs diff **0.0**) on 400 synthetic bars (`docs/measure_median_ad_hl2_gate_a.py`); `scipy` is a DEV-ONLY dependency (`setup.py extras_require["dev"]`), never imported by the shipped module. Hand-computed window: hl2 `[1,2,3,4,100]` → median 3, abs devs `[2,1,0,1,97]` → MAD 1, `/close` 10 → 0.1, pinned in `test_hand_computed_window` |
| B Causality | pass | 23-offset future-perturbation sweep (`range(20, 580, 25)`): real module 0 leaks. A single-bar forward-read mutant (`hl2.shift(-1)`) was tried first and rejected: it is not shipped in `tests/test_median_ad_hl2.py` because a rolling MEDIAN is an order statistic, robust to swapping in one ordinary future value out of five, so that probe caught the mutant unreliably (not on every offset) and would be a flaky guard. The shipped mutant instead shifts the WRITE index by the full window (`mad.shift(-length)`), so the boundary bar compares an all-original window against an all-future one: proved live (output differs from the real module), then caught at 23 of 23 |
| C Reachability | measured on a 3,000-bar synthetic tick-rounded walk (seed 7, tick 0.05): 2,996 of 3,000 finite (the 4 that do not are the `length=5` warm-up), 2,980 distinct values, 0 exact zeros, range [0.00016111, 0.02866025], median 0.00501987. Real BIST-frame counts are Gate E's job (deferred below), not re-measured here |
| D Scale-free | pass | ×8 / ×64 bit-identical (`test_power_of_two_scale_is_bit_identical`): a power-of-two multiplier changes only a float's exponent, not its mantissa, so `hl2`, the window median, and `close` all scale without rounding and the `/close` ratio is exact; ×10 / ×3.7 within 1e-12 (`test_other_scales_within_tolerance`), since those factors do round; `0 < fires < n` plus > 100 distinct values (`test_column_is_not_constant_and_fires`) so a constant column cannot pass |
| E Attribution | **PENDING**, run by issue-solver after this session, via `gate_e_overlap.py run --module pandas_ta.statistics.median_ad_hl2 --name median_ad_hl2` |
| F Suites | this repo, pandas 2.3.3: 3 failed / 3,269 passed / 83 skipped (2026-10-30). No new failure: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (CLAUDE.md known break, `docs/pine/` untracked), `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, CI-deselected), and `test_gate_e_ledger::test_every_indicator_that_needs_a_row_has_one` (expected per this issue's rules — no ledger row until the launcher runs Gate E; the companion parametrized test `test_every_new_indicator_has_gate_b_and_d_tests[median_ad_hl2]` already passes). Parent repo not run here |

## Prototype's measured overlap (not Gate E; from the issue, carried forward for context)

The round-2 prototype screen measured, on the engine's real data (`compute_all`,
n = 397,692, 89 ALTPORT-1 frames): max |ρ| **0.4989** vs `natr` → SHIP under the
0.76 ship line. That run is the prototype's, not this port's — this port's own Gate E
run, on the module as shipped, is the number that governs ship/revert here.

## To close

1. Launcher runs Gate E on `pandas_ta.statistics.median_ad_hl2` and records the row in
   `docs/gate_e_ledger.csv`.
2. A later receipt session fills in the measured max |ρ|, comparator, and verdict above,
   replacing "PENDING".
3. On a revert: delete the module, its export, `Category` entry, accessor, test file, the
   `docs/measure_median_ad_hl2*.py` scripts, and back out the README /
   `IndicatorDictionary.md` / `MLCompanionContract.md` / `test_altport2_ports.py` count
   bumps — keep this file as the receipt.
