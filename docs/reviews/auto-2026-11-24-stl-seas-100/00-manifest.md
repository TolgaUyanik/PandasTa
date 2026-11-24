# Auto run stl-seas-100 — 2026-11-24

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | KATS-STL-SEAS-100 | issue #155 (`/brutally-honest-review --auto` free-form task) | Port Kats tsfeatures' `get_stl_features` seasonality line (`1 - var(resid) / var(seasonal + resid)` from an STL(period=5) decomposition of log close, 100-bar window) as `stl_seasonal_strength` (statistics) through Gates A-D, wiring, tests, and `docs/StlSeasonalStrengthMeasured.md`; Gate E and both whole suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text and the system-prompt overrides (no Gate E, no whole-suite
  runs, `docs/issues/` read-only) fully specified scope. Two judgment calls made without
  asking (logged as ASSUMPTIONs in `01-stl-seas-100.md`):
  1. `statsmodels` cannot be imported by shipped code (dev-only dependency, `setup.py`), so
     STL itself had to be reimplemented from scratch in numpy rather than called directly —
     the same approach `kpss.py`/`arch_lm.py` already take for their own statsmodels
     originals. Smaller-blast-radius reading: match the established in-repo pattern rather
     than add a new hard dependency the fork's sole consumer does not have.
  2. `length` floor set to 50 (this port's own choice, derived from its LOESS implementation's
     own requirements — see Decision 4 in the Measured doc), not from Kats' own minimum, which
     is not independently confirmed (no network access to the Kats source).

## Execution map
| Task | Lane | Why |
|------|------|-----|
| KATS-STL-SEAS-100 | main thread | single task, sequential (implement -> gate), needed iterative numerical validation against the statsmodels oracle before the implementation could be trusted |
