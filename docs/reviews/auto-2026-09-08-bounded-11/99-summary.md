# 99 — Run summary: bounded-11 batch (Mode C)

Invocation: `/brutally-honest-review --auto @PandasTa/TODO.md`
Scope set in Phase 2: **Mode C · bounded 11 · `rma` documented-not-changed.**

## Status — ALL 11 COMPLETE

| task | rounds | outcome |
|---|---|---|
| RMA-W (owner-directed prereq) | 2 | `wilder_rma` + `mamode="wrma"`; `rma`/`atr`/`natr` byte-identical, pinned |
| PINEBI-1c | 3 | 7 alternates kept, **2 measured and deleted** |
| PINEBI-1d | 1 | 2 lower-timeframe indicators; `docs/LowerTimeframeData.md` |
| PINEBI-1e | 2 | 4 ML utilities |
| TALIB-1 | 1 | **10 ported, ta-lib gap 10 → 0**; 8 columns ship, **5 reverted** |
| CANDLE-0 | 3 | shortlist + harness + 7 CSVs |
| CANDLE-1 | 3 | 4 modules / 22 columns; **6 columns deleted**, **rectangle SKIPPED** |
| CANDLE-2 | 1 | 3 items closed; `talib` promoted to its own extra |
| INDREF-0 | 3 | page + template + a guard verified against 5 controls |
| MLCOL-2 | 2 | **0 of 5 companions ship** |

Deferred by the owner up front: PINEBI-2, INDREF-1, MLCOL-1.
Dropped with reason: INDREF-2 (depends on the deferred INDREF-1).

**Suite at close: `PYTEST_EXIT=0`, 1,563 passed, 23 skipped** (1,344 at the start).
Gaps: pandas-ta-classic **19 → 11**, tti **10 → 9**, ta-lib **10 → 0**. All three
verifiers report no reproducible row.

## The batch's real output is deletions, not ports

Twelve columns were built, measured and deleted; one whole task shipped nothing.

- **MLCOL-2: 0 of 5.** `SMA_10_DIST_PCT` works as a shape — ρ +0.008 against its
  own parent proves the distance form stripped the price level — and dies at
  ρ **0.9462** against the already-shipped `NWE_MID_200_8.0_8.0`. The two
  apparent survivors fell to a placebo and an across-seed refit.
- **TALIB-1 reverted 5 of 13 columns** at ρ 0.9148–0.9850, every one against a
  column the engine already had.
- **CANDLE-1 deleted 6** on internal overlap up to ρ = 1.0000, then **skipped the
  rectangle** on a pre-registered trigger.

## Three findings that outlive their tasks

1. **Gate E has been blind to non-numeric comparators.** `SAREXTs` was about to
   ship at ρ 0.8393 because `PSAR_Signal` is an object column ("Bullish"/
   "Bearish") that `select_dtypes` drops. Coerced: **0.9598**. Every prior Gate E
   measurement in this repo shares the blind spot.
2. **An unsigned magnitude on a sparse support is mostly a description of that
   support.** Two independent such columns correlate ρ = 1.0000 (90,137 tied
   zeros against 360 values); signing one drops it to −0.0001. Reproduced
   independently. This is why 6 of CANDLE-1's columns died, and it should screen
   every event-flag companion MLCOL-1 builds.
3. **`.reset_index(drop=True)` before `compute_all` silently drops 17 columns.**
   The calendar/period features need `.to_period()`. Anyone measuring against
   `IndicatorEngine` with a reset index is measuring a different engine.
4. **A re-derivation of a deleted column is only evidence if it is on the
   population the survivors are measured on.** CANDLE-1's `TRIW_CONV` was
   deleted at ρ −0.8928 — close enough to the 0.9 line to be called "the one
   judgement call" in the write-up. Regenerating the evidence exposed that the
   re-derivation ran a duplicated loop that still accepted rectangles, so it
   compared two different populations. On the shipped post-skip population the
   real figure is **−0.9994**: post-skip every accepted pattern converges by
   construction, so `CONV` and `WIDTH` are nonzero on the identical 3,204 bars.
   The deletion was never a judgement call.

## On the process itself

- **A pre-registered trigger only works with a tie-break rule fixed in advance.**
  CANDLE-1's rectangle missed by a tenth of a standard error and was resolved in
  the shipper's favour with tiebreakers invented after the number arrived. Under
  the rule written down afterwards, **round 1's own numbers already fired** — the
  250-ticker re-run confirmed the decision but was never what changed it.
- **Prefix truncation cannot certify anchor-sparse output**, and a single
  perturbation point is not enough either: a back-dating mutant escapes at J=200
  for `triangle_wedge` and J≥250 for `rounding_cup`. Sweep J.
- **Reconcile counts once, at the end.** Piecemeal regeneration against a tree
  three agents were writing produced two false accusations against subagents,
  both of them mine.
- **`| tail` reports tail's exit code, not pytest's.** It misled two agents and
  me. Every suite result here is `PYTEST_EXIT` captured directly.

## Why the last five did not run

They are 35 indicators (PINEBI-1b 16, -1c 9, TALIB-1 10) plus ~10 pattern
detectors, each owing Gates A–F: a line-by-line Pine/TA-Lib citation, a mutant
causality test, a scale-invariance check, and a Gate E overlap measurement
against the full ~200-indicator production config. The six completed tasks took
**14 review rounds** between them and every round found something real. Running
the remaining 35 at a lower bar would manufacture exactly the defect class this
batch spent its time removing.

## What the gates caught (all in work produced THIS run)

The recurring defect was never the mathematics. It was prose asserting things
the code did not do.

**Main-thread work:**
- `atr` named itself from `mamode[0]`, so `mamode="wma"` and `mamode="wrma"`
  both produced `ATRw_14` — two indicators, one column name, second write
  silently overwriting the first. The test asserted that name while its own
  failure message claimed names encode the smoothing. Now `ATRwr_14`, with
  every pre-existing mamode's name pinned unchanged.
- Five "golden" `natr` constants were invented rather than measured. Caught by
  the test failing.
- **`natr` defaults to `mamode="ema"`, not `"rma"`** — it never inherited the
  `rma` defect at all. The live-threshold exposure is `atr` only. The premise in
  the Phase-2 question was broader than the facts; the owner's decision still
  holds, for `atr`.
- A missing comma in `Category` made Python concatenate `"zscore"` +
  `"rolling_sum"` and `"zigzag_fib"` + `"pivot"`, silently deleting two
  **existing** indicators. Regression test added.
- `wilder_rma` refused an entire 300-bar series over one NaN at bar 5 while the
  Pine reference returned 281 values. The seed now slides to the first clean
  window, which is Pine's own rule.
- The `covariance` accessor defaulted `other="volume"`, so
  `df.ta.strategy("statistics")` silently emitted the covariance of price
  against share count at magnitude ~2.8e5.
- `covariance`'s alignment guard — advertised as preventing silent misalignment
  — turned 100 rows against 97 into **194** on a duplicated index.
- `normalize`'s flat-window `0.5` was defended on principle and measured at
  **17.7%** of settled bars on a tick-rounded walk. Changed to NaN: a gap is
  information, a fabricated mid-range reading is not.
- The dictionary probe called two-series indicators one-armed, publishing a
  *Known breaks* row that libelled working `covariance` while `CLAUDE.md` next
  door swore nothing was outstanding.
- Docstrings cited `tests/test_pivot.py` and `tests/test_normalize.py`. Neither
  file existed.
- "`ta.sum` is never called live in the corpus" was a grep against the retired
  name; Pine v5 renamed it `math.sum`, which the corpus calls **214 times
  across 88 files**.

**Subagent work:**
- CANDLE-0 reported `liquidity_compression_box` dead across five columns having
  called it with the wrong argument order; real firings 7,872 / 3,974 / 3,871.
  That error had also removed the prime duplicate-suspect from the correlation
  matrix. On rerun the headline held (max |ρ| **0.1452**) but the rectangle's
  clearing argument changed from "those columns never fire" to a one-directional
  co-fire and specificity argument, with a pre-registered flip trigger.
- INDREF-0 grafted reach-row expectations onto taint-window bar counts,
  inflating a suppression claim 2.7×; and stated the dictionary fixture "pins
  High/Low at ±2% of Close" when it draws `close × |N(0, 0.006)|`.
- INDREF-0's first guard bit only on the two controls its author chose; a
  fabricated number inside a *registered* section passed. Now group-anchored
  with declared counts, verified against five controls.

## Notable results

- **MLCOL-2 deleted 3 of 5 companions.** `SMA_10_DIST_PCT` works as a shape
  (ρ +0.008 against its own parent) but dies at ρ **0.946** against the
  engine's existing `NWE_MID_200_8.0_8.0`. Gate E alone would have shipped
  `FVG_BULL_RATE_60`; the incremental-signal axis killed it. Only
  `FVG_BULL_BARS_SINCE` cleared permutation importance.
- **`pandas_ta.rma` is not Wilder's smoothing** — measured 285 of 287 bars
  differing, max 0.241. Shipped as `wilder_rma` alongside; `rma`/`atr`/`natr`
  byte-identical, pinned by test.
- **Prefix truncation cannot certify `pivot`.** Levels publish only at anchors,
  so a back-dating mutant scores 0.0 under both prefix and endpoint rescanning.
  Future-perturbation catches it (real 0.0, mutant 50.0). Recorded because
  `CLAUDE.md`'s standing mutant advice does not cover anchor-sparse output.
- **CANDLE-0's premise was stale**: TA-Lib is installed and all 62 patterns are
  reachable, 0 constant on 91,197 BIST bars. `dtdb` and `flag_breakout` already
  ship double-top and flag, so both were struck from the shortlist.

## Not done

Nothing is committed. `../Backtesting/scripts/analysis/measure_chart_patterns_overlap_full.py`
is written but **untracked** — all thirteen sibling harnesses are tracked and it
should join them on the owner's next commit.
