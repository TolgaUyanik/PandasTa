# Mode C manifest — PVCORR (issue #18)

## Task (as given)

> PVCORR: port the indicator of issue #18 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (rolling
> correlation between the bar return and the change in log volume over a window.). Gate E
> and the suites are run by the launcher afterwards.

Single free-form task, no TODO tags. Run folder: `docs/reviews/auto-2026-10-31-pvcorr/`.

## Clarifications

AskUserQuestion is unavailable in this headless session (issue-solver system prompt
override). Per that override: most conservative reading taken, logged as ASSUMPTION, no
question asked.

The issue itself delegates several choices to "Gate A" explicitly ("Pick at Gate A",
"Decisions: ... owed"), so these are not scope gaps in the Mode C sense — they are the
task's own instruction to decide and document. Decisions made, with reasoning in
`docs/PvcorrMeasured.md`:

* ASSUMPTION: category = `volume` (not `statistics`). Reason: `pvcorr` takes only `close`
  and `volume`, already present on any OHLCV frame, like `mfi`/`nvi`/`obv` (volume
  category) rather than `beta`/`covariance` (statistics category, which need an external
  `other` series the frame does not carry). Smaller-blast-radius reading: registering in
  `Category` under `volume` lets `df.ta.strategy()` sweep it with no exclusion-list entry,
  same as every other close+volume indicator already there.
* ASSUMPTION: volume transform = masked log-ratio `log(V[t]/V[t-1])`, NaN when either side
  is non-positive — not qlib's `log(V[t]/V[t-1] + 1)`. Reason: the issue names "zero-volume
  bars (log 0)" as an explicit open decision; the `+1` form still divides by `V[t-1]` before
  the `+1` runs, so it is undefined at a zero-volume prior bar, and it breaks exact
  scale-invariance under volume rescaling (Gate D). The masked ratio is both well-defined at
  zero volume and exactly scale-invariant. Full reasoning: `docs/PvcorrMeasured.md`.
* ASSUMPTION: Pearson, not Spearman. Reason: none of the three cited sources, nor qlib's
  `CORR`/`CORD`, ask for a rank correlation.
* ASSUMPTION: window = 20 bars. Reason: not measured or sourced; picked as a month-scale
  default, smaller than the fork's other rolling-stat defaults (30), documented as a Gate A
  judgment call, not a claim of optimality.

No destructive or irreversible step was in scope (code, tests, docs only); nothing escalated
on that basis.

## Execution map

One task, no parallelizable sub-scope (wiring, module, tests and docs are not independently
assignable — the wiring touch points and the tests both depend on the module's final column
name and category). Executed on the main thread, in this order: module → wiring (3 touch
points) → tests → regenerate dictionary → README/contract counts → `docs/PvcorrMeasured.md`.
Gated once, per Mode C Phase 4, by a Fletcher reviewer subagent against the full diff.
