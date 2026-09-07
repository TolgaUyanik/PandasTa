# PandasTa Tolga Uyanik's Fork To-do's

Library-scoped work only. Engine-side work (mining, wiring, live book) lives in
`../Backtesting/TODO.md` — the pine-porting initiative **TVPTA** (TVPTA-0 … TVPTA-7b) is there, and
several sections below extend it rather than restarting it.

Port protocol every section here is bound by: `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`
(Gates A–F; overlap ρ ≥ ~0.9 → revert, 0.76–0.80 → ship with disclosure, < 0.76 → ship).
Column inventory and ML form of everything currently shipped: `docs/IndicatorDictionary.md`.

---

# ═══ ACTIVE ═══

**Nothing active.** The AlternativeRepos audit ran 2026-09-07/08: TTIND-0/-1, MULTIL-0 and
TALIB-0 are DONE and removed from this file; what remains is **ALTFIX** in the BACKLOG band — six
findings the 3-round review cap left open. Read
`docs/reviews/auto-2026-09-07-ttind-multil-talib/99-summary.md` before touching any scanner.

⚠ **FVGENG moved to `../Backtesting/TODO.md` on 2026-09-07 (owner: "we will not work on mining
relevant tasks").** Both items were `../Backtesting/` and `deploy/` work and only lived here
because FVGDEAD-1 spun them out during a review of this fork. The `fvg` repair itself is done and
shipped here; what moved is the engine/live follow-up.

⚠ **Completed and removed from this file:** WIRING-1/-2/-3, FVGDEAD-0/-1, SQZOFF-0, FVGENG-0,
PINEBI-0, PINEBI-1a (2026-09-07); TTIND-0/-1, MULTIL-0, TALIB-0 and the PTCLASSIC pair
(2026-09-08 — see `docs/reviews/auto-2026-09-07-ttind-multil-talib/`). Full detail — what was found, every review
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
| `have` | 55 |
| `port - primitive` (→ -1a) | 18 |
| `port` (→ -1b) | 16 |
| `port - alternate impl` (→ -1c) | 9 |
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

- [ ] **PINEBI-0b — Audit the remaining 40 `have` rows (MAJOR, NEW 2026-09-07 round 6).**
  A `have` verdict asserts that a Pine name is already covered by a pandas_ta function, and it removes
  that name from every port task permanently. **Three such assertions have been wrong so far** — `kcw`
  (Keltner width vs bands), `dm` (Demarker vs Directional Movement) and `cagr` (two arbitrary
  endpoints vs a whole-series scalar) — and each was found only when somebody finally read the source
  rather than the name.
  The CSV now carries an `audited` column with the EVIDENCE for each claim: **15 rows yes, 40 rows no**. Round 7 shrank the `yes` side deliberately: 13 names had been certified on the library's
  one-line `@function` summary alone, and four such certifications (`trima`, `stc`, `aroon`,
  `kvo`) turned out to be divergent. Only comparisons with a `file:line` receipt count now.
  **Done when:** every `have` row reads `audited=yes` with a `file:line` receipt in `audit_evidence`, each having been checked by comparing what the
  two implementations compute and emit — not their names; divergences that survive as `have` carry a
  `SEMANTIC_CAVEAT` — read `gen.SEMANTIC_CAVEAT`, not a list here, which drifted to 11 names while the
  map held 15; and anything that is not the same indicator moves to -1b.
  ⚠ `test_have_rows_declare_whether_anyone_checked_them` currently asserts the backlog is non-empty.
  Delete that assertion with this task.

- [ ] **PINEBI-1b — Port the 16 `port` rows (MAJOR, depends on PINEBI-0).**
  ROWS: `dm`, `frama`, `ht`, `ift`, `kcw`, `pzo`, `relativeVolume`, `rms`, `rwi`, `stc`, `szo`, `vStop`, `vStop2`, `vzo`, `williamsFractal`, `wpo`
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
  method that had already caught `ft` (Fisher) and `vi` (Vortex). ⚠ **12 of the 17 tier-2 `have` rows remain unread** — round 7 withdrew certifications that had been
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
- [ ] **PINEBI-1c — Port the 9 alternate implementations, and keep only the ones that differ (MAJOR,
  depends on PINEBI-0).** 
  ROWS: `atr2`, `dema2`, `ema2`, `rma2`, `stochFull`, `stochRsi`, `supertrend2`, `t3Alt`, `tema2` All nine have a shipped sibling; the differences to measure are warm-up and
  reachable parameters, not whether a sibling exists. Each restates an indicator the fork already ships, so Gate E will read ρ ≈ 1.0 against its
  own sibling and the revert rule would delete all nine on sight. **That rule is suspended here for one
  measured reason:** the alternates differ in *seeding and smoothing*, not in signal — `ta.ema2` is
  documented in the corpus as "extends `ta.ema` to start without delay at first bar and deliver usable
  data instead of `na`", which is a **warm-up** difference, and warm-up is a cost this fork's ML rules
  care about (`docs/IndicatorDictionary.md` prints a warm-up column for every indicator).
  So the acceptance test is not overlap, it is warm-up and parameter reach:
  **Done when:** each of the 9 is measured against its shipped sibling on two axes — bars of warm-up
  saved, and any parameter the sibling cannot express (`stochFull`'s separate %K smoothing, `t3Alt`'s
  volume factor) — and the ones that save no warm-up and reach no new parameter are **deleted, not
  shipped**, with the measurement recorded. Survivors ship named `<name>2` or `<name>_tv` so the
  distinction is visible in a column name.
- [ ] **PINEBI-1d — Implement the 2 lower-timeframe data requests behind a capability check (MAJOR,
  depends on PINEBI-0; the data source is the blocker, not the code).** `requestVolumeDelta` and
  `requestUpAndDownVolume` split a bar's volume into buying and selling pressure using intrabar data.
  The engine's floor is 1h and yfinance serves sub-hourly bars for ~60 days only, so on today's data
  these produce a short, ragged column — which is a data problem, not a reason to skip the port.
  **Done when:** both exist, take an explicit lower-timeframe frame as an argument rather than fetching
  one, raise a clear error when it is missing, and carry a test on a synthetic 1h-from-5m fixture. A
  companion note in `docs/` states how much history the current data source can actually feed them.
- [ ] **PINEBI-1e — Add the remaining 4 "noise" functions as ML utilities (MINOR, depends on
  PINEBI-0).** `sum`, `pivot`, `normalize`, `covariance`.
  ⚠ **Scope corrected in review round 2: `max` and `min` are NO LONGER here.** They are core Pine
  built-ins returning all-time extremes and shipped in -1a; the earlier wording had them as rolling
  fork utilities, which was wrong twice over.
  Of the four that remain, none is called live in the corpus: the hits are comments and third-party
  library methods (one literally reads *"Pine has no native ta.covariance"*). `ta.sum` IS a real
  built-in (sliding sum) — it simply never appears outside a comment here, so there is nothing to
  port against and it would be a fork utility either way. They are added because the fork wants them,
  documented with no TradingView provenance and **no MPL attribution**, which would be false.
All four are fork utilities in -1e, not `_pine.py` primitives — `_pine.py` is for things Pine
  actually calls, and none of these is called live here. `sum` is a rolling sliding sum; `pivot` is
  classic pivot-point levels (PP/R1-R3/S1-S3 — measure against `pivot_point_levels`, already shipped
  in -1a with all 11 Traditional levels); `normalize` is rolling min-max scaling; `covariance` is
  rolling covariance.
  **Done when:** all **4** exist with tests; `pivot`'s levels ship **only** as scale-free distances
  from `close`, never as raw price levels (the dictionary's `PX` rule); and `normalize`'s window is
  causal (trailing min/max, never whole-series, which would leak the future into every bar).
- [ ] **PINEBI-2 — Resume the community corpus after the built-ins (MAJOR, depends on PINEBI-1a…-1e).**
  `docs/pine/` holds 2,211 `.pine` files, untracked since 2026-09-07 (912 are MPL-2.0
  © TradingView; root `LICENSE` is MIT). TVPTA already ported 195 and left two queues:
  the 43-candidate `defer` backlog (TVPTA-6) and the 992 never-scanned `library`-type files (TVPTA-1b).
  **Done when:** this repo's side of whichever queue is picked is ported and green; the queue's own
  acceptance criteria stay owned by the parent task.

⚠ Ties: extends **TVPTA-1b** (`../Backtesting/TODO.md:489`) and **TVPTA-6** (`:253`) — do not open a
third pine initiative. `docs/pine/` is currently neither committed nor gitignored; decide which in
PINEBI-0. `williamsFractal` (-1b) overlaps the engine's existing `FRACTAL_UP`/`FRACTAL_DN` columns and
`ta.pivothigh`/`ta.pivotlow` (-1a) — measure all three against each other before shipping any.
The other 6 `© TradingView` libraries on disk (`ZigZag`, `zigzag-force`, `RiskMetrics`, `ValueAtTime`,
`Request`, `Color`) are unaudited; `ZigZag`/`zigzag-force` overlap the shipped `zigzag`/`zigzag_fib`.

## CANDLE — generic multi-bar chart patterns (NEW 2026-09-06, user)

> **Goal (user):** *"We should review add generic candle patterns like shoulder head shoulder."*

- [ ] **CANDLE-0 — Decide the pattern list and prove each one is not already covered (MAJOR).** The
  `candles` category ships 5 modules (`cdl_doji`, `cdl_inside`, `cdl_pattern`, `cdl_z`, `ha`), and
  `cdl_pattern` is a TA-Lib wrapper — **TA-Lib is not installed in this environment**, so its ~60
  patterns are unreachable (the probe prints `[X] Please install TA-Lib to use <pattern>` for each).
  Multi-bar structure is partly covered already by `zigzag`, `zigzag_fib`, `swing_equilibrium`,
  `equal_highs_lows`, `bos`, `choch`.
  **Done when:** a shortlist exists (head-and-shoulders, double top/bottom, triangle, wedge, …) where
  each entry states which existing column it might restate and why it is still worth measuring.
- [ ] **CANDLE-1 — Implement the shortlist as scale-free, causal columns (MAJOR, depends on CANDLE-0).**
  A pattern must emit a *feature*, not a drawing: confirmation flag, bars-since, and the pattern's
  measured move as a fraction of price — never pixel geometry or absolute levels.
  **Done when:** each pattern has a test module including the Gate B mutant test, Gate D scale
  invariance, and a Gate E overlap max against the full shipped column set.
- [ ] **CANDLE-2 — Settle the TA-Lib question (MINOR).** Either add TA-Lib as an optional-but-tested
  dependency so `cdl_pattern`'s 60 patterns become reachable, or document them as unavailable.
  **Done when:** `docs/IndicatorDictionary.md` states which candle patterns are actually callable.

⚠ Ties: overlap risk is highest against the SMC/structure ports (`bos`, `choch`, `zigzag_fib`) — those
are precedent for how a structure pattern gets measured. Feeds **MLCOL**.

## INDREF — per-indicator reference pages, then an engine-side results doc (NEW 2026-09-06, user)

> **Goal (user):** *"Backtest reports or analysis documents will add."*

- [ ] **INDREF-0 — Define the page template on one indicator (MINOR).** Sections: what it measures ·
  columns and ML form (pull from `docs/IndicatorDictionary.md`) · Pine/TA-Lib provenance · measured
  overlap max with sample size · reachability counts on real data · whether mining has ever selected it.
  **Done when:** one page exists (suggest `tvstop` — its measurements are already recorded) and reads
  end-to-end without a reader needing the git log.
- [ ] **INDREF-1 — Generate the pages for every shipped indicator (MAJOR, depends on INDREF-0).**
  Machine-fill everything the dictionary probe already knows; hand-write only provenance and the
  "what it measures" paragraph.
  **Done when:** `docs/indicators/<name>.md` exists for all 201, an index page links them, and the
  generator is committed next to `docs/gen_indicator_dictionary.py`.
- [ ] **INDREF-2 — Engine-side results write-up (MAJOR, depends on INDREF-1, lands in `../Backtesting/docs/`).**
  Which ported columns mining actually selected, which never fired, and what they cost in compute.
  **Done when:** the doc names, per indicator, selected / never-selected / never-fired, and links back
  to the INDREF page.

⚠ Ties: the parent repo already runs a family-doc convention at `../Backtesting/docs/indicators/`
(`family-oscillator-momentum.md`, `family-trend-overlay.md`) — match it, don't invent a second shape.
INDREF-2 is the honest test of PINEBI and MLCOL: an indicator nothing selects is dead weight.

## TALIB — diff TA-Lib against the fork and port the gaps (NEW 2026-09-06, user)

> **Goal (user):** *"Review ta-lib & ta-lib-python repos to find new indicators."*

- [ ] **TALIB-1 — Port the `port` rows (MAJOR, depends on TALIB-0).** Same five touch points and Gates
  A–F; the Pine-source citation in Gate A becomes the TA-Lib C source or the documented formula.
  **Done when:** each new indicator ships with a test module and a measured overlap max, and the
  dictionary is regenerated.

⚠ Ties: overlap is the whole risk here — TA-Lib and pandas_ta share heritage, so expect ρ ≈ 0.9
reverts. Coordinate with **CANDLE-2** so candle patterns are not ported twice. TALIB-2 supersedes
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

## ALTFIX — finish the AlternativeRepos audit (NEW 2026-09-08, from the 3-round review cap)

> **Origin:** the TTIND/MULTIL/TALIB batch hit its 3-round review cap with TALIB-2 and the
> pandas-ta-classic scan ESCALATED. Full record: `docs/reviews/auto-2026-09-07-ttind-multil-talib/`
> (`99-summary.md` is the entry point). TTIND-0/-1, MULTIL-0 and TALIB-0 are DONE and removed.

**What shipped and is sound:** three behavioural scanners with 40 guard tests,
`../AlternativeRepos/IndicatorList.md` with every table generated from its CSV, and
`../AlternativeRepos/*.csv` carrying `probe_env` stamps. Gaps as of 2026-09-08: classic **33**,
tti **10**, ta-lib **10**.

⚠ **The recurring defect: eight false gap entries across three rounds** — an indicator published as
absent while the fork ships it. Every one had the same root cause: the probe called fork functions in
exactly one narrow way (default kwargs, close-only inputs, default windows), so anything reachable
another way looked absent. Rounds 1-2 hardened the tti and ta-lib scanners and left the classic one
untouched, and the defect simply moved there.

- [ ] **ALTFIX-0 — Measure `correl` / `CORREL` (MAJOR).** Both CSVs carry
  `unknown - not comparable`; the measured answer is `have` —
  `pandas_ta_classic.correl` vs `ta.correlation` **0.0**, `talib.CORREL` vs `ta.correlation`
  **7.836e-12**. The two-series channel exists in the classic scanner but `classify()` does not reach
  it, and the ta-lib scanner has none.
  **Done when:** both rows read `have` with a receipt, and no row anywhere reads
  `unknown - not comparable` without naming the signature the harness cannot build.
- [ ] **ALTFIX-1 — Give the classic scanner the pinned-window retry (MAJOR).** `linregslope`,
  `linregangle`, `linregintercept` and `tsf` read `port - alternate impl` because the scanner compares
  at each side's own default window. At a matched window they are `have` (slope **1.829e-14**, angle
  **1.035e-12**). No longer false absences, still the wrong verdict.
  **Done when:** the three scanners share ONE resolver — kwargs variants, pinned window, two-series,
  cross-name search — so they cannot disagree about the same fork function again.
- [ ] **ALTFIX-2 — Make the gap guards derive their answer instead of listing yesterday's mistakes
  (MAJOR).** `test_absence_was_searched_for_not_assumed` and
  `test_no_gap_row_names_something_the_fork_actually_ships` are allowlists of names a reviewer already
  caught; they cannot catch occurrence nine. `test_a_mapped_name_is_never_reported_as_absent` cannot
  fail at all — it looks for `port` rows with a non-empty equivalent, and the only path emitting
  `port` hard-codes an empty one.
  **Done when:** for every `port` row the test RE-RUNS the resolver and asserts nothing on the fork
  surface reproduces the output. Keep the allowlists as regression pins underneath.
- [ ] **ALTFIX-3 — Harden the `seeding` promotion (MINOR).** `_tail_diff` promotes to `have` when the
  final quarter agrees to 1e-6, with no degeneracy check, and `ravel()`s multi-column frames into a
  meaningless interleaving. Three rows ride it today and all three are genuine.
  **Done when:** the tail must be non-degenerate and single-column on both sides, else no promotion.
- [ ] **ALTFIX-4 — Generate the counts in the manifest and the TODO files (MINOR).** Only
  `IndicatorList.md` is generated and guarded. Hand-typed counts elsewhere are bound to nothing —
  which is exactly where the `rsi` kept set drifted (`7 28` published against a CSV saying `7 50`).
  **Done when:** the marker/generate/guard pattern covers the manifest's count block, or a test
  cross-checks every digit adjacent to a verdict word against the CSVs.

⚠ **TALIB-1 is still open and unblocked by this** — its shortlist of 8 is named in
`docs/reviews/auto-2026-09-07-ttind-multil-talib/00-manifest.md`. It needs Gate E, a
`../Backtesting/` measurement the owner removed from that batch.
⚠ **Audit only** (ALTREPO scope decision). Do not port anything under this tag.

## MLCOL — per-indicator ML companion columns (NEW 2026-09-06, user)

> **Goal (user):** *"We should optimize each indicator for ML. Each indicator should show binary fields
> like cheap, expensive or buy & sell type of things. Also it should include percentage based analysis."*

**Decision (user, 2026-09-06):** hand-authored per indicator, not a generic transform layer — the
threshold that means "expensive" is indicator-specific and a generic percentile is wrong for bounded
oscillators and event flags.


- [ ] **MLCOL-0 — Design the column contract on three indicators first (MAJOR). GATES the rest.** Pick
  one bounded oscillator (`rsi`), one price-scaled overlay (`sma`), one event flag (`fvg`) and define
  the companion set for each: the binary state(s), the percentage/percentile form, and the naming
  pattern. Note that `docs/IndicatorDictionary.md` already flags which of the 201 emit price levels
  (`PX`) and therefore *need* a relational companion before they are usable at all.
  **Done when:** the three are implemented, named consistently, and the contract is written down in
  `docs/` so the remaining ~198 are mechanical.
- [ ] **MLCOL-1 — Roll the contract out, PX columns first (MAJOR, depends on MLCOL-0).** Order the work
  by the dictionary's *"Needs a transform before modelling"* table — those indicators are unusable as
  features today, so they pay back first.
  **Done when:** every `PX` column in the dictionary has a scale-free companion, and the regenerated
  dictionary shows no indicator whose entire output is `PX`.
- [ ] **MLCOL-2 — Prove the companions carry signal the parent column does not (MAJOR).** A binary
  derived from a column is correlated with it by construction; that is exactly what Gate E exists to
  catch.
  **Done when:** each companion has a measured ρ against its parent and against the full shipped set,
  and the ones in the revert band are deleted rather than shipped.

⚠ Ties: this is the fork's stated purpose — see `CLAUDE.md` → *The ML feature contract* and the README's
ML rules. `ichimoku_ml` is the reference precedent (5 price lines → 8 scale-free causal columns).
Depends on **WIRING-1** (bulk runs) and interacts with **MULTIL** (companions multiply per length).
