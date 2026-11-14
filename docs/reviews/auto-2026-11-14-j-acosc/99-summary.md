# Run summary — `/brutally-honest-review --auto` (Mode C), 2026-11-14

**Run folder:** `docs/reviews/auto-2026-11-14-j-acosc/`
**Task:** J-ACOSC — port jesse's `acosc` as `j_acosc` (PandasTa issue #106).
**Files:** `00-manifest.md` (tasks, assumptions, execution map),
`01-j-acosc.md` (implementation log + all four review rounds verbatim),
this file.

## The table

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `j-acosc` | **REVISE at round 4 — the loop's cap, all findings applied, unreviewed** | 4 (REVISE, REVISE, REVISE, REVISE) | `pandas_ta/momentum/j_acosc.py`, `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_j_acosc.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/JAcoscMeasured.md`, `docs/measure_j_acosc.py`, `docs/measure_j_acosc_cpu.py`, this folder | Gate E owed (the launcher runs it); Gate C's real-data counts come with it; round 4's seven fixes are unreviewed; the `fast-lead` label is kept as historical; a pre-existing `pandas_ta/core.py` `Category` ordering defect is recorded, not fixed |

⚠ **No round returned PASS.** The review loop's cap is four rounds (round
1 plus three re-runs) and round 4 returned REVISE with 2 MAJOR, 3 MINOR
and 2 NIT. **All seven were applied** — `01-j-acosc.md` lists each one and
what landed — so nothing a reviewer named is left standing, but those
seven fixes are the only changes in this port that no reviewer has seen.
That is stated here rather than dressed up as a PASS, which is what round
4's second MAJOR caught an earlier draft of this very file doing.

## What shipped

One column, **`J_ACOSC_5_34_5`**, in `momentum`:

```
mid     = (high + low) / 2
AO      = SMA(mid, 5) - SMA(mid, 34)
J_ACOSC = (AO - SMA(AO, 5)) / close
```

Gates A–D measured in `docs/JAcoscMeasured.md`; **Gate E pending**, run by
issue-solver after this session. Gate F here: **175** for the module, the
same **175** under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
FMA3"`, full suite **3 failed / 9,120 passed / 85 skipped** — the three
being `dev`'s two clean-checkout failures plus the owed Gate E row.

## The review rounds

Each round was a fresh read-only `Explore` subagent with the Fletcher
persona, given the target list, the session's binding rules, and an
instruction to re-run every measurement itself. Every round did re-run the
scripts and the suites.

| round | verdict | CRITICAL | MAJOR | MINOR | NIT | total | applied | declined |
|---|---|---|---|---|---|---|---|---|
| 1 | REVISE | 0 | 1 | 2 | 2 | 5 | 5 | 0 |
| 2 | REVISE | 1 | 2 | 2 | 1 | 6 | 6 | 0 |
| 3 | REVISE | 0 | 2 | 2 | 2 | 6 | 5 | 1 |
| 4 | REVISE | 0 | 2 | 3 | 2 | 7 | 7 | 0 |
| **total** | | **1** | **7** | **9** | **7** | **24** | **23** | **1** |

**Not one of the twenty-four findings was about the mathematics.** Every
round re-ran `docs/measure_j_acosc.py` and reported its tables
reproducing; rounds 3 and 4 certified them cell by cell.

Of the twenty-four, **nineteen** were the repo's named dominant defect —
*a claim written before it was measured*. The other **five** were a
different genus: a dead `FIRED` constant (r2 NIT), a dangling `§G(c)`
cross-reference (r1 NIT), a `99-summary.md` named by the manifest but
never written (r3 MINOR), a `§F` heading claiming an exact zero the same
section measured at 6.939e-18 (r4 NIT), and the declined path (r3 NIT).

## What the rounds were actually about

**The same absolute, three times, on a different surface each round** —
which is the lesson worth carrying forward, because it is the repo's
recorded failure mode ("a correction applied to three of four prose
surfaces is not a correction") caught in the act:

1. **Round 1** killed a bolded "every one moves EVERY shared bar" in the
   test docstring, when the session's own §B2 already recorded the
   exception (`divisor-lead` on `grid`, 1,456 of 1,462).
2. **Round 2** found the SAME absolute still standing in the receipt's
   Verdict table, after the first three surfaces had been fixed.
3. **Round 3** found it a third time, in the shipped module docstring:
   "caught on every frame" where the sweep runs on six of seven.

**And then a mechanism written instead of measured, twice** — the second
time inside the fix for the first:

* **Round 2** found `fast-lead`'s mechanism wrong on five surfaces
  ("`center=True` costs two bars at each end"). The anchor is `_sma`'s
  only line, so every mean is centred and the real reach is
  `(SLOW-1)//2 + (SIGNAL-1)//2` = **18** — which the session's own
  shared-bar deficit (1,463 − 1,445) and moved-bar count (18) both already
  said. New `§B4` and a new test derive it from the constants.
* **Round 4** found that round 3's fix to the "every frame" scope had
  replaced it with a reason nobody had run — "a perturbation of a constant
  price is still a constant price", which is false, because the sweep
  multiplies bars `>= J` by 1.03 and leaves a two-level step. Measured:
  four of the five mutants ARE caught on `flat` at 36 of 36; the exception
  is `divisor-lead` at 0 of 36, because a constant price makes `AO`
  exactly 0.0 on every pre-`J` bar and `0.0 / c` is `0.0` whatever `c` is.
  New `§B5`, a new `§B(e)` in the script and a new test.

**Three findings changed the deliverable rather than its prose**, and all
three came from a reviewer asking for an assertion the session had not
written:

* Round 1's ×8/×64-at-extreme-levels claim was reworded-or-measured; it
  was **measured**, so §D(c) and the test now re-run both exact factors at
  1e-6 / 1e+6 / 1e+100.
* Round 3 asked for `max |value|` to be asserted EQUAL across those three
  levels. **The assertion failed**, falsifying a sentence the receipt had
  been carrying: the three agree to 3.9e-15 relative (4.4e-15 reduced) but
  are not bit-equal, because 1e-6/1e+6/1e+100 are not exact binary
  multiples and the rebuilt price paths already differ in their last bits.
  A four-digit print had hidden it; §D3 now prints 17.
* Round 4 found `sum |tap| = 0.800000` in the test docstring's *pinned*
  list with no assertion behind it — and the 6-digit print was hiding an
  ulp: the value is **0.80000000000000004**. Now asserted at `rel_tol=1e-12`.

**One finding was declined, and round 4 confirmed the refusal was right**
(round 3, NIT): the manifest's `docs/issues/105-j-acosc.md` is the correct
local path — the owner's tracker numbers this issue 105 and GitHub numbers
it #106, systematically offset. Round 4 read the gitignored files and
reported that `docs/issues/106-sk-fcb-width.md` exists and is a different
indicator, so round 3's "fix" would have pointed the manifest at the wrong
issue. The manifest carries a ⚠ note instead.

## Follow-ups this port leaves behind

1. **Gate E is owed.** `tests/test_j_acosc.py::test_the_gate_e_row_is_owed`
   asserts `docs/gate_e_ledger.csv` has no `j_acosc` row;
   `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
   fails locally reporting
   `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'j_acosc', 'lumpiness', 'mtd_ret']`.
   The receipt session replaces that test with one pinning the row's
   identity and writes §E.
   ⚠ The screen measured the bit-identical PROTOTYPE at **DISCLOSE_GAP**
   (max |ρ| 0.8381 vs `FWMA_Slope_pct_Pctl`, n = 391,996, top-5 per-frame
   max median 0.8431), so a STRUCK run is not expected — but if it lands
   STRUCK the column is reverted or waived and `docs/JAcoscMeasured.md`
   stays as the receipt.
2. **Gate C's real-data counts** come from the same run; everything in §C
   is synthetic.
3. **Round 4's seven fixes are unreviewed**, the loop's cap having been
   reached. They are listed individually in `01-j-acosc.md` under "Fixes
   applied after round 4", and the largest of them —
   `test_the_flat_frame_is_excluded_because_divisor_lead_cannot_be_caught_there`
   plus `§B5` plus `§B(e)` — is backed by a run whose output is pasted
   into both that log and the receipt.
4. **The `fast-lead` mutant's label is historical** and every surface says
   so. Renaming it to `center-all` would rewrite the test IDs and the
   receipt's tables for no measurement gain;
   `test_the_fast_lead_mutant_reaches_eighteen_bars_not_two` is what keeps
   the wrong explanation from returning.
5. **Recorded, not fixed — outside this issue's scope** (already recorded
   by #100 … #105): `pandas_ta/core.py:453` hands out the live
   `Category[name]` list and `core.py:692` removes names from it, so a
   module that exercises `df.ta.strategy()` shrinks `Category` for every
   module collected after it in the same process. Measured again this
   session: `python -m pytest tests/test_ml_companions.py
   tests/test_wiring_accessors.py tests/test_readme_counts.py` fails 3
   tests, all in `test_readme_counts.py`; dropping
   `test_wiring_accessors.py` gives 20 passed. Alphabetical collection
   hides it in a full run.
6. **The uncomfortable disclosure a consumer must carry**, on all four
   prose surfaces and pinned by
   `test_the_column_is_near_the_ao_1_bar_change_and_far_from_its_level`:
   this column reads Spearman **0.8638 .. 0.9016** against `AO`'s own
   1-bar change over close, and only 0.1187 .. 0.3026 against the
   `AO / close` LEVEL. The differencing IS the column, so "this is more
   than the Awesome Oscillator" is not an argument available at Gate E.
   Neither comparator is a shipped `Category` column — `AO_5_34` ships as
   a price level — and the nearest shipped fork column is
   `stochrsi:STOCHRSIk_14_14_3_3` at 0.7965 .. 0.8682 synthetic, matching
   the screen's 0.8233 on 12 real frames.
