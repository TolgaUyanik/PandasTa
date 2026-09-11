# FVGDEAD-0 · SQZOFF-0 — log and review rounds

Status: **PASS** after 3 rounds. FVGDEAD-1 has its own file (`02-FVGDEAD-1.md`).

## Implementation

**FVGDEAD-0.** `pandas_ta/trend/fvg.py`: membership is tested against zones that already exist,
BEFORE the zone the bar forms is appended; a bull zone is retained while `close > zone_low` (bear:
`close < zone_high`). Gates run by `Backtesting/scripts/analysis/measure_fvg_overlap_full.py` on 89
BIST_100 frames / 408,253 daily bars — the Grid A basis of `measure_ifvg_overlap_full.py`:

| gate | result |
|---|---|
| C reachability | `IN_FVG_BULL` 90,506 (22.17%), `IN_FVG_BEAR` 81,021 (19.85%); 89/89 frames fire, 0 saturated. `FVG_BULL`/`FVG_BEAR` unchanged at 62,969 / 53,929 |
| D scale invariance | dyadic ×2/×8/×64/×1024 bit-identical (0 of 1,633,012 cells); non-dyadic ×10 / ×3.7 differ on 63 / 35 (0.006%) — rounding flipping an exact tie in a strict price comparison |
| E attribution | max \|ρ\| **0.6390** (`IN_FVG_BULL` × `FSME_CE_DIST_BULL_5`, n=30,667) and **0.5962** (`IN_FVG_BEAR` × `FSME_CE_DIST_BEAR_5`, n=22,824); full-coverage maxima 0.3680 / 0.3158. Under the 0.76 ship line → **ship** |

Artifacts: `backtest_results/tvpta6/fvg_{overlap_gridA_full,gateC_reachability,gateD_scale_mismatch,prerepair_counts}.csv`.
Tests: `tests/test_fvg.py` (12), including a Gate B mutant and a hand-built retrace.

**SQZOFF-0.** A shared `flag_as_int(series, asint)` in `pandas_ta/utils/_core.py` casts to `int` only
when the series has no NaN, and keeps the float form (leading NaN — what every other indicator's
offset produces) when it does. `offset=0` output is unchanged, so the default dtype stays `int32`.

## Round 1 — REVISE

> **MAJOR** — WIRING-2 patched exactly one instance of a class of bug and declared victory. …
> `ta.zlma(close, mamode="sma")` raises `TypeError: 'module' object is not callable` today, and so
> does `ta.ui(close, everget=True)`.

Reproduced both before acting. A package-wide scan found 11 shadowed bindings across exactly 2
modules; both fixed, and `test_no_module_shadows_a_function_name_anywhere_in_the_package` now scans
for the class rather than the instance.

> **MAJOR** — Gate E measured the WRONG COLUMNS. `pool` is built from `eng.compute_all`, and the
> engine keeps its own unrepaired copy of the loop.

Correct, and the same run had documented that engine copy two files away. The script now asserts
engine == `ta.fvg` per frame before scoring. The real figure is 0.6390, not 0.1363.

> **CRITICAL** — "24.17% of bars close exactly at their high or low" is unsupported. The pooled rate
> is **21.17%**.

Correct: the old figure summed two event counts instead of counting bars. Fixed in four files.

> **CRITICAL** — the pre-repair counts have no committed script.

Added as "Gate 0 — the defect as it was", which reimplements the pre-repair loop and writes
`fvg_prerepair_counts.csv`.

> **MAJOR** — the freeze is a legitimate boundary for copy 3 and a dodge for copies 1 and 2.

Accepted. Both now delegate to `pandas_ta.fvg`; 45 lines of duplicated loop deleted.

## Round 2 — REVISE

> **CRITICAL** — the retracted 24.17% is still in `test_fvg.py`, contradicting itself inside its own
> parenthesis. **MAJOR** — four places still say, in the present tense, that the engine does not call
> `pandas_ta.fvg`. **MAJOR** — the "asserts the substitution is not a no-op" claim shipped a `print`.
> **MAJOR** — the parity test never touches copy 2. **MAJOR** — the delegation changed
> `FVG_BULL`/`FVG_BEAR` from int to float, contradicting the family page. **MAJOR** —
> `_calculate_fvg` lost the try/except every sibling has.

All applied: the figure removed, the four claims put in past tense, a real `assert np.array_equal`,
`test_speedy_fvg_zones_equal_the_library` (copy 2 is reached only from the SpeedyAnalysis pipeline),
an int32 cast plus a dtype test, and a short-frame guard. The short-frame test is scoped to the two
FVG calculators because `compute_all` on a 2-bar frame raises for unrelated pre-existing reasons —
verified by stashing the change.

## Round 3 — PASS

Seven MINOR/NIT, all applied: `calculate_fvg_zones` gained the same short-frame guard, the vacuous
half of its test was replaced, `.astype("int32")` made explicit (bare `int` is the platform C long),
a wrong line citation corrected for the second time, "(3 tests)" → "(6 tests)", the SQZOFF write-back
corrected to name the shared `flag_as_int` rather than a per-module `_flag`, and a stale "1 newly
classified" the regenerated register denies.

Reviewer's closing verification: every headline figure reconciled against the four CSVs, the Gate E
assert confirmed load-bearing, the int cast confirmed NaN-safe, and the
`compute_all`-already-raised claim independently reproduced.
