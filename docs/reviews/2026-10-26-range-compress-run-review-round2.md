# Brutally Honest Review: range_compress_run (round 2)

**Date:** 2026-10-26
**Target:** `pandas_ta/volatility/range_compress_run.py`, `tests/test_range_compress_run.py`,
`docs/RangeCompressRunMeasured.md`, wiring (`pandas_ta/volatility/__init__.py`,
`pandas_ta/__init__.py`, `pandas_ta/core.py`), counts (`README.md`,
`docs/IndicatorDictionary.md`, `tests/test_altport2_ports.py`)
**Type:** code
**Verdict:** PASS
**Prior round:** `docs/reviews/2026-10-26-range-compress-run-review.md` (REVISE)

## Round 1 status

- **CRITICAL, false float-tie example**: FIXED. The docstring (`range_compress_run.py:58-61`) and
  the Measured doc now use bars 170/171 of the seed-11 walk. Re-run: 115.80000000000001 - 112.95 =
  2.8500000000000085 and 117.75 - 114.9 = 2.8499999999999943, both 57 ticks. Pinned at
  `test_range_compress_run.py:96-99`.
- **MAJOR, Gate F unrecorded / no PR**: FIXED. The "Gate F, this repo" section gives the
  pass/fail counts for both venvs, with and without the change, against base 479cd8f. It names
  `test_wilder_rma::test_the_incumbents_did_not_move` and says F is not met. On .venv-pd2 the natr
  golden differs (2.1645906239237416 vs 2.164590623923742). The +15 passes match the 15 collected
  test items.
- **MINOR, range-relative tolerance fails near 1e7**: FIXED. The tolerance is now
  `4*eps*(|high|+|high[1]|)` (line 21), pinned by `test_tie_tolerance_holds_at_high_prices`.
- **MINOR, "×10 / ×3.7 both became bit-identical" overclaim**: FIXED. The text now reads "×10
  moved 9, ×3.7 moved 0", scoped to seed 11. Re-measured.
- **MINOR, `decreasing` prior art not reproducible**: FIXED. The doc states the seed and the
  length. Re-measured: 4/2/2/1 disagreements out of 600/203/53/9 at k=1..4.
- **MINOR, missing NaN/tie/offset/fillna tests**: FIXED. `test_edge_cases` covers them, and its
  NaN-mask assert is load-bearing.
- **NIT, fill_method branch raises on pandas 3**: FIXED. The branch is removed, and the module
  passes on pandas 3.0.6.
- **NIT, tolerance flips on inverted bars**: FIXED. The tolerance uses `|high|`, tested at line 124.

## Findings

### MINOR / NIT
- **MINOR, `range_compress_run.py:10` and `:24`**: a fractional `cap` below 1 mislabels the
  column. `cap=0.5` gives `int(0.5) = 0`, so the name is `RCR_0`, while `ml_bars_since` treats 0
  as falsy and clips at 100. Measured: name RCR_0, max 4.0. The column name is API.
  - Fix: `cap = int(cap) if cap and int(cap) > 0 else 100`, and add
    `assert range_compress_run(h, lo, cap=0.5).name == "RCR_100"` to `test_cap`.
- **MINOR, `range_compress_run.py:62-63`**: "so the tolerance holds at any price level" is an
  unscoped claim. Only 1e7 was measured, and the claim fails in principle once `8*eps*price`
  reaches a tick (about 2.8e13 at a 0.05 tick).
  - Fix: "holds at the price levels tested (to 1e7, `test_tie_tolerance_holds_at_high_prices`);
    stays below one 0.05 tick up to about 2.8e13."
- **MINOR, `RangeCompressRunMeasured.md` "Gate F, this repo" vs CLAUDE.md "Known breaks"**:
  `test_wilder_rma` is a second clean-checkout failure. It is recorded only in this port's
  receipt, which a Gate E revert would delete. CLAUDE.md still says "1 failed".
  - Fix: open a `docs/issues/` entry for the natr golden drift and link it from Gate F. Or, with
    the owner's OK, add a Known-breaks line naming `test_wilder_rma` and 661b97f.
- **NIT, `tests/test_range_compress_run.py:120`**: `assert out[503] in (0.0, out[502] + 1)` holds
  for any run counter, so it pins nothing.
  - Fix: `r_t = ht - lt; assert out[503] == ((out[502] + 1) if r_t[503] < r_t[502] else 0.0)`.

## Summary

Every round-1 finding is fixed, including the CRITICAL and the MAJOR, and the reviewer
re-measured the numbers rather than taking them on trust. What remains is small: a fractional
`cap` mislabels the column, one docstring line claims "any price level", the new `test_wilder_rma`
break lives only in a doc a Gate E revert deletes, and one edge assertion is vacuous. Gate E is
still owed and Gate F is honestly marked not met.

**Not checked by the reviewer:** pytest could not start in the sandbox (temp directories are
read-only), so the test functions were called directly on pandas 2.3.3 and 3.0.6. The full suites
were not run (the Gate F counts are taken from the doc). Gates C and E were not checked, because
the Backtesting repo is not on this machine.
