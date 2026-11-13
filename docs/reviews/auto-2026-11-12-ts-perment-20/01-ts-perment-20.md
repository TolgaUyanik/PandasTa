# Task `ts-perment-20` — log

Port *permutation entropy of close (order 3, 20)* (PandasTa issue #91) through
Gates A–D, the five wiring touch points, a test module and
`docs/TsPerment20Measured.md`. Gate E and both repos' suites are the
launcher's. Lane: main thread. Appended as the work happened.

## Implementation

1. Read `CLAUDE.md`, the two merged sibling ports (`ts_binent_20` #89,
   `ts_c3_20` #88) and the screen prototype
   (`docs/issues/screen/ind_screen.py`, `perm_entropy3` + candidate
   `ts_perment_20`).
2. **Found the prototype's defect before writing the module.** Enumerated all
   27 triples of values from `{1, 2, 3}` — every weak order on three points —
   and measured which of the eight 3-bit codes occur: `{0, 2, 3, 4, 5, 7}` do,
   `{1, 6}` never. The prototype loops `(0, 1, 3, 4, 6, 7)`: it visits the two
   impossible codes and skips two realisable ones holding 25.90% of a walk's
   triples. Per `CLAUDE.md` ("Gate A starts from the source formula, not the
   prototype") the six-pattern Bandt-Pompe form ships, and the divergence is
   measured (Spearman 0.5487 / 0.4817 / −0.0296 on walk / tick-rounded /
   coarse grid) and disclosed in the module docstring, the receipt, the
   manifest and `docs/MLCompanionContract.md`. ASSUMPTION 1 in
   `00-manifest.md`.
3. Wrote `pandas_ta/statistics/ts_perment_20.py`: int8 pattern codes over a
   `sliding_window_view`, six bool-sum passes, `PATTERNS` fixed in
   `np.unique`'s rank-vector order so the module is bit-equal to the source's
   own spelling rather than merely close.
4. Wired touch points 2–4 (`statistics/__init__.py`, `Category["statistics"]`,
   `core.py`), then the counts the suite checks: `README.md` (324 / 332 /
   `statistics (33)`), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL = 324`),
   `docs/MLCompanionContract.md` (669 tagged / 312 `SF`), and regenerated
   `docs/IndicatorDictionary.md` with `python docs/gen_indicator_dictionary.py`
   (row: `TS_PERMENT_20_3` `SF`, warm-up 19).
5. Wrote `docs/measure_ts_perment_20.py` (8 sections) and ran every section,
   then `tests/test_ts_perment_20.py` (158 tests) and
   `docs/TsPerment20Measured.md` from those runs.

Two sequencing errors made and corrected inside the session, recorded because
the repo's dominant defect is a claim written before it was measured:

* The first draft of the test module quoted **0.6067** as port-vs-prototype on
  the coarse grid; it is the four-pattern variant's figure. The test FAILED on
  the real value (−0.0296), which is how it was caught — in the test module,
  before any document was final. The docstring kept the wrong number until
  review round 1 found it (MAJOR 1 below).
* The Monte-Carlo attainability sampler called `codes_of(rng.permutation(...))`
  inside a six-element generator expression, so it drew a fresh permutation per
  pattern and reported 41,856 "reached" count vectors — more than the 33,649
  that exist. The impossibility of the number is what exposed the bug; fixed,
  the figure is 2,814.

Measured outcome: Gates A–D cleared, Gate C's real-data counts and Gate E
owed to the launcher, `158 passed` for the module's own suite and
`3 failed, 6085 passed, 83 skipped` for the full suite (the two `CLAUDE.md`
*Known breaks* plus the owed ledger row `['mtd_ret', 'ts_perment_20']`).

## Review round 1 — REVISE

Fresh read-only Fletcher subagent. Verdict and findings, verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: tests/test_ts_perment_20.py:19-20 (file docstring, item 1)
    problem:  "Measured, port against the prototype: Spearman **0.5487** on a walk, **0.4817** tick-rounded, **0.6067** on a coarse grid." The coarse-grid number is wrong. `python docs/measure_ts_perment_20.py source` prints port-vs-prototype as 0.548665 / 0.481738 / **−0.029641**; 0.606731 is the *A5* variant that keeps the tie rule fixed and only drops two patterns. The file's own `test_the_port_is_not_the_column_the_screen_measured` is parametrized with −0.0296 at line 398, and the receipt's table (docs/TsPerment20Measured.md:95) says −0.029641. So the single most load-bearing sentence in the module that carries the "this is not the column #91 screened" headline quotes a number from a different experiment — and it quotes the one that makes the divergence look *smaller* (0.61 instead of "uncorrelated"). This is the exact defect CLAUDE.md names: a number not corresponding to its run.
    fix:      Replace 0.6067 with −0.0296 in item 1, and keep the two measurements visibly separate: port-vs-prototype = 0.5487 / 0.4817 / −0.0296 (patterns *and* tie rule differ), four-pattern variant with the tie rule held fixed = 0.5487 / 0.4811 / 0.6067. The module docstring (ts_perment_20.py:139-141 and 165-167) already gets this right — copy its wording.
  - severity: MAJOR
    location: tests/test_ts_perment_20.py:64 (item 3) and docs/TsPerment20Measured.md:291
    problem:  Item 3 is headed "Gate B, by mutant, on **six configurations**", states the real module's 0/37 over all six, and then asserts "⚠ The mutants are caught at **15-37 of 37** offsets". Over six configurations that is false: the file's own `test_the_mutants_at_non_default_lengths` parametrization pins `(2, 4, 7)` and `(4, 4, 11)` — `forward_leg` is caught 7/37 and `forward_triple` 11/37 at `length=4`, and `back_date_full` falls to 25/37 there. The measured range across the six configurations is 7–37, not 15–37. 15–37 is only true of the three default-length frames. The receipt repeats the same framing one table too late: "Three of the five mutants are caught at 15–32 of 37" sits *below* the non-default-length table whose minimum is 7.
    fix:      Scope the range to what was run: "15–32 of 37 at the default length on three frames; 7–37 once `length` 10/60/4 are included, the floor at `length=4` where a window holds two triples." Same edit in the receipt's ⚠ paragraph so the sentence sits with the table it describes.
  - severity: MINOR
    location: pandas_ta/statistics/ts_perment_20.py:202-208 (and tests/test_ts_perment_20.py:74-79)
    problem:  "it is bit-identical under ANY strictly increasing transform of price -- x8, x64 and x1024 on 1,481 of 1,481 bars of each of seven frames, and so are x10, x3.7, x0.1, `log`, `sqrt`, `x**3` and `+1000`." Two over-claims in one sentence. (a) `log`/`sqrt`/`x**3`/`+1000` were measured on the **walk only** — one frame, not seven (`test_any_strictly_increasing_transform_of_price_is_bit_identical` parametrizes transforms, not frames; the script's section prints the walk alone). (b) "ANY ... bit-identical" is false in float64 and the receipt knows it: docs/TsPerment20Measured.md:391-396 says a non-power-of-two scale can COLLAPSE two distinct closes onto one double and that the collapse is *visible* when the earlier close is the larger. The shipped docstring — the text the dictionary excerpts and the only text a consumer reads — carries the absolute without the caveat.
    fix:      "x8/x64/x1024 and x10/x3.7/x0.1 bit-identical on 1,481 of 1,481 bars of each of seven frames; `log`, `sqrt`, `x**3` and `+1000` on the walk. Invariance holds up to a float64 collapse: a transform that maps two distinct closes onto one double *can* move the column (see the receipt's Gate D note)."
  - severity: MINOR
    location: tests/test_ts_perment_20.py:386
    problem:  `path = os.path.join("docs", "issues", "screen", "ind_screen.py")` is CWD-relative, so `test_the_retyped_prototype_is_the_screens_own_code` — the only guard that the retyped prototype is the screen's real code rather than a paraphrase, and the thing item 1's whole argument rests on — silently turns into a skip whenever pytest is invoked from anywhere but the repo root. The repo convention is already `Path(__file__).resolve().parents[1]` (tests/config.py:17, tests/test_gate_e_ledger.py:75).
    fix:      `path = Path(__file__).resolve().parents[1] / "docs" / "issues" / "screen" / "ind_screen.py"`, so "absent" means absent and not "you cd'd".
  - severity: MINOR
    location: tests/test_ts_perment_20.py:980
    problem:  `assert moved == 15` with no tolerance, in the same file whose docstring (line 115-118) promises "Counts that depend on the last bits of a generated frame ... carry a tolerance: CI's runner has measured different last bits for the same seeds (commit 22fe27b)." The frame is `100*exp(cumsum(normal))`; `np.exp` is libm-dependent, and the count of moved bars is a function of order relations between closes that can differ in their last bit. 22fe27b is this repo's receipt for exactly that failure mode.
    fix:      Pin what the docstring argues — `assert outs[0].equals(outs[1]) and outs[0].equals(outs[2])` (the real claim: size is invisible) plus `assert 10 <= moved <= 20` (a spike sits in at most `length` windows). Drop the bare 15 or give it `abs=3`.
  - severity: MINOR
    location: docs/TsPerment20Measured.md:266-271 and 289
    problem:  "Five mutants" overstates the diversity of what Gate B covers. Rolling `codes` forward by k is arithmetically identical to writing the column k bars early, so `forward_triple` is a 1-bar back-date, `rolled_window` is a `length // 2`-bar back-date, and `back_date_two`/`back_date_full` are 2- and `length−1`-bar back-dates: four distances of one mechanism, plus `forward_leg` (the only mutant that changes how a triple is built). The `length=4` row is the proof — `back_date_two` and `rolled_window` both read 22/37 with byte-identical missed-offset lists `[200, 240, 480, …]`, because `length // 2 == 2` makes them the same mutation — and the table presents that cell twice as independent evidence.
    fix:      Say so in the mutant list: "two mechanisms — the write index back-dated by 1 / 2 / `length//2` / `length−1` bars (mutants 5, 1, 4, 2; at `length=4` mutants 1 and 4 coincide, hence the identical row) and the newest leg read one bar ahead (mutant 3)." Gate B is still cleared; the inventory just has to match what it is.
  - severity: MINOR
    location: docs/TsPerment20Measured.md:93-95, 189-203, 243-245
    problem:  Spearman figures are quoted to six decimals (0.548665, 0.481095, 0.038409, 0.210808) with no note that the last digits are not portable. 22fe27b moved `ts_binent_20`'s Spearman from 0.651029 to 0.648490 between this machine and CI on the *same* pandas/numpy/scipy — the third decimal. The test module hedges correctly (`abs=0.02`–`0.05`); the receipt reads as if six decimals were reproducible.
    fix:      Add one line next to "Every number here is printed by …": "Spearman and last-bit counts are this machine's; CI's runner has measured the third decimal differently for the same seeds (22fe27b), which is why the tests pin them with a tolerance."
  - severity: MINOR
    location: pandas_ta/statistics/ts_perment_20.py:29
    problem:  `UNREALISABLE = (1, 6)` is never read by the shipped module — only by the test through `_REAL.UNREALISABLE`. It is a documentation constant masquerading as code in a module whose own comments are otherwise load-bearing.
    fix:      Either fold the fact into the comment above `PATTERNS` and delete the constant (the test can keep its own tuple and assert `set(_REAL.PATTERNS) == {0,2,3,4,5,7}`), or state in one clause that it exists only as a pin for the test.
  - severity: MINOR
    location: pandas_ta/statistics/ts_perment_20.py:17-20, docs/TsPerment20Measured.md:237-239
    problem:  "Ties are broken by INDEX ... which is what `argsort` does on a 3-element array and therefore what tsfresh does." `np.argsort`'s default `kind="quicksort"` is documented as **not stable**; the index tie-break holds only because numpy falls back to insertion sort below 16 elements. The claim is measured against the installed numpy (27 triples, exhaustive) but written as a property of `argsort`.
    fix:      Write it as what it is: "measured against this numpy's `argsort` over all 27 triples; `argsort`'s default kind is not documented as stable, so the oracle in `tests/test_ts_perment_20.py` is the guard if that ever changes." Optionally spell the oracle `np.argsort(..., kind="stable")` and note tsfresh does not.
  - severity: NIT
    location: pandas_ta/statistics/ts_perment_20.py:8-14
    problem:  The comment calls `TAU` the embedding "delay". In tsfresh, `permutation_entropy(x, tau, dimension)` passes `tau` to `_into_subchunks(x, dimension, tau)` as `every_n` — the stride *between* subchunks, not the delay *within* one. The two coincide only at `tau=1`, which is what ships, so nothing is wrong; the comment just misdescribes the source it cites, in a file that otherwise cites carefully.
    fix:      "`tau=1`: in tsfresh `tau` is the stride between subchunks, which at 1 is also the within-triple delay — the two readings coincide here."
  - severity: NIT
    location: tests/test_ts_perment_20.py:1111 and 1158
    problem:  `assert _accumulate([1], 1) == 0.0` asserts arithmetic about the test's own helper (`1/1 = 1`, `log 1 = 0`) and cannot fail for any state of the module. And `pytest.approx(1.7060571156426696, abs=1e-12)` quotes 17 significant digits against a 1e-12 tolerance.
    fix:      Drop the first assertion (the real content is `_REAL.MIN_LENGTH == 4` plus the name check) and round the second to the tolerance you actually assert (1.706057115643).

SUMMARY: The mathematics is the best part of this port and I almost never get to say that — the 3-bit code is a genuine bijection with `argsort(argsort(x))` over all 27 weak orders, the six realisable codes are right, 1 and 6 are provably impossible, bit-equality with tsfresh's own `np.unique` spelling is *earned* by fixing `PATTERNS` in the rank-vector order rather than lucked into, the ceiling-is-one-ulp-below-`log 6` detail is pinned with a real witness, the deliberate divergence from the screen's four-pattern prototype is the correct call and is disclosed in all four places a reader would look, Gate C/E owed is stated plainly, and the full suite reproduces 3 failed / 6085 passed / 83 skipped to the digit. Then the file whose whole job is to carry the measured numbers quotes the wrong one for the headline claim: 0.6067 where the run says −0.0296, lifted from a neighbouring experiment, and it happens to flatter the port by making the divergence look like a correlation instead of nothing at all. Three paragraphs later the same docstring claims a 15–37 catch band over six configurations while its own parametrize table pins 7. Both are one-line edits and neither touches the shipped column, but this repo's recorded failure mode is a claim written before it was measured, and you have shipped two of them inside the document that exists to prevent exactly that. Fix the two MAJORs, tighten the "ANY strictly increasing transform" sentence so the docstring says what the receipt already says correctly, un-CWD the screen loader, and this passes.
```

**Every finding applied**, in the reviewer's words where they were specific:

| # | severity | what changed |
|---|---|---|
| 1 | MAJOR | test item 1 now carries both measurements, labelled: port-vs-prototype 0.5487 / 0.4817 / **−0.0296** and the four-pattern variant 0.5487 / 0.4811 / 0.6067 |
| 2 | MAJOR | test item 3 and the receipt's ⚠ now read "15–32 of 37 at the default length on three frames, and 7–37 over all six configurations", with the `length=4` floor named |
| 3 | MINOR | module docstring and test item 4: the four monotone transforms are scoped to the walk, and the float64-collapse caveat moved into the shipped docstring |
| 4 | MINOR | `_screen_candidate()` anchors on `Path(__file__).resolve().parents[1]` |
| 5 | MINOR | the spike test pins `0 < moved <= LENGTH` plus `approx(15, abs=3)` |
| 6 | MINOR | the receipt's Gate B now has a mechanism table and a ⚠ that the `length=4` coincidence is one measurement, not two |
| 7 | MINOR | a ⚠ portability paragraph at the top of the receipt |
| 8 | MINOR | the comment above `PATTERNS` says `UNREALISABLE` is read only by the test, as the pin for the pair |
| 9 | MINOR | the tie rule is written as measured against the installed numpy, with the test as the guard if `argsort`'s kind changes |
| 10 | NIT | the `TAU` comment states that at `tau = 1` the within-triple delay and the between-triple stride coincide, so the module does not have to choose a reading of tsfresh's parameter |
| 11 | NIT | the helper-arithmetic assertion dropped; the subnormal-close constant rounded to 1.706057115643 |

`python -m pytest tests/test_ts_perment_20.py -q` → **158 passed** after the
round-1 fixes.

## Review round 2 — REVISE

A second fresh Fletcher subagent, told which fixes to verify and to hunt what
round 1 missed. Verdict and findings, verbatim:

```
VERDICT: REVISE

FINDINGS:
  - severity: MAJOR
    location: docs/TsPerment20Measured.md:22-23 (the ⚠ portability paragraph, round-1 fix #7)
    problem:  The new paragraph says "The bit-equality counts under Gate A3 and Gate D are structural — they are equalities of comparisons, not of roundings — and are pinned exactly." That is false for A3 and the file proves it two sections later. Gate D's 1481/1481 *is* structural (a monotone transform leaves every `<=` unchanged, so both runs execute identical arithmetic). Gate A3's 581/581 is an equality between two *different* float pipelines: the module's `np.log` over a 581-row array accumulated as six `h -= p*log(p)` subtractions, versus the oracle's `np.log` over a ≤6-element array summed by `-np.sum(...)`. §A3 itself says the equality is "earned, not luck … the module accumulates the six terms in the order `np.unique` returns the rank vectors", and §A4 measures that merely reordering the identical terms moves the value by 4.44e-16. So the one exact pin the paragraph declares immune to "CPU float detail" (`assert int((port[m] == definition[m]).sum()) == 581`, tests/test_ts_perment_20.py:497) is precisely a rounding equality — it depends on numpy returning the same double for `log(p)` in both call shapes and on the summation order, neither of which the 22fe27b precedent says is portable. A reader following this paragraph will treat a CI failure of `test_matches_the_argsort_definition` as impossible.
    fix:      Rewrite the sentence to split the two: "Gate D's bit-equality is structural (equalities of comparisons). Gate A3's is an equality of two float pipelines that holds because the module accumulates in `np.unique`'s order (§A3) — measured on this machine, not guaranteed by the arithmetic; §A4 shows a reordering costs 4.44e-16." Then either keep `== 581` and say explicitly that it is a last-bit pin that may need the 22fe27b treatment, or pin 581/581 at 1e-12 (the portable claim, already asserted) and keep the bit-equal count as a reported measurement.
  - severity: MINOR
    location: tests/test_ts_perment_20.py:536
    problem:  `assert float(diff.max()) <= 5e-16` against a measured 4.44e-16 — exactly 2 ulp at ~1.6, with 12% headroom. A libm whose `log` differs by one more ulp in an 18-term accumulation puts the max at 6.66e-16 and the test goes red for a reason the docstring says is not a disagreement about any value. This is the same class of pin that 22fe27b had to tear out of `ts_binent_20`, and the file's own closing note promises such numbers "carry a tolerance".
    fix:      Loosen to the claim the receipt actually makes — `assert float(diff.max()) <= 1e-14` plus the already-present `(diff > 1e-12).sum() == 0` — and keep 4.44e-16 as the measured value in the docstring rather than as the bound.
  - severity: MINOR
    location: docs/TsPerment20Measured.md:352 (Gate C, "Real data: owed")
    problem:  "The arithmetic floor to expect is `398,849 − 89 × 19 = 397,158` non-NaN bars" has the direction backwards: `89 × 19` is the *minimum* NaN count, so 397,158 is the maximum attainable non-NaN count, not a floor. The house phrasing gets it right (`docs/TsC320Measured.md:258` and `docs/TsBinent20Measured.md:398`: "the arithmetic floor on the NaN count"), and `docs/CorrelationCycleMeasured.md:70` records exactly 397,158 for another 19-warm-up column over the same 89 frames — so the later receipt session will see a number that can only be ≤ a figure this file calls a floor.
    fix:      Reword to "`89 × 19 = 1,691` is the arithmetic floor on the NaN count, so expect at most `397,158` non-NaN bars; anything lower means a frame carried a non-finite close."
  - severity: MINOR
    location: docs/TsPerment20Measured.md:246-248 and tests/test_ts_perment_20.py:105-107 (item 6), 595
    problem:  §Source says anything tsfresh does beyond the issue's line is "unverified here" and the module docstring (round-1 fix #9) now hedges the tie rule as "what the installed numpy's `argsort` does — measured over all 27 triples, not assumed". The receipt's §The tie rule and the test's item 6 were not brought along: both still state flatly "which is what `argsort` does and therefore what tsfresh does". The first half is measured; the second half is an inference about an uninstalled library, i.e. the same defect round 1 flagged for the `TAU` comment, left in the two places a reader will quote.
    fix:      In both places, write "which is what the installed numpy's `argsort(argsort(x))` does (measured over all 27 triples) and therefore what tsfresh's `argsort` spelling does *if* that is its spelling — tsfresh is not installed here, see §Source."
  - severity: MINOR
    location: docs/reviews/auto-2026-11-12-ts-perment-20/00-manifest.md:73-75
    problem:  "Gate per task: … every verdict quoted in `01-ts-perment-20.md`." No such file exists — the run folder holds only `00-manifest.md`, so round 1's REVISE (2 MAJOR, 7 MINOR, 2 NIT) and this round are unrecorded. The manifest states as fact a record that does not exist; LEAN-HURST-100 had to commit `8b17506` specifically to record this gap rather than leave the claim standing.
    fix:      Either write `01-ts-perment-20.md` with each round's verdict and findings quoted, or change the sentence to "the Fletcher gate ran in-session; its verdicts are not recorded in this folder" so the manifest does not promise a file it has not got.
  - severity: NIT
    location: docs/TsPerment20Measured.md:275-276, 284, and tests/test_ts_perment_20.py:63-66
    problem:  "rolling the code array forward by k is arithmetically the same as writing the column k bars early" is true only away from the tail: `np.roll` wraps, so the last k windows of `rolled_window`/`forward_triple` read codes from the head of the series, which a true back-date would not. It does not change any measured number (the `length=4` coincidence of `back_date_two` and `rolled_window` was verified as identical missed sets), but it is an "arithmetically the same" claim that is not.
    fix:      Add "(except for the k wrapped windows at the tail, which `np.roll` fills from the head)" to the mechanism sentence in both the receipt and the test docstring.
  - severity: NIT
    location: docs/TsPerment20Measured.md:563 (Cost table)
    problem:  The 400,000-bar row says 117 ms; re-running `python docs/measure_ts_perment_20.py cost` on this machine gives 119 ms best-of-three (10,000 and 100,000 and the 18.5 MB peak reproduce exactly). A best-of-three wall time is the one number in the file that cannot be re-run to the digit.
    fix:      Write it as "~117-120 ms (best of three, one machine)" so the figure is not read as a reproducible constant.

SUMMARY: Every round-1 fix landed, and — unusually — they landed measured: I re-ran `source`, `gate_a`, `gate_b`, `gate_c_d`, `attainable`, `meaning`, `guards`, `cost`, the module's 158 tests and the full suite, and the documents match the runs digit for digit — prototype 0.548665 / 0.481738 / −0.029641 split cleanly from the four-pattern variant's 0.548667 / 0.481095 / 0.606731, the mutant grid reproduced cell by cell (real module 0/37 on all six configurations, the `length=4` back-date-two/rolled-window coincidence identical down to the missed-offset list, 15–32 at the default and 7–37 overall), the ceiling one ulp below `log 6` and attained, 5,978/175/2,814, 1481/1481 under six scales and four monotone transforms, 0.210808 under drift, and Gate F's "3 failed, 6,085 passed, 83 skipped" exactly as written with the expected `['mtd_ret', 'ts_perment_20']` ledger failure. The prototype-identity guard now actually runs instead of skipping. The port itself is right: `argsort(argsort(X))` + `np.unique`, 18 triples, first value at bar 19, nats, unnormalised, bit-equal to the independent spelling, and the tsfresh `tau`-as-stride trap is handled honestly. What drags this to REVISE is that one of the round-1 fixes bought peace by writing a sentence the file itself refutes: the new portability ⚠ declares Gate A3's bit-equality "structural … not of roundings" two sections above the measurement (§A4, 4.44e-16 for a reordered sum) that proves it is exactly a rounding, and uses that to bless the single exact `== 581` pin as CPU-proof — which is the precise failure mode commit 22fe27b existed to clean up. Fix that sentence, loosen the 5e-16 bound, turn the Gate C "floor" the right way round, stop telling the reader what tsfresh does in a file that says tsfresh is unverifiable here, and either write `01-ts-perment-20.md` or stop claiming it exists. None of it touches the column; all of it touches whether the next reader can trust the receipt's own labels.
```

**Every finding applied:**

| severity | what changed |
|---|---|
| MAJOR | the receipt's ⚠ portability paragraph now splits the two bit-equality claims: Gate D's is structural, Gate A3's is an equality of two float pipelines measured on this machine. `test_matches_the_argsort_definition` keeps 581/581 as the measured value but pins `>= 579` with the portable half (`0 bars > 1e-12`, `max <= 1e-14`) pinned exactly; §A3 carries the same ⚠ |
| MINOR | the scalar-loop bound loosened from `5e-16` to `1e-14`, with 4.44e-16 kept as the measured value in the comment |
| MINOR | Gate C reworded: `89 × 19 = 1,691` is the floor on the NaN count, so **at most** 397,158 non-NaN bars |
| MINOR | the receipt's §The tie rule and the test's item 6 now hedge the tsfresh half exactly as the module docstring does |
| MINOR | this file written, with both rounds quoted in full |
| NIT | the `np.roll` wrap caveat added to the mechanism sentence in the receipt and the test docstring |
| NIT | the cost row reads `~117–120 ms (best of three, one machine)`, in the receipt and in the module docstring |

## Review round 3 — PASS (with MINOR/NIT findings, all applied)

A third fresh Fletcher subagent, given rounds 1–2 verbatim and told not to
re-raise an applied finding unless its fix was wrong. Verdict and findings,
verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/TsPerment20Measured.md:36-38 (and tests/test_ts_perment_20.py:500-504, 514)
    problem:  Round-2's MAJOR fix bought the right split and then wrote a rationale nobody measured. The receipt and the test docstring both claim the bit-equal count "is pinned with a small tolerance so a last-bit change reports rather than failing the build, which is the 22fe27b lesson applied in advance", and the pin is `>= 579` — two bars of slack on 581. The failure mode the paragraph itself names (a numpy whose `log` takes a different SIMD path for the `(n,)` and `(<=6,)` shapes) does not move two bars: this file's own §A4 measures that merely reordering the same six terms moves 223–246 of 581 bars (346/335/358 bit-equal — reproduced here). Any real libm divergence blows a 2-bar window instantly, so the tolerance absorbs nothing it is advertised to absorb; it is decoration with a measured-sounding sentence attached. The same paragraph also calls agreement to 1e-12 something "the arithmetic does guarantee" when what exists is an error-analysis margin measured on four 600-bar frames.
    fix:      Say what the pin is: "`>= 579` is slack for a one- or two-bar drift only; a libm that disagrees on `log` across call shapes would move hundreds of bars and SHOULD fail here, which is why the portable claim (0 bars > 1e-12, max <= 1e-14) is the one pinned exactly." Drop "the 22fe27b lesson applied in advance", and write 1e-12 as "measured on four frames with ~3 orders of margin on the rounding", not as an arithmetic guarantee.
  - severity: MINOR
    location: tests/test_ts_perment_20.py:289-293 (docstring of `test_the_accumulation_order_is_the_sources_own`)
    problem:  "The module accumulates in the same order, which is the only reason `test_matches_the_argsort_definition` can assert bit-equality rather than a tolerance." After round-2's fix that test no longer asserts bit-equality — line 513 pins `max <= 1e-14` and line 514 pins `>= 579`, i.e. exactly a tolerance. The round-2 fix left behind a sentence that now describes a test that no longer exists, inside the file whose job is to say what is pinned. Five documents must agree; this one disagrees with the assertion sitting 220 lines below it.
    fix:      Reword to what it now is: "…which is why `test_matches_the_argsort_definition` measures 581 of 581 bit-equal rather than a mere agreement to 1e-12; that count is reported with two bars of slack, and the order pin lives here."
  - severity: MINOR
    location: tests/test_ts_perment_20.py:615-616 and docs/reviews/auto-2026-11-12-ts-perment-20/00-manifest.md:52-54
    problem:  Round-2's MINOR on "and therefore what tsfresh does" was applied in the receipt's §The tie rule and the test file's item 6 — and nowhere else. Two places still state it flat: the tie-rule test's own docstring ("Ties are broken by INDEX (`<=`), which is what `argsort` and so tsfresh do") and ASSUMPTION 5 in the manifest ("That is what `argsort(argsort(x))` does on a 3-element array and therefore what tsfresh does"). The manifest is the document a later session reads first, and `python docs/measure_ts_perment_20.py source` prints `ModuleNotFoundError: No module named 'tsfresh'` in this very worktree. A fix applied to two of four occurrences is not applied.
    fix:      Same hedge as the module docstring in both: "what the installed numpy's `argsort(argsort(x))` does — measured over all 27 triples — and therefore what tsfresh's `argsort` spelling does *if* that is its spelling; tsfresh is not installed here."
  - severity: MINOR
    location: docs/TsPerment20Measured.md:378-379 (Gate C)
    problem:  "expect **at most** `398,849 − 1,691 = 397,158` non-NaN bars" — the direction is now right, but 398,849 arrives with no provenance in a file whose opening paragraph claims "Every number here is printed by `python docs/measure_ts_perment_20.py` … Nothing in this file was typed from expectation". The script cannot print it and never does; there are no BIST frames in this worktree. This is the identical finding the sibling port's round-1 reviewer raised against `ts_binent_20` (quoted at docs/reviews/auto-2026-11-12-ts-binent-20/01-ts-binent-20.md:119-120), and the house fix is visible two files away: `docs/TsBinent20Measured.md:387-388` and `docs/TsC320Measured.md:247-248` cite the ledger run's `overlap_max.csv` for the same denominator.
    fix:      Cite it where you use it: "398,849 pooled bars over the 89 ALTPORT-1 frames — the denominator every `docs/gate_e_ledger.csv` run reports (`docs/TsC320Measured.md`, run `is88-ts_c3_20-…`), not a number measured in this worktree."
  - severity: NIT
    location: pandas_ta/statistics/ts_perment_20.py:78-84
    problem:  The outer `np.where(p > 0, …, 0.0)` cannot change a value. With the inner `np.where(p > 0, p, 1.0)` in place, `p == 0` already yields `p * log(1.0) == 0.0 * 0.0 == 0.0` exactly, so both branches of the outer guard return the same double for every input. The comment above it ("which is why the inner `where` exists") explains one of the two and leaves the dead one unexplained in a module whose comments are otherwise load-bearing.
    fix:      `h -= p * np.log(np.where(p > 0, p, 1.0))` and keep the comment, which already states the real reason (the inner `where` is what keeps `log(0)` out of the expression); or, if the outer one is kept for readability, say in one clause that it is redundant and why.
  - severity: NIT
    location: docs/reviews/auto-2026-11-12-ts-perment-20/01-ts-perment-20.md:187 and docs/TsPerment20Measured.md:576
    problem:  The log's round-3 section says "See `99-summary.md` for the round-3 verdict and the final suite counts" and the receipt says any later full-suite run "is recorded in docs/reviews/auto-2026-11-12-ts-perment-20/99-summary.md". That file does not exist — the run folder holds `00-manifest.md` and `01-ts-perment-20.md` only. This is the same shape as round-2's MINOR about the manifest promising `01-ts-perment-20.md`, re-created one file over.
    fix:      Write `99-summary.md` in the same commit as these sentences, or phrase them in the future tense the session can honour ("round 3's verdict is appended to this file").
  - severity: NIT
    location: docs/measure_ts_perment_20.py:269
    problem:  `path = os.path.join("docs", "issues", "screen", "ind_screen.py")` — round-1's MINOR #4 anchored the test's loader on `Path(__file__).resolve().parents[1]`, and the script's copy was left CWD-relative. Run from anywhere but the repo root, §A2 prints "the screen registry is absent from this worktree" and the receipt's load-bearing "bit-equal to the screen's own registry entry on 1,481 of 1,481 bars of each of the three frames" silently loses its evidence instead of erroring.
    fix:      Anchor it the same way as the test: `Path(__file__).resolve().parents[1] / "docs" / "issues" / "screen" / "ind_screen.py"`.
SUMMARY: Third time through and the numbers finally stop moving. I re-ran `source`, `gate_a`, `gate_b`, `gate_c_d`, `attainable`, `meaning`, `guards`, `cost`, the module's 158 tests and the full suite, and every figure in the five documents came back digit for digit: 0.548665 / 0.481738 / −0.029641 against the imported prototype (bit-equal to the retyped one on 1481/1481 of all three frames, the owner's tree being present), the four-pattern variant cleanly separated at 0.548667 / 0.481095 / 0.606731, 581/581 bit-equal to the `argsort`+`np.unique` spelling on four frames, 4.44e-16 and 0 bars over 1e-12 from the scalar loop, the ceiling one ulp below `log 6` and attained by the pinned witness found at shuffle 12, the entire mutant grid cell by cell including the `length=4` back-date-two/rolled-window coincidence down to the missed-offset list, 5,978 / 175 / 2,814, 63/63 and 116/116, 1481/1481 under six scales on seven frames, 0.210808 under drift, 1,236 zeros on the trending frame, 119 ms and an 18.5 MB peak, and "3 failed, 6085 passed, 83 skipped" with exactly the two Known breaks plus the owed `['mtd_ret', 'ts_perment_20']` row. `git status --porcelain` is clean of strays and the diff touches only permitted files. All seven round-2 fixes landed. What is left is the usual residue of fixing by sentence: the new `>= 579` pin carries a rationale that its own §A4 refutes — a libm divergence moves hundreds of bars, not two, so the "reports rather than fails" promise is empty — and the fix orphaned a docstring three screens away that still claims that test asserts bit-equality. The tsfresh hedge was applied to two of its four occurrences, and 398,849 still walks into Gate C without papers in a file that advertises total provenance. None of it touches the column, none of it is a gate, and none of it is worth another round: fix the four MINORs on the way to the Gate E ledger row.
```

Round 3 is a **PASS** under the skill's gate rule (no CRITICAL, no MAJOR).
The seven findings were applied anyway, because the user's review-loop rule
counts a PASS only if no fix lands after it:

| severity | what changed |
|---|---|
| MINOR | the `>= 579` rationale rewritten in the receipt (top ⚠ and §A3) and in the test docstring: two bars of slack is worth a one- or two-bar drift and nothing more, a real libm divergence would move hundreds of bars (§A4 measures 223–246 of 581) and SHOULD fail; 1e-12 is a measured margin, not an arithmetic guarantee |
| MINOR | `test_the_accumulation_order_is_the_sources_own`'s docstring no longer claims the other test "asserts bit-equality rather than a tolerance" |
| MINOR | the tsfresh hedge applied to the two remaining occurrences: the tie-rule test's own docstring and ASSUMPTION 5 in `00-manifest.md` |
| MINOR | Gate C now cites where 398,849 comes from (`docs/TsC320Measured.md`, run `is88-ts_c3_20-853aeed4`) and says it is not a number this worktree can measure |
| NIT | the redundant outer `np.where` removed from the module (`h -= p * np.log(np.where(p > 0, p, 1.0))`); re-ran `gate_a` afterwards and every figure, including the 581/581 bit-equality, is unchanged |
| NIT | `99-summary.md` written, and the sentences that promised it now have it |
| NIT | the measure script's screen-registry path anchored on `Path(__file__)` like the test's |

`python -m pytest tests/test_ts_perment_20.py -q` → **158 passed** after the
round-3 fixes.

## Review round 4 — PASS (the loop's last gate)

A fourth fresh Fletcher subagent, given rounds 1–3 and told to verify round
3's fixes and to confirm nothing they touched broke. Verdict and findings,
verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/TsPerment20Measured.md:35-38 and tests/test_ts_perment_20.py:503-505
    problem:  Round-3 fix #1 replaced one unmeasured rationale with a smaller one. Both places now pin two bounds in a single breath — "0 bars differing by more than 1e-12, with max |diff| under 1e-14, measured on four frames at about three orders of margin over the 4.44e-16 that a reordering costs". Three orders is true of 1e-12 (1e-12/4.44e-16 = 2252×); it is false of 1e-14, which is 22× — one and a third orders. The reviewer's own prescription attached the "~3 orders" to the 1e-12 pin alone, and the sentence re-attached it to both. Same sentence also says "measured on four frames": the 4.44e-16 it is taking margin over is §A4's, which runs three frames (walk / tick-rounded / coarse grid, reproduced here); four is §A3's frame count.
    fix:      Split the two bounds: "0 bars differ by more than 1e-12 — about three orders over the 4.44e-16 a different accumulation costs (§A4, three frames) — and max |diff| under 1e-14, roughly 20×." Make the identical edit in the test docstring so the two documents still agree.
  - severity: MINOR
    location: tests/test_ts_perment_20.py:501-503 and docs/TsPerment20Measured.md:31-33, 196-198
    problem:  The new rationale's load-bearing magnitude — "a mere reordering of the same six terms costs 4.44e-16 and moves 223-246 of the 581 bars" — is read off §A4, which is not a reordering. `_scalar_loop` (tests:521-549) replaces `np.log` over an `(n,)` array with `math.log` on Python scalars, builds a dict and accumulates in first-occurrence order; the 346/335/358 bit-equal counts (235/246/223 differing, reproduced here) are that whole package, not the order alone. The one measurement that *is* a pure reordering — `test_the_accumulation_order_is_the_sources_own`, tests:310-311, and the receipt's §A3 paragraph — reports only "max < 1e-12" and "a non-zero number of differing bars" and never prints a count, so the number quoted to justify the `>= 579` pin is attributed to an experiment that was not run.
    fix:      Either relabel it ("an independent accumulation — different order AND a different `log` call — moves 223-246 of 581, §A4"), or print the differing-bar count of the `PATTERNS`-reordered variant in `docs/measure_ts_perment_20.py`'s `gate_a` section and cite that figure, since both the test helper (`_variant(..., patterns=(0,2,3,4,5,7))`) and the script's `variant` already exist.
  - severity: MINOR
    location: docs/reviews/auto-2026-11-12-ts-perment-20/99-summary.md:7
    problem:  The summary table records the task as **PASS** over "4 (round 1 REVISE, round 2 REVISE, round 3 PASS with MINOR/NIT, round 4 the confirming pass)" — a verdict for a review that had not run when the sentence was written. `01-ts-perment-20.md:244` gets it right ("Round 4's verdict is appended below after it runs") and 99-summary's own per-round table leaves round 4 as "—", so the file contradicts itself two tables apart. This is the species of defect rounds 1-3 each flagged — a claim written before it was measured — committed in the document whose only job is to record what was measured, and it is the one place the round-3 NIT fix created new text.
    fix:      Write row 7 as the log does: status "round 4 pending", review rounds "3 complete (REVISE, REVISE, PASS) + round 4 in progress", and fill in PASS only after the verdict exists.
  - severity: NIT
    location: docs/TsPerment20Measured.md:343-347 (Gate B, below the non-default-length table)
    problem:  "The whole-window leaks (`back_date_full`, `rolled_window`) move so much that they are caught everywhere" sits directly under the table where, at `length=4`, `back_date_full` reads 25/37 and `rolled_window` 22/37. The next sentence does disclose that the catch rate falls at `length=4`, so this is wording, not a wrong number — but "caught everywhere" is refuted by the row above it, which is exactly the reading error round 1's MAJOR 2 was raised about.
    fix:      "caught at 36-37/37 at every length but 4, where they fall to 22-25/37" — the figures are already in the table.
SUMMARY: Fourth pass, and for once the residue is shrinking instead of migrating. All seven round-3 fixes landed and landed measured: the `>= 579` rationale is rewritten in the receipt's top ⚠, §A3 and the test docstring; the orphaned "asserts bit-equality rather than a tolerance" sentence is gone; the tsfresh hedge is now on all four occurrences, including the tie-rule test docstring and the manifest's ASSUMPTION 5; 398,849 is cited to `is88-ts_c3_20-853aeed4`, which I confirmed is a real row in `docs/gate_e_ledger.csv` carrying that exact denominator; the measure script's registry loader is anchored on `Path(__file__)`; and `99-summary.md` exists. The redundant outer `np.where` is gone and it cost nothing — I re-ran `gate_a` and `gate_c_d`: A3 is still 581/581 bit-equal with max |diff| 0.000000e+00 on all four frames, every hand case still lands 0.0 away with the ceiling one ulp below `log 6`, A4 still 4.44e-16 / 0 bars over 1e-12, the five open readings reproduce to six decimals (0.548665 / 0.481738 / −0.029641 and 0.548667 / 0.481095 / 0.606731), Gate D is 1481/1481 on seven frames × six scales and four monotone transforms, drift 0.210808, trending 1,236 zeros over 6 distinct values, and the mutation targets are still unique — `_load_mutant` asserts `src.count(old) == 1` and the 30 mutant cells pass, so the edit did not silently neuter Gate B. 158 passed for the module, and the full suite reproduces `3 failed, 6085 passed, 83 skipped` with the ledger failure printing exactly `['mtd_ret', 'ts_perment_20']`. Wiring is all five touch points plus 324/332/`statistics (33)`, `CATEGORY_TOTAL = 324`, 669 tagged / 312 `SF`, and the dictionary row `TS_PERMENT_20_3 SF` warm-up 19; `git status` carries nothing outside the allowlist. What is left is the tail of fixing-by-sentence: an order-of-magnitude that is right for one bound and wrong for the other, a 223-246 figure borrowed from an experiment that changed more than the accumulation order, and — in the summary written by the round-3 NIT fix — my verdict typed in before I rendered it. None of it is a gate, none of it touches the column. Clean up the four, hand it to the Gate E ledger, and stop editing prose.
```

Round 4 is the loop's last gate (the skill caps at 3 REVISE rounds, the user's
rule at 4 rounds total), and it is a **PASS**. Its four findings were applied
anyway, and — stated plainly — **those four edits landed after the last gate
and are therefore unreviewed**:

| severity | what changed |
|---|---|
| MINOR | the margin sentence split: 1e-12 is ~3 orders over 4.44e-16, 1e-14 is ~20× |
| MINOR | **measured rather than relabelled.** `docs/measure_ts_perment_20.py`'s `gate_a` now prints the PURE reordering (same counts, same `np.log`, only `PATTERNS` in code order): max \|diff\| 4.440892e-16, 0 bars over 1e-12, and **249–274 of 581 bars moved** on four frames (walk 256, tick-rounded 262, coarse grid 274, two-point 249). The receipt's §A3 carries the table and both documents now cite that figure instead of §A4's |
| MINOR | `99-summary.md`'s status row and per-round table now say what actually happened, with round 4's PASS filled in only once rendered |
| NIT | the Gate B paragraph no longer says the whole-window leaks are "caught everywhere"; the `length=4` fall to 22–25/37 is named where the claim is made |

`python -m pytest tests/test_ts_perment_20.py -q` → **158 passed**, and
`python -m pytest -q` → **3 failed, 6,085 passed, 83 skipped** after the
round-4 fixes; the three failures are the two `CLAUDE.md` *Known breaks* plus
the owed Gate E row.

