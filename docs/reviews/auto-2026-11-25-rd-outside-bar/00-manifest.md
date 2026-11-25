# Run manifest — RD-OUTSIDE-BAR (issue #167)

## Task

Port `rd_outside_bar` (issue #167) through Gates A-D, wiring, tests,
`docs/RdOutsideBarMeasured.md`, per the issue-solver system prompt and the
issue text. Single free-form task, taken as given.

## Clarifications

None needed. Issue text, the Gate E/F overrides in the system prompt, and
`CLAUDE.md`'s porting protocol fully specify scope, formula, and done
criterion. Precedent (`rd_horseshoe`, #164) resolved the one open style
question (signature shape, column naming, test/doc structure) by example.

## Execution map

One task, main thread (file scope overlaps the shared wiring files
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/candles/__init__.py`,
`README.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` —
no parallel lane possible or needed for a single task).

## Files touched

New:
- `pandas_ta/candles/rd_outside_bar.py`
- `tests/test_rd_outside_bar.py`
- `docs/measure_rd_outside_bar.py`
- `docs/measure_rd_outside_bar_cpu.py`
- `docs/RdOutsideBarMeasured.md`

Modified:
- `pandas_ta/candles/__init__.py` (export)
- `pandas_ta/__init__.py` (`Category`)
- `pandas_ta/core.py` (accessor)
- `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 395 -> 396)
- `README.md` (three counts, candles section)
- `docs/MLCompanionContract.md` (tagged/BIN counts, chain entry)
- `docs/IndicatorDictionary.md` (regenerated)

## Known, expected test state

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails — no ledger row until the launcher's Gate E run and the receipt
session record it. Per the issue-solver system prompt, this is expected, not
a finding.
