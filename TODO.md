# PandasTa Tolga Uyanik's Fork To-do's

Library-scoped work only. Engine-side work (mining, wiring, live book) lives in
`../Backtesting/TODO.md` — the pine-porting initiative **TVPTA** (TVPTA-0 … TVPTA-7b) is there, and
several sections below extend it rather than restarting it.

Port protocol every section here is bound by: `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`
(Gates A–F; overlap ρ ≥ ~0.9 → revert, 0.76–0.80 → ship with disclosure, < 0.76 → ship).
Column inventory and ML form of everything currently shipped: `docs/IndicatorDictionary.md`.

---

# ═══ ACTIVE ═══

## WIRING — repair the two defects that block the sections below (NEW 2026-09-06, found while writing the indicator dictionary)

> **Goal:** the ML-column, multi-length and pattern work below all need `df.ta.strategy()` and a clean
> import to run in bulk. Both are broken today, so this goes first.

- [ ] **WIRING-1 — Add the 11 missing `core.py` accessor methods (MAJOR).** `wavetrend`, `ema_align`,
  `ichimoku_ml`, `linreg_channel`, `bos`, `choch`, `fvg`, `halftrend`, `ob`, `zigzag`, `vol_delta` are
  registered in `Category` (`pandas_ta/__init__.py`) but have no method in `pandas_ta/core.py`, so
  `df.ta.strategy()`, `df.ta.strategy("overlap")` and `df.ta.strategy("trend")` raise
  `AttributeError`. Touch point 4 of 5 was skipped on each.
  **Done when:** `df.ta.strategy()` runs to completion on a 600-bar frame with no `exclude` list, and
  a test asserts `all(hasattr(df.ta, n) for n in every name in Category)`.
- [ ] **WIRING-2 — Fix `aberration` (MINOR).** `pandas_ta/volatility/aberration.py:5` does
  `from pandas_ta.overlap import hlc3, sma`; circular-import ordering binds `sma` to the **submodule**,
  not the function, so `aberration.py:26` raises `TypeError: 'module' object is not callable` on every
  call. Import from `pandas_ta.overlap.sma` directly, or resolve lazily.
  **Done when:** `ta.aberration(high, low, close)` returns its 4 columns in a fresh interpreter, with a
  test that calls it as the first pandas_ta call in the process.

⚠ Ties: `mcgd` — the third break of this kind (`Series.append`, removed in pandas 2.0) — is already
registered as **TVPTA-7b** in `../Backtesting/TODO.md:477`; do not duplicate it here. Both defects
above are recorded in `docs/IndicatorDictionary.md` → *Known breaks*.

---

# ═══ BACKLOG ═══

## PINEBI — port TradingView's built-in indicators, then continue the community corpus (NEW 2026-09-06, user)

> **Goal (user):** *"We will review each pine scripts to implement to repo from PandasTa/docs/pine/
> folder. We can start with TradingView basic indicators."*

**"Built-in" is three populations, not one (measured 2026-09-06).** Only two are portable:

| tier | what | source | inventory |
|---|---|---|---|
| 1 | core `ta.*` compiler intrinsics (`ta.sma`, `ta.pivothigh`) | none published — spec is the Pine v6 reference | 75 distinct tokens used across the corpus; **47 covered, 28 not** |
| 2 | official `TradingView/*` libraries, MPL-2.0, `© TradingView` | **published, and on disk** | `docs/pine/RA2vGpkA-ta.pine` = `TradingView/ta` v10, 47 exports; **26 covered, 21 not** |
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
- **6 are noise** — `sum`, `max`, `min`, `pivot`, `normalize`, `covariance` (≤3 files each; the hits are
  comments such as *"Pine has no native ta.covariance"* and third-party library methods). **They are not
  Pine built-ins at all.**
- **14 are real core gaps**, and they are rolling *primitives*, not indicators: `highest` (324 files),
  `lowest` (298), `pivothigh` (229), `pivotlow` (224), `valuewhen` (58), `barssince` (56), `cum` (36),
  `correlation` (29), `percentrank` (27), `highestbars` (23), `lowestbars` (22),
  `percentile_nearest_rank` (7), `percentile_linear_interpolation` (6), `pivot_point_levels` (1).

**Scope decision (user, 2026-09-06): add all three groups, including the tier-2 calls and the "noise".**
The noise six are then *not* Pine ports — they are ML utilities the fork wants on their own merit, and
`-1e` says so rather than filing them under a provenance they do not have. Total: **46 additions.**

| sub-task | n | what |
|---|---|---|
| -1a | 16 | rolling primitives: the 14 core gaps + `highestSince`, `lowestSince` |
| -1b | 12 | portable `TradingView/ta` indicators |
| -1c | 10 | alternate implementations of indicators already shipped |
| -1d | 2 | lower-timeframe data requests — blocked on a sub-hourly source |
| -1e | 6 | the "noise" six, re-scoped as ML utilities |

Reconciliation, so the arithmetic is checkable: the library's **21 uncovered exports** = 12 (-1b) + 5
alternates whose sibling is *also* uncovered (`ema2`, `rma2`, `supertrend2`, `t3Alt`, `vStop2`) + 2 data
requests (-1d) + 2 primitives (-1a). -1c adds 5 more alternates whose sibling the fork already covers
(`atr2`, `dema2`, `tema2`, `stochFull`, `stochRsi`) — they are not in the 21 for that reason, but they
are the same kind of work, so they are measured in the same pass.

- [ ] **PINEBI-0 — Freeze the audit above into a machine-readable CSV (MINOR). GATES -1a … -1e.** The
  counts are measured; what is missing is the artifact. One row per function: tier · name · files-using ·
  pandas_ta equivalent (or blank) · verdict (`have` / `port` / `skip — variant of X` / `n/a — data
  request` / `n/a — noise`), plus the classifier that produced it so a re-run reproduces the counts.
  **Done when:** `docs/pine_builtin_coverage.csv` exists, every tier-1 and tier-2 function has a verdict,
  and re-running the classifier reprints the 47/28 and 26/21 splits.
- [ ] **PINEBI-1a — Add the 16 rolling primitives (MAJOR, depends on PINEBI-0).** The 14 core gaps plus
  `highestSince` and `lowestSince`, which are tier-2 by publication but primitives by nature. These are
  not features and must not be registered in `Category` as indicators — they are the vocabulary every
  later port is written in (`ta.highest`/`ta.lowest` alone appear in 622 files). Land them in
  `pandas_ta/utils/` next to the existing `above`/`below`/`cross` helpers.
  **Done when:** all 16 exist with tests, each matches its Pine semantics on a hand-checked fixture
  (`ta.barssince` returns `na` before the first occurrence, `ta.pivothigh` confirms `right` bars late and
  that lag is documented as the causality cost), and no primitive is exposed via `df.ta.strategy()`.
- [ ] **PINEBI-1b — Port the 12 portable `TradingView/ta` indicators (MAJOR, depends on PINEBI-0).**
  From the library's 21 uncovered exports: `frama`, `rwi`, `szo`, `vzo`, `pzo`, `wpo`, `vStop`,
  `williamsFractal`, `relativeVolume`, `rms`, `ht`, `ift`. Of the remaining 9 uncovered exports, 5
  alternates go to -1c and 2 data requests to -1d; `highestSince`/`lowestSince` are primitives and go
  to -1a.
  ⚠ **Licence:** the library is MPL-2.0, `© TradingView`. Each port carries the attribution in its module
  docstring, as the existing Pine ports do (`tvstop` cites `7YXrxMjV`, MPL-2.0, © LyroRS). Applies to
  -1c and -1d too.
  **Done when:** each of the 12 has a test module, a Gate B mutant test, a Gate D scale check, a measured
  Gate E overlap max with its sample size, the MPL attribution, and `docs/IndicatorDictionary.md`
  regenerated so the new columns appear with their ML form.
- [ ] **PINEBI-1c — Port the 10 alternate implementations, and keep only the ones that differ (MAJOR,
  depends on PINEBI-0).** `ema2`, `rma2`, `supertrend2`, `t3Alt`, `vStop2`, `atr2`, `dema2`, `tema2`,
  `stochFull`, `stochRsi`. Each restates an indicator the fork already ships, so Gate E will read ρ ≈ 1.0 against its
  own sibling and the revert rule would delete all nine on sight. **That rule is suspended here for one
  measured reason:** the alternates differ in *seeding and smoothing*, not in signal — `ta.ema2` is
  documented in the corpus as "extends `ta.ema` to start without delay at first bar and deliver usable
  data instead of `na`", which is a **warm-up** difference, and warm-up is a cost this fork's ML rules
  care about (`docs/IndicatorDictionary.md` prints a warm-up column for every indicator).
  So the acceptance test is not overlap, it is warm-up and parameter reach:
  **Done when:** each of the 10 is measured against its shipped sibling on two axes — bars of warm-up
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
- [ ] **PINEBI-1e — Add the 6 "noise" functions as ML utilities (MINOR, depends on PINEBI-0).** `sum`,
  `max`, `min`, `pivot`, `normalize`, `covariance`. ⚠ **These are not Pine built-ins** — the corpus hits
  were comments and third-party library methods (one literally reads *"Pine has no native
  ta.covariance"*). They are being added because the fork wants them, so they are documented as
  fork utilities with no TradingView provenance and **no MPL attribution**, which would be false.
  Rolling `sum`/`max`/`min` join -1a's primitives; `pivot` is classic pivot-point levels
  (PP/R1-R3/S1-S3, distinct from core `ta.pivot_point_levels` in -1a — measure them against each other);
  `normalize` is rolling min-max scaling; `covariance` is rolling covariance.
  **Done when:** all 6 exist with tests; `pivot`'s levels ship **only** as scale-free distances from
  `close`, never as raw price levels (the dictionary's `PX` rule); and `normalize`'s window is causal
  (trailing min/max, never whole-series, which would leak the future into every bar).
- [ ] **PINEBI-2 — Resume the community corpus after the built-ins (MAJOR, depends on PINEBI-1a…-1e).**
  `docs/pine/` holds 2,211 `.pine` files (untracked). TVPTA already ported 195 and left two queues:
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

- [ ] **TALIB-0 — Produce the coverage diff (MINOR).** TA-Lib's ~158 functions vs the 201 shipped here:
  name · pandas_ta equivalent · verdict (`have` / `port` / `skip — candle pattern, see CANDLE-2`).
  **Done when:** the CSV exists in `docs/` with a verdict on every TA-Lib function.
- [ ] **TALIB-1 — Port the `port` rows (MAJOR, depends on TALIB-0).** Same five touch points and Gates
  A–F; the Pine-source citation in Gate A becomes the TA-Lib C source or the documented formula.
  **Done when:** each new indicator ships with a test module and a measured overlap max, and the
  dictionary is regenerated.

⚠ Ties: overlap is the whole risk here — TA-Lib and pandas_ta share heritage, so expect ρ ≈ 0.9
reverts. Coordinate with **CANDLE-2** so candle patterns are not ported twice.

## MULTIL — multiple lookback lengths for the indicators that earn them (NEW 2026-09-06, user)

> **Goal (user):** *"We need different time spans for same indicators. RSI 14 RSI 28, EMA150, EMA50, etc"*

- [ ] **MULTIL-0 — Pick the lengths per indicator on measurement, not convention (MAJOR).** Every
  indicator already takes `length`; the gap is that the engine computes one. Adding a second length is
  cheap to compute and expensive to justify — `RSI_14` vs `RSI_28` is a candidate ρ ≈ 0.9 pair, which
  is the revert band. Measure the length-vs-length correlation grid per indicator first.
  **Done when:** a table of indicator × candidate lengths with the measured ρ between them, and a kept
  set where no retained pair exceeds the revert threshold.
- [ ] **MULTIL-1 — Wire the kept set into the engine's compute list (MAJOR, depends on MULTIL-0, lands in `../Backtesting/`).**
  **Done when:** the new columns appear in the engine's feature register with explicit routing, and the
  column count agrees across register, manifest and family index.
- [ ] **MULTIL-2 — Check nothing downstream breaks on the new column names (MAJOR).** Mined rules in
  `StrategyMaster.csv` match column-name strings; a new `RSI_28` must not shadow or rename `RSI_14`.
  **Done when:** the existing paper strategies still resolve every column they reference.

⚠ Ties: this is the cheapest way to inflate the column count and the easiest way to double-weight one
signal in the miner — Gate E applies to a length variant exactly as to a new indicator. Feeds **MLCOL**
(each retained length needs its own binary/percentile companions).

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
