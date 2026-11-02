# mtd_ret — measured (issue #206)

> **Status: Gates A, B, D cleared. Gate C synthetic only. Gate E OWED, verdict pending. Gate F
> this repo only.** The Backtesting repo and the BIST cache were not available in this session,
> so nothing here is a real-data measurement of the port.

Month-to-date return from the month's first open, as a fraction. Module
`pandas_ta/performance/mtd_ret.py`, column `MTD_RET`. Tests: `tests/test_mtd_ret.py` (16).
Numbers: `python -m docs.measure_mtd_ret`. Environment: CI's pins (Python 3.11, pandas 2.3.3,
numpy 1.26.4). Measured 2026-11-02.

Source is Reddit, tier 4: r/thinkorswim 1opks13 (2025-11-06). Existence, not evidence: nothing
here tests the poster's claimed use, a watchlist column showing the gain since the period start.

## Gate E: the prototype's numbers, not this port's

The issue's screen, `screen_r9_20261029`, measured the prototype `b3_mtd_ret`: max |ρ| 0.7997 vs
`bias` (n = 397,156), top-5 per-frame max median 0.8029, verdict DISCLOSE. Its fork overlap was
0.8411 vs `pivot:PIVOT_PP_DIST_PCT`. The prototype sits in `docs/issues/screen/`, which is not on
this machine, so the port has not been compared with it. Do not read those figures as this
column's result.

Owed, from `../Backtesting/Backtesting`:

    python scripts/analysis/gate_e_overlap.py run --module pandas_ta.performance.mtd_ret --name mtd_ret
    python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD

The prototype's 0.7997 sits 0.0003 under the 0.80 line, where DISCLOSE becomes DISCLOSE_GAP. If
the port lands on the other side, that changes the disclosure band, not whether it ships.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass, against the issue's restatement | The thread itself returned Reddit's "Blocked" page, so the formula is the issue's: at the first bar of a new period store its open, value = (close / period_open − 1) × 100, as a fraction per the issue. Hand-derived 5-bar frame across a month and year boundary reads 0.10, −0.10, 0.10, −0.50, 0.50. An independent per-bar loop matches exactly on all 900 bars |
| B Causality | pass | Rewriting all bars from `j` onward, 30 offsets: real module **0 of 30** leak. Mutant (`s.iloc[0]` → `s.iloc[-1]`, each month anchored on its last open, `exec`'d in memory) differs from the real module and leaks at **26 of 30**. The other 4 offsets are months' first bars, where no partial month sits behind the cut |
| C Reachability | synthetic only | 900-bar walk, 42 months: 900 non-NaN, 424 above the month's first open, 476 below, 900 distinct, range [−0.132356, 0.268591], median −0.003668. Real-data counts come with the Gate E run |
| D Scale-free | pass | ×8/×64 bit-identical, max\|diff\| 0.0. ×10/×3.7 max\|diff\| 2.22e-16 against a 1e-9 tolerance. NaN masks match at all four. `0 < 424 < 900` |
| E Attribution | **OWED** | See above |
| F Suites | this repo only | With `GATE_E_PENDING_OK=1` and CI's two deselected tests: 4195 passed, 86 skipped, 0 failed; one of the skips is `mtd_ret`'s owed row. Without the variable, `test_every_indicator_that_needs_a_row_has_one` fails until the row is recorded, as designed. The parent repo's suite was not run |

## Choices a reader should check

* **A frame starting mid-month** anchors its first partial month on its first bar's open, so those
  bars are a return since the frame started, not a month-to-date return. The frame cannot tell a
  truncated month from one whose first session is simply late. The alternative, blanking the
  first month, would also blank complete ones.
* **A missing first open blanks that month.** `transform("first")` would skip the NaN and read a
  later bar's open, a look-ahead that a sweep on clean opens cannot see. Pinned by
  `test_missing_first_open_blanks_the_month_and_not_the_next`.
* **Without a `DatetimeIndex` the function returns `None`**, and the accessor leaves the frame
  unchanged, so a strategy sweep on a `RangeIndex` frame skips the column rather than crashing.
* **Months are calendar months of the index as written.** A tz-aware index resets on local time.
* **Month only.** The source's formula takes any period and #205 asks for the quarter form, but
  that issue is still open and its numbers are its own, so no period parameter was added here.

## Wiring

`Category` **273 → 274** (`performance` **5 → 6**); accessors **281 → 282**. Touch points:
`pandas_ta/performance/mtd_ret.py`, `pandas_ta/performance/__init__.py`, `pandas_ta/__init__.py`
→ `Category["performance"]`, `pandas_ta/core.py` → `AnalysisIndicators.mtd_ret`,
`tests/test_mtd_ret.py`. Also updated: `README.md` counts and row, `docs/IndicatorDictionary.md`
(regenerated, `MTD_RET` tagged `SF`), `docs/MLCompanionContract.md` (620 tagged columns, 264 `SF`),
and `CATEGORY_TOTAL` in `tests/test_altport2_ports.py`.
