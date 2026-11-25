# Auto run rd-gap-fill-rate-60 — 2026-11-25

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | RD-GAP-FILL-RATE-60 | issue #165 | Port `rd_gap_fill_rate_60` through Gates A-D, wiring, tests, docs/RdGapFillRate60Measured.md (Gate E/F deferred to launcher per the session's system-prompt override) |

## Clarifications (asked ONCE, before execution)
- none needed — the issue states the formula (poster's words), the prototype
  path, and the default window (60, "this prototype's choice"); the only
  genuinely open call was the exact column name and whether `min_gap` should
  be a parameter or a hard-coded constant. Resolved conservatively (most
  consistent with repo convention, smaller surprise): parameterize both
  `length` and `min_gap` with defaults matching the issue's own numbers, and
  name the column with both — logged as an ASSUMPTION in
  `01-rd-gap-fill-rate-60.md`.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| RD-GAP-FILL-RATE-60 | main thread | single task, file scope (statistics module + wiring + tests + docs) needs judgment calls on naming/parameterization that benefit from main-context continuity; no parallel decomposition opportunity |
