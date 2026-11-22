# Auto run 2026-11-20 — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `c22-dfa` (issue #128) | **PASS** (round 4, the cap; its four findings were then fixed — see the note in `01-c22-dfa.md`) | 4 | `pandas_ta/statistics/c22_dfa.py` (new), `tests/test_c22_dfa.py` (new, 186 tests), `docs/measure_c22_dfa.py` (new), `docs/measure_c22_dfa_cpu.py` (new), `docs/C22DfaMeasured.md` (new), `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E and Gate C's real-data limb are owed to the launcher's run; the receipt session records the ledger row and swaps `test_the_gate_e_row_is_owed` for tests that pin it |

## What shipped

`C22DFA_100` in `statistics`: catch22's `SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1` over the
last 100 daily simple returns — where the detrended fluctuation curve of the return
profile breaks from one power law to another, reported as the share of the 21 box sizes
in the first piece of a two-piece log-log fit. Six possible values at the default
`length`, 8/21 .. 13/21.

## The rounds

| round | verdict | findings | the one that mattered |
|---|---|---|---|
| 1 | REVISE | 2 MAJOR, 4 MINOR, 1 NIT | `_prop_rows`'s docstring named the residual NORMS — the reading the port's first attempt got wrong — while the kernel minimises the SQUARES; and §P1b of the receipt carried a row the harness cannot produce while dropping three it does |
| 2 | PASS | 4 MINOR, 2 NIT | the module docstring said a one-bar-forward window "ends on the return of bar T"; it ends on bar T+1's and KEEPS bar T's, which is the actual reason the mutant is causal |
| 3 | PASS | 4 MINOR, 1 NIT | the dispatch paragraph claimed EVERY figure in the docstring reproduces with AVX off, while quoting §T's wall clock (irreproducible on either dispatch) and six counts from the GPL-3.0 sections that were never re-run |
| 4 | PASS | 1 MINOR, 3 NIT | the clause round 3 asked for, which scopes which figures were re-measured under the CI dispatch, filed §A5's own 366-window tallies under the GPL-3.0 sections — withdrawing coverage from a section the same sentence certifies |

Every finding of every round was applied, including on the three PASS rounds, because
the house rule is that a PASS counts only if no fix lands after it — and since round 4
is the cap, its own four fixes have no fifth round behind them. What stands in place of
that is in `01-c22-dfa.md` under "The cap, and what it means here": no CRITICAL or
MAJOR after round 1, the four round-4 fixes are four sentences and one constant, and
the module was re-run green (186, and 186 with the CI dispatch) after them.

Eighteen findings over four rounds, fifteen of them the repository's named dominant
defect — a sentence or a number written past the run it came from — and not one about
the mathematics: all four reviewers re-ran the harness, the GPL-3.0 black box and the
module under both CPU dispatches, and reproduced every table they checked. Three rounds
running, the fix for a claim-past-its-measurement shipped a smaller one; that is the
honest headline of this run and it is why round 4 was spent hunting exactly that.

Six more defects of the same family were caught by a self-check before round 1's verdict
arrived and are listed in `01-c22-dfa.md`.

## The numbers that decide the port

* **Gate A.** Bit-equal to the GPL-3.0 reference on **8,400 of 8,400** windows of six
  frames, 0 disagreements; the same reading predicts it on **3,084 of 3,084** windows
  across all 32 ladder sizes the feature can produce (16 .. 47 rungs, `length` 79 ..
  1,187). Three structural readings the definition leaves open were pinned by fitting
  2,304 + 560 + 168 candidate pipelines to that output, not by taste. Plus a
  plain-Python spelling (bit-equal on 1,200 windows) and an exact-rational oracle (90 of
  90 breaks, worst margin 3.598e-04 relative).
* **Gate B.** 0 of 35 offsets leak on six frames under a gentle splice and 0 of 35 under
  a violent one; a one-close-at-a-time dependency map puts every mover in `[T-100,
  T-1]`, 0 at or after T; fifteen mutants, all accounted for. The column is causal and
  **one bar stale** — the value at bar T does not read `close[T]`, though its NaN mask
  does.
* **Gate C.** 1,400 of 1,500 bars fire on every frame, all six values on each of five
  stochastic ones; a 2-lira stock on a 1-kurus tick prints 14.01% of its returns as
  exactly zero and still fires everywhere, reading the same median as a continuous walk.
  Real-data limb owed.
* **Gate D.** Bit-identical under x8, x64, 2**-40, 2**40, x10, x3.7, x0.1 and
  x1.0000001, at three lengths and three price levels; `0 < fires < n`; not constant.
* **Gate E.** Pending, run by issue-solver after this session.
* **Gate F.** 186 module tests green, and the same 186 with `AVX512F AVX512_SKX AVX2
  FMA3` disabled; eight of the receipt's ten sections re-measured under that dispatch
  with exactly one digit moving; full repository suite 2 failed, 13,677 passed, 86
  skipped, the two failures being the owed Gate E row and the sibling-checkout test CI
  deselects.

## Where the reports live

* `00-manifest.md` — the task, the assumptions (no questions could be asked in a
  headless session), the execution map.
* `01-c22-dfa.md` — the implementation log, the pre-review self-check, and all four
  verdicts verbatim with a fix table each.
* `docs/C22DfaMeasured.md` — the receipt every number comes from.
