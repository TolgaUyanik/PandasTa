# Task log — J-KAUFMANSTOP-DIST (issue #124)

Lane: main thread. Gate: a fresh read-only Fletcher reviewer subagent per
round, dispatched with the files, the issue text and the original ask
verbatim. Reviewer verdicts are quoted, never summarised.

## Implementation summary (before round 1)

* `pandas_ta/trend/j_kaufmanstop_dist.py` — `PERIOD = 22`, `MULT = 2.0`,
  `MIN_BARS = PERIOD`, one column `J_KAUFMANSTOP_DIST_22_2.0`:
  `rng = high - low`; `avg = sma(rng, 22)`; `stop = low - 2*avg`;
  `dist = (close - stop)/close`, with three input finite guards, a
  close-is-positive-and-normal guard on the divisor and a final `isfinite`
  mask.
* `docs/measure_j_kaufmanstop_dist.py` — **21** sections (ENV, A1–A5,
  B1–B2, C1–C2, D1–D4, E, G1–G4, L, Z; §G5 was added after round 1, making
  22); `docs/measure_j_kaufmanstop_dist_cpu.py` — the reduced-CPU-dispatch
  runner.
* `tests/test_j_kaufmanstop_dist.py` — 306 tests.
* `docs/JKaufmanstopDistMeasured.md` — the receipt, Gate E pending.
* the five wiring touch points plus README / dictionary / contract /
  `CATEGORY_TOTAL` counts.

All figures in the module docstring, the test docstring and the receipt were
taken from a run of the measurement script, on both numpy dispatches, before
round 1 — which is what made round 1's findings about *prose* rather than
*arithmetic*.

---

## Round 1 — VERDICT: REVISE

Reviewer re-ran: `pytest tests/test_j_kaufmanstop_dist.py` (306 passed), the
same module under `NPY_DISABLE_CPU_FEATURES` (306 passed), every section of
both measurement scripts, `test_gate_e_ledger.py` (1 failed / 1,404 passed,
message naming only `j_kaufmanstop_dist`), the full suite (2 failed, 12,422
passed, 86 skipped), the prototype at `ind_screen_r2.py:127-129` and
`ind_screen.py:47`, and the four tracker CSVs behind §E.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/JKaufmanstopDistMeasured.md:24 (header, above §A1)
    problem:  "**One cell of one section moved** and it is marked where it sits (§D2)" is a
              specific count that the receipt's own §D2 paragraph (lines 387-392) contradicts and
              that my re-run contradicts. EIGHT of the 24 §D2 cells move between dispatches:
              walk ×10 3.669e-14→3.338e-14, trend ×3.7 4.109→4.145, trend ×0.1 3.978→3.330,
              range-bound ×10 4.400→3.592, ×3.7 3.307→3.328, ×0.1 3.456→3.782,
              ×1.0000001 3.122→3.111, jump ×3.7 3.456→3.775. One SECTION moved; eight cells did.
              In a repo whose stated dominant defect is "a claim written before it was measured",
              the headline count of the receipt disagreeing with its own table is the exact defect.
    fix:      Rewrite line 24 as "**Eight cells of one section moved** (§D2, listed there); the
              worst cell is the same 5.160e-14 under both dispatches." Nothing else needs touching
              — §D2's own list is already right, cell for cell.
  - severity: MAJOR
    location: tests/test_j_kaufmanstop_dist.py:984-985 (and docs/JKaufmanstopDistMeasured.md:518-522)
    problem:  "⚠ Pinned as bit-equality in BOTH directions, so a pandas upgrade that changed the
              absorption would fail here as well as there" — and §G2's "pins this bit-equality in
              both directions, so the same upgrade fails here too" — is reasoned, not run, and the
              module's own structure refutes it. If a future pandas propagated an infinite
              observation instead of NaN-ing the window, the guard-off branch computes
              rng=+inf → avg=+inf → stop=-inf → dist=+inf, and line 143's
              `dist.where(np.isfinite(dist))` turns that into NaN at exactly the bars the guard-on
              branch already blanks. Same NaN mask, nothing finite to compare: the test stays GREEN.
              §G3's own cells prove the mask does that conversion (99 inf without it, 0 with it).
              So the justification offered for keeping three measured-dead lines overstates what
              one of the two pinning tests can catch.
    fix:      Either delete the "as well as there"/"fails here too" clause from both places and say
              plainly that only `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`
              catches a change in the absorption — or measure it: add a §G section that execs the
              module source with `sma` rebound to a propagating mean
              (`lambda s, length=None: s.rolling(length, min_periods=length).apply(np.mean, raw=True)`,
              which returns inf rather than NaN), print whether ship and guard-off still read
              bit-equal, and quote that cell instead of the inference.
  - severity: MINOR
    location: pandas_ta/trend/j_kaufmanstop_dist.py:234-237 (docstring), docs/JKaufmanstopDistMeasured.md:74 and §D3:396-406
    problem:  "bit-identical on 1,479 of 1,479 bars of each of all nine test frames and at price
              levels 1e-6, 1e+6 and 1e+100" reads as nine frames × three levels = 27 cells. What
              was run is nine frames at a level of 100 (§D1) plus SIX cells on the `walk` frame
              alone (§D3; `test_gate_d_scale_at_extreme_price_levels` hard-codes `_frame("walk")`
              at tests/test_j_kaufmanstop_dist.py:875), plus `tied` at 1e-6 in §A4(c). §D3's table
              makes this impossible to see: its columns are level/fired/×8/×64/largest
              intermediate, with no frame column and no prose naming the frame.
    fix:      Name the frame in §D3 (a "frame" column reading `walk`, or "on the `walk` frame" in
              the lead-in), and reword the two prose claims to "on all nine frames at a level of
              100, and on `walk` at levels 1e-6 / 1e+6 / 1e+100 (plus `tied` at 1e-6, §A4(c))" —
              or parametrize `test_gate_d_scale_at_extreme_price_levels` over `NAMES` and print
              the 27 cells, then keep the sentence as written.
  - severity: MINOR
    location: docs/JKaufmanstopDistMeasured.md:18-24 (the re-printed-section list)
    problem:  "every section that carries a figure which could move with the numpy kernel was
              re-printed by `measure_j_kaufmanstop_dist_cpu.py` — §A1, §A3, §B1, §B2, §C1, §C2,
              §D1, §D2, §D3, §D4, §G2, §G3 and §L" is a universal claim with a false enumeration.
              §A4(b) carries 1.667e-02 … 5.606e-02 and Spearman 0.278975 … 0.533358, taken over
              `np.exp`/`np.cumsum` prices — figures that obviously "could move" — and §A2, §A5,
              §G1 and §G4 likewise are not in the list. I ran all five under the reduced dispatch:
              identical cell for cell, so the fix is bookkeeping, not re-measurement.
    fix:      Add §A2, §A4, §A5, §G1 and §G4 to the list (all verified identical under
              `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`), or drop the universal
              quantifier and write "the sections re-printed under the reduced dispatch were …".
  - severity: MINOR
    location: pandas_ta/trend/j_kaufmanstop_dist.py:256-259 (docstring)
    problem:  "One NaN, +inf or -inf high or low blanks exactly bars T .. T+21" is stated without
              a boundary. A bad high at bar 1,495 of a 1,500-bar frame blanks bars 1,495 … 1,499
              — five bars, not 22 — and a bad bar inside the warm-up blanks fewer still. §G4 and
              `test_a_bad_range_leg_empties_exactly_its_own_windows` only plant at 100, 700 and
              1,100, where T+21 is always inside the frame, so the measurement does not support
              the unqualified "exactly".
    fix:      Write "blanks exactly bars T … min(T+21, n-1) — measured as 22 bars at plant points
              100, 700 and 1,100 of a 1,500-bar frame (§G4)". Same edit for the test docstring's
              item 6 wording if you want the two to read alike.
  - severity: NIT
    location: pandas_ta/trend/j_kaufmanstop_dist.py:280-283 (docstring, §L paragraph)
    problem:  The paragraph is scoped to "the six varying frames", then quotes "|rho| 0.857 ..
              0.920 against 0.572 .. 0.620". Both outer endpoints come from a SEVENTH frame,
              `tied` (0.9203 / 0.5719). On the six the measured ranges are 0.8570 … 0.8839 and
              0.5741 … 0.6198. The receipt's §L table is correct; the prose attribution is not.
    fix:      Either quote the six-frame ranges (0.857 … 0.884 against 0.574 … 0.620) or say
              "over the six varying frames and `tied`".
  - severity: NIT
    location: pandas_ta/trend/j_kaufmanstop_dist.py:259-260 (docstring)
    problem:  "(§G4, nine plant points per leg)" — §G4 plants at THREE points (100, 700, 1,100)
              with three values each, i.e. nine CELLS per leg. The receipt says "9 cells"
              correctly; the module docstring inflates the plant points threefold.
    fix:      "(§G4, nine cells per leg: three plant points × three values)".
  - severity: NIT
    location: pandas_ta/trend/j_kaufmanstop_dist.py:172-173 and docs/JKaufmanstopDistMeasured.md:15-16
    problem:  "The underlying rule is Perry Kaufman's stop." is the one historical claim in two
              files that otherwise disclaim everything they cannot read — jesse is not installed,
              web access is off, and the issue says only "Kaufman's stop".
    fix:      Attribute it: "issue #124 names the rule Kaufman's stop; the attribution is the
              issue's, not checked here" — or delete the sentence.
SUMMARY: The arithmetic is not the problem; I could not break it. Every figure I re-ran came back
to the digit — §A1 through §G4, §L, both dispatches, 306 tests twice, 1,404+1 on the ledger, and the
full suite's 2/12,422/86 reproduced to the line — the prototype really is bit-equal, the ×8/×64
identity really is non-vacuous (+10 moves 1,479 of 1,479), the mutant strings each occur exactly
once and each mutant is live before it is caught, and MIN_BARS == PERIOD is run rather than
recalled at bar 21 by three independent spellers. So this fails on exactly the thing this repo says
kills ports: prose written past the run. Your headline tells the reader ONE cell moved between
dispatches while your own §D2, twenty lines later, lists EIGHT — you contradicted yourself in the
same document, and I found it by typing the command you printed. Then you told a reader that a
pandas upgrade which stopped absorbing infinities "would fail here as well as there", when your own
line 143 mask converts that infinity to a NaN at precisely the bars the guard already blanks, so
the test you cite stays green — a coverage claim invented to justify keeping three lines you had
just proved dead. Fix those two, tighten the three scope claims (levels on one frame not nine, the
re-print list, the T+21 boundary), and this is a clean port. Not yet.
```

### Fixes applied after round 1 (all eight)

| finding | what was done |
|---|---|
| MAJOR, the "one cell" headline | Recounted the two §D2 runs: **eight** of 24 cells move (walk ×10, trend ×3.7, trend ×0.1, range-bound ×10 / ×3.7 / ×0.1 / ×1.0000001, jump ×3.7). The header now says eight, says the worst cell is the same 5.160e-14 under both dispatches, and says the review caught it. |
| MAJOR, the "both directions" coverage claim | **Measured instead of re-worded.** New §G5: `sma` is rebound, by editing the shipped import line, to a mean that propagates an infinity, and each input guard is removed on top. Result: the column is still bit-equal in all six cells, because the final mask converts the propagated infinity at exactly the bars the guard blanks — the reviewer's refutation is correct. The claim is gone from the test docstring, from §G2 and from the module comment; `test_the_guards_stay_no_ops_even_if_the_rolling_mean_propagates` is the new pin. ⚠ **Both specifics this row originally carried were later refuted, and round 3 found the row still asserting them:** (1) the rebinding was written as `rolling(...).apply(np.mean, raw=True)`, which round 2's own fix then measured as NOT propagating — §G5's mean is a numpy window mean with no `rolling` in it; and (2) the row said all three places now name `..._into_nan` as the **only** test such an upgrade would fail, which was round 2's MAJOR — it is **two** tests. See the round-2 and round-3 tables. |
| MINOR, levels on one frame | Took the second option: `test_gate_d_scale_at_extreme_price_levels` is parametrized over all nine frames (**54 cells**) and §D3 prints all nine with a frame column. The prose claim is now literally what ran. Side finding, now in §D3: `trend` carries the largest intermediate (9.776e+101 at 1e100, not `walk`'s 1.006e+100), so the headroom figure moved to **1.839e+206×**. |
| MINOR, the re-print list | Ran §A2, §A4, §A5, §G1, §G4 and the new §G5 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` myself: identical cell for cell. The header now lists every section except §ENV and §Z and says so. |
| MINOR, the T+21 boundary | Added plant point **1,495** to §G4 and to `test_a_bad_range_leg_empties_exactly_its_own_windows` / `test_a_bad_close_empties_its_own_bar_and_moves_no_other`, with the expectation computed as `min(T+22, n)`. Measured: **5** bars blanked at 1,495, 22 in the middle of the frame. The claim is now `T … min(T+21, n-1)` in the module docstring, the test header and §G4. |
| NIT, §L ranges | Split into the six varying frames (0.857 … 0.884 vs the wick, 0.574 … 0.620 vs the range term) and `tied` (0.920 vs 0.572), in both the module docstring and §L. |
| NIT, "nine plant points" | Now "12 cells per leg: four plant points × three values", after the 1,495 addition. |
| NIT, the Kaufman attribution | "Issue #124 names the rule Kaufman's stop; that attribution is the issue's and is not checked here" — ⚠ applied to the **module docstring only**. This row originally claimed the receipt too; round 2 caught that the receipt's header still read "The underlying rule is Perry Kaufman's stop." bare, and it was fixed then. The row is corrected rather than left standing, because a review log recording a fix that did not land is worse than the NIT. |

Suites after the fixes: `tests/test_j_kaufmanstop_dist.py` **369 passed**
(306 → 369: +54 extreme-level cells net of the 6 replaced, +6 §G5 cells,
+9 plant-point cells), the same **369** under the reduced dispatch; with
`tests/test_gate_e_ledger.py`, **1,467 passed, 1 failed** (the owed row);
full suite **2 failed, 12,485 passed, 86 skipped**.

---

## Round 2 — VERDICT: REVISE

A fresh reviewer, same dispatch, told what round 1 found and what was
changed, and asked to attack the fixes hardest.

Reviewer re-ran: `pytest tests/test_j_kaufmanstop_dist.py` (369 passed), the
same module under `NPY_DISABLE_CPU_FEATURES` (369 passed), every section of
both scripts, port + ledger (1,467 passed / 1 failed naming only
`j_kaufmanstop_dist`), the full suite (2 failed, 12,485 passed, 86 skipped),
the prototype, and the four tracker CSVs.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/JKaufmanstopDistMeasured.md:664 (also :110-111 of tests, tests:1010-1011, docs/measure_j_kaufmanstop_dist.py:1022)
    problem:  You were told your coverage claim was reasoned rather than run. You ran it — and then
              wrote a NEW unrun claim on top of the measurement: "the only test in this port that
              would fail on such a pandas upgrade is
              `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`". It is false, and
              your own §G3 contains the counterexample. `test_route_1_never_reaches_the_output`
              (tests:1136-1146) asserts `int(np.isinf(bare).sum()) == 0` on the route-1 frame
              (+DBL_MAX high, -DBL_MAX low), where `high - low` overflows to +inf from two FINITE
              legs. That zero exists ONLY because today's rolling mean NaNs the window: with a mean
              that propagates, avg = +inf -> stop = -inf -> dist = +inf, and with the final mask
              removed the bare column reads 99 infinities of 120 — the same 99 as routes 2 and 3.
              So a propagating-mean pandas fails TWO tests, flips §G3's route-1 row from 0 to 99,
              and turns your bold "**Two of the three** reach the output without the final mask"
              (receipt:577) into three of three. The word "only" is stated in four files and was
              measured in none of them.
    fix:      Run §G3's three routes through §G5's rebinding — the machinery is already there: one
              more table in §G5 with `_overflow_routes()` executed against
              `_mutant(*propagating)` and against `propagating + FINITE_GUARD_OFF`. Print route 1's
              "inf w/o the mask" (expect 99). Then replace the sentence in all four places with
              what ran: "two tests would fail on such an upgrade —
              `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan` and
              `test_route_1_never_reaches_the_output`, whose zero is the same absorption — and
              §G3's route-1 row would move from 0 to 99."
  - severity: MINOR
    location: docs/measure_j_kaufmanstop_dist.py:974-978 and docs/JKaufmanstopDistMeasured.md:636-639
    problem:  §G5's premise — that `rolling(length, min_periods=length).apply(np.mean, raw=True)`
              PROPAGATES an infinity — is the whole load-bearing claim of the section, and not one
              printed cell establishes it. Work the table: with the guard ON, `hi` is NaN'd, the
              window is NaN, the mean is NaN, 22 bars blank, fired 1457. With the guard OFF and a
              PROPAGATING mean, the inf is masked at those same 22 bars, fired 1457. With the guard
              OFF and an ABSORBING mean, the window NaNs — fired 1457 again. All six cells read
              identically in both worlds, so the printed evidence cannot distinguish the world
              §G5's own heading asks about. The section that exists to replace an inference rests
              on an inference. (It happens to be true — `np.mean` over a window holding +inf is
              +inf — but "happens to be true" is the standard this repo says kills ports.)
    fix:      One cell, in §G5's first table: print `_mutant(*propagating)`'s `sma(rng, 22)` at the
              planted bar with the guard removed, or the `inf w/o the final mask` count under the
              rebinding (expect inf, and 99 on the route-1 frame). That single number both proves
              the premise and supplies the MAJOR above its counterexample.
  - severity: MINOR
    location: pandas_ta/trend/j_kaufmanstop_dist.py:266-268 (also receipt:614-619, tests:934-955)
    problem:  Round 1 handed you BOTH edges of the T+21 boundary — "a bad high at bar 1,495 blanks
              five bars, and a bad bar inside the warm-up blanks fewer still". You added 1,495 and
              left the left edge exactly where it was. "blanks exactly bars `T .. min(T+21, n-1)`"
              is still false below the warm-up, by your own definition of blanked
              (`base.notna() & col.isna()`): a bad high at bar 5 loses bars 21 .. 26 — SIX bars,
              not the twenty-two your formula predicts over 5 .. 26, because bars 5 .. 20 were
              never fired. §G4 plants at 100, 700, 1,100 and 1,495 only, so nothing measured
              supports the unqualified "exactly" on the left any more than it did on the right.
    fix:      Add plant point 5 (or 15) to §G4's `for j in (...)` tuple and to the `j` parametrize
              lists of both bad-price tests, with `want = list(range(max(j, WARMUP),
              min(j + PERIOD, N)))`, and write the rule as
              `max(T, 21) .. min(T+21, n-1)` — measured 6 bars at 5, 22 at 100/700/1,100, 5 at
              1,495 — in the module docstring, the test header item 6 and §G4.
  - severity: MINOR
    location: docs/JKaufmanstopDistMeasured.md:19-26
    problem:  The fix for round 1's false enumeration is itself a false enumeration. "§A1, §A2,
              §A3, §A4, §A5, §B1, §B2, §C1, §C2, §D1, §D2, §D3, §D4, §G1, §G2, §G3, §G4, §G5 and
              §L, i.e. all of them except §ENV (versions) and §Z (wall-clock)" names nineteen of
              the script's TWENTY-TWO sections and claims the remainder is two. §E is the third,
              it is in `SECTIONS`, and it prints figures (0.8776182137043917, 396980, 0.8611).
              Same defect, one section smaller.
    fix:      Write "all of them except §ENV (versions), §E (the screen's quoted figures, named
              exception 3) and §Z (wall-clock)" — or add §E to the list, since it reprints
              identically under the reduced dispatch.
  - severity: MINOR
    location: docs/JKaufmanstopDistMeasured.md:15 and docs/reviews/auto-2026-11-19-j-kaufmanstop-dist/01-j-kaufmanstop-dist.md:160
    problem:  Round 1's NIT 8 named two locations for "The underlying rule is Perry Kaufman's
              stop." — the module docstring and the receipt's header. Your own fix table says it
              was corrected "in the module docstring and the receipt's header". The module was
              fixed. The receipt was NOT: line 15 still reads "The underlying rule is Perry
              Kaufman's stop." bare, in a document whose next paragraph disclaims everything it
              cannot read. So a review log in this repo now records a fix that was not applied —
              which is worse than the NIT, because the next session will trust the table.
    fix:      Copy the module's wording into the receipt: "Issue #124 names the rule Kaufman's
              stop; that attribution is the issue's and is not checked here." Then make the log row
              say which files it actually touched.
  - severity: NIT
    location: docs/JKaufmanstopDistMeasured.md:58 (against :26 and :771-779)
    problem:  "Everything else in this receipt is a cell from a run" is false for at least two
              figures outside the five named exceptions: the header's own "**Eight** of §D2's 24
              cells moved" (a count no section prints — it is a hand diff of two §D2 runs; correct,
              I recounted it off both dispatches, but not run output), and §F's wiring counts
              (`CATEGORY_TOTAL` 358 -> 359, README 358 -> 359 / 366 -> 367 / trend (65)), which
              exception 2 covers only for the contract's 703 -> 704.
    fix:      Either make the cpu script print the §D2 diff, or extend the exception block: a sixth
              item for the cross-dispatch cell count and a clause in item 2 covering the README and
              `CATEGORY_TOTAL` numbers (checked by `tests/test_readme_counts.py` and
              `tests/test_altport2_ports.py`, not by this script).
  - severity: NIT
    location: pandas_ta/trend/j_kaufmanstop_dist.py:287-290
    problem:  The §L paragraph reads as a descending ranking — "0.5506, then `j_chandelier_dist` at
              0.1436, a retyped `Stop_2ATR_pct` at 0.1366 and `natr`'s `NATR_14` at 0.1092" — and
              silently drops `true_range/close (retyped)` at 0.1096, which §L's own table ranks
              ABOVE `natr`. A reader counting positions puts `natr` fourth; it is fifth of seven.
    fix:      Insert it ("...0.1366, a retyped `true_range/close` at 0.1096 and `natr`'s `NATR_14`
              at 0.1092") or say "four of the seven rows of §L" so the list stops reading as the
              whole ranking.
  - severity: NIT
    location: docs/reviews/auto-2026-11-19-j-kaufmanstop-dist/01-j-kaufmanstop-dist.md:15-16
    problem:  "`docs/measure_j_kaufmanstop_dist.py` — 20 sections (ENV, A1–A5, B1–B2, C1–C2,
              D1–D4, E, G1–G4, L, Z)" — count your own parenthesis: 1+5+2+2+4+1+4+1+1 = 21. With
              §G5 the script now has 22. A specific count that disagrees with the list beside it,
              in the log that records a round whose MAJOR was a specific count disagreeing with the
              table beside it.
    fix:      "21 sections" in the before-state line, and add a note that §G5 makes 22 after round
              1.
  - severity: NIT
    location: docs/JKaufmanstopDistMeasured.md:748-752
    problem:  "**369 passed** ..., two of which read documents rather than the column" — three do.
              `test_the_docstrings_first_paragraph_survives_the_dictionary_cut` lifts `desc` out of
              `docs/gen_indicator_dictionary.py` with `ast` and asserts on the docstring, not on a
              single bar of the column.
    fix:      "three of which read documents rather than the column" and name the third, or scope
              the clause: "two of which read documents this port must keep in step (the receipt and
              the ledger)".
SUMMARY: The arithmetic is still untouchable and I stopped trying — every cell of §A1 through §G5,
§L and §Z came back to the digit on both dispatches, the eight moved §D2 cells are exactly the eight
you now list with 5.160e-14 worst under both, §D3's 54 cells and the 9.776e+101 / 1.839e+206 headroom
are real, the 1,495 plant point reads 5, 369 twice, 1,467+1 with the owed row naming nothing else,
and 2/12,485/86 to the line. So you fixed seven of eight findings properly and then did the one thing
this repo keeps dying of: you repaired an unrun coverage claim by writing a BIGGER unrun coverage
claim. "The only test that would fail on such a pandas upgrade" — in four files — and
`test_route_1_never_reaches_the_output`, sitting twenty lines from the sentence, asserts a zero that
exists purely because of the absorption you are hypothesising away. You had the counterexample
printed in your own §G3 and walked past it. Worse, §G5 — the section built to stop inferring —
prints six cells that read identically whether the rebound mean propagates or absorbs, so it never
shows the one fact its heading depends on. And you were handed the T+21 boundary with BOTH ends
named; you fixed the right one and shipped the left. Measure the three routes under the propagating
mean, name the second test that breaks, plant a bad bar inside the warm-up, and put the Kaufman
attribution in the receipt you claimed you had already put it in. Then it is clean. Not yet.
```

### Fixes applied after round 2 (all nine) — and one finding partly REFUTED by the fix

| finding | what was done |
|---|---|
| MINOR, §G5's unproven premise | **The fix refuted the reviewer's own mechanism, and the measurement is now in §G5.** Printing the mean at the planted bar showed `rolling(...).apply(np.mean, raw=True)` reading **NaN**, not inf: pandas converts an infinity to a NaN in `_prep_values`, *before* the window function runs, so **no `rolling` aggregation can propagate one** — `sma`, `apply(np.mean)` and `rolling(...).max()` all read NaN with 0 infinite bars, while a numpy window mean with no `rolling` reads **inf** with 22. `PROPAGATING_MEAN` was rebuilt as that numpy window mean, §G5 prints the four means side by side, and `test_no_rolling_aggregation_can_propagate_an_infinity` pins it. This also sharpens §G3: the absorption is a property of pandas' window **preparation**, not of the mean. |
| MAJOR, "the only test" | **Confirmed once the propagating mean was real, and measured.** Under the numpy window mean, route 1 ships **99 of 120** infinite readings without the final mask — exactly the reviewer's prediction — so `test_route_1_never_reaches_the_output` would fail too and §G3's route-1 row would move from 0 to 99, making it three of three. ⚠ Under the reviewer's proposed `rolling` version it still shipped **0**, so the finding was right about the *conclusion* and wrong about the *vehicle*; both halves are recorded in §G5 rather than the convenient one. The "only" sentence is gone from all four files, replaced by the two named tests, and `test_route_1s_zero_is_the_absorption_and_would_move_without_it` pins the 99. §G3's route-1 row now says it is the one contingent figure in the section. |
| MINOR, the T+21 left edge | Plant point **5** added to §G4 and to both bad-price tests, with `want = range(max(j, WARMUP), min(j + PERIOD, N))` computed rather than typed. Measured: a bad high or low at bar 5 blanks **6** bars (21 … 26), a bad close blanks **0**. The rule reads `max(T, 21) … min(T+21, n-1)` in the module docstring, the test header and §G4. |
| MINOR, the re-print enumeration | Now "all 22 of the script's sections except §ENV, §E and §Z", with §E pointed at exception 3. |
| MINOR, the Kaufman attribution in the receipt | Applied to the receipt's header, and the round-1 fix row above corrected to say it had only reached the module. |
| NIT, "everything else is a cell from a run" | Exceptions extended from five to **seven**: item 2 widened to cover the README / `CATEGORY_TOTAL` counts, item 6 for the cross-dispatch cell count, item 7 for the "identical cell for cell" comparisons. |
| NIT, §L's dropped row | `true_range/close` at 0.1096 inserted, and the list labelled "five of §L's seven rows, in order". |
| NIT, the log's section count | "21 sections … §G5 was added after round 1, making 22". |
| NIT, "two of which read documents" | **Three**, with the third named. |

Suites after the round-2 fixes: `tests/test_j_kaufmanstop_dist.py` **380
passed** (369 → 380: +9 bar-5 cells, +1 premise test, +1 route-1
contingency test), the same **380** under the reduced dispatch; §G4 and §G5
re-printed under the reduced dispatch, identical cell for cell; with
`tests/test_gate_e_ledger.py`, **1,478 passed, 1 failed** (the owed row,
naming only `j_kaufmanstop_dist`); full suite **2 failed, 12,496 passed, 86
skipped**.

---

## Round 3 — VERDICT: REVISE

A fresh reviewer, same dispatch, told what rounds 1 and 2 found and asked to
attack the round-2 fixes hardest. It re-ran every section on both
dispatches and reproduced 380, 1,478/1 and 2/12,496/86 to the line.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: tests/test_j_kaufmanstop_dist.py:1151-1153 (docstring of test_the_guards_stay_no_ops_even_if_the_rolling_mean_propagates)
    problem:  Round 2 told you your propagating mean did not propagate. You rebuilt
              PROPAGATING_MEAN as a numpy window mean (line 1053) and then left the OLD, REFUTED
              vehicle written into the one test that depends on it: "this test makes pandas stop,
              by rebinding `sma` to `rolling(...).apply(np.mean, raw=True)`, which returns an
              infinity rather than a NaN". Both halves are false. The test body calls
              `_propagating()`, which is the numpy window mean with no `rolling` in it, and
              `test_no_rolling_aggregation_can_propagate_an_infinity` — 60 lines above, which I ran
              — asserts that `apply(np.mean, raw=True)` reads NaN at the planted bar with 0
              infinite bars. The same docstring then contradicts itself at lines 1164-1167: "the
              `rolling`-based version round 2 of the review proposed does not [propagate], so
              without that test these six cells would prove nothing." So a reader is told, in one
              docstring, that the rebinding is the thing the file elsewhere proves cannot be the
              rebinding. This is round 2's MAJOR reborn: a fix that left a new false statement
              exactly where the fix landed, and the only one of the four co-located files
              (module comment, receipt §G5, measurement script) that still carries it.
    fix:      Replace lines 1151-1153 with what runs: "so this test makes pandas stop, by rebinding
              `sma` to `PROPAGATING_MEAN` -- a numpy window mean with no `rolling` in it, which
              reads inf at the planted bar where every `rolling` aggregation reads NaN
              (`test_no_rolling_aggregation_can_propagate_an_infinity`) -- and removes the guard on
              top of that." Then delete the now-redundant "⚠ And the rebinding really does
              propagate" sentence or keep it as the cross-reference it is.
  - severity: MAJOR
    location: docs/JKaufmanstopDistMeasured.md:71-73 (exception item 7)
    problem:  Round 2's NIT asked you to extend the exception block; the extension invented a count
              and got it wrong by eight. Item 7 licenses "the three 'identical cell for cell under
              the reduced CPU dispatch' lines" as hand comparisons rather than run output. I
              grepped the file: that exact sentence appears ELEVEN times — lines 171, 228, 328,
              348, 367, 442, 552, 597, 708, 755 — plus the §D1 variant "Identical under the reduced
              CPU dispatch" at line 394. Because line 75 then says "Everything else in this receipt
              is a cell from a run", the eight-to-nine unnamed occurrences are now claimed as run
              output when every one of them is two printed tables read against each other, which is
              precisely what item 7 exists to disclaim. This is the round-1 MAJOR's defect — a
              headline count contradicted by the document's own body — reintroduced by a round-2
              fix, in the paragraph whose entire job is counting honestly, and under a sentence
              that boasts "seven numbered items, and the count is the number of items".
    fix:      Make item 7 countless or correct: "and every 'identical cell for cell under the
              reduced CPU dispatch' line (§A1, §A3, §B1, §B2, §C1, §D3, §G2, §G3, §G4, §G5, §L, and
              §D1's 'Identical under the reduced CPU dispatch') is the same kind of comparison --
              two printed tables read against each other, not a diff the script computes." If you
              want a number, count the lines first and state eleven plus the §D1 variant.
  - severity: MINOR
    location: pandas_ta/trend/j_kaufmanstop_dist.py:62-63, docs/JKaufmanstopDistMeasured.md:672-687, tests/test_j_kaufmanstop_dist.py:1047-1049 and 1075-1076
    problem:  The replacement mechanism is named from pandas' internals and then credited to a
              print that does not contain it. The module comment says "no `rolling` aggregation can
              propagate, because pandas sanitises an infinity in `_prep_values` before the window
              sees it, **which §G5 also prints**". I ran §G5 on both dispatches: it prints four
              means (`sma`, `apply(np.mean, raw=True)`, `rolling().max()`, numpy window mean) and
              their values at bar 700. It prints nothing from, about, or naming `_prep_values`; no
              test reads pandas' source; and pandas lives outside the worktree this session may
              read. The universal that rests on it — "No `rolling` aggregation can be that mean",
              and the test NAME `test_no_rolling_aggregation_can_propagate_an_infinity` — is
              generalised from three sampled aggregations. The conclusion is almost certainly
              right; the attribution is a claim written past the run, which is the defect this
              repo's CLAUDE.md puts first.
    fix:      Scope it to the three cells that ran and stop crediting the print: "the three
              `rolling` aggregations measured -- `sma`, `apply(np.mean, raw=True)` and
              `rolling().max()` -- all read NaN at the planted bar while a numpy window mean reads
              inf, which places the conversion before the window function rather than in the mean;
              pandas' own `_prep_values` is where its documentation puts that conversion, and that
              source is not readable from this worktree, so §G5 prints the behaviour and not the
              mechanism." Apply the same scoping to the test docstring, and either rename the test
              `test_the_rolling_aggregations_measured_cannot_propagate_an_infinity` or state the
              three-sample scope in its first line.
  - severity: MINOR
    location: docs/reviews/auto-2026-11-19-j-kaufmanstop-dist/01-j-kaufmanstop-dist.md:155 (round-1 fix table, the "both directions" row)
    problem:  The round-1 fix row still asserts, as fact, that §G5 rebinds `sma` to
              "`rolling(...).apply(np.mean, raw=True)`, which propagates an infinity", and that
              "all three places now say that **only**
              `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan` would fail on
              such an upgrade". Round 2 refuted both — the first in the round-2 table at line 323,
              the second as round 2's MAJOR — yet this row carries no annotation, while the row
              immediately below it (line 161, the Kaufman attribution) does exactly that: "⚠
              applied to the module docstring only. This row originally claimed the receipt too;
              round 2 caught that ... The row is corrected rather than left standing, because a
              review log recording a fix that did not land is worse than the NIT." You applied your
              own standard to one stale row and not the one next to it, so the log now hands a
              later session a false pandas mechanism in its own history.
    fix:      Append to the row, in the style of line 161: "⚠ Both halves of this row were later
              refuted: round 2 measured that `rolling(...).apply(np.mean, raw=True)` does NOT
              propagate (so §G5's mean was rebuilt as a numpy window mean), and that TWO tests
              would fail on such an upgrade, not only `..._into_nan`. See the round-2 table."
  - severity: NIT
    location: docs/measure_j_kaufmanstop_dist.py:419-429 (_largest_intermediate), quoted as §D3 and in the module docstring at :248-249
    problem:  "the largest intermediate **anywhere in the chain**" and "worst intermediate
              9.776e+101" are computed over `[high, low, close, rng, avg, stop]` — the chain also
              computes `MULT * avg` and `dist`, neither of which is in `parts`. At the levels
              measured the omission cannot change the answer (2*avg is sub-percent of the price on
              every frame, `dist` is ~0.01), so the 1.839e+206 headroom stands; but "anywhere" is a
              universal over a set that excludes two computed values, in a receipt that elsewhere
              refuses to extrapolate a single cell.
    fix:      Add `MULT * avg` and `dist` to `parts` and re-print §D3 (the figures will not move),
              or write "the largest of `high`, `low`, `close`, `rng`, `avg` and `stop`" in §D3's
              column header and in the docstring.
  - severity: NIT
    location: docs/JKaufmanstopDistMeasured.md:62-64 (exception item 5)
    problem:  Item 5 names "the asserted bounds quoted next to several measurements (1e-12 and 1e-9
              at §A1, 1e-12 at §A2, 1e-6 at §B1, 1e-4 at §B2, 1e-9 at §D2, the `> 50` infinite
              readings at §G3 and §G5)". Three of those seven locations are real: §A1 (line 183),
              §B1 (line 331), §D2 (line 412). The other four are phantom — §A2, §B2, §G3 and §G5
              quote no bound anywhere in this receipt, as a grep for `1e-12|1e-4|> 50` shows. An
              exception block that licenses figures the document does not contain is the same
              bookkeeping failure as one that misses figures it does, and this one has survived
              three rounds.
    fix:      Either cut §A2, §B2, §G3 and §G5 from the parenthesis, or quote the bound in those
              four sections the way §A1 and §D2 do ("the test asserts 1e-12 absolute", "the test
              asserts more than 50 infinite readings"), so the list and the document agree.
SUMMARY: The arithmetic is beyond my reach and I stopped swinging at it two hours ago — every cell of
§ENV through §G5, §L and §Z came back to the digit on both dispatches, the eight moved §D2 cells are
exactly the eight you list and I recounted them off both tables myself, §D3's 54 cells and
9.776e+101 / 1.839e+206 are real, §G4's bar-5 row reads 6 and bar-1,495 reads 5, §G5's 99-of-120 under
the numpy window mean is there, the prototype at ind_screen_r2.py:127-129 against ind_screen.py:47 is
bit-equal, all four tracker CSVs match §E to the last digit of 0.8776182137043917, 380 passed twice,
1,478+1 with the owed row naming nothing else, and 2/12,496/86 to the line. So you fixed the
measurements and then did it AGAIN with the words. You rebuilt the propagating mean because round 2
proved `apply(np.mean, raw=True)` cannot propagate — and left the docstring of the very test that
uses the new mean telling a reader it rebinds `sma` to `apply(np.mean, raw=True)`, "which returns an
infinity", twelve lines above the sentence where the same docstring says that version does not
propagate. That is not a stale number; that is the file arguing with itself about the one fact round 2
made you measure. Then you extended the exception block round 2 asked for and wrote "the three
'identical cell for cell' lines" over a document containing eleven of them, so your own closing
sentence — "Everything else in this receipt is a cell from a run" — now swallows eight hand
comparisons, which is round 1's one-versus-eight headline wearing a different hat. Three rounds, three
false counts or mechanisms born inside the fix. Correct the docstring, count the lines, stop crediting
§G5 with printing `_prep_values` it never printed, annotate the log row you left standing, and this
port is done. Not yet.
```

### Fixes applied after round 3 (all six)

| finding | what was done |
|---|---|
| MAJOR, the stale vehicle in the test docstring | Rewritten to `PROPAGATING_MEAN` — "a numpy window mean with no `rolling` in it, which reads **inf** at a planted bar where every `rolling` aggregation measured reads NaN" — with a ⚠ line recording that an earlier draft named the refuted `rolling` version here, and the redundant sentence twelve lines below turned into the cross-reference it was. |
| MAJOR, item 7's invented count | Counted: **twelve** statements — eleven in that wording (§A1, §A3, §B1, §B2, §C1, §D3, §G2, §G3, §G4, §G5, §L) and one shorter at §D1. Item 7 now covers *every* such statement and enumerates the sections. ⚠ The first replacement count written here was **eleven**, from a single-line grep that missed §G4's wrapped sentence; it was corrected with a multiline count before this round closed, and item 7 says why. ⚠ This row originally added that the round-3 reviewer's own figure had the same off-by-one; round 4 checked and it did **not** — its count of eleven in that wording was right, only its line-number list was one short. |
| MINOR, the `_prep_values` attribution | Scoped to what ran, in all four places (module comment, receipt §G5, the test docstring, the script's print): the three `rolling` aggregations measured read NaN where the numpy mean reads inf, which places the conversion before the aggregation; pandas' source is not readable here, so the mechanism is not claimed and §G5 is credited with the behaviour only. The test keeps its name and states the three-sample scope in its first lines. The receipt adds, as a verifiable in-repo pointer rather than a derivation, that `docs/JGatorMeasured.md` and `pandas_ta/momentum/j_gator.py` already name `_prep_values` for the `ewm` path. |
| MINOR, the un-annotated round-1 log row | Annotated in the style of the Kaufman row: both specifics it carried were later refuted, with pointers to the round-2 and round-3 tables. |
| NIT, `_largest_intermediate`'s incomplete set | `MULT * avg` and `dist` added, §D3 re-printed on both dispatches. The 1e+06 and 1e+100 columns did not move and the **1.839e+206** headroom stands, exactly as the reviewer predicted — and the 1e-06 column DID move, from ~1e-06 to ~1.4e-02, because at that level the largest value in the chain is the dimensionless output. §D3, the script and the module docstring now say "largest value the chain computes" over all eight series, and §D3 states the 1e-06 reading and the `flat` exception. |
| NIT, item 5's phantom bounds | Cut to the three places the receipt actually quotes a bound (§A1's 1e-12 / 1e-9, §B1's 1e-6, §D2's 1e-9), with a note that the item had named four sections carrying none. |

Suites after the round-3 fixes: `tests/test_j_kaufmanstop_dist.py` **380
passed**, the same **380** under the reduced dispatch (no test was added —
all six fixes were prose or the measurement set); §D3 re-printed on both
dispatches; the whole measurement script re-run end to end; full suite
**2 failed, 12,496 passed, 86 skipped**.

---

## Round 4 — VERDICT: REVISE (the loop's last round)

A fresh reviewer, same dispatch, told what rounds 1–3 found and asked to
attack the round-3 fixes hardest. It re-ran everything and reproduced 380 on
both dispatches, 1,478/1, and 2/12,496/86.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/JKaufmanstopDistMeasured.md:902-907 (What a later session should know, item 5) and docs/measure_j_kaufmanstop_dist.py:991-997
    problem:  Round 3's MINOR was "stop naming pandas' internal as the mechanism"; your own fix table
              says it was scoped "in all four places". It was scoped in four places and left standing
              in two others — and one of them is the receipt. Line 904: "What the column *does* lean
              on is pandas converting an infinity to a NaN in `_prep_values`". Line 715 of the SAME
              document: "this receipt does not re-derive it and does not lean on the name", with the
              in-repo pointer scoped to the `ewm` path. So the receipt tells a later session it does
              not lean on `_prep_values` and then tells it that `_prep_values` is what the column
              leans on, for the `rolling` path nothing here measured. The script repeats it as bare
              fact at :994 — "pandas converts an infinity to a NaN in `_prep_values`, BEFORE the
              window sees it, so no `rolling` aggregation of any kind can carry one" — four lines
              above its own print, which I ran, that says "What is measured is the BEHAVIOUR of three
              aggregations, not pandas' source, which this worktree cannot read". Pandas lives outside
              the worktree; no test and no section reads it. Round 4, fourth fix that leaves a new
              false statement, in the paragraph the fix was supposed to clean.
    fix:      Rewrite receipt item 5's last sentence to what ran: "What the column *does* lean on is
              pandas turning an infinite observation into a NaN before a `rolling` aggregation sees
              it — measured on three aggregations in §G5, mechanism not claimed: two tests would fail
              if that went (`test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan` and
              `test_route_1_never_reaches_the_output`), and neither depends on the guards." Replace
              the script comment at :991-997 with the same scoping ("the three `rolling`
              aggregations the premise table prints all read NaN where a numpy window mean reads inf,
              so `rolling` is left out"), and drop "of any kind".
  - severity: MAJOR
    location: docs/JKaufmanstopDistMeasured.md:822-825 (§L closing ⚠) and :896-898 (What a later session should know, item 4)
    problem:  "⚠ One consequence worth stating: `lean_avgrange_14` is an **unported candidate** of the
              same round at 0.8646 against this column … If it is ported later, that pair needs
              measuring against this one", and item 4: "**`lean_avgrange_14` (issue not yet ported)
              pairs at 0.8646** … Measure that pair before shipping both." I read
              `docs/issues/screen/candidates_r2.csv` — the file §E quotes four of its own figures out
              of. Line 6 of it: `lean_avgrange_14 … 0.9489221914865852,natr,compute_all,397692.0,
              0.9458059808195928,STRUCK,0.9433,natr:NATR_14,FORKDUP,…,dropped: Gate E STRUCK` — with
              an empty issue column, and `docs/issues/screen/skipped_r7.py:42` repeats "round 2
              lean_avgrange_14 (SMA(H-L)/close) was struck vs natr at 0.9489". There is no issue, it
              will not be ported, and "before shipping both" is advice about an event the tracker
              already closed. The omission is not neutral either: the one candidate this receipt
              tells a later session to go measure is the nearest member of the same family, STRUCK at
              0.9489 against `natr` — the very comparator this column reads 0.8776 against — which is
              the most load-bearing piece of context a DISCLOSE_GAP port could carry, and it is
              nowhere in the receipt.
    fix:      Replace both passages with the CSV's own record: "`lean_avgrange_14` — the screen's own
              `SMA(H - L, 14)/close` candidate, which paired at 0.8646 with this one
              (`cand_pairs_r2.csv`) — was itself measured at max \|ρ\| 0.9489 vs `natr` and **dropped
              STRUCK** (`candidates_r2.csv`, status `dropped: Gate E STRUCK`, catalog FORKDUP), so
              there is no port to measure against. ⚠ Read it as a risk signal instead: the nearest
              range-family candidate of the same round was struck against the same comparator this
              column reads 0.8776 against." Add the same sentence to §E's three-things list.
  - severity: MINOR
    location: pandas_ta/trend/j_kaufmanstop_dist.py:71-72 and docs/JKaufmanstopDistMeasured.md:585-586
    problem:  "removing them would not change a measured cell" / "removing these three lines would not
              change a measured cell in this receipt" is a universal over the whole receipt, run on
              part of it. The three input finite guards were removed and compared in 42 cells: §G1's
              27 (three guards × nine clean frames), §G2's 9 (bar 700) and §G5's 6. §G4 is 45
              measured cells of exactly the input these guards exist for — NaN/+inf/−inf in high,
              low or close at bars 5, 100, 700, 1,100 and 1,495 — and only the bar-700 column of it
              has ever been run with a guard off. The conclusion is almost certainly right; the
              quantifier is one plant point wide and claims four more.
    fix:      Either scope it ("would not change any of the 42 guard-off cells measured here — §G1's
              27, §G2's 9, §G5's 6; §G4's other four plant points were not re-run with a guard
              removed"), or add the guard-off column to §G4 and to
              `test_a_bad_range_leg_empties_exactly_its_own_windows` and keep the sentence.
  - severity: MINOR
    location: tests/test_j_kaufmanstop_dist.py:147-150
    problem:  The exception paragraph names the asserted bounds in this docstring as "(1e-12 and 1e-9
              in item 1, 1e-6 in item 4)" and then says the measured figure beside each is a run —
              presenting that parenthesis as the complete set. Item 5 quotes a fourth: "within
              **5.160e-14** relative, so the bound is asserted at 1e-9" (line 74-76). That is the
              same bookkeeping defect round 3 found in receipt item 5 — a bounds list that disagrees
              with its own document — with the sign flipped from phantom to missing, and it survives
              in the file whose closing paragraph claims every other number is printed by the script.
    fix:      "(1e-12 and 1e-9 in item 1, 1e-6 in item 4, 1e-9 in item 5)".
  - severity: MINOR
    location: pandas_ta/trend/j_kaufmanstop_dist.py:237, tests/test_j_kaufmanstop_dist.py:60, docs/JKaufmanstopDistMeasured.md:336
    problem:  "asserted at 1e-6, which is still eight orders above the 5.160e-14 an inexact rescale
              costs", in three files. 1e-6 / 5.160e-14 = 1.94e+07. Eight orders above 5.160e-14 is
              5.16e-06, which is ABOVE the bound you assert. The gap is seven orders, not eight — a
              specific number, wrong in the same direction in all three places, in a port whose
              receipt counts the number of items in its own exception list.
    fix:      "more than seven orders above the 5.160e-14" in all three, or quote the ratio
              ("1.9e+07×").
  - severity: NIT
    location: docs/measure_j_kaufmanstop_dist.py:419-437 (_largest_intermediate), quoted at docs/JKaufmanstopDistMeasured.md:449-451
    problem:  Round 3's NIT was that "every value the chain computes" quantified over a set missing
              `MULT * avg` and `dist`. Both were added — and the set still omits the division's
              numerator, `px - stop`, and the guarded divisor `px`, both of which the chain computes
              on the way to `dist`. The function's own new docstring says "'Anywhere in the chain' is
              a universal, so the set it quantifies over has to be the whole chain", over a `parts`
              list of eight that is not the whole chain. I checked the arithmetic: at 1e100
              `px - stop ≈ 1.4e+100`, two orders under `trend`'s 9.776e+101, so nothing moves — same
              shape of defect as round 3's, one iteration later.
    fix:      Add `px - stop` (and `px`) to `parts` and re-print §D3 (the figures will not move), or
              drop the universal: "the largest of the three inputs, `rng`, `avg`, `MULT*avg`, `stop`
              and `dist` — the eight series listed" in the function docstring, §D3's prose and the
              module docstring.
  - severity: NIT
    location: docs/reviews/auto-2026-11-19-j-kaufmanstop-dist/01-j-kaufmanstop-dist.md:486
    problem:  The round-3 fix row says "The reviewer's own figure ('eleven times … at ten line
              numbers, plus the §D1 variant') had the same off-by-one from the same cause." It did
              not. I ran the multiline count myself: eleven statements in that wording (lines 176,
              233, 333, 353, 372, 447, 568, 613, 652, 736, 783) plus §D1's shorter one at 399 —
              twelve, exactly as item 7 now says. The round-3 reviewer's COUNT of eleven was right;
              only their line-number list was one short. The log now records a prior round's correct
              figure as wrong, in the fix row whose subject is counting honestly.
    fix:      "⚠ The reviewer's count of eleven was right; their line-number LIST was one short, from
              the same single-line grep — which is how the first replacement count here came out
              eleven for the total instead of twelve."
SUMMARY: The arithmetic is untouchable and I gave up on it inside the first hour: every cell of §ENV
through §G5, §L and §Z reproduced to the digit on both dispatches, the eight moved §D2 cells are
exactly the eight you list with 5.160e-14 worst under both, §D3's 54 cells and the 9.776e+101 /
1.839e+206 headroom are real with `MULT*avg` and `dist` now in the set, §G4's bar-5 row reads 6 and
bar-1,495 reads 5, §G5's 99-of-120 is there, the prototype is bit-equal, item 7's TWELVE is right and
I counted it myself with a multiline match, 380 twice, 1,478+1 naming nothing else, 2/12,496/86 to
the second decimal of the duration, and all five wiring touch points plus every count moved. And then
round four of the same disease. You were told to stop naming `_prep_values` as the mechanism, you
scoped it in four places, you wrote a fix row saying "all four places" — and the receipt still tells a
later session, at line 904, that `_prep_values` is "what the column *does* lean on", 190 lines after
the same receipt says it "does not lean on the name", with the script repeating the universal at :994
four lines above its own print that disclaims it. Then there is the thing no round has caught: you
quote `candidates_r2.csv` for four of §E's figures and tell a later session twice to go measure
`lean_avgrange_14` "before shipping both", while line 6 of that same CSV records it STRUCK at 0.9489
against `natr` and "dropped: Gate E STRUCK" — the nearest candidate of this column's own family,
struck against this column's own top comparator, and your receipt turns it into a to-do instead of a
warning. Fix those two, scope the "not a measured cell" universal to the 42 cells that ran, correct
"eight orders", and this port is finally done. Not yet.
```

### Fixes applied after round 4 (all seven)

| finding | what was done |
|---|---|
| MAJOR, `_prep_values` still standing in two places | Receipt item 5 and the script's `PROPAGATING_MEAN` comment rewritten to the measured scoping: pandas turns an infinite observation into a NaN before a `rolling` aggregation sees it, measured on three aggregations, mechanism not claimed, "of any kind" dropped. The claim is now absent from every file in this port (`git grep _prep_values` returns only the pre-existing `j_gator` files). |
| MAJOR, `lean_avgrange_14` was STRUCK, not pending | **Verified in the CSV before writing:** `candidates_r2.csv:6` records `0.9489221914865852` vs `natr`, n = 397,692, per-frame 0.9458059808195928, verdict `STRUCK`, catalog `FORKDUP`, status `dropped: Gate E STRUCK`, empty issue column; `skipped_r7.py:42` repeats it. Both passages inverted it. §L's closing ⚠ now records the strike and reads it as a risk signal; "What a later session should know" item 4 says there is nothing to measure the pair against; and §E gains a paragraph on it — the nearest member of this column's own family, struck against this column's own top comparator, with the margin between the two being the wick term plus the ×2. ⚠ This is the most load-bearing thing any round changed, and it is Gate E context rather than arithmetic. |
| MINOR, the "not a measured cell" universal | Scoped in both places to the **42** guard-off cells that ran (§G1's 27, §G2's 9, §G5's 6), with §G4's other four plant points named as not re-run with a guard removed. |
| MINOR, the test docstring's bounds list | "(1e-12 and 1e-9 in item 1, 1e-6 in item 4, 1e-9 in item 5 — those four, counted)". |
| MINOR, "eight orders" | 1e-6 / 5.160e-14 = **1.9e+07**, so seven orders. Corrected to the ratio in both files that carried it — `tests/test_j_kaufmanstop_dist.py` (two places) and the receipt's §B1. ⚠ The reviewer said three files; a repo-wide grep for "eight orders" found three instances across **two** files, and the module docstring never carried it. |
| NIT, `_largest_intermediate` still incomplete | `px` and `px - stop` added, so `parts` is now the full **ten** series. §D3 re-printed on both dispatches: every cell unchanged, headroom still 1.839e+206 — the reviewer's prediction again. §D3's prose, the function docstring, the module docstring and the test docstring all say ten. |
| NIT, the log's claim about the round-3 reviewer's count | Checked: its count of eleven in that wording was right and only its line-number list was short. The row now says so instead of calling the figure wrong. |

Suites after the round-4 fixes: `tests/test_j_kaufmanstop_dist.py` **380
passed**, the same **380** under the reduced dispatch (no test added — six
of the seven fixes were prose, the seventh the measurement set); §D3
re-printed on both dispatches, every cell unchanged; full suite **2 failed,
12,496 passed, 86 skipped** in 313 s.

⚠ **Round 4 was this loop's last round** (the cap is round 1 plus three
re-runs), so **its seven fixes have no post-fix review**. There are no open
findings and there is also no PASS: every round of this loop returned
REVISE, and `99-summary.md` says so rather than implying a clean bill.
