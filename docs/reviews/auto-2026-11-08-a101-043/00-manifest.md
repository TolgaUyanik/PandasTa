# Auto run a101-043 — 2026-11-08

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | A101-043 | issue #46 / `/brutally-honest-review --auto` invocation | Port Alpha101 `#43` (relative-volume rank x 7-day reversal rank) through Gates A-D, wiring, tests, and `docs/A101043Measured.md`. Gate E and both repos' suites are run by the launcher after this session. |

## Clarifications (asked ONCE, before execution)
- none needed: the issue text, CLAUDE.md's porting protocol, and the three
  already-merged sibling ports (`a101_021`, `a101_048`, `a101_058`) fully
  specify scope, category placement, and gate requirements.
  `AskUserQuestion` is unavailable in this session per the system prompt's
  override rules.
- Two formula-level ambiguities were resolved as disclosed ASSUMPTIONs in the
  module docstring and `docs/A101043Measured.md` (not asked, since no
  question mechanism is available this session): (a) `adv(d)` as a plain
  volume rolling mean rather than Kakushadze's literal dollar-volume
  definition, reusing `a101_021`'s own resolution of the identical ambiguity
  (required for the expression to stay scale-free in `close` independently
  of `volume`); and (b) `ts_rank(x, d)` as `count(x[t-d+1..t] <= x[t]) / d`,
  reusing `a101_058`'s own `_ts_rank` convention (also shared by
  `pandas_ta.statistics.rank`).
- Category placement (`momentum`, not `volume`): the formula multiplies a
  volume-relative rank by a price-reversal rank; `a101_021`/`a101_048` (also
  mixed or price-led Alpha101 ports) sit in `momentum`, so this one follows
  that precedent rather than `a101_058`'s `volume` placement.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| A101-043 | main thread | single task, needs judgment calls on category placement, ambiguous-operator resolution, and mutant-strength tuning that a parallel lane would re-derive from scratch |
