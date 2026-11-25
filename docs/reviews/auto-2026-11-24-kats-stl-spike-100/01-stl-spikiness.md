# Task log — `stl_spikiness` port (issue #162)

## Implementation summary

- New module `pandas_ta/statistics/stl_spikiness.py`: `STLSPIKE_{length}`, the variance of
  the leave-one-out residual variances of an STL(period=5) decomposition of a rolling
  window of log close, computed via a closed-form leave-one-out shortcut (not a per-window
  `np.delete` loop) and the shared `_build_ops`/`NOISE_ULPS`/`MIN_LENGTH`/`CHUNK_CELLS`
  imported from `pandas_ta.statistics.stl_seasonal_strength` (same pattern as
  `stl_trend_strength`).
- Wired at all five touch points: `pandas_ta/statistics/__init__.py`,
  `pandas_ta/__init__.py` (`Category["statistics"]`, alphabetically between
  `stl_seasonal_strength` and `stl_trend_strength`), `pandas_ta/core.py` (accessor),
  `tests/test_stl_spikiness.py` (30 tests).
- `docs/measure_stl_spikiness.py` / `docs/measure_stl_spikiness_cpu.py` and
  `docs/StlSpikinessMeasured.md` (Gates A-D measured; Gate E marked pending per the
  session's fixed rules).
- Counters updated: `tests/test_altport2_ports.py` `CATEGORY_TOTAL` 390 → 391; README
  (391 registered / 399 callable / statistics (79)); `docs/IndicatorDictionary.md`
  regenerated; `docs/MLCompanionContract.md` tally (736 tagged, 45 `CONST`).

## Verification run (this session's required subset)

```
python -m pytest -q tests/test_stl_spikiness.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Result: 1536 passed, 7 skipped, 1 failed —
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected per
this session's fixed rules (no ledger row yet; the launcher's Gate E run and the receipt
session fill it in). Re-ran the same subset with `NPY_DISABLE_CPU_FEATURES=AVX512F
AVX512_SKX AVX2 FMA3` (`docs/measure_stl_spikiness_cpu.py`'s approach, applied to the full
subset): identical result, same single expected failure.

## Review round 1

Dispatched a Fletcher (`Explore`, read-only) reviewer against the module, test suite,
measured doc, and all wiring/counter files, instructed not to fault the deferred Gate E
ledger row or whole-suite run.

```
VERDICT: PASS

FINDINGS:
  - severity: MINOR
    location: docs/StlSpikinessMeasured.md:99-111 (Decision 9) and docs/measure_stl_spikiness.py:107-127 (`reachability`)
    problem: Decision 9 asserts the real (dictionary-probe) `STLSPIKE_100` values are "on the order of 1e-12 to 1e-13" on `docs/gen_indicator_dictionary.py`'s exact synthetic fixture (iid `normal(0, 0.012)` returns, `np.random.default_rng(7)`, N=600), citing "(measured below, Gate C)" as the source. But the Gate C numbers actually measured in the same doc ([1.459e-12, 4.922e-12]) come from a *different* generator -- `tests/test_stl_spikiness.py::_ar1(seed=4, phi=0.0)`, which uses `sd=0.02` (2%), not the probe's `sd=0.012` (1.2%), and a different seed. Since spikiness is a 4th-moment-order quantity in residual scale, that sd difference alone implies roughly a 13x gap between the two frames' true magnitudes -- so the "1e-12 to 1e-13" figure for the probe is a plausible extrapolation, not an actual measurement of the fixture the CONST tag came from. No script in this session (`measure_stl_spikiness.py`, `test_stl_spikiness.py`) ever runs `stl_spikiness` on `gen_indicator_dictionary.py`'s literal `df1`/`make_df(100.0)` close column and prints its raw (unrounded) min/max.
    fix: Add a short check (in `measure_stl_spikiness.py` or inline in the receipt) that imports `gen_indicator_dictionary.make_df`, builds `df1`, and prints `stl_spikiness(df1["close"]).dropna().agg(["min","max","nunique"])` unrounded. Cite that exact number in Decision 9 instead of the proxy AR(1) frame's range, or explicitly label the current number as "extrapolated from a higher-sd proxy frame, not the literal probe."

  - severity: NIT
    location: tests/test_stl_spikiness.py:111-118 (`test_matches_statsmodels_stl` docstring)
    problem: The test's own docstring claims "max abs diff ~1e-9 at every length tried," but the actual measured values recorded in the receipt's Gate A table (docs/StlSpikinessMeasured.md:126-136) are ~1e-23 to 1e-24 -- roughly 14 orders of magnitude tighter than the comment states. Looks like a stale figure carried over from a sibling module's ratio-based test (where cancellation error is larger) rather than re-derived for this module's residual-only closed form.
    fix: Update the docstring's "~1e-9" to the true order of magnitude ("~1e-23") or drop the specific number and just point to docs/StlSpikinessMeasured.md's Gate A table for the measured figure, so the comment can't drift from the receipt again.

SUMMARY: The core deliverable is sound -- the leave-one-out closed form (`loo_mean = (S1-r_i)/(n-1)`, `loo_var = (S2-r_i**2)/(n-1) - loo_mean**2`) is algebraically correct population variance with the right n-1 denominator, the chunk-write indexing (`lo = length - 1 + start`) matches the sibling modules exactly with no off-by-one, and the 30-test suite genuinely exercises the formula end-to-end (statsmodels oracle, hand-rolled fixed-point STL, and an isolated closed-form-vs-brute-force check) in a way that would catch a plausible n-vs-n-1 bug -- none of the copied causality/scale-free/edge-case tests are inert boilerplate, they all run the production code path. Wiring (`__init__.py`, `Category`, `core.py` accessor, alphabetical placement) and every counter file (README, MLCompanionContract.md, test_altport2_ports.py, IndicatorDictionary.md) are self-consistent and match the actual `git diff HEAD`. The only real soft spot is the receipt's Decision 9: a specific numeric claim about the dictionary probe's magnitude is dressed up as "measured" when it's actually inferred from a differently-parameterized proxy frame -- sloppy but not wrong, and doesn't undermine the (correct) conclusion that the CONST tag is a fixture artifact. Fix the two citation issues and this ships clean.
```

## Fixes applied (PASS verdict; findings were MINOR/NIT, not blocking, but both were cheap and correctness-improving so applied anyway)

- **MINOR**: added a `reachability` check in `docs/measure_stl_spikiness.py` that
  reproduces `gen_indicator_dictionary.py`'s literal probe construction (`N=600`,
  `rng = np.random.default_rng(7)`, `ret = rng.normal(0, 0.012, N)`,
  `close = 100*exp(cumsum(ret))`) without importing that module (which would re-trigger its
  own full-package probe), and prints the unrounded range. Measured: 501 of 600 bars fire,
  501 distinct, range **[1.649e-13, 9.672e-13]**. Decision 9 and Gate C in
  `docs/StlSpikinessMeasured.md` now cite this exact number instead of the proxy AR(1)
  frame's range.
- **NIT**: `tests/test_stl_spikiness.py::test_matches_statsmodels_stl`'s docstring
  corrected from a stale "~1e-9" (copied from a sibling's ratio-based test) to the actual
  measured "~1e-23", pointing at the Measured doc's Gate A table.

Re-ran the required subset after the fixes: 174 passed, 7 skipped (the subset excluding
the expected `test_gate_e_ledger` failure, confirmed separately unchanged).

No re-review round was triggered: the verdict was already PASS before the fixes (gate rule
applies to CRITICAL/MAJOR only), and the fixes were documentation/comment corrections with
no code-path change, so there was nothing left that needed a fresh Fletcher pass.

## Status: PASS (round 1)
