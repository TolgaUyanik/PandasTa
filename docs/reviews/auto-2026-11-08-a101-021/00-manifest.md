# Auto run a101-021 — 2026-11-08

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | A101-021 | issue #45 / `/brutally-honest-review --auto` invocation | Port Alpha101 `#21` (mean/std band regime with volume tiebreak) through Gates A-D, wiring, tests, and `docs/A101021Measured.md`. Gate E and both repos' suites are run by the launcher after this session. |

## Clarifications (asked ONCE, before execution)
- none needed: the issue text, CLAUDE.md's porting protocol, and the two
  already-merged sibling ports (`a101_048`, `a101_058`) fully specify scope,
  category placement, and gate requirements. `AskUserQuestion` is unavailable
  in this session per the system prompt's override rules.
- Two formula-level ambiguities were resolved as disclosed ASSUMPTIONs in the
  module docstring and `docs/A101021Measured.md` (not asked, since no question
  mechanism is available this session): (a) `stddev`'s degrees-of-freedom
  convention (`ddof=1`, pandas default, matching the issue's own prototype
  script), and (b) `adv(d)` as a plain volume rolling mean rather than
  Kakushadze's literal dollar-volume definition (required by the issue's own
  disclosed "unchanged under price x8" pre-flight measurement).

## Execution map
| Task | Lane | Why |
|------|------|-----|
| A101-021 | main thread | single task, needs judgment calls on category placement, ambiguous-operator resolution, and mutant-strength tuning that a parallel lane would re-derive from scratch |
