# PINEBI-1c — the nine TradingView `ta` alternates, measured

Source for all nine: `docs/pine/RA2vGpkA-ta.pine` (untracked, see `CLAUDE.md`) —
the TradingView/`ta` Pine v5 library, **MPL-2.0, © TradingView**.

Every one of the nine restates an indicator this fork already ships, so Gate E
reads ρ ≈ 1.0 against the sibling and the standing `ρ ≥ 0.9 → revert` rule would
delete all nine on sight. PINEBI-1c suspends that rule and substitutes a
two-axis acceptance test:

| axis | question | how it was established |
|---|---|---|
| **warm-up saved** | how many bars earlier does the alternate become usable? | sibling's first-stable index minus the alternate's, on a shared fixture |
| **parameter reach** | is there a parameter the sibling genuinely cannot express? | by **calling** the sibling with it and recording the result, never by reading its signature |

An alternate that saves **no** warm-up **and** reaches **no** new parameter is
deleted. Two of the nine were.

## Fixtures

* **GRID_S** — a 400-bar seeded geometric random walk (`default_rng(1729)`,
  σ = 0.01 per bar) with a symmetric high/low spread. Defined identically in
  `tests/test_pinebi_1c_alternates.py::grid_s` and in the measurement script, so
  the numbers in the tests and the numbers here are the same measurement.
* **GRID_A** — the first 40 `BIST_100` tickers with a cached
  `Backtesting/datastore/cache/<t>_1d.parquet` of ≥ 400 rows. Median overlap
  n ≈ 5,686 bars per ticker.

Measurement script: `Backtesting/scripts/analysis/measure_pine_alternates.py`
(writes `backtest_results/tvpta6/pine_alternates_warmup_rho.csv` and
`pine_alternates_param_reach.csv`).

**Warm-up is measured as FIRST-STABLE — the index after the LAST NaN — not as
first-valid-index.** `pandas_ta.supertrend` pre-fills its `trend` list with `0`
and its loop starts at `i = 1`, so index 0 holds a spurious finite `0.0`
followed by 7 NaNs. Under first-finite that scores the sibling at 0 and reports
`supertrend2` saving nothing; it saves 7.

ρ is Spearman over the bars where **both** series are finite, so the warm-up
difference itself neither inflates nor deflates it.

## The table

| candidate | sibling | warm-up saved (GRID_S) | warm-up saved (GRID_A, 40 tickers) | parameter reach | ρ vs sibling (GRID_S) | ρ vs sibling (GRID_A min–max) | verdict |
|---|---|---|---|---|---|---|---|
| `ema2` | `ema(10)` | **9** (9 → 0) | 9 on every ticker | per-bar `Series` length; fractional scalar | 0.999989 | 0.999784 – 1.000000 | **KEEP** as `ema2` |
| `rma2` | `wilder_rma(10)` | **9** (9 → 0) | 9 on every ticker | per-bar `Series` length; fractional scalar | 0.999996 | 0.998081 – 1.000000 | **KEEP** as `rma2` |
| `rma2` | `rma(10)` *(the wrong sibling, recorded)* | 9 (9 → 0) | 9 on every ticker | — | 0.999792 | 0.995790 – 1.000000 | — |
| `dema2` | `dema(10)` | **9** (9 → 0) | 9 on every ticker | per-bar `Series` length | 0.999966 | 0.997969 – 1.000000 | **KEEP** as `dema2` |
| `tema2` | `tema(10)` | **9** (9 → 0) | 9 on every ticker | per-bar `Series` length | 0.999940 | 0.998169 – 1.000000 | **KEEP** as `tema2` |
| `t3Alt` | `t3(10, 0.7)` | **9** (9 → 0) | 9 on every ticker | per-bar `Series` length; **volume factor ≥ 1**, which `t3` silently clamps | 0.999983 | 0.997013 – 1.000000 | **KEEP** as `t3_tv` |
| `atr2` | `atr(14)` | **14** (14 → 0) | 14 on every ticker | per-bar `Series` length; fractional scalar | 0.970769 | 0.996317 – 1.000000 | **KEEP** as `atr2` |
| `supertrend2` | `supertrend(7, 3.0)` | **7** (7 → 0) | 7 on every ticker | per-bar `Series` ATR length; **per-bar `Series` factor** (L602 declares both); **`wicks`**, which `supertrend` swallows into `**kwargs` | 0.992770 | 0.790134 – 0.999999 | **KEEP** as `supertrend2` |
| `stochFull` | `stoch(k=14, d=3, smooth_k=3)` | **0** | 0 (see note) | **none** — reproduced bit for bit | 1.000000, max\|diff\| = 0.0 | 1.000000 on all 40 | **DELETE** |
| `stochRsi` | `stochrsi(14, 14, 3, 3)` | **0** | 0 on every ticker | **none** — reproduced bit for bit | 1.000000, max\|diff\| = 0.0 | 1.000000 on all 40 | **DELETE** |

## Why the two deletions

The task text expected `stochFull` to reach "a separate %K smoothing" the
sibling cannot express. **That expectation is wrong, and the measurement is what
caught it.** `pandas_ta.stoch` has carried `smooth_k` separately from `d` all
along; the mapping is exact:

```
Pine  stochFull(periodK, smoothK, periodD)
fork  stoch(k=periodK, d=periodD, smooth_k=smoothK)

Pine  stochRsi(lengthRsi, periodK, smoothK, periodD)
fork  stochrsi(length=periodK, rsi_length=lengthRsi, k=smoothK, d=periodD)
```

Measured at the *non-default* parameters where the two smoothing lengths differ
(`stoch(k=14, d=3, smooth_k=5)` vs `stochFull(14, 5, 3)`, and
`stochrsi(length=21, rsi_length=14, k=5, d=3)` vs `stochRsi(14, 21, 5, 3)`):
**max\|diff\| = 0.0** on GRID_S, ρ = 1.0 on all 40 GRID_A tickers. Neither
alternate is a smoothing that already ships, so neither ships.

*Note on GRID_A's `stochFull` row:* the raw Pine port is *worse* than the
sibling on **two of the 40 tickers** — `ENKAI.IS` at −1087 and `EREGL.IS` at
−1064, each appearing twice in the CSV because %K and %D are scored separately
(four negative rows in all). Cause, measured: `ENKAI.IS` has exactly one flat
14-bar window in 5,717 bars, where `highest − lowest = 0`. The Pine expression
divides by it and yields NaN; `pandas_ta.stoch` routes the denominator through
`non_zero_range` and stays finite. The sibling is a strict superset — one more
reason to delete rather than ship.

*Scope of "bit for bit":* exact on **GRID_S** — max|diff| is literally 0.0 for
all four columns, and reproduced by the reviewer at (14,5,3), (21,7,4) and
(14,21,5,3). On **GRID_A** it holds exactly for `stochRsi` (max|diff| 0.0 on all
40 tickers) but not quite for `stochFull`, where the CSV records max|diff|
**2.586e-12** (%K) and **2.416e-12** (%D) — float summation order in a
5,700-bar rolling window, ~10 orders of magnitude below a price tick, not a
behavioural difference. Round 1 of this document said "bit for bit" unqualified
and the delivered CSV contradicted it.

## What each survivor's parameter reach actually looks like when you call the sibling

| probe | result |
|---|---|
| `ema` / `wilder_rma` / `dema` / `tema` / `t3` / `atr` / `supertrend` with a per-bar `Series` length | `ValueError: The truth value of a Series is ambiguous` — every one of them does `length = int(length) if length and length > 0`, which evaluates the Series in a boolean context |
| `ema(length=12.5)` | truncated to `int(12.5) == 12`, numerically identical to `length=12` |
| `atr(length=12.5)` | truncated to `int(12.5) == 12` |
| `t3(a=1.5)` | returns a column **named `T3_10_0.7`**, numerically identical to `a=0.7`. The `a > 0 and a < 1` clamp is silent and the name does not admit it |
| `supertrend(wicks=True)` | `wicks` falls into `**kwargs`, is never read, and the returned frame is identical to the default |
| `supertrend(multiplier=Series)` | `ValueError: The truth value of a Series is ambiguous` — Pine's L602 `factor` is `series float` and the sibling cannot take it either |

## Two arithmetic guesses that were wrong before they were measured

1. **Chaining EMAs does not multiply the warm-up.** `dema`/`tema`/`t3` stack
   2/3/6 SMA-seeded `ema` calls; the natural guess is 18/27/54 bars at
   `length=10`. Measured: **all three settle at 9.** The nested `ema` re-seeds
   with `mean(inner[0:length])` over a window holding exactly one finite value,
   so it re-publishes the inner series' own first value at the same index.
2. **`supertrend`'s first-valid-index is 0 and means nothing** (see the
   first-stable note above).

Both are now pinned by
`tests/test_pinebi_1c_alternates.py::test_chaining_emas_does_not_multiply_the_warm_up`
and `::test_first_finite_would_have_scored_supertrend_wrong`.

## Two things about the survivors that will mislead a reader who assumes

* **`rma2`'s sibling is `wilder_rma`, not `rma`.** `pandas_ta.rma` is
  `ewm(alpha=1/length, adjust=True)` — a renormalised weighted mean of the
  window, not Wilder's recursion. Pine's `ta.rma` **is** Wilder's. Measured at
  `length=10` on GRID_S, `rma2` sits 6.6× closer to `wilder_rma`
  (max\|diff\| 0.0711) than to `rma` (0.4667).
* **`SUPERT2d_*` uses Pine's sign: `-1` is an UPTREND.** This is now the FIRST
  sentence of `supertrend2.__doc__`, because `docs/IndicatorDictionary.md`
  truncates the description at 150 characters and round 1 buried the sign note
  below the cut — invisible in the very file `CLAUDE.md` tells a reader to
  consult before judging a column. `docs/MLCompanionContract.md` carries it too.
   `pandas_ta.supertrend`
  uses the opposite. Measured on GRID_S, `SUPERT2d == -SUPERTd` on **96.75%** of
  400 bars — not 100%, because the two also differ on the band ratchet (Pine
  re-arms on `price[1]` breaking the *previous* band; `supertrend` on `close[i]`
  breaking `band[i-1]`). That residual is also why GRID_A's ρ floor for
  `supertrend2` is 0.790 rather than ~1.0: on some tickers this is a materially
  different line, not a restatement.

## What the saved warm-up is worth to the consumer today: measured, and it is zero rows

The warm-up numbers above are the acceptance criterion and they are real. What
they are *worth* is a separate question. Round 1 asserted the answer with no
measurement; round 2 measured it under a broken config and quoted six numbers
with no artefact behind them. This is the third version and it is generated:
`run_materiality()` in `measure_pine_alternates.py` writes
`backtest_results/tvpta6/pine_alternates_warmup_materiality.csv`, one row per
ticker, and every figure below is read out of it.

**Config, stated because it changes the answer:**
`IndicatorEngine(include_advanced=False).compute_all` on the cached
`datastore/cache/<ticker>_1d.parquet`, **index left alone** (`DatetimeIndex`),
365 numeric columns, warm-up measured as the *position* of each column's first
non-NaN (not the index label — with a `DatetimeIndex` that is a Timestamp).

| ticker | bars | date range | median | p90 | max | slowest column | max excl. calendar |
|---|---|---|---|---|---|---|---|
| `ACSEL.IS` | 753 | 2023-08-28 → 2026-08-26 | 9 | 88 | **499** | `HARPARK_1_5_22_500` | 499 (same) |
| `AKBNK.IS` | 5,748 | 2004-03-30 → 2026-08-27 | 13 | 123 | **2,779** | `tom_pos` | 623 (`MADIV_BEAR_AREA_R_20_60_120`) |

A usable **row** is gated by the slowest column, not the fastest. AKBNK's
ceiling is a **calendar** feature — `tom_pos`, with `sessions_to_holiday`,
`sessions_from_holiday`, `ramazan_day` and `days_to_bayram` beside it — not an
indicator; strip those five and the ceiling is still 623. Either way it is
hundreds to thousands of bars against 9. Shaving 9 (or 14) bars off one column
moves the frame's usable start by **zero rows**.

*What went wrong in round 2, recorded because it is the more instructive
failure:* that run called `.reset_index(drop=True)` before `compute_all`. That
turns the parquet's `DatetimeIndex` into a `RangeIndex` and silently drops the
17 calendar/period-dependent columns that need `.to_period()` — 348 numeric
columns instead of 365 — which moved every quantile and hid the true ceiling.
Five of its six figures did not reproduce. The conclusion was never in doubt
(the real ceiling is *worse*), but a conclusion is not its receipt.

## What actually shipped, stated plainly

Worth writing down rather than leaving a reader to infer:

* **Six of the seven survive on parameter reach alone.** The warm-up axis is
  measured and real per column, and worth zero usable rows to the only
  consumer that exists (above). `supertrend2` is the exception with an
  independent case — its GRID_A ρ floor of 0.790 means it is a materially
  different line on some tickers, not a restatement.
* **All seven are `PX`.** None clears Gate D of the ML feature contract.
* **There are zero call sites in either repo.** Verified by grepping
  `(ema2|rma2|dema2|tema2|t3_tv|supertrend2|atr2)\s*\(` across
  `pandas_ta/`, `backtesting_engine/`, `scripts/` and `runners/`: the only
  matches outside the seven modules themselves are the seven `core.py`
  accessors — the wiring, not a consumer. Nothing in the parent engine calls
  them; the four loose `../Backtesting` hits are `ema26` / `ema20`
  substrings.

So what shipped is **a capability with no customer**: reachable through
`ta.<name>()`, `df.ta.<name>()` and `df.ta.strategy()`, exercised only by
tests. That is defensible under PINEBI-1c's stated acceptance test — warm-up
saved and parameter reach, both measured — and it is not the same thing as a
feature anyone is using. Whoever picks up per-bar-length work (`frama` and the
adaptive filters in the same Pine library are the obvious first callers) is the
customer this was built for.

## Gate D: stated, not passed

All seven survivors are **price-scale** columns — six moving averages, an ATR
and a SuperTrend line — exactly like the siblings they extend, and the generated
`docs/IndicatorDictionary.md` marks every one of them `PX`. They **do not**
clear Gate D of the ML feature contract and are not offered as scale-free
features. They ship on the same footing as `EMA_10` and `ATRr_14`: raw material
for ratios and distances, not features to hand a tree directly. Under a ×8
price scaling every one of them scales by exactly 8 (bit-identical in float64),
which is the property a tree cannot use, and
`test_the_survivors_are_price_scale_like_their_siblings` asserts it rather than
leaving it implicit.

## The same standard, applied to these seven (round 2)

Round 1 indicted `t3` for silently clamping a parameter and naming the column
for a value the call did not use — and then did the same thing itself. Fixed,
and pinned by `tests/test_pinebi_1c_alternates.py`:

| defect (round 1) | now |
|---|---|
| `ema2(close, -5)` returned `EMA2_10`, bit-identical to `length=10`, while `ema2(close, Series(-5))` clamped to 1 — **one argument, two answers**, and neither matched the cited L159 `math.max(1.0, length)` | both paths apply Pine's clamp; `EMA2_1`, and the name carries the **effective** value |
| `t3_tv(vf=0.0)` → `T3tv_10_0.7`; `supertrend2(multiplier=0.0)` → `SUPERT2_7_3.0` | L661 and L602 put **no** bound on `vf`/`factor`, so neither does this port: `T3tv_10_0.0`, `SUPERT2_7_0.0`. `vf=0` is asserted to equal the plain triple-EMA chain |
| `supertrend2(..., multiplier=Series)` raised `ValueError: The truth value of a Series is ambiguous` — from `float(multiplier) if multiplier and multiplier > 0`, **the exact idiom this document records as the sibling's failure**. L602 declares BOTH `factor` and `atrLength` `series float`; only one was ported | the factor is normalised the same way as the length; `SUPERT2_7_dyn2.0-4.0-882ee074`. `supertrend2`'s parameter reach is therefore **three**, not two |
| two different per-bar lengths both produced `EMA2_dyn`, so `append=True` silently overwrote the first — in the one call shape the module was kept for | the token is `dyn<min>-<max>-<8 hex>`, a `blake2b` digest of the float64 buffer (deterministic across processes, unlike Python's salted `hash()`); 4 bytes rather than 2 because a 16-bit digest collides at ~300 Series by the birthday bound, and a collision here IS the silent overwrite |

## Column names shipped

`EMA2_10` · `RMA2_10` · `DEMA2_10` · `TEMA2_10` · `T3tv_10_0.7` · `ATR2_14` ·
`SUPERT2_7_3.0` / `SUPERT2d_7_3.0` / `SUPERT2l_7_3.0` / `SUPERT2s_7_3.0`

A per-bar parameter has no single number to encode, so it names the column
`dyn<min>-<max>-<8 hex digest>` — `EMA2_dyn5-30-7c148edc`,
`T3tv_dyn5-30-7c148edc_0.7`, `SUPERT2_dyn5-30-7c148edc_3.0`, and for a per-bar
factor `SUPERT2_7_dyn2.0-4.0-882ee074`.
`supertrend2(wicks=True)` appends `w` (`SUPERT2_7_3.0w`). None of these collides with a shipped column —
asserted by `test_the_survivor_column_names_collide_with_nothing_shipped`, and
in particular `ATR2_14` collides with none of `atr`'s `mamode[0]`-derived names
(`ATRr_14`, `ATRe_14`, `ATRs_14`, `ATRw_14`, `ATRwr_14`, `ATRt_14`).

`Category` gains **+7** from this scope: +6 overlap (`ema2`, `rma2`, `dema2`,
`tema2`, `t3_tv`, `supertrend2`) and +1 volatility (`atr2`). The absolute
counts in `README.md` / `CLAUDE.md` are deliberately not restated here —
TALIB-1 and CANDLE-1 are adding indicators concurrently and the coordinator
reconciles the totals once, at the end.
