# Task log — c22_low_freq_power (issue #141)

## Implementation

Files added:
- `pandas_ta/statistics/c22_low_freq_power.py`
- `tests/test_c22_low_freq_power.py`
- `docs/measure_c22_low_freq_power.py`
- `docs/measure_c22_low_freq_power_cpu.py`
- `docs/C22LowFreqPowerMeasured.md`

Files modified (wiring + doc counts):
- `pandas_ta/statistics/__init__.py` (export)
- `pandas_ta/__init__.py` (`Category["statistics"]`)
- `pandas_ta/core.py` (`df.ta.c22_low_freq_power()` accessor)
- `README.md` (374 -> 375 total, 382 -> 383 accessor count, statistics 68 -> 69)
- `docs/IndicatorDictionary.md` (regenerated)
- `docs/MLCompanionContract.md` (719 -> 720 tagged, SF 353 -> 354)
- `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 374 -> 375)

No GPL-3.0 code was read or run: pycatch22 is not installed in this
environment (not a declared dependency of this fork); Gate A's oracle is an
independent direct-DFT written for this port.

## Review round 1

VERDICT: REVISE

FINDINGS:
  - severity: MAJOR
    location: pandas_ta/statistics/c22_low_freq_power.py:175-189 (module docstring)
    problem: Claimed the equal-frequency-width and equal-bin-count band-1
      cutoffs "can diverge at other lengths" without a supporting example;
      derivation shows they are in fact identical at every power-of-two
      NFFT this module can produce, since NBANDS=5 never divides one.
    fix: Correct the docstring to state and derive the actual result (the
      two conventions are provably identical, not merely coincidentally
      equal at the default length), and back it with a computational test.

SUMMARY: Port is otherwise clean (numbers independently re-run and
matched), but the docstring's reading-ambiguity paragraph asserted a false
claim with no computation behind it -- exactly the repo's dominant defect
pattern ("a claim written before it was measured").

## Fix applied

- Rewrote the docstring paragraph in `c22_low_freq_power.py` ("ONE READING
  THE DEFINITION LEAVES OPEN, AND WHY IT DOES NOT MATTER") with the
  `half = 5q + s`, `s in {1,2,3,4}` derivation showing both cutoffs equal `q`.
- Updated `docs/C22LowFreqPowerMeasured.md` section 0 to match.
- Added `test_the_equal_width_cutoff_matches_the_equal_bin_count_cutoff` to
  `tests/test_c22_low_freq_power.py`, computing both cutoffs independently
  across 15 lengths (8..2000) and asserting equality.
- Re-ran the targeted suite: 1,492 passed, 7 skipped, 1 expected failure
  (`test_every_indicator_that_needs_a_row_has_one`, Gate E owed).

## Review round 2

VERDICT: PASS
FINDINGS: (none)
SUMMARY: Round-1 MAJOR resolved; the fix's algebra re-derived independently
and confirmed correct; the new test is genuine and non-vacuous (imports the
shipped module's own constants, passes on its own: "1 passed, 113
deselected").
