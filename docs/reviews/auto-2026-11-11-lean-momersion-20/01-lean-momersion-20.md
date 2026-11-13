# Task log — `lean-momersion-20`

**Date:** 2026-11-11 · **Lane:** main thread · **Status:** PASS at round 4
(with post-PASS MINOR/NIT fixes applied and verified by re-running the
harness and the suites — see "After the PASS" at the bottom).

## Implementation summary

New files:

* `pandas_ta/momentum/lean_momersion_20.py` — the indicator. `r[t] =
  close[t]/close[t-1] - 1`, `pair[t] = sign(r[t]) * sign(r[t-1])`, and
  `100 * MC / (MC + MRC)` over the trailing `length` pairs, where `MC` counts
  `pair > 0` and `MRC` counts `pair < 0`. A zero return is in neither bucket;
  a window whose every pair is flat is NaN; the warm-up (21 bars at the
  default) is NaN. One `.rolling(` call, in a local `count()` closure used
  three times, so there is one window whose causality Gate B must pin.
* `tests/test_lean_momersion_20.py` — 104 tests.
* `docs/measure_lean_momersion_20.py` — the harness that prints every number
  the receipt quotes.
* `docs/LeanMomersion20Measured.md` — the receipt.

Wiring, all five touch points plus the counter files:
`pandas_ta/momentum/__init__.py`, `Category["momentum"]` in
`pandas_ta/__init__.py`, the `df.ta.lean_momersion_20()` accessor in
`pandas_ta/core.py`, `README.md` (319 → 320 registered, 327 → 328 callable,
momentum 82 → 83), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 319 →
320), `docs/MLCompanionContract.md` (664 → 665 tagged columns, 307 → 308
`SF`), and `docs/IndicatorDictionary.md` regenerated with
`python docs/gen_indicator_dictionary.py`.

Gate E was not run and `../Backtesting` was not read, per the session rules;
`docs/gate_e_ledger.csv` is untouched.

## Review rounds

Each round dispatched a fresh read-only Fletcher subagent with the target
paths, the original ask, and the repo's rubric. Verdicts are quoted verbatim.

### Round 1 — REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/LeanMomersion20Measured.md:354 (the "Parameter guards" table, first row)
    problem:  The row claims `length` = None / 0 / −5 / 1 / 0.5 / **2.9** all give the
              effective column `LEAN_MOMERSION_20` with 379 fires. `2.9` does not.
              `int(2.9) == 2 >= MIN_LENGTH`, so it is accepted, and your own harness prints
              it four lines apart from the numbers you did transcribe:
                  length=2.9: name=LEAN_MOMERSION_2, fires 397
              The row is wrong on both cells (name and count), it contradicts the sentence
              nine lines below it ("`length=50.9` and `length=50` are the same column
              (`int()` truncation)") — truncation is exactly why 2.9 behaves like 2 — and it
              falsifies the receipt's own masthead at line 10-14, "Every number here is
              printed by `python docs/measure_lean_momersion_20.py` ... Nothing in this file
              was typed from expectation." It was typed from expectation. This is the
              repo's named dominant defect, reproduced in the one table a reader consults
              before passing a parameter. The test module does not cover it either: it
              parametrises `[None, 0, -5, 1, 0.5, 1.9]` — 1.9, not 2.9 — so nothing in the
              suite would have caught the sentence.
    fix:      Split the row to match the run: keep `None / 0 / −5 / 1 / 0.5 / 1.9` →
              `LEAN_MOMERSION_20`, 379, and add a row `2.9` → `LEAN_MOMERSION_2`, 397,
              next to the existing `length = 2` row (or state "a fraction that truncates
              BELOW 2 falls back; 2.9 truncates to 2 and is accepted"). Then add `2.9` to
              `test_a_length_below_the_minimum_falls_back_to_the_default`'s complement —
              e.g. extend `test_the_smallest_accepted_length_is_two` to assert
              `lean_momersion_20(close, length=2.9).name == "LEAN_MOMERSION_2"` and 397
              fires — so the receipt row has a pin behind it.
  - severity: MINOR
    location: docs/LeanMomersion20Measured.md:285 ("Nearest neighbours ... (13 shipped columns, one frame)")
    problem:  The table has 13 rows, and 20 lines later the same section says the leader —
              "lag-1 autocorrelation of the last 20 log returns (hand-rolled, not shipped)" —
              is "**not** a shipped column, so it is not a Gate E comparator". So the count
              is 12 shipped columns plus one hand-rolled probe, not 13 shipped. A count
              claim contradicted inside its own section, in a repo whose rule is that every
              count corresponds to a run.
    fix:      Write "(12 shipped columns plus a hand-rolled lag-1 autocorrelation, one
              frame; ...)". The harness's `cands` dict is the authority: 12 `ta.*` columns +
              `autocorr_lag1_20 (hand-rolled)`.
  - severity: MINOR
    location: docs/LeanMomersion20Measured.md:245-249 and pandas_ta/momentum/lean_momersion_20.py:150-154
    problem:  The stated PROOF of ×10/×3.7 bit-identity is incomplete, and it is stated as a
              property of the column rather than of the three frames: "multiplying every
              close by the same positive constant can neither reorder two closes nor
              separate two equal ones." Those are two of three cases. The third is FUSION:
              for closes a ≠ b differing by ~1 ulp, `k*a` and `k*b` can round to the same
              double (×3.7 moves a value from [1,2) into [4,8), where the ulp is 4× wider),
              which turns a signed pair flat, shrinks the denominator and changes the value.
              The same ulp hole sits under the docstring's "on a frame with no exact price
              ties every pair is signed, so the denominator is always 20" (line 100-105):
              `a/b - 1` can round to exactly 0.0 for distinct closes, and under the
              `close.diff()` row of A5, which would then disagree with the ratio spelling.
              The measurements (1479/1479 on three frames) are sound; the universal
              argument offered for them is not.
    fix:      Either bound the claim — "bit-identical on frames whose consecutive closes
              differ by more than a few ulps (measured: three frames, 1,479/1,479 bars);
              a rescale can fuse two closes that differ by 1 ulp, which no price feed
              produces" — or measure it: one 60-bar frame of `np.nextafter`-adjacent closes
              under ×3.7, reported as the one frame where the identity is not guaranteed.
              Same clause in the module docstring at line 150.
  - severity: NIT
    location: tests/test_lean_momersion_20.py:371
    problem:  `TOTAL = len(list(OFFSETS))` is dead — the only consumer of the sweep count is
              the literal 36 inside `PATH_SWEEP` / `DIRECTED`. Copy-paste residue from the
              harness, which does use its `total`.
    fix:      Delete the line, or use it: `assert TOTAL == 36` next to the dicts, so a change
              to `OFFSETS` fails loudly instead of silently re-scaling every pinned count.
  - severity: NIT
    location: docs/LeanMomersion20Measured.md:166-167 and the B2 preamble at line 158-162
    problem:  "whichever **reverses** the sign of `r[J]`" is not what happens on every J of
              the grid frames: where `r[J] == 0` (14.01% of returns on the 0.5 grid), the
              probe takes k = 2.0 and turns a flat bar into an up bar. The premise test
              only asserts `np.sign(pr[J]) != np.sign(r[J])`, which that satisfies, so the
              test is honest and the prose is not.
    fix:      Say "whichever CHANGES the sign of `r[J]` — a reversal where `r[J] != 0`, and
              flat → up where it is zero", and note that the zero-return J are part of why
              the 0.5-grid column reads 27-33/36 rather than 36/36.
SUMMARY: One hundred and two tests pass, the harness reproduces Gates A-D line for line, and I checked essentially every number in the receipt against the run — the Gate B tables (0/36 real, 36/36 and 19/36 and 27/36 mutants), the A4 readings (5.5556 / 55.7143 / 0.8399, 4.4737 / 0.9685), the 2,000-window spread (50.1300 / 50 / 11.2276 / 35 / 65 / 0.4220), the twelve ×8/×64/×10/×3.7 cells, the 1,479 fires, the 22-bar hole, the 129 reachable values, the prototype's 1198/1479 bit-equal at 7.105427e-15, the imported screen candidate, the Gate F line (3 failed, 5560 passed, 83 skipped) and the ledger's exact `['lean_momersion_20', 'mtd_ret']`. All of it holds, the five touch points are all taken, the counts move together (320 / 328 / 320 / 665 / 308), and the directed-probe idea — flip exactly one return with a power of two, because a random replacement path repeats the sign half the time — is the right answer to a sign-driven column and you proved its premise instead of assuming it. And then you typed `2.9` into the guard table without reading the line your own script printed, so the document that opens with "Nothing in this file was typed from expectation" ships a cell that is wrong in both columns, contradicts the truncation rule stated nine lines later, and has no test behind it because the suite pins 1.9 instead. You do not get credit for measuring forty numbers and inventing the forty-first — that is the exact failure mode this repo has lost 17 of 18 candidates to. Fix the row, pin it, fix the two count/prose slips and the ulp hole in the Gate D proof, and this is a ship.
```

**Fixes applied after round 1.** The guard table split into the `1.9` row and
a `2 / 2.9` row, both matching the harness, with
`test_the_smallest_accepted_length_is_two` parametrised over `[2, 2.9]` to
pin it. The neighbour count rewritten as "12 shipped columns plus one
hand-rolled probe". The ×10/×3.7 claim bounded and MEASURED: `ulp_walk()`
added to the harness and `test_the_scale_free_claim_stops_at_one_ulp_moves`
to the suite. `assert TOTAL == 36` added. "Reverses" → "changes" in the
receipt and the tests.

### Round 2 — REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/LeanMomersion20Measured.md:249-275 (Gate D, the parenthetical and "Where that stops"); docs/measure_lean_momersion_20.py:565-577,591-594; pandas_ta/momentum/lean_momersion_20.py:152-157; tests/test_lean_momersion_20.py:63-66,575-581
    problem:  Round 1 flagged the universal x10/x3.7 argument as ignoring ulp-level effects. You added a measurement — good — and then kept the broken argument and wrapped a FALSE MECHANISM around the new numbers. Two shipped claims are wrong, one of them refuted by your own harness two lines later.
              (a) "two adjacent doubles scaled by `k` land a real distance `k·ulp` apart, which is between 1 and 2 ulps of the product's own binade [harness: "in [1, 2) ulps"], so they cannot round together unless `k` is a power of two". Do the algebra: x in [2^p,2^{p+1}), x' = x + 2^{p-52}, kx in [2^m,2^{m+1}). The gap in ulps of the product's binade is k·2^{p-m}, and the two binade constraints give k·2^{p-m} ∈ (1/2, 2) — NOT [1,2). Take k=10 and x in [1.6,2): 10x in [16,20), so the gap is 10·2^-4 = 0.625 ulp. Below one ulp, two DISTINCT closes can and do round to the same double under a non-power-of-two rescale. The stated bound is arithmetically false and the "cannot round together unless k is a power of two" that rests on it is false with it.
              (b) "The argument above covers the closes; it does not cover the RATIO. `close / close.shift(1)` can round to exactly 1.0 for two distinct closes one ulp apart" (same sentence in the module docstring, which ships in `help()`, and in the test docstring). It cannot. For adjacent doubles the exact quotient is 1 + u/a with u/a in (2^-53, 2^-52], which rounds to 1+2^-52, never to 1.0 — which is exactly why `test_the_scale_free_claim_stops_at_one_ulp_moves:585` asserts **zero** returns read as 0.0 on that frame and the harness prints "0.0000 of returns read as EXACTLY zero". You ship a mechanism your own measurement disproves.
    fix:      Replace the mechanism with the one your numbers actually demonstrate, and keep the (correct) conclusion. (1) In the receipt parenthetical and docs/measure_lean_momersion_20.py:570, change "[1, 2) ulps" to "(1/2, 2) ulps of the product's own binade", and delete "so they cannot round together unless `k` is a power of two" — state instead that below one ulp of separation a non-power-of-two `k` CAN fuse two distinct closes (k=10, x in [1.6,2) → 0.625 ulp). (2) Rewrite "Where that stops" and the module/test docstrings to name the real cause: scaling is monotone and a ratio of two distinct doubles never rounds to 1.0, so a return's sign can only change by becoming zero, so the measured x10/x3.7 breakdown on the one-ulp frame is `fl(k·close)` FUSING adjacent closes — not the ratio rounding to 1.0. (3) Make that a number, not an argument: add one harness line printing `zero_share(ulp_walk() * k)` and the count of fused adjacent closes for k = 8/64/10/3.7, and assert the x10 count in `test_the_scale_free_claim_stops_at_one_ulp_moves` (it must be 0 at x8/x64 and > 0 at x10/x3.7). (4) Re-derive the surviving bound from (1) rather than hand-waving "a few": a separation of >= 3 ulps makes `k·gap > 1` ulp for every `k` in (1/2, 2) of a binade, hence fusion is impossible — which is what makes "every real frame" (relative tick 1e-9 vs relative ulp 2.2e-16) safe.
  - severity: NIT
    location: docs/measure_lean_momersion_20.py:376,460,466
    problem:  Round 1's "reverses the sign" NIT was fixed in the receipt (line 161) and the tests (line 459) and left untouched in the harness that PRINTS the evidence: `flip_tail`'s docstring, the Gate B preamble and the output line "the sign of r[J] actually reversed at 36/36 J". The check is `np.sign(pr) != np.sign(r)`, and on the 0.5 grid 14.01% of returns are zero, where the move is 0 -> + and not a reversal.
    fix:      In all three places say "CHANGES the sign of r[J] -- a reversal where r[J] != 0, flat -> up where it is zero", and change the printed label to "the sign of r[J] actually changed at {flipped}/{total} J", matching docs/LeanMomersion20Measured.md:161-166.
  - severity: NIT
    location: pandas_ta/momentum/lean_momersion_20.py:60
    problem:  `with np.errstate(divide="ignore", invalid="ignore")` guards a division that cannot warn: `signed.where(signed > 0)` has already turned every zero denominator into NaN, so neither a divide-by-zero nor an invalid operation is reachable. It is copy-paste from `lean_hurst_100.py:53`, where the `log` of a floored sd genuinely needs it.
    fix:      Drop the `errstate` context and dedent the `values = ...` line, or keep it and say in the comment that it is belt-and-braces because the NaN denominator already suppresses the warning -- do not leave a reader thinking a zero denominator reaches the divide.
SUMMARY: The mathematics, the wiring and the measurement discipline are, this round, almost exactly what this repo asks for: 104 green tests, a full suite that reproduces to the bar, a harness that prints every cell the receipt quotes, two Gate B probes with a measured premise and 32 live mutant cells, and the round-1 CRITICAL and both MINORs genuinely fixed. And then you took the one finding you were told to measure instead of assert, measured it beautifully, and bolted a false explanation onto the result — a bound that is off by a factor of two in the only direction that matters, a "cannot round together unless k is a power of two" that your own x10 table disproves, and a "the ratio rounds to exactly 1.0" that sits four lines from the harness line printing "0.0000 of returns read as EXACTLY zero". That sentence is now in the shipped docstring, where every user who types `help(ta.lean_momersion_20)` will read it. You do not get credit for measuring the right number if you then narrate the wrong cause: the number was never the point, the claim was. Fix the mechanism, pin the fusion count as a number, and this ships.
```

Both arithmetic claims were re-derived on the main thread before accepting
them: the binade factor really is `k·2^(e−f)` ∈ (1/2, 2), and the quotient of
two distinct normal doubles cannot round to 1.0. **Fixes applied:** the
mechanism rewritten as FUSION in the receipt, the harness, the module
docstring and the test docstring; the fused-pair counts and post-scaling
zero-return shares measured (×8/×64 fuse 0 of 299; ×10 fuses 58, 19.40% zero
returns; ×3.7 fuses 10, 3.34%) and pinned in
`test_the_scale_free_claim_stops_at_one_ulp_moves`; the harness prose and its
printed label changed to "changes the sign"; the `errstate` dropped.

### Round 3 — REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/measure_lean_momersion_20.py:51-58 (`ulp_walk` docstring)
    problem:  The refuted mechanism from round 2 is still shipping, verbatim, in the
              harness: "`close / close.shift(1)` can round to exactly 1.0 for two
              distinct closes, so a real move reads as flat, and whether it does can
              depend on the scale." That is false, and this file proves it false 530
              lines later: `gate_d()` prints "0.0000 of returns read as EXACTLY zero
              although every close differs from the last (the ratio cannot round to
              1.0)" on this very frame, and the test pins the count at exactly 0. The
              arithmetic: for adjacent a < b in the same binade the exact ratio is
              1 + u/a with u/a in (2^-53, 2^-52], strictly above the 1 + 2^-53
              midpoint, so it rounds to 1 + 2^-52, never to 1.0; downward, 1 - u/a
              <= 1 - 2^-53, below the 1 - 2^-54 midpoint, so never 1.0 either. You
              fixed this sentence in the four places the brief named and left the
              fifth, in the file that is supposed to be the evidence.
    fix:      Rewrite the docstring to the mechanism the rest of the port now states:
              "every move is one ulp -- the only frame where the x10/x3.7 claim can be
              attacked, not through the division (the ratio of two distinct doubles
              never rounds to 1.0, measured below: 0 of 299) but through FUSION,
              `fl(k*a) == fl(k*b)`, which turns a signed pair flat."
  - severity: MAJOR
    location: tests/test_lean_momersion_20.py:59-61 (header docstring, item 4)
    problem:  "Only the SIGN of a price ratio reaches the counts, and multiplying every
              close by a positive constant can neither reorder two closes nor fuse two
              distinct ones" -- and then, three lines down in the same paragraph, "a
              non-power-of-two `k` can round two closes ONE ULP apart to the same
              double", with 58 of 299 fused pairs pinned by the test below it. The
              docstring asserts a universal and refutes it in the next breath. This is
              the file CLAUDE.md says carries the heaviest docstring in the port,
              i.e. the one a future reader will believe.
    fix:      Drop "nor fuse two distinct ones" and state the true pair of facts:
              a rescale cannot REORDER two closes (`fl(k*x)` is monotone) and cannot
              SEPARATE two equal ones; the one thing it can do is fuse two distinct
              ones, which is the bound item 4 then measures.
  - severity: MINOR
    location: docs/LeanMomersion20Measured.md:259-261 and docs/measure_lean_momersion_20.py:578-581
    problem:  "at k = 10 with `x` in [0.5, 1) it is 10*2^-4 = 0.625" is right for only
              part of that interval. The factor is k*2^(e-f) with x in [2^e, 2^(e+1))
              and k*x in [2^f, 2^(f+1)): for x in [0.8, 1) the product is in [8, 16),
              f = 3, and the factor is 10*2^(-1-3) = 0.625 -- fusion possible, which is
              the sub-1.0 half of the measured frame. For x in [0.5, 0.8) the product
              is in [4, 8), f = 2, and the factor is 1.25 > 1 -- fusion IMPOSSIBLE. The
              interval as written over-generalises the example that carries the whole
              (1/2, 2) argument.
    fix:      Narrow it: "at k = 10 with x in [0.8, 1), where 10x lands in [8, 16), it
              is 10*2^-4 = 0.625" -- and note that the same k at x in [0.5, 0.8) gives
              1.25, which is why fusion is binade-dependent rather than a property of k.
  - severity: NIT
    location: docs/LeanMomersion20Measured.md:262, 277-279; module docstring; test docstring item 4
    problem:  "A separation of 3 ulps or more makes the scaled gap exceed one ulp for
              every k" is true but needlessly loose, and the looseness reads as a
              guess where the rest of the section is exact. Your own bound settles it:
              the scaled gap is g*k*2^(e-f) ulps with k*2^(e-f) > 1/2 strictly, so the
              gap exceeds one ulp for every g >= 2 and ONLY g = 1 can ever fuse.
    fix:      State the tight result -- "only closes exactly ONE ulp apart can fuse;
              at 2 ulps the scaled gap exceeds one ulp for every k" -- and keep 3 as
              stated margin if you want one, labelled as margin.
  - severity: NIT
    location: docs/LeanMomersion20Measured.md:276-277
    problem:  "x8/x64 are bit-identical unconditionally" is a universal with two known
              holes: a close that is subnormal unscaled but normal scaled (5e-309 is
              NaN by the module's guard, 8*5e-309 = 4e-308 is not) changes the NaN
              mask, and k*x can overflow near 1e308.
    fix:      Say "bit-identical on any frame of normal doubles whose k*x does not
              overflow (the arithmetic is exact, 0 pairs fused)".
  - severity: NIT
    location: docs/measure_lean_momersion_20.py:212 and tests/test_lean_momersion_20.py:284
    problem:  The pointless `np.errstate(divide=..., invalid=...)` round 2 killed in the
              module survives in both `variant` helpers. `total.where(total > 0)` has
              already turned every zero denominator into NaN, so there is no warning
              to suppress -- the guard is decoration that implies a hazard that is not
              there.
    fix:      Delete both `with np.errstate(...)` wrappers and dedent the division.
SUMMARY: The mathematics is finally right where it counts -- I re-derived the (1/2, 2)
binade bound, the "never rounds to 1.0" midpoint argument and the g = 1 fusion
condition myself, and all three hold; the harness reproduces every number in the
receipt (7.105427e-15 / 1198 / 1479, 19|12|11 and 36|36|36|27|33 of 36, 58 and 10 fused,
0.1940 and 0.0334, 50.1300 / 11.2276 / 35 / 65, Spearman 0.382917), the 104 tests pass,
the full suite lands on exactly the claimed "3 failed, 5562 passed, 83 skipped" with
exactly the claimed three failures, Gate E is correctly left owed, and all five wiring
touch points plus 320, 328, 83, 320, 665 and 308 are real. And you still shipped the lie. The
sentence round 2 struck -- that the quotient of two distinct doubles can round to 1.0 --
is sitting in `ulp_walk`'s docstring in the file whose own stdout refutes it, and the
test header still claims a rescale "can neither reorder two closes nor fuse two distinct
ones" two lines above the 58 fused pairs it pins. You patched the four places I pointed
at and never grepped for the fifth, which is precisely the habit this repo's history is
made of. Fix the two contradictions, tighten 0.625 to [0.8, 1) and the ulp threshold to
the 2 your own bound proves, and this port is done. Not before.
```

**Fixes applied after round 3:** `ulp_walk`'s docstring rewritten to the
fusion mechanism; the test header's "nor fuse two distinct ones" replaced
with "nor separate two equal ones"; the k = 10 example narrowed to
`x ∈ [0.8, 1)` with the `[0.5, 0.8) → 1.25` contrast stated; the threshold
tightened; the ×8/×64 universal qualified with its two holes; both leftover
`errstate` wrappers deleted.

### Round 4 — PASS

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: pandas_ta/momentum/lean_momersion_20.py:105; docs/LeanMomersion20Measured.md:93, 210-211, 238
    problem:  "the same walk rounded to 0.01" and "the walk on a 0.5 grid" are not the
              same walk. The continuous walk is `walk(1500, seed=11)`; `tick_rounded()`
              and `coarse_grid()` both wrap `walk(n, seed=55)`. So the docstring's
              "(measured: 14 distinct values over a 1,500-bar walk, 25 on the same walk
              rounded to 0.01, 87 on a 0.5 grid)" asserts a within-path effect that was
              never measured — three numbers from two unrelated paths. Same false
              identity in A4's "a continuous walk ..., the same walk rounded to 0.01" and
              in the Gate C / Gate D row and column labels. A3 (line 89) is the only
              place where it is true: there both frames are seed 5.
    fix:      Either relabel every seed-55 frame for what it is ("a second 1,500-bar
              walk, seed 55, rounded to 0.01" / "that walk on a 0.5 grid") in the module
              docstring, A4, the Gate C table and the Gate D column header, or change
              `tick_rounded`/`coarse_grid` to default to seed 11 and re-run the harness
              and the pinned counts so the sentence becomes a measurement.
  - severity: MINOR
    location: pandas_ta/momentum/lean_momersion_20.py:158-162; tests/test_lean_momersion_20.py:71-75; docs/measure_lean_momersion_20.py:584-588; docs/LeanMomersion20Measured.md:264-266
    problem:  The step that rules out fusion at g >= 2 is still not sufficient. "Since
              the factor is always above 1/2, only g = 1 can ever fuse: at 2 ulps the
              scaled gap already exceeds one ulp for every k" assumes a gap above one ulp
              forbids two exact values rounding to the same double. That holds inside a
              binade, not across one: at d = 2^m the fusion window is half the spacing
              below plus half the spacing above, 2^(m-54) + 2^(m-53) = 1.5 ulp of the
              lower binade, with ties going to the even significand d. g = 2 with a
              factor in (1/2, 0.75] gives a gap in (1, 1.5] — inside that window by the
              stated bound alone. The conclusion is still true, but by a step the text
              does not take.
    fix:      Add the step that closes it: fusing at d = 2^m needs P = k*x within half a
              lower-binade ulp of d, i.e. P/2^(m-1) >= 2 - 2^-53, and with 2^e/x > 1/2
              that forces k*2^(e-m+1) > 1 - 2^-54 — so g = 2 lands more than
              2 - 2^-53 ulp apart, past even the 1.5-ulp boundary window. Write the
              1.5-ulp boundary window down explicitly in all four copies instead of
              implying the threshold is always one ulp.
  - severity: MINOR
    location: docs/LeanMomersion20Measured.md:6 vs :196-199
    problem:  The header says "Status: Gates A–D through"; forty lines later Gate C says
              "Real data: owed. This worktree has no BIST frames." Gate C's requirement
              in CLAUDE.md is that every shipped column fires on real data with counts
              stated, so the header claims a gate the body concedes is unfinished. The
              lean_hurst_100 receipt at the same stage (12c54a1) claimed no such status.
    fix:      Make the header say what the body says: "Gates A, B and D through on
              synthetic frames; Gate C synthetic only — its real-data counts are owed
              with Gate E, run by issue-solver."
  - severity: NIT
    location: pandas_ta/momentum/lean_momersion_20.py:45-48
    problem:  "The cast is what makes a NaN pair count as False rather than propagate" is
              the wrong mechanism. `pair > 0` already yields False for NaN; by the time
              `.astype(float)` runs there is no NaN left to propagate. The cast only
              keeps the rolling sum in float.
    fix:      "The COMPARISON is what stops a NaN pair propagating -- `NaN > 0` is False,
              so an unknown pair counts neither way; the cast only keeps the rolling sum
              in float."
  - severity: NIT
    location: pandas_ta/momentum/lean_momersion_20.py:7-9
    problem:  "Below two pairs the column can only be 0, 50 or 100" — below two pairs is
              one pair, whose only values are 0 and 100; {0, 50, 100} is the value set AT
              length 2. The receipt (line 401) and the public docstring both get this
              right ("a one-pair window can only read 0 or 100"), so the module's own
              comment is the odd one out.
    fix:      "A one-pair window can only read 0 or 100, which is a flag and not a
              share."
  - severity: NIT
    location: docs/LeanMomersion20Measured.md:279-288
    problem:  The two bounds are qualified asymmetrically. x8/x64 get the overflow and
              subnormal-boundary holes spelled out; x10/x3.7 are claimed "bit-identical
              on any frame whose consecutive closes are at least 2 ulps apart" although
              they carry exactly the same two holes, and "which is every real frame" is
              an "every" about real data in a session that read no real frame.
    fix:      Carry the same parenthetical onto the x10/x3.7 clause (normal doubles,
              `k*close` not overflowing) and mark the real-frame step as what it is: an
              argument from tick size, not a measurement — "no real frame was read this
              session; the tick argument is the reason, Gate E's run is the check".
  - severity: NIT
    location: docs/measure_lean_momersion_20.py:519-521; tests/test_lean_momersion_20.py:82-84
    problem:  The persistence ordering is measured on four different innovation paths —
              `seed=40 + int(10*phi)` gives 48/44/36/32 — so the 80/60/35/20 ordering
              mixes the phi effect with four unrelated draws. And the test docstring
              bills the 50 as an "AR(1) median at phi = 0" when it comes from `_walk()`
              (sigma 0.015), not from `_ar1(phi=0)` (sigma 0.01); the receipt's table
              labels that row honestly, the test header does not.
    fix:      Use one seed for every phi (common random numbers) so the ordering is a
              controlled comparison, and say "AR(1) medians 80 / 60 / 35 / 20 at phi =
              +0.8 / +0.4 / -0.4 / -0.8, and 50 on an iid gaussian walk" in the test
              header.
  - severity: NIT
    location: docs/measure_lean_momersion_20.py:493-499
    problem:  `describe()` ends with `return s.median()` and not one of its six call
              sites uses the value. Dead return in the one script the whole receipt is
              traced to.
    fix:      Drop the `return`.
SUMMARY: Four rounds and the arithmetic finally stops moving. I re-derived both float claims rather than trusting the prose: the ratio of two distinct normal doubles cannot round to 1.0 (u/a in (2^-53, 2^-52], strictly past the midpoint), the binade factor really is confined to (1/2, 2), and only one-ulp neighbours can fuse — but your reason for that last one is STILL not the reason, because at a power of two the fusion window is 1.5 ulp, not 1, and your "exceeds one ulp" sentence walks right past it. The conclusion survives; the proof you shipped does not reach it. Then there is the sentence you have now repeated in four files: "the same walk rounded to 0.01" is a different walk — seed 55 against seed 11 — so the one causal reading a reader takes from 14 / 25 / 87 is the one you never measured. That is the house defect wearing a measurement's clothes, and it is in the shipped docstring. Everything else holds up: 104 tests pass, the harness reprints every cell of Gates A–D, the full suite lands on your exact 3 failed / 5562 passed / 83 skipped with the ledger naming exactly `['lean_momersion_20', 'mtd_ret']`, the five touch points plus 320 / 328 / 83 / 665 / 308 are all guard-tested, Gate E is owed in writing with no ledger row, and the directed probe is an honest answer to a sign-driven column instead of a shrug. Nothing here is wrong, broken or unsafe, so the gate opens on MINOR and NIT — fix the four copies of the fusion step, un-lie the "same walk", and stop calling Gate C "through" in a header your own body contradicts. Clears the bar. Barely, and only because the measurements were real this time.
```

## After the PASS

Round 4 is the loop's cap (round 1 plus three re-runs), so no fifth reviewer
was dispatched. Its three MINORs and four NITs were nonetheless applied,
because each removes a false or misleading statement rather than adding one:

1. **Every seed-55 frame is now labelled as a second walk** — in the module
   docstring, A4, A3, the Gate C rows, the Gate D column header and the
   distinct-value paragraph. The 14 / 25 / 87 comparison is explicitly
   between frames, not within one path.
2. **The fusion step is written out in full** in the receipt and the harness
   (the 1.5-ulp window at a power of two, and the extra step that rules out
   `g = 2`), and in one line in the module and test docstrings.
3. **The status header** now says Gates A, B and D through on synthetic
   frames, Gate C synthetic only with its real-data counts owed with Gate E.
4. The `count()` docstring names the comparison, not the cast; `MIN_LENGTH`'s
   comment says a one-pair window reads 0 or 100; the ×10/×3.7 bound carries
   the same two qualifications as ×8/×64 and marks the real-frame step as an
   argument from tick size with no real frame read this session; `describe()`
   lost its dead `return`.
5. **The AR(1) rows were re-measured with common random numbers** (one seed,
   40, for every φ), which changed the medians from 80/60/35/20 to
   **80/65/35/20** and their distinct/min/p10/p90/max/share cells with them.
   The Gate C table, the module docstring, the test docstring and
   `test_it_orders_persistence` were all updated to the new run.

Verification after those edits, on the main thread rather than by a fifth
reviewer: `python docs/measure_lean_momersion_20.py` reprints every changed
cell, `python -m pytest tests/test_lean_momersion_20.py -q` → **104 passed**
in 3.91 s, `python docs/gen_indicator_dictionary.py` regenerated, and
`python -m pytest -q` → **3 failed, 5562 passed, 83 skipped** in 116.10 s,
the three failures being the two `CLAUDE.md` "Known breaks" plus the owed
Gate E ledger row (`['lean_momersion_20', 'mtd_ret']`).
