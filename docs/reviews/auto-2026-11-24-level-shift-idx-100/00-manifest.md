# Auto run level-shift-idx-100 — 2026-11-24

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | KATS-LEVEL-SHIFT-IDX-100 | issue #159 (`/brutally-honest-review --auto` free-form task) | Port Kats tsfeatures' `get_level_shift_features` argmax -- the position of the largest level shift (100) -- as `level_shift_idx` (statistics) through Gates A-D, wiring, tests, and `docs/LevelShiftIdxMeasured.md`; Gate E and both whole suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text, the prototype's own citation of the Kats formula
  (`ind_screen_r5.py`'s `@cand` decorator strings), and the system-prompt overrides (no Gate
  E, no whole-suite runs, docs/issues/ read-only) fully specified scope. One judgment call
  made without asking (logged as an ASSUMPTION in `01-level-shift-idx-100.md`): `window_size`
  (20, Kats' own default) is a fixed module constant, not an exposed keyword, matching
  `stability`/`lumpiness`'s own convention for their fixed `window_size=20` tiling — the
  smaller-blast-radius reading, since the issue's candidate name (`kats_level_shift_idx_100`)
  exposes only the outer window.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| KATS-LEVEL-SHIFT-IDX-100 | main thread | single task, sequential (implement -> gate), no parallel benefit |
