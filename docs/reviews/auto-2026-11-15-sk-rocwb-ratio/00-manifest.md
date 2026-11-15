# /brutally-honest-review --auto — run manifest

**Date:** 2026-11-15 · **Run id:** `sk-rocwb-ratio` · **Mode:** C (batch task
execution, one task) · **Reviewer:** Fletcher persona, fresh read-only subagent
per round.

Mode B was not used: the `--auto` argument is a free-form task, not a path to a
plan file, so there is no plan to pre-gate (Mode D step 0 applies to Mode B only).

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `sk-rocwb-ratio` | Port `sk_rocwb_ratio` — the 20-bar ROC over the root mean square of its own last 5 readings, Skender Stock.Indicators' `RocWb` (Apache-2.0) — through Gates A–D, the five wiring touch points, tests and `docs/SkRocwbRatioMeasured.md`. Gate E and both repos' suites are run by the launcher afterwards. | the `--auto` argument, which restates PandasTa issue #109 and the issue-solver rules in the session prompt |

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless issue-solver session, so every
ambiguity was resolved by the most conservative (smallest-scope) reading and
logged as an ASSUMPTION in `docs/SkRocwbRatioMeasured.md`. The four that mattered:

1. **The band is an RMS, not a standard deviation.** The issue spells it
   `sqrt(mean5(ROC20^2))`; `RocWb.Series.cs` is unreadable from this worktree, so
   the issue's spelling is taken literally and the stdev reading is MEASURED as
   the alternative (§C2) rather than argued away.
2. **The ROC keeps the prototype's spelling** `100 * (c / c20 - 1)` instead of
   importing `pandas_ta.roc` (`100 * (c - c20) / c20`). The repo's "import the
   helper" rule pulls one way; the issue's "Gate E was measured on this
   expression" pulls the other. §A3 measures the gap (up to 4.007e-12 relative on
   703 .. 1,411 bars per frame) and the Gate E tie wins.
3. **An `isfinite` mask is added** although the prototype has none — the same
   divergence issue #108 made — on measured evidence (§G2: without it, an
   infinite close leaves five bars carrying plausible numbers instead of a gap).
   On finite input the two are bit-identical, so the tie survives.
4. **Parameters are exposed** (`length`, `band_length`) rather than frozen as
   module constants, matching `roc` and the rest of the bucket. Defaults are the
   issue's (20, 5), which is what the Gate E ledger requires.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `sk-rocwb-ratio` | main thread | one indicator, five wiring touch points in shared files (`pandas_ta/__init__.py`, `core.py`), plus measurement-driven judgment at every step — nothing to parallelise and nothing safe to hand to a subagent |

Destructive steps: none. Nothing is pushed; the launcher opens the PR.

## Files

Added:

* `pandas_ta/momentum/sk_rocwb_ratio.py`
* `tests/test_sk_rocwb_ratio.py`
* `docs/measure_sk_rocwb_ratio.py`, `docs/measure_sk_rocwb_ratio_cpu.py`
* `docs/SkRocwbRatioMeasured.md`
* this folder

Modified: `README.md`, `docs/IndicatorDictionary.md` (regenerated),
`docs/MLCompanionContract.md`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
`pandas_ta/momentum/__init__.py`, `tests/test_altport2_ports.py`.

## Reports

* `01-sk-rocwb-ratio.md` — the task log, and every review round's findings with
  the fix applied under each: rounds 1 and 2 (both REVISE) verbatim, rounds 3 and
  4 (both PASS) as the findings they returned.
* `99-summary.md` — the run summary: one row per round, the final gate state, and
  what is owed to the launcher.
