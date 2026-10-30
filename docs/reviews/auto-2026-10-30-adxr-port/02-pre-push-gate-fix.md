# ADXR port -- pre-push review gate, round 1 finding fixed

Target: HEAD at the time of the gate, `fd6d56fe8a40` (LEAN-ADXR-14: record
Gate E measured numbers, DISCLOSE_GAP 0.8838 vs ADX, shipped not STRUCK.
Refs #110).

## Pre-push gate verdict (external, round 1 of 3)

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/AdxrMeasured.md -- Gate F row (and its "Status" line) +
      docs/reviews/auto-2026-10-30-adxr-port/01-adxr-port.md reviewer's
      quoted figures
    problem: docs/AdxrMeasured.md's Gate F receipt said "3 failed,
      3271 passed, 83 skipped" and named
      tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one
      as a pre-existing failure, but the same diff's docs/gate_e_ledger.csv
      already carries the adxr row that test checks for, so it should pass,
      not fail. The launcher's clean-worktree measurement at this HEAD
      reports 2 failed, 3279 passed.
    fix: re-run python -m pytest -q on HEAD and update the Gate F row/Status
      line to the actual count, dropping the ledger test from the named
      pre-existing failures.
SUMMARY: The math (Gates A/B/D/E) is right; the one defect is Gate F's own
  receipt quoting a stale, pre-ledger-row suite run.
```

## Fix applied

Re-ran `python -m pytest -q` in this worktree (after the `adxr` row was
already in `docs/gate_e_ledger.csv`): **2 failed, 3279 passed, 83 skipped,
96714 warnings in 74.36s**. Failures: `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
-- both pre-existing, neither naming `adxr`.
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is not in the failure list (it now passes, since the `adxr` ledger row is
present).

Updated `docs/AdxrMeasured.md`: Status line "3 pre-existing failures" ->
"2 pre-existing failures"; Gate F table row's pytest numbers and failure
list corrected to match the re-run, with a note that the ledger test now
passes because the row landed. `docs/reviews/auto-2026-10-30-adxr-port/01-adxr-port.md`
is left as-is: it is a frozen record of round 1's review against commit
`a8ed3c0`, truthfully dated before the ledger row existed, not a live claim.

## Re-review (round 2)

```
VERDICT: PASS
FINDINGS: none
SUMMARY: The round-1 fix is real and complete -- both the Status line and
  the Gate F table row now say "2 pre-existing failures" / "2 failed,
  3279 passed, 83 skipped," correctly drop test_gate_e_ledger.py's
  row-check from the failure list, and name the two actual unrelated
  failures; no stale "3271"/"3 failed" text survives anywhere else in the
  file. Spot-checks of the other quantitative claims hold up against the
  actual worktree: docs/gate_e_ledger.csv carries the exact
  adxr:ADXR_14 DISCLOSE_GAP 0.8838 row cited, tests/test_altport2_ports.py
  pins CATEGORY_TOTAL = 238 and trend: 59 matching the doc's 237->238/58->59
  claim, docs/MLCompanionContract.md and README.md already show the
  571/217 and 246 figures the doc claims, and tests/test_adxr.py expands
  via its three @pytest.mark.parametrize functions to exactly 13 collected
  tests as stated. Ship it.
```

Outcome: PASS on round 2. One round of fixes applied, no further
re-dispatch needed.
