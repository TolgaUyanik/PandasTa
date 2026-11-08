# Auto run a101-046 — 2026-11-08

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | A101-046 | issue #49 (verbatim user ask) | Port Alpha101 #46 (10-day price acceleration) through Gates A-D, wiring, tests, docs/A101046Measured.md |

## Clarifications (asked ONCE, before execution)
- none needed — AskUserQuestion unavailable in this headless session (issue-solver rule); the task was fully actionable from the issue text + CLAUDE.md porting protocol + the three merged sibling ports (`a101_023`, `a101_048`, `a101_053`). Two judgment calls were made conservatively and logged as ASSUMPTIONs in `01-a101-046.md` rather than asked:
  - single `length` parameter (default 10) with the far delay fixed at `2*length`, rather than two independent length params, because the formula's two `/10` divisors share one literal step and the far delay is exactly double it — not an independent degree of freedom.
  - no `.replace([inf,-inf], nan)` on the final `/close` division, matching the sibling port `a101_023`'s identical `-d2/close` pattern (close is a price series, never realistically zero) rather than adding unneeded defensive code.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| A101-046 | main thread | single task, overlapping scope with existing wiring files (`pandas_ta/__init__.py`, `core.py`, `momentum/__init__.py`), no parallelism benefit |
