# Run manifest — RD-CORR-C-OBV-20 (issue #168)

## Task

Port `rd_corr_c_obv_20` (issue #168) through Gates A-D, wiring, tests,
`docs/RdCorrCObv20Measured.md`, per the issue-solver system prompt and the
issue text. Single free-form task, taken as given.

## Clarifications

None needed. Issue text (rolling correlation of price and OBV, window 20,
Reddit rd:algotrading:chnbr1), the Gate E/F overrides in the system prompt,
and `CLAUDE.md`'s porting protocol fully specify scope, formula, and done
criterion. Precedent (`pvcorr`, issue #18 — another price/volume correlation
port) resolved the open style questions (signature shape, correlation
helper reuse, mutant-test technique, non-redundancy argument structure) by
example.

## Execution map

One task, main thread (file scope overlaps the shared wiring files
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/volume/__init__.py`,
`README.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` —
no parallel lane possible or needed for a single task).

## Files touched

New:
- `pandas_ta/volume/rd_corr_c_obv_20.py`
- `tests/test_rd_corr_c_obv_20.py`
- `docs/measure_rd_corr_c_obv_20.py`
- `docs/measure_rd_corr_c_obv_20_cpu.py`
- `docs/RdCorrCObv20Measured.md`

Modified:
- `pandas_ta/volume/__init__.py` (export)
- `pandas_ta/__init__.py` (`Category`)
- `pandas_ta/core.py` (accessor)
- `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 396 -> 397,
  `CATEGORY_BUCKETS["volume"]` 44 -> 45)
- `README.md` (three counts, volume section)
- `docs/MLCompanionContract.md` (tagged/SF counts, chain entry)
- `docs/IndicatorDictionary.md` (regenerated)

## Known, expected test state

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails — no ledger row until the launcher's Gate E run and the receipt
session record it. Per the issue-solver system prompt, this is expected, not
a finding.
