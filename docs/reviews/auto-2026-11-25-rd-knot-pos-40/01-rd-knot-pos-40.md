# RD-KNOT-POS-40 — port `rd_knot_pos_40`

Issue #166. Port the indicator through Gates A-D, the wiring, the tests and
`docs/RdKnotPos40Measured.md`. Gate E and the whole suites are deferred to
the launcher (this session's system-prompt override); Gate F here is
limited to the named test subset, never the whole suite.

## Execution log

- Read the prototype (`docs/issues/screen/ind_screen_r6.py`'s
  `rd_knot_pos_40`, `_knot_scan`, `_knots`) and the closest structural
  precedent, `pandas_ta/statistics/trend_scan.py` (same shape: a per-window
  OLS regression scanned over a parameter, reported as a scale-free
  position/t-stat) and `pandas_ta/statistics/rd_gap_fill_rate_60.py` (same
  issue family: a Reddit tier-4 post, no source line numbers, Gate E
  deferred).
- Chose category `statistics` and parameterized both `length` (default 40)
  and `knot_margin` (default 5, giving candidate knots `[5, 34]`) rather
  than hard-coding either — logged as an ASSUMPTION in `00-manifest.md`.
- Derived Gate A independently from the issue's own words (continuous
  one-knot hinge model `y = a + b*t + c*max(t-k,0)`, OLS per candidate knot,
  argmin SSE), not by reading the prototype's `_knots`/`_knot_scan` pinv
  trick, though the two are mathematically equivalent.
- Wrote `pandas_ta/statistics/rd_knot_pos_40.py`: `_hinge_basis` builds the
  (knots, residual-maker) basis once per call (pure function of
  `length, knot_margin`), `_knot_age` applies it to every causal
  40-bar-by-default window via `sliding_window_view`, masking any window
  holding a non-finite value to NaN rather than trusting `argmin` on an
  all-NaN row.
- Wired all five touch points (module, `pandas_ta/statistics/__init__.py`,
  `Category` in `pandas_ta/__init__.py`, the `core.py` accessor,
  `tests/test_rd_knot_pos_40.py`).
- Wrote 20 tests: noiseless hand-derived fixture (exact knot=5 hinge, chosen
  on paper before the module ran), independent-loop cross-check
  (`np.linalg.lstsq` per candidate knot, not read from the module),
  knot_margin-too-large raises, non-finite-window NaN case, warm-up,
  offset/fillna, short-input, causality (future-splice sweep + look-ahead
  mutant), scale-free (x8/x64/x10/x3.7), reachability, wiring.
- Wrote `docs/measure_rd_knot_pos_40.py` and ran it; every number in
  `docs/RdKnotPos40Measured.md` is copied from that run's actual output:
  hand fixture 0.4444444444444444 (matches 4/9 to 1e-9); independent-loop
  cross-check max |diff| 0.000e+00 over 261 defined bars; fires 1,561/1,600,
  min 0.1282, max 0.8718, exactly 30 distinct values (the full discrete
  knot grid at defaults — an unanticipated finding, written up as Decision 3
  in the Measured.md rather than glossed over); real module 0/28 leaks,
  mutant 25/28; x8/x64/x10/x3.7 all 0 mismatches on 1,561 cells (stronger
  than merely "within tolerance" — the intercept term makes the SSE
  argmin invariant to any additive `log(close)` shift in exact arithmetic,
  and this frame's measured float rounding never flips an argmin tie).
- Wrote `docs/measure_rd_knot_pos_40_cpu.py`
  (`NPY_DISABLE_CPU_FEATURES = "AVX512F AVX512_SKX AVX2 FMA3"`) and ran it:
  20 passed.
- Updated `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 394 -> 395),
  `README.md` (394 -> 395 registered, 402 -> 403 callable, statistics
  (81) -> (82)), regenerated `docs/IndicatorDictionary.md`
  (`python docs/gen_indicator_dictionary.py`; diff is exactly the new row,
  the three header counts, the statistics section count, and the
  no-transform-needed shortlist), and `docs/MLCompanionContract.md` (739 ->
  740 tagged, 370 -> 371 `SF`, matching the dictionary's own classification
  of `RD_KNOT_POS_40_5` as `SF`).
- Ran the required subset:
  `python -m pytest -q tests/test_rd_knot_pos_40.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
  — 1,558 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  expected: Gate E is pending until the launcher runs it).

## Review round 1

```
VERDICT: PASS

FINDINGS:
  - severity: MINOR
    location: pandas_ta/statistics/rd_knot_pos_40.py:27-28
    problem:  The module docstring tells the reader "0 means the lowest-MSE knot sits at the current bar (a break just now); 1 means it sits at the window's oldest usable knot position," but with `knot_margin` restricting candidate knots to `[knot_margin, length-1-knot_margin]`, `best` can never equal `length-1` or `0` for any `knot_margin >= 1` -- so neither endpoint is ever actually reachable. `docs/RdKnotPos40Measured.md` Decision 3 discloses this correctly ("never exactly 0 or 1"), but a reader of only the module source is told the opposite.
    fix:      Add one sentence to the Gate A docstring paragraph giving the true reachable range at the stated knot_margin, e.g. "neither 0 nor 1 is ever reached; at defaults the range is [5/39, 34/39] = [0.1282, 0.8718]."
SUMMARY: This is a clean, well-executed port -- I verified every claim rather than trusting it, and it holds up. The hinge-regression math (pinv projection matrices, SSE invariance under additive log-shift) is correct and matches standard OLS theory; the causality indexing via `sliding_window_view` is genuinely trailing-only with no off-by-one; the independent `_oracle` in the test file uses a different algorithmic path (`np.linalg.lstsq` per-window per-knot vs. the module's precomputed projection-matrix batch approach) so it's a real independent check, not copy-paste; the hand-derived fixture's arithmetic (4/9) is correct by construction. I reran `docs/measure_rd_knot_pos_40.py` and `docs/measure_rd_knot_pos_40_cpu.py` myself and every number in `docs/RdKnotPos40Measured.md` matched byte-for-byte, including the module SHA1, the CPU-feature list, and the 1,558/7/1 pytest tally from the exact required command. Wiring (Category, core.py accessor, statistics `__init__`, README/IndicatorDictionary/MLCompanionContract counters, CATEGORY_TOTAL) is complete, alphabetically placed, and internally consistent with the diff. The lone issue is a documentation nicety -- the public docstring implies 0 and 1 are reachable states when the margin makes that impossible -- which doesn't rise above MINOR since it's already correctly disclosed in the measured receipt. Ship it.
```

### Fixes applied

- `pandas_ta/statistics/rd_knot_pos_40.py`: reworded the Gate A docstring's
  age-range paragraph to state that neither 0 nor 1 is ever reached under
  `knot_margin`, giving the true reachable range at defaults
  (`[5/39, 34/39] = [0.1282, 0.8718]`), matching
  `docs/RdKnotPos40Measured.md`'s own Decision 3. `tests/test_rd_knot_pos_40.py`
  re-run clean (20 passed) after the edit.

## Outcome

PASS (round 1, one MINOR finding fixed although not required for PASS).
