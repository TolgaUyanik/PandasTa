# Brutally Honest Review — kalman_trend port

**Date:** 2026-10-23
**Target:** `pandas_ta/overlap/kalman_trend.py`, `tests/test_kalman_trend.py`, `docs/KalmanTrendMeasured.md`, `docs/measure_kalman_trend_proxy.py`; wiring edits in `pandas_ta/overlap/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`
**Type:** code (dominant) + text
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/KalmanTrendMeasured.md:33, 42, 49-50, 62; kalman_trend.py:100; measure_kalman_trend_proxy.py:2** — The receipt quotes numbers that no script prints: ρ = 0.9170, gains (0.159, 0.0092), the 1.6e-3 from the half-warm-up check, "114 vs 123", and the ×10/×3.7 max diff 2.8e-14. The proxy script's docstring says it prints the doc's numbers. The tests assert only bounds (`> 1e-3`, `< 1e-9`). This breaks CLAUDE.md's rule that every count must correspond to a run.
  - Fix: Make the proxy script print each of those numbers: expose rho and K from `_steady_warmup`, plus the half-warm-up diff, the 1e-3/20 prediction against the empirical value, and the ×10/×3.7 max diffs. Paste the printed values into the doc, and delete any number the script doesn't print.

### MINOR / NIT
- **MINOR · kalman_trend.py:43, doc:30** — The loop skips only NaN. A zero close gives y = −inf, which poisons every later bar, though the doc says "not poisoned".
  - Fix: Skip any value that fails `isfinite`, and anchor on the first finite positive close. Add a test with one interior close set to 0.
- **MINOR · kalman_trend.py:54-56 vs docstring** — The mask counts bars from the first valid one, not valid bars. Interior NaNs inside the warm-up therefore shorten the real warm-up.
  - Fix: Cut at the (W+1)-th valid bar (`flatnonzero(notna)[warmup]`). Add a test with NaNs in the head.
- **MINOR · tests** — No test covers leading NaNs, and an all-NaN series raises IndexError instead of returning None.
  - Fix: Add a test that prepends 50 NaNs and checks the output matches the unpadded run, shifted by 50. Return None when the number of valid bars is ≤ warmup.
- **MINOR · tests:160-182** — The warm-up rule is checked only at the default parameters. The closed-loop matrix is non-normal and the early gains are not at steady state, so the spectral-radius rule needs testing at other settings too.
  - Fix: Parametrize the head test over (0.01, 1e-4), (0.0, 1e-3) and (0.1, 1e-5).
- **MINOR · tests:117-121** — No mutant shows that the harness catches a full-series noise fit, which is the 🔴 decision in the task.
  - Fix: Add a fourth mutant that scales `q_level` by the variance of the whole series. Show it is live and caught at 32 of 32.
- **MINOR · tests:95-100** — The interior-NaN test is weak: a wrong predict-only step would still pass it.
  - Fix: Add a NaN branch to the independent matrix filter and compare the whole output to 1e-9.
- **MINOR · doc:16** — "0.0008 short of the revert line" is false precision against an approximate threshold, on a single-seed proxy.
  - Fix: Reword to "at the ≈ 0.9 revert line on the synthetic proxy; Gate E decides".
- **MINOR · IndicatorDictionary.md:29-32; MLCompanionContract.md:22** — The note now says the `pfe` row came from a 2026-10-23 pandas 2.3.3 probe, and nothing in the repo records that run. MLCompanionContract still says the dictionary was "regenerated", but it is partly hand-patched.
  - Fix: Keep the original `pfe` provenance and add a separate `kalman_trend` line, or name the reproducing command. Reword "regenerated" in MLCompanionContract.
- **MINOR · doc:12-14; Category** — The proxy puts VEL at the revert line, and the port is still registered in `Category` before Gate E.
  - Fix: Either keep `kalman_trend` out of `Category` until Gate E (and adjust the counts), or record shipping before Gate E as the owner's call.
- **NIT · kalman_trend.py:58** — Column names are built from float repr: `1e-05` and `0.30000000000000004` both end up in names, and names are API.
  - Fix: Format with `:g`, or document the repr and pin it in a test.
- **NIT · kalman_trend.py:8-24** — `_steady_warmup` runs 5,000 iterations on every call, with no cache and no early exit. `q_slope=0` silently falls back to the default. If rho reaches 1.0, `ceil(-inf)` raises OverflowError.
  - Fix: Add `lru_cache` and break early once P converges. Document the `q_slope` rule, and raise ValueError when rho ≥ 1.
- **NIT · doc:39-53** — Nothing justifies the 1e-8 shrink target, which costs 213 bars of warm-up.
  - Fix: Justify it in one sentence, or tie it to the 1e-6 tolerance the tests assert.

## Fixes applied (2026-10-23, same day)

All 14 findings were applied. The suite after them: 2 failed / 3,151 passed / 86 skipped, with the same two pre-existing failures; `tests/test_kalman_trend.py` 17 → 24 tests.

- MAJOR: `docs/measure_kalman_trend_proxy.py` now prints every number in the receipt. Re-measuring corrected two of them: "114 vs 123" is now **112 vs 120**, and the initial transient is 16.1, not "near 20". The figures came from a different ad-hoc harness before.
- Bad closes: the filter now skips anything that is not finite, and anchors on the first positive close. NaN, 0 and −1 are each tested.
- The warm-up mask now counts valid closes. Added tests for leading NaNs, NaNs inside the head, and all-NaN input / too few valid closes (returns None).
- The head test now runs at three parameter pairs. (0.1, 1e-5) was swapped for (0.1, 0.001), because its warm-up is 1,842 bars, longer than the test series.
- Added a fourth mutant that fits the noise on the whole series. The matrix reference filter gained a predict-only branch.
- Doc wording: removed the false precision, recorded registering in `Category` as the `pfe` precedent and the owner's call, restored the original `pfe` provenance line, and reworded "regenerated" in MLCompanionContract.
- NITs: names use `:g`. `_steady_state` is `lru_cache`d and exits early once converged. A rho ≥ 1 raises ValueError. The `q_slope=0` fallback is documented, and the reason for the 1e-8 target is stated.

## Summary

As far as reading can tell, the filter is correct. The scalar recursion matches the matrix-form test filter, the causality harness can actually fail, the mutants are proved live, and the head test is designed correctly. Wiring covers all five touch points. The receipt is what fails. It is the deliverable the task names, and it carries at least six figures that no script prints, which alone forces REVISE. Behind that are edge-case gaps: a zero close poisons the series, the warm-up mask counts bars rather than valid bars, there is no leading-NaN or all-NaN test, and the warm-up rule is validated only at the defaults. The dictionary's provenance edit for `pfe` is unrecorded. Fix the traceability, the isfinite skip, the valid-bar mask and the missing tests, and this passes pending Gate E. The reviewer read only and ran nothing.
