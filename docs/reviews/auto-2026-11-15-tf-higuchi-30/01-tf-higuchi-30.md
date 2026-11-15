# TF-HIGUCHI-30 — task log

Mode C, one task, gated by a fresh read-only Fletcher reviewer each round.
Every verdict below is quoted verbatim from the subagent's return. Nothing is
summarised.

⚠ **Four** quoted lines carry an invisible `<!--stale-by-design-->` HTML
comment, and this paragraph deliberately does not retype the string that
makes them necessary. Round 1's §A5 finding quotes an interval list as five
slash-joined fives, and
`tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
reads any five slash-joined numbers in any `.md` file in the fork as a
retyped PINEBI verdict split. The marker is that guard's own escape hatch for
a review record, so each quote stays word for word and declares itself. The
four lines are round 1's NIT, round 3's CRITICAL (twice: the quoted text and
the quoted assertion message) and round 3's SUMMARY. Round 3 found this as a
RED SUITE, not as a style point — see its CRITICAL. ⚠ The guard matches
marker to claim file-wide, not line-wide
(`tests/test_pine_coverage_csv.py:337-339`), so if a later round rewords one
of the four, re-run that test rather than assuming the other three still
cover it.

## Implementation summary

Ported TSFEL's `higuchi_fractal_dimension` over 30 closes as
`pandas_ta/statistics/tf_higuchi_30.py`, column `TFHIGUCHI_30`.

* `_higuchi_fd` walks the window's lag-`k` differences in `k` interleaved
  strands (a stride, not a copy), normalises each strand by
  `(length - 1) / (intervals * k) / k`, averages the strands into `L(k)`, and
  returns the OLS slope of `log(L(k) / L(1))` on `log(1 / k)` for
  `k = 1 .. 5`.
* Two deliberate divergences from the owner's screen prototype, both
  documented and both measured: the logarithm is taken of the RATIO
  `L(k) / L(1)` (which makes an exact binary rescale of the price
  bit-identical instead of a tolerance) and the final dot product is summed
  rather than written `@` (which makes the arithmetic shape-stable, so the
  chunk loop cannot change a value). A mutant with both put back is
  bit-equal to the prototype on all twelve frames, under both numpy
  dispatches.
* Five wiring touch points plus `README.md` (three counts),
  `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md` (698 tagged columns / 336 `SF`) and
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL = 353`).
* Evidence: `docs/TfHiguchi30Measured.md`, `docs/measure_tf_higuchi_30.py`
  (15 sections) and `docs/measure_tf_higuchi_30_cpu.py` (the same sections
  and the test module with `AVX512F AVX512_SKX AVX2 FMA3` disabled).
* Gate E was NOT run here: the launcher runs it, the receipt says "pending",
  and `test_the_gate_e_row_is_owed_and_not_yet_recorded` asserts the ledger
  row is absent.

## Round 1 — REVISE (1 CRITICAL, 1 MINOR, 3 NIT)

> Full suite reproduced (2 failed / 11,145 passed / 85 skipped, exactly the two documented failures), 324 passed on both dispatches, and I re-ran every measured section on both dispatches. Here is what survived.
>
> ```
> VERDICT: REVISE
>
> FINDINGS:
>   - severity: CRITICAL
>     location: docs/TfHiguchi30Measured.md:556 (§G, "What the ±inf fold is for") and tests/test_tf_higuchi_30.py:1126
>     problem:  You wrote a row into the receipt that your own script refutes. §G's table says the
>               fold-deleted mutant is "quiet" on one inf close, because "`inf - finite` is plain `inf`",
>               and the test docstring repeats it — "One infinite close alone does NOT reach it ...
>               which is why this test plants two (§G)". I ran the script you cite as the source,
>               unmodified, on this machine:
>                   with the +-inf fold deleted:
>                     one inf close                RAISED invalid value encountered in divide
>                     two inf closes 5 bars apart  RAISED invalid value encountered in subtract
>               ONE infinite close raises. It raises at `safe / safe[:, :1]` — `inf / inf` is NaN with
>               the invalid flag — which is a site the `L(k)/L(1)` divergence CREATED. The claim is
>               stale: it describes the module before you changed the logarithm's argument, and nobody
>               re-ran §G afterwards. That is the exact defect CLAUDE.md names as this repo's dominant
>               one, planted in the document whose only job is to be evidence, and echoed into a test
>               docstring so a reader is told the weaker precondition is the strong one.
>     fix:      Re-run `python docs/measure_tf_higuchi_30.py G` and transcribe what it prints: the
>               "one inf close" row becomes **RAISED: invalid value encountered in divide**, and name
>               the site (`safe / safe[:, :1]`, reached because the ratio spelling divides an
>               overflowed/infinite `L(k)` by an infinite `L(1)`). Delete the "`inf - finite` is plain
>               `inf`" explanation — it is true of the subtraction and irrelevant to where the raise
>               actually lands. Then rewrite the docstring of
>               `test_the_infinity_fold_is_what_keeps_errstate_quiet` to say one inf suffices, and
>               parametrise its mutant limb over `(250,)` AND `(250, 255)` so the test pins the raise
>               on the single-inf frame too, which is the weaker input and therefore the stronger pin.
>
>   - severity: MINOR
>     location: pandas_ta/statistics/tf_higuchi_30.py:88 and tests/test_tf_higuchi_30.py:40
>     problem:  "§F2 of the Measured doc lists every figure that moves." It does not. §L1's level-shift
>               rows move and are absent from §F2: `+1` reads 8.882e-16 on the default dispatch and
>               1.332e-15 with AVX-512/AVX2/FMA3 off; `+100` reads 1.354e-14 against 1.132e-14. §L1
>               prints them with no dispatch tag at all, so a reader quoting that table quotes a figure
>               whose provenance the document claims to have catalogued and has not. "Every" is one of
>               the six words CLAUDE.md tells you must correspond to a run.
>     fix:      Add the two §L1 shift rows to §F2 with both dispatches and the "quoted / not quoted"
>               column, or drop the word "every" from both docstrings and say "§F2 lists the figures
>               this port quotes that move with the CPU". Prefer the first: the table is cheap and the
>               claim is the point of the table.
>
>   - severity: NIT
>     location: docs/TfHiguchi30Measured.md:228 (§A5)
>     problem:  "Every strand has at least 5 intervals except `k = 4`, where two have 6." Six is not
>               fewer than five. The sentence contradicts itself and the table directly above it, which
>               shows k=4 at 7/7/6/6 and k=5 at 5/5/5/5/5. <!--stale-by-design-->
>     fix:      Say what the table says: "The minimum is 5 intervals, at `k = 5`. `k = 4` is the only
>               spacing whose strands differ in length — two of 7 intervals and two of 6 — which is
>               what the `(N - 1) / (intervals * k)` factor exists to make comparable."
>
>   - severity: NIT
>     location: docs/TfHiguchi30Measured.md:721-724 (§Z)
>     problem:  The §Z table sits under "Every figure below is printed by [the script]", and its time
>               column does not reproduce on the machine that produced it: I measured 0.61 s / 0.74 s
>               against the recorded 0.42 s / 0.66 s. The memory and `fires` columns reproduce exactly.
>               A wall-clock in a table of pinned measurements invites a later reader to treat a
>               scheduler artefact as a regression.
>     fix:      Either drop the time column — the 57.4 MB vs 298.0 MB peak is the figure that justifies
>               the budget — or annotate it "indicative, load-dependent; the peak and the fire count
>               are the reproducible columns".
>
>   - severity: NIT
>     location: pandas_ta/statistics/tf_higuchi_30.py:166-172
>     problem:  `gap[:, m::k]` is sliced twice per strand (once for `.sum`, once for `.shape[1]`), and
>               `curve > 0.0` is evaluated twice — once for `defined`, once for `safe`. Both are cheap,
>               neither is wrong, both make the reader check whether the two spellings can disagree.
>     fix:      Bind `strand = gap[:, m::k]` inside the comprehension's generator (or hoist the
>               interval count, which depends only on `length`, `k` and `m`), and bind
>               `positive = curve > 0.0` once before the two uses.
> ```
>
> SUMMARY: The mathematics is clean and, unusually for this bucket, actually anchored — the `(N-1)/(n*k)/k` normalisation is Higuchi's, `len(range(m,N,k))-1` is his `floor((N-m)/k)` and your `math.fsum` scalar loop proves it to 8.882e-16 rather than asserting it; the ramp reads 1.0000000000000002, Brownian 1.5137, iid 1.9978, and the both-spellings-restored mutant is bit-equal to the prototype on all twelve frames under both dispatches, which is the only thing that makes the 4.219e-15 tolerance mean anything. Gate B's five mutants are live and the mask mutant is honestly declared invisible to the sweep and pinned another way. Gate D's missing shift check is correctly replaced rather than quietly dropped. I re-ran A1, A2, A3, A4, A5, B, C, D, G, L, L4, W, Z, Z2 on both dispatches and every figure in the receipt matched to the digit — except one. You wrote "quiet" into §G for the single-inf mutant and then built a test docstring on top of it, and your own script, in the same section, prints RAISED. The `L(k)/L(1)` divergence you argued so carefully for created a new raise site at the division and you never went back and re-ran the guard section that the divergence invalidated. Everything else here is a receipt; that row is a guess wearing a receipt's clothes, and in this repo that is the whole game. Fix it, fix the "every figure that moves" overclaim that is false by two measurable rows, and this ships.

### Applied, round 1

| finding | applied |
|---|---|
| CRITICAL — stale §G fold row | Re-ran `G`. §G's table now records `one inf close → RAISED: invalid value encountered in divide` at `safe / safe[:, :1]` and `two inf closes → RAISED: … in subtract` at the subtraction, with a ⚠ naming the divide site as one the `L(k)/L(1)` divergence created. The "`inf - finite` is plain `inf`" line now explains why the subtraction is quiet rather than why nothing raises. `test_the_infinity_fold_is_what_keeps_errstate_quiet` is parametrised over `(250,)` and `(250, 255)`, and its docstring states both routes. The module gained a comment at the fold stating both. |
| MINOR — "§F2 lists every figure that moves" | The three §L1 shift rows (+1, +100, -50) were added to §F2 with both dispatches and the "quoted" column; §L1's own table now tags the two that move; §F2 gained a ⚠ **Scope** paragraph stating that it covers the figures the port QUOTES and not every number the script prints; and both docstrings now say §F2 "tabulates the figures this port quotes, what each reads on the two dispatches, and which of the two is quoted". |
| NIT — §A5 self-contradiction | Rewritten: "The minimum is **5** intervals, at `k = 5`. `k = 4` is the only spacing whose strands differ in length — two of 7 intervals and two of 6 …". |
| NIT — §Z wall-clock | The time column is now a range (`~0.4–0.6 s` / `~0.6–0.8 s`) with a ⚠ note giving both observed pairs and naming the peak and the fire count as the reproducible columns. |
| NIT — double slice / double compare | `strand = gap[:, m::k]` and `positive = curve > 0.0` are each bound once. Re-ran §A1 after the refactor: byte-identical output (worst 3.996803e-15, 6,687 bars differ, both-spellings mutant bit-equal on all twelve frames), so the refactor is behaviour-preserving. |

## Round 2 — REVISE (1 CRITICAL, 5 MINOR)

> Everything measurable, I measured: 325/325 on both dispatches, the full suite, and every section of both measure scripts on both dispatches.
>
> ReportFindings is not the contract here — the required shape is the text block below.
>
> ```
> VERDICT: REVISE
> FINDINGS:
>   - severity: CRITICAL
>     location: docs/TfHiguchi30Measured.md:461-463 (§F1 — the runs)
>     problem:  The Gate F receipt table is stale on every row. I ran all three.
>               `python -m pytest tests/test_tf_higuchi_30.py -q` → **325 passed**, not 324.
>               `python docs/measure_tf_higuchi_30_cpu.py` → **325 passed**, not 324.
>               `python -m pytest -q` → **2 failed, 11146 passed, 85 skipped**, not 11,145.
>               Round 1's own CRITICAL fix added the `(250,)`/`(250,255)` parametrisation to
>               `test_the_infinity_fold_is_what_keeps_errstate_quiet`, which is exactly the
>               +1, and nobody re-read §F1 afterwards. You patched a measured-after-the-fact
>               claim by writing a new one. This is the repo's named dominant defect, in the
>               one table whose entire job is to be a transcript of a run.
>     fix:      Set the three §F1 cells to 325 / 325 / "2 failed, 11,146 passed, 85 skipped",
>               having re-run all three, and re-read §F1 as the LAST edit of any future round
>               that adds, removes or parametrises a test.
>   - severity: MINOR
>     location: docs/TfHiguchi30Measured.md:30-31 (the Verdict paragraph)
>     problem:  "it reproduces the textbook dimensions of a line, a Brownian path and iid
>               noise to three decimals". §A4 measures 1.5137 against 1.5 and 1.9978 against
>               2.0. That is agreement to 0.014 and 0.0022 — the Brownian figure does not
>               survive even TWO decimals. The section below is honest about the bias ("the
>               30-bar / k ≤ 5 ladder costs variance, not very much bias"); the headline
>               verdict quietly upgrades it to a precision the port does not have.
>     fix:      Replace "to three decimals" with the measured numbers and their errors:
>               "…and it reads 1.0000000000000002, 1.5137 and 1.9978 against the textbook
>               1, 1.5 and 2.0 — within 0.014 of the Brownian anchor and 0.0022 of the iid
>               one, the ladder's bias, measured in §A4."
>   - severity: MINOR
>     location: pandas_ta/statistics/tf_higuchi_30.py:313 (function `__doc__`, Calculation
>               block) and tests/test_tf_higuchi_30.py:49 (docstring item 3)
>     problem:  Both say the column is NaN on "a window of period exactly 2 or 4, where L(2)
>               and L(4) are zero while L(1) is not", and cite §G. For period exactly 4 that
>               is false: on a,b,c,d,a,b,c,d the lag-2 differences are |c-a| and |d-b|, so
>               L(2) is NOT zero — only L(4) is. And §G measures ONE such frame,
>               `alternating`, which is period 2; no period-4 window is measured anywhere in
>               the port. The module's own inline comment at line 181 gets it right
>               ("a period-2 window at k = 2 and 4"); the two docstrings drifted off it and
>               generalised to a case nobody ran.
>     fix:      In both places say what was measured: "a window of period exactly 2, where
>               L(2) and L(4) are zero while L(1) is not (measured [29, 0, 3.222, 0, 1.16],
>               §G)", and if the period-4 case is worth keeping, state it separately and
>               correctly — "a window of period exactly 4, where L(4) alone is zero" — and
>               add the frame to §G's table so it is a run and not an inference.
>   - severity: MINOR
>     location: pandas_ta/statistics/tf_higuchi_30.py:102 (module docstring, CAUSALITY)
>     problem:  "…and by re-running the sweep with the chunk budget cut to one row per
>               chunk." No sweep is re-run at a cut budget. `test_prefix_truncation_holds_
>               across_a_chunk_boundary` (budgets 30 and 210) and §B3 run PREFIX TRUNCATION
>               plus equality with the default run — never `_caught_at`. CLAUDE.md's Gate B
>               says in terms that "prefix truncation alone proves nothing", so describing it
>               as "the sweep" overstates the strongest causality limb the port has, in the
>               shipped module's own docstring.
>     fix:      Say what runs: "…and by re-running the prefix-truncation limb and the
>               equality with the default run at chunk budgets of one and seven rows (§B3),
>               on top of `test_the_arithmetic_does_not_depend_on_the_block_shape`, which is
>               what actually makes the chunk loop safe."
>   - severity: MINOR
>     location: docs/measure_tf_higuchi_30.py:2-4 (module docstring)
>     problem:  "Every number in `docs/TfHiguchi30Measured.md` and in the docstrings of
>               `pandas_ta/statistics/tf_higuchi_30.py` and `tests/test_tf_higuchi_30.py` is
>               printed by this script." It is not. §F1's three pytest counts are not printed
>               by it (and are the ones that went stale — see the CRITICAL). Neither is §F2's
>               "dispatchable features still enabled" list (that is the `_cpu` script) nor the
>               whole Gate E block (0.5231, 0.5298, 0.5207, 0.5015, 398,849 bars, 687
>               comparators), which is quoted from the issue. The Measured doc hedges this
>               correctly at line 25 ("except Gate E's"); the script that claims to BE the
>               evidence does not, and an "every" that is false is the sentence class
>               CLAUDE.md polices.
>     fix:      Hedge it the way the receipt already does: "Every measured number in
>               `docs/TfHiguchi30Measured.md` and in the two docstrings is printed by this
>               script, EXCEPT the pytest counts of §F1, the enabled-dispatch list of §F2
>               (`docs/measure_tf_higuchi_30_cpu.py`) and the Gate E block, which is quoted
>               from issue #115 and measured on the prototype."
>   - severity: MINOR
>     location: docs/reviews/auto-2026-11-15-tf-higuchi-30/00-manifest.md:41
>     problem:  "Every round's verdict is quoted verbatim in `01-tf-higuchi-30.md`, and
>               `99-summary.md` carries the table." Neither file exists; the folder holds
>               only `00-manifest.md`. Every sibling port commits all three
>               (`auto-2026-11-15-tf-zero-cross-20/` has `00-manifest.md`,
>               `01-tf-zero-cross-20.md`, `99-summary.md`), so the deliverable the issue asks
>               for is incomplete and the manifest asserts in the present tense a file that
>               is not there.
>     fix:      Before the port is committed, write `01-tf-higuchi-30.md` with round 1's and
>               round 2's verdicts quoted verbatim and what was applied for each finding, and
>               `99-summary.md` with the round/verdict/finding-count table, matching the
>               shape of `docs/reviews/auto-2026-11-15-tf-zero-cross-20/`.
> SUMMARY: The mathematics is the best thing in this port and I am not going to pretend
> otherwise by listing it as a finding — Higuchi's normalisation, the 1-based/0-based
> interval identity, the three oracles, the two deliberate divergences and the reversal
> symmetry all survive scrutiny, and I re-ran every section of both measure scripts on both
> dispatches: §A1 (6,687 / 3.996803e-15 default, 6,593 / 4.218847e-15 AVX-off), §A2, §A3,
> §A4, §A5, §B (288 catches, 0 misses, mask mutant dead and caught by the planted NaN), §C,
> §D, §G, §L, §L4, §W, §Z and §Z2 — every digit in the receipt and in both docstrings
> reproduced. Round 1's five fixes all landed and the `_higuchi_fd` refactor is
> behaviour-preserving exactly as claimed. And then you shipped a Gate F table that says 324
> when the suite says 325, twice, plus a full-suite count off by one — the stale number
> created by your own round-1 patch, in the one table that exists solely to be a transcript.
> You fixed a measured-after-the-fact claim and wrote a new one three sections later. Add a
> verdict line that promises three decimals on a Brownian anchor that is off by 0.014, a
> period-4 case stated wrongly and never run, an "Every number … is printed by this script"
> that is false four ways, a causality claim that calls prefix truncation "the sweep", and a
> review folder missing two of its three files, and the pattern is unmistakable: the
> arithmetic is measured and the PROSE ABOUT the arithmetic is still being typed from memory.
> Fix the six, re-read §F1 last, and this ships.
> ```

### Applied, round 2

| finding | applied |
|---|---|
| CRITICAL — stale §F1 counts | §F1 is now the LAST edit of the round. All three runs re-done after every other change: **326 passed**, **326 passed** on the AVX-disabled dispatch, and **2 failed, 11,147 passed, 85 skipped** on the full suite. (326, not the reviewer's 325, because this round added the period-4 guard test below.) §F1 gained a ⚠ saying these three cells are the one part of the document no script prints, naming both drifts (324 → 325 → 326) and instructing a later round to re-read the table last. |
| MINOR — "three decimals" | The verdict paragraph now gives the readings and their errors: 1.0000000000000002, 1.5137 and 1.9978 against 1, 1.5 and 2.0 — within 0.014 and 0.0022, named as the ladder's bias and pointed at §A4. |
| MINOR — the period-4 case | Measured rather than restated. §G now builds a 30-close window of period 4 (`100, 101, 103, 102`) and prints `L = [43, 14.5, 4.893, 0, 1.7168]`, zero at `k = 4` ALONE, fires 0, prototype fires 0. `test_a_period_four_window_is_a_gap_but_for_a_different_reason` pins it, §G's table has a third row and a ⚠ saying the two cases are not the same, and both docstrings now state the three measured routes separately. |
| MINOR — "re-running the sweep" at a cut budget | The module's CAUSALITY paragraph now says the budget runs are the prefix-truncation limb and the equality with the default run, names `test_the_arithmetic_does_not_depend_on_the_block_shape` as what actually makes the chunk loop safe, and adds a ⚠ repeating `CLAUDE.md`'s "prefix truncation alone proves nothing". |
| MINOR — "Every number … is printed by this script" | Hedged with the three named exceptions: §F1's pytest counts, §F2's enabled-dispatch list (the `_cpu` script prints it) and the Gate E block, which is quoted from issue #115 and was measured on the prototype. |
| MINOR — missing `01-` and `99-` files | This file and `99-summary.md` are written, with both rounds' verdicts verbatim. |

## Round 3 — REVISE (1 CRITICAL, 2 MINOR, 1 NIT)

> VERDICT: REVISE
>
> FINDINGS:
> ```
>   - severity: CRITICAL
>     location: docs/reviews/auto-2026-11-15-tf-higuchi-30/01-tf-higuchi-30.md:87
>               and docs/TfHiguchi30Measured.md:466, 475 (§F1)
>     problem:  You wrote the ⚠ yourself. You wrote, in bold, "Re-read this table LAST in any round
>               that touches the test module." Then you added a FILE after the last run and the table
>               went stale for the third consecutive round — and this time it is not only prose, it is
>               a red suite. I ran it:
>                   python -m pytest -q
>                   -> 3 failed, 11146 passed, 85 skipped
>                   FAILED tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split
>               §F1 says "**2 failed, 11,147 passed, 85 skipped**" and then says "The two failures are
>               both expected and neither is this port's arithmetic." There are three, and the third is
>               YOUR file. Round 2's own fix — writing `01-tf-higuchi-30.md` to quote the earlier
>               verdicts verbatim — carried round 1's NIT text through verbatim, including
>               "shows k=4 at 7/7/6/6 and k=5 at 5/5/5/5/5" on line 87. `NAMELESS_SPLIT` in <!--stale-by-design-->
>               `tests/test_pine_coverage_csv.py:57` is `\b\d+(?:/\d+){4,}\b`; five slash-joined
>               numbers, so the guard reads it as a retyped PINEBI verdict split:
>                   AssertionError: these documents retype the verdict split instead of pointing at
>                   docs/CompletedWork.md: {'docs/reviews/auto-2026-11-15-tf-higuchi-30/01-tf-higuchi-30.md':
>                   [('5/5/5/5/5', None)]} <!--stale-by-design-->
>               CLAUDE.md deselects exactly ONE test in CI (`test_regenerating_reproduces_the_committed_rows`)
>               and skips the owed Gate E row under `GATE_E_PENDING_OK=1`. This one is neither, so the PR
>               goes red in `ci.yml` and the merge queue switches auto-merge off. Gate F is not green.
>               And the ⚠ you added is itself part of the failure: it says the cells "go stale the moment
>               a test is ADDED OR PARAMETRISED", which is why you did not re-run after adding a
>               DOCUMENT. The guard you tripped is a documents guard. Six rounds of arithmetic measured
>               to the last bit, and the deliverable is a suite that does not pass.
>     fix:      Three steps, in order, and do not reorder them. (1) The guard ships its own escape hatch
>               for exactly this case — `STALE_BY_DESIGN = "<!--stale-by-design-->"` at
>               `tests/test_pine_coverage_csv.py:268`, whose comment says "review records narrate the
>               numbers that WERE wrong". Append `<!--stale-by-design-->` to line 87 of
>               `01-tf-higuchi-30.md` so the quote stays verbatim and declares itself, or reword that one
>               clause so no five-number split exists; the
>               marker is the better choice because the round-1 verdict must stay quoted word for word.
>               (2) Re-run `python -m pytest -q`, `python -m pytest tests/test_tf_higuchi_30.py -q` and
>               `python docs/measure_tf_higuchi_30_cpu.py` and transcribe all three §F1 cells from those
>               runs — the two module cells currently read correctly (I measured 326 passed on both
>               dispatches) and the full-suite cell becomes "2 failed, 11,147 passed, 85 skipped" once
>               the guard is green, so re-read it rather than assuming it. (3) Widen the ⚠ at
>               docs/TfHiguchi30Measured.md:468-473 from "the moment a test is added or parametrised" to
>               "the moment a test is added or parametrised OR a document is added to the worktree —
>               several suite guards scan every `.md` file in the fork", and add the review folder to the
>               list of things that must be written BEFORE the §F1 runs, not after.
>
>   - severity: MINOR
>     location: tests/test_tf_higuchi_30.py:82-83 (header item 6), against line 118
>     problem:  "`_higuchi_fd` on one row is asserted bit-equal to the same row inside a 300-row block."
>               There is no 300-row block anywhere in this port. The test that makes the claim,
>               `test_the_arithmetic_does_not_depend_on_the_block_shape`, builds `_windows(FRAMES[name]())`
>               on a 400-bar frame at `length` 30 — 371 rows. §Z2 of the receipt runs the same check on a
>               1,500-bar frame — 1,471 rows. Neither is 300. Line 118 of the same docstring then says
>               "Every number above is printed by `python docs/measure_tf_higuchi_30.py`", which makes
>               the file assert that a number no section prints was printed. A specific count that
>               corresponds to no run is the sentence class CLAUDE.md polices, and it is sitting in the
>               header of the test module that is supposed to be the port's inventory of measurements.
>     fix:      Say what the test runs: "`_higuchi_fd` on one row is asserted bit-equal to the same row
>               inside the whole 371-row block of a 400-bar frame (§Z2 runs the same check on 1,471
>               rows)". Or drop the count — "inside the whole block" is the property being pinned and
>               needs no number.
>
>   - severity: MINOR
>     location: docs/TfHiguchi30Measured.md:496-500 (§F2, the ⚠ Scope paragraph)
>     problem:  The paragraph contradicts itself inside three sentences. It opens "The table below covers
>               the figures this document and the docstrings QUOTE, read on both dispatches", then
>               excludes "the per-frame columns of §A1 and §C" — and §C's per-frame columns are quoted,
>               as digits, in three places: the function `__doc__` ("the column runs 0.9458 .. 2.1941",
>               line 291-292 and again at 337) and `test_every_reading_is_finite_and_inside_a_loose_sanity_band`'s
>               docstring. Also quoted in docstrings and absent from the table entirely: §L4's -0.8901 /
>               0.4721 / 0.8284 / 0.7151, §Z's 57.4 MB and 298.0 MB, §W's 133 and 17, §A5's 0.4190. Round
>               1 already ruled on this exact claim ("§F2 lists every figure that moves"); the fix added
>               a Scope hedge that re-states the overclaim in a weaker coat. I checked the omitted
>               figures under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` and every one of
>               them reproduces identically, so nothing is WRONG — only the sentence describing the
>               table's coverage is, which is the same defect in a smaller size.
>     fix:      Make the sentence match the table: "The table below covers every figure that MOVES
>               between the two dispatches, plus the equalities. Figures quoted in the receipt or the
>               docstrings that are identical on both dispatches and are therefore not listed: §C's
>               per-frame min/max (0.9458 .. 2.1941), §L4's Spearman figures, §Z's two peaks, §W's 133 /
>               17 and §A5's 0.4190 — each verified on both dispatches." Keep the closing sentence about
>               the "—" rows; it is the only part of the paragraph that is true as written.
>
>   - severity: NIT
>     location: pandas_ta/statistics/tf_higuchi_30.py:186-188
>     problem:  Round 2 made you measure the period-4 route and state it in both docstrings. The inline
>               comment on the guard still lists two of the three: "a flat window at every k, a period-2
>               window at k = 2 and 4". A reader of the GUARD — the one person who most needs to know
>               that `L(k) > 0` at every spacing is load-bearing and not belt-and-braces — gets the
>               version that was wrong two rounds ago.
>     fix:      Add the third: "… a flat window at every k, a period-2 window at k = 2 and 4, a period-4
>               window at k = 4 alone (§G measures all three)."
> ```
> SUMMARY: The arithmetic is still the best thing here and I will not list it as a finding: I re-ran A1, A2, A3, A4, A5, B, C, D, G, L, L4, W, Z and Z2 on both dispatches and every single digit reproduced — 6,687 / 3.996803e-15 default against 6,593 / 4.218847e-15 AVX-off, the loop oracle at 8.881784e-16, lstsq at 3.108624e-15 default and 2.442491e-15 off, the line at 1.0000000000000002, Brownian 1.5137, iid 1.9978, 288 catches and no misses, the mask mutant dead on clean frames and caught by the planted NaN, 28-of-200 for `@` and 0 for the shipped sum, 59/4.441e-16 reversal windows default and 71/6.661e-16 off, 5.906386e-14 and 5.750955e-14 for the inexact rescale, 57.4 against 298.0 MB. Round 2's period-4 fix is correct and it earns it: `L(4)` is exactly zero because the lag-4 differences are the same float, `L = [43, 14.5, 4.893, 0, 1.7168]` reproduces to the digit, and the test pins `[i for i, v in enumerate(curve) if v == 0.0] == [3]`, which is the distinction and not a restatement. All six round-2 fixes landed. And then you did it a third time, in the same table, after writing the warning telling your successor not to. You added a document after the last run, that document trips `test_no_other_document_retypes_the_split` on a `5/5/5/5/5` you copied out of round 1's own NIT, and §F1 now certifies "2 failed, 11,147 passed" and "neither is this port's arithmetic" while the suite says three failures and one of them is yours — in CI, not deselected, not skipped. The guard even hands you the fix in a constant named `STALE_BY_DESIGN`. You measured the fractal dimension of a Brownian path to four decimals on two CPU dispatches and did not run pytest once after your last edit. <!--stale-by-design-->

### Applied, round 3

| finding | applied |
|---|---|
| CRITICAL — this file turned the suite red, and §F1 certified a green it did not have | The **four** lines quoting a five-number interval list now carry `<!--stale-by-design-->`, which is `tests/test_pine_coverage_csv.py`'s own escape hatch for a review record, so the round-1 verdict stays quoted word for word and the guard is green. A ⚠ at the top of this file says why the marker is there. §F1's three cells were then re-transcribed from fresh runs as the LAST edit, and its ⚠ now warns that **a new document** turns the suite red just as readily as a new test, with the instruction to write the review folder BEFORE the §F1 runs. |
| MINOR — the non-existent "300-row block" | Replaced with what runs: one row against the whole block of a 400-bar frame, with §Z2's 1,500-bar run named as the other size. No row count is quoted, because the property being pinned needs none. |
| MINOR — §F2's self-contradicting Scope paragraph | Rewritten to say the table covers every figure that MOVES plus the bit-equalities, and to name the quoted figures that are IDENTICAL on both dispatches and therefore absent: §C's 0.9458 .. 2.1941, §L4's Spearman figures, §Z's 57.4 / 298.0 MB, §W's 133 / 17 and §A5's 0.4190. Each of those was re-run under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` in this session before the sentence was written. |
| NIT — the guard comment listed two of three routes | The inline comment now names all three and says why the guard has to read every spacing rather than only `L(1)`. |

## Round 4 — PASS (3 MINOR, 1 NIT)

Round 4 is the last round the review loop allows, and it is the round that
PASSed: no CRITICAL, no MAJOR. Its four findings were applied anyway, because
all four are sentences about **where a number came from** and leaving a known
-false provenance claim in a receipt is the defect this port spent three
rounds removing. None of them touches code or test logic.

> Everything measurable, I measured: the full suite, the port module on both dispatches, and every section of both measure scripts on both dispatches.
>
> ```
> VERDICT: PASS
>
> FINDINGS:
>   - severity: MINOR
>     location: docs/TfHiguchi30Measured.md:16-25 (the "Every figure below is printed by" block)
>     problem:  The receipt opens with "Every figure below is printed by [four commands] ... except
>               Gate E's" and then refutes itself twice over. §F1's own ⚠ at line 468 says, in bold
>               type, that its three cells are "the one part of this document that no section of
>               docs/measure_tf_higuchi_30.py prints" — and `python -m pytest -q` is not one of the
>               four commands listed either, so the full-suite cell is printed by nothing on that
>               list. Three more figures below are borrowed from a SIBLING port's receipt and printed
>               by neither script: §L2:680's "a time reversal moves [tf_dfa_100] by up to 0.3698",
>               §A4:185's "puts the iid centre at 0.63", and §G:584's "tf_dfa_100 blanks 100 windows
>               for a zero close". I checked all three against docs/TfDfa100Measured.md (0.3698 at
>               line 919, iid normal 0.6289 at line 251, "100 for the rest" at line 804) — the
>               numbers are right; the sentence claiming where they came from is not. Round 2 found
>               this exact sentence class in the measure script's docstring and the fix hedged the
>               SCRIPT while quoting this very line as the model of how to do it. It was not the
>               model. "Every" is one of the six words CLAUDE.md tells you must correspond to a run,
>               and this is its fourth outing in four rounds.
>     fix:      Extend the clause to the exceptions the document already knows about: "...except
>               §F1's pytest counts (which `python -m pytest` prints and §F1 flags), the Gate E
>               block (quoted from issue #115, measured on the prototype), and the three
>               `tf_dfa_100` figures quoted for contrast in §A4, §G and §L2, which come from
>               `docs/TfDfa100Measured.md`." Cite that file's section beside each of the three.
>
>   - severity: MINOR
>     location: tests/test_tf_higuchi_30.py:120-122 (header closing line), against line 29
>     problem:  "Every number above is printed by `python docs/measure_tf_higuchi_30.py`, and by
>               `python docs/measure_tf_higuchi_30_cpu.py <section>` for the AVX-disabled dispatch."
>               Item 2, nine lines up, quotes "the expression Gate E's **0.5231** was measured on".
>               Neither script prints 0.5231 — the measure script's OWN docstring, lines 3-11, lists
>               it first among the three things it does not print. So the test module asserts in
>               prose that a figure was printed by a script that declares it is not. Round 2's
>               finding fixed the script's claim and left the identical claim standing one file over.
>               Everything else in that header I verified printed and reproducing to the digit, on
>               both dispatches, which is what makes the one exception avoidable rather than
>               forgivable.
>     fix:      Hedge it the way the script now does: "Every number above is printed by
>               `python docs/measure_tf_higuchi_30.py`, and by
>               `python docs/measure_tf_higuchi_30_cpu.py <section>` for the AVX-disabled dispatch,
>               EXCEPT Gate E's 0.5231, which is quoted from issue #115 and was measured on the
>               prototype; `docs/TfHiguchi30Measured.md` carries the tables."
>
>   - severity: MINOR
>     location: docs/reviews/auto-2026-11-15-tf-higuchi-30/01-tf-higuchi-30.md:7-8, against :361
>     problem:  Two sentences in the same file give two different counts of the same thing, and both
>               are wrong. The ⚠ at line 7 says "One quoted line carries an invisible
>               `<!--stale-by-design-->` HTML comment"; the round-3 applied row at line 361 says
>               "The two lines quoting a five-number interval list now carry" it. Four lines carry
>               it — 95, 278, 283 and 355 — and FIVE lines carry a five-slash-joined number (8, 95,
>               278, 283, 355). Worse, line 8 is one of them: the ⚠ that exists to declare the
>               marker retypes the literal itself and does NOT carry the marker. The suite is green
>               only because `test_no_other_document_retypes_the_split` matches marker to claim
>               file-wide rather than line-wide (tests/test_pine_coverage_csv.py:337-339), so line 8
>               is covered by line 95's copy of the identical literal. Reword round 1's quote on line
>               95 — the one thing a future round might legitimately do — and line 8 turns the suite
>               red on its own. This is the round-3 CRITICAL's own blast radius, counted from memory.
>     fix:      Append `<!--stale-by-design-->` to line 8 so the ⚠ declares itself rather than
>               borrowing another line's declaration, and replace the count with what is there:
>               "⚠ Four quoted lines (95, 278, 283, 355) and this warning carry an invisible
>               `<!--stale-by-design-->` comment". Fix line 361 to say the same number.
>
>   - severity: NIT
>     location: docs/reviews/auto-2026-11-15-tf-higuchi-30/00-manifest.md:34 (Phase 3)
>     problem:  "One task, touching nine files that overlap (module, three wiring files, two docs,
>               two test files, two measure scripts)". The parenthetical enumerates ten, and
>               `99-summary.md`'s own "Files touched" table lists thirteen paths — fifteen files once
>               the review folder is expanded. Nine corresponds to nothing. It is a planning note and
>               it costs nobody anything, which is the only reason it is a NIT rather than another
>               line in the same tally above.
>     fix:      Either drop the number ("touching the module, three wiring files, three generated
>               docs, the receipt, two test files and two measure scripts") or make it thirteen and
>               match `99-summary.md`'s table.
> ```
>
> SUMMARY: I will not list the arithmetic as a finding, because for the fourth round running it does not deserve one: I re-ran A1, A2, A3, A4, A5, B, C, D, G, L, L4, W, Z and Z2 on both dispatches and every digit reproduced — 6,687 / 3.996803e-15 default against 6,593 / 4.218847e-15 with AVX-512/AVX2/FMA3 off, the sum of the per-frame columns landing on 13,259 and 6,687 exactly as the text claims, the fsum loop at 8.881784e-16, lstsq at 3.108624e-15 / 2.442491e-15, the line at 1.0000000000000002 on all 1,471 bars, Brownian 1.5137 and iid 1.9978, 288 catches and no misses with the mask mutant dead on clean frames and caught by the planted NaN, 28-of-200 for `@` and 0 for the shipped sum, 59/4.441e-16 reversal windows default and 71/6.661e-16 off, 5.906386e-14 / 5.750955e-14, 0.4190 for the KMAX-10 mutant, 57.4 against 298.0 MB, and every one of §F2's "identical on both dispatches" claims — §C's 0.9458 .. 2.1941, §L4's -0.8901 / 0.7151, §W's 133 / 17, §A5's 0.4190 — verified under the disabled dispatch, which is the first time in four rounds that a Scope sentence in this document has been true. §F1 is finally a transcript: 326, 326, and `2 failed, 11147 passed, 85 skipped` in 279.78 s, the two failures being exactly `test_regenerating_reproduces_the_committed_rows` and the owed Gate E row, and the review folder green under the document guard it turned red last round. Gate A's 0-based `len(range(m,N,k))-1` is Higuchi's 1-based `floor((N-m)/k)` and I re-derived it rather than taking your word; both divergences are slope-preserving in exact arithmetic and the ratio spelling genuinely buys exact bit-equality under a binary rescale; the guard reads every spacing because period-2 and period-4 windows need it to; nothing pins a count of last bits. What is left is the same disease in its mildest form yet: four sentences about where numbers came from, written from memory. Your receipt says every figure in it is printed by your script and then tells you, in its own §F1, that three are not; your test header says every number above is printed by a script whose docstring names the exception; and the warning you wrote to explain one stale-by-design marker miscounts the markers in its own file and forgets to declare itself. Fix those four lines in whatever round records this verdict. The code and the measurements clear the bar — barely, and only because the prose that failed this time cannot ship a wrong number to a miner.

### Applied, round 4 (after the PASS, prose only)

| finding | applied |
|---|---|
| MINOR — the receipt's "Every figure below is printed by" | Replaced with a numbered list of **four** exceptions: §F1's pytest counts, the Gate E block (quoted from issue #115, measured on the prototype), §F2's enabled-dispatch banner, and the three `tf_dfa_100` figures quoted for contrast — each with its section in `docs/TfDfa100Measured.md`, re-read in this session to confirm 0.6289 / 0.6292 (§A5, §A5b), 0.3698 (§L5) and "101 for a NaN and 100 for the rest" (§G). |
| MINOR — the test header's "Every number above is printed by" | Hedged with the one exception, Gate E's 0.5231, naming the measure script's own docstring as the place that already declares it. |
| MINOR — the marker count in this file | The ⚠ now says **four** marked lines, names which four, and no longer retypes the five-slash literal itself (so it needs no marker of its own); it also records that the guard matches marker to claim file-wide and not line-wide, with the instruction to re-run that test if a later round rewords one of the four. The round-3 applied row says four as well. |
| NIT — the manifest's "nine files" | The count is dropped; the sentence enumerates the lanes and points at `99-summary.md`'s table as the authoritative list. |
