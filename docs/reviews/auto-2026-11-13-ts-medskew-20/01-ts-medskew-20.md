# TS-MEDSKEW-20 — task log

Lane: main thread. Four Fletcher review rounds (REVISE, REVISE, REVISE,
REVISE-with-two-blockers), every finding applied. Each reviewer was a fresh
read-only subagent with no memory of the work; each one re-ran
`docs/measure_ts_medskew_20.py` (all seven sections), the test module, the
AVX-disabled re-run and the ledger test before writing its contract.

## Implementation summary

`TS_MEDSKEW_20 = (mean(r) − median(r)) / sd(r)` over 20 simple returns, sd
with `ddof=1` — the nonparametric skewness of the window.

* `pandas_ta/statistics/ts_medskew_20.py`: returns as a price RATIO minus one
  (so a ×2^k rescale cancels exactly), a per-return square bound, window mean
  and two-pass sd from a `sliding_window_view` with a per-position deviation
  loop (no `(rows, length)` temporary), the median from pandas' rolling skip
  list, a RELATIVE dispersion floor (`4096 eps × max|r|`) and an `isfinite`
  backstop.
* `tests/test_ts_medskew_20.py`: 207 tests.
* `docs/measure_ts_medskew_20.py`: sections A, B, C, D, G, O, Z — every
  number in the receipt and in both docstrings.
* `docs/measure_ts_medskew_20_cpu.py`: the module's tests with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.
* `docs/TsMedskew20Measured.md`: the receipt. Gate E pending.
* Wiring: touch points 2–4, `README.md` (331/339/statistics 40),
  `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
  (676 tagged columns, 318 `SF`), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 331).

## Round 1 — VERDICT: REVISE

2 CRITICAL, 2 MINOR, 2 NIT.

1. **CRITICAL** `pandas_ta/statistics/ts_medskew_20.py` (the comment above
   `reported &= np.isfinite(value)`) — claimed the backstop "HAS a witness: at
   return magnitudes below about 1e-150 …", where §G4 of the receipt is titled
   "has NO witness" and the run shows the frame cannot be built (`1 + 1e-150`
   is `1.0`). *Fix applied:* the comment now says NO witness, kept
   deliberately, with the arithmetic reason and the role it plays in the Gate
   B zero-patch probe.
2. **CRITICAL** module docstring, locality paragraph — "at x1e+02, x1e+06,
   x1e+08, x1e+100 and x1e+300 the 20 windows holding it read 0.223607":
   x1e+300 is above the 1.06e+153 per-return bound and those windows are
   EMPTY, and x1e+02 reads 0.223491. The receipt's §G7 table and the test both
   had it right; only the shipped docstring was wrong. *Fix applied:*
   rewritten.
3. **MINOR** the ulp argument used only the upward ulp (2.220e-16); downwards
   it is 1.110e-16. *Fix applied:* the script prints both.
4. **MINOR** "merged … one day before this one" — same day (6ace3dd 16:28,
   merge b99eeb5 17:30). *Fix applied:* commits quoted instead of an interval.
5. **NIT** `docs/IndicatorDictionary.md`'s row carries no disclosure.
6. **NIT** a 0.81 s timing that moves between runs.

> SUMMARY (verbatim, trimmed to its verdict sentences): "You measured
> everything and then transcribed from memory into the one file a consumer
> actually opens. That is not a rounding error, it is the exact defect
> CLAUDE.md names as this repo's dominant one … Fix the four lines, re-read
> the module docstring against the receipt line by line rather than by
> recollection, and this is a pass."

## Round 2 — VERDICT: REVISE

1 CRITICAL, 5 MINOR, 2 NIT.

1. **CRITICAL** the ulp fix had landed in the module and the receipt but NOT
   in `tests/test_ts_medskew_20.py`'s headline docstring, which still said
   2.2e-16 — the same file saying 1.110e-16 832 lines later. *Fix applied.*
2. **MINOR** `((NOISE_FACTOR*rmin)/LENGTH)**2` was labelled "the smallest
   squared-deviation SUM"; it is not that quantity. *Fix applied:* re-derived
   as `(s/2)²` — the two extremes straddle the mean, so one is at least `s/2`
   from it — 2.549e-57, relabelled in four files.
3. **MINOR** the rewritten locality paragraph said twenty windows "read" a
   value of which only the MEDIAN was computed. *Fix applied:* "fire, with a
   median of …", and §G7 now also prints the 20 windows' spread.
4. **MINOR** the backstop test probed 13 frames where the docstrings said 14.
   *Fix applied:* the quiet frame added, and the count tied to `FRAMES`.
5. **MINOR** the sixth of "six readings priced" was not priced — it pointed at
   a different variant. *Fix applied:* `|mean−median|/sd` measured (Spearman
   −0.206800, bit-equal 642/1,480) and pinned by a new test.
6. **MINOR** the ×3 test asserted a Spearman true of any series. *Fix
   applied:* it pins the measured max |difference| instead.
7. **NIT** 8.6e-14 against a measured 8.520e-14.
8. **NIT** "empties the same 1,459-of-1,500" — 1,459 is the number that fire.

> SUMMARY (verbatim, trimmed): "One file, two numbers, same quantity, and the
> one on the front page is the wrong one; that is the whole historical defect
> of this repo wearing a fresh coat."

## Round 3 — VERDICT: REVISE

1 CRITICAL, 2 MAJOR, 3 MINOR, 2 NIT.

1. **CRITICAL** the 8.6e-14/3.4e-16 fix had landed in the headline docstring
   only; the test's own docstring still carried the stale pair. *Fix applied.*
2. **MAJOR** the same stale 3.4e-16 had propagated into
   `docs/MLCompanionContract.md`. *Fix applied.*
3. **MAJOR** four order-of-magnitude claims asserted rather than divided
   ("three orders" for a ratio of 3.9e+05). *Fix applied:* each recomputed
   from the printed figures, with the ratio stated beside it.
4. **MINOR** bare millisecond figures outside the disclaimed paragraphs. *Fix
   applied:* ms dropped, peaks kept.
5. **MINOR** the `OSAP_RETSKEW_21` bullet claimed its length-21 figures were
   "identical to the rolling-skew row", which is §O3b's length-20 re-run.
   *Fix applied.*
6. **MINOR** the dictionary row carried no disclosure. *Fix applied:* the
   module docstring's opening paragraph was rewritten so the overlap lands
   inside the 150 characters `gen_indicator_dictionary.py` keeps; the row now
   reads "⚠ Overlaps the shipped TS_ABOVE_MEAN_20 at 0.8428 on real frames."
7. **NIT** four unfailable assertions. *Two replaced by measured bands, two
   kept as explicit derivations and labelled as such.*
8. **NIT** the spike test parametrized five magnitudes where the docs say six.
   *Fix applied:* `1e154` added.

> SUMMARY (verbatim, trimmed): "The port is sound; the paperwork is where it
> keeps bleeding, and it bleeds in the same vein every round — orders of
> magnitude asserted instead of divided."

## Round 4 — VERDICT: REVISE

1 CRITICAL, 1 MAJOR, 2 MINOR, 3 NIT. **This was the fourth and last round
allowed; both blockers were applied, and no fifth reviewer ran.**

1. **CRITICAL** — *this port makes a SHIPPED docstring false.*
   `pandas_ta/statistics/ts_above_mean_20.py:178` says of the 0.8428 pair
   "still a prototype and not shipped (issue #98)", and
   `docs/TsAboveMean20Measured.md` §5 lists "no module in `pandas_ta/`" as one
   of three reasons not to revert that column. Both go false the moment this
   branch merges.
   *Response:* **neither file is in this session's allowed-modify list**
   (issue #98's rules permit modifying `README.md`,
   `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
   `docs/gate_e_ledger.csv`, `pandas_ta/__init__.py`, `pandas_ta/core.py`,
   `pandas_ta/{category}/__init__.py`, `tests/test_altport2_ports.py`, and
   adding new files only). Editing them would block the push. So the finding
   is recorded instead, in three places: a new table in
   `docs/TsMedskew20Measured.md` §O naming both files and both line numbers,
   with the annotation the receipt session should append; a dated correction
   in `docs/MLCompanionContract.md`, whose copy of the same clause IS in the
   list; and the commit message. **This is the one round-4 finding not fixed
   as the reviewer asked, and the reason is scope, not disagreement.**
2. **MAJOR** §G3's "the spread is 3.6e-13, three orders above …" was derivable
   but not printed by any section — in the one sentence that calls itself a
   measurement, justifying the departure from three sibling ports' absolute
   floor. *Fix applied:* §G3 now prints the quiet frame's median window spread
   (3.648e-13), both floors and the ratio to §D4's rounding spread
   (8.215e+02), and the receipt and the test quote the printed values. The
   mirror frame's spread (3.575e-14 against a 4.547e-13 floor) is printed too.
3. **MINOR** Gate F carried no full-suite numbers, only a pointer to a commit
   message that did not yet exist. *Fix applied:* the measured counts and the
   three failing test ids are in §F.
4. **MINOR** "the two `CLAUDE.md` Known breaks" — that section documents ONE;
   the second failure is the `../AlternativeRepos`-only test CI deselects by
   name. *Fix applied.*
5. **NIT** a quotation mark around a phrase that is not verbatim in the file
   cited. *Fix applied:* the verbatim half is quoted and the rest attributed
   to `docs/MLCompanionContract.md`, both re-greped.
6. **NIT** "the sixth open reading" where the lists call it the third. *Fix
   applied.*
7. **NIT** `assert len(probes) == 14` cannot fail. *Fix applied:*
   `len(probes) == len(FRAMES) + 5 == 14`, so adding a frame fails here.

> SUMMARY (verbatim, trimmed): "You spent an entire receipt section arguing
> that the 0.8428 pair is the fact a consumer must know — five places carry
> the disclosure, you counted them — and you left the SIXTH place, the shipped
> docstring of the other half of the pair, telling that consumer
> `ts_medskew_20` is 'still a prototype and not shipped'."
