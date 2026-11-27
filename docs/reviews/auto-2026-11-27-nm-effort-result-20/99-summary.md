# Summary — NM-EFFORT-RESULT-20 (issue #185)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| NM-EFFORT-RESULT-20 | PASS | 1 | `pandas_ta/volume/nm_effort_result_20.py`, `tests/test_nm_effort_result_20.py`, `docs/NmEffortResult20Measured.md`, `docs/measure_nm_effort_result_20.py`, `docs/measure_nm_effort_result_20_cpu.py`, `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E owed (launcher runs it); ledger row and `docs/NmEffortResult20Measured.md`'s Gate E section await a later receipt session |

Ported `nm_effort_result_20` (Wyckoff's effort-vs-result, relative volume over relative range,
20-bar window) directly from the issue's own stated formula — disclosed plainly as identical to
the screen prototype's formalisation, since no independently published formula exists — through
Gates A-D, the five wiring touch points, and the test/doc bookkeeping this fork requires. One
Fletcher review round, PASS with zero findings: no REVISE rounds needed.

Gate F target suite (`python -m pytest -q tests/test_nm_effort_result_20.py
tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`): **1,775 passed, 7 skipped, 1 failed** — the one
failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected until
the launcher's Gate E run and a later receipt session record the ledger row.
`tests/test_nm_effort_result_20.py` alone: 37 passed. CPU-feature variant
(`python docs/measure_nm_effort_result_20_cpu.py`, `AVX512F AVX512_SKX AVX2 FMA3` disabled):
37 passed.
