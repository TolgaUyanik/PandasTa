# Run summary — g191-190 (2026-11-09)

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|---------------|------------|
| G191-190 | PASS | 1 | pandas_ta/statistics/g191_190.py, pandas_ta/statistics/__init__.py, pandas_ta/__init__.py, pandas_ta/core.py, tests/test_g191_190.py, docs/G191190Measured.md, docs/measure_g191_190.py, README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, tests/test_altport2_ports.py | Gate E (real-data correlation) and both repos' full suites: run by the launcher after this session, per repo rules. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` is expected to fail/skip locally until the launcher's Gate E run is recorded. |

Task-file write-back: skipped — no local task file for this issue in this
worktree (`docs/issues/` is gitignored and read-only; the issue was passed
verbatim as the --auto argument, not read from a tracked TODO.md).

## Round 1 (PASS)
- One MINOR: an unmeasured "never hits this edge" claim about the
  warm-up masking's naive-vs-masked discrepancy. Fixed voluntarily (not
  required by the gate rule) by measuring the actual discrepancy (16 of 19
  bars differ) and quoting that instead, in both the module docstring and
  `docs/G191190Measured.md`.

Commits: `28f633e` (port), `e5df9fc` (round-1 voluntary fix).
