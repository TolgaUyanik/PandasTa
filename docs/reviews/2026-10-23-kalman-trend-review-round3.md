# Brutally Honest Review — kalman_trend port, round 3

**Date:** 2026-10-23
**Target:** the round-2 fixes. Files: `pandas_ta/overlap/kalman_trend.py`, `pandas_ta/core.py` (`_indicators_by_category`), `tests/test_kalman_trend.py`, `tests/test_wiring_accessors.py`, `tests/test_altport2_ports.py`, `docs/KalmanTrendMeasured.md`
**Type:** code
**Verdict:** PASS
**Scope note:** Gate E, Gate C real-data counts and CLAUDE.md were excluded by the owner.

## Findings

### MINOR
- **kalman_trend.py docstring Args; KalmanTrendMeasured.md:22; tests** — The docs blamed non-convergence only on "a q_slope too small (e.g. 1e-12)". In fact any pair whose Riccati recursion needs more than 5000 steps raises. That is q_slope small relative to q_level: (0.01, 1e-8), (2, 1e-5) and (30, 1e-4) all raise, and they genuinely converge slowly (for example 7330 steps, warm-up 10090), so raising is correct.
  - Fix: Reword the docs to describe that domain. Add `{"q_slope": 1e-8}` and `{"q_level": 30}` to `test_bad_parameters_raise`. **Applied.**

### NIT
- **kalman_trend.py `_props`** — With `.12g`, a numpy float32 parameter leaks its rounding into the column name: `np.float32(1e-4)` names as `9.99999974738e-05`. Every documented or tested pair names the same as it did under `:g`.
  - Fix: A one-line docstring note to pass Python floats. **Applied.**
- **kalman_trend.py:43** — `q_slope == 0` was compared before `float()`, so `"0"` raised while `0` fell back to the default.
  - Fix: Convert first, then apply `or 0.0001`. **Applied.** After the change, `0`, `0.0`, `-0.0`, `np.float64(0)`, `"0"` and `None` all name as `_0.01_0.0001`.

## Round-2 findings

Everything is fixed and verified by the reviewer. Riccati non-convergence now raises; `lru_cache` does not cache exceptions, and the defaults never raise inside `strategy()`. The Gate C wording is fixed. The 1e-8 justification now quotes the measured 4.0e-7 and 120 vs 112. Bad parameters raise. Names use `.12g`, pinned by a test. The test docstring carries the measured values. The altport2 comment is updated. On the `Category` mutation, the reviewer simulated the old behaviour and the new assertion catches it on trend and momentum. `_indicators_by_category` has exactly one caller.

**Reverted after this review, at the owner's request:** the `core.py` `_indicators_by_category` copy fix and its `test_wiring_accessors.py` assertion are an existing upstream bug unrelated to this port. They are deferred to a separate fix off `main`. Nothing else in this review depends on them.

## Summary

Every round-2 fix is real, and every number in the edited docs matches a fresh run. The only remaining gap was wording about which parameters fail to converge, and it is fixed. After the round-3 fixes: `tests/test_kalman_trend.py` passes 32/32. The full suite gives 2 failed (both already failing before this port: the pine_coverage_csv evidence test and the wilder_rma `natr` 1-ulp test) / 3159 passed / 85 skipped / 1 error caused by the sandbox `tmp_path` setup.

**Not checked (owner's call):** whether a 5000-step cap suits long intraday series that would legitimately want warm-ups of 8k to 18k bars.
