# Run summary — auto-2026-11-26-rd-knot-dslope-40-prepush-r1

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| PREPUSH-R1 | PASS | 1 | `pandas_ta/statistics/rd_knot_dslope_40.py`, `tests/test_rd_knot_dslope_40.py`, `docs/measure_rd_knot_dslope_40.py`, `docs/RdKnotDslope40Measured.md`, `docs/MLCompanionContract.md`, `docs/gate_e_ledger.csv` | Gate E owed again (see 01-PREPUSH-R1.md) -- issue-solver must re-run Gate E and a later receipt session re-records the ledger row for the new module sha1 `f48afaf88e993671fa92390428b7bee35b8b6406` |

Task-file write-back: skipped (no task-file convention for an ad-hoc review-gate fix -- the
source is the pre-push review's own contract, not `docs/issues/` or `TODO.md`).

Test evidence (final state): `python -m pytest -q tests/test_rd_knot_dslope_40.py
tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py` -> **1,614 passed, 7 skipped, 1 failed**
(`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected per
CLAUDE.md's "Gate E owed, not failed" rule). CPU-feature variant
(`python docs/measure_rd_knot_dslope_40_cpu.py`, AVX512F/AVX512_SKX/AVX2/FMA3 disabled):
20 passed.
