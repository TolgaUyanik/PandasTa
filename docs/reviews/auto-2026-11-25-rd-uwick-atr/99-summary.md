# RD-UWICK-ATR auto run — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| rd-uwick-atr | PASS | 1 | `pandas_ta/candles/rd_uwick_atr.py` (new), `tests/test_rd_uwick_atr.py` (new), `docs/RdUwickAtrMeasured.md` (new), `docs/measure_rd_uwick_atr.py` (new), `docs/measure_rd_uwick_atr_cpu.py` (new), `pandas_ta/candles/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E owed — run by issue-solver after this session, recorded in `docs/gate_e_ledger.csv` by the receipt session; if STRUCK, revert per the issue's own "measured revert" rule |

Reviewer verdict: **PASS** on round 1 (2 NITs, both addressed post-PASS). No escalation.

Gate F subset (`tests/test_rd_uwick_atr.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`): 1,589 passed, 7 skipped, 1 failed (expected
`test_gate_e_ledger` row, owed until the launcher's Gate E run). CPU-feature variant
(`python docs/measure_rd_uwick_atr_cpu.py`, `AVX512F AVX512_SKX AVX2 FMA3` disabled):
19 passed.
