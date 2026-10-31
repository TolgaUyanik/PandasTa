# Run manifest — FFD port (issue #13)

Mode C batch execution, single task, driven by the issue-solver headless session for
`TolgaUyanik/PandasTa#13`.

## Task

Port AFML's fixed-width window fractional differencing of log price as a new indicator,
through Gates A-D, the five wiring touch points, tests, and `docs/FfdMeasured.md`. Gate E
and the parent repo's suite are run by the issue-solver launcher after this session, not by
this run.

## Clarifications

None asked (AskUserQuestion unavailable in this headless session; the issue text and
CLAUDE.md fully specify scope). Two judgment calls the issue explicitly left open were
resolved and logged as ASSUMPTIONs below, using the most conservative / narrowest-scope
reading in each case.

**ASSUMPTION 1 — Gate D fix.** The issue offered three options: "a tolerance with a stated
reason, a re-centred form, or something else." Chose the re-centred form (forcing
`sum(weights) = 0` by adjusting the most-lagged weight) combined with the existing
`kalman_trend` anchor-ratio device, because it fixes bit-identical scale invariance AND an
anchor-dependence bug the anchor-only approach introduced (measured: head-stability failure
of 6.3e-2 before the fix, 1.2e-15 after). Narrowest-scope reading: a one-line correction to
the weight vector, not a new generic re-centring layer.

**ASSUMPTION 2 — Causality of `d`.** The issue offered "`d` must be a fixed parameter, or
chosen on a trailing window only." Chose the fixed-parameter form (narrower scope: no new
ADF implementation, no trailing-window estimator, no new warm-up/test machinery for a
second algorithm).

**ASSUMPTION 3 — default `threshold`.** Not raised by the issue. AFML's own worked example
uses `threshold=1e-5`, which needs 1,458 bars just to emit a first value and does not fit
this repo's fixed 600-bar `gen_indicator_dictionary.py` probe at all (that script is an
existing helper module outside this session's allowed edit scope). Chose `threshold=1e-4`
(width 282) as the default, which fits the probe and is still within AFML's own
commonly-used threshold range; a caller can pass `1e-5` to get AFML's own cutoff.

## Execution map

Single task, main thread (no parallel lanes — one indicator, one coherent set of judgment
calls that need to be made together, not independently parallelizable).

| task | lane | why |
|---|---|---|
| FFD port | main thread | one indicator; the two design decisions interact (the re-centring fix also fixes the anchor-dependence bug the scale-invariance fix introduced), so splitting them across agents would risk inconsistent reasoning |
