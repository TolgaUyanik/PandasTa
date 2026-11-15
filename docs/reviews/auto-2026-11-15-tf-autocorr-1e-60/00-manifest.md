# `/brutally-honest-review --auto` run — TF-AUTOCORR-1E-60

**Date:** 2026-11-15
**Mode:** C (batch task execution) — the invocation's argument is a free-form
task reference, not a plan file path, so Mode C applies and there is **no
pre-gate** (Mode C resolves tasks, not plans carrying load-bearing reasoning).
`--fletcher` is on automatically.
**Run folder:** `docs/reviews/auto-2026-11-15-tf-autocorr-1e-60/`

## Phase 1 — Select

One task.

| id | scope | source |
|---|---|---|
| `tf-autocorr-1e-60` | Port the first 1/e crossing of the ACF of log price (60) as `pandas_ta/statistics/tf_autocorr_1e_60.py` through Gates A–D, five wiring touch points, tests and `docs/TfAutocorr1E60Measured.md`. | the `--auto` argument, which quotes PandasTa issue #114 |

The task text, verbatim:

> TF-AUTOCORR-1E-60: port the indicator of issue #114 through Gates A-D, the
> wiring, the tests and docs/<Name>Measured.md, per the issue and the rules in
> your system prompt (first 1/e crossing of the ACF of log price (60). Source:
> TSFEL (BSD-3-Clause) — `features.py autocorr: first lag with ACF < 1/e`.).
> Gate E and the suites are run by the launcher afterwards.

## Phase 2 — Clarify

**No questions were asked.** `AskUserQuestion` is unavailable in this headless
session, and the governing rules say: *"Where a skill says to ask, take the
most conservative reading (the smaller scope) and log it as an ASSUMPTION."*
Every open reading was therefore decided by the smaller-scope rule and logged.

### ASSUMPTIONS

| # | Open question | Reading taken (smaller scope) | Where it is priced |
|---|---|---|---|
| A1 | Which category? | `statistics` — the home of every other autocorrelation column in the fork (`ts_ac1_60`, `ts_aggac_60`, `firstzero_ac`, `diff2_acf1`) and of the other TSFEL ports. | — |
| A2 | Column name? | `TFAUTOCORR1E_{length}`, following the `TFDFA_` / `TFCENTROID_` / `TFSPECENT_` / `TFZEROCROSS_` pattern already in `pandas_ta/statistics/`. | — |
| A3 | ADJUSTED or biased ACF? | **Adjusted** (divide the lag-k products by `length - k`): what the screen prototype's `.mean(1)` computes and what `statsmodels.acf(adjusted=True)` gives. The biased reading is measured and shown to be a different column. | Measured §A7(a) |
| A4 | Strict `<` or `<=`? | **Strict `<`** — the issue's own words ("ACF < 1/e"). | Measured §A7(b) |
| A5 | Is `NLAGS` a parameter? | **No.** 20 is the issue's own parameter and so the ladder the screen measured; `length` alone is exposed, exactly as `tf_dfa_100` fixes its box ladder. Smaller API surface. | module docstring, `Args` |
| A6 | What is the minimum `length`? | `2 * NLAGS = 40` — two points per lag at the longest lag. Below it, fall back to the default rather than ship an estimator averaging a handful of products. | Measured §C |
| A7 | A noise floor, or none (the prototype has none)? | **Floor kept**, at the fork's existing 4096 eps on a dimensionless quantity, because the unguarded failure is invisible rather than absurd. Its cost is measured and published rather than assumed to be zero. | Measured §G |
| A8 | Degenerate window: NaN, or the 21 sentinel? | **NaN.** 21 means "no crossing", which is a statement about a window that has an ACF; a window with no variance has none. This is also the prototype's behaviour (`np.where(var == 0, np.nan, out)`). | module docstring |

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `tf-autocorr-1e-60` | **main thread** | A single task whose work is one coupled unit — the module, its five wiring touch points, the harness, the tests and the receipt all have to agree on the same measured numbers. Nothing to parallelise, and no second task to conflict with. No worktree isolation needed. |

## Phase 4/5 — see `01-tf-autocorr-1e-60.md` and `99-summary.md`

## Sequencing honesty

This manifest was written **after** the implementation and before the first
review gate, not before Phase 4 as the skill's phase order prescribes. The
task set was a single, fully specified item, so nothing in it was decided by
writing it down; the ASSUMPTIONS table records decisions made during the
implementation, in the order the implementation hit them. Recorded here rather
than silently back-dated.
