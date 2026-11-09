# Auto run g191-044 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | G191-044 | issue #60 (verbatim, passed as --auto argument) | Port GTJA191 alpha #44 (decayed low-volume correlation rank + VWAP momentum rank) through Gates A-D, wiring, tests, docs/G191044Measured.md. Gate E and both repos' suites run by the launcher afterward. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text, CLAUDE.md's porting protocol, and the merged
  sibling ports (`g191_026`, `g191_098`, `g191_144`, `g191_165`, `g191_190`)
  fully specify scope, gates and done-criterion. AskUserQuestion is
  unavailable in this headless issue-solver session; no ambiguity required
  it anyway.
- No disclosed interpretation ambiguity: the issue's own parenthetical
  states the scale-free conversion directly ("VWAP -> (H+L+C)/3"), and the
  issue's own prototype (`docs/issues/screen/ind_screen.py:362-366`)
  matches the issue's formula string line-for-line, including every window
  length (`mean_v_length=10, corr_length=7, decay1_length=6,
  tsrank1_length=4, delta_length=3, decay2_length=10, tsrank2_length=15`).

## Execution map
| Task | Lane | Why |
|------|------|-----|
| G191-044 | main thread | single task, already implemented in this session before the review was invoked; no parallelism opportunity, no scope overlap to isolate |
