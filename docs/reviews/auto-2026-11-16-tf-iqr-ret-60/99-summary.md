# Run summary — `/brutally-honest-review --auto` (Mode C), 2026-11-16

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `tf-iqr-ret-60` | **DELIVERED, no post-fix PASS** (rounds 2 and 3 PASSed and were then edited; round 4 REVISEd and was fixed at the cap) | **4** of 4 | 5 new, 7 modified — see below | 3, all named |

## What shipped

`TFIQRRET_60` — the interquartile range of the last 60 simple returns,
`q75 - q25`, from TSFEL's `features.py interq_range` as PandasTa issue
**#117** states it. A volatility reading, sign-blind, scale-free by
construction.

New:

* `pandas_ta/statistics/tf_iqr_ret_60.py`
* `tests/test_tf_iqr_ret_60.py` — 273 collected, 272 pass, 1 skip
* `docs/measure_tf_iqr_ret_60.py` — 14 sections, every figure in the
  receipt
* `docs/measure_tf_iqr_ret_60_cpu.py` — the same, with numpy's `AVX512F
  AVX512_SKX AVX2 FMA3` dispatch disabled; refuses to run if the
  environment edit did not take
* `docs/TfIqrRet60Measured.md` — the receipt

Modified: `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`
(`Category`), `pandas_ta/core.py` (accessor), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL` 353 → 354), `README.md` (353 → 354, 361 → 362,
statistics 55 → 56), `docs/IndicatorDictionary.md` (regenerated),
`docs/MLCompanionContract.md` (698 → 699 tagged, 336 → 337 `SF`).

## Gates

| gate | result |
|---|---|
| A Correctness | **PASS.** BIT-equal to three independent oracles on 1,440 of 1,440 bars of each of ten frames: a retyped pandas `roll_quantile`, the source's own `np.percentile` spelling (28,800 single-quartile readings, plus 14,404 at five other lengths), and an exact `fractions.Fraction` oracle at 0.00 ulp. |
| B Causality | **PASS.** 0 of 35 offsets leak on three frames and at `length` 2, 5 and 250. Five live mutants caught 24–35 of 35; the sixth is DEAD on a clean frame and caught 12 of 12 on a designed one, moving exactly bar J−1. |
| C Reachability | **PASS (synthetic).** Fires 1,440 of 1,500 on every frame, non-negative on every fired bar and on 2,400 tie-heavy probe windows. ⚠ Real-data limb OWED from the launcher's Gate E run. |
| D Scale-free | **PASS.** ×8/×64 bit-identical everywhere measured; a level SHIFT moves every fired bar, so the check is not vacuous; `0 < fires < n` and >1 distinct value on all ten frames. |
| E Attribution | **PENDING, run by issue-solver after this session.** No ledger row, by design; an OWED `ts_q05_60` check carries a revert rule and a test fails if it is dropped. |
| F Suites | 272 passed / 1 skipped for the module under BOTH numpy dispatches; full suite 2 failed / 11,427 passed / 86 skipped, both failures expected and named. |

## The review loop

Four rounds, 16 findings, every one applied.

| round | verdict | findings |
|---|---|---|
| 1 | REVISE | 1 MAJOR, 3 MINOR, 2 NIT |
| 2 | PASS | 2 MINOR, 2 NIT — applied, so it does not count as the PASS |
| 3 | PASS | 3 MINOR, 2 NIT — applied, so it does not count either |
| 4 | REVISE | 1 MAJOR, 2 MINOR, 2 NIT — applied at the cap |

⚠ **There is no post-fix PASS, and that is stated rather than implied.**
The loop caps at four rounds; round 4's five findings were fixed and
re-measured, leaving **no open findings**, but no reviewer has seen the
final bytes. A reviewer rerun is the one thing this run could not buy.

**Not one of the 16 findings was about the mathematics.** Both MAJORs and
every MINOR were the same defect in different clothes — a sentence written
before the run that would have settled it:

* round 1's MAJOR: the docstring said one figure moves between numpy
  dispatches where the receipt's own table said two;
* round 4's MAJOR: a `git log` date table typed from output read
  positionally — `git log … -- fileA fileB` prints one line per commit, not
  one per path, so three of nine dates were rotated between three names.
  The conclusion survived; the evidence did not.

Three findings were **earned instead of deleted**, which is why the port is
better than its first draft: §D2 gained a measured `max ulp` column (32–208
ulps, against a claim of "one"), `section_G` now prints the widest window
return range as well as the smallest (the ladder's is 6.661e-16, not the
4.441e-16 that had been quoted under the wrong label), and §A2's
bit-equality is stated as a property of these frames — the two algebraic
`_lerp` forms differ on 16 of 20,000 random windows and on 0 of the 14,400
these frames produce.

Twelve more were found by self-audit between rounds and are logged in
`01-tf-iqr-ret-60.md` with the rounds they fall between — including a
mislabelled comparator (`TS_AGGAC_60_5` for a column whose default `maxlag`
is 10), which was fixed by keying every comparator on the Series' own
`.name` so that class of drift cannot recur.

## Follow-ups

1. **Gate E** is owed. The launcher runs it; a later receipt session
   records the ledger row and rewrites
   `test_the_gate_e_row_is_still_owed` to pin it.
2. **The `ts_q05_60` overlap** is owed from that same run, with a revert
   rule: if `ts_q05_60` is not among the 687 comparators, measure ρ against
   `TS_Q05_60` over the same 89 frames, read it against
   `r3-perframe-0.90`, and revert this column if it is STRUCK.
   `docs/TfIqrRet60Measured.md` §O carries the rule and a test fails if the
   block is dropped.
3. **Pre-existing, not this port's to fix:** running
   `tests/test_wiring_accessors.py` before `tests/test_readme_counts.py` in
   one process makes the latter fail — the former leaves `long_run`,
   `short_run` and `td_seq` out of `Category` (354 → 351). Reproduces with
   this port's test module absent; invisible under the full suite's
   ordering; the file is outside this issue's allowed set.

## Where the reports live

`docs/reviews/auto-2026-11-16-tf-iqr-ret-60/` — `00-manifest.md` (tasks,
the four ASSUMPTIONS taken because `AskUserQuestion` is unavailable, the
execution map), `01-tf-iqr-ret-60.md` (the implementation log and all four
verdicts verbatim), this file.
