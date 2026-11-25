# Auto run 2026-11-21-c22-transition-variance

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | C22-TRANSITION-VARIANCE | user prompt (/brutally-honest-review --auto), issue #130 | Port catch22's `SB_TransitionMatrix_quantile_3_ac_sumdiagcov` through Gates A-D, wiring, tests and `docs/<Name>Measured.md`, OR measure-and-revert per the issue's own closing rule. |

## Clarifications (asked ONCE, before execution)
- none needed — the issue text and the session's system-prompt rules fully
  specify scope, the allowed-files list, the Gate F test subset, and the
  explicit sanction for a measured revert ("Done when: shipped ... OR
  measured and reverted with that file kept as the receipt"). AskUserQuestion
  is unavailable per the issue-solver rules; no ambiguity required it anyway.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| C22-TRANSITION-VARIANCE | main thread | Needs main-context judgment throughout: reconstructing an undocumented GPL-3.0-only algorithm from a one-line paper gloss, a 432-combination black-box grid search against the pycatch22 oracle, and the ship-vs-revert call based on the measured ceiling. Not parallelizable — each step depends on the prior measurement. |

## What happened (summary, full log in `01-c22-transition-variance.md`)

Grid-searched 432 candidate pipelines (4 symbolisations x 3 matrix
normalisations x 3 covariance axes x 2 ddofs x 6 lags) against
`pycatch22.catch22_all`'s `transition_variance` output (GPL-3.0, used
strictly as a black-box numeric oracle, never read as source) over 366
sampled windows across 6 synthetic frames. Best result: Spearman rho 0.789,
7/366 windows exactly matched (tol 1e-9) — a qualitative gap from this
fork's bar for a correct catch22 port (its shipped siblings `c22_dfa`,
`c22_periodicity`, `c22_ami2` are bit-equal or near-so). Outcome: MEASURED
REVERT, per the issue's own closing rule. No `pandas_ta` module, wiring, or
test file was added or shipped.
