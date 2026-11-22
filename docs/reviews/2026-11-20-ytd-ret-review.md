# Brutally Honest Review — ytd-ret

**Date:** 2026-11-20
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/performance/__init__.py, tests/test_altport2_ports.py, docs/YtdRetMeasured.md, docs/measure_ytd_ret.py, pandas_ta/performance/ytd_ret.py, tests/test_ytd_ret.py (issue #204 port, uncommitted)
**Type:** code (with a text receipt)
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/YtdRetMeasured.md:26-29 ("Fork overlap (synthetic, not Gate E)")** — The receipt quotes seven numbers that nothing in the repo can reproduce: `MADISP_200_SMA` 0.7853 (range 0.6235–0.8582), `percent_return` at 126/189/252/63 (0.7376/0.7039/0.6852/0.6420), and `mtd_ret` 0.3391. `docs/measure_ytd_ret.py` prints none of them. They came from a deleted `/tmp/ytd204.py`. CLAUDE.md and the acceptance criteria require every number in the receipt to be reproducible by `docs/measure_<name>.py`. A /tmp script is not acceptable. The paragraph also ends "None at the 0.85 equivalence line". No 0.85 line exists anywhere in the issue or in CLAUDE.md: the issue's fork-overlap line is 0.90, and CLAUDE.md's Gate E bands are 0.76/0.80/0.90. That is an invented threshold attached to a claim.
  - Fix: Either move the synthetic fork-overlap computation into `docs/measure_ytd_ret.py` (12 frames, seeds, tick rounding, Spearman per frame, median |ρ|, plus the range for `ma_disparity`) so the script prints every quoted value, or delete the paragraph. In both cases, replace "0.85 equivalence line" with the issue's 0.90 line or remove the sentence.

### MINOR / NIT
- **MINOR — docs/YtdRetMeasured.md:19-29 (Gate E owed section)** — The receipt quotes the prototype's Gate E numbers but drops the issue's real fork-overlap result: 0.7678 vs `ma_disparity:MADISPSQ_200_SMA` on 12 real frames, per-frame max median 0.7670. In its place is a synthetic figure against a different column, `MADISP_200_SMA`. It also leaves out the caveat that `MtdRetMeasured.md` states: Gate E compares against the engine only, so this fork's columns are still not measured against the port. A reader could take the synthetic 0.7853 as the overlap measurement.
  - Fix: Add the issue's line ("prototype, stage 2, 12 real frames: 0.7678 vs `MADISPSQ_200_SMA`, per-frame 0.7670, below 0.90") and a sentence saying the fork overlap has not been measured on the port. Keep any synthetic figure only if the script reproduces it, and label it clearly as synthetic.
- **MINOR — docs/YtdRetMeasured.md:40 (Gate F row)** — "1246 passed, 8 skipped" does not say whether `GATE_E_PENDING_OK=1` was set. Without it, `tests/test_gate_e_ledger.py` fails locally on the owed `ytd_ret` row (CLAUDE.md: "on every local run the variable is not `1` and these fail"). So the stated result cannot be reproduced from the command as written. The reviewer could not re-run it because the sandbox blocked the env-prefixed command.
  - Fix: Write the exact command with `GATE_E_PENDING_OK=1` and state that the 8 skips include the "Gate E owed" skip. Or report the run without the variable and its 1 expected failure.
- **NIT — pandas_ta/performance/ytd_ret.py:54 and docs/YtdRetMeasured.md:52** — "(#205 asks for the quarter form)" is a cross-reference that nothing in this change or the issue text supports.
  - Fix: Cite #205's title or remove the parenthetical.

## Summary

The code is fine. It is a faithful copy of `mtd_ret` with the grouping key changed to `index.year`, and every touch point is wired: module, `performance/__init__`, `Category`, a `core.py` accessor that forwards `offset`, and the test file. Gate A cites the issue's formula, with a hand-derived frame that crosses a month boundary. Gate B is a real exec'd-mutant sweep over all 899 offsets: 0 leaks for the real module, 896 for the last-open mutant, 4 for the one-bar-late mutant. Gate D is bit-identical at ×8/×64, has a 260-bar NaN mask, and fires on 279 of 900 bars. All 23 tests pass. `python -m docs.measure_ytd_ret` reproduces every A–D number in the receipt exactly. Counts check out: README 362/370, performance 7, `CATEGORY_TOTAL` 362, the dictionary row `YTD_RET` SF, and 343 `SF` tags. The empty-series and duplicate-timestamp edge cases behave. The receipt has the defect CLAUDE.md calls the dominant historical one, a claim nobody can re-run: a whole paragraph of fork-overlap numbers from a deleted /tmp script, judged against an invented 0.85 line, while the issue's real 0.7678 figure is left out. Script it or cut it, fix the threshold, and this passes.

## Reviewer's caveats

- The reviewer did not run the Gate F test set (the sandbox blocked the env-prefixed command) and did not regenerate the dictionary to diff it.
- The reviewer's own quick regex count of the dictionary gave 706 tags, not 707 (`PX` 136 vs 137). It put that down to its regex but did not confirm it. The main session's count, `/tmp/tagcount204.py` against HEAD and the regenerated file, gave 707 tags and 343 `SF`.

## Main-session notes (not reviewer findings)

- The 0.85 threshold was not invented. It is the equivalence cutoff from the pre-port analysis task in this session, not a CLAUDE.md band. The receipt still needs to say where it comes from.
- `/tmp/ytd204.py` still exists. It was not deleted, but it is outside the repo, so the reproducibility finding stands.
- The targeted run quoted in the Gate F row was a plain `python -m pytest ...` with no variable set in that shell, and `test_gate_e_ledger.py` passed. Why it passed was not checked; the variable may already be set in the environment.
