# `ts-reoccur-20` — task log

PandasTa issue #103. Lane: main thread. Status: **PASS not reached;
four rounds run, every finding applied** (see `99-summary.md`).

## Implementation

`percentage_of_reoccurring_datapoints_to_all_datapoints` over a rolling
window of 20 closes, as `pandas_ta/statistics/ts_reoccur_20.py`
(`TS_REOCCUR_20`). Sorting each window puts every run of equal closes
together, so a datapoint reoccurs exactly when it equals its left or
right neighbour in the sorted row — `value_counts()[>1].sum()` without a
counter per window, and the screen prototype's own spelling. The sorted
copy is taken `CHUNK_VALUES // length` rows at a time so it does not
grow with either `len(close)` or `length`; a window holding a bad close
(NaN, inf, zero, negative, subnormal) is emptied, which is this fork's
missing-data rule and NOT the source's.

Five wiring touch points: the module, `pandas_ta/statistics/__init__.py`,
`Category` in `pandas_ta/__init__.py`, the `core.py` accessor,
`tests/test_ts_reoccur_20.py` (223 tests). Count bookkeeping: `README.md`
(341 → 342, 349 → 350, statistics 49 → 50),
`docs/IndicatorDictionary.md` (regenerated),
`docs/MLCompanionContract.md` (686 → 687 tagged, 42 → 43 `CONST`),
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 341 → 342).

Measurements: `docs/measure_ts_reoccur_20.py` (sections A1–A6, B, M, C,
D, G, O, L, W, Z) and `docs/measure_ts_reoccur_20_cpu.py` (the same
module and any named section under `NPY_DISABLE_CPU_FEATURES="AVX512F
AVX512_SKX AVX2 FMA3"`). Receipt: `docs/TsReoccur20Measured.md`.

Gate E is **owed** — run by issue-solver after this session, per the
session's rules. `test_the_gate_e_row_is_owed` asserts the ledger has no
row for this indicator, which is the receipt session's cue to replace it.

---

## Round 1 — REVISE

Verdict and findings, verbatim:

> VERDICT: REVISE
>
> FINDINGS:
>   - severity: CRITICAL
>     location: docs/TsReoccur20Measured.md:265 and :287 (§A4), tests/test_ts_reoccur_20.py:75
>     problem:  "the boolean is constant on **4 of the 7** grid frames" / "it is constant on 4 of 7 frames" is a count no run produces, and the table nine lines above it says otherwise. `python docs/measure_ts_reoccur_20.py A4` prints `has_duplicate` with `distinct = 1` on exactly three frames — grid-2tick, range-bound, round-1000 — and `distinct = 2` with a finite ρ (0.5248 / 0.9280 / 0.9999 / 0.6225) on grid-10tick, grid-40tick, grid-200tick and heavy-tailed. Your own §A4 table carries exactly three dashes in the `has_duplicate` rows. You wrote the sentence, then printed the table that refutes it, and shipped both. This is the repo's named dominant defect, reproduced verbatim in the receipt AND in the test module's docstring.
>     fix:      Change all three occurrences to "constant on **3 of the 7** grid frames (`grid-2tick`, `range-bound`, `round-1000` — the three that never read 0.00 in §C)". Better: make `section_A4` print `sum(nu == 1 for has_duplicate rows)` so the sentence is a quote and not a hand count.
>
>   - severity: MAJOR
>     location: docs/TsReoccur20Measured.md:194-195 (§A3 table) and :451 (§C)
>     problem:  The lattice size is miscounted by one, three times. `A3` prints `length 20: k values [0, 2, 3, …, 20]` — twenty entries, not nineteen — and `length 60: [0, 2, …, 60]` — sixty, not fifty-nine. §C then builds an argument on the wrong number: "19 reachable values at `length` 20, of which a single tick regime visits 3 to 19" reads as "heavy-tailed visits all of them", when it visits 19 of 20. The docstring's own "the reachable set at `length` 20 is 0.0 and 0.10 .. 1.00" is 1 + 19 = 20 and contradicts the table.
>     fix:      §A3: "(20 values)" and "(60 values)". §C: "20 reachable values at `length` 20, of which a single tick regime visits 3 to 19". And have `section_A3` print `len(ks)` next to the list so the next reader cannot count the ellipsis wrong either.
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:217 (§A3) against docs/measure_ts_reoccur_20.py:360
>     problem:  "Measured: 1.0 on all 281 bars at `length` 20, **0.6667 almost everywhere at `length` 3**." Section A3 runs `_two_level(300)` at the default length only — one line, one number, `1.0000 .. 1.0000 on 281 bars`. Nothing in the script prints a length-3 reading of that frame, let alone a frequency. The file's header says "Every number in §A1–§A6 … is printed by `python docs/measure_ts_reoccur_20.py`", so this sentence falsifies the header as well as itself. `test_the_closed_forms_are_exact` only bounds the reachable SET at length 3; it says nothing about "almost everywhere".
>     fix:      Loop `_two_level(300)` over `(MIN_LENGTH, 3, LENGTH, 60)` in `section_A3` and print `value_counts(normalize=True)`, then quote it — or delete the clause and say only what the test proves: at `length` 3 the reachable set is `{1.0, 0.6667}`.
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:897-899 (§Z) and pandas_ta/statistics/ts_reoccur_20.py:256-266
>     problem:  You disclaim the milliseconds and then promote the ratio: "What survives a re-run is the flat peak, the monotone ordering and the **ratio 20.58 … 20.67×**". I re-ran `Z` on this machine: 20.93 / 20.90 / 20.74 — three runs, all outside the band you say survives a re-run. The traced peak reproduced to the digit (17.3 / 28.2 / 27.7 / 27.6 MB); the ratio did not. The shipped docstring repeats the dead band ("between 20.58x and 20.67x").
>     fix:      Quote the ratio at one significant figure — "~20× at `length` 250 against `length` 2" — in both the receipt and the docstring, and move the 2-dp figures into §Z's table where the ms already live, under the same "this run's" disclaimer.
>
>   - severity: MINOR
>     location: pandas_ta/statistics/ts_reoccur_20.py:113-119 vs docs/IndicatorDictionary.md:274
>     problem:  The docstring justifies its own shape — "the first two sentences are short on purpose: `gen_indicator_dictionary.py` keeps only the first 150 characters … so the warning has to fit inside them" — and then the generated row cuts the warning in half: "⚠ It reads EXACT price equality, so it is a tick-grid feature:…". The clause that actually tells a reader what happens, "identically 0.0 on continuous-float prices", falls off the end. The stated design goal is not met in the one document CLAUDE.md sends a reader to first.
>     fix:      Compress to roughly "Share of the last `length` closes that repeat inside the window. ⚠ EXACT price equality — a tick-grid feature, identically 0.0 on continuous prices." (≈145 chars), then re-run `python docs/gen_indicator_dictionary.py` and check the row renders the whole warning.
>
>   - severity: MINOR
>     location: tests/test_ts_reoccur_20.py:660
>     problem:  `assert len(_caught(mod.ts_reoccur_20, close, other)) >= 1` is the tightest band in the file and it sits exactly on the measured value: section M prints `write_index_earlier` and `forward_window` caught **1 of 36** on `grid-40tick`. Your own §F argues the frames are the fragile part — built with `np.exp`, `np.cumsum`, `np.round`, so "a close can land on a different grid point in the last bits" — which is precisely the thing that would turn that 1 into a 0 on a GitHub runner and red the suite for a reason unrelated to the port.
>     fix:      Keep the per-frame derived back-dating assertion (it is the one that carries Gate B anyway) and make the sweep assertion frame-robust: assert `sum(len(_caught(mod.ts_reoccur_20, *PAIRS[f])) for f in PAIRS) >= 4`, or restrict `>= 1` to the two high-churn frames (`grid-2tick`, `range-bound`, measured 21 and 21) and drop it on `grid-40tick`.
>
>   - severity: NIT
>     location: pandas_ta/core.py:2125
>     problem:  The continuation `**kwargs)` is indented 30 spaces; the call paren opens at column 31. Every neighbouring accessor (`ts_perment_20` at :2113, `ts_q05_60` at :2119) aligns exactly. One column off, in the file whose whole job is being boringly uniform.
>     fix:      Add one space to line 2125 so `**kwargs)` sits under `close=close`.
>
> SUMMARY: The mathematics is right and the port is the right function — this is `percentage_of_reoccurring_datapoints_to_all_datapoints` (bars with a twin), not the `values_to_all_values` sibling, and §A4 prices the sibling rather than waving at it; `nbad`/`holds_bad` is a correct prefix-sum over `c[i : i+length]` with no off-by-one; the chunk loop is value-neutral at budgets 1 through 10⁹; `np.sort`'s NaN placement is noted and not depended on; `verify_series(close, length)` takes 20 closes and not 21; the mutant harness really does read the module off disk and `exec` it, and the "derived displacement" is a strengthening of Gate B, not a dodge — the sweep assertion is still there, and the sixth mutant's `[J−1]` moved-set is a geometric derivation, not a search. Every table in §A1–§A6, §B, §C, §D, §G, §O, §L and §Z's traced peak reproduced on re-run, to the digit. And then you hand-counted. Three times: the `has_duplicate` boolean is constant on three frames and you wrote four, with the refuting table printed directly above the sentence; the length-20 lattice has twenty reachable values and you wrote nineteen, in the row whose job is to transcribe a printed list; the two-grid-point frame at `length` 3 got a frequency claim from no run at all. The header of that file says every number in those sections comes out of the script. Four of them do not. You built an instrument that measures everything and then overrode it with arithmetic done in your head — which is the exact failure CLAUDE.md spends a paragraph on. Fix the counts, make the script print them so they cannot drift again, and this ships. Two things I could not verify and am not charging you for: the sandbox refused `docs/measure_ts_reoccur_20_cpu.py` and every `NPY_DISABLE_CPU_FEATURES` invocation, so §F's second row and the surviving-feature list are unchecked; and `tests/test_altport2_ports.py::test_the_category_count_moved_by_exactly_three` fails at 339 vs 342 when run after `tests/test_wiring_accessors.py` because `core.py:453` hands out the live `Category[name]` list that `:692` then `.remove()`s from — pre-existing, the same −3, not yours.

**Fixes applied, all seven.** `section_A4` now counts the constant
`has_duplicate` rows itself and prints the frame names (3 of 7:
`grid-2tick`, `range-bound`, `round-1000`); `section_A3` prints
`len(ks)` (20 and 60) and the two-grid-point frame's `value_counts` at
four lengths; §Z and the docstring dropped the dead bracket; the
docstring's opening was rewritten and the dictionary regenerated so the
whole ⚠ warning survives the cut; the Gate B sweep floor became 5 on the
two high-churn frames only; `core.py`'s continuation line was aligned.

---

## Round 2 — REVISE

> VERDICT: REVISE
>
> FINDINGS:
>   - severity: CRITICAL
>     location: pandas_ta/statistics/ts_reoccur_20.py:115 (`ts_reoccur_20.__doc__`, opening paragraph)
>     problem:  "That opening is 143 characters on purpose" is wrong, and it is wrong *because* of round‑1 fix #5 — the paragraph was rewritten and the count was not re‑derived. The opening is **147** characters […]. `docs/gen_indicator_dictionary.py:290` keeps `d[:150]` and then drops the partial trailing word, so the real headroom is **3** characters, not the 7 the docstring advertises. The number that documents a 150‑character guard is itself the thing that will blow the guard […]. A count no run produced, in the shipped docstring.
>     fix:      Replace "143" with 147, or — better, since the paragraph will be edited again — delete the count and state the headroom as the thing that was actually measured […].
>
>   - severity: MAJOR
>     location: docs/TsReoccur20Measured.md:556 (§D2), also line 89 (Verdict row D), pandas_ta/statistics/ts_reoccur_20.py:227, tests/test_ts_reoccur_20.py:59
>     problem:  "Measured over all eight frames and all four factors: **0 merges**" is a count no line of `section_D` prints. The ×10/×3.7/×0.1/×1.0000001 loop calls `_agree` only and prints bit‑equal/shared; `np.unique` is computed solely for §D3's 20‑double frames. And bit‑equality does **not** imply zero merges: if two closes that merge under the rescale each already have a twin inside a window, the duplicate count is unchanged and the column is bit‑identical while a merge happened. On `grid-200tick`, where 1,346 of 1,481 bars already read a repeat, that is precisely the regime where a merge would hide. The repeated word "measured" attaches a run to an inference, four times […].
>     fix:      Either print the count — in `section_D`'s non‑exact loop add `np.unique(close.to_numpy()).size - np.unique((close * k).to_numpy()).size` per frame and factor and quote the printed zeros in §D2 — or strike the word from all four places […].
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:637 (§G2) vs docs/measure_ts_reoccur_20.py:786-794
>     problem:  §G2 reads "Under `np.errstate(all="raise")`: an all‑NaN frame fires 0 of 400, a frame of 400 zeros fires 0, a frame of 400 negative prices fires 0 — and no error is raised." `section_G` prints neither of the last two under that contract: the 400‑negative‑price frame is never run by the script at all, and the 400‑zeros line sits **outside** the `with np.errstate(all="raise")` block. […]
>     fix:      Move the zeros frame inside the `np.errstate(all="raise")` block in `section_G` and add `Series(np.full(400, -1.0))` beside it, printing both fired counts […].
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:518 (§C1)
>     problem:  "Those two deltas are read off `git diff docs/IndicatorDictionary.md`, which adds exactly one tagged output column (`TS_REOCCUR_20` CONST) and **changes no other table row**." The diff I ran changes four other lines […] and it **adds a second table row**, the `ts_reoccur_20 | TS_REOCCUR_20` entry in *Never fires on the probe* […]. (The arithmetic itself checks out: 43 `CONST` tags in the dictionary, and `test_the_contract_quotes_the_dictionarys_actual_ml_form_counts` passes against 687.)
>     fix:      Rewrite as: "…which adds exactly one tagged output column row (`` `TS_REOCCUR_20` CONST ``) and one *Never fires on the probe* row, and otherwise changes only the four package counts (343→344 probed, 341→342 registered, 349→350 callable, statistics 49→50)."
>
>   - severity: MINOR
>     location: tests/test_ts_reoccur_20.py:752
>     problem:  `test_gate_c_is_not_a_constant_and_spans_a_real_range` asserts `col.nunique() >= 3` and `max - min >= 0.15` for every frame in `VARYING`, and on `grid-200tick` the measured values are exactly 3 and exactly 0.20 — zero margin […]. This is the same zero‑margin pattern round‑1 finding #6 raised […], left in place one test over.
>     fix:      Split the floor by frame […]: assert `nunique >= 2` and `max - min >= 0.10` on `grid-200tick`, and `nunique >= 6`, `max - min >= 0.35` on the other six […].
>
>   - severity: NIT
>     location: docs/TsReoccur20Measured.md:91 (Verdict row F)
>     problem:  The row ends "…; full suite in §F", and §F says the opposite: "The full-suite figure is in the commit message rather than here […]". A reader following the pointer finds a refusal. (For the record, the full suite on this worktree is 3 failed, 8,590 passed, 85 skipped […].)
>     fix:      Change the cell to "…; the full-suite figure is in the commit message (§F says why)."
>
>   - severity: NIT
>     location: docs/TsReoccur20Measured.md:478 (§C, histogram caption)
>     problem:  "The value histograms (share of fired bars, **the eight lowest values**)" does not describe the table, which is keyed on the eight lowest *lattice points* 0.00 … 0.40. […]
>     fix:      Caption it […] — or widen the table to the printed cells.
>
>   - severity: NIT
>     location: docs/TsReoccur20Measured.md:924 (§Z) and pandas_ta/statistics/ts_reoccur_20.py:261
>     problem:  […] A third run of `python docs/measure_ts_reoccur_20.py Z` on this worktree printed **21.26 / 21.27 / 21.05** — outside both disclosed brackets […]. "~20×" survives only by rounding 21.3 down to one significant figure […]. (The traced peak reproduced exactly: 17.3 / 28.2 / 27.7 / 27.6 MB.)
>     fix:      State the observed envelope instead of a point […]. Mirror the same range in the module docstring.
>
> SUMMARY: Round 2 landed all seven round‑1 fixes — I re‑ran A1–A6, B, M, C, D, G, O, L and Z myself and every table, every per‑frame cell, every churn figure, every histogram share and the reduced‑dispatch reproduction matched to the printed digit […]. Then the round‑2 lesson arrived exactly where the launcher said to look: fix #5 rewrote the docstring's opening paragraph and left behind "143 characters" for a paragraph that is 147 […] — a fresh unmeasured number carried in by a fix, in the one sentence whose whole job is to stop the warning from being truncated. Alongside it, "measured 0 merges" is stamped on four documents for a count that no line of `section_D` computes and that bit‑equality does not entail, and §G2 quotes two readings the script never prints under the contract it claims. None of this is mathematics: the port's arithmetic is sound, Gate A is genuinely bit‑equal on 11,848 of 11,848 bars, Gate B's derived back‑dating is the right instrument and the sixth mutant's J−1 is real, the wiring is complete and the 687/43 tag deltas hold up against a live parse. It is provenance discipline, and this repo fails on provenance. Fix the two counts, re‑attribute §G2, and stop writing "measured" over an inference.

**Fixes applied, all eight.** A new measured section `W` prints the
character count and the cut; `section_D` prints the merge count per
frame and factor (`m0` in all 32 cells) and the test asserts it;
`section_G` runs all three bad-close frames inside one
`np.errstate(all="raise")`; §C1's diff sentence names what the diff
actually changes; the Gate C floors became ≥ 6 / 0.35 on six frames and
≥ 2 / 0.10 on `grid-200tick`; the verdict row, the histogram caption and
§Z's envelope were corrected.

---

## Round 3 — REVISE

> VERDICT: REVISE
>
> FINDINGS:
>   - severity: MAJOR
>     location: docs/TsReoccur20Measured.md:969 (§Z) and pandas_ta/statistics/ts_reoccur_20.py:263
>     problem:  Round-2 fix #8 widened the cost ratio to "`length` 250 costs **20 … 21×** `length` 2" and then, three lines later, disclosed a run that printed "21.26 / 21.27 / 21.05". 21.27 is not in 20…21. The document contradicts itself in the same paragraph. I then ran a fourth `python docs/measure_ts_reoccur_20.py Z` on this worktree: 21.52 / 21.17 / 21.23 — outside the stated bracket and outside all three disclosed runs […]. You fixed a stale character count by writing a stale ratio.
>     fix:      Re-run §Z, state the bracket as the measured span over ALL runs […], add run 4's three figures to §Z's list […], and make the module docstring […] read the same numbers. If the bracket is meant to be re-run-stable, say what it is stable to (the monotone ordering and the ~20× order of magnitude) rather than pinning two significant figures that a fourth run already broke.
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:129-132 (§E0, second bullet)
>     problem:  "the two **tsfresh variants of itself** that the screen's own `skipped.py` names […]" is a count claim about a file in the tree, and the file says otherwise. `docs/issues/screen/skipped.py:126` names four […]. The two sum variants are neither measured nor mentioned anywhere, and the sentence asserts they do not exist.
>     fix:      Rewrite to "the variants … `skipped.py` names (four, at `skipped.py:126`)", say §A4 prices two of them […], and state in one clause why the other two are out […].
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:501-520 (§C1) and docs/MLCompanionContract.md:27
>     problem:  The generated row you added under *Never fires on the probe* has the owning-task cell "— unregistered, file one". That is false: `ts_reoccur_20` is in `Category["statistics"]` with an accessor […]. A consumer reading the dictionary first (which CLAUDE.md tells them to) is told the column is unregistered.
>     fix:      Add one sentence to §C1 and to the contract paragraph, on the `lot_zeroret_60` model: the cell is `gen_indicator_dictionary.py`'s generic fallback for any indicator with no `DEAD_TASKS` entry […], not a claim about registration […].
>
>   - severity: MINOR
>     location: pandas_ta/statistics/ts_reoccur_20.py:168 and docs/MLCompanionContract.md:27
>     problem:  Both say the comparator is "`LOT_ZERORET_20`, the share of ZERO RETURNS in the same window". §O2 of the receipt says the opposite in capitals: "⚠ At length 20 the two read DIFFERENT windows (`LOT_ZERORET_20` needs 21 closes)". The shipped docstring states as fact the thing the receipt raises a warning about, and it is the warning that is right.
>     fix:      In both places write "the share of zero returns over the same 20 BARS — 21 closes, so not the same window; the window-identical comparison is at `length` 19, §O2". The 0.5185 figure itself is correct and stays.
>
>   - severity: NIT
>     location: docs/TsReoccur20Measured.md:478-479 (§C) and tests/test_ts_reoccur_20.py:758
>     problem:  "whose third value is carried by four bars" / "0.003 of 1,481 bars -- four of them". No section prints that integer. […] 0.003 is what both 4/1481 and 5/1481 round to. The one number carrying the justification for `grid-200tick`'s special floor is the one number the script does not print […].
>     fix:      Have `section_C` print the raw bar count alongside each histogram share […], re-run `C`, and quote the printed integer […].
>
>   - severity: NIT
>     location: pandas_ta/statistics/ts_reoccur_20.py:239-242
>     problem:  "such a close empties the `length` = 20 windows it sits in […]". §G1 measured 1 / 2 / 19 / 20 / 2 / 1 windows emptied at bars 0 / 1 / 18 / 200 / 398 / 399 — "20" holds only away from the ends, and the parenthetical cites the very run that shows it does not.
>     fix:      "empties the (at most `length` = 20) windows it sits in — 1 / 2 / 19 / 20 / 2 / 1 at bars 0 / 1 / 18 / 200 / 398 / 399, fewer near either end — and nothing earlier".
>
>   - severity: NIT
>     location: docs/TsReoccur20Measured.md:7-41 (the preamble)
>     problem:  "Every number in §A1–§A6, §B, §C, §D, §G, §O, §L and §W … is printed by `python docs/measure_ts_reoccur_20.py`", followed by a four-item list of what does not come from that command […] — which reads as exhaustive. §C1 holds six numbers the script never prints […].
>     fix:      Add a fifth bullet […].
>
> SUMMARY: The mathematics is not in question and never was — `_reoccurring` is bit-equal to a `value_counts()` oracle and to the screen prototype on 11,848 of 11,848 bars over eight frames and at six lengths, the prefix sum over the bad-close mask is indexed correctly, the chunk budget is provably invisible, five mutants are the real column back-dated by a number derived from the edit rather than searched for, the sixth proves the sweep blind where it is blind, and all 223 tests pass twice, once with AVX512F/AVX512_SKX/AVX2/FMA3 off. The wiring is complete across all five touch points and `git status` is clean to the allowed list. What is wrong is what has been wrong for three rounds: a number written to make a sentence read well instead of to report a run. Round 2's fix for the stale character count was good; round 2's fix for the cost ratio replaced one false bracket with another […]. Fix the bracket, fix the four smaller places where a cited source says something other than what the citing sentence claims it says, and this ships.

**Fixes applied, all seven.** A fifth §Z invocation was run and the
section now lists every invocation's ratios and claims only "about 20×";
§E0 names four variants and says why two are out of scope; the
"— unregistered, file one" cell is explained as the generator's
`DEAD_TASKS.get` fallback in both §C1 and the contract; the
`LOT_ZERORET_20` window wording is corrected in the docstring and the
contract; `section_C` prints raw bar counts; the bad-close sentence
carries the six measured counts; the preamble gained a fifth bullet.

---

## Round 4 — REVISE (the round cap; fixes applied, not re-reviewed)

> VERDICT: REVISE
>
> FINDINGS:
>   - severity: MAJOR
>     location: docs/measure_ts_reoccur_20.py:987-994 · docs/TsReoccur20Measured.md:889,896 · pandas_ta/statistics/ts_reoccur_20.py:115-120
>     problem:  §W is the one section whose entire job is to BE the generator's cut, and it is not the generator's cut. `docs/gen_indicator_dictionary.py:290-295` is `d[:150].rsplit(" ", 1)[0] + "…"` — a 150-character prefix *and then a word-boundary trim*. `section_W` models it as `flat[:150]`, prints `150 - len(warning)` = 3 […]. Work the real function: at 148 the cut keeps the sentences, at 149 it keeps them, at **150 it does not** […]. So the usable length is 149 and the slack is TWO. You wrote "THREE characters of slack […]" — and a future editor who spends all three gets a dictionary row reading "…identically 0.0 on continuous…", losing the exact disclosure CLAUDE.md routes a consumer to first. The guard invites the failure it exists to prevent, and it does so because the receipt measured a reimplementation instead of the generator.
>     fix:      In `section_W`, replace `flat[:150]` with the generator's own two-line cut […], print `kept`, assert `warning` is a prefix of it, and compute the slack by search rather than subtraction […]. Then change […] to "2 to spare" […] and the module docstring's "THREE characters of slack" to "TWO characters of slack".
>
>   - severity: MINOR
>     location: docs/MLCompanionContract.md:27
>     problem:  The #103 entry is not parenthesised. Every other delta on that line is its own `( … )`; yours opens `(686 -> 687 / 42 -> 43 \`CONST\` …`, never closes, and swallows the `(` that used to open #102's entry […] so #103 and #102 are one run-on parenthetical and a sibling's record was reformatted by a port that had no business touching it.
>     fix:      Insert `)` immediately after "carries every figure here." and restore the `(` before "685 -> 686" […].
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:983-1003 (§Z)
>     problem:  Two things. The table is headed "the LATEST invocation of `section_Z` on this worktree" — a sixth invocation, run for this review on this worktree, printed `21.66x`, `21.01x`, `22.04x`. The header is now false […]. Worse, the span you state as the reason not to write two significant figures — "Fifteen figures spanning **20.58 … 21.52**" — understates: 22.04 is outside it. […] The traced peak reproduced to the digit […] and monotone was True on all three runs — those claims hold.
>     fix:      Change the header to "the FIFTH invocation of `section_Z`, the last one run from the porting session" and extend the list […]. Leave "about 20×", the monotone ordering and the peak as they are — all three survived the sixth invocation.
>
>   - severity: MINOR
>     location: pandas_ta/statistics/ts_reoccur_20.py:33
>     problem:  "`docs/TsReoccur20Measured.md` A1/A3 measures it bit-equal to both that and a per-window `value_counts()` oracle." §A3 is the lattice section […]. The section that measures bit-equality to both oracles at other lengths is §A2.
>     fix:      Change `A1/A3` to `A1/A2` in that comment.
>
>   - severity: MINOR
>     location: docs/TsReoccur20Measured.md:129-132 (§E0) · tests/test_ts_reoccur_20.py:1030-1032
>     problem:  "the fork sweep's comparator set is **every `Category` indicator at its defaults whose output is unchanged under price ×8** […], so `LOT_ZERORET_60` … is in it by construction". Read that file again: `fork_overlap.py:85-93` keeps a column only if it survives FOUR tests — ≥ 100 finite bars, NaN masks identical under ×8, `np.nanstd(u) != 0` on the canary frame, and the ×8 relative-difference check. You quoted one of the four and then said "by construction". […]
>     fix:      State the filter as the file states it […] and downgrade the conclusion to "so `LOT_ZERORET_60` is in that pool provided it cleared the non-constant test, which `fork_overlap.csv` does not record". Same correction in `test_it_is_not_the_share_of_zero_returns_though_it_is_close`'s docstring.
>
>   - severity: NIT
>     location: docs/TsReoccur20Measured.md:973 (§Z)
>     problem:  "**Traced peak on 400,000 bars**, which is flat in `length` by design" sits directly above a table reading 17.3 / 28.2 / 27.7 / 27.6 MB. 17.3 to 28.2 is a 63% step. The claim you can defend […] is that the peak does not GROW with `length`; the 17.3 is low because at `length` 2 the whole 400,000-row frame is a single chunk […].
>     fix:      Change to "which does not grow with `length` […]", and in §Z's "what survives a re-run" list change "the **flat peak**" to "the peak, to the digit".
>
> SUMMARY: The mathematics is not the problem and never was — Gates A through D hold on the merits, every table in §A1–§A6, §B, §C, §D, §G, §O, §L and §W reproduced to the printed digit on my re-run, the reduced-dispatch run printed 223 passed and the identical feature list you quote, the five wiring touch points are all present, the ledger is correctly untouched, and `git status` is exactly the eleven paths you were allowed. What you did instead is commit the same sin one level deeper. For four rounds the recurring failure has been a number written to make a sentence read well rather than to report a run; you were told that, you fixed §Z twice, and then you left §W — the section whose single purpose is to be the generator's cut — measuring a reimplementation of the generator that is wrong by one character, and printed "THREE characters of slack" as an invitation to a future editor to silently delete the tick-grid disclosure from the one document CLAUDE.md sends a consumer to first. `d[:150]` is not `d[:150].rsplit(" ", 1)[0]`. Read line 294 of the generator and then tell me what survives at 150. Meanwhile the contract entry lost its parentheses and ate a sibling's, §Z's table calls itself "the latest" on a worktree where it is now the fifth of six, the span it offers as its justification has already been broken by my run, and a comment points at §A3 for a measurement §A3 does not contain. None of it is hard. All of it is the same habit: writing the sentence first and the measurement second. Fix the six, re-run `W` and `Z`, and do not write "three" again until the script prints it from the function the generator actually calls.

**Fixes applied, all six.**

1. `section_W` now imports `docs/gen_indicator_dictionary.py` by path and
   calls **its** `desc()` instead of modelling the cut, and finds the
   slack by GROWING the sentence until that function loses it. Printed:
   the warning is 147 characters and can still grow by **2**, so the
   usable length is 149. The receipt's §W and the module docstring now
   say two, and say why it is not three.
2. The contract entry is parenthesised again and #102's `(` restored.
3. §Z's table is headed "the fifth invocation … the last one run from the
   porting session", the sixth invocation's three ratios are listed, and
   the span is **20.58 … 22.04** over eighteen figures.
4. `A1/A3` → `A1/A2` in the module comment.
5. §E0 and the test docstring state all four of `fork_overlap.py`'s
   filters and downgrade "by construction" to "provided it cleared the
   non-constant test, which the CSV does not record".
6. §Z's peak is "does not GROW with `length`", with the reason `length` 2
   reads lower.

⚠ **These six changes are the only ones no reviewer has seen.** The round
cap is four; round 4 returned REVISE, so this task is recorded as
ESCALATED rather than PASS even though no finding is outstanding.

---

## Verification after the last fix

| run | result |
|---|---|
| `python -m pytest tests/test_ts_reoccur_20.py -q` | 223 passed |
| `python docs/measure_ts_reoccur_20_cpu.py` (the module under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`) | 223 passed |
| `python -m pytest tests/test_ts_reoccur_20.py tests/test_ml_companions.py tests/test_readme_counts.py tests/test_wiring_accessors.py -q` | 310 passed |
| `python -m pytest -q` (full suite) | 3 failed, 8,590 passed, 85 skipped |
| `python docs/measure_ts_reoccur_20.py W` | warning 147 chars, slack 2, the ⚠ sentence survives the generator's own `desc()` |
| `python docs/gen_indicator_dictionary.py` | re-run after the docstring edit; the row carries the whole warning |

The three full-suite failures are
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
and `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(CLAUDE.md's documented clean-checkout breaks, which CI deselects or
skips) and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
which lists `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac',
'halflife', 'lumpiness', 'mtd_ret', 'ts_reoccur_20']` — the owed Gate E
row, expected, and a skip rather than a failure under
`GATE_E_PENDING_OK=1` on the way to `dev`.
