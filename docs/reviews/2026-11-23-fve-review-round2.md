# Brutally Honest Review — fve port (issue #260), round 2

**Date:** 2026-11-23
**Target:** tests/test_altport2_ports.py, docs/FveMeasured.md, pandas_ta/volume/fve.py, tests/test_fve.py, docs/reviews/2026-11-23-fve-review.md (re-review of round 1: docs/reviews/2026-11-23-fve-review.md)
**Type:** code (with text receipts)
**Verdict:** PASS

## Round-1 CRITICAL/MAJOR resolution

- **MAJOR (docs/FveMeasured.md, the "wider screen" paragraph quoting numbers from outside the repo)**: **resolved.** The paragraph is gone. Every number in the Non-redundancy section is now printed by `python -W ignore docs/measure_fve.py`: 0.7951 / 0.8714 / 0.6500 / 0.1890, plus the 12-frame medians, minimums and maximums.

## Findings

### MINOR / NIT
- **MINOR — docs/FveMeasured.md (Gates rows C and D) and the tests/test_fve.py module docstring (the "878 of 900 here" and "x10 and x3.7 were bit-identical" lines).** The receipt says the 900-bar frame has "435 positive / 443 negative" and that the same frame "also measured 0 at ×10 / ×3.7". `docs/measure_fve.py` prints neither number, because it only runs the 1,500-bar frame. The test the receipt names, `::test_fires_and_is_not_constant`, only asserts `fires == 878` and `(d>0).any()`. The x10/x3.7 test asserts `< 1e-9`, not 0. The reviewer re-ran both and the numbers are true (878 / 435 / 443, and max|diff| = 0.0 at x10 and x3.7), but no named run in the repo produces them.
  - Fix: Add a block to `docs/measure_fve.py` that runs `_frame(900)` and prints fires, the positive and negative counts, and max|diff| at x10 and x3.7, then cite its output. Alternatively, delete "(435 positive / 443 negative)" and "The 900-bar test frame also measured 0 at ×10 / ×3.7" from the receipt, and the matching phrases from the test docstring.
- **NIT — tests/test_altport2_ports.py:196 (`CATEGORY_TOTAL` comment).** The round-1 NIT is half fixed. The receipt pointer and the Gate E status are in, but the separator still reads `docs/FveMeasured.md),+1 on issue #146's`, with no space after the comma.
  - Fix: Change `),+1 on issue #146's` to `), +1 on issue #146's`.
- **NIT — pandas_ta/volume/fve.py:57.** `cutoff=True` is accepted as 1.0 and names the column `FVE_22_1.0`. A string such as `'0.01'` raises `TypeError` at the `>=` comparison instead of being converted by `float()`. No caller is likely to hit either case.
  - Fix (optional): `cutoff = float(cutoff) if cutoff is not None else 0.003; cutoff = cutoff if cutoff >= 0 else 0.003`. Otherwise leave as is; this does not block.

## Summary

The round-1 MAJOR is fixed, and the round-1 MINOR fix caused no regression. The receipt's other script-sourced numbers all match a fresh run of `docs/measure_fve.py`: 1,478 values, 718 / 760, +650 / −617 / 232, 315 pinned closes, bit-identical scaling, 0/35 and 35/35 leaks, bar 721, and inf = 0.

The `cutoff` change behaves as described:

- `cutoff=0` names the column `FVE_22_0.0`, and its output differs from the default.
- A negative cutoff falls back to `FVE_22`.
- The default still names the column `FVE_22`.

The Args text, the Returns naming, the receipt's naming and strict-band claims, and the dictionary row (`cutoff=None`, `FVE_22 SF`, warm-up 22) all match the code. The "for non-negative volume" wording is in both docstring spots.

Test runs:

- `tests/test_fve.py`: 24 tests, all passing.
- A three-file run: 49 passed, 3 skipped.
- The receipt's seven-file run reproduced exactly: 1405 passed, 8 skipped.

What remains is small: two 900-bar figures that are true but come from no named run, and a missing space in a comment. Neither blocks the port.

The reviewer did not run the full suite or the parent repo, and did not regenerate the dictionary. Gate E is still owed. As the receipt says, it could come back DISCLOSE against `G191_040_26`: the 12-frame median |ρ| is 0.8155.
