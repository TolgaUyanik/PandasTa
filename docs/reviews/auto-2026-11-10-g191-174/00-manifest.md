# Mode C manifest — G191-174 (issue #74)

## Tasks

1. `g191-174` — port GTJA191 alpha `#174` ("up-day volatility EMA") as `g191_174` through
   Gates A-D, the five wiring touch points, tests, and `docs/G191174Measured.md`, per issue #74
   and the issue-solver system prompt's override rules (Gate E and the test suites run by the
   launcher afterwards, not this session). Source: free-form task description in the
   `/brutally-honest-review --auto` invocation, taken as given (Mode C step 1, "free-form list
   -> take as given").

## Clarifications (Phase 2)

None needed. The task text embeds the issue's own formula, the system prompt carries the full
issue text plus the repo's porting protocol (CLAUDE.md) and the Gate E/F override rules, and the
sibling ports `g191_023` (issue #73, same `STD`/GTJA `SMA` operators, ratio form) and `g191_160`
(issue #67, down-day counterpart) gave an unambiguous implementation template -- `g191_160` in
particular is the closer precedent since this alpha, like it, is a single (non-ratio)
accumulator needing an explicit `/close` division, per the issue's own candidate line
("scale-free form: /close"). No destructive step is implicated (new files plus additive edits
to allow-listed files only).

ASSUMPTION: "Gate E and the suites are run by the launcher afterwards" in the task text is read
as the issue-solver system prompt's own override rule restated, not a new instruction -- this
session still runs `python -m pytest -q` itself (required by the system prompt) but treats Gate
E and the *parent repo's* (Backtesting) suite as out of scope, and does not touch
`docs/gate_e_ledger.csv`.

## Execution map

Single task, no parallel lanes: main thread. Reason: the work spans a tightly-coupled set of
five wiring touch points plus four shared project-wide docs (README.md, IndicatorDictionary.md,
MLCompanionContract.md, test_altport2_ports.py) that all encode the SAME running counts and must
stay mutually consistent -- splitting it across subagents would just reintroduce the
coordination problem Mode C's parallel-map is meant to avoid for genuinely independent tasks.

## Files touched

`pandas_ta/volatility/g191_174.py` (new), `pandas_ta/volatility/__init__.py`,
`pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_g191_174.py` (new),
`docs/measure_g191_174.py` (new), `docs/G191174Measured.md` (new), `README.md`,
`docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`,
`tests/test_altport2_ports.py`.
