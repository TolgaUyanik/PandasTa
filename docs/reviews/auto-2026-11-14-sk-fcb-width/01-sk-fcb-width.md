# 01 — SK-FCB-WIDTH: implementation log and review rounds

**Task:** port Skender's `Fcb` width (span 2) as `sk_fcb_width` (volatility) through
Gates A–D, the five wiring touch points, the tests and `docs/SkFcbWidthMeasured.md`.
Gate E and both suites are the launcher's.
**Rounds:** 4 — the cap, per the user's standing review-loop rule. Rounds 1 and 2 are
recorded verbatim below; rounds 3 and 4 are summarised below them with their findings and
outcomes. **No round returned PASS**, and round 4's fixes are therefore the only changes
in this port that no reviewer has read; `99-summary.md` says so too, and lists them.

---

## Implementation log

1. **Read the sources available.** The issue (`docs/issues/106-sk-fcb-width.md`, GitHub
   #107), the screen prototype (`docs/issues/screen/ind_screen_r2.py:54-61` for
   `last_fractal` and `:175-176` for the candidate), `CLAUDE.md`'s gate table, and the
   two most recent merged ports for shape (`j_damiani` in this same category, `j_acosc`
   for the test-module standard). **`Fcb.Series.cs` itself is unreadable here** — no
   package, no `docs/pine/`, no web — so Gate A is the formula the issue names, spelled
   two ways, and the attribution says so.
2. **Module** (`pandas_ta/volatility/sk_fcb_width.py`): `SPAN = 2` and
   `MIN_BARS = 2 * SPAN + 1` as module constants, `_last_fractal` as the rolling
   strict-dominance form the prototype uses, a guard masking non-finite high/low, and the
   usual `close` divisor guard. One column, `SK_FCB_WIDTH_2`.
3. **Measurement script** (`docs/measure_sk_fcb_width.py`): 17 sections, each printing a
   gate limb. Eight frames — `tests/test_j_acosc.py`'s seven plus `coarse`, a 2.0-tick
   walk built specifically because the fractal predicate is strict and this repo has
   already been burned once (FVGDEAD) by synthetic continuous floats.
4. **Ran every section**, then wrote the module docstring from the printed output rather
   than the other way round.
5. **Wiring**, five touch points plus three count surfaces, and
   `python docs/gen_indicator_dictionary.py` re-run: 345 → 346 in `Category`, 353 → 354
   accessors, 347 → 348 probed, volatility 36 → 37, 690 → 691 tagged columns, 329 → 330
   `SF`. All read back out of the generated file (§M), not incremented by hand.
6. **Test module** (`tests/test_sk_fcb_width.py`), and `docs/measure_sk_fcb_width_cpu.py`
   to re-run it and any section with numpy's `AVX512F`/`AVX512_SKX`/`AVX2`/`FMA3`
   dispatch disabled.
7. **Receipt** (`docs/SkFcbWidthMeasured.md`), Gate E recorded as pending.

### Things the measurements changed about the port

- **The high/low guard's justification was wrong in the first draft.** The comment claimed
  an unguarded `+inf` high makes "800 of 800 later bars infinite". Measured: **9**, because
  the next fractal replaces it. The comment now says 9 (and 5 for a `-inf` low), and §G3
  adds that four of the six bad-price plants cost nothing even unguarded.
- **"Unbounded forward reach" for a bad high/low was an argument, not a measurement.**
  Measured reach: 10 bars (high) and 4 (low) for a plant at bar 700 of `walk`. The claim
  is now "not bounded by a window the way a rolling mean's is", with those two numbers
  labelled as that plant on that frame.
- **The explanation for §F's synthetic-vs-real gap was tested and refuted.** The obvious
  guess — "on a continuous frame the band is re-drawn every few bars, so the close carries
  the column" — predicts a high correlation with `1/close`. Measured: -0.0330 .. 0.4571
  against `1/close` and 0.5357 .. 0.9973 against the column's own numerator. The guess is
  recorded as refuted and no replacement mechanism is offered.
- **The blind sweep is a weak detector for this column**, and that is why the detector was
  changed before any of this was written up: a fractal is a comparison, so a 3% tail nudge
  leaves most boundary decisions intact. The sweep became "one shared past, two wholly
  different futures".

---

## Round 1 — REVISE (2 MAJOR, 3 MINOR, 2 NIT)

Reviewer's findings, verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/SkFcbWidthMeasured.md:238 (also pandas_ta/volatility/sk_fcb_width.py:214, tests/test_sk_fcb_width.py:52 and :758, docs/MLCompanionContract.md:27)
    problem:  "It reads NEGATIVE on 5 .. 105 bars of each of the seven firing frames" is a number no run prints. §C's `< 0` column, which I re-ran, reads 20 / 91 / 5 / 33 / 21 / 20 / 20 — the range is 5 .. 91. The 105 is `coarse`'s 20 negatives PLUS its 85 exact zeros, which the very same sentence then reports again as "plus 85 readings of exactly 0.0", so the headline double-counts the zeros and inflates the worst frame by 15%. You wrote the arithmetic and called it a measurement, in four places, one of them the contract the parent repo reads. This is the exact defect CLAUDE.md says killed 17 of 18 candidates.
    fix:      Replace "5 .. 105" with "5 .. 91" in all four locations, and if the `<= 0` figure is the one you want, state it separately and label it: "5 .. 91 negative, and 5 .. 105 readings `<= 0` once `coarse`'s 85 exact zeros are included". Then re-grep the four files for "105" so no copy survives.
  - severity: MAJOR
    location: docs/SkFcbWidthMeasured.md:234 (and tests/test_sk_fcb_width.py:746)
    problem:  "a divergence from every rolling-window column in this category, which would read 0.0" is an unmeasured "every" about 36 other columns, and it is false. `j_damiani` is in `Category["volatility"]` and its own receipt, in this tree, measures the flat frame as "NaN on 1,500 of 1,500" (docs/JDamianiMeasured.md:878, :1167). `massi` is a ratio of EMAs of `high - low`, i.e. 0/0 on a flat frame, and nothing here ran it either. `docs/measure_sk_fcb_width.py` prints no such column — §F touches six comparators and none of them on `flat`. The trailing clause is loose too: `j_acosc` reads 0.0 on 1,463 of 1,500 bars, not "every bar".
    fix:      Either delete the comparison, or make it a measurement: add a block to §C that runs the volatility bucket on `_flat()` and prints fired/0.0/NaN per column, then quote the real split (naming `j_damiani` as the counter-example, since the fork already measured it). Change "fires on every bar at exactly 0.0" to "reads exactly 0.0 on all 1,463 of its fired bars".
  - severity: MINOR
    location: docs/SkFcbWidthMeasured.md:187-190
    problem:  "The gate is therefore a pair of statements, both asserted in `tests/test_sk_fcb_width.py`: 1. the module is caught on 0 of 1,499 offsets on each of the eight frames". The test asserts no such thing — `OFFSETS = list(range(N - 36, N))`, so `test_gate_b_mutant_the_module_reads_no_future_bar` asserts 0 of 36, and the test's own docstring (line 666) correctly says the 1,499 form is "too slow to keep here". The strong form lives only in a script CI never runs, so a future refactor that leaks a look-ahead outside the last 36 bars is guarded by nothing. The receipt advertises a regression guard that does not exist.
    fix:      Rewrite statement 1 as "caught on 0 of 36 offsets on each of the eight frames in `tests/test_sk_fcb_width.py`, and 0 of 1,499 in `docs/measure_sk_fcb_width.py` §B, which the suite does not run", or add one dense-sweep test on a single frame so the claim has an assertion behind it.
  - severity: MINOR
    location: pandas_ta/volatility/sk_fcb_width.py:130-133 (and docs/SkFcbWidthMeasured.md:24-28)
    problem:  "`docs/pine/` is absent, Stock.Indicators is not installed and web access is unavailable (`tests/..::test_the_source_library_is_not_readable_here` records all three ... so the claim cannot rot)". That test has three assertions and none of them is about web access: `find_spec("stock_indicators") is None`, `docs/pine` missing, and `rglob("Fcb.Series.cs")` empty. The "all three" is a count that does not correspond to the run — the third assertion is a repo file search, and the one fact that could silently change (a machine with network) is the one nothing pins.
    fix:      Say "two of the three pinned by that test (the package and `docs/pine/`, plus a repo-wide search for `Fcb.Series.cs`); web access was unavailable in this session and is NOT pinned" in both the docstring and §"What this port does NOT establish".
  - severity: MINOR
    location: tests/test_sk_fcb_width.py:789-798
    problem:  The docstring promises "far fewer band steps than fired bars, and strictly more distinct column values than band levels". The first is asserted (`0 < steps < fired / 2`); the second is not. `assert up.dropna().nunique() <= _steps(up) + 1` is a tautology for any step function — the number of distinct levels of a series can never exceed its number of changes plus one — so the test passes on any implementation whatsoever and pins nothing about the divisor moving the column.
    fix:      Assert what the docstring says: `assert col.dropna().nunique() > up.dropna().nunique() + lo.dropna().nunique()` (1,491 > ~218+207 on `walk`, 60 > ~16+13 on `coarse`), or drop the clause from the docstring and keep only the step/fired-bar bound.
  - severity: NIT
    location: docs/measure_sk_fcb_width.py:780-782
    problem:  §G3's prose says "two of the six plants are already clean unguarded", while the table it prints two lines later shows four clean rows (high NaN, high -inf, low NaN, low +inf) and two infinite ones. The receipt got this right ("the four plants it buys nothing for", §G3), so the script and its own output disagree.
    fix:      Change the sentence to "four of the six plants are already clean unguarded -- the two wrong-side infinities and the two NaNs, which never made a fractal anyway".
  - severity: NIT
    location: docs/SkFcbWidthMeasured.md:76
    problem:  "**Bit-equal on all eight frames**, max |diff| 0.000e+00 everywhere" — on `flat` the script prints `nan`, not 0.000e+00, because no bar fires and `_abs` returns NaN. §A1's table handles the same cell honestly with "—"; §A2's prose does not. Same looseness at §A4: `EndType.Close` is said to differ "on nearly every shared bar", which is 896 of 1,411 on `coarse`.
    fix:      Write "max |diff| 0.000e+00 on the seven firing frames; `flat` has no shared bar, so the figure is undefined and bit-equality is the all-NaN masks matching", and replace "nearly every shared bar" with the measured range (896 .. 1,491 of the shared bars).
SUMMARY: The mathematics is the one part of this I could not break: the window alignment is right (centre `T-2`, left `T-4..T-3`, right `T-1..T`, result placed at `j + span`), the strict `>` matches the `evalHigh <= pHigh` you transcribed, the oracle is a genuinely independent double loop, the prototype retype matches `ind_screen_r2.py:54-61` and `:175-176` character for character, Gate B's mutants are really read off disk and `exec`'d, `0 < fires < n` is really asserted, and all 157 tests pass under reduced CPU dispatch with §A3/§C identical cell for cell — I re-ran every section and every figure I checked reproduced, from 10,330 pooled bars to the 1.229e-12 on `grid` at x3.7 to the 6.6/26.4 MB peaks. Then you did the one thing this repo says it will not forgive: you wrote two numbers you had not run. "5 .. 105 negative bars" is 5 .. 91 — you added `coarse`'s 85 zeros into a negative count and then listed them separately in the same breath, and shipped that arithmetic into the module docstring, two test docstrings, the receipt and the ML companion contract the parent repo consumes. "Every rolling-window column in this category would read 0.0" is a claim about 36 columns you never ran, contradicted by `j_damiani`'s own receipt sitting in this tree at NaN on 1,500 of 1,500. On top of that the receipt advertises a 0-of-1,499 assertion the test module does not contain, cites a test as pinning a web-access fact it cannot see, and ships one tautological assertion dressed up as a structural pin. Fix those six sentences and one assert; the port itself is sound.
```

### What landed for round 1

| # | severity | fix | outcome |
|---|---|---|---|
| 1 | MAJOR | 5 .. 105 → 5 .. 91, `<= 0` stated separately | **applied** in all four places (module docstring, receipt §C, two test docstrings, contract); re-grepped |
| 2 | MAJOR | run the bucket on a flat frame | **applied** — new §C3 runs all 37 indicators / 63 columns through their accessors: **13 all-NaN** (incl. `j_damiani` and this column), **26 all-0.0**, 24 other, 0 raised. The claim is now the measured split and the old sentence is recorded as refuted. `j_acosc` clause corrected to "all 1,463 of its fired bars" |
| 3 | MINOR | reword, or add a dense test | **both** — §B statement 1 reworded, and a new `test_gate_b_mutant_the_module_reads_no_future_bar_at_any_offset` sweeps 299 of 300 offsets |
| 4 | MINOR | web access is not pinned | **applied** in the module docstring and the receipt's opening section |
| 5 | MINOR | replace the tautology | **applied** (and round 2 then found the replacement was still a proxy — see below) |
| 6 | NIT | "four of the six plants" | **applied** in the measure script's §G3 prose |
| 7 | NIT | §A2's `nan` cell, §A4's "nearly every" | **applied** — 0.000e+00 on the seven firing frames with `flat` named, and 896 .. 1,491 |

158 tests, passing under both dispatches after the round-1 fixes.

---

## Round 2 — REVISE (2 MAJOR, 4 MINOR, 2 NIT)

Reviewer's findings, verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/MLCompanionContract.md:27 (the `sk_fcb_width` paragraph, sentence beginning "Four things a consumer must know")
    problem:  "Four things a consumer must know, each of them a departure from how the other
              volatility columns behave." Nothing measured that. It is the EXACT defect round 1
              caught in §C and §C3 — an unmeasured universal about 36 other columns — relocated
              into the one consumer-facing surface round 1 only checked for the 5 .. 105 figure.
              And it is refuted by this port's own §C3: 13 of the bucket's 63 columns read
              all-NaN on a flat frame, `j_damiani` among them, so bullet 1's flat-frame clause is
              the OPPOSITE of a departure. It is refuted a second time by the paragraph three
              screens below it in the same file, where `j_damiani`'s own entry says "A flat frame
              fires on 0 of 1,500 bars and a frame flat for its first 50 bars fires from bar 53,
              not bar 3" — a data-dependent warm-up, the same alleged departure. Bullet 3 is no
              safer: `donchian`'s bands over close are also a step function over a moving divisor,
              and nothing in the run checked.
    fix:      Cut "each of them a departure from how the other volatility columns behave" to
              "Four things a consumer must know." In the warm-up bullet, append §C3's measured
              split verbatim: "13 of the bucket's 63 columns read all-NaN on a flat frame,
              `j_damiani` among them (`docs/SkFcbWidthMeasured.md` §C3), so the all-NaN reading is
              not a divergence." If a departure claim is wanted for bullets 2, 3 or 4, run the
              bucket for that property the way §C3 ran it for the flat frame; otherwise say
              nothing about the other columns.
  - severity: MAJOR
    location: docs/SkFcbWidthMeasured.md:375-376 and 389-392 (§F), and the `sk_fcb_width`
              paragraph of docs/MLCompanionContract.md:27
    problem:  §F's entire subject is why in-fork overlap against `natr` reads 0.0722 .. 0.3202
              here, and it answers with "These numbers understate the real-data overlap ... where
              the screen's 89 real frames read 0.6104 — short by roughly 0.29", then "Why is not
              established here". That gap is measured against the ENGINE's comparator while the
              one real-data measurement of the IDENTICAL fork pair goes uncited: the screen's
              stage-2 fork overlap in `docs/issues/106-sk-fcb-width.md` — max |ρ| 0.5873 vs
              `natr:NATR_14`, per-frame max median 0.5772, 12 real frames, scale-free `Category`
              outputs at defaults. §A2's bit-equality to the prototype is exactly the argument the
              receipt uses to carry the 0.6104 across, so it carries 0.5873 too. A grep of the
              module, the receipt, the measure script, the tests and the contract finds neither
              0.5873 nor 0.5772 anywhere. Both sibling ports put that figure in precisely this
              slot (`j_damiani`: "the 2026-10-24 screen's own fork-overlap stage put `massi`
              nearest instead, at 0.7023 on 12 REAL frames"; `j_gator` likewise). The contract
              paragraph compounds it by carrying no non-redundancy clause at all, where
              `j_damiani` and `j_gator` both carry "⚠ Non-redundancy, SYNTHETIC: ...". A section
              that opens "⚠ Synthetic, and a disclosure rather than a gate" and then omits the
              only real number for its own pair is a hole wearing a disclosure's coat.
    fix:      In §F quote the screen's stage-2 figures (max |ρ| 0.5873 vs `natr:NATR_14`,
              per-frame max median 0.5772, 12 real frames, from the issue), re-derive the gap
              against the apples-to-apples figure (0.5873 vs this file's 0.0722 .. 0.3202, i.e.
              roughly 0.27) and keep the engine's 0.6104 separately labelled as the engine
              comparator. Add a one-line "⚠ Non-redundancy, SYNTHETIC" clause to the contract
              paragraph carrying the same three numbers.
  - severity: MINOR
    location: docs/SkFcbWidthMeasured.md:313-314 (§C3, closing sentence)
    problem:  The round-1 fix introduced a fresh unmeasured claim: "What is distinctive here is
              only the *reason*: no strict local extreme, rather than a guard or a division by
              zero." §C3 prints `fired` and `zeros` per column and nothing else; the mechanisms
              behind the other twelve all-NaN columns (`cvi`, `edge`, three `g191_*`, `har_park`,
              `j_damiani`, three `range_profile`, `roll_spread`, `rvi`) were never inspected. The
              sentence asserts both an exclusivity ("only") and a fact about twelve other
              modules' internals.
    fix:      Replace with the measured statement: "The reason here is a missing strict local
              extreme rather than a guard or a zero divisor; the other twelve were not inspected,
              so no claim is made about their mechanisms."
  - severity: MINOR
    location: tests/test_sk_fcb_width.py:807-828 (test_the_band_is_a_step_function_over_a_moving_divisor)
    problem:  The replacement for round 1's tautology is a proxy weaker than the docstring it
              serves. The docstring says the assertion is "strictly more distinct column values
              than the two legs have distinct levels between them -- which is the divisor moving
              the column on bars where the band did not move." It is not. The number of distinct
              (upper, lower) PAIRS is bounded by the number of band steps plus one, not by
              `up.nunique() + lo.nunique()`, so on `coarse` — 15 + 12 = 27 steps, up to 28
              distinct pairs, against legs whose repeated tick levels can total fewer than 20
              distinct values — the inequality can be satisfied with a CONSTANT divisor and no
              divisor motion at all. The mechanism is asserted in prose and tested only by
              proxy, which is the shape round 1 flagged.
    fix:      Assert the mechanism: count bars where `up` and `lo` each equal their previous
              value and the column still changed, assert that count > 0 on every firing frame,
              and put the measured per-frame counts in the docstring prose.
  - severity: MINOR
    location: tests/test_sk_fcb_width.py:691-708 and docs/SkFcbWidthMeasured.md:184-190 (§B,
              `right-window-lead`)
    problem:  The weakest mutant — one extra bar of right-hand window, the most insidious edit in
              the set — is carried by "caught somewhere" with a measured margin of 4 of 36 on
              `jump`, and the receipt stops at reporting that. This repo already solved this exact
              problem one port earlier: `j_gator`'s teeth mutant sat at 5 of 36 and the limb was
              carried by "a mechanism-aware sweep that catches 95 of 95 exposed offsets"
              (`docs/MLCompanionContract.md`, `j_gator` paragraph). 4 of 36 is also the only
              assertion in this module that a last-bit price move near a boundary could flip, so
              it is the suite's thinnest ice as well as its weakest evidence.
    fix:      Add a mechanism-aware sweep for `right-window-lead`: restrict the offsets to those
              where the extra bar is actually exposed (where `x[j]` exceeds `x[j-1]` and the
              comparison against `ref` on bar `j-1` flips), and assert the mutant is caught on
              every exposed offset. Keep the 4-of-36 blind figure in §B as the blind number.
  - severity: MINOR
    location: docs/reviews/auto-2026-11-14-sk-fcb-width/ (folder contents)
    problem:  The folder holds `00-manifest.md` and nothing else. Every sibling run carries
              `01-<name>.md` ("implementation log + all four review rounds verbatim") and
              `99-summary.md`; the manifest's own execution map ends "→ review rounds" and logs
              none. The consequence is not cosmetic: round 1's seven findings and what landed for
              each now exist on disk ONLY as self-referential asides inside the shipped artefacts
              — `docs/SkFcbWidthMeasured.md` lines 30-31, 199-200, 310-314 and 316, and test
              docstrings at lines 679-685, 770-772 and 817-819 ("which round 1 of the review
              caught", "An earlier draft of this receipt..."). A consumer reading a module's test
              docstring should get the measurement, not the review's confession log.
    fix:      Write `01-sk-fcb-width.md` (implementation log, round 1 and round 2 verbatim, and
              what landed per finding) and `99-summary.md` on the sibling pattern, then strip the
              seven "round 1 of the review caught it" asides from the receipt and the test
              docstrings, leaving the measured sentence standing alone.
  - severity: NIT
    location: docs/SkFcbWidthMeasured.md:195-196 (§B statement 1) and
              tests/test_sk_fcb_width.py:674-688
    problem:  "on 0 of 299 — every bar — of a 300-bar walk" and the test docstring's "EVERY bar
              of a 300-bar walk is a split point, 299 of them" contradict themselves: the sweep
              runs `range(1, 300)`, so bar 0 is excluded. The same loose phrasing covers the
              dense table ("0 of 1,499" called every bar of 1,500).
    fix:      Say "every bar but bar 0 — 299 of 300, and 1,499 of 1,500 in §B's table" in both
              places.
  - severity: NIT
    location: tests/test_sk_fcb_width.py:831-841 (test_a_tick_grid_starves_the_band) against
              docs/SkFcbWidthMeasured.md:292-293
    problem:  §C2's prose says "rounding starves the band monotonically in the tick" — the band,
              both legs, and the table carries both (216/212/71/15 upper, 205/199/82/12 lower).
              The test builds `counts` from the UPPER leg only, so half the claimed monotonicity
              has no assertion.
    fix:      Loop `(h, True)` and `(l, False)` in the test and assert the ordering on each, or
              narrow the prose to "the upper leg, with the lower leg measured in the table".
SUMMARY: Seven fixes were owed and seven landed — 5 .. 91 with `<= 0` at 5 .. 105 in all four
places, §C3 run instead of guessed, the dense 299-offset test built, §A2's `nan` and §A4's
896 .. 1,491 stated, "four of the six plants", and the tautology replaced. I re-ran A2, A3, A4, B,
C, C3, D and F and every cell reproduced; 158 pass under both dispatches; the wiring counts hold
on all six surfaces. The mathematics is not where this fails. It fails where it always fails in
this repo: the moment the prose stops reporting a run and starts narrating a position. The
contract still tells a consumer that four behaviours are "a departure from how the other
volatility columns behave" — a claim about 36 modules that the port's own §C3 refutes for the
first of them and that the `j_damiani` paragraph in the same file refutes again; you fixed that
sentence in the receipt and left it standing on the one page an ML consumer actually reads. And
§F spends two paragraphs confessing that it cannot explain the synthetic-to-real gap against
`natr` while the issue it is implementing carries the real figure for that identical fork pair,
0.5873 on 12 real frames, which appears nowhere in the port — both siblings put it in exactly
that slot. A disclosure that omits the one number in scope is not a disclosure. Add to that a
replacement assertion that still only proxies its own docstring, a 4-of-36 mutant margin where
the previous port built a mechanism-aware sweep, and a review folder that is two files short so
that round 1's history lives in a shipped test docstring instead of a log. Fix the two MAJORs
and the rest is tidying.
```

### What landed for round 2

| # | severity | fix | outcome |
|---|---|---|---|
| 1 | MAJOR | cut the "departure" claim from the contract; add §C3's split | **applied** — the clause is gone and the warm-up bullet now carries "13 of 63 all-NaN, `j_damiani` among them, 26 exactly 0.0" |
| 2 | MAJOR | quote the screen's stage-2 fork figures; add a non-redundancy clause to the contract | **applied** — §F gains a three-row table (synthetic 0.0722 .. 0.3202 / fork stage 2 **0.5873**, per-frame max median **0.5772**, 12 real frames / engine **0.6104**, 89 frames) and re-derives the gap as ~0.27 against the apples-to-apples figure; the contract paragraph gains "⚠ Non-redundancy, SYNTHETIC" with the same three numbers |
| 3 | MINOR | §C3's closing "only the reason" | **applied** — "the other twelve all-NaN columns were not inspected, so no claim is made about their mechanisms" |
| 4 | MINOR | assert the mechanism, not a proxy | **applied** — new §C counts bars where neither leg moved and the column moved anyway (1,071 of 1,071 on `walk`; **271 of 1,387** on `coarse`), and the test asserts that count > 0 per firing frame |
| 5 | MINOR | mechanism-aware sweep for `right-window-lead` | **applied** — new §B2 derives the exposure condition from the edit (`x[j-3] > max(x[j-5], x[j-4], x[j-1])`, necessary by construction), sweeps 1,495 offsets of each of the seven firing frames: **0 of 8,743 unexposed offsets caught**, 1,692 of 1,722 exposed ones, and all **30 misses classified** into three named buckets (17 / 9 / 4) with **0 left over**. A new test asserts both halves on 300-bar `walk` and `coarse`. ⚠ Round 3 caught this row's first draft hand-adding the control to 8,730 and the buckets to 21/9/4; the script now prints both pooled rows |
| 6 | MINOR | write `01-*.md` and `99-summary.md`; strip the review asides from the shipped files | **partly applied, and the other half DECLINED with a reason** — the two log files are this file and `99-summary.md`. The "an earlier draft said X, which was wrong" notes stay: that is this repo's own convention for a changed conclusion, not an invention here (`docs/JAcoscMeasured.md:522` "⚠ **Not bit-equal, and an earlier draft of this section said it was.**", `docs/TsEnergyLast20Measured.md:628-631` "...and round 1 of the review caught it", `docs/G191158Measured.md:49,83`, `docs/TsAggac60Measured.md:133,270`, and `tests/test_j_acosc.py:763` "An earlier draft of this port ARGUED it"). Deleting them would make the receipt read as if it had been right the first time, which is the failure mode those notes exist to prevent |
| 7 | NIT | "every bar but bar 0" | **applied** in §B and the dense test's docstring |
| 8 | NIT | tick-starve test on both legs | **applied** — the test loops both legs and asserts the ordering and the 5x drop on each |

160 tests, passing under both dispatches after the round-2 fixes. §B2 and §C's new tables
are identical under reduced dispatch.

---

## Round 3 — REVISE (3 MAJOR, 3 MINOR, 3 NIT)

Dispatched after the round-2 fixes. The reviewer re-ran §A1–§A4, §B, §B2, §C, §C3, §D,
§F, §G, §H, §L, §M and §W, confirmed every cell reproduced, confirmed the §B2 derivation
is sound, confirmed the five citations behind round 2's declined half, and then found
three fresh arithmetic claims:

| # | severity | finding | fix | outcome |
|---|---|---|---|---|
| 1 | MAJOR | §B2's control total was hand-added as **8,730**; it is **8,743** (7 × 1,495 − 1,722). Shipped in the module docstring, §B2, the Verdict row and this log — "round 1 killed the identical defect and round 2's own fix re-committed it" | quote 8,743, and have the script print the pooled totals | **applied in all four places**, and `section_B2` now prints `POOLED 10465 / 1722 / 1692 / 0` and `unexposed 8743` |
| 2 | MAJOR | the new mutant test's docstring said "**21** verdict-agreement, 9 level-equality, 4 not-yet-fired" — which sums to 34 against the 30 the same sentence claims, where the printed table says **17** | 17, and state the per-frame split | **applied**, and `section_B2` prints the `POOLED 30 17 9 4 0` row |
| 3 | MAJOR | `99-summary.md` **did not exist** while this log asserted in the present tense that it did, and pointed the round-3 verdict at it | write it, or say it is deferred | **applied** — `99-summary.md` written on the sibling pattern |
| 4 | MINOR | §F's new row and the contract said "**8** synthetic" frames; `flat` never fires, so it carries no Spearman — the same folding-in round 1's NIT #7 had already paid for | "7 synthetic" | **applied** in both |
| 5 | MINOR | the contract's non-redundancy clause ranked by **signed** ρ, putting two invented proxies ahead of the shipped `rvi:RVI_14` (\|−0.2858\|), where the screen, the issue and the other receipts rank by max \|ρ\| | rank by \|ρ\|, name `rvi` second, or print the ordering | **applied** — `section_F` sorts by \|ρ\| and prints the column; the receipt's table and the contract both rank natr 0.3202, rvi 0.2858, true_range 0.2422, donchian 0.2302, chop 0.2023, massi 0.1551 |
| 6 | MINOR | round 2's MAJOR #2 had landed in the receipt and the contract but **not** in the test module's header, which still framed the gap against the engine comparator alone | add the fork stage's figures there | **applied** — 0.5873 / 0.5772 / 12 real frames, and the ~0.27 gap |
| 7 | NIT | "every offset of every frame" where the §B2 sweep is `range(5, n)`; plus two surviving "every bar" copies | "every offset from 5 on — 1,495 of 1,500", "every bar but bar 0" | **applied** in all four §B2 places and the two survivors |
| 8 | NIT | §C's band-held reading was a two-regime dichotomy that left `grid` (1,050 of 1,054) out of both, and a test docstring said "six continuous frames" where the module defines continuous as five | name all three regimes; match the module's phrasing | **applied** in both |
| 9 | NIT | `00-manifest.md` carried the stale 158 test count and its execution map ended in nothing | 160 and a pointer | **applied**, with the round-by-round counts |

## Round 4 — REVISE (3 MAJOR, 2 MINOR, 4 NIT) — the cap

The reviewer re-ran everything again (A1–W, both dispatches), confirmed 8,743 / 1,722 /
1,692 and 17 / 9 / 4 reproduce, confirmed the `right-window-lead` exposure condition is
necessary by construction, and confirmed the six wiring surfaces. Its findings:

| # | severity | finding | outcome |
|---|---|---|---|
| 1 | MAJOR | the fix for round 3 #5 re-sorted §F's table and then **bolted on a fresh un-run sentence** — "`rvi:RVI_14` is ... second-from-last by signed ρ", printed by the script itself. `rvi`'s signed maximum is **0.1409**, the smallest of the six: it is **last**, behind both invented proxies *and* two shipped siblings (`chop` 0.1763, `massi` 0.1551) | **applied** — `section_F` now PRINTS a second ranking by signed maximum instead of describing it, and the receipt carries both orderings side by side with the corrected reading |
| 2 | MAJOR | `99-summary.md`'s "3 failed, **9,286** passed, 85 skipped" is the round-1 suite, 157 tests ago; it is **9,289** now | **applied** — re-ran `python -m pytest -q`: 3 failed, **9,289** passed, 85 skipped, and the summary now says where the three extra came from |
| 3 | MAJOR | round 3's nine findings and outcomes existed **nowhere on disk** while both log files asserted they did, and the two files disagreed on whether three or four rounds had run | **applied** — the round-3 table above, this round-4 table, and the header corrected to four rounds |
| 4 | MINOR | "spelled two **independent** ways" is wrong about limb 2: `_prototype`'s `last_fractal` is the module's `_last_fractal` operation for operation, so its bit-equality is structural, not corroboration | **applied** — the receipt (§A1, §A2, the opening section and the Verdict row), the module docstring and the test header now say "two ways, one of them independent", and what §A2's limb actually buys |
| 5 | MINOR | "on the **eight** frames the first fire lands on bar 7 .. 89" in the contract and the module docstring — seven fire, and the eighth is a constant, not random. The same defect as round 3 #4, left on two surfaces | **applied** in both |
| 6 | NIT | §B's table header still said "and then over every bar" where the table is headed 1,499 | **applied** |
| 7 | NIT | §B2's two pooled rows sat after a blank line, so they rendered as a header-less second table | **applied** — rows folded into the table with real cells |
| 8 | NIT | the test's "All three routes to that source are pinned shut" is the one surface that does not carry the web-access caveat | **applied** |
| 9 | NIT | `99-summary.md`'s gate row B dropped the "six frames other than `flat` and `coarse`" qualification the receipt bolds | **applied** |

⚠ **Round 4 is the cap, so these nine fixes are the only changes in this port that no
reviewer has read.** They are listed above and in `99-summary.md` rather than folded in
silently. Eight of the nine are prose; the one code change is `section_F` printing a
second ranking, whose output is in this session's run log and in the receipt's new table.
