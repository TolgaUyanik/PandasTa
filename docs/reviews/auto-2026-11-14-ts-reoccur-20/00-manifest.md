# auto run 2026-11-14 — `ts-reoccur-20`

`/brutally-honest-review --auto "TS-REOCCUR-20: port the indicator of
issue #103 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system
prompt (share of repeated closes (20). Source: tsfresh
feature_calculators (MIT) —
`percentage_of_reoccurring_datapoints_to_all_datapoints on 20 closes`.).
Gate E and the suites are run by the launcher afterwards."`

**Mode C** (batch task execution). The argument is a free-form task
reference, not a plan file, so Mode B's step-0 pre-gate does not apply —
Mode C has no pre-gate by design.

## Phase 1 — the resolved task list

| id | scope | source |
|---|---|---|
| `ts-reoccur-20` | Port tsfresh's `percentage_of_reoccurring_datapoints_to_all_datapoints` over 20 closes as `pandas_ta/statistics/ts_reoccur_20.py`, through Gates A–D, the five wiring touch points, `tests/test_ts_reoccur_20.py` and `docs/TsReoccur20Measured.md`. Gate E and both repos' suites are the launcher's. | PandasTa issue #103 (headless issue-solver run, branch `issue-103-ts-reoccur-20`) |

Run folder: `docs/reviews/auto-2026-11-14-ts-reoccur-20/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, and the
session's rules say to take the most conservative (smaller-scope)
reading and log it. **No questions were asked.** The readings taken:

| # | ambiguity | conservative reading taken | where it is priced |
|---|---|---|---|
| A1 | which tsfresh function — `…_datapoints_to_all_datapoints` or the sibling `…_values_to_all_values` | the one the issue NAMES (datapoints), i.e. the share of the window's BARS | §A4 measures the sibling as a different column (\|ρ\| 0.9726 … 1.0000, 1 to 1,346 of 1,481 bars equal) |
| A2 | tsfresh is not installed and web access is unavailable | Gate A checks the quantity the source's NAME states, spelled two independent ways, and the docstring says tsfresh's own source was NOT read | `test_the_source_library_is_not_installed_here`, receipt header |
| A3 | the window: 20 closes or 20 returns | 20 CLOSES, the issue's own word | §A4: on returns it is a different column, \|ρ\| 0.1637 … 0.6553 |
| A4 | a missing close: the source deflates the share, this fork empties the window | empty the window — the narrower output, and every `statistics/` sibling's rule | §A4's last table (361 vs 381 fired bars) |
| A5 | equality: exact or within a tolerance | EXACT, which is the source's own test | §A4: 1e-12 changes nothing, 1e-4 changes the price-100 frame (1e-4 of 100 IS one tick) |
| A6 | `length` as an argument: free, or fixed at 20 | kept as an argument with a floor of 2 and the default 20, exactly as every sibling in `statistics/` does; the column name carries it | `test_a_length_below_the_minimum_falls_back_to_the_default` |
| A7 | a second column (e.g. the `has_duplicate` boolean, or the distinct-value share) | ONE column. More columns is more scope and more Gate E surface | §A4 prices both as variants |
| A8 | Gate E | NOT run here (the session's rules forbid touching `../Backtesting`); the receipt says "pending, run by issue-solver after this session" and a test asserts the ledger row is absent | §E, `test_the_gate_e_row_is_owed` |

**ASSUMPTION (A9).** `docs/issues/screen/ind_screen.py` is present in
this worktree as a read-only, gitignored copy of the owner's tracker, so
the prototype's exact spelling (`w_pct_reoccurring`) was read rather
than guessed. It is quoted in the receipt and retyped in the test
module; nothing under `docs/issues/` is staged.

**No destructive or irreversible step was reached**, so Mode C's hard
limit never bound: no push, no deploy, no delete, no external post. The
launcher pushes.

## Phase 3 — the execution map

| task | lane | why |
|---|---|---|
| `ts-reoccur-20` | **main thread** | One task, one file scope, and every step needs main-context judgment against `CLAUDE.md`'s gate table and the sibling ports. Nothing to parallelise and no worktree isolation needed. |

Reviewer lanes are fresh read-only `Explore` subagents, as Mode C
requires; the gate is never skipped.

## Files the task may touch (the session's own list)

* **modify**: `README.md`, `docs/IndicatorDictionary.md`,
  `docs/MLCompanionContract.md`, `pandas_ta/__init__.py`,
  `pandas_ta/core.py`, `pandas_ta/statistics/__init__.py`,
  `tests/test_altport2_ports.py`;
* **add**: `pandas_ta/statistics/ts_reoccur_20.py`,
  `tests/test_ts_reoccur_20.py`, `docs/TsReoccur20Measured.md`,
  `docs/measure_ts_reoccur_20.py`, `docs/measure_ts_reoccur_20_cpu.py`,
  this folder.

`docs/gate_e_ledger.csv` is in the modifiable list and is deliberately
**not** touched: the row is owed.
