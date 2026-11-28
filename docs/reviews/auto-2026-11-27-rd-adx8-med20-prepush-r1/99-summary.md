# Run summary — auto-2026-11-27-rd-adx8-med20-prepush-r1

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| PREPUSH-R1 | PASS | 1 | `docs/RdAdx8Med20Measured.md`, `tests/test_altport2_ports.py` | none -- `pandas_ta/trend/rd_adx8_med20.py`'s NIT was deliberately left unapplied (see 01-PREPUSH-R1.md) |

Task-file write-back: skipped (no task-file convention for an ad-hoc review-gate fix -- the
source is the pre-push review's own contract, not `docs/issues/` or `TODO.md`).

Test evidence (final state): `python -m pytest -q tests/test_rd_adx8_med20.py
tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py` -> **1,720 passed, 7 skipped, 0 failed** (unchanged
from the receipt's own prior count -- the Gate E ledger row already existed before this round).
