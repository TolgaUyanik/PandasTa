# TTR-TDI-20 (issue #148) — auto run manifest

## Task

Port the indicator of issue #148 through Gates A-D, the wiring, the tests and
`docs/TdiMeasured.md`: Trend Detection Index (Pee; 20, multiple 2). Source: R TTR
(GPL-2.0) — `TDI.R: |sum_n mom| - (sum_2n |mom| - sum_n |mom|), mom = price - price[n]`.
Gate E and both repos' whole suites are run by the launcher afterward, not this session.

## Clarifications

None needed — the issue states the formula, the scale-free `/close` form, and the
parameters (length 20, multiple 2) explicitly. One judgment call made and logged as an
ASSUMPTION below, per the session's "most conservative reading" rule (no AskUserQuestion
available in this session).

**ASSUMPTION:** the prototype (`docs/issues/screen/ind_screen_r5.py`, `ttr_tdi_20`)
applies `mom.fillna(0)` before the rolling sums; the issue's own distilled formula has no
such term. Per the session rule "Gate A starts from the source formula, not the
prototype", the port does NOT reproduce the `fillna(0)`, leaving `mom` (and therefore the
column) NaN until real history exists. This lengthens the warm-up relative to the
prototype (59 bars at the defaults) but keeps Gate A traceable to the issue's own text
rather than to an unstated screening-harness convenience. Disclosed in the module
docstring, the test docstring, and `docs/TdiMeasured.md`.

## Execution map

Single task, no parallel fan-out: implementation on the main thread (needs the session's
full CLAUDE.md context — porting conventions, five wiring touch points, doc/count
update locations — which a fresh subagent would have to re-derive from scratch), gated by
one Fletcher reviewer subagent per round, per Mode C step 9.

## Category/name choice

`tdi`, category `trend` (R TTR classifies TDI as a trend indicator; sits alongside
`vhf`/`chop`/`adx` in `pandas_ta/trend/`, all trend-vs-chop ratio indicators). Column
`TDI_20_2` (length, multiple — both always appended, matching the issue's own
parenthetical "(Pee; 20, multiple 2)").
