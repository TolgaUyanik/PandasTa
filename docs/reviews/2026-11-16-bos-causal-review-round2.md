# Brutally Honest Review — bos-causal (round 2)

**Date:** 2026-11-16
**Target:** CLAUDE.md (task list said "LAUDE.md", a typo), README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/trend/__init__.py, pandas_ta/trend/bos_causal.py, tests/test_altport2_ports.py, tests/test_bos_causal.py, docs/BosCausalMeasured.md, docs/measure_bos_causal.py, docs/indicators/README.md and every docs/indicators/*.md page (about 241 tracked pages modified, about 120 new untracked pages)
**Type:** code plus docs/receipt
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/indicators/*.md (about 241 tracked pages modified); docs/indicators/README.md; docs/indicators/fvg.md** — The regeneration ran without the parent `../Backtesting` repo and silently overwrote correct content with false-looking content. (a) `fvg.md` lost its "Gate E run exists ... g3_fvg" note and now says "found no campaign record". (b) Register verdicts such as "OK (as FVG_BULL)" became "no row" across the diff. (c) `docs/indicators/README.md` now reads "**0** indicators have a Gate E run", where it said 14; the measured-page list lost `fvg` and the measured count fell from 40 to 39. The remaining diff is byte-count noise in the "Module length" rows (adx 5411 -> 5263), which looks like a line-ending difference. This is unrelated churn that degrades existing evidence, and the "0 Gate E runs" claim is false.
  - Fix: Restore the tracked pages (`git checkout -- docs/indicators`, and the dictionary/contract if they picked up unrelated churn). Keep only the `bos_causal` additions by hand: one new page `docs/indicators/bos_causal.md`, the `trend` count and row in `docs/indicators/README.md`, and the `bos_causal` rows in the dictionary and companion contract. Or regenerate where the parent repo and a matching line-ending setting are present. Do not commit the ~120 never-generated pages as part of this change.

- **docs/indicators/bos_causal.md (§6, §12, header "Tests" row)** — The page says `tests/test_bos_causal.py` "produced no case in the recorded full-suite run", and §6 and the Gate B/C/D rows are stubs, contradicting the shipped receipt, which has real Gate A-D evidence. `gen_indicator_pages.py --check` reports "WOULD CHANGE: bos_causal.md", so the page is also stale against the generator. §1/§3/§4 "owed by a human" fields are left as STUB.
  - Fix: Hand-fill §1, §3, §4, §5, §6 and §12 from `docs/BosCausalMeasured.md` and `tests/test_bos_causal.py`, then re-run `--check` and confirm no change for that page.

- **Whole change vs issue #332 ("Delete tests/test_bos_lookahead.py", "fix in place"); CLAUDE.md:129-134; docs/BosCausalMeasured.md "Not done here"** — The ask was an in-place fix. This ships a new `bos_causal` beside `bos` and `choch`, which still leak by 1-4 bars. The departure is disclosed accurately in the receipt and CLAUDE.md, and the orchestrator directed it, so honesty is not the problem, but the issue's "Done when" (shipped, or measured and reverted) is not met. The reviewer could not confirm that the orchestrator's instruction overrides the owner's issue text.
  - Fix: Either (a) apply the issue as written (`bos.py` and `choch.py` use the causal confirmation, delete `tests/test_bos_lookahead.py`, update CLAUDE.md), or (b) get written owner approval for the sibling-indicator path and record it in the receipt and CLAUDE.md, stating in the receipt header that issue #332 is NOT closed.

### MINOR / NIT
- **docs/BosCausalMeasured.md, "How to reproduce"** (MINOR) — Gate A and the mutant results are asserted only by pytest, not by the script. Every printed number in the receipt matches a fresh run (counts 6258, 6658, 1995, 1956, 546, 607, 3743 tie bars, Spearman 0.7256/0.7332/-0.0689/-0.0669/0.7043/0.7062, 0 edge mismatches, reach 0, 1, 2, 3, 4), but "every number reproducible by that script" is not strictly true.
  - Fix: Have the script run Gate A (`_ref`) on 8 frames x 4 lengths and the mutant and print pass/caught lines, or say plainly that those two are test-only.
- **tests/test_altport2_ports.py (`CATEGORY_TOTAL` comment)** (NIT) — The new "+1 on issue #332" entry is prepended to a 4 KB one-line comment in reverse-chronological order.
  - Fix: Leave as is, or move the history to a docstring. Low priority.

## Summary

The code is solid: `bos_causal` passes its 49 tests, the mutant is real, ties are right, the scale tests pass, every receipt number reproduces on a fresh run, and the `README.md`/`CATEGORY_TOTAL`/`core.py` wiring is consistent. The departure from the issue is disclosed honestly, but the issue is not actually fixed, since `bos` and `choch` still leak. The docs churn is the real blocker: regenerating 241 pages without the parent repo replaced correct Gate E and register evidence with "no row" and "no campaign record", and dropped the Gate E count from 14 to 0. Revert that churn. The new `bos_causal.md` page is stubbed and contradicts the receipt. Fix the pages and obtain owner sign-off on the sibling-indicator route, or do the in-place fix.

Not checked by the reviewer: the full test suite (only `test_bos_causal`, `test_bos_lookahead`, `test_altport2_ports` and `test_indref_pages` were run, all passed), and the parent repo (access blocked, so its absence was inferred from the page diffs).
