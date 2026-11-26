# Auto run rd-gap-fill — 2026-11-26

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|-----------------|
| 1 | RD-GAP-FILL | GitHub issue #174 | Port `rd_gap_fill` (same-day gap fill, signed) through Gates A-D, wiring, tests, docs/RdGapFillMeasured.md; Gate E and whole suites deferred to the launcher per the issue-solver system prompt. |

## Clarifications (asked ONCE, before execution)
- Q: none asked — `AskUserQuestion` is unavailable in this headless issue-solver session
  (per the system prompt). → A: n/a.
- ASSUMPTION (conservative reading, logged per the system prompt's own instruction for
  when AskUserQuestion is unavailable): category home is `candles`, matching the sibling
  signed/binary `rd_*` ports (`rd_horseshoe`, `rd_outside_bar`, `rd_uwick_atr`,
  `rd_wick_pressure_10`) already in that category, not `statistics` where the twin rolling
  share `rd_gap_fill_rate_60` lives — the issue's own candidate is a per-bar signed flag,
  the same shape as `rd_horseshoe`, not a rolling share.
- ASSUMPTION: kept `min_gap` as a parameter (default 0.003, the poster's own 0.3%) rather
  than hard-coding it, matching the twin `rd_gap_fill_rate_60`'s own decision and the
  fork's convention for every other threshold-based indicator.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| RD-GAP-FILL | main thread | single task, needs main-context judgment (category placement, Gate A/B/D derivation, docs); not parallelizable against itself. |
