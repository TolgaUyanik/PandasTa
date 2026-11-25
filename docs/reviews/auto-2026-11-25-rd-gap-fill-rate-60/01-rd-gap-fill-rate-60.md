# RD-GAP-FILL-RATE-60 — port `rd_gap_fill_rate_60`

Issue #165. Port the indicator through Gates A-D, the wiring, the tests and
`docs/RdGapFillRate60Measured.md`. Gate E and the whole suites are deferred
to the launcher (this session's system-prompt override); Gate F here is
limited to the named test subset, never the whole suite.

## Execution log

- Read the prototype (`docs/issues/screen/ind_screen_r6.py`'s
  `rd_gap_fill_rate_60`, `GAP = 0.003`, and the `sdiv` helper) and the closest
  structural precedent, `pandas_ta/candles/rd_horseshoe.py` /
  `tests/test_rd_horseshoe.py` / `docs/RdHorseshoeMeasured.md` (same issue
  family: a Reddit tier-4 post, no source line numbers, Gate E deferred).
- Chose category `statistics` (matches `lot_zeroret_60`'s "trailing share"
  shape) and parameterized both `length` (default 60) and `min_gap` (default
  0.003) rather than hard-coding either — logged as an ASSUMPTION in
  `00-manifest.md`.
- Wrote `pandas_ta/statistics/rd_gap_fill_rate_60.py`, wired all five touch
  points (module, `pandas_ta/statistics/__init__.py`, `Category` in
  `pandas_ta/__init__.py`, the `core.py` accessor, `tests/test_rd_gap_fill_rate_60.py`).
- Wrote 19 tests: hand-derived fixture (recomputed by hand before running),
  no-gap-in-window NaN case, independent-loop cross-check, warm-up,
  offset/fillna, short-input, causality (future-splice sweep + look-ahead
  mutant), scale-free (x8/x64 bit-identical, x10/x3.7 bounded tolerance),
  reachability, wiring.
- Wrote `docs/measure_rd_gap_fill_rate_60.py` and ran it; every number in
  `docs/RdGapFillRate60Measured.md` is copied from that run's actual output
  (fires 1,541/1,600, min 0.4706, max 0.8649, 181 distinct values; real
  module 0/28 leaks, mutant 18/28; x8/x64/x10/x3.7 all 0 mismatches on 1,541
  cells).
- Wrote `docs/measure_rd_gap_fill_rate_60_cpu.py` (NPY_DISABLE_CPU_FEATURES =
  "AVX512F AVX512_SKX AVX2 FMA3") and ran it: 19 passed.
- Updated `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 393 -> 394),
  `README.md` (393 -> 394 registered, 401 -> 402 callable, statistics
  (80) -> (81)), regenerated `docs/IndicatorDictionary.md`
  (`python docs/gen_indicator_dictionary.py`; diff is exactly the new row,
  the three header counts, the statistics section count, and the
  no-transform-needed shortlist), and `docs/MLCompanionContract.md` (738 ->
  739 tagged, 369 -> 370 `SF`, matching the dictionary's own classification
  of `RD_GAP_FILL_RATE_60_0.3` as `SF`).
- Ran the required subset:
  `python -m pytest -q tests/test_rd_gap_fill_rate_60.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
  — 1,549 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  expected: Gate E is pending until the launcher runs it).

## Review round 1

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: pandas_ta/statistics/rd_gap_fill_rate_60.py:36-38
    problem:  The shipped module docstring's Gate B paragraph states the look-ahead mutant "leaks at every swept J too." I re-ran `docs/measure_rd_gap_fill_rate_60.py` in this session: the actual result is 18 of 28 swept J values, not 28 of 28. That's the exact same number the port's own Measured.md and the test's inline comment report correctly. The docstring — the one artifact a future session reads as ground truth — is simply wrong about its own Gate B claim.
    fix:      Rewrite lines 36-38 to state the measured bound honestly, e.g. "the real module leaks 0 bars before J at every swept J; the mutant ... leaks at 18 of the same 28 swept J (measured, docs/RdGapFillRate60Measured.md) — a majority, not every one, since a NaN-mask coincidence at the splice point can let it slip through at some J."
  - severity: MAJOR
    location: tests/test_rd_gap_fill_rate_60.py:13-18
    problem:  The test module's own top-of-file docstring says the mutant "is proved live and caught at every swept J" and that "a sweep catches the mutant everywhere, not just at some J." Three sections later in the same file, `test_lookahead_mutant_is_caught` only asserts `hits >= len(OFFSETS) // 2` and its inline comment admits the measured count is 18 of 28. The file contradicts itself on the single most load-bearing causality number it reports.
    fix:      Rewrite lines 13-18 to match the code: "...caught at 18 of 28 swept J (a majority, not every one) — this is a continuous ratio that changes on almost every bar, unlike a rare binary flag, so a sweep catches the mutant at most J, not merely at some J."
SUMMARY: The arithmetic is sound — I hand-checked the fixture, re-ran the measurement script, re-ran the full Gate-F command, and re-ran the CPU-feature-variant run, and every number in docs/RdGapFillRate60Measured.md came back bit-for-bit identical to what's claimed (1,541 fires, 0/28 real leaks, 18/28 mutant leaks, 0 scale mismatches at x8/x64/x10/x3.7, 1,549 passed / 7 skipped / 1 expected failure). Wiring, file scope, and the README/dictionary/contract counters are all consistent. But you let an "every" slip into the one sentence that exists purely to prove the causality gate isn't theater — twice, in two different files, both contradicted by your own measured 18-of-28 three paragraphs later. That's not a typo, that's not reading what you wrote. Fix both sentences to say 18 of 28 and this ships.
```

### Fixes applied

- `pandas_ta/statistics/rd_gap_fill_rate_60.py`: rewrote the CAUSALITY
  paragraph to state "the mutant ... leaks at 18 of the same 28 swept J
  (measured, docs/RdGapFillRate60Measured.md) -- a majority, not every one,
  since a NaN-mask coincidence at the splice point can let it slip through
  at some J", while keeping the (correct, unchanged) "real module leaks 0
  bars before J at every swept J (28 of 28)" claim.
- `tests/test_rd_gap_fill_rate_60.py`: rewrote the top-of-file CAUSALITY
  bullet to state "caught at 18 of the same 28 swept J -- a majority, not
  every one ..., but still far more than a rare binary flag like
  `rd_horseshoe` manages (24 of 293)".

## Review round 2

```
VERDICT: PASS
FINDINGS:
SUMMARY: Both docstrings now say exactly what the script measured — module (lines 36-38) and test (lines 13-20) both read "18 of the same 28 swept J," matching the live run I just did again: `python docs/measure_rd_gap_fill_rate_60.py` → "real module leaked at 0, mutant leaked at 18." The remaining "28 of 28"/"every one of 28 swept J" phrases are scoped to the real module's 0-leak claim, not the mutant — that's correct and must stay. The `OFFSETS` sweep is genuinely 28 points, the assertion threshold (`>= 14`) and the receipt doc's Gate B section all agree with each other and with the code; `rd_horseshoe`'s cross-reference ("24 of 293") checks out against its own measured doc too. Ran the full 19-test file — green. No new overclaim, no stale number, no code/docstring drift anywhere else in either file. That was acceptable. Barely.
```

## Outcome

PASS (round 2).
