# TS-CROSS-MEAN-20 — task log

Lane: main thread. Done criterion: issue #100's "Done when" — shipped
through Gates A–F with the numbers in `docs/TsCrossMean20Measured.md`, or
measured and reverted with that file kept as the receipt. Gate E and both
repos' suites are the launcher's.

## Implementation summary

`TS_CROSS_MEAN_20` = how many of the 19 adjacent pairs of a 20-bar window
of log closes sit on opposite sides of that window's own mean — tsfresh's
`number_crossing_m(x, m=mean)` on `x = log(close)`.

* `pandas_ta/statistics/ts_cross_mean_20.py` — `sliding_window_view` over
  `np.log(close)`, window mean from the window's own sum, two `(rows,)`
  boolean columns carried through a loop over the window positions, and a
  RELATIVE dispersion floor (`spread > 4096 eps · max |log c|`) that also
  serves as the bad-close mask. No magnitude bound (derived unnecessary:
  `|log c| ≤ 709.79`) and no `isfinite` backstop (the output is an integer
  count).
* Five wiring touch points, plus `CATEGORY_TOTAL` 332 → 333, README
  332 → 333 / 340 → 341 / statistics 41 → 42, `IndicatorDictionary.md`
  regenerated, `MLCompanionContract.md` 677 → 678 tagged / 52 → 53 `ORD`.
* `docs/measure_ts_cross_mean_20.py` (sections A B C D G O Z),
  `docs/measure_ts_cross_mean_20_cpu.py`, `docs/TsCrossMean20Measured.md`.
* `tests/test_ts_cross_mean_20.py`.

Verdict reached before review: **ship, pending Gate E.** Gate A bit-equal
against three independent oracles including `decimal.Decimal.ln` at 60
significant digits; Gate B 0 of 37 with six mutants; Gate C
`0 < 1,481 < 1,500`, no zeros; Gate D bit-identical at ×8/×64 as a
measurement with a six-order margin; in-fork overlap topping out at
+0.6296 against `chop` on synthetic frames.

### Two decisions the measurements reversed, before any review

* The counting step was first written as the source's own two lines (a
  `(rows, length)` bool matrix). Section Z, run twice in both orders with a
  warm-up call, showed the matrix form's traced peak growing 30.0 → 218.8
  MB with `length` where the loop's stays at 29.2 MB, with the times within
  noise. The loop shipped. (The first A/B, run without a warm-up, said the
  opposite — whichever spelling went second won. That is recorded in the
  module comment so the next person does not repeat it.)
* The designed Gate B probe for the shifted-floor mutant was first the
  sibling port's halt-patch frame, which caught it **3 of 37**. Deriving
  what the mutant can actually move (only bar J−1, and only when the
  floor's verdict on window J flips) produced the frame that catches it
  37 of 37. Both are kept in the receipt, because the contrast is the
  finding.

---

## Review round 1 — VERDICT: REVISE

Reviewer: fresh `Explore` subagent, Fletcher persona, read-only. It ran
all seven measurement sections, the test module, the AVX-off re-run and
the full suite, and reported every structural number reproducing to the
digit.

Findings, verbatim:

> - severity: MAJOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:27-32 (the NOISE_FACTOR comment block)
>   problem:  The shipped source asserts "an absolute `4096 eps` floor would never fire at all (measured in docs/TsCrossMean20Measured.md, Guards G3: it reports every one of the 280 pure-rounding windows of a flat frame that the relative floor refuses)." I ran the section it cites. G3 prints `flat  relative fires 0, absolute fires 0` — the absolute floor refuses the flat frame exactly as the relative one does, because 20 identical closes give `hi - lo == 0.0` and `0 > x` is False for either threshold. The count is wrong too: a 300-bar flat frame has 281 windows, not 280. And the sentence contradicts itself inside one parenthesis. This is the repo's named dominant defect — a claim written before it was measured — sitting in shipped code, citing as evidence a run that says the opposite.
>   fix:      Replace the parenthetical with what G3 actually printed.
>
> - severity: MAJOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:283-286 (also 74-76) and docs/TsCrossMean20Measured.md:321-325 (D0)
>   problem:  "nothing here is bit-identical BY CONSTRUCTION, which separates this column from every sibling tsfresh port in this package: those read price RATIOS". That universal is false, and it is false about the two siblings this very port spends §O1 measuring itself against. `ts_peaks_20.py` reads raw closes and comments at line 56 "Only comparisons are read: no difference, no ratio, no sum"; `ts_perment_20.py` reads raw closes too. Both ARE order-exact under a rescale by construction — precisely the property the paragraph claims only this column lacks.
>   fix:      Narrow the contrast to what is true.
>
> - severity: MINOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:272-275
>   problem:  The length-3 derivation has its inequality backwards: "...they would then have to sum to less than twice it." If `x1 = m` then `x0 + x2 = 2m` exactly, so two neighbours both strictly above `m` would sum to MORE than twice the tie. The Measured doc and the test docstring both have it right; only the shipped docstring, the copy a consumer reads, is wrong.
>   fix:      Change "less" to "more", with the reason.
>
> - severity: MINOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:290-293 and :108-111; tests/test_ts_cross_mean_20.py:64-65
>   problem:  Two sentences attach one measured count to a list of conditions that produced four different counts. "bit-equal on 1,481 of 1,481 ... at `length` 3 / 5 / 60 / 250" — D1b measured 1,498 / 1,496 / 1,441 / 1,251. "the two agree on every count (measured: 399,981 of 399,981 at `length` 20 and at 3, 60 and 250)" — §Z measured 399,998 / 399,981 / 399,941 / 399,751.
>   fix:      Split the clauses and quote the four numbers.
>
> - severity: MINOR
>   location: docs/TsCrossMean20Measured.md:428-444 (G3b) and docs/measure_ts_cross_mean_20.py:829-841
>   problem:  G3b is headed "how far a WINDOW's log closes must spread...in ulps of the window's own magnitude", but the x-axis the script prints is the FRAME's median spread normalised by a hard-coded nominal magnitude, not each window's own spread against its own `amax`. The grid also jumps 1,050 → 4,202, so "the floor sits at 4096 ulps, which is where the agreement becomes total" brackets a 4x range; the data is consistent with the true threshold being 1,200. "Calibrated, not guessed" is stronger than the run supports.
>   fix:      Bucket the windows by their OWN ratio across one frame, or soften the sentence.
>
> - severity: NIT
>   location: tests/test_ts_cross_mean_20.py:279 and docs/measure_ts_cross_mean_20.py:207
>   problem:  `_exact_windowed` sets `getcontext().prec = 60` on the process-global decimal context and never restores it.
>   fix:      Wrap in `decimal.localcontext()`, in both files.
>
> - severity: NIT
>   location: tests/test_ts_cross_mean_20.py:503-507 and :940-947
>   problem:  Two tests cannot fail. `test_the_share_is_an_exact_rescaling_a_rank_miner_cannot_see` asserts that dividing a series by a positive constant preserves ranks — true by the definition of rank. `test_no_magnitude_bound_is_needed_and_the_derivation_says_why` asserts three IEEE-754 constants.
>   fix:      Give them something to bite on, or delete them.

### Fixes applied, all seven

1. **MAJOR 1** — the `NOISE_FACTOR` block now states what G3 printed: the
   two floors are indistinguishable on the ordinary frames (flat 0/0, walk
   1,481/1,481, ladder 281/281, halt-patches 1,343/1,343) and separate at a
   price near 1.0, where the relative floor reports all 581 windows and the
   60-digit oracle confirms every one while the absolute floor keeps 44.
   "Would never fire at all" and the number 280 are gone.
2. **MAJOR 2** — the contrast is now enumerated and checked:
   `ts_peaks_20.py:40-59` and `ts_perment_20.py:53` were read, both take
   `close.to_numpy()` and `ts_peaks_20.py:56` says so in the source. The
   claim is narrowed to "the eight RETURN-based ports read ratios; the two
   close-based ones read only the ORDER; this one takes a LOGARITHM" in all
   four places (module comment, module docstring, receipt §0, receipt D0)
   and in the test-module docstring.
3. **MINOR 1** — the inequality is corrected and the derivation spelled
   out: with `x1 = m` the three values sum to `3m`, so `x0 + x2` is exactly
   `2m` and two values both above `m` would sum to more.
4. **MINOR 2** — both sentences now carry their four measured numbers.
5. **MINOR 3** — `docs/measure_ts_cross_mean_20.py` G3b was REBUILT rather
   than reworded: `_ramped_vol` generates a 6,000-bar frame whose per-bar
   volatility sweeps 1e-18 → 1e-08, and `_ulps_and_agreement` buckets its
   5,981 windows by **their own** `(hi − lo) / (eps · max |x|)`. The new
   measurement is less flattering and is reported as such: below 16 ulps
   float gets 0.5678 / 0.5198 of the counts right (price 100 / 1e+6), and
   above the floor — the last three rows of each of the two price columns,
   six cells in all — agreement is total in five and **350 of 351** in the
   sixth. The receipt now says the floor
   is "a strong filter and NOT a proof" and that 4096 is the siblings'
   constant placed where the error rate has already collapsed, not a
   measured threshold. A second table gives where the nine ordinary frames
   actually sit (worst window 1.27e+13 ulps, nine orders above the floor).
   The test asserts the bands and never 1.0.
6. **NIT 1** — `localcontext()` in both files.
7. **NIT 2** — `test_the_share_is_...` became
   `test_the_output_is_the_raw_count_and_not_the_share`, which asserts the
   values (a monotone window reads 1.0, not 1/19); the magnitude test now
   runs the MODULE at `tiny * 4` and `max / 4` at `length` 250 and asserts
   finite counts in [1, 249].

Test count 193 → **204**. `python docs/measure_ts_cross_mean_20_cpu.py`
→ 204 passed with AVX512/AVX2/FMA3 off. Full suite → 3 failed, 7,520
passed, 85 skipped (the same three expected failures).

⚠ One sentence in this fix log was itself wrong when first written: it
said the rebuilt G3b showed agreement "total in seven of the eight
admitted buckets". Round 2 counted the table and found six admitted
cells, five of them total. It was corrected in the receipt and in the
test docstring at the time — and NOT here, which round 3 caught: this
file went on carrying the bad count under a note claiming it had been
removed. Item 5 above now reads five of six.

---

## Review round 2 — VERDICT: REVISE

Same dispatch, fresh subagent. It re-ran A, B, C, D, G, O, Z, the test
module, the CPU script and the full suite, and reported every structural
figure reproducing. Two MAJOR, four MINOR, two NIT — and the first MAJOR
was a defect the round-1 FIX introduced.

Findings, verbatim:

> - severity: MAJOR
>   location: docs/TsCrossMean20Measured.md:458 (G3b), repeated verbatim at tests/test_ts_cross_mean_20.py:925-926 and docs/reviews/auto-2026-11-13-ts-cross-mean-20/01-ts-cross-mean-20.md:122
>   problem:  The paragraph written as the round-1 MINOR-3 fix invents a new count that its own run refutes: "Above the floor the agreement is total in seven of the eight admitted buckets, and 350 of 351 in the eighth." The floor admits ratios above 4096, which is three buckets per price column — six cells, not eight. Five of those six read 1.0000 and the sixth reads 350/351. There is no reading of the printed table under which "seven of the eight" is true. This is the repo's named dominant defect reintroduced by a fix, now in three committed files including the test docstring.
>   fix:      "total in five of the six admitted buckets, and 350 of 351 in the sixth", in all three places.
>
> - severity: MAJOR
>   location: tests/test_ts_cross_mean_20.py:80-83 (module docstring, item 5)
>   problem:  The round-1 MINOR-3 fix rebuilt G3b and retracted its conclusion, but the test module's docstring still carries the OLD, now-retracted measurement: "The 4096 is calibrated, not guessed: ... 265/381, 346/381, 371/381 and 377/381 ... and on 381/381 at 4,202." No committed script produces any of those numbers any more, and the conclusion is the exact opposite of what the same file says eleven lines further down.
>   fix:      Rewrite from the current G3b output; delete "calibrated, not guessed" and every 381/4,202 figure.
>
> - severity: MINOR
>   location: docs/measure_ts_cross_mean_20.py:467
>   problem:  Round 1's MINOR-1 (the backwards inequality) was fixed in the module docstring and nowhere else. The measurement script still prints "sum to less than twice the tie". The receipt's opening says every sentence can be re-derived by running this file; the file derives the claim backwards.
>   fix:      "more than twice the tie".
>
> - severity: MINOR
>   location: docs/TsCrossMean20Measured.md:460-462 and :481-483
>   problem:  (a) "the error rate has already collapsed by three orders" — the printed rate goes 0.4322 → 0.00285, a factor of 152, i.e. 2.2 orders. (b) "A1/A3 then measure the whole of those nine frames bit-equal against the exact oracle: 5,924 windows over four frames plus 1,743 over three quiet ones" — contradicts itself: 5,924 is 4 x 1,481, and A3 ran the 60-digit oracle on four frames only. Five of the nine have never been put to it; A1 checks them against a different oracle.
>   fix:      "by two orders", and split the sentence by oracle.
>
> - severity: MINOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:121-124 and tests/test_ts_cross_mean_20.py:1216-1218
>   problem:  "this form is also the faster of the two up to `length` 60" is asserted in two places. My re-run of section Z reverses it: shipped 34.1 / 61.9 / 101.5 / 312.9 ms against matrix 45.9 / 68.1 / 96.1 / 263.9 — at `length` 60 the matrix form is the faster one. The doc says "the milliseconds move between runs" and then asserts the direction anyway. The peaks reproduced to the digit.
>   fix:      Delete the speed claim; keep the memory claim.
>
> - severity: MINOR
>   location: tests/test_ts_cross_mean_20.py:534-543
>   problem:  `test_a_tie_cannot_separate_strict_from_weak_at_length_three` builds `[a, sqrt(a*b), b]` so the middle log ties the mean in EXACT arithmetic, then asserts strict == weak — without ever checking the tie survived to a double. Its length-4 sibling does exactly that. If rounding puts `x[1]` one ulp off, the test passes while testing nothing.
>   fix:      Assert `x[1] == x.sum() / 3.0` before comparing, as at :553.
>
> - severity: NIT
>   location: tests/test_ts_cross_mean_20.py:909 and :927
>   problem:  The docstring says "this test asserts a band rather than 1.0", but the `(16384, inf)` case is `at_least=0.9999` over 2,105 windows — one disagreement fails it. A pin on perfection wearing a band's clothes, and the assertion most exposed to a different CPU's last bits.
>   fix:      Lower to a bound that tolerates one window, or strike the clause.
>
> - severity: NIT
>   location: docs/TsCrossMean20Measured.md:37
>   problem:  "It is the only tsfresh port in this fork that takes a LOGARITHM" is refuted by its own enumeration: `ts_perment_20.py:85` and `ts_binent_20.py:88` both call `np.log`, on probabilities.
>   fix:      "the only tsfresh port whose WINDOW holds a logarithm of the price".

### Fixes applied, all eight

1. **MAJOR 1** — "five of the six admitted buckets, and 350 of 351 in the
   sixth", in the receipt and the test docstring. ⚠ It was NOT applied to
   this log at the time, although the sentence above claimed it had been;
   round 3 caught that and it is applied now.
2. **MAJOR 2** — the test module's item 5 is rewritten from the current
   G3b output (0.5678 / 0.8205 / 0.9307 / 0.9812 below the floor, 0.9972
   at [4096, 16384)), says the floor is a filter and not a proof, and no
   longer contains the words "calibrated, not guessed" or any 381/4,202
   figure.
3. **MINOR 1** — the measure script prints the derivation the right way
   round; re-run and read off the output to confirm.
4. **MINOR 2** — "by two orders", with the two rates quoted
   (0.4322 against 0.0028); and the oracle sentence split, naming the five
   frames the 60-digit oracle has NOT seen.
5. **MINOR 3** — the speed claim is deleted from the module comment, the
   module docstring and the test docstring, and §Z now carries all three
   timing runs side by side (mine, the reviewer's, mine again) so the
   reader can see the ordering flip at `length` 60 for themselves.
6. **MINOR 4** — the length-3 test now SEARCHES integer triples
   `[k/p, k, k*p]` for ones whose tie survives to a double, asserts it
   found at least 20, and only then compares the spellings.
7. **NIT 1** — the `(16384, inf)` bound is 0.998, and the docstring's
   claim about bands is now true of every case.
8. **NIT 2** — "the only tsfresh port whose WINDOW holds a logarithm of
   the price", with `ts_perment_20` and `ts_binent_20` named as the two
   that log probabilities.

204 tests still pass.

---

## Review round 3 — VERDICT: REVISE

Same dispatch, fresh subagent. (The first attempt at this round died on an
API session limit mid-run and was re-dispatched from scratch.) It re-ran
every section, the 204 tests, the CPU script and the full suite, and
reported every structural figure reproducing to the digit — A1, A3, B, C,
D, G3b, Z's peaks, the wiring, `CATEGORY_TOTAL` 333, README 333 / 341 /
statistics 42, the dictionary's 335, the contract's 678 / 53 `ORD`. Three
MAJOR, one MINOR, one NIT, and two of the three MAJOR were defects the
round-1 and round-2 FIXES introduced or failed to propagate.

Findings, verbatim:

> - severity: MAJOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:267-268 and docs/TsCrossMean20Measured.md:122-124 (A3b)
>   problem:  The shipped docstring ends Gate A with the unqualified universal "Float has not decided one comparison the wrong way in any run that the floor admitted", and the receipt bolds the same sentence and adds "Where it *does* get them wrong — below the floor — is measured in G3b, and those windows are refused." Both are refuted by G3b: the bucket `[4096, 16384)` at price 100 reads 351 windows / 350 exact / 0.9972. Those windows are ABOVE the floor, so one of them is admitted and miscounted. The receipt says so itself 340 lines later. The copy a consumer reads carries only the false half.
>   fix:      State the scope that was measured, and name the 350/351 as the limit of it.
>
> - severity: MAJOR
>   location: docs/reviews/auto-2026-11-13-ts-cross-mean-20/01-ts-cross-mean-20.md:122-123, with the false claims at :143 and :199-200
>   problem:  Round 2's MAJOR 1 was not fixed in this file. Line 122-123 still reads "seven of the eight admitted buckets ... in the eighth", while line 143 says "Corrected above and in the two other files" and :199-200 says the correction landed in "the receipt, the test docstring and this log". The receipt and the test docstring WERE corrected. The log was not. A fix log that lies about its own state is worse than no fix log.
>   fix:      Correct :122-123 and make the two claims about it true.
>
> - severity: MAJOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:122-123 and tests/test_ts_cross_mean_20.py:1241-1243
>   problem:  Round 2's MINOR-3 fix deleted a speed claim and installed a new one: "the two are within a fifth of each other". At `length` 3 the four recorded A/Bs are 32%, 35%, 24% and 36% apart. Not one is within a fifth, and three of them are in the committed table eleven lines below the sentence.
>   fix:      Drop the magnitude, or quote the measured one.
>
> - severity: MINOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:337-339
>   problem:  "roughly 35-100 ms at `length` 3-60 and 270-310 ms at 250" — three of the four endpoints are outside the project's own committed data (`length` 60 at 101.1 / 101.5 / 102.3; `length` 3 at 34.1 in run 2; `length` 250 at 269.7 and 312.9).
>   fix:      Widen to the measured range, or name the single run.
>
> - severity: NIT
>   location: pandas_ta/statistics/ts_cross_mean_20.py:341-342 and docs/TsCrossMean20Measured.md:694-696
>   problem:  "the window-by-window oracle ... is 174 ms on 20,000 bars" — my run prints 167.0, and unlike the shipped/matrix table this figure carries no wobble caveat.
>   fix:      Quote a band, or attach the caveat.

### Fixes applied, all five

1. **MAJOR 1** — Gate A's closing claim now states its SCOPE and its
   LIMIT, in both files: over every window A1/A2/A3/A3b admitted (13,329
   + 4,443 + 5,924 + 1,743) float decided no comparison wrongly, and
   ⚠ that is not a guarantee, because G3b's `[4096, 16384)` bucket holds
   one admitted, miscounted window in 351. The module docstring carries
   the warning as well as the result, and points at G3b and at the
   1.27e+13-ulp distance the ordinary frames keep from that edge.
2. **MAJOR 2** — item 5 of the round-2 fix list now reads "five of the
   six admitted buckets ... 350 of 351 in the sixth", and both sentences
   that claimed the correction had already landed now say plainly that it
   had not, and that round 3 caught it.
3. **MAJOR 3** — "within a fifth of each other" is gone from the module
   comment and the test docstring. What replaces it is the only
   time-related fact three runs agree on: the WINNER changes, two of the
   three complete A/Bs at `length` 60 going one way and one the other.
4. **MINOR** — the cost paragraph quotes the range across the three
   complete runs: 34.1-102.3 ms at `length` 3-60, 269.7-312.9 ms at 250.
5. **NIT** — the oracle figure is a band, 161-175 ms, with the module at
   2.8-3.5 ms, in both files.

204 tests still pass; the dictionary was regenerated after the docstring
edits and `tests/test_ml_companions.py` and `tests/test_readme_counts.py`
are green.

---

## Review round 4 — VERDICT: REVISE (the cap)

Same dispatch, fresh subagent, the last round the review loop allows
(round 1 + 3 re-runs). It re-ran every section, the tests, the CPU script
and the full suite; every structural figure reproduced. One MAJOR, three
MINOR, one NIT — and the MAJOR was, for the third round running, a defect
in the PREVIOUS round's fix.

Findings, verbatim:

> - severity: MAJOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:268-270 and docs/TsCrossMean20Measured.md:122-125 (A3b)
>   problem:  The round-3 MAJOR-1 fix replaced one bad universal with another. "Over every window A1, A2, A3 and A3b put to an oracle, float decided no comparison the wrong way. That is 13,329 windows against the window-by-window source, 4,443 against `math.fsum`, and 5,924 + 1,743 against the 60-digit oracle." A1 compares the module's double arithmetic against another implementation's double arithmetic; A2's `math.fsum` removes the summation error but `math.log` still returns a double and the comparison is still decided in a double. Neither can witness a comparison decided wrongly. Only A3/A3b can, and the project says so in four places. The fix inflates 7,667 exactly-checked windows into 25,439, and it is the copy a consumer reads that carries the inflated half.
>   fix:      Say what each check measured; name the 5,924 + 1,743 as the exact count and the other two as double-against-double.
>
> - severity: MINOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:353-357 and docs/TsCrossMean20Measured.md:701-705
>   problem:  Round 3's NIT fix turned one unreproducible oracle timing into an unreproducible band, "161 to 175 ms". My run prints 159.8, outside it. The band cites runs recorded in no table, and the script times the oracle with a single cold call — no warm-up, no best-of-three, unlike every other timing in the file.
>   fix:      Back the band with the record, or keep only the two-orders gap.
>
> - severity: MINOR
>   location: docs/TsCrossMean20Measured.md:688-699, repeated at pandas_ta/statistics/ts_cross_mean_20.py:121-129 and tests/test_ts_cross_mean_20.py:1243-1245
>   problem:  "Three runs of this section happened on this machine" is false by this folder's own record: round 3's finding quotes a fourth A/B. The derived count "two of the three complete A/Bs go one way and one the other" survives only because that run was dropped; my run is 101.3 shipped against 95.8 matrix at `length` 60, making the tally 2-2. The direction of the claim is right; the census is not.
>   fix:      Add the missing runs, correct the count, and replace it with "the winner at `length` 60 has gone both ways across the runs on record".
>
> - severity: MINOR
>   location: pandas_ta/statistics/ts_cross_mean_20.py:326-330 and docs/TsCrossMean20Measured.md:381-387 (D4)
>   problem:  "so ANY strictly monotone power map of the price leaves it alone" is an unqualified universal in the same docstring that insists nothing is bit-identical by construction because `log(8p)` is not `log(8) + log(p)`. `log(p**a)` is not exactly `a·log(p)` either. The evidence is three maps on one frame.
>   fix:      Grant the power map the same distinction the rescale gets: exact in the reals, measured in doubles.
>
> - severity: NIT
>   location: tests/test_ts_cross_mean_20.py:927-934
>   problem:  `test_where_the_floor_sits_on_its_own_axis` tabulates eight buckets and parametrizes six; the missing `[1024, 4096)` is the only sub-floor bucket reading 1.0000, and the one a reader is most likely to cite as evidence the floor is conservative.
>   fix:      Add `(1024, 4096, 1.0, 0.97)`.

### Fixes applied, all five

1. **MAJOR** — Gate A's closing paragraph, in both files, now credits the
   exact count to the 60-digit oracle alone (5,924 + 1,743) and states in
   as many words that A1's 13,329 and A2's 4,443 are double-against-double
   and cannot witness a wrongly decided comparison, with the five frames
   that have never seen an exact oracle named.
2. **MINOR 1** — the oracle timing is no longer a band to be checked
   against: the claim is the two-orders gap, the endpoints (159.8-174.8 ms
   against 2.8-3.5) are labelled observations, and the fact that they come
   from cold single calls the script does not warm up is stated.
3. **MINOR 2** — §Z's table now has five rows, including the two partial
   reviewer runs, and the derived tally is replaced in all three files by
   "the winner at `length` 60 has gone both ways across the runs on
   record" — which runs 1 and 3 (shipped) against 2 and 5 (matrix) now
   show directly.
4. **MINOR 3** — D4 and the docstring grant the power map exactly the
   caveat D0 grants the rescale: exact in the reals, a measurement in
   doubles, three maps on one frame.
5. **NIT** — the `[1024, 4096)` bucket is parametrized. 204 → **205**
   tests.

### Round 4 was the cap, and it ended on REVISE

The loop allows four rounds. All five findings were applied and verified
by re-running the tests (205 passed), the CPU script (205 passed with
AVX512/AVX2/FMA3 off), the dictionary generator and the full suite
(3 failed, 7,521 passed, 85 skipped — the three expected). **No fifth
review ran**, so these five fixes are the only ones in the session that
no reviewer has seen. Every one of them is a prose correction with its
run quoted beside it, and none touches the computation: the module's
output is bit-identical to what rounds 1-4 all measured.

If a later session wants one more pass, the thing to attack is the same
thing every round attacked — a sentence that outran its run — and the
standing record is that three consecutive generations of fixes each
introduced one.
