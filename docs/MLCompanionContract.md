# The ML companion contract (MLCOL-0)

> **Goal (user):** *"We should optimize each indicator for ML. Each indicator
> should show binary fields like cheap, expensive or buy & sell type of things.
> Also it should include percentage based analysis."*

**Decision (user, 2026-09-06): hand-authored per indicator, not a generic
transform layer.** The threshold that means "expensive" is indicator-specific,
and a generic percentile is wrong for a bounded oscillator and meaningless for
an event flag.

This document is the contract. It is designed on three indicators chosen to be
the three *shapes* the fork actually contains, so the remaining rollout is
mechanical rather than a fresh decision each time.

---

## Why three shapes, not 201 decisions

`docs/IndicatorDictionary.md` already classifies every shipped column by its observed ML form.

Measured on the live package (parsed from the dictionary, 546 tagged columns): **137 `PX`** (price-level), **196 `SF`** (scale-free), **100 `BIN`** (binary), 49 `ORD`, 41 `CONST`, 2 `PX2`, 21 `??`. (Was 551 / 200 `SF` / 50 `ORD` before TALIB-1's Gate E reverts deleted `SAREXTd`/`SAREXTs`, `HT_TRENDLINE_DIST` and `MAMAf`/`MAMAd` — five columns that measured 0.9148–0.9850 against `bias`, `QQE_RSIMA`, `dist_to_psar_pct`, `NWE_MID_200_8.0_8.0` and `PSAR_Signal`, all already shipped.) Every figure in this sentence is read out of a `Counter` over the regenerated `docs/IndicatorDictionary.md`, not typed; `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts` re-derives it. (An earlier revision of this paragraph, added on 2026-09-08 to keep that guard green, quoted 530 / 182 `SF` / 91 `BIN` and then narrated CANDLE-1's 22 columns as "8 BIN confirmation flags and `*_PEND`, 4 SF `*_AGE`, 6 event-sparse magnitudes" -- three counts, all three wrong, inside the document whose job is to stop exactly that. The real split, from the Counter: **8 `BIN`** confirmation flags, **3 `ORD`** `*_PEND` counts, **4 `SF`** `*_AGE` columns, **3 `SF`** `TRIW_SLOPE_UP` / `TRIW_SLOPE_DN` / `TRIW_WIDTH`, and **4 `??`** magnitudes -- `HS_TGT_PCT`, `TRPL_TGT_PCT`, `CUP_DEPTH`, `CUP_CURV` -- which the 600-bar synthetic probe frame cannot reach because no pattern confirms on it. Those four are scale-free by construction and bit-identical under x8/x64; they are measured on real data in `docs/CandlePatternsMeasured.md` §2.)

⚠ **`*_PEND` counts were being tagged `BIN`, and one case was NOT CANDLE-1's.** The probe reads observed cardinality, so a net pending-pattern count that happens to take only two values on a 600-bar synthetic frame is indistinguishable from a flag. Measured over 40 BIST daily frames / 71,402 bars, `HS_PEND` spans [-2, +2] (5 distinct) and `DTDB_PEND` -- which shipped long before CANDLE-1 -- spans [-2, +2] as well; both had been tagged `BIN`. `FLAG_PEND` genuinely spans only [-1, +1], so `BIN` is correct for it and a blanket "`*_PEND` is ordinal" rule would have mislabelled it. `gen_indicator_dictionary.py`'s `FORM_OVERRIDES` therefore lists the two measured cases explicitly, with the measurement, rather than pattern-matching the name.

⚠ An earlier draft of this paragraph said 128/172/92/3 and called them measured. They were not; `tests/test_ml_companions.py` now parses the dictionary and asserts these.

Those forms, not the indicator names, decide what a companion must do:

| shape | reference | what is wrong with the parent column | what the companion must supply |
|---|---|---|---|
| bounded oscillator | `rsi` → `RSI_14` (SF, 0–100) | nothing is *wrong*; it is already scale-free. But a tree must rediscover "70 is extended" at every split | the regime, named |
| price-scaled overlay | `sma` → `SMA_10` (PX) | **unusable as a feature.** A tree cannot compare 41.72 to a price that was 12 two years ago | a scale-free relation to price |
| event flag | `fvg` → `FVG_BULL` (BIN) | fires and vanishes; a tree sees only the bar it fired on | persistence and recency |

⚠ **A percentile is the wrong companion for two of these three.** Rolling-rank
an already-bounded oscillator and you double-weight the same signal — the
`MULTIL-0` finding, where `RSI_14` vs `RSI_28` measured ρ 0.936 and reverted.
Rolling-rank a binary and you get the event *rate*, which is a different and
usually more useful column, but it is not "the same indicator as a percentage".

---

## The contract

For each parent column, a companion set of at most three columns:

### 1. STATE — a small ordinal, never a bare boolean pair

    <PARENT>_STATE   ∈ {-2, -1, 0, 1, 2}

`-2` deeply cheap · `-1` cheap · `0` neutral · `+1` expensive · `+2` deeply
expensive. One ordinal column, not four one-hot booleans: a tree splits an
ordinal in one node and needs four to reassemble a one-hot set, and the
one-hot version quadruples the column count for no information.

**The thresholds are per indicator and are written down, not inferred.** For a
bounded oscillator they are the documented levels. For anything unbounded they
are quantiles of a *causal trailing window*, never of the whole series.

⚠ **A trailing quantile on a price LEVEL does not give the nominal tails.** Measured
on a 1500-bar random walk at `length=252`: `|STATE| == 2` covers **31.4%** of settled
bars, not the 10% the 5/95 split implies — a non-stationary series sits at its own
window extreme constantly. Ranking the DISTANCE instead brings it to **9.9%**.
**So a `PX` parent's STATE is computed on its `DIST_PCT`, never on the raw level.**
That is what the `PX` shape is for, and the first draft of this contract walked
straight past it.

### 2. DISTANCE — the scale-free relation (PX parents only)

    <PARENT>_DIST_PCT = (close - parent) / close

This is the column that makes a `PX` parent usable at all. It is the
`ichimoku_ml` precedent, which the fork already ships: five price lines became
eight scale-free causal columns.

⚠ Emit this **instead of**, not in addition to, any raw-level companion. A
`PX` column plus its distance form is the same information twice.

### 3. PERSISTENCE — for event flags only

    <PARENT>_BARS_SINCE   integer, capped
    <PARENT>_RATE_<W>     fraction of the trailing W bars where the flag fired

A flag is invisible to a tree on every bar except the one it fires on.
`BARS_SINCE` is capped (default 100) so a never-fired series does not emit an
unbounded ordinal that dominates every split.

---

## Rules every companion obeys

1. **Causal.** Trailing windows only. A whole-series quantile leaks the future
   into every bar — the defect `normalize` is warned about in PINEBI-1e.
2. **Scale-free.** A companion may not reintroduce a price level. If the parent
   is `PX`, the companion is a ratio or a distance.
3. **Named by the parent.** `<PARENT>_STATE`, not `RSI_STATE_14` — the parent
   column name already encodes its parameters, and mined rules in
   `StrategyMaster.csv` match on these strings.
4. **Gate E applies.** A companion derived from a column is correlated with it
   *by construction*; that is exactly what the revert band exists to catch.
   MLCOL-2 measures every companion against its parent and against the shipped
   set, and anything in the revert band is **deleted, not shipped**.
5. **No companion for a column nothing selects.** INDREF-2 is the honest test:
   an indicator mining never picks does not need three more columns.

---

## The three reference implementations

| parent | shape | companions | MLCOL-2 verdict |
|---|---|---|---|
| `RSI_14` (engine: `RSI`) | bounded SF | `RSI_STATE` (thresholds 20/30/70/80, documented levels) | **DELETED** — a deterministic coarsening of `RSI`; permutation importance +0.00013 ± 0.00067 over 15 fits, beats a shuffled null 7/15 |
| `SMA_10` | PX | `SMA_10_DIST_PCT`, then `SMA_10_DIST_PCT_STATE` (quantiles of a trailing 252-bar window **of the distance**, not the level) | **BOTH DELETED** — `_DIST_PCT` ρ 0.9462 vs the already-shipped `NWE_MID_200_8.0_8.0` (revert band); `_STATE` adds nothing measurable |
| `FVG_BULL` | BIN | `FVG_BULL_BARS_SINCE`, `FVG_BULL_RATE_60` | **BOTH DELETED** — both clear Gate E (0.586 / 0.553) and both fail the incremental axes; `BARS_SINCE`'s within-bin ρ is matched by its own parent (excess +0.0004) |

⚠ **ALL 5 are deleted.** Measured 2026-09-08 on 139,657 BIST daily bars against
the engine's production column set — see *Measured — MLCOL-2* at the end of
this document. Round 1 of that section shipped 2 of the 5; both were reversed
in round 2 by controls round 1 did not run (a placebo on the conditional axis,
an across-seed band on the model axis). Do not re-derive any of the five in
MLCOL-1 without reading that section: the reasons generalise.

Implementation: `pandas_ta/ml/companions.py`. Tests:
`tests/test_ml_companions.py`.

⚠ **`RSI` gets no DISTANCE and no RATE.** It is already scale-free, and a rate
of a continuous column is meaningless. The contract says *at most* three
companions; two of the three shapes take fewer, and resisting the urge to emit
a uniform triple is the point of designing on three shapes first.

---

## What this contract does NOT settle

- **The rollout order.** MLCOL-1 orders by the dictionary's
  *"Needs a transform before modelling"* table, because those parents are
  unusable today and pay back first.
- **Whether all 137 `PX` parents deserve a companion.** They do not: many are
  intermediate lines of a multi-column indicator whose useful form is already
  emitted elsewhere. MLCOL-1 decides per indicator, not per column.
- **The trailing-window length for STATE quantiles.** 252 is a placeholder,
  chosen as one trading year. It is a parameter to measure, not a constant to
  believe.

---

# Measured — MLCOL-2 (2026-09-08, round 2)

Rule 4 above says a companion gets no Gate E waiver for being derived. This
section is that measurement.

> ## **Result: 0 of 5 ship. All five reference companions are deleted.**
>
> Round 1 of this section claimed 2 of 5 shipped. Both SHIPs were wrong, and
> both were caught by controls that round 1 did not run: a **placebo** on the
> conditional axis and an **across-seed error band** on the model axis. The
> three round-1 DELETEs were re-verified and stand unchanged.

**Harness:** `../Backtesting/scripts/analysis/measure_ml_companion_overlap.py`.
**CSVs:** `../Backtesting/backtest_results/tvpta6/` —
`mlcol2_companion_overlap_gridA_full.csv` (2,425 cells),
`mlcol2_companion_verdicts.csv`, `mlcol2_companion_model_runs.csv` (75 fits),
`mlcol2_companion_sensitivity.csv`.

**Grid.** 30 BIST_100 daily frames from `datastore/cache` with >= 400 bars,
**139,657 pooled bars**. Comparator set: the **485** numeric columns of
`IndicatorEngine(include_advanced=True).compute_all()` — the config
`batch_runner.py` wires in production, and the larger of the two available
comparator sets. (`measure_fvg/ifvg/madiv_overlap_full.py` used
`include_advanced=False` and so never scored against the columns `True` adds,
`natr` among them.) ⚠ **485 is 2 optimistic and includes 5 non-features:**
5 of the 485 are the raw OHLCV inputs, and `TOD_SLOT_RVOL_20_20` /
`TOD_SLOT_VVOL_20_20` are intraday-only and all-NaN on daily bars, scoring 0
cells (`note = n<100`, n = 0) — so **483 columns are effective, 478 computed**.

Exact invocation and versions, from the run's own `PROVENANCE` lines:

    scripts/analysis/measure_ml_companion_overlap.py --stage 2 --work <cache>
    python=3.11.9 pandas=2.3.3 numpy=1.26.4 scipy=1.13.0 sklearn=1.4.2

⚠ **The contract writes the RSI parent as `RSI_14`; the engine ships it as
`RSI`**, and it is `rsi(Close, length=14)` (`speedy_indicators.py:30`). The
measurement uses the name production emits.

## Gate E — rho vs parent and vs the shipped set

| companion | parent | ρ vs parent | ρ vs parent (Fisher-z, 30 frames) | max abs ρ vs shipped set (excl. parent) | against | n (that cell) | Gate E |
|---|---|---|---|---|---|---|---|
| `RSI_STATE` | `RSI` | +0.5886 | +0.5876 | 0.5950 | `ATR_BREAKOUT_UP` | 139,237 | SHIP |
| `SMA_10_DIST_PCT` | `SMA_10` | +0.0079 | +0.0051 | **0.9462** | `NWE_MID_200_8.0_8.0` | 133,657 | **REVERT** |
| `SMA_10_DIST_PCT_STATE` | `SMA_10_DIST_PCT` | +0.8877 | +0.8929 | 0.8347 | `NWE_MID_200_8.0_8.0` | 133,657 | DISCLOSE |
| `FVG_BULL_BARS_SINCE` | `FVG_BULL` | −0.6260 | −0.6255 | 0.5861 | `CCI` | 138,692 | SHIP |
| `FVG_BULL_RATE_60` | `FVG_BULL` | +0.1604 | +0.1523 | 0.5533 | `ICHI_CHIKOU_VS_CLOUD` | 137,347 | SHIP |

The pooled-bar ρ and the per-frame Fisher-z pooled ρ agree to within 0.009 on
every row (largest gap `FVG_BULL_RATE_60`, 0.1604 vs 0.1523), so the pooled
figure is not a frame-length artefact. **Gate E alone would ship three of these
five.** It ships none.

## Axis 3a — model, over 5 seeds × 3 split points (15 fits per companion)

Chronological split per ticker at 0.6 / 0.7 / 0.8; `HistGradientBoostingClassifier`
on `[parent]` versus `[parent, companion, NULL]`, where **NULL is the
companion's own values shuffled** — same marginal distribution, zero
information, so its measured importance is this procedure's noise floor rather
than an assumed one.

| companion | AUC parent | AUC +companion | Δ (sd across runs) | perm. imp. companion (**sd across runs**) | within-fit shuffle sd | perm. imp. **parent** | perm. imp. NULL | beats NULL |
|---|---|---|---|---|---|---|---|---|
| `RSI_STATE` | 0.5087 | 0.5090 | +0.0002 (0.0024) | +0.00013 (**0.00067**) | 0.00015 | +0.00885 | +0.00000 | 7/15 |
| `SMA_10_DIST_PCT` | 0.5038 | 0.5046 | +0.0008 (0.0053) | +0.00194 (**0.00239**) | 0.00166 | +0.00216 | −0.00034 | 13/15 |
| `SMA_10_DIST_PCT_STATE` | 0.5044 | 0.5045 | +0.0001 (0.0016) | +0.00028 (**0.00226**) | 0.00215 | +0.00689 | +0.00009 | 9/15 |
| `FVG_BULL_BARS_SINCE` | 0.4999 | 0.5018 | +0.0018 (0.0023) | +0.00128 (**0.00264**) | 0.00192 | −0.00001 | +0.00055 | 9/15 |
| `FVG_BULL_RATE_60` | 0.4999 | 0.5009 | +0.0009 (0.0044) | +0.00079 (**0.00392**) | 0.00220 | −0.00024 | +0.00036 | 8/15 |

⚠ **Round 1's error is visible in this table's last three columns.** It
reported `FVG_BULL_BARS_SINCE` at +0.00468 ± 0.00190 and shipped it on
mean − 2sd = +0.0009. That ±0.00190 was ten shuffles of ONE fitted model at
ONE seed and ONE split — shuffle noise only, with learner-seed and split
variance excluded, and those are the dominant terms at AUC ≈ 0.50. The
across-run sd is 0.00264 against a mean of 0.00128, so mean − 2sd is
**negative**. Round 1's own output already contained the calibration that
proved it: `perm_imp_parent` was **negative** for a parent the model was
fitted on, which puts procedure noise at O(0.002–0.004). That column existed
in `mlcol2_companion_verdicts.csv` and round 1 did not print it. It is printed
here, and it is the reason no companion clears this axis.

**No companion clears axis 3a.** Every one fails mean − 2·(across-run sd) > 0,
and none beats the shuffled NULL in more than 13 of 15 runs.

## Axis 3b — conditional rank correlation, against a PLACEBO

Inside each bin of the parent, Spearman ρ between the companion and the forward
return, Fisher-z pooled — and **the identical statistic run on the PARENT over
the same bins and the same rows**. Comparing the companion's within-bin ρ to
zero, as round 1 did, is the wrong null.

| companion | h | companion ρ (z) | **placebo parent ρ (z)** | excess | paired bootstrap 95% CI (300 ticker resamples) | bins | n |
|---|---|---|---|---|---|---|---|
| `RSI_STATE` | 1 | −0.0099 (−1.11) | −0.0151 (−1.70) | −0.0053 | — | 3 | 12,565 |
| `RSI_STATE` | 5 | −0.0372 (−4.17) | **−0.0226 (−2.53)** | +0.0146 | [+0.0026, +0.0281], 99.3% > 0 | 3 | 12,529 |
| `SMA_10_DIST_PCT` | 1 | +0.0165 (+3.38) | −0.0029 (−0.59) | +0.0136 | [−0.0062, +0.0205], 88.7% > 0 | 10 | 41,881 |
| `SMA_10_DIST_PCT` | 5 | +0.0253 (+5.17) | −0.0118 (−2.42) | +0.0134 | [−0.0238, +0.0328], 75.0% > 0 | 10 | 41,761 |
| `SMA_10_DIST_PCT_STATE` | 1 | +0.0040 (+0.81) | +0.0016 (+0.32) | +0.0024 | — | 10 | 41,881 |
| `SMA_10_DIST_PCT_STATE` | 5 | −0.0067 (−1.36) | +0.0036 (+0.74) | +0.0030 | — | 10 | 41,761 |
| `FVG_BULL_BARS_SINCE` | 1 | −0.0093 (−1.91) | +0.0021 (+0.43) | +0.0072 | — | 1 | 41,881 |
| `FVG_BULL_BARS_SINCE` | 5 | −0.0166 (−3.39) | **+0.0162 (+3.31)** | **+0.0004** | [−0.0116, +0.0114], **52.7% > 0** | 1 | 41,761 |
| `FVG_BULL_RATE_60` | 1 | +0.0031 (+0.63) | +0.0021 (+0.43) | +0.0010 | — | 1 | 41,881 |
| `FVG_BULL_RATE_60` | 5 | +0.0060 (+1.24) | +0.0162 (+3.31) | −0.0101 | — | 1 | 41,761 |

The bootstrap resamples whole tickers with replacement, because the companion's
ρ and the placebo's are computed on the same rows and are strongly dependent —
their separate z-scores say nothing about whether the *difference* is real.
It is run only on cells that reach |z| >= 2.5, since a cell that fails on z
cannot be rescued by it.

**`FVG_BULL_BARS_SINCE` is settled by this table.** Its round-1 headline
(|ρ| 0.0166 at fwd5, z −3.39) is almost exactly matched by the placebo
(|ρ| 0.0162, z +3.31) on the same rows: excess **+0.0004**, bootstrap CI
straddling zero, positive in **52.7%** of resamples. A coin flip. The parent
carries that relation; the companion restates it.

⚠ **Both `FVG_BULL` companions condition on 1 bin.** `FVG_BULL` is binary, so
binning its raw values collapses to its two levels and only the zero level has
both ≥ 100 rows and a non-constant companion. "Conditioning on the parent" for
these two therefore means "restricting to bars where the flag did not fire" —
weaker conditioning than the ten-bin case, and stated rather than hidden.
(Round 1 reported 9 bins here. That was a defect: it binned
`rank(method="first")`, which makes every rank unique, so `qcut` never saw a
duplicate edge, `duplicates="drop"` and its `except ValueError` were dead code,
and a 2-valued parent was sliced **by row order**. Round 2 bins raw values.)

### Why `RSI_STATE` is deleted even though it beats its placebo

`RSI_STATE` is the one cell where the companion's within-bin |ρ| genuinely
exceeds the parent's: 0.0372 vs 0.0226 at fwd5, and the paired bootstrap puts
the excess above zero in 297 of 300 ticker resamples. That is a real measured
difference and it is not thrown away.

It is still not a reason to ship, for a reason of principle that the numbers
then confirm:

`ml_state(source, kind="rsi")` (`companions.py`) is a **memoryless monotone
step function of the current RSI value and nothing else**. Inside a bin of the
parent it is a *coarsening* of the parent — a subset of its information, never
a superset. So it cannot carry information the parent lacks, and a larger
within-bin Spearman does not contradict that: **Spearman measures monotone rank
association, not information.** A two-level step can track a non-monotone
within-bin relation better than the underlying continuous value does, which is
precisely what these numbers show.

That makes the benefit **representational, not informational** — worth
something only to a learner that cannot express the step itself. This fork's
consumer is a **tree-based miner**, which can express it, and the axis that
uses such a learner says so plainly: permutation importance +0.00013 ± 0.00067
across 15 runs, beating the shuffled NULL in **7 of 15** — worse than chance.
The tree finds the threshold on its own and gains nothing from being handed it.

⚠ **Round 1's line 214 said the opposite in plain English** — that `RSI_STATE`
carries ρ −0.037 "that the raw RSI value does not". The raw RSI value
*determines* which side of the threshold the bar is on. That sentence was false
as information, and it was the whole SHIP argument. It is retracted.

The harness now encodes this: companions flagged
`deterministic_of_parent=True` in the `COMPANIONS` registry (`RSI_STATE`,
`SMA_10_DIST_PCT_STATE`) cannot ship on the conditional axis at all; the model
axis decides for them. `SMA_10_DIST_PCT` (also reads `Close`),
`FVG_BULL_BARS_SINCE` and `FVG_BULL_RATE_60` (read the parent's *history*) are
not deterministic functions of the current parent value and keep both axes.

## Thresholds: not pre-registered, and no longer decisive

⚠ **`COND_Z_MIN = 3.0` and `COND_RHO_FLOOR = 0.01` were written after round 1's
numbers were on screen, and the harness is untracked, so nothing orders the
constants before the data.** They were also decisive at the margin in round 1:
`RSI_STATE`'s fwd1 |ρ| = 0.00987 sat 1.3% under the floor while fwd5 cleared,
and `FVG_BULL_BARS_SINCE` sat at |z| 2.58 / 2.65 against a 3.0 bar.

Two corrections:

1. **Multiplicity.** The conditional axis is an OR over 2 horizons × 5
   companions = **10 tests**; at an uncorrected |z| >= 3 the family-wise error
   is not 5%. The harness now applies a two-sided Bonferroni correction over
   that family: critical **|z| = 2.807**, printed by the run.
2. **Sensitivity.** The full verdict table is recomputed over
   z ∈ {2.5, 3.0, 3.5} × ρ_floor ∈ {0.005, 0.01, 0.02}
   (`mlcol2_companion_sensitivity.csv`). **All 9 cells return DELETE for all 5
   companions; the run reports `verdicts that MOVE across the grid: none`.**
   The 0-of-5 result does not depend on either constant.

## Verdicts

| companion | Gate E | axis 3a (model) | axis 3b (conditional vs placebo) | verdict |
|---|---|---|---|---|
| `RSI_STATE` | SHIP (0.595) | fails: +0.00013 ± 0.00067, beats NULL 7/15 | not competent — deterministic coarsening of parent | **DELETE** |
| `SMA_10_DIST_PCT` | **REVERT** (0.9462) | fails: +0.00194 ± 0.00239 | excess +0.0134, CI straddles 0 | **DELETE** |
| `SMA_10_DIST_PCT_STATE` | DISCLOSE (0.8877 vs parent) | fails: +0.00028 ± 0.00226 | not competent — deterministic | **DELETE** |
| `FVG_BULL_BARS_SINCE` | SHIP (0.586) | fails: +0.00128 ± 0.00264, beats NULL 9/15 | excess **+0.0004**, 52.7% > 0 | **DELETE** |
| `FVG_BULL_RATE_60` | SHIP (0.553) | fails: +0.00079 ± 0.00392 | excess −0.0101 | **DELETE** |

**`SMA_10_DIST_PCT` deserves its own note**, because the shape did work: ρ
against its own parent `SMA_10` is +0.0079, so the distance form really did
strip out the price level. It dies on redundancy — the engine already ships
this construction under other names. `NWE_MID_200_8.0_8.0` is
`(close − nw_mid) / close * 100`
(`pandas_ta/overlap/nadaraya_watson_envelope.py:47`) at ρ 0.946, and `bias` is
`(close − SMA_20) / SMA_20` (`indicator_engine.py:1151`) at ρ 0.849 — the same
construction on a different smoother and a different length. Then `week_trend`
0.909, `kdj_J_9_3` 0.883, `BB_%B` / `ZSCORE_20` 0.875, `willr` 0.860,
`CCI` 0.852.

⚠ **This is a re-derivation, not a discovery.** `iama`'s
%-distance-from-MA column was wired, measured against the same
`NWE_MID_200_8.0_8.0` at **ρ 0.9498**, and un-wired for it on **2026-08-14** —
recorded at `../Backtesting/scripts/utils/gen_indicator_register.py:643-645`.
That MLCOL-2 independently landed within 0.004 of the August figure is
corroboration; that the screen it now recommends was already known in August
and not applied to the contract is the more useful finding.

**Nothing is removed from `pandas_ta/ml/companions.py`.** That module ships the
four *primitives*, not per-parent columns, and no measurement in either round
found a defect in any primitive. What is deleted is the reference COLUMN SET.

## What MLCOL-1 must do differently

1. **Gate E is necessary but not sufficient.** Three of these five clear Gate E
   outright and none survives. `FVG_BULL_RATE_60` passes at 0.553 and dies.
2. **Screen a proposed `DIST_PCT` against the engine's existing distance
   columns before building it** — `NWE_MID_200_8.0_8.0`, `bias`,
   `dist_to_psar_pct`, `ATR_POSITION`, `BB_%B`, `ZSCORE_20`. This was already
   known on 2026-08-14 (above). For the number of `PX` parents this applies to,
   read the opening paragraph of this document; it is `Counter`-derived from
   the generated dictionary and asserted by
   `tests/test_ml_companions.py`. **Do not retype it here** — four different
   numbers for that one quantity were in circulation on 2026-09-08.
3. **A STATE companion on a continuous parent is a deterministic coarsening.**
   It cannot add information, only representation, and a tree does not need the
   representation. Both STATE companions measured here died. Do not emit STATE
   for a continuous parent without a specific argument that the *consumer*
   cannot express the threshold.
4. **Run both incremental axes with their controls** — the placebo on the
   conditional axis, and across-seed/across-split bands plus a shuffled NULL on
   the model axis. Round 1 ran neither and produced two false SHIPs out of two.

## Not measured

- **Hourly frames.** Daily only. The event-flag companions are the most
  bar-size sensitive and nothing here speaks to that.
- **The other `PX`, `SF` and `BIN` parents.** MLCOL-1 is deferred; this proves
  the method, not the answers.
- **Any target other than forward close-to-close return** at 1 and 5 bars. The
  live books trade path-dependent exits (SL / TS / max-hold); a companion
  useless for direction could still be useful for exit timing.
- **US frames, and BIST_100 tickers past the first 30** with a cached daily
  parquet of >= 400 bars. `--max-tickers` raises the grid.
- **Whether a companion helps a NON-tree consumer.** The `RSI_STATE` deletion
  turns on this fork's consumer being tree-based. A linear or rank-based model
  downstream would change that verdict, and no such consumer was tested.
