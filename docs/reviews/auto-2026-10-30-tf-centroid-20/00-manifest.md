# Manifest — auto-2026-10-30-tf-centroid-20

## Phase 1 — Select

Single free-form task, taken as given (Mode C, batch-of-one):

> TF-CENTROID-20: port the indicator of issue #116 through Gates A-D, the wiring, the
> tests and docs/<Name>Measured.md, per the issue and the rules in your system prompt
> (temporal centroid of squared returns (20). Source: TSFEL (BSD-3-Clause) —
> `features.py calc_centroid: sum(t * x^2) / sum(x^2)`.). Gate E and the suites are run
> by the launcher afterwards.

Run folder: `docs/reviews/auto-2026-10-30-tf-centroid-20/`.

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this environment (issue-solver headless session).
Per the overriding instructions, gaps are resolved by the most conservative (smaller-scope)
reading and logged as ASSUMPTIONs instead of asked:

1. **Category placement.** The issue does not name a `pandas_ta` category. No `tf_`-prefixed
   TSFEL candidate has shipped before (checked: no match for "TSFEL" or "calc_centroid" in
   `pandas_ta/` or `docs/` outside `docs/issues/`). ASSUMPTION: `statistics`, the existing
   home for comparable scale-free statistical descriptors (`entropy`, `kurtosis`, `skew`,
   `zscore`) built from a single input series — the closest sibling kind already in the
   fork, and the smaller-scope choice versus inventing a new category or forcing it into
   `momentum` (which holds price-direction oscillators, not generic signal statistics).
2. **Parametrization.** The issue's candidate id bakes in `_20` and the prototype hardcodes
   `length=20`. ASSUMPTION: ship `length` as a parameter (default 20), following this fork's
   own precedent for every recent port with a baked-in window in its candidate id (`pfe`,
   `maxvol_adv`) — smaller-scope than inventing a parametrization scheme, since it reuses an
   existing convention rather than adding a new one.
3. **Gate E / proxy overlap re-run.** Per the overriding rules in this session's system
   prompt, Gate E is run by the launcher, not this session. The issue's own prototype-stage
   numbers (max |ρ| 0.5943, fork overlap 0.6167) are quoted in `docs/TfCentroid20Measured.md`
   as owner-measured context, explicitly marked as not re-verified this session, never
   presented as a Gate E result on the port.

No questions asked; "none needed" in the Mode C sense (the questions above have no human to
answer them in this environment, so they are ASSUMPTIONs rather than blocked items).

## Phase 3 — Plan execution

One task, file scope: `pandas_ta/statistics/tf_centroid_20.py` (new),
`pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`tests/test_tf_centroid_20.py` (new), `tests/test_altport2_ports.py`, `README.md`,
`docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
`docs/TfCentroid20Measured.md` (new). All touch points overlap through the same
five-wiring-point contract (CLAUDE.md) and the README/dictionary/contract count
cross-checks, so there is no independent, non-overlapping slice to hand to a parallel
subagent. **Lane: main thread**, single task, no parallelism.
