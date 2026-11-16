# run summary — `auto-2026-11-16-j-chandelier-dist`

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `j-chandelier-dist` (PandasTa #122) | **SHIPPED, no PASS** — see below | 4 (the loop's cap) | 13 | Gate E (launcher) · Gate C's real-data limb · the ledger row (receipt session) |

## Status, stated precisely

The port is **complete and shipped**: Gates A–D measured, five wiring touch
points, four counted surfaces, 254 tests green on both numpy dispatches,
`docs/JChandelierDistMeasured.md` written. Gate E and both repos' suites
are the launcher's, as the issue's own terms say.

⚠ **There is no PASS, and there are no open findings.** The review loop is
capped at four rounds. Round 4 returned REVISE on one MAJOR and five
lesser findings; every one was applied, and there was no fifth round to
confirm them. So this run ends with:

* rounds 1, 2 and 3: REVISE → fixed → re-reviewed, each round confirming
  the previous round's fixes dead;
* round 4: REVISE → fixed → **not re-reviewed**.

That is stated here rather than implied, because "four rounds of review"
reads as "passed four reviews" otherwise.

## The rounds

| round | verdict | findings | what it was about |
|---|---|---|---|
| 1 | REVISE | 1 CRITICAL, 4 MAJOR, 6 MINOR, 1 NIT | A guard claim INVERTED (three guards called decoration when the table's own rows exist only because they change the column); an unmeasured claim that Gate E cannot see any §L neighbour; "every shared bar" over a measured 1,294; five statements about jesse's and Skender's source code in a worktree where neither is installed; a blanket "nothing here is derived by hand" that was itself false |
| 2 | REVISE | 3 MAJOR, 2 MINOR, 1 NIT | All three MAJORs **introduced while fixing round 1**: five surviving library claims; §L miscounting its own Gate E name overlap (two stated, three actual — the third being `Range_Pos_20`, the comparator that decided the prototype's band); `walk`'s reduced-dispatch bar given as another frame's |
| 3 | REVISE | 1 MAJOR, 2 MINOR, 2 NIT | "**Five** exceptions" written over a list of six, in the sentence whose whole job is to be countable; §G3's denominator unprinted after §G4's was printed for that exact reason; §G2's dispatch-dependent counts stated bare |
| 4 | REVISE | 1 MAJOR, 3 MINOR, 2 NIT | "Every later bar" in five places, refuted by §G1's own printed `bars MOVED` column (658 of 1,400 at a plant of 100); a Markdown table stapled in half by the round-3 fix; the asserted-bounds list pointing at the wrong sections |

**25 findings, every one applied.** Not one of them was about the
mathematics. Every round re-ran the measurement script, the reduced-CPU
variant and the suites, and every round reported all 21 sections
reproducing cell for cell.

## The shape worth carrying forward

The arc is one defect repeating: **the author fixed the hard finding and
mis-edited the sentence next to it.** Round 1's CRITICAL was a correct
table with an inverted caption; round 2 found three new errors created in
the act of fixing round 1; round 3 found "Five" left standing over six
items *in the same edit that added the sixth*; round 4 found "every later
bar" surviving in five places while the receipt one page earlier printed
the three bounded counts. The tables never moved. The prose around them did.

Two mechanisms came out of that and are in the files rather than in this
summary:

1. **Print the denominator.** §G3 and §G4 now print their frame length and
   §A2 its NaN-mask column, because a receipt that quotes "97 of 120" from
   a script that only prints 97 has a hand-typed number in it. Round 3
   found one such; round 2 found four.
2. **Print both dispatches where a figure moves.** §A1, §A3, §D2 and now
   §G2 carry their reduced-CPU values inline, so a reader cannot take a
   dispatch-dependent count for a structural fact — and the assertions
   underneath are shapes (`> 300` bars, `> 100` bars, `> 1e-5`, 1e-9,
   1e-12), never the counts.

## What is owed after this session

| owed | by whom |
|---|---|
| **Gate E** — `gate_e_overlap.py run --module pandas_ta.trend.j_chandelier_dist` | the launcher, after this session |
| the `docs/gate_e_ledger.csv` row, and the measured numbers written into §E of the receipt | a later receipt session (`test_no_gate_e_row_is_recorded_yet` and `test_the_receipt_says_gate_e_is_pending` are its cue and are expected to be REPLACED, not to keep passing) |
| **Gate C's real-data limb** — the non-NaN count over the 89 BIST frames | the same Gate E run |
| both repos' suites in clean worktrees | the launcher |

⚠ And the one thing the owner should read before approving anything that
touches the `cksp` family: §L measures the distance from the close to
`cksp`'s `CKSPl_10_3_20` at a per-frame median |ρ| of **0.9320** against
this column over six synthetic frames. `cksp` ships the price LEVEL, which
the ML contract does not treat as a feature, so the column measured against
does not exist in the fork — but it is a one-line derivation, and six
synthetic frames read **+0.0575** high against the one comparator with a
real figure. If the port's own Gate E lands in DISCLOSE_GAP as the
prototype's did, that family is where the redundancy would be.

## Deliverables

`pandas_ta/trend/j_chandelier_dist.py` · `pandas_ta/trend/__init__.py` ·
`pandas_ta/__init__.py` · `pandas_ta/core.py` ·
`tests/test_j_chandelier_dist.py` · `docs/measure_j_chandelier_dist.py` ·
`docs/measure_j_chandelier_dist_cpu.py` ·
`docs/JChandelierDistMeasured.md` · `README.md` ·
`docs/IndicatorDictionary.md` · `docs/MLCompanionContract.md` ·
`tests/test_altport2_ports.py` · this folder.
