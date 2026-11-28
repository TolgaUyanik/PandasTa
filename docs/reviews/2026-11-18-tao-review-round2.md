# Brutally Honest Review — tao (issue #266, TAO-10-5), round 2

**Date:** 2026-11-18
**Target:** pandas_ta/momentum/tao.py, docs/reviews/2026-11-18-tao-review.md (re-review: round-1 CRITICAL/MAJOR resolution + files changed since)
**Type:** code
**Verdict:** PASS

## Findings

### MINOR / NIT
- **NIT — pandas_ta/momentum/tao.py:82-85 (`tao.__doc__`, the NaN paragraph)** — The corrected sentence was not rewrapped. Line 83 ("first value is on bar 13. NaN also for `ma_length` bars") stops well short of the width the rest of the docstring uses, so the paragraph is ragged. The text itself reads correctly.
  - Fix: Rewrap the paragraph to the same width as the rest of the docstring: "NaN on bars 0 .. 12 (the first `length + ma_length - 2` = 13 bars); the first value is on bar 13. NaN also for `ma_length` bars from any bar whose 10-bar range is exactly 0 (a flat window), since the rolling mean then has a NaN in its window."

## Summary

The one CRITICAL from last round is fixed. tao.py:82-83 now says "NaN on bars 0 .. 12 (the first `length + ma_length - 2` = 13 bars); the first value is on bar 13". A run on a random walk confirms it: bars 0..12 are NaN and `first_valid_index()` is 13. The wrong "0 .. 13" claim does not appear anywhere else. Grepping tests/test_tao.py, docs/TaoMeasured.md:118, docs/measure_tao.py:33 and docs/IndicatorDictionary.md:149 (warm-up column 13) shows they all say a 13-bar warm-up with the first value at `length + ma_length - 2` = 13, which matches. The rest of the edited paragraph holds up. A single flat bar gives a NaN O, which blanks that bar and the next four, so "NaN for `ma_length` bars" is right for an isolated flat window. The causal-span sentence (`T - 13 .. T`) also agrees with a 14-bar footprint. The mutant line strings still occur exactly once: tests/test_tao.py:243 and docs/measure_tao.py:234 assert `src.count(old) == 1`, all 142 tests pass, and `measure_tao.py B` runs clean. docs/reviews/2026-11-18-tao-review.md is an accurate record of round 1: REVISE, one CRITICAL with the exact fix that was applied, no MAJOR, and seven MINOR and one NIT. Still open, left on purpose: the coarse-frame wording in the test docstring (test_tao.py:27-28), the receipt's claim that `flat` is bit-identical under the exact factors, which the script never prints, and the `TAO_14_3_40` name in §W, also never printed. Also open: `:g` naming can give two midpoints the same column name, the hand-derived L-sweep claims and the "5 TAO bars" header, the `_coarse` flat-window wording, the unstated reading of "5 values of O", and the 1,333-passed count, which depends on test order.

Not checked by the reviewer: the full suite (as instructed), and the sections of measure_tao.py other than B. tao.py is untracked, so the reviewer could not diff it to isolate the round-2 edit and reviewed the whole docstring instead.
