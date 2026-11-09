# Run summary — g191-165 (2026-11-09)

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|---------------|------------|
| G191-165 | PASS | 2 | pandas_ta/statistics/g191_165.py, pandas_ta/statistics/__init__.py, pandas_ta/__init__.py, pandas_ta/core.py, tests/test_g191_165.py, docs/G191165Measured.md, docs/measure_g191_165.py, README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, tests/test_altport2_ports.py | Gate E (real-data correlation) and both repos' full suites: run by the launcher after this session, per repo rules. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` is expected to fail/skip locally until the launcher's Gate E run is recorded. |

Task-file write-back: skipped — no local task file for this issue in this
worktree (`docs/issues/` is gitignored and read-only; the issue was passed
verbatim as the --auto argument, not read from a tracked TODO.md).

## Round 1 (REVISE)
- MAJOR: false citation claiming `g191_146` corroborates the `STD` ddof=1
  interpretation choice, when `g191_146`'s formula never invokes `STD`.
- MINOR: `sqrt(47/48)` stated as `~0.98961`, measured value is `0.989529`.
- MINOR: the `0/0 -> NaN` branch (constant window) was documented but
  untested.
All three fixed, committed as `5d39283`.

## Round 2 (PASS)
- One NIT, accepted as-is (a historical report file correctly retaining its
  own pre-fix numbers as the record of round 1's findings).

Commits: `34ca792` (port), `5d39283` (round-1 fixes).
