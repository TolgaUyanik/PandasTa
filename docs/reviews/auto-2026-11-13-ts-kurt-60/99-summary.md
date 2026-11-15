# Run summary — 2026-11-13, `ts-kurt-60` (PandasTa issue #93)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-kurt-60` | **DELIVERED, last review round REVISE** — the round-4 findings were applied and no fifth review was run (the session's four-round cap). All four were documentation accuracy; none touched the indicator's arithmetic. | 4 (round 1 + 3 re-runs) | **new:** `pandas_ta/statistics/ts_kurt_60.py`, `tests/test_ts_kurt_60.py`, `docs/TsKurt60Measured.md`, `docs/measure_ts_kurt_60.py`, this run folder · **modified:** `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E (launcher); the Gate E ledger row and Gate C's real-data counts (a later receipt session); the absolute timings in §Cost are machine-dependent and could be reduced to ratios if they keep drifting |

## Verdicts

| round | verdict | findings | the one that mattered |
|---|---|---|---|
| 1 | REVISE | 1 CRITICAL, 4 MAJOR, 2 MINOR, 1 NIT | A §A4 superlative false against its own table — and an undisclosed defect: one astronomically large return made every LATER bar NaN (199 of 400), which became a code change rather than a disclosure |
| 2 | REVISE | 1 CRITICAL, 2 MAJOR, 4 MINOR, 1 NIT | Two of round 1's findings came back in files the first pass did not grep; and the new guard's locality was provable false for TWO large returns in one window |
| 3 | REVISE | 1 CRITICAL, 4 MINOR, 2 NIT | The Cost section's conclusion was inverted and rested on one anomalous reading |
| 4 | REVISE | 1 MAJOR, 2 MINOR, 1 NIT | The Cost numbers still did not reproduce (84 ms against the reviewer's 55, twice), and this run folder's own promise of a log was unmet |

Every verdict is quoted in full in `01-ts-kurt-60.md`.

## What the review loop actually changed in the shipped column

Not prose only. Three code decisions came out of it:

1. **The arithmetic.** The first implementation was a hand-rolled numpy
   two-pass form; the first measurement run showed it was bit-equal to the
   screened prototype on only 38 of 1,440 bars, so pandas'
   `rolling(length).kurt()` was kept instead and the numpy form became the
   oracle. The port and the column issue #93's Gate E figures were taken on
   are now the same arithmetic (1,440/1,440 on three frames).
2. **The fourth-power guard** (round 1's third MAJOR, hardened in round 2):
   without it one finite-but-huge return empties every later bar — 199 of 400
   measured — because `rolling.kurt` accumulates power sums online. It bounds
   the window SUM, not the single term, because two returns whose fourth
   powers are each finite can sum past the float maximum (199 emptied bars
   against 91, measured).
3. **Its spelling** (round 3): `np.square(np.square(r))` rather than
   `r ** 4`, bit-equal on 1,940/1,940 bars and about 19 ms cheaper on a
   400,000-bar frame.

## Counts, from the runs

* `python -m pytest tests/test_ts_kurt_60.py -q` → **149 passed**, and clean
  under `-W error::RuntimeWarning`.
* Full suite → **3 failed, 6443 passed, 83 skipped**. The three are the two
  `CLAUDE.md` *Known breaks* (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`) plus
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  which reports exactly `['mtd_ret', 'ts_kurt_60']` — the owed Gate E row,
  expected until the launcher's run is recorded.
* `Category` total 325 → **326**; `statistics` 34 → **35**; the dictionary's
  tagged-column total 670 → **671**, `SF` 312 → **313**.

## Assumptions logged (no questions were possible)

`AskUserQuestion` is unavailable in this headless session, so every
ambiguity took the smaller-scope reading. The six are in `00-manifest.md`;
the two that would be worth a second opinion are A5 (keep `rolling.kurt`
rather than re-derive the moments — decided by measurement, §A4 of the
receipt) and A4 (a degenerate window reads NaN, where the two pandas
spellings of the source read −3.0 and 0.0 respectively).
