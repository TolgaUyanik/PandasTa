# KATS-STL-TREND-100 — port STL trend strength as `stl_trend_strength`

Task text (verbatim, from the invocation):

> KATS-STL-TREND-100: port the indicator of issue #160 through Gates A-D, the wiring, the
> tests and docs/<Name>Measured.md, per the issue and the rules in your system prompt (STL
> trend strength of log price (100, period 5). Source: Kats tsfeatures (Meta, MIT) —
> `get_stl_features: 1 - var(resid) / var(trend + resid)`.). Gate E and the whole suites are
> run by the launcher afterwards. You and every subagent verify with `python -m pytest -q
> <the port's test modules> tests/test_readme_counts.py tests/test_altport2_ports.py
> tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py
> tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` plus any PandasTa
> test module a finding names, never the whole suite (the launcher runs it). Until the
> launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected,
> not a finding.

Clarifications: none needed (see `00-manifest.md`).

## Execution log

- Found the exact sibling port already merged: issue #155's `stl_seasonal_strength`
  (`pandas_ta/statistics/stl_seasonal_strength.py`), same STL decomposition
  (`period=5`, `seasonal=7`, `trend=11`, `low_pass=7`, `inner_iter=5`, `robust=False`),
  same Kats `get_stl_features` source, differing only in the final ratio
  (`var(seasonal + resid)` there, `var(trend + resid)` here).
- Read that module in full, including its `_build_ops` docstring (the linear-operator
  reduction under `robust=False`) and its Measured doc / test file / BHR run folder
  (`docs/reviews/auto-2026-11-24-stl-seas-100/`), which also records that port's own
  round-1 finding (a false "independent" claim about its hand-run fixed-point
  cross-check) — read specifically to avoid repeating that exact mistake here.
- Decided to import `_build_ops` (and `NOISE_ULPS`/`MIN_LENGTH`/`CHUNK_CELLS`) from
  `stl_seasonal_strength.py` rather than duplicating ~300 lines of LOESS/cycle-
  subseries/low-pass code. Confirmed this is an established repo pattern, not a new
  one, by grepping `pandas_ta/*/*.py` for cross-module imports of private helpers: e.g.
  `pandas_ta/momentum/sk_fcb_pos.py` imports `MIN_BARS, SPAN, _last_fractal` from
  `pandas_ta/volatility/sk_fcb_width.py`.
- Wrote `pandas_ta/statistics/stl_trend_strength.py`: same chunked sliding-window
  structure as `stl_seasonal_strength.py` (log-relative-to-window-start input, the
  flat/jitter guard, the matrix multiply against the shared operators), with the ratio
  changed to `1 - var(resid) / var(trend + resid)`.
- Wired the 3 new-module touch points: `pandas_ta/statistics/__init__.py` export
  (alphabetically after `stl_seasonal_strength`), `pandas_ta/__init__.py`
  `Category["statistics"]` entry (same position), `pandas_ta/core.py` accessor
  (`df.ta.stl_trend_strength()`); `pandas_ta/core.py`'s `from pandas_ta.statistics
  import *` picks the new function up automatically, confirmed by running the wiring
  test (`tests/test_wiring_accessors.py`) rather than assuming it.
- Wrote `tests/test_stl_trend_strength.py` (29 tests), explicitly scoping what the
  module's own test suite does and does not independently check in both the module
  docstring and the test file's module docstring (learning directly from stl-seas-100's
  round-1 finding rather than repeating it): Gate A's statsmodels oracle (every window
  of two 400-bar frames at lengths 50/100/101, plus a non-multiple-of-5 length 53) IS
  independent of `_build_ops`'s construction code (it compares against statsmodels'
  own `trend`/`resid`, not anything `_build_ops` produces); the hand-run fixed-point
  recursion is explicitly labelled as NOT independent (it calls the same
  `_seasonal_op`/`_loess_weights` `_build_ops` itself uses).
- Ran `tests/test_stl_trend_strength.py` standalone first: 29/29 passed on the first
  run (statsmodels present in this environment, so the oracle test actually executed,
  not merely skipped) — no iteration needed, unlike stl-seas-100's two fixed test bugs,
  because this port reused an already-debugged numerical core and only had to get the
  ratio and the wiring right.
- Wrote `docs/measure_stl_trend_strength.py` and `docs/measure_stl_trend_strength_cpu.py`
  (adapted from `stl_seasonal_strength`'s equivalents) and ran both to get every number
  in the Measured doc from actual tool output:
  - Gate A: max abs diff 1.15e-14..2.74e-14 across 7 (frame, length) combinations.
  - The drift case: measured, not assumed, that a noiseless drift fires with trend
    strength of exactly 1.0000 at display precision for every tested steepness
    (1e-2..1e-10) — the mathematically expected result for a residual near 0, but
    worth confirming numerically rather than asserting from the formula alone.
  - Gate B: 0/16 leaks for the real module, 16/16 caught for the chunk-write mutant.
  - Gate C: 501/600 bars fire on a 600-bar AR(1) synthetic frame, range
    [0.9093, 0.9958] — high, consistent with the known tsfeatures behaviour that a
    random walk's trend strength sits near 1.
  - Gate D: x8/x64 bit-identical; x10/x3.7 max abs diff 2.22e-16 (tighter than
    stl_seasonal_strength's 1e-10 on the same operators, still nowhere near the 1e-9
    tolerance either way); chunk-boundary noise 1.11e-16.
- Ran `python docs/measure_stl_trend_strength_cpu.py`: 29/29 passed with
  `AVX512F AVX512_SKX AVX2 FMA3` disabled.
- Updated `README.md` (headline 385->386, callable 393->394,
  `statistics (74)` -> `statistics (75)` with `stl_trend_strength` added),
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 385->386, new history entry
  prepended), and `docs/MLCompanionContract.md`'s running SF tally (730->731 tagged
  columns, 364->365 `SF`) by prepending a new history entry, matching the file's
  existing append-only convention.
- Ran `python docs/gen_indicator_dictionary.py` to regenerate
  `docs/IndicatorDictionary.md`: confirmed the new row auto-tags `STLTREND_100` as `SF`
  (scale-free), matching Decision 2's reasoning.
- Ran the full required test subset: `tests/test_stl_trend_strength.py
  tests/test_readme_counts.py tests/test_altport2_ports.py
  tests/test_wiring_accessors.py tests/test_ml_companions.py
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
  tests/test_prose_counts_match_the_csvs.py`: 1 expected failure
  (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, naming
  `stl_trend_strength` as the indicator owed a row), 1495 passed, 7 skipped.
- Wrote `docs/StlTrendStrengthMeasured.md` transcribing every number above from actual
  tool output, flagging Gate E as pending.

## Review round 1

VERDICT: PASS
FINDINGS: (none)
SUMMARY: Every claim in this port checks out against actual re-execution, not just
internal consistency. The ratio in `pandas_ta/statistics/stl_trend_strength.py:48`
(`1 - var_resid / var_trend_resid`) matches the issue's formula exactly, built from the
SAME trend/resid the shared `_build_ops` operators produce. The cross-module import
precedent (`sk_fcb_pos.py` importing `MIN_BARS, SPAN, _last_fractal` from
`sk_fcb_width.py`) is real, confirmed by grep, not invented. The port explicitly avoided
the sibling's round-1 mistake: its "independent of `_build_ops`'s construction code"
claim (`test_stl_trend_strength.py:19-28`, Measured.md Decision 1 and Gate A) is true as
written because the statsmodels oracle compares this module's output against
statsmodels' own `trend`/`resid` attributes directly, never against anything
`_build_ops` produces -- and the one check that IS dependent (the hand-run fixed-point
recursion) is correctly and explicitly labelled as not independent in both the test
docstring and the Measured doc, unlike the sibling's round-1 draft. Gate B's mutant
targets `lo = length - 1 + start` (`stl_trend_strength.py:50`), a line in this module's
own chunk-write logic, not inside the imported `_build_ops` -- so causality is tested on
the module under review, not laundered through code that can't leak. Re-ran
`python docs/measure_stl_trend_strength.py` and every number (Gate A max diffs
1.15e-14..2.74e-14, Gate B 0/16 and 16/16, Gate C 501/600 range [0.9093, 0.9958], Gate D
bit-identical x8/x64 and 2.22e-16 at x10/x3.7, chunk noise 1.11e-16, the drift-fires-at-
1.0000 table) matches `docs/StlTrendStrengthMeasured.md` verbatim -- nothing invented or
copy-pasted unchanged from the sibling's different ratio. The required test subset ran
1 failed / 1495 passed / 7 skipped, the failure naming `stl_trend_strength` as
Gate-E-owed exactly as documented, and the CPU-variant script passed 29/29 with
AVX-512/AVX2/FMA3 disabled. The 3 wiring touch points are alphabetically correct and
forward `length`/`offset` under the right keyword names, confirmed by
`test_wiring_accessors.py` passing. Every counter (README 385->386/393->394/74->75,
`CATEGORY_TOTAL` 385->386, MLCompanionContract 730->731 tagged / 364->365 SF)
arithmetically follows the previous committed value, not just an internally-consistent
new number. `docs/IndicatorDictionary.md`'s diff is the expected mechanical one, with
`stl_trend_strength` tagged `SF`. Scope is clean: no edits to `stl_seasonal_strength.py`,
its test, or its Measured doc; no Gate E ledger write; no whole-suite run claimed
anywhere.

## Outcome
PASS (round 1)
