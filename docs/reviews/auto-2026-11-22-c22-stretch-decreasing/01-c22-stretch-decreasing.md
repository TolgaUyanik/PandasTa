# Task: c22-stretch-decreasing (issue #140)

## Round 1

VERDICT: REVISE

FINDINGS (verbatim):
- severity: MAJOR
  location: tests/test_c22_stretch_decreasing.py:35-37 (module docstring, item 2)
  problem:  The module docstring claims "the real module leaks 0 of 68 offsets on three frames (24 independent random splices each) while the four equivalent one-bar mutants are each caught on only 1 to 3 of those 68." Every number in that sentence is false, and is falsified by this same file and by a live run:
            - `OFFSETS = range(140, 1500, 40)` (line 247) is 34 offsets, not 68 — the file's own later comment at line 292 even says "offsets of 34 caught."
            - `_leak_offsets(fn, close, offsets=OFFSETS, splices=8)` (line 261) uses 8 splices per offset, not 24.
            - `CAUGHT` (lines 302-309) has no value above 2, so "1 to 3" is wrong; it is "1 to 2".
            - `python docs/measure_c22_stretch_decreasing.py gate_b` (re-run live) prints exactly "34 offsets ... 8 independent random splices tried per offset" and "caught 1/34" / "caught 2/34" for every one-bar mutant on every frame — never 3.
            This is precisely the project's self-described dominant defect ("a claim written before it was measured"), sitting inside the one file whose entire job is to pin measured numbers. It is also self-contradictory within the same file, not merely stale.
  fix:      Replace line 35-37's clause with the numbers the file (and `docs/C22StretchDecreasingMeasured.md`, which already has this right) actually produces: "the real module leaks 0 of 34 offsets on three frames (8 independent random splices each) while the four equivalent one-bar mutants are each caught on only 1 to 2 of those 34." Grep the rest of this docstring and `docs/measure_c22_stretch_decreasing.py`'s docstring for any other hand-typed count and re-derive each one from a harness run before shipping.

SUMMARY (verbatim): The port itself is in good shape — Gate A, D, the noise
floor, the wiring touch points, and MIN_LENGTH=2 reasoning all check out
against a live re-run, and docs/C22StretchDecreasingMeasured.md's numbers
reproduce exactly on this machine (1,436 passed / 7 skipped / 1
expected-owed failure, and all 90 tests still green under disabled
AVX/FMA kernels). But the test suite's own module docstring — the thing
that is supposed to be the trustworthy index of what each test proves —
ships a sentence with three wrong numbers (68 instead of 34, 24 instead of
8, "1 to 3" instead of "1 to 2") that is contradicted by code eight lines
later in the same file and by a thirty-second harness run. That is not a
rounding error, it is the exact failure mode this repo's CLAUDE.md names
as its worst habit, caught inside the artifact whose entire purpose is to
prevent it. Fix the sentence, re-grep for siblings, and this ships.

## Fixes applied (round 1)

1. Fixed the docstring sentence in `tests/test_c22_stretch_decreasing.py`
   (item 2 of the file's "what this file pins" list) to read "0 of 34
   offsets on three frames (8 independent random splices each) ... caught
   on only 1 to 2 of those 34" — the numbers the code and the measure
   script actually produce, and that `docs/C22StretchDecreasingMeasured.md`
   already stated correctly.
2. Grepped the whole diff (`68\b`, `/68`, `24 independent`, `24 random`)
   across `tests/test_c22_stretch_decreasing.py`,
   `docs/measure_c22_stretch_decreasing.py`,
   `docs/C22StretchDecreasingMeasured.md` and
   `pandas_ta/statistics/c22_stretch_decreasing.py` — no other occurrence
   of the stale numbers found.

Verification after fix:
`python -m pytest -q tests/test_c22_stretch_decreasing.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ 1,436 passed, 7 skipped, 1 failed (the expected Gate-E-owed ledger test).

Re-dispatched the Fletcher reviewer for round 2.

## Round 2

VERDICT: PASS

FINDINGS (verbatim): none.

SUMMARY (verbatim): The round-1 fix is exactly correct —
`python docs/measure_c22_stretch_decreasing.py gate_b` prints "34 offsets J
= 140..1460 step 40, 8 independent random splices tried per offset", the
real module leaks 0/34 on all three frames, and all four one-bar mutants
land at 1/34 (walk, ar1) or 2/34 (tick-rounded) — never 3, never the old
68/24/"1 to 3" numbers, which a repo-wide grep confirms are gone everywhere
relevant. Every section of the harness (`gate_a`, `gate_b`, `noise_floor`,
`gate_c_d`, `cost`) and the CPU-kernel variant reproduced every number in
`docs/C22StretchDecreasingMeasured.md` bit-for-bit (Gate A 1,400/1,400
oracle match, Gate C's 3/6/4/4 distinct values and exact value/count
tables, Gate D's bit-identical rescales, the noise-floor spans down to the
exponent, and the 382.3 MB peak at 400k bars; only wall-clock drifted,
which is expected machine noise and not a pinned claim). The full targeted
suite ran 1,436 passed / 7 skipped / 1 failed, the one failure being
exactly the expected Gate-E-owed ledger test. Spot-checks of Gate A, the
Gate B engineered-window proof, the NOISE_FLOOR guard's rationale and exact
constant, MIN_LENGTH=2's reasoning, and all three wiring touch points all
still hold with nothing regressed. No new hardcoded count anywhere in the
diff is unverified.

No further fix round. Run complete.
