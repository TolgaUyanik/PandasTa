# 00-manifest.md — C22-OUTLIER-TIMING-POS

**Run:** `auto-2026-11-23-c22-outlier-timing-pos`
**Invocation:** `/brutally-honest-review --auto "C22-OUTLIER-TIMING-POS: port the indicator of
issue #143 through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue
and the rules in your system prompt ... Gate E and the whole suites are run by the launcher
afterwards."`

## Phase 1 — select

One free-form task, taken as given: port catch22's `DN_OutlierInclude_p_001_mdrmd` ("timing of
positive return outliers") as `c22_outlier_timing_pos`, per PandasTa issue #143 and the
issue-solver system prompt's rules (Gate E and the whole suites are the launcher's job, not
this session's).

## Phase 2 — clarify

No gaps needing a user question: the issue's "Done when" and gate table are actionable as
written, and `AskUserQuestion` is unavailable to this headless session per the system prompt
(take the most conservative reading, log as ASSUMPTION). ASSUMPTIONS made during execution,
each stated in the module docstring / `docs/C22OutlierTimingPosMeasured.md` as well:

- **ASSUMPTION (outer aggregation).** The published one-line definition does not say whether the
  outer median is taken over the full swept 0.01-step grid (so a wide threshold band outweighs a
  narrow one) or over distinct count-levels only. Took the literal "sweep in increments of 0.01"
  reading: the full grid, each `m` counted once. Smaller scope: this is what the family's own
  naming ("_001" = the step) says most directly, without inventing an extra normalization.
- **ASSUMPTION (minimum count).** The sweep's floor is "at least 2 points" (the fewest that admit
  a gap), not a larger named minimum. Smallest defensible floor, not an invented larger one.
- **ASSUMPTION (gap units).** Gaps are reported as a fraction of `length`, matching the rest of
  this fork's scale-free columns, and is provably inert for Gate E (a monotone rescale, invisible
  to Spearman rank correlation) — so this choice cannot be wrong at the only gate that measures
  predictive value, only at Gate A's exact-value check against a reference this environment
  cannot run anyway.

No destructive or irreversible step was in scope (code, tests, docs only; no push, no Gate E run,
no whole-suite run per the system prompt's explicit carve-out).

## Phase 3 — execution map

Single task, main thread (not a parallel-subagent lane): implementing a catch22 port from a
one-line published definition, with no reliable reference implementation available, needed
main-context judgment at every step (algorithm reconstruction, a from-scratch closed-form
performance rewrite, Gate A/B/C/D measurement, docs). Nothing here had a non-overlapping,
independently-parallelizable scope.

## Phase 4 — gate

Gated below (01-c22-outlier-timing-pos.md) by a Fletcher reviewer subagent, per the user's
standing "Review loop: fix and re-review up to round 4" override of this skill's own 3-round cap.
