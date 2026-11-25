# Manifest — C22-HIGH-FLUCTUATION (issue #144)

**Mode:** C (batch task execution), single task.

## Phase 1 — Select

Task (verbatim from the invocation): port the indicator of issue #144
through Gates A-D, the wiring, the tests and `docs/<Name>Measured.md`, per
the issue and the rules in the issue-solver system prompt. catch22 share of
successive return changes above 0.04 sd (100). Source: catch22 (Lubba et
al. 2019, DMKD 33:1821; reference code pycatch22 1.0.2, GPL-3.0 — port from
the definitions) — `MD_pNN_pnn40` on the last 100 daily returns. Gate E and
the whole suites are run by the launcher afterwards.

Run folder: `docs/reviews/auto-2026-11-23-c22-high-fluctuation/`.

## Phase 2 — Clarify

AskUserQuestion is unavailable in this issue-solver session (system prompt
rule). Gaps found and resolved by the most conservative (smallest-scope)
reading, measured rather than guessed, and logged as ASSUMPTIONS:

- **ASSUMPTION (the generalised pNNx definition).** The issue's own prose
  ("share of successive return changes above 0.04 sd") and catch22's
  published `MD_pNNx` family description (an HRV pNN50 generalisation:
  z-score the series, count successive differences exceeding a fixed
  absolute threshold) pin the formula without needing the GPL-3.0
  reference code: `Z = zscore(window, ddof=1)`, `share = mean(|diff(Z)| >
  0.04)`. No part of this needed the reference implementation.
- **ASSUMPTION (`ZSCORE_DDOF = 1`).** Matches this fork's existing
  catch22-port convention (`c22_median_freq`), MATLAB `zscore`'s default
  and hctsa being MATLAB. Documented as load-bearing here (unlike
  `c22_median_freq`, where it is inert) since it genuinely moves which
  diffs clear 0.04.
- **ASSUMPTION (`MIN_LENGTH = 3`, not 2).** Measured (not guessed) via
  `docs/measure_c22_high_fluctuation.py min_length`: a 2-return window is a
  forced constant 1.0 over 3,000 random draws (z-scoring 2 values with
  ddof=1 always places them at ±1/sqrt(2), so the one diff is a forced
  sqrt(2) ≈ 1.4142, always above 0.04); a 3-return window reaches both 0.5
  and 1.0 over 30,000 draws, so it is the smallest genuinely data-dependent
  length and the chosen floor.
- **ASSUMPTION (`NOISE_FLOOR` reused on the window's own return standard
  deviation).** Reused this fork's existing `NOISE_ULPS = 4096` /
  `NOISE_FLOOR` convention (`c22_median_freq`, `c22_mode_10`,
  `c22_stretch_decreasing`), guarding the z-score's own divisor (`sd`)
  rather than re-deriving a new floor, since dividing by a near-zero
  standard deviation is exactly the failure mode the convention exists to
  prevent.
- No destructive or irreversible steps were in scope for this task; none
  were skipped.

## Phase 3 — Plan execution

Single task, no parallel lanes. Executed on the main thread (porting a
financial-feature indicator needs continuous judgment — deriving the Gate A
oracle, picking `MIN_LENGTH` from a measured probe, designing Gate B
mutants, and reconciling four cross-referencing doc/count files — that does
not decompose into independent subagent-sized pieces without duplicating
context).

## Phase 4 — Execute + gate

Implementation: `pandas_ta/statistics/c22_high_fluctuation.py`,
`tests/test_c22_high_fluctuation.py` (87 tests),
`docs/measure_c22_high_fluctuation.py`,
`docs/measure_c22_high_fluctuation_cpu.py`,
`docs/C22HighFluctuationMeasured.md`, wiring in `pandas_ta/__init__.py` /
`pandas_ta/core.py` / `pandas_ta/statistics/__init__.py`, count updates in
`README.md` / `docs/MLCompanionContract.md` / `tests/test_altport2_ports.py`,
regenerated `docs/IndicatorDictionary.md`.

Verification commands run (all green except the expected pending-Gate-E
failure):
`python -m pytest -q tests/test_c22_high_fluctuation.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ 1,481 passed, 7 skipped, 1 failed
(`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
naming only `c22_high_fluctuation` as the missing row — expected, per the
issue-solver rules).
`python docs/measure_c22_high_fluctuation_cpu.py disable pytest`
(AVX512F/AVX512_SKX/AVX2/FMA3 disabled, confirmed present on this CPU before
disabling) → 87 passed.

Gate review: see `01-c22-high-fluctuation.md`.
