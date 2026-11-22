# Run summary — auto-2026-11-22-b3-qtd-ret-prepush-r1

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| PREPUSH-R1 | PASS | 2 | `docs/QtdRetMeasured.md`, `docs/MLCompanionContract.md`, `tests/test_qtd_ret.py`, `tests/test_altport2_ports.py` | none |

Task-file write-back: skipped (no task-file convention for an ad-hoc review-gate fix — the
source is the pre-push review's own contract, not `docs/issues/` or `TODO.md`).

Test evidence (final state): `python -m pytest -q tests/test_qtd_ret.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py` → **1363 passed, 7 skipped**.
