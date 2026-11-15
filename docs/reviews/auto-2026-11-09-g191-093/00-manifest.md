# Auto run g191-093 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | G191-093 | issue-solver invocation (`/brutally-honest-review --auto`) | Port GTJA191 alpha `#93` (20-day sum of open-down moves, DBM) as `g191_093`, Gates A-D, wiring, tests, `docs/G191093Measured.md`. Gate E and the suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text (#62), `CLAUDE.md`'s porting protocol, and the
  issue-solver system prompt's own overrides (Gate E/F deferred to the
  launcher, file-scope allowlist, no push) fully specify goal, scope and
  "done". The only interpretation choice (which `pandas_ta` category to file
  the module under) was resolved by precedent: `dm` (directional movement,
  open/high/low/close) and `g191_146` (another GTJA191 alpha) both live in
  `momentum`, so `g191_093` (open/low/close, a directional down-move measure)
  followed them there — logged as an ASSUMPTION in `01-g191-093.md`, not asked.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| G191-093 | main thread | single task, sequential (module -> wiring -> tests -> docs), needs main-context judgment (Gate A derivation, mutant design); no parallelism opportunity |
