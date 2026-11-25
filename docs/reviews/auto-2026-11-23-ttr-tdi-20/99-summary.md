# Run summary — TTR-TDI-20 (issue #148)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| TTR-TDI-20 (port `tdi`) | PASS | 2 | see below | Gate E + ledger row (launcher/receipt session); both repos' whole suites (launcher) |

## Files touched

Added: `pandas_ta/trend/tdi.py`, `tests/test_tdi.py`, `docs/TdiMeasured.md`,
`docs/measure_tdi.py`, `docs/measure_tdi_cpu.py`.

Modified: `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/trend/__init__.py`,
`tests/test_altport2_ports.py`.

## Review rounds

1. REVISE -- 1 CRITICAL (a "measured" figure cited for a claim it was never actually
   measured against, and a copy of the wrong number into `docs/MLCompanionContract.md`),
   1 MAJOR (prototype-divergence rationale missing from the module docstring).
2. PASS -- both fixes verified genuine; 2 NIT (a numeric coincidence worth a footnote,
   a missing summary line in the measure script); both applied.

## Verification (targeted; whole suites run by the launcher)

```
python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py tests/test_altport2_ports.py \
  tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py \
  tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```
1 failed (expected at the time: no Gate E ledger row for `tdi`), 1534 passed, 7 skipped.

`python docs/measure_tdi_cpu.py disable pytest` (NPY_DISABLE_CPU_FEATURES="AVX512F
AVX512_SKX AVX2 FMA3"): 116/116 `test_tdi.py` tests pass.

## Closing note

Commit a2989a7 (after this run) recorded the launcher's Gate E row: `is148-tdi-c25dda7f`,
SHIP, max |rho| 0.4924 vs `mad_pct_Pctl`, in `docs/gate_e_ledger.csv`. The ledger failure
above is resolved.
