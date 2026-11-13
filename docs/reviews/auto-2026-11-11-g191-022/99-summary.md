# Run summary — `/brutally-honest-review --auto`, 2026-11-11, runid `g191-022`

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `g191-022` — port GTJA191 alpha `#22` as `g191_022` (Gates A–D, wiring, tests, receipt) | **PASS on the work, REVISE on the last review round** — the port and its measurements cleared every round; round 4's prose fixes landed with the review cap spent and were not re-reviewed | **4** (REVISE ×4; cap) | new: `pandas_ta/momentum/g191_022.py`, `tests/test_g191_022.py`, `docs/measure_g191_022.py`, `docs/G191022Measured.md`, this folder. modified: `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` | Gate E (the launcher's run) and the ledger row; the parent repo's suite |

## What shipped

Column `G191_022_6_3_12_1` in `momentum`, scale-free and causal:
`SMA((C-MEAN(C,6))/MEAN(C,6) - DELAY(that,3), 12, 1)` with GTJA's recursive
`SMA` as `ewm(alpha=1/12, adjust=False, min_periods=12)`. First fire bar 19,
`min_length` 20. `Category` 315 → 316 (`momentum` 80 → 81).

Measured (`python docs/measure_g191_022.py`, 1,500-bar close-only walk):
1,481 of 1,500 bars fire, 1,481 distinct, 749 positive / 732 negative / 0
zero, range `[-0.01020038, 0.01319801]`; price ×8/×64 bit-identical, ×10/×3.7
within 8.33e-17 / 5.81e-17, 0 bars change sign; 0 of 37 causality leaks
against 37 of 37 for each of three live mutants; bit-identical to the issue's
real prototype candidate on all 1,481 bars they share.

29 tests pass. Full suite: **3 failed, 5294 passed, 83 skipped** — the two
CLAUDE.md "Known breaks" plus the owed Gate E ledger row, which names
`['g191_022', 'mtd_ret']`.

## Review rounds

| round | verdict | findings | the one that mattered |
|---|---|---|---|
| 1 | REVISE | 3 MAJOR, 2 MINOR, 1 NIT | a MINOR: the `smi` comparator was selected positionally, so the issue's own Gate E top comparator (`SMIo_5_20_5`) was never measured. Fixed → **ρ 0.9116** on the synthetic frame, above the 0.90 strike line |
| 2 | REVISE | 1 MAJOR, 2 MINOR, 1 NIT | round 1's `wilder_rma` fix had introduced two new unopened citations |
| 3 | REVISE | 1 CRITICAL, 1 MAJOR, 2 NIT | round 2's added "0.8900 is 0.0002 under the strike line" — 0.90 − 0.8900 = 0.0100 |
| 4 | REVISE | 1 MAJOR, 2 NIT | the `smooth_weight` note promised a raise for "any `m > smooth_length`"; `m = 12.5` truncates to `alpha = 1.0`, raises nothing, and silently ships an unsmoothed column |

17 findings, **none a mathematics error**: every round reproduced every
number and failed the prose wrapped around it. Root pattern, not patched a
fifth time: derived figures are now written with the subtraction shown, and
no citation survives that was not opened in this session.

## Assumptions logged (no questions were possible — headless)

1. Category `momentum` (the inner term is the fork's own `bias`, a momentum
   indicator). 2. The source's subtraction spelling over the shipped `bias`
   helper's division spelling, so Gate A settles bit-for-bit against the
   prototype. 3. The fork's `min_periods=n` on the GTJA `SMA`, with the
   prototype's no-`min_periods` spelling measured alongside it. 4. Gate E
   and the parent repo's suite are the launcher's. 5. The `smooth_weight`
   guard left sibling-consistent rather than widened (narrower change), with
   its three `alpha` bands measured and documented instead.

## Open, by design

* **Gate E is pending**, run by issue-solver after this session. The
  synthetic 0.9116 against `smi:SMIo_5_20_5` says the strike line is in
  play; if the real run is STRUCK the column is reverted (or waived) and
  `docs/G191022Measured.md` stays as the receipt.
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails until the receipt session records the row. Expected (CLAUDE.md,
  "Owed, not failed").
* Round 4's fixes were not re-reviewed; the exact list is in
  `docs/G191022Measured.md`'s "Review record".
