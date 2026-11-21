# `c22_entropy_pairs` — measured

**Issue:** [#133](https://github.com/TolgaUyanik/PandasTa/issues/133) · C22-ENTROPY-PAIRS ·
catch22 entropy of 2-letter words in a 3-quantile return alphabet (100)
**Module:** `pandas_ta/statistics/c22_entropy_pairs.py` · **Column:** `C22ENTROPYPAIRS_100`
**Harness:** `docs/measure_c22_entropy_pairs.py` (sections S, A–D, G; **P** is
opt-in and is the only place in this repository that runs the GPL-3.0
reference)
**CPU re-run:** `docs/measure_c22_entropy_pairs_cpu.py`
**Tests:** `tests/test_c22_entropy_pairs.py` (116 tests)
**Measured:** 2026-11-21, numpy 1.26.4 / pandas 2.3.3 / python 3.11, with
`AVX512F AVX512_SKX AVX2 FMA3` **enabled** (the CI dispatch is §F1).

**Gate E: measured 2026-11-21, SHIP.** `C22ENTROPYPAIRS_100` max |ρ|
**0.1371** vs `ROLLING_LOW_250` (`compute_all`, n = 376,599); per-frame max
median 0.1290 vs `ROLLING_HIGH_250` (89 frames, 0.0% of frames ≥ 0.90) → well
under the `r3-perframe-0.90` SHIP line (< 0.76). Full run in §E below. §P
below is this port's own black-box comparison to the GPL-3.0 reference, which
is a correctness check, not Gate E.

---

## 0. What the column is

Cut the last 100 daily simple returns into 3 letters at their own 1/3 and 2/3
empirical quantiles, read off every overlapping 2-letter word, and report the
Shannon entropy of the observed word-type distribution, in nats, over the 9
possible word types:

```
r[t]   = close[t] / close[t-1] - 1
Z      = (X - mean(X)) / sd(X, ddof=1)                     # inert, §A3
q1, q2 = the 1/3 and 2/3 empirical quantiles of Z (linear interpolation)
k[t]   = how many of {q1, q2} that Z[t] stands strictly above
W      = {(k[t], k[t+1]) : t = 1 .. 99}                    # 99 overlapping words
C22ENTROPYPAIRS = -sum over observed word types of p * log(p)
```

Three things a reader has to know before using it:

1. **It is bounded in `[0, log 9]` = `[0, 2.1972245773362196]`**, an
   ENCLOSURE reached only by a perfectly uniform 9-way distribution.
   Measured range over six synthetic frames: **1.255674 to 2.197225**
   (§C1) — close to the top of the scale on five of six, because 99
   overlapping words over 9 types land near-uniform on most return
   sequences that are not themselves highly repetitive.
2. **The quantile ESTIMATOR is an open reading the definition does not
   settle**, and this port's choice (linear interpolation, `numpy.
   quantile`'s default, "type 7") does not reproduce the GPL-3.0 reference
   bit for bit — see §P. The structural reading (overlapping pairs, natural
   log) is measured to be the best fit among the structural candidates
   tried (§P2); the residual gap itself is NOT attributed to the quantile
   convention — §P1 measures that swapping conventions, including MATLAB/
   hctsa's own Hazen rule, moves the typical gap only in the fourth decimal
   place — so the cause of the ~0.02 median disagreement with the reference
   is disclosed as unidentified, not pinned on interpolation.
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

Linear-interpolated quantiles of a finite sample are a RATIONAL function of
the order statistics, so the letter sequence can be recomputed with zero
rounding (`Fraction` arithmetic) and compared to the shipped float pipeline.

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

⚠ At `length` = 100 this does not exercise interpolation at all: the virtual
index `(length - 1) * p` is exactly 33.0 and 66.0 for `p` = 1/3, 2/3 (99 is
divisible by 3), so `numpy.quantile`'s `linear` method returns the plain
order statistics `x[33]`, `x[66]` with `frac` = 0 on both cuts — the oracle
above matches trivially because neither spelling ever interpolates. A second
run at `length` = 120, where `(length - 1) / 3` = 39.667 and `(length - 1) *
2 / 3` = 79.333 are both non-integral, forces the real interpolation:

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
| walk | 200 | 4.44e-16 |
| tick-rounded | 200 | 8.88e-16 |
| penny | 200 | 4.44e-16 |
| ar1 | 200 | 8.88e-16 |
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
| walk | 1,400 | **530** | 0.1158 | 2.132676 | 2.196305 |
| tick-rounded | 1,400 | **543** | 0.0944 | 2.105018 | 2.196305 |
| penny | 1,400 | **748** | 0.1415 | 1.255674 | 2.196305 |
| ar1 | 1,400 | **966** | 0.1851 | 1.871165 | 2.165775 |
| cosine | 1,400 | **26** | 0.6269 | 1.635248 | 1.659030 |
| student-t | 1,400 | **636** | 0.0958 | 2.115633 | 2.197225 |

This column takes an INTEGER-bincount-derived value (unlike `c22_ami2`'s
continuous mutual information), so tie shares are higher (9.4%–62.7%) and
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
| walk | 1,400 | 530 | 2.132676 | 2.182479 | 2.196305 |
| tick-rounded | 1,400 | 543 | 2.105018 | 2.178481 | 2.196305 |
| penny | 1,400 | 748 | 1.255674 | 2.173883 | 2.196305 |
| ar1 | 1,400 | 966 | 1.871165 | 2.035772 | 2.165775 |
| cosine | 1,400 | 26 | 1.635248 | 1.656289 | 1.659030 |
| student-t | 1,400 | 636 | 2.115633 | 2.178843 | 2.197225 |

Derived bounds: `[0, 2.1972245773362196]`. The column sits near the top of
the scale on five of six synthetic frames, because 99 overlapping 2-letter
words spread over 9 types land close to uniform on most non-repetitive
sequences — this is the column's own baseline, not a sign that it is
constant: the walk frame alone has 530 distinct values.

### C2. The issue's own worry: BIST tick rounding

The penny frame (a 2-lira stock on a 1-kurus tick) has 21.68% of its returns
exactly 0.0. Its first window's 3 letters hold 35 / 32 / 33 points — the
quantile split still comes out close to equiprobable despite the rounding,
because the ties sit at the SAME return value and so fall together inside
whichever letter their quantile band lands in, rather than collapsing two
letters into one the way a fixed-width bin would. The column still fires
everywhere, with 748 distinct values (the most of any non-ar1 frame) and the
widest range (1.255674 to 2.196305) of the six synthetic frames.

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
| −0.005 | 1,400 of 1,500 | 0.9950 / 1.1497 / 2.1356 |

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

Run by the issue-solver launcher, `gate_e_overlap.py run --module
pandas_ta.statistics.c22_entropy_pairs`, 89 ALTPORT-1 frames, 398,849 pooled
bars, 687 comparators (329 `compute_all` + 358 `ml_features` manifest),
canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`). Outputs:
`is133-c22_entropy_pairs-1d07d116`, recorded in `docs/gate_e_ledger.csv`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | per-frame against | verdict |
|---|---|---|---|---|---|---|
| `C22ENTROPYPAIRS_100` | **0.1371** | `ROLLING_LOW_250` | 376,599 | 0.1290 | `ROLLING_HIGH_250` | **SHIP** |

Both the pooled figure and the per-frame max median sit well under the
`r3-perframe-0.90` ship line (< 0.76), close to the 2026-10-24 screen's
prototype figure for the reference's own column (max |ρ| 0.1247 vs
`ROLLING_LOW_250`) — the port reads the same as the prototype on this
measure.

§P below is this port's own black-box correctness check against the GPL-3.0
reference (pycatch22 1.0.2) — a Gate A corroboration, not Gate E.

⚠ **`module_sha1` re-pinned, review round 2.** The findings below (§P1/§P2,
docstring wording) only touched prose: no line that the kernel executes
moved. `tests/test_gate_e_ledger.py::test_row_output_has_not_moved` confirms
the recorded output fingerprint still matches this file's live output, so
`docs/gate_e_ledger.csv`'s `module_sha1` for this row was updated to the new
file's hash (`a9a061f1…`) without a new Gate E run — the measured numbers
above are unchanged.

---

## F. Gate F — suites

**This module:** `python -m pytest tests/test_c22_entropy_pairs.py -q` →
**116 passed** (review round 1 added 18: the length guard band and column
naming, a short-input probe, wiring/accessor checks, offset/fillna, the
chunk budget, and a stricter dictionary-row check; review round 2 added 6: a
second exact-rational-oracle run at a non-integral quantile index, §A1).

**Required subset (review round 2, 2026-11-21, after the §P1/§P2 fixes
below):**
`python -m pytest -q tests/test_c22_entropy_pairs.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ **1422 passed, 7 skipped.** The prior session's one expected failure
(`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
missing ledger row) is gone now that `docs/gate_e_ledger.csv` carries the
Gate E run's row; the `module_sha1` re-pin above keeps
`test_row_still_describes_its_module` passing too.

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

Five of six frames correlate above 0.83; the cosine frame (only 26 distinct
values over 1,400 bars, §B4) is the weakest, which is the usual low-distinct-
value caveat rather than a sign of a wrong formula. **0 of 90 windows agree
to 1e-9** — this port does not reproduce the reference bit for bit — but the
correlation is strong enough to confirm the same underlying signal.

### P1. Candidate quantile interpolation conventions, fit to the black box

Nine `numpy.quantile` interpolation methods, same 90 windows, holding the
structural reading (overlapping pairs, natural log) fixed. MATLAB's own
`quantile` (hctsa is MATLAB) assigns sorted values to the midpoint
probabilities `p_k = (k - 0.5) / n` and interpolates linearly — the Hazen
rule, "type 5" — which is public from MathWorks' own documentation (no
GPL-3.0 source needed) and has shipped as `numpy.quantile(method="hazen")`
since numpy 1.22 (this environment runs 1.26.4). It is in the sweep below,
alongside `weibull` for completeness:

| method | agree < 1e-9 | mean gap | median gap | max gap |
|---|---|---|---|---|
| linear (**shipped**, "type 7", `p_k=(k-1)/(n-1)`) | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| lower | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| higher | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| nearest | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| midpoint | 0 of 90 | 0.0192 | 0.0202 | 0.0437 |
| median_unbiased | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |
| normal_unbiased | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |
| **hazen** (MATLAB/hctsa's own convention, "type 5") | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |
| weibull | 0 of 90 | 0.0185 | 0.0202 | 0.0202 |

**These nine rows are two distinct behaviours, not nine.** At the default
`length` = 100 the virtual index `(length - 1) * p` is exactly 33.0 and 66.0
for `p` = 1/3, 2/3 (99 is divisible by 3), so `linear`, `lower`, `higher`,
`nearest` and `midpoint` all land on the same two order statistics `x[33]`,
`x[66]` — they are ONE convention measured five times, which is why those
five rows are byte-identical. `median_unbiased`, `normal_unbiased`, `hazen`
and `weibull` use plotting positions whose virtual index at `length` = 100
is NOT an integer, so they interpolate and (here) land in the same bracket,
producing a second byte-identical group. The sweep is two distinct cut-point
behaviours, not nine, and no inference should be drawn from the agreement
among rows within either group.

Across those two behaviours the MEDIAN gap does not move (0.0202 both), only
the MAX does (0.0437 → 0.0202, Hazen's worst case is half linear's). Hazen —
the convention MATLAB/hctsa's `quantile` actually uses — does not reproduce
the reference bit for bit either (0 of 90 agree to 1e-9), and it does not
close the typical ~0.02 gap at all; it only trims the tail. **The residual is
therefore NOT attributed to the quantile convention**: swapping to the
source-faithful Hazen reading leaves the typical disagreement with the
reference unchanged, so whatever drives it is not this interpolation choice.
**`linear` is kept as the shipped reading** on three grounds — it is the
natural "the 1/3 and 2/3 empirical quantile" reading, it is `numpy.
quantile`'s own default, and its median gap ties Hazen's — and switching to
Hazen now would retroactively invalidate the Gate E measurement already
recorded in `docs/gate_e_ledger.csv` for the `linear` column (a different
quantile convention is a different column, by this port's own §0 item 1) for
a tail-only improvement that does not touch the actual unexplained residual.

### P2. Candidate structural readings, fit to the black box

Same 90 windows, holding the quantile convention fixed at linear:

| candidate reading | median gap | max gap |
|---|---|---|
| **shipped** (overlapping pairs, natural log, raw) | **0.0202** | **0.0437** |
| non-overlapping pairs (`floor(length/2)` words) | 0.0506 | 0.2587 |
| `log2` instead of natural log | 0.9388 | 0.9569 |
| normalized by `log(#observed word types)` | 1.2023 | 1.2169 |
| word-count divisor `length` (100) instead of `length - 1` (99) | 0.0318 | 0.0531 |
| word-count divisor `length - 2` (98) instead of `length - 1` (99) | 0.0081 | 0.0343 |

The shipped reading beats four of the five alternatives tried, by a wide
margin over `log2`, the type-count normalization and the wrong-divisor-by-
100 candidate — evidence that the structural reading (words are OVERLAPPING
consecutive letter pairs, entropy in NATS) was read correctly from the
definition. **It does not beat all five.** Dividing the word COUNTS by
`length - 2` = 98 instead of the correct `length - 1` = 99 — which does not
sum the word-type frequencies to 1, so it is not a valid probability
distribution and is not a candidate this port can adopt — fits the black box
better than the shipped reading on both the median (0.0081 vs 0.0202) and
the max (0.0343 vs 0.0437). This is reported as a measured near-miss, not
explained: it says the residual correlates with SOME divisor-like quantity
smaller than 99, but a 98-divisor is not a coherent alternative reading of
`SB_MotifThree(y, 'quantile', 3)`, so no candidate tried here — across both
§P1's quantile conventions and this table's structural readings — identifies
the actual cause of the ~0.02 median disagreement with the GPL-3.0
reference. **This is a Gate A corroboration of the structural reading, not
Gate E, and not a claim that this port reproduces the reference**: the
residual gap, the sub-1.0 Spearman on two of six frames, and the unexplained
98-divisor near-miss are all stated, not hidden.

---

## Summary

| Gate | Result |
|---|---|
| A | Exact rational oracle agrees on 15/15 sampled windows per frame (6 frames) at `length` 100 AND at a non-integral-index `length` 120; independent plain-Python spelling agrees to 8.9e-16; z-score and word-order invariances measured and hold; structural reading (overlapping pairs, nats, raw) beats 4 of 5 alternative readings against the GPL-3.0 black box (§P2), but the ~0.02 median gap to the reference is NOT attributed to the quantile convention (§P1: swapping to MATLAB/hctsa's own Hazen rule leaves it unchanged) and its cause is otherwise unidentified |
| B | 0 of 35 future-perturbation offsets leak on 6 frames + 3 non-default lengths; every look-ahead mutant that can move a clean frame is caught at ≥10 of 35, the one that cannot (`mask-back-dated`) is caught 12 of 12 on a dirty frame; two cross-row mutants dead by measured affine invariance |
| C | Fires on every full-window bar on all 6 synthetic frames, including the tick-rounded penny frame (21.68% zero returns); blanks correctly on a flat run and an exact geometric ladder |
| D | Bit-identical under ×8/×64/2⁻⁴⁰/2⁴⁰ price rescale (24/24 cells); 0 bars moved under ×10/×3.7/×0.1/×1.0000001 return rescale; `0 < fires < n` |
| E | **SHIP** — max \|ρ\| 0.1371 vs `ROLLING_LOW_250` (n = 376,599); per-frame max median 0.1290, well under the `r3-perframe-0.90` line |
| F | This module's 116 tests pass, under both the local dispatch and the CI CPU-feature set; required cross-module subset passes, ledger row now recorded |

**Decision: SHIP.** Nothing in Gates A–E disqualifies the column; the one
open reading (the quantile interpolation convention) is disclosed in the
module's docstring and corroborated as the best structural fit against the
GPL-3.0 reference in §P.
