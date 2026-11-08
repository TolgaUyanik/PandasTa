# Auto run a101-007 — 2026-11-08

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | A101-007 | issue #51 (`TolgaUyanik/PandasTa`) | Port Alpha101 `#7` (volume-gated 7-day move rank) through Gates A-D, wiring and tests, write `docs/A101007Measured.md`; Gate E and both repos' suites run by the launcher afterwards |

## Clarifications (asked ONCE, before execution)
- Q: none asked — AskUserQuestion is unavailable in this headless issue-solver
  session (session rules). Ambiguities below were resolved by the most
  conservative reading and logged as ASSUMPTIONs in `01-a101-007.md` instead.
- A: n/a

## Execution map
| Task | Lane | Why |
|------|------|-----|
| A101-007 | main thread | single task, no parallelism to exploit; needs the issue-solver's own Bash/git tool restrictions (no worktree isolation, no push) and the repo's own porting conventions (five wiring touch points, Gate A-D docstring discipline) that only the main thread has full context for |
