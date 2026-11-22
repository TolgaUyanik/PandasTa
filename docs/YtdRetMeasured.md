# ytd_ret — measured (issue #204)

> **Status: Gates A, B, D cleared on synthetic frames. Gate E DISCLOSE** (measured 2026-11-22 by
> the owner on this module: max |ρ| 0.7614 vs `Dist_to_SMA_200_pct`; ships disclosed, see below).
> **Gate F this repo only.**

Year-to-date return from the year's first open, as a fraction. Module
`pandas_ta/performance/ytd_ret.py`, column `YTD_RET`. Tests: `tests/test_ytd_ret.py` (23).
Numbers: `python -m docs.measure_ytd_ret`. Measured 2026-11-20.

Source is Reddit, tier 4: r/thinkorswim 1opks13 (2025-11-06), the same thread as `mtd_ret`
(#206), quoted by the issue as `def ytd = Round((close / yearOpen - 1) * 100, 2);`. Existence,
not evidence: nothing here tests the poster's claimed use, a watchlist column showing the gain
since the period start.

## Gate E — DISCLOSE (ships disclosed)

Measured 2026-11-22 by the owner on this module, after the branch was merged with `dev`; row
`pr355-ytd_ret` in `docs/gate_e_ledger.csv`. `gate_e_overlap.py run --module
pandas_ta.performance.ytd_ret` over the 89 BIST frames, 687 comparators, canary bit-equal:

| column | max \|ρ\| | against | set | n | per-frame max median | verdict |
|---|---|---|---|---|---|---|
| `YTD_RET` | 0.7614 | `Dist_to_SMA_200_pct` | manifest | 381,138 | 0.7654 | DISCLOSE |

Against `compute_all` the top is 0.6807 vs `EMA_ALIGN_BULL`. The band is DISCLOSE
(0.76 ≤ ρ < 0.80, `CLAUDE.md` Gate E row): the column ships, with this overlap disclosed. A
year-to-date return largely tracks how far price sits from its 200-day mean, about a year of
bars. The figures equal the issue's prototype (0.7614 vs `Dist_to_SMA_200_pct`, per-frame
0.7654). Only n differs: 381,138 here vs 381,008 there, so the port scores 130 more bars than
the prototype did. Gate C's real-data limb is this run's n.

**Fork overlap.** The issue's stage-2 screen on the *prototype* (12 real frames, scale-free
`Category` outputs at defaults): max |ρ| 0.7678 vs `ma_disparity:MADISPSQ_200_SMA`, per-frame max
median 0.7670, below the 0.90 restatement line. Gate E compares against the engine only, so this
fork's columns are **still not measured against the port on real data**.

*Synthetic only* (the `overlap` lines of `python -m docs.measure_ytd_ret`): the pre-port
equivalence screen, 12 synthetic 1,500-bar business-day frames from 2015-01-01, tick-rounded to
0.1, Spearman per frame, median of |ρ|: `ma_disparity` `MADISP_200_SMA` (and `MADISPSQ_200_SMA`,
same ranks) 0.7853 (range 0.6235–0.8582), `percent_return` length 126 0.7376, 189 0.7039,
252 0.6852, 63 0.6420, `mtd_ret` 0.3391. That screen's cutoff for "already shipped" was a
per-frame median |ρ| ≥ 0.85 against one column. The cutoff came from the screening task's own
rule, not a CLAUDE.md band. No column reached it, nor the 0.90 line.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass, against the issue's quotation | value = (close / yearOpen − 1) × 100, as a fraction per the issue, not rounded. Hand-derived 5-bar frame across a month change inside 2023 and the 2024/2025 year changes reads 0.10, −0.10, 0.10, −0.50, 0.50 (the anchor does not reset at a month). An independent per-bar loop matches exactly on all 900 bars |
| B Causality | pass | Rewriting all bars from `j` onward, all 899 offsets of a 900-bar walk over 4 calendar years (2022–2025): real module **0 of 899** leak. Two mutants, `exec`'d in memory, each differing from the real module. `s.iloc[0]` → `s.iloc[-1]` (each year anchored on its last open) leaks at **896 of 899**; the other 3 offsets are years' first bars. `s.iloc[0]` → `s.iloc[min(1, len(s) - 1)]` (one bar late) leaks at **4 of 899**, exactly the years' second bars (2022's at `j = 1` included), which is why the sweep takes every offset. Unsorted frames are refused (return `None`) |
| C Reachability | synthetic; real data: Gate E scored 381,138 bars | 900-bar walk: 900 non-NaN, 279 above the year's first open, 621 below, 900 distinct, range [−0.281170, 0.332203], median −0.037828 |
| D Scale-free | pass | ×8/×64 bit-identical, max\|diff\| 0.0. ×10/×3.7 max\|diff\| 2.22e-16 against a 1e-9 tolerance. Same frame with 2023's first open blanked, so 260 of 900 bars are NaN; masks match at all four. `0 < 279 < 900` on the unblanked frame |
| E Attribution | **owed** | see above |
| F Suites | this repo, targeted | `GATE_E_PENDING_OK=1` (set in this session's environment) `python -m pytest -q -p no:cacheprovider -W ignore tests/test_ytd_ret.py tests/test_altport2_ports.py tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py tests/test_readme_counts.py tests/test_wiring_accessors.py`: 1246 passed, 8 skipped. The skips include the "Gate E owed" skip for `ytd_ret`. Without the variable, that test fails until the owner records the row, as designed. Full suite and the parent repo not run in this session |

## Choices a reader should check

* **A frame starting mid-year** anchors its first partial year on its first bar's open, so those
  bars are a return since the frame started, not a year-to-date return. For a short frame that is
  most of the data.
* **A missing or zero first open blanks that whole year**, up to ~260 daily bars. `transform("first")`
  would read a later bar's open (look-ahead); a zero gives `inf`.
* **An unusable index returns `None`** (not a `DatetimeIndex`, not ascending, NaT, or open/close
  indexes differ), so a `df.ta.strategy()` sweep skips the column instead of aborting.
* **Calendar years of the index as written**; a tz-aware index resets on local time.
* **Year only**, as `mtd_ret` is month only: no period parameter (#205 asks for the quarter form).

## Wiring

`Category` **361 → 362** (`performance` **6 → 7**); accessors **369 → 370**. Touch points:
`pandas_ta/performance/ytd_ret.py`, `pandas_ta/performance/__init__.py`, `pandas_ta/__init__.py`
→ `Category["performance"]`, `pandas_ta/core.py` → `AnalysisIndicators.ytd_ret`,
`tests/test_ytd_ret.py`. Also updated: `README.md` counts and row, `docs/IndicatorDictionary.md`
(regenerated, `YTD_RET` tagged `SF`), `docs/MLCompanionContract.md` (707 tagged columns, 343 `SF`),
and `CATEGORY_TOTAL` in `tests/test_altport2_ports.py`.
