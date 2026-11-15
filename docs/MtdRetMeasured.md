# mtd_ret — measured (issue #206)

> **Status: Gates A, B, D cleared. Gate E measured 2026-11-15: DISCLOSE, 0.7997 vs `bias`**
> (run `gatee7-20261115-mtd_ret`, recorded in `docs/gate_e_ledger.csv`; see "Gate E"). Gate C's
> real-data counts come from the same run. **Gate F this repo only.** The rest of this file was
> written 2026-11-02 without the Backtesting repo or the BIST cache; only the Gate E section and
> the C and E rows of the gate table are real-data measurements of the port.

Month-to-date return from the month's first open, as a fraction. Module
`pandas_ta/performance/mtd_ret.py`, column `MTD_RET`. Tests: `tests/test_mtd_ret.py` (24).
Numbers: `python -m docs.measure_mtd_ret`. Environment: CI's pins (Python 3.11, pandas 2.3.3,
numpy 1.26.4). Measured 2026-11-02.

Source is Reddit, tier 4: r/thinkorswim 1opks13 (2025-11-06). Existence, not evidence: nothing
here tests the poster's claimed use, a watchlist column showing the gain since the period start.

## Gate E — measured: DISCLOSE

Run `gatee7-20261115-mtd_ret`, 2026-11-15, on this module as it stands on `dev` at `8000158`,
default parameters (`MTD_RET`). Recorded with
`python docs/gate_e_ledger.py record ... --measured 2026-11-15`.

- Pooled max |ρ| **0.7997** vs `bias` (compute_all), n = 397,158. The manifest's max is
  0.7840, vs `bias_ta` (n = 396,624).
- Top-5 per-frame max median |ρ| **0.8029** vs `bias`, over 89 frames; 0 frames at or above
  0.90.
- 687 comparators (329 compute_all + 358 manifest); none dropped as degenerate. Canary
  bit-equal on AKBNK, BIENY, AGHOL and SASA.
- Next comparators: `ATR_POSITION` 0.7934, `bias_ta` 0.7840, `ZSCORE_20` 0.7760, `BB_%B`
  0.7760.

**Disclosure.** `MTD_RET` overlaps the engine's `bias`: pooled ρ 0.7997; per frame
(`perframe.csv`) median 0.8029, 50 of 89 frames at or above 0.80, range 0.7549–0.8694. The
next comparator, `ATR_POSITION`, reads pooled 0.7934, per-frame median 0.7956, 39 of 89
frames at or above 0.80. Read from the Backtesting source, both place the close against a
recent level: `bias` is `(close - sma20) / sma20` (`indicator_engine.py:988`), and
`ATR_POSITION` is the close's position between `ATR_LOWER` and `ATR_UPPER`
(`ml_features.py:274`). `MTD_RET` places the close against the month's first open.
`bias_ta` (0.7840), `ZSCORE_20` and `BB_%B` (0.7760 each) were not read.

**Band.** Pooled 0.7997 is in DISCLOSE (0.76 ≤ ρ < 0.80), 0.0003 under the 0.80 line where
DISCLOSE_GAP starts, so it ships with the comparator named here and no waiver. The per-frame
0.8029 is above 0.80, but the ladder's per-frame limb only acts at 0.90 (STRUCK), so it does not
move the band (`backtesting_engine/gate_e.py:99-111`, `verdict()`: the per-frame median feeds
only STRUCK; the pooled figure picks DISCLOSE_GAP, DISCLOSE or SHIP). Either way it ships; the
band only changes the disclosure.

Outputs: `MultipleBranchWork/Backtesting-adhoc-gatee-agent/backtest_results/gatee/gatee7-20261115-mtd_ret/`
on the owner's machine; Backtesting `91ab7ae2`, stamp `engine_code` `f58eb5da`,
`pandas_ta_src_sha1` `9293d757`. To re-run, from `../Backtesting/Backtesting`:
`python scripts/analysis/gate_e_overlap.py run --module pandas_ta.performance.mtd_ret --name <run name>`.

**The prototype.** The issue's screen, `screen_r9_20261029`, measured the prototype
`b3_mtd_ret` at 0.7997 vs `bias` (n = 397,156), per-frame 0.8029, DISCLOSE. The port reproduces
both to four decimals over 2 more bars. The screen's fork overlap, 0.8411 vs
`pivot:PIVOT_PP_DIST_PCT`, was measured on the prototype; Gate E compares against the engine
only, so this fork's columns are **still not measured** against the port.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass, against the issue's restatement | The thread itself returned Reddit's "Blocked" page, so the formula is the issue's: at the first bar of a new period store its open, value = (close / period_open − 1) × 100, as a fraction per the issue. Hand-derived 5-bar frame across a month and year boundary reads 0.10, −0.10, 0.10, −0.50, 0.50. An independent per-bar loop matches exactly on all 900 bars |
| B Causality | pass | Rewriting all bars from `j` onward, all 899 offsets: real module **0 of 899** leak. Two mutants, `exec`'d in memory, each differing from the real module. `s.iloc[0]` → `s.iloc[-1]` (each month anchored on its last open) leaks at **858 of 899**; the other 41 offsets are months' first bars, where no partial month sits behind the cut. `s.iloc[0]` → `s.iloc[min(1, len(s) - 1)]` (anchored one bar late) leaks at **42 of 899**, exactly the months' second bars, which is why the sweep takes every offset. Unsorted frames are refused, not swept: see below |
| C Reachability | pass | **Real data** (Gate E run `gatee7-20261115-mtd_ret`, 89 BIST daily frames, flat zero-volume bars dropped by the harness): 398,849 of 398,849 pooled bars non-NaN, 387,805 non-zero, so 11,044 read exactly 0. Synthetic, 900-bar walk, 42 months: 900 non-NaN, 424 above the month's first open, 476 below, 900 distinct, range [−0.132356, 0.268591], median −0.003668 |
| D Scale-free | pass | ×8/×64 bit-identical, max\|diff\| 0.0. ×10/×3.7 max\|diff\| 2.22e-16 against a 1e-9 tolerance. Run on the same frame with February 2022's first open blanked, so 20 of 900 bars are NaN and the masks have something to match; they match at all four. `0 < 424 < 900` on the unblanked frame |
| E Attribution | **DISCLOSE** | 0.7997 vs `bias`, n = 397,158; per-frame 0.8029. See "Gate E" |
| F Suites | this repo only | With `GATE_E_PENDING_OK=1` and CI's two deselected tests: 4203 passed, 86 skipped, 0 failed; one of the skips is `mtd_ret`'s owed row. Without the variable, `test_every_indicator_that_needs_a_row_has_one` failed until the row was recorded (2026-11-15), as designed. The parent repo's suite was not run |

## Choices a reader should check

* **A frame starting mid-month** anchors its first partial month on its first bar's open, so those
  bars are a return since the frame started, not a month-to-date return. The frame cannot tell a
  truncated month from one whose first session is simply late. The alternative, blanking the
  first month, would also blank complete ones.
* **A missing or zero first open blanks that month.** `transform("first")` would skip a NaN and
  read a later bar's open, a look-ahead that a sweep on clean opens cannot see. A zero would give
  `inf`, which `fillna` does not clear. Pinned by
  `test_missing_first_open_blanks_the_month_and_not_the_next` and
  `test_zero_first_open_blanks_the_month_and_not_the_next`.
* **An unusable index returns `None`**: not a `DatetimeIndex`, not ascending (NaT included), or
  different between `open_` and `close`. The accessor then leaves the frame unchanged. Ascending
  matters for causality: the anchor is the month's first row, so on a reversed frame the 02-01 bar
  read the open of 02-02. This returns `None` rather than raising as `avwap_z` does, so one bad
  frame skips the column instead of aborting a `df.ta.strategy()` sweep; the cost is that the
  column goes missing without a message. `test_no_datetime_index_returns_none_and_a_strategy_sweep_skips_it`
  runs a real sweep on a dated and an undated frame.
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
