# Run summary — auto 2026-11-19, j-kaufmanstop-dist

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `J-KAUFMANSTOP-DIST` (issue #124) | **done, with no PASS** — see below | **4** (the loop's cap), every round REVISE, all **30** findings applied (8 + 9 + 6 + 7) | `pandas_ta/trend/j_kaufmanstop_dist.py` (new), `tests/test_j_kaufmanstop_dist.py` (new), `docs/measure_j_kaufmanstop_dist.py` (new), `docs/measure_j_kaufmanstop_dist_cpu.py` (new), `docs/JKaufmanstopDistMeasured.md` (new), this run folder (new); `pandas_ta/trend/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E and Gate C's real-data limb are **owed** — the launcher runs the harness, a receipt session records the ledger row and replaces two tests. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails locally until then, naming only `j_kaufmanstop_dist`. |

## ⚠ There is no PASS, and this file says so rather than implying one

Four rounds, four REVISE verdicts. Round 4 is the cap (round 1 plus three
re-runs), so **round 4's seven fixes have no post-fix review**. There are no
open findings — every finding of every round was applied — but a fixed
REVISE is not a PASS, and the loop ran out of rounds before one could be
given.

| round | verdict | findings | the one that mattered |
|---|---|---|---|
| 1 | REVISE | 2 MAJOR, 3 MINOR, 3 NIT | the receipt's header said **one** §D2 cell moved between numpy dispatches over its own table listing **eight** |
| 2 | REVISE | 1 MAJOR, 4 MINOR, 4 NIT | round 1's repair claimed that one test pins pandas' absorption "in both directions"; a second test does, and the claim was unrun |
| 3 | REVISE | 2 MAJOR, 2 MINOR, 2 NIT | the test docstring still named the **refuted** propagating mean twelve lines above the sentence refuting it |
| 4 | REVISE | 2 MAJOR, 3 MINOR, 2 NIT | the receipt told a later session to go measure `lean_avgrange_14`, which the CSV it quotes records as **STRUCK and dropped** |

## What every round agreed on

The arithmetic. All four reviewers re-ran `docs/measure_j_kaufmanstop_dist.py`
and `docs/measure_j_kaufmanstop_dist_cpu.py` section by section and reported
every cell reproducing on both numpy dispatches, plus the three suite counts
to the line. **Not one finding in four rounds was about the mathematics**,
the oracle, the mutants, the scale-freeness or the wiring.

## The defect that repeated, and what came out of it

Every round's hardest finding was **a count or a mechanism written past the
run, inside a fix for the previous round's count or mechanism**: one cell
versus eight (r1), one test versus two (r2), a refuted vehicle left in place
and "the three identical-dispatch lines" over twelve of them (r3),
`_prep_values` left standing in two of six places and an inverted screen
verdict (r4). Even this loop's own corrections were not immune: the
replacement count for round 3's MAJOR came out **eleven** from a
single-line grep that missed a wrapped sentence, and had to be recounted
with a multiline match before the round closed.

Three habits came out of it and are in the files:

1. **Count with a tool, then state the number.** Item 7 of the receipt's
   exception block enumerates its twelve statements by section and says
   which match found them.
2. **Measure the hypothetical instead of reasoning about it.** §G5 exists
   because round 1's inference was refuted; it then refuted round 2's
   proposed mechanism (`rolling(...).apply(np.mean, raw=True)` does not
   propagate) and confirmed round 2's conclusion by the right vehicle
   (route 1 ships 99 of 120 under a numpy window mean).
3. **Scope a universal to the cells that ran.** "Removing the three input
   guards would not change a measured cell" became "would not change any of
   the **42** guard-off cells measured here", with the four plant points
   that were not re-run named.

## What a reader should take from the port itself

* **The screen prototype is this column's arithmetic, bit for bit** (§A3,
  nine frames) — the opposite of the sibling port #122 — so the screen's
  DISCLOSE_GAP figures describe this arithmetic rather than a neighbour's.
* **Gate E is PENDING** and the launcher runs it. The screen measured
  0.8776 vs `natr`; ⚠ the nearest candidate of the same family,
  `lean_avgrange_14`, measured **0.9489** against the same comparator and
  was **struck**.
* **The column does not change sign** (0.005961 … 0.014415 over 8,874
  bars), which is where it parts from both sibling stop distances.
* **Three of its five guards are measured dead code**, kept for defence in
  depth and consistency, and the receipt says so plainly with the 42 cells
  behind it.

## Assumptions logged

Five, in `00-manifest.md` — category `trend`, constants not arguments, the
fork's own `sma`, a plain `high - low` rather than `non_zero_range`, and no
short side. `AskUserQuestion` was unavailable (headless), so each took the
most conservative reading.
