# Task log — ts-peaks-20

**Status:** PASS (round 4 and round 5 both PASS; four NITs from round 5 were
applied after the last gate and are unreviewed — disclosed below).
**Rounds:** 5 (PASS → REVISE → REVISE → PASS → PASS).

## Implementation

1. Read `CLAUDE.md`, the two merged precedents (`git show --stat 886192c`,
   `ts_perment_20` / issue #91, and the `lean_tdd_20` merge), the issue copy
   `docs/issues/091-ts-peaks-20.md` and the screen prototype
   `docs/issues/screen/ind_screen.py` candidate `ts_peaks_20`.
2. Established what the prototype computes: `x = c.shift(2)`,
   `pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) & (x > c)`,
   `rolling(16).sum()` masked by `c.shift(19).notna()` — i.e. exactly
   `number_peaks(n=2)` over a 20-close window, 16 candidates at bars T-17 …
   T-2. Unlike issue #91, the prototype and the source formula agree here, so
   Gate A's "start from the source formula" and "be the screened column" do
   not conflict.
3. Wrote `pandas_ta/statistics/ts_peaks_20.py`: int8 peak flags over the
   candidate bars, `sliding_window_view` of 16, `sum(axis=1)` for the count
   and `min(axis=1) < 0` for the NaN-window mask. Column `TS_PEAKS_20_2`,
   warm-up 19, `length` the only parameter (minimum 5).
4. Wired the five touch points: the module, `pandas_ta/statistics/__init__.py`,
   `Category["statistics"]` in `pandas_ta/__init__.py`, the `core.py`
   accessor, `tests/test_ts_peaks_20.py`. Updated `README.md` (324 → 325,
   332 → 333, statistics 33 → 34), regenerated
   `docs/IndicatorDictionary.md` with `python docs/gen_indicator_dictionary.py`
   (row `TS_PEAKS_20_2 ORD`, warm-up 19), `docs/MLCompanionContract.md`
   (669 → 670 tagged columns, `ORD` 51 → 52) and `CATEGORY_TOTAL` in
   `tests/test_altport2_ports.py` (324 → 325).
5. Wrote `docs/measure_ts_peaks_20.py` (8 sections: `source`, `gate_a`,
   `gate_b`, `designed`, `gate_c_d`, `meaning`, `guards`, `cost`), ran every
   section, and wrote `docs/TsPeaks20Measured.md` from its output only.
6. `python -m pytest tests/test_ts_peaks_20.py -q` → **192 passed**.
   `python -m pytest -q` → **3 failed, 6,285 passed, 83 skipped** (133.15 s),
   the three being the two `CLAUDE.md` *Known breaks* plus the owed Gate E
   row, which names exactly `['mtd_ret', 'ts_peaks_20']`.

## Round 1 — VERDICT: PASS (5 MINOR)

Reviewer re-ran all eight measure sections, the module suite and the full
suite, and re-derived causality by hand. Verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: tests/test_ts_peaks_20.py:82
    problem:  "Only 6 values exist at length 20, and the top one (6) is reached by none of
              the seven synthetic frames." You wrote a count and then refuted it one clause
              later -- if only 6 values existed the top one would be 5. The module docstring
              says "7 possible values", the receipt says "So the column has 7 possible
              values", your own test_the_column_takes_at_most_seven_values says "0 .. 6".
              Seven exist; six were OBSERVED. In a repo whose dominant defect is an unmeasured
              count, a count that contradicts your own two other files is not a typo, it is
              the defect.
    fix:      Rewrite as "Seven values exist at length 20 (0..6); at most 6 distinct appear on
              the seven synthetic frames and the ceiling 6 is reached by none of them."
  - severity: MINOR
    location: docs/measure_ts_peaks_20.py:256-259 (variant docstring) and
              docs/TsPeaks20Measured.md:193,207-212
    problem:  "`same_bar` ... which lets bar T itself fire" is false of the code you wrote. The
              branch changes only the predicate (`core > left`); the slice stays
              `core = c[pad:n-pad]` and the write stays `out[cands + 2*pad - 1:]`, so the
              newest candidate is still bar T-2 and bar T never fires. What you measured is a
              no-confirmation column at the SAME 2-bar lag, which is the better experiment --
              but the A5 table row "a same-bar reading" and the bullet "The same-bar reading is
              a different feature entirely (0.000035)" bill 0.000035 to a column nobody
              computed. The §A5 note's "over the same 16 positions" is the only place the truth
              survives.
    fix:      Delete the clause "which lets bar T itself fire"; rename the knob and the A5 row
              to "no confirmation, same 16 candidate positions" in the table, the bullet, the
              test id (tests/test_ts_peaks_20.py:578) and the module docstring's A5 reference.
              If you want the genuine same-bar column priced, write `out[cands - 1:]` for that
              branch and re-measure it as a separate row.
  - severity: MINOR
    location: docs/TsPeaks20Measured.md:219-221
    problem:  "that maximum is 6, uniquely at window positions (2, 5, 8, 11, 14, 17)".
              `max_peaks_exhaustive` (docs/measure_ts_peaks_20.py:346-355) keeps a set only on
              `len(chosen) > best`, so it reports the FIRST 6-subset the mask order hands it and
              never counts the others; test_the_ceiling_is_six_exhaustively asserts that same
              single tuple. Uniqueness is true (span 17-2 = 15 forces five gaps of exactly 3)
              but it is an argument, and you printed it as a measurement.
    fix:      In the same loop accumulate `winners = [s for s of size best]` and print
              `len(winners)`; assert `winners == [(2,5,8,11,14,17)]` in the test. Otherwise
              strike the word "uniquely".
  - severity: MINOR
    location: docs/TsPeaks20Measured.md:198-199
    problem:  "(0.9999999999999999 as pandas computes it on the walk -- the rank correlation's
              own last bit)". No committed section prints that repr: `gate_a` formats rho at six
              decimals (1.000000) and the test only asserts `> 1.0 - 1e-9`. A 16-digit float
              typed into the receipt with nothing behind it is exactly the sentence this
              repo's README of sins is about.
    fix:      Print the share row's rho with `!r` (or `:.17g`) in gate_a's A5 output, or delete
              the parenthetical and keep "Spearman 1.000000 to six places, and the ratio is
              exactly 1/16 bar by bar, asserted".
  - severity: MINOR
    location: tests/test_ts_peaks_20.py:800-801,838
    problem:  `("forward_leg", 3, 41)` with `assert mut_hits == expected` pins a
              frame-last-bit-dependent count to the digit, in a file whose own header says
              "Counts that depend on the last bits of a generated frame ... carry a tolerance"
              and whose receipt cites commit 22fe27b for CI measuring different last bits on the
              same seeds. The 9 misses are decided by float comparisons on rng(11)'s draws; one
              last bit and the gate's own Gate B test goes red on CI for no defect.
    fix:      Keep the invariant `mut_hits + dead == 50` and `real_hits == 0` exact, and relax
              the absolute to a band (`35 <= mut_hits <= 45`), as CAUGHT already does for the
              sweep.
SUMMARY: Gates A through D hold, and for once the arithmetic is not where the file is soft --
the port is `number_peaks(x, n=2)` spelled honestly: four strict comparisons at distances 1 and
2 on both sides, 16 candidates in a 20-close window, the raw count, bit-equal to an np.roll
oracle, a plain-Python loop, eight hand windows and the owner's own registry entry; the write
index lands at `length-1` and the newest candidate is bar T-2, which I re-derived by hand rather
than take from your tests; the mutants are genuinely read off disk, genuinely exec'd, genuinely
verified live, and when the blind sweep collapsed to 1-5 of 37 you did the right thing and said
so out loud instead of hiding behind the 37/37 rows -- the designed probe and the
caught-equals-flipped set equality are the only reason Gate B is worth anything here. What is
soft is the prose, and all five hits are prose: a knob whose docstring describes behaviour its
own code does not have and whose number is then billed to the wrong column, a "uniquely" that
your enumeration never checked, a 16-digit float nobody printed, a 41 pinned to the digit in a
file that lectures the reader about tolerances, and a sentence that says six values exist
twelve lines after your module says seven. None of that ships a wrong column, so it passes --
but you wrote a receipt for the receipt and then four sentences in it that no run supports.
Fix the five, and understand that the only thing standing between this port and the 17 of 18
that failed first review is that this time the slips landed in the comments.
```

**Fixes applied (round 1 → 2):** item 5 of the test docstring rewritten to
separate "seven exist" from "six observed"; the `same_bar` knob renamed
`no_confirm` and relabelled in the measure script, the test ids, the A5 table
and the receipt's bullet; `max_peaks_exhaustive` now collects every maximal
subset and prints the count (measured: 1), with the test asserting the single
winner; `gate_a` now prints the share correlation with `!r` (walk
0.9999999999999999, tick-rounded 1.0, coarse-grid 1.0 — the first draft's
claim about which frames give which was wrong and was corrected to the run);
`forward_leg`'s designed-probe count banded 35–45 with `mut_hits + dead == 50`
and `real_hits == 0` kept exact.

## Round 2 — VERDICT: REVISE (1 MAJOR, 1 MINOR, 3 NIT)

Verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: pandas_ta/statistics/ts_peaks_20.py:202-206 (and docs/TsPeaks20Measured.md:506-509, the Cost section)
    problem:  The Cost prose itemises the module's allocations and omits the largest one, then uses that wrong itemisation to explain the only memory number you measured. Line 73 is `bad = (windows < 0).any(axis=1)`. numpy does not fuse a comparison into a reduction: `windows < 0` materialises a bool array of shape `(n - length + 1, length - 4)`. At n = 400,000, length 20 that is 399,981 × 16 = 6,399,696 bytes = **6.4 MB** — sixteen times the 0.4 MB int8 flag array you do name, and more than half of the 11.7 MB `tracemalloc` peak the doc prints. Your own number convicts the sentence: the peak occurs at that line (flags 0.4 + ok/peak/valid 1.2 + counts 3.2 + the 6.4 MB temporary + bad 0.4 ≈ 11.6 MB, which is what the script reported). So "memory is O(n) and the windows themselves are a view" and "a few `bool` arrays of the same length" are both false as written: peak memory is O(n · (length − 4)) bytes, and `length` is a caller parameter the tests push to 250, where the same frame would allocate roughly a hundred megabytes for that one temporary — a figure nobody measured and the doc's "O(n)" actively hides. This is the repo's named defect in its purest form: an explanation written for the code someone meant to write.
    fix:      Replace line 73 with `bad = windows.min(axis=1) < 0` — flags are int8 in {−1, 0, 1}, so `min < 0` is bit-equivalent to `any(< 0)` and is a true strided reduction with no 2-D temporary — then re-run `python docs/measure_ts_peaks_20.py cost` and put the new peak in both surfaces. If you keep `(windows < 0).any(axis=1)`, then delete "so memory is O(n)" and "a few bool arrays of the same length", say instead "the `windows < 0` test allocates a `(n - length + 1) × (length - 4)` bool array — 6.4 MB of the measured 11.7 MB peak at n = 400,000, length 20 — so peak memory grows with `length`", and add a measured row at `length=250` to the cost table.
  - severity: MINOR
    location: docs/TsPeaks20Measured.md:214-218; tests/test_ts_peaks_20.py:95-96 and 329-331; docs/measure_ts_peaks_20.py:256-260
    problem:  Round 1 told you to stop claiming the `same_bar` knob did something the code does not do. You renamed it `no_confirm`, which is right, and then wrote the correction in a vocabulary your own documents define to mean the opposite: "bar T still never fires in it". In this receipt "fires" means *produces a non-NaN value* — "fires 1481/1500", "1,481 fired bars", "each fire 1,481 bars". The `no_confirm` variant writes a value at every bar from 19 onward, bar T included; what is true is that bar T is never a *candidate*. So the one sentence that exists to prevent a misreading asserts, in the file's own terms, something false. Four copies of it.
    fix:      In all four places write: "it keeps the candidate positions, so the newest candidate is still bar T-2 and today's close is never counted — bar T still produces a value, it just cannot contain itself", and drop the word "fires" from that sentence.
  - severity: NIT
    location: docs/TsPeaks20Measured.md:13-16 (masthead) and 491-494 (the dictionary/contract paragraph)
    problem:  "Every number here is printed by `python docs/measure_ts_peaks_20.py` … or asserted by `python -m pytest tests/test_ts_peaks_20.py -q`" is an absolute, and three numbers in the file come from neither: the Gate F line ("3 failed, 6,277 passed, 83 skipped") is `python -m pytest -q` (verified here: 3 failed, 6277 passed, 83 skipped), the owed-row name `['mtd_ret', 'ts_peaks_20']` is `tests/test_gate_e_ledger.py` (verified), and "the 600-bar probe sees 5 distinct values" is `python docs/gen_indicator_dictionary.py`, which prints no cardinality anywhere — the dictionary records only the tag `ORD` and warm-up 19, both of which I confirmed; the 5 is recorded in no output in this repo. The claims are true; the provenance sentence that guards them is not.
    fix:      Extend the masthead to "…, by `python -m pytest -q` (the suite line and the owed ledger row), or by `python docs/gen_indicator_dictionary.py` (the ML tag and warm-up)", and either make the generator print the observed distinct count or replace "(the 600-bar probe sees 5 distinct values)" with "(the probe's `classify` tags `ORD` for ≤ 12 integer values; the observed set is not recorded in the generated file)".
  - severity: NIT
    location: docs/TsPeaks20Measured.md:19-23
    problem:  "commit 22fe27b moved `ts_binent_20`'s 0.651029 to 0.648490" misreports the commit I read: 22fe27b *kept* the pin at 0.651029 and widened its tolerance to `abs=0.01` because CI measured 0.648490. And "because the generated frames themselves differ in their last bits" states a mechanism nobody isolated — the commit message attributes the drift to "the runner's CPU", not to the frames. You are warning about unmeasured claims in a paragraph containing one.
    fix:      Rewrite as: "CI's runner measured 0.648490 where this machine measures 0.651029 for `ts_binent_20`, on the same pandas/numpy; 22fe27b widened that pin to `abs=0.01` rather than isolating the cause."
  - severity: NIT
    location: docs/TsPeaks20Measured.md:192 (A5 table row "the 19 returns of the window")
    problem:  The row names a number the measured variant does not use. `_variant(on_returns=True)` builds the whole return series `r[t] = c[t]/c[t-1] - 1`, keeps the same 16 candidate positions and the same 16-wide window, so bar T's window spans returns T-19 … T — twenty returns, reaching back to close T-20 — not the 19 returns internal to a 20-close window. The Spearman (0.096399 / 0.187320 / 0.259749, all reproduced here) is unaffected; the label is wrong.
    fix:      Relabel the row "peaks of the return series at the same 16 candidate positions" and drop "19".
SUMMARY: The five round-1 fixes landed and I verified each against a live run: the test docstring's item 5 now separates "seven values exist" from "six observed" and the suite pins `max <= 5.0`; the `same_bar` knob is gone, replaced by `no_confirm`, whose code really does drop only the forward legs; the A6 enumeration now counts the maximal subsets and prints "how many subsets attain it: 1 — [(2, 5, 8, 11, 14, 17)]"; `gate_a` now prints the share correlation to every digit (0.9999999999999999 on the walk, 1.0 on the other two) so the repr in the doc has a run behind it; and `forward_leg`'s 41 is banded 35–45 with `mut_hits + dead == 50` carrying the exactness. Every other number I re-derived came back on the nose — the A5 matrix to six places, the 11/16/11, 37/37/36, 2/5/2, 35/36/31, 1/4/1 mutant table, the `caught == flipped` set equality on all three frames, 50/50 and 41/50 on the designed probe, 1481/1481 under all 42 scalings, the Gate C histograms, 0.406613, 0.566696, the guard counts, 184 passed, 3 failed / 6277 passed / 83 skipped, and `['mtd_ret', 'ts_peaks_20']`. The mathematics is right, the slicing is causal by hand (bar T reads closes T−19 … T, newest candidate T−2), the oracle is the genuine `number_peaks` spelling, and the wiring and the five counts hold. And then, in a fix round, you wrote a brand-new sentence about the shipped code that is simply untrue — "memory is O(n) and the windows themselves are a view" — while line 73 quietly allocates a 6.4 MB bool matrix that is over half the very peak you printed two lines later. You measured the number and then explained it with code you did not read. Fix the allocation or fix the sentence, stop saying "fires" when you mean "is a candidate", and come back.
```

**Fixes applied (round 2 → 3):** `bad` respelled `windows.min(axis=1) < 0`;
`cost` extended with a length sweep (20 / 60 / 250 at n = 400,000) and a
direct measurement of the two spellings; both prose surfaces rewritten around
the measured numbers, with the earlier wrong sentence recorded as a ⚠ in the
receipt rather than quietly replaced; the four "still never fires" copies
reworded to "bar T still produces a value, it just cannot contain itself"; the
masthead extended to name every command; the 22fe27b sentence corrected
against `git show`; the A5 return row relabelled.

Note on the MAJOR's arithmetic, measured rather than accepted: removing the
temporary did **not** move the module's traced peak (11.7 MB before and
after), so the peak is reached at the final `float64` stage and not at `bad`.
What the change does fix is the growth with `length` — measured 11.7 MB at
`length` 20, 60 and 250, where the `any` spelling's own temporary traces
6.8 MB and 98.7 MB. Both surfaces now say that, not the reviewer's
reconstruction.

## Round 3 — VERDICT: REVISE (1 MAJOR, 2 MINOR, 1 NIT)

Verbatim:

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: `docs/measure_ts_peaks_20.py:950-972` (the `cost` section), quoted as evidence in `docs/TsPeaks20Measured.md` Cost §(~line 529) and `pandas_ta/statistics/ts_peaks_20.py:72-76`
    problem:  You replaced an unmeasured O(n) claim with a measurement that cannot fail. The receipt says "the flags are `int8` in {−1, 0, 1} so the two are equivalent (measured: they agree on every window at `length` 20 and 250)". The array that measurement runs on is built as `flags = np.where(np.isfinite(c[SUPPORT:n - SUPPORT]), np.int8(0), np.int8(-1))` — by construction it can never contain a `1` at all, and on `walk(400000, seed=12)` (a log-random walk, nothing infinite: sigma 0.015 × sqrt(4e5) ≈ 9.5 in the exponent) every element is `0`. So both spellings return an all-False array and `np.array_equal` prints `True` on a constant input: the run I just made prints "the two agree on every window: True" at both lengths without ever evaluating a `-1`. One of the three reachable flag values is exercised. The equivalence happens to be true (`min < 0` ⟺ some element `< 0` for any numeric array, int8 or not) and the `-1` path is pinned behaviourally by `test_a_non_finite_close_empties_exactly_length_bars`, so nothing ships broken — but the parenthetical "(measured: …)" is a receipt for a run that could not have caught a difference, which is this repo's named defect wearing a lab coat.
    fix:      In `cost()`, build the windows from flags that actually contain all three values — e.g. plant a NaN and a `-inf` in the 400,000-bar frame and compute `flags` with the module's own expression (`np.where(valid, peak.astype(np.int8), np.int8(-1))`, or reuse `flags_of` plus an `ok` mask) — then print `np.bincount(flags + 1)` (or the counts of −1/0/1) next to the agreement line so the reader can see the `-1`s were present, and re-run. Memory numbers are shape/dtype-driven and will not move (6.8 / 98.7 / 0.8 MB reproduce exactly). Then either keep the sentence with the real counts, or say plainly that the equivalence is structural (`min < 0` iff any element `< 0`) and that the measurement is only a smoke test.
  - severity: MINOR
    location: `pandas_ta/statistics/ts_peaks_20.py:74-76`
    problem:  "the `any` form materialises a `(rows, candidates)` bool array first -- 6.4 MB at n = 400,000 of a measured 11.7 MB peak" reads as "6.4 of the 11.7 are this array", and that is arithmetically impossible: the 11.7 MB was traced with the `min` spelling, which allocates no such array (`cost` run: 11.7 MB at `length` 20, 60 and 250). 6.4 MB is the script's `would be` arithmetic `(400000-19)*16/1e6`; the measured traced peak of the `any` expression is 6.8 MB. The module's own comment and its docstring (line 211) therefore quote two different numbers for the same object, and the comment's is the one that is not a measurement.
    fix:      Rewrite line 74-76 as: "the `any` form materialises a `(rows, candidates)` bool array first -- traced at a 6.8 MB peak at `length` 20 and 98.7 MB at `length` 250 against 0.8 MB for `min`, on the same windows (docs/TsPeaks20Measured.md, Cost)". Drop "of a measured 11.7 MB peak", or restate it as "on top of the module's 11.7 MB peak".
  - severity: MINOR
    location: `tests/test_ts_peaks_20.py` (no test), against `pandas_ta/statistics/ts_peaks_20.py:77` and `docs/TsPeaks20Measured.md` Cost §
    problem:  Three prose surfaces now assert *which spelling the code uses* ("That is the reason `bad` is spelled `windows.min(axis=1) < 0`", plus the ⚠ paragraph about the revision that drifted), and nothing in the suite pins it. 184 tests pass with either spelling — they are behaviourally identical, which is the whole point. So the next person who finds `(windows < 0).any(axis=1)` more readable restores exactly the doc-versus-code divergence round 2 caught, silently, with a green suite and a receipt that still claims a 0.8 MB reduction.
    fix:      Add a one-line source test next to `test_the_docstring_states_the_source_and_the_gap`: read `_REAL.__file__` and assert `"windows.min(axis=1) < 0" in src` and `"(windows < 0).any(" not in src`, with a docstring saying the Cost section's memory table is measured on that spelling. (The mutant loader already proves the source is readable and that these exact strings are unique.)
  - severity: NIT
    location: `docs/TsPeaks20Measured.md:13-19` (the masthead)
    problem:  "Every number here comes from a run in this session, and from one of exactly four" is still an absolute the file breaks three lines later. The screen's Gate E figures (0.2453, n = 397,158, 0.2345, `LINREG_LOWER_2` 0.2432, `PSAR` 0.2430) come from `docs/issues/091-ts-peaks-20.md`; 0.648490 / 0.651029 and `22fe27b` come from `git show`; `docs/gen_indicator_dictionary.py:147` comes from reading a file. All three are attributed where they appear — which is the honest part — but "exactly four" is then not true of "every number here".
    fix:      Make the scope explicit: "Every number this session MEASURED comes from one of exactly four commands: … . Three figures are quoted from outside those runs and labelled where they appear: the screen's Gate E numbers (`docs/issues/091-ts-peaks-20.md`), commit 22fe27b's CI counts, and the `classify` line number in `docs/gen_indicator_dictionary.py`."
SUMMARY: Round 2's five fixes landed, and I checked them rather than took your word: the code now reads `windows.min(axis=1) < 0`, the Cost section's new table reproduces to the digit on my machine (11.7 MB flat across `length` 20/60/250 at n = 400,000; `any` 6.8 MB / 98.7 MB against `min` 0.8 MB / 0.8 MB), the `no_confirm` wording says "bar T still produces a value, it just cannot contain itself" in all four copies, 22fe27b is now described as what it actually is (pin widened to `abs=0.01`, drift blamed on the runner's CPU), and the A5 row says "the return series, same 16 positions" instead of inventing 19 returns. Nothing in the column moved: 184 passed, full suite 3 failed / 6277 passed / 83 skipped with the owed row naming exactly `['mtd_ret', 'ts_peaks_20']`, and every Gate A/B/C/D figure I re-ran — 0.767425, 0.115928, −0.098358, 0.791649, 0.9999999999999999, 0.288630, 0.096399, 0.000035, the 65,536-subset ceiling and its single winner, 11/16/11, 37/37/36, 2/5/2, 35/36/31, 1/4/1, 50/50, 41 + 9 = 50, 0.406613, 0.566696, every histogram — came back identical. And then, in the one section you rewrote, you shipped a measurement that cannot fail: the `any`-versus-`min` agreement is "measured" on a flag array that `np.where(isfinite, 0, -1)` makes identically zero, so the run never evaluates the `-1` the whole NaN-window branch exists for, and the sentence claiming the flags are "{−1, 0, 1}" is describing an array that contains no `1` by construction. That is not a bug — the equivalence is structural and the `-1` path is pinned elsewhere — it is worse in this repo: it is a claim written before it was measured, re-dressed as a receipt. Four lines in `cost()` and a `bincount` print close it. Fix that, correct the 6.4-of-11.7 arithmetic in the module comment, pin the spelling your prose now argues for, and this port is done.
```

**Fixes applied (round 3 → 4):** `cost()` now builds its flag array with
`module_flags()` — the module's own expression — over a 400,000-bar frame with
a NaN and a `-inf` planted, prints the census (measured: −1 × 10,
0 × 343,609, 1 × 56,377 of 399,996 candidates) and asserts that the retyped
copy reproduces the shipped column on all 399,981 bars; the receipt now says
the equivalence is **structural** and the run only a smoke test, with the
census as evidence that the smoke test had something to find; the module
comment quotes the traced 6.8 / 98.7 against 0.8 MB instead of the 6.4-of-11.7
arithmetic; `test_the_nan_window_test_keeps_its_cheap_spelling` pins the source
line; the masthead scopes the "exactly four commands" claim to what the session
measured.

## Round 4 — VERDICT: PASS (3 MINOR, 3 NIT)

Verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: pandas_ta/statistics/ts_peaks_20.py:204 (and docs/TsPeaks20Measured.md:488)
    problem:  "it invalidates the `2 * SUPPORT + 1` = 5 candidates it sits in and so
              empties exactly `length` = 20 bars at the default -- measured" is an
              INTERIOR-bar statement sold as the rule. It was measured at bar 200 of a
              400-bar frame and nowhere else. A non-finite close at bar n-1 is a
              candidate for only one window: it invalidates candidate n-3 (n-2 and n-1
              are not candidates at all), so exactly ONE bar goes NaN, not 20. Same at
              the head: a NaN at bar 5 invalidates candidates 3..7, whose windows end at
              T in [5, 24], and the warm-up swallows all but bars 19..24 -- six. The
              "exactly 20" holds only for 19 <= b <= n - 20. The guards bullet at
              docs/TsPeaks20Measured.md:488 carries the same bolded absolute as a
              headline, then scopes it to bar 200 in the next sentence.
    fix:      In both places, state the rule and then the measurement: "a window is
              emptied iff it holds a non-finite close, so an INTERIOR close (bar
              `length - 1` .. `n - length`) empties exactly `length` bars -- measured at
              bar 200 of a 400-bar frame -- and one nearer either end empties fewer
              (a NaN at the last bar empties one)." Add the edge case to
              `test_a_non_finite_close_empties_exactly_length_bars` as a second
              parametrisation (bad at bar `len-1`, expect 1 emptied bar) so the
              qualifier is pinned, not just written.
  - severity: MINOR
    location: docs/TsPeaks20Measured.md:92-114 (section "⚠ The port IS the column the screen measured")
    problem:  The section header claims identity "bit-for-bit" and the table's four rows
              are all clean synthetic frames. The port and the prototype are NOT the
              same function off clean data, and this document says so forty lines later
              without connecting the two: line 491 boasts that the port "refuses rather
              than reading the NaN as 'not a peak', which would undercount silently" --
              which is precisely what the prototype does. `pk = (x > c.shift(3)) & ...`
              is False at a NaN, `.astype(float).rolling(16).sum()` still returns a
              number, and `.where(c.shift(19).notna())` masks only the one bar 19 after
              the NaN. So for a non-finite close at bar k the prototype emits 19
              undercounted values where the port emits NaN. The module docstring gets
              this right twice ("bit-equal to it on every clean frame measured"); the
              receipt's headline does not, and it is the headline that the "indicative"
              Gate E transfer leans on -- on real BIST frames the two columns can differ
              in exactly the bars the port refuses.
    fix:      Add one sentence under the table: "Measured on clean frames only. The
              prototype reads a NaN comparison as 'not a peak' and still emits a count;
              this port empties the window (§Guards), so the two part company on any
              frame carrying a non-finite close -- how often that happens on the 89 BIST
              frames comes with Gate E's real-data counts." Reword the header to "the
              port is the screen's column on clean data".
  - severity: MINOR
    location: tests/test_ts_peaks_20.py:870
    problem:  The designed-probe test's accounting branch is `elif not
              leg_flags[p - SUPPORT]`, with `leg_flags = _mutant_flags_of(...)` --
              `forward_leg`'s flag -- for BOTH parametrisations. `docs/measure_ts_peaks_20.py:683`
              guards the same branch with `name == "forward_leg"`; the test dropped the
              guard. It passes today only because `forward_flag` is caught 50/50, so
              `dead` stays 0 by luck. If `forward_flag` ever came in at 49, `dead` would
              be incremented off an unrelated mutant's flag array and
              `assert mut_hits + dead == 50` could pass on nonsense -- the one assertion
              the test's own docstring calls "the part that cannot drift".
    fix:      Make it `elif mutant == "forward_leg" and not leg_flags[p - SUPPORT]:` and
              add `if mutant == "forward_flag": assert dead == 0` so the 50/50 row is
              pinned as exhaustive rather than accidentally consistent.
  - severity: NIT
    location: docs/TsPeaks20Measured.md:18-21
    problem:  "Figures *quoted from outside* those runs are labelled where they appear,
              and there are three" -- there are four. The Gate E configuration at lines
              408-411 (the 89 frozen ALTPORT-1 frames, 329 + 358 = 687 comparators, the
              `r3-perframe-0.90` bands) is quoted from CLAUDE.md and measured by nothing
              in this session. It is attributed in place, so this is a miscount in the
              document's own honesty contract rather than an unsourced number -- which
              is still the genre of defect this repo is named after.
    fix:      Make it four items and name the fourth: "and the Gate E configuration
              quoted from `CLAUDE.md` (89 frames, 687 comparators, the
              `r3-perframe-0.90` bands)."
  - severity: NIT
    location: pandas_ta/statistics/ts_peaks_20.py:119 (and docs/TsPeaks20Measured.md:60)
    problem:  "The freshest bar it can read is T-2, by construction" contradicts the
              docstring's own Causal line ("bar T reads closes T - length + 1 .. T") and
              the sentence immediately after it ("the newest two closes of the window
              enter ONLY as confirmation"). The column DOES read close T; what it cannot
              do is count bar T. A consumer who takes the heading literally will
              conclude today's close is not an input at all.
    fix:      "The freshest bar it can COUNT is T-2" in both places; keep the
              confirmation sentence as the explanation.
  - severity: NIT
    location: docs/TsPeaks20Measured.md:526-529 (Cost, the length table)
    problem:  Re-run on this machine today: 22 / 35 / 66 ms against the table's
              22 / 30 / 65. The 60-row is 17% off. The section's closing line ("A wall
              time is the one number here that cannot be re-run to the digit") covers
              the digit, not a 17% gap, and the module docstring repeats "~22 / 30 / 65".
    fix:      Re-take the three rows in one run and quote them as bands ("22-23 /
              30-35 / 65-66 ms, best of three, two runs on one machine"), or drop the
              length-60 wall time and keep only the memory column, which is the claim
              that section exists to make.
  - severity: NIT
    location: docs/measure_ts_peaks_20.py:695-708, 971-977
    problem:  The Cost section asserts "the flag array it runs on is the MODULE's own",
              but `module_flags()` is a RETYPED copy of lines 45-59 with nothing tying
              it to the module. Edit the module's flag expression and the any-vs-min
              smoke test keeps reporting a three-valued census over code that no longer
              ships -- the same silent-rot failure mode the new source-pin test was
              added to close.
    fix:      In `cost()`, after building `flags`, assert the copy reproduces the module:
              `w = sliding_window_view(flags, CANDIDATES); expect = np.where(w.min(axis=1) < 0,
              np.nan, w.sum(axis=1, dtype=np.int64)); assert np.array_equal(expect,
              ts_peaks_20(Series(c)).to_numpy()[LENGTH - 1:], equal_nan=True)` and print
              the assertion's result as part of the receipt.
SUMMARY: Round 3's four fixes all landed and all four survive re-measurement: `cost()`
now builds its flag array from the module's own expression over a 400,000-bar frame with
a NaN and a `-inf` planted and prints the census I reproduced to the unit (−1 × 10,
0 × 343,609, 1 × 56,377 of 399,996), so the any-vs-min agreement check finally has
something to find; the 6.4-of-11.7 arithmetic slip is gone and the module comment quotes
the traced 6.8 / 98.7 against 0.8 MB, which is what the run prints; the spelling the
prose argues for is pinned by source in test 185 of 185; and the masthead no longer
claims an unqualified "exactly four commands". Gate A reproduces to the last digit on
every one of the thirty-odd A5 figures, the `np.roll` oracle and the scalar loop are
581/581 on every frame claimed, the ceiling enumeration lands on one subset, Gate B's
designed probe is genuinely decisive where the blind sweep is honestly admitted to be
blunt — the 2-of-37 row is explained as a set equality and holds — and the slicing is
causal when I walk the indices by hand: row r of the window view covers candidate bars
T-17..T-2, never T-1. The five touch points, the four count surfaces and the owed-ledger
state are all exactly where they should be. What is left is small and all of one kind:
you still write absolutes one bar wider than you measured them. "Empties exactly 20 bars"
is true for bar 200 and false for bar 399, and you measured one of them. "The port IS the
column the screen measured, bit-for-bit" is true on the four clean frames you ran and
false the moment a close is not finite — a divergence your own Guards section brags about
on line 491 and your §A2 header does not mention. Fix the scope of those two sentences and
restore the `name == "forward_leg"` guard the test lost on its way out of the measure
script. It clears the bar.
```

**Fixes applied (round 4 → 5), even though the verdict was PASS:** the
emptied-bar rule is now stated as the INTERIOR rule in both prose surfaces,
`guards` prints the emptied count for a NaN at ten bar positions (measured:
1 / 3 / 6 / 20 / 20 / 20 / 20 / 20 / 3 / 1 at bars 0 / 2 / 5 / 19 / 21 / 200 /
379 / 380 / 397 / 399) and
`test_near_either_end_a_non_finite_close_empties_fewer_bars` pins seven of
them; §A2 is renamed "the port is the screen's column ON CLEAN DATA" and
carries a measured paragraph on the divergence (one NaN at bar 200 of a
400-bar walk: 19 bars where the port is NaN and the prototype emits a number,
361/361 agreeing elsewhere), mirrored in the test docstring; the designed
probe's `dead` branch is guarded by `mutant == "forward_leg"` with
`dead == 0 and mut_hits == 50` asserted for `forward_flag`; the masthead names
four quoted-from-outside figures; "read" became "COUNT" in both places; the
cost wall times are bands over the session's four `cost` runs; and `cost()`
asserts its retyped `module_flags` copy reproduces the shipped column on all
399,981 bars. Test count 185 → 192.

## Round 5 — VERDICT: PASS (4 NIT)

Round 5 exists because round 4's fixes landed after its PASS. Verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: docs/TsPeaks20Measured.md:546 (Cost, length table)
    problem:  The length-20 cell says "22 ms" flat while line 539 bands the
              IDENTICAL measurement — n = 400,000 at the default length, same
              `walk(400000, seed=12)` frame, same best-of-three — at "22-24 ms".
              Line 550 then declares every time in that table a band over four
              runs. My two re-runs confirm the two blocks disagree (n-sweep 23 ms,
              length-sweep 22 ms), which is exactly why one cell must not pose as
              a single reproducible reading when its twin two lines up does not.
    fix:      Write "22-24 ms" in the length-20 cell, or append to line 550:
              "the length-20 row is a second timing of the n = 400,000 row above,
              hence the same 22-24 ms band."
  - severity: NIT
    location: pandas_ta/statistics/ts_peaks_20.py:218
    problem:  "65-66 ms (best of three, over four runs on one machine). That is
              the reason `bad` is spelled" runs to 93 characters — the only prose
              line over 79 in the file, and it is the line the round-4 Cost fix
              touched. Lines 119-122 are left similarly ragged ("A peak at bar P"
              alone on line 121) by the fix-5 reword.
    fix:      Re-wrap 216-219 and 119-124 at 78 columns, as the rest of the
              docstring is.
  - severity: NIT
    location: docs/TsPeaks20Measured.md:585-586
    problem:  "A wall time is the one number here that cannot be re-run to the
              digit" repeats, 33 lines later and weaker, the caveat lines 551-553
              already state ("a best-of-three wall time is the one number here
              that does not reproduce to the digit"). The duplicate makes the
              second statement look like a separate claim.
    fix:      Delete the trailing sentence at 585-586 and end the paragraph at
              "...a few `bool` arrays of the same length."
  - severity: NIT
    location: docs/TsPeaks20Measured.md:166-169 (§A2)
    problem:  The A2 stub still reads "bit-equal on 1,481 of 1,481 bars of four
              frames" with no clean-data qualifier. It is true and it points at
              the section that qualifies it, but A2 is the line a reader lifts
              when quoting the gate, and round 4's finding was precisely that the
              A2 headline sold bit-equality without the NaN caveat.
    fix:      Make line 168 read "See the previous section: bit-equal on 1,481 of
              1,481 bars of four CLEAN frames (off clean data the two part
              company — same section)".
SUMMARY: The six fixes are real, not cosmetic, and I could not find a number in
this deliverable that failed to reproduce — gate_a through cost, 192 module
tests, 3/6,285/83 on the full suite, the Gate B sweep's thirty cells, the guards'
1/3/6/20/20/3/1 edge span, the 19-bar prototype divergence, the designed probe's
guarded `dead` accounting, the fourth quoted-from-outside figure sitting where
CLAUDE.md:155 says it sits. The emptied-window "iff" and the interior-bar rule
survive a structural check, not just a sample: emptied = [b, b+length-1] clipped
to the warm-up and the frame end, which is what both prose surfaces now say. What
is left is four pieces of lint: one cost cell quoting a single wall time where its
own twin table bands the same measurement, a 93-character line and a ragged
re-flow left by the two prose edits, a duplicated caveat sentence, and an A2 stub
that still reads quotable-without-the-asterisk. None of that ships a bug or a
false claim. Fix the lint and stop polishing; the module is done and Gate E is
the launcher's problem.
```

**Fixes applied after round 5 (UNREVIEWED):** all four NITs — the length-20
cost cell banded 22–24 ms with a line saying why, the module docstring
re-wrapped at the two ragged spots, the duplicated wall-time caveat deleted,
and the §A2 stub qualified with "four CLEAN frames". These four edits landed
after the loop's last gate and no reviewer has seen them. They touch prose
only; `python -m pytest -q` was re-run on the committed tree afterwards
(**3 failed, 6,285 passed, 83 skipped**, 133.15 s, the same three failures).

## Assumptions and observations

* The five ASSUMPTIONs of `00-manifest.md` stand, each priced in §A5.
* **Observed, pre-existing, NOT fixed:** `pandas_ta/core.py:691-692` mutates
  the global `Category` — `_indicators_by_category` returns `Category[name]`
  itself (line 453) and `strategy()` then calls `.remove()` on it for every
  excluded indicator. So a category-mode `df.ta.strategy("momentum")` run
  permanently deletes three names from `Category` in that process. Measured in
  this session: running `tests/test_wiring_accessors.py` before
  `tests/test_altport2_ports.py` makes
  `test_the_category_count_moved_by_exactly_three` report "Category total 322,
  expected 325". The full suite's own ordering (alphabetical) does not hit it,
  which is why this is invisible in CI and in the numbers above. It is an
  upstream global-state defect unrelated to this port, and fixing it would
  change `strategy()` behaviour well outside issue #92's scope — left for the
  owner.
