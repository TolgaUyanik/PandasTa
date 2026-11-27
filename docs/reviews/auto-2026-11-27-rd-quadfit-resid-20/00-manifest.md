# Auto run rd-quadfit-resid-20 — 2026-11-27

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | RD-QUADFIT-RESID-20 | issue #180 | Port `rd_quadfit_resid_20` through Gates A-D, wiring, tests, docs/RdQuadfitResid20Measured.md (Gate E/F whole-suite deferred to the launcher per the session's system-prompt override) |

## Clarifications (asked ONCE, before execution)
AskUserQuestion is unavailable in this issue-solver session; per its own override
("take the most conservative reading ... log it as an ASSUMPTION"), the following
were resolved without asking and logged here rather than raised:

- **Residual sd estimator (ddof).** The poster's words name a model (2nd-order
  polynomial fit) and a residual (observed - predicted) but no estimator for
  "residual sd." Resolved to population std (ddof=0, numpy's own `.std()`
  default), matching the one concrete recipe the issue discloses: the screen
  prototype's own `_quad_resid` helper, `R.std(1)`. Not pandas' ddof=1 default.
- **Category placement.** Resolved to `statistics`, matching the two siblings
  from the same prototype function family already ported there
  (`rd_knot_pos_40`, `rd_knot_dslope_40`), not `trend` (price-action/structural
  ports only) or `momentum`.
- **`length < 4` behaviour.** A quadratic's 3 fitted parameters leave zero
  residual degrees of freedom below `length=4` (every window fits exactly,
  output is always `0/0 = NaN`). Resolved to raise `ValueError` rather than
  silently ship an all-NaN column — matches the fork's existing convention
  (`rd_knot_pos_40`'s `knot_margin` validation).
- **Design matrix parametrization (raw vs normalised `t`).** The screen
  prototype normalises `t` to `[0, 1]`; this port uses raw `t = 0..length-1`
  instead, matching `rd_knot_pos_40`'s own convention. Mathematically
  equivalent (the OLS residual-maker's column space is invariant to any
  invertible affine reparametrization of `t`) — not a behavioural difference,
  just a style choice to match the nearer precedent.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| RD-QUADFIT-RESID-20 | main thread | single task, file scope (statistics module + wiring + tests + docs) needs judgment calls on the ddof/category/validation decisions above that benefit from main-context continuity; no parallel decomposition opportunity |
