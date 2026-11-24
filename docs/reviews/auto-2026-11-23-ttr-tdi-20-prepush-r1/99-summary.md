# Run summary — pre-push gate round 1, TTR-TDI-20 (issue #148)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| Fix pre-push gate findings (HEAD a2989a7) | PASS | 1 | see below | none |

## Files touched

Modified: `tests/test_tdi.py`, `docs/MLCompanionContract.md`,
`tests/test_altport2_ports.py`, `docs/TdiMeasured.md`,
`docs/reviews/auto-2026-11-23-ttr-tdi-20/01-TTR-TDI-20.md`,
`docs/reviews/auto-2026-11-23-ttr-tdi-20/99-summary.md`.

## Review rounds

1. PASS — all 3 MAJOR, both MINOR, and the NIT fixed; verified against
   `docs/gate_e_ledger.csv` digit-for-digit.

## Verification

```
python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py tests/test_altport2_ports.py \
  tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py \
  tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```
1542 passed, 7 skipped.
