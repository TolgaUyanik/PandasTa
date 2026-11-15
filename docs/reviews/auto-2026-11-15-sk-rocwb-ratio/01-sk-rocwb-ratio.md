# Task `sk-rocwb-ratio` — log and review rounds

Port `sk_rocwb_ratio`, the 20-bar ROC over the root mean square of its own last
5 readings (PandasTa issue #109, Skender Stock.Indicators' `RocWb`, Apache-2.0),
through Gates A–D, the five wiring touch points, tests and
`docs/SkRocwbRatioMeasured.md`. Gate E and both repos' suites are the launcher's.

## Implementation

    ROC[T]              = 100 * (close[T] / close[T - 20] - 1)
    band[T]             = sqrt(mean(ROC[T - 4 .. T]^2))
    SK_ROCWB_RATIO_20_5 = ROC[T] / band[T]          (+-inf -> NaN)

The decisions that were not mechanical, each measured rather than argued:

1. **The band is an RMS, so the column is BOUNDED to +-sqrt(band_length).**
   `roc[T]` is one of the terms of its own denominator. Measured attained to 0
   ulps by a hand frame and 0 bars over the bound on every synthetic frame — this
   is the column's defining property and the receipt leads with it (§C2).
2. **The ROC keeps the prototype's spelling** rather than importing
   `pandas_ta.roc`, which spells it `100 * mom / close.shift`. §A3 measures the
   gap at 4.007e-12 relative, Spearman 1.0000 — too small to move a Gate E figure,
   so the override of the repo's import-the-helper rule is for PROVENANCE (the
   port is then the screened expression bit for bit) and is logged as ASSUMPTION
   2. Round 1 caught the first draft dressing this up as numerical risk.
3. **An `isfinite` mask is added**, diverging from the prototype, on §G2's
   evidence: without it an infinite close leaves five bars reading plausible
   numbers (-2.2216 against a clean 0.4980) instead of a gap. Bit-identical to the
   prototype on finite input, so the Gate E tie survives.
4. **The `+-inf -> NaN` fold is kept although §G3 measures it dead**, because
   removing it would change the shipped expression with no measurement behind it.

Files: `pandas_ta/momentum/sk_rocwb_ratio.py`, `tests/test_sk_rocwb_ratio.py`
(186 tests), `docs/measure_sk_rocwb_ratio.py` (16 sections: the source of every
figure quoted anywhere except the receipt's §E, which are the SCREEN's figures
on the prototype, and Gate F's, which are the pytest runs named there),
`docs/measure_sk_rocwb_ratio_cpu.py`,
`docs/SkRocwbRatioMeasured.md`, plus the five wiring touch points and the four
count-bearing documents.

Runs: `python -m pytest tests/test_sk_rocwb_ratio.py -q` → 186 passed;
`python docs/measure_sk_rocwb_ratio_cpu.py` → the same 186 under numpy's
`AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled; `python -m pytest -q` →
3 failed, 9711 passed, 85 skipped (the two known breaks plus the owed Gate E row).

## Review round 1 — VERDICT: REVISE

Verbatim findings (2 MAJOR, 5 MINOR, 2 NIT):

* **MAJOR** `docs/SkRocwbRatioMeasured.md` Gate C — CLAUDE.md defines Gate C as
  "every shipped column fires on **real data**, with counts stated". Every count
  was synthetic and the receipt never said so, while invoking FVGDEAD by name
  three times — naming the lesson without spending it. Issue #108's receipt opened
  with that disclosure; this one deleted it.
  *Fix:* a numbered ASSUMPTION stating the real-data limb is owed to the receipt
  session, naming the number it must fill in, mirrored at the head of §C.
* **MAJOR** `sk_rocwb_ratio.py` / §A3 — "That is the **entire** reason this module
  does its own two lines" and "keep the Gate E tie exact" correspond to no run and
  are contradicted by §E and by the ledger's own fingerprint rule; a 4e-12 move at
  Spearman 1.0000 cannot shift a rho reported to four decimals.
  *Fix:* rewrite to what the measurement supports (provenance, not numerical
  risk) or import `roc` and re-run §A1–§A3.
* **MINOR** docstring A1/A2 ranges — "is NOT bit-equal ... 102 .. 1,082 bars per
  frame" silently drops `flat`, which is bit-equal. *Fix:* scope to the firing
  frames.
* **MINOR** §B2 — "1,475 of 1,475 on the continuous frames (1,474 on `grid`)"
  conflates the two mutants: `band-lead` is 1,474 on `grid`, `band-centred` 1,475,
  which is why the totals differ. *Fix:* split the sentence per mutant.
* **MINOR** Gate D — "2^-20, 2^20, 2^300 bit-identical on every fired bar of all
  eight frames" was never run that way: the harness ran them on `walk` only and
  the test omitted 2^20 entirely. *Fix:* sweep all three over all eight frames and
  add 2^20 to the test.
* **MINOR** §C2 — the "over the bound" count carries 1e-12 of slack while the
  prose and the `Returns:` line read strict. *Fix:* print both counts.
* **MINOR** `_exposed_band_lead` — guards `i >= LENGTH` where the bar needs
  `i + 1 >= WARMUP`; the condition's exactness was an artefact of the sweep
  starting at offset 25. *Fix:* tighten the guard or say the exactness is
  range-bound.
* **NIT** `test_the_source_library_is_not_readable_here` — `__import__("Stock")`
  can never succeed for a NuGet package, so that limb is decoration, and the
  rglob walks `.git`. *Fix:* pruned walk for `*.cs` / `*.pine`.
* **NIT** the cost sentence miscounts the operations.

All nine applied. The B2 sweep was re-run over the full offset range 1..1,499
(11,992 offsets), which moved its totals to 9,883 / 10,034 exposed, still 0
caught-outside and 0 exposed-but-missed; the test count went 178 → 186 with the
added 2^20 rows.

## Review round 2 — VERDICT: REVISE

Seven of nine round-1 items verified landed by re-running every section. New
findings (2 MAJOR, 4 MINOR, 2 NIT):

* **MAJOR** `docs/measure_sk_rocwb_ratio.py` §A3 preamble — the repudiated
  justification was still PRINTED BY THE HARNESS ("the import would be a different
  column ... the difference is largest exactly where the ratio is smallest"), so
  the receipt and its own generator contradicted each other, and the second half
  was a brand-new unmeasured correlation. The test module header repeated it.
  *Fix:* both rewritten to the provenance wording; the unmeasured superlative
  deleted outright rather than kept and hedged.
* **MAJOR** `sk_rocwb_ratio.py` Gate C paragraph — "on seven of the eight frames
  every bar from 24 on fires (1,476 of 1,500)": §C measures that on SIX frames
  (`coarse` fires 1,370), and the docstring contradicted itself seven lines later.
  *Fix:* "on SIX of the eight frames ... the 2.0-tick frame fires 1,370 and a flat
  price 0".
* **MINOR** 343 vs 449 — the zero-NUMERATOR argument cites 343 (bars reading 0.0)
  in five places where the right quantity is 449 (bars with a zero ROC; 449 = 343
  + the 106 blanked). *Fix:* 449 wherever the sentence is about the numerator,
  343 only where it is about output zeros.
* **MINOR** §B2 prose — "on the five continuous frames and on `jump`" names six
  frames and does not sum to the 9,883 in the table above it. *Fix:* name the
  frames and check the sum.
* **MINOR** the two header universals — "No real-data figure in this file" is
  false of §E (a real-data rho, the prototype's) and "Every number below is
  printed by the harness" is false of §E and Gate F. *Fix:* scope both.
* **MINOR** ASSUMPTION 5 — two of the three owed numbers come from the ledger row,
  the third (`close[T] == close[T-20]`) does not, so as written the owed limb is
  defined around a figure its owner may not be able to produce. *Fix:* name each
  number's source and give the lower bound the row does supply.
* **NIT** the cost sentence still omitted the square, the multiply and the
  subtract. *Fix:* enumerate completely or stop enumerating.
* **NIT** the manifest promises `01-...md` and `99-summary.md`, neither present.
  *Fix:* write them before the commit.

All eight applied.

## Review round 3 — VERDICT: PASS

Four findings, no MAJOR, all applied:

* **MINOR** `sk_rocwb_ratio.py` / §C2 — "the frame that **attains** the bound is
  the 2.0-tick one" rested on `closest 1.0000`, a four-decimal ratio that
  `0.99995` also prints; the harness showed an ulp distance only for the hand
  frame. *Fix applied:* `section_C2` now prints `max |x|`, `math.sqrt(5)` and the
  ulp distance for every frame whose `closest` rounds to 1.0000. `coarse` is
  **0 ulps**, so "attains" is now measured; the receipt and the docstring cite
  that instead of the rounded ratio.
* **MINOR** `tests/test_sk_rocwb_ratio.py` — the comment "the six frames with no
  exactly-zero ROC" is false of `grid`, which §C4 measures at one such bar, and
  the receipt says so in §B2. The constant was right and its stated reason was
  wrong, which is worse, because a later reader reuses the reason. *Fix applied:*
  the comment now says "the six frames where every bar after the warm-up fires"
  and names `grid`'s zero-ROC bar.
* **NIT** §G1 — "0.0 and 1e-310 empty 720 .. 724" named a window the harness
  printed for only three of the seven plants. *Fix applied:* the emptied-bar list
  is printed for all seven; `1e-310` does empty 720 .. 724 and `-1.0` empties
  nothing.
* **NIT** the manifest promised `99-summary.md`, which did not exist. *Fix
  applied:* written.

## Review round 4 — VERDICT: PASS (confirmation)

Round 3's PASS was not taken as final, because four fixes landed after it. Round
4 re-ran the same reviewer against the fixed tree and returned PASS with three
MINOR and one NIT, none of them about a number in the column:

* **MINOR** `99-summary.md` had pre-filled round 4's row before round 4 ran — the
  session's own dominant defect turned on its review record. *Fix applied:* the
  row now quotes what round 4 actually returned.
* **MINOR** this file said the harness has "15 sections" (it has 16) and called it
  "the only source of any figure quoted anywhere", the unscoped universal round 2
  killed in the receipt header. *Fix applied:* 16, and scoped.
* **MINOR** the manifest calls this file "every review round, verbatim" while it
  stopped at round 2. *Fix applied:* rounds 3 and 4 are above.
* **NIT** the docstring's Gate B paragraph described the two band mutants three
  times without naming them, in two different orders, so pairing by position gave
  the wrong figures. *Fix applied:* both are named, one order, every figure
  labelled.
* ⚠ Round 4's own disclosure, kept because it bears on how strongly this is
  verified: that reviewer's sandbox allowed only `python -m pytest`, so it could
  not execute the harness or the reduced-CPU re-run, and verified the new §C2 and
  §G1 blocks by reading their source against the quoted text. Rounds 2 and 3 did
  execute them. Both were re-run in this session after the round-4 fixes.
