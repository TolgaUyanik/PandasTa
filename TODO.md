# PandasTa Tolga Uyanik's Fork To-do's

Library-scoped work only. Engine-side work (mining, wiring, live book) lives in
`../Backtesting/TODO.md` — the pine-porting initiative **TVPTA** (TVPTA-0 … TVPTA-7b) is there, and
several sections below extend it rather than restarting it.

Port protocol every section here is bound by: `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`
(Gates A–F; overlap ρ ≥ ~0.9 → revert, 0.76–0.80 → ship with disclosure, < 0.76 → ship).
Column inventory and ML form of everything currently shipped: `docs/IndicatorDictionary.md`.

---

# ═══ ACTIVE ═══

**The bounded-11 batch closed 2026-09-08/09** — all eleven tasks done and gated.
Record: `docs/reviews/auto-2026-09-08-bounded-11/99-summary.md`.
Suite at close: **1,563 passed / 23 skipped**, `PYTEST_EXIT=0` (1,344 at the start).
`Category` 199 → **221**. Gaps: pandas-ta-classic 33 → **11**, tti 10 → **9**,
ta-lib 10 → **0**; all three verifiers report no reproducible row.

Closed: **RMA-W** (new, owner-directed), **PINEBI-1c/-1d/-1e**, **TALIB-1**,
**CANDLE-0/-1/-2**, **INDREF-0**, **MLCOL-2**.
Deferred by the owner up front: **PINEBI-2, INDREF-1, MLCOL-1** — of these **INDREF-1 was since
done (2026-09-10)**, see the INDREF section.
Dropped with reason and later revived: **INDREF-2** (dropped because INDREF-1 was deferred; INDREF-1
landed 2026-09-10 and **INDREF-2 was done 2026-09-11** — see the INDREF section).
Still open: **PINEBI-1b** — 7 of the 16 `port` rows landed 2026-09-11 (tranche 1: `kcw`, `rwi`,
`pzo`, `vzo`, `szo`, `rms`, `wpo`); **9 remain**.

⚠ **The batch's output was mostly DELETIONS.** Twelve columns were built, measured
and deleted, and one whole task shipped nothing. Read that as the gates working,
not as wasted effort — `TVS_DIST`, `FLAG_POLE_ATR` and `RPO_OSC` set the same
precedent.

⚠ **Three findings that outlive their tasks — read before the next measurement:**
1. **Gate E has been blind to non-numeric comparators.** `SAREXTs` was about to
   ship at ρ 0.8393 because `PSAR_Signal` is an object column ("Bullish"/
   "Bearish") that `select_dtypes` silently drops. Coerced: **0.9598**, a revert.
   Every prior Gate E measurement in this repo shares the blind spot.
2. **An unsigned magnitude on a sparse support is mostly a description of that
   support.** Two independent such columns correlate ρ = **1.0000** (90,137 tied
   zeros against 360 values); signing one drops it to −0.0001. This killed six of
   CANDLE-1's columns and should screen every event-flag companion MLCOL-1 builds.
3. **`.reset_index(drop=True)` before `compute_all` silently drops 17 columns** —
   the calendar/period features need `.to_period()`. Measuring against
   `IndicatorEngine` with a reset index measures a different engine.

⚠ **MLCOL-1's premise is now in question.** MLCOL-2 shipped **0 of 5**: the
contract's three reference indicators produced no shippable companion. The shapes
are sound — `SMA_10_DIST_PCT` demonstrably stripped the price level — but it dies
at ρ **0.9462** against the already-shipped `NWE_MID_200_8.0_8.0`. Re-examine the
premise before spending 137 measurements.

Earlier that day the AlternativeRepos audit closed as an audit:
**ALTFIX-0…-4, MLCOL-0 and PINEBI-0b**, and all three scanners hold. Read
`docs/reviews/auto-2026-09-08-altfix-pinebi-mlcol/99-summary.md` before touching any scanner —
it carries the measurements the guards are built on.

⚠ **FVGENG moved to `../Backtesting/TODO.md` on 2026-09-07 (owner: "we will not work on mining
relevant tasks").** Both items were `../Backtesting/` and `deploy/` work and only lived here
because FVGDEAD-1 spun them out during a review of this fork. The `fvg` repair itself is done and
shipped here; what moved is the engine/live follow-up.

⚠ **Completed and removed from this file:** WIRING-1/-2/-3, FVGDEAD-0/-1, SQZOFF-0, FVGENG-0,
PINEBI-0, PINEBI-1a (2026-09-07); TTIND-0/-1, MULTIL-0, TALIB-0 and the PTCLASSIC pair
(2026-09-08 — see `docs/reviews/auto-2026-09-07-ttind-multil-talib/`); **ALTFIX-0/-1/-2/-3/-4,
MLCOL-0 and PINEBI-0b** (2026-09-08 — see `docs/reviews/auto-2026-09-08-altfix-pinebi-mlcol/`);
**RMA-W, PINEBI-1d, PINEBI-1e, CANDLE-0, INDREF-0, MLCOL-2** (2026-09-08 — see
`docs/reviews/auto-2026-09-08-bounded-11/`). Full detail — what was found, every review
round verbatim, and the measurements — is in
`docs/reviews/auto-2026-09-07-fvg-sqz-pinebi/` and in the six commits on
`fix/wiring-fvg-pine-primitives`. Do not re-derive them from scratch; read the run reports.

# ═══ BACKLOG ═══

## PINEBI — port TradingView's built-in indicators, then continue the community corpus (NEW 2026-09-06, user)

> **Goal (user):** *"We will review each pine scripts to implement to repo from PandasTa/docs/pine/
> folder. We can start with TradingView basic indicators."*

**"Built-in" is three populations, not one (measured 2026-09-06).** Only two are portable:

⚠ **The inventory column below is the ORIGINAL HAND COUNT and is superseded by the generated
verdict table above.** Kept for the tier definitions only.

| tier | what | source | inventory (hand count, superseded) |
|---|---|---|---|
| 1 | core `ta.*` compiler intrinsics (`ta.sma`, `ta.pivothigh`) | none published — spec is the Pine v6 reference | 75 tokens seen; the classifier measures 59 used, 41 have, 17 port |
| 2 | official `TradingView/*` libraries, MPL-2.0, `© TradingView` | **published, and on disk** | `docs/pine/RA2vGpkA-ta.pine` = `TradingView/ta` v10, 47 exports; the classifier measures 18 have, 27 port |
| 3 | Indicators-dialog built-ins ("Bollinger Bands") | closed | out of scope — no source to port against |

Corpus join is verified: `ScrapyTUyanikProjects/TradingView/ScrapyTUyanik/testfolder/tv_source.jsonl`
(3,730 rows, 2,250 with source) matches `docs/pine/` **2,211 / 2,211 on basename**. The `source_path`
field still says `datastore/pine/…` — stale prefix, same filenames, so join on the basename.

⚠ **The tier-1 "28" is not 28 indicators.** Split by whether the using file does
`import TradingView/ta/<n>` (the library binds to the name `ta`, with or without `as`, and shadows the
core namespace):

- **8 are tier-2 library calls, not core** — `ema2`, `stochFull`, `stochRsi`, `rms`, `highestSince`,
  `lowestSince`, `requestVolumeDelta`, `requestUpAndDownVolume` appear in **zero** files that do not
  import the library.
- **6 looked like noise, and three of them were not.** `sum`, `max`, `min`, `pivot`, `normalize`,
  `covariance` (≤3 files each; the hits are comments such as *"Pine has no native ta.covariance"* and
  third-party library methods). ⚠ **Corrected in review**: `ta.max` and `ta.min` ARE core built-ins
  (all-time extremes, no length) and shipped in -1a; `ta.sum` IS a real sliding-sum built-in that this
  corpus only ever mentions in comments. Only `pivot`, `normalize` and `covariance` are genuinely not
  Pine built-ins. The generated verdict table above is authoritative.
- **14 are real core gaps**, and they are rolling *primitives*, not indicators: `highest` (324 files),
  `lowest` (298), `pivothigh` (229), `pivotlow` (224), `valuewhen` (58), `barssince` (56), `cum` (36),
  `correlation` (29), `percentrank` (27), `highestbars` (23), `lowestbars` (22),
  `percentile_nearest_rank` (7), `percentile_linear_interpolation` (6), `pivot_point_levels` (1).

**Verdict split, generated — this is the table the -1b…-1e scopes are cut from.**
Produced by `docs/gen_pine_builtin_coverage.py` (PINEBI-0, done 2026-09-07).

| verdict | n |
|---|---|
| `have` | 71 |
| `port - primitive` (→ -1a) | 18 |
| `port` (→ -1b) | 9 |
| `n/a - not a Pine built-in` | 4 |
| `n/a - not worth a primitive` | 2 |
| `port - blocked on data` (→ -1d) | 2 |
| `n/a - never called live in the corpus` | 1 |

⚠ These counts are **asserted**, not retyped: `test_the_docs_quote_the_csvs_actual_split` reads this
table and fails if any number disagrees with the CSV. Four review rounds went by with a stale split
standing in three documents; that is now a test failure rather than a reading exercise.

**Scope decision (user, 2026-09-06): add all three groups, including the tier-2 calls and the "noise".**
The noise six are then *not* Pine ports — they are ML utilities the fork wants on their own merit, and
`-1e` says so rather than filing them under a provenance they do not have. Total: **46 additions.**

⚠ **Superseded by the generated verdict table above.** Kept to show what the hand count
said before the classifier existed; every row moved.

| sub-task | hand count | measured |
|---|---|---|
| -1a | 16 | **18** — the 14 core gaps + `highestSince`/`lowestSince` + `max`/`min` |
| -1b | 12 | **15** — 14 library ports + `kcw`, a tier-1 gap `kc` does not cover |
| -1c | 10 | **9** — `vStop2` is a port, not an alternate |
| -1d | 2 | **2** |
| -1e | 6 | **4** — `max`/`min` were built-ins, not fork utilities |

Reconciliation as a closed identity over the **47 library exports**, so it balances:

    47 = 18 have + 14 port (-1b) + 9 alternate (-1c) + 2 blocked (-1d)
       + 2 primitive (-1a) + 2 n/a (`cagr`, `changePercent`)

  ⚠ **The earlier 4-vs-5 split of the alternates was justified by a criterion the CSV contradicts**
  ("sibling also uncovered" — `ema`, `rma`, `supertrend` and `t3` are all `have`). All nine alternates
  go to -1c; the real distinction, if one is wanted, is that `ema2`/`rma2`/`supertrend2`/`t3Alt` take a
  `series float` length the shipped sibling cannot express, and the rest do not — which is exactly what
  -1c is supposed to measure rather than assume.

  -1b's fifteenth entry, `kcw`, is a tier-1 core gap rather than a library export, so it is outside
  this identity.

✅ **PINEBI-0b — DONE 2026-09-08.** Every `have` row now declares whether anyone checked it, with a
`file:line` receipt that a test opens and reads. **30 of 55 `have` rows certified** against an
independent Pine v6 reference; the remaining 25 each state a reason — silence is what let five wrong
`have` verdicts ship. Divergences that survive as `have` carry a measured `SEMANTIC_CAVEAT`
(`rma` 0.2138, `median` 1.0122, `cmo` 42.48, `hma` 0.4740 over 287 bars).

Two findings worth carrying forward:
- **`pandas_ta.rma` is not Wilder's smoothing.** It is `ewm(alpha=1/length, adjust=True)` and differs
  from Pine on 189/287 bars. **`atr` inherits it.** A real fork defect, not a reference bug — it has
  no task yet.
- The receipts cite line numbers *into* `docs/audit_pine_have_rows.py`, so editing that file reddens
  `test_audited_rows_carry_their_evidence` until the audit and then the generator are re-run. That is
  the guard working; the script's docstring says so.

- [ ] **PINEBI-1b — Port the `port` rows (MAJOR, depends on PINEBI-0). 7 of 16 DONE 2026-09-11.**
  ROWS: `dm`, `frama`, `ht`, `ift`, `relativeVolume`, `stc`, `vStop`, `vStop2`, `williamsFractal`
  (9 remaining; the CSV is the source of truth, not this line)

  ✅ **Tranche 1 landed 2026-09-11** — `kcw`, `rwi`, `pzo`, `vzo`, `szo`, `rms`, `wpo`. All seven
  wired through the five touch points, `Category` 224 → **231**, `tests/test_pinebi1b_ports.py`
  **50 passed**. Per-port evidence is in the CSV's `audit_evidence` column, written by
  `docs/gen_pine_builtin_coverage.py`'s `AUDITED` table rather than retyped here.

  ⚠ **Two findings from tranche 1 that outlive it, both about the GATE rather than the ports:**
  1. **A sign-based indicator cannot be causality-tested with a multiplicative perturbation.**
     Scaling every future close by 1.3 leaves their ORDER unchanged, so `sign(change(close))` is
     unchanged, so a genuinely non-causal `szo` mutant reproduced the prefix exactly and
     **escaped at 65 of 113 J values**. Mirroring the future fixes most of it but not at bar `J`
     itself, where the mirror is the identity. The reliable mutant for these mutates the
     SMOOTHER, where magnitude is visible, not the sign input.
  2. **A centred-window mutant on a NaN-heavy series is degenerate.** `wpo`'s `ti` is NaN on
     every gap-down bar, so `rolling(center=True)` at the default `min_periods` needs a fully
     finite window and produced a mutant that was **99.8% NaN** — nothing to compare, `caught=0`,
     an escape that was an artifact of the mutant rather than a statement about `wpo`.
     `min_periods=1` is load-bearing.

  ⚠ **`ift` needs a decision before it can be ported** (flagged, not silently made): it is
  `tanh`, so on raw price it saturates to a constant and would fail Gate C as a close-based
  column. It is a TRANSFORM, and the honest options are to register it applied to a bounded
  input, or to ship it unregistered like the `ma` dispatcher. Owner/next-session call.

  ⚠ **`dm` and `stc` collide with shipped names** and need distinct ones: the library's `dm` is
  the **Demarker** oscillator while `pandas_ta.dm` is Wilder's Directional Movement, and the
  library's `stc` differs from the shipped `stc` in parameters, clamping and a guard (see the
  round-5/round-7 notes below). The `-2`/`_tv` suffix convention PINEBI-1c set is the precedent.
  Take the list from the CSV's `port` rows, not from here — `test_the_docs_quote_the_csvs_actual_split`
  now asserts every one of them appears in this block, because `stc` was announced as "scoped into
  -1b" for a whole round while living only in a CSV note string.

  ⚠ **Three of these were classified `have` until review caught them**, and all three would have
  been deleted silently:
  - `kcw` (round 4) — Pine's `ta.kcw` is the Keltner **width**, `(upper - lower) / basis`;
    `pandas_ta.kc` returns `KCLe_/KCBe_/KCUe_` with no width column.
  - `dm` (round 5) — the library's `dm` is the **Demarker** oscillator
    (`RA2vGpkA-ta.pine:174`, `sma(demax)/(sma(demax)+sma(demin))`, bounded 0–1);
    `pandas_ta.dm` is Wilder's Directional Movement, `DMP_`/`DMN_`. Same short name, different
    indicator.

  - `stc` (round 7) — the library is `ema(stoch(ema(stoch(macd,cycle),d1),cycle),d2)` clamped to
    [0,100] (`RA2vGpkA-ta.pine:527`) with `d1`/`d2` as parameters; `pandas_ta.stc` has neither,
    substitutes a fixed-alpha recursion, does not clamp, and its `if lowest_xmacd.iloc[i] > 0` guard
    (`stc.py:195`) freezes the first stochastic whenever the rolling MACD minimum is ≤ 0 — the normal
    case for a zero-centred oscillator.

  All three were found by reading the library's own body rather than trusting the name — the
  method that had already caught `ft` (Fisher) and `vi` (Vortex). ⚠ **9 of the 15 tier-2 `have` rows remain unread** (was 12 of 17; PINEBI-0b certified six more on 2026-09-08 — `ao`, `ichimoku`, `uo`, `coppock`, `donchian`, `ft`, `t3`, `trix`, `vi` are what is left) — round 7 withdrew certifications that had been
  made on the library's one-line `@function` summary alone, after four of them turned out to diverge.
  See PINEBI-0b. The test asserts only that the CSV *declares* which rows are unaudited. (`vStop2` sits here, not in -1c: it is an
  alternate of `vStop`, which is not shipped either, so there is no sibling to measure it against.) The rest of the 47 library exports are scoped by the CSV,
  not by this sentence: **9** alternates to -1c, 2 data requests to -1d, 2 primitives already in -1a,
  2 `n/a`. An earlier version said "4 alternates" here and would have scoped -1c to less than half
  its list.
  ⚠ **Licence:** the library is MPL-2.0, `© TradingView`. Each port carries the attribution in its module
  docstring, as the existing Pine ports do (`tvstop` cites `7YXrxMjV`, MPL-2.0, © LyroRS). Applies to
  -1c and -1d too.
  **Done when:** each of the 16 has a test module, a Gate B mutant test, a Gate D scale check, a
  measured Gate E overlap max with its sample size, and `docs/IndicatorDictionary.md` regenerated so
  the new columns appear with their ML form. The MPL attribution applies to the 14 library exports;
  `kcw` and `stc` are core built-ins and carry none.
✅ **PINEBI-1c — DONE 2026-09-08.** The nine alternates were measured against their shipped
siblings on two axes — warm-up saved and parameter reach — because every one of them reads
ρ ≈ 1.0 against its own sibling and the revert rule would have deleted all nine unread. That rule
was suspended for this scope; ρ is recorded, not used as a veto.
  ROWS: none remaining — all nine are resolved and the CSV now routes them to have; the
  per-candidate table with the measured numbers is `docs/PineAlternatesMeasured.md`.

**KEPT (7), wired through all five touch points, MPL-2.0 © TradingView in every docstring:**
ema2 (9 bars), rma2 (9, against `wilder_rma` — NOT `rma`, which is `adjust=True` and a different
filter), dema2 (9), tema2 (9), t3_tv (9, and reaches a volume factor `t3` silently rewrites to 0.7),
atr2 (14), supertrend2 (7, and reaches BOTH `wicks` — swallowed into `**kwargs` by the sibling —
and Pine's per-bar `factor`, L602). All six length-taking siblings raise
`ValueError: The truth value of a Series is ambiguous` on a per-bar length; the alternates take it
and name the column `dyn<min>-<max>-<8 hex>`.

⚠ **Shipped, no consumer yet.** There are zero call sites for any of the seven in either repo
(the four `../Backtesting` hits are `ema26`/`ema20` substrings). They are reachable through
`ta.<name>()`, `df.ta.<name>()` and `df.ta.strategy()`, and the per-bar-length path is exercised
only by tests.

⚠ **The saved warm-up is worth zero usable ROWS to the current consumer**, measured, with the
receipt in `backtest_results/tvpta6/pine_alternates_warmup_materiality.csv`
(`run_materiality()`; `IndicatorEngine(include_advanced=False).compute_all`, parquet index left as
`DatetimeIndex`, 365 numeric columns). Per-column first-valid position: ACSEL.IS median 9 / p90 88 /
max **499** (`HARPARK_1_5_22_500`); AKBNK.IS median 13 / p90 123 / max **2,779** (`tom_pos`, a
CALENDAR feature — 623 excluding the five calendar columns). A row is gated by the slowest column,
so 9 bars off one column moves the usable start by nothing. The 9 bars are real per column and are
the measured acceptance criterion; the materiality is not. (An earlier version of these figures was
measured after `.reset_index(drop=True)`, which silently drops the 17 calendar/period columns —
348 columns, five of six figures wrong. Config is part of the measurement.)

**DELETED (2), and the measurement is the deliverable:** stochFull and stochRsi were reproduced
BIT FOR BIT by `stoch(k=periodK, d=periodD, smooth_k=smoothK)` and
`stochrsi(length=periodK, rsi_length=lengthRsi, k=smoothK, d=periodD)` — max|diff| 0.0 on the
fixture, ρ 1.0 on all 40 tickers, including at `smoothK != periodD`. The scope text's claim that
stochFull reaches "a separate %K smoothing" the sibling cannot express was wrong: `stoch` has
carried `smooth_k` separately from `d` all along.

⚠ **These seven are price-scale (`PX` in the dictionary) and do NOT clear Gate D.** They ship on
the same footing as `EMA_10` and `ATRr_14` — raw material for ratios, not features to hand a tree.
`SUPERT2d`'s polarity is INVERTED against every other direction column in the package (−1 is an
uptrend, Pine's sign) and now leads `supertrend2.__doc__` so it survives the dictionary's
150-character truncation.

**Round 2** held the port to the standard it judged the siblings by: the length clamp is now Pine's
`math.max(1.0, length)` on both the scalar and Series paths (round 1 sent a non-positive scalar to
the DEFAULT and named the column for it), `vf` and `factor` are passed through unclamped because
Pine bounds neither, the per-bar factor is ported, and two different per-bar lengths no longer
share a column name. `Category` gains +7 from this scope; absolute totals are left to the
coordinator's single reconciliation, since TALIB-1 and CANDLE-1 are adding indicators concurrently.
Tests: `tests/test_pinebi_1c_alternates.py` (69). Measurement script:
`../Backtesting/scripts/analysis/measure_pine_alternates.py`.

✅ **PINEBI-1d — DONE 2026-09-08.** `pandas_ta/volume/up_and_down_volume.py` and
`volume_delta.py`, MPL-2.0 © TradingView attributed, Gate A cited to
`RA2vGpkA-ta.pine:381-404` / `:439-442` / `:474-489`. Neither fetches: both take the
lower-timeframe frame and the anchor as arguments and raise named errors when absent.
22 tests on a synthetic 1h-from-5m fixture pin the `var bool isBuyVolume` carry, the
`VD_HIGH >= VD_OPEN >= VD_LOW` construction and the `UDV_POS - UDV_NEG == volume` identity.

⚠ **The data blocker is real and now measured** (`docs/LowerTimeframeData.md`): the cache holds
578 `_1d` and 362 `_1h` files and **zero** sub-hourly. Only 1h-under-daily is possible today,
and the 1h cache's latest bar is 2026-07-21. yfinance's sub-hourly window is a rolling ~60 days,
cannot be back-filled, and expires — so a 5m panel has to be captured forward from now.
Both functions are therefore **unprobed** by `gen_indicator_dictionary.py` (its harness builds one
daily frame) and the generated *Known breaks* section says so rather than counting them either way.

✅ **PINEBI-1e — DONE 2026-09-08.** Four fork utilities, no TradingView provenance and no MPL
attribution: `rolling_sum` (named that, not `sum`, so it cannot shadow the builtin — the emitted
column is still `SUM_<length>`), `normalize`, `covariance`, and `pivot`. 25 tests.

- `pivot` ships **only** scale-free distances (`PIVOT_<level>_DIST_PCT`, 11 columns), bit-identical
  under x8/x64. It is the missing companion to `pivot_point_levels`, which returns 11 raw prices
  and is dead as a feature — not a duplicate of it.
- `normalize`'s window is trailing, pinned by a mutant. Its flat-window value is **NaN**, not 0.5:
  0.5 was measured planting a synthetic reading on **17.7%** of settled bars on a tick-rounded walk,
  at the exact centre of the feature's distribution.
- ⚠ `rolling_sum` and `covariance` are **not scale-free** on price input and say so; they are
  building blocks, not features.
- ⚠ Correction to this section's old text: `ta.sum` is NOT absent from the corpus. Pine v5 renamed
  it `math.sum`, which is called **214 times across 88 files**. The no-attribution conclusion holds
  for the real reason — no source is copied.

- [ ] **PINEBI-2 — Resume the community corpus after the built-ins (MAJOR, depends on PINEBI-1a…-1e).**
  `docs/pine/` holds 2,211 `.pine` files, untracked since 2026-09-07 (912 are MPL-2.0
  © TradingView; root `LICENSE` is MIT). TVPTA already ported 195 and left two queues:
  the 43-candidate `defer` backlog (TVPTA-6) and the 992 never-scanned `library`-type files (TVPTA-1b).
  **Done when:** this repo's side of whichever queue is picked is ported and green; the queue's own
  acceptance criteria stay owned by the parent task.

  🔶 **TRIAGE HALF DONE 2026-09-10/11 → `docs/PineCorpusTriage.md`. Porting half NOT started, and
  the triage now recommends NOT starting it.** Nothing ported, nothing committed to the corpus.
  Every count above is wrong and the doc measures the corrections:
  - **"ported 195" was the port *target*.** `tvpta_status.py` measures **~37 actually landed**
    (±2 on two AMBIGUOUS rows); 5 `port` rows never landed and 1 `defer` row did (`iama`).
  - **"43-candidate `defer` backlog" is 7**, of which 1 already landed and 2 are recorded NOT
    PORTABLE → **4 actionable**. Queue A is cleanup, hours, not a MAJOR.
  - **Libraries are the LEAST math-dense bucket, not the most.** Verbatim `classify_bucket` over
    all 992: `no_math` **649 (65.4%)** vs 21.2% for `indicator`; shortlist-eligible **269 (27.1%)**
    vs 44.0%. What gets published as a Pine `library()` is overwhelmingly infrastructure —
    theming, logging, drawing, alert strings, matrix algebra, expression parsers.
  - **Sampled survival 4/30 = 13.3%**, Wilson 95% CI [5.3%, 29.7%], seed 20260910, recipe in the
    doc and executable.

  **Round 2 (2026-09-11) — the Fletcher gate returned REVISE with 2 CRITICALs + 3 MAJORs; all
  applied, and they inverted the recommendation.**
  - **The yield headline did not compose from its own discounts.** It printed "10–25 landed
    indicators" while instructing the reader to shrink 3–6× behaviourally and then delete 34% at
    Gate E — which gives 4–8. Add the licence cut below and the honest figure is **3–6 landed
    indicators, plausibly 1**. Every band is now shown as multiplication that can be checked.
  - **Licensing was measured in §1 and then never mentioned in the recommendation.** Of the 269
    candidate files, **179 carry MPL-2.0, 19 a bare ©, and 71 carry no attribution at all
    (26.4%)**. By `Backtesting/TODO.md`'s own IP gate those 71 cannot ship to a public MIT repo,
    so the effective pool is **198** — and the unshippable count exceeds the entire projected
    yield. A licence-attribution gate is now a precondition on Queue B.
  - **§1.1's headline accusation was a strawman and is retracted.** It claimed "the documented
    source is wrong"; `TODO.md:91` actually claims a *basename* join (`tv_source.jsonl`,
    3,730 rows, 2,211/2,211), which reproduces and is correct. The *script_type* join is a
    separate lookup the TODO never attributed to that file.
  - **TVPTA-8's objection is now answered instead of dodged.** Cost is stated: **198 files read to
    land 3–6 indicators, 33–66 files each**, while 62 already-built indicators sit unexecuted by
    any engine path (INDREF-2 §5b).
  - **Recommendation inverted: DEFER Queue B; do the wiring pass first.** Order is now
    TVPTA-9 → PINEBI-1b → TVPTA-6 close-out → **wiring pass (TVPTA-8's 30 + INDREF-2's 62)** →
    TVPTA-1b, if at all. This agrees with INDREF-2 §7, reached independently.

  🔴 **LICENSING, OWNER DECISION, NOT AUTO SCOPE.** The gate closed a limit the triage had filed as
  "not checked": there is a **second copy of the whole corpus at `Backtesting/docs/TradingView/pine/`
  and it is TRACKED** — `git -C Backtesting ls-files docs/TradingView/pine | wc -l` → **2211**,
  `check-ignore` → not ignored. 912 carry MPL-2.0 headers under **hundreds of individual
  rightsholders** (only 8 say `© TradingView`), and **`Backtesting` has no `LICENSE` file at all**.
  The 2026-09-07 untracking closed this for `PandasTa` only. Whether that repo is public is
  **unverified**. No action taken: remediation means history rewriting and a force-push.

⚠ Ties: extends **TVPTA-1b** (`../Backtesting/TODO.md:489`) and **TVPTA-6** (`:253`) — do not open a
third pine initiative. ~~`docs/pine/` is currently neither committed nor gitignored; decide which in
PINEBI-0.~~ **Stale — it IS gitignored** (`.gitignore:167`, decided 2026-09-07). The open licensing
question is the tracked second copy in `Backtesting`, above, not this one. `williamsFractal` (-1b) overlaps the engine's existing `FRACTAL_UP`/`FRACTAL_DN` columns and
`ta.pivothigh`/`ta.pivotlow` (-1a) — measure all three against each other before shipping any.
The other 6 `© TradingView` libraries on disk (`ZigZag`, `zigzag-force`, `RiskMetrics`, `ValueAtTime`,
`Request`, `Color`) are unaudited; `ZigZag`/`zigzag-force` overlap the shipped `zigzag`/`zigzag_fib`.

## CANDLE — generic multi-bar chart patterns (NEW 2026-09-06, user)

> **Goal (user):** *"We should review add generic candle patterns like shoulder head shoulder."*

✅ **CANDLE-0 — DONE 2026-09-08.** `docs/CandlePatternShortlist.md`, backed by
`../Backtesting/scripts/analysis/measure_chart_patterns_overlap_full.py` + 7 CSVs (written,
**untracked** — the thirteen sibling `measure_*_overlap_full.py` harnesses are all tracked and this
one should join them).

**BUILD (9):** head-and-shoulders bear/bull · triple top/bottom · asc/desc triangle · symmetrical
triangle · rising/falling wedge · cup-and-handle/rounding bottom · rounding top · **rectangle,
last, with disclosure**. **DEFER:** broadening/megaphone. **SKIP — already shipped:** double
top/bottom (`dtdb`), flag/pennant (`flag_breakout`). **SKIP — reachable today:** all 62 TA-Lib
candles.

Measured on 50 BIST tickers / 91,197 daily bars: largest |ρ| **anywhere is 0.1452**
(`P_RECT_UP × SWINGEQ_BOS_BULL_5_5`) against a 0.76 disclosure line.
⚠ **That is NOT Gate E** — it sweeps 112 columns from 16 modules chosen for collision risk, not the
full ~200-indicator production config. ✅ **CANDLE-1 re-ran it in full** against
`IndicatorEngine(include_advanced=True)` = 485 columns: the maximum moved 0.1452 → 0.2911 and no
verdict changed. `docs/CandlePatternsMeasured.md` §4.
⚠ The rectangle is the contested one: 68.7% / 71.2% of its breaks sit within ±3 bars of an
`LCB_BREAKOUT_*` (highest coverage of any candidate; next is H&S at 0.206), but the co-fire is
one-directional — only 1.9% of LCB's 3,974 firings. Flip trigger pre-registered at recall ≥ ~0.69.

✅ **CANDLE-1 — DONE 2026-09-08 (round 2).** Eight of the eleven shortlisted patterns shipped as
**four** modules / **22 columns**, all five wiring touch points, `Category` trend +4. Results:
`docs/CandlePatternsMeasured.md`. Harness:
`../Backtesting/scripts/analysis/measure_candle1_overlap_full.py` + 6 CSVs in `candle1_out/`
(written, **untracked**, same status as CANDLE-0's harness). Tests:
`tests/test_candle1_patterns.py` (38).

| module | patterns | columns |
|---|---|---|
| `head_shoulders` | H&S, inverse H&S | `HS_CONF_BEAR/BULL` `HS_TGT_PCT` `HS_PEND` `HS_AGE` |
| `triple_top_bottom` | triple top / bottom | `TRPL_CONF_BEAR/BULL` `TRPL_TGT_PCT` `TRPL_PEND` `TRPL_AGE` |
| `triangle_wedge` | asc/desc/symmetrical triangle, rising/falling wedge | `TRIW_CONF_BEAR/BULL` `TRIW_SLOPE_UP/DN` `TRIW_WIDTH` `TRIW_PEND` `TRIW_AGE` (suffix `_5_5_60`) |
| `rounding_cup` | cup & handle / rounding bottom, rounding top | `CUP_CONF_BULL/BEAR` `CUP_DEPTH` `CUP_CURV` `CUP_AGE` (suffix `_40_10_0.6_0.1_0.05`) |

Five patterns share `triangle_wedge` on purpose: they differ only in two boundary-slope signs, so
the module ships the MEASUREMENTS and a tree derives the taxonomy in two splits — no one-hot flags.
`pandas_ta/trend/_patternlib.py` (underscore-prefixed, no public indicator) holds the shared pivot
stream, the same code CANDLE-0's probe ran.

**Gate C:** 0 of 22 dead over 50 tickers / 91,197 bars, and the shipped modules reproduce CANDLE-0's
prototype counts EXACTLY on the identical pool (H&S 180/180, triple 187/219, cup 406). Two
deliberate divergences disclosed: rounding top 241→312 (the probe applied a cup-shaped depth guard
to the top branch; this uses the correct mirror) and triangles 3,680→3,621.

**Gate B:** future-perturbation mutants, four modules, `T → T // 2` back-dating. Real modules leak
0.0 at every J in {150,200,250,300}; the mutant is caught at some J. The J sweep is deliberate —
at a single J the mutant escapes for `triangle_wedge` (J=200) or `rounding_cup` (J≥250).

**Gate D:** bit-identical under ×8/×64 — `!=` on the arrays, no tolerance — 0 mismatches all four.

**Gate E, run in full against `IndicatorEngine(include_advanced=True)` = 485 columns**, closing the
gap CANDLE-0 recorded at §5 item 3. Largest |ρ| anywhere is **0.2911** (`TRPL_AGE` ×
`RPO_VA_WIDTH_PCT_110_80`, n=85,697) against a 0.76 disclosure line. Widening 112 → 485 moved the
maximum from 0.1452 to 0.2911 and changed no verdict.

⚠ **SIX columns were built, cleared Gate E, and were then DELETED on the INTERNAL overlap** —
`HS_SYM`, `HS_HEAD_EXC`, `TRPL_SPREAD`, `TRIW_CONV`, `CUP_R2`, `CUP_SYM`. Up to **ρ = 1.0000**
against a sibling magnitude. The mechanism is general and is the reusable finding here: a magnitude
that is nonzero only on its own event's support is, to a rank correlation, mostly a description of
that support (90,137 tied zeros vs 360 values), so two such columns correlate ≈1 whatever they
measure. **A SIGNED magnitude escapes it** — `CUP_DEPTH × CUP_CURV = 0.1307` on the identical
support. Read this before adding a magnitude column to any event-flag module in this fork.

⚠ **THE RECTANGLE IS SKIPPED. The pre-registered trigger FIRED and is honoured** —
`triangle_wedge` no longer matches it. Round 1 of this task shipped it and was wrong twice, both
errors pushing the same way:

1. **Wrong population.** The rectangle count came from a proxy mask over the PUBLISHED columns
   (`CONF & |SLOPE_UP|<0.0015 & |SLOPE_DN|<0.0015`). Those slopes are aggregated by max-|value|
   across every pattern confirming on the bar, so a rectangle co-confirming with a steeper triangle
   was erased. Measured on the same pool: **0 false positives, 59 false negatives** (214→248 up,
   202→227 down) and both recalls moved UP. The matcher's loop is now factored into `_scan`, which
   reports the exact branch, and `rect_lcb.csv` carries both masks side by side.
2. **Sample too small to decide.** 202–214 events, SE ≈ 0.032, so 0.69 sat *inside* the 1-SE band
   and round 1 resolved it on the third decimal, in its own favour.

**Tie-break rule adopted and written into the harness:** *when the pre-registered threshold lies
inside the measured statistic's 1-SE band, the trigger is FIRED unless a larger sample resolves
it.* `trigger_fires_1se_rule` and `trigger_fires_literal` are both CSV columns, so it cannot be
re-litigated after the fact. **Under that rule round 1's own numbers already fired the trigger** —
no new data was needed to get the right answer, only a rule fixed in advance.

Enlarged run, **250 tickers / 343,638 bars, exact mask** (`rect_lcb_large.csv`, engine-free path so
it is cheap): RECT_UP 811 events recall **0.7102 ± 0.0159**, RECT_DN 756 events **0.6958 ± 0.0167**.
Both clear 0.69 on the point estimate with 0.69 *below* the band — fires on the literal reading too.
Second trigger (Gate E |ρ| > 0.76 vs any LCB column) definitively not met: no `TRIW_*` column
reaches 0.14 against any of the 485. Against `LCB_FORMED_5` lift is *below 1* (0.78 / 0.94).
Measured cost of honouring it: 811/6,951 bull and 756/6,386 bear confirmations (11.7% / 11.8%).
`_scan(..., include_rect=True)` keeps the evidence reproducible after the decision.
Three post-hoc tiebreakers round 1 used to justify shipping are **struck** — all were discovered
after the number and none is in the pre-registration. No null band for the lifts; still open.

**Broadening / megaphone is NOT built** — CANDLE-0's DEFER honoured, and `triangle_wedge`'s shape
test rejects the diverging branch explicitly so it cannot creep in.

⚠ **Two NAMING defects found in round 2, both fixed, both invisible to the test that was watching.**
`rounding_cup` computed with `min_depth` but left it out of the suffix — `min_depth=0.05` fires 4
times and `0.30` fires 0 times under the SAME name `CUP_CONF_BULL_30_5_0.6_0.1`, a silent collision
in mined-rule strings. `triangle_wedge` did the mirror image: `tol` was in the name and never read,
so `tol=0.03` and `tol=0.99` gave bit-identical output under two names. Four literal-string
assertions could see neither. Replaced by a property test over every numeric parameter — *output
changed ⇒ name changed, output unchanged ⇒ name unchanged* — with a mutant test that rebuilds both
defects and proves the property fires on each.

⚠ **`*_PEND` columns were tagged `BIN` in the dictionary, and one case predates CANDLE-1.** The
probe reads observed cardinality on a 600-bar synthetic frame. Measured over 40 BIST frames /
71,402 bars, `HS_PEND` spans [−2,+2] and so does **`DTDB_PEND`**, which shipped long before this
task; `FLAG_PEND` genuinely spans [−1,+1] so `BIN` is right for it and a blanket name rule would
have mislabelled it. `gen_indicator_dictionary.py` now carries `FORM_OVERRIDES` listing the two
measured cases with their evidence.

**Not measured:** whether any of this PREDICTS anything (no return study), parameter sensitivity,
non-BIST behaviour, a null band for the ±3-bar lifts, and whether `dtdb` + a touch-count parameter
or `liquidity_compression_box` + a pivot-anchored boundary mode would have been better than two of
these modules. All five carried into `docs/CandlePatternsMeasured.md` §7.
✅ **CANDLE-2 — DONE 2026-09-08.** All three items closed.

1. **The 23 `CONST` tags are a FIXTURE artifact, not a defect** — and the dictionary now says
   so, from the generator so it survives regeneration. The probe runs one 600-bar synthetic
   frame in which rare patterns simply do not occur; CANDLE-0 measured the same set over 50
   BIST tickers / 91,197 daily bars and found **0 of 62 constant**. The dead-column table's
   own rule (*confirm on real data, then repair or delete*) was followed and the answer was
   that they are fine. **Do not delete those columns.**
2. **`talib` promoted out of `extras_require["dev"]` into its own `talib` extra** — it is the
   only optional dependency that changes what the package COMPUTES rather than what it can
   plot or test (2 patterns without it, 62 with), and burying it beside matplotlib and
   vectorbt made it read as a dev convenience. `pip install pandas-ta[talib]`.
3. **`tests/test_candle_patterns_reachable.py`** pins 62 columns, the 60-forwarded/2-native
   split, and non-constancy against the real parquet cache — with an explicit skip branch so
   a green run WITHOUT TA-Lib cannot be mistaken for a green run with it. That gap was real:
   `grep -rn "cdl_pattern" tests/` was empty before this.

⚠ Ties: overlap risk is highest against the SMC/structure ports (`bos`, `choch`, `zigzag_fib`) — those
are precedent for how a structure pattern gets measured. Feeds **MLCOL**.

## INDREF — per-indicator reference pages, then an engine-side results doc (NEW 2026-09-06, user)

> **Goal (user):** *"Backtest reports or analysis documents will add."*

✅ **INDREF-0 — DONE 2026-09-08.** `docs/indicators/tvstop.md` (the worked example),
`docs/indicators/_TEMPLATE.md`, and `tests/test_indref_pages.py` — the guard, which is the part that
makes INDREF-1 safe. Matches the parent's family-doc shape rather than inventing a second one.

The guard is group-anchored (`§<sec>#T<k>` / `§<sec>#P`) with declared counts, so adding or removing
any number fails the build; it covers prose and bullets, not only tables; and it was verified with
five negative controls including a fabricated number inside an already-registered section, which the
first version passed. `DERIVED` is a first-class provenance class beside QUOTED and MEASURED.

⚠ **The Gate C/D/E numbers on that page are QUOTED, and their CSVs are gone** — `backtest_results/`
is gitignored, so they were never committed. The page says so and names the re-run commands.
INDREF-1 hit exactly this for every indicator: most pages carry the stub token in
§6–§9 rather than a quoted number whose artifact nobody opened. (The 3-measured/230-stub split
first recorded here was itself wrong — see the round-2 note below; it is **40 / 193**.)

✅ **INDREF-1 — DONE 2026-09-10/11.** `docs/gen_indicator_pages.py` beside
`docs/gen_indicator_dictionary.py`, **233 pages** in `docs/indicators/` plus
`docs/indicators/README.md` as the index. `tests/test_indref_pages.py` is green over all of them:
**1,404 passed**, `python -m pytest tests/test_indref_pages.py -q`, **pytest exit 0**, re-run
2026-09-11. Measurements behind the pages were taken 2026-09-10 and are frozen in
`docs/indicators/_facts.json`; the full suite at that point was **2,983 passed / 0 failed / 23
skipped, exit 0** (1,585 before these pages existed — the pages add 1,398 guard cases).

**Round 2 (2026-09-11) — the Fletcher gate returned REVISE with two CRITICALs, both fixed and
re-emitted.** Both were the same defect: the generator stated the limits of its own greps as facts
about the world, in bold, with a machine's authority.

- 🔴 **Round 2 found both CRITICAL fixes had been applied to one cell each and not swept through
  the page**, so the top-of-page Gate-coverage banner still printed the round-1 sentence on 230
  pages and contradicted §7 on 33 of them; the banner and §7 now share one branch. The wiring cell's
  "not reached by **any** engine call path" was also a fresh absolute the source could not support —
  INDREF-2's facts cover only the two engine modules — so it is now scoped to those two modules and
  reports the Gate-E/analysis script count alongside, from a new `ANALYSIS_CALLERS()` scan.
- 🔴 **"not called by the parent engine" was false on 206 pages.** The cell was driven by a
  `ta.<name>(` literal grep, which is structurally blind to `getattr(ta, func_name)` over
  `INDICATOR_SPECS` (104 entries) and to import aliases (41). `kc`, `eom`, `squeeze` and 200-odd
  others are dispatched every run at `speedy_indicators.py:1064`. The generator now reads
  INDREF-2's measured swept set from `_indref2_facts.json`: **170 pages say "called by the parent
  engine" with the mechanism named, 62 say "not reached by the engine" scoped to the two modules
  actually scanned, 0 carry the old claim** — and 170 + 62 reconciles exactly with INDREF-2's swept 171 (minus protected `tvstop`)
  and never-swept 62. When that file is absent the cell degrades to naming the scan's limits, not
  asserting a negative.
- 🔴 **"No overlap campaign has been run for this indicator" was printed on pages whose Gate A–F
  record is in a tracked file two directories up** — `sarext` among them, whose Gate E is ρ +0.9850
  vs `dist_to_psar_pct` over 408,075 bars in `docs/TalibPortsMeasured.md`. The `measured` test was
  a filename match on `measure_<name>_overlap_full.py` and could not see a batch campaign. Now
  joins the four campaign docs (TALIB-1, ALTPORT, CANDLE-1, PINEBI-1c): **measured 3 → 40, stub
  230 → 193** (36 after round 2's first pass; 40 once the five probe-raising indicators, which have
  no probed columns to match on, were made to fall back to their declared stem — `sarext` was still
  being branded uncampaigned until then). The match is by emitted column name, and because a campaign doc names comparator
  columns as well as ported ones, the page says so explicitly and tells the reader to open the doc
  rather than guessing which it is — matching on the function name instead marked 47 indicators
  measured, which was the same overclaim with the opposite sign.
- Also fixed: probe-derived provenance rows no longer carry the frozen cache date as if it dated a
  live measurement; the five indicators whose probe raises now say "probe raised — see §2" instead
  of "— no probed column", which read as "emits nothing".
- Idempotence re-verified after all of it: `--check` → **changed=0**.

The guard was re-verified to BITE on a GENERATED page, not merely to pass: a fabricated row
(`| \`ROC_FAKE\` | 3.14 | 2,718 |`) inserted into `roc.md`'s already-registered §10 table failed
`test_every_number_group_is_covered_with_a_matching_count[roc.md]` with exit 1, and the page was
restored.

⚠ **The task line said "all 201" and that number was already stale by 32.** The live surface,
re-probed on the day: **224** registered in `Category`, **232** callable as `df.ta.<name>()`, **2**
callable on the module only. INDREF-1 therefore had to define "shipped" before it could count, and
the definition it applies — stated on the index page and in the generator's docstring — is
`Category` **plus** every callable the registry does not know about, **minus** `ma`. `ma` is a
moving-average *dispatcher* that emits no column of its own, which is not a fresh judgement:
`gen_indicator_dictionary.py` already carries `SKIP = {"ma"}` and the dictionary lists it under
*Not indicators*. The other nine unregistered callables (`beta`, `drawdown`, `ht_trendline`,
`hwma`, `mama`, `sarext`, `up_and_down_volume`, `volume_delta`, `vp`) each get a page whose header
says a `df.ta.strategy()` sweep skips them.

⚠ **193 of the 233 pages carry the stub token in §6–§9 (corrected in round 2 — it was reported as
230, which understated the measured set by an order of magnitude).** A page counts as measured if
any of three things holds: a harness named for that indicator exists
(`measure_<name>_overlap_full.py` — true for `dtdb` and `fvg`), one of the four batch campaign
documents names one of its emitted columns, or the page is hand-written (`tvstop`). The first test
alone branded `sarext` a stub while its Gate E (ρ +0.9850, n=408,075) sat in a tracked
`docs/TalibPortsMeasured.md`. The campaign match is by column name and **cannot separate a ported
column from a Gate E comparator** — matching on the function name instead swings the count to 47 by
catching every comparator mention — so each affected page states the ambiguity and points at the
document rather than guessing. It is a compromise, and the index says so.

Machine-filled from a real run: the header table's declared rows, §2 (columns, ML form, warm-up,
probe range, register verdict joined from `../Backtesting/docs/knowledgebase/IndicatorMLRegister.md`),
§3's module length, §5's leak flag, §10's mining greps, §12's Gate F count. Owed by a human and
stub-tokened: §1, §3's source identification, §4, §6–§9, §11, and the *effective defaults* row —
the last one deliberately, because `inspect.signature` reports `None` for every validated parameter
on this fork's ports and substituting the real value into a row labelled "declared signature" would
contradict the dictionary row beside it.

Slow inputs (the full-suite `--junitxml` run, the one-pass read of the gitignored
`backtest_results/` tree — 383 non-image files, 4.9 GB, measured by the generator on the run) are frozen in `docs/indicators/_facts.json`, so a plain re-run is
byte-stable and `python docs/gen_indicator_pages.py --check` exits 0 (verified: `changed=0`). Re-measure with
`--refresh-facts`; it takes tens of minutes and is the only path that touches the parent repo.

⚠ **Left for a human, named so nobody assumes otherwise:** the §1 paragraph, §3 provenance and §4
formula on 232 generated pages. The generator quotes the module docstring as a labelled *seed* and
refuses to promote it to §1, per `_TEMPLATE.md`. `tvstop.md` is `PROTECTED` in the generator and was
not regenerated.
- [x] **INDREF-2 — Engine-side results write-up. DONE 2026-09-11.**
  Which ported columns mining actually selected, which never fired, and what they cost in compute.
  **Deliverable:** `../Backtesting/docs/indicators/IndicatorSelectionResults.md` (233 rows, one per
  shipped indicator, each linking back to its INDREF-1 page), regenerated end-to-end by
  `../Backtesting/scripts/analysis/measure_indref2_selection.py --refresh` into
  `../Backtesting/docs/indicators/_indref2_facts.json`. No number on the page is hand-typed.

  **OUTCOME (all measured 2026-09-11, 6 cleaned BIST daily frames, 37,144 bars):**
  SELECTED **34** · NEVER SELECTED **60** · barred-by-`MiningConfig` **59** · SWEPT-BUT-CALL-FAILS
  **16** · SWEPT-BUT-EMITS-NOTHING **1** (`vp`) · NEVER FIRED **1** (`tod_profile` — 2 constant
  columns on daily bars, confirmed engine-side) · NEVER SWEPT **62** (= 233).
  Three states beyond the four the task named were forced by the data; each would have credited our
  own plumbing to the indicator if folded into "never selected". **175 of 233 (75%) were never in a
  position to be selected at all**, so the ties line's premise fails as stated. Compute:
  `IndicatorEngine(include_advanced=True).compute_all` measured at 66.1 s per ticker-history in the
  cached run, but an earlier run the same day measured ~20 s — **treat it as a 20–66 s band**, not
  a point (§8; needs N≥3 cached runs to settle).

  **Round 2 (2026-09-11) — the Fletcher gate returned REVISE on six load-bearing overclaims in the
  prose, all now corrected in the renderer and re-rendered.** The measurement scaffolding survived
  the gate intact; the failures were all in sentences the machine did not generate:
  - **"139 / 60%" and "only the 60 were genuinely passed over" were wrong.** The page's own §2
    measured that 73 indicators postdate the last mining run (2026-07-20) — and **36 of those sit
    inside the 60**. Corrected to **175 (75%)** and a genuinely-offered set of **24**.
  - **"34 indicators account for *every* feature reference"** contradicted §3 three sections
    earlier. It is **1118 of 1370 (82%)**; the rest name engine-native columns.
  - **"9.91 s provably wasted on barred columns, the specs can be skipped" was wrong by ~40×.** A
    consumer scan added to `analyse()` finds **9.66 s of the 9.91 s has a consumer outside mining**
    — `strategy_factory.py` builds named crossover strategies on 59 of the barred columns
    (`ha_HA_close`, `alma`, `vidya`, `mcgd`, `t3`, `rma`, …). Genuine orphan: **0.24 s**. Skipping
    those specs would have broken a shipped non-mining consumer.
  - **"never executed by anything in this repo"** was asserted after parsing two files. A repo-wide
    scan finds **21 of the 62 never-swept are executed by the Gate-E/overlap scripts** under
    `scripts/analysis/`. The defensible claim is "no *engine* call path reaches them".
  - **Tokeniser bug:** `[A-Za-z_]\w*` shattered the real column `BB_%B` into phantom tokens `BB_`
    and `B`, and minted `e` from float exponents — 12 uses over 3 non-features. Now matches the
    actual column list longest-first, with an assertion that no counted token is unknown. Distinct
    selection tokens 59 → **54**. No state flipped.
  - **The "RECALL LAW" was false as printed** (a dozen hand-typed figures in §2 and §6). Narrowed
    to §1 and §3–§9, with the cited-elsewhere figures marked as quoted, not re-measured.
  Also downgraded: §5c's shadowing claim now says co-existence, not causation, and no longer
  recommends swapping in `ta.zigzag` — `indicator_engine.py:1430` documents its `ZIGZAG` as
  LOOKAHEAD-CONTAMINATED and the fork's causality was never checked against it.

  **Two corrections to INDREF-1's cached facts** (both reproduce exactly, both mislead): the
  `ta.<name>(` scan finds 26 call sites but the engine actually sweeps **171** — 104 through
  `getattr(ta, func_name)` over `INDICATOR_SPECS` and 41 through import aliases, neither visible to
  a name grep; and the `StrategyMaster` stem scan is case-sensitive, so it reports 18 stems where
  exact column-token matching finds **34** indicators. The `backtest_results/` column is not a
  selection signal at all (`HARPARK`'s 215 "files" are 208 dumped `_work/*.parquet` frames).

  🔴 **New defect — §5d: 16 of the 104 `INDICATOR_SPECS` entries pass an arg list that does not
  match the pandas_ta signature** (`("kc", ["Close"], …)` where `ta.kc` needs high/low/close;
  `eom` given High/Low/Volume where the signature is high/low/close/volume). Each raises
  `TypeError` on every run and is swallowed by the bulk loop's bare `except: continue`, so
  `aberration`, `eom`, `hilo`, `kc`, `long_run`, `pdist`, `pgo`, `pvol`, `pvr`, `rvgi`,
  `short_run`, `smi`, `squeeze`, `thermo`, `trend_return`, `ttm_trend` **have never emitted a
  column in any mining run.** Reproduced independently on the main thread by AST-parsing the spec
  table and executing each entry through the engine's own `df.get(arg)` resolution: same 16 names,
  same exception strings, 104 specs.

  🔴 **And it is not one table — the same 16 are broken in all SIX copies** (verified 2026-09-11 by
  running every spec table the same way): `backtesting_engine/speedy_indicators.py` (104),
  `deploy/app/analysis/DailyAnalysis.py` (104), `MarketAnalysis.py` (104), `SpeedyAnalysis.py`
  (104), `SpeedyAnalysisUS.py` (106), and the untracked root `SpeedyAnalysisDaily.py` (104).
  Fix not attempted: out of INDREF-2's scope, it changes the engine's column set, and **four of
  the six are inside `deploy/`, where repairing the arg lists would make 16 indicators start
  emitting columns in the live container — a strategy-affecting change under the TRADING FREEZE.**
  Owner decision required before any of the six is touched.

  **New finding — §5c:** the engine keeps **private re-implementations of 14 fork indicators**
  (`bos`, `choch`, `ob`, `zigzag`, `halftrend`, `wavetrend`, `zscore`, `chop`, …), which is why 10
  of the 62 never-swept are never swept. 35 mined-rule references land on those private copies.
  This is FVGENG generalised.

⚠ Ties: the parent repo already runs a family-doc convention at `../Backtesting/docs/indicators/`
(`family-oscillator-momentum.md`, `family-trend-overlay.md`) — match it, don't invent a second shape.
INDREF-2 is the honest test of PINEBI and MLCOL: an indicator nothing selects is dead weight.

## TALIB — diff TA-Lib against the fork and port the gaps (NEW 2026-09-06, user)

> **Goal (user):** *"Review ta-lib & ta-lib-python repos to find new indicators."*

✅ **TALIB-1 — DONE 2026-09-08.** All ten `port` rows ported, measured through Gates A–F, and
**five columns deleted on their own Gate E measurement.** Full per-indicator table:
`docs/TalibPortsMeasured.md`. Tests: `tests/test_talib1_ports.py` (19, green, pytest exit 0).
Harness: `../Backtesting/scripts/analysis/measure_talib1_overlap_full.py` + CSVs under
`backtest_results/talib1/`.

**The tie was right: overlap was the whole risk, and it cost four columns.** Gate E ran against
the production `IndicatorEngine(include_advanced=True)` — 485 comparators, 89 BIST_100 daily
frames, 408,253 bars:

| deleted column | ρ | against |
|---|---|---|
| `SAREXTd_0.02_0.2` | +0.9850 | `dist_to_psar_pct` |
| `SAREXTs_0.02_0.2` | +0.9598 | `PSAR_Signal` (**stage 4 only** — see below) |
| `HT_TRENDLINE_DIST` | +0.9576 | `bias` |
| `MAMAf_0.5_0.05` | +0.9408 | `QQE_RSIMA` |
| `MAMAd_0.5_0.05` | +0.9148 | `NWE_MID_200_8.0_8.0` |

Every one is a "distance from a smoothed price", "distance from a SAR" or "SAR direction" shape
the engine already carries. The **eight** surviving columns are all under 0.76 and ship clean,
the highest being `HT_PHASOR_IP` at 0.7533.

⚠ **`SAREXTs` is the one to remember.** On the numeric grid it read +0.8393 — inside the
disclose band — and was about to ship on that number. `PSAR_Signal` is an OBJECT column holding
the strings "Bullish"/"Bearish", so `select_dtypes(include=[np.number])` drops it and the main
grid never compares a new SAR direction flag against the engine's existing one. Stage 4 coerces
the three non-numeric stop columns and re-measures: **+0.9598**. A max-ρ taken over the numeric
comparators alone is a measured number that is still wrong about what it measures. Stage 4 was
then widened to all fourteen candidates; `SAREXTs` is the only breach, and the eight shipped
columns top out at 0.4302 there.

**Three indicators were emptied of features by that.** `ht_trendline`, `mama` and `sarext` now
return TA-Lib's raw price levels, are OUT of `Category`, and sit in
`AnalysisIndicators.strategy`'s exclusion list beside `beta` — which is out because it needs a
BENCHMARK series a single-frame sweep cannot supply. All four stay callable as
`df.ta.<name>()` so the ports are not lost and Gate A stays reproducible; `emit_dist=True`
brings the deleted columns back for re-measurement only.

**The numerical finding worth not re-learning:** seven of the ten are ONE Hilbert state machine
(`pandas_ta/cycles/_hilbert.py`), and it has **two warm-ups** — 12 primed bars for the
lookback-32 read-outs, 37 for the lookback-63 ones. Using 12 everywhere reproduces `HT_DCPERIOD`
EXACTLY and leaves `HT_TRENDLINE` wrong by 0.18 and `HT_DCPHASE` by 70°, as a transient that
decays to exactly zero by ~bar 700 — invisible to any check run on the tail. Separately, the
Hilbert taps must be summed in TA-Lib's order: the algebraically identical one-liner is wrong by
1.1e-2 on MAMA, because MAMA's clamped alpha amplifies a 1-ulp `atan` difference into a factor
of ten.

⚠ **Left for the coordinator's single reconciliation.** `Category` moved **215 → 224 → 221**
during this task. `README.md` and `CLAUDE.md` were edited mid-task to 224 / 229 and are now
**STALE by 3 on the `Category` count** (correct: 221 registered, 229 accessors), so
`tests/test_readme_counts.py` is RED and that is this task's doing.
`docs/IndicatorDictionary.md` was regenerated mid-task and still documents the five DELETED
columns, so it must be regenerated again. All three were left alone once the coordinator
claimed them. `../AlternativeRepos/altrepo_talib.csv` and `IndicatorList.md` ARE regenerated
and green (`verify_gap_rows.py ta-lib` → `gap_rows: 0`, `reproducible: {}`;
`test_indicator_list_tables` + `test_altrepo_talib_csv` + `test_prose_counts_match_the_csvs` +
`test_talib1_ports` = 35 passed).

⚠ Ties: Coordinate with **CANDLE-2** so candle patterns are not ported twice. TALIB-2 supersedes
TALIB-0's "~158 functions" estimate with the measured 161.

## ALTREPO — the shared contract for `../AlternativeRepos/IndicatorList.md`

> **Goal (user):** *"We should review @AlternativeRepos sub folders. After carefully review we should
> list the absent indicator lists to the @AlternativeRepos/IndicatorList.md file."*

Not a task — the contract the three scans below share, so they produce one coherent file instead of
three shapes. **Scope decision (user, 2026-09-07): audit only.** These tasks produce the list and
stop; porting anything is a separate decision taken once the size of the gap is visible.

**Absent means absent, not unmatched (user, 2026-09-07).** Name-diff to enumerate candidates cheaply,
then **read the body before recording any row as covered**. This is not caution for its own sake:
PINEBI-0 shipped five `have` verdicts that were wrong on exactly this axis — `dm` (Demarker vs
Wilder's Directional Movement), `kcw` (Keltner width vs bands), `cagr` (two endpoints vs
whole-series), and `cross`/`crossunder` (either-direction vs upward-only). Each would have deleted a
real port silently.

⚠ **Name-level previews are inflated by 3-6× and must never be quoted as gap sizes.** The
name-diff said pandas-ta-classic 143/288, ta-lib-python 128/161, tti 57/58. The BEHAVIOURAL scans
measured **33**, **10** and **10**. tti is the proof of the point — it names its modules
`_average_true_range.py`, so almost nothing matches `atr` by string while most of it is shipped.

**Generated, not hand-written (user, 2026-09-07).** A hand list rots: a hand-typed split went stale
in three documents across four review rounds this week. Reuse the shape that survived —
`docs/gen_pine_builtin_coverage.py` → `docs/pine_builtin_coverage.csv` + a guard test:

- one scanner per repo writing a machine-readable CSV per repo (name · category · verdict ·
  `pandas_ta_equivalent` · `audited` · `audit_evidence` · note), plus `IndicatorList.md` as the
  human-readable merge that points at them;
- verdict vocabulary matching the existing CSV: `have` / `port` / `port - alternate impl` /
  `n/a - <reason>`;
- `audit_evidence` carrying a `path:line` + backticked token that a test opens and checks, exactly
  as `test_audited_rows_carry_their_evidence` does — a receipt whose format is checked but whose
  content is not was already caught once;
- a guard test asserting regeneration reproduces the committed verdicts.

⚠ **The three repos COLLIDE in-process (measured 2026-09-07).** `pandas_ta_classic` registers the
DataFrame accessor under the same name as this fork (`register_dataframe_accessor("ta")`,
`pandas_ta_classic/core.py:107`), so importing it replaces `df.ta` for every DataFrame built
afterwards — one in-process import in a guard test took the suite from green to **109 failures**.
Every scanner and verifier is therefore **subprocess-invoked**, and
`test_importing_classic_in_process_is_forbidden` blocks a re-add. **Check the same for
`ta-lib-python` and `tti` before importing either.**

⚠ **Licences (checked 2026-09-07): all three are permissive** — pandas-ta-classic MIT,
ta-lib-python BSD-2-Clause, tti MIT. No repeat of the `docs/pine` MPL problem, but attribution is
still required on any port, and none of these repos may be committed into this one.

## ALTFIX — finish the AlternativeRepos audit ✅ DONE 2026-09-08

> **Record:** `docs/reviews/auto-2026-09-08-altfix-pinebi-mlcol/99-summary.md`. Origin was the
> TTIND/MULTIL/TALIB batch hitting its 3-round cap with the pandas-ta-classic scan ESCALATED.

**All five closed** — ALTFIX-0 (`correl`/`CORREL` measured to `have`), -1 (one shared resolver:
`docs/_altrepo_resolve.py`), -2 (the gap guards re-run the resolver instead of listing yesterday's
mistakes), -3 (`seeding` promotion requires a non-degenerate single-column tail), -4 (counts are
generated and guarded, `IndicatorList.md` included).

**Measured gaps at close:** classic **19**, tti **10**, ta-lib **10**. All three verifiers report no
reproducible row. Suite 1344 passed / 22 skipped.

⚠ **The recurring defect was FOURTEEN false gap entries across seven review rounds**, not the eight
this section originally claimed — an indicator published as absent while the fork ships it. Root
cause was always the same: the probe called fork functions in one narrow way, so anything reachable
another way looked absent. **The structural fix is the part to remember** — a relation search now
gives an exact miss a path to `port - alternate impl`, because previously the code could only ever
upgrade to `have` on a bit-identical match and every false gap therefore had to be found by a human,
one at a time.

Two measurements worth keeping:
- `emv` **is** `ta.eom(length=1, divisor=1)` — Spearman +1.000000, residual 5.42e-20. Invisible until
  the surface swept length **1**; at the probed default the two correlate only +0.21.
- `fosc` is **not** `cfo`, despite the name and the docstrings. Peak +0.950818, residual 1.18 (17.6%
  relative) at every length and scalar tried. It stays in the gap, and its note names `cfo` as a
  measured near-miss so the next reader does not re-raise it.

⚠ **TALIB-1 is still open and unblocked by this** — its shortlist of 8 is named in
`docs/reviews/auto-2026-09-07-ttind-multil-talib/00-manifest.md`. It needs Gate E, a
`../Backtesting/` measurement the owner removed from both batches.
⚠ **Audit only** (ALTREPO scope decision). Do not port anything under this tag.

## ALTPORT — port the 20 measured AlternativeRepos gaps (NEW 2026-09-09, user)

> **Goal (user):** *"Do we have tasks for these new indicators from engine & AlternativeRepos? If not please create that tasks"* — the audit is finished and the gap is now a short, measured list; this is the decision about what to do with it.

**ALTREPO was scoped AUDIT ONLY (owner, 2026-09-07) and that scope is now spent.** The three
scanners hold, all three verifiers report no reproducible row, and the gap is **20 rows of 442
scanned**. This tag is the porting decision the audit deliberately deferred; ALTREPO itself stays
audit-only and must not grow port sub-items.

**Where the 442 went** (`../AlternativeRepos/*.csv`, regenerated 2026-09-09): `have` **184** ·
`port - alternate impl` **114** · **`port` 20** · `n/a` **115** · `unknown` **9**. ta-lib is at
**0** after TALIB-1.

⚠ **`port - alternate impl` (114) is NOT a queue.** Those are the same indicator with different
behaviour; porting one yields a variant, not a capability. PINEBI-1c did exactly that for 9 of
them, kept 7 on parameter reach alone, and its own write-up calls the result "a capability with no
customer" — zero call sites in either repo. Do not treat that column as backlog without a reason
per row.

- [x] **ALTPORT-0 — Triage the 20 before building anything (MAJOR). GATES the rest.** ✅ DONE 2026-09-09 (round 3)
      **OUTCOME: 7 BUILD / 13 SKIP — `docs/AltportTriage.md`**, measured by
      `docs/gen_altport0_triage.py` + `docs/scalecheck_altport0.py` on 12 BIST daily frames
      (52,022 bars). Rounds 2–3 retracted all three round-1 "identity" claims (`fosc`, `dx`,
      `VolatilityChaikins`) — each had been produced by transcribing the candidate with FORK
      helpers and comparing it to a FORK column — and REVERSED `smc_sweep` to BUILD on a
      coincidence test round 1 named but did not run. Verdicts survived; the stated reasons did not.
      ⚠ The checkbox was left open until 2026-09-10; closed as part of ALTPORT-1, which consumed it.
      The 11 classic rows are `adxr` `avolume` `ce` `cvi` `dx` `fosc` `hvol` `mavp` `msw`
      `smc_sweep` `vosc`. The 9 tti rows are `Envelopes` `MarketFacilitationIndex`
      `ProjectionBands` `ProjectionOscillator` `RangeIndicator` `RelativeMomentumIndex`
      `SwingIndex` `VolatilityChaikins` `WilliamsAccumulationDistribution`.
      Each already carries a measured note saying why it is not a rename of something shipped —
      e.g. `MarketFacilitationIndex` is Bill Williams `(high-low)/volume`, NOT the fork's `mfi`;
      `ProjectionOscillator` shares an acronym with the shipped `po` and is a different indicator.
      **Read those notes; do not re-derive them.**
      ⚠ **`fosc` is a known near-miss, not a clean gap** — it peaks at Spearman **+0.950818**
      against the fork's `cfo` at every length and scalar tried (residual 1.18, 17.6% relative).
      Same family, different maths. It is the row most likely to fail Gate E.
      **Done when:** every one of the 20 has a BUILD / SKIP verdict with a stated reason, and each
      BUILD names the economic question it answers that no shipped column answers. A SKIP is the
      expected outcome for several.
- [x] **ALTPORT-1 — Screen every BUILD against the production set BEFORE writing it (MAJOR, depends on ALTPORT-0).** ✅ DONE 2026-09-10 (round 3)
      Inverted deliberately: measure first, build second. The 2026-09-08 batch built ~35 columns
      and **deleted 12** on redundancy against columns the engine already ships —
      `NWE_MID_200_8.0_8.0`, `bias`, `dist_to_psar_pct`, `QQE_RSIMA`, `PSAR_Signal`. MLCOL-2
      shipped 0 of 5 for the same reason. Screening a formula against the shipped set is far
      cheaper than porting it through Gates A–F and then reverting it.
      ⚠ **Depends on `TVPTA-9` in `../Backtesting/TODO.md`** — Gate E currently drops object-dtype
      comparators via `select_dtypes`, which nearly shipped `SAREXTs` at 0.8393 when the true
      figure against `PSAR_Signal` is 0.9598. Screening before that fix lands measures against an
      incomplete set.
      **Done when:** each BUILD candidate has a max |ρ| against the full production config with its
      sample size, taken with non-numeric comparators included, and anything in the revert band is
      struck from the queue with the measurement recorded.
      **OUTCOME (round 3) — the two standards in this batch DISAGREE, and that is the finding.**
      Write-up: `docs/AltportScreen.md`. Harness
      `../Backtesting/scripts/analysis/measure_altport1_overlap_full.py` (8 stages, all exit 0);
      10 CSVs under `../Backtesting/backtest_results/altport1/`.
      * **Gate E band as written: 1 STRUCK / 4 ship-with-disclosure / 4 ship.**
        **ALTPORT-0's own applied standard (question-redundancy): 3 clear / 2 conditional /
        3 skipped / 1 struck.**
      * **492 comparators** (485 numeric + 1 bool + 6 ordered), **`n_unmapped` 0 AND
        `n_unmapped_values` 0** on all 89 rows; 89 BIST_100 daily frames / **408,253 bars**.
      * **STRUCK: `ProjectionOscillator` → `POSC_14`** — pooled |ρ| **0.894742** vs `cfo`,
        per-frame **median 0.910212, ≥0.90 on 62.9% of 89 frames**. Corroborating mechanism:
        `AltportTriage.md` row 10 SKIPs `fosc` at **0.967784 vs `CFO_14`** — the same
        linreg-forecast-residual collision against the same column. (The 0.950818 quoted at
        line 648 is a PROBE-frame figure, not the basis of that SKIP.)
      * **CLEAR on both standards (3): `cvi` → `CVI_10` 0.501290 · `MarketFacilitationIndex`
        → `MFI_BW_SF_20` 0.536816 (0.573380 after the quantisation correction) ·
        `smc_sweep` → `SMC_SWEEP` 0.161383**, whose event test now carries a chance baseline:
        observed 20.96% vs null **11.09 ± 0.36** (200 per-frame circular shifts),
        **enrichment 1.89×, z 27.4** — an UPPER BOUND on bar-level alignment.
      * **CONDITIONAL (2), together or not at all: `PB_UP_DIST_PCT` 0.773573 ·
        `PB_LO_DIST_PCT` 0.727354.** They are the same construction mirrored; splitting them
        on 0.046 of ρ would be a correlation gate, not the question gate ALTPORT-0 applied.
        One ruling decides both: *is a slope-corrected extreme a different question from a raw one?*
      * **SKIPPED on question-redundancy (3): `HVOL_20` 0.834724 vs `natr` · `PB_WIDTH_PCT`
        0.874411 vs `natr` · `WAD_BAR_SF` 0.889416 vs the signed daily return.** ALTPORT-0
        SKIPped `vosc` at **0.753468** on exactly this test — these are 0.83–0.89.
        Shippable under the Gate E band alone; that is a choice to be made explicitly.
      * New guard: `../Backtesting/tests/test_comparators.py` — **14 passed, pytest exit 0**.
      🔴 **ALTPORT-2 MUST NOT START until the owner rules on (a) the standards clash and
      (b) the slope-correction question.** The input set is 3, 5, or 8 columns depending on both.
      ⚠ **`CLAUDE.md:98` has no rule for 0.80–0.90.** Round 3 resolves it on the PER-FRAME
      median at the same 0.90 the band already names — no new constant. (Round 2 used a
      fitted `REVERT_APPROX = 0.89`, deleted.) `docs/AltportScreen.md` proposes an exact
      replacement; its `pct_frames_ge_090 >= 25%` clause is calibrated on ONE datapoint and
      is marked provisional. **Owner decision pending — not applied.**
      ⚠ **Gate D was RUN, not inferred: 6 of 9 columns are NOT bit-identical at ×8/×64**
      (tti's fixed-decimal rounding; `POSC_14` worst at 0.4807; NaN masks match on all 18
      cells). ALTPORT-2 must re-run Gate D bit-identical on the ported fork implementation.
      ⚠ **`MFI_BW_SF_20` is a LOCAL construction around a DECORATIVE tti call** — tti returns
      `(h−l)/volume` and the form multiplies volume back out (verified: tti `mfi` vs a local
      `(h−l)/volume`, max|d| **4.99908e-11**). Its Gate A must go to Bill Williams directly.
      ⚠ **`TVPTA-9` still OPEN** — this fixed ONE harness; ~14 others still `select_dtypes`.

- [ ] **ALTPORT-2 — Port the survivors through Gates A–F (MAJOR, depends on ALTPORT-1).**
      Five wiring touch points per `CLAUDE.md`. Attribution: pandas-ta-classic is MIT, tti is MIT —
      permissive, but attribution is still required on any port and neither repo may be committed
      into this one.
      ⚠ **Gate B needs the right mutant.** Prefix truncation cannot certify anchor-sparse or
      event-flag output — a back-dating mutant scores 0.0 under it AND under endpoint rescanning.
      Use future-perturbation, and SWEEP the perturbation point: CANDLE-1's mutant escapes at
      J=200 for one module and J≥250 for another. See
      `tests/test_pinebi_1e_utilities.py::test_pivot_is_causal_with_a_mutant`.
      ⚠ **Gate D is bit-identical** at x8/x64 (`== 0.0`, not a tolerance).
      ⚠ For any event-flag column, screen the **tied-zero trap**: an unsigned magnitude nonzero
      only on its own event's support is mostly a description of that support — two such columns
      correlate ρ ≈ 1.0000. Signing one escapes it.
      **Done when:** each survivor ships with a test module, a measured Gate E max with its sample
      size, and `docs/IndicatorDictionary.md` regenerated; reverted candidates stay in the write-up
      with their measurement, as `docs/TalibPortsMeasured.md` does.

⚠ Ties: extends the **ALTREPO** contract (audit-only; this tag owns the porting). Consumes
`../AlternativeRepos/IndicatorList.md` + the three CSVs. Engine-side consumption is **TVPTA-8** in
`../Backtesting/TODO.md`, and the Gate E correctness fix it depends on is **TVPTA-9**. Precedent
for the measure-then-delete discipline: `docs/TalibPortsMeasured.md`,
`docs/CandlePatternsMeasured.md`, `docs/PineAlternatesMeasured.md`.


## MLCOL — per-indicator ML companion columns (NEW 2026-09-06, user)

> **Goal (user):** *"We should optimize each indicator for ML. Each indicator should show binary fields
> like cheap, expensive or buy & sell type of things. Also it should include percentage based analysis."*

**Decision (user, 2026-09-06):** hand-authored per indicator, not a generic transform layer — the
threshold that means "expensive" is indicator-specific and a generic percentile is wrong for bounded
oscillators and event flags.


✅ **MLCOL-0 — DONE 2026-09-08.** Contract written at `docs/MLCompanionContract.md`; the four
primitives ship in `pandas_ta/ml/companions.py` (`ml_state`, `ml_dist_pct`, `ml_bars_since`,
`ml_rate`). Three shapes, measured against the dictionary: **126 PX · 169 SF · 90 BIN · 2 PX2**.

The finding that shaped the contract, and the reason MLCOL-1 must follow it rather than improvise:
**a trailing quantile on a price LEVEL does not give the nominal tails.** On a 1500-bar walk at
`length=252`, `|STATE| == 2` covers **31.4%** of settled bars against the 10% a 5/95 split implies —
a non-stationary series sits at its own window extreme constantly. Ranking the DISTANCE instead gives
**9.9%**. So a `PX` parent's STATE is computed on its `DIST_PCT`, never on the raw level, and
`ml_state` now **enforces that by measurement rather than by column name** — there is no PX registry
to check a name against, and a name check passes every renamed column. Pass
`allow_nonstationary=True` to override deliberately.

- [ ] **MLCOL-1 — Roll the contract out, PX columns first (MAJOR, UNBLOCKED — MLCOL-0 done).** Order the work
  by the dictionary's *"Needs a transform before modelling"* table — those indicators are unusable as
  features today, so they pay back first.
  **Done when:** every `PX` column in the dictionary has a scale-free companion, and the regenerated
  dictionary shows no indicator whose entire output is `PX`.
  ⚠ **Owner's sequencing (2026-09-08): "contract, then roll out with Gate E per companion."** Gate E
  is per companion, not once at the end — one measurement per PX column. (For the count, read the
  opening paragraph of `docs/MLCompanionContract.md`; it is Counter-derived from the generated
  dictionary and asserted by `tests/test_ml_companions.py`. Four different numbers for that one
  quantity were in circulation on 2026-09-08 — do not retype it.)
  ⚠ **MLCOL-2 added a prerequisite screen:** Gate E is necessary but NOT sufficient (it would have
  shipped `FVG_BULL_RATE_60`), and every MA-family `DIST_PCT` must be checked against the engine's
  existing relational columns first — `SMA_10_DIST_PCT` died at ρ 0.946 against `NWE_MID_200_8.0_8.0`.
  Use `measure_ml_companion_overlap.py --companions`.
✅ **MLCOL-2 — DONE 2026-09-08 (round 2).** Harness at
`../Backtesting/scripts/analysis/measure_ml_companion_overlap.py` + 4 CSVs in
`../Backtesting/backtest_results/tvpta6/`. Grid: 30 BIST_100 daily frames, **139,657 pooled bars**,
against the **485** numeric columns of `IndicatorEngine(include_advanced=True)` — the production
config, not the `include_advanced=False` earlier scripts used. (485 includes 5 raw OHLCV inputs and
2 all-NaN intraday-only `TOD_SLOT_*`; **483 effective, 478 computed**.)
⚠ `--companions` **SUBSETS a hard-coded `COMPANIONS` registry** and raises on any name not in it —
MLCOL-1 extends the harness by ADDING registry entries, then re-runs stage 1, which builds only the
companions missing from the existing cache as per-ticker sidecars (one new companion costs one
column, not a 30-frame `compute_all` sweep).

## **ALL 5 reference companions were DELETED. MLCOL-2 ships 0 of 5.**

That is a finding, not a failure. **Round 1 of this task claimed 2 SHIPs and both were wrong**,
reversed by two controls round 1 did not run: a PLACEBO on the conditional axis (the same statistic
on the PARENT, over the same bins and rows) and an ACROSS-SEED error band on the model axis
(5 seeds × 3 split points, plus a shuffled-NULL column).

| companion | ρ vs parent | max ρ vs shipped set (n) | perm. imp. (**sd across 15 fits**) | cond. ρ vs **placebo** (fwd5) | verdict |
|---|---|---|---|---|---|
| `RSI_STATE` | +0.5886 | 0.5950 (n=139,237) | +0.00013 (**0.00067**), beats null 7/15 | −0.0372 vs −0.0226 | **DELETE** |
| `SMA_10_DIST_PCT` | +0.0079 | **0.9462** `NWE_MID_200_8.0_8.0` (n=133,657) | +0.00194 (**0.00239**) | +0.0253 vs −0.0118, CI straddles 0 | **DELETE — revert band** |
| `SMA_10_DIST_PCT_STATE` | +0.8877 | 0.8347 (n=133,657) | +0.00028 (**0.00226**) | −0.0067 vs +0.0036 | **DELETE** |
| `FVG_BULL_BARS_SINCE` | −0.6260 | 0.5861 (n=138,692) | +0.00128 (**0.00264**), beats null 9/15 | −0.0166 vs **+0.0162**, excess **+0.0004** | **DELETE** |
| `FVG_BULL_RATE_60` | +0.1604 | 0.5533 (n=137,347) | +0.00079 (**0.00392**) | +0.0060 vs +0.0162 | **DELETE** |

⚠ The `n` column is the SAMPLE SIZE of the max-ρ cell, not a row count.
⚠ `RSI_STATE`'s conditional cell used **3 of 10 parent bins, 12,529 of 41,761 test rows** — it is
constant inside the other seven RSI deciles. Both `FVG_BULL` companions condition on **1 bin**
(binary parent), i.e. "bars where the flag did not fire".

Findings that change how MLCOL-1 must be run:
- **Gate E is necessary and NOT sufficient.** Three of the five clear Gate E outright (0.595 / 0.586
  / 0.553) and none survives. Gate E alone would have shipped `FVG_BULL_RATE_60`.
- **The DIST_PCT shape works and still dies.** ρ +0.008 against its own `SMA_10` parent means the
  distance form genuinely stripped the price level; it is killed by the engine ALREADY shipping the
  construction (`NWE_MID_200_8.0_8.0` at 0.946, `bias` at 0.849). **Screen every MA-family
  `DIST_PCT` against `NWE_MID` / `bias` / `dist_to_psar_pct` / `ATR_POSITION` / `BB_%B` / `ZSCORE_20`
  BEFORE building it.** ⚠ This is a RE-DERIVATION: `iama` was measured at ρ 0.9498 against the same
  column and un-wired for it on 2026-08-14 —
  `../Backtesting/scripts/utils/gen_indicator_register.py:643-645`.
- **A STATE on a continuous parent is a deterministic coarsening.** It cannot add information, only
  representation, and this fork's consumer is a TREE miner that can already express a threshold.
  Both STATE companions died. `ml_state`'s value has to be argued from the consumer, not assumed.
- **Names drift between repos**: the contract says `RSI_14`, the engine ships `RSI`
  (`speedy_indicators.py:30`). MLCOL-1 will hit this for every parent.
- **Thresholds were NOT pre-registered** (`COND_Z_MIN`, `COND_RHO_FLOOR`), and the run now proves
  they are not load-bearing: a sensitivity sweep over z ∈ {2.5, 3.0, 3.5} × ρ_floor ∈ {0.005, 0.01,
  0.02} returns DELETE in all 9 cells for all 5 companions — `verdicts that MOVE across the grid:
  none`. Multiplicity is Bonferroni-corrected over the 10-test family (critical |z| = 2.807).

Nothing was removed from `pandas_ta/ml/companions.py` — it ships the four PRIMITIVES, not per-parent
columns, and no measurement in either round found a defect in a primitive.

⚠ Ties: this is the fork's stated purpose — see `CLAUDE.md` → *The ML feature contract* and the README's
ML rules. `ichimoku_ml` is the reference precedent (5 price lines → 8 scale-free causal columns).
Depends on **WIRING-1** (bulk runs) and interacts with **MULTIL** (companions multiply per length).
