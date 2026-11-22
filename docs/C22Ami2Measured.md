# `c22_ami2` — measured

**Issue:** [#127](https://github.com/TolgaUyanik/PandasTa/issues/127) · C22-AMI2 ·
catch22 automutual information of returns at lag 2 (5 bins) (100)
**Module:** `pandas_ta/statistics/c22_ami2.py` · **Column:** `C22AMI2_100`
**Harness:** `docs/measure_c22_ami2.py` (sections S, A–E, G, H, T, Z — §F below
is the suite run, not a harness section; **P** is opt-in and is the only place
in this repository that runs the GPL-3.0 reference)
**CPU re-run:** `docs/measure_c22_ami2_cpu.py`
**Tests:** `tests/test_c22_ami2.py`
**Measured:** 2026-11-20, numpy 1.26.4 / pandas 2.3.3 / python 3.11.2, with
`AVX512F AVX512_SKX AVX2 FMA3` **enabled** (the CI dispatch is §F1).

**Gate E: measured 2026-11-20 by issue-solver** on this tree (run
`is127-c22_ami2-23b6686b`): `C22AMI2_100` pooled max \|ρ\| **0.05943562162216838**
vs `Dist_from_High_252_pct` (n = 389,949), per-frame max median
**0.07418786831507361** vs `natr` over 89 frames → **SHIP** under
`r3-perframe-0.90`. §E has the full table and the ledger row; §E0 keeps the
2026-10-24 screen's **prototype** figure, which is the reference
implementation's column, and §P1 is the measurement of whether this port is
that same column.

---

## 0. What the column is

Cut the last 100 daily simple returns into 5 **even** bins spanning their own
range, count the 98 lagged pairs `(bin[t], bin[t+2])` into a 5×5 table, and
report the **Miller–Madow bias-corrected** mutual information of that table in
nats:

```
r[t]   = close[t] / close[t-1] - 1
Z      = (X - mean(X)) / sd(X, ddof=1)          # inert, §A6
b[i]   = min(Z) + i * (max(Z) - min(Z)) / 5,      i = 1 .. 4
         b[0] = min(Z) - 0.1, b[5] = max(Z) + 0.1 # neither can bind, §A7
k[t]   = how many of b[1..4] that Z[t] stands at or above
N[a,c] = #{t : k[t] = a and k[t+2] = c}           # 98 pairs
p = N / 98,  pi = rowsums(p),  pj = colsums(p)
MI     = sum over N[a,c] > 0 of p log(p / (pi pj))
C22AMI2 = MI - (occupied cells - occupied rows - occupied cols + 1) / (2 * 98)
```

Three things a reader has to know before using it:

1. **It can be NEGATIVE.** A mutual information cannot be; a bias-corrected
   *estimate* of one that is near zero lands on both sides of zero. Derived
   bounds at `length` 100: `[-0.0816, 1.6298]`. Measured over five stochastic
   frames: **−0.0329 to 0.2066**.
2. **"No lag-2 dependence" is ≈ +0.028, either sign, AT `length` 100** — not
   0, and not the same number at another length. On 400 independent normal
   windows drawn through the shipped kernel the column's median is **+0.0284**
   and **17.3%** of them are negative (§A10b). §A10 draws its own separate 400
   windows and gets +0.0282 and 15.5%; that is the sample the plug-in
   comparison is made on, where the *uncorrected* plug-in MI reads **+0.0856**
   — its own first-order bias `(5−1)²/(2·98) = 0.0816`. The correction scales
   as `1/(2(length−2))`, so the same measurement gives **+0.228 at `length`
   27** and **+0.008 at 250** (§A10b).
3. **It reads the SHAPE of the window relative to its own range**, and nothing
   about size: any positive affine map of the window leaves every value alone
   (§A6, §D3), while the same returns in a different order move 467 of 467
   windows.

## 1. Attribution, and what it is NOT evidence of

catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data Mining and
Knowledge Discovery* 33:1821), feature `ami2` /
`CO_HistogramAMI_even_5bin_ami2` of catch22 1.0 — the hctsa operation
`CO_HistogramAMI(y, 2, 'even', 5)`. The bias correction is Miller and Madow's
(1955), applied to each of the three entropies in
`MI = H(i) + H(j) − H(i, j)`.

⚠ **Which catch22 this is.** catch22 1.0 renamed **and redefined** this
feature from `CO_HistogramAMI_even_2_5` "to match hctsa" — that is the
reference's own deprecation notice, quoted verbatim in §P. Every figure in
this document is measured against **pycatch22 1.0.2**, i.e. the post-change
definition, which is also the one the 2026-10-24 screen read
(`docs/issues/screen/ind_screen_r3.py` names the new spelling). The pre-1.0
definition was never run here and nothing in this port claims to be it; the
deprecated alias `CO_HistogramAMI_even_2_5` is what §P0 calls through, and on
the one window §P0 scores it returns the same double as `catch22_all`'s
`ami2`.

The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this fork is
MIT. This module was written from the definitions and from a named estimator;
no shipped module imports the reference (`tests/test_c22_ami2.py::test_the_reference_implementation_is_not_imported_by_shipped_code`
sweeps every `.py` file under `pandas_ta/` — **398** on this tree, this module
included, **0** of them importing it, printed by §H so the digit cannot drift);
and the one place it is run at all is §P — opt-in, measurement only, the same
use the owner's own screen prototype makes of it.

⚠ **hctsa's own source is not in this tree and was not read.** What §P knows
about it is what the reference's OUTPUT shows. Two structural readings of the
definition were identified by fitting candidate formulas to that output
(§P1c), which is how a measurement can settle a reading without copying code.

⚠ catch22 is a subset selected for **time-series classification** performance
on 93 reference problems. That is not return prediction, and nothing here
tests it on BIST: the presence of this column in the fork is **existence, not
evidence**.

---

## A. Gate A — correctness

### A1. The exact oracle — zero roundings where a rounding could matter

The bin edges are *affine* in the window's own minimum and maximum, so the
z-score's irrational `sd` cancels out of every membership test: `u/sd >=
min(u)/sd + i (max(u) − min(u))/(5 sd)` is `u >= min(u) + i (max(u) − min(u))/5`,
a comparison of two rationals. The whole 5×5 count matrix is therefore decided
exactly, and the only roundings left in the value are the 25 logarithms.

| frame | windows | count matrices equal | max \|value gap\| |
|---|---|---|---|
| walk | 15 | **15** | 8.3e-17 |
| tick-rounded | 15 | **15** | 1.1e-16 |
| penny | 15 | **15** | 1.7e-16 |
| ar1 | 15 | **15** | 1.1e-16 |
| cosine | 15 | **15** | 2.2e-16 |
| student-t | 15 | **15** | 1.4e-16 |

90 of 90 sampled windows, stride 97.

### A2. Four more spellings that share no code with the module

| frame | windows | plain Python (`fsum`) | `H(i)+H(j)−H(i,j)` | `np.histogram2d` | `sklearn.mutual_info_score` |
|---|---|---|---|---|---|
| walk | 200 | 5.6e-17 | 1.2e-15 | 5.6e-17 | 1.0e-15 |
| tick-rounded | 200 | 5.6e-17 | 1.3e-15 | 5.6e-17 | 1.0e-15 |
| penny | 200 | 5.6e-17 | 1.4e-15 | 5.6e-17 | 1.0e-15 |
| ar1 | 200 | 5.6e-17 | 1.6e-15 | 5.6e-17 | 1.0e-15 |
| cosine | 200 | 1.1e-16 | 7.8e-16 | 1.1e-16 | 8.9e-16 |
| student-t | 200 | 5.6e-17 | 9.0e-16 | 5.6e-17 | 1.2e-15 |

Max gap over all 1,200 windows per column. `sklearn`'s is the plug-in MI with
this module's own correction term subtracted, so it checks the information and
not the correction; the correction is checked by §A3's laws and by §A5b.

### A3. Two EXACT laws

A return series with `r[t+2] = f(r[t])` for an invertible `f` the binning
resolves makes the joint table a **bijection**: every occupied row has exactly
one occupied cell. Then the plug-in MI is the marginal entropy exactly, and
the Miller–Madow term over `k` occupied cells is `(1 − k)/(2·98)` — it **adds**
`(k−1)/196`.

| frame | fired | distinct (12 dp) | value | occupied cells | max \|value − (H + (k−1)/196)\| |
|---|---|---|---|---|---|
| alternating ±2% | 1,400 | **1** | 0.698249221376 | 2 | **0.0e+00** |
| cosine period 4 | 1,400 | **1** | 1.049820721962 | 3 | **0.0e+00** |
| cosine period 2 | 1,400 | **1** | 0.698249221376 | 2 | **0.0e+00** |

`ln 2 = 0.6931472` and `ln 2 + 1/196 = 0.6982492`. The alternating frame is
the one test that would catch a sign slip in the correction: the uncorrected
value there is exactly `ln 2` and the shipped one is above it.

### A3b. The cosine frames, by period

| period | fired | distinct (9 dp) | min | median | max |
|---|---|---|---|---|---|
| 4 | 1,400 | 1 | 1.049821 | 1.049821 | 1.049821 |
| 5 | 1,400 | 3 | 0.498805 | 0.499067 | 0.506271 |
| 6 | 1,400 | 2 | 0.870358 | 0.870358 | 0.877276 |
| 8 | 1,400 | 1 | 0.069775 | 0.069775 | 0.069775 |
| 10 | 1,400 | 3 | 0.412818 | 0.413170 | 0.417043 |
| 20 | 1,400 | 5 | 0.727466 | 0.729533 | 0.734307 |
| 40 | 1,400 | 10 | 0.773122 | 0.787731 | 0.797632 |
| 97 | 1,400 | 7 | 1.013492 | 1.031105 | 1.036321 |

There is **no monotone law in the period** — period 8 reads 0.0698, barely
above the no-dependence value, while period 6 reads 0.8704 — because what
decides the reading is whether the lag-2 map is one-to-one *on the bins*, not
how long the cycle is. At period 8 the lag-2 map sends two different bins into
the same bin and the information collapses. This is the column working, and it
is worth knowing before reading a high value as "a cycle".

### A4. The bin-assignment spelling

Counting the interior edges a point stands at or above (shipped) against
`floor((y − b1)/width) + 1`, clipped. Compared as INTEGER arrays, because that
is the question — the value also carries the summation's rounding.

| frame | windows | points binned differently | value bars differing in any bit | max \|value gap\| |
|---|---|---|---|---|
| walk | 200 | **0** | 108 | 5.6e-17 |
| tick-rounded | 200 | **0** | 134 | 5.6e-17 |
| penny | 200 | **0** | 126 | 5.6e-17 |
| ar1 | 200 | **0** | 121 | 5.6e-17 |
| cosine | 200 | **0** | 60 | 1.1e-16 |
| student-t | 200 | **0** | 114 | 5.6e-17 |

Not one point lands in a different bin; the last-bit differences are the two
spellings' own arithmetic (plain-Python `fsum` against the numpy reduction) and
are 5.6e-17.

### A5. **THE EDGE SPELLING — the one reading a porter can get wrong**

The definition's buffer ("ensure all points are included") can be read two
ways, and they are different columns:

* **SHIPPED:** evenly spaced edges from the window's min to its max, with only
  the two **OUTER** ones pushed out by 0.1. The buffer exists for INCLUSION and
  does not move an interior edge.
* **the other reading:** evenly spaced over `[min − 0.1, max + 0.1]`, which
  moves every interior edge by up to a tenth of a standard deviation. **This
  was this port's first reading**, and §P1c is what overturned it.

| frame | windows | value bars moved | max \|gap\| | Spearman |
|---|---|---|---|---|
| walk | 467 | **434** | 0.0697 | +0.8282 |
| tick-rounded | 467 | **463** | 0.0521 | +0.7319 |
| penny | 467 | **246** | 0.0684 | +0.8705 |
| ar1 | 467 | **462** | 0.0701 | +0.8778 |
| cosine | 467 | 0 | 0.0000 | +0.9863 |
| student-t | 467 | **434** | 0.0418 | +0.8644 |

The cosine frame moves **0** — its returns are a lattice both spellings
separate the same way — and is named rather than averaged in.

### A5b. **THE MILLER–MADOW CORRECTION, priced**

Dropping it leaves the raw plug-in MI. Measured through a mutant of the
module's own source, so this is the shipped code path and not a re-spelling.

| frame | windows | **moved** (at 1e-12) | max \|gap\| | mean correction | min | max | Spearman corrected vs plug-in | median of the column |
|---|---|---|---|---|---|---|---|---|
| walk | 467 | **467** | 0.0816 | +0.056887 | +0.030612 | +0.081633 | +0.9450 | 0.042746 |
| tick-rounded | 467 | **467** | 0.0816 | +0.055074 | +0.030612 | +0.081633 | +0.8782 | 0.027351 |
| penny | 467 | **467** | 0.0816 | +0.056559 | +0.030612 | +0.081633 | +0.9063 | 0.026924 |
| ar1 | 467 | **467** | 0.0765 | +0.055216 | +0.020408 | +0.076531 | +0.9603 | 0.088763 |
| cosine | 467 | **467** | 0.0153 | +0.015306 | +0.015306 | +0.015306 | +0.9863 | 0.729533 |
| student-t | 467 | **436** | 0.0765 | +0.030864 | **−0.000000** | +0.076531 | +0.7369 | 0.023269 |

The correction is `(5−1)²/(2·98) = 0.0816` at a full table and `−1/196` at a
two-cell bijection (§A3), so it both subtracts and adds.

⚠ **It does not move every window, and the exceptions are exact.** The
correction is an integer multiple of `1/(2·98) = 0.005102`, and it is exactly
**0** where the table's occupied cells, rows and columns satisfy
`cells = rows + cols − 1`. That is what the Student-t frame's 436 of 467 and
its `min` of −0.000000 are: 31 windows where the corrected and uncorrected
readings are the same double. §P1b sees the same thing from the other side —
the uncorrected plug-in matches the reference on 31 of 2,802 windows, which
are exactly the windows where there is nothing to correct.

**How big it is, compared with what.** 0.0816 nats at a full table is larger
than the **median reading** of four of the five stochastic frames and not of
the fifth — all five digits from the table above, the same 467 windows:
walk 0.0427, tick-rounded 0.0274, penny 0.0269, student-t 0.0233, and AR(1)
**0.0888**. Against the 20-bar cosine frame's 0.7295 it is 11% of the level.
Against the **span** rather than the level the comparison turns over: the
walk's measured range is 0.195 nats wide (§D4's `max − min`) and the mean
correction of 0.0569 is **29%** of that span. The level comparison is in the
table above, the span one in §D4; neither of them alone is "larger than the
signal", which is why that phrase is not used.

### A6. The z-score is INERT, and that is a property of the edges

The interior edges are an affine function of the window's own extremes, so any
positive affine map of the window leaves every bin assignment alone.

| frame | windows | ddof 0 moved | no z-score moved | shifted +1 moved | max \|gap\| |
|---|---|---|---|---|---|
| walk | 467 | **0** | **0** | **0** | 5.6e-17 |
| tick-rounded | 467 | **0** | **0** | **0** | 5.6e-17 |
| penny | 467 | **0** | **0** | **0** | 5.6e-17 |
| ar1 | 467 | **0** | **0** | **0** | 8.3e-17 |
| cosine | 467 | **0** | **0** | **0** | 1.1e-16 |
| student-t | 467 | **0** | **0** | **0** | 5.6e-17 |

The reference agrees: it returns the *same double* for a window and for its
z-score (§P0). The z-score is written out anyway because it is what catch22
does before every feature, and because this inertness is a measured fact and
not an obvious one — under the OTHER edge reading (§A5) it would not hold.

### A7. The BUFFER cannot bind

Six frames, 467 windows each, against the shipped 0.1:

| frame | windows | buffer 0 | buffer 0.01 | buffer 1 | buffer 1e6 | max \|gap\| |
|---|---|---|---|---|---|---|
| walk | 467 | **0** | **0** | **0** | **0** | 5.6e-17 |
| tick-rounded | 467 | **0** | **0** | **0** | **0** | 5.6e-17 |
| penny | 467 | **0** | **0** | **0** | **0** | 5.6e-17 |
| ar1 | 467 | **0** | **0** | **0** | **0** | 8.3e-17 |
| cosine | 467 | **0** | **0** | **0** | **0** | 1.1e-16 |
| student-t | 467 | **0** | **0** | **0** | **0** | 5.6e-17 |

"Moved" is counted at a tolerance of 1e-12; the residual 1e-16 is the
plain-Python spelling's own rounding against the numpy reduction (§A2), the
same floor every comparison in §A against `value_def` carries.

No point lies outside `[min, max]`, so the two outer edges cannot exclude
anything whatever their position. ⚠ The same 0.1 moves 246–463 windows when it
is pushed into the interior edges (§A5): the number is load-bearing, *where it
goes* is the decision, and the knob itself is inert.

### A8. Where the range comes from: the window, or one limb

The definition bins the SERIES and then forms the lagged limbs, so the last
`TAU` points — which appear in the lagged-TO limb only — are part of the range.
Taking it from the lagged-FROM limb instead:

| frame | windows | value bars moved | max \|gap\| |
|---|---|---|---|
| walk | 200 | 6 | 0.0343 |
| tick-rounded | 200 | 5 | 0.0477 |
| penny | 200 | 9 | 0.1182 |
| ar1 | 200 | 9 | 0.0452 |
| cosine | 200 | 0 | 0.0000 |
| student-t | 200 | 6 | 0.0674 |

Small but real, and the two limbs' **union** is the whole window, so there is
no third reading.

### A9. The lag and the bin count are the feature's own parameters

467 windows of the walk frame.

| reading | median | Spearman vs shipped |
|---|---|---|
| tau = 1 | 0.027203 | +0.1301 |
| **tau = 2 (shipped)** | 0.042746 | +1.0000 |
| tau = 3 | 0.027828 | +0.0570 |
| tau = 5 | 0.027388 | +0.1317 |
| bins = 3 | 0.005701 | −0.0525 |
| **bins = 5 (shipped)** | 0.042746 | +1.0000 |
| bins = 10 | 0.234608 | +0.4433 |

Neither is a smooth knob: at `tau` 1 the column is almost unrelated to this
one (+0.13), and at 10 bins the *level* triples because the table has 100
cells over 98 pairs.

### A10. What the column reads on INDEPENDENT data

| reading | windows | mean | median | min | max | share < 0 |
|---|---|---|---|---|---|---|
| iid normal windows, **corrected** | 400 | 0.030237 | **0.028248** | −0.046481 | 0.152281 | **0.1550** |
| iid normal windows, plug-in | 400 | 0.088502 | 0.085612 | 0.024948 | 0.213505 | 0 |
| first-order plug-in bias `(5−1)²/(2·98)` | | | 0.081633 | | | |

⚠ These are §A10's own 400 windows, drawn through the plain-Python spelling so
that the corrected and uncorrected readings come off the same draw. §A10b
draws **another** 400 through the shipped kernel and gets a median of
+0.028435 with 17.3% negative. The two samples agree on the median to 2e-4
and differ on the negative share by 1.8 points, which is what a 400-window
sample of a quantity whose median sits 0.028 above zero does; the figure
quoted elsewhere in this port is **§A10b's**, because that one runs through
the shipped code path.

| frame (shipped column) | mean | median | share above the iid median 0.0282 |
|---|---|---|---|
| walk | 0.043894 | 0.042816 | 0.6664 |
| tick-rounded | 0.033607 | 0.027017 | 0.4757 |
| penny | 0.028934 | 0.026224 | 0.4700 |
| ar1 | 0.088655 | 0.088334 | 0.9064 |
| cosine | 0.730438 | 0.729533 | 1.0000 |
| student-t | 0.027640 | 0.023382 | 0.3793 |

The AR(1)-in-returns frame is the only stochastic one that sits clearly above
the independence level, which is the column doing its job: that is the frame
with real lag-2 structure. The walk's own windows read 0.0428 against 0.0267
for the *same windows shuffled* — so even an iid-by-construction frame's
ordering carries a little of what this column measures, at this sample size.

### A10b. The same, at the lengths the guard band allows

Every interpretive statement about "no dependence" is a **length-100**
statement, because the correction scales as `1/(2(length − 2))`. 400
independent normal windows per length, through the shipped kernel:

| `length` | pairs | windows | iid median | share < 0 | first-order plug-in bias | `ami_bounds` |
|---|---|---|---|---|---|---|
| **27** (`MIN_LENGTH`) | 25 | 400 | **+0.227979** | 0.0025 | 0.320000 | [−0.3200, 1.6894] |
| 50 | 48 | 400 | +0.083742 | 0.0850 | 0.166667 | [−0.1667, 1.6511] |
| **100** (default) | 98 | 400 | **+0.028435** | 0.1725 | 0.081633 | [−0.0816, 1.6298] |
| 250 | 248 | 400 | +0.007576 | 0.2850 | 0.032258 | [−0.0323, 1.6175] |

⚠ **`MIN_LENGTH = 27` is a floor, not a recommendation.** Its stated reason —
at least as many lagged pairs (25) as the table has cells (25) — describes the
*thinnest* regime a histogram estimator has, one observation per cell, and the
table says what that costs: the reading at 27 is dominated by its own bias
(+0.228 against the default's +0.028, and a plug-in bias four times as large),
and only 0.25% of independent windows come out negative there against 17.3% at
the default. The guard band exists to stop a caller computing something
*thinner* than one pair per cell. It does not say 27 is a good place to work,
and the `length` argument's own documentation now says so.

### A11. How close the binning runs to a rounding flip

| frame | windows | min margin | median min margin | points within 1e-12 of an edge |
|---|---|---|---|---|
| walk | 200 | 1.253e-06 | 4.175e-03 | **0** |
| tick-rounded | 200 | 9.270e-06 | 2.563e-03 | **0** |
| penny | 200 | 3.798e-04 | 1.933e-02 | **0** |
| ar1 | 200 | 1.262e-05 | 4.257e-03 | **0** |
| cosine | 200 | 1.719e-02 | 1.719e-02 | **0** |
| student-t | 200 | 2.677e-04 | 4.610e-03 | **0** |

This is the number §D2 rests on: below the margin, a perturbation cannot move
the integer count matrix, and the value is a function of that matrix alone.

---

## B. Gate B — causality

### B1. The real module

Replace every close from bar J on with a fresh path; no bar before J may move.

| frame | offsets | splices | leaking offsets |
|---|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 35 each | 8 | **none** |
| walk at `length` 27 / 120 / 250 | 35 each | 4 | **none** |

### B2. Twelve mutants, read off this module's source, edited and exec'd in memory

Same sweep, walk frame, 35 offsets × 8 splices.

| mutant | what it does | offsets caught of 35 |
|---|---|---|
| write-back-dated | writes each chunk one bar early | **35** |
| window-one-ahead | each window reads one return from the future | **35** |
| window-ten-ahead | each window reads ten returns from the future | **35** |
| returns-rolled | the return series is shifted one bar earlier | **35** |
| chunk-wide-extremes | the bin edges come from the whole chunk's extremes | **30** |
| mask-back-dated | the bad-data MASK reads the next bar | 0 (see §B3) |
| chunk-wide-demean | each row is centred on the chunk's mean | 0 (see §B4) |
| chunk-wide-sd | each row is scaled by the chunk's sd | 0 (see §B4) |
| joint-transposed | swaps which limb indexes the rows of the joint table | 0 (see §B4) |
| no-bias-correction | drops the Miller–Madow correction | 0 (not a look-ahead) |
| no-overflow-guard | drops the `isfinite(sd)` limb | 0 (not a look-ahead) |
| no-floor | drops the noise floor | 0 (not a look-ahead) |

The four look-aheads are caught on the **whole** sweep, which is unusual for
this family: the two integer-valued siblings' ONE-BAR mutants are caught on
8 of 35 (`c22_periodicity`, walk) and 22 of 35 (`c22_ami_timescale`, walk),
where they tie on 88.7% and 79.7% of neighbouring pairs and reach 100% on
their cosine frames, so their sweeps cannot witness most splices
(`docs/C22PeriodicityMeasured.md` §B2, `docs/C22AmiTimescaleMeasured.md` §B2).
This column ties on 7.2% to 21.7% (§B5; 7.4% to 21.5% under the CI dispatch,
§F1), so a one-bar shift has almost nowhere to hide.

### B2b. Where a one-bar mutant moves anything, it moves exactly bar J − 1

22 of 35 offsets move some pre-splice bar, and on **22 of 22** the first moved
bar is J − 1. That is what makes it a look-ahead of one bar and not of two.

### B3. The mask mutant

Bit-equal to the real module on all 1,500 bars of the clean walk — it
back-dates the bad-data MASK, and a clean frame has no mask to move. On a
frame with one bad close it moves exactly bar J − 1, caught **12 of 12**.

### B4. Three mutants are DEAD, and each reason is measured

| mutant | walk | tick-rounded | penny |
|---|---|---|---|
| chunk-wide-demean | bit-equal | bit-equal | bit-equal |
| chunk-wide-sd | bit-equal | bit-equal | bit-equal |
| joint-transposed | 568 bars differ, max gap **5.6e-17** | 618 bars, 5.6e-17 | 613 bars, 5.6e-17 |
| *the same under the CI dispatch* | 539 bars | 613 bars | 625 bars (gap 5.6e-17 throughout) |
| chunk-wide-extremes | moved 1,400, max gap 0.125 | moved 1,400, 0.105 | moved 1,400, 0.133 |

The first two ARE reads of other rows, so the sweep *should* see them. It
cannot, for the §A6 reason: the interior edges are affine in each row's own
extremes, so centring or scaling a row by the whole chunk's mean or standard
deviation moves the data and every edge together and no point changes bin.

The third answers a different question — whether the module has the joint
table's **axes** the right way round. It does not matter which limb indexes
the rows: a mutual information is symmetric, and so is the Miller–Madow term,
which counts occupied cells, rows and columns. Transposing the table therefore
changes nothing but the ORDER of the 25 logarithms, and that is exactly what
is measured: 5.6e-17 on 568 to 618 bars of 1,400, one unit in the last place.
⚠ This is NOT the same as the "marginals transposed" candidate of §P1c, which
pairs `pi[j]` with `pj[i]` and is a real (and wrong) formula — it matches the
reference on 21 of 2,802 windows.

All three are counted among the twelve rather than quietly dropped, and the
cross-row read that *does* bite — taking the extremes from the chunk — is
caught both by values and by the sweep.

### B5. Tie density — the sweep's power

| frame | fired bars | share of neighbouring pairs exactly equal | distinct values |
|---|---|---|---|
| walk | 1,400 | 0.0893 | 1,266 |
| tick-rounded | 1,400 | 0.0715 | 1,296 |
| penny | 1,400 | 0.1008 | 1,252 |
| ar1 | 1,400 | 0.0843 | 1,272 |
| cosine | 1,400 | 0.1994 | 8 |
| student-t | 1,400 | 0.2166 | 1,043 |

⚠ Both of these columns are counts of exact float equality, so both move
under the CI dispatch: the tie shares read 0.0901 / 0.0736 / 0.1015 / 0.0836 /
0.1994 / 0.2152 and the distinct values 1,264 / 1,293 / 1,251 / 1,271 / 7 /
1,047 (§F1). The range quoted elsewhere, 7.2% to 21.7%, is therefore 7.4% to
21.5% there; what the tests pin is "under 40%" and "at least 700 distinct
values".

---

## C. Gate C — reachability

### C1. Synthetic frames (1,500 bars each)

| frame | fired | distinct | min | median | max | share == 0 | share > 0.5 |
|---|---|---|---|---|---|---|---|
| walk | 1,400 | 1,266 | −0.032827 | 0.042816 | 0.162773 | 0 | 0 |
| tick-rounded | 1,400 | 1,296 | −0.031129 | 0.027017 | 0.144120 | 0 | 0 |
| penny | 1,400 | 1,252 | −0.032866 | 0.026224 | 0.119293 | 0 | 0 |
| ar1 | 1,400 | 1,272 | −0.022386 | 0.088334 | 0.206591 | 0 | 0 |
| cosine | 1,400 | 8 | 0.727466 | 0.729533 | 0.734307 | 0 | 1.0000 |
| student-t | 1,400 | 1,043 | −0.019797 | 0.023382 | 0.116091 | 0 | 0 |

Derived bounds at `length` 100: `[−0.081633, 1.629846]`. Exactly 0.0 is
reachable — a window whose whole table is one cell — and was reached on **0**
of these 8,400 bars; it IS reached by the overflow case in §H, which is why
that guard exists.

### C2. The issue's own worry: BIST tick rounding

| frame | zero returns | median distinct returns per window | median value | fired |
|---|---|---|---|---|
| walk | 0.0000 | 100 | 0.042816 | 1,400 |
| tick-rounded | 0.0027 | 100 | 0.027017 | 1,400 |
| penny | **0.2168** | **68** | **0.026224** | 1,400 |

On the penny frame's first window the 5 bins hold 2 / 15 / **48** / 28 / 7
points: the exactly-zero return collapses nearly half the window into the
middle bin. The column still fires everywhere with 1,252 distinct values, and
what the rounding does to the READING is to push it **down**, from the walk's
0.0428 to 0.0262 — toward the no-dependence value, not away from it. Whether a
price level or a candle-shape column becomes its top real comparator was Gate
E's question, and the 2026-11-20 run answers it: the top comparator is
`Dist_from_High_252_pct`, with `drawdown_DD_PCT` top inside `compute_all` —
both price-DERIVED, both **percent distances rather than the price levels the
issue named** (`mcgd`, `ROLLING_LOW_250`, `Volume`), and neither is close
enough to matter: \|ρ\| **0.0594** pooled and **0.0742** as the largest
per-frame median (§E).

### C3. What the one blanking rule costs

| frame | fired | max window sd | unguarded would read | range |
|---|---|---|---|---|
| flat run from bar 400 | 399 of 700 | 1.7e-02 | 3 of 4 sampled | −0.0269 … 0.0521 |
| exact geometric ladder | **0** of 1,500 | 1.5e-16 | 8 of 8 sampled | −0.0195 … 0.0621 |
| 1-ulp step at 1e6 | **0** of 1,500 | 2.2e-17 | 100 of 100 (§G, every window) | 0.000000 … 0.000105 |
| one kurus a bar | **1,400** of 1,500 | 2.9e-07 | 8 of 8 | 1.3432 (constant) |

`NOISE_FLOOR = 9.095e-13`. The `unguarded` column above is sampled; §G
measures the geometric ladder on **every** window instead, through the
module's own source with the floor removed, and it fires on **1,400 of
1,500** reading −0.0199 to 0.0932 (median 0.0103). Those readings sit squarely
inside the walk frame's own range: a reader could not tell them from a real
one, and they are the rounding of `start * (1 + step)**k` (3 or 4 distinct
returns per window).

⚠ **The one-kurus-a-bar path FIRES here**, and that is the asymmetry worth
knowing:

| frame | `c22_ami2` | `c22_ami_timescale` | `c22_periodicity` |
|---|---|---|---|
| exact geometric ladder | 0 | 0 | 0 |
| one kurus a bar | **1,400** | 1,400 | **0** |

Its return standard deviation is 2.9e-07, 316,000× the floor, so nothing
blanks it — and it reads **1.3432**, constant, within 0.29 of the top of the
scale, because a smooth monotone return series really is almost perfectly
lag-2 dependent. A companion must not assume the three catch22 ports blank
together.

### C4. The floor is inert on anything price-shaped

Guarded against the unguarded spelling (a mutant of the module's own source):
**0 value bars and 0 mask bars differ** on each of the six frames.

### C5. Real data — measured 2026-11-20 by the Gate E run

Every count in §A–§D is SYNTHETIC; this is the real-data limb, from run
`is127-c22_ami2-23b6686b` over the 89 frozen ALTPORT-1 BIST frames:

| | |
|---|---|
| pooled bars | 398,849 |
| `C22AMI2_100` non-NaN | **389,949** |
| non-zero | **389,949** |

**389,949 of 398,849 bars fire (97.77%)**, and the 8,900 NaN bars are
`89 × 100` exactly — the warm-up (100 returns needed, so bars 0–99 of each
frame), with **0 further bars blanked**. The §C3 floor and the §P2 difference
from the reference therefore cost nothing on this universe: no BIST window of
100 returns is flat or exactly geometric enough to trip `sd ≤ 9.095e-13`.

non-zero equals non-NaN, so exactly 0.0 — reachable in principle (§C1) and
never reached on 8,400 synthetic bars either — was **not** read on any of the
389,949 BIST bars. The sibling `c22_periodicity` has the two counts differing
(389,949 / 389,926), so the field does discriminate.

---

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

All four factors — ×8, ×64, 2⁻⁴⁰, 2⁴⁰ — against all three axes:

| axis | cells | result |
|---|---|---|
| the six frames | 24 | **bit-equal** |
| `length` 27 / 120 / 250 (walk) | 12 | **bit-equal** |
| price levels 1e−6 / 1e+6 / 1e+100 | 12 | **bit-equal**, 1,400 bars firing at each level |

By construction — the price enters only as `c[t]/c[t−1]`, and `8a / 8b` is the
double `a / b`.

### D2. Inexact rescales — also bit-identical, and not by luck

×10, ×3.7, ×0.1 and ×1.0000001 on all six frames: **0 value bars moved, max
gap 0.0e+00, 0 mask bars**, 24 of 24 cells. The arithmetic does not promise
this — ×10 is not exact in binary, so the returns themselves move in the last
bits — but the structure does: the value is a function of a 5×5 matrix of
INTEGER counts, so a perturbation that moves no point across a bin edge cannot
move the output at all, and the measured margin to the nearest edge is
1.25e-06 (§A11).

### D3. Blind to the AMPLITUDE of the returns, not to their ORDER

| reading | moved of 467 | |
|---|---|---|
| returns ×0.5 | **0** | max gap 5.6e-17 |
| returns ×2 | **0** | max gap 5.6e-17 |
| returns ×10 | **0** | max gap 5.6e-17 |
| the same returns SHUFFLED | **467** | Spearman +0.0450 |

### D4. `0 < fires < n`, and not constant

1,400 fired of 1,500 on every frame; 1,043 to 1,296 distinct values on the
five stochastic ones (8 on the cosine frame, spanning 0.0068 nats), max − min
0.136 to 0.229 (0.0068 on the cosine frame).

---

## E. Gate E — measured 2026-11-20 by issue-solver → **SHIP**

Run `is127-c22_ami2-23b6686b`
(`gate_e_overlap.py run --module pandas_ta.statistics.c22_ami2`), made by the
launcher against this tree: 89 frozen ALTPORT-1 BIST frames, 398,849 pooled
bars, 329 `compute_all` + 358 `ml_features` manifest = **687** comparators
(the run's `n_degenerate` field reads 1), canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`,
pandas 2.3.3 / numpy 1.26.4, module sha1 `bbc248507ee8de16080355815ed5260cc807590c`,
tree sha1 `df4cb6d97fcf141f3eaab2d71717bd16133db261`, data stamp
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`.

| | `C22AMI2_100` |
|---|---|
| pooled max \|ρ\| | **0.05943562162216838** (ρ = −0.05943562162216838) |
| against | `Dist_from_High_252_pct` (manifest), n = **389,949** |
| top within `compute_all` | `drawdown_DD_PCT` 0.056832547398623645, n = 389,949 |
| per-frame max median \|ρ\| | **0.07418786831507361** vs `natr`, 89 frames |
| frames with a per-frame median ≥ 0.90 | **0.0%** |
| non-NaN / non-zero | 389,949 / 389,949 (§C5) |
| bands | `r3-perframe-0.90` → pooled 0.0594 < 0.76 and 0.0742 < 0.90 → **SHIP** |

SHIP is the whole verdict: no column is removed, nothing is disclosed, no
waiver is needed. The row is in `docs/gate_e_ledger.csv` as
`c22_ami2,pandas_ta.statistics.c22_ami2,C22AMI2_100,SHIP,…,is127-c22_ami2-23b6686b,2026-11-20`
with an empty waiver field, recorded by
`python docs/gate_e_ledger.py record … --measured 2026-11-20`, which refuses a
row whose module sha1 is not this tree's.

### E0. The prototype's figure, beside this port's

The 2026-10-24 screen measured the **prototype** — the GPL-3.0 reference's
column through pycatch22 (run `screen_r3_20261024`, same 89 frames, 398,849
bars, 687 comparators, canary bit-equal):

| | prototype, 2026-10-24 | this port, 2026-11-20 |
|---|---|---|
| pooled max \|ρ\| | **0.0595** | **0.0594** (0.05943562162216838) |
| against | `Dist_from_High_252_pct`, n = 389,949 | the same, n = 389,949 |
| top-5 per-frame max median | 0.0742 | 0.0742 (0.07418786831507361) |
| next comparators | `drawdown_DD_PCT` 0.0568, `drawdown_DD_LOG` 0.0568 | `drawdown_DD_PCT` 0.0568 is the `compute_all` top |
| fork overlap (stage 2, 12 frames, not Gate E) | 0.0596 vs `covariance:COV_30_1`, per-frame max median 0.0854 | not re-run (§E1 is the in-fork reading made here) |

They agree to three decimals on the same top comparator and the same sample
size, and §P1 is why that was expected: this column equals the reference to
1e-12 on 8,400 of 8,400 windows of six frames. The two runs are still two runs
— the fourth decimal differs as printed (0.0595 vs 0.0594), and the
prototype's number is not evidence for this port; the row above is.

### E1. In-fork overlap, measured HERE (6 synthetic frames, not Gate E)

Spearman against every other `statistics` column the fork registers that
scores — 60 comparator columns, **price-level ones included**: there is no tag
filter in the harness, and `MAD_30` (ninth in the table below) is tagged `PX`
by the dictionary. A price-level comparator scoring high here would be the
issue's own worry showing up, which is why they are not filtered out:

| comparator | max \|ρ\| over the frames | on which frame | median \|ρ\| |
|---|---|---|---|
| `TS_AGGAC_60_10` | 0.8784 | cosine | 0.1340 |
| `TS_AC1_60` | 0.8777 | cosine | 0.1714 |
| `COV_30_1` | 0.8761 | cosine | 0.0616 |
| `TS_CID_CE_20` | 0.8754 | cosine | 0.1028 |
| `TFDFA_100` | 0.8691 | cosine | 0.1193 |
| `KPSS_100` | 0.8153 | cosine | 0.1414 |
| `DIFF2ACF1_100` | 0.8136 | cosine | 0.2304 |
| `KURT_30` | 0.8051 | cosine | 0.0587 |

⚠ **Every one of the twelve largest maxima is on the cosine frame**, where
this column takes 8 distinct values over 1,400 bars and a rank correlation is
mostly a tie-breaking artefact. The quantity the `r3-perframe-0.90` band uses
is the per-frame **median**, and the largest here is **0.2304**
(`DIFF2ACF1_100`). This is not Gate E: 6 synthetic frames, not 89 BIST ones,
and 60 comparators rather than 687.

### E2. Against the two catch22 siblings in this fork

| sibling | max \|ρ\| | median \|ρ\| |
|---|---|---|
| `c22_ami_timescale` | 0.4709 | 0.1273 |
| `c22_periodicity` | 0.2402 | 0.1303 |

The three read the same 100-return window and are not restatements of each
other on these frames.

### E4. **OWED RULE** — two catch22 relatives that are not in this tree

Issue **#132** (`SB_MotifThree_quantile_hh`, the entropy of 2-letter words in
a 3-quantile return alphabet) and issue **#129**
(`SB_TransitionMatrix_quantile_3`, the same window's lag-1 transition matrix)
both **bin the same 100 returns and count lagged pairs** — this column's
construction with a different alphabet and a different lag. #132 is literally
one of the three entropies in this column's formula, `H(i, j)`, over a
3-symbol alphabet at lag 1. Neither is in `Category`, so neither Gate E nor
§E1 can see them, and no run has priced the pair.

Priced here instead, by **proxies written from those features' descriptions**
— not ports, and not Gate E — over the six frames, 467 windows each:

| relative (proxy) | walk | tick-rounded | penny | ar1 | cosine | student-t | max | median |
|---|---|---|---|---|---|---|---|---|
| #132, entropy of the 9 two-letter words | 0.0274 | 0.0067 | 0.1741 | 0.5272 | 0.2445 | 0.0887 | **0.5272** | 0.1314 |
| #129, trace of the transition matrix's column covariance | 0.0289 | 0.0054 | 0.1606 | 0.4937 | 0.2355 | 0.0880 | **0.4937** | 0.1243 |

(\|ρ\| of Spearman against `C22AMI2_100`.) Both peak on the AR(1) frame, which
is the frame with real lag-structure — exactly where two lagged-pair features
should agree — and sit at 0.0054 to 0.25 everywhere else. That is well under
the `r3-perframe-0.90` line, on synthetic frames.

**THE RULE.** When issue #132 or #129 is ported, it is measured against
`C22AMI2_100` before it ships. ⚠ Gate E cannot do it: its 687 comparators are
the engine's `compute_all` ∪ the `ml_features` manifest, and this fork's own
`C22AMI2_100` is not among them (§E1: "60 comparators rather than 687"). The
instrument is the **stage-2 fork-overlap** screen — scale-free `Category`
outputs at defaults, which is how the 2026-10-24 screen reported its own fork
comparison — or §E1 re-run with the new column in `Category`. The figures
above are the prior; a pooled \|ρ\| at or above 0.90, or a top-5 per-frame
median at or above 0.90, at the same line Gate E's bands use, means one of
the two is a restatement and must be reverted or waived. `tests/test_c22_ami2.py::test_the_owed_rule_for_the_nearest_catch22_relatives`
fails if this section is dropped.

---

## F. Gate F — suites

**This module:** `python -m pytest tests/test_c22_ami2.py -q` → **244 passed**
in 17.6 s (the receipt session swapped the two pending-Gate-E tests for three
that pin the recorded row; the porting session's run was 243 passed in 17.9 s).

**Under the CI CPU dispatch:** `python docs/measure_c22_ami2_cpu.py` →
**244 passed** in 17.8 s with `NPY_DISABLE_CPU_FEATURES = 'AVX512F
AVX512_SKX AVX2 FMA3'`. That script sets the variable before numpy is
imported and then **refuses to run** unless all four features are actually
off — it prints the dispatchable features still enabled (`SSSE3`, `SSE41`,
`POPCNT`, `SSE42`, `AVX`, `F16C`, `AVX512CD`, `AVX512_CLX`, `AVX512_CNL`,
`AVX512_ICL`) — so the claim cannot drift from what was turned off. ⚠ The
launcher's own spelling (`NPY_DISABLE_CPU_FEATURES=… python -m pytest …`) is
an environment-prefixed command, which this session's shell rules do not
allow; the script is the same run by another route.

**Whole suite:** `python -m pytest -q` → **1 failed, 13,491 passed, 86
skipped** in 8 m 41 s, on the final tree with the review log and the recorded
ledger row in place. The one failure is expected and is not caused by this
port's code:

| failure | why |
|---|---|
| `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` | pre-existing on every clean checkout here: it needs the sibling `../AlternativeRepos` tree, and CI deselects it by name. |

The porting session's run was **2 failed, 13,482 passed, 86 skipped**; the
second failure was `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(*"no Gate E ledger row for ['c22_ami2']"*), which the recorded row closes —
`tests/test_c22_ami2.py::test_the_gate_e_row_is_recorded_and_says_ship` is now
the mirror of it.

The 86 skips are the upstream correlation suite (`data/SPY_D.csv` is
gitignored) plus the environment-dependent ones; the port's own tests are
self-contained.

**The Backtesting repo's suite** is Gate F's other half and is run by the
launcher in a clean worktree.

### F1. What moves under the CI CPU dispatch

Re-measured sections A, B, C, D, E and G with the four features off. The rows
below are the whole re-measurement: every digit named here moves on a CI CPU,
and the facts named as unchanged inside each row were checked. §H and §T came
back identical; §P needs the GPL-3.0 reference and is not part of the CI
question. §E's Gate E digits and §C5's BIST counts are the launcher's single
run on its own machine and were not re-measured here at all — which is why the
tests pin the ρ figures as the **bands** they decide (`< 0.76`, `< 0.90`) and
the integer counts exactly (389,949, `non_zero == non_nan`), and check the
printed decimals only as text in this document.

| section | moves |
|---|---|
| A1 / A2 (oracle and spelling gaps) | last digits only. A1's max gap goes 8.3e-17 → 6.9e-17 (walk), 1.7e-16 → 1.8e-16 (penny) and 1.1e-16 → 8.3e-17 (ar1). A2's `sklearn` column moves in **every** cell (1.0e-15 → 8.7e-16 / 8.0e-16 / 8.5e-16 / 8.3e-16 on the first four frames, 1.2e-15 → 1.0e-15 on student-t, and **up**, 8.9e-16 → 1.0e-15, on the cosine one) and its entropy-identity column in two (tick-rounded 1.3e-15 → 1.4e-15, student-t 9.0e-16 → 8.9e-16). Count matrices still **15 of 15** on every frame. |
| A4 (the bin-assignment spelling) | the "value bars differing in any bit" column moves 108 → 104 (walk), 134 → 115, 126 → 111, 121 → 114, 60 → 50, 114 → 115. **"Points binned differently" stays 0 of 200 on every frame**, which is the structural claim. |
| A5 / A5b (the two load-bearing readings) | the cosine frame's Spearman +0.9863 → +0.9886 in both. Every bars-moved count identical (434 / 463 / 246 / 462 / 0 / 434 and 467 / 467 / 467 / 467 / 467 / 436), and so is every correction figure. |
| A6 / A7 (the inert knobs) | the tick-rounded frame's max \|gap\| 5.6e-17 → 1.1e-16. All **42** moved-counts still **0** (§A6's 3 readings × 6 frames and §A7's 4 × 6). |
| B4 / B5 | the `joint-transposed` bars-moved counts go 568 / 618 / 613 → **539 / 613 / 625** (its max \|gap\| stays 5.6e-17, which is the claim), and §B5's tie shares 0.0893 / 0.0715 / 0.1008 / 0.0843 / 0.1994 / 0.2166 → **0.0901 / 0.0736 / 0.1015 / 0.0836 / 0.1994 / 0.2152**, so §B5's range reads **7.4% to 21.5%** instead of 7.2% to 21.7%. §B5's distinct-value counts are §C1's. **Every catch count is identical**: B1 none on six frames and three lengths, B2 35 / 35 / 35 / 35 / 30 and seven zeros, B2b 22 of 22, B3 bit-equal then 12 of 12, B4's three dead mutants still dead and `chunk-wide-extremes` still 1,400 bars on three frames. |
| E1 / E4 (Spearman maxima) | §E1's eight printed maxima move by **+0.0004 to +0.0126** — `TS_AGGAC_60_10` 0.8784 → 0.8789, `TS_AC1_60` 0.8777 → 0.8781, `COV_30_1` 0.8761 → 0.8776, `TS_CID_CE_20` 0.8754 → 0.8768, `TFDFA_100` 0.8691 → 0.8746, `KPSS_100` 0.8153 → 0.8258, `DIFF2ACF1_100` 0.8136 → 0.8246, `KURT_30` 0.8051 → **0.8177** — and §E4's proxies by up to 0.0036 (#132 walk 0.0274 → 0.0273, tick-rounded 0.0067 → 0.0066, penny 0.1741 → 0.1740, cosine 0.2445 → **0.2409**, student-t 0.0887 → 0.0885, median 0.1314 → 0.1313; #129 cosine 0.2355 → 0.2336). Every per-frame **median** in §E1, both §E4 maxima (0.5272 and 0.4937), §E4's #129 walk / tick-rounded / penny / ar1 / student-t cells and the ordering of §E1's top eight are unchanged. These are rank correlations on a frame where the column takes 7 or 8 values (§E1's own warning), so they are the most dispatch-sensitive numbers in the document — and the largest of them is still 0.08 below the 0.90 band line. |
| A3 (the exact laws) | **nothing** — 0.0e+00 on all three frames, same values to 12 dp. |
| C1 and §D4 (distinct values) | 1,266 → 1,264 (walk), 1,296 → 1,293, 1,252 → 1,251, 1,272 → 1,271, 8 → **7** (cosine), 1,043 → **1,047** (student-t), in both sections, which print the same counts. min / median / max identical to 6 dp on every frame; `share == 0`, `share > 0.5`, the fired counts and §D4's `max − min` identical. |
| C2, C4 | identical. |
| C3 and §G (the rounding-noise frames) | every fired count identical (0 / 0 / 1,400 / 399 in §C3, 1,400 and 100 for §G's two unguarded runs), and so is the one-kurus reading 1.3432 — but the geometric ladder's own digits move, because that frame IS rounding: max window sd 1.455e-16 → 1.392e-16, **min window sd 8.882e-17 → 7.679e-17** and so "× the floor" 1.6e-04 → 1.5e-04, unguarded sampled range [−0.0195, 0.0621] → [−0.0168, 0.0263], §G's full unguarded min/median/max −0.0199/0.0103/0.0932 → −0.0199/0.0074/0.0417, distinct returns per window 3–4 → 3. The 1-ulp frame's own figures (100 fired, 0.000000/0.000105/0.000105) are identical. |
| D1 | identical — bit-equal in all 24 cells, all three lengths, all three price levels. |
| D2 | identical — 0 value bars moved, max gap 0.0e+00, in all 24 cells. |

That is why `test_the_column_is_not_constant_on_a_stochastic_frame` asserts
**≥ 700** distinct values rather than 1,266, and why
`test_the_cosine_frame_is_nearly_constant_by_construction` asserts ≥ 4
rather than 8. The structural facts — the count matrices, the exact laws, the
bit-identity under rescale — do not move, which is the §A11 margin again:
the integers are decided with 1.25e-06 of room and only the sum of 25
logarithms is dispatch-sensitive.

---

## G. The floor, and what it buys

`NOISE_ULPS × eps = 9.094947e-13`. The floor bounds the window's **return
standard deviation**, which is the same quantity the z-score divides by: one
number doing two jobs.

| frame | min window sd | × the floor |
|---|---|---|
| walk | 1.287e-02 | 1.4e+10 |
| tick-rounded | 1.200e-02 | 1.3e+10 |
| penny | 1.041e-02 | 1.1e+10 |
| ar1 | 9.636e-03 | 1.1e+10 |
| cosine | 7.107e-03 | 7.8e+09 |
| student-t | 1.077e-02 | 1.2e+10 |
| geometric ladder (max) | 1.455e-16 | 1.6e−04 |
| 1-ulp step at 1e6 (max) | 2.220e-17 | 2.4e−05 |
| one kurus a bar (max) | 2.873e-07 | **3.2e+05** |

Ten orders of magnitude separate a real frame from the floor, and five
separate the floor from the smooth path it does **not** catch.

What the ladder reads **unguarded**, measured on every window through the
`no-floor` mutant of this module's own source (not on a sample):

| | |
|---|---|
| fires | **1,400 of 1,500** (guarded: **0**) |
| min / median / max | −0.0199 / 0.0103 / 0.0932 |
| distinct returns per window | 3 to 4 |
| window sd | 8.882e-17 to 1.455e-16, against a floor of 9.095e-13 |

Every one of those 1,400 readings is inside the walk frame's own measured
range (§C1: −0.0329 to 0.1628), which is what the floor buys. ⚠ The frame IS
rounding noise, so the three value digits move with the CPU dispatch — with
`AVX512F AVX512_SKX AVX2 FMA3` off they are −0.0199 / 0.0074 / 0.0417 and the
window holds 3 distinct returns — while the **count** does not (§F1).

And the 1-ulp frame measured the same way, every window through the same
mutant:

| | |
|---|---|
| fires | **100 of 1,500** (guarded: **0**) |
| min / median / max | 0.000000 / 0.000105 / 0.000105 |

Only the 100 windows that hold the step have any variation at all; the other
1,400 are exactly flat and blank under any rule, which is why the fired count
is 100 and not 1,400.

---

## H. Bad data, the guard band and the wiring

| bad close at bar 700 | blank bars ≥ `length` | first | last |
|---|---|---|---|
| NaN, ±inf, 0.0, −5.0, 1e−310 | **101** each | 700 | 800 |

| close pair | return | blank | without the `isfinite(sd)` limb |
|---|---|---|---|
| 1e−300 → 1e100 | inf | 100 | the limb is inert (the return filter catches it) |
| 1e−100 → 1e100 | 1.0e+200 | 100 | those bars read **0.0** |
| 1e−50 → 1e27 | 1.0e+77 | 0 | inert — the sums stay finite |

The `~isfinite(sd)` limb is load-bearing exactly once and it is measured: a
*finite* return of 1e200 overflows the window's sum of squares, `sd` becomes
+inf — which CLEARS the floor — every z becomes 0, and the row would read
exactly **0.0**, this column's "nothing in the window", instead of blanking.

| n | result | | `length` | name | fired |
|---|---|---|---|---|---|
| 99 | `None` | | `None` / 0 / 1 / 26 | `C22AMI2_100` | 1,400 |
| 100 | `None` | | 27 | `C22AMI2_27` | 1,473 |
| 101 | fired 1 | | 250 / 250.7 | `C22AMI2_250` | 1,250 |
| 102 | fired 2 | | | | |

`offset=2` shifts the column; `fillna=-1` fills exactly the 100 warm-up bars.
Five wiring touch points: module, package export, `Category["statistics"]`,
`df.ta.c22_ami2`, `tests/test_c22_ami2.py` — all present. `Category` totals
**362** with **60** in `statistics`, which is what `README.md`,
`docs/IndicatorDictionary.md` and `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` now say and what `tests/test_readme_counts.py` checks against
the live package. The sweep of §1: **398** `.py` files under `pandas_ta/`,
**0** importing the GPL-3.0 reference.

---

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_ami2.py P`. pycatch22 1.0.2 is run to MEASURE only —
the same use `docs/issues/screen/ind_screen_r3.py` makes of it — and no
shipped module imports it. The entry point found at runtime is
`CO_HistogramAMI_even_2_5`, which emits a deprecation notice: *"now
CO_HistogramAMI_even_5bin_ami2 (catch22 v1.0, which also changed its
definition to match hctsa)"*. `catch22_all`'s short name for it is `ami2`,
index 14.

### P0. Entry points, and whether the reference z-scores for us

All four readings of the walk frame's first window are the **same double**:

| | value |
|---|---|
| `catch22_all` on the raw window | −0.026946688721 |
| `CO_HistogramAMI_even_2_5` on the raw window | −0.026946688721 |
| the same on the **z-scored** window | −0.026946688721 |
| `catch22_all` on the z-scored window | −0.026946688721 |
| **this port** | −0.026946688721 |

So the reference is affine-invariant too, which is the §A6 property seen from
outside, and the screen's use of `catch22_all` on raw returns is the same
column as a z-scored one.

### P1. Shipped against the reference, EVERY window of six frames

| frame | windows | bit-equal | equal to 1e-12 | max \|gap\| | Spearman |
|---|---|---|---|---|---|
| walk | 1,400 | 279 | **1,400** | 1.4e-16 | +1.0000 |
| tick-rounded | 1,400 | 259 | **1,400** | 1.2e-16 | +1.0000 |
| penny | 1,400 | 235 | **1,400** | 1.1e-16 | +1.0000 |
| ar1 | 1,400 | 383 | **1,400** | 1.4e-16 | +1.0000 |
| cosine | 1,400 | 980 | **1,400** | 2.2e-16 | +0.9858 |
| student-t | 1,400 | 163 | **1,400** | 1.7e-16 | +1.0000 |
| **TOTAL** | **8,400** | **2,299** | **8,400 of 8,400** | | +0.9999 |

0 disagreements beyond 1e-12. The cosine frame's Spearman is +0.9858 rather
than +1 because the column takes 8 values there and the ranks are nearly all
ties; the max gap of 2.2e-16 is the real statement for that frame.

The residual 1e-16 is the order of the 25 logarithms' own summation, not a
structural difference — which §A1's exact count matrices confirm from the
other side.

### P1b. WHICH reading the reference implements

Every third window of the six frames (2,802), scored by this port and by the
other defensible readings. The count is windows where that reading equals the
REFERENCE to 1e-12.

| reading | agrees with the reference |
|---|---|
| **shipped (outer-edge buffer, Miller–Madow, ddof 1)** | **2,802 / 2,802** |
| shipped, plain-Python spelling | 2,802 / 2,802 |
| population z-score (ddof 0) | 2,802 / 2,802 |
| floor-division bin assignment | 2,802 / 2,802 |
| range from the lagged-from limb, not the window | 2,705 / 2,802 |
| the buffer pushed into the interior edges too | **763** / 2,802 |
| no bias correction (raw plug-in MI) | **31** / 2,802 |
| no correction AND the interior buffer | 15 / 2,802 |
| tau = 1 | 0 / 2,802 |
| 10 bins | 0 / 2,802 |

The four readings at 2,802 are the ones §A4/§A6 measured to be the *same
quantity*; the ones below are different columns.

### P1c. HOW the estimator was identified

**This port's first reading was wrong, and the measurement is what found it.**
The first version computed the plug-in MI over bins evenly spaced across the
padded range `[min − 0.1, max + 0.1]` — a defensible reading of "even bins,
buffered so all points are included". It agreed with the reference on **15 of
2,802** windows.

The reference returns **negative** values (−0.0269 on the walk's first
window), and a mutual information is a Kullback–Leibler divergence and cannot
be negative. That is a structural fact, not a tolerance question, so the
quantity it reports is not a plug-in MI of a 5×5 table at all.

A battery of 18 candidate formulas was then derived — from named estimators
(Miller–Madow), from the readings of the definition's own sentence (where the
buffer goes), and from the normalisation slips that make marginals sum to more
than one — and fitted to the reference as a black box over the same 2,802
windows:

| candidate | equals the reference | mean residual | max \|residual\| |
|---|---|---|---|
| **MI − Miller–Madow (cells)** | **2,802 / 2,802** | −0.000000 | 0.000000 |
| interior buffer, MI − Miller–Madow | 763 / 2,802 | −0.001121 | 0.070080 |
| plug-in MI, no correction | 31 / 2,802 | +0.044984 | 0.081633 |
| marginals transposed | 21 / 2,802 | +0.046681 | 0.085095 |
| interior buffer, plug-in MI | 15 / 2,802 | +0.042317 | 0.119250 |
| MI − (occ_i−1)(occ_j−1)/2N | 13 / 2,802 | −0.035396 | 0.066327 |
| MI − (bins−1)²/2N | 13 / 2,802 | −0.036648 | 0.081633 |
| marginals over the whole window, /n | 0 / 2,802 | +0.045952 | 0.082925 |
| marginals over the whole window, /pairs | 0 / 2,802 | +0.005546 | 0.042519 |
| joint /n, marginals /n | 0 / 2,802 | +0.060705 | 0.100376 |
| one marginal over the whole window | 0 / 2,802 | +0.025273 | 0.062338 |
| (and 7 more interior-buffer variants) | 0–**8** / 2,802 | | |

The best of those seven unlisted variants is `interior buffer, marginals
transposed` at 8 of 2,802; the other six are 0.

One candidate reproduces it on every window of six very different frames, to
1e-12 — the residual is **2.2e-16** at worst over the 8,400 windows of §P1,
which is where it was measured; the `0.000000` in the table above is only the
battery's print resolution — and `MI = H(i) + H(j) − H(i, j)` with
Miller and Madow's `+(m−1)/(2N)` on each of the three entropies is exactly
that candidate. The two nearest misses differ from it only in the buffer
(763) or only in the correction (31), so the fit identifies **both** readings
and not a lucky combination.

What this is and is not: it is a measurement of the reference's OUTPUT, used
to choose between readings of a definition. It is not a transcription of
GPL-3.0 code, and the shipped module contains no line derived from one — the
correction is a 1955 estimator spelled from its own formula, and §A3's exact
laws and §A1's exact oracle check it independently of the reference.

### P2. The windows this port BLANKS and the reference scores

| frame | blank here (sampled) | scored by the reference | its values |
|---|---|---|---|
| geometric ladder | 61 | **61** | −0.0186 … −0.0104 |
| flat run from bar 400 | 9 | **9** | 0.0 |
| one kurus a bar | 0 | 0 | — |

The reference scores the degenerate windows this port refuses, so this
column's non-NaN count on real data is **lower** than the prototype's wherever
a BIST window is flat or exactly geometric. On the 89-frame universe the
prototype's own `w.std() > 0` filter already removes the fully flat ones, and
the Gate E run shows the floor costs nothing beyond it: 389,949 non-NaN of
398,849 is the 100-bar warm-up and nothing else (§C5). The sentence above is
therefore a statement about windows that BIST does not contain, not about this
universe.

---

## T. Chunking and cost

`CHUNK_VALUES` of 100, 400, 1,024 and the default 524,288: **bit-equal**. At
n = 400,000 the run takes 1.4 s with a traced peak of 27.1 MB (tracemalloc)
and fires 399,900 bars. Wall clock is not quoted as a band because it does not
reproduce.

---

## What a consumer must know

1. **The value can be negative** and "no lag-2 dependence" is ≈ **+0.028** at
   `length` 100, not 0. Do not read the sign as the direction of anything,
   and do not carry that +0.028 to another length: it is +0.228 at `length`
   27 and +0.008 at 250 (§A10b).
2. **It is a bias-corrected ESTIMATE**, in nats, enclosed by
   `[-0.0816, 1.6298]` at `length` 100 — an enclosure, not a measured range
   (the measured one is §C1's) — and those bounds move with `length`,
   because the correction scales as `1/(2(length − 2))`.
3. **It reads shape, not size.** Any positive affine map of the window is
   invisible to it (0 of 467 windows); the ORDER of the returns moves 467 of
   467.
4. **High means "the lag-2 map is one-to-one on the bins"**, which a smooth
   monotone path satisfies as well as a cycle does: the one-kurus-a-bar frame
   reads 1.3432. There is no monotone law in the cycle period (§A3b).
5. **It blanks where the window does not vary** (sd ≤ 9.09e-13) and that
   includes an exactly geometric path, but **not** a deterministically smooth
   one — unlike `c22_periodicity`, which blanks both.
6. **Gate E says SHIP** (run `is127-c22_ami2-23b6686b`, 2026-11-20): nothing
   among the engine's 687 comparators restates this column — the largest is
   0.0594 (`Dist_from_High_252_pct`) pooled and 0.0742 (`natr`) as a per-frame
   median (§E). It fires on 389,949 of 398,849 pooled BIST bars and read
   exactly 0 on none of them (§C5). Still owed: the two unported catch22
   relatives of §E4, which Gate E cannot see.
