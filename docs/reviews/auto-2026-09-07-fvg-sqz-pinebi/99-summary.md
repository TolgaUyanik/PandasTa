# Run summary — 2026-09-07 — `/brutally-honest-review --auto FVGDEAD-0 FVGDEAD-1 SQZOFF-0 PINEBI-0 PINEBI-1a PINEBI-1b PINEBI-1c PINEBI-1d PINEBI-1e PINEBI-2`

Mode C, Fletcher gate, 3-round cap per task group. All implementation on the main thread.

## Scope, as the user set it in Phase 2

Ten tasks were named. The batch is 3 defect fixes **plus 46 new indicators**, each port needing
Gates A–F. Asked how to sequence it, the user chose **"Defects + PINEBI-0 + 1a"**, so
**PINEBI-1b, -1c, -1d, -1e and -2 were never started** — deferred by decision, not by failure. Their
TODO entries are untouched apart from scope corrections the coverage CSV forced.

Three other Phase-2 answers shaped the work: repair `fvg` if it clears the gates (my call on the
measurement), match the existing `measure_*_overlap_full.py` precedent for Gate E, and make the Pine
primitives **Pine-exact with the lag documented**.

## Results

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| FVGDEAD-0 | **PASS** | 3 | `pandas_ta/trend/fvg.py`, `tests/test_fvg.py`, `Backtesting/scripts/analysis/measure_fvg_overlap_full.py` + 4 CSVs | FVGENG-2 |
| FVGDEAD-1 | **PASS** | 3 | `02-FVGDEAD-1.md`; engine copies 1+2 fixed | FVGENG-1, FVGENG-2 |
| SQZOFF-0 | **PASS** | 3 | `pandas_ta/momentum/squeeze.py`, `squeeze_pro.py`, `pandas_ta/utils/_core.py` | — |
| PINEBI-0 | REVISED through **8** rounds | 8 | `docs/gen_pine_builtin_coverage.py`, `docs/pine_builtin_coverage.csv`, `tests/test_pine_coverage_csv.py` | -1b…-1e scopes |
| PINEBI-1a | REVISED through **8** rounds | 8 | `pandas_ta/utils/_pine.py`, `tests/test_pine_primitives.py` | — |
| PINEBI-1b/-1c/-1d/-1e/-2 | not started | — | — | deferred by the user's scoping answer |

⚠ **PINEBI ran to eight rounds** — the 3-round cap was reached at round 3, and the user authorised
rounds 4-8. Every extra round found real defects, and rounds 4-6 each found that the previous
round had fixed the instances a reviewer named rather than the class described. Round 8 returned REVISE (three CRITICALs: the `variance`
caveat asserted a divergence that does not exist, the evidence guard never opened the files it
demanded citations to, and `stc` had been "scoped" only into a CSV note string). Its fixes are
applied and both suites are green, but **round 8's own fixes have not been re-gated**.

Suites: fork **1,252 passed / 21 skipped** (was 1,151 at the start of this run). Parent
**746 passed**, plus 6 new parity tests; its 3 failures and 2 collection errors are pre-existing and
reproduce with the change stashed (`fcntl` is Unix-only).

## What the gate changed that would otherwise have shipped

1. **Gate E measured the wrong column.** The first FVG run scored the pooled *engine* frame — and the
   engine kept its own unrepaired copy of the loop, which I had documented two files away in the same
   run. Reported max |ρ| 0.1363; the repaired column's real figure is **0.6390**. Still under the
   0.76 ship line, so the decision held, but nobody had measured it.
2. **"Constant zero by construction" was false on real data.** My own premise, measured on synthetic
   continuous floats. Real prices tie: 86,415 of 408,253 BIST bars (21.17%) close exactly at an
   extreme, and the old code fired 18,895 / 14,320 times. The defect was not a dead column but a
   **tick-rounding artifact** — worse to model on, because it looks like signal.
3. **WIRING-2's defect class had two more victims.** `zlma` (every `mamode`) and `ui` (`everget=True`)
   carried the same module-shadowing import and still raised.
4. **The `TRADING FREEZE` was invoked to skip work it does not cover.** Copies 1 and 2 of the FVG loop
   are research code outside the container; only copy 3 is frozen. Both are now fixed.
5. **`ta.max`/`ta.min` are core Pine built-ins**, hand-labelled "not a Pine built-in" and queued into
   -1e as *rolling* fork utilities. They are all-time extremes. The corpus says so in a comment
   (`docs/pine/c1pPR2kI.pine:137-139`).
6. **Four Pine semantics were wrong**: a NaN condition counted as true; `highest_since` returned NaN
   until the first trigger where the library source on disk tracks from bar 0; `*bars` broke ties
   toward the oldest bar; `pivot_point_levels` shipped 7 of Pine's 11 levels under Pine's name.
7. **`from pandas_ta import *` would have replaced Python's `max`.** Shipped as
   `alltime_max`/`alltime_min`.
8. **Two `have` verdicts were wrong and would have deleted real ports.** `kcw` (Pine's Keltner
   *width*; `pandas_ta.kc` emits no width column) and `dm` (the library's is the **Demarker**
   oscillator, not Wilder's Directional Movement). Both were caught by reading the library's
   `@function` line — the method that had already caught `ft` and `vi` and had then not been applied
   to the other eighteen rows.
9. **Three more `have` verdicts were wrong, all in the highest-traffic rows.** `ta.crossunder`
   (307 corpus files) and `ta.cross` (either-direction in Pine) both mapped to `pandas_ta.cross`,
   which detects **upward** crosses only; `swma` mapped to a function whose own docstring says it
   disagrees with TradingView's fixed 4-bar kernel; `supertrend`'s direction sign is **inverted**
   against the library's. The CSV now carries an `audited` column — 29 rows checked, **28 not** — so
   an unverified `have` reads as unverified instead of as an all-clear.
10. **Tests that pinned nothing**: one compared the implementation to a copy of its own body; one
   passed on any of four values; several were structurally blind because their fixture was chosen
   tie-free. Pivot strictness survived a `>` → `>=` mutation with the whole suite green.

## The recurring failure, stated plainly

Every round, in both task groups, the same shape: **the code gets fixed and the artifact describing
it does not.** Round 2 reclassified `max`/`min` and the regenerated CSV still called them "rolling";
the FVG repair landed while `CLAUDE.md`, the README and the measurement script's own docstring still
described the bug as live; counts in `TODO.md` were written before the test files stopped growing.
`PandasTa/CLAUDE.md` names this as the repo's dominant historical defect. It was the dominant defect
of this run too.

## Registered, not fixed

| task | why |
|---|---|
| **FVGENG-2** | Copy 3 of the FVG loop is in the live container. Changing a live feature's semantics is a decision-basis change even under `ENTRIES_FROZEN`, and Mode C puts deployment out of auto scope. **Research and live now compute different `IN_FVG_*` columns** until this lands. |
| **FVGENG-1** | `IN_FVG_BULL` earned its seat in the 17-feature MLF-5 priors list while it was the artifact; the repaired column has never been justified there. |
| **PINEBI-1b…-1e, -2** | Deferred by the user's Phase-2 scoping answer. The CSV scopes them — read it, do not read this line: as of round 8, **16 ports**, 9 alternates, 2 data-blocked, 4 utilities, plus **PINEBI-0b** (audit the 40 `have` rows nobody has compared). Three ports (`kcw`, `dm`, and `cagr` as an `n/a`) were classified `have` until review caught them. |
