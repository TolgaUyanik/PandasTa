# Auto run a101-026 — 2026-11-08

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | A101-026 | issue #44 / command arguments | Port Alpha101 #26 (volume-high rank correlation peak) through Gates A-D, wiring, tests, docs/A101026Measured.md |

## Clarifications (asked ONCE, before execution)
- (none needed — scope, formula, and "done" criterion are fully specified by the issue
  text and by this worktree's system-prompt rules: Gate E and Gate F suites are run by
  the launcher, not this session)

## Execution map
| Task | Lane | Why |
|------|------|-----|
| A101-026 | main thread | single task, no parallelism to exploit; needs judgment calls (parameter naming, mutant design, NaN-propagation investigation) better made in-context |
