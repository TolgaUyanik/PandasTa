# Auto run g191-002 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | G191-002 | issue-solver invocation (`/brutally-honest-review --auto`) | Port GTJA191 alpha `#2` (one-day change of close location) as `g191_002`, Gates A-D, wiring, tests, `docs/G191002Measured.md`. Gate E and the suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text (#63), `CLAUDE.md`'s porting protocol, and the
  issue-solver system prompt's own overrides (Gate E/F deferred to the
  launcher, file-scope allowlist, no push) fully specify goal, scope and
  "done". Two interpretation choices were resolved by precedent, not asked,
  and logged as ASSUMPTIONs in `01-g191-002.md`:
  - category: `a101_053` (Alpha101's own close-location-ratio port, same
    algebraic shape, different denominator) lives in `momentum`, so
    `g191_002` followed it there.
  - exposing the formula's fixed `DELTA(...,1)` window as a tunable
    `length` parameter (default `1`): every sibling `g191_*`/`a101_*` port
    in this fork exposes its DELTA/SUM window as a tunable even when the
    issue states one fixed number (`a101_053`'s own `length=9` default),
    so `g191_002` followed that convention instead of hard-coding `1`.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| G191-002 | main thread | single task, sequential (module -> wiring -> tests -> docs), needs main-context judgment (Gate A derivation, mutant design); no parallelism opportunity |
