# J-MEDIAN-AD-5

Port median absolute deviation of hl2 (5): jesse (MIT) `median_ad.py`, computing
`scipy.stats.median_abs_deviation(hl2, window=5)`. Scale-free form per the issue: `/close`.

## ASSUMPTIONs

- The issue cites `scipy median_abs_deviation` — the newer scipy function
  (`scipy.stats.median_abs_deviation`, default `scale=1.0`, the plain unscaled statistic),
  not the older, deprecated `scipy.stats.median_absolute_deviation` (default `scale=1.4826`,
  a normal-consistent estimator). Took the unscaled form as given: it matches the round-2
  prototype's math exactly (`docs/issues/screen/ind_screen_r2.py`, `j_median_ad_5`, which
  applies no `1.4826` factor), and the issue's own text names the newer function. Smaller
  scope / no extra guessing.
- Column name `MEDIANAD_HL2_<length>`: no existing jesse-sourced port in this repo to copy a
  naming convention from (checked: none). Named for clarity (statistics' existing `mad` is
  close-based mean absolute deviation; `MEDIANAD_HL2` avoids colliding with it) and to encode
  the parameter per the repo's `NAME_length` convention (`MAD_30`, `PFE_10_5`).

## What was done

1. Implemented `pandas_ta/statistics/median_ad_hl2.py`: rolling (window=5 default) median
   absolute deviation of `(high+low)/2`, unscaled (`scale=1.0`), divided by `close`.
2. Wired all 5 touch points: module, `pandas_ta/statistics/__init__.py` export,
   `pandas_ta/__init__.py` `Category["statistics"]`, `pandas_ta/core.py` accessor,
   `tests/test_median_ad_hl2.py`.
3. Tests (11): correctness vs an independent loop and a hand-computed window; causality via
   a `write_index` mutant (shifts the rolling result's write index by the full window so
   output[t] reads a window entirely from bars > t) caught at 23/23 perturbation offsets,
   real module 0 leaks; scale-free ×8/×64 bit-identical, ×10/×3.7 within 1e-12; reachability
   / not-constant.
4. Gate A measured against the SOURCE formula (not the prototype): matches
   `scipy.stats.median_abs_deviation(window, scale=1.0)` bit-for-bit (max abs diff 0.0) on
   400 synthetic bars (`docs/measure_median_ad_hl2_gate_a.py`; `scipy` is a dev-only
   dependency, never imported by the shipped module).
5. Gate C measured on a 3,000-bar synthetic walk: 2,996/3,000 finite, 2,980 distinct, 0 zeros
   (`docs/measure_median_ad_hl2.py`).
6. Wrote `docs/MedianAdHl2Measured.md` with Gate E marked PENDING (launcher's job) per the
   session's rules.
7. Bumped counts: `README.md` (238 registered, 246 accessors, statistics (13)),
   `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md` (571 total /
   217 SF, new parenthetical note), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 238).
8. Full suite: 3 failed / 3,269 passed / 83 skipped — the 3 failures are pre-existing known
   breaks (`test_pine_coverage_csv`, `test_altrepo_talib_csv`) plus the expected
   `test_gate_e_ledger::test_every_indicator_that_needs_a_row_has_one` (no ledger row until
   the launcher runs Gate E). No new failure.

## Review rounds

### Round 1 — REVISE
Fletcher reviewer (Explore subagent) findings:
- MAJOR: `docs/MedianAdHl2Measured.md`'s Gate B row and `tests/test_median_ad_hl2.py`'s
  `_leaks` docstring both quoted an unmeasured count ("16-17 of 23 offsets" for a single-bar
  mutant never shipped in the test suite), contradicting the doc's own "every number is
  printed by these two scripts" promise.
- MINOR: `median_ad_hl2.py` hardcoded `min_periods=length` with no override, unlike sibling
  `mad.py`/`median.py`.
- NIT: Gate D row didn't explain why ×8/×64 are bit-identical but ×10/×3.7 are only
  tolerance-matched.

Fixes applied:
- Struck the unmeasured "16-17 of 23" number from both files; replaced with qualitative
  language claiming only what the shipped 23/23 `write_index` mutant proves.
- Added `min_periods` kwarg override to `median_ad_hl2.py` (same pattern as `mad.py` /
  `median.py`: `max(length, min_periods)` on all three `verify_series` calls,
  `min_periods=min_periods` in the rolling call, docstring Kwargs section updated); updated
  the mutant's source-text match in the test file since the matched line changed.
- Added a sentence to the Gate D row explaining the power-of-two mantissa-preservation
  reasoning.
- Re-ran `tests/test_median_ad_hl2.py` (11 passed), `docs/measure_median_ad_hl2.py` and
  `docs/measure_median_ad_hl2_gate_a.py` (numbers unchanged), and the full suite (same 3
  pre-existing failures, no new ones).

### Round 2 — PASS
Fletcher reviewer findings:
- MINOR: the test file's top-of-file module docstring still described the shipped mutant
  inaccurately (said it swaps `min_periods` for "a forward-shifted hl2", which is not what
  `write_index` does — it shifts the rolling result's write index, correctly described 90+
  lines later in the `_leaks` docstring). Two docstrings in the same file contradicted each
  other about what the test proves.

Fix applied: corrected the module docstring's mutant description to match `_leaks`'s
accurate language. Re-ran `tests/test_median_ad_hl2.py` (11 passed).

PASS reached at round 2 of the 3-round cap.
