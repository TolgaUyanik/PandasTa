# Brutally Honest Review — vwd port (issue #202), round 2

**Date:** 2026-11-25
**Target:** docs/VwdMeasured.md, docs/measure_vwd.py, pandas_ta/momentum/vwd.py, tests/test_vwd.py (round-1 report docs/reviews/2026-11-25-vwd-review.md as context)
**Type:** code (with text: receipt and docstrings)
**Verdict:** PASS

## Round-1 MAJOR — resolved

`docs/measure_vwd.py` has a `B1U` section (lines 363-375) that applies a uniform ×1.03 suffix at `OFFSETS[0]` to `CAUSALITY_MUTANTS[3:5]` on `SWEPT`. The reviewer ran `python -W ignore docs/measure_vwd.py B1U A4`, which printed:

* vp-lead: 1.930e-14 / 1.097e-13 / 1.703e-13
* vs-lead: 5.551e-16 / 1.599e-14 / 2.359e-16

Both match the receipt's §B1U, the FACTORS comment and the test docstring. The test is parametrized over vp-lead and vs-lead × the three swept frames. All round-1 MINOR and NIT findings were addressed as well.

## Findings

### MINOR / NIT
- **MINOR — docs/VwdMeasured.md:232-234 (§L, last sentence) vs :21-31 (header exceptions)** — §L quotes "0.2640, against `PPIVOT_MAOFFSET_10_10`", issue #202's fork-overlap figure. No script section prints it, and exception 3 covers only §E0's screen figures.
  - Fix: Change exception 3 to "§E0's screen figures and §L's closing fork-overlap figure (0.2640) are issue #202's, quoted", or move that sentence into §E0.
- **NIT — pandas_ta/momentum/vwd.py:114-118 (docstring)** — "Kept as the source computes it" now reads as if it covers the H < L blanking, which is the deviation from the source. Line 117 is also much longer than the lines around it.
  - Fix: Move "Kept as the source computes it" so it follows the H == L sentence. End the paragraph with "An H < L bar (corrupt data) is blanked the same way, although the source would compute it: a deliberate deviation." Rewrap to the file's line width.
- **NIT — tests/test_vwd.py:390, :460 (test names); :24-27 (module docstring item 2)** — The test names are stale: they also cover V = NaN and vs-lead. Docstring item 2 mentions only V == 0.
  - Fix: Rename them to `test_volume_cancels_except_where_it_is_zero_or_nan` and `test_a_uniform_suffix_rescale_cannot_see_a_vp_or_vs_lead`. Append "or NaN (same 1,473, same bars)" to item 2. Update the test name quoted at VwdMeasured.md:140.

## Summary

The round-1 MAJOR is fixed, and the reviewer re-ran the script to check it. `B1U` reproduces every number that is quoted, and the test covers both mutants. Every round-1 MINOR and NIT was addressed:

* H < L is disclosed and pinned by a test.
* The §C3 speculation is gone.
* V NaN is disclosed, measured and tested.
* The two oracles match token for token.
* The 0.85 line is replaced by thresholds that CLAUDE.md and the issue define.

The docstring's first paragraph is unchanged, so `docs/IndicatorDictionary.md` is not stale. `tests/test_vwd.py` passes 124/124. What is left is one quoted issue figure outside the named exceptions, plus stale names and wording. None of it blocks shipping.

The reviewer ran only `B1U`, `A4` and `tests/test_vwd.py`. It did not re-run the other sections or the multi-file run quoted in §F.
