# B3-QTD-RET — port qtd_ret (issue #205)

Task text (verbatim, from the launcher's prompt): port the indicator of issue #205 through
Gates A-D, the wiring, the tests and `docs/<Name>Measured.md`, per the issue and the rules in
the system prompt. Gate E and the whole suites are run by the launcher afterwards.

## Execution log

- Read `docs/issues/screen/` for the issue's prototype: `ind_screen_r9.py` and
  `candidates_r9.csv` do not exist in this worktree (only up to `_r8` files are present). Issue
  #205's "Gates owed" line already says Gate A starts from the source formula, not the
  prototype, so the port proceeded from the issue's own quoted formula rather than blocking on
  the missing prototype file.
- Found `pandas_ta/performance/mtd_ret.py` (issue #206, same Reddit thread, same quote,
  month-anchored) already shipped. Its receipt (`docs/MtdRetMeasured.md`) explicitly flags this
  gap: "#205 asks for the quarter form... no period parameter was added here." Used it as the
  direct template — same validation, same NaN/zero-anchor handling, same offset/fillna
  plumbing — with the grouping key changed from `year*12+month` to `index.quarter`
  (`DatetimeIndex.quarter`, checked against the issue's own month-range mapping).
- Wrote `pandas_ta/performance/qtd_ret.py`, wired it into
  `pandas_ta/performance/__init__.py`, `pandas_ta/__init__.py` (`Category["performance"]`),
  `pandas_ta/core.py` (`AnalysisIndicators.qtd_ret`).
- Wrote `tests/test_qtd_ret.py` (24 tests): hand-derived correctness across a quarter and a
  year boundary, an independent per-bar loop, tz-local-time reset, missing/zero first-open
  blanking, unsorted/NaT/mismatched-index rejection, a strategy-sweep skip test, offset/fillna,
  two causality mutants (`exec`'d in memory: last-open anchor, one-bar-late anchor) swept over
  all 899 offsets, x8/x64 bit-identical and x10/x3.7 tolerance scale tests, and a wiring test.
  Every leak/offset count in the test docstring is `python docs/measure_qtd_ret.py`'s printed
  output, not hand-typed.
- Wrote `docs/measure_qtd_ret.py` (prints the Gate A/B/C/D numbers) and
  `docs/measure_qtd_ret_cpu.py` (re-runs `tests/test_qtd_ret.py` with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, per the system prompt's CPU-variant
  rule). Both ran; 24/24 pass under both dispatches.
- Regenerated `docs/IndicatorDictionary.md` (`python docs/gen_indicator_dictionary.py`): diff is
  exactly the `qtd_ret` row, the `performance (7 -> 8)` header, and the three package-wide
  counts (368/376/370 -> 369/377/371), tagged `SF`.
- Updated `README.md` (headline counts, `performance (6)` -> `(7)` row),
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 368 -> 369, chain comment), and
  `docs/MLCompanionContract.md` (713 -> 714 tagged columns, 348 -> 349 `SF`, new chain entry),
  consistent with what `test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
  recomputes from the dictionary.
- Wrote `docs/QtdRetMeasured.md`: Gate E section reads "pending, run by issue-solver after this
  session" per the system prompt's override rule, not the issue's Gate E instructions directly.
  Gate F section records only the subset command run and its result, plus "Whole suites: run by
  issue-solver in clean worktrees (see the PR body)" — no whole-suite count claimed.
- Ran `python -m pytest -q tests/test_qtd_ret.py tests/test_readme_counts.py
  tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
  tests/test_prose_counts_match_the_csvs.py`: **1 failed, 1354 passed, 7 skipped**. The one
  failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected
  per the system prompt until the launcher's Gate E run and a receipt session record the ledger
  row.
- ASSUMPTION: no `period=` parameter added to `mtd_ret`, and no generalized period system
  built. Took the smaller-scope reading `mtd_ret`'s own receipt anticipated (a second,
  independently-measured module) over the larger-scope alternative (refactoring the already
  shipped, measured `mtd_ret` into a parametrized form), since `AskUserQuestion` is unavailable.
- ASSUMPTION: category `performance`, matching `mtd_ret`'s precedent (same source, same shape:
  an open/close period-return pair of inputs), not `overlap` or `trend`.

## Review round 1

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/performance/qtd_ret.py:1 (whole file, vs pandas_ta/performance/mtd_ret.py)
    problem:  qtd_ret.py is a structural clone of mtd_ret.py -- validation block, zero-guard, offset, fillna, and docstring shape are copy-pasted with only the groupby key (month->quarter) and names swapped. The receipt's "no period parameter" paragraph defends against one alternative (a `period=` flag bolted onto the shipped `mtd_ret`) but never considers the middle path: a small shared private helper the two thin wrappers both call.
    fix:      Not a blocker given this repo's established mtd_ret/seas precedent of one module per period -- but file a follow-up note (or a TODO in the receipt) that the next period-anchored port (ytd_ret, wtd_ret, ...) should factor the shared logic into a helper before a third copy-paste makes drift between the two modules' NaT/zero-guard/offset handling a real risk.

SUMMARY: I re-ran the measure script and the full required test subset myself rather than trusting the receipt, and every number checked out exactly -- non_nan=900, above=438/below=462, min/max/median, the 886/14/13 causality split, the 65-bar blank-quarter NaN count, the 2.22e-16 scale tolerance, and the "1 failed (the expected ledger row), 1354 passed, 7 skipped" suite result all matched the live run bit-for-bit. The hand-derived test genuinely spans a quarter boundary that isn't a year boundary as claimed, the mutant tests compute their expected leak counts in-test rather than hardcoding them, the quarter key matches pandas's own `.quarter` mapping against the issue's stated ranges, Gate E is correctly left pending rather than fabricated, and all five wiring touch points plus every count edit (README, IndicatorDictionary, MLCompanionContract, CATEGORY_TOTAL) are mutually consistent and match the live package. The one thing worth a sentence in the next session's notes is that this is the second verbatim copy of mtd_ret's body with no shared helper -- acceptable once, a liability the third time. This clears the bar; don't let it go to your head.
```

### Fixes applied
- None required (NIT only, does not gate per the rubric). Noted here, not acted on: if a THIRD period-anchored port (e.g. `ytd_ret`) is ever added, factor `mtd_ret`/`qtd_ret`'s shared validation/zero-guard/offset/fillna body into a private helper rather than copy-pasting a third time.

## Outcome
PASS (round 1)
