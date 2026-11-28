# Auto run manifest — rd-lh-run-182

**Date:** 2026-11-27
**Mode:** C (batch task execution), single task, invoked via issue-solver's `--auto` call.

## Task

> RD-LH-RUN: port the indicator of issue #182 through Gates A-D, the wiring, the tests and
> docs/\<Name\>Measured.md, per the issue and the rules in the session's system prompt (run
> length of consecutive lower highs, Reddit tier 4 sources). Gate E and the whole suites are
> run by the launcher afterwards. Verify with the issue-solver's fixed pytest subset, never the
> whole suite. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> failing is expected, not a finding, until the launcher's Gate E run and the receipt land.

## Clarifications

None needed — the issue (#182) and the session's system prompt (CLAUDE.md porting protocol,
the file-scope allowlist, the Gate E/F deferral rules) fully specify scope, formula, and done
criteria. No AskUserQuestion round was run.

## Execution map

One task, main thread (no parallel lanes — a single indicator port with a fixed file scope,
no independent sub-work to fan out).

## Files touched

- `pandas_ta/trend/rd_lh_run.py` (new)
- `pandas_ta/trend/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py` (wiring)
- `tests/test_rd_lh_run.py` (new)
- `tests/test_altport2_ports.py` (`CATEGORY_TOTAL`, `CATEGORY_BUCKETS`)
- `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` (counters)
- `docs/RdLhRunMeasured.md`, `docs/measure_rd_lh_run.py`, `docs/measure_rd_lh_run_cpu.py` (new)
