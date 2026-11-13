# Auto run g191-187 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | G191-187 | issue-solver invocation (`/brutally-honest-review --auto`) | Port GTJA191 alpha `#187` (20-day sum of open-up moves, DTM) as `g191_187`, Gates A-D, wiring, tests, `docs/G191187Measured.md`. Gate E and the suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text (#65), `CLAUDE.md`'s porting protocol, and the
  issue-solver system prompt's own overrides (Gate E/F deferred to the
  launcher, file-scope allowlist, no push) fully specify goal, scope and
  "done". The only interpretation choice (which `pandas_ta` category to file
  the module under) was resolved by precedent: the mirror alpha `#93`
  (open-down moves, "DBM") is already shipped as `g191_093` in `momentum`,
  so `#187` (open-up moves, "DTM") followed it there — logged as an
  ASSUMPTION in `01-g191-187.md`, not asked. (The issue's own Gate E
  comparators for the prototype — `natr`, `Stop_2ATR_pct`,
  `Swing_Range_pct` — lean volatility; this is noted as a judgment call,
  not resolved by asking, per the smaller-blast-radius rule: following the
  already-shipped sibling's placement is the more conservative choice than
  inventing a new category assignment.)

## Execution map
| Task | Lane | Why |
|------|------|-----|
| G191-187 | main thread | single task, sequential (module -> wiring -> tests -> docs), needs main-context judgment (Gate A derivation, mutant design); no parallelism opportunity |
