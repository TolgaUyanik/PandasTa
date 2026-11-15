# Run manifest — IEASYM (issue #28)

## Task (free-form, taken as given)

> IEASYM: port the indicator of issue #28 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (the empirical
> form of Jiang et al. (2020)'s distribution-based asymmetry measure, over the). Gate E and
> the suites are run by the launcher afterwards.

Single task, no refs to resolve.

## Clarification

AskUserQuestion is unavailable in this session (issue-solver headless run). Per the
issue-solver rules, ambiguities are resolved with the most conservative reading and logged
as ASSUMPTION rather than asked. Assumptions below.

- ASSUMPTION 1: Issue's "Alternative forms ... pick one at Gate A" is read as "stay with the
  issue's own `IE_n` formula unless Gate A/C/D measurement on this repo's synthetic data
  shows it is unworkable (e.g. the count is always zero, or the std=0 edge case dominates)",
  not as "survey and pick among Rachev ratio / vol ratio / tsfresh form instead of the
  formula the issue actually specifies." The issue's "What" section states the formula as
  the ask; the alternatives are catalogued as fallbacks. Smaller-scope reading: implement
  `IE_n` first, record the fallback menu in the Measured doc, only switch if `IE_n` fails a
  gate.
- ASSUMPTION 2: returns are bar-to-bar log-returns of `close` (not simple pct-change), log
  so the column is exactly scale-free under power-of-two price rescaling (matches
  `pfe`/CLAUDE.md pattern: `step = log(close/close.shift(1))`).
- ASSUMPTION 3: std uses `ddof=1` (pandas default, sample stdev) since the issue's formula
  does not specify biased vs unbiased and there is no Pine/TA-Lib oracle for this one (no
  Pine source given for this indicator — unlike other ports, Gate A here is self-consistency
  against an independently written loop, same pattern as `pfe`, not a Pine-line citation).
- ASSUMPTION 4: category `statistics` (rolling tail-count statistic over returns, same
  family as `skew`, `kurtosis`, `zscore` already there).

## Execution map

One task, heavy main-context judgment (formula design, measurement, gate verdicts) →
**main thread**, not a parallel subagent lane. Gated once by a Fletcher reviewer subagent
after implementation, per Mode C step 9, round cap 3.
