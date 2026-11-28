# Summary — NM-PRICE-DENSITY-10 (issue #186)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| NM-PRICE-DENSITY-10 | PASS | 2 | `pandas_ta/volatility/nm_price_density_10.py`, `tests/test_nm_price_density_10.py`, `docs/NmPriceDensity10Measured.md`, `docs/measure_nm_price_density_10.py`, `docs/measure_nm_price_density_10_cpu.py`, `pandas_ta/volatility/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E owed (launcher runs it); ledger row and `docs/NmPriceDensity10Measured.md`'s Gate E section await a later receipt session |

Ported `nm_price_density_10` (Kaufman's price density, 10-bar window) directly from Kaufman 2013's
own chapter formula through Gates A-D, the five wiring touch points, and the test/doc bookkeeping
this fork requires. One Fletcher review round found a MAJOR documentation-correctness defect (an
unqualified "denominator==0 implies numerator==0" claim that silently assumed High >= Low); fixed by
disclosing the precondition and adding a regression test for the malformed-input case. Round 2:
PASS, zero findings.

Gate F target suite (`python -m pytest -q tests/test_nm_price_density_10.py
tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`): **1,777 passed, 7 skipped, 1 failed** — the one failure
is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected until the
launcher's Gate E run and a later receipt session record the ledger row.
`tests/test_nm_price_density_10.py` alone: 31 passed. CPU-feature variant
(`python docs/measure_nm_price_density_10_cpu.py`, `AVX512F AVX512_SKX AVX2 FMA3` disabled):
31 passed.

Superseded at commit 79b4698 — Gate E ran SHIP, ledger row recorded, target suite re-ran
1,785 passed, 7 skipped, 0 failed; see docs/NmPriceDensity10Measured.md.
