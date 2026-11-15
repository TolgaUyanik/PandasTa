# Run summary — `/brutally-honest-review --auto`, 2026-11-13

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| TS-CROSS-MEAN-20 (issue #100) | ESCALATED — four review rounds, all REVISE; all 21 findings applied, the last five unreviewed | 4 (the cap) | `pandas_ta/statistics/ts_cross_mean_20.py`, `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_ts_cross_mean_20.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/TsCrossMean20Measured.md`, `docs/measure_ts_cross_mean_20.py`, `docs/measure_ts_cross_mean_20_cpu.py` | Gate E (launcher), then the receipt session: ledger row, Gate C's real-data counts, and deletion of `test_the_gate_e_row_is_still_owed` |

## What shipped

`TS_CROSS_MEAN_20` — how many of the 19 adjacent pairs of a 20-bar window
of **log closes** sit on opposite sides of that window's own mean.
tsfresh's `number_crossing_m(x, m=mean)`, the issue's line, the screen
prototype's exact arithmetic. A dimensionless integer on 1 .. 19.

Verdict: **ship, pending Gate E**, and the receipt names what would
reverse it (a run at pooled |ρ| ≥ 0.90, or a top-5 comparator's per-frame
median ≥ 0.90). The screen measured its prototype at 0.5500 vs
`BB_BWidth_Pctl`, and this port is bit-equal to that prototype on 1,481 of
1,481 bars of each of nine frames.

## Review rounds

| round | verdict | findings | the one that mattered |
|---|---|---|---|
| 1 | REVISE | 2 MAJOR, 3 MINOR, 2 NIT | a shipped comment claiming an absolute floor "would never fire at all", citing a run that prints the opposite |
| 2 | REVISE | 2 MAJOR, 4 MINOR, 2 NIT | round 1's own fix invented "seven of the eight admitted buckets" where the table it had just printed has six |
| 3 | REVISE | 3 MAJOR, 1 MINOR, 1 NIT | round 2's fix log declared a correction it had not made, and the retracted count was still in a committed file |
| 4 | REVISE (cap) | 1 MAJOR, 3 MINOR, 1 NIT | round 3's fix credited two double-against-double checks with 17,772 windows of exactness they cannot witness |

Every round re-ran all seven measurement sections, the test module, the
CPU-restricted re-run and the full suite, and every round reported every
STRUCTURAL figure reproducing to the digit. **Not one finding in four
rounds was about the mathematics.** All twenty-one were sentences that
outran their runs — and three consecutive generations of fixes each
introduced a fresh one, which is the single most useful thing this log
records.

## Final state

* `python -m pytest tests/test_ts_cross_mean_20.py -q` → 205 passed.
* `python docs/measure_ts_cross_mean_20_cpu.py` → the same 205 with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.
* `python -m pytest -q` → 3 failed, 7,521 passed, 85 skipped — the
  `CLAUDE.md` Known break, the `../AlternativeRepos`-only test CI
  deselects, and the owed Gate E row (`['halflife', 'mtd_ret',
  'ts_cross_mean_20']`).
* Gate E: **owed**, run by issue-solver after this session.

## Escalation, stated plainly

The loop's cap is four rounds and round 4 ended on REVISE, so the five
round-4 fixes are the only changes in this session no reviewer has seen.
All five are prose corrections with their run quoted beside them; none
touches the computation, and the module's output is bit-identical to what
all four rounds measured. The open risk is therefore not a wrong number in
the column — it is the possibility of one more wrong sentence about it.
