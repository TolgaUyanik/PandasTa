# Task: flat_spots port (issue #161)

## Implementation summary

Ported Kats tsfeatures' `get_flat_spots` (via the 2026-10-25 screen prototype's own
time-chunked reading) as `pandas_ta/statistics/flat_spots.py`: over a rolling window of
`length` closes (default 100), split into 10 equal-size time chunks (dropping the
window's newest `length % 10` bars when not a multiple of 10), find the longest run of
consecutive identical closes in any chunk, report 1 + that run.

Files:
- `pandas_ta/statistics/flat_spots.py` (new) — the indicator + docstring.
- `tests/test_flat_spots.py` (new) — 24 tests (correctness oracle, two closed forms,
  semantics, causality mutant + perturbation, scale-free, edge cases, wiring).
- `docs/FlatSpotsMeasured.md` (new) — the measured receipt.
- `docs/measure_flat_spots.py`, `docs/measure_flat_spots_cpu.py` (new) — reproduce the
  receipt's numbers, including under the CI CPU-feature set.
- Wiring: `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py` (`Category`),
  `pandas_ta/core.py` (accessor).
- Counters: `README.md`, `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`.

Gate E and the ledger row are explicitly deferred to the launcher, per the issue-solver
system prompt.

## Review round 1

Dispatched a Fletcher reviewer (`Explore` subagent, read-only) against all new/changed
files, the issue text, and the issue-solver's constraints (Gate E deferred, the owed
ledger-row test failure expected). Verdict:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: pandas_ta/statistics/flat_spots.py:109
    problem:  The module docstring cites the prototype at "lines 107-121", but
      `_flat_spots` (def through `return`) in `docs/issues/screen/ind_screen_r5.py` only
      spans lines 107-116. Lines 117-121 are a blank line, the `@cand` registration
      decorator, and the `roll(c, N, _flat_spots)` call -- not the ported function. The
      test file (L10, L59) and docs/FlatSpotsMeasured.md (L13) both cite the correct
      "107-116"; only the module's own docstring drifted.
    fix:      Change "lines 107-121" to "lines 107-116" in the module docstring (line
      109) to match the test file and the Measured.md receipt.
  - severity: NIT
    location: docs/FlatSpotsMeasured.md:65-67
    problem:  Decision 4 attributes "x8, x64, x10 and x3.7 are all exactly 0.0 max abs
      diff" to `measure_flat_spots.py`'s `scale_tolerance`, but that function only
      exercises k=10.0/3.7. The x8/x64 case is checked in
      `tests/test_flat_spots.py::test_price_scale_is_bit_identical` via a boolean `==`
      comparison, which never computes or prints a "max abs diff" number.
    fix:      Split the sentence so the parenthetical citation only covers x10/x3.7
      (scale_tolerance), and cite `test_price_scale_is_bit_identical` for the x8/x64
      boolean-exact claim.
SUMMARY: This port earns its green run honestly -- the chunking math, the `+1`
  run-length conversion, the causal mutant/perturbation probe, and the "`==` survives
  any uniform rescale" Gate D argument are all mathematically sound and, unlike a lot of
  first-pass work, every number in FlatSpotsMeasured.md reproduces exactly when you
  actually run `measure_flat_spots.py`, `measure_flat_spots_cpu.py`, and the named
  pytest command (1 failed / 1522 passed / 7 skipped, 24/24 under the CPU-feature
  variant, bit-for-bit on every Gate A/D figure). The CONST-tag explanation is a
  faithful, non-misleading restatement of the exact `ts_reoccur_20` §C1 precedent, and
  all five wiring touch points plus every counter file (README, MLCompanionContract,
  IndicatorDictionary, test_altport2_ports) are mutually consistent with the actual
  `git diff`. The only blemish worth a developer's five minutes is a stale line-range
  citation in the module's own docstring (107-121 vs. the correct 107-116, which the
  test file and Measured.md both got right) -- sloppy, not dangerous, and not the
  "claim written before it was measured" failure mode this repo is scarred by.
```

## Fixes applied (PASS, but both findings fixed anyway since they were one-line)

- `pandas_ta/statistics/flat_spots.py`: "lines 107-121" -> "lines 107-116".
- `docs/FlatSpotsMeasured.md`: Decision 4 and the Gate D section now separately attribute
  the x8/x64 bit-identical claim to `test_price_scale_is_bit_identical` and the x10/x3.7
  exact-0.0 claim to `measure_flat_spots.py`'s `scale_tolerance`, rather than one sentence
  covering all four scales under the wrong citation.

Re-ran `python -m pytest -q tests/test_flat_spots.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py` after the fixes: 1 failed (the expected owed
ledger row), 1522 passed, 7 skipped — unchanged, confirming the fixes were doc-only.

## Outcome

PASS (round 1). No re-review needed (both findings were MINOR/NIT, fixed as a courtesy,
not required by the gate rule).
