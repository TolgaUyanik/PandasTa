# Run summary — rd-quadfit-resid-20 (2026-11-27)

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| RD-QUADFIT-RESID-20 | PASS | 1 | pandas_ta/statistics/rd_quadfit_resid_20.py, pandas_ta/statistics/__init__.py, pandas_ta/__init__.py, pandas_ta/core.py, tests/test_rd_quadfit_resid_20.py, tests/test_altport2_ports.py, README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, docs/RdQuadfitResid20Measured.md, docs/measure_rd_quadfit_resid_20.py, docs/measure_rd_quadfit_resid_20_cpu.py | Gate E owed — the launcher runs it after this session; a later receipt session records the `docs/gate_e_ledger.csv` row and fills in the measured Gate E number in `docs/RdQuadfitResid20Measured.md` |

Task-file write-back: skipped — no detectable task-file convention in this
worktree for a single issue-solver session (the task originates from the
GitHub issue itself, not a local TODO.md/board entry).

Gate E and the whole-suite runs are explicitly out of scope for this session
per the issue-solver system prompt; this run only verifies the required test
subset (`python -m pytest -q tests/test_rd_quadfit_resid_20.py
tests/test_readme_counts.py tests/test_altport2_ports.py
tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`): 1,718 passed, 7 skipped, 1
expected failure (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
owed until the launcher's Gate E run).

Noteworthy finding this run (not assumed going in, discovered mid-session):
SUPERSEDED by gate round 1 — the ratio-to-first-bar fix makes x8/x64
bit-identical; see docs/RdQuadfitResid20Measured.md Decision 3. (Historical
text below, true at the time it was written.)
the port's scale-free (Gate D) output is NOT bit-identical under a
power-of-two price rescale (x8/x64), unlike its two nearest structural
siblings (`rd_knot_pos_40`, `rd_std_ratio_20_60`) — `np.log` of a rescaled
price is not itself bit-preserving. The module docstring, tests, and receipt
were all written to state this honestly (measured ~5e-9 relative tolerance,
same order of magnitude as the non-power-of-two case) rather than copy the
precedent's bit-identical claim unverified.
