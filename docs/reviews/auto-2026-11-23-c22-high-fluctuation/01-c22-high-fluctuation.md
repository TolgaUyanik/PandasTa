# Gate review — c22-high-fluctuation (issue #144)

## Round 1

VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: tests/test_c22_high_fluctuation.py (test_a_two_return_window_is_a_forced_constant, test_min_length_three_is_informative_not_a_forced_constant)
    problem:  The docstrings cite the harness's sample sizes (3,000 / 30,000 draws) but the loops in the test functions themselves ran smaller counts (500 / 2,000) — the number next to the code did not match the number the code ran, the exact defect class CLAUDE.md names as this fork's dominant historical failure.
    fix:      Bumped both loops to run the cited counts (3,000 and 30,000) directly, so the docstring and the code agree without a cross-reference.
SUMMARY: The port is in genuinely good shape — the reviewer re-ran the measurement harness and the full targeted suite independently and every pinned number (Gate B's 0/34 real-module leak and the 15/8/14 and 9/6/8 mutant catch counts, Gate C/D's distinct-value counts and bit-identical rescales, the 1,481 passed/7 skipped/1 failed Gate F line, and the Gate-E-ledger failure naming only `c22_high_fluctuation`) reproduced exactly. The formula, window indexing, `MIN_LENGTH=3` math, Gate A oracle independence, Gate D epistemic hedging, docstring attribution, and all five wiring points plus the four doc/count files check out and are mutually consistent; the session touched nothing outside its assigned scope. The one finding was a documentation-precision slip, not a correctness bug.

## Fix applied

Both test loops bumped to the cited sample sizes (`tests/test_c22_high_fluctuation.py`); targeted suite re-run after the fix: 1,481 passed, 7 skipped, 1 failed (same expected Gate-E-owed failure, unchanged).

No round 2 needed — round 1 already PASSed; the fix was applied because it was cheap and the finding named a real inconsistency, not because the gate required it.
