# Brutally Honest Review — kalman_trend port, round 2

**Date:** 2026-10-23
**Target:** `pandas_ta/overlap/kalman_trend.py`, `tests/test_kalman_trend.py`, `docs/KalmanTrendMeasured.md`, `docs/measure_kalman_trend_proxy.py`; wiring edits in `pandas_ta/overlap/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`
**Type:** code (dominant) + text
**Verdict:** PASS
**Scope note:** The user excluded Gate E (Spearman attribution). It is not reviewed here.

## Findings

### MINOR
- **pandas_ta/overlap/kalman_trend.py:15-22 (`_steady_state`)** — The Riccati loop stops at 5000 iterations and returns an unconverged K and rho without saying so. At (0.01, 1e-12) it runs out with rho 0.999799, against a true value of about 0.999990. The warm-up mask comes out far too short (it emits from bar about 91,650, while the transient needs about 1.8M bars), and no test sees the resulting head. Every documented parameter pair converges early (193 to 1390 iterations).
  - Fix: Add `for ... else: raise ValueError(...)` for non-convergence, or put a lower bound on q_slope. Add a test that q_slope=1e-12 raises.
- **docs/KalmanTrendMeasured.md:10-12, Gates table row C** — The Gate C counts are synthetic only, but the merge-blocker sentence names only Gate E.
  - Fix: Reword it to "Do not merge to `main` before Gates C (real-data counts) and E". Have the overlap script print the per-column counts on the BIST cache and paste them into row C.

### NIT
- **kalman_trend.py:26-28; KalmanTrendMeasured.md:49-50** — The justification for the 1e-8 target predicts about 2e-7 (code) or about 1.6e-7 (doc). The measured worst case is 4.0e-7, and the decay is slower than rho predicts (120 bars against 112).
  - Fix: Quote the measured 4.0e-7 and the 120 vs 112 bars in both places. Drop the predicted figures.
- **kalman_trend.py:38-39** — A negative or NaN `q_level`, or a negative `q_slope`, silently falls back to the defaults, and the columns get default names.
  - Fix: Raise ValueError for a negative or non-finite parameter. Keep `None` meaning the default, and keep the documented `q_slope=0` fallback.
- **kalman_trend.py:76** — `:g` keeps only 6 significant digits, so `0.01000001` produces the same column name as `0.01`. Column names are API.
  - Fix: Use `.12g`, or reject parameters with more than 6 significant digits. Pin one such case in a test.
- **tests/test_kalman_trend.py:2-41** — The docstring gives the test bounds but not the measured values.
  - Fix: Put each measured value next to its bound, e.g. "1e-6 (measured worst 4.0e-7)", "> 1e-3 (measured 1.6e-3)", "1e-9 (measured 2.8e-14)", and give the warm-ups 213 / 147 / 174.
- **tests/test_altport2_ports.py:159-164** — The count-history comment stops at 233, but the pin is now 235.
  - Fix: Append "-> 234 by pfe, -> 235 by kalman_trend (both Gate E pending; revert with the port)".
- **tests/test_wiring_accessors.py (existing code, not in this diff)** — This test changes `Category` in place. When it runs before `tests/test_readme_counts.py`, 3 README count tests fail.
  - Fix: Copy `Category`, or use `monkeypatch.setitem`, instead of changing the module global.

## Round-1 findings

All of them are fixed except one. Every number in the receipt was re-run through `docs/measure_kalman_trend_proxy.py` and matched line by line, apart from Gate F, which the doc says is hand-reported. The fixes for a zero or inf close, warm-up counting of valid bars, leading/all-NaN handling, the head test across parameter pairs, the full-series-fit mutant (caught 32/32), the stronger interior-NaN check, the "0.0008" wording and the pfe provenance were all verified. The `_steady_warmup` NIT is only partly fixed: nothing catches the silent stop at the iteration cap (it became the new MINOR above).

## Summary

The round-1 MAJOR is fixed: every number in the receipt now comes from a script, and the script's output matches the doc. The filter matches an independent matrix-form reference to 1e-9, including predict-only bars. Causality holds: no leaks, and four live mutants are each caught. ×8/×64 is bit-identical. All five touch points are wired, and the counts agree with a fresh regeneration. `tests/test_kalman_trend.py` passes 24/24. What is left is small. The Riccati solver can silently return an unconverged rho for a tiny q_slope. The Gate C merge-blocker wording leaves Gate C out. Invalid parameters fall back to the defaults instead of raising. The 1e-8 justification quotes a prediction 2.5× below the measured error. With Gate E set aside, as instructed, this passes.

**Reviewer did not check:** the claim that the pandas 2.3.3 venv has no TA-Lib, and whether the RAG-scan sources match the formulas. The full suite ran with `-p no:tmpdir` because of the sandbox. Result: 2 failed (the same two), 3151 passed, 85 skipped, and 1 error caused by the sandbox setup.
