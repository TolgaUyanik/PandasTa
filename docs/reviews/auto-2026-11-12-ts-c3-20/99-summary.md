# Auto run summary — TS-C3-20, 2026-11-12

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-c3-20` (issue #88) | **ESCALATED at the round cap** — all findings applied, the last fix set unreviewed | 4 (REVISE, REVISE, REVISE, REVISE) | `pandas_ta/statistics/ts_c3_20.py` (new), `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_ts_c3_20.py` (new), `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/TsC320Measured.md` (new), `docs/measure_ts_c3_20.py` (new), this run folder | Gate E (launcher), then the ledger row and Gate C's real-data counts (receipt session); the round-4 fix set has not been through a reviewer |

## What shipped

`TS_C3_20_1` in `Category["statistics"]`:
`mean(r[t]·r[t-1]·r[t-2])` over the 18 triples inside a window of 20 simple
returns, divided by the cube of those returns' sample standard deviation
(`ddof=1`). `lag` is a parameter (tsfresh's own), clamped to
`(length - 2) // 2`; the column name carries both parameters.

Gates A, B and D are through on synthetic frames; Gate C is synthetic only,
its real-data counts owed with Gate E; Gate E was not run here by session
rule and no `docs/gate_e_ledger.csv` row was added, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails with `['mtd_ret', 'ts_c3_20']` as expected. Every number quoted in the
module docstring, the test module and `docs/TsC320Measured.md` is printed by
`python docs/measure_ts_c3_20.py` or by the test run.

Final runs: `python -m pytest tests/test_ts_c3_20.py -q` → **98 passed**;
`python -m pytest -q` → **3 failed, 5668 passed, 83 skipped** (the two
`CLAUDE.md` Known breaks plus the owed ledger row).

## Why ESCALATED rather than PASS

The loop hit its cap at four rounds without a PASS. No round found a defect
in the mathematics, the gates, the wiring or a measured number; all four
CRITICALs were sentences that over-claimed against their own run — a count
of neighbouring ports, a Gate D fire count at `length=60`, a suite triple
that went stale because this very log tripped
`test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`, and a
sufficient condition written as a necessary one. Each was rewritten to what
the run says and re-measured. The honest residual risk is the same class
again, in the round-4 fix set, which no reviewer has seen:
`docs/reviews/auto-2026-11-12-ts-c3-20/01-ts-c3-20.md` records exactly what
changed so the next reviewer can start there.

## Assumptions logged (see `00-manifest.md`)

Seven, none of them asked of the user (`AskUserQuestion` is unavailable in
this headless session): the statistics category, `lag` as a parameter,
`ddof=1`, the in-window triple count, the rounding-noise floor, Gate E not
run, and Gate C's real-data counts left owed. Each is priced against its
alternative in `docs/TsC320Measured.md` §Gate A rather than asserted.
