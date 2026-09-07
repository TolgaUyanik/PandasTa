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

- [x] **WIRING-1 — Add the 11 missing `core.py` accessor methods (MAJOR).** ✅ **DONE 2026-09-07** —
  run log + both Fletcher review rounds: `docs/reviews/auto-2026-09-07-wiring/`. `wavetrend`,
  `ema_align`, `ichimoku_ml`, `linreg_channel`, `bos`, `choch`, `fvg`, `halftrend`, `ob`, `zigzag`,
  `vol_delta` now have accessors; `df.ta.strategy()` completes with no `exclude` on both the serial
  and the default multiprocessing path. Guards in `tests/test_wiring_accessors.py`: accessor
  existence over all of `Category`, a call-spy proving each keyword arrives under the declared name
  (mutation-checked — renaming `swing_length` to `swing_len` in `bos` fails the suite), and an
  `offset` test over all eleven.
- [x] **WIRING-2 — Fix `aberration` (MINOR).** ✅ **DONE 2026-09-07 — the reported instance was one of
  three.** Round 1 review caught that `overlap/zlma.py` (every `mamode`) and `volatility/ui.py`
  (`everget=True`) carried the same defect and still raised. All three now import from the submodule
  (`from pandas_ta.overlap.sma import sma`). `test_no_module_shadows_a_function_name_anywhere_in_the_package`
  scans `sys.modules` for the class rather than the instance.
- [x] **WIRING-3 — Fix `mcgd` (MINOR, added 2026-09-07 by user decision during the run).** ✅ **DONE** —
  `Series.append` (removed in pandas 2.0) → `pd.concat`. This was WIRING-1's blocker: its acceptance
  criterion says "no `exclude` list", which `mcgd` made unreachable.
  ⚠ **This closes TVPTA-7b in `../Backtesting/TODO.md:477`** — that task still points at a fixed
  defect and should be marked done there.

⚠ Ties: `docs/IndicatorDictionary.md` regenerated — its *Known breaks* section is now empty and says
so. `CLAUDE.md` updated: the touch-point-drift paragraph is past tense and the suite count is
1138 pass / 21 skip.

## FVGDEAD — `fvg`'s two zone columns were driven by tick rounding (NEW 2026-09-07, found by the WIRING round-2 review)

> **Goal:** `IN_FVG_BULL` and `IN_FVG_BEAR` ship as `BIN` features and are fed to the miner, and they
> are constant zero. Either make them fire or delete them — a column that cannot fire is worse than
> no column, because it looks like a feature.

⚠ **The goal's premise was WRONG, and the correction makes the defect worse, not milder.**
"Constant zero" was measured on synthetic continuous-float frames. On real data the old code
DID fire — 18,895 (4.63%) / 14,320 (3.51%) over 89 BIST frames and 408,253 daily bars —
because **86,415 of those bars (21.17%) close exactly at their high or low**, and a tie was
exactly what let a zone survive its own formation bar. So the columns were not dead; they were **driven by
tick rounding** rather than by the structure they name. Repaired rates: 22.17% / 19.85%.

**Mechanism** (line numbers are the PRE-REPAIR file). `pandas_ta/trend/fvg.py` appended a bull
zone at bar `i` as
`(zl=high[i-2], zh=low[i])` and then, in the SAME iteration, retained it only `if close[i] <= zh`
— i.e. `close[i] <= low[i]`, true only on a tie. The bear branch is symmetric.

- [x] **FVGDEAD-0 — Decide fire-or-delete on measurement (MAJOR).** ✅ **DONE 2026-09-07 — REPAIRED
  and shipped, all gates clear.** Membership is now tested BEFORE the forming zone is appended, and
  a bull zone is retained while `close > zl` (bear: `close < zh`).
  Measured by `../Backtesting/scripts/analysis/measure_fvg_overlap_full.py`, 89 BIST_100 frames /
  408,253 daily bars — the same Grid A basis as `measure_ifvg_overlap_full.py`:
  **Gate C** 90,506 / 81,021 fires, 89/89 frames firing, 0 saturated; `FVG_BULL`/`FVG_BEAR`
  unchanged (62,969 / 53,929), so detection was not touched.
  **Gate D** dyadic ×2/×8/×64/×1024 bit-identical (0 differing cells of 1,633,012); non-dyadic
  ×10 / ×3.7 differ on 63 / 35 cells (0.004% / 0.002%) — rounding flipping an exact tie in a strict
  price comparison, reported not asserted.
  **Gate E** max |Spearman ρ| vs all 361 other engine columns: `IN_FVG_BULL` **−0.6390**
  (`FSME_CE_DIST_BULL_5`, n=30,667), `IN_FVG_BEAR` **−0.5962** (`FSME_CE_DIST_BEAR_5`, n=22,824) —
  under the 0.76 ship line, one comparator each above 0.5; against full-coverage comparators the
  maxima are 0.3680 and 0.3158.
  ⚠ **Corrected in review round 1.** The first run reported 0.1363 / 0.1445 because it scored the
  pooled ENGINE frame while the engine still kept its own unrepaired copy of the loop — it measured
  the column being replaced. The script now asserts engine == `ta.fvg` per frame before scoring
  (round 2: this was a `print`, not an assert).
  Artifacts: `backtest_results/tvpta6/fvg_overlap_gridA_full.csv`, `fvg_gateC_reachability.csv`,
  `fvg_gateD_scale_mismatch.csv`, `fvg_prerepair_counts.csv` (Gate 0 = the pre-repair logic,
  reimplemented in the script so the 18,895 / 14,320 counts are reproducible).
  Tests: `tests/test_fvg.py` (12, incl. a Gate B mutant and a hand-built retrace).
- [x] **FVGDEAD-1 — Check the engine and the mined rules for references (MAJOR).** ✅ **DONE
  2026-09-07** — full reference table: `docs/reviews/auto-2026-09-07-fvg-sqz-pinebi/02-FVGDEAD-1.md`.
  🔴 **The engine did not call `pandas_ta.fvg` at all** — three independent copies of the same
  defective loop lived in `../Backtesting/`, so the library repair alone changed nothing there. Two
  are fixed in this run (FVGENG-0); the live container's copy is owner-gated (FVGENG-2). No mined rule is at risk: `StrategyMaster.csv` has **0** matches and no rule
  text in `backtest_results/` references either column — they were available to the miner and never
  selected, which is what a tie-driven artifact should look like. The live exposure is forward-only:
  `IN_FVG_BULL` is one of the **17 hand-curated MLF-5 priors** in
  `scripts/mining/run_bist_daily_canonical_mining.py:108`.

⚠ Ties: `NO_OBSERVABLE_EFFECT` is now empty in `tests/test_wiring_accessors.py` — `max_zones` finally
changes output. Same reachability gate that deleted `tvstop`'s `TVS_DIST` and `range_profile`'s
`RPO_OSC`, except this one cleared it.

## FVGENG — the engine carries three private copies of the `fvg` zone loop (NEW 2026-09-07, spun out of FVGDEAD-1)

> **Goal:** FVGDEAD repaired `pandas_ta.fvg`, and the engine did not notice, because it never called
> it. Three hand-rolled duplicates carry the tick-rounding defect into research, dashboards and the
> live container.

| # | file | role | state |
|---|---|---|---|
| 1 | `../Backtesting/backtesting_engine/indicator_engine.py` (`_calculate_fvg`) | research / mining features | ✅ delegates (FVGENG-0) |
| 2 | `../Backtesting/backtesting_engine/speedy_indicators.py` (`calculate_fvg_zones`) | dashboards | ✅ delegates (FVGENG-0) |
| 3 | `../Backtesting/deploy/app/paper_trading/paper_trading.py:804-825` | **live container** | ⏸ owner-gated (FVGENG-2) |

- [x] **FVGENG-0 — Replace copies 1 and 2 with a call to `pandas_ta.fvg` (MAJOR).** ✅ **DONE
  2026-09-07** — `indicator_engine._calculate_fvg` and `speedy_indicators` now delegate; 45 lines of
  duplicated loop deleted. Parity test `../Backtesting/tests/test_fvg_engine_parity.py` (**6 tests**)
  pins engine == `ta.fvg`, the fire rate out of the old ~4% artifact band, the
  no-membership-on-the-formation-bar rule, copy 2 exercised directly (`compute_all` never calls it),
  the int32 dtype of the formation flags, and short-frame degradation to a warning. Parent suite 746 passed (3 failures + 2 collection errors
  are pre-existing — verified by stashing the change). SHIP-WITH-THE-CHANGE done: family page
  `docs/indicators/family-structure-smc.md`, `gen_indicator_register.py` re-run (492 cols),
  `verify_claude_md.py` all PASS.
  ⚠ **Review round 1 corrected the scope here**: the first pass deferred all three copies on freeze
  grounds, but copies 1 and 2 are research code outside the container and the freeze does not reach
  them.
- [ ] **FVGENG-2 — Copy 3, the live container (MAJOR, OWNER-GATED).**
  `../Backtesting/deploy/app/paper_trading/paper_trading.py:804-825` still runs the old loop, so
  **research and live now compute different `IN_FVG_*` columns.** Changing it alters a live feature's
  semantics, which is a decision-basis change even under `ENTRIES_FROZEN`, and needs a rebuild.
  **Done when:** the owner lifts the freeze for this change, the block is replaced by the same
  delegation, and the container is rebuilt with the SHA bump.
- [ ] **FVGENG-1 — Re-examine `IN_FVG_BULL`'s seat in the 17-feature MLF-5 priors list (MINOR,
  depends on -0).** It was selected into that list while it was a tick-rounding artifact; its
  repaired form is a different column and has never been justified there.
  **Done when:** either a measurement supports keeping it, or it is replaced in
  `BIST_DAILY_PRIORS` and the change is recorded against `docs/IndicatorMLAudit.md`.

⚠ **FVGENG-2 alone is owner-gated.** Copy 3 is `deploy/` code, and the **TRADING FREEZE
(2026-07-27)** suspends strategy-motivated changes and rebuilds; changing a live feature's semantics
is a decision-basis change even with `ENTRIES_FROZEN`. FVGENG-1 is a research measurement with no
freeze exposure. Also regenerate the stale snapshots
(`backtest_results/indicator_snapshot_bist_1d_*.csv`).

## SQZOFF — `squeeze` and `squeeze_pro` raise on any non-zero `offset` (NEW 2026-09-07, found by the WIRING round-3 review)

> **Goal:** `df.ta.strategy("momentum", offset=1)` dies. Two indicators take a whole bulk run
> down with them, and the failure is a `ValueError` deep in pandas, not anything that names
> the indicator.

**Measured 2026-09-07:** `df.ta.squeeze(offset=1)` and `df.ta.squeeze_pro(offset=1)` →
`ValueError: cannot convert float NaN to integer`. `offset=0` (the default) is fine, so this
has been invisible. Both files are untouched since the fork's first commit — **upstream
defect, not introduced by WIRING.**

**Mechanism:** `pandas_ta/momentum/squeeze.py:69-73` shifts the four output series, which
introduces leading NaNs, and the `int` cast applied to the on/off/no-squeeze flags afterwards
cannot represent NaN.

- [x] **SQZOFF-0 — Make the cast NaN-safe, or shift after casting (MINOR).** ✅ **DONE 2026-09-07** —
  a single shared `flag_as_int(series, asint)` in `pandas_ta/utils/_core.py`, imported by both
  modules, casts to `int` only when the series has no NaN,
  and keeps the float form (leading NaN, exactly what every other indicator's offset produces)
  when it does. `offset=0` output is unchanged, so the default dtype stays `int32`.
  `tests/test_wiring_accessors.py` no longer excludes them, and 14 new cases cover
  `{}, offset=1, offset=2+detailed, offset+fillna, offset+asint=False, lazybear+offset` for both
  indicators plus a dtype guard on the default path.

⚠ Ties: the exclusion in `test_each_previously_broken_category_runs` is the marker to delete
when this lands. Same family as the pandas-2 `mcgd` break — an upstream line that no test
reached.

---

# ═══ BACKLOG ═══

## PINEBI — port TradingView's built-in indicators, then continue the community corpus (NEW 2026-09-06, user)

> **Goal (user):** *"We will review each pine scripts to implement to repo from PandasTa/docs/pine/
> folder. We can start with TradingView basic indicators."*

**"Built-in" is three populations, not one (measured 2026-09-06).** Only two are portable:

⚠ **The inventory column below is the ORIGINAL HAND COUNT and is superseded by the generated
verdict table under PINEBI-0.** Kept for the tier definitions only.

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
  Pine built-ins. The generated verdict table under PINEBI-0 is authoritative.
- **14 are real core gaps**, and they are rolling *primitives*, not indicators: `highest` (324 files),
  `lowest` (298), `pivothigh` (229), `pivotlow` (224), `valuewhen` (58), `barssince` (56), `cum` (36),
  `correlation` (29), `percentrank` (27), `highestbars` (23), `lowestbars` (22),
  `percentile_nearest_rank` (7), `percentile_linear_interpolation` (6), `pivot_point_levels` (1).

**Scope decision (user, 2026-09-06): add all three groups, including the tier-2 calls and the "noise".**
The noise six are then *not* Pine ports — they are ML utilities the fork wants on their own merit, and
`-1e` says so rather than filing them under a provenance they do not have. Total: **46 additions.**

⚠ **Superseded by the generated verdict table under PINEBI-0.** Kept to show what the hand count
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

- [x] **PINEBI-0 — Freeze the audit above into a machine-readable CSV (MINOR). GATES -1a … -1e.**
  ✅ **DONE 2026-09-07** — `docs/gen_pine_builtin_coverage.py` → `docs/pine_builtin_coverage.csv`,
  **107 rows**, every one with a verdict. The classifier is the artifact; the counts are whatever it
  prints on the day, so a changed count is not a finding but a changed verdict is.
  Columns: tier · name · files_using · files_without_lib_import · files_with_lib_import ·
  in_tradingview_ta_library · pandas_ta_equivalent · verdict · **audited** · **audit_evidence** · note.

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

  🔴 **Two hand labels were wrong and are corrected (review round 2).** `ta.max` and `ta.min` were
  labelled "third-party library method, not a Pine built-in". They **are** core built-ins, and they
  return the **all-time** extreme from bar 0 — not a rolling window, which is why they take no
  length. `docs/pine/c1pPR2kI.pine:137-139` comments `// All Time High and Low` directly over
  `ta.max(HIGH_)` / `ta.min(LOW_)`. They are now primitives (shipped in -1a), **not** -1e utilities.
  The `ta.sum` note was also invented — `ta.sum(src, len)` is a real sliding-sum built-in; its
  verdict stands only because every corpus hit is a comment, which is now what the note says.

  ⚠ **Reproducibility was broken once and is now tested.** Landing -1a put all 18 primitives in the
  `pandas_ta` namespace, and `classify()` consulted that namespace before its own `PRIMITIVES` list —
  so a re-run silently reclassified 14 rows from `port - primitive` to `have`, retiring the task that
  produces them. `PRIMITIVES` now outranks a namespace match, regeneration is byte-identical, and
  `tests/test_pine_coverage_csv.py` (38, of which 3 guard reproducibility directly) fails if any
  verdict moves on a re-run.

  ⚠ **The CSV supersedes the hand-counted numbers in the section above (16/12/10/2/6 = 46).**
  Read the verdict table for the split; it is asserted against the CSV. Do not restate it in prose —
  a second copy with a second denominator is how this entry ended up claiming 47 non-`have` rows over
  a 107-row file where the real figure is 50.

  🔴 **It also caught two ports that would have duplicated shipped indicators**, by reading the
  library's own `@function` docstrings rather than matching names: `ft` is "the Fisher Transform"
  (= `fisher`, `RA2vGpkA-ta.pine:217`) and `vi` is "the Vortex Indicator" (= `vortex`, `:755`). Under
  those abbreviations, name-matching alone would have shipped both as new indicators — the
  SEMANTIC-DUPLICATE LAW that SRMIX-1 paid for twice.
  A third, `changePercent`, is **not** a duplicate and is not `percent_return`: the library defines it
  on two arbitrary values (`100 * (a - b) / b`) while `percent_return` is a one-series rolling return.
  It is recorded `n/a - not worth a primitive` — a one-liner at the call site.
- [x] **PINEBI-1a — Add the rolling primitives (MAJOR).** ✅ **DONE 2026-09-07** —
  `pandas_ta/utils/_pine.py`, **18** functions (the 16 scoped, plus `max`/`min` once round 2
  established they are core built-ins), exported through `utils/__init__.py`; tests in
  `tests/test_pine_primitives.py` (50) and `tests/test_pine_coverage_csv.py` (38). **Pine-exact with the lag documented**, per the owner's
  decision, so later ports transliterate rather than paraphrase.
  `highest` `lowest` `highestbars` `lowestbars` `valuewhen` `barssince` `cum` `correlation`
  `percentrank` `percentile_nearest_rank` `percentile_linear_interpolation` `pivot_point_levels`
  `pivothigh` `pivotlow` `highest_since` `lowest_since` `alltime_max` `alltime_min`. An explicit
  `__all__` keeps the star import to exactly those eighteen.

  ⚠ Pine's `ta.max`/`ta.min` ship as **`alltime_max`/`alltime_min`**. Under Pine's own names they
  would shadow the builtins package-wide — `_pine.__all__` feeds `pandas_ta.utils`, which `core.py`
  star-imports — so `max(...)` anywhere in the package, and in any user file doing
  `from pandas_ta import *`, would silently return a Series. `test_the_builtins_are_not_shadowed`
  pins it. They are also **all-time, not rolling**: no length, running from bar 0.

  The semantics that differ from the obvious pandas one-liner, each with its own test:
  - `barssince` / `valuewhen` return **NaN before the first true**, not 0 and not a back-fill;
  - `percentrank` ranks against the **previous** `length` bars — including the current bar would floor
    every result at `100/length`;
  - `*bars` return non-positive **offsets**, not distances;
  - `cum` treats NaN as 0;
  - `pivothigh`/`pivotlow` report the pivot's price on the **confirmation bar**, `right` bars after the
    pivot. That lag is the causality cost and is stated in the docstring; a Gate B mutant test moves
    the write to the pivot bar and requires the output to change.

  `test_primitives_are_not_indicators` pins that none of the 18 is in `Category` or on `df.ta` — a
  primitive swept into `df.ta.strategy()` would become an unaudited feature column.

  ⚠ **Four semantics were wrong in the first pass and were caught by review**, all of them the same
  failure — writing what Pine "obviously" does instead of measuring it:
  - a `NaN` condition counted as **true** (`Series.astype(bool)`), so `barssince` returned 0 on
    undefined bars. Every condition built on a rolling source is NaN during warm-up, so this fired at
    the head of every series;
  - `highest_since`/`lowest_since` returned NaN until the first true condition. The library source on
    disk (`RA2vGpkA-ta.pine:236-240`) runs its `math.max` line **unconditionally** — tracking starts at
    bar 0. Cited but not read;
  - `highestbars`/`lowestbars` broke ties toward the **oldest** bar (`np.argmax`); Pine walks back from
    the current bar and reports the nearest. Untestable on the original fixture, which was chosen
    tie-free — and 21.17% of real BIST bars close exactly at an extreme;
  - `pivot_point_levels` shipped 7 of Pine's 11 levels under Pine's name. Now all 11, with a `type=`
    argument that raises on the five unimplemented variants instead of silently substituting.

  Suite: 1,252 passed / 21 skipped.

  ⚠ **Two guards were added in round 5 to end the class of defect that dominated this review**:
  `test_every_tier2_have_row_was_docstring_audited` fails when a tier-2 row is classified `have`
  without someone recording that they read the library's `@function` line (this is how `dm` and
  `cagr` survived four rounds), and `test_the_docs_quote_the_csvs_actual_split` reads the verdict
  table in this file and fails if any number disagrees with the CSV.

  ⚠ **Three review rounds, and the pattern in all three was the same**: the code got fixed and the
  artifacts describing it did not. Round 2 corrected `max`/`min` from "not a built-in" to a primitive
  and the regenerated CSV still called them "rolling"; round 3 caught that, the `sum` verdict still
  reading `n/a - not a Pine built-in` above a note saying it is one, an na-policy table that covered
  16 of 18 functions, and a `FutureWarning` "fix" placed after the call that emits it. **The
  round-3 fixes were applied but NOT re-gated — the 3-round cap was reached.**
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
