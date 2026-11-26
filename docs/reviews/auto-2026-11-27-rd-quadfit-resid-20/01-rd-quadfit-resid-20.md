# RD-QUADFIT-RESID-20 — port `rd_quadfit_resid_20`

Issue #180. Port the indicator through Gates A-D, the wiring, the tests and
`docs/RdQuadfitResid20Measured.md`. Gate E and the whole suites are deferred
to the launcher (this session's system-prompt override); Gate F here is
limited to the named test subset, never the whole suite.

## Execution log

- Read the prototype (`docs/issues/screen/ind_screen_r6.py`'s
  `_quad_resid`/`rd_quadfit_resid_20`) and the two closest structural
  precedents from the same prototype function family already ported:
  `pandas_ta/statistics/rd_knot_pos_40.py` (per-window OLS projection-matrix
  trick, intercept-invariance scale-free argument) and
  `pandas_ta/statistics/rd_std_ratio_20_60.py` (a sibling Reddit tier-4 port,
  same Gate E deferral convention).
- Derived Gate A independently from the issue's own words (quadratic
  `y = a + b*t + c*t^2` OLS fit over the trailing window, residual =
  observed - predicted at the last bar, divided by the window's own
  residual sd), not by reading the prototype's `_quad_resid` pinv code,
  though the two are mathematically equivalent. Resolved the residual-sd
  estimator (ddof=0) and the category (`statistics`) as ASSUMPTIONs, logged
  in `00-manifest.md`.
- Wrote `pandas_ta/statistics/rd_quadfit_resid_20.py`: `_quad_basis` builds
  the (length, length) residual-maker once per call (pure function of
  `length`), `_quad_resid` applies it to every causal 20-bar-by-default
  window via `sliding_window_view`, masking any window holding a
  non-finite value to NaN, and masking any window whose residual sd is
  exactly zero (a perfect fit) rather than returning `0/0`.
- Wired all five touch points (module, `pandas_ta/statistics/__init__.py`,
  `Category` in `pandas_ta/__init__.py`, the `core.py` accessor,
  `tests/test_rd_quadfit_resid_20.py`), alphabetically between
  `rd_knot_pos_40` and `skew`/`rolling_sum`.
- Wrote 20 tests: a hand-derived fixture (length=4, exploiting that the
  quadratic residual-maker for 4 equally spaced points is exactly the
  classic orthogonal cubic contrast `(-1,3,-3,1)`, giving an exact
  `1/sqrt(5)` answer computed on paper before the module ran), an
  independent-loop cross-check (`np.linalg.lstsq` per window, not read from
  the module), length-too-small raises, non-finite-window NaN case,
  warm-up, offset/fillna, causality (future-splice sweep + look-ahead
  mutant), scale-free (x8/x64/x10/x3.7), reachability, wiring.
- **Mid-session finding, not assumed going in:** ran
  `docs/measure_rd_quadfit_resid_20.py` and discovered the x8/x64
  power-of-two rescale is NOT bit-identical (0 of 1,581 co-finite cells),
  unlike `rd_knot_pos_40` (argmin, robust to ulp noise) and
  `rd_std_ratio_20_60` (no `log`, exact cancellation through
  sum-of-squared-deviations). Root cause: this port's intercept-invariance
  argument is exact only in real-number arithmetic — `np.log` of a
  power-of-two-rescaled `close` is not itself bit-preserving the way an
  exact multiply or a correctly-rounded `sqrt` of an exact square is.
  Corrected the module docstring, both scale tests, and the receipt to
  state "measured NOT bit-identical, tight relative tolerance (~5e-9), same
  order of magnitude as the non-power-of-two case" instead of claiming
  bit-identity — rather than leaving an unmeasured claim standing.
- Wrote `docs/measure_rd_quadfit_resid_20.py` and ran it; every number in
  `docs/RdQuadfitResid20Measured.md` is copied from that run's actual
  output: hand fixture `0.4472135954999547` (matches `1/sqrt(5) =
  0.4472135954999579` to 3.2e-15); independent-loop cross-check max |diff|
  1.807e-12 over 261 defined bars; fires 1,581/1,600, min -2.6635, max
  2.5259, 1,581 distinct values; real module 0/28 leaks, mutant 28/28;
  x8/x64/x10/x3.7 all 0 of 1,581 bit-identical but max relative diff
  ~1.6e-9 to 5.1e-9 across all four.
- Wrote `docs/measure_rd_quadfit_resid_20_cpu.py`
  (`NPY_DISABLE_CPU_FEATURES = "AVX512F AVX512_SKX AVX2 FMA3"`) and ran it:
  20 passed.
- Updated `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 414 -> 415),
  `README.md` (414 -> 415 registered, 422 -> 423 callable, statistics
  (83) -> (84)), regenerated `docs/IndicatorDictionary.md`
  (`python docs/gen_indicator_dictionary.py`; diff is exactly the new row,
  the three header counts, the statistics section count, and the
  no-transform-needed shortlist), and `docs/MLCompanionContract.md` (759 ->
  760 tagged, 385 -> 386 `SF`, matching the dictionary's own classification
  of `RD_QUADFIT_RESID_20` as `SF`).
- Ran the required subset:
  `python -m pytest -q tests/test_rd_quadfit_resid_20.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
  — 1,718 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  expected: Gate E is pending until the launcher runs it).
- A stray tracked-file deletion (`downloaded_files/dashboard.lock`), a
  known side effect of running this repo's test suite (per git history, the
  same file has been deleted-and-restored by prior port sessions), was
  restored with `git restore` before review — not part of this port's
  intended diff.

## Review round 1

```
VERDICT: PASS

FINDINGS:
  - severity: MINOR
    location: docs/RdQuadfitResid20Measured.md:88-90 (Gate A section, "Module's measured output at the one defined bar...")
    problem: The receipt claims the hand-derived fixture's exact value `1/sqrt(5) = 0.4472135954999579...` "matches to **3.2e-14**" against the module's measured output `0.4472135954999547`. The actual difference between those two printed numbers is `0.4472135954999579... - 0.4472135954999547 ≈ 3.24e-15`, not `3.2e-14` — the stated tolerance is off by a factor of 10.
    fix: In docs/RdQuadfitResid20Measured.md line 89, change "matches to **3.2e-14**" to "matches to **3.2e-15**" (or regenerate the line's wording directly from `docs/measure_rd_quadfit_resid_20.py`'s printed values rather than hand-subtracting).
SUMMARY: This port is clean work -- Gate A's hand-derived orthogonal-contrast fixture is correct (verified v=(-1,3,-3,1) orthogonal to raw t=0,1,2,3 and t^2, v.y=1, v.v=20, ratio =1/sqrt(5) exactly), the independent-loop oracle and all measured Gate A/B/C/D numbers reproduce exactly via docs/measure_rd_quadfit_resid_20.py (0 leaks for the real module across 28 swept J, 28/28 leaks for the importlib-exec'd .shift(-1) lookahead mutant, 0-of-1581 bit-identical but ~5e-9-relative-tolerance power-of-two scale results matching the non-power-of-two case, exactly as the module docstring, test file, and Measured.md all consistently claim with zero stray "bit-identical" leftovers anywhere), the length < 4 guard is justified and tested, all five wiring touch points are present and alphabetically correct, the README/MLCompanionContract/IndicatorDictionary/test_altport2_ports.py counter bumps are arithmetically self-consistent, the diff touches nothing outside the allowed set, and the required pytest subset returns exactly the claimed "1 failed (the expected/owed ledger test), 1718 passed, 7 skipped." The one defect found is a cosmetic order-of-magnitude slip in a single float-precision sentence in the Measured.md receipt -- real but inconsequential to every gate, test, and shipping decision this session made.
```

### Fixes applied

- `docs/RdQuadfitResid20Measured.md`: corrected "matches to **3.2e-14**" to
  "matches to **3.2e-15**" in the Gate A section. No test or gate verdict
  depended on this value (`test_hand_derived_value` uses `pytest.approx`
  with `abs=1e-9`, which passes either way).

## Outcome

PASS (round 1, one MINOR finding fixed although not required for PASS).
