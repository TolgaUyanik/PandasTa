# auto run 2026-11-14 — `ts-reoccur-20` — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-reoccur-20` (PandasTa #103) | **ESCALATED** — four rounds, all REVISE, every one of 28 findings applied, round 4's six fixes not re-reviewed | 4 (the cap) | 6 new, 7 modified — listed below | Gate E (the launcher's), then the receipt session; nothing else open |

## Why ESCALATED and not PASS

The round cap is four (round 1 plus three re-runs). Round 4 returned
REVISE with one MAJOR, four MINOR and one NIT; all six were applied, and
the cap then forbids a fifth review. **No finding is outstanding** — the
status records that the last six fixes have not been seen by a reviewer,
not that anything is known to be wrong.

| round | verdict | findings | all applied |
|---|---|---|---|
| 1 | REVISE | 1 CRITICAL, 1 MAJOR, 4 MINOR, 1 NIT | yes |
| 2 | REVISE | 1 CRITICAL, 1 MAJOR, 3 MINOR, 3 NIT | yes |
| 3 | REVISE | 1 MAJOR, 3 MINOR, 3 NIT | yes |
| 4 | REVISE | 1 MAJOR, 4 MINOR, 1 NIT | yes |

**Not one of the 28 findings was about the mathematics.** Every reviewer
re-ran the whole measurement script and reported every table reproducing
to the printed digit; all four summaries say so explicitly. What they
found, four times in a row, was the repo's named dominant defect — a
number written to make a sentence read well rather than to report a run:

* round 1: `has_duplicate` "constant on 4 of 7 frames" with the table
  printing 3 directly above it; a lattice miscounted as 19 where the
  script prints 20; a frequency claim ("0.6667 almost everywhere") from
  no run at all;
* round 2: the **fix** for round 1's docstring rewrite left "143
  characters" behind for a 147-character sentence, and "measured 0
  merges" was stamped on four documents for a count nothing computed and
  that bit-equality does not entail;
* round 3: the **fix** for round 2's cost ratio replaced one false
  bracket with another that a run three lines below it already refuted;
* round 4: §W — the section added in round 2 precisely to stop the
  character count from drifting — measured a **reimplementation** of
  `gen_indicator_dictionary.py`'s cut rather than the function itself,
  and was wrong by one character of slack in the direction that would
  silently truncate the tick-grid warning out of the one document
  CLAUDE.md routes a consumer to first.

The pattern is worth the owner's attention because the root cause is
structural rather than careless: every time a claim was *derived* instead
of *printed*, it rotted at the next edit. The three repairs that held
were the three that moved the number into the script — `section_A4`
counts its own constant rows, `section_C` prints raw bar counts beside
each share, and `section_W` now calls the generator's `desc()` and finds
the slack by growing the sentence until that function loses it. The ones
that kept breaking were the ones left as prose (§Z's ratio, three times,
until it was finally stated as an order of magnitude over an eighteen-run
span).

## Files

**New (6):** `pandas_ta/statistics/ts_reoccur_20.py`,
`tests/test_ts_reoccur_20.py` (223 tests),
`docs/TsReoccur20Measured.md`, `docs/measure_ts_reoccur_20.py`,
`docs/measure_ts_reoccur_20_cpu.py`, this folder (3 files).

**Modified (7):** `pandas_ta/__init__.py` (`Category`),
`pandas_ta/core.py` (accessor), `pandas_ta/statistics/__init__.py`
(export), `README.md` (341 → 342, 349 → 350, statistics 49 → 50),
`docs/IndicatorDictionary.md` (regenerated),
`docs/MLCompanionContract.md` (686 → 687 tagged, 42 → 43 `CONST`),
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 341 → 342).

All eleven paths that changed are inside the session's allowed list.
`docs/gate_e_ledger.csv` is in that list and is deliberately untouched:
the row is owed.

## Suites

| run | result |
|---|---|
| module | 223 passed |
| module under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` | 223 passed |
| full suite | 3 failed, 8,590 passed, 85 skipped |

The three are CLAUDE.md's two documented clean-checkout breaks
(`test_audited_rows_carry_their_evidence`, and the `../AlternativeRepos`
one CI deselects by name) and the owed Gate E row, which lists
`['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife',
'lumpiness', 'mtd_ret', 'ts_reoccur_20']`.

## Follow-ups

1. **Gate E** on `pandas_ta.statistics.ts_reoccur_20` — the launcher's,
   then a receipt session records the ledger row, fills §E and §E1 of
   `docs/TsReoccur20Measured.md` with the real-data reachability counts,
   and replaces `test_the_gate_e_row_is_owed` with one pinning the row's
   identity. The screen measured the PROTOTYPE at \|ρ\| 0.7222 vs
   `stdev` (SHIP, but the top of 687 comparators), and §A1 measures this
   module bit-equal to that prototype, so the figures are expected to
   carry over — the run is still what decides ship or revert.
2. **What Gate E's run should also settle, and §C cannot:** how much of
   the 89-frame universe sits in `grid-200tick`'s near-binary regime
   (0.00 on 90.9% of bars, 3 distinct values). A column that almost never
   fires carries little information however low its correlation.

## Recorded, not fixed (pre-existing, outside this issue's scope)

`pandas_ta/core.py:453` hands out the live `Category[name]` list and
`core.py:692` removes names from it, so running
`tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py` in
one process fails the pinned `CATEGORY_TOTAL` (339 against 342 in the
round-4 reviewer's ad-hoc module order). Alphabetical collection hides
it, and a full-suite run is green on that test. Already recorded by
#100, #101 and #102; `statistics` is not one of the categories the
removal touches.
