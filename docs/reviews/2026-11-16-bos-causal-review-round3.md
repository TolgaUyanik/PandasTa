# Brutally Honest Review — bos-causal (round 3)

**Date:** 2026-11-16
**Target:** CLAUDE.md (task list said "LAUDE.md", a typo), README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/trend/__init__.py, tests/test_altport2_ports.py, docs/BosCausalMeasured.md, docs/indicators/bos_causal.md, docs/measure_bos_causal.py, pandas_ta/trend/bos_causal.py, tests/test_bos_causal.py
**Type:** code plus docs/receipt
**Verdict:** PASS

## Findings

### MINOR / NIT
- **docs/indicators/bos_causal.md §3 "Module length"** (MINOR) — The page says "142 newline-terminated lines, 4925 bytes". Fresh counts are `grep -c ''` = 143 and `wc -c` = 4948, so the specific count is false.
  - Fix: Change the row to 143 lines, 4948 bytes. Better, drop the row, since it goes stale on any edit.
- **docs/indicators/bos_causal.md §10** (MINOR) — Every table cell is STUB, but the text underneath says "**Nothing in either.**" and "The counts above come from one direct read of the tree". No such read produced counts. This is leftover generator boilerplate asserting a zero that was never measured.
  - Fix: Replace the paragraph with one line: "Not measured; module is new, no mining sweep has seen `BOSC_*`." Or run the greps against the parent repo and fill the cells.
- **docs/indicators/bos_causal.md header and Provenance and Status rows; §13** (MINOR) — The page still says it is "GENERATED" and that "Nothing here was hand-asserted", then contradicts that two lines later. Provenance, Status and §11 remain STUB, and the §13 metrics table is generator output for a page that was hand-edited. The page is honest enough but confusing.
  - Fix: Rewrite the header as "hand-written page, not generated". Fill Provenance and Status from the receipt, or delete the generator-only boilerplate.
- **pandas_ta/trend/bos_causal.py `_confirm` (np.nanmax/np.nanmin); page §4 "NaN windows follow the module"** (MINOR) — `bos` and `choch` use `rolling(L, center=True)` with the default min_periods, so any NaN in a window means no swing. `_confirm` instead ignores NaN and only skips all-NaN windows. A partially-NaN window can still register a swing, which the shipped modules and the issue's centred-window source would not. No test covers NaN input, so Gate A is silent on it and the page's "follow the module" wording is unsupported.
  - Fix: Either skip any window containing a NaN (`np.isnan(w).any()`) to match `rolling`, or keep the behaviour and add a NaN-input test. Reword §4 to say which one it is.
- **docs/BosCausalMeasured.md header and "Not done here"; CLAUDE.md lines ~132-134** (MINOR) — The change is a sibling indicator, not the in-place fix the issue asked for. `bos` and `choch` still look ahead, `test_bos_lookahead.py` is kept, and `bos` stays OPEN. This departure is disclosed in the receipt header, the receipt body and CLAUDE.md, and it follows the orchestrator's explicit instruction, so the reviewer treated it as an accepted, recorded limit and not a blocker. Owner approval of the sibling route is still owed and is stated as owed.
  - Fix: When the PR is opened, put "issue #332 is NOT closed; sibling route; owner sign-off pending" in the PR body so the merge does not auto-close the issue.

## Summary

The code is correct and the receipt holds up. A fresh run of `docs/measure_bos_causal.py` reproduced every number in `docs/BosCausalMeasured.md`: counts 6258, 6658, 1995, 1956, 546, 607, 3743 tie bars, x8/x64 bit-identical, x10/x3.7 with 0 mismatching cells, Spearman medians, 0 rising-edge mismatches, and reaches 0 vs `bos` 1/2/3/4 vs `choch` 1/2/1/1. A 1604-test run covering the bos_causal, indref-page, readme-count, wiring, altport and bos_lookahead tests passed. `git status` is clean apart from the target files and docs/reviews. The five wiring points are present, `core.py` forwards every parameter under its own keyword, and `CATEGORY_TOTAL`, README and the dictionary move consistently (355 to 356, trend 63). The mutant test is a real `importlib`/`exec` mutant, and the event logic matches `bos` and `choch` line by line. What remains is documentation polish plus one untested NaN divergence. None of these is a blocker, so the verdict is PASS.

Not checked by the reviewer: the full suite beyond the six test files above, and Gate E (owed, not a finding).
