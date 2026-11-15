# Brutally Honest Review — range_compress_run

**Date:** 2026-10-26
**Target:** `pandas_ta/volatility/range_compress_run.py`, `tests/test_range_compress_run.py`,
`docs/RangeCompressRunMeasured.md`, wiring (`pandas_ta/volatility/__init__.py`,
`pandas_ta/__init__.py`, `pandas_ta/core.py`), counts (`README.md`,
`docs/IndicatorDictionary.md`, `tests/test_altport2_ports.py`)
**Type:** code
**Verdict:** REVISE

## Findings

### CRITICAL
- **`range_compress_run.py` docstring; `RangeCompressRunMeasured.md` "The tie tolerance"**: the
  example pair `100.35 - 100.20` vs `99.10 - 98.95` is not unequal in float. Both evaluate to
  exactly `0.14999999999999147`, so neither `<` is True. This is the sentence that justifies the
  epsilon, and it was written before it was measured.
  - Fix: use a measured pair from the seed-11 test walk: bar 170 (high 115.80000000000001, low
    112.95, range 2.8500000000000085) vs bar 171 (high 117.75, low 114.9, range
    2.8499999999999943). Equal in ticks, unequal in float. Pin it with an assertion in
    `test_float_flag_matches_exact_tick_arithmetic`.

### MAJOR
- **`RangeCompressRunMeasured.md`, Gates row F ("This repo: see the PR")**: the row records no
  numbers, and no PR exists. The suite results (pd2: 2 failed; pd3: 42 failed, the same before and
  after) are written down nowhere. `test_wilder_rma` is not in CLAUDE.md's Known breaks.
  - Fix: record the pytest summary lines for both venvs, with and without the change. Name
    `test_wilder_rma` and the commit it fails on. State that "both suites green" is not met.

### MINOR / NIT
- **MINOR, `range_compress_run.py:20`**: the tolerance is relative to the range, but subtraction
  noise scales with price. Once price/range exceeds about 5e6, ties read as compression again.
  Verified with high = 1e7 + 0.05·k, which gives `[nan, 1.0, 0.0]` on tick-equal ranges.
  - Fix: make the tolerance price-aware (`rng < prior - (1e-9*prior + 8*eps*high.abs())`), or add
    a `shortcut:` comment stating the limit.
- **MINOR, test docstring and Measured doc ("×10 / ×3.7 become bit-identical")**: ×3.7 was already
  bit-identical without the tolerance (0 bars moved). Only ×10 changed (9 bars).
  - Fix: reword it and scope the claim to "on the seed-11 walk".
- **MINOR, Measured doc "Prior art"**: the `decreasing` comparison (5,000 bars, longest run 6)
  states no seed and has no test, so it cannot be reproduced.
  - Fix: state the generator and seed, or add it as a test, or delete the counts.
- **MINOR, tests (missing cases)**: nothing tests NaN mid-series, zero-range ties, `offset` or
  `fillna`. Removing the NaN mask line would not fail any test.
  - Fix: one small test covering NaN at bar 500 (NaN at 500 and 501, finite at 502), a zero-range
    tie reading 0, `offset=1` equal to `.shift(1)`, and `fillna=0` leaving no NaN.
- **NIT, `range_compress_run.py:33-34`**: the `fill_method` branch raises TypeError on pandas 3.
  - Fix: drop it from the new module, and leave the house-wide fix to a separate issue.
- **NIT, `range_compress_run.py:20`**: on inverted bars (high < low) the tolerance flips, so a tie
  counts as compression.
  - Fix: use `prior.abs()` in the tolerance term, or document that inverted bars are out of
    contract.

## Summary

The core is sound and small. It reuses `ml_bars_since` correctly, wires all five touch points, and
updates the counts consistently. The reviewer independently re-checked these numbers: 4 of 14
ties, ×10 moves 9 bars, 600/599/1, runs 0..4, and 12 of 31 for the random-only rewrite. The Gate B
mutants are real one-bar look-aheads, caught at 31 of 31. But the example used to justify the main
departure from the prototype is false, which is exactly the defect class CLAUDE.md warns about. The
Measured doc also fails the issue's done criterion on Gate F, and it waves off an unlisted
`test_wilder_rma` failure without recording it.

Not checked by the reviewer: Gates C and E and the Backtesting suite (no `../Backtesting` on this
machine), the full suite run (the sandbox blocked pytest's temp directory), and regenerating the
dictionary row.
