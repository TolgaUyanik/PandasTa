# Run summary — auto-2026-09-08-altfix-pinebi-mlcol

Mode C batch. Requested: `TALIB-1 ALTFIX-0..4 MLCOL-0..2 PINEBI-0b PINEBI-1b/1c/1d/1e PINEBI-2`.
Owner scoping in Phase 2 cut this to: **run the small, well-defined ones; skip all
porting; defer PINEBI-2 entirely; contract first, then roll out with Gate E per
companion.**

## Status

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| ALTFIX-0 | PASS | 3 | `docs/gen_altrepo_*.py` | — |
| ALTFIX-1 | PASS | 3 | `docs/_altrepo_resolve.py` | — |
| ALTFIX-2 | PASS | 3 | `docs/verify_gap_rows.py` | — |
| ALTFIX-3 | PASS | 3 | `docs/gen_indicator_list_tables.py`, `AlternativeRepos/IndicatorList.md` | — |
| ALTFIX-4 | PASS | 3 | `tests/test_prose_counts_match_the_csvs.py` | — |
| MLCOL-0 | PASS | 3 | `docs/MLCompanionContract.md`, `pandas_ta/ml/companions.py` | — |
| PINEBI-0b | PASS | 3 | `docs/audit_pine_have_rows.py`, `docs/gen_pine_builtin_coverage.py` | — |
| TALIB-1 | DEFERRED (owner) | — | — | porting skipped this batch |
| MLCOL-1, MLCOL-2 | DEFERRED (owner) | — | — | roll out with Gate E per companion |
| PINEBI-1b/1c/1d/1e | DEFERRED (owner) | — | — | porting skipped this batch |
| PINEBI-2 | DEFERRED (owner) | — | — | explicitly deferred entirely |

Suite at close: **1344 passed, 22 skipped**. All three gap verifiers clean
(`pandas-ta-classic` 19/19, `tti` 10/10, `ta-lib` 10/10, no reproducible rows).

## What the three review rounds actually found

The recurring defect was not arithmetic. It was **a published claim with no
mechanism behind it** — an absence nobody could have detected, a count nobody
regenerated, a provenance comment describing a writer that did not exist.

**Fourteen false gap entries** were closed across the run. The last two are the
instructive ones, because the reviewer named both and was right about one:

- `emv` — genuinely false. It is `ta.eom(length=1, divisor=1)`: Spearman
  **+1.000000**, max affine residual **5.42e-20** over 259 bars. At the probed
  default (14) the two correlate **+0.21**, so no threshold on the old surface
  could ever have rescued it. Cause: the shared surface swept lengths `(5, 30)`
  and never **1**, so no fork function's *unsmoothed* form was reachable. Fixed
  as a class, not a name — the sweep is now `(1, 5, 30)`.
- `fosc` — the reviewer's claim that it is "character-for-character the fork's
  `cfo`" does **not** survive measurement. Peak **+0.950818** across every
  length and scalar tried, max residual 1.18 (17.6% relative). Different maths
  (TSF vs linreg). It stays in the gap, but its note now names `cfo` as a
  measured near-miss instead of claiming nothing correlates — which is what
  invited the misreading in the first place.

Adding the two ALIAS entries as instructed would have published one correct
equivalence and **one false one**.

## Mechanisms added (so these classes cannot recur silently)

- Relation search (`_related_to`): an exact miss can now become
  `port - alternate impl` with a measured affine fit. Previously there was no
  path from "no fork function of this name" to anything but "absent" — the
  structural reason false gaps had to be found by hand, one reviewer at a time.
  Rescued `emv`, `rocr`, `rocr100`. Classic gap **29 → 19**.
- Near-miss reporting at ρ ≥ 0.90, below the 0.99 equivalence bar.
- `ml_state` enforces the contract clause *"a PX parent's STATE is computed on
  its DIST_PCT, never on the raw level"* — by **measurement, not by column
  name** (no PX registry exists, and a name check passes every renamed column).
  A price level puts **31.8%** of settled bars at `|STATE| == 2` against a
  nominal 10%; its distance, **11.0%**. Reproduces the contract's 31.4% / 9.9%.
- `NOT_CERTIFIED` has one home. The generator's copy was hand-typed under a
  comment claiming a script wrote it — same provenance defect as the `audited`
  column, one file over.
- PINEBI-0b receipts cite the real `ta.*` call. Demanding a literal
  `ta.<pine name>(` silently failed for the four indicators whose fork name
  differs (`wpr`→`willr`, `tr`→`true_range`, `cog`→`cg`, `dev`→`mad`); all four
  had **matched** and were nonetheless filed as unaudited-without-reason.
  Certifications 30 of 55 `have`.
- `pine_builtin_coverage.csv` carries `probe_env` — the one of four CSVs that
  did not say what its verdicts were conditional on. Installing TA-Lib moved `dm`.
- The prose guard reads `IndicatorList.md` (the deliverable, in a non-git
  sibling directory, previously outside every check) and matches
  `Measured gap: **N**`, not just the generated shape. It was publishing 12
  against a real 10.

## Known live consequence

`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` goes
red whenever `audit_pine_have_rows.py` is edited, because the receipts carry
line numbers into that file. Re-run the audit then the generator. This is the
guard working; it is documented in the audit script's docstring.

## Not done

Nothing was committed. Every deferral above is the owner's Phase 2 decision,
not a blocker found during the run.
