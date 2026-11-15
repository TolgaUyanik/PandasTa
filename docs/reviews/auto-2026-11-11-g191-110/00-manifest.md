# auto run 2026-11-11 — g191-110 (manifest)

Mode C (batch task execution), one task, `--fletcher` on automatically. Run folder:
`docs/reviews/auto-2026-11-11-g191-110/`.

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `g191-110` | Port GTJA191 alpha `#110` (`SUM(MAX(0,H-C1),20) / SUM(MAX(0,C1-L),20) * 100`) through Gates A-D, the five wiring touch points, the test module and `docs/G191110Measured.md`. Gate E and both repos' suites are run by the issue-solver launcher afterwards. | the `/brutally-honest-review --auto "..."` argument, which quotes issue #84 (TolgaUyanik/PandasTa) |

Not in scope, by the launcher's own rules: running `gate_e_overlap.py`, reading or writing
anything under `../Backtesting`, recording a `docs/gate_e_ledger.csv` row, pushing, opening a
PR.

## Phase 2 — clarifications

**None were asked.** `AskUserQuestion` is unavailable in a headless issue-solver session, and
the launcher's rules say: "Where a skill says to ask, take the most conservative reading (the
smaller scope) and log it as an ASSUMPTION."

### ASSUMPTION 1 — category: `momentum`

The issue does not name a category. `brar` (the shipped indicator this formula restates) is in
`momentum`, the formula compares upside against downside pressure rather than measuring
dispersion, and the sibling GTJA ports of close-to-close `MAX(0,.)` sums (`g191_167`,
`g191_129`) are in `momentum` too. Chosen on that basis: `pandas_ta/momentum/g191_110.py`.

### ASSUMPTION 2 — ship the port rather than pre-empt the owner with a revert

The port turned out to be `brar`'s `BR` column at a different window length — measured, at the
same length, as Spearman 1.0 / max |diff| 5.68e-14, with the port's own expression re-spelled
`brar`'s way bit-identical to `BR_20`. Whether a near-duplicate at a non-default length earns
a `Category` entry is an OWNER RULING (the class `tests/test_altport2_ports.py`'s `NOT_PORTED`
records as "question-redundancy skip", at LOWER overlap than this one), and it is not a gate
verdict: the `r3-perframe-0.90` bands strike at 0.90 and the issue's own prototype measured
0.8860 pooled against `brar_BR_26`.

Conservative reading taken: **deliver the port, with the duplication measured and stated in
the six places listed here** — the module docstring's opening block, the public
`g191_110.__doc__`, the receipt's status banner, the receipt's "The redundancy, measured"
section, the test module's docstring, and `docs/MLCompanionContract.md`'s tag line — and do
NOT revert it in this commit. ⚠ One surface does NOT carry it:
`docs/IndicatorDictionary.md`'s generated row truncates the `__doc__` at its first sentence
("Over a trailing window, the total distance highs reached ABOVE the prior close divided…"),
so the dictionary — the document CLAUDE.md tells a reader to consult before judging a column —
shows no redundancy flag at all. Reasons for shipping anyway:

* the gates as written do not say "do not ship": `r3-perframe-0.90` strikes at 0.90 and the
  prototype measured 0.8860, and a measured revert is for when a gate says stop;
* the issue's "Gates owed" asks for Gate E re-run ON THE PORT, and only the launcher can
  produce that row — reverting now means no row ever exists for it;
* the revert is one commit later and the receipt file is already written to survive it, with
  the exact revert list in it.

**But the receipt's recommendation is SKIP**, ranked and argued there (CLAUDE.md's
Non-redundant rule, CLAUDE.md's "deleting an over-correlated column you just built is the
expected outcome", and the three `NOT_PORTED` question-redundancy skips at 0.834-0.889, all on
weaker grounds than this one). Keeping the port in the commit is bookkeeping so Gate E can
run; it is NOT a judgement that the column earns its place. Round 1 of review caught an
earlier version of this assumption arguing the Gate E row as if it were evidence about
redundancy; it is not, and the wording above no longer says so.

Logged here so the ruling is visible without reading the diff.

### ASSUMPTION 3 — Gate C on real data is owed, not claimed

Gate C asks for fire counts on real data. This session has no real frames (the 89 ALTPORT-1
BIST frames live behind `../Backtesting`, which is out of bounds here), so Gate C is reported
as PASS ON SYNTHETIC with the 1,500-bar walk's counts, and the real-data number is owed with
Gate E. The issue's own prototype screen number (n = 396,399 pooled bars) is quoted as a
PRIOR and labelled as the prototype's, not the port's.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `g191-110` | main thread | One task, one module, and every judgement call in it (the three ambiguous readings of the source string, the `brar` redundancy ruling) needs the main context. Nothing to parallelise; worktree isolation would buy nothing. |

Gate: one Fletcher reviewer subagent per round (`Explore`, read-only), max 3 REVISE rounds per
the skill, extended to 4 by the user's standing "Review loop" rule. Verdicts are quoted
verbatim in `01-g191-110.md`, never summarised.
