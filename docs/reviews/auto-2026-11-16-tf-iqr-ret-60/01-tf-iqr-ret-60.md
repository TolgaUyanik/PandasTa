# Task log — `tf-iqr-ret-60`

**Task:** port TSFEL's `interq_range` over 60 daily returns as
`pandas_ta/statistics/tf_iqr_ret_60.py` (column `TFIQRRET_60`), through
Gates A–D, the five wiring touch points, a test module and
`docs/TfIqrRet60Measured.md`. PandasTa issue **#117**.
**Lane:** main thread. **Gate:** Fletcher reviewer subagent (`Explore`,
read-only), one per round.

---

## Implementation summary

**The column.** `r = close / close.shift(1) - 1`, then
`r.rolling(60).quantile(0.75) - r.rolling(60).quantile(0.25)` — the screen
prototype's expression, kept literally so the port and the screened
prototype are the same arithmetic to the last bit. At `length` 60 that
reads exactly four of the window's 60 returns, ranks 15, 16, 45 and 46
counting up from the smallest.

**What the module adds over the prototype:** a close-level guard (a close
that is not a finite, normal, positive float has no return to take, so it
is NaN), `errstate(over="ignore")` scoped to the ratio, and a finiteness
mask on the returns. The last of those turned out to be **defence in
depth** rather than work — pandas' `rolling.quantile` already blanks a
whole window holding one infinity — and that is measured and said plainly
rather than implied away.

**Wiring (five touch points):** the module; `statistics/__init__.py`;
`Category` in `pandas_ta/__init__.py`; the `df.ta.tf_iqr_ret_60()`
accessor in `core.py`; `tests/test_tf_iqr_ret_60.py`. Plus the four
document counts that drift if a port forgets them: `CATEGORY_TOTAL`
353 → 354 in `tests/test_altport2_ports.py`, README 353 → 354 / 361 → 362 /
statistics 55 → 56, `docs/IndicatorDictionary.md` regenerated, and
`docs/MLCompanionContract.md` 698 → 699 tagged columns / 336 → 337 `SF`.

**Evidence:** `docs/measure_tf_iqr_ret_60.py` (14 sections) prints every
figure; `docs/measure_tf_iqr_ret_60_cpu.py` re-runs the module and any
section with numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled, and
refuses to run if the environment edit did not take. Receipt:
`docs/TfIqrRet60Measured.md`.

**Gate results.** A: bit-equal to three independent oracles — a retyped
pandas `roll_quantile`, the source's own `np.percentile` spelling, and an
exact `fractions.Fraction` oracle — on 1,440 of 1,440 bars of each of ten
1,500-bar frames, 0.00 ulp. B: 0 of 35 offsets leak; five live mutants
caught 24–35 of 35; the sixth (the NaN mask's own index) is DEAD on a
clean frame and caught 12 of 12 on a frame designed for it, moving exactly
bar J−1. C: fires 1,440 of 1,500 on every frame, non-negative everywhere
measured, real-data limb owed from Gate E. D: ×8/×64 bit-identical, a
level shift moves every bar so the check is not vacuous. E: **pending, run
by issue-solver after this session**, with an OWED `ts_q05_60` check
carrying a revert rule. F: 272 passed / 1 skipped under both dispatches;
full suite 2 failed / 11,427 passed / 86 skipped, both failures expected
and named.

### ASSUMPTIONS logged (AskUserQuestion is unavailable; conservative reading taken)

See `00-manifest.md`, Phase 2 — A1 the column name, A2 simple returns, A3
pandas' quantile arithmetic, A4 ship-with-disclosure rather than revert.

---

## Round 1 — REVISE

Verdict verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: pandas_ta/statistics/tf_iqr_ret_60.py:363 (docstring, "no dispersion floor" block) and docs/TfIqrRet60Measured.md:370 (§C2)
    problem:  You wrote "The ladder's two values are the ONE figure in this port that moves between numpy dispatches" — and then, 500 lines down in your own receipt, §F2 says "So **two** things move on this machine besides the timing" and carries the row "§D2 individual (frame, factor) cells | e.g. walk ×3.7 1.890e-14 | **moves**: 1.972e-14". I re-ran both dispatches: walk ×3.7 relative difference 1.890e-14 -> 1.972e-14, walk ×0.1 1.923e-14 -> 2.223e-14, walk ×3.7 max |diff| 3.331e-16 -> 4.163e-16. So the shipped docstring asserts "ONE" where your own measurement says two, and §C2 repeats it as "the one figure in this file" while §F2 of that same file refutes it. A reader of the module — which is where a consumer looks — is told the port has exactly one dispatch-sensitive number. That is the defect class CLAUDE.md names, dressed in a count.
    fix:      In both places, say what the run says: "the ladder's reading is the only figure that moves apart from the §D2 relative-difference cells (walk ×3.7 1.890e-14 -> 1.972e-14); §F2 lists both." Keep "ONE"/"the one figure" only if you delete the §D2 row, and you cannot, because it is true.
  - severity: MINOR
    location: pandas_ta/statistics/tf_iqr_ret_60.py:373-374
    problem:  "the quiet frame survives it, its smallest window return range being 3.751e-06, and so do all ten ordinary frames, the walk's smallest being 4.470e-02." `section_G` computes the smallest window return range for exactly four frames — flat, ladder, quiet, walk — and prints four lines. Nine of your "all ten" were never measured. The claim is almost certainly true and is still unearned, and the receipt's §G5 table is honest enough to list only the four, so the docstring is the only place that over-reaches.
    fix:      Either loop the floor-cost probe over `FRAMES` in `section_G` and print ten smallest-range rows (then the sentence is backed), or cut it to "and so does the walk, whose smallest window return range is 4.470e-02".
  - severity: MINOR
    location: tests/test_tf_iqr_ret_60.py:1011 (test_a_flat_frame_reads_exactly_zero_and_a_ladder_reads_its_jitter)
    problem:  The test's own docstring says "⚠ The ladder's reading is DISPATCH-DEPENDENT and that is why it is a bound and not a value" — and the next lines assert `float(lad.min()) == 0.0`, which is a value, on the exact quantity §F2 flags as moving (2 doubles up to 5.551e-17 by default, 1 double of 0.0 with AVX off). It holds on both dispatches on this machine because at least one of the 240 windows collapses its read ranks; nothing structural guarantees that on a third CPU where the constant rate renders as a different pair of doubles. `lad.max() < 1e-15` and `len(set(lad)) <= 4` are already the right shape; the min is the one line that can break the launcher's CI-CPU re-run.
    fix:      `assert 0.0 <= float(lad.min()) < 1e-15` — and drop "min exactly 0.0" from the §C2 sentence that describes this test's assertions as a BOUND.
  - severity: MINOR
    location: docs/TfIqrRet60Measured.md §F1 ("Full suite, on this worktree: 2 failed, 11,425 passed, 86 skipped")
    problem:  Measured just now, `python -m pytest -q -p no:randomly`: **2 failed, 11,427 passed, 86 skipped**, and the two failures are exactly the two you name. 11,425 is the count from before you added `test_pandas_already_blanks_a_window_holding_an_infinity` and `test_deleting_the_mask_line_changes_nothing_on_this_pandas`; you updated §F1's module row to 272 and left the full-suite row at the pre-edit number. A receipt whose suite line is stale by the size of its own last edit is a receipt that was not re-read after the edit.
    fix:      Rewrite the line as "2 failed, 11,427 passed, 86 skipped" from a fresh full run, and re-check the §F2 header counts the same way whenever the test module changes.
  - severity: NIT
    location: docs/TfIqrRet60Measured.md §B ("The test pins bands (`forward_return` 18–35, `back_date_two` 20–35, the rest 30–35)")
    problem:  `CAUGHT["back_date_two"]` is per frame: walk (26, 35), tick-rounded (20, 35), heavy-tailed (24, 35). "20–35" is the loosest of the three quoted as if it were all three, so a reader checking the receipt against the test finds a floor 6 points lower than the code enforces on the walk.
    fix:      "back_date_two 26 / 20 / 24 – 35, per frame".
  - severity: NIT
    location: docs/measure_tf_iqr_ret_60.py, section_C inline comment ("Windows built to put ranks 15..45 on ONE value")
    problem:  The construction is `14 + 32 + 14`, i.e. indices 14..45, which is ranks 15..46 one-based — what the receipt §C3 and the docstring both say. The script's own comment says 15..45 and so disagrees with the two documents it is the evidence for.
    fix:      Make the comment read "ranks 15..46 (indices 14..45)".
SUMMARY: The mathematics is not where you are weak, and I will not pretend to be impressed by it: three independent oracles bit-equal on 14,400 bars, an exact `Fraction` oracle at 0.00 ulp, six mutants with the dead one dissected and then caught 12 of 12 on a frame built for it, x8/x64 bit-identity with a level shift proving the check is not vacuous, five wiring points plus README, dictionary, contract and CATEGORY_TOTAL all moved, Gate E owed and fenced with a revert rule and a test that fails if the fence is dropped. I reproduced every section of the measurement script and every figure in §A1–§A6, §B, §C, §D, §G, §O, §S matched to the digit, under both numpy dispatches, 272 passed / 1 skipped each way. Then you wrote "the ONE figure in this port that moves between numpy dispatches" into the shipped docstring while your own §F2 table, in the same deliverable, says two and names the other — and I measured the other. You also told me all ten frames survive the siblings' floor when you measured one, pinned `lad.min() == 0.0` as a "bound" in the very test whose docstring warns that it is dispatch-dependent, and left the full-suite count two short of the suite you yourself grew. Not one of these is the arithmetic. Every one of them is you asserting a number nobody ran. Fix the four and the two polish items, re-run the suite, and this ships.
```

### Round 1 fixes applied

| finding | what changed |
|---|---|
| MAJOR, the "ONE figure" count | `pandas_ta/statistics/tf_iqr_ret_60.py` and §C2 now both say **two** things move between the dispatches, name the other (§D2's relative-difference cells, walk ×3.7 1.890e-14 → 1.972e-14), and point at §F2 as the single place that lists them. No section claims a count of dispatch-sensitive figures any more except §F2 itself. |
| MINOR, "all ten ordinary frames" | `section_G`'s floor-cost probe now loops over the three degenerate frames **and** all ten `FRAMES`, printing 13 rows. §G5 carries the full table; the docstring quotes the measured range, 2.000e-02 (two-point) to 6.913e-02 (heavy-tailed), with the walk's 4.470e-02. |
| MINOR, `lad.min() == 0.0` | now `0.0 <= float(lad.min()) < 1e-15`; the test's docstring says BOTH min and max are bounds and why; §C2 no longer describes the min as exactly 0.0. |
| MINOR, stale §F1 | re-ran the full suite: **2 failed, 11,427 passed, 86 skipped**. §F1 corrected; §F1's module row and §F2 re-read against the grown module (272 passed / 1 skipped, both dispatches). |
| NIT, §B band | now "`forward_return` 18–35 on each of the three frames, `back_date_two` 26–35 / 20–35 / 24–35 per frame (walk / tick-rounded / heavy-tailed), the other three 30–35 on each." |
| NIT, `section_C` comment | now "ranks 15..46 (indices 14..45)". |

### Work done after round 1 was dispatched, and so not in its verdict

Two gaps the author found by auditing their own prose while the review ran.
Both are recorded here because they changed shipped claims:

1. **The module's comment about `rolling.quantile` vs `np.percentile` was
   typed from the sibling, not measured.** It said the two "are not the
   same double" and "differ by at most one ulp per quantile" — while §A2
   measured them BIT-EQUAL. §A2 now runs the per-quantile comparison over
   all ten frames and five extra lengths (**28,800** and **14,404**
   readings, 0 disagreements), **probes** which `_lerp` branch numpy takes
   instead of recalling it (`np.percentile` is `b - d*(1-f)` on 20,000 of
   20,000 at q0.25 and `a + d*f` on 20,000 of 20,000 at q0.75, so q0.75's
   spelling is pandas' already and q0.25's is the non-trivial half), and
   measures that the two spellings genuinely CAN differ — 16 of 20,000
   random windows — but do not on **0 of the 14,400** windows these frames
   produce. The claim is now stated as a property of these frames and not
   as a theorem, in the module, the test docstring and §A2.
2. **The module's comment about the finiteness mask asserted work it does
   not do.** It said an infinity "could reach q75" and that dropping it
   kept the window trustworthy. Measured: pandas' `rolling.quantile`
   returns NaN for the WHOLE window on a single infinity, at both
   quartiles, and a mutant with the mask line DELETED is bit-identical to
   the module on a clean walk, an overflowing frame and the 1e308 cycle
   (650 shared bars, 0 differences). The line is now documented as defence
   in depth, with `test_pandas_already_blanks_a_window_holding_an_infinity`
   and `test_deleting_the_mask_line_changes_nothing_on_this_pandas` pinning
   both halves — which is also the mechanism behind Gate B's sixth mutant
   being dead.

---

## Round 2 — PASS (2 MINOR, 2 NIT), then fixed, so it does not count as the PASS

Verdict verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/TfIqrRet60Measured.md §F2, closing paragraph (lines 975-980)
    problem:  Round 1 killed a "one vs two" miscount in this exact section and it has grown back three lines below its own table. The table row (line 962) now reads "walk ×3.7 1.890e-14 / 3.331e-16; walk ×0.1 1.923e-14 → moves: 1.972e-14 / 4.163e-16; 2.223e-14" — two cells, three figures — while the paragraph under it still says "and one Gate D cell moves in its 15th digit". I ran both dispatches myself: default walk ×3.7 is 3.331e-16 / 1.890e-14 and AVX-off is 4.163e-16 / 1.972e-14; walk ×0.1 goes 1.923e-14 → 2.223e-14. And 3.331e-16 → 4.163e-16 is not a 15th-digit wobble in the reported figure, it is a 25% move in its first digit. The table is right and the sentence is wrong, which is the worse way round for the one sentence a reader skims.
    fix:      Replace "and one Gate D cell moves in its 15th digit" with what the row says: "and two Gate D cells move — walk ×3.7 in both its relative (1.890e-14 → 1.972e-14) and its absolute (3.331e-16 → 4.163e-16) figure, and walk ×0.1 in its relative one (1.923e-14 → 2.223e-14) — each by one ulp of the underlying value."
  - severity: MINOR
    location: pandas_ta/statistics/tf_iqr_ret_60.py:379-382
    problem:  The docstring names the second dispatch-sensitive item "the Gate D relative-difference cells (walk x3.7 1.890e-14 -> 1.972e-14)". Relative is not all of it: walk ×3.7's absolute max |diff| moves 3.331e-16 → 4.163e-16 and walk ×0.1's relative moves 1.923e-14 → 2.223e-14, both of which §F2 now tabulates and this line does not. The same sentence then closes "every other figure in this port is identical either way", where §F2's own summary is careful to say "besides the timing" — §Z's wall-clock is a figure in this port and it is not identical either way.
    fix:      Reword to "That and the Gate D per-cell tolerance figures (walk x3.7 1.890e-14 -> 1.972e-14 relative and 3.331e-16 -> 4.163e-16 absolute, walk x0.1 1.923e-14 -> 2.223e-14) are the two things measured to move between the dispatches; docs/TfIqrRet60Measured.md (F2) tabulates them, and every other figure in this port except the wall-clock is identical either way."
  - severity: NIT
    location: pandas_ta/statistics/tf_iqr_ret_60.py:101 and :289; tests/test_tf_iqr_ret_60.py:34
    problem:  "the two spellings DO differ on 16 of 20,000 random 60-draw windows" is stated unscoped in three places. 16 is q0.25's count. The receipt's own probe table (lines 129-130) prints 19,983 / 20,000 at q0.75, so at the other quartile they differ on 17. Verified by running `docs/measure_tf_iqr_ret_60.py A2`: 19,984 and 19,983. The figure is measured; the scope it is written in is not.
    fix:      In all three places write "on 16 of 20,000 random 60-draw windows at q0.25 and 17 at q0.75".
  - severity: NIT
    location: docs/TfIqrRet60Measured.md §Z (the paragraph under the cost table)
    problem:  "the same three measurements ... differ by about 45%" is the extreme dressed as the typical: 180/124 is 45%, 351/257 is 37%, 432/319 is 35%.
    fix:      Write "differ by 35-45%".
SUMMARY: Round 1's six findings are closed, and closed by measurement rather than by rewording — I re-ran them instead of taking your word. §G5's floor-cost probe now walks all thirteen frames and the smallest window return ranges print 2.000e-02 .. 6.913e-02 exactly as the prose claims; the ladder test pins `0.0 <= min < 1e-15` and both dispatches land inside it; §F1's full-suite line is now true to the digit (2 failed, 11,427 passed, 86 skipped on my own run, the two failures being the owed Gate E row and the missing sibling checkout); §B's back_date_two band is per frame; `section_C`'s rank comment counts correctly. The unprompted round-1.5 work holds up too: 28,800 and 14,404 single-quartile readings reproduce bit for bit, the `_lerp` branch probe prints 20,000/20,000 and 19,984/19,983 as tabulated, and A2's bit-equality is now stated as a property of these frames with the 16 disagreeing random windows admitted — which is the honest form and the one this repo keeps failing to write. The mask-line pair is real defence-in-depth, measured on 650 shared bars, not decorated as work. What is left is bookkeeping about bookkeeping: §F2's summary sentence undercounts the very cells its own table names, and the module docstring calls an absolute-tolerance move a relative one. You also edited the deliverables three times while I was measuring them — the AGGAC label and the dead `_pow2_window` warm-up vanished mid-review, which spares me two findings but means this verdict is on exactly these bytes. At those checksums the module tests are 272 passed / 1 skipped under both the default dispatch and with AVX512F AVX512_SKX AVX2 FMA3 off. That was acceptable. Barely.
```

All four applied. ⚠ The reviewer's suggested wording for its first finding
contained a mechanism clause — "each by one ulp of the underlying value" —
that was itself unmeasured; it was taken at round 2 and then **earned and
corrected** at round 3 (below), which is where it belongs in this log.

### Work done after round 2 was dispatched, and so not in its verdict

The reviewer noted it: three edits landed mid-review. Both were defects
found by self-audit, not drive-by changes.

1. **A comparator was mislabelled.** `TS_AGGAC_60_5` in the overlap table,
   the module docstring and the receipt — the column's default `maxlag` is
   **10**, so the name is `TS_AGGAC_60_10`. Fixed, and the whole class
   removed: `_comparators` now keys every entry by the Series' own `.name`
   instead of a typed-in string, so a label there cannot drift again.
2. **Dead code in the measurement script.** `_pow2_window` existed only to
   feed one line of `section_A4` that computed nothing and was commented
   "warm the fn". Both deleted.
3. **§A2 and §C2 gained the two-dispatch readings** for the figures §F2
   reports as moving.

---

## Round 3 — PASS (3 MINOR, 2 NIT), then fixed, so it does not count either

Verdict verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/TfIqrRet60Measured.md:405-408 (§C2, the ⚠ after the ladder table)
    problem:  Round 2 told you the module docstring named the second dispatch-sensitive item "the Gate D relative-difference cells" and claimed everything else was identical when §Z's wall-clock is not. You fixed the docstring — line 380-385 now names the absolute figure and says "except the wall-clock" — and left the IDENTICAL sentence standing in the receipt: "⚠ It is one of **two** things measured to move between the dispatches — the other is §D2's individual relative-difference cells". Measured here under both dispatches: walk ×3.7 moves in its ABSOLUTE figure too (3.331e-16 → 4.163e-16), which §F2's own row 963 prints, and §F2's last row says the wall-clock moves as well. So §C2 under-names the move and over-claims the count by omitting the timing, in the same file whose §F2 gets both right. A fix applied to one of two places carrying the same sentence is a fix half-applied.
    fix:      Rewrite 405-408 to mirror the docstring's corrected form: "⚠ It is one of two things that move between the dispatches apart from the wall-clock — the other is §D2's walk ×3.7 cell in BOTH its relative (1.890e-14 → 1.972e-14) and its absolute (3.331e-16 → 4.163e-16) figure and walk ×0.1 in its relative one (1.923e-14 → 2.223e-14) — and §F2 is the single place that lists them."
  - severity: MINOR
    location: docs/TfIqrRet60Measured.md:980-984 (§F2 closing paragraph, "each by one ulp of the underlying value")
    problem:  The figures in that sentence are right — I reproduced all three under `measure_tf_iqr_ret_60_cpu.py D`. The mechanism clause bolted to them is a number nobody ran. "one ulp of the underlying value" fails under every reading available: the absolute cell moves by 8.33e-17 on a column whose walk values live in 1.178554e-02 .. 3.083563e-02, where one ulp is 1.73e-18 or 3.47e-18 — 24 to 48 ulps, not one; the relative cells move by 8.2e-16 and 3.0e-15 where one relative ulp is ~2.2e-16 — four to fourteen. Nothing in `docs/measure_tf_iqr_ret_60.py` prints an ulp distance for §D2 at all (`grep ulp` finds it only in §A3's oracle). This is the repo's signature defect, shrunk to four words and tucked into the one section whose job is to say exactly what moves.
    fix:      Either delete the clause and stop at "…(1.923e-14 → 2.223e-14)", or earn it: have `section_D` print `|a-b|` at the max cell in ulps of the column value (`_ulps`) under each dispatch and quote the measured figure instead of "one".
  - severity: MINOR
    location: pandas_ta/statistics/tf_iqr_ret_60.py:395-396 and docs/TfIqrRet60Measured.md:637 ("widest window return range 4.441e-16 either way")
    problem:  `section_G` prints exactly one range per frame and labels it "smallest window return range" (docs/measure_tf_iqr_ret_60.py:1053-1054); the ladder's is 4.441e-16. Both the shipped docstring and §G5 re-label that print as the WIDEST. Under AVX-off the two coincide by accident — the frame holds 3 return doubles spanning 4.441e-16, so smallest = widest — but under the default dispatch the frame holds 4 doubles spanning 6.661e-16, and nothing printed rules out a 60-window holding both extremes, i.e. a widest of 6.661e-16. A receipt that opens with "every number in §A1–§A6, §B, §C, §D, §G, §O, §S and §Z is printed by the script" must not quote a figure the script prints under the opposite label.
    fix:      Add `float(rng_[fired].max())` to the `section_G` floor-cost print and quote the measured widest in both places; or, if you will not re-run it, reword both to "smallest window return range 4.441e-16 either way", which is what the run says.
  - severity: NIT
    location: docs/measure_tf_iqr_ret_60.py:105-111 (`_two_point` docstring) and :792 (the §C caption)
    problem:  The builder's docstring says the two-point column "takes few values but they are far apart" and the caption three lines above its own print says "few values, but NOT numerically a constant". The print that follows reads `5 distinct doubles, span 2.220e-16 (1.110e-14 relative)`, all five at 0.02, and §A4 line 218, the test module's `_two_point` docstring and the module docstring all read that as numerically constant rounding — which is the whole reason Gate D asserts the relative difference on this frame instead of the Spearman. The evidence script contradicts the three documents it is the evidence for, exactly as its `section_C` comment did in round 1.
    fix:      Reword both to the measured reading: "Every return is ±1%, so every window's q25 is −0.01 and q75 is +0.01 and the column sits at 0.02 — 5 doubles spanning 2.220e-16, numerically a constant. The Gate D tie frame."
  - severity: NIT
    location: docs/reviews/auto-2026-11-16-tf-iqr-ret-60/00-manifest.md:31
    problem:  "following the four `tf_*` siblings already in `statistics`" and then five names: `TFCENTROID`, `TFDFA`, `TFHIGUCHI`, `TFSPECENT`, `TFZEROCROSS`. `Category["statistics"]` carried five `tf_*` entries before this port. A count contradicted by its own list, in the file that records how you decided the column's name.
    fix:      "the five `tf_*` siblings".
SUMMARY: The arithmetic is not in question and I will not dwell on it: I re-ran all fourteen sections under both numpy dispatches and every digit in §A1–§A6, §B, §C, §D, §G, §O, §S matched — 1,440 of 1,440 bit-equal against three independent oracles at 0.00 ulp, 28,800 and 14,404 single-quartile readings, five live mutants at 34/28/31, 35, 25/25/24, 35, 35 inside their bands, the dead sixth caught 12 of 12 at exactly J−1, ×8/×64 bit-identical with a level shift moving all 1,440 bars, 272 passed / 1 skipped default and 272 passed / 1 skipped with AVX-512/AVX2/FMA3 off, full suite 2 failed / 11,427 passed / 86 skipped with both failures the two you named. The five wiring points, CATEGORY_TOTAL 354, README, dictionary and contract all moved, and Gate E is fenced with a revert rule and a test that fails if the fence is dropped. What is left is the same disease in a smaller dose: round 2 made you rewrite one sentence about what moves between dispatches, and you rewrote it in the module and not in §C2, which still names only the relative cells and still forgets the clock; you then bolted "each by one ulp of the underlying value" onto correct figures when the move is twenty-four to forty-eight ulps and no run prints an ulp there; and your docstring calls a number "widest" that your own script prints as "smallest". Three sentences, none of them mathematics, all of them written rather than measured. Fix them and stop re-typing claims your scripts already answer. That was acceptable. Barely.
```

### Round 3 fixes applied

| finding | what changed |
|---|---|
| MINOR, §C2's half-applied sentence | §C2 now mirrors the corrected form, names the absolute figure, and says "apart from the wall-clock". |
| MINOR, "each by one ulp" | **Earned, not deleted.** `section_D` now prints a `max ulp` column — the same distance as `max |diff|`, in units of the last place of the COLUMN's own value, via `_ulps`. Measured **32 .. 208** ulps across the 16 (frame, factor) cells, so the clause was wrong by two orders of magnitude; it is gone, §D2's table carries the column per frame, and §F2 now states the bounds that do NOT move (≤ 4.163e-16, ≤ 2.672e-14, ≤ 208 ulps). |
| MINOR, "widest" vs "smallest" | `section_G`'s floor-cost print now gives BOTH per row. The ladder's measured widest is **6.661e-16** by default and 4.441e-16 with AVX off; the docstring and §G5 say so, and §F2 gained a row for it. |
| NIT, `_two_point` and the §C caption | both reworded to the measured reading. |
| NIT, the manifest's "four" | "five", read out of `Category["statistics"]`. |

### Work done after round 3 was dispatched

Seven more, all found by re-reading the author's own prose against the
script's output while the review ran:

1. §A2's "16 of 20,000" was unscoped in a **fourth** place.
2. §A3 quoted `ts_q05_60`'s one-ulp figure without attribution.
3. §A4's "their returns are exact negations" — the returns the frames are
   BUILT from are; `cumprod` and the module's re-derivation re-round them,
   which is why the agreement is seven figures and not bit-equality.
4. The docstring said all three Gate A oracles' bit-equality "is explained
   by the quartiles being exact binary fractions". Only the third is.
5. The test docstring's ladder "two values on 240" lacked the dispatch
   caveat.
6. §Z and the docstring carried two timing runs; a third was measured and
   all three are now shown.
7. "The other fork columns that landed AFTER the screen" was an unverified
   claim about ten columns, so a `git log --diff-filter=A` date table was
   added — **and round 4 found that table wrong**; see below.

---

## Round 4 — REVISE (1 MAJOR, 2 MINOR, 2 NIT), the round cap

Verdict verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/TfIqrRet60Measured.md §E0 table (lines 914-923) and pandas_ta/statistics/tf_iqr_ret_60.py:207-210
    problem:  You replaced an unverified claim with a table and then did not run the command you cite. §E0 says "Read out of git rather than assumed — `git log --diff-filter=A` on each module file gives the date the column entered the tree", and three of its nine rows disagree with git. Measured just now, `git log --diff-filter=A --format='%h %ad %cd' --date=short --name-only`: `tf_zero_cross_20.py` is `22407b5`, author AND commit date **2026-11-15**, where your table says 2026-10-30. `tf_centroid_20.py` is `4f1063b`, **2026-10-30** both ways, where your table says 2026-11-14. `tf_higuchi_30.py` is `2148671`, **2026-11-16** both ways, where your table says "the file ... 2026-11-12" and then footnotes 2026-11-16 as the Category entry — so the file row is wrong and the footnote is the real date. (`ts_strike_20.py` is `0f09487`, author 2026-11-12 / commit 2026-11-15; your 2026-11-15 survives only under the committer date, which is not what plain `git log` shows.) It reads like a rotation of three dates between three names, and it is in the one block you added this round specifically to earn a claim by measurement. Worse, it propagates into the SHIPPED docstring: "every `ts_*` and `tf_*` column below entered the tree between 2026-10-30 and 2026-11-15" — `TFHIGUCHI_30` is in that list and its module entered on 2026-11-16, which your own §E0 footnote states. A consumer reading the module is given a range the receipt refutes. The conclusion ("all after 2026-10-24") survives; the evidence does not.
    fix:      Re-run `git log --diff-filter=A --format=%ad --date=short --name-only --` per module file and retype §E0 from the output: `tf_centroid_20` 2026-10-30, `lot_zeroret_60` 2026-11-02, `ts_strike_20` 2026-11-12, `ts_kurt_60`/`ts_ac1_60`/`ts_aggac_60`/`ts_imq_20` 2026-11-13, `ts_q05_60` 2026-11-14, `tf_zero_cross_20`/`tf_dfa_100`/`tf_spec_entropy_64` 2026-11-15, `tf_higuchi_30` 2026-11-16. State which date field you read (author or committer) since `ts_strike_20` differs between them. Then change the docstring range to "between 2026-10-30 and 2026-11-16" and delete the now-redundant "Category entry 2026-11-16" parenthetical.
  - severity: MINOR
    location: docs/TfIqrRet60Measured.md §F2 (row at line 995 and the paragraph at 1008-1017), §C2 (411-415), and pandas_ta/statistics/tf_iqr_ret_60.py:384-389
    problem:  Round 3 made you add §D2's `max ulp` column to earn the "one ulp" clause. You then did not re-read the sections that enumerate what moves between dispatches. §D2's walk row brackets the AVX-off ulp reading as "144 .. 160 **[.. 176]**" — so a third (frame, factor) cell moves — and I reproduced it: walk ×1.0000001 is 160.0 ulps by default and **176.0** with `AVX512F AVX512_SKX AVX2 FMA3` off, while its `max |diff|` (3.608e-16) and relative (2.251e-14) are identical either way. §F2's row lists only "walk ×3.7 1.890e-14 / 3.331e-16; walk ×0.1 1.923e-14" with no ulp figure at all, §F2's paragraph says "**two** Gate D cells move" and names two, §C2 repeats the same two, and the module docstring closes with "every other figure in this port except the wall-clock is identical either way" — which §D2's own bracket contradicts. Same section, same sentence, two answers. (§F2's "§G5 floor-cost table, all thirteen rows ... **identical**" has the same defect in miniature: the ladder's widest window return range is 6.661e-16 by default and 4.441e-16 with AVX off, which is one of those thirteen rows and which §G5 itself brackets.)
    fix:      Make §F2's §D2 row carry the ulp column — "walk ×3.7 1.890e-14 / 3.331e-16 / 144 ulp; walk ×0.1 1.923e-14; walk ×1.0000001 160 ulp" → "1.972e-14 / 4.163e-16 / 144; 2.223e-14; 176" — say "three Gate D cells move" in the paragraph and in §C2, and change the docstring's closing clause to "every other figure in this port except the wall-clock and §D2's walk cells is identical either way". Qualify the §G5 row as "all thirteen rows; the ladder's widest return range moves (see the row above)".
  - severity: MINOR
    location: tests/test_tf_iqr_ret_60.py:1231-1241 (test_no_warning_is_raised_on_bad_closes)
    problem:  The docstring asserts "none of the **five** bad-close kinds reaches a warning" and the body sets four: `inf`, `0.0`, `-5.0`, `1e-310`. The kind it omits is the one a reader would actually worry about — `NaN`, which reaches `c >= np.finfo(float).tiny` as a NaN comparison — and it is the fifth label of your own §A6 guard table (inf / zero / subnormal / negative / nan). Everywhere else in this port the bad-value set is six (`test_a_bad_close_empties_its_windows_and_nothing_earlier` parametrises `nan, inf, -inf, 0.0, -100.0, 1e-310`, §G1's "six bad values ... 30 pairs"). §G6 is honest and names the four. So the test docstring is the only place carrying a count no run covers.
    fix:      Add `close.iloc[300] = np.nan` and `close.iloc[50] = -np.inf` to the body and say "none of the six bad-close kinds", or cut the docstring to the four the body sets and keep §G6's wording.
  - severity: NIT
    location: tests/test_tf_iqr_ret_60.py:610-618 (test_the_tie_frame_is_five_nearly_equal_doubles)
    problem:  `assert 2 <= len(v) <= 12` puts a non-collapse FLOOR on a distinct-value count for the frame your own §A4 calls "numerically a constant" (5 doubles spanning 2.220e-16). You reasoned about exactly this risk for the ladder — whose count did collapse from 2 to 1 under AVX off, which is why `test_a_flat_frame_reads_exactly_zero_and_a_ladder_reads_its_jitter` asserts `len(set(lad)) <= 4` with no floor — and then bet the other way here. Both dispatches on this machine give 5, so nothing fails today; the floor is simply a claim no mechanism guarantees on a third CPU, and the test's own name hard-codes "five" while its band admits 2 to 12.
    fix:      `assert 1 <= len(v) <= 12` — the span and 0.02 assertions below it still pass at one value — and rename to `test_the_tie_frame_is_a_handful_of_nearly_equal_doubles`.
  - severity: NIT
    location: pandas_ta/statistics/tf_iqr_ret_60.py:296-297 and docs/TfIqrRet60Measured.md:136-138
    problem:  "the two spellings differ on 16 of those 20,000 random windows at q0.25 and **17 at q0.75**". Traced to the script, "the two spellings" there means the two algebraic `_lerp` forms, and that is what `section_A2`'s probe counts — so 16 and 17 are both right. But the sentence lands two lines after "q0.75's spelling is already pandas'", where the salient pair is pandas-vs-numpy, and at q0.75 pandas and numpy agree **20,000 of 20,000**. So the 17 invites precisely the misreading the paragraph exists to prevent: that numpy and pandas disagree 17 times at q0.75. This is round 3's finding 3 again — a figure quoted under a label a reader resolves differently.
    fix:      "the two algebraic forms differ on 16 of those 20,000 windows at q0.25 and 17 at q0.75 — at q0.75 numpy takes the form that IS pandas', so those 17 are not pandas/numpy disagreements; the pandas/numpy disagreement count is 16 at q0.25 and 0 at q0.75."
SUMMARY: The arithmetic is beyond reproach and I am not going to applaud it twice. I reproduced every section of the measurement script under both numpy dispatches and every digit landed: three independent oracles bit-equal on 14,400 bars, an exact `Fraction` oracle at 0.00 ulp, the `_lerp` branch probed rather than recalled, 28,800 + 14,404 single-quartile readings, six mutants with the dead one dissected and then caught 12 of 12 on a frame built for it, ×8/×64 bit-identity with a level shift proving it is not vacuous, the ulp column you were made to add in round 3 measuring 32–208 and not "one", 272 passed / 1 skipped under both dispatches, full suite 2 failed / 11,427 passed / 86 skipped with exactly the two failures you name, five wiring points plus README, dictionary, contract and CATEGORY_TOTAL all moved, Gate E owed and fenced with a revert rule and a test that fails if the fence is dropped. And then, in the one block you added this round *because* a claim was unmeasured, you typed a `git log` table without running `git log`: `tf_zero_cross_20` is 2026-11-15 not 2026-10-30, `tf_centroid_20` is 2026-10-30 not 2026-11-14, `tf_higuchi_30` is 2026-11-16 not 2026-11-12 — and the shipped docstring now tells a consumer the range ends 2026-11-15 while your own footnote says 11-16. You also bolted a `max ulp` column onto §D2, watched it move 160 → 176 under AVX off, bracketed it in the table, and left three other places saying two cells move and "every other figure is identical". Four rounds in, the mathematics has never been the problem and the prose still is. Fix the dates, fix the count, and it ships.
```

### Round 4 fixes applied

| finding | what changed |
|---|---|
| **MAJOR, the `git log` date table** | The reviewer is right about the cause and the author can name it: `git log --diff-filter=A --format="%ad %H" -- fileA fileB …` prints **one line per commit in reverse-chronological order**, not one per path, and the dates were read off positionally against the path list. Re-measured **one file at a time**, with BOTH date fields: `tf_centroid_20` 2026-10-30, `lot_zeroret_60` 2026-11-02, `ts_strike_20` 2026-11-12 (committer 2026-11-15), `ts_kurt_60` / `ts_ac1_60` / `ts_aggac_60` 2026-11-13, `ts_imq_20` 2026-11-13 (committer 2026-11-14), `ts_q05_60` 2026-11-14, `tf_dfa_100` / `tf_spec_entropy_64` / `tf_zero_cross_20` 2026-11-15, `tf_higuchi_30` 2026-11-16. §E0's table carries all twelve rows with both fields, names which command produces them and why passing several paths at once is the trap; the docstring range is now 2026-10-30 .. 2026-11-16 and the parenthetical is gone. The conclusion — every one after 2026-10-24 — was right and is now backed. |
| MINOR, the third moving Gate D cell | Measured: walk ×1.0000001 is 160 ulps by default and **176** with AVX off, its absolute and relative figures identical. §F2's row now carries the ulp column, §F2's paragraph and §C2 say **three** cells, and the docstring's closing clause excludes "the wall-clock and those walk cells". §F2's §G5 row is qualified and the ladder's widest return range got its own row. |
| MINOR, the five-vs-four bad-close kinds | The body now sets all **six** (`-inf`, `inf`, `0.0`, `-5.0`, `1e-310`, `NaN`), the docstring says six and names why `NaN` is the interesting one, and the test asserts the column still fires. |
| NIT, the tie-frame floor | `1 <= len(v) <= 12`, renamed `test_the_tie_frame_is_a_handful_of_nearly_equal_doubles`, with the reason — the ladder's own count collapsed 2 → 1 under AVX off — in the docstring. Both references updated. |
| NIT, "the two spellings" at q0.75 | All four places now say "the two ALGEBRAIC FORMS" and add the measured pandas-versus-numpy count: 16 at q0.25 and **0** at q0.75. |

After these, the module tests are **272 passed / 1 skipped** under both
dispatches and the full suite is **2 failed / 11,427 passed / 86 skipped**
with the two expected failures.

⚠ **No fifth round.** The loop caps at four (`~/.claude/CLAUDE.md`, "Review
loop: fix and re-review up to round 4"), so round 4's REVISE is the last
verdict on record. There are **no open findings** — all five were applied
and re-measured — but there is no post-fix PASS either, and this log says
so rather than implying one. Rounds 2 and 3 each returned PASS, and each is
disqualified as *the* PASS by the fixes that followed it.

### One thing observed and deliberately NOT fixed

Running `tests/test_wiring_accessors.py` before `tests/test_readme_counts.py`
in one process makes the latter fail: the former leaves `long_run`,
`short_run` and `td_seq` removed from `Category`, so the live count reads
351 against the README's 354 — exactly the three it removed. Reversing the
two files' order passes. It reproduces with this port's test module absent,
so it is **pre-existing**, it is invisible under the full suite's ordering
(which is why `python -m pytest -q` is green), and `tests/test_wiring_accessors.py`
is not among the files this issue may modify. Recorded here for the owner,
not fixed.
