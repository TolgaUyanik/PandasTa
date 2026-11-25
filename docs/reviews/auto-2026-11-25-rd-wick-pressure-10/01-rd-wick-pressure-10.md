# Task 01 — rd-wick-pressure-10

## Implementation summary

Ported issue #170's `rd_wick_pressure_10` (candles): trailing sum of lower wicks on bear
candles minus trailing sum of upper wicks on bull candles, over 10 bars, divided by the
trailing sum of ranges. Gate A read from the issue's own restated formula, not the screen
prototype. Files:

- `pandas_ta/candles/rd_wick_pressure_10.py` (new)
- `tests/test_rd_wick_pressure_10.py` (new, 19 tests)
- `docs/measure_rd_wick_pressure_10.py`, `docs/measure_rd_wick_pressure_10_cpu.py` (new)
- `docs/RdWickPressure10Measured.md` (new)
- Wiring: `pandas_ta/candles/__init__.py`, `pandas_ta/__init__.py` (`Category`),
  `pandas_ta/core.py` (accessor)
- Counters: `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 397 → 398), `README.md`,
  `docs/MLCompanionContract.md`, `docs/IndicatorDictionary.md` (regenerated)

Gate E and whole-suite runs are owed to the launcher, per the issue-solver system prompt;
`docs/RdWickPressure10Measured.md` records "Gate E: pending, run by issue-solver after
this session" rather than a SHIP/STRUCK verdict.

Assumption logged: none needed — the issue's own text and the launcher's system prompt
fully specified scope (Gates A-D + wiring + tests + Measured.md; no Gate E/F in this
session).

## Review round 1

VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/candles/rd_wick_pressure_10.py:89 and docs/RdWickPressure10Measured.md Decision 4
    problem:  The `.replace([np.inf, -np.inf], np.nan)` guard is dead code on every path exercised by the tests (zero-range case already yields 0/0 = NaN directly, never ±inf); the claim it is defensive-only is correct but untested by anything in this PR.
    fix:      No functional change needed; purely a documentation/comment nit, not blocking.
  - severity: NIT
    location: docs/RdWickPressure10Measured.md Gate C section
    problem:  "spanning roughly −0.23 to +0.30 across seeds" rounds instead of quoting the already-computed literal extremes (−0.2276 to 0.3013).
    fix:      Could quote the literal numbers instead of rounding; cosmetic only.
SUMMARY: Gate A's fixture hand-checks correctly against the issue's own restated formula
(1/15 and -1/16 verified by hand), the denominator's prototype-sourced provenance is
disclosed rather than smuggled in as the issue's own, the Gate B mutant is a live
`importlib`/`exec` source mutation proven live and caught at all 28 swept splice points,
Gate D correctly demands bit-identical equality for the power-of-two case and a tight
1e-9 tolerance for the non-power-of-two case, every number in RdWickPressure10Measured.md
reproduced byte-for-byte on re-run, the five wiring touch points are all present and
correctly forward `length`/`offset`, and `git status --porcelain` showed nothing outside
the allowed path list with exactly one new `pandas_ta/<category>/*.py` file.

No fixes applied — both findings are NIT-level and PASS does not require action.
