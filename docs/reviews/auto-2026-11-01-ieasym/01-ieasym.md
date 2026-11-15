# Task: IEASYM (issue #28) — log + review rounds

## Implementation summary

- `pandas_ta/statistics/ie_asym.py`: `IE_n = (#{r > mean+mult*std} - #{r < mean-mult*std}) / length`
  over rolling log-returns, default `length=260`, `mult=2.0`, column `IEASYM_260_2.0`.
- Wired all five touch points: module, `pandas_ta/statistics/__init__.py` export,
  `pandas_ta/__init__.py` `Category["statistics"]`, `pandas_ta/core.py` accessor,
  `tests/test_ie_asym.py` (14 tests).
- Gate A: no Pine/TA-Lib source exists for this formula; checked against an independent
  loop + two hand-computed windows (same pattern as `pfe`). Kept the issue's own `IE_n`
  formula rather than switching to a catalogued alternative (Rachev ratio / vol ratio /
  `ratio_beyond_r_sigma`) — logged as ASSUMPTION 1 in `00-manifest.md`.
- Gate B: 20-offset future-perturbation mutant test. Real module 0/20 leaks. Two
  look-ahead mutants caught 18/20 — diagnosed and documented (not papered over) as a
  measured property of a discrete tail-count statistic, not a test defect.
- Gate D: x8/x64 bit-identical, x10/x3.7 max diff measured 0.0, `0 < 846 fires < 940`.
- Gate C: synthetic only (846-850/940 nonzero depending on tick rounding); real-data
  counts left OWED to the launcher's Gate E run, per the issue-solver rules.
- `docs/IeAsymMeasured.md` written with every gate's evidence, the Gate A decision
  rationale, the mutant-miss diagnosis, and a proxy-overlap check against the issue's own
  guessed comparators (`skew`, `max_return`, `natr` — all well under the 0.76 ship line
  on synthetic data).
- README.md / docs/IndicatorDictionary.md / docs/MLCompanionContract.md counts updated
  (261 Category, 269 `df.ta` accessors, 20 statistics, 597 tagged / 242 `SF`).
  `tests/test_altport2_ports.py`'s pinned `CATEGORY_TOTAL` bumped 260 -> 261.
- Full local suite: 3 failed (all pre-existing/expected: `test_pine_coverage_csv`,
  `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows`,
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`) / 3,843 passed
  / 83 skipped.

## Review round 1

Dispatched Fletcher reviewer (`Explore` subagent, read-only) against the full diff.

**VERDICT: REVISE**

Findings (verbatim):
- MAJOR — `tests/test_ie_asym.py:29-31`: module docstring mislabeled Gate D's
  `0 < fires < n` evidence as "850 of 940 ... on a 1,200-bar tick-rounded walk" when
  850/90 is actually the NO-tick-rounding numbers; the tick-rounded walk's real numbers
  (846/94) are used correctly a few lines later in the same file.
- MINOR — `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` historical comment chain not
  extended for this port's 260->261 bump.
- MINOR — `docs/IeAsymMeasured.md` missing the issue's own guessed-comparator proxy check
  (`skew`/`max_return`/`natr`), which sibling receipts include informally before Gate E.
- NIT — docstring said "roughly [-1, 1]" when the range is exact by construction.
- NIT — `_asym` divides by `len(window)`, not the fixed `length`; undocumented for
  `min_periods < length` callers.

## Fixes applied

- Corrected the mislabeled numbers in `tests/test_ie_asym.py` (846/94, matching the
  tick-rounded walk).
- Extended `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` comment chain with the
  `ie_asym` entry.
- Added a "Proxy overlap (NOT Gate E)" section to `docs/IeAsymMeasured.md` with measured
  Spearman ρ against `skew` (-0.0479), `max_return` (0.2647), `natr` (0.0646), n=940 each.
- Tightened `pandas_ta/statistics/ie_asym.py`'s docstring: "exactly bounded to [-1, 1] by
  construction", and documented the `min_periods < length` denominator caveat.
- Re-ran the affected test modules (53 passed, 3 skipped) before re-committing.

## Review round 2

Re-dispatched the same reviewer pattern against the fix commit.

**VERDICT: PASS** — no findings. All five round-1 items verified fixed (reviewer re-ran
`docs/measure_ie_asym.py` and the affected test modules itself); no new issue introduced.

## Outcome

PASS at round 2 (of the 3-round cap). Task complete.
