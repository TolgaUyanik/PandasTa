# Brutally Honest Review — b3-outside-pivot3 (issue #199)

**Date:** 2026-11-25
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py,
pandas_ta/candles/__init__.py, pandas_ta/core.py, tests/test_altport2_ports.py,
docs/B3OutsidePivot3Measured.md, docs/measure_b3_outside_pivot3.py,
pandas_ta/candles/b3_outside_pivot3.py, tests/test_b3_outside_pivot3.py
**Type:** code (with docs)
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/B3OutsidePivot3Measured.md:41-47 (Decision 4)** — Decision 4 cites numbers that `docs/measure_b3_outside_pivot3.py` does not produce: "14 tick-rounded frames, 2,000 bars each, 26,600 rows after a 100-bar burn-in", "0 mismatches against that decomposition", "median Spearman ρ 0.4528 (`CDL_INSIDE`)" and "−0.0857 against `RD_OUTSIDE_BAR`". They came from a /tmp script that has since been thrown away. CLAUDE.md says every number in the receipt must be reproducible by the measure script, so these are unsourced. The reviewer re-ran the decomposition on 14 `_ticky(2000, s)` frames and got 0 mismatches, so that claim is true. The two ρ values cannot be checked from anything in the repo.
  - Fix: Add a `decomposition()` function to docs/measure_b3_outside_pivot3.py and call it from `__main__`. On seeds 0–13 it should take `_ticky(2000, s)`, drop the first 100 bars, and print (a) the mismatch count of `b3_outside_pivot3` against `rd_outside_bar(h,l).shift(1).astype(bool) & cdl_inside(o,h,l,c,asbool=True).astype(bool)` and (b) the per-frame Spearman ρ against `CDL_INSIDE` and against `RD_OUTSIDE_BAR`, with their medians. Then replace the Decision 4 numbers with that output. If the ρ values are not worth scripting, delete them and keep only the decomposition count once it is scripted.

### MINOR / NIT
- **MINOR — docs/B3OutsidePivot3Measured.md:123 (Gate F)** — The figure "1,558 passed, 8 skipped" comes from a hand-picked set of 7 test files, not the full suite. The issue's "Done when" asks for both repos' suites green. The receipt says it is a targeted run, but it never says the full suite is still owed. The reviewer re-ran the same command and got 1,558 passed, 8 skipped, so the number holds.
  - Fix: Add one line under Gate F: "Full PandasTa suite and the Backtesting suite are owed with Gate E; not run in this session."
- **NIT — tests/test_altport2_ports.py:196 (CATEGORY_TOTAL comment)** — The new entry reads only "+1 on issue #199's b3_outside_pivot3 port (candles)". Every recent neighbour (#168, #167, #166…) also gives a short description, the source id, the Gate E status and the receipt path. This one breaks that pattern.
  - Fix: Expand it to "+1 on issue #199's b3_outside_pivot3 port (candles; prior bar is both a strict 3-bar swing high and swing low; Reddit tier 4, rd:options:1k1hyso; Gate E: pending, run by issue-solver after this session; see docs/B3OutsidePivot3Measured.md)".
- **NIT — pandas_ta/candles/b3_outside_pivot3.py:82-83 (public docstring)** — "Equivalently, an outside bar at T-1 (`rd_outside_bar`) followed by an inside bar at T (`cdl_inside`)" is only true with `cdl_inside(asbool=True)`. With the default `asbool=False`, `cdl_inside` is multiplied by candle colour and returns signed ±1/0, so the equivalence fails. The same text is copied into the dictionary row.
  - Fix: Change it to "`cdl_inside(..., asbool=True)`".
- **NIT — pandas_ta/candles/__init__.py:3** — The new import goes after `from .ha import ha`, but `Category` and README list the names alphabetically.
  - Fix: Leave it, or move it so the imports are ordered the same way as the `Category` list. It has no effect at runtime.

## Summary

The code is right, and the reviewer checked rather than assumed it. The formula matches the issue line by line: strict on both sides, the flag written on bar T, two warm-up NaN bars, and open/close never read. All five wiring points are present, and the accessor passes `high`, `low` and `offset` under the right keywords. Gate B uses a real mutant that is exec'd in memory: the real module leaked at 0 of 293 J values and the mutant at 12. Gate D is bit-identical at ×8, ×64, ×10 and ×3.7, with 69 fires out of 1,998 bars. The measure script reproduces every number in Gates A, B, C, D and the sha1 exactly. The new test file passes 33 of 33, and the README, `CATEGORY_TOTAL`, dictionary and contract counts all match. The one real problem is the receipt itself. Decision 4 includes ρ values (0.4528, −0.0857) that only ever existed in a deleted /tmp script, and the project rule says that is not allowed in a receipt. The reviewer reproduced the 0-mismatch decomposition independently, but the ρ values cannot be checked. Script them or delete them, then this passes. The Gate F count is acceptably sourced because the targeted command is printed and re-runs to the same 1,558 passed and 8 skipped. It just needs to say that the full suites are still owed.

Not checked by the reviewer: the full suite, the Backtesting repo's suite, and Gate E.
