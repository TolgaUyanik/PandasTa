# Run summary — `auto-2026-11-14-ts-q05-60`

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-q05-60` (PandasTa issue #101) | **PASS** at round 4 | 4 (REVISE, REVISE, REVISE, PASS) | 12: 6 new, 6 modified — listed in `01-ts-q05-60.md` | Gate E, run by the issue-solver launcher after this session; the receipt session then records the ledger row and replaces `test_the_gate_e_row_is_owed` with one pinning the row's identity |

## What shipped

`pandas_ta/statistics/ts_q05_60.py` — `TS_Q05_60`, the 5% quantile of 60
simple returns, a one-day historical VaR; tsfresh `quantile(q=0.05)` and
Lean's `ValueAtRisk` as issue #101 states them. All five wiring touch
points, 213 tests, `docs/TsQ0560Measured.md` as the receipt and
`docs/measure_ts_q05_60.py` as the evidence generator.

## The four rounds, in one line each

| round | verdict | findings | what it caught |
|---|---|---|---|
| 1 | REVISE | 2 MAJOR, 3 MINOR, 2 NIT | a `NATR_60` Spearman range that excluded a frame measured in this session's own receipt, propagated to five places; and "overflow is the ONE float error the ratio can raise", which underflow disproves and which made the advertised bound `(-1, +inf)` false |
| 2 | REVISE | 3 MAJOR, 1 MINOR, 3 NIT | all three MAJORs were defects INTRODUCED by round 1's fixes: a new unmeasured universal in the paragraph written to repair an unmeasured universal, four stale test counts after a test was added, and a "Round 2 — PASS" heading pre-written before the round ran |
| 3 | REVISE | 1 CRITICAL, 2 MAJOR, 2 MINOR, 2 NIT | quoting the round-2 verdict into this log tripped `test_no_other_document_retypes_the_split` and turned the suite red; and a round-2 fix adopted a reviewer's claim without running the section that disproves it |
| 4 | **PASS** | 3 MINOR, 2 NIT | bookkeeping only: the generator's own banner still printed the bound round 1 corrected, a count of bars labelled as windows, and this file asserted to exist before it did. All five applied on the way out |

The pattern is worth keeping: **nothing in four rounds was about the
mathematics.** Every reviewer re-ran the measurement sections and reported
each table reproducing to the digit. All twenty findings were sentences
that outran their runs — and three consecutive rounds of FIXES each
introduced a fresh one, which is the failure mode CLAUDE.md names as this
repo's dominant defect.

⚠ The five round-4 fixes landed AFTER the PASS and so are the only changes
in this branch no reviewer has seen. Four are prose; the fifth deletes an
unused parameter from a test signature. `01-ts-q05-60.md` says so too.

## Final runs

Made last, after every file in the branch was final:

* `python -m pytest tests/test_ts_q05_60.py -q` → **213 passed**.
* `python docs/measure_ts_q05_60_cpu.py` → **213 passed** with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.
* `python -m pytest -q` → **3 failed, 8,125 passed, 85 skipped**. The
  three are CLAUDE.md's known `test_pine_coverage_csv.py` break, the
  `../AlternativeRepos`-only regeneration test CI deselects by name, and
  the owed Gate E row, which reports `['arch_lm', 'diff2_acf1', 'edge',
  'firstzero_ac', 'halflife', 'lumpiness', 'mtd_ret', 'ts_q05_60']`.

## Assumptions logged (no questions were asked — headless session)

Eight, all listed with their readings and where each is priced, in
`00-manifest.md` Phase 2. The two that most change the column: `q = 0.05`
is a module constant rather than an argument, and the module has NO
dispersion floor and NO magnitude bound, both decisions measured in
`docs/TsQ0560Measured.md` §G3/§G4 rather than argued.
