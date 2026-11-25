# Auto run auto-2026-11-23-fn-baspn-net — 2026-11-23

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|-----------------|
| 1 | FN-BASPN-NET | issue #150 (verbatim in the /brutally-honest-review --auto invocation) | Port finta's BASPN as `fn_baspn_net` (volume) through Gates A-D, the five wiring touch points, the tests and `docs/FnBaspnNetMeasured.md`. Gate E and the whole suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed. `AskUserQuestion` is unavailable in this headless issue-solver session
  (per the session's own rules); the task text and the repo's `CLAUDE.md` fully specify
  the formula, the gate table, and the file scope, so no ambiguity needed resolving by
  the most-conservative-reading rule either.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| FN-BASPN-NET | main thread | single task, no parallel scope to split; needs main-context judgment on EMA-implementation and naming decisions not fully specified by the formula text |
