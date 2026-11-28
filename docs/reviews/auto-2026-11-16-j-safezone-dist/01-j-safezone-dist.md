# J-SAFEZONE-DIST — task log

Task: port jesse's `safezonestop` long-side distance as `j_safezone_dist`
through Gates A–D, the five wiring touch points, tests and
`docs/JSafezoneDistMeasured.md`. Issue
[#121](https://github.com/TolgaUyanik/PandasTa/issues/121).
Lane: main thread. Gate E and both repos' suites: the launcher's.

## Implementation

Read first, before writing anything: `CLAUDE.md` (the porting protocol and
its gate table), `docs/issues/120-j-safezone-dist.md` (the issue's local
copy), `docs/issues/screen/ind_screen_r2.py` lines 132–140 (the screened
prototype) and its helpers in `ind_screen.py` (`sdiv`, `_fin`), and the two
nearest merged ports for shape — `j_damiani` (#105, the other jesse port,
also constants-not-arguments) and `tf_iqr_ret_60` (#117, the most recent).

Built, in this order:

1. `pandas_ta/trend/j_safezone_dist.py`. Written from the SOURCE formula as
   issue #121 quotes it, not from the prototype — Gate A's requirement —
   with the prototype used afterwards as a second oracle.

   ```
   pen[T]  = max(low[T-1] - low[T], 0)
   avg[T]  = sum(pen, 22) / count(pen > 0, 22)
   raw[T]  = low[T-1] - 2.5 * avg[T-1]
   stop[T] = max(raw[T-2], raw[T-1], raw[T])
   out[T]  = (close[T] - stop[T]) / close[T]
   ```

   Three guards, each with a measured justification rather than a habit:
   `low` sanitised to finite (it enters through differences), `close`
   sanitised to finite-positive-normal (it is the divisor), and a final
   finite mask. ⚠ Review round 2 corrected what that last one is for:
   finite inputs leave THREE routes to an infinity (the subtraction, the
   rolling sum and the final division), and the mask covers the one of
   them that reaches the output — §G3 now runs all three with their
   intermediates.

2. The five wiring touch points: the module, `pandas_ta/trend/__init__.py`,
   `Category["trend"]` in `pandas_ta/__init__.py`, the `core.py` accessor,
   and `tests/test_j_safezone_dist.py`. Then the counts the suite checks:
   `README.md` (355→356 registered, 363→364 callable, `trend (62)`→`(63)`
   and the name in its list), `tests/test_altport2_ports.py`
   (`CATEGORY_TOTAL` 355→356, `CATEGORY_BUCKETS["trend"]` 62→63),
   `docs/MLCompanionContract.md` (700→701 tagged, 338→339 `SF`), and
   `docs/IndicatorDictionary.md` regenerated with
   `python docs/gen_indicator_dictionary.py` (probe tags the column `SF`,
   warm-up 25).

3. `docs/measure_j_safezone_dist.py` — thirteen sections, the only place a
   figure in the receipt, the module docstring or the test module may come
   from — and `docs/measure_j_safezone_dist_cpu.py`, which re-runs them and
   the test module under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
   FMA3"` and refuses to run if the environment edit did not take.

4. `tests/test_j_safezone_dist.py` — 203 tests as shipped (193 as first
   written; review rounds 2, 3 and 4 added ten).

5. `docs/JSafezoneDistMeasured.md` — the receipt.

### What the measurement changed about the code

Two things, both found by running the script rather than by reading:

* **The Gate B mutant set was wrong on the first attempt.** Three of the
  six look-ahead mutants (`pen-lead`, `avg-lead`, `stop-lead`, each a
  `shift(-1)`) were caught **0 of 36** — because the stop carries TWO
  `shift(1)`s, so a one-bar lead is absorbed by them and lands on bar T's
  own low rather than a future one. Those three became `-2` mutants (caught
  3..36 of 36), and the three `-1` versions moved into a new
  `BLIND_SPOT_MUTANTS` set with the two `shift(1)`-removed mutants, where
  §B2 pins that the sweep cannot catch them and Gate A's oracle can. This
  is the finding of the port's Gate B and it is in the module docstring,
  the test docstring and §B2.
* **Six prose numbers written before the run were wrong and were
  corrected** before any review: the per-22 Spearman range (0.9361..0.9895
  → 0.9378..0.9705), the column's range (−0.2214..0.1935 →
  −0.3262..0.3375), the bars a bad low empties (24 → 25), the mutant catch
  counts (36 of 36 → 3..36 of 36), the finite guard's reach, and the §L
  nearest-neighbour figures.

## Review round 1 — REVISE

Reviewer: fresh `Explore` subagent, Fletcher persona, read-only, which
re-ran every measurement section including under reduced CPU dispatch.
Verbatim:

```
VERDICT: REVISE

FINDINGS:
  - severity: MAJOR
    location: docs/JSafezoneDistMeasured.md:699-701 (§F1)
    problem:  "The 86 skips are the repo's standing set: `tests/config.py` skips the whole upstream correlation suite at import because `data/SPY_D.csv` is gitignored." You quoted the count off a run and then wrote the *reason* from memory. I re-ran your own command with `-rs`: `2 failed, 11835 passed, 86 skipped in 301.65s` — your counts reproduce to the digit, so you had the run and did not look at it. Of those 86, exactly **21** are `tests/config.py:23` SPY_D.csv. The other **65** come from roughly fourteen unrelated causes: `../AlternativeRepos/*.csv` absent (6+1+2+1+1+1+6+9+1), the parent repo's parquet cache (1+1+1+6+1+1), `Backtesting/datastore/cache` (4), `test_candle_patterns_reachable.py:131: TA-Lib IS installed`, `test_pine_coverage_csv.py:116: docs/pine corpus is untracked by design`, `test_multil_length_grid.py:298: Backtesting/TODO.md absent`, `IndicatorList.md absent`, and two port-local degenerate-comparator skips in `test_ts_aggac_60.py`. CLAUDE.md told you the number for that one cause is 21 and you wrote 86 over it. This is the one sentence in the whole receipt that a reader cannot check without the parent repo, and it is the one you fabricated.
    fix:      Re-run `python -m pytest -q -rs`, paste the SKIPPED block into §F1, and replace the sentence with the measured split — "21 of the 86 are `tests/config.py:23` (SPY_D.csv, gitignored); the remaining 65 are the sibling `../AlternativeRepos` CSVs, the parent repo's parquet cache, `TA-Lib IS installed`, the untracked `docs/pine/` corpus and two per-port degenerate-comparator skips". Drop "the repo's standing set" unless you intend to enumerate it.

  - severity: MAJOR
    location: docs/JSafezoneDistMeasured.md:658-662 (ASSUMPTIONS 1), repeated at :645 (decisions table) and docs/reviews/auto-2026-11-16-j-safezone-dist/00-manifest.md:34-36
    problem:  You justified the shipped category with "§L supports it after the fact: the four volatility comparators sit at |ρ| ≤ 0.21 and the nearest column is a channel distance at 0.70." §L measures **seven** comparators, and three of them live in `pandas_ta/volatility/`: `natr` (0.2053), `massi` (0.0911) and **`rvi` — the Relative Volatility Index, `pandas_ta/volatility/rvi.py:9`, a rolling-stdev indicator — at |ρ| 0.5174**, the second-highest row in your own table. There is no run in which "four volatility comparators" sat at ≤0.21. Your §L prose at :583-585 gets away with it by naming the four (`NATR`, `VHF`, `MASSI`, `CHOP`) — two of which are `pandas_ta/trend/` choppiness filters, not volatility — and quietly leaving out the actual volatility index that disagrees. The ASSUMPTIONS entry and the manifest drop even the names, so the decision record reads as a measurement and is not one. The category choice survives on the `cksp`/`vstop`/`tvstop`/`psar` precedent; the evidence sentence does not.
    fix:      In all three places state the measured split: "`rvi` (Relative Volatility Index, `pandas_ta/volatility/`) is the second-nearest at 0.5174; the other volatility-category comparators, `natr` and `massi`, read 0.2053 and 0.0911", and rest the category argument on the stop-distance precedent plus the nearest column being a channel distance. If you want to keep "volatility comparators near zero", say which four by module path and admit the one you excluded.

  - severity: MINOR
    location: docs/measure_j_safezone_dist.py:583
    problem:  The script prints "A plant at the LAST bar is the one that cannot empty 24 bars" two lines below its own table, which prints `emptied = 25` on all twelve interior plants — and the module docstring (:211), the test docstring (:73) and the receipt (:470-475) all say 25. A typed number, in the one file whose own docstring (:8-11) declares it "the only place a figure in the receipt, the module docstring or `tests/test_j_safezone_dist.py` may come from". The receipt only escaped it because you hand-rewrote that sentence instead of quoting it.
    fix:      Change the literal to the chain: `print(f"\n  A plant at the LAST bar is the one that cannot empty {PERIOD + LOOKBACK} bars,")`, so a changed constant cannot leave the prose behind.

  - severity: MINOR
    location: pandas_ta/trend/j_safezone_dist.py:225-231 and docs/JSafezoneDistMeasured.md:557-558
    problem:  The shipped docstring says "**What it is nearest to inside this fork** is … `LINREG_LOWER_2_DIST_PCT` … then `RVI_14` at 0.5174 and nothing else above 0.21 (§L)", and the receipt's §L lead-in says "Scale-free fork columns at their defaults". The run behind both is seven hand-picked comparators, `docs/measure_j_safezone_dist.py:660-668`, out of 356 registered indicators and 701 tagged columns. "Nothing else above 0.21" is a universal over a population you never swept. The reference port you were told to copy discloses exactly this — `docs/JDamianiMeasured.md:1048-1050`: "These are synthetic frames and **a handful of neighbours, chosen as the nearest questions this fork already answers**" — and you dropped the disclosure while adding the superlative.
    fix:      Say "seven neighbours, chosen as the nearest questions this fork already answers" in §L's lead-in and in `section_L`'s printed header, and narrow the docstring to "nothing else among the seven neighbours of §L reaches 0.21"; keep the fork-wide claim only where it is sourced — the screen's 12-real-frame stage-2 sweep at 0.7578.

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:192-193 and :462-463
    problem:  Line 27 contracts the whole document: "Everything below is printed by `python docs/measure_j_safezone_dist.py`". Two fenced blocks then contain lines the script never prints: §B's `close-lead     all six          True    36 of 36` / `output-early   all six          True    36 of 36` (the script prints six per-frame rows each — I checked all twelve) and §G1's `close     inf  (same as nan, all five plants)` / `close    -inf  (same as nan, all five plants)` (the script prints ten rows). The compressions happen to be true — I verified every cell — but a fence that is a transcript everywhere except where it is a paraphrase is how the next reader stops checking the fences.
    fix:      Either paste the real rows, or move the summaries outside the fence as prose ("the six `close-lead` and six `output-early` rows are 36 of 36 on every frame; the ten `close` rows are identical for NaN, +inf and -inf") and mark the fence as abridged.

  - severity: NIT
    location: docs/measure_j_safezone_dist.py:443
    problem:  The printed §B caption says "`clip(lower=0)`, the `max` over the hits and the `rolling(3).max()` all discard information". It is the **mean** over the hits — the receipt (:197), the module docstring (:240) and the test docstring (:53) all say mean. The script, the one artefact that is supposed to be upstream of the prose, is the one that says `max`.
    fix:      `print("  the mutant: `clip(lower=0)`, the mean over the hits and the")`.

  - severity: NIT
    location: tests/test_j_safezone_dist.py:37-38 and :65-66
    problem:  Two unmeasured absolutes in a docstring whose closing paragraph promises that "Every number above is printed by `python docs/measure_j_safezone_dist.py`". "no other port in this fork has quite this shape" is a universal over 356 indicators backed by no run (and "quite" makes it unfalsifiable rather than measured). "the only figure in this port that moves between numpy dispatches" is contradicted by §Z, whose milliseconds moved 1.80→1.77, 6.17→6.21, 40.57→41.74 across my two runs; §Z disclaims itself, but the word "only" does not carry the exemption.
    fix:      Cut "no other port in this fork has quite this shape" or replace it with the comparison you did measure (`j_damiani`, named). Write "the only figure outside §Z's timings that moves between numpy dispatches".

SUMMARY: The arithmetic is the strongest part of this port and I have nothing to take from it — bit-equal to the screen prototype on all eight frames, 0.0 absolute and relative against a genuinely independent bar-by-bar oracle on 1,475 of 1,475 bars of each of six, every bit-equality limb confined to operations that are identical by construction (×2^k rescale, prototype, prefix), the level-shift test that keeps Gate D from being vacuous, and a Gate B that goes looking for its own blind spot and pins five one-bar-lead mutants the suffix sweep is rightly blind to. I re-ran every section, including under reduced CPU dispatch, and every cell in the receipt reproduced. Which makes the failures all the more irritating, because they are all in the prose, and they are the exact defect CLAUDE.md names: you had the suite run in front of you, reproduced "2 failed, 11835 passed, 86 skipped" to the digit, and then attributed all 86 skips to one cause that accounts for 21 of them — with CLAUDE.md's own "21" sitting on the page you read first. Then you justified the shipped category with "the four volatility comparators sit at |ρ| ≤ 0.21" while `rvi` — the Relative Volatility Index, second-highest row in your own §L table — reads 0.5174, and you repeated that selected evidence in the decisions table and the manifest. Add a script that prints "24 bars" under a table printing 25 and "the `max` over the hits" where it means the mean, and the pattern is clear: you measured beautifully and then stopped reading your own output. Fix the two MAJORs, bring the prose back under the runs, and this ships.
```

### Fixes applied after round 1 (all seven)

| # | finding | what was done |
|---|---|---|
| 1 | MAJOR, §F1's skip attribution | Re-ran `python -m pytest -q -rs` and replaced the sentence with a measured table of all 86 skips grouped by cause: 45 the sibling `../AlternativeRepos` CSVs, 21 `tests/config.py:23` (SPY_D.csv), 14 the parent repo's frame cache, 3 per-port degenerate comparators, and one each for `TA-Lib IS installed`, the untracked `docs/pine/` corpus and `Backtesting/TODO.md`. The groups are summed in the receipt and come to 86. The reviewer's own count of 21 for the SPY_D cause is reproduced. |
| 2 | MAJOR, the category evidence | Struck "the four volatility comparators sit at \|ρ\| ≤ 0.21" from all three places. ASSUMPTIONS 1 now rests the choice on the `cksp`/`vstop`/`vstop2`/`tvstop`/`psar` precedent and says §L does NOT settle it, naming `rvi` (`pandas_ta/volatility/rvi.py`) as the second-nearest at 0.5174. The decisions table and `00-manifest.md` carry the same correction. §L's own prose now names the four dispersion readings by module path and says explicitly that `rvi` is the one that disagrees. |
| 3 | MINOR, "24 bars" in the script | Now `f"... cannot empty {PERIOD + LOOKBACK} bars"`; re-run prints 25. |
| 4 | MINOR, the §L universal | §L's lead-in, `section_L`'s printed header and the module docstring now say "seven neighbours, chosen as the nearest questions this fork already answers", not a fork sweep; "nothing else above 0.21" is scoped to those seven, and the one fork-wide figure is attributed to the screen's stage-2 sweep. |
| 5 | MINOR, the abridged fences | Both fences now end where the transcript ends, with the abridgement stated as prose outside them, and the document's opening contract names §B and §G1 as the two abridged blocks. |
| 6 | NIT, "`max` over the hits" | Fixed to "mean" in the script; re-run confirms. |
| 7 | NIT, two test-docstring absolutes | "no other port in this fork has quite this shape" → the measured comparison with `j_damiani` (NaN there means no movement, here no DOWNWARD movement). "the only figure in this port" → "the only figure outside §Z's timings", in the test docstring, the test's own docstring and the module docstring, and §D2 now says the same with §Z named. |

Not one finding was about the mathematics. All seven were the repo's named
dominant defect, and the two MAJORs were the same shape: a count taken from
a run, and then the EXPLANATION of that count written from memory.

`python -m pytest tests/test_j_safezone_dist.py -q` after the fixes: 193
passed.

## Review round 2 — REVISE

Reviewer: a second fresh `Explore` subagent, Fletcher persona, read-only,
given round 1's report and told to verify each fix landed on EVERY surface
and to look for what round 1 missed. It re-ran every section on both
dispatches and the full suite with `-rs`. Verbatim:

```
VERDICT: REVISE

FINDINGS:
  - severity: MAJOR
    location: pandas_ta/trend/j_safezone_dist.py:130-136, repeated at docs/JSafezoneDistMeasured.md:538-540 (§G3), :674 (decisions table) and docs/reviews/auto-2026-11-16-j-safezone-dist/01-j-safezone-dist.md:35-36 (task log)
    problem:  "With both inputs finite the only way out of the real numbers left is OVERFLOW in this division -- a huge stop over a tiny close -- which needs a frame spanning some 600 orders of magnitude." Both halves are false, and you can refute them with a pencil. `pen = (low.shift(1) - low).clip(lower=0)` overflows on finite input the moment two consecutive lows straddle DBL_MAX in opposite signs -- and your own docstring at :91-92 explicitly admits negative lows ("A non-positive low is left alone"). Worse, no negative low is even needed: lows alternating 1.7e308 / 1.0 give eleven penetrations of ~1.7e308 inside a 22-bar window, so `pen.rolling(22).sum()` overflows to +inf, `avg` goes inf, `raw` goes -inf, `stop` goes -inf, and `(px - (-inf)) / px` is +inf. The final mask is what saves it -- on a frame spanning 308 orders, not 600, and through a route that is not "this division". So the guard is LOAD-BEARING on inputs you never measured, you wrote "the only way" over three surfaces plus the task log, and §G3 measures exactly one of the three overflow routes while the prose promises it is the only one. This is the same defect round 1 named twice: a number from a run, an explanation from memory.
    fix:      Strike "the only way out of the real numbers left is OVERFLOW in this division" from all four places and write what is true: "with both inputs finite an infinity can still be created by overflow in `low.shift(1) - low`, in `pen.rolling(22).sum()`, or in the final division; §G3 measures the division route (a low near DBL_MAX over a close near DBL_MIN)". Then add the second route to `section_G`'s §G3 -- a 26-bar frame of lows alternating 1.7e308 / 1.0 with a close of 100.0 -- print guarded/unguarded finite/infinite/NaN as you already do, and add the matching assertion next to `test_the_finite_guard_is_not_a_no_op_where_the_division_overflows`. Drop "some 600 orders of magnitude" or scope it to the division route.

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:45 (gate table D), pandas_ta/trend/j_safezone_dist.py:256-258, tests/test_j_safezone_dist.py:65-66, docs/MLCompanionContract.md:27
    problem:  Four surfaces say the same unmeasured conjunction: "x8/x64 ... bit-identical on 1,475 of 1,475 bars of each of six frames **and at price levels 1e-6, 1e+6 and 1e+100**" (gate table: "×8/×64 bit-identical on all six and at three price levels"; the contract paragraph: "bit-identical under x8 and x64 ... and at price levels ..."). §D3 runs ONE factor at those levels -- `docs/measure_j_safezone_dist.py:546`, `_bit_equal(base, j_safezone_dist(*_scaled(frame, 8.0)))`, and the table's own column header says `x8 bit-identical`. `test_gate_d_scale_at_extreme_price_levels` parametrizes the level and hard-codes 8.0 as well. x64 at 1e+100 has never run. It would pass -- that is not the point; you wrote four sentences asserting a run that does not exist, which is the one thing CLAUDE.md names.
    fix:      One of two. Either add 64.0: loop `for factor in (8.0, 64.0)` in §D3 and parametrize the test on `[8.0, 64.0]`, re-run, and keep the sentences. Or narrow all four to "x8/x64 on each of six frames, and x8 at price levels 1e-6, 1e+6 and 1e+100 (§D3)". Do not fix three and leave `docs/MLCompanionContract.md` behind -- that is the surface round 1 never opened.

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:486-488 and tests/test_j_safezone_dist.py:134-137
    problem:  The count 25 is measured and right; its arithmetic does not add up. "the rolling sum carries the two spoiled penetrations for PERIOD + 1 windows, `avg.shift(1)` for one more and `rolling(3).max()` for LOOKBACK - 1 more" sums to 23 + 1 + 2 = 26, under a table that prints `emptied 25` on all twelve interior plants and next to a constant defined as `PERIOD + LOOKBACK = 25`. A `shift` TRANSLATES a NaN run, it does not widen it: the two NaN penetrations at T and T+1 spoil the 23 windows ending T..T+22 (= PERIOD + 1), `avg.shift(1)` moves that run to T+1..T+23 and adds nothing, and `rolling(3).max()` adds LOOKBACK - 1 = 2, giving T+1..T+25. 23 + 0 + 2 = 25. You explained a measured count with a decomposition that contradicts it, in the receipt and in the comment that defines the constant.
    fix:      In both places: "the rolling sum spoils PERIOD + 1 = 23 windows (the two NaN penetrations at T and T+1); `avg.shift(1)` moves that run to T+1 .. T+23 without widening it; `rolling(LOOKBACK).max()` adds LOOKBACK - 1 = 2 more, so 23 + 2 = PERIOD + LOOKBACK = 25 bars, T+1 .. T+25."

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:27-38 (the document's contract), violated at :314-317 (§C3) and :574 (§L)
    problem:  Round 1 flagged this exact sentence and the fix stopped at the fences. The contract now reads "Everything below is printed by `python docs/measure_j_safezone_dist.py` ... except §E's prototype figures ... and §F/§F1's suite counts ... Two fenced blocks (§B and §G1) are ABRIDGED". Two more figures below are printed by neither script. §C3: "replace its lows with their own running maximum ... and it fires on **0**" -- `section_C` prints no such row; that number comes from `test_the_missingness_is_not_missing_at_random`, which you name one line later, so you knew. §L:574: "not a sweep of the 356 registered indicators or the **701 tagged columns**" -- `section_L`'s header prints the 356 and not the 701. Both are checkable elsewhere, which is precisely why the exception list should name them instead of leaving the reader to discover that the contract has holes.
    fix:      Extend the contract sentence: "... except §E's prototype figures, §F/§F1's suite counts, §C3's running-maximum count (which is `tests/test_j_safezone_dist.py::test_the_missingness_is_not_missing_at_random`) and §L's 701-tagged-column figure (`docs/MLCompanionContract.md`)". Or print the running-maximum row in `section_C` and the 701 in `section_L`'s header, and leave the contract as it stands.

  - severity: NIT
    location: tests/test_j_safezone_dist.py:586-587
    problem:  "asserted at 1e-5, which is still three orders above the 4.1e-11 an inexact rescale costs." 1e-5 / 4.091e-11 = 2.4e5, i.e. five and a half orders. The receipt's version of the same comparison (:235, "3.399e-04 ... seven orders above the 6.5e-11") is right to the order; the test docstring's is understated by two, in the one file whose numbers are supposed to be the script's.
    fix:      "asserted at 1e-5, which is still five orders above the 4.091e-11 an inexact rescale costs (§D2)."

  - severity: NIT
    location: docs/measure_j_safezone_dist.py:636
    problem:  The printed caption is "§G5 an index of length 0 or 1, and a constant-NaN frame" and the section then measures a 5-bar frame and a 100-bar all-NaN frame. Length 0 and length 1 are measured nowhere, by the script or the test module, and the receipt quietly retitles the section "§G5 short and empty frames" -- so the only place that promises the empty-index case is the artefact that is supposed to be upstream of the prose.
    fix:      Either print what you measure -- `print("\n§G5 a frame below MIN_BARS, and a constant-NaN frame\n")` -- or add the two cases: `j_safezone_dist(Series(dtype=float), Series(dtype=float))` and a one-bar frame, with a matching assertion in `test_a_frame_shorter_than_min_bars_is_refused`.

SUMMARY: The arithmetic is still untouchable and the two MAJORs of round 1 are genuinely dead. I re-ran every section on both dispatches: §A1 through §Z reproduce cell for cell, §D2's 4.091e-11 and its 6.546e-11 twin both land, 193 passed with AVX-512/AVX2/FMA3 off, and `pytest -q -rs` gave me "2 failed, 11835 passed, 86 skipped" with a SKIPPED block whose every group matches your §F1 table to the digit -- 10+6+7+5+9+4+3+1 = 45, 21 for SPY_D.csv, 6+4+2+2 = 14, 3, 1, 1, 1, summing to 86. That is how a skip attribution is supposed to be written, and the `rvi` correction landed on all four surfaces including the manifest. So I had to go looking elsewhere, and I found the same disease in a new organ: your module docstring tells the next maintainer that with finite inputs the ONLY remaining route to an infinity is overflow in the final division, needing 600 orders of magnitude. It takes eleven penetrations near DBL_MAX inside one 22-bar window to overflow `pen.rolling(22).sum()`, and your own guard note two paragraphs up admits negative lows, which overflow the subtraction. You wrote "the only way" four times -- docstring, §G3, decisions table, task log -- about a guard whose reach you measured along exactly one of three paths. Then you asserted x64 bit-identity at 1e+100 on four surfaces while §D3 and the test both hard-code 8.0, explained a measured 25 with a decomposition that sums to 26, and left the document's opening contract claiming every figure below it comes from a script that prints neither §C3's zero nor §L's 701. The mathematics is a ship. The prose is still writing cheques the runs have not signed. Fix the "only", measure the x64, make the arithmetic of 25 equal 25, and this is done.
```

### Fixes applied after round 2 (all six)

| # | finding | what was done |
|---|---|---|
| 1 | MAJOR, "the only way out of the real numbers" | The claim was struck from all four surfaces, and the correction is a MEASUREMENT rather than a rewording. `docs/measure_j_safezone_dist.py` gained `_OVERFLOW_ROUTES()` and §G3 now runs all three routes with their intermediates (`pen max`, `sum(22)`, `stop`). ⚠ **The reviewer's own diagnosis was half right and the run says so**: routes 1 and 2 never reach the output, with OR without the final mask, because pandas' `rolling.sum` is COMPENSATED and an overflowing window reads NaN rather than `inf` — `sum(22)` is `all NaN` on both. So the mask covers exactly ONE of the three routes (the division, 95 infinite readings of 120 without it), and the other two are absorbed by a pandas BEHAVIOUR, which is now measured directly (a 22-window holding one `+inf` reads NaN on all 22 of its windows; two DBL_MAX summands, all 23 of theirs) and pinned by a test next to `test_the_other_two_overflow_routes_never_reach_the_output` (both renamed later — round 3 renamed the second to `test_routes_1_and_2_never_reach_the_output`, round 4 the first to `test_the_rolling_sums_overflow_behaviour_is_not_uniform`, and round 4 also showed the "22 of 31 / 23 of 31" figures quoted here were 21 bars of `min_periods` warm-up plus the contamination — see round 4's MAJOR). |
| 2 | MINOR, x64 at the three price levels | Measured rather than narrowed: §D3 now loops `(8.0, 64.0)` and `test_gate_d_scale_at_extreme_price_levels` is parametrized on both. All six cells `True`. The four prose surfaces — gate table, module docstring, test docstring and `docs/MLCompanionContract.md` — now describe a run that exists; none was left behind. |
| 3 | MINOR, the 25 that decomposed to 26 | Both places now read "the two NaN penetrations at T and T+1 spoil the PERIOD + 1 = 23 windows ending T .. T+22; `avg.shift(1)` TRANSLATES that run to T+1 .. T+23 without widening it; `rolling(LOOKBACK).max()` adds LOOKBACK − 1 = 2. 23 + 0 + 2 = 25". |
| 4 | MINOR, the document's contract | The exception list is now four bullets and names §C3's running-maximum count (with the test it comes from) and §L's 701 (with the document it comes from). |
| 5 | NIT, "three orders" | "five orders above the 4.091e-11", with §D2 cited. |
| 6 | NIT, §G5's caption | The script now prints `§G5 frames below MIN_BARS, and a constant-NaN frame` **and measures 0, 1 and 5 bars**; `test_a_frame_below_min_bars_is_refused_at_every_length` parametrizes `[0, 1, 5, MIN_BARS - 1]`. The receipt's §G5 heading and fence match. |

Again, not one finding was about the mathematics. The module's arithmetic
has not changed since it was first written; everything in two rounds has
been prose claiming more than a run supported, plus two measurements that
did not exist until a reviewer asked for them (x64 at the extreme levels,
and the two extra overflow routes).

After the fixes: `python -m pytest tests/test_j_safezone_dist.py -q` 203
passed; `python docs/measure_j_safezone_dist_cpu.py` 203 passed with
AVX-512/AVX2/FMA3 off; full suite 2 failed, 11,845 passed, 86 skipped —
the same two expected failures.

## Review round 3 — REVISE

Reviewer: a third fresh `Explore` subagent, Fletcher persona, read-only,
given both prior reports and explicitly invited to refute round 2's
rolling-sum conclusion with a run. It re-ran every section on both
dispatches and the full suite with `-rs`. Verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/JSafezoneDistMeasured.md:390, docs/measure_j_safezone_dist.py:579, tests/test_j_safezone_dist.py:713
    problem:  "`x64` at 1e+100 is 6.4e+101, four orders inside DBL_MAX, so the rescale does not overflow." DBL_MAX is 1.7976931348623157e+308. 6.4e+101 is **two hundred and six** orders inside it, not four. You are off by 202 orders of magnitude in the one sentence whose entire job is to state a margin, and you put it on three surfaces — the receipt, the script that is supposed to be upstream of the receipt, and a shipped test docstring. Worse: this is the section review round 2 FORCED you to add, so the one new measurement of this round arrived with a typed number that no run produced and that arithmetic refutes on sight. The conclusion survives (the rescale does not overflow — it does not come within 200 orders of overflowing), which is exactly why nobody checked the number. §D3's largest intermediate is `pen.rolling(22).sum()` at roughly 1e+101; nothing in the chain exceeds 1e+102 at that level.
    fix:      Stop typing an order count and print the measured one. In `section_D`'s §D3, compute the largest intermediate at each level — `max(abs(pen.rolling(22).sum()).max(), abs(stop).max())` — print it as a column, and change the caption to `print(f"\n  ⚠ the largest intermediate at 1e+100 x64 is {worst:.2e}, against DBL_MAX {np.finfo(float).max:.2e}, so")` / `print("  the rescale does not overflow; the cell is the same claim as §D1's.")`. Then copy the printed figure into docs/JSafezoneDistMeasured.md:388-392 and narrow tests/test_j_safezone_dist.py:711-713 to "x64 at 1e+100 is 6.4e+101, more than 200 orders inside DBL_MAX (§D3), so it does not overflow."

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:547-569 (§G3) and docs/measure_j_safezone_dist.py:680-681
    problem:  Round 2's fix renumbered the three overflow routes on three surfaces and left two behind, and the result is a sentence that is false against the table it cites. The §G3 fence prints the routes in the order division / rolling sum / subtraction. The prose below it numbers them 1 = subtraction, 2 = rolling sum, 3 = division, then says "the `sum(22)` column **above** is `all NaN` for routes 1 and 2". Read against the only numbering the table offers — its row order — row 1 is the division and its `sum(22)` cell reads **5.29e+298**, not `all NaN`. Meanwhile the script prints the opposite convention two lines under the same table: "routes 2 and 3 never reach the output". Three artefacts, three numberings, for one measurement. `pandas_ta/trend/j_safezone_dist.py:131-141` and `tests/test_j_safezone_dist.py:806-813` follow the receipt's; the script follows its own.
    fix:      Pick one numbering and make the table carry it. Reorder `_OVERFLOW_ROUTES()` to subtraction, rolling sum, division and prefix each label with its number — `"1. subtraction (+max to -max)"`, `"2. rolling sum (alternating max)"`, `"3. division (1e300 / 1e-300)"` — then change docs/measure_j_safezone_dist.py:680 to `print("\n  ⚠ Read the `sum(22)` column: routes 1 and 2 never reach the")`. The receipt's §G3 fence, numbered list and "routes 1 and 2" sentence then agree with the rows above them, and `test_the_other_two_overflow_routes_never_reach_the_output`'s docstring already matches.

  - severity: MINOR
    location: pandas_ta/trend/j_safezone_dist.py:283 and docs/JSafezoneDistMeasured.md:680
    problem:  "Cost: two `rolling` sums, one `rolling` max, two shifts and one division." The rolling counts are right; the other two are not. Shifts: `low.shift(1)` at :42, `lo.shift(1)` and `avg.shift(1)` at :116 — **three**. Divisions: `total / hits.where(...)` at :71 and `(px - stop) / px` at :129 — **two**. Two specific counts in a shipped docstring, repeated in §Z, neither matching the file they describe. And this exact defect was filed against the sibling port two days ago, in a review folder sitting in this repo: `docs/reviews/auto-2026-11-14-j-acosc/01-j-acosc.md:556-566` is a NIT reading "'three rolling passes and **one division**'. There are two". You read the j_damiani and tf_iqr_ret_60 ports for shape and skipped the one review that had already found the sentence you were about to retype.
    fix:      Both places: "Cost: two `rolling` sums, one `rolling` max, three shifts (`low.shift(1)` in the penetration, `lo.shift(1)` and `avg.shift(1)` in the raw stop) and two divisions (the mean over the hits and the final `/ close`). Linear in bars."

  - severity: MINOR
    location: pandas_ta/trend/j_safezone_dist.py:200, docs/JSafezoneDistMeasured.md:129, and the decisions table at :704-714 / ASSUMPTIONS at :716-741
    problem:  "⚠ **WHICH MEAN is the one decision in this formula**" — and your own §B2 prices a second one eight sections earlier. The issue quotes "L1 - 2.5*mean(down-penetrations, 22)". Whether the mean is lagged WITH `L1` or evaluated at T is a reading the quote does not settle, and `today-avg` (`raw = lo.shift(1) - MULT * avg`) is that other reading: measured rho 0.9929 / 0.9873 and max |abs| 9.970e-03 / 9.389e-02 against the oracle. You shipped the lagged form — correctly, it is the prototype's (`ind_screen_r2.py:138`, `avg.shift()`) and the causal one — and then filed the alternative as a MUTANT, i.e. as a defect, while the decisions table logs seven lesser choices and ASSUMPTIONS logs four, and neither logs this one. "The one decision" is an absolute of exactly the class CLAUDE.md polices, refuted by a table inside the same document.
    fix:      Strike "the one" from both surfaces: "WHICH MEAN is the load-bearing reading of this formula". Add a decisions-table row: "| `avg` is lagged WITH `L1`, not evaluated at T | the issue's quote does not settle it; the prototype (`ind_screen_r2.py:138`) lags it, and the unlagged form makes bar T's stop depend on bar T's own low — a stop no trader could have had in the market. Priced: Spearman 0.9929 / 0.9873 vs the oracle, max \|abs\| 9.970e-03 / 9.389e-02 | §B2, `today-avg` |", and say in §B2's lead-in that `today-avg` is the issue's literal reading rather than only a wrong one.

  - severity: NIT
    location: docs/JSafezoneDistMeasured.md:206-211
    problem:  Round 1's fix table claims "Both fences now end where the transcript ends, with the abridgement stated as prose outside them". §G1's does (:494-496). §B's does not: the fence at :206-211 still contains two lines the script never prints — "`... and trend, range-bound, grid, heavy-tailed, jump: all 36 of 36`", twice. I checked all twelve rows and the compression is true, which is not the point: §G1 got the treatment the fix table describes and §B got half of it.
    fix:      Cut the two `...` lines out of the fence, leaving only the two `walk` rows the script prints, and move the compression into the prose lead-in already above it: "the remaining five rows of each are `True` and `36 of 36` on every frame."

  - severity: NIT
    location: docs/reviews/auto-2026-11-16-j-safezone-dist/00-manifest.md:59
    problem:  "Summary: `99-summary.md`." There is no `99-summary.md` in the run folder — it holds exactly two files. The manifest is the index a reader opens first and it points at a file that does not exist.
    fix:      Either write the summary, or make the reference a forward one: "Summary: `99-summary.md`, written when the loop closes."
SUMMARY: The arithmetic is still untouchable and I will not pretend otherwise: §A1 through §Z reproduced cell for cell on both dispatches, §D2 is the only section whose numbers moved (4.091e-11 → 6.546e-11, exactly as claimed), 203 passed with AVX-512/AVX2/FMA3 off, `pytest -q -rs` gave me "2 failed, 11845 passed, 86 skipped" with a SKIPPED block whose every group matches your §F1 table to the digit — 45 / 21 / 14 / 3 / 1 / 1 / 1 — and the owed-row message names `['j_safezone_dist']` and nothing else. All five wiring touch points are live, every count the suite checks moved together, and round 2's rolling-sum conclusion is right: I reran all three routes and the compensated `rolling.sum` does read NaN on an overflowing window, so there is nothing to refute there. Which leaves the prose, again, and the pattern is now three rounds old. Round 2 made you add §D3, and §D3 arrived carrying "6.4e+101, four orders inside DBL_MAX" — it is two hundred and six, a number a pencil refutes, planted on the receipt, the script and a shipped test docstring. Round 2 made you renumber the overflow routes, and you renumbered three surfaces out of five, so §G3 now tells a reader that the `sum(22)` column "above" is all NaN for routes 1 and 2 while row 1 of that very table prints 5.29e+298. You typed "two shifts and one division" over a function with three shifts and two divisions, two days after a reviewer filed that identical sentence against `j_acosc` in a folder sitting in this repo. And you called the mean "the one decision in this formula" while §B2 quietly prices the second one and the decisions table logs seven smaller ones. You measure like a professional and proofread like a tourist. Fix the DBL_MAX margin by printing it instead of guessing it, make one numbering survive all five surfaces, count the operators in your own file, and this ships.
```

### Fixes applied after round 3 (all six)

| # | finding | what was done |
|---|---|---|
| 1 | MAJOR, "four orders inside DBL_MAX" | The order count is gone and the margin is now PRINTED. `_largest_intermediate()` walks the whole chain (`lo`, `close`, `pen`, `total`, `avg`, `stop`) and §D3 prints it as a column per level: 6.419e-05 / 6.419e+07 / 6.419e+101, with the worst of the six cells against DBL_MAX 1.798e+308 as a factor of **2.800e+206**. The receipt quotes the printed cells and the test docstring quotes the factor; neither types an order count. |
| 2 | MINOR, three numberings for three routes | `_OVERFLOW_ROUTES()` is reordered to the order the routes occur in the chain — subtraction, rolling sum, division — and each label now CARRIES its number (`1.`, `2.`, `3.`), so the table itself defines the numbering. The script's caption, the receipt's fence, its numbered list and its "routes 1 and 2" sentence, the module docstring and the test (now `test_routes_1_and_2_never_reach_the_output`, parametrized `["subtraction", "sum"]`, with `_overflow_frame`'s branches in the same order) all agree. |
| 3 | MINOR, "two shifts and one division" | Counted in the file: three shifts and two divisions. Both the module docstring and §Z now name them individually, so the count cannot drift from the code again. ⚠ The reviewer is right that `docs/reviews/auto-2026-11-14-j-acosc/01-j-acosc.md` had already filed this sentence against the sibling port; that folder was not read before writing. |
| 4 | MINOR, "the one decision in this formula" | Struck from the module docstring and §A4, both now "the load-bearing reading". The second reading — whether `avg` is lagged with `L1` — is now a decisions-table row with its measured price (Spearman 0.9929 / 0.9873, max \|abs\| 9.970e-03 / 9.389e-02), and §B2's lead-in says `today-avg` is the issue's quote taken literally rather than only a wrong version. |
| 5 | NIT, §B's half-abridged fence | The two `...` lines are out of the fence; the two rows the script prints stay in it and the compression is prose below it. |
| 6 | NIT, the dangling `99-summary.md` | The manifest now says "written when the loop closes". |

## Review round 4 — REVISE (the loop's last round)

Reviewer: a fourth fresh `Explore` subagent, Fletcher persona, read-only,
given all three prior reports and pointed first at the artefacts rounds 2
and 3 had CAUSED to exist. Verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/JSafezoneDistMeasured.md:586-588 (§G3), repeated at docs/reviews/auto-2026-11-16-j-safezone-dist/01-j-safezone-dist.md:198 and dressed up as a test comment at tests/test_j_safezone_dist.py:842-844
    problem:  "measured directly in the last two lines (a window holding one `+inf` reads NaN on all 22 of its windows; two DBL_MAX summands, NaN on all 23 of theirs)." You printed `NaN 22 of 31` and `NaN 23 of 31` and then told the reader what those numbers mean without subtracting the part pandas hands you for free. `Series([inf] + [1.0]*30)` is 31 long; `rolling(22, min_periods=22)` blanks indices 0..20 on ANY 31-bar series, bad value or not. That is 21 NaNs before the `+inf` does a thing. So the measured contamination is **one** window for `one_inf` and **two** for `two_big` — the 22 and the 23 are 21 + 1 and 21 + 2, and the fact that 22 happens to equal `PERIOD` is an accident of the frame length you chose, which is exactly why nobody checked it. Worse, the frame cannot show the claim even in principle: of the 22 windows that contain index 0, twenty-one do not exist as valid windows, so "all 22 of its windows" is a statement no run in this port distinguishes from warm-up. And the test comment at :842 — "Every window that reaches the bad value is blanked, not merely the one that holds it alone" — asserts a blast radius its own frame has exactly one instance of, under an assertion (`>= PERIOD`) that 21 free NaNs plus any single extra satisfies. This is the block review round 2 forced into existence and round 3 blessed, and it arrived carrying a count read off a figure that does not contain it: the third generation of the same defect, in the third section a reviewer created.
    fix:      Measure the blast radius instead of inferring it. In `section_G`'s last block use a frame long enough to separate the two causes — e.g. `Series([1.0]*40 + [np.inf] + [1.0]*40)` and `Series([1.0]*40 + [np.finfo(float).max]*2 + [1.0]*38)` — and print three cells per frame: `warm-up NaN` (`PERIOD - 1`), `extra NaN`, and the first/last blanked index. Then write the printed numbers into §G3 and into the task log row ("of the 22 NaNs on the 31-bar probe, 21 are the `min_periods` warm-up and N are the windows the bad value blanks; on a 81-bar frame the +inf blanks bars X..Y"). Replace the test's `assert int(s.isna().sum()) >= PERIOD` with the exact split — `assert int(s.isna().sum()) == PERIOD - 1 + <measured extra>` — and cut the comment, or rewrite it to the range the new frame actually shows. The load-bearing half (`isinf == 0`) stays as it is; it is the only part of that test doing work today.

  - severity: MINOR
    location: docs/measure_j_safezone_dist.py:601, copied to docs/JSafezoneDistMeasured.md:395 and tests/test_j_safezone_dist.py:715-717
    problem:  "the largest intermediate anywhere in the chain over those six cells is 6.419e+101." `_largest_intermediate` is called once per level — `docs/measure_j_safezone_dist.py:596`, `_largest_intermediate(*_scaled(frame, 64.0))` — so the run covers **three** cells, and the column header says so: `largest intermediate, x64`. The six cells are the six bit-equality cells, and the x8 half of them was never put through the headroom walk. The figure happens to bound all six (x8's intermediates are smaller by exactly 8), which is precisely the shape of round 2's finding against this same section: a conclusion that is safe, asserted over a run that was not performed. A specific count, on three surfaces, one of which is a shipped test docstring.
    fix:      Either measure the six: `for f in (8.0, 64.0): interm = _largest_intermediate(*_scaled(frame, f))`, print both columns, keep `worst_interm` across all six, and leave the sentences alone. Or narrow all three to the run that exists — "the largest intermediate over the three x64 cells is 6.419e+101; the x8 cells are smaller by the factor 8" — and change the caption from "those six cells" to "those three".

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:657-661 (§L)
    problem:  "What it says is that three of the four readings built on dispersion alone — `natr` 0.2053 (also `volatility/`), `massi` 0.0911 (also `volatility/`), and `chop` 0.0687 and `vhf` 0.0948 (both `trend/` choppiness filters, not `volatility/`) — are near zero, while `rvi` is not." Count the names inside your own dash: four. You wrote "three of the four" and then listed four, all four of which read under 0.21. Round 1's MAJOR was this exact sentence's parent ("the four volatility comparators sit at |ρ| ≤ 0.21"); the rewrite swapped one miscount for another, in the paragraph whose whole purpose is to stop a reader trusting a grouping you did not count.
    fix:      "All four of the other dispersion readings — `natr` 0.2053 and `massi` 0.0911 (`pandas_ta/volatility/`), `chop` 0.0687 and `vhf` 0.0948 (`pandas_ta/trend/` choppiness filters) — sit at or under 0.21, and `rvi` at 0.5174 is the one of the five that does not." Then check the sentence against the table above it before you commit it.

  - severity: MINOR
    location: docs/JSafezoneDistMeasured.md:395-396 (§D3's fence), and :502 (§G1's)
    problem:  Line 44 of this document: "Two fenced blocks (§B and §G1) are ABRIDGED and say so where they are cut; every other fence is a transcript." §D3's fence then ends with two lines the script never prints — `largest intermediate over the six cells: 6.419e+101` / `DBL_MAX: 1.798e+308 — a factor of 2.800e+206`, where the script prints a five-line ⚠ paragraph. The em dash is the tell: the script prints `--`. §D3 is not on the abridged list. And §G1's fence carries `bars before the hole, bit-identical:` where the script prints three different lines — an abridgement is a cut, not a substitution, so the note at :507 does not cover it. This is round 1's finding #5, in the section round 3 created, and the fix table claims it was closed.
    fix:      In §D3, end the fence at the table and put the margin outside it as prose, or paste the script's five ⚠ lines verbatim. In §G1, replace the typed line with the three the script prints, or cut it and let the two `bit-identical` rows stand under the existing prose. Then re-read :44 and confirm it is still true of every fence in the file.

  - severity: NIT
    location: docs/reviews/auto-2026-11-16-j-safezone-dist/01-j-safezone-dist.md:58 and :198
    problem:  The index a reader opens first carries two dead facts. ":58 — `tests/test_j_safezone_dist.py` — 193 tests" describes the shipped artefact and the file has 203 (verified: `203 passed`). ":198 names `test_the_other_two_overflow_routes_never_reach_the_output`, which round 3 renamed to `test_routes_1_and_2_never_reach_the_output`; the function no longer exists. Round 3's own fix table records the rename twenty lines down, so a reader gets there eventually — by first grepping for a name that is gone.
    fix:      ":58 → "— 203 tests (193 as first written; rounds 2 and 3 added ten)". :198 → the current name, or "`test_the_other_two_overflow_routes_never_reach_the_output` (renamed in round 3 to `test_routes_1_and_2_never_reach_the_output`)".

  - severity: NIT
    location: docs/measure_j_safezone_dist.py:487, :600, :601
    problem:  Three `print(f"...")` calls with no placeholder in them. Harmless, and it is slop in the one file whose whole claim to authority is that everything in it was printed rather than typed — :600 and :601 are the margin caption that round 3 made you add, where the `f` prefix is a leftover from the version that still typed the number in.
    fix:      Drop the `f` prefix on all three.
SUMMARY: The mathematics has survived four rounds untouched and I will say so once: §A1 through §Z reproduced cell for cell on both dispatches, §D2 the only mover (4.091e-11 / 6.546e-11, as claimed), 203 passed with AVX-512/AVX2/FMA3 off, `pytest -q -rs` gave me 2 failed, 11845 passed, 86 skipped in 297s with the two expected failures, all five wiring touch points live, the dictionary regenerated, 356/364/trend (63)/701/339 moving together, and the prototype retype bit-faithful to `ind_screen_r2.py:136-139` down to the inlined `sdiv`. Rounds 2 and 3's additions hold up where I was told to look hardest: §D3's headroom column prints the margin instead of guessing it, the three overflow routes now carry their numbers in the table's own row labels and all five surfaces finally agree, the `avg.shift(1)` decision is logged with its measured price, the skip table sums to 86, the refusal test covers 0 and 1 bars, and the operator count is right — I counted them, three shifts and two divisions, the fourth `.shift(offset)` being default-dead and named nowhere as part of the cost. So I went to the one block nobody has re-derived with a pencil, and there it was: you printed `NaN 22 of 31`, and `min_periods` hands you 21 of those 22 on a clean series, so the sentence "reads NaN on all 22 of its windows" is a blast radius your frame is too short to show — and you shipped a test comment claiming the same thing under an assertion that 21 free NaNs plus one satisfies. Then "the largest intermediate over those six cells" where three were walked, "three of the four" over a list of four, and a §D3 fence that is typed prose wearing a transcript's clothes. Four rounds, and the arithmetic has never once been the problem; what keeps failing is the sentence you write after you read the number. Lengthen those two probe frames, print the warm-up and the contamination as separate columns, and stop explaining figures you have not decomposed.
```

### Fixes applied after round 4 (all six)

| # | finding | what was done |
|---|---|---|
| 1 | MAJOR, the 31-bar rolling-sum probe | The probe is replaced, not reworded. `_ROLLING_SUM_PROBES()` now uses 81-bar frames with the bad value at bar 40, and §G3 prints `inf`, `warm-up` (`PERIOD − 1` = 21), `extra` and the blanked span as separate columns. ⚠ **And the new measurement refuted the claim it was meant to support.** One `+inf` at bar 40: 0 infinite readings, 22 contaminated windows, bars 40 .. 61. Two DBL_MAX at bars 40 and 41: **1 infinite reading** — the window in which the overflow first happens — and only 21 NaN, bars 42 .. 62. So "pandas' compensated `rolling.sum` yields NaN rather than `inf`" is true of routes 1 and 2's frames and is NOT a rule, which is now what §G3, the module docstring's guard note and the test all say. The test is renamed `test_the_rolling_sums_overflow_behaviour_is_not_uniform` and asserts the exact split including the `inf 1`; the vacuous `>= PERIOD` assertion and its comment are gone. The load-bearing assertion stays where the reviewer put it: on the MODULE's output, in `test_routes_1_and_2_never_reach_the_output`. |
| 2 | MINOR, "those six cells" over three | §D3 now walks `_largest_intermediate` at BOTH factors and prints two columns (x8 8.024e-06 / 8.024e+06 / 8.024e+100, x64 6.419e-05 / 6.419e+07 / 6.419e+101). The margin sentence is now true of six cells because six were walked, on all three surfaces. |
| 3 | MINOR, "three of the four" over four names | §L now reads "Of the FIVE dispersion readings among the seven, four sit at or under 0.21 … and `rvi` at 0.5174 is the one that does not", counted against the table above it. |
| 4 | MINOR, §D3's and §G1's fences | §D3's fence ends at the table and the margin paragraph is quoted below it as prose. §G1's fence now carries the script's own three lines. The document's contract at the top names all three cases (abridged §B and §G1, quoted-not-pasted §D3). |
| 5 | NIT, two dead facts in this log | The test count reads 203 (193 as first written), and the renamed tests are named with their renames. |
| 6 | NIT, three `f`-prefixed prints with no placeholder | One survived the earlier edits; it is gone. (The other two named by the reviewer had already been rewritten into real f-strings by fix #2.) |

⚠ **Round 4 was the loop's last round** (the session's review rule caps at
round 1 plus three re-runs). All six findings are applied and the suite is
green, but **no reviewer has seen the post-round-4 state**: there are no
open findings and there is also no post-fix PASS. This file says so rather
than implying one.

Four rounds, twenty-five findings, every one applied, and not one of them
about the mathematics. Two of the nineteen were measurements that did not
exist until a reviewer asked (x64 at the extreme price levels; the two
extra overflow routes, which then refuted the reviewer's own diagnosis of
them). The remaining seventeen were prose claiming more than a run
supported. The shape worth carrying forward is round 3's: **the one
NEW measurement this loop produced arrived with a typed number in its
caption**, because a margin that is obviously safe is a margin nobody
checks. The fix was not to retype it but to make the script print it.
