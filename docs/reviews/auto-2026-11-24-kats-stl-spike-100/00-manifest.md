# Manifest — KATS-STL-SPIKE-100 (issue #162)

## Task

Port Kats tsfeatures' `get_stl_features` spikiness metric — `var(nanvar of leave-one-out
resid)` — as a new PandasTa indicator `stl_spikiness` (column `STLSPIKE_100`), through
Gates A-D, the five wiring touch points, the test suite, and `docs/StlSpikinessMeasured.md`,
per issue #162 and `CLAUDE.md`'s porting protocol. Gate E and the whole-repo test suites
are explicitly out of scope for this session (run later by the launcher/receipt session).

## Clarifications

None needed. The issue text, the sibling ports (`stl_seasonal_strength`,
`stl_trend_strength`, both reusing the same shared STL operators), and the fixed rules in
the system prompt (Gate E deferred, no whole-suite run, files-may-change list) fully
specified the task.

## Execution map

Single task, no parallel lanes: main thread implemented the module, tests, wiring and
measured doc directly (no sub-scopes with independent file ownership to split across
subagents).

| task | lane | why |
|---|---|---|
| port `stl_spikiness` | main thread | one coherent unit: module + tests + 5 wiring points + doc, all touching overlapping/adjacent files (`pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`) with ordering dependencies (wiring must follow the module; docs must follow measurement) |
