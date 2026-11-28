# Summary — NM-MMI-250 (issue #184)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| NM-MMI-250 | PASS | 3 | `pandas_ta/statistics/nm_mmi_250.py`, `tests/test_nm_mmi_250.py`, `docs/NmMmi250Measured.md`, `docs/measure_nm_mmi_250.py`, `docs/measure_nm_mmi_250_cpu.py`, `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E owed (launcher runs it); ledger row and `docs/NmMmi250Measured.md`'s Gate E section await a later receipt session |

Ported `nm_mmi_250` (Market Meanness Index of daily returns, 250-bar window) from the issue's own
restated source formula, through Gates A-D, the five wiring touch points, and the test/doc
bookkeeping this fork requires. Two genuine REVISE rounds, both about prose overclaiming "every"
on measured counts that were actually frame-specific and non-uniform (round 1), and a stale module
sha1 left behind by the round-1 docstring edit (round 2) — both fixed and independently
re-verified in round 3. No destructive or irreversible steps were needed or attempted.

Gate F target suite (`python -m pytest -q tests/test_nm_mmi_250.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`): **1,783 passed, 7 skipped, 1 failed** — the one
failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected until
the launcher's Gate E run and a later receipt session record the ledger row. CPU-feature variant
(`python docs/measure_nm_mmi_250_cpu.py`, `AVX512F AVX512_SKX AVX2 FMA3` disabled): 53 passed.
