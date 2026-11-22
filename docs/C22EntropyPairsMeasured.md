# `c22_entropy_pairs` — measured

**Issue:** [#133](https://github.com/TolgaUyanik/PandasTa/issues/133) · C22-ENTROPY-PAIRS ·
catch22 entropy of 2-letter words in a 3-quantile return alphabet (100)
**Module:** `pandas_ta/statistics/c22_entropy_pairs.py` · **Column:** `C22ENTROPYPAIRS_100`
**Harness:** `docs/measure_c22_entropy_pairs.py` (sections S, A–D, G; **P** is
opt-in and is the only place in this repository that runs the GPL-3.0
reference)
**CPU re-run:** `docs/measure_c22_entropy_pairs_cpu.py`
**Tests:** `tests/test_c22_entropy_pairs.py` (116 tests)
**Measured:** 2026-11-21, numpy 1.26.4 / pandas 2.3.3 / python 3.11.2, with
`AVX512F AVX512_SKX AVX2 FMA3` **enabled** (the CI dispatch is §F1).

**Gate E: measured 2026-11-21 on the Hazen column (this receipt session).**
Run `is133-c22_entropy_pairs-43140f40`, 89 ALTPORT-1 frames, 398,849 pooled
bars, 687 comparators (329 `compute_all` + 358 `ml_features` manifest),
canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`). `C22ENTROPYPAIRS_100`:
max |ρ| 0.12465894564119429 vs `ROLLING_LOW_250` (n = 376,599), per-frame max
median 0.12777015187024565 vs `ROLLING_HIGH_250` — **SHIP** (< 0.76 line).
Recorded in `docs/gate_e_ledger.csv`. This supersedes the earlier type-7
column's run (`is133-c22_entropy_pairs-d0ad14ca`, max |ρ| 0.1371), removed
from the ledger when review round 2 swapped the quantile convention; §E
below keeps that superseded number for context only.

---

## 0. What the column is

Cut the last 100 daily simple returns into 3 letters at their own 1/3 and 2/3
empirical quantiles, read off every overlapping 2-letter word, and report the
Shannon entropy of the observed word-type distribution, in nats, over the 9
possible word types:

```
r[t]   = close[t] / close[t-1] - 1
Z      = (X - mean(X)) / sd(X, ddof=1)                     # inert, §A3
q1, q2 = the 1/3 and 2/3 empirical quantiles of Z (Hazen interpolation)
k[t]   = how many of {q1, q2} that Z[t] stands strictly above
W      = {(k[t], k[t+1]) : t = 1 .. 99}                    # 99 overlapping words
C22ENTROPYPAIRS = -sum over observed word types of p * log(p)
```

Three things a reader has to know before using it:

1. **It is bounded in `[0, log 9]` = `[0, 2.1972245773362196]`**, an
   ENCLOSURE reached only by a perfectly uniform 9-way distribution.
   Measured range over six synthetic frames: **1.263948 to 2.197225**
   (§C1) — close to the top of the scale on five of six, because 99
   overlapping words over 9 types land near-uniform on most return
   sequences that are not themselves highly repetitive.
2. **The quantile ESTIMATOR is an open reading the definition does not
   settle, and this port follows the source: the Hazen rule** (MATLAB/
   hctsa's own `quantile`, since hctsa is MATLAB — see §P1). `numpy.
   quantile`'s own default ("type 7") was considered and rejected: it does
   not reproduce the GPL-3.0 reference bit for bit either, and §P1 found no
   measured reason to prefer it over Hazen (median gap ties, max gap is
   worse). Neither convention reproduces the reference bit for bit — see §P
   — and §P3's designed-input probe explains why a black-box fit cannot
   settle this choice at all: Shannon entropy over the 9 word-type counts is
   invariant to a boundary shift that only PERMUTES which category holds
   which count, which is exactly what moving between quantile conventions
   does on rank-only data. The structural reading (overlapping pairs,
   natural log, divisor `length - 1`) is measured to reproduce the GPL-3.0
   reference EXACTLY on three designed, rank-only inputs (§P3) — the
   strongest Gate A corroboration this receipt has — while the one
   structural near-miss on real data (§P2's divisor-98 candidate) does NOT
   reproduce the reference on those same designed inputs, so it is ruled out
   as a fitting artifact rather than a hint at the true structure. The ~0.02
   median gap to the reference on real (non-designed) windows remains
   disclosed as unidentified.
3. **Z-scoring is INERT** (§A3): the empirical quantile of an increasing
   affine map of a sample is the same affine map of the quantile of the
   sample, so no letter boundary can move relative to the data under a
   positive rescale or a shift.

## 1. Attribution, and what it is NOT evidence of

catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data Mining and
Knowledge Discovery* 33:1821), feature `SB_MotifThree_quantile_hh` of catch22
1.0 — hctsa's `SB_MotifThree(y, 'quantile', 3)`, the `hh` (two-letter-word)
output.

The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this fork is
MIT. This module was written from the paper's description of the motif/word
feature family and from hctsa's published operation name and parameters,
never from the reference's source; no shipped module imports it
(`tests/test_c22_entropy_pairs.py::test_the_reference_implementation_is_not_imported_by_shipped_code`
sweeps every `.py` file under `pandas_ta/`); and the one place it is run at
all is §P below — opt-in, measurement only, the same use the owner's own
screen prototype makes of it.

⚠ catch22 is a subset selected for **time-series classification** performance
on 93 reference problems. That is not return prediction, and nothing here
tests it on BIST: the presence of this column in the fork is **existence,
not evidence**.

---

## A. Gate A — correctness

### A1. The exact rational oracle — zero roundings on the letter sequence

Hazen-interpolated quantiles are a RATIONAL function of the order statistics
(virtual index `p * n - 1/2`, no irrational operation), so the letter
sequence can be recomputed with zero rounding (`Fraction` arithmetic) and
compared to the shipped float pipeline.

| frame | windows | letter sequences equal | max \|value gap\| |
|---|---|---|---|
| walk | 15 | **15** | 0.00e+00 |
| tick-rounded | 15 | **15** | 0.00e+00 |
| penny | 15 | **15** | 0.00e+00 |
| ar1 | 15 | **15** | 0.00e+00 |
| cosine | 15 | **15** | 0.00e+00 |
| student-t | 15 | **15** | 0.00e+00 |

15 of 15 sampled windows per frame, stride 97. The value gap is exactly 0.0
because once the letter sequence matches, both spellings reduce to the same
`bincount` + `log` arithmetic on the same integers.

Under Hazen's virtual index `p * n - 1/2`, the default `length` = 100
already interpolates for real at both cuts (32.8333 and 66.1667 of 99
returns, neither an integer) — unlike the REJECTED type-7 reading, where
`(length - 1) * p` lands exactly on 33.0 and 66.0 at this length (99 is
divisible by 3) and the quantile is a plain order statistic with `frac` = 0.
A second run at `length` = 120 (cuts at 39.5 and 79.5 of 119 returns — an
exact half rather than a repeating third) is kept as a second, independently
-fractioned data point rather than the only one that exercises
interpolation:

| frame | windows | letter sequences equal | max \|value gap\| |
|---|---|---|---|
| walk | 15 | **15** | 0.00e+00 |
| tick-rounded | 15 | **15** | 0.00e+00 |
| penny | 15 | **15** | 0.00e+00 |
| ar1 | 15 | **15** | 0.00e+00 |
| cosine | 15 | **15** | 0.00e+00 |
| student-t | 15 | **15** | 0.00e+00 |

(`tests/test_c22_entropy_pairs.py::test_bit_equal_to_the_exact_rational_oracle_non_integral_index`)

### A2. A second spelling, sharing no code with the module

Plain Python with `math.fsum` and a hand-written linear-interpolation
quantile function, no numpy vectorisation.

| frame | windows | max \|gap\| |
|---|---|---|
| walk | 200 | 8.88e-16 |
| tick-rounded | 200 | 8.88e-16 |
| penny | 200 | 4.44e-16 |
| ar1 | 200 | 6.66e-16 |
| cosine | 200 | 2.22e-16 |
| student-t | 200 | 8.88e-16 |

### A3. Z-scoring is INERT, and that is a property of the quantile

The empirical quantile of an increasing affine map of a sample is the same
affine map of the quantile of the sample, so no letter boundary can move
relative to the data under a positive rescale or a shift.

| frame | windows | ddof 0 moved | no z-score moved | shifted +1 moved |
|---|---|---|---|---|
| walk | 467 | **0** | **0** | **0** |
| tick-rounded | 467 | **0** | **0** | **0** |
| penny | 467 | **0** | **0** | **0** |
| ar1 | 467 | **0** | **0** | **0** |
| cosine | 467 | **0** | **0** | **0** |
| student-t | 467 | **0** | **0** | **0** |

The z-score is written out anyway because it is what catch22 does before
every feature; this inertness is a measured fact and not an obvious one.

### A4. Word order reversed — dead up to summation order, not bit-equal

Swapping `(letter[t], letter[t+1])` for `(letter[t+1], letter[t])` transposes
the 3×3 count table: it permutes which of the 9 cells holds which count, but
changes no count's VALUE, so the entropy — a function of the MULTISET of
probabilities — is mathematically identical. It is **not** bit-equal, because
the two sums add the same nine terms in a different order and floating
addition is not associative.

| frame | windows | moved (tol 1e-9) | mask differs | max \|gap\| |
|---|---|---|---|---|
| walk | 467 | **0** | 0 | 4.44e-16 |
| tick-rounded | 467 | **0** | 0 | 4.44e-16 |
| penny | 467 | **0** | 0 | 8.88e-16 |
| ar1 | 467 | **0** | 0 | 8.88e-16 |
| cosine | 467 | **0** | 0 | 2.22e-16 |
| student-t | 467 | **0** | 0 | 8.88e-16 |

---

## B. Gate B — causality and sweep power

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a fresh
path; no bar before J may move.

| frame | offsets | splices | leaking offsets |
|---|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 35 each | 8 | **none** |
| walk at `length` 10 (`MIN_LENGTH`), 120, 250 | 35 each | 4 | **none** |

### B2. Mutants read off this module's source, edited and exec'd in memory

Walk frame, 35 offsets × 8 splices (or 12 for the mask mutant).

| mutant | what it does | offsets caught of 35 |
|---|---|---|
| write-back-dated | writes each chunk one bar early | **≥10** (measured ≥10 of 35) |
| window-one-ahead | each window reads one return from the future | **≥10** |
| window-ten-ahead | each window reads ten returns from the future | **≥10** |
| returns-rolled | the return series is shifted one bar earlier | **≥10** |
| chunk-wide-quantile | the cut points come from the whole chunk's flattened returns | **≥10** |
| mask-back-dated | the bad-data MASK reads the next bar | 0 of 35 (bit-equal on clean, caught 12 of 12 on a dirty frame) |
| chunk-wide-demean | each row is centred on the chunk's mean | 0 (dead, §B3) |
| chunk-wide-sd | each row is scaled by the chunk's sd | 0 (dead, §B3) |
| word-order-swapped | transposes the 3x3 count table | 0 (dead to tolerance, §A4) |
| no-overflow-guard | drops the `isfinite(sd)` limb | 0 (not a look-ahead) |
| no-floor | drops the noise floor | 0 (not a look-ahead) |

### B3. Two mutants are DEAD by the same affine invariance as §A3

`chunk-wide-demean` and `chunk-wide-sd` replace each row's own mean or
standard deviation with the whole CHUNK's — a per-row affine map, which §A3
already showed cannot move a letter boundary. Measured: bit-equal to the real
module on all 1,500 bars of walk, tick-rounded and penny.

### B4. Tie density and distinct values — the sweep's power

| frame | fired | distinct values | share of neighbouring pairs tied | min | max |
|---|---|---|---|---|---|
| walk | 1,400 | **509** | 0.1237 | 2.124410 | 2.196305 |
| tick-rounded | 1,400 | **576** | 0.0879 | 2.106414 | 2.196305 |
| penny | 1,400 | **745** | 0.1372 | 1.263948 | 2.197225 |
| ar1 | 1,400 | **944** | 0.1823 | 1.886269 | 2.163134 |
| cosine | 1,400 | **34** | 0.6269 | 1.635248 | 1.659793 |
| student-t | 1,400 | **609** | 0.1008 | 2.110775 | 2.196305 |

This column takes an INTEGER-bincount-derived value (unlike `c22_ami2`'s
continuous mutual information), so tie shares are higher (8.8%–62.7%) and
distinct-value counts lower — the sweep still catches every look-ahead mutant
that can move a CLEAN frame on the 35-offset test above because 8 independent
splices per offset are enough even at these tie rates. The one look-ahead
mutant that cannot move a clean frame, `mask-back-dated` (§B2), is caught on
a dirty one instead.

---

## C. Gate C — reachability

### C1. Synthetic frames (1,500 bars each)

| frame | fired | distinct | min | median | max |
|---|---|---|---|---|---|
| walk | 1,400 | 509 | 2.124410 | 2.182310 | 2.196305 |
| tick-rounded | 1,400 | 576 | 2.106414 | 2.179048 | 2.196305 |
| penny | 1,400 | 745 | 1.263948 | 2.174901 | 2.197225 |
| ar1 | 1,400 | 944 | 1.886269 | 2.035946 | 2.163134 |
| cosine | 1,400 | 34 | 1.635248 | 1.656649 | 1.659793 |
| student-t | 1,400 | 609 | 2.110775 | 2.178843 | 2.196305 |

Derived bounds: `[0, 2.1972245773362196]`. The column sits near the top of
the scale on five of six synthetic frames, because 99 overlapping 2-letter
words spread over 9 types land close to uniform on most non-repetitive
sequences — this is the column's own baseline, not a sign that it is
constant: the walk frame alone has 509 distinct values.

### C2. The issue's own worry: BIST tick rounding

The penny frame (a 2-lira stock on a 1-kurus tick) has 21.68% of its returns
exactly 0.0. Its first window's 3 letters hold 33 / 34 / 33 points — the
quantile split still comes out close to equiprobable despite the rounding,
because the ties sit at the SAME return value and so fall together inside
whichever letter their quantile band lands in, rather than collapsing two
letters into one the way a fixed-width bin would. The column still fires
everywhere, with 745 distinct values (the most of any non-ar1 frame) and the
widest range (1.263948 to 2.197225) of the six synthetic frames.

### C3. What the blanking floor costs

| frame | fired | why |
|---|---|---|
| flat-from-bar-400 (700-bar walk, flattened from 400) | **399** | blanks from the first all-zero-return window (bar 499) |
| exact geometric ladder (`step` 0.01 / 0.001 / −0.005) | **0** of 1,500 each | return sd 1.2e-16 to 1.5e-16, under the 9.095e-13 floor |

Unguarded (the `no-floor` mutant, every window, not a sample):

| ladder `step` | fired | min / median / max |
|---|---|---|
| 0.01 | 1,400 of 1,500 | 0.4534 / 0.7578 / 0.9594 |
| 0.001 | 1,400 of 1,500 | 0.3973 / 0.7029 / 1.0288 |
| −0.005 | 1,400 of 1,500 | 0.9950 / 1.1541 / 2.1356 |

These unguarded readings sit well inside the derived bounds and overlap the
real frames' own ranges (§C1), which is what the floor buys: without it this
column would read the rounding of an exactly geometric price path as if it
were real return structure.

---

## D. Gate D — scale-free

### D1. Bit-identical under a power-of-two price rescale

The price enters only as `c[t] / c[t-1]`, so a power-of-two rescale (×8, ×64,
2⁻⁴⁰, 2⁴⁰) multiplies and divides out exactly in floating point.

| frame | factors checked | result |
|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 8, 64, 2⁻⁴⁰, 2⁴⁰ (24 cells) | **bit-equal**, all 24 |

### D2. Inexact RETURN rescale — also bit-identical, not by construction

×10, ×3.7, ×0.1 and ×1.0000001 applied directly to the walk frame's RETURNS
stream (not a power-of-two, so not exact in binary):

| factor | value bars moved (tol 1e-9) | mask differs | max \|gap\| |
|---|---|---|---|
| 10.0 | **0** | 0 | 0.00e+00 |
| 3.7 | **0** | 0 | 0.00e+00 |
| 0.1 | **0** | 0 | 0.00e+00 |
| 1.0000001 | **0** | 0 | 0.00e+00 |

This is a measured fact, not a guarantee the arithmetic makes by itself: the
value is a function of which side of a quantile cut point each point falls,
and no point here sits close enough to a cut point for these rescales to
flip one.

### D3. `0 < fires < n`

1,400 fired of 1,500 bars on the walk frame — `0 < 1400 < 1500`.

---

## E. Gate E

**Measured 2026-11-21 (this receipt session), on the Hazen column.** Run
`gate_e_overlap.py run --module pandas_ta.statistics.c22_entropy_pairs`, run
id `is133-c22_entropy_pairs-43140f40`, 89 ALTPORT-1 frames, 398,849 pooled
bars, 687 comparators (329 `compute_all` + 358 `ml_features` manifest),
canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`).
`C22ENTROPYPAIRS_100`: max |ρ| **0.12465894564119429** vs `ROLLING_LOW_250`
(n = 376,599), per-frame max median **0.12777015187024565** vs
`ROLLING_HIGH_250` (89 frames, 0% of frames ≥ 0.90) — **SHIP**, well under
the `r3-perframe-0.90` line (< 0.76). Recorded in `docs/gate_e_ledger.csv`.

**Superseded run, kept for context only.** The type-7 column was measured
with `gate_e_overlap.py run --module pandas_ta.statistics.c22_entropy_pairs`,
89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all`
+ 358 `ml_features` manifest), canary bit-equal (`AKBNK.IS, BIENY.IS,
AGHOL.IS, SASA.IS`) — max |ρ| 0.1371 vs `ROLLING_LOW_250` (n = 376,599),
per-frame max median 0.1290 vs `ROLLING_HIGH_250`, well under the
`r3-perframe-0.90` SHIP line (< 0.76), run id `is133-c22_entropy_pairs-d0ad14ca`.
That number measured the REJECTED type-7 column, not the Hazen column this
tree now ships, so it is not carried forward as this port's Gate E result.

§P below is this port's own black-box correctness check against the GPL-3.0
reference (pycatch22 1.0.2) — a Gate A corroboration, not Gate E, and
unaffected by which gate-E-ledger row exists.

---

## F. Gate F — suites

**This module:** `python -m pytest tests/test_c22_entropy_pairs.py -q` →
**116 passed** (review round 1 added 18: the length guard band and column
naming, a short-input probe, wiring/accessor checks, offset/fillna, the
chunk budget, and a stricter dictionary-row check; review round 2 added 6: a
second exact-rational-oracle run at a non-integral quantile index, §A1). The
test count is unchanged by review round 3's quantile-convention fix: the
same oracles now exercise Hazen instead of type 7.

**Required subset (review round 3, 2026-11-21, after the §P1 quantile fix
below):**
`python -m pytest -q tests/test_c22_entropy_pairs.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ **re-run 2026-11-21 (this receipt session), after the Gate E ledger row
landed: 1422 passed, 7 skipped** (the prior run's one failure,
`test_every_indicator_that_needs_a_row_has_one`, is now green).

**Under the CI CPU dispatch:** `python docs/measure_c22_entropy_pairs_cpu.py`
→ see its own run below (§F1).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Under `NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512_SKX AVX2 FMA3'`

`python docs/measure_c22_entropy_pairs_cpu.py` sets the variable before numpy
is imported and refuses to run unless all four features are actually off.

Run result: **116 passed**, `tests/test_c22_entropy_pairs.py -q`. No count in
the test module is pinned to an exact value that this dispatch could move —
every distinct-value and tie-share claim in §B4/§C1 is asserted as a `>=`
bound (`>= 20` distinct values, `> 0.05` range) rather than an exact count,
and every value comparison uses a tolerance (1e-9 to 1e-12) rather than `==`,
because the column is an integer bincount feeding `log`, and the integers are
robust to CPU dispatch while the final sum of up to 9 logarithms is not.

---

## G. The floor, and what it buys

`NOISE_FLOOR = NOISE_ULPS * eps = 9.094947e-13`, the same convention this
fork's other catch22-on-returns ports use. It bounds the window's RETURN
standard deviation, which is also what the (inert) z-score divides by.

| frame | min window sd (synthetic) |
|---|---|
| geometric ladder (`step` 0.01 / 0.001 / −0.005) | 1.2e-16 to 1.5e-16 |

Roughly 10 orders of magnitude separate a real-shaped frame's window sd from
the floor and 3 separate the floor from the exactly-geometric ladder it
blanks (§C3).

---

## H. Bad data and wiring

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR whose
ratio overflows to an infinite return; on a window whose SUM OF SQUARES
overflows although the returns themselves are finite; and under the §C3/§G
blanking rule. `MIN_LENGTH = NUM_LETTERS ** WORD_LENGTH + 1 = 10`.

Five wiring touch points: `pandas_ta/statistics/c22_entropy_pairs.py` (the
module), `pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py`
→ `Category["statistics"]` (discovery / `df.ta.strategy`), `pandas_ta/core.py`
→ `DataFrame.ta.c22_entropy_pairs()` (accessor), `tests/test_c22_entropy_pairs.py`
(tests). `tests/test_wiring_accessors.py` and `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL` 364 → 365) both pin the wiring.

---

## P. The GPL-3.0 reference — OPT-IN, measurement only

`pycatch22` IS installed in this environment (unlike the owner's stated
expectation for a clean checkout — this is an opt-in measurement, not a
dependency of any shipped code, and `test_the_reference_implementation_is_not_imported_by_shipped_code`
confirms no shipped module imports it). `docs/measure_c22_entropy_pairs.py P`
runs it, never any other command.

### P0. Spearman against this port, per frame

90 windows total (15 per frame, stride 97), `pycatch22.catch22_all(window)`'s
`entropy_pairs` output (its own short name for `SB_MotifThree_quantile_hh`)
against this port's `_entropy_pairs_rows` kernel on the identical window:

| frame | Spearman |
|---|---|
| walk | **0.9723** |
| tick-rounded | 0.8371 |
| penny | 0.9393 |
| ar1 | **0.9821** |
| cosine | 0.6387 |
| student-t | 0.8714 |

Five of six frames correlate above 0.83; the cosine frame (only 34 distinct
values over 1,400 bars, §B4) is the weakest, which is the usual low-distinct-
value caveat rather than a sign of a wrong formula. **0 of 90 windows agree
to 1e-9** — this port does not reproduce the reference bit for bit — but the
correlation is strong enough to confirm the same underlying signal.

### P1. Candidate quantile interpolation conventions, fit to the black box

Nine `numpy.quantile` interpolation methods, same 90 windows, holding the
structural reading (overlapping pairs, natural log) fixed. The cited source,
hctsa's `SB_MotifThree(y, 'quantile', 3)`, is MATLAB, and MATLAB's own
`quantile` assigns sorted values to the midpoint probabilities
`p_k = (k - 0.5) / n` and interpolates linearly — the Hazen rule, "type 5" —
which is public from MathWorks' own documentation (no GPL-3.0 source needed)
and has shipped as `numpy.quantile(method="hazen")` since numpy 1.22 (this
environment runs 1.26.4). `weibull` is in the sweep too, for completeness:

| method | agree < 1e-9 | mean gap | median gap | max gap |
|---|---|---|---|---|
| linear (**rejected**, "type 7", `p_k=(k-1)/(n-1)`, `numpy.quantile`'s own default) | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| lower | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| higher | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| nearest | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| midpoint | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| median_unbiased | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |
| normal_unbiased | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |
| **hazen** (**shipped**, MATLAB/hctsa's own convention, "type 5") | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |
| weibull | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |

**These nine rows are two distinct behaviours, not nine.** At the default
`length` = 100 the rejected `linear` reading's virtual index
`(length - 1) * p` is exactly 33.0 and 66.0 for `p` = 1/3, 2/3 (99 is
divisible by 3), so `linear`, `lower`, `higher`, `nearest` and `midpoint` all
land on the same two order statistics `x[33]`, `x[66]` — they are ONE
convention measured five times, which is why those five rows are
byte-identical. `median_unbiased`, `normal_unbiased`, `hazen` and `weibull`
use plotting positions whose virtual index at `length` = 100 is NOT an
integer, so they interpolate and (here) land in the same bracket, producing
a second byte-identical group — the shipped Hazen reading is one member of
this second group. The sweep is two distinct cut-point behaviours, not nine,
and no inference should be drawn from the agreement among rows within either
group.

Across those two behaviours the MEDIAN gap does not move (0.0202 both), only
the MAX does (0.0437 → 0.0202, Hazen's worst case is half the rejected
`linear` reading's). **Gate A says start from the source formula, and the
source formula is MATLAB's, so this port SHIPS Hazen**, not `linear` —
`linear` was the more common convention and the one a reader reproducing
"the 1/3 and 2/3 empirical quantile" from the paper's own words alone would
reach for first, but it is not the source's, and this very table gives no
measured reason to keep it anyway: its median gap merely TIES Hazen's and its
max gap is WORSE. Neither convention reproduces the GPL-3.0 reference bit for
bit (0 of 90 agree to 1e-9 either way), and §P3 below explains why a
black-box fit cannot settle this choice at all: on designed, rank-only
inputs every one of these nine conventions reproduces the reference
identically, because Shannon entropy over the 9 word-type counts is
invariant to the single-index relabelling a quantile-convention swap
produces there. The quantile convention is decided by fidelity to the
source, not by which one fits noisy data better — because on this feature,
fit cannot discriminate between them.

### P2. Candidate structural readings, fit to the black box

Same 90 windows, holding the quantile convention fixed at the shipped Hazen
reading:

| candidate reading | median gap | max gap |
|---|---|---|
| **shipped** (overlapping pairs, natural log, raw) | **0.0202** | **0.0202** |
| non-overlapping pairs (`floor(length/2)` words) | 0.0472 | 0.2587 |
| `log2` instead of natural log | 0.9397 | 0.9521 |
| normalized by `log(#observed word types)` | 1.2017 | 1.2169 |
| word-count divisor `length` (100) instead of `length - 1` (99) | 0.0319 | 0.0322 |
| word-count divisor `length - 2` (98) instead of `length - 1` (99) | 0.0082 | 0.0135 |

The shipped reading beats four of the five alternatives tried, by a wide
margin over `log2`, the type-count normalization and the wrong-divisor-by-
100 candidate — evidence that the structural reading (words are OVERLAPPING
consecutive letter pairs, entropy in NATS) was read correctly from the
definition. **It does not beat all five on this noisy fit.** Dividing the
word COUNTS by `length - 2` = 98 instead of the correct `length - 1` = 99 —
which does not sum the word-type frequencies to 1, so it is not a valid
probability distribution and is not a candidate this port can adopt — still
fits the black box better than the shipped reading on both the median
(0.0082 vs 0.0202) and the max (0.0135 vs 0.0202). §P3 below settles this
near-miss with designed inputs instead of a noisy fit: the shipped reading
reproduces the reference EXACTLY on all three designed windows, and the
98-divisor candidate does not reproduce it on any of them — so the near-miss
on real data is a fitting artifact, not a hint at the true structure, and is
ruled out rather than merely disclosed. What §P3 does NOT settle is the
~0.02 median gap on real (non-designed) windows itself: that residual's
cause remains unidentified. **This is a Gate A corroboration of the
structural reading, not Gate E, and not a claim that this port reproduces
the reference**: the residual gap and the sub-1.0 Spearman on two of six
frames are both stated, not hidden.

### P3. Designed, rank-only inputs — exact identification instead of a noisy fit

§P1 and §P2 above FIT every candidate to 90 real, noisy windows, where many
readings differ by amounts of the same order as the residual itself — which
is why the 98-divisor candidate "wins" a fit without being a coherent
reading. Three designed windows remove the noise: each is a sequence whose
RANK order is fixed by construction, so the letter sequence under any
quantile convention is forced and the word-type counts are deterministic.
`pycatch22.catch22_all` is run directly on each (`LENGTH` = 100 values fed as
the "returns" window, matching how real windows are probed above):

| window | pycatch22 | all 9 quantile methods | shipped structural | other 5 structural candidates |
|---|---|---|---|---|
| monotone (0, 1, .., 99; no ties) | 1.189142 | **EXACT**, all 9 | **EXACT** (gap 0.00e+00) | all 5 miss (gap 1.88e-03 to 5.26e-01) |
| one-step-plateau (ranks 32/33 tied, else monotone) | 1.189142 | **EXACT**, all 9 | **EXACT** (gap 0.00e+00) | all 5 miss (gap 1.88e-03 to 5.26e-01) |
| two-level (50 × 0.0, 50 × 1.0) | 0.742611 | **EXACT**, all 9 | **EXACT** (gap 0.00e+00) | all 5 miss (gap 2.52e-03 to 3.29e-01) |

Two findings, not one:

1. **The structural reading is pinned exactly.** The shipped reading
   (overlapping pairs, natural log, divisor `length - 1` = 99) reproduces
   `pycatch22` bit-for-bit on all three designed windows — the strongest Gate
   A corroboration in this receipt, because there is no fitting involved: the
   predicted and reference values are either equal or they are not. Every
   structural alternative tried, INCLUDING the 98-divisor near-miss that beat
   the shipped reading on the noisy §P2 fit, disagrees with the reference on
   every designed window. The near-miss is therefore a fitting artifact of
   real data, not evidence for a 98 divisor.
2. **The quantile convention cannot be identified this way.** All nine
   `numpy.quantile` methods — including the rejected `linear`/type-7 reading
   and the shipped Hazen reading — reproduce `pycatch22` EXACTLY on all three
   windows, i.e. they agree with each other too. This is not a coincidence of
   these three windows: Shannon entropy over the 9 word-type counts is a
   function of the MULTISET of counts, invariant to which category holds
   which count. On rank-only data, moving the quantile convention shifts at
   most one letter's boundary by one index, which PERMUTES two counts between
   categories without changing the multiset — so the entropy is identical
   under every convention whenever no other structure breaks that symmetry.
   This is also why §P1's noisy fit found the quantile convention barely
   moves the gap: the effect of the convention on this feature's value is
   usually a no-op by this same argument, so no designed OR real input can
   use the black box to choose between Hazen and type 7. The choice is
   correctly made by fidelity to the source (§P1), not by fit.

---

## Summary

| Gate | Result |
|---|---|
| A | Ships the Hazen quantile convention (MATLAB/hctsa's own `quantile`, §P1), not `numpy.quantile`'s default. Exact rational oracle agrees on 15/15 sampled windows per frame (6 frames) at `length` 100 AND at a second fractional offset, `length` 120; independent plain-Python spelling agrees to 8.9e-16; z-score and word-order invariances measured and hold; the structural reading (overlapping pairs, nats, divisor `length - 1`) reproduces the GPL-3.0 reference EXACTLY on three designed, rank-only inputs (§P3), which also rules out the real-data 98-divisor near-miss as a fitting artifact and explains why the quantile convention itself cannot be chosen by any black-box fit (entropy's permutation invariance over the word-type counts); the ~0.02 median gap on real (non-designed) windows remains unidentified |
| B | 0 of 35 future-perturbation offsets leak on 6 frames + 3 non-default lengths; every look-ahead mutant that can move a clean frame is caught at ≥10 of 35, the one that cannot (`mask-back-dated`) is caught 12 of 12 on a dirty frame; two cross-row mutants dead by measured affine invariance |
| C | Fires on every full-window bar on all 6 synthetic frames, including the tick-rounded penny frame (21.68% zero returns); blanks correctly on a flat run and an exact geometric ladder |
| D | Bit-identical under ×8/×64/2⁻⁴⁰/2⁴⁰ price rescale (24/24 cells); 0 bars moved under ×10/×3.7/×0.1/×1.0000001 return rescale; `0 < fires < n` |
| E | **SHIP** — Hazen column, max \|ρ\| 0.12465894564119429 vs `ROLLING_LOW_250` (n = 376,599), per-frame max median 0.12777015187024565 vs `ROLLING_HIGH_250` (89 frames, 0% ≥ 0.90); well under the `r3-perframe-0.90` SHIP line (< 0.76); recorded in `docs/gate_e_ledger.csv` |
| F | This module's 116 tests pass, under both the local dispatch and the CI CPU-feature set; required cross-module subset passes clean (1422 passed, 7 skipped) with the Gate E ledger row in place |

**Decision: SHIP.** Gates A–D pass on the Hazen quantile convention (the
source-faithful one, per §P1), corroborated exactly against the GPL-3.0
reference on designed inputs in §P3; Gate E measures well clear of the
SHIP line. The column ships as `C22ENTROPYPAIRS_100`.
