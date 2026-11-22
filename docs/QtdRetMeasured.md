# qtd_ret — measured (issue #205)

> **Status: Gates A-E cleared (Gate E: DISCLOSE, max |ρ| 0.7975 vs `Dist_to_SMA_50_pct`, ship
> with disclosure, no revert owed). Gate F: this repo's listed subset only (below); both
> repos' whole suites: run by issue-solver in clean worktrees (see the PR body).**

Quarter-to-date return from the quarter's first open, as a fraction. Module
`pandas_ta/performance/qtd_ret.py`, column `QTD_RET`. Tests: `tests/test_qtd_ret.py` (24).
Numbers: `python docs/measure_qtd_ret.py`. Environment: numpy 1.26.4; the test module and the
CPU-restricted re-run (`python docs/measure_qtd_ret_cpu.py`, `NPY_DISABLE_CPU_FEATURES`
`AVX512F AVX512_SKX AVX2 FMA3`) both pass. Measured 2026-11-22.

Source is Reddit, tier 4: r/thinkorswim 1opks13 (2025-11-06),
https://www.reddit.com/r/thinkorswim/comments/1opks13/. Issue #205 restates it as: *"same,
quarter: month <= 3 -> 1, <= 6 -> 2, <= 9 -> 3, else 4"*, i.e. the poster's year-anchored
formula (`def ytd = Round((close / yearOpen - 1) * 100, 2)`) applied to the calendar quarter
instead of the calendar year. Existence, not evidence: nothing here tests the poster's claimed
use, a watchlist column showing the gain since the period start.

This port is `mtd_ret` (issue #206, `docs/MtdRetMeasured.md`, same source thread and quote)
with the anchoring period changed from calendar month to calendar quarter. `mtd_ret`'s own
receipt flagged this gap explicitly: *"Month only. The source's formula takes any period and
#205 asks for the quarter form, but that issue is still open and its numbers are its own, so no
period parameter was added here."* This file is that issue's own numbers, as a separate column
rather than a `period=` parameter on `mtd_ret` — the two share no code, mirroring the fork's
existing `mtd_ret`/(no `ytd_ret` shipped) split rather than adding a branch to a shipped,
measured module.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass, against the issue's restatement | The issue's quote and the thinkorswim thread give the period boundary, not a worked example; verified instead against a hand-derived 5-bar frame spanning a quarter boundary that is not a year boundary (Sep -> Oct 2023) and one that is both (Dec 2023 -> Jan 2024), reading 0.10, −0.10, 0.10, −0.50, 0.50. An independent per-bar loop (its own `(year, quarter)` tracking, not the module's `groupby` key) matches on all 900 bars of the synthetic fixture. The quarter boundary itself is `pandas`'s `DatetimeIndex.quarter`, checked against the issue's own month-range mapping (month 1-3 -> 1, 4-6 -> 2, 7-9 -> 3, 10-12 -> 4) rather than assumed equal to it |
| B Causality | pass | Rewriting all bars from `j` onward, all 899 offsets: real module **0 of 899** leak. Two mutants, `exec`'d in memory, each differing from the real module. `s.iloc[0]` -> `s.iloc[-1]` (each quarter anchored on its last open) leaks at **886 of 899**; the other 13 offsets are quarters' first bars, where no partial quarter sits behind the cut. `s.iloc[0]` -> `s.iloc[min(1, len(s) - 1)]` (anchored one bar late) leaks at **14 of 899**, exactly the quarters' second bars, which is why the sweep takes every offset. Unsorted frames are refused, not swept: see below |
| C Reachability | synthetic + real (Gate E run) | 900-bar business-day walk (seed 17), 14 calendar quarters: 900 of 900 non-NaN, 438 above the quarter's first open, 462 below, 900 distinct values, range [−0.218220, 0.332203], median −0.003209. Real data (Gate E run `is205-qtd_ret-ddf9146b`, 89 BIST frames, 398,849 pooled bars): 398,849 of 398,849 non-NaN, 393,683 non-zero (fires), 0 degenerate frames |
| D Scale-free | pass | x8/x64 bit-identical, max\|diff\| 0.0. x10/x3.7 max\|diff\| 2.22e-16 against a 1e-9 tolerance. Run on the same frame with Q2 2022's first open blanked (65 of 900 bars NaN, Q2 2022's business-day count), so the masks have something to match; they match at all four. `0 < 438 < 900` on the unblanked frame. All of the above reproduces identically under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` |
| E Attribution | **DISCLOSE** | Run `is205-qtd_ret-ddf9146b` (`gate_e_overlap.py run --module pandas_ta.performance.qtd_ret`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS). `QTD_RET` max \|ρ\| **0.7975** vs `Dist_to_SMA_50_pct` (manifest, n = 394,488); per-frame max median **0.8022** (0.0% of 89 frames ≥ 0.90). 0.76 ≤ 0.7975 < 0.80 is the DISCLOSE band (CLAUDE.md's Gate E row): ship, disclosed, no waiver owed. `mtd_ret`'s own run (DISCLOSE, 0.7997 vs `bias`) was the closest prior guess and landed close: both land in DISCLOSE against a moving-average-shaped comparator, not identical numbers. Recorded in `docs/gate_e_ledger.csv` (measured 2026-11-22) |
| F Suites | this repo, listed subset only | `python -m pytest -q tests/test_qtd_ret.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: **1 failed, 1354 passed, 7 skipped**. The one failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected until the launcher's Gate E run and a receipt session record this port's ledger row. Whole suites: run by issue-solver in clean worktrees (see the PR body) |

## Choices a reader should check

* **A frame starting mid-quarter** anchors its first partial quarter on its first bar's open,
  so those bars are a return since the frame started, not a quarter-to-date return. The frame
  cannot tell a truncated quarter from one whose first session is simply late.
* **A missing or zero first open blanks that quarter.** `transform("first")` would skip a NaN
  and read a later bar's open, a look-ahead a clean-open sweep cannot see. A zero would give
  `inf`, which `fillna` does not clear. Pinned by
  `test_missing_first_open_blanks_the_quarter_and_not_the_next` and
  `test_zero_first_open_blanks_the_quarter_and_not_the_next`.
* **An unusable index returns `None`**: not a `DatetimeIndex`, not ascending (NaT included), or
  different between `open_` and `close`. The accessor then leaves the frame unchanged, so one
  bad frame skips the column instead of aborting a `df.ta.strategy()` sweep.
  `test_no_datetime_index_returns_none_and_a_strategy_sweep_skips_it` runs a real sweep on a
  dated and an undated frame.
* **Quarters are calendar quarters of the index as written.** A tz-aware index resets on local
  time, pinned the same way `mtd_ret`'s month test is: two bars whose UTC instants both fall in
  Q1 but whose local (Europe/Istanbul, fixed UTC+3, no DST) representations fall in Q1 and Q2.
* **No period parameter.** `mtd_ret` and `qtd_ret` are two separate modules, not one module with
  a `period=` argument, following the split `mtd_ret`'s own receipt anticipated rather than
  retrofitting a parameter onto a already-shipped, measured column.

## Wiring

`Category` **368 -> 369** (`performance` **7 -> 8**); accessors **376 -> 377**. Touch points:
`pandas_ta/performance/qtd_ret.py`, `pandas_ta/performance/__init__.py`, `pandas_ta/__init__.py`
-> `Category["performance"]`, `pandas_ta/core.py` -> `AnalysisIndicators.qtd_ret`,
`tests/test_qtd_ret.py`. Also updated: `README.md` counts and row, `docs/IndicatorDictionary.md`
(regenerated, `QTD_RET` tagged `SF`), `docs/MLCompanionContract.md` (714 tagged columns, 349
`SF`), and `CATEGORY_TOTAL` in `tests/test_altport2_ports.py`.

## To close

All gates cleared (A-F, this repo's listed subset). Both repos' whole suites are run by the
launcher in clean worktrees.
