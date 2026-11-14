# 99 — summary · J-GATOR (issue #104)

**Run:** `docs/reviews/auto-2026-11-14-j-gator/` · **Mode C**, one task, main
thread · **2026-11-14**

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| 01 `j-gator` | **PASS** (round 4) | 4 | `pandas_ta/momentum/j_gator.py` (new), `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_j_gator.py` (new, 137), `docs/measure_j_gator.py` (new), `docs/measure_j_gator_cpu.py` (new), `docs/JGatorMeasured.md` (new), `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`, this folder | Gate E (the launcher's run, then a receipt session records the ledger row and replaces `test_the_gate_e_row_is_owed`); Gate C's real-data limb comes with it |

## The rounds

| round | verdict | CRITICAL | MAJOR | MINOR | NIT | what it was about |
|---|---|---|---|---|---|---|
| 1 | REVISE | 1 | 3 | 3 | 1 | a fabricated citation to "jesse's `numpy_ewma`" and the unpriced `alpha = 2/(n+1)` reading; a four-module run called "green" that is red; manifest A7 describing a deleted `mid` guard; no `## Verdict` section; a vacuous Gate A limb on the `flat` frame |
| 2 | REVISE | 2 | 2 | 2 | 2 | §L falsely claiming `ICHI_TK_CROSS_AGE` "does not exist in this repo at all" — which excused not measuring the nearest in-fork comparator; the receipt and manifest still asserting jesse's `upper`/`lower`; a stale full-suite count in the Verdict table; this folder's `01`/`99` files missing |
| 3 | REVISE | 1 | 0 | 4 | 2 | the same `upper`/`lower` fabrication surviving in a fifth place (the receipt's decision log); the script's copy of a banned absolute; `ICHI_TK_DIST` dropped from the near-neighbour ranking; §G5 citing a section that did not measure finiteness |
| 4 | **PASS** | 0 | 0 | 3 | 3 | §A1's narration contradicted by the zeros under it; the "high OR LOW" infinity claim measured only on the high; a test docstring citing a Gate D test that would pass on an all-infinite column; three cosmetic |

Each round was a fresh read-only `Explore` subagent with the Fletcher persona,
given the previous rounds' findings and the claimed fixes, and told to verify
the fixes before hunting anything new. Every round re-ran
`docs/measure_j_gator.py`, the reduced-dispatch script, the module's tests and
(rounds 2–4) the full suite; all four reported every figure reproducing to the
printed digit. **Not one finding in four rounds was about the mathematics.**
All 25 were the repo's named dominant defect — a claim written before it was
measured — which is the lesson this run adds to the pile: the arithmetic was
right from round 1 and the prose took four rounds to catch up.

The recurrence is worth naming, because it is the same claim three times: a
fact about **jesse's source, which this worktree cannot read**. Round 1 struck
it as the function name `numpy_ewma`; round 2 struck it as the `upper`/`lower`
return shape in the receipt, the manifest and the script; round 3 found it
still standing in the receipt's decision log, the one place that explains WHY
the port shipped one column. Editing the strings each reviewer quoted, instead
of auditing the class of claim, cost two extra rounds. What finally closed it
was a grep for the words across every file plus renaming the script's own
locals, so the vocabulary is gone rather than hidden.

The two findings that changed the deliverable rather than its prose:

* **round 1's §A4(c)** — the `alpha = 2/(n+1)` reading of "SMMA" was never
  measured. It is a **different column** (Spearman 0.5165 … 0.7075, 0 bars in
  common), so the alpha is the load-bearing reading of the source's word and
  the seed is only a warm-up. That measurement now exists, with a test.
* **round 2's `ICHI_TK_CROSS_AGE`** — the fork DOES ship the screen's
  runner-up comparator, in `ichimoku_ml`. Measured: 0.2415 … **0.4910** over
  six frames, the largest in-fork figure, far under the 0.76 ship line and
  consistent with the screen's real-data 0.3635. The non-redundancy limb had
  a prose excuse where a 20-line measurement belonged.

## Round 4's verdict, verbatim

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/measure_j_gator.py:333-335 (and 00-manifest.md:79-82, ASSUMPTION A8)
    problem:  The script's §A1 narration asserts "`ewm` divides by `(1 - alpha) + alpha`, which is not 1.0 for
              every alpha, so an independent spelling differs in the last bits" — and then prints max |diff|
              and max |rel| of 0.000e+00 in all seven rows immediately below it. Manifest A8 states the same
              thing flatly [...]. Measured on this tree it IS bit-equal, on 10,444 of 10,444 bars, under full and reduced dispatch. The receipt's §A1
              gets this right [...]; the script and the assumption log did not get the correction. It is round 3's §G3
              finding again — prose in the evidence trail contradicted by the numbers printed under it.
    fix:      In `section_A1`, print "an independent spelling is NOT OBLIGED to round the same way; measured
              0.000e+00 here, because `(1-a) + a` is exactly 1.0 for alpha = 1/13, 1/8 and 1/5 on this
              machine". Rewrite A8's second clause [...].
  - severity: MINOR
    location: pandas_ta/momentum/j_gator.py:76 and :219-225 (docs/JGatorMeasured.md §G2/§G3, docs/measure_j_gator.py:691-731, tests/test_j_gator.py:742-762)
    problem:  The module says "an infinite high or low never reaches the output" [...] and
              §G2/§G3 are titled for high OR low. Every measurement behind those sentences perturbs `high`
              only [...]. The claim is true by the
              symmetry of `mid = (high + low) / 2`, but it is asserted as measured over a surface half of
              which was not run — the repo's named defect, one notch quieter.
    fix:      Either add the rows [...] and parametrize the test
              over which leg carries the bad value [...], or scope all four sentences to `high` and state the symmetry as a derivation.
  - severity: MINOR
    location: tests/test_j_gator.py:808 (the test at :803-813; the test it points at is :681-691)
    problem:  `test_the_cross_scale_overflow_is_disclosed_and_unguarded` justifies itself with "the same walk
              at ONE scale is finite at 1e-6, 1e+6 and 1e+100 (see the Gate D tests)".
              `test_gate_d_scale_at_extreme_price_levels` does not measure that: it asserts
              `base.notna().sum() == FIRED` and bit-equality to the ×8/×64 rescale, and an `inf` is `notna`
              and compares equal to `inf`. A column that read `inf` on all 1,492 bars at 1e+100 passes that
              test unchanged.
    fix:      Add one line [...]: `assert bool(np.isfinite(base.dropna().to_numpy()).all())`, and change :808 to cite that
              assertion [...].
  - severity: NIT
    location: docs/reviews/auto-2026-11-14-j-gator/01-j-gator.md:6-8
    problem:  "**Status:** round 2's fixes applied; round 3 dispatched and not yet returned [...]" The same file now carries round 3's verbatim verdict [...]. The status field is three states behind its own body.
    fix:      "**Status:** rounds 1–3's fixes applied; round 4 (the loop's last) dispatched [...]"
  - severity: NIT
    location: docs/measure_j_gator.py:733
    problem:  The §G4 heading reads "an all-NaN and an all-zero frame raise nothing" and the loop then prints
              three rows [...]. Two, then three; the same off-by-one genus rounds 2 and 3 both struck.
    fix:      "G4 an all-NaN, an all-zero and an all-negative frame raise nothing:".
  - severity: NIT
    location: docs/measure_j_gator.py:795-801
    problem:  `section_L` still computes the two spreads into locals named `upper` and `lower` — the exact two
              names that were fabricated as jesse's return shape in rounds 2 and 3. The printed labels were
              fixed; the variables kept the fabricated vocabulary inside the file that is supposed to be the
              evidence, which is how a struck claim finds its sixth hiding place.
    fix:      Rename to `jaw_teeth` and `teeth_lips`, matching the printed labels.
SUMMARY: Three rounds of being told you wrote claims you had not run, and this is the first time I cannot
hand you a CRITICAL. I re-ran A1 A2 A3 A4 B C D G L W Z, the reduced-dispatch A1/D, the module twice, the
four-guard process and the full suite, and every digit in the module docstring, the test docstring, the
receipt, the contract entry and the review log came back the same: 1,492 fired, 0.000e+00 on the oracle,
0 of 36 on the module and 36 of 36 on four of five mutants, 95 of 95 where the cancellation lets the fifth
show, 6.480e-10 against a 1e-7 bound, 0.4910 as the nearest fork column, 146 characters with 4 to spare,
3 failed / 8734 passed / 85 skipped with the owed list printing the eight names you typed. I checked the
things you cannot fake — `ind_screen.py:746-750` really does return one series, `candidates.csv:94` really
does say 0.3736 against `TK_Cross_Age`, `ichimoku_ml.py:39,45` really do write the pair you measured, and
pandas really does convert inf to nan at `rolling.py:408`. What is left is residue, not rot: the script's
§A1 still tells the reader that the oracle differs in the last bits directly above a table of zeros, the
"HIGH or LOW" infinity claim was only ever run on the high, and one test docstring still points at a Gate D
test that would pass on an all-infinite column. Fix those three and the sentences will finally be as honest
as the numbers have been since round 1. Ship it.
```

## ⚠ The changes no reviewer has seen

Round 4 returned PASS, and its six findings were applied **after** that
verdict, so they are the only edits in this run that no reviewer has read.
They are listed in `01-j-gator.md` under "What the six post-PASS fixes
changed". Two of them moved measurements rather than prose:

* §G2 and §G3 now run **both legs** (`high` and `low`) — four cells each.
  Measured: the low's six decay figures are the high's six, and all four
  inf-vs-NaN cells are bit-equal on 1,492 of 1,492. The test is parametrized
  over the leg, so the module went **135 → 137 tests** and the full suite
  **8,734 → 8,736 passed**.
* `test_gate_d_scale_at_extreme_price_levels` gained
  `assert np.isfinite(...).all()`, and §D(c) of the script prints a `finite`
  column, so §G5's "one scale is fine" rests on a measurement instead of a
  cross-reference that could not carry it.

Everything re-run after those edits: `137 passed` plain and `137 passed`
under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, full suite
`3 failed, 8736 passed, 85 skipped` with the three being `dev`'s
clean-checkout failures (`docs/JGatorMeasured.md` §F1).

## What is NOT in this run

* **Gate E.** The launcher runs `gate_e_overlap.py`; this session never read
  `../Backtesting`. `docs/JGatorMeasured.md` §E says pending, and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  is red by design, reporting `j_gator` among eight owed indicators.
* **Gate C's real-data limb**, which comes with that run.
* **A Codex review.** The owner's pre-push rule asks for one BHR and one
  Codex review; `codex` is not an allowed command in this headless session
  (the shell is restricted to `python -m pytest`, `python docs/…` and read-only
  `git`), so only the BHR loop ran. The launcher's reviewer is the second eye.
