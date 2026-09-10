# ALTPORT-1 — Gate E screen of the seven ALTPORT-0 BUILDs, before anything is written

**Under the Gate E band: 1 STRUCK · 4 ship-with-disclosure · 4 ship.**
**Under ALTPORT-0's own applied standard, which this batch is bound by: 3 clear, 2
conditional, 3 skipped, 1 struck.** The two standards disagree, the disagreement is the
main finding of round 3, and **it must be settled before ALTPORT-2 starts** — see
*The standards clash*.

`C_POSC_14` is struck either way: pooled |ρ| **0.894742** against `cfo`, per-frame
**median 0.9102 with |ρ| ≥ 0.90 on 62.9% of 89 frames**.

`TODO.md` ALTPORT-1 inverts the usual order deliberately: *screen every BUILD against the
production set BEFORE writing it.* The 2026-09-08 batch built ~35 columns and deleted 12
on redundancy against columns the engine already ships. This document is the measurement
that comes first. **Nothing has been written into `pandas_ta/` — that is ALTPORT-2, and
only for survivors.**

Harness: `../Backtesting/scripts/analysis/measure_altport1_overlap_full.py` (8 stages).
CSVs: `../Backtesting/backtest_results/altport1/`.

> **Round history, because two of the three rounds changed the verdict and none changed
> the arithmetic.** Round 1 reported a pooled max only, resolved the 0.80–0.90 range into
> the most permissive rung, and shipped 0.894742 as a disclosure. Round 2 added the
> per-frame leg and struck POSC — but did so with `REVERT_APPROX = 0.89`, a constant
> chosen after seeing the nine numbers, and **never re-ran stage 2**, so the published CSV
> carried round 1's verdict for a whole review round while stages 6 and 7 consumed it.
> Round 3 deletes the fitted constant, resolves the range on the per-frame leg at the same
> 0.90 the band already names, regenerates every artifact, and adds a schema stamp that
> makes the staleness an error instead of a silence.

---

## The comparator surface

| quantity | value |
|---|---|
| engine columns swept (`IndicatorEngine(include_advanced=True).compute_all`) | **492** |
| `n_numeric` / `n_bool` / `n_ordered` | 485 / 1 / 6 |
| **`n_unmapped`** (columns with no declared scale) | **0** — `unmapped_columns` `[]` |
| **`n_unmapped_values`** (levels a declared ladder omits) | **0** — `unmapped_values` `{}` |
| extra named comparators NOT emitted by `compute_all` | 4 (`X_` prefixed) |
| **total comparators per candidate** | **496** |
| frames / pooled bars | **89** BIST_100 daily / **408,253** |
| degenerate cells (n < 100 or a constant side) | 18 of 4,464 |

Both zeros are per-frame across all 89 rows of `_work/_comparator_report.csv`.
**Both are now enforced in stage 2**, which is where verdicts are actually taken: round 2
put the guard only in stage 1, which skips every ticker whose parquet is already cached —
so on a warm 89-frame cache it loaded nothing and the guard could not fire at all.

⚠ **`TVPTA-9` remains OPEN.** This run fixed **one** harness. The other ~14
`measure_*_overlap_full.py` scripts still call `select_dtypes(include=[np.number])`, so
every verdict they produced is still a 485-comparator number. Read this section as
"ALTPORT-1 is clean", never as "the repo-wide blind spot is closed".

The four `X_` comparators, flagged because they are **not** `compute_all` columns:

| column | what it is |
|---|---|
| `X_rel_vol_20` | `IndicatorEngine.compute_relative_features(df, XU100_IS)['rel_vol_20']` — the **production static method** (`indicator_engine.py:436`). Needs an INDEX frame, so `compute_all` never emits it. |
| `X_close_roll20_std` | `close.rolling(20).std()`, the divisor inside `ZSCORE_20` at `:1060`. Price-scaled; ships nowhere. |
| `X_eng_width_20`, `X_eng_pos_20` | `dist_low_20 − dist_from_high_20` and its implied position |

Every candidate's max is reported both over all 496 and over the 492 `compute_all` columns
alone. **They coincide for all nine columns.**

---

## The band, and how the 0.80–0.90 range is resolved

`../PandasTa/CLAUDE.md:98`: *ρ ≈ 0.9 → revert; 0.76–0.80 → ship with disclosure; below
0.76 → ship.* **0.80–0.90 is undescribed.**

Round 2 resolved it with `REVERT_APPROX = 0.89`. That constant was never derived. It sat
0.0006 above the second-highest candidate (0.889416) and 0.0053 below the highest
(0.894742) — the one value in the neighbourhood that struck exactly one column, chosen
after the nine numbers were on the table. **Round 3 deletes it.** No new threshold is
invented; the gap is resolved on the estimator this document already argues for:

```
STRUCK    pooled |rho| >= 0.90  OR  per-frame MEDIAN |rho| >= 0.90
DISCLOSE  0.76 <= pooled < 0.90   (0.76-0.80 = the written rung;
                                   0.80-0.90 = labelled DISCLOSE_GAP, never hidden)
SHIP      pooled < 0.76
```

Two facts make this the strict reading rather than a convenient one. Pooling frames of
different price levels **depresses** ρ here — POSC is 0.9102 per-frame and 0.8947 pooled —
so a pooled-only rule is the *friendlier* one. And the per-frame leg is the estimator the
repo's own **SEMANTIC-DUPLICATE LAW** uses: it deleted `dist_to_bb_upper_pct` on a
per-frame distribution, and recorded that the check which had *cleared* that column sat at
0.879 with 29.2% of frames above 0.9 — *"it was never clear"*.

`altport1_overlap_max.csv` carries `verdict`, `verdict_pooled_only` and
`verdict_permissive_ge090` side by side, plus `verdict_schema`, so the effect of the
choice is three columns rather than an argument.

**Correction to round 2's precedent citation.** Round 2 cited `fosc` at 0.950818. That is
a *probe-frame* figure; the actual SKIP rests on `AltportTriage.md` row 10 at **ρ 0.967784
vs `CFO_14`** over 51,866 bars. So the precedent struck a column clearing even the
permissive 0.90 line by 0.068 — **it corroborates the mechanism** (a linear-regression
forecast residual measured against `cfo`) **and says nothing about where the threshold
sits.** POSC's threshold case rests on the per-frame leg alone, which is sufficient.

**Proposed replacement for `CLAUDE.md:98`** — owner's call, *not applied*:

> **E Attribution.** Spearman ρ against the entire shipped column set of the production
> config, non-numeric comparators coerced through declared ordered scales. Report the
> **pooled max with its sample size AND the per-frame distribution** (`n_frames`,
> `median_abs_rho`, `pct_frames_ge_090`).
> **|ρ| ≥ 0.85 → revert; 0.76–0.85 → ship with disclosure; < 0.76 → ship.**
> A column with `pct_frames_ge_090` ≥ 25% is reverted regardless of the pooled figure.

⚠ **That 25% clause is calibrated on ONE datapoint** — `FINDINGS.md`'s 0.879 / 29.2% case
— and it is in tension with its own source: it clears `C_WAD_BAR_SF` at 12.4% whose
pooled 0.889416 is *above* the 0.879 that precedent calls "never clear". **Mark it
provisional** pending a second datapoint, or derive it from the distribution across
columns the repo has already deleted versus kept.

---

## The table

Pooled max over 496 comparators; per-frame leg over the same 89 frames. Regenerated
2026-09-10 under `verdict_schema = r3-perframe-0.90`.

| BUILD | column | pooled max \|ρ\| | against | n | per-frame median | ≥0.90 on | **verdict** |
|---|---|---|---|---|---|---|---|
| `ProjectionOscillator` | `C_POSC_14` | **0.894742** | `cfo` | 406,760 | **0.910212** | **62.9%** | **STRUCK** |
| `WilliamsAccumulationDistribution` | `C_WAD_BAR_SF` | 0.889416 | `percent_return` | 397,219 | 0.889192 | 12.4% | DISCLOSE_GAP |
| `ProjectionBands` | `C_PB_WIDTH_PCT` | 0.874411 | `natr` | 407,096 | 0.864806 | 1.1% | DISCLOSE_GAP |
| `hvol` | `C_HVOL_20` | 0.834724 | `natr` | 406,473 | 0.831216 | 4.5% | DISCLOSE_GAP |
| `ProjectionBands` | `C_PB_UP_DIST_PCT` | 0.773573 | `dist_from_high_5` | 407,096 | 0.764326 | 0.0% | DISCLOSE |
| `ProjectionBands` | `C_PB_LO_DIST_PCT` | 0.727354 | `cfo` | 407,096 | 0.752230 | 0.0% | SHIP |
| `MarketFacilitationIndex` | `C_MFI_BW_SF_20` | 0.536816 | `vol_at_low_ratio` | 394,399 | 0.537448 | 0.0% | SHIP |
| `cvi` | `C_CVI_10` | 0.501290 | `CHOP` | 405,514 | 0.499606 | 0.0% | SHIP |
| `smc_sweep` | `C_SMC_SWEEP` | 0.161383 | `CCI` | 406,562 | 0.166059 | 0.0% | SHIP |

**1 STRUCK · 4 ship-with-disclosure · 4 ship.** The disclosure count splits into the
**written 0.76–0.80 rung: 1** (`C_PB_UP_DIST_PCT` at 0.773573) and the **undescribed
0.80–0.89 range: 3** (`C_WAD_BAR_SF`, `C_PB_WIDTH_PCT`, `C_HVOL_20`).

⚠ Round 2 headlined "5 ship" by counting `C_PB_UP_DIST_PCT` as a ship while its own text
called it *"BUILD with disclosure"* and `_verdict` returned `DISCLOSE` for it. That was
round 1's defect — a headline the code contradicted — reproduced in the other direction.
0.76–0.80 is *ship with disclosure* by the band's own wording, and it is counted as a
disclosure here.

The full grid is `altport1_overlap_max.csv`; the per-frame table (top-5 comparators per
candidate) is `altport1_perframe.csv`; top-25 comparators per column is
`altport1_overlap_top25.csv`.

### Per-frame detail for the four columns it matters for

| pair | n_frames | median | mean | max | min | ≥0.90 | ≥0.80 |
|---|---|---|---|---|---|---|---|
| **`C_POSC_14` × `cfo`** | 89 | **0.910212** | 0.901983 | 0.937402 | 0.721263 | **62.9%** | 98.9% |
| `C_WAD_BAR_SF` × `percent_return` | 89 | 0.889192 | 0.889346 | 0.911075 | 0.869207 | 12.4% | 100.0% |
| `C_PB_WIDTH_PCT` × `natr` | 89 | 0.864806 | 0.861677 | 0.901611 | 0.772068 | 1.1% | 97.8% |
| `C_HVOL_20` × `natr` | 89 | 0.831216 | 0.828936 | 0.910479 | 0.606570 | 4.5% | 82.0% |

56 of 89 frames put `C_POSC_14` × `cfo` at or above 0.90 individually. The mechanism is
worth naming — `cfo` is `100·(close − linreg-forecast)/close`, `ProjectionOscillator` is
the position of close inside bands built from rolling OLS slopes of high and low, so both
are "how far is close from where the regression says it should be", and `cfo` is one of
the two columns the Indicator Book records as carrying the entire deployed hourly book —
but the number decides it.

---

## The standards clash — and what ALTPORT-2 should actually receive

**This is the finding that gates ALTPORT-2.** The two halves of this chain apply different
laws to the same question, and the looser one is the half that ships.

**ALTPORT-0's applied standard was question-redundancy, not correlation.** Two rows prove
it, and both are in `AltportTriage.md`:

* **`vosc` SKIP at ρ 0.753468** vs `PVO_12_26_9` — *"Same question as the shipped `pvo`…
  differing only in `mamode`. A question-redundancy skip… 0.7535 sits just **under** the
  0.76 ship line, so a correlation-only gate would have passed it."*
* **`msw` SKIP at ρ 0.032** vs `HT_SINE` — *"Low ρ says the estimator **disagrees**, not
  that the question is new."*

ALTPORT-1 then proposes to ship `C_PB_WIDTH_PCT` at **0.874** while describing it in its
own words as *a range-width restating a range-width*, and `C_HVOL_20` at **0.835** while
noting it sits in a dense shipped width lane. **Under the standard ALTPORT-0 actually
applied, those are SKIPs at roughly a third of the correlation.** "Owner call" is not a
resolution when the same document set already resolved the identical question twice, both
times against the candidate.

Applying ALTPORT-0's test explicitly, in writing, to every non-struck column:

| column | its economic question | already shipped? | ALTPORT-0 standard |
|---|---|---|---|
| `C_CVI_10` | is the trading range *expanding or contracting*, and by how much | No. `natr` gives the level, `chop` trending-vs-ranging, `massi` a ratio of range smoothings. No shipped column is a rate of change of range (verified: no `natr`-ROC column exists in the 492). | **CLEAR** |
| `C_MFI_BW_SF_20` | how much range does a unit of volume buy — price impact / liquidity | No. `eom` is directional and not shipped as a feature; `CMF` −0.043; `PPIVOT_VOLRATIO_10_10` −0.163. | **CLEAR** |
| `C_SMC_SWEEP` | was a rolling extreme taken out and rejected on a wick | Concept shared with `liquidity_sweep` — but ALTPORT-0 itself reversed this row to BUILD on measured evidence that the shipped detector does not cover these bars, now with a null (1.89× chance, z 27.4). | **CLEAR**, on ALTPORT-0's own reasoning |
| `C_PB_LO_DIST_PCT` | how far is close above the *trend-corrected* floor | "Distance above the recent floor" ships six times (`dist_low_{5,20,21,60,63,252}`). The slope correction is the claimed novelty. | **CONDITIONAL** |
| `C_PB_UP_DIST_PCT` | how far is close below the *trend-corrected* ceiling | Same, mirrored: `dist_from_high_{5,20,21,60,63,252}`. | **CONDITIONAL** |
| `C_HVOL_20` | how volatile is this stock | Yes — `natr`. The differentiator is the *estimator* (gap-inclusive c2c log returns vs intraday true range), which is the `msw` shape, not a new question. | **SKIP** |
| `C_PB_WIDTH_PCT` | how wide is the recent range as a % of price | Yes — `natr` is exactly that. | **SKIP** |
| `C_WAD_BAR_SF` | which way and how hard did price move, scaled by its range | Yes — the signed daily return (`percent_return`), at 0.889. | **SKIP** |

**I dispute the reviewer's survivor count of 4, with evidence.** That list keeps
`C_PB_LO_DIST_PCT` and drops `C_PB_UP_DIST_PCT`, and the only thing separating them is
0.046 of ρ (0.727354 vs 0.773573, either side of vosc's 0.753468). But they are **the same
construction mirrored** — the upper and lower band of one indicator, both slope-corrected,
both against the same twelve-member Donchian grid. Splitting them on a correlation
threshold *is a correlation gate*, which is the very mixing of standards being objected
to. On a question test the two coherent answers are:

* the slope correction **is** a new question → **both** survive → clear set = **5**
* the slope correction **is not** → **neither** → clear set = **3**

**Recommended hand-off to ALTPORT-2, stated as a decision rather than a default:**

| tier | columns | basis |
|---|---|---|
| **Ship (3)** | `C_CVI_10`, `C_MFI_BW_SF_20`, `C_SMC_SWEEP` | clear on BOTH standards |
| **Conditional (2)** | `C_PB_UP_DIST_PCT`, `C_PB_LO_DIST_PCT` | together or not at all, on one ruling: *is a slope-corrected extreme a different question from a raw one?* ALTPORT-0 argued yes (measured: 0.42 against `willr`); the Donchian grid does not strike either (worst cells 0.774 / 0.717) |
| **Skip (3)** | `C_HVOL_20`, `C_PB_WIDTH_PCT`, `C_WAD_BAR_SF` | question already shipped. Available as ship-with-disclosure under the Gate E band alone — that is the choice being made, and it should be made explicitly |
| **Struck (1)** | `C_POSC_14` | 0.894742 pooled, 0.910212 per-frame, 62.9% of frames ≥ 0.90 |

**The alternative — "a screen taken after triage may use a looser rule than the triage" —
is defensible but must be stated, not assumed.** The argument for it: ALTPORT-0's
question test is a *cheap prior* used to decide what is worth measuring, and ALTPORT-1's
correlation is the *measurement*; a measurement that comes back at 0.835 rather than 0.95
is evidence the prior was too harsh. The argument against: `vosc` was skipped at 0.753 on
exactly that prior after being measured, so the batch has already declined to make that
move once. **I recommend the strict reading** — the precedent is inside the same batch,
and the asymmetry favours it (a column wrongly skipped costs one re-measurement; a column
wrongly shipped double-weights a signal in every future mining run).

---

## Provenance — which candidate has an upstream oracle, and which does not

Round 1 claimed *"the single piece of local arithmetic is the true range"*. **False**, and
false in exactly the class the ML feature contract polices. Round 2 fixed it in this
document and **left the same false sentence in the harness docstring**; round 3 fixed both.
The exact split:

| candidate | provenance | check |
|---|---|---|
| `C_CVI_10` | pure upstream `tac.cvi(h, l, 10)` | the call is the value |
| `C_HVOL_20` | pure upstream `tac.hvol(c, 20)` | " |
| `C_SMC_SWEEP` | pure upstream `tac.smc_sweep(o, h, l, c)` | " |
| `C_POSC_14` | upstream read-through of tti `posc` | " |
| `C_PB_WIDTH_PCT` / `C_PB_UP_DIST_PCT` / `C_PB_LO_DIST_PCT` | **local** percent forms of tti's upstream `upper_band`/`lower_band` | the bands are upstream; the `/close·100` is local |
| `C_WAD_BAR_SF` | **local**: upstream `wad` ÷ a locally computed true range | TR diffed vs `pandas_ta.true_range`: **max \|d\| = 4.44089e-16** over 89 frames |
| `C_MFI_BW_SF_20` | **local construction around a DECORATIVE upstream call** | see below |

**`C_MFI_BW_SF_20` had no oracle at all until round 2.** tti returns `mfi = (h−l)/volume`
and the shipped form multiplies volume straight back out —
`((h−l)/close) / (volume / SMA(volume, 20))` — so the only upstream contribution is
`(h−l)`, available from raw OHLC, and tti computes nothing this form uses. Its check, run:
**tti `mfi` vs a local `(h−l)/volume` — max |d| = 4.99908e-11 over 5,564 AEFES bars**
(the `.round(10)` half-ulp floor, 455 distinct values). The upstream call is confirmed
decorative. **Its Gate A in ALTPORT-2 must go to Bill Williams' definition directly, not
to tti.**

---

## Gate D — run, not inferred, and 6 of 9 fail

Round 1 carried `PB_LO_DIST_PCT`'s scale invariance forward as *inferred from
`PB_UP_DIST_PCT`'s construction*. Inferring a gate is not running it, and the inference
was drawn from a path that itself fails. AEFES.IS, 5,695 bars, O/H/L/C × 8 and × 64,
against `TODO.md` ALTPORT-2's requirement of **bit-identical (`== 0.0`, not a tolerance)**
— `altport1_gate_d.csv`:

| column | max \|Δ\| ×8 | max \|Δ\| ×64 | bit-identical | NaN masks match |
|---|---|---|---|---|
| `C_CVI_10` | 0.000000 | 0.000000 | **yes** | yes |
| `C_HVOL_20` | 0.000000 | 0.000000 | **yes** | yes |
| `C_SMC_SWEEP` | 0.000000 | 0.000000 | **yes** | yes |
| `C_MFI_BW_SF_20` | 0.004193 | 0.003931 | no | yes |
| `C_WAD_BAR_SF` | 0.020113 | 0.019275 | no | yes |
| `C_PB_UP_DIST_PCT` | 0.031702 | 0.029420 | no | yes |
| `C_PB_LO_DIST_PCT` | **0.033587** | **0.033587** | no | yes |
| `C_PB_WIDTH_PCT` | 0.058776 | 0.051429 | no | yes |
| `C_POSC_14` | 0.480700 | 0.450700 | no | yes |

NaN masks match on all eighteen cells. **The failures are tti's fixed-decimal rounding,
not the mathematics** — ALTPORT-0's `scalecheck_altport0.py` showed the same forms are
exactly invariant once rounding is removed. But that is a statement about a form a port
would ship, not about what was screened, so **Gate D must be re-run bit-identical against
the ported fork implementation in ALTPORT-2, for every survivor.** No inferred Gate D
leaves this document.

## tti quantisation — the corollary, measured

Round 1 argued rounding *"can only add ties, biasing Spearman toward zero, so a high ρ is
conservative"* and never stated the other half: **a low ρ on quantised output is
ANTI-conservative**, and the tti-derived columns include ships. Measured by recomputing
the candidates on prices × 1e5 (dropping the fixed-decimal floor five decades) against the
same unscaled engine comparators. Pooled, 89 frames (`altport1_quantisation_pooled.csv`):

| column | against | ρ ×1 | ρ ×1e5 | Δ | verdict flips |
|---|---|---|---|---|---|
| **`C_MFI_BW_SF_20`** | `vol_at_low_ratio` | **−0.536816** | **−0.573380** | **−0.0365645** | no |
| `C_SMC_SWEEP` | `CCI` | −0.161383 | −0.160772 | +6.11e-04 | no |
| `C_PB_WIDTH_PCT` | `natr` | 0.874411 | 0.874498 | +8.74e-05 | no |
| `C_PB_LO_DIST_PCT` | `cfo` | 0.727354 | 0.727437 | +8.34e-05 | no |
| `C_POSC_14` | `cfo` | 0.894742 | 0.894812 | +6.91e-05 | no |
| `C_WAD_BAR_SF` | `percent_return` | 0.889416 | 0.889366 | −4.97e-05 | no |
| `C_PB_UP_DIST_PCT` | `dist_from_high_5` | −0.773573 | −0.773618 | −4.56e-05 | no |
| `C_HVOL_20` | `natr` | 0.834724 | 0.834724 | −4.81e-10 | no |
| `C_CVI_10` | `CHOP` | −0.501290 | −0.501290 | +1.81e-09 | no |

**max |Δ| = 0.0365645, 0 verdicts flip.** The `C_MFI_BW_SF_20` move is real and makes that
ship less clean than round 1 stated (0.537 → 0.573).

⚠ **A single frame hides this.** On AEFES alone the same test gives −0.603294 → −0.603253,
Δ = 4.1e-05 (`altport1_quantisation.csv`). It is a **pooling** effect: `.round(10)` is a
*fixed-decimal* floor, so it bites differently on a 5 TL stock than a 500 TL one, and that
frame-dependent distortion only appears once frames share a rank ordering. Both tables are
kept for that reason.

---

## The named adversaries

`altport1_named_adversaries.csv`.

### `hvol` — the predicted adversary is not the adversary

| against | ρ | n |
|---|---|---|
| **`X_rel_vol_20`** (`indicator_engine.py:436`, production method) | **0.452296** | 406,473 |
| `X_close_roll20_std` (`ZSCORE_20`'s divisor, `:1060`) | 0.288544 | 406,473 |
| `ZSCORE_20` (the shipped column) | −0.021156 | 406,160 |
| `natr` | **0.834724** | 406,473 |
| `natr_percentile` | 0.536691 | 401,845 |
| `ATR` | 0.248152 | 406,473 |

The per-date index-volatility denominator decorrelates `rel_vol_20` far more than "the same
numerator" suggests, and `ZSCORE_20` is orthogonal because it is a *position*, not a width.
The real adversary is `natr`, which rose 0.821076 (12 frames, ALTPORT-0) → **0.834724**
(89 frames) — the full sweep moved it up, as ALTPORT-0 predicted it could. Second and third
are `X_eng_width_20` 0.788564 and `BB_BWidth` 0.714719: a dense shipped width lane.

### `ProjectionBands` / `ProjectionOscillator` × the twelve-member Donchian grid

| column | worst Donchian-grid \|ρ\| | against |
|---|---|---|
| `C_PB_UP_DIST_PCT` | **0.773573** | `dist_from_high_5` |
| `C_PB_LO_DIST_PCT` | 0.716610 | `dist_low_5` |
| `C_POSC_14` | 0.641116 | `dist_from_high_5` |
| `C_PB_WIDTH_PCT` | 0.445632 | `dist_from_high_20` |

Plus `C_PB_WIDTH_PCT` × `X_eng_width_20` 0.766860. **The Donchian grid strikes nothing** —
the BB-deletion precedent at 0.9429/0.9379 is not reproduced, and the grid's long windows
(60/63/252) are near orthogonal to a 14-bar projection. The columns that bite are `natr`
and `cfo`, neither of which was the predicted adversary.

### `smc_sweep` — event test with a chance baseline

"79% disjoint" was meaningless on its own: the mask is a ±1-bar **dilation** of 15,830
events over 408,253 bars, covering roughly 3× its own event count, so a double-digit
overlap is expected from nothing at all. Null: **200 per-frame circular shifts, seed
20260910**, preserving each frame's event count, clustering and autocorrelation and
destroying only the alignment (`altport1_smc_event_coincidence.csv`):

| LSH flag | LSH events | observed | null ± sd | p95 | enrichment | z |
|---|---|---|---|---|---|---|
| **ANY of the four** | 15,830 | **20.96%** | **11.09 ± 0.36** | 11.68 | **1.89×** | 27.4 |
| `LSH_SWEEP_BEAR_10` | 4,073 | 9.21% | 2.90 ± 0.22 | 3.24 | 3.17× | 28.7 |
| `LSH_SWEEP_BULL_10` | 2,932 | 5.36% | 2.07 ± 0.17 | 2.33 | 2.58× | 19.1 |
| `LSH_RECLAIM_BULL_10` | 4,296 | 3.83% | 3.12 ± 0.21 | 3.43 | **1.23×** | 3.4 |
| `LSH_RECLAIM_BEAR_10` | 4,689 | 3.86% | 3.41 ± 0.22 | 3.77 | **1.13×** | 2.0 |

The correct statement is **"1.89× chance, not 79% disjoint"**. The per-flag rows carry a
nuance the pooled row hides: the two *sweep* flags are 2.6–3.2× enriched, the two *reclaim*
flags barely distinguishable from chance. The shared concept is the sweep leg.

⚠ **1.89× is an UPPER BOUND on the bar-level alignment component.** A circular shift
destroys shared *time-varying density* as well as alignment — both detectors fire more
often in volatile periods — so the enrichment bundles regime co-occurrence with genuine
bar-level agreement. A block bootstrap preserving local density would give a tighter null
and a smaller enrichment; it was not run.

Density and sign: 6,474 events on 408,253 bars (**1.586%**), signed **2,335 `+1` / 4,139
`−1`**. The signing defuses the CANDLE-1 tied-zero trap; measured rank correlations against
the LSH lane are correspondingly tiny (max 0.078). ρ stays secondary.

### `C_WAD_BAR_SF`'s comparator lane is ONE comparator, measured

Round 1 called `percent_return`, `VELOCITY`, `log_return`, `increasing` and `decreasing` a
*"four-column lane"* and leaned on its width. Round 2 corrected that in prose but quoted
one of the three supporting numbers from a single frame and got it wrong by four orders of
magnitude in the residual. It is now a stage, pooled over 89 frames
(`altport1_wad_lane.csv`, n = 408,164):

| column | Spearman vs `percent_return` | max \|d\| vs `percent_return` | identical | ρ vs `C_WAD_BAR_SF` |
|---|---|---|---|---|
| `percent_return` | 1.000000 | 0.000000 | — | 0.889416 |
| `VELOCITY` | **1.000000** | **0.000000** | **yes — bit-identical** | 0.889416 |
| `log_return` | **0.999990** | 0.005931 | no; `max\|log_return − log1p(percent_return)\|` = **7.72e-09** | 0.889370 |
| `increasing` | 0.861849 | 1.000000 | no (0/1 sign) | 0.863458 |
| `decreasing` | −0.859545 | 1.104999 | no (0/1 sign) | −0.861550 |

⚠ **Round 2 reported Spearman(`percent_return`, `log_return`) as 0.9999999999.** That was
AEFES alone; **pooled it is 0.999990** — the reviewer's figure, not mine. Corrected.

So the lane is **one independent comparator (the signed daily return) at 0.889416, plus its
sign indicators at 0.863 / −0.862**. `log_return` is a strictly monotone transform and
cannot corroborate. The deletion case for WAD rests on that one number plus the mechanism —
on an up bar, `close − min(prev close, low)` over the true range is "today's move as a
fraction of today's range" — never on a lane count.

### `MarketFacilitationIndex` and `cvi`

| column | against | ρ | n |
|---|---|---|---|
| `C_MFI_BW_SF_20` | `vol_at_low_ratio` / `VOL_RATIO` | −0.536816 | 394,399 |
| | `natr` | 0.508009 | 394,399 |
| | `PPIVOT_VOLRATIO_10_10` (ALTPORT-0's untested risk) | **−0.162534** | 325,287 |
| | `CMF` | −0.042926 | 394,399 |
| `C_CVI_10` | `CHOP` | −0.501290 | 405,514 |
| | `massi` | 0.305523 | 405,405 |
| | `natr` | 0.242417 | 406,562 |

---

## Candidate × candidate

`altport1_sibling_overlap.csv`. Nothing reaches the line:

| pair | ρ |
|---|---|
| `C_PB_LO_DIST_PCT` × `C_POSC_14` | 0.792959 |
| `C_PB_UP_DIST_PCT` × `C_POSC_14` | −0.783387 |
| `C_HVOL_20` × `C_PB_WIDTH_PCT` | 0.764389 |
| `C_PB_WIDTH_PCT` × `C_PB_UP_DIST_PCT` | 0.577829 |
| `C_POSC_14` × `C_WAD_BAR_SF` | 0.531616 |
| every other pair | < 0.53 |

With `C_POSC_14` struck, the `PB` distance columns lose their nearest sibling.

## Reachability

89 of 89 frames fire every column. Pooled non-NaN / non-zero of 408,253 bars:

| column | non-NaN | non-zero |
|---|---|---|
| `C_CVI_10` | 406,562 | 406,562 |
| `C_HVOL_20` | 406,473 | 406,163 |
| `C_MFI_BW_SF_20` | 394,399 | 381,397 |
| `C_PB_WIDTH_PCT` | 407,096 | 406,760 |
| `C_PB_UP_DIST_PCT` | 407,096 | 406,987 |
| `C_PB_LO_DIST_PCT` | 407,096 | 406,964 |
| `C_POSC_14` | 407,096 | 406,274 |
| `C_WAD_BAR_SF` | 397,219 | 360,162 |
| `C_SMC_SWEEP` | 408,253 | 6,474 (1.586%) |

A Gate E by-product, not Gate C.

---

## Suites

`python -m pytest tests/test_comparators.py -q` in `../Backtesting` — **14 passed**,
**pytest exit code 0** (captured directly, never through a pipe). New file
`../Backtesting/tests/test_comparators.py` pins the ladder ORDER of all three declared
scales, the sentinel→NaN rule, an undeclared column being all-NaN *and reported*, an
undeclared *value* being reported, and the 492 / 485 / 1 / 6 / 0 / 0 engine shape on a
cached frame.

Nothing was written into `pandas_ta/`, so no PandasTa suite is implicated and none is
claimed. `../Backtesting`'s full suite was not re-run: the change surface is two analysis
scripts under `scripts/analysis/`, and `_comparators` has exactly one other consumer, this
harness (verified by grep).

## Reproducibility

All artifacts regenerated 2026-09-10 from a cold `_work/` cache, stages 1→8, all exit 0.
`altport1_overlap_max.csv` carries `verdict_schema = r3-perframe-0.90`; stages 6 and 7
**assert** that stamp and refuse to run against a CSV carrying any other value, because
round 2's defect was consuming a stale one silently for a whole review round.

## What I could not measure, and why

1. **Gates A, B, C, F are out of scope**; Gate D is measured but only against tti's rounded
   output and **must be re-run bit-identical on the fork implementation in ALTPORT-2**.
2. **One parameterisation each.** `cvi(10)`, `hvol(20)`, MFI's `SMA(volume, 20)`,
   `ProjectionBands`/`Oscillator` at tti's `period=14`. `hvol`'s 0.821 → 0.835 move from 12
   frames to 89 shows these numbers do not only fall.
3. **BIST daily only.** 89 frames, 408,253 bars, one market, one timeframe. No US, no
   hourly — and the hourly book is where `cfo` earns, so `C_POSC_14` × `cfo` was measured
   on the quieter timeframe.
4. **`rel_vol_20` is production code but not a `compute_all` column.**
5. **Two forms deliberately unscreened**: `ProjectionOscillator`'s 3-EMA trigger line and
   Williams AD's cumulative line.
6. **The smc null is a circular shift, so 1.89× is an upper bound** on bar-level alignment;
   a density-preserving block bootstrap was not run.
7. **The proposed `CLAUDE.md:98` replacement is a proposal**, and its `pct_frames_ge_090`
   clause is calibrated on one datapoint.
8. **The standards clash is presented, not decided.** ALTPORT-2's input set depends on it.
9. **`TVPTA-9` is open** — ~14 other overlap harnesses still use `select_dtypes`.

---

## Metrics

- metric: comparators_swept value: 492 @ backtest_results/altport1/_work/_comparator_report.csv
- metric: n_unmapped value: 0 @ backtest_results/altport1/_work/_comparator_report.csv
- metric: n_unmapped_values value: 0 @ backtest_results/altport1/_work/_comparator_report.csv
- metric: frames value: 89 @ backtest_results/altport1/altport1_reachability.csv
- metric: pooled_bars value: 408253 @ backtest_results/altport1/altport1_reachability.csv
- metric: verdict_schema value: r3-perframe-0.90 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: posc_pooled_max_abs_rho value: 0.894742 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: posc_verdict value: STRUCK @ backtest_results/altport1/altport1_overlap_max.csv
- metric: posc_perframe_median_abs_rho value: 0.910212 @ backtest_results/altport1/altport1_perframe.csv
- metric: posc_pct_frames_ge_090 value: 62.921348 @ backtest_results/altport1/altport1_perframe.csv
- metric: wad_pooled_max_abs_rho value: 0.889416 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: wad_pct_frames_ge_090 value: 12.359551 @ backtest_results/altport1/altport1_perframe.csv
- metric: pb_width_pooled_max_abs_rho value: 0.874411 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: hvol_pooled_max_abs_rho value: 0.834724 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: pb_up_pooled_max_abs_rho value: 0.773573 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: hvol_vs_rel_vol_20_rho value: 0.452296 @ backtest_results/altport1/altport1_named_adversaries.csv
- metric: smc_density_pct value: 1.586 @ backtest_results/altport1/altport1_smc_event_coincidence.csv
- metric: smc_observed_any_lsh_pct value: 20.960766 @ backtest_results/altport1/altport1_smc_event_coincidence.csv
- metric: smc_null_any_lsh_pct value: 11.092369 @ backtest_results/altport1/altport1_smc_event_coincidence.csv
- metric: smc_enrichment_x value: 1.889656 @ backtest_results/altport1/altport1_smc_event_coincidence.csv
- metric: gate_d_bit_identical_columns value: 3 @ backtest_results/altport1/altport1_gate_d.csv
- metric: quantisation_max_abs_delta value: 0.0365645 @ backtest_results/altport1/altport1_quantisation_pooled.csv
- metric: quantisation_verdicts_flipped value: 0 @ backtest_results/altport1/altport1_quantisation_pooled.csv
- metric: wad_lane_log_return_spearman value: 0.999990 @ backtest_results/altport1/altport1_wad_lane.csv
- metric: mfi_upstream_identity_max_abs_diff value: 4.99908e-11 @ backtest_results/altport1/altport1_gate_d.csv
- metric: candidates_struck value: 1 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: survivors_gate_e_band value: 8 @ backtest_results/altport1/altport1_overlap_max.csv
- metric: survivors_altport0_standard value: 3 @ docs/AltportScreen.md
- metric: pytest_exit_code value: 0 @ Backtesting/tests/test_comparators.py
