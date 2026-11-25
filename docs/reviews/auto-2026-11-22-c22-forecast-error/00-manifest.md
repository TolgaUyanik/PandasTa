# Auto run c22-forecast-error — 2026-11-22

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | C22-FORECAST-ERROR | issue #137 (verbatim in session system prompt) | Port catch22 `FC_LocalSimple_mean3_stde` (3-bar mean forecast error of the last 100 daily returns) through Gates A-D, the five wiring touch points, tests, and `docs/C22ForecastErrorMeasured.md` |

## Clarifications (asked ONCE, before execution)
- none needed — the issue, `CLAUDE.md`'s porting protocol and two prior
  catch22 ports (`c22_mode_10`, `c22_ami2`) in this same repo fully specify
  scope, gates and file touch points. The only open question (the exact
  catch22 output name and ddof convention) was settled by measurement
  against the installed GPL-3.0 `pycatch22` package (Gate A's own
  black-box-fit methodology, already established by this fork's sibling
  ports), not by asking.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| C22-FORECAST-ERROR | main thread | single task, no parallel scope to split; implementation requires judgment (formula derivation via black-box fit) that a sub-agent lane would just hand back up anyway |
