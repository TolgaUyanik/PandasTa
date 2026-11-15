# EWMAC port — Mode C batch run (issue #29)

## Task

Single free-form task, taken as given (no TODO tag, no plan file):

> EWMAC: port the indicator of issue #29 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in the system prompt
> (`(EMA_fast(close) - EMA_slow(close)) / sigma`, where `sigma` is the recent standard
> deviation). Gate E and the suites are run by the launcher afterwards.

## Clarifications

`AskUserQuestion` is unavailable in this (issue-solver) session. Per the issue-solver
rules, any ambiguity is resolved by the most conservative (smaller-scope) reading and
logged as an ASSUMPTION rather than asked. Two such assumptions were needed, both
recorded in `docs/EwmacMeasured.md`'s "Gate A decisions" section:

- ASSUMPTION: `sigma` is Carver's EWMA standard deviation of `close.diff()`, computed
  ONCE and shared across all six columns, with EWMA span (`vol_length`) defaulting to 35
  (recalled from `pysystemtrade`'s `robust_vol_calc`, not cited to a page — no book/web
  access in this session).
- ASSUMPTION: no forecast scalar or cap is shipped (the issue explicitly allows this: "a
  tree does not need the scalar; the raw ratio is enough").
- ASSUMPTION: Kaufman's possibly-squared-stdev Divergence Index variant was not checked
  against the physical book (no access); `ewmac`'s own `sigma` is unsquared and
  scale-free by construction, and Kaufman's form is treated as the same family rather
  than built as a second module.

No destructive or irreversible step was in scope (no push, no Gate E run, no suite run
beyond this repo's own `pytest`).

## Execution map

Single task, main-thread execution (not parallelizable: one module touching five wiring
points plus shared doc files with cross-dependencies between them — Category count,
README count, dictionary regeneration, MLCompanionContract's running count sentence all
depend on each other in sequence).

## Gate

One Fletcher reviewer dispatch (`Explore` subagent, read-only), round 1. Verdict: PASS,
with one NIT (cosmetic alphabetical ordering in `pandas_ta/core.py`). Fixed inline since
free and verified with a re-run of `tests/test_ewmac.py` + `tests/test_wiring_accessors.py`
(80 passed). No second review round needed — the NIT alone would not have gated.
