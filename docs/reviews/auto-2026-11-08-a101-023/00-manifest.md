# Auto run a101-023 — 2026-11-08

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | A101-023 | issue-solver invocation (issue #47) | Port Alpha101 #23 (two-day high change above the 20-day mean high) through Gates A-D, wiring, tests, docs/A101023Measured.md |

## Clarifications (asked ONCE, before execution)
- Q: none asked -- the issue's formula (`mean(high,20) < high ? -delta(high,2) : 0`,
  scale-free via `/close`) has no ambiguous operator (no `adv(d)` or `ts_rank` term,
  unlike `a101_021`/`a101_043`), so no ASSUMPTION needed beyond the warm-up re-mask
  choice, which is resolved by matching the issue's own prototype
  (`docs/issues/screen/ind_screen.py`'s `.where(mean(h,20) < h, 0.0).where(mean(h,20).notna())`)
  and disclosed in the module docstring and `docs/A101023Measured.md`.
- ASSUMPTION: Gate E and both repos' test suites (Gate F) are run by the launcher per
  the issue-solver system prompt override, not in this session. `docs/A101023Measured.md`
  states Gate E as pending.
→ none needed from the user.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| A101-023 | main thread | single port touching the fixed five wiring points plus README/dictionary/contract docs; no parallelizable sub-scope, and file-scope is restricted by the issue-solver system prompt to specific paths |
