# Task: diff1_pacf5 (issue #151)

## Implementation log

1. Read the prototype registration in `docs/issues/screen/ind_screen_r5.py`
   (`kats_diff1_pacf5_100`, lines 187-189) and the already-ported sibling `diff2_acf1`
   (`pandas_ta/statistics/diff2_acf1.py`, `docs/Diff2Acf1Measured.md`,
   `tests/test_diff2_acf1.py`) for the shared Kats control-flow citation and the repo's
   port conventions (chunked `sliding_window_view`, rounding guard shape, mutant-test
   pattern).
2. Determined, by measurement, which statsmodels `pacf` method implements "Durbin-
   Levinson on the unadjusted ACF" (the issue's stated scale-free form): `method="ywm"`,
   not the historical default `method="ywadjusted"` — see `docs/measure_diff1_pacf5.py`,
   `pacf_method_probe`. This was an ASSUMPTION resolved by measurement, not by asking (no
   AskUserQuestion available in this session), per the conservative-reading rule.
3. Wrote `pandas_ta/statistics/diff1_pacf5.py`: Durbin-Levinson recursion on the
   window's unadjusted lag-1..5 ACF of log returns, with a NOISE_ULPS rounding guard one
   differencing level earlier than `diff2_acf1`'s.
4. Wired the 3 non-test touch points: `pandas_ta/statistics/__init__.py` (export),
   `pandas_ta/__init__.py` (`Category["statistics"]`), `pandas_ta/core.py` (accessor) —
   alphabetically placed before `diff2_acf1` in all three.
5. Wrote `tests/test_diff1_pacf5.py` (33 tests: correctness vs an independent recursion
   and statsmodels, causality mutant + leak test, the rounding guard from both sides,
   scale-free ×8/×64/×10/×3.7, edge cases, wiring).
6. Wrote `docs/measure_diff1_pacf5.py` (Gate A oracle reproducing Kats' control flow,
   the rounding-guard measurement, Gate C reachability, cost) and
   `docs/measure_diff1_pacf5_cpu.py` (the CI CPU-feature-variant wrapper).
7. Updated counters: `README.md` (381→382, 389→390, statistics (70)→(71)),
   `docs/MLCompanionContract.md` (726→727 tagged, 360→361 `SF`),
   `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 381→382), regenerated
   `docs/IndicatorDictionary.md`.
8. Wrote `docs/Diff1Pacf5Measured.md` with Gate A-D evidence and
   `Gate E: pending, run by issue-solver after this session` per the session's override
   rules.
9. Verified with the required test subset
   (`tests/test_diff1_pacf5.py tests/test_readme_counts.py tests/test_altport2_ports.py
   tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py
   tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`): 1467
   passed, 7 skipped, 1 failed — the expected, named `test_gate_e_ledger.py` owed-row
   failure for `diff1_pacf5`. Also ran the CPU-variant wrapper (33/33 passed with
   `AVX512F AVX512_SKX AVX2 FMA3` disabled).

## Fixes applied during development (not review rounds — caught while writing the tests)

Two off-by-one bugs in the test file's own edge-case index ranges (not in the module)
were caught and fixed before the review gate, by re-deriving the affected-bar ranges
from the window arithmetic instead of copying `diff2_acf1`'s ranges verbatim (that
module differences twice; this one differences once, so the reach of a bad close is one
bar wider on each side). Both are reflected in the final `tests/test_diff1_pacf5.py`.

## Review round 1

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: This one actually did the work instead of writing about it. I hand-derived the
Durbin-Levinson recursion from the textbook formula and traced every index in
`_pacf5_sumsq` and `_diff1_pacf5_rows` by hand -- the phi-list reindexing between orders
(`phi[k-j-1]` representing `phi[k-1,k-j]`) is non-obvious and it is correct, not just
"looks correct." I reran the bar-mapping arithmetic for
`test_a_bad_close_blanks_its_windows` and `test_a_price_ratio_that_overflows_is_missing_not_inf`
from first principles (which two log returns a single bad close kills, which window
range reads either) and both tests' claimed index ranges (150..249 and
151..249/finite-but-altered at 150/250) are arithmetically exact, not approximate. I
didn't stop at reading the code: I ran `pytest tests/test_diff1_pacf5.py` (33/33 passed,
statsmodels present so the cross-check actually executed rather than being silently
skipped), ran `docs/measure_diff1_pacf5.py` and matched every printed number against the
Measured.md table, ran the CPU-feature-variant script (33 passed with AVX-512/AVX2/FMA3
disabled), ran the full named Gate-F subset and got the exact "1467 passed, 7 skipped, 1
failed" the receipt claims, and diffed every modified file against HEAD to confirm the
counter bumps (381→382, 389→390, 70→71, 726→727/360→361) are internally consistent and
alphabetically placed in all three wiring files, with zero files touched outside the
declared set. The one disclosed gap -- the `diff1y_pacf5` assembly line not being
re-confirmed against Kats source -- is adequately compensated: two independent
recursions (a from-scratch loop and statsmodels `pacf(method="ywm")`) both corroborate
the math, and the oracle script's Kats-control-flow emulation agrees to 1e-14/1e-15
across 16 frame/length combinations. Nothing here is a claim written before it was
measured.
```

Status: **PASS**, round 1. Marked done, no further rounds needed.
