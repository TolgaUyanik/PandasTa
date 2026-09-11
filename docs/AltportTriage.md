# ALTPORT-0 — Triage of the 20 `port` candidates

**Verdict: 7 BUILD, 13 SKIP.** Scope: the 11 `verdict == "port"` rows of
`../AlternativeRepos/altrepo_pandas_ta_classic.csv` and the 9 of
`../AlternativeRepos/altrepo_tti.csv`. The 114 `port - alternate impl` rows are out of scope.

**BUILD here means "enters ALTPORT-1 screening", not "authorised to write."** ALTPORT-1
runs Gates A–F; this document only decides which candidates are worth spending that on.
A BUILD row can still be deleted at Gate E, and one of the seven (`hvol`) is expected to
have to fight for it.

This document does **not** implement anything and does not run Gate E. It answers the
question the behavioural scanners did not: *is it worth building*, given that they only
established *it is not a rename of something shipped*.

## Round 2: what changed, and why

Round 1 of this file carried three "identity" numbers — `fosc` = `cfo` diff 0.0, `dx`
diff 7.1e-14, `VolatilityChaikins` = `cvi` diff 0.0 — and **all three were wrong.** Each
was produced by hand-transcribing the candidate with FORK helpers (`ta.linreg`, `ta.rma`,
`ta.ema`) and comparing it to a FORK column. That comparison cannot fail. Every number in
every CANDIDATE in this file is called from the **upstream package**.

⚠ **The unrounded Gate-D forms are the exception and are transcriptions**, not upstream
calls — `scalecheck_altport0.py` recomputes them without tti's `.round(4)` precisely
because the rounding is what it is measuring. That is structurally the same shape as the
round-1 defect, so the transcriptions are DIFFED against upstream at x1 rather than
trusted: max |transcription − tti| is **4.99983e-05** (PB upper/lower), **4.99415e-05**
(WAD bar), **4.99922e-05** (RangeIndicator 5/3) and **4.99998e-05** (RangeIndicator
14/3) — in every case exactly the `.round(4)` half-ulp floor, which is the largest
agreement a rounded reference permits.

| row | round 1 claimed | round 2, upstream |
|---|---|---|
| 9 `fosc` | `= cfo`, max abs diff **0.0** | max abs diff **9.8601**, ρ **0.967784** |
| 10 `dx` | `= 100·\|DMP−DMN\|/(DMP+DMN)`, diff **7.1e-14** | max abs diff **24.931**, **3,860 / 51,854 bars (7.44%)** over 1e-9, ρ **0.998721** |
| 2 `VolatilityChaikins` | `= cvi`, diff **0.0** | AEFES max abs diff **6.3675**, pooled max **8073.93** (ALFAS_IS), ρ **0.999955** |

Round 1 also filed the scanners' correct `fosc` ↔ `cfo` ρ of 0.950818 — which `TODO.md:646`
said not to re-derive — as an unexplained discrepancy in its own limitations section. It was
not a discrepancy; the document was wrong and the scan was right. **All three verdicts
survive. None of the three stated reasons did.** Three more round-1 claims are corrected
below (`Envelopes` algebra, the `ce` family count, `crsi`), and one verdict is **reversed**
(`smc_sweep`) on a measurement round 1 named as the right test and then did not run.

## What was measured, and on what

| script | what it does |
|---|---|
| `docs/gen_altport0_triage.py` | Spearman ρ of each candidate — **called from the upstream package** — against the shipped columns nearest to it, plus the identity checks, the `smc_sweep` coincidence test, and the scanners' own probe frame |
| `docs/scalecheck_altport0.py` | the cheap half of Gate D: recompute at O/H/L/C × 8, report `max\|x8 − x\|`, with and without tti's output rounding |

**Frame.** The first 12 `*_1d.parquet` files in `Backtesting/datastore/cache/` carrying
OHLCV with ≥ 800 rows — **52,022 daily bars**, pooled. Named, not globbed at read time:
`AEFES_IS` `AGHOL_IS` `AHGAZ_IS` `AKBNK_IS` `AKCNS_IS` `AKFGY_IS` `AKFYE_IS` `AKSA_IS`
`AKSEN_IS` `ALARK_IS` `ALBRK_IS` `ALFAS_IS`. The ×8 checks run on `AEFES_IS` alone
(5,695 bars). Where the scanners' seeded 260-bar `_probe_frame` is quoted it says so.

**Three caveats that bound every number here.**

1. This is **not Gate E.** Gate E is ρ against the *entire* shipped column set of the
   engine's production config. Below is ρ against hand-picked near neighbours. A candidate
   that looks clean here can still fail Gate E; the full-set maximum can only rise.
2. Both scripts import `pandas_ta` and `pandas_ta_classic` into one process, so `df.ta` is
   registered twice under the same name. Nothing goes through `df.ta` — every call is
   `ta.<fn>(...)` / `tac.<fn>(...)` against the module. Do not import either script from
   the test suite.
3. 12 tickers, one market, one timeframe, daily only. `vosc` in particular is a volume
   indicator judged on BIST daily volume.

**tti rounds its output** — `.round(4)` on most classes, `.round(10)` on
`MarketFacilitationIndex`, whose values are of order 1e-7. Rounding a price-scaled quantity
to fixed decimals is itself scale-dependent, so a form *derived from tti output* fails an
×8 check even when the maths is invariant. Every Gate-D number below is reported both ways.
A port would not round.

## The table

`shipped checked` lists the columns each candidate was actually correlated against.

| # | candidate | source | what it computes | shipped checked (ρ) | verdict | reason |
|---|---|---|---|---|---|---|
| 1 | `cvi` | classic | Chaikin Volatility: `100·(EMA₁₀(H−L) − EMA₁₀(H−L)[−10]) / EMA₁₀(H−L)[−10]` | `NATR_14` 0.260468 · `MASSI_9_25` 0.302922 · `CHOP_14` −0.262132 | **BUILD** | Nothing shipped measures the *rate of change* of range. Scale-free as written (×8 Δ 0, unrounded and from upstream). |
| 2 | `VolatilityChaikins` | tti | the same construction as `cvi` | vs upstream `tac.cvi`: ρ **0.999955** (n=51,794); AEFES max abs diff **6.3675**, 5,675 / 5,676 bars over 1e-9 | **SKIP** | The same indicator reached the shortlist from two repos. It is **not** bit-identical — tti seeds `ewm(adjust=False)` at bar 1 and `.round(4)`s, classic's `ema` seeds with an SMA, and the differences are a warm-up transient — but at ρ 0.999955 only one of the two can ship. Build `cvi`, whose parameters are exposed. |
| 3 | `hvol` | classic | `100·stdev(log returns, ddof=1)·√252` | `NATR_14` **0.821076** · `HARPARK` 0.683306 | **BUILD** | Gap-inclusive close-to-close realised vol; `natr` is intraday-range vol. Highest Gate E risk of the seven — see below. |
| 4 | `avolume` | classic | `stdev(log returns, ddof=0)·√252` | vs upstream `tac.hvol`: ρ **1.000000**, ratio constant **0.009746794345** = √(19/20)/100 to 12 dp (n=51,782) | **SKIP** | Rank-identical to `hvol` by construction: same formula, `ddof` and the ×100 are positive constants. Verified against both upstream functions, not a transcription. |
| 5 | `MarketFacilitationIndex` | tti | Bill Williams `(H−L)/volume` | `NATR_14` 0.490149 · `PVR` 0.265396 · `EOM` −0.070531 · `CMF_20` 0.022134 | **BUILD** | Range produced per unit of volume — a price-impact/liquidity question nothing shipped asks in scale-free form. |
| 6 | `ProjectionBands` | tti | rolling-OLS slope of H and of L, project each of the last n bars forward onto today, take max/min → slope-corrected Donchian | width% vs a donchian-width% derivation **0.854738** · upper-dist% vs same 0.473020 | **BUILD** | "Highest high / lowest low *after removing the trend*". `donchian` is raw; `linreg_channel` bands close by stdev. ⚠ **An earlier revision of this row claimed the engine ships no donchian-derived column, on a `grep` for `DCU`/`DCL`. That was wrong and the file being grepped says so in words.** `../Backtesting/backtesting_engine/indicator_engine.py:1278-1329` emits a twelve-member Donchian distance grid — `dist_low_{5,20,21,60,63,252}` and `dist_from_high_{5,20,21,60,63,252}` — and the comment at `:1367-1369` reads *"Donchian deliberately gets NOTHING - its causal form already ships as dist_low_20 / dist_from_high_20"*. Searching for a NAME instead of the thing is the same defect the altrepo scanners kept producing. Measured against the real production forms, same 12 frames (n=51,866): `pb_width_pct` vs `dist_low_n − dist_from_high_n` **0.832368** (n=14), 0.784615 (n=5), 0.749556 (n=20); `pb_up_dist_pct` vs `dist_from_high_5` **−0.767717**, vs `dist_from_high_14` −0.532970; `pb_lo_dist_pct` vs `dist_low_14` 0.448420; `posc_14` vs the engine-grid position 0.402444. **BUILD survives at 0.832 < 0.90, but `dist_low_*` / `dist_from_high_*` are the Gate E adversary for rows 6 and 7, not a hypothetical.** Precedent ALTPORT-1 will be judged against: `indicator_engine.py:1373-1396` records the engine DELETING `dist_to_bb_upper_pct` / `dist_to_bb_lower_pct` at r 0.9429 / 0.9379 against exactly those columns. |
| 7 | `ProjectionOscillator` | tti | `100·(close − lower)/(upper − lower)` + a 3-EMA trigger | `WILLR_14` **0.421606** · `STOCHk_14_3_3` 0.201571 · donchian-position 0.421606 | **BUILD** | The slope correction is not second-order: 0.42 against `willr`, which is the same read-out on the *uncorrected* range. Not the shipped `po` (Price Oscillator) — acronym collision only. |
| 8 | `WilliamsAccumulationDistribution` | tti | per bar: up → `close − min(prev close, low)`; down → `close − max(prev close, high)`; else 0 | `BOP` **0.697630** · `ADo` 0.025122 · `TRUERANGE_1` 0.000815 | **BUILD** | "How much of the true range did the close capture in the direction of today's move" — direction-gated and gap-aware; `ad`'s multiplier is undirected, `bop` ignores the prior close. |
| 9 | `smc_sweep` | classic | prior swing extreme taken out and reclaimed intrabar, filtered by wick ≥ `wick_mult`×body → one ±1 column | vs shipped `liquidity_sweep`, ±1-bar event coincidence: **133 of 895 smc_sweep events (14.9%)**, **132 of 881 LSH events (15.0%)** | **BUILD** *(reversed from round 1)* | Round 1 skipped this as "the identical event" and named ±1-bar coincidence as the right metric without running it. Run, it **refutes** that reason: the two detectors fire on nearly disjoint bars. `liquidity_sweep` uses confirmed pivots with an ATR tolerance and a level pool; `smc_sweep` uses a rolling n-bar extreme plus a wick-rejection filter — closer to "a hammer at a 20-bar low". Weakest of the seven: the *concept* is still shared, and both flags are sparse (~1.7% of bars). |
| 10 | `fosc` | classic | `100·(close − classic.linreg(close, n, tsf=True))/close` | `CFO_14` **ρ 0.967784, max abs diff 9.8601** (n=51,866) · `CFO_9` 0.732801 · probe frame at length 14 **ρ 0.950818, diff 1.4219**; at length 9 **0.913517**; at each side's default **0.759855** | **SKIP** | ρ 0.9678 is above the 0.90 revert line. It is **not** the same expression, and round 1 was wrong to say so: `pandas_ta.linreg` runs x = 1..n and `pandas_ta_classic.linreg` runs x = 0..n−1, so `pandas_ta.linreg(tsf=True)` == `classic.linreg(tsf=False)` (max diff 1.5e-14) and classic's TSF projects one slope-step further. Measured: **`fosc = cfo − 100·slope/close`, max residual 3.5e-13 over 51,866 bars.** A different forecast point, not a rename — and still too close to ship. |
| 11 | `dx` | classic | `100·\|DM⁺ − DM⁻\|/(DM⁺ + DM⁻)` on Wilder-smoothed DM | vs `100·\|DMP_14−DMN_14\|/(DMP_14+DMN_14)` from shipped columns: **ρ 0.998721, max abs diff 24.931, 3,860 / 51,854 bars (7.44%) over 1e-9** · `ADX_14` 0.576974 | **SKIP** | `pandas_ta/trend/adx.py` computes this exact `dx` internally and emits its RMA; the ATR normalisation in the shipped `DMP`/`DMN` cancels in the ratio. So **the fork can already produce `dx` from two shipped columns in one line.** The upstream 24.931 gap is warm-up seeding, not a different indicator: classic's `ma("rma")` seeds Wilder smoothing with an SMA at bar `length`, `ta.rma` does not. **Trap:** ρ against `ADX_14` is only 0.577 — a correlation-only gate would have shipped a column that is a one-line function of two shipped ones. |
| 12 | `adxr` | classic | `(ADX + ADX[−(n−1)])/2` | `ADX_14` **0.888016** | **SKIP** | An exact function of one shipped column and its own lag. A lag feature on `ADX_14` gives the miner the same thing. |
| 13 | `ce` | classic | Chandelier Exit: `max(H,n) − mult·ATR` / `min(L,n) + mult·ATR` | distance form vs `cksp` distance **0.923196** · vs `supertrend` distance 0.779945 | **SKIP** | Above the 0.9 revert line against `cksp` (Chande Kroll Stop), the same construction. The fork already ships **six** members of this family, all confirmed in `Category`: `cksp`, `supertrend`, `supertrend2`, `pmax`, `halftrend`, `tvstop`. |
| 14 | `mavp` | classic | SMA with a per-bar variable window taken from a second input series | — (rests on the scanners' `t3_tv` 0.9886; not re-derived) | **SKIP** | Price level (`PX`), so it needs a distance form; and it needs a `periods` series the engine does not carry. The fork ships 30+ MAs including adaptive ones (`kama`, `vidya`, `mama`). Parameter reach — PINEBI-1c's road. |
| 15 | `msw` | classic | Mesa Sine Wave: one-bin DFT phase over a fixed 5-bar window → `sin(φ)`, `sin(φ+45°)` | `HT_SINE` 0.032402 · `HT_LEADSINE` 0.007007 · `EBSW` 0.260061 | **SKIP** | Same economic question as the shipped `ht_sine` — cycle phase as a sine/lead pair — with the estimator Ehlers superseded (fixed 5-bar DFT on undetrended price vs the adaptive Hilbert dominant cycle TALIB-1 already shipped). Low ρ says the estimator *disagrees*, not that the question is new. Also fails scale-free: **160 / 5,690 bars change under ×8** (max Δ 1.97 on a ±1 column) because `abs(rp) > 0.001` is an absolute epsilon on a price-scaled quantity — the branch fires **194×** at ×1 and **34×** at ×8. |
| 16 | `vosc` | classic | `100·(SMA(vol,12) − SMA(vol,26))/SMA(vol,26)` | `PVO_12_26_9` **0.753468** | **SKIP** | Same question as the shipped `pvo` — volume momentum as a percentage of the slow average — differing only in `mamode`. A question-redundancy skip, and the measurement is disclosed as marginal: 0.7535 sits just *under* the 0.76 ship line, so a correlation-only gate would have passed it. |
| 17 | `Envelopes` | tti | `(1±shift)·SMA(close, n)`, default `period=20, shift=0.10` | distance form vs `BIAS_SMA_20` **ρ 0.999998** | **SKIP** | With `u = close/MA`, the distance form is `1 − (1+s)/u` and `bias` is `u − 1`: **strictly monotone in `u`, hence Spearman ≈ 1 by construction.** Round 1 called this an affine shift; it is not — the std of `env_dist − 100·bias` is **1.0760**, not 0. Monotone is enough: a tree sees the identical split set. The previous batch deleted a column on exactly this collision. |
| 18 | `RangeIndicator` | tti | up bar → `TR/Δclose`, down bar → `TR`; min–max normalised over `range_period`; EMA(`smoothing_period`) | `ER_10` 0.037407 · `CHOP_14` −0.047021 · `NATR_14` 0.023026 (at 5/3) | **SKIP** | **Fails Gate D by construction, measured at both parameterisations and with tti's rounding removed:** at tti's own defaults `range_period=5, smoothing_period=3` max Δ under ×8 is **83.2727** on a column whose max is 97.91; at `14, 3` it is **68.9421** on 90.6229. The up-bar branch is unitless (`TR/Δclose`), the down-bar branch is a price, and the min–max window normalises across incommensurable quantities. No repair preserves Dorsey's definition. For the record its overlap with everything tested is ~0 — well-formed, it would have been the most interesting row here. |
| 19 | `RelativeMomentumIndex` | tti | RSI with `close − close[−m]` in place of `close − close[−1]`; defaults `period=8, momentum_period=4` | `RSI_14` **0.929918** | **SKIP** | Above the 0.9 revert line at tti's own defaults. RMI is RSI with the difference lookback as a parameter, on top of a shipped RSI family: `rsi`, `rsx`, `lrsi`, `stochrsi`, `kalman_rsi`, `rsi_divergence`, `cmo` — all seven verified present in `Category`. (Round 1 listed `crsi`; `hasattr(ta,"crsi")` is False and it is in no `Category`.) |
| 20 | `SwingIndex` | tti | Wilder's Swing Index per bar: `50·(num/R)·(K/3)`, clamped ±100 | as written vs `BOP` 0.739406 · scale-free repair `swi_sf_direct` = `50·num/R` vs `BOP` **0.775144** (n=51,196) · vs `qstick/close` 0.278947 | **SKIP** | As written it is **not scale-free** — max Δ **87.4942** under ×8 — because `K/3` is a raw price over Wilder's limit-move constant. (Clamping is not the objection: 0.5899% of the 51,196 pooled bars reach ±100, and 0.00% of AEFES, whose max \|swi\| is 51.1595.) The repair `50·num/R` **is** scale-free (×8 Δ 0 computed directly) but measures 0.794215 against `BOP` alone — inside the 0.76–0.80 disclosure band before any of the rest of the candle/range family is counted — and it is no longer Wilder's indicator, so Gate A loses its oracle. |

## Gate-D screen, both ways

`docs/scalecheck_altport0.py`, AEFES_IS, 5,695 bars, O/H/L/C × 8.

| form | from upstream output | tti rounding removed | verdict |
|---|---|---|---|
| `cvi_10` | 0 | — | scale-free |
| `hvol_20` | 0 | — | scale-free |
| `ce_long_dist_pct` | 2.5e-13 | — | scale-free (skipped for other reasons) |
| `mfi_bw_sf` | 0.00419343 | **0** | scale-free; the deviation is `.round(10)` on values of order 1e-7 |
| `pb_width_pct` | 0.0587765 | **0** | scale-free; `.round(4)` on a price-scaled band |
| `pb_up_dist_pct` | 0.0317016 | **0** | as above |
| `posc_14` | 0.4807 | **0** | as above |
| `wad_bar_sf` | 0.0201128 | **1.2e-13** | scale-free; `.round(4)` on a price |
| `swi_sf` | 49.9714 | **0** | scale-free when computed directly; see below |
| `swi_tti` | 87.4942 | — | **NOT scale-free** — the `K/3` term |
| `msw_sine_5` | 1.97188 | — | **NOT scale-free** — absolute epsilon |
| `ri_5_3` | 83.2727 | **83.2727** | **NOT scale-free** — mixed units |
| `ri_14_3` | 68.9422 | **68.9421** | **NOT scale-free** — mixed units |

`swi_sf` fails only when *derived* from tti output by dividing `K/3` back out: at ×8 the
`K/3` term is 8× larger, so the ±100 clamp bites — **0 clamped bars at ×1, 101 at ×8** —
and the pre-clamp value cannot be recovered. Computed directly as `50·num/R` it is exactly
invariant. That does not rescue the verdict (the ρ does the skipping), but the
distinction matters for anyone reading the table.

## The seven BUILDs

### 1. `cvi` — Chaikin Volatility

* **Question no shipped column answers.** Is the trading range *expanding or contracting*,
  and by what percentage over the last n bars? `natr` gives the level, `massi` a ratio of
  two range smoothings, `chop` trending-vs-ranging. Measured: 0.260 / 0.303 / −0.262.
* **Form.** Already scale-free — a ratio of two range EMAs. ×8 Δ 0 from upstream.
  Ship `CVI_{ema_length}_{roc_length}`, one `SF` column.
* **Gate E risk.** Low; nearest measured 0.303. The real risk is a *derived* engine column
  (`natr.pct_change(10)`); ALTPORT-1 must sweep the production config, not the package.

### 2. `hvol` — annualised realised volatility

* **Question.** Close-to-close realised volatility includes overnight gaps and excludes
  intraday range; `natr` is the opposite. On BIST that is not academic — DI-1 exists
  because the daily series is full of limit moves and gaps.
* **Form.** Already scale-free (log returns). ×8 Δ 0. Ship `HVOL_{length}_{annualization}`.
* **Gate E risk — the highest of the seven.** ρ **0.821076** against `NATR_14`.
  ⚠ **The nearest shipped column by construction is NOT measured here:**
  `indicator_engine.py:436` computes `rel_vol_20 = s_ret1.rolling(20).std() /
  i_ret1.rolling(20).std()` — `hvol_20`'s own numerator over a per-date constant.
  ALTPORT-1 must measure against `rel_vol_20` FIRST, and against `ZSCORE_20`'s
  `close.rolling(20).std()` (`:1060`) if it reaches the production config.
  (n=51,782), which *is* in the engine's production config. Above the 0.76–0.80 disclosure
  band and not far off 0.9, before the full sweep, which can only raise it. Build last;
  expect to defend it or delete it.
* Do **not** also build `avolume`: ρ 1.000000, ratio constant.

### 3. `MarketFacilitationIndex` — range per unit volume

* **Question.** How much price movement does each unit of volume buy — price impact /
  liquidity efficiency. `eom` is the nearest shipped idea but is *directional* and `PX2`,
  i.e. not a feature as shipped (ρ −0.071). `cmf` 0.022, `pvr` 0.265.
* **Form.** Raw `(H−L)/volume` is neither price- nor volume-scale-free. Ship the double
  ratio `MFI_BW_{length} = ((high − low)/close) / (volume / SMA(volume, length))` — range
  as a percent of price, per unit of *relative* volume. ×8 Δ 0 unrounded. This is exactly
  the pre-engineered relation the `mlf-feature-ml-format` finding asks for: a tree cannot
  form `a/b` on its own.
* **Gate E risk.** Moderate; max measured 0.490 (`NATR_14`) — the numerator is a range.
  Untested and worth checking: `pocket_pivot`'s `PPIVOT_VOLRATIO`, which shares the
  denominator.

### 4. `ProjectionBands` — slope-corrected Donchian

* **Question.** Where are the highest high and lowest low *once the trend is removed*?
* **Form.** The bands are `PX` and must not ship as levels — `pandas_ta/trend/pivot.py` is
  the reference. Ship `PB_UP_DIST_PCT`, `PB_LO_DIST_PCT`, `PB_WIDTH_PCT`. ⚠ ×8 Δ 0 unrounded is measured on TWO of the three (`pb_width_pct`, `pb_up_dist_pct`); `pb_lo_dist_pct` is in no script's FORMS, so its invariance is INFERRED from the identical construction, not run. All ×8 Δ 0
  unrounded. Do not carry tti's `.round(4)` into the port.
* **Gate E risk.** `PB_WIDTH_PCT` 0.855 against a donchian-width-percent construction the
  engine does not currently compute; the distance columns are cleaner (0.473).
  Cost note, not a gate: tti's implementation is a per-bar Python loop over `statsmodels`
  `RollingOLS`. It vectorises to a rolling polyfit slope plus one `max` over n shifted
  arrays — do that, or this indicator alone will dominate an engine run.

### 5. `ProjectionOscillator` — position within the corrected range

* **Question.** Where does close sit inside the *trend-corrected* range? `willr` and
  `stoch` answer it on the uncorrected range; 0.422 / 0.202 says the correction matters.
* **Form.** `POSC_{length}` is a 0–100 position; **1.4480%** of 51,866 bars fall outside
  [0,100] where close exceeds a projected extreme — keep those, do not clamp, they are the
  informative bars. ×8 Δ 0 unrounded. Name it `POSC_*`, never `PO_*`. The 3-bar EMA trigger
  is a chart artefact — omit it, or ship `posc − trigger`, not both.
* **Gate E risk.** Low–moderate against `willr`/`stoch`; the untested one is against
  `PB_LO_DIST_PCT` from row 6, which shares the lower band. Build both in one module and
  measure them against each other before shipping both.

### 6. `WilliamsAccumulationDistribution` — directional true-range capture

* **Question.** On an up bar, how much of the true range did the close capture measured
  from the *lower* of yesterday's close and today's low (mirrored on a down bar)? The
  direction gate and the prior-close reference are the novelty: `ad`'s multiplier is
  undirected and ignores the gap (0.025), `bop` uses the open instead (0.698).
* **Form.** tti returns a price. Ship `wad_bar_sf = wad_bar / true_range` (named `wad_bar_sf` throughout — naming is API), bounded ≈ [−1, 1]
  (measured max |x| 1.0). ×8 Δ 1.2e-13 unrounded. If the cumulative line is wanted (the
  real Williams AD is a running sum) it must ship as a normalised slope or a z-score, never
  as a raw cumsum.
* **Gate E risk.** 0.698 against `BOP` is the number to beat — under 0.76 but not
  comfortably. Test against `bop`, `rvgi`, `cdl_z`'s close column, `tri_dir_pressure`.

### 7. `smc_sweep` — wick rejection at a rolling extreme *(reversed from round 1)*

* **Why it reversed.** Round 1 skipped it as "the identical event" to the shipped
  `liquidity_sweep` and named ±1-bar event coincidence as the correct metric without
  running it. Run on the same 52,022 bars: **14.9% and 15.0%.** The two detectors fire on
  nearly disjoint bars, so the stated reason is refuted by its own test.
* **Question.** `liquidity_sweep` sweeps *confirmed pivots* from a level pool with an ATR
  tolerance and an explicit reclaim leg. `smc_sweep` fires on a rolling n-bar extreme with
  a wick-rejection filter — nearer "a hammer at a 20-bar low" than a pool sweep.
* **Form.** Already `BIN`/`ORD` (±1). Causal.
* **Gate E risk / the honest caveat.** This is the weakest of the seven. The *concept* is
  still shared with a shipped indicator, and Spearman is the wrong instrument for two
  sparse flags (895 and 881 events in 52,022 bars, ~1.7%), so neither the low coincidence
  nor a low ρ would settle it. The question ALTPORT-1 has to answer is whether two sparse
  detectors of the same concept earn two slots — and the case for building is that the
  measurement shows the shipped one does not cover these bars.

## The thirteen SKIPs, grouped by why

**Over the 0.9 revert line against a shipped column (5).** `fosc` 0.967784 vs `CFO_14`;
`RelativeMomentumIndex` 0.929918 vs `RSI_14`; `ce` 0.923196 vs `cksp`;
`VolatilityChaikins` 0.999955 vs `cvi` (same batch); `Envelopes` 0.999998 vs `bias`.

**Reconstructible from shipped columns (3).** `dx` = `100·|DMP−DMN|/(DMP+DMN)`;
`adxr` = a lag average of `ADX_14`; `avolume` = `hvol` × √(19/20)/100.

**Same economic question, different construction (2).** `vosc` vs `pvo` (0.753468, a
judgement call, disclosed); `msw` vs `ht_sine` (plus a measured Gate D failure).

**Fails the feature contract (3).** `RangeIndicator` — not scale-invariant at either
parameterisation, unrounded. `SwingIndex` — not scale-invariant as written, and the repair
is 0.794 vs `BOP`. `mavp` — a price level needing a second input series the engine lacks.

## Where the algebra rule stands after round 2

Round 1's general rule — *algebra can decide where correlation cannot* — is right, and
`dx` is still its best example: ρ 0.577 against `ADX_14`, yet reconstructible from two
shipped columns in one line. But round 1 then broke the rule three times by "verifying"
algebra against a fork transcription of the upstream function. The corrected statement:

> The algebra holds for the **fork's own** smoothing. Any `dx` this fork ships is exactly
> `100·|DMP_14 − DMN_14|/(DMP_14 + DMN_14)`, and that is what makes it redundant *here*.
> Agreement with the **upstream** `pandas_ta_classic.dx` is a separate question — it is a
> Gate A question — and it is **not** established: the measured gap is 24.931 over 7.44% of
> bars, from Wilder-smoothing seed differences. The same distinction applies to `fosc`
> (a genuinely different forecast point) and `VolatilityChaikins` (a warm-up transient — measured: the max occurs in rows 0-10 on all 12 frames and max|d| after row 100 is 4.99e-05 to 5.00e-05, i.e. the `.round(4)` floor — plus
> `.round(4)`).

Only two round-1 identity claims survive untouched, and both were verified against upstream
in round 2: `avolume` ↔ `hvol` and `Envelopes` ↔ `bias`.

## What I could not determine

1. **Whether any BUILD clears Gate E.** Every ρ here is against hand-picked near
   neighbours, not the engine's full production column set. The four I would not bet on:
   `hvol` 0.821076 vs `NATR_14`, `PB_WIDTH_PCT` 0.832368 vs the engine's real `dist_low_n - dist_from_high_n`, `wad_bar_sf`
   0.697630 vs `BOP`, `swi_sf_direct` 0.775144 (already a SKIP).
   ⚠ The round-2 figure 0.794215 was measured on `swi_sf_derived` = `swi/(K/3)` — tti's
   already-clamped, already-rounded output divided back out — NOT on `50·num/R`. Two
   different series carried one variable name across the two scripts; pooled
   max |direct − derived| = **53.23**. Both sit in the 0.76–0.80 band, so the SKIP is
   unmoved, but the number was attributed to a formula it was not computed from.
2. **Gate A for every candidate.** The scripts call upstream, so the ρ values are sound,
   but nothing here checks a port against upstream line by line. Three seeding/rounding
   divergences are already documented (`dx` Wilder seed, `cvi`↔`vch` EMA seed + `.round(4)`,
   `fosc` linreg x-origin) and there will be more.
3. **`ProjectionBands` cost and numerical agreement.** The vectorised form recommended
   above is what `scalecheck_altport0.py`'s unrounded probe computes, and it is *not*
   diffed against tti's `RollingOLS` output. tti also `fillna(0)`s the input before
   fitting, which differs at the head of a series. Gate A must settle it.
4. **Whether `msw` and `RangeIndicator` carry information or noise.** Both are
   near-orthogonal to everything tested (|ρ| ≤ 0.26 and ≤ 0.047). I measured *overlap*,
   never *informativeness*. Their SKIPs rest on the question being shipped (`msw`) and on a
   contract failure (`RangeIndicator`), not on the low ρ.
5. **`mavp` carries no measurement of my own.** It rests on the scanners' `t3_tv` 0.9886
   and on two contract facts (price level, second input series). It is one of two rows
   with no ρ from this run — the other, `smc_sweep`, now has a coincidence number.
6. **`smc_sweep` is the least secure verdict in the file**, in either direction. 14.9%
   coincidence refutes "the same bars"; it does not establish "a different question", and
   no statistic on two ~1.7%-density flags will.
7. **Sample breadth.** 12 BIST tickers, 52,022 daily bars, one market, one timeframe. No
   US data, no hourly.
