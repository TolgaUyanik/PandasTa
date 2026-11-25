# Run summary — 2026-11-21-c22-transition-variance

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| C22-TRANSITION-VARIANCE | PASS | 3 | `docs/measure_c22_transition_variance.py`, `docs/C22TransitionVarianceMeasured.md` | A future attempt at this feature needs the paper's or hctsa's own text for the transition-matrix normalisation and the covariance's axis/divisor convention — see `docs/C22TransitionVarianceMeasured.md` §E |

Outcome: **measured revert**, per issue #130's own closing rule ("Done when:
shipped ... OR measured and reverted with that file kept as the receipt ...
A measured revert closes this exactly as well as a ship"). A 432-combination
black-box grid search against `pycatch22` (GPL-3.0, measurement-only) tops
out at Spearman ρ 0.789 at the right order of magnitude and 7/366 exact
matches at best overall — a qualitative gap from this fork's bar for a
correct catch22 port. No `pandas_ta` module, wiring, or test file was added
or shipped.

Task-file write-back: skipped (no convention detectable — this task came
from a verbatim issue-solver prompt, not a TODO-file task list with its own
checkbox convention).
