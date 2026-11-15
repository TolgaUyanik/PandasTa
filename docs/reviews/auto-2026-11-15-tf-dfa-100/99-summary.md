# Run summary — `/brutally-honest-review --auto` (Mode C), run `tf-dfa-100`

**Date:** 2026-11-15 · **Branch:** `issue-112-tf-dfa-100` · **Issue:**
PandasTa #112 (TF-DFA-100)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `tf-dfa-100` | APPLIED (4 rounds, last verdict REVISE, all findings applied) | 4 (REVISE, REVISE, REVISE, REVISE) | `pandas_ta/statistics/tf_dfa_100.py` (new), `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_tf_dfa_100.py` (new), `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/TfDfa100Measured.md` (new), `docs/measure_tf_dfa_100.py` (new), `docs/measure_tf_dfa_100_cpu.py` (new), this folder | Gate E, Gate C's real-data limb and the ledger row, all owed to issue-solver |

## Why the loop stopped at four rounds and not at PASS

The user's standing rule caps a review loop at four rounds (round 1 plus
three re-runs) and then requires the open findings to be reported rather
than a fifth round run. Round 4 returned REVISE with one MAJOR, two MINOR
and one NIT; **all four were applied**, each backed by a run made in the
session, and no round 5 was dispatched. Nothing from round 4 is left open.

## What the four rounds actually found

Eighteen findings across rounds 1–3 and four in round 4. **Not one was about
the mathematics.** Every reviewer re-ran the whole measurement script, on
both CPU dispatches from round 2 onward, and every time confirmed the
arithmetic as DFA-1, the chunk loop as index-correct and shape-stable, the
five mutants as live, the five wiring touch points as wired and the counts
as right.

All 22 were one disease, the one `CLAUDE.md` names: **a claim written before
it was measured** — and in this port it took a specific, repeating shape.

* **Round 1 (7 findings, 1 CRITICAL).** §L3 was measured before the final
  dot product was respelled and never re-measured, and it fed a bound
  (7.883e-15) into the shipped docstring and the ML contract that the
  AVX-disabled run exceeds.
* **Round 2 (7 findings, 1 CRITICAL).** The fix for round 1's bound shipped
  the same defect one section away: the polyfit oracle's 2.9e-15 is
  3.109e-15 with AVX-512/AVX2/FMA3 off. And §L3's new sentence claimed it
  was "the one section whose figures move with the CPU" — five others do.
* **Round 3 (4 findings, 1 MAJOR).** §F2, the table written to end the
  problem, said "Everything else reproduced digit for digit" without running
  §Z2, §A1's second table, §A2's relative column, §A8's `jump` or §D's
  relative column. All five move.
* **Round 4 (4 findings, 1 MAJOR).** The "how reachable is the `@`
  instability" paragraph was corrected by ALGEBRA in round 3 and still never
  run on the second dispatch. Run, it is not a threshold at all: with AVX
  off the `@` variant is unstable at 1, 2, 5, 7 and 8 rows per chunk and
  stable at 6.

The repairs that held all moved a claim into something executable or into a
table built from a run: `_mutant_alpha` (the iid-centre limb now runs the
shipped arithmetic on another ladder), the `inf`-fold mutant test (the
defensive line now has a run behind it), §F2 (15 rows, each with its worse
dispatch and its quoting site), and §Z's two-dispatch budget sweep.

One reviewer finding was **measured and came back the other way**: round 2
argued a window could be blanked by returns that are merely constant inside
each aligned box. Two constructions were built, one with exactly-equal
dyadic returns, and neither blanks — the window mean is not dyadic, so the
profile is not exactly straight. The docstrings now say the all-equal window
is the only blanking measured, and leave the rest open instead of asserting
either way.

## Suites

* `tests/test_tf_dfa_100.py`: **280 passed**.
* The same 280 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
  FMA3"` via `python docs/measure_tf_dfa_100_cpu.py`, which refuses to run
  unless the four features are really off and prints the ones still enabled.
* Full suite: **3 failed, 10,266 passed, 85 skipped** — the two CLAUDE.md
  clean-checkout breaks and the owed Gate E row, which reports
  `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'lumpiness',
  'mtd_ret', 'tf_dfa_100']`.

## Files in this folder

* `00-manifest.md` — the task, the seven ASSUMPTIONS (no `AskUserQuestion`
  in a headless session), the execution map.
* `01-tf-dfa-100.md` — the task log: all four rounds verbatim and the fixes
  applied against each.
* `99-summary.md` — this file.
