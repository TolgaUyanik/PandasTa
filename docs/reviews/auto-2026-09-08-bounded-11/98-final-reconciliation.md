# 98 — The single end-of-run reconciliation

Three agents edited this repo concurrently (PINEBI-1c, TALIB-1, CANDLE-1), so
counts and generated artefacts were a moving target all afternoon. Rather than
regenerate repeatedly against a tree still being written, every count-bearing
artefact is reconciled ONCE, here, after all three land.

Doing it piecemeal is what produced two false accusations earlier in this run:
CANDLE-0 was told it "invented" a Category discrepancy that the main thread had
in fact caused mid-flight, and INDREF-0 spent a round proving six suite failures
were not its own.

## Run, in this order

1. `python docs/gen_indicator_dictionary.py`
2. `python docs/gen_pine_builtin_coverage.py`
3. `python docs/gen_altrepo_pandas_ta_classic.py`
4. `python docs/gen_altrepo_tti.py`
5. `python docs/gen_altrepo_talib.py`
6. `python docs/gen_altrepo_ptclassic_divergence.py`
7. `python docs/gen_indicator_list_tables.py`
8. `python docs/verify_gap_rows.py {pandas-ta-classic,tti,ta-lib}` — all three
   must report `reproducible: {}`
9. Reconcile by hand from the regenerated dictionary: `README.md` headline
   count, accessor count, and every per-category count; `CLAUDE.md`'s two
   adjacent counts; `docs/MLCompanionContract.md`'s tagged-column line.
10. `python -m pytest -q > out.txt 2>&1; echo "PYTEST_EXIT=$?"` — capture
    pytest's OWN status. Piping into `tail` reports tail's, which misled two
    agents today.

## Known-red going in, with the cause already identified

| test | cause | closes on |
|---|---|---|
| `test_altrepo_ptclassic_csv::test_have_rows_carry_a_receipt_that_opens` | the raw-docstring fix in `pandas_ta/utils/_pine.py` added 5 comment lines, shifting every `_pine.py:NNN` receipt by **+5** (`highest` 109→114, `lowest` 121→126, `correlation` 249→254) | step 3 |
| `test_altrepo_ptclassic_csv::test_regenerating_reproduces_the_committed_verdicts` | `rolling_sum` moved `port - alternate impl` → `have` when PINEBI-1e shipped it | step 3 |
| `test_readme_counts` ×3 | PINEBI-1c (+7) and CANDLE-1 (+4 so far) landed after the last reconciliation | step 9 |

⚠ **Fix the receipts, never the guard.** The receipt test opens each cited file
and checks the token is on that line; a stale line number is supposed to fail
loudly. PINEBI-1c hit the same thing with `pine_builtin_coverage.csv` and
correctly bumped the receipts. The one guard edit that WAS legitimate this run
was a false positive: `test_no_other_document_retypes_the_split` matched
`report 25` as the verdict `port` because its regex lacked a leading `\b`.

## Last known-good

`PYTEST_EXIT=0`, **1483 passed, 22 skipped**, 11m29s — taken after the CANDLE-2
work and the first regeneration pass, before TALIB-1 and CANDLE-1 landed. It
certifies that point, not the end state.
