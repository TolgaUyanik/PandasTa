# Task: rd-uwick-atr — log

## Implementation (main thread)

Ported `rd_uwick_atr` (issue #172, upper wick in ATR5 units) into `pandas_ta/candles/`:

- `pandas_ta/candles/rd_uwick_atr.py` — new module, `upper_wick = high - MAX(open, close)`,
  `RD_UWICK_ATR = upper_wick / ATR(5, mamode="wrma")`.
- Wiring: `pandas_ta/candles/__init__.py` (export), `pandas_ta/__init__.py` (`Category`
  entry), `pandas_ta/core.py` (`rd_uwick_atr` accessor).
- `tests/test_rd_uwick_atr.py` — 19 tests: hand-derived Gate A fixture, independent-loop
  cross-check, flat-run (epsilon-floor) behaviour, Gate B future-splice + mutant, Gate D
  power-of-two / non-power-of-two scale checks, reachability, wiring.
- `docs/measure_rd_uwick_atr.py`, `docs/measure_rd_uwick_atr_cpu.py` — reproduction
  scripts (the CPU one disables `AVX512F AVX512_SKX AVX2 FMA3` before numpy import).
- `docs/RdUwickAtrMeasured.md` — Gates A/B/D measured numbers, Gate C synthetic-only
  (no BIST cache in this worktree), Gate E marked pending (run by issue-solver after this
  session), Gate F command + result.
- Counters: `README.md` (398→399, 406→407, candles 8→9), `docs/IndicatorDictionary.md`
  (regenerated), `docs/MLCompanionContract.md` (743→744 tagged, 373→374 `SF`),
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 398→399).

Verification command run before and after the gate:
```
python -m pytest -q tests/test_rd_uwick_atr.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```
Result: 1,589 passed, 7 skipped, 1 failed — the single failure is
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected
per the issue-solver rules (no ledger row until the launcher's Gate E run and the receipt
session record it).

## Assumptions

See `00-manifest.md` — category placement (candles), ATR smoothing method (this fork's
`wrma`, carrying through the screen prototype's disclosed `atr_wilder` choice), column
naming (`RD_UWICK_ATR`, no suffix), MAE scope (excluded per the issue's own text).

## Gate — round 1

Fletcher reviewer (`Explore` subagent, read-only) dispatched against the full file set
below, with the original user ask verbatim and the repo's CLAUDE.md context.

**VERDICT: PASS**

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/candles/rd_uwick_atr.py:53-58 (Gate D docstring) and docs/RdUwickAtrMeasured.md "Gate D" section
    problem:  The power-of-two "bit-identical" argument is stated as an unconditional mathematical certainty ("(a*k)/(b*k) ... equal in every bit to a/b"), but it silently depends on the test frame containing no exact `high == low` tie. `true_range`'s `non_zero_range` adds a FIXED (unscaled) `sflt.epsilon` to the *entire* diff series the moment any single bar ties — not `k * epsilon` — so on a frame with a real tie (e.g. a BIST limit-lock day where O=H=L=C), the scaled and unscaled true-range paths would diverge by more than rounding, breaking the claimed bit-identity. The claim is correct for the measured frame (seed=4, continuous floats, no ties) but is not disclosed as conditional on tie-freedom.
    fix:      Add one sentence to the Gate D paragraph (module docstring + RdUwickAtrMeasured.md Decision 4 or the Gate D section) noting the power-of-two bit-identical claim holds only when `non_zero_range`'s epsilon floor is not triggered (no exact high==low bar anywhere in the series), consistent with Decision 4's own flat-run discussion of that same floor. This is shared, pre-existing `true_range`/`atr` infrastructure (not a regression introduced by this port) and every sibling ATR-based SF port in `MLCompanionContract.md` carries the identical unstated gap, so this is a documentation nit, not a correctness defect in this port specifically.
  - severity: NIT
    location: docs/reviews/auto-2026-11-25-rd-uwick-atr/00-manifest.md:44
    problem:  The manifest says "Fletcher reviewer dispatched per round below; log in `01-rd-uwick-atr.md`," but that file does not exist in the worktree at review time.
    fix:      Have the orchestrating process persist this review's verdict into `docs/reviews/auto-2026-11-25-rd-uwick-atr/01-rd-uwick-atr.md` as the manifest promises (not actionable by a read-only reviewer).
SUMMARY: This port is clean. Gate A's formula and the hand-derived fixture (bar2 = 4/8 = 0.5) check out by hand against `wilder_rma`'s actual SMA-seed-then-`ewm(adjust=False)` mechanics, and the independent per-bar loop cross-check reproduces to 2.776e-16 (one ulp). The Gate B mutant genuinely patches the unique, asserted write-site string, is live (differs from the real module), and is caught at all 28 swept splice points while the real module leaks at 0/28 — rerunning `docs/measure_rd_uwick_atr.py` and `docs/measure_rd_uwick_atr_cpu.py` reproduces every number in `docs/RdUwickAtrMeasured.md` exactly, including the Gate D x8/x64 (0 mismatches) and x10/x3.7 (1.865e-14 / 1.371e-14) figures. All five wiring touch points are present and consistent, matching the `rd_wick_pressure_10` sibling pattern bit for bit, and `test_accessor_matches_module_level` proves it live. Every counter bump (398→399, 406→407, 400→401, 743→744, 373→374, candles 8→9) is arithmetically correct and matches a live `python -m pytest` run that came back exactly as claimed: 1589 passed, 7 skipped, 1 failed (the expected, owed `test_gate_e_ledger` row). Scope is exactly the allowed file set — `git status`/`git diff` show nothing outside it, and `docs/gate_e_ledger.csv` is untouched. The only gap worth naming is a narrow, pre-existing, fork-wide (not port-specific) edge case in the "bit-identical under power-of-two" argument that the module's own epsilon-floor could in principle break on a tied high==low real-data bar — disclosable in one sentence, not a blocker.
```

## Fixes applied after PASS

Both NITs addressed even though PASS did not require it:

1. Added the tie-conditional disclosure sentence to the Gate D argument in both
   `pandas_ta/candles/rd_uwick_atr.py`'s module docstring and
   `docs/RdUwickAtrMeasured.md`'s Gate D section.
2. This file (`01-rd-uwick-atr.md`) now exists, closing the manifest's forward
   reference.

Re-ran the Gate F subset after the docstring/doc edits — still 1,589 passed, 7 skipped,
1 failed (the same expected `test_gate_e_ledger` failure); no test asserts docstring
text, so the edits are a documentation-only change confirmed not to affect behavior.

**Status: DONE.**
