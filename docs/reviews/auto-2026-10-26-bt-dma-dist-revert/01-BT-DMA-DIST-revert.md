# BT-DMA-DIST-revert — act on the pre-push gate's REVISE (round 1 of 3, HEAD 0156f88)

Task text, verbatim from the invocation:

> Fix every CRITICAL and MAJOR finding of the pre-push review gate (round 1 of 3, HEAD
> 0156f881e48a), quoted in this message, per the rules in your system prompt; fix MINOR/NIT
> findings only when cheap and safe.

The gate's contract, verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/DicksonMaMeasured.md:42-45 (status), :185 (Gate E row), :248-273 (To close); pandas_ta/__init__.py:62 (`Category` entry); gatee/is147-dickson_ma-0663a68d/overlap_max.csv:2
    problem:  The Gate E run on this port has come back STRUCK. `DICKSON_DIST_30_7` reaches max |ρ| 0.8927 against `Dist_to_PP_pct` (n = 374,196). Its per-frame median |ρ| is 0.9023 over 89 frames, and 52.8% of frames are at or above 0.90. Under schema `r3-perframe-0.90` the verdict is `STRUCK`; pooled-only would have given DISCLOSE_GAP. You knew this could happen. Your own doc says the prototype's per-frame median sat 0.0021 below the line "so the verdict could land on either side". It landed on the wrong side. Yet HEAD still registers `dickson_ma` in `Category`, the accessor, the export, the README, the dictionary and the contract counts. The receipt still says "Gate E: pending". "Done when" offers two exits: shipped through A–F, or measured and reverted with the receipt kept. HEAD meets neither. It is a STRUCK column still shipping, with a receipt that has no Gate E numbers.
    fix:      Carry out your own *To close* step 3 (STRUCK). Delete `pandas_ta/overlap/dickson_ma.py`, its export in `pandas_ta/overlap/__init__.py`, the `Category` entry, the `core.py` accessor, `tests/test_dickson_ma.py` and `docs/measure_dickson_ma.py`. Set `CATEGORY_TOTAL` back to 235. Revert the README hunks. Remove the contract parenthetical and restore 568 / 215. Revert only the port's dictionary hunks, or regenerate the dictionary with TA-Lib. Keep `docs/DicksonMaMeasured.md` and rewrite its status line and Gate E row with the measured figures: max |ρ| 0.8927 vs `Dist_to_PP_pct` (manifest), n 374,196, per-frame median 0.9023 over 89 frames, 52.8% of frames ≥ 0.90, compute_all max 0.8617 vs `log_return`, verdict STRUCK (pooled-only DISCLOSE_GAP), plus the run stamp from `meta.json`. Add a line comparing these to the prototype prior (0.8889 / 0.8979).
  - severity: MAJOR
    location: docs/DicksonMaMeasured.md:41-42, :181 (Gate A row); :183 (Gate C row)
    problem:  The issue says "Gate A starts from the source formula". Here Gate A was checked only against a listing typed from memory. Module and oracle share that recall, which the doc admits. Gate C exists only on a synthetic walk; the real-data counts are "owed". If this ships, two of the gates it owes have not been earned. A revert does not need either of them. A ship does.
    fix:      Once the revert in the first finding is done, write both rows as "not completed; port reverted on Gate E (STRUCK)". That way nobody reading the receipt later takes "cleared against a recalled transcription" as a pass. Record the real-data Gate C figures Gate E already gives you: non_nan 374,196 and non_zero 374,196 pooled bars, out of 398,849. If you ever un-revert the port, you must first do step 0: diff against the S&C Nov 2010 listing and backtrader's docstring defaults.
  - severity: MINOR
    location: tests/test_dickson_ma.py:1013-1014 (module docstring, "EC behaves mostly like a fixed fast smoother")
    problem:  In round 2 you corrected the doc to a two-pole filter, with the slow EMA pole carrying 1/6 of the DC gain. The test docstring still says "fast smoother". If the module is reverted this file is deleted anyway.
    fix:      If the file survives, match the doc's wording: "mostly a fixed two-pole filter (0.613 / 0.935)".
  - severity: NIT
    location: tests/test_altport2_ports.py:980-981; docs/MLCompanionContract.md:348
    problem:  Both comments say "Gate E pending" for `dickson_ma`. Gate E is no longer pending.
    fix:      Remove them with the revert, which restores the base text.
SUMMARY: The maths is not where this fails. I checked the EC recursion against Ehlers & Way's published form: the same alpha, the EMA feed, gains −5.0..+5.0 in steps of 0.1, and the strict `<` that maps to first-minimum `argmin`. HMA uses the fork's `int(n/2)` / `int(sqrt n)` `hma`, and DMA = (EC + HMA) / 2. Every look-ahead path is covered by a live, caught mutant. I re-derived the counts 915 / 1,103 / 720 / 923 / 2,723 from the warm-up and the HMA hole, and the scale tests are bit-identical under ×8 and ×64. The launcher's tests.md shows no regressions in either repo, with all 39 new tests passing. None of that helps you. You wrote down a threshold in advance, and the launcher's Gate E run measured you over it: per-frame median 0.9023 against a 0.90 line, so STRUCK. You are still pushing a registered indicator with a receipt that says "pending". You already wrote the procedure for this outcome in *To close* step 3. Not quite my tempo. Follow step 3: revert, write the measured numbers into the receipt, and close #147 as a measured revert. That closes the issue as fully as a ship would.
```

## Execution log

- Read the launcher's Gate E outputs (`gatee/is147-dickson_ma-0663a68d/`: `overlap_max.csv`,
  `top25.csv`, `perframe.csv`, `degenerate.csv`, `meta.json`), `gate-1/tests.md`,
  `gate-1/acceptance.md`, `run.log`, `journal.json`. The gate's Gate E figures match
  `overlap_max.csv` / `perframe.csv`; 398,849 matches `meta.json` `pooled_bars`; 0.8889 /
  0.8979 are quoted from `issue.md`; 235 and 568 / 215 match the base files (corrected after
  review round 1, which found the first wording pinned all of them to the two CSVs). Gate E
  ran on HEAD 0156f88 (acceptance.md names it; the
  gate-e stage started 22:59:08, after that commit at 22:42:50).
- Wrote `00-manifest.md` before any change.
- Revert: `git restore --source=b0422ad --staged --worktree --` on the three added files
  (`pandas_ta/overlap/dickson_ma.py`, `tests/test_dickson_ma.py`,
  `docs/measure_dickson_ma.py`, removed because they do not exist at base) and the seven
  modified wiring/doc files (`README.md`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
  `pandas_ta/overlap/__init__.py`, `tests/test_altport2_ports.py`,
  `docs/MLCompanionContract.md`, `docs/IndicatorDictionary.md`). `git diff --stat b0422ad`
  afterwards: only `docs/DicksonMaMeasured.md` and the three files of
  `docs/reviews/auto-2026-10-25-bt-dma-dist/`.
- ASSUMPTION: the gate offers "revert only the port's dictionary hunks, or regenerate with
  TA-Lib", and the old receipt's step 3 kept the contract's "regenerated in full" wording.
  Taken instead: both `docs/IndicatorDictionary.md` and `docs/MLCompanionContract.md`
  restored whole to base. Reason: the non-port dictionary hunks (probe date, removal of the
  `pfe` / `kalman_trend` hand-patch notes) came from a regeneration whose output contained
  the port; keeping them would leave a dictionary no generator run produced, and the
  "regenerated in full" wording would be false against the base dictionary. Whole-file
  restore is the smaller blast radius: those two files leave the branch diff entirely. It
  also discharges the NIT (both "Gate E pending" comments are gone with the base text).
- MINOR (test docstring wording): moot, `tests/test_dickson_ma.py` is deleted.
- Re-read `git show 0156f88:pandas_ta/overlap/dickson_ma.py`: the Gate A table's module line
  citations (:7, :14, :15, :20–22, :23, :24, :25, :38, :50, :51) match that file.
- Rewrote `docs/DicksonMaMeasured.md` as the receipt: status REVERTED on Gate E (STRUCK) with
  the measured figures; Gate A and Gate C rows "not completed; port reverted on Gate E
  (STRUCK)", Gate C with the real-data `non_nan` / `non_zero` 374,196 of 398,849; a *Gate E*
  section with the pooled, per-frame and `meta.json` stamp rows copied from the launcher's
  files and the comparison with the prototype prior (0.8889 → 0.8927, 0.8979 → 0.9023);
  *To close* replaced by *Closed: measured revert* and *If this is ever un-reverted* (step 0
  Gate A, Gate C split, a non-STRUCK Gate E).
- Guards run on the reverted tree, `python -m pytest -q tests/test_altport2_ports.py
  tests/test_readme_counts.py tests/test_ml_companions.py tests/test_wiring_accessors.py`:
  106 passed, 3 skipped (369.69 s, with the full suite running alongside).
- Committed the code revert as 5a7b463 (10 files, 19 insertions, 744 deletions; the three
  added files deleted). The receipt follows in a second commit.
- Full suite `python -m pytest -q` on the reverted tree: 2 failed, 3162 passed, 83 skipped
  in 1050.57 s. Failures: `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows`
  (pandas-ta-classic not found outside the repo) and
  `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (`RA2vGpkA-ta.pine`). The
  counts equal the launcher's base run in `gate-1/tests.md`. Filled into the receipt's Gate F
  row.
- Round-1 reviewer dispatched while the suite ran, told the Gate F row was a placeholder.

## Review round 1

Fletcher reviewer (Explore subagent, read-only). The Gate F row was a placeholder at dispatch
and was out of scope.

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/DicksonMaMeasured.md:28
    problem:  The receipt gets its own date wrong. "Measured 2026-10-25; Gate E and the revert 2026-10-26" says Gate E ran on the 26th. It did not. `run.log` has `2026-10-25 22:59:08 #147 stage: gate-e`, and `journal.json` has the gate-e entry at 23:04:12 with `seconds: 304`. The receipt's own heading at :165 says "(issue-solver, 2026-10-25)", and :169 says "started 2026-10-25 22:59:08". So line 28 contradicts lines 165 and 169 of the same file. You wrote a receipt and dated it wrong in the paragraph that lists your sources.
    fix:      Change :28 to "Measured and Gate E 2026-10-25; the revert 2026-10-26."
  - severity: MINOR
    location: docs/DicksonMaMeasured.md:163 (Gate F row); docs/reviews/auto-2026-10-26-bt-dma-dist-revert/01-BT-DMA-DIST-revert.md:73
    problem:  The Done-when says "Both repos' suites green", and CLAUDE.md Gate F says "both repos green". The only suite run the log plans is `python -m pytest -q` in this fork. The new receipt does not mention the Backtesting suite anywhere. The old Gate F row at least said "Parent repo: run by the launcher", and the rewrite dropped that line. Neither suite is green at base either. `tests.md` shows PandasTa base 3162 passed / 2 failed, and Backtesting 1584 passed / 16 failed / 4 errors / 14 skipped at both base and 0156f88. If you fill the row with one repo's counts and the word "green", that is a claim nobody measured.
    fix:      When you fill the Gate F row, add the Backtesting line from `gate-1/tests.md`: base = HEAD 0156f88 = 1584 / 16 failed / 4 errors / 14 skipped, 0 regressions. Note that the revert puts every fork code path back to base, so Backtesting now runs against base code. Name the PandasTa failures from the full run and say they also fail at base (`tests.md`: 2 failed at base), the way the old row named `test_pine_coverage_csv` and `test_altrepo_talib_csv`.
  - severity: MINOR
    location: docs/reviews/auto-2026-10-26-bt-dma-dist-revert/01-BT-DMA-DIST-revert.md:37-38
    problem:  "Every figure the gate quotes matches `overlap_max.csv` / `perframe.csv`" is false as written. The gate also quotes 398,849, which is `meta.json` `pooled_bars`; 0.8889 / 0.8979 and the 0.0021, which come from `issue.md`; and 235 and 568 / 215, which come from the base files. None of those are in either CSV. The figures do match their real sources, but you pinned them to two files that don't hold them. That is the repo's usual defect: an "every" claim that was never checked.
    fix:      Rewrite it as: "Every Gate E figure the gate quotes matches `overlap_max.csv` / `perframe.csv`; 398,849 matches `meta.json` `pooled_bars`; 0.8889 / 0.8979 are quoted from `issue.md`; 235 and 568 / 215 match the base files."
  - severity: NIT
    location: docs/DicksonMaMeasured.md:160 (Gate C row)
    problem:  "374,196 finite" comes from the `non_nan` column of `overlap_max.csv`, and non-NaN does not mean finite (±inf is not NaN). The gate's fix said "non_nan 374,196". You turned it into a stronger word than the file gives you.
    fix:      Write "374,196 non-NaN (`non_nan`) and 374,196 non-zero (`non_zero`) of 398,849 pooled bars".
  - severity: NIT
    location: docs/DicksonMaMeasured.md:23-27 (where the numbers come from)
    problem:  The provenance list no longer covers numbers the receipt still cites. The 568→569 / 215→216 and 235 / 243 counts in *Docs touched by the wiring* come from the git diff of 0156f88 against b0422ad, which the list doesn't mention since you dropped the `gen_indicator_dictionary.py` source. The 22:59:08, 22:42:50 and 304 s timings come from `run.log`, `journal.json` and `git log`, which the list doesn't mention either.
    fix:      Add: "the dictionary / contract / README counts from `git diff b0422ad 0156f88`; the Gate E timing from `run.log`, `journal.json` and `git log`."
  - severity: NIT
    location: pandas_ta/overlap/__pycache__/dickson_ma.cpython-311.pyc; tests/__pycache__/test_dickson_ma.cpython-311.pyc; tests/__pycache__/test_dickson_ma.cpython-311-pytest-8.4.1.pyc
    problem:  The port's bytecode is still in the worktree. git ignores it and Python will not import it without the source, but the port is not fully gone from this tree.
    fix:      Delete the three .pyc files once the full suite finishes.
SUMMARY: The revert itself holds, and I checked it rather than took your word. `git diff --name-status b0422ad HEAD` lists four added docs and nothing else. Grepping for `dickson` hits only the receipt and the review logs. 236 / 244 / 569 / 216 no longer appear in the README, the dictionary, the contract or the guard tests. Commit 5a7b463's stat (10 files, 19 insertions, 744 deletions) matches the log. I checked every Gate E figure against the CSVs and `meta.json`: 0.8927, 374,196, 0.9023, 52.8% = 47/89, 98.9% = 88/89, mean / min / max per comparator, 0.8617, 687 = 329 + 358, the degenerate `squeeze_SQZ_NO`, all seven stamp hashes and both source sha1s. I recomputed every derived figure: 24,653 = 89×277, 24,030 = 89×270, +0.0038, +0.0044, 0.0073, 0.0023, 0.0021, 114 / 218, 44, 47×, the 10.3267 hand check, and the 0.613 / 0.935 poles. The Gate A line citations (:7 to :51) match the deleted module line for line, and 277 / 92 / 461 are in the deleted tests. The ASSUMPTION also stands: restoring the dictionary and the contract whole is right, because the base contract's "hand-patched" wording only matches the base dictionary, and the two files drop out of the branch diff. Both MAJORs were carried out as ordered. What's left is sloppiness around the edges. Line 28 gives the wrong day for Gate E. The Gate F row is about to say "suites" while ignoring the second repo, and neither repo is green at base. Your log says "every figure" matches two CSVs that don't hold half of them. Fix the date, put the Backtesting counts and the pre-existing failures into Gate F, and stop writing "every" about things you didn't check. That was acceptable. Barely.
```

### Fixes applied
- MINOR date → receipt now reads "Measured and Gate E 2026-10-25; the revert 2026-10-26."
- MINOR Gate F → the filled row names both PandasTa failures, states the post-revert counts
  equal the launcher's base run, carries the Backtesting line from `gate-1/tests.md`
  (1,584 / 16 failed / 4 errors / 14 skipped at base and 0156f88, 0 regressions), says
  neither repo is fully green at base, and that after 5a7b463 no `pandas_ta/` file differs
  from base. The row claims neither suite green; it states that neither repo is fully green
  at base (corrected in round 2: this bullet first said the word "green" was not used).
- MINOR log "every figure" → rewritten with each figure's actual source (log line above).
- NIT Gate C "finite" → "374,196 non-NaN (`non_nan`) and 374,196 non-zero (`non_zero`)".
- NIT provenance → added `git diff b0422ad 0156f88` for the dictionary / contract / README
  counts and `run.log` / `journal.json` / `git log` for the Gate E timing.
- NIT `.pyc` files → not applied. ASSUMPTION: the session's allowed commands (pytest,
  `python docs/…`, and a fixed set of git commands) include nothing that deletes an untracked,
  gitignored file, so they stay. Git ignores them, and (the reviewer's reading, not
  re-checked) Python will not import them without their source.
- Round 2 dispatched because the Gate F row, filled after round 1, was never reviewed.

## Review round 2

Scope: the Gate F row, the round-1 fixes, and the `.pyc` ASSUMPTION.

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/reviews/auto-2026-10-26-bt-dma-dist-revert/01-BT-DMA-DIST-revert.md:121-125 ("Fixes applied", MINOR Gate F bullet)
    problem:  The bullet ends with "The word 'green' is not used." Two lines earlier the same bullet says the row "says neither repo is fully green at base". The Gate F row at docs/DicksonMaMeasured.md:165 does contain "Neither repo is fully green at base either." So you wrote a false sentence about your own text, in the paragraph that reports how you fixed a finding about unchecked claims. You did not grep your own row before describing it. That is the CLAUDE.md "claim written before it was measured" defect again, and this time the claim is about your own work.
    fix:      Replace "The word 'green' is not used." with "The row claims neither suite green; it states that neither repo is fully green at base."
  - severity: MINOR
    location: docs/DicksonMaMeasured.md:165 (Gate F row, "Those counts equal the launcher's base `b0422ad` run")
    problem:  Round 1 asked you to say that the two failures also fail at base. You wrote that the counts are equal. "2 failed" at base and "2 failed" after the revert does not show they are the same two tests, and the reader is left to assume it. The evidence is in the run folder: `C:/Users/Tolga/.issue-solver/runs/20261025-210235-147/tests/pandasta-base.xml` (`failures="2" skipped="83" tests="3247"`, so 3,162 passed) names exactly `tests.test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` and `tests.test_pine_coverage_csv::test_audited_rows_carry_their_evidence`. Its classic path is `D:\AwakenAnalytics\PandasTaWork\_clean\AlternativeRepos\pandas-ta-classic`, not the path your run printed. You had the receipt and did not cite it.
    fix:      After the counts clause, add: "and the same two tests are the base run's two failures (`tests/pandasta-base.xml` in the run folder: failures=2, those two testcases; at base the classic path is `…\PandasTaWork\_clean\AlternativeRepos\pandas-ta-classic`)."
  - severity: NIT
    location: docs/DicksonMaMeasured.md:165 (Gate F row, "Backtesting … at both base and HEAD")
    problem:  "HEAD" here means 0156f88, copied from `tests.md`. Once the receipt is committed, HEAD is the receipt commit on top of 5a7b463. Someone reading at that point will take "HEAD" as a post-revert Backtesting run, and none exists. The next sentence corrects it, but only after the reader has already been misled. Your own "Fixes applied" bullet says "at base and 0156f88". The row should say the same.
    fix:      Change "at both base and HEAD" to "at both base and 0156f88".
SUMMARY: The Gate F row was the only thing in scope that had not been reviewed. I checked every number in it, and every number holds. Post-revert: 2 failed / 3,162 passed / 83 skipped in 1,050.57 s, matching the quoted run. Base in `tests.md`: 3,162 / 2 / 83 with 0 errors. 0156f88: 3,201 / 2 / 83, 0 regressions, and 39 new tests, which equals 3,201 − 3,162 and the 39 at :22. Backtesting: 1,584 / 16 / 4 / 14 at both runs, and both XMLs total 1,618. Both failure messages match the quoted output word for word. The `supertrend` / `RA2vGpkA-ta.pine` break is in CLAUDE.md "Known breaks". `git diff --name-status b0422ad`, against both HEAD and the working tree, lists four added docs and nothing under `pandas_ta/`. 5a7b463's stat is 10 files, 19 insertions, 744 deletions, dated 2026-10-26. Gate E timings: run.log 22:59:08, journal.json 304 s, git log 22:42:50. No new text in the receipt or the log trips the prose guards that walk `docs/`. All five round-1 fixes you claim were carried out are in the files. The `.pyc` ASSUMPTION is honest. `task.md:61` allows nothing that removes an untracked ignored file: `git restore` and `git rm --cached` don't do it, and `task.md:55` says "Never delete or rename a file". Python does not import a sourceless `__pycache__` file. What is left is sloppiness about your own text. You wrote that a word does not appear in a row where it does. You wrote "counts equal" when the XML naming the same two tests was sitting in the run folder. And "HEAD" will point at the wrong commit as soon as you commit. Fix those three sentences. That was acceptable. Barely.
```

### Fixes applied
- MINOR "green" bullet → reworded as the fix says (bullet above, marked as corrected).
- MINOR same two failures → the Gate F row now adds that the same two tests are the base
  run's two failures, citing `tests/pandasta-base.xml` (`failures="2"`, those two testcases;
  re-read by the executor with Grep before citing). The classic-path detail was not added:
  it was not re-checked.
- NIT "base and HEAD" → "base and 0156f88".

## Outcome
PASS (round 2). Both MAJORs of the pre-push gate carried out (revert 5a7b463; receipt with
the measured Gate E numbers and Gates A / C marked not completed); the MINOR and NIT of the
gate are moot with the revert (test file deleted, base text restored).
