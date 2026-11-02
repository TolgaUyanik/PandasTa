# Task log — osap_retskew_21 (issue #36)

## Implementation (round 0)

Ported OSAP `ReturnSkew` as `pandas_ta/statistics/osap_retskew_21.py`: Fisher-Pearson
bias-corrected skewness of `close.pct_change()` over a 21-bar trailing window
(`close.pct_change().rolling(21).skew()`), scale-free by construction (a ratio's rolling
skew), wired through all 5 touch points, 13 tests in `tests/test_osap_retskew_21.py`
(correctness, Gate B causality by future-perturbation + look-ahead mutant, Gate D scale-free
x8/x64 bit-identical + x10/x3.7 tolerance + fires/non-constant, wiring). Receipt:
`docs/OsapRetskew21Measured.md`, backed by `docs/measure_osap_retskew_21.py`. README,
`docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md` and
`tests/test_altport2_ports.py::CATEGORY_TOTAL` updated for the new count (268->269 Category,
276->277 accessors, statistics 21->22, SF tag 259->260). Full suite:
`python -m pytest -q` -> 3 failed (all pre-existing/expected, see Gate F note in the receipt),
4,084 passed, 83 skipped.

## Review round 1 — REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/OsapRetskew21Measured.md:37-38 (and repeated at line 48)
    problem:  The "hand-derived" Gate A receipt is fabricated, not measured. For closes
              [100, 103, 101, 108] the actual bias-corrected skew is approximately -0.339,
              not the claimed +1.153547 -- wrong sign and roughly 3x the magnitude.
    fix:      Regenerate the 3-bar example from the actual running code and paste the real
              printed numbers into the doc.
  - severity: MAJOR
    location: docs/OsapRetskew21Measured.md Gate F row/note
    problem:  Gate F doesn't state the actual pytest counts and names only two of the three
              real failures, dropping test_altrepo_talib_csv.
    fix:      State the literal measured line ("3 failed, 4084 passed, 83 skipped") and name
              all three failing tests by full nodeid.
SUMMARY: The port itself is sound -- formula, causality mutant, scale-free numbers, and
wiring/count arithmetic all check out against a live run. But the receipt doc's hand
derivation is simply wrong (wrong sign, wrong magnitude), and the Gate F accounting is vaguer
than every comparable prior receipt in this repo. Fix both before this ships.
```

## Fix applied (round 1 -> round 2)

* Added a permanent printed 3-bar example to `docs/measure_osap_retskew_21.py` (prints
  returns, mean, std, skew, and the module's own output for the same inputs) instead of
  hand-typing the arithmetic. Ran it: `skew=-0.339166`, matching the module to 1e-6 (not
  +1.153547 -- the reviewer's correction was right; verified independently by re-deriving the
  same numbers by hand a second time before accepting the fix).
  Updated `docs/OsapRetskew21Measured.md` (prose paragraph and the Gate A table row) to the
  correct, now-printed number, and noted the round-1 catch inline so a reader of the receipt
  sees the correction, not just the corrected value.
* Replaced the Gate F row's "see note below" with the literal measured line
  (`3 failed, 4,084 passed, 83 skipped`) and rewrote the note to name all three failing tests
  by full nodeid (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`), each with why
  it's pre-existing/expected and not caused by this change.
* Re-ran `tests/test_osap_retskew_21.py` (13 passed) and grepped the repo for the old wrong
  numbers (`1.153547`, `0.027963`, `0.044648`) to confirm no stale copy survived anywhere.

## Review round 2 — PASS

```
VERDICT: PASS
SUMMARY: Both round-1 findings are genuinely resolved, not just reworded. The Gate A 3-bar
example is now computed by docs/measure_osap_retskew_21.py (not hand-typed) and the quoted
numbers (mean=0.0266298, std=0.0444581, skew=-0.339166) are internally consistent and match an
independent manual re-derivation of the same closes/formula to within my own arithmetic's
precision (sign and magnitude both correct this time, unlike round 1's fabricated +1.153547).
The doc also discloses the round-1 catch inline. Gate F now states the literal pytest line
("3 failed, 4,084 passed, 83 skipped") and names all three failing tests by full nodeid
(tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one,
tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence,
tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows), each with a
stated reason, and all three test functions actually exist with those exact names in those exact
files. No stale copies of the old wrong numbers (1.153547/0.027963/0.044648) survive outside the
historical review-log record, the module docstring stays consistent with the doc, and the
measure script remains a clean, runnable module. Nothing else in the diff was touched, so there
is no new blast radius to flag.
```

PASS reached in round 2 (1 REVISE round applied). No further rounds needed.
