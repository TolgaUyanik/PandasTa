# Run manifest — TF-MEDIAN-ABSDIFF-20 (issue #118)

Mode C (batch task execution), single task, invoked via `--auto` with the task text given directly
(not resolved from a TODO file).

## Task

> TF-MEDIAN-ABSDIFF-20: port the indicator of issue #118 through Gates A-D, the wiring, the tests
> and docs/<Name>Measured.md, per the issue and the rules in your system prompt (median absolute
> daily log return (20). Source: TSFEL (BSD-3-Clause) — `features.py median_abs_diff:
> median(|diff(x)|)`.). Gate E and the suites are run by the launcher afterwards.

## Clarifications (Phase 2)

None asked. AskUserQuestion is unavailable in this issue-solver session; two judgment calls were
made at the most conservative (smallest-scope) reading and are logged as ASSUMPTIONs below.

* **ASSUMPTION (category / column name):** the issue gives no category. Chose `volatility`
  (alongside `natr`, `true_range`, `ui`), not `statistics` (where the sibling port
  `tf_centroid_20`, issue #116, landed), because this candidate's own measured comparators in the
  issue are volatility columns (`natr` 0.7422, `Stop_2ATR_pct` 0.7422, `Swing_Range_pct` 0.6794) —
  it is a realised-volatility measure (median absolute return), not a distributional-shape
  statistic. Column name `MEDABSDIFF_{length}` (default `MEDABSDIFF_20`), tracking the TSFEL
  function name `median_abs_diff`, following this codebase's uppercase-acronym-plus-params
  convention (`PFE_10_5`, `RCR_100`).
* **ASSUMPTION (log-return computation):** the prototype computes `np.log(c).diff().abs()`; the
  port instead computes `np.log(c / c.shift(1)).abs()` — algebraically identical, but the ratio
  form is bit-identical under a power-of-two price rescale while the two-log-and-subtract form is
  not (measured residual 8.882e-16 at ×8 / 1.776e-15 at ×64 for the rejected form, 0 for the
  shipped ratio form -- both reproducible by running `docs/measure_tf_median_absdiff_20.py`, which
  carries the rejected form as a non-shipped comparison block). Chosen because CLAUDE.md's Gate D
  explicitly requires ×8/×64 to be bit-identical, not merely close; `docs/TfMedianAbsdiff20Measured.md`
  records the measurement that drove the choice.

## Execution map (Phase 3)

Single task, main thread (not parallelizable — one indicator touching the five wiring points plus
shared doc files). No worktree isolation needed.

## Files touched

New: `pandas_ta/volatility/tf_median_absdiff_20.py`, `tests/test_tf_median_absdiff_20.py`,
`docs/TfMedianAbsdiff20Measured.md`, `docs/measure_tf_median_absdiff_20.py`.
Modified: `pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/volatility/__init__.py`,
`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
`tests/test_altport2_ports.py`.

## Known, disclosed limitation (not this port's bug, found while testing it)

`pandas_ta.core.AnalysisIndicators.strategy()` mutates the live `Category[name]` list in place
when sweeping a category (`_indicators_by_category` returns the dict's own list object, then
`strategy()` removes excluded names from it directly, with no restore). Calling
`df.ta.strategy("trend", ...)` or `"momentum"` once, anywhere earlier in the same process, drops
`long_run`/`short_run`/`td_seq` out of `Category` for the rest of that process. This is pre-existing
on `dev`, unrelated to this port, and only surfaces when `tests/test_wiring_accessors.py`'s
`test_each_previously_broken_category_runs` runs before `tests/test_altport2_ports.py`'s
category-count pin within the same pytest session — which the default alphabetical full-suite run
does not do (confirmed: `python -m pytest -q` is clean on this point). Recorded in
`docs/TfMedianAbsdiff20Measured.md`'s Gate F section instead of fixed, since `pandas_ta/core.py`'s
`strategy()` behaviour is out of this task's scope.
