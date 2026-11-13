# auto-2026-11-13-ts-above-mean-20 — manifest

`/brutally-honest-review --auto` (Mode C, one task), run headless by
issue-solver on branch `issue-97-ts-above-mean-20`.

## Task

**TS-ABOVE-MEAN-20** — port the indicator of PandasTa issue #97 through
Gates A–D, the five wiring touch points, the tests and
`docs/TsAboveMean20Measured.md`.

Source line, verbatim from the issue: *share of returns above the window mean
(20). Source: tsfresh feature_calculators (MIT) — `count_above_mean / n on 20
returns`.*

Gate E and both repos' suites in clean worktrees are run by the launcher
after this session.

## Clarifications

`AskUserQuestion` is unavailable in a headless run, so every ambiguity was
resolved by the most conservative (smallest-scope) reading and logged as an
ASSUMPTION below rather than asked.

### ASSUMPTIONS

1. **Simple returns**, `close/close.shift(1) - 1` — the screen prototype's
   `ret`. Log returns are a different column and are priced in
   `docs/TsAboveMean20Measured.md` §A5 (Spearman 0.983938).
2. **20 RETURNS, so 21 closes**, first value at bar 20. The 20-closes (19
   returns) reading is priced at 0.888618 in §A5.
3. **Strict `>`**, the source's `np.where(x > np.mean(x))[0].size`. No
   generated frame can see this choice (0 exact ties in 29,600 window/return
   pairs), so it is pinned by a constructed window instead.
4. **The SHARE**, not the raw count — the issue says `count_above_mean / n`.
   An exact rescaling either way.
5. **`length` is a parameter with default 20**, and the column name carries
   it (`TS_ABOVE_MEAN_{length}`), which is this fork's habit for a window
   that appears in the name.
6. **The dispersion floor is RELATIVE** (`4096 eps × max|r|`), not the
   sibling ports' absolute `4096 eps`. Both are measured against each other
   in §4 of the receipt; the relative one is the smaller-scope choice in the
   sense that matters here — it refuses strictly fewer honest windows while
   refusing every rounding-decided one that the absolute floor refuses.
7. **Gate E is NOT run here** (issue-solver's rule overrides the issue text),
   and `docs/TsAboveMean20Measured.md` says "pending, run by issue-solver
   after this session". `tests/test_gate_e_ledger.py` fails locally until the
   receipt session records the row; that is expected.

## Execution map

| task | lane | why |
|---|---|---|
| TS-ABOVE-MEAN-20 | main thread | one indicator, five wiring touch points plus docs; no independent sub-task worth isolating, and every file is shared |

## Files

New:

* `pandas_ta/statistics/ts_above_mean_20.py`
* `tests/test_ts_above_mean_20.py`
* `docs/measure_ts_above_mean_20.py`
* `docs/measure_ts_above_mean_20_cpu.py`
* `docs/TsAboveMean20Measured.md`
* this folder

Modified:

* `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`,
  `pandas_ta/core.py` (touch points 2–4)
* `README.md`, `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 329 → 330)
