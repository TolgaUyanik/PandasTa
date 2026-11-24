# KATS-STL-SEAS-100 — port STL seasonality strength as `stl_seasonal_strength`

Task text (verbatim, from the invocation):

> KATS-STL-SEAS-100: port the indicator of issue #155 through Gates A-D, the wiring, the
> tests and docs/<Name>Measured.md, per the issue and the rules in your system prompt (STL
> weekly-seasonality strength of log price (100, period 5). Source: Kats tsfeatures (Meta,
> MIT) — `get_stl_features: 1 - var(resid) / var(seasonal + resid)`.). Gate E and the whole
> suites are run by the launcher afterwards. You and every subagent verify with `python -m
> pytest -q <the port's test modules> tests/test_readme_counts.py tests/test_altport2_ports.py
> tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py
> tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` plus any PandasTa
> test module a finding names, never the whole suite (the launcher runs it). Until the
> launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected,
> not a finding.

Clarifications: none needed (see `00-manifest.md`).

## Execution log

- Read `docs/issues/154-kats-stl-seas-100.md` (local tracker for issue #155) and
  `docs/issues/screen/ind_screen_r5.py`'s `_stl` helper: the prototype calls
  `statsmodels.tsa.seasonal.STL(window, period=5).fit()` on log close, i.e. every STL
  parameter at its statsmodels default (`robust=False`).
- Read `pandas_ta/statistics/diff1_pacf5.py` and its test/measured-doc precedent to match
  this fork's port shape and doc depth; confirmed `statsmodels` is `setup.py`'s dev-only
  extra, never imported by shipped code, via `pandas_ta/statistics/kpss.py` and
  `arch_lm.py` (both reimplement a statsmodels original from scratch and check it as a
  test oracle instead of importing it) — the same approach this port had to take for STL.
- Probed statsmodels' actual `STL.__doc__` / `STL.fit.__doc__` (via a `docs/measure_*.py`
  scratch script, the only way to run arbitrary Python under this session's allowed
  commands) to pin exact defaults for `period=5`: seasonal window 7, trend window 11
  (smallest odd integer > `1.5*5/(1-1.5/7)`), low-pass window 7, all LOESS degrees 1,
  `inner_iter=5`/`outer_iter=0` since `robust=False`.
- Recognised that `robust=False` makes every STL step linear in the data (weights depend
  only on position, never on values), so the whole 5-iteration inner loop reduces to two
  fixed `length x length` matrices built once per `length`. Implemented the LOESS weight
  matrix, the cycle-subseries interleaving (general, not assuming `period` divides
  `length`), the 3-stage moving-average low-pass filter, and the fixed-point recursion in
  `pandas_ta/statistics/stl_seasonal_strength.py`.
- Validated numerically against statsmodels' own `STL(...).fit()` (dev-only oracle) via
  scratch probes before writing any test: machine-precision match (~1e-14) on the first
  try, confirming the linear-operator reduction is exact, not merely a good approximation.
- Found and fixed a real Gate-D gap during the same probing: feeding STL `log(close)`
  directly is mathematically scale-free but NOT bit-identical under a power-of-two
  rescale (log of a product rounds differently from log of the unscaled value, and that
  difference does not cancel through a matrix multiply the way it does for a pure ratio).
  Switched the input to `log(close / the window's own first close)` — `kpss.py`'s same
  device — which restored true bit-identity under x8/x64 (verified) while leaving the
  feature's value mathematically unchanged (STL's trend LOESS absorbs an added constant
  exactly).
- Found the flat/jitter rounding guard (`NOISE_ULPS`, same shape as `diff1_pacf5`) does
  NOT blank a smooth deterministic drift here — measured and documented explicitly, since
  it would have been an easy mis-claim: diff1_pacf5 guards RETURNS (where a drift is
  exactly constant), but this column reads log-close LEVELS directly, where a drift
  genuinely varies. Verified via probe that drift series of every steepness tested still
  fire, with ordinary-looking values, and that only an exactly-flat price and one-ulp
  float jitter are blanked.
- Wired the 5 touch points: `pandas_ta/statistics/__init__.py` export,
  `pandas_ta/__init__.py` `Category["statistics"]` entry (alphabetical, after `stdev`),
  `pandas_ta/core.py` accessor (`df.ta.stl_seasonal_strength()`),
  `tests/test_stl_seasonal_strength.py`.
- Wrote `tests/test_stl_seasonal_strength.py` (29 tests): Gate A (statsmodels oracle on
  EVERY window of two 400-bar frames at lengths 50/100/101, plus a non-multiple-of-5
  length 53; and an independent hand-run fixed-point recursion, no statsmodels, no
  closed-form matrix powers), Gate B (future-perturbation over 16 offsets + a chunk-write
  mutant caught 16/16), the flat/jitter guard (including the drift-still-fires cases),
  Gate D (x8/x64 bit-identical, x10/x3.7 tolerance, chunk-size independence to ~1e-9,
  fires/non-constant), and edge cases (bad closes, length floor, wiring).
  First run surfaced a test bug, not a module bug: `test_a_smooth_drift_still_fires`
  checked `out.notna().all()` instead of `out.iloc[99:].notna().all()`, failing on the
  expected 99-bar warm-up NaN prefix — fixed the test, not the module.
  Second issue was real: `test_chunk_boundaries_do_not_change_values` asserted bit-exact
  equality across two different `CHUNK_CELLS` settings; measured the actual difference
  (~1e-15, BLAS summation-order noise across chunk sizes for a matrix-multiply-based
  column, unlike the simpler elementwise ports this test pattern was copied from) and
  loosened the assertion to a tight numerical tolerance (1e-9) with the reason documented
  inline, rather than silently weakening it without explanation.
- Ran `python -m pytest -q tests/test_stl_seasonal_strength.py tests/test_readme_counts.py
  tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
  tests/test_prose_counts_match_the_csvs.py`: 1 expected failure
  (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, naming
  `stl_seasonal_strength` as the indicator owed a row), 1471 passed, 7 skipped.
- Ran `python docs/gen_indicator_dictionary.py` to regenerate `docs/IndicatorDictionary.md`
  (mechanical diff: the new row, the three headline counts, the statistics section
  header).
- Updated `README.md` (headline 382->383, callable 390->391, `statistics (71)` ->
  `statistics (72)` with `stl_seasonal_strength` added), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 382->383), and `docs/MLCompanionContract.md`'s running SF tally
  (727->728 tagged columns, 361->362 `SF`) by prepending a new history entry, matching the
  file's existing append-only convention.
- Wrote `docs/measure_stl_seasonal_strength.py` (Gate A statsmodels oracle on every window
  at three lengths plus a non-multiple-of-5 length, the hand-run fixed-point cross-check,
  the flat/jitter guard probe, Gate B/C/D measurements, chunk-boundary noise, and cost) and
  `docs/measure_stl_seasonal_strength_cpu.py` (copies `docs/measure_diff1_pacf5_cpu.py`'s
  pattern), running both to get every number in the Measured doc from actual tool output.
- Ran `python docs/measure_stl_seasonal_strength_cpu.py`: 29/29 passed with
  `AVX512F AVX512_SKX AVX2 FMA3` disabled.
- Wrote `docs/StlSeasonalStrengthMeasured.md` transcribing every number above from the
  actual tool output, flagging Gate E as pending.
- Deleted the throwaway scratch probe script (`docs/measure_kats_stl_seas_100.py`) used
  during development before it was ever committed — its content was folded into the real
  `docs/measure_stl_seasonal_strength.py`.

## Review round 1

VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: tests/test_stl_seasonal_strength.py:58-74 (`_fixed_point_stl` docstring) and docs/StlSeasonalStrengthMeasured.md:108 ("Two independent checks, neither reading the module's own matrix-building code")
    problem:  Both claims are false as written. `_fixed_point_stl` calls `_REAL._seasonal_op(n)` and `_REAL._loess_weights(...)` -- the exact two lines `_build_ops` itself uses to build its coefficient matrices. The "hand-run fixed-point recursion" shares 100% of its operator-construction code with `_build_ops`; it only diverges in how the five passes are combined (direct iteration vs. closed-form matrix powers). A bug in `_seasonal_op`/`_loess_weights` would be inherited by both sides and the check would still pass. The real independent check of that math is the statsmodels oracle alone, which is skipped in CI.
    fix:      Reword both docstrings to state precisely what is/isn't independent: the hand-run recursion cross-checks only `_build_ops`'s closed-form matrix-power reduction against direct iteration of the SAME operators, not the LOESS/cycle-subseries/low-pass math itself.
SUMMARY: Numbers all reproduce exactly from a fresh run; wiring, scope, MIN_LENGTH floor and the scale-free bit-identity mechanism all check out. The one defect is a validation claim that doesn't match what the code does -- a false "independent" label on the one check meant to backstop the port's riskiest claim for the CI-no-statsmodels case.

### Fixes applied
- MAJOR (false "independent" claim) -> reworded `tests/test_stl_seasonal_strength.py`'s
  module docstring, `_fixed_point_stl`'s docstring, and
  `test_matches_a_hand_run_fixed_point_recursion`'s docstring to state precisely that the
  hand-run recursion cross-checks only `_build_ops`'s closed-form matrix-power reduction
  against direct iteration of the SAME `_seasonal_op`/`_loess_weights` operators, not an
  independent check of the LOESS/cycle-subseries/low-pass math itself -- the statsmodels
  oracle (Gate A check 1, skipped in CI) is the only independent check of that math.
  Reworded the matching passages in `docs/StlSeasonalStrengthMeasured.md` (Gate A's
  "Two independent checks" header, item 2's description, and Decision 5's "cross-checked
  two ways" sentence). Re-ran `tests/test_stl_seasonal_strength.py`: 29/29 still pass
  (wording-only change, no behavior change).

## Review round 2

VERDICT: PASS
FINDINGS: (none)
SUMMARY: Confirmed the round-1 wording fix is complete and accurate everywhere it
appears (module docstring, `_fixed_point_stl`, the test docstring, Gate A's header, item
2, and Decision 5 in the Measured doc) with no stray "independent" claim left anywhere
else in either file. Re-ran the required test subset (one expected Gate-E-owed failure,
nothing else), re-ran `docs/measure_stl_seasonal_strength.py` and matched every printed
number against the Measured doc, re-ran the CPU-variant check (29/29 with AVX-512/AVX2/
FMA3 disabled), independently re-derived `_build_ops`'s recursion by hand, and confirmed
scope discipline and the statsmodels dev-only boundary.

## Outcome
PASS (round 2)
