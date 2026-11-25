# Task log — rd_corr_c_obv_20 (issue #168)

## Implementation

Ported `RD_CORR_C_OBV_20 = close.rolling(20).corr(OBV(close, volume))` as
`pandas_ta/volume/rd_corr_c_obv_20.py`, reusing this fork's own `obv`
(imported from its own module, per the repo's import rule) and the shared
rolling-Pearson helper (`pandas_ta.utils._pine.correlation`, the same one
`pvcorr` uses). Wired into `pandas_ta/volume/__init__.py`,
`pandas_ta/__init__.py` (`Category["volume"]`), `pandas_ta/core.py`
(accessor). Added `tests/test_rd_corr_c_obv_20.py` (19 tests: correctness,
causality/mutant, scale-free, edge cases, wiring), `docs/measure_rd_corr_c_obv_20.py`,
`docs/measure_rd_corr_c_obv_20_cpu.py`, and the receipt
`docs/RdCorrCObv20Measured.md`. Updated README.md, docs/IndicatorDictionary.md
(regenerated), docs/MLCompanionContract.md, tests/test_altport2_ports.py
counters.

Design decisions, all in the module docstring and the Measured.md:
- The poster's z-score step is skipped: a Pearson correlation is already
  invariant to a GLOBAL (whole-series) affine rescale, which is what a
  z-score is, so z-scoring first and not z-scoring read the same number —
  measured in `test_zscoring_either_input_first_does_not_move_the_result`,
  deliberately built with a global, not rolling, mean/std (a rolling
  per-point z-score is a different, non-affine transform and would not
  test the poster's claim correctly — this was caught and fixed mid-session
  when the first draft of the test, built with a rolling z-score, failed
  with a ~0.6 diff instead of ~0).
- A "-1" correctness construction is not offered, because it is
  structurally unreachable: OBV's increment always shares the sign of
  `close.diff()`, so a monotone close forces OBV monotone in the same
  direction. Documented as a structural fact, not a test gap.
- Non-redundant with `pvcorr` (issue #18): different pair of series
  (price/OBV levels vs. return/log-volume-diff), different transform of
  volume (cumulative running sum vs. instantaneous ratio).

## Review round 1

Dispatched the Fletcher reviewer (Explore agent, read-only) against the
module, test file, both measure scripts, the Measured.md, and the wiring
diffs, instructed to actually re-run every command itself rather than trust
the docstrings.

VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/volume/rd_corr_c_obv_20.py:89
    problem: `length=1` (or 0/negative) silently falls back to the default
      20, matching fork convention, but is not pinned by a test.
    fix: add an assertion test for this fallback. Not applied in this
      session (NIT, no blocking finding, round cap reached at round 1 PASS
      — see `/brutally-honest-review` Mode C step 10: PASS closes the task).
  - severity: NIT
    location: docs/RdCorrCObv20Measured.md, Gate C
    problem: reachability is synthetic-only this session (disclosed), real
      counts owed to the receipt session.
    fix: none needed now; flagged so the receipt-session reviewer checks
      the promise is kept.
SUMMARY (quoted verbatim): "This is a clean, disciplined port. Every
quantitative claim in docs/RdCorrCObv20Measured.md was independently
reproduced bit-for-bit (or within the stated float tolerance) by re-running
tests/test_rd_corr_c_obv_20.py, docs/measure_rd_corr_c_obv_20.py, and
docs/measure_rd_corr_c_obv_20_cpu.py from a clean checkout: 19/19 module
tests pass, the combined Gate-F command gives the exact '1,573 passed, 7
skipped, 1 failed' the doc claims (the 1 failure is the expected,
un-landed ledger row), and the Gate A/C/D numbers match to the printed
digit. Gate A's correctness argument is sound and actually tested
(monotone-close +1 construction with a correctly-scoped '-1 is structurally
unreachable by this construction' claim, an independent
np.corrcoef/plain-Python-OBV loop, and a GLOBAL- not rolling-z-score
equivalence test that correctly distinguishes the only z-score form a
Pearson correlation is invariant to). Gate B's mutant is a genuine
look-ahead (`obv_series.shift(-1)` read one bar into the future before
correlating), built via the required importlib-read/exec-in-memory
technique, proven live and caught at all 16 swept offsets. Gate D's
scale-free math is correct ... and is measured, not asserted ... The
non-redundancy argument against `pvcorr` holds up against the actual
pvcorr.py source ... not a dressed-up duplicate. The quoted Gate-E
prototype numbers ... are correctly labeled as quoted, not re-measured, and
Gate E is correctly marked pending rather than fabricated. File-change scope
is respected ... No CRITICAL or MAJOR findings; ship it."

## Outcome

PASS at round 1. Task marked done. No fixes required (both findings NIT,
non-blocking).
