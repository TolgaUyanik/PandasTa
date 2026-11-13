# auto-2026-11-13-ts-medskew-20 — manifest

`/brutally-honest-review --auto` (Mode C, one task), run headless by
issue-solver on branch `issue-98-ts-medskew-20`.

## Task

**TS-MEDSKEW-20** — port the indicator of PandasTa issue #98 through Gates
A–D, the five wiring touch points, the tests and
`docs/TsMedskew20Measured.md`.

Source line, verbatim from the issue: *mean-minus-median of returns over std
(20). Source: tsfresh feature_calculators (MIT) — `symmetry_looking,
continuous form: (mean-median)/std on 20 returns`.*

Gate E and both repos' suites in clean worktrees are run by the launcher
after this session.

## Clarifications

`AskUserQuestion` is unavailable in a headless run, so every ambiguity was
resolved by the most conservative (smallest-scope) reading and logged as an
ASSUMPTION below rather than asked.

### ASSUMPTIONS

1. **The formula is the ISSUE's, not the named function's.** Published
   `feature_calculators.symmetry_looking` compares `|mean - median|` against
   `r * (max - min)` and returns a BOOLEAN; the continuous
   `(mean - median)/std` form is issue #98's own wording. Gate A therefore
   starts from the issue's line, and the divergence is stated in the module
   docstring, in `docs/TsMedskew20Measured.md` §A0, and priced there
   (Spearman −0.194171 against the literal quantity).
2. **Simple returns**, `close/close.shift(1) - 1` — the screen prototype's
   `ret`. Log returns are priced at 0.999961 in §A5.
3. **20 RETURNS, so 21 closes**, first value at bar 20. The 20-closes (19
   returns) reading is priced at 0.918816 in §A5.
4. **`ddof=1`**, the prototype's `rolling.std()`. `ddof=0` is an exact
   rescaling by `sqrt(20/19)` (§A5b), invisible to a rank miner.
5. **The numerator keeps its SIGN** and there is no factor 3. Both
   alternatives are priced in §A5 (−0.206800 and an exact ×3).
6. **The dispersion floor is RELATIVE** (`4096 eps × max|r|`), not the
   absolute `4096 eps` of `ts_kurt_60` / `ts_binent_20` / `ts_c3_20`. Both
   are measured against each other in §G3; the relative one refuses strictly
   fewer honest windows while refusing every rounding-decided one.
7. **The window moments are computed from a `sliding_window_view` and the
   median from pandas' rolling skip list**, not from `rolling.mean()`/
   `rolling.std()`. The prototype's online accumulators are measured failing
   locality in §G7 (a 1e+8 spike moves later bars by 0.403).
8. **Gate E is NOT run here** (issue-solver's rule overrides the issue text),
   and `docs/TsMedskew20Measured.md` says "pending, run by issue-solver after
   this session". `tests/test_gate_e_ledger.py` fails locally until the
   receipt session records the row; that is expected.
9. **SHIP with disclosure, not a measured revert.** Every band with a
   real-frame measurement behind it says SHIP or DISCLOSE_GAP (§O3). The
   adverse pair — pooled 0.8428 against `TS_ABOVE_MEAN_20`, merged earlier
   the same day — is DISCLOSE_GAP under `r3-perframe-0.90` and is disclosed
   in five places. A question-redundancy skip on that pair is the owner's
   ruling to make, and §O3 names it as the reversal condition.
10. **Files outside the allowed-modify list were left alone.**
    `pandas_ta/statistics/ts_above_mean_20.py` and
    `docs/TsAboveMean20Measured.md` now contain stale claims that
    `ts_medskew_20` is "not shipped"; both are recorded in §O and in the
    commit message rather than edited.

## Execution map

| task | lane | why |
|---|---|---|
| TS-MEDSKEW-20 | main thread | one indicator, five wiring touch points plus docs; no independent sub-task worth isolating, and every file is shared |

## Files

New:

* `pandas_ta/statistics/ts_medskew_20.py`
* `tests/test_ts_medskew_20.py`
* `docs/measure_ts_medskew_20.py`
* `docs/measure_ts_medskew_20_cpu.py`
* `docs/TsMedskew20Measured.md`
* this folder

Modified:

* `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`,
  `pandas_ta/core.py` (touch points 2–4)
* `README.md`, `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 330 → 331)
