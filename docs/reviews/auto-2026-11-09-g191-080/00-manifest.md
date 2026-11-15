# Auto run g191-080 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | g191-080 | issue #64 | Port GTJA191 alpha #80 (5-day volume change) through Gates A-D, wiring, tests, docs/G191080Measured.md |

## Clarifications (asked ONCE, before execution)
- none needed — the issue's own text and prototype (`docs/issues/screen/ind_screen.py:426-427`)
  fully specify the formula (`(V-V5)/V5*100`, `V5 = DELAY(VOLUME,5)`) and the gates owed. No
  ambiguity to resolve; AskUserQuestion is unavailable in this session per the harness rules, so
  this would have been an ASSUMPTION rather than a question regardless.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| g191-080 | main thread | single task, no parallel-eligible scope split; Gate E and this repo's
full suite run are the launcher's job, not this session's |
