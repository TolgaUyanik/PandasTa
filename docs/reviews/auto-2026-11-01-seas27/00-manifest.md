# Run manifest -- SEAS (issue #27)

Invocation: `/brutally-honest-review --auto "SEAS: port the indicator of issue #27 through
Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue and the rules
in your system prompt (Heston-Sadka annual-lag seasonality, per instrument. At bar T, the
return over the next). Gate E and the suites are run by the launcher afterwards."`

Mode: C (batch task execution), single task. No plan file was given; the argument is one
free-form task description, so Mode B's plan routing does not apply and there is no
pre-gate.

## Phase 1 -- Select

One task: port the Heston-Sadka annual-lag seasonality indicator (issue #27) through
Gates A-D, wire it (Category / core.py accessor / package export), write
`tests/test_seas.py`, and write `docs/SeasMeasured.md`, per this worktree's `CLAUDE.md`
and the issue-solver system prompt's overrides (no Gate E run, no suite run beyond this
repo, no git push, shell restricted to the allowed command list).

## Phase 2 -- Clarify

AskUserQuestion is unavailable in this session (issue-solver headless run). No human
answers. Every open choice is resolved by the most conservative (smaller-scope) reading
and logged as an ASSUMPTION rather than asked:

- **ASSUMPTION (category):** `performance`. The issue's indicator is a per-instrument
  return measure; the existing `performance` category already holds
  `log_return`/`percent_return`/`trend_return`/`max_return` -- all return-based,
  scale-free-by-construction indicators of exactly this shape. `ml`/`statistics` were
  considered and rejected: this is a return, not a generic statistic.
- **ASSUMPTION (`years` default):** 1, not 5. The issue says "decide at Gate A" between
  Quantpedia's `Y=1` and the issue's own `Y=5` alternative. `Y=1` is the smaller-scope
  reading (252-bar warm-up, not 1,260) and is the version actually cited by the issue's
  strongest (T2) source. `years` stays a free parameter so `SEAS_21_5` is reachable; it is
  just not what `df.ta.strategy()` sweeps by default.
- **ASSUMPTION (bar-count vs. date-anchored):** bar-count (252 bars), matching the
  formula as literally given in the issue (`T - 252*y + h`). The issue's own risk note
  calls the date-anchored, `DatetimeIndex`-based version a separate, larger-scope design;
  not built here.
- **ASSUMPTION (length cap):** `length` must be `<= 252`, enforced by raising
  `ValueError`. At `years=1` (the smallest `y` the loop ever uses), a longer window would
  read `close[T - 252 + length]` with `length > 252`, i.e. a bar strictly after `T` --
  the exact causality violation the issue itself flags as "Gate B must still prove it
  with a mutant." One check at `y=1` covers every larger `y`, which has strictly more
  slack.

Recorded here rather than asked; no destructive or irreversible step is implicated by any
of the four, so none needed pre-authorization.

## Phase 3 -- Plan execution

Single task, no parallel lanes: implemented on the main thread (file scope is one new
indicator module plus five already-known wiring touch points, no independent slices to
split across subagents).

| Task | Lane | Why |
|---|---|---|
| SEAS-27 | main thread | one coherent port; the five wiring touch points and the test/docs pair are not independently choosable work |

## Phase 4/5 -- Execute + gate

Implementation log, review round(s), and the final summary are in
`01-seas27.md` and `99-summary.md` in this folder.

## Hard limits observed

No destructive/irreversible step appears in this task (no force-push, no deletion of
data, no deploy, no external publish). Gate E and both repos' suites are explicitly out
of this session's scope per the issue-solver system prompt (the launcher runs them); this
is a scope boundary from the surrounding system, not a Mode C hard-limit trigger.
