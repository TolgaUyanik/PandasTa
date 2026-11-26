# Brutally Honest Review — b3-outside-pivot3 (issue #199), round 2

**Date:** 2026-11-25
**Target:** tests/test_altport2_ports.py, docs/B3OutsidePivot3Measured.md,
docs/measure_b3_outside_pivot3.py, pandas_ta/candles/b3_outside_pivot3.py,
docs/reviews/2026-11-25-b3-outside-pivot3-review.md. This round checks the round-1
MAJOR and reviews the files changed since then.
**Type:** code (with docs)
**Verdict:** PASS

## Round-1 MAJOR — resolved

Decision 4's numbers are now produced by `decomposition()` in
`docs/measure_b3_outside_pivot3.py`, which `__main__` calls. Re-run by the reviewer:
14 frames × 2,000 bars, 26,600 rows after burn-in, 1,689 ties, 48–97 fires per frame,
0 mismatches on every frame. Median ρ is 0.4528 against `CDL_INSIDE` (min 0.4106,
max 0.5108) and −0.0857 against `RD_OUTSIDE_BAR` (min −0.1046, max −0.0568). These
match the receipt. The receipt's sha1 `5a14f7e6194fff4b8f6fe3028b6d4180fbb18359` matches
what the script now prints.

## Findings

### MINOR / NIT
- **MINOR — docs/B3OutsidePivot3Measured.md, Decision 4 ("the best single shipped column")**
  — This sentence claims `CDL_INSIDE` has the highest ρ of any shipped column, but
  `decomposition()` only measures two columns (`CDL_INSIDE` and `RD_OUTSIDE_BAR`). No
  run compares the flag against the rest of the package, so the claim has no evidence
  behind it. The prototype's Gate E screen put the top comparator at `HIGHER_HIGH`
  0.1318, but that is a different measure on different data and does not settle it.
  - Fix: Change "the best single shipped column" to "the higher of the two columns
    measured". Or drop the phrase.
- **NIT — docs/B3OutsidePivot3Measured.md, Decision 4 (row base)** — The text implies the
  mismatch count uses the same 26,600 rows. It does not: `decomposition()` counts
  mismatches over `iloc[2:]` (1,998 rows per frame, 27,972 in total), and the 100-bar
  burn-in only applies to the ρ rows.
  - Fix: Write "0 mismatches on every frame (all 1,998 settled bars per frame); ρ on
    26,600 rows after a 100-bar burn-in."
- **NIT — pandas_ta/candles/__init__.py:3** — The round-1 NIT is still open: the import
  order does not match the alphabetical `Category` list. It has no effect at runtime.
  - Fix: Move `from .b3_outside_pivot3 import b3_outside_pivot3` above
    `from .ha import ha`, or leave it.

## Summary

The round-1 MAJOR is fixed, and the reviewer checked the fix by running it. Every
Decision 4 figure matches the `decomposition()` output, which uses
`cdl_inside(asbool=True)`, the correct equivalence. The quoted sha1 matches the module
after the docstring change. Three of the four round-1 MINOR/NITs are fixed (the Gate F
"owed" line, the `CATEGORY_TOTAL` comment, `asbool=True` in the docstring). The fourth,
the import order, is cosmetic and still open. The Gate A–D numbers reproduce unchanged.
The targeted tests pass: 72 passed, 3 skipped. The module change is docstring-only.
What remains are one unsupported superlative and some row-count wording, neither of
which blocks.

Not checked by the reviewer: the full suite, the Backtesting suite, Gate E, and whether
the dictionary regeneration is byte-exact.
