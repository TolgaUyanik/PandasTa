# Auto run rd-knot-pos-40 — 2026-11-25

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | RD-KNOT-POS-40 | issue #166 | Port `rd_knot_pos_40` through Gates A-D, wiring, tests, docs/RdKnotPos40Measured.md (Gate E/F deferred to launcher per the session's system-prompt override) |

## Clarifications (asked ONCE, before execution)
- none needed — the issue states the poster's words, the prototype path
  (`docs/issues/screen/ind_screen_r6.py`'s `rd_knot_pos_40` and its
  `_knot_scan`/`_knots` helpers), and the window/knot-range choice (40 bars,
  knots 5..34). The genuinely open calls were: which category to file it
  under, whether `length`/`knot_margin` should be parameters or hard-coded,
  and the exact column name. Resolved conservatively (most consistent with
  repo convention, smallest surprise): category `statistics` (matches
  `trend_scan`'s regression-over-a-window shape, not `trend`, which holds
  only price-action/structural ports); both parameterized with defaults
  matching the issue's own numbers; column name carries both parameters
  (`RD_KNOT_POS_{length}_{knot_margin}`) — logged as an ASSUMPTION in
  `01-rd-knot-pos-40.md`.
- `rd_knot_dslope_40` (the sibling candidate in the same prototype function
  family, "slope change at the best one-knot spline break") is a SEPARATE
  candidate id in the same screen file, not named by issue #166's text at
  all — out of scope for this session, not ported.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| RD-KNOT-POS-40 | main thread | single task, file scope (statistics module + wiring + tests + docs) needs judgment calls on naming/parameterization that benefit from main-context continuity; no parallel decomposition opportunity |
