# Manifest — C22-STRETCH-DECREASING (issue #140)

**Mode:** C (batch task execution), single task.

## Phase 1 — Select

Task (verbatim from the invocation): port the indicator of issue #140
through Gates A-D, the wiring, the tests and `docs/<Name>Measured.md`, per
the issue and the rules in the issue-solver system prompt. catch22 longest
run of falling returns (100). Source: catch22 (Lubba et al. 2019, DMKD
33:1821; reference code pycatch22 1.0.2, GPL-3.0 — port from the
definitions) — `SB_BinaryStats_diff_longstretch0` on the last 100 daily
returns. Gate E and the whole suites are run by the launcher afterwards.

Run folder: `docs/reviews/auto-2026-11-22-c22-stretch-decreasing/`.

## Phase 2 — Clarify

AskUserQuestion is unavailable in this issue-solver session (system prompt
rule). Gaps found and resolved by the most conservative (smallest-scope)
reading, logged as ASSUMPTIONS rather than asked:

- **ASSUMPTION (the sign convention for "falling").** catch22's own
  published one-line description is "longest period of successive
  decreases"; the feature's binarization convention (`diff < 0` vs
  `diff <= 0`) is not pinned by that description, and hctsa's source was
  not read (GPL-3.0). Chose the STRICT reading (`diff < 0`; a diff of
  exactly zero is FLAT, not falling, and breaks the run) as the literal,
  smallest-surprise reading of "falling" and "decrease" — a flat/repeated
  return is not a decrease. Disclosed explicitly in the module docstring
  as a choice the definition does not pin.
- **ASSUMPTION (z-score skipped).** catch22's pipeline z-scores every
  window before every feature. Proved (not assumed) that the z-score is
  INERT for this specific feature: it is an affine map with positive slope
  for `sd(x) > 0`, and `diff(a*x + b) = a * diff(x)`, so a positive `a`
  cannot flip the sign a diff-based run statistic reads. The module skips
  computing and discarding it.
- **ASSUMPTION (MIN_LENGTH = 2).** A 1-return window has zero diffs and is
  a forced constant 0 (no information); a 2-return window has exactly one
  diff whose sign is data-dependent, so it is already informative — unlike
  `ts_strike_20`'s analogous length=2, which is a forced constant there.
  Set the floor at the smallest length that is NOT a forced constant.
- **ASSUMPTION (NOISE_FLOOR reused).** Reused this fork's existing
  `NOISE_ULPS = 4096` / `NOISE_FLOOR` convention on the window's own return
  SPAN (not on each diff individually) to blank an exactly-flat window to
  0 rather than report a run read off float64 rounding noise — the same
  habit `ts_strike_20`, `ts_binent_20`, `ts_c3_20` and `lean_hurst_100` use
  on a dimensionless return quantity, re-derived (not copy-pasted blind)
  for this statistic: verified by the engineered-ladder test that the
  guard is live and costs nothing on real-shaped frames.
- No destructive or irreversible steps were in scope for this task; none
  were skipped.

## Phase 3 — Plan execution

Single task, no parallel lanes. Executed on the main thread (porting a
financial-feature indicator needs continuous judgment — picking the
binarization reading, deriving the Gate A oracle, designing a Gate B proof
sensitive enough for a tie-heavy statistic — that does not decompose into
independent subagent-sized pieces without duplicating context).

## Phase 4 — Execute + gate

Implementation: `pandas_ta/statistics/c22_stretch_decreasing.py`,
`tests/test_c22_stretch_decreasing.py` (90 tests),
`docs/measure_c22_stretch_decreasing.py`,
`docs/measure_c22_stretch_decreasing_cpu.py`,
`docs/C22StretchDecreasingMeasured.md`, wiring in `pandas_ta/__init__.py` /
`pandas_ta/core.py` / `pandas_ta/statistics/__init__.py`, count updates in
`README.md` / `docs/MLCompanionContract.md` / `tests/test_altport2_ports.py`,
regenerated `docs/IndicatorDictionary.md`.

Verification commands run (all green except the expected pending-Gate-E
failure):
`python -m pytest -q tests/test_c22_stretch_decreasing.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ 1,436 passed, 7 skipped, 1 failed
(`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
expected per the issue-solver rules).
`python docs/measure_c22_stretch_decreasing_cpu.py disable pytest`
(AVX512F/AVX512_SKX/AVX2/FMA3 disabled) → 90 passed.

Gate review: see `01-c22-stretch-decreasing.md`.
