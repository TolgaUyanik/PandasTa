# Pine Corpus Triage — PINEBI-2, triage half

**Date:** 2026-09-10 · **Scope:** measurement and recommendation only. **Nothing was ported. Nothing was committed.**

This document is the *triage half* of PINEBI-2. The porting half is **blocked** (§5) and was
deliberately not attempted; that is an explicit scope decision, recorded here rather than quietly
narrowed. Its output feeds `../Backtesting/TODO.md` **TVPTA-1b** and **TVPTA-6** — it does not
replace them, and no third pine initiative is opened.

No MPL-licensed source text is reproduced below. Candidates are cited by slug and by exported
function name only.

---

## 1. Measured inventory

Every number PINEBI-2's task text asserts, checked. Commands are re-runnable from `d:/AwakenAnalytics/`.

| Claim in PINEBI-2 | Verdict | Measured |
|---|---|---|
| `docs/pine/` holds **2,211** `.pine` files | ✅ **CONFIRMED** | `find docs/pine -name '*.pine' -type f \| wc -l` → **2211**. Also 2,211 total files (no strays), **46 MB**. |
| **912** are MPL-2.0 © TradingView | ⚠️ **HALF WRONG — and worse, not better** | **912** files carry the MPL-2.0 header (`grep -rl "Mozilla Public License"`) ✅. But only **8** mention `© TradingView`. The copyright lines are `// © <individual author>` — 746 in the plain single-name form plus variants, i.e. **hundreds of separate rightsholders**, not one. The exposure is larger than "TradingView owns it", not smaller. |
| TVPTA already **ported 195** | ❌ **WRONG — 195 was the port *target*, not the ported count** | `datastore/source/pine_candidates_families.csv` has **195 rows** = the shortlist (`portable` 53 + `extractable_core` 142). Its `tvpta3_decision` column: **drop 138 · port 40 · defer 7 · ported 1 · blank (excluded) 9**. `scripts/utils/tvpta_status.py` reports 5 of the 40 `port` rows **never landed** (`GC3Vxs8n`, `iOd2A4mw`, `oLJsy4Id`, `w8Umyq4c`, `yQdPgJ6s`) and 1 `defer` row **did** land (`6SVLw0kE` → `iama`). **Actually landed ≈ 37**, not 195. Two rows are flagged AMBIGUOUS by the tool and are not resolved here (±2). |
| the **43-candidate** `defer` backlog (TVPTA-6) | ❌ **WRONG, and so is the parent TODO's own correction** | `tvpta_status.py` measures **7** `defer` rows today, not 43. The parent `TODO.md`'s later line *"Remaining TVPTA-6 backlog (NOT started): volatility (6), signal-utility (6), prior-extreme (5) — 17 candidates"* is **also stale**: measured families are composite **3**, prior-extreme **3**, volatility **1**, signal-utility **0**. |
| **992** never-scanned `library`-type files | ✅ **CONFIRMED** | Join of the 2,211 file stems against the index → `library` **992** · `indicator` **443** · `strategy` **428** = 1,863 matched, **348** orphans. Reproduces TVPTA-1's numbers exactly. |
| `docs/pine/` is "currently neither committed nor gitignored" | ❌ **STALE — it IS gitignored** | `git check-ignore -v docs/pine` → `.gitignore:167: docs/pine/`, exit 0. `git status --porcelain docs/pine` → empty. Untracked *and* ignored since 2026-09-07. **No licensing exposure in `PandasTa`** — but see §1.2: the second copy under `Backtesting/docs/TradingView/pine/` is **tracked**, all 2,211 of it, so the corpus-wide question is open. The PINEBI-2 tie line should be corrected; `CLAUDE.md` already states it correctly. |

### 1.1 There are two different joins, and both are correct

An earlier draft of this section claimed the documented join source "is wrong". **That was a
strawman and is retracted.** The two joins answer different questions and neither is in error.

`TODO.md:91` (the PINEBI-1a tier table, **not** PINEBI-2 at :292) states: *"Corpus join is verified:
`…/tv_source.jsonl` (3,730 rows, 2,250 with source) matches `docs/pine/` 2,211 / 2,211 on
basename."* That is a **file-existence** join — does every `.pine` on disk correspond to a scraped
row — and it is **correct**: 3,730 rows reproduce, and all 2,211 stems match with 0 orphans.

The jsonl has no `script_type` field (keys: `url, slug, pub_id, script_name, script_access, version,
created, updated, source_available, source_len, source_path, pub_selection, error`), but the TODO
never claimed it did. The **script-type** join is a separate lookup, documented in its own tool's
docstring at `scripts/utils/triage_pine_indicators.py:69`:
`Backtesting/docs/TradingView/tv_scripts_index_union.csv` (2,960 rows, one per slug, carrying
`script_type`). Matching the 2,211 stems against it reproduces 1,863 / 348 and 992 / 443 / 428
exactly.

Use the jsonl for provenance, the union CSV for type. Nothing needs correcting.

### 1.2 A second, undocumented copy of the corpus

`Backtesting/docs/TradingView/pine/` holds the **same 2,211 filenames** (set difference in both
directions = 0). The triage tooling reads *that* copy, not `PandasTa/docs/pine/`. So the 912
MPL-licensed files exist twice on disk (~92 MB).

🔴 **Measured. The all-clear in the table above is repo-local, and the corpus-wide question is open.** The second copy is **tracked**:

```sh
git -C Backtesting check-ignore -v docs/TradingView/pine   # exit 1 — NOT ignored
git -C Backtesting ls-files docs/TradingView/pine | wc -l  # 2211
```

All 2,211 files — including the 912 carrying MPL-2.0 headers under **hundreds of separate
individual rightsholders**, only 8 of which say `© TradingView` — are in the `Backtesting` git
index. `Backtesting` has **no `LICENSE` file at all**. So the row above reading "No licensing
exposure in this repo" is true only of *this* repo (`PandasTa`), and the untracking exercise of
2026-09-07 did not close the question repo-wide; it moved it.

**Not determined here, and it decides the severity:** whether `github.com/TolgaUyanik/Backtesting`
is public or private. **Owner action, not auto scope** — remediation means history rewriting and a
force-push. This document takes no action on it and does not treat it as blocking the triage.

---

## 2. The two queues, characterised

### Queue A — the TVPTA-6 `defer` backlog

**Measured size: 7**, not 43.

| slug | family | note |
|---|---|---|
| `6SVLw0kE-Institutional-Moving-Averages` | composite | **already landed as `iama`** — the CSV row is stale |
| `HrU0i0ZN-ORB-Confluence-Pro` | composite | TVPTA-6's own log records it **NOT PORTABLE** (sub-hourly session windows; pipeline floor is 1h) |
| `W74Algwa-Pre-Market-High-Low-ORBs-EMAs-VWAP-Pivots-v6` | composite | same — **NOT PORTABLE** |
| `K0SEi3Ct-TL-PbD-Shape-Pro…` | volatility | volume-profile shapes |
| `Vrrujyso-Delta-Volume-Profile-Order-Flow…` | prior-extreme | needs order-flow / delta data |
| `hgSyMtJe-Anchored-Trend-Follower` | prior-extreme | |
| `izua5dXx-Smart-Trend-Zones` | prior-extreme | |

Net workable content: **4 candidates** (7 − 1 landed − 2 recorded not-portable), and two of those
four need volume-profile / order-flow inputs the single-OHLCV-frame contract does not supply. Add
the 5 `port` rows that never landed and the true remaining TVPTA-6 surface is **~9 candidates, of
which perhaps 4–5 are actionable**. This queue is essentially drained; it is a cleanup, not a MAJOR.

### Queue B — the 992 `library` files

Never scanned. I ran the **verbatim** TVPTA-1 classifier (`classify_bucket`, imported from
`scripts/utils/triage_pine_indicators.py`, not re-implemented) over all 992:

| bucket | library (992) | share | indicator (443) | share |
|---|---:|---:|---:|---:|
| `no_math` | **649** | **65.4%** | 94 | 21.2% |
| `portable` | 179 | 18.0% | 53 | 12.0% |
| `extractable_core` | 90 | 9.1% | 142 | 32.1% |
| `needs_multisymbol` | 74 | 7.5% | 154 | 34.8% |
| **shortlist-eligible** (`portable` + `extractable_core`) | **269** | **27.1%** | **195** | **44.0%** |

**Licence composition of the 269-file pool** — measured, because the IP gate
(`Backtesting/TODO.md`, the "IP / LICENSE GATE" block) turns it into per-file work before a port:

| attribution found IN THE FILE | n | share | what the IP gate actually requires |
|---|---:|---:|---|
| MPL-2.0 header | **179** | 66.5% | clause (a): port carries author + source URL + the existing licence header |
| `©` / Copyright line, no MPL header | 19 | 7.1% | clause (c): **licence must be resolved per file** — if it is not MPL-2.0 it does not ship |
| neither | **71** | 26.4% | same as above: no header to preserve, so the terms must be established before porting |

⚠ **An earlier draft called these 71 "unattributable" and cut the pool to 198. That was an
overread and is retracted.** The gate's unattributable clause (b) is explicitly about the **348
orphan pine files, which have no author and no URL** — and none of the 71 is an orphan. Measured
against `tv_scripts_index_union.csv`: **71 of 71 carry an author, 71 of 71 carry a source URL, 0
are absent from the index.** Clause (a)'s attribution is therefore satisfiable for every one of
them from the index; what is missing is an in-file statement of *terms*, and MPL-2.0 is a
TradingView **convention**, not a guarantee, so a missing header is not evidence of non-MPL either
way.

**The honest shape of the supply cut is a band, not a number:**

- **269** if the 90 files without an MPL header resolve to MPL-2.0 on inspection (attribution comes
  from the index, which has it for all of them);
- **179** if clause (c) is read literally and every file that does not *state* MPL-2.0 is dropped
  unexamined.

Both bands are carried through §4. Resolving the 90 is per-file work that nobody has done, and it
is a precondition on Queue B either way — which is the actionable point, and it survives whichever
end of the band you take.

🔴 **This refutes the parent TODO's stated premise.** `../Backtesting/TODO.md:86` argues libraries are
*"on the face of it the **most** portable category"*. Measured, they are the **least** math-dense
bucket in the corpus: **65.4% contain none of the 43 whitelisted `ta.*` functions**, three times the
indicator rate, and the shortlist-eligible share is **27.1% vs 44.0%**. A Pine `library()` is indeed
exported reusable code — but what gets published as a library is overwhelmingly *infrastructure*:
theming, logging, drawing, alert-string formatting, matrix algebra, expression parsers, session and
timezone math. That is visible in the sample in §4 and is the single most decision-relevant finding
in this document.

---

## 3. Recommendation: **defer Queue B; wire the 62 already-ported indicators first**; close Queue A as cleanup

Reasoning, in the order that decides it:

1. **Queue A has no volume left.** 4 actionable candidates cannot justify a MAJOR. Its remaining
   items should be **re-decided in place** (2 already recorded NOT PORTABLE, 1 already landed, the
   rest blocked on data contracts) and the section closed. Hours, not a project.
2. **Queue B is the only queue with supply** — 269 shortlist-eligible files, 138% of the entire
   indicator shortlist that produced ~37 landed ports.
3. **But supply is not the constraint; selection is,** and this repo now has a measured base rate
   saying so:
   - TVPTA-1 → -6: 195 shortlisted → **138 dropped (70.8%)** → 40 `port` → **~37 landed (19.0% of the shortlist)**.
   - The 2026-09-08 bounded-11 batch built ~35 columns and **deleted 12 (34%) on Gate E redundancy**.
   - ALTPORT triaged 20 AlternativeRepos candidates → **3 ports (15%)**.
   - MLCOL-2 shipped **0 of 5**.
   - And the fork is *fuller* now than when TVPTA-1 ran: **224** registered indicators vs the 157
     that shortlist was deduped against. Every historical base rate is therefore an **overestimate**
     of today's.
4. **Licensing is per-file work before anything is built, on 90 of the 269.** 179 carry an MPL-2.0
   header; **90 do not** (19 have a bare `©`, 71 have neither) and their terms must be established
   per file, because `Backtesting/TODO.md`'s IP gate clause (c) says a candidate that is not
   MPL-2.0 does not ship. They are **not** unattributable — all 71 carry an author and a source
   URL in the index (§2), and the gate's unattributable clause is about the 348 orphans, which
   these are not. Effective pool: **179–269**, depending how clause (c) is read.
5. **The demand-side objection, which supply figures cannot answer.** TVPTA-8 measured the last two
   porting batches at **zero** engine call sites; INDREF-2 measured **62** fork indicators that no
   engine path calls at all — and INDREF-2 presents the 62 as the generalisation of TVPTA-8's
   result, so **TVPTA-8's 28 are inside the 62, not additional to them**. Adding 2–7 more unwired
   indicators to a shelf of 62 lowers that ratio further. Nothing in this document rebuts that,
   because it is not a supply question.

**Revised recommendation, against the corrected 2–7 yield (§4): DEFER Queue B; do the wiring pass
first.** The earlier "open it" rested on a yield of 10–25 that the discounts do not produce. At
2–7 landed indicators — plausibly 1 — from 179–269 files read, the cost per landed indicator is
roughly **36–90 Pine files read and classified each** (pairing each pool with its own yield row
in §4: 179/5 … 179/2, and 269/7 … 269/3), while 62 already-built, already-tested,
already-documented indicators sit unexecuted by any engine path. Wiring those is strictly cheaper
per unit of measurable signal, and until a mining run has seen them nobody can say whether the
fork needs a 235th indicator at all.

Queue A closes as cleanup either way (4 actionable candidates, hours not a project).

**If the owner opens Queue B regardless**, the shape is: not *"triage 992 files"* but *"**triage the
179–269 shortlist-eligible libraries, Gate-E-screen first, build second**"* — with the 649
`no_math` and 74 `needs_multisymbol` rejected on the recorded classifier verdict and never opened,
and the licence terms of the 90 non-MPL-headered files resolved before effort is spent on them. §5's blockers
must clear first, because the Gate E screen is the thing that is currently broken.

---

## 4. Sample triage

**Sampling rule.** Population = the **269** library files in `portable` ∪ `extractable_core` (the
only actionable subset; `no_math` and `needs_multisymbol` are rejected by the classifier's own
recorded rule). Pool sorted by `slug` ascending, then `random.seed(20260910)`,
`random.sample(pool, 30)` (CPython `random`, Mersenne Twister — reproducible). **n = 30**, 11.2% of
the pool.

**Screen applied.** For each file: extract exported function names
(`^\s*export\s+(?:method\s+)?\w+\s*\(`) and the set of `ta.*` calls, then judge the *capability*
against `pandas_ta.Category` (224 registered) and the ML feature contract (causal · scale-free ·
non-redundant).

⚠️ **This is a capability-level screen, not a behavioural measurement.** `CLAUDE.md`'s own record
says name-level previews inflate gap sizes **3–6×** (pandas-ta-classic: name-diff 143 absent →
behavioural 33 → 9). The surviving fraction below is therefore an **upper bound**. No candidate was
transcribed using fork helpers and compared to a fork column — that method produced three false
identities in ALTPORT-0 and is not used here. Where a "duplicate" call rested on a name, I checked
the fork function's actual signature and docstring instead; **two calls changed as a result** (#3 and
#23, marked).

### Per-candidate verdict

| # | slug | what it exports | verdict | reason |
|---|---|---|---|---|
| 1 | `2s4g7oso-MusaCandlePatterns` | 98 exports: doji, engulf, hammer, star, tweezer… | ❌ REJECT | duplicates `cdl_pattern` / `cdl_doji` / `cdl_inside` |
| 2 | `646kjfgg-DafeVisLib` | theming, gradients, heatmap colours | ❌ REJECT | not a feature — visualisation |
| 3 | `7UuKSgeS-mt-elliott-core` | `ewo`, wave-phase state machine over pivots | 🟡 MAYBE | ⚠️ call changed on check: fork `ao` is SMA(5/34) on **hl2**; EWO is conventionally EMA on **close** — *not* an automatic duplicate. Phase model is discrete/labelled. Gate E must settle it. |
| 4 | `8vJftqgC-visualization` | tagLine, textLabel, box | ❌ REJECT | drawing only |
| 5 | `95Gosqs3-ICOptimizerLib` | IC pearson/spearman/kendall, forward return, param optimiser | ❌ REJECT | `f_forward_return` is **look-ahead by construction** (Gate B); the rest is a research harness, not a column |
| 6 | `AhaZ4O0w-cloudTheory` | drawCloud, priceAction | ❌ REJECT | drawing-dominant |
| 7 | `BnoJgkde-lib-pickmytrade` | alert-message JSON builders | ❌ REJECT | not a feature |
| 8 | `CGOIkYOw` (MaidongLiquidityLibrary) | 1 export `LLF` (pivots + ATR + `valuewhen`) | 🟡 MAYBE | fork ships `liquidity_sweep`, `smc_sweep`, `liquidity_compression_box`, `equal_highs_lows` — high prior of redundancy, but unmeasured |
| 9 | `EGO3TmRA-DrawZigZag` | zigzag drawing | ❌ REJECT | `zigzag` / `zigzag_fib` ship |
| 10 | `EgFhIWqq-StrengthFactors` | 13 threshold-normalised bar factors: distance, uniformity, overlap, body, close, breakout, always-in, directional | ✅ **SURVIVE** | scale-free by construction; the fork has candle *patterns* but no normalised bar-shape factor set. Best candidate in the sample. |
| 11 | `EnGbheTv` (HTFStructCore_v2) | structure-from-pivots, adx, retest / sweep triggers | ❌ REJECT | `bos`, `choch`, `band_cross_retest`, `smc_sweep`, `adx` all ship |
| 12 | `F4THFatm-aprox` | DFT2 / DFT3 / DFT32 / FFT, Wavelet, Wavelet_std, whitenoise, smooth | ✅ **SURVIVE** | fork `cycles` ships `ht_*`, `ebsw` and `dsp` — **no Fourier or wavelet decomposition**. (`dsp` is an EMA detrend, not a transform, so the gap stands.) Genuine capability gap. |
| 13 | `IggPrYnb-CyberNumLib` | 63 numeric primitives: tanh, erf, norm_inv, supersmoother, Butterworth, Savitzky-Golay, winsorize, zscore variants | ❌ REJECT | helpers, not features; `zscore` / `normalize` / `ssf` ship, the rest is scipy. Savitzky-Golay is **centred → non-causal** (Gate B). |
| 14 | `JzA7OH6K-KEAS` | 1 composite score over ema / rsi / sma | ❌ REJECT | composite of shipped columns → redundant by construction |
| 15 | `KHAOZTZ4-ImrLibrary` | 1 export, 694 B, `change` + `rma` | ❌ REJECT | RSI internals |
| 16 | `LYPLUYbl-TA` | sma, ema, rma, wma, vwma, ma selector | ❌ REJECT | all six ship |
| 17 | `QNGQtaZJ-ExprLib` | expression parser / evaluator | ❌ REJECT | not an indicator |
| 18 | `SpXPpg08-TR-Utility-Library-v6-Fork` | PVSRA, ADR / ADR-high / ADR-low, session strings, DST, pips, drawing | 🟡 MAYBE | PVSRA (relative-volume candle classification) and ADR-distance are plausible features; the session / DST half needs a timezone contract that does not exist |
| 19 | `TOCd0Roc-Scale` | UI framework (getElementById, addRuler, addLabel…) | ❌ REJECT | not a feature |
| 20 | `TZZj5Wdc-Cometreon-Public` | multiMa, rsi_Special, macd_Special, alligator_Special | ❌ REJECT | **variants, not capabilities** — the PINEBI-1c finding applies verbatim |
| 21 | `U4A5cbJo-ZigZag-ATR-Pct` | ATR-percent zigzag | ❌ REJECT | `ta.zigzag(pct_threshold=…)` ships; ATR-vs-pct threshold is a parameterisation |
| 22 | `a6hydryv` (DivergenceDetector) | divergence hi / lo, **`f_rci`** (Rank Correlation Index) | ✅ **SURVIVE** (RCI only) | divergence duplicates `rsi_divergence` / `macd_area_divergence`; **RCI** — rolling Spearman of price against time — has no fork equivalent and is scale-free |
| 23 | `bk5TzEs9-SPTS-StatsPakLib` | linear / multiple / quadratic / **KNN** regression, t-tests, CIs, R², normality | ✅ **SURVIVE** (narrowed) | ⚠️ call changed on check: `ta.linreg` already exposes `r=`, so R² is **not** a gap. What survives is **multiple / quadratic regression residuals and rolling KNN regression**, which have no fork equivalent |
| 24 | `fTPAKPCj-MLMatrixLib` | 173 matrix ops | ❌ REJECT | numpy; adds no capability the consumer lacks |
| 25 | `h7z24VYf-MatrixMetrics` | equity-curve metric table | ❌ REJECT | backtest reporting, not a column |
| 26 | `h8jg8nlR` (DynamicRSI) | RSI with ATR-adaptive bounds | ❌ REJECT | variant; `rsi`, `rsx`, `stochrsi`, `qqe`, `kalman_rsi` ship |
| 27 | `hfkBS2oS-MarketStructureLib` | Liquidity, Pivot, EqualHighOrLow, BOS, CHoCH | ❌ REJECT | `bos`, `choch`, `equal_highs_lows` ship |
| 28 | `l9TIkqak` (SMCNexusFactsCore) | SMC fact state machine over pivots | ❌ REJECT | fork SMC coverage is already dense (`bos`, `choch`, `ob`, `fvg`, `smc_sweep`, `sd_zone_pro`, `swing_equilibrium`) |
| 29 | `lFM8PXEW-LogLib` | 114 logging / bit-packing exports | ❌ REJECT | not a feature |
| 30 | `s5waF1z9-HanJinSignals26` | pinbar, engulf, fractal, harami, BB touch, position mgmt | ❌ REJECT | candle patterns duplicate `cdl_pattern`; position management is out of contract |

### Estimated surviving fraction

| basis | k / n | rate | 95% Wilson CI | projected onto the 269-file pool |
|---|---:|---:|---|---|
| SURVIVE only | **4 / 30** | **13.3%** | **[5.3%, 29.7%]** | point **36**, CI **14 – 80** |
| SURVIVE + MAYBE (upper bound) | 7 / 30 | 23.3% | [11.8%, 40.9%] | point 63, CI 32 – 110 |

**Read this conservatively — and compose the discounts, do not just name them.** An earlier draft
named the discounts and then printed a headline of "10–25", which is **not reachable** from them;
it applied the Gate E factor and silently skipped the behavioural shrink. A second draft over-cut
the pool to 198 on a licensing overread now retracted in §2. Corrected, with the multiplication
shown so every cell can be checked.

The 13.3% is a *capability-level* rate measured **before** Gates A–F. Two discounts apply: the
same screen run behaviourally has historically shrunk **3–6×**, and Gate E deleted **34%** of the
columns that did get built (12 of ~35, 2026-09-08), i.e. ×0.66 survival. The pool is the band from
§2 — **269** if the 90 non-MPL-headered files resolve on inspection, **179** if clause (c) is read
literally.

| basis | pool | × rate | ÷ 3–6 behavioural | × 0.66 Gate E | **landed indicators** |
|---|---:|---:|---|---|---|
| CI floor 5.3% | 269 | 14.3 | 4.8 – 2.4 | 3.1 – 1.6 | **1 – 3** |
| point 13.3% | 269 | 35.8 | 11.9 – 6.0 | 7.9 – 3.9 | **3 – 7** |
| CI ceiling 29.7% | 269 | 79.9 | 26.6 – 13.3 | 17.6 – 8.8 | **8 – 17** |
| CI floor 5.3% | 179 | 9.5 | 3.2 – 1.6 | 2.1 – 1.0 | **1 – 2** |
| point 13.3% | 179 | 23.8 | 7.9 – 4.0 | 5.2 – 2.6 | **2 – 5** |
| CI ceiling 29.7% | 179 | 53.2 | 17.7 – 8.9 | 11.7 – 5.9 | **5 – 11** |

**The honest headline is 2–7 landed indicators, plausibly as few as 1.** Not 36, not 10–25, and
certainly not 269.

**One more downward bias, named and quantified rather than merely gestured at.** The base rates
were measured when the fork held **157** indicators; it now registers **224** — a **1.43× denser**
comparator set for Gate E to reject against. Gate E rejection is monotone in comparator count, so
every figure above is biased high. It is not applied as a fourth multiplier because the
relationship between comparator count and rejection rate has not been measured, only its
direction; treat the low end of each band as the better estimate.

§3 is re-argued against this figure above. It does not survive unchanged.

The sample's qualitative signal is as useful as its rate. Of the 23 rejects, **11 are not technical
analysis at all** (#2, #4, #6, #7, #9, #13, #17, #19, #24, #25, #29 — visualisation, drawing,
logging, UI frameworks, matrix algebra, alert strings, expression parsers, numeric helpers); the
other 12 are duplicates or parameterisations of shipped columns. The 649 `no_math` libraries are
almost certainly more of the first kind. Sample composition: **4 SURVIVE · 3 MAYBE · 23 REJECT = 30**.

---

## 5. What the porting half needs before it can start

Written out so the next reader does not re-derive the chain.

1. **PINEBI-1b — the 16 `port` rows — is OPEN and unstarted.** Verified: `docs/pine_builtin_coverage.csv`
   has 107 rows, of which **16 carry `verdict = port`** (plus 18 `port - primitive`, 2
   `port - blocked on data`). PINEBI-2 declares itself dependent on PINEBI-1a…-1e; **-1b is not
   done**, so PINEBI-2's stated precondition is unmet.
2. **TVPTA-9 — Gate E is blind to object-dtype comparators — is OPEN, and it invalidates the screen
   PINEBI-2 depends on.** Every `measure_*_overlap_full.py` selects comparators with `select_dtypes`,
   silently dropping object columns (`PSAR_Signal` holds `"Bullish"` / `"Bearish"`). Measured on
   TALIB-1's `SAREXTs`: numeric grid **ρ = 0.8393** (ship-with-disclosure) vs coerced **ρ = 0.9598**
   (revert) — a band change caught only by luck. `docs/indicators/column_manifest.txt` is **492
   lines**; a Gate E run today screens against **485** numeric columns. Any port measured now must
   be re-measured after TVPTA-9.
3. **TVPTA-8 is the standing evidence that porting is not the bottleneck.** 28 fork indicators were
   added 2026-09-08/09 and **zero are called by the engine**. Adding more unwired indicators lowers
   that ratio further.

**Therefore the order is: TVPTA-9 → PINEBI-1b → TVPTA-6 close-out → *the wiring pass (INDREF-2's 62
never-swept, which already contains TVPTA-8's 28)* → TVPTA-1b (Queue B), if at all.** Starting Queue B before
TVPTA-9 means every Gate E verdict it produces is knowingly against an incomplete comparator set
and will need redoing. Starting it before the wiring pass means adding 2–7 indicators to a shelf of
62 that no engine path executes.

A licence-resolution gate joins the chain as a precondition on Queue B itself: the terms of the
**90 non-MPL-headered files** (§2) must be established **before** reading begins, not discovered at
port time. Attribution itself is not the problem — it is satisfiable for all of them from the
index; the licence *terms* are.

**Cost, stated because "largest untapped seam" is a supply claim standing in for a cost/benefit
one:** Queue B means reading and classifying **179–269** Pine files to land **2–7** indicators —
36–90 files per landed indicator, pairing each pool with its own yield row in §4, before Gates
A–F are run on any of them.

Two corrections to make in `TODO.md` while doing that, both stale text:
- PINEBI-2's tie line, *"`docs/pine/` is currently neither committed nor gitignored"* — it **is**
  gitignored (`.gitignore:167`), decided 2026-09-07.
- PINEBI-2's *"43-candidate `defer` backlog"* and the parent's *"17 candidates across 3 families"* —
  the measured figure is **7**.

---

## 6. What I could not determine

- **Whether `github.com/TolgaUyanik/Backtesting` is public or private.** This decides the severity
  of the tracked second copy measured in §1.2 (2,211 files, 912 MPL, no `LICENSE` in that repo).
  Owner action; remediation needs history rewriting and a force-push, which is out of auto scope.
- **The two AMBIGUOUS TVPTA rows** (`GUaRGMmZ` / `xla3FbZ2` "Dynamic N-Day MA (x3)"; `srZnoN9T` /
  `uKQBgrg2` "Weis Wave Renko"). `tvpta_status.py` cannot resolve which of each pair landed, so the
  "≈37 landed" figure carries ±2.
- **Whether the 5 unlanded `port` rows were dropped on purpose or lost.** The tool reports the
  drift; no reason is recorded anywhere I found.
- **Any behavioural overlap number for the 4 survivors.** No Gate E was run — deliberately, because
  TVPTA-9 makes any Gate E run today wrong by a known amount. The 13.3% is a screen, not a
  measurement.
- **Whether the 269-file pool contains near-duplicates of each other.** The classifier dedupes
  against pandas_ta, not within the library set; the true distinct-capability count is ≤ 269 by an
  unknown margin.

---

## Reproducing this document

```sh
cd d:/AwakenAnalytics
git -C PandasTa check-ignore -v docs/pine
find PandasTa/docs/pine -name '*.pine' -type f | wc -l
grep -rl "Mozilla Public License" PandasTa/docs/pine | wc -l
python Backtesting/scripts/utils/tvpta_status.py
```

Bucket counts, the licence split and the seeded sample, executable (note it reads the **Backtesting**
copy of the corpus -- see §1.2 -- not `PandasTa/docs/pine/`):

```python
import csv, os, glob, random, re, sys
sys.path.insert(0, 'Backtesting/scripts/utils')
from triage_pine_indicators import classify_bucket        # VERBATIM, not re-implemented

PINE = 'Backtesting/docs/TradingView/pine'
stems = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(PINE + '/*.pine')}
idx = {r['slug']: r['script_type']
       for r in csv.DictReader(open('Backtesting/docs/TradingView/tv_scripts_index_union.csv',
                                    encoding='utf-8'))}
lib = [s for s in stems if idx.get(s) == 'library']       # 992

pool, buckets = [], {}
for s in sorted(lib):                                      # sorted by slug -- fixes sample order
    b = classify_bucket(open(stems[s], encoding='utf-8', errors='replace').read())
    buckets[b] = buckets.get(b, 0) + 1
    if b in ('portable', 'extractable_core'):
        pool.append(s)
# buckets -> {'no_math': 649, 'portable': 179, 'extractable_core': 90, 'needs_multisymbol': 74}
# len(pool) -> 269

mpl = other = none = 0
for s in pool:
    src = open(stems[s], encoding='utf-8', errors='replace').read()
    if 'Mozilla Public License' in src:                        mpl += 1
    elif re.search(r'©|\(c\)\s*\d|Copyright', src, re.I):  other += 1
    else:                                                      none += 1
# mpl=179  other=19  none=71  -> pool 269; 179 if IP-gate clause (c) read literally

random.seed(20260910)
sample = random.sample(pool, 30)
# sample[:5] -> ['EGO3TmRA-DrawZigZag', 'TOCd0Roc-Scale', '95Gosqs3-ICOptimizerLib',
#                'IggPrYnb-CyberNumLib', 'h8jg8nlR']
```
