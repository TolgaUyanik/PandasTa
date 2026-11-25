# TTR-SNR-20 — port signal-to-noise ratio as `ttr_snr_20`

Task text (verbatim, from the invocation):

> TTR-SNR-20: port the indicator of issue #149 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (signal-to-noise
> ratio: |20-bar move| over ATR (20). Source: R TTR (GPL-2.0) — `SNR.R: abs(Cl - lag(Cl, n)) /
> ATR(n)`.). Gate E and the whole suites are run by the launcher afterwards. You and every
> subagent verify with `python -m pytest -q <the port's test modules> tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
> plus any PandasTa test module a finding names, never the whole suite (the launcher runs it).
> Until the launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails: expected,
> not a finding.

Clarifications: none needed (see `00-manifest.md`).

## Execution log

- Read `pandas_ta/momentum/pfe.py`, `pandas_ta/overlap/kalman_trend.py`,
  `pandas_ta/volatility/tf_median_absdiff_20.py`, `pandas_ta/statistics/lean_tdd_20.py` and their
  test/measured-doc precedents to match this fork's port shape and doc depth.
- Read `pandas_ta/volatility/atr.py`, `true_range.py`, `wilder_rma.py` and confirmed the
  fork's own `atr()` default (`"rma"`) is explicitly NOT Wilder's smoothing, while TTR's own
  `ATR()` default IS Wilder's.
  ASSUMPTION: `SNR.R` is not in this worktree (per the system prompt's "Library code ...
  existence, not evidence" rule and CLAUDE.md), so TTR's own `ATR()` smoothing default is
  recalled, not read from source. Picked `mamode="wrma"` (this fork's name for Wilder's
  smoothing) over the fork's own `atr()` default to match the CITED source formula rather than
  silently substitute this package's own default — the smaller-blast-radius reading given the
  issue names `ATR(n)` from a source whose own default is Wilder's, not this fork's `rma`.
  Documented explicitly in the module docstring and `docs/TtrSnr20Measured.md`, not left
  implicit.
- Wrote `pandas_ta/volatility/ttr_snr_20.py`: `move = |close - close.shift(length)|`,
  `atr(..., mamode="wrma")`, `snr = move / atr`. Both legs are price-scale quantities, so no
  log-return/percent conversion is needed (unlike most of this fork's other ports).
- Wired the 5 touch points: `pandas_ta/volatility/__init__.py` export,
  `pandas_ta/__init__.py` `Category["volatility"]` entry, `pandas_ta/core.py` accessor
  (`df.ta.ttr_snr_20()`), `tests/test_ttr_snr_20.py`.
- Wrote `docs/measure_ttr_snr_20.py`: Gate A independent scalar-loop Wilder-ATR oracle, Gate C
  synthetic reachability counts, Gate D x8/x64/x10/x3.7 scale checks, and two frozen-price edge
  probes (flat-from-bar-0, and frozen-after-a-volatile-run) with debug prints of the raw
  ATR/move values, run via `python docs/measure_ttr_snr_20.py` to get real numbers before
  writing any claim.
- Found via that script: a totally flat series does NOT read `0/0` NaN, because
  `true_range`'s own `non_zero_range` helper (`pandas_ta/utils/_core.py`) adds a float epsilon
  to a degenerate zero high-low range — ATR settles at exactly `2.220446049250313e-16` (one
  float64 ulp), not 0.0, so the ratio reads a clean `0.0`. Corrected an earlier draft of the
  module docstring, which had WRONGLY claimed "matches R's own `0/0 = NaN`" before this was
  measured — caught by running the probe rather than asserting from the source formula's
  shape.
- Wrote `tests/test_ttr_snr_20.py` (21 tests): Gate A (scalar-loop oracle + 5-bar hand-derived
  window), Gate B (two `importlib`/`exec` mutants — final-write shifted 10 bars earlier, and
  `move`'s close read shifted one bar forward — both proven live and caught 31/31 on a
  31-offset future-perturbation sweep), Gate D (x8/x64 bit-identical, x10/x3.7 tolerance, fires
  and non-constant), the two frozen-series edge cases, plus warm-up/fallback/fillna/wiring
  guards.
  First run surfaced a wrong hand-derived expectation in the Gate-A test (assumed TR constant
  at 1.0 from `high-low`, ignoring that the close-to-close gap exceeds the wick range) — fixed
  by hand-deriving the correct TR/ATR values bar by bar and re-running to confirm.
- Ran `python -m pytest -q tests/test_ttr_snr_20.py tests/test_readme_counts.py
  tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
  tests/test_prose_counts_match_the_csvs.py`: 1 expected failure
  (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, naming
  `ttr_snr_20` as the indicator owed a row — expected per CLAUDE.md's "Owed, not failed" rule),
  1439 passed, 7 skipped on the full invocation; 165 passed / 7 skipped on the subset excluding
  that one expected failure.
- Ran `python docs/gen_indicator_dictionary.py` to regenerate `docs/IndicatorDictionary.md`
  (mechanical, clean 11-line diff) rather than hand-editing counts.
- Updated `README.md` (headline 379->380, callable 387->388, `volatility (38)` ->
  `volatility (39)` with `ttr_snr_20` added to the list), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 379->380, `CATEGORY_BUCKETS["volatility"]` 38->39), and
  `docs/MLCompanionContract.md`'s running SF tally (724->725 tagged columns, 358->359 `SF`) by
  prepending a new history entry, matching the file's existing append-only convention.
- Wrote `docs/measure_ttr_snr_20_cpu.py` (copies the `docs/measure_c22_ami2_cpu.py` pattern:
  sets `NPY_DISABLE_CPU_FEATURES` before numpy import, prints which dispatchable features are
  still enabled, then runs the test module under pytest) and ran it: 21/21 passed with
  `AVX512F AVX512_SKX AVX2 FMA3` disabled.
- Wrote `docs/TtrSnr20Measured.md` transcribing every number above from the actual tool output,
  flagging Gate E as pending and Gate C as synthetic-only.

## Review round 1

VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: docs/TtrSnr20Measured.md, Gate B row ("| B Causality | pass | ...")
    problem:  The row says both mutants are "caught at 31 of 31 offsets on every frame tested," but the suite only ever constructs one base path (`_ohlc_walk()`, seed 11) and one perturbation path (`seed=99`) per mutant — there is exactly one frame pair under test, not a plural set of frames. The phrasing overstates the breadth of what was actually run (though the underlying 31-offset sweep claim itself is accurate and reproduces bit-for-bit).
    fix:      Reword to "caught at 31 of 31 offsets on the one base/perturbation frame pair tested" (or just drop "on every frame tested" entirely, since the offset count already says what was swept).
SUMMARY: This port is clean. Every load-bearing claim was independently re-derived and matched exactly: the Gate A scalar-loop oracle and the 5-bar hand arithmetic both check out against the shipped column; the two Gate-B mutants (`importlib`-read + `exec`'d, not hand-copied) are genuinely live and are caught at 31/31 offsets by a real future-perturbation sweep, not prefix truncation; the `mamode="wrma"` choice is correctly justified against `atr.py`'s own docstring and against TTR's cited `ATR()` default, not a silent substitution; the x8/x64 bit-identical claim for Gate D is both mathematically sound (power-of-two scaling is exponent-only and cancels exactly through TR, Wilder's EWM recursion, and the final division) and reproduced bit-for-bit by rerunning `docs/measure_ttr_snr_20.py`; the frozen-series 0.0-not-NaN claim traces correctly through `non_zero_range`'s `sys.float_info.epsilon` guard and the module's own debug trace reproduces the exact `2.220446049250313e-16` value claimed. Wiring across all five touch points is consistent with sibling accessors (`atr`, `true_range`), and every count (README 379->380, volatility bucket 38->39, dictionary 381->382, MLCompanionContract 724->725 / 358->359 SF, `CATEGORY_TOTAL`/`CATEGORY_BUCKETS`) is self-consistent and matches a live rerun. Running the verbatim targeted suite plus `tests/test_gate_e_ledger.py` reproduces exactly the stated 165 passed/7 skipped (minus the one explicitly-expected, instructed-not-to-flag ledger failure), and the CPU-feature-disabled rerun passes 21/21 as claimed. Scope is surgical -- only the allowed files were touched, one new indicator module, no deletions or renames. The one nit above is cosmetic wording, not a correctness or process defect.

### Fixes applied
- NIT (Gate B row wording) -> reworded `docs/TtrSnr20Measured.md`'s Gate B evidence cell from
  "on every frame tested" to "on the one base/perturbation frame pair tested".

## Outcome
PASS (round 1)
