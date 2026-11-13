# ts-imq-20 — task log

## Implementation

`pandas_ta/statistics/ts_imq_20.py`, column `TS_IMQ_20`:

    x          = the trailing 20 simple returns
    TS_IMQ_20  = (argmax(cumsum(|x|) / sum(|x|) >= 0.5) + 1) / 20

tsfresh `feature_calculators.index_mass_quantile(q=0.5)` applied to the
window's returns, as PandasTa #99 states it. Written as two `length`-pass
loops over a `sliding_window_view` rather than `np.cumsum(aw, axis=1)`
(peak would grow with `length`) or a global `np.cumsum` differenced per
window (lossy and non-local — measured: that spelling returns NaN on all
1,780 later bars at a 1e+100 spike). The window total is accumulated in the
same sequential order as the scan, which is what makes the last ratio
exactly 1.0 and the crossing always findable.

Wiring: `statistics/__init__.py`, `Category["statistics"]`,
`core.py` accessor, `tests/test_ts_imq_20.py`,
`tests/test_altport2_ports.py::CATEGORY_TOTAL` 331 → 332. README 331 → 332 /
339 → 340 / statistics 40 → 41; `docs/IndicatorDictionary.md` regenerated;
`docs/MLCompanionContract.md` 676 → 677 tagged / 318 → 319 `SF`.

Receipt: `docs/TsImq20Measured.md`. Measurement script:
`docs/measure_ts_imq_20.py` (sections A B C D G O Z). CPU-dispatch re-run:
`docs/measure_ts_imq_20_cpu.py`.

---

## Round 1 — REVISE

> SUMMARY: "The mathematics is the best-evidenced thing in this folder …
> Every single number I re-derived matched, including the gitignored
> screen's. That is not the problem. The problem is that you built a
> cathedral of measurement and then, in the two places where measuring was
> inconvenient, you wrote the answer down instead."

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | MAJOR | `test_an_arbitrary_price_rescale_is_within_one_position` asserted `eq == shared == FIRED` — an exact 1,480-of-1,480 bit-equal count — on the path its own docstring called "NOT bit-identical by construction", and claimed to assert only a tolerance. | **FIXED.** Assertion reduced to masks + `shared == FIRED` + `mx <= ONE_POSITION` + a `eq >= 1400` band; docstring rewritten to say what is asserted. |
| 2 | MAJOR | §A5's "the source's `+ 1`" row was a tautology: the script computed `no_plus_one = base - 1/LENGTH` and the test asserted `_spearman(base, base - ONE_POSITION) == approx(1.0)`. Both pass on a module that returns garbage. | **FIXED.** `_no_plus_one_variant` built from scratch in script and test. It measures what the `+ 1` buys: the heavy-tailed frame's variant reads **0.0** on 6 bars where the column reads 0.05, and the shift spans [0.049999999999999933, 0.050000000000000044] — not exactly 0.05, hence a tolerance. |
| 3 | MINOR | Three tests never called `ts_imq_20`. | **FIXED.** The backstop test is now two mutants (`Q = 1.5`, then also dropping `& found`); the iid-level test drives the shipped function. |
| 4 | MINOR | The docstring claimed ×8/×64 at `length` 2/5/60/250 where only ×8 was measured. | **FIXED.** ×64 added to the script loop and the test parametrisation; both now measured. |
| 5 | MINOR | Wall-clock ms differed between the module docstring and §Z. | **FIXED.** The module docstring now carries no timing at all; §Z is the single site. |
| 6 | NIT | An uncheckable comparative ("stronger Gate A result than the fork's other `ts_*` ports") and an unflagged computed 800 MB. | **FIXED.** Comparative deleted; 800 MB labelled "computed, not traced". |
| 7 | NIT | The two-point rescale test REQUIRED the frame to move. | **FIXED.** Hard bound kept, the "it does move" half dropped. |

## Round 2 — REVISE

> SUMMARY: "All seven round-1 findings are genuinely fixed … What keeps this
> at REVISE is that you fixed the symptom of round-1 finding #1 and not the
> disease."

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | MAJOR | Three Gate A tests still pinned an exact 1,480-of-1,480 bit-equal count on the `two-point` tie frame against oracles whose summation order differs from the module's (`math.fsum`, `Fraction`, the prototype's pairwise `A.sum(1)`), and §A2/A3 defended it as "structural, not luck" — contradicted by §D2. | **FIXED.** `TIE_FRAME` excluded from all three; new `test_the_tie_frame_is_held_to_a_tolerance_and_not_to_the_bits` holds all three oracles there to one position. Bit-equality is asserted on all nine frames only for `_source_windowed`, whose Python `sum` + `np.cumsum` IS the module's accumulation order. The ladder and quiet-frame prototype checks were loosened for the same reason. |
| 2 | MINOR | The log-return test claimed "the rest move by one position" while asserting `3 * ONE_POSITION`, and no max\|d\| was printed. | **FIXED.** The script now prints max\|d\| (0.050000000000000044 = 1.00 positions) and the assertion is `ONE_POSITION`. |
| 3 | MINOR | §A4's two mutant counts were not printed by the script. | **FIXED.** The script's A4 now loads both mutants and prints the three rows. |
| 4 | NIT | §Z quoted the fastest of several observed timings. | **FIXED.** Three runs per row, reported as a range. |
| 5 | NIT | "exactly 0.05" in three places against a printed 0.050000000000000044, while §A5 insisted the same-sized `+1` shift was NOT exactly 0.05. | **FIXED.** One standard everywhere. |
| 6 | NIT | The restatement test asserted `< 0.5` against a documented maximum of 0.1034. | **FIXED.** Band tightened to 0.25. |

## Round 3 — PASS (with five MINOR/NIT)

> SUMMARY: "Round 3 is clean enough to ship. The MAJOR is genuinely dead …
> What is left is one sentence that claims the fsum oracle is asserted on
> eight frames when it is asserted on two — you over-corrected an
> over-assertion into an over-claim, which in this repo is the same sin
> wearing a different hat."

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | MINOR | §A2/A3 said the fsum oracle was asserted on eight frames; it was parametrized on two. | **FIXED** by taking the reviewer's second option: the script's A2 now sweeps all nine frames and the test is parametrized on the eight non-tie ones, so the sentence is true as written. Test count 206 → 212. |
| 2 | NIT | `test_a_quiet_but_honest_frame_is_reported_and_is_exact` promised exactness its assertion did not buy. | **FIXED.** Renamed `..._is_within_one_position`; docstring separates measured from asserted. |
| 3 | NIT | `assert eq <= FIRED` was arithmetically unfailable. | **FIXED.** Deleted. |
| 4 | NIT | §Z's ranges did not bracket an independent re-run. | **FIXED.** Disclaimer names every observed sweep on all four rows. |
| 5 | NIT | "Every number below is printed by the script" was untrue of §F, the 800 MB and the wiring counts. | **FIXED.** Scoped to §§A–D, Guards, O, Z with the three exceptions named at point of use. |

## Round 4 — PASS (with four MINOR/NIT)

> SUMMARY: "Four rounds in, this is as close to clean as this repo gets, and
> I resent how little is left to hit. All five round-3 fixes landed and none
> of them broke anything … I re-derived every figure … and found exactly one
> mismatch — the fsum oracle's frame count, which the author updated in the
> receipt and forgot in the two docstrings, and which errs by *under*-claiming,
> the only direction this repo has never failed in. Ship it."

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | MINOR | The fsum frame count was updated in the receipt and left at "three of them" in the module and test docstrings. | **FIXED** (the reviewer's own wording): "each of those nine" in both. |
| 2 | NIT | The prototype test's docstring said the pairwise total "cannot matter" on the eight frames; it can, it did not. | **FIXED** to "did NOT change the crossing (measured; the tie frame is where it can)". |
| 3 | NIT | §Z's widened disclaimer illustrated only two of four rows. | **FIXED.** All four rows now carry their observed spreads, from a fresh sweep run here (`length` 60 at 114.0–132.8 ms, `length` 250 at 474.0–505.3 ms). |
| 4 | NIT | No `docs/reviews/auto-*` folder, unlike every sibling port. | **FIXED.** This folder. |

⚠ The round-4 fixes landed AFTER the round-4 PASS and the four-round cap was
reached, so no fifth review ran. All four were text corrections the reviewer
dictated verbatim, plus this folder; none changed an assertion or a number
except §Z's spreads, which were re-measured here.

---

## Verification at the end of round 4

| check | result |
|---|---|
| `python -m pytest tests/test_ts_imq_20.py -q` | **212 passed** |
| `python docs/measure_ts_imq_20_cpu.py` (AVX512F / AVX512_SKX / AVX2 / FMA3 disabled, dispatch asserted) | **212 passed** |
| `python -m pytest -q` (full suite) | 3 failed, 7,495 passed, 85 skipped — the CLAUDE.md known break (`test_pine_coverage_csv`), the `../AlternativeRepos`-only test CI deselects by name, and the OWED Gate E row (`['mtd_ret', 'ts_imq_20']`) |
| `tests/test_altport2_ports.py` alone | 19 passed, 3 skipped (`CATEGORY_TOTAL = 332`) |
| `tests/test_readme_counts.py`, `tests/test_ml_companions.py`, `tests/test_wiring_accessors.py` | pass |
