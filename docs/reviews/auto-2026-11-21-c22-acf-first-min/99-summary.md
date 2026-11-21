# C22-ACF-FIRST-MIN — run summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| Port issue #131 (`c22_acf_first_min`, catch22 `CO_FirstMin_ac`) through Gates A-D, wiring, tests, receipt | **PASS** | 2 | see below | Gate E (launcher), whole-suite runs (launcher), ledger row (next receipt session) -- superseded, see note below |

## Files touched

New: `pandas_ta/statistics/c22_acf_first_min.py`,
`tests/test_c22_acf_first_min.py`, `docs/measure_c22_acf_first_min.py`,
`docs/measure_c22_acf_first_min_cpu.py`, `docs/C22AcfFirstMinMeasured.md`,
this run folder.

Modified: `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`,
`pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`.

## Headline result

Bit-equal to the actual GPL-3.0 reference (`pycatch22.CO_FirstMin_ac`) on
every one of 8,400 sampled windows across six synthetic frames
(`docs/C22AcfFirstMinMeasured.md` §P) — the cleanest Gate A result of any
catch22 port in this fork so far (`c22_periodicity` matched 8,387/8,400;
`c22_ami2` matched to 1e-12 but not bit-equal).

## Review rounds

1. REVISE — one MAJOR: an unmeasured "467" copy-pasted from a sibling
   indicator's receipt into the Gate D summary row. Fixed (one-line edit).
2. PASS — fix confirmed, independent re-measurement of every section
   reproduces the receipt digit for digit, required test subset green.

## What is NOT done here (by design, per the system prompt's overrides)

⚠ **Stale at HEAD, superseded by commit `1c71b0b`:** this section
describes the porting session's end state, before the launcher's Gate E
run. Commit `1c71b0b` filled the receipt's §E and recorded the
`docs/gate_e_ledger.csv` row, so `test_every_indicator_that_needs_a_row_has_one`
now passes. See the receipt's §E for the current state, including the
open sibling comparison it still owes.

* Gate E (BIST, the launcher's `gate_e_overlap.py` run) — the receipt's
  §E states "pending, run by issue-solver after this session," and names
  the OWED comparison against `C22PERIODICITY_100` that
  `docs/C22PeriodicityMeasured.md` §E4 flagged in advance.
* `docs/gate_e_ledger.csv` row — written by the receipt session after
  Gate E runs; until then `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails naming exactly `['c22_acf_first_min']`, confirmed expected.
* Whole-suite runs of both repos — the launcher's job per the system
  prompt; only the named subset plus the module's own 31 tests were run
  here (175 passed, 7 skipped).
