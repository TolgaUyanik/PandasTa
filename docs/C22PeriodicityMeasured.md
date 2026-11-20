# `c22_periodicity` — measured

PandasTa issue **#126** (C22-PERIODICITY), ported 2026-11-20 on branch
`issue-126-c22-periodicity`.

⚠ **Round 1 of the pre-push review changed the shipped quantity, and every
number below is re-measured on the new one.** The autocorrelation's divisor
was the biased one — the lagged products over the RESIDUAL's own sum of
squares — attributed to `CO_AutoCorr(y, k, 'Fourier')`. Neither source
spells that line: `PD_PeriodicityWang` writes `acf(i) =
mean(y(1:N-i).*y(i+1:N))` and catch22's C reference divides by
`size - tau`, both on a series catch22 z-scores BEFORE the detrend. The
shipped reading is now that one (§A5), it agrees with the reference
implementation on 2,798 of 2,802 windows where the old one agreed on 2,794
(§P1b), and **the Gate E run of 2026-11-20 is withdrawn with the old
column** (§E).

| | |
|---|---|
| module | `pandas_ta/statistics/c22_periodicity.py` |
| column | `C22PERIODICITY_100` (`ORD`, a whole number in `{0} ∪ {2 .. 33}`) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `PD_PeriodicityWang_th0_01` — the hctsa operation `PD_PeriodicityWang` at threshold 0.01, whose own source is Wang, Wirth and Wang, *Seventh IEEE ICDM* 351–360 (2007); reference code pycatch22 1.x, **GPL-3.0** — ported from the definitions |
| tests | `tests/test_c22_periodicity.py` (268 tests) |
| harness | `docs/measure_c22_periodicity.py` (sections S, A–E, G, H, P, T, Z; **P is opt-in** and is the only one that imports the GPL-3.0 reference), `docs/measure_c22_periodicity_cpu.py` |
| Gate A | correct against an exact rational oracle, two other spellings of the same fit and one independent B-spline implementation, 0 disagreements; the detrend's knot structure and the autocorrelation's divisor decided by measurement against the source line — §A |
| Gate B | causal; 0 of 35 offsets leak on six frames × eight splices, and at three lengths; seven mutants — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames (11–31 distinct values on five of them, the cosine frame constant at 20 by construction, §A3); whole DETERMINISTIC frames blank by the floor (§C3, §G); the real-data limb is **OWED** with Gate E — §C |
| Gate D | ×8/×64/2^±40 bit-identical; `0 < fires < n`; not constant on five of six frames — §D |
| Gate E | **pending, run by issue-solver after this session.** The 2026-11-20 run is withdrawn: it measured the pre-fix autocorrelation — §E |
| Gate F | PandasTa green (268 module tests; full suite below); Backtesting's suite **pending, run by issue-solver** — §F |

Every number below was produced by `python docs/measure_c22_periodicity.py`
on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11) and re-run after
the divisor fix, with four exceptions: the §F suite counts
(`python -m pytest -q`), §F1's no-AVX column
(`docs/measure_c22_periodicity_cpu.py`), the 2026-10-24 screen figures,
which are the owner's PROTOTYPE measurements, and the withdrawn Gate E run's
figures in §E1, §E2 and §C4, which were measured by the launcher on the
PRE-FIX column. The last two kinds are labelled wherever they appear and are
expectations, not results for the shipped column.

---

## 0. What the column is

```
r[t]   = close[t] / close[t-1] - 1
X      = r[T-99 .. T]                        (the 100 returns ending at T)
V      = var(X, ddof=1)                      (BEFORE the detrend: catch22
                                              z-scores, so every acf below
                                              is in z-scored units)
S      = the least-squares CUBIC spline on two pieces, one interior knot at
         the middle of the window, fitted to X
Y      = X - S                               (the detrended window)
D      = Y - mean(Y)
acf(k) = sum(D[:-k] * D[k:]) / ((100 - k) * V),  k = 1 .. ceil(100/3) = 34
C22PERIODICITY = the first lag tau in 2 .. 33 with
                 (a) a strict local minimum of acf at some lag below tau,
                 (b) acf(tau) - acf(that minimum) >= 0.01,
                 (c) acf(tau) >= 0, and acf(tau) a strict local maximum;
                 else 0
```

**0 is a SENTINEL and it is also the FLOOR of the scale.** It means "no peak
passed the three conditions", not "a period of zero" and not "a short
period". The column is tagged `ORD`: it is a lag in bars, it ties on 79.4% to
100% of neighbouring bar pairs, and a consumer must feed it as an ordinal or
one-hot rather than as a magnitude.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository tests
it on BIST: the feature's presence here is existence, not evidence. The issue
says so and this receipt repeats it.

The reference implementation is GPL-3.0 and this fork is MIT. The port was
written from the definitions — the paper's feature name, the hctsa operation
it names (`PD_PeriodicityWang`: `spap2(2, 4, 1:N, y)` for the detrend and
`acf(i) = mean(y(1:N-i).*y(i+1:N))` for the autocorrelations, which that
operation spells inline rather than delegating to `CO_AutoCorr`), catch22's
own `acf[tau-1] /= size - tau` and its z-score of the series before the
detrend, and Wang et al.'s own description of the measure. No shipped module
imports the reference: the
test `test_the_reference_implementation_is_not_imported_by_shipped_code`
sweeps every `.py` file under `pandas_ta/` (397 on this tree) for an import
statement mentioning it and finds none. ⚠ pycatch22 **is installed in this
worktree**, so that guard is not vacuous.

The one place the reference is run is `docs/measure_c22_periodicity.py`
section **P**, which is opt-in (a bare run skips it and does not import it)
and is MEASUREMENT only — the same use the owner's own screen prototype makes
of it (`docs/issues/screen/ind_screen_r3.py`: "it is used here only to
MEASURE, on the owner's machine"). It answers two questions the definitions
cannot, and the answers are in §P: which reading of the spline the reference
implements, and whether this port is the column the 2026-10-24 screen's
Gate E numbers were measured on. ⚠ **It is not** — 8,387 of 8,400, not
8,400 of 8,400.

## A. Gate A — correctness

### A1. The spline basis is a choice of SPANNING SET, not of model

The shipped fit is a projection onto the QR factor of the truncated power
basis `1, t, t², t³, (t - ½)³₊` on `t = 0 .. 1`, which spans exactly the
twice-differentiable piecewise cubics with one break at the middle — the
function space a cubic regression spline on two pieces fits. Three other
spellings of the SAME space, every 7th window of each frame (200 per frame,
1,200 each):

| frame | `np.linalg.lstsq` | normal equations | `scipy` B-spline |
|---|---|---|---|
| walk | 0 moved, rel 2.3e-14 | 0 moved, rel 8.7e-13 | 0 moved, rel 1.7e-14 |
| tick-rounded | 0, 1.8e-14 | 0, 5.1e-13 | 0, 1.1e-14 |
| penny | 0, 2.2e-14 | 0, 6.3e-13 | 0, 1.5e-14 |
| ar1 | 0, 4.1e-14 | 0, 1.3e-12 | 0, 2.5e-14 |
| cosine | 0, 2.1e-14 | 0, 7.1e-13 | 0, 1.3e-14 |
| student-t | 0, 1.3e-14 | 0, 4.9e-13 | 0, 8.8e-15 |

`rel` is the worst residual difference as a fraction of the residual's own
largest value. `scipy.interpolate.LSQUnivariateSpline(x, y, t=[(n-1)/2], k=3)`
is an independent implementation in a B-SPLINE basis — the basis hctsa's
`spap2` uses — so this row is the one that says the space was read correctly
and not merely spelled consistently.

### A2. The exact rational oracle — zero roundings

Every input double is an exact rational; so are the basis functions on the
window's grid. The normal equations, their solution, the fitted values, the
residual, its mean, the autocorrelations and all three of Wang's conditions
(including the 0.01, which is `Fraction(1, 100)`) are therefore decidable
exactly. The z-score's `sd` is irrational and is never needed: the quantity
divides by `(n - k) * var`, and `var` is a rational, so the square root
cancels. Nothing in the oracle rounds. Every 13th window of all six frames —
**648 windows**, 14.3 s:

| frame | agree | disagree |
|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 108 / 108 each | **0** |

### A3. The cosine law, and the ceiling where it stops

Returns that are an exact cosine of period P:

| P | 8 | 10 | 12 | 15 | 20 | 25 | 30 | 33 | 34 | 40 | 60 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| values read | 8 | 10 | 12 | 15 | 20 | 25 | 30 | 0, 32, 33 | 0 | 0 | 0 |
| constant? | yes | yes | yes | yes | yes | yes | yes | no | yes | yes | yes |

**Exactly P, on every one of 1,400 fired bars, at each of the seven periods
measured — P = 8, 10, 12, 15, 20, 25 and 30.** That is the
law that says the column reads a PERIOD and not an index into something. It
frays only where the peak reaches the last testable lag — three values at
P = 33, median 33 — and past the ceiling `ceil(length / 3) - 1` = 33 it goes
silent rather than wrong: at P = 34, 40 and 60 **every** fired bar reads the
sentinel. **A cycle much longer than a third of the window cannot be
reported by this feature, by construction.**
(Under the pre-fix biased divisor P = 30 read 29 or 30 and P = 34 read 0 or
33; the source spelling is the cleaner of the two here, which is a result
and not a reason — §P1b is the reason.)

### A4. Z-scoring the window changes nothing

catch22 z-scores its input before computing a feature, and so does this
module (§A5) — so z-scoring the INPUT must be inert, and is: the
least-squares fit is equivariant under an affine map (the constant function
is in its span) and every autocorrelation is divided by the window's OWN
variance, so any affine map of it cancels in exact arithmetic whatever
`ddof` the caller used.
Measured on 200 windows per frame: **0 of 1,200** moved. A caller handing
this column pre-normalised returns therefore gets the same values. The same
holds for the reference, 61 of 61 windows (§P2) — which is why §P can
compare raw-return windows against a library that z-scores internally.

### A5. The autocorrelation spelling — the divisor the sources PIN

`PD_PeriodicityWang` does not delegate to `CO_AutoCorr`: it spells the line
inline as `acf(i) = mean(y(1:N-i).*y(i+1:N))`, and catch22's C reference
divides the same products by `size - tau`. That is the ADJUSTED divisor, and
what makes those averages dimensionless — so that condition (b)'s ABSOLUTE
0.01 means anything at all — is that catch22 z-scores the series BEFORE the
detrend. The shipped divisor is therefore `(n - k) * var(window)`, with
`var` taken on the window and not on the residual.

⚠ **Until review round 1 of 2026-11-20 this module divided by the residual's
own sum of squares** (the biased autocorrelation of the residual) and
attributed that to `CO_AutoCorr(y, k, 'Fourier')`. That attribution was
wrong: it is not the line either source writes, and the deviation is two
multiplicative factors — the lag-dependent taper `(n - 1) / (n - k)`, which
is 1.00 at lag 1 and 1.48 at lag 33, and the per-window ratio
`resid_ss / window_ss`, which is at most 1 because the spline's span holds
the constant function (§C3). Both are visible to an ABSOLUTE threshold.
What they cost, over 467 windows of each frame:

| frame | biased divisor: moved | Spearman | `n - k` but normalised on the residual |
|---|---|---|---|
| walk | 0 | +1.0000 | 0 |
| tick-rounded | **1** | +0.9918 | 1 |
| penny | 0 | +1.0000 | 0 |
| ar1 | **4** | +0.9832 | 3 |
| cosine | 0 | (constant) | 0 |
| student-t | **1** | +0.9996 | 0 |

Small — 6 bars of 2,802 — and §P1b is where it is decided rather than here:
the shipped reading agrees with the reference implementation on **2,798 of
2,802** windows and the biased one on **2,794**.

Two conventions the source line does NOT fix, plus the order it is written
in, measured rather than argued. Each moves **0 bars of 467 on every one of
the six frames**, and each scores the same 2,798 of 2,802 against the
reference (§P1b):

| convention | shipped | the alternative | moved |
|---|---|---|---|
| the z-score's divisor | `ZSCORE_DDOF = 1` (MATLAB `zscore`'s, so hctsa's) | the population `ddof = 0`, every acf × 1.0101 | 0 |
| the residual's mean | subtracted (that is what an autocorrelation IS) | not subtracted, as the source line writes it | 0 |
| the spelling | one division by `var` at the end | divide the series by `sd` first, project again | 0 |

The last row is the literal source order and it is the module's own
conditioning check: the two are the same quantity rounded differently, and
nothing in 2,802 windows can tell them apart.

### A5b. The DETREND is load-bearing, and its knot structure is not a taste

Over 467 windows of each frame, against the shipped two-piece cubic:

| frame | no detrend | a straight line | one cubic, no knot | knot at ⅓ | three pieces |
|---|---|---|---|---|---|
| walk | 62 moved, ρ +0.810 | 53, +0.822 | 19, +0.951 | 12, +0.973 | 31, +0.888 |
| tick-rounded | 52, +0.852 | 41, +0.872 | 20, +0.931 | 16, +0.950 | 26, +0.905 |
| penny | 93, +0.773 | 71, +0.826 | 30, +0.916 | 17, +0.954 | 31, +0.927 |
| ar1 | **202**, +0.485 | 175, +0.492 | 105, +0.710 | 69, +0.805 | 110, +0.736 |
| cosine | 0, (constant) | 0 | 0 | 0 | 0 |
| student-t | 65, +0.837 | 58, +0.849 | 22, +0.947 | 17, +0.963 | 26, +0.925 |

So the spline is the step that makes this column what it is, and a later
"simplification" of it would change shipped values on up to 202 bars in 467.
Which of the five is right is settled by §P1b, not by taste.

### A6. The 0.01 threshold is load-bearing

| frame | th = 0 | th = 0.1 |
|---|---|---|
| walk | 5 moved of 467 | 41 |
| tick-rounded | 5 | 54 |
| penny | 0 | **90** |
| ar1 | 15 | 60 |
| cosine | 0 | 0 |
| student-t | 1 | 38 |

### A6b. Wang's other two conditions, ablated

Conditions (a) "a trough before it" and (c) "a non-negative peak" are the two
the scan's bookkeeping could most easily get wrong, so each is dropped and
the column re-read over 467 windows per frame:

| frame | no trough required | a negative peak allowed |
|---|---|---|
| walk | 167 moved | 117 |
| tick-rounded | 124 | 116 |
| penny | 136 | 190 |
| ar1 | **0** | **316** |
| cosine | 0 | 0 |
| student-t | 190 | 106 |

Both conditions are load-bearing, and the two zeros are findings rather than
gaps: on the AR(1) frame the autocorrelation always has a strict local
minimum before the lag the column reports, so condition (a) costs nothing
there, and the cosine frame's single clean peak satisfies every condition
with room to spare. The tests assert the four frames where (a) bites and
name the AR(1) zero separately.

### A7. Strictness, and `ceil` against `floor`

| frame | `<=` instead of `<` | `floor(n/3)` instead of `ceil` |
|---|---|---|
| walk, tick-rounded, penny, cosine, student-t | 0 moved of 467 | 0 |
| ar1 | 0 | **1** |

⚠ The `floor` column is the one figure in this receipt that would be
misleading on its own: it moves 1 bar in 467 on a realistic frame, and it
moves the TOP OF THE SCALE. Under `floor` the largest reportable period at
`length` 100 is 32, not 33, so the documented range `{0} ∪ {2 .. 33}` and
the cosine law at P = 33 both break.
`test_the_lag_ceiling_is_a_ceil_and_its_top_lag_is_reachable` pins that with
two limbs a `floor` spelling cannot satisfy — an exact 33-bar cosine reading
33, and a 16-bar cosine at `length` 50 reading 16.

The strictness is kept because that is what a local extremum means, and on
this sample the difference is unreached rather than cosmetic — see §A8 for
what that does and does not cover.

### A8. Exact ties in the comparisons the scan makes

**0 exactly flat slopes** in 15,411 sampled lag pairs on each of the six
frames, and **0** windows where a peak stands exactly `TH` above the trough
before it. So nothing the scan decided HERE was decided by a tie, which is
why `<=` for `<` moved nothing (§A7) and why the margins in §D5 are what
they are. ⚠ That is six SYNTHETIC frames; real BIST windows — where a fifth
of the returns can be exactly 0.00% — are unmeasured in this receipt (§C4),
so "no ties" is a result about this sample and not a property of the
column.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a different
path, and no bar before J may move. 35 offsets per frame, **eight** different
futures at each:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 35** each |
| walk at `length` 30, 120, 250 (four splices) | **0 / 35** each |

### B2. Six mutants, read off this module's source, edited and exec'd in memory

| mutant | edit | walk | tick-rounded | cosine |
|---|---|---|---|---|
| `write-back-dated` | `out[length + a:...]` → `out[length - 1 + a:...]` | 8 / 35 | 8 / 35 | 0 / 35 |
| `window-one-ahead` | the window takes one more future return | 8 / 35 | 8 / 35 | 0 / 35 |
| `window-ten-ahead` | ten more | **33 / 35** | **33 / 35** | **35 / 35** |
| `returns-rolled` | the return series shifted one bar earlier | 8 / 35 | 8 / 35 | 0 / 35 |
| `mask-back-dated` | the bad-data mask reads the next bar | dead on a clean frame — see B3 |
| `chunk-wide-demean` | the residual demeaned by the whole chunk's mean | 0 / 35, and bit-equal to the real module on all three frames |

(A seventh, `no-overflow-guard`, is read off the same source in §H1b.)

**The counts below 35 are a finding, not a defect, and they are the reason
mutants are here at all.** A one-bar back-dating can only be seen on a bar
whose value differs from its neighbour's, and this column ties on 88.7%
(walk), 86.4% (tick-rounded) and 100% (cosine, a constant column) of
neighbouring pairs. On the cosine frame the three one-bar mutants are caught
on **0** of 35 offsets: a catch needs a PRE-SPLICE bar to move, and a
one-bar look-ahead pulls exactly one spliced return into bar J − 1's window,
which still reads 20 — while a ten-bar one pulls ten and does not, so the
ten-bar mutant IS caught there, 35 of 35. (On the clean frame those three
mutants differ from the real module on 0 of 1,500 bars on the cosine frame,
against 158 on the walk and 190 on the tick-rounded one.) Prefix truncation
would have proved less than any of this.

`chunk-wide-demean` is near-DEAD and that is measured rather than excused: it
IS a read of other rows, but both means are ~1e-18 (see §A5), so subtracting
the wrong one changes nothing. It is counted among the six rather than
quietly dropped.

### B2b. Where a one-bar mutant moves anything, it moves exactly bar J − 1

Over 35 offsets of the walk with one splice each, **2** offsets move a
pre-splice bar and on **2 of 2** the first moved bar is J − 1.

### B3. The mask mutant

On a clean walk it is **bit-equal** on all 1,500 bars — invisible, not merely
weak. On a frame with one bad close it is caught at **12 of 12** offsets, and
the bar it moves is exactly **J − 1** every time.

### B4. Tie density

| frame | walk | tick-rounded | penny | ar1 | cosine | student-t |
|---|---|---|---|---|---|---|
| neighbouring pairs equal | 88.7% | 86.4% | 86.2% | 79.4% | 100% | 89.6% |

## C. Gate C — reachability

### C1. Synthetic frames (1,500 bars each)

| frame | fired | distinct | range | median | zeros | first bar |
|---|---|---|---|---|---|---|
| walk | 1,400 / 1,500 | 13 | 3 .. 16 | 5 | 0 | 100 |
| tick-rounded | 1,400 | 13 | 3 .. 15 | 5 | 0 | 100 |
| penny | 1,400 | 15 | 3 .. 20 | 5 | 0 | 100 |
| ar1 | 1,400 | 31 | 0 .. 33 | 14 | **10 (0.7%)** | 100 |
| cosine (P = 20) | 1,400 | **1** (constant 20) | 20 .. 20 | 20 | 0 | 100 |
| student-t | 1,400 | 11 | 3 .. 13 | 5 | 0 | 100 |

Every bar with a full window fires. The walk's distribution is
`{3: 258, 4: 193, 5: 273, 6: 268, 7: 237, 8: 13, 9: 127, 11: 3, 12: 13,
13: 2, 14: 10, 15: 1, 16: 2}` — i.e. on a near-iid return window the first
qualifying peak of the autocorrelation lands where the sampling noise of the
autocorrelation puts it, between lags 3 and 9 on 98% of bars. The AR(1)
frame, whose returns have real structure, is the one that spreads out
(median 14, range 0 .. 33).

⚠ **The sentinel is rare**: 0 of the 5,600 bars of the four non-AR
stochastic frames, 10 of 1,400 on the AR(1) one. A consumer cannot learn what
0 means from the data, which is why §0 and the docstring lead with it.

### C2. The issue's own worry: BIST tick rounding

| path | zero returns | fired | distinct | median |
|---|---|---|---|---|
| 2-lira stock on a 1-kurus tick (`penny`) | **21.7%** | 1,400 | 15 | 5 |
| 100-lira walk rounded to the kurus | 0.3% | 1,400 | 13 | 5 |
| 100-lira walk, unrounded | 0.0% | 1,400 | 13 | 5 |

Three different paths (seeds 23 / 55 / 11), not one at three price levels.
A fifth of the returns being exactly 0.00% does not blank a window and does
not move the column's shape: same median, same order of distinct values, all
1,400 bars fired.

⚠ What this does NOT settle is Gate E's question, which is **owed again**:
the run of 2026-11-20 answered it for the PRE-FIX column and is withdrawn
with it (§E). What that run found, on a column that agreed with this one on
2,796 of 2,802 sampled windows, was the issue's tell PRESENT and tiny:
`cdl_doji` leading pooled at 0.0415, two price levels at 0.0392, price
levels taking the top three per-frame medians with `EMA_200` largest at
0.0950, no volume column in the pooled top 25 and `mcgd` ninth at 0.0314.
That is an EXPECTATION for the re-run, not a result for this column.

### C3. What the one blanking rule costs

| input | fired | why |
|---|---|---|
| 400-bar walk then 300 flat closes | 399 of 700, last live bar **498** | bar 499 is the first whose whole window of returns is zero; bar 498's window still holds the one non-zero return |
| exact geometric ladder, step +1% / +0.1% / −0.5% | **0** of 1,400 | 3 to 5 distinct returns per window, window sd 1.2e-16 .. 1.5e-16, under the 9.09e-13 floor. Unguarded it fires all 1,400 and reads inside [3, 11] (§G, all 1,400 windows of the +1% step; this section's own figure is a stride-29 sample of them, 4 .. 10 / 4 .. 9 / 4 .. 8 for the three steps on this dispatch) |
| returns that ARE a cubic in the bar index | **0** of 1,400 | the window varies (sd 2.81e-05 .. 1.15e-03) but the spline fits it to a residual rms of 7.7e-17 .. 1.4e-16. Unguarded: 1,400 bars, **every one reading the SENTINEL 0** — a legal value of this column, and a claim that a window of pure fit rounding has no periodicity rather than nothing to read (§G) |

The floor is applied to the DETRENDED window and that is one rule doing two
jobs rather than a looser rule: the spline's span contains the constant
function, so the residual's sum of squares never exceeds the window's
deviations from its mean — measured on **9,800 rows** (the six frames plus
the cubic one), **0** break it. A residual above the floor therefore implies
a window above it.

### C4. Real data — **OWED**

Everything in this receipt is measured on SYNTHETIC frames. The two counts
this section needs — how many of the 89 frozen ALTPORT-1 BIST frames'
**398,849** pooled bars are non-NaN, and how many of those are non-zero —
come from the launcher's Gate E run, which is **owed again** (§E) because the
2026-11-20 run measured the pre-fix autocorrelation.

What that withdrawn run found, on a column that agrees with this one on
2,796 of 2,802 sampled windows, is kept here as the EXPECTATION for the
re-run and labelled as the pre-fix column's:

| count (**PRE-FIX column, withdrawn**) | value | share |
|---|---|---|
| `C22PERIODICITY_100` non-NaN | 389,949 of 398,849 | 97.77% |
| of those, non-zero | 389,928 of 389,949 | 99.995% |
| the sentinel 0 | 21 of 389,949 | 0.0054% |

The blank 8,900 bars were the warm-up — 89 frames × 100 bars, exactly the
`length` returns the window needs — so on that column no BIST frame lost a
bar to the noise floor of §G or to the bad-data guards of §H, and the
sentinel was rarer on BIST (0.0054%) than on any synthetic frame here (0.0%
to 0.7%, §C1). Whether both still hold for the shipped column is what the
re-run settles.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64, ×2^−40, ×2^40) | 24 of 24 **bit-identical** |
| walk at `length` 30 / 120 / 250 × (×8, ×64) | 6 of 6 **bit-identical** |
| price levels 1e−6 / 1e+6 / 1e+100, ×8 | 3 of 3 bit-identical, 1,400 bars fired at each |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`.

### D2. Inexact rescales

| frame | ×10 | ×3.7 | ×0.1 | ×1.0000001 |
|---|---|---|---|---|
| all six | 0 bars, 0 mask | 0 | 0 | 0 |

Not promised by the arithmetic — the output is an integer decided by float
comparisons — and the tests bound it (≤ 5 bars) rather than pinning 0.

### D3. Blind to amplitude, not to order

| probe | walk | ar1 |
|---|---|---|
| the window's returns × 0.5 / × 2 / × 10 | 0 of 467 moved each | 0 each |
| the same returns in a different ORDER | **401** of 467 | **446** of 467 |

A correlation cannot see a rescale of both limbs and a least-squares fit is
equivariant under one, so the bit-identity in D1 is not vacuous — the column
reads the SHAPE of the return sequence.

### D4. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on all six frames; 11 to 31 distinct values on five of
them. The cosine frame is constant at 20 **by construction** (§A3), which is
the feature working rather than a dead column, and the tests name it rather
than averaging it away.

### D5. How close the deciding comparisons run to a rounding flip

Over the 465 to 467 windows per frame where the column reports a lag (the
sentinel rows have no peak to measure, which is the two missing AR(1) rows):

| frame | walk | tick-rounded | penny | ar1 | cosine | student-t |
|---|---|---|---|---|---|---|
| min slope at the peak | 4.96e-04 | 2.51e-04 | 5.87e-04 | **7.10e-05** | 4.12e-02 | 9.40e-05 |
| min \|peak − trough − TH\| | 1.13e-03 | **2.63e-05** | 2.93e-03 | 1.10e-03 | 1.79e+00 | 8.24e-03 |

Eleven orders of magnitude above a last-bit question, which is why D2 comes
out clean and why no test pins a ρ to 1e-6. ⚠ The smallest cell, the
tick-rounded frame's 2.63e-05, is the deciding margin of one of the four
windows where this port and the reference disagree (§P1b) — a marginal
window, which is a different claim from a precision problem.

## E. Gate E — **pending**

**Gate E: pending, run by issue-solver after this session.**

It was run once, on 2026-11-20, and that run is **WITHDRAWN**: review round 1
corrected the autocorrelation's divisor (§A5), so the run's module sha1
(`cea7fab8e7f28c910006a5ced3e126a48c042f5e`), tree sha1
(`e9379ea2d992902cee5ee7bf649094b292e2a8e0`) and output fingerprint
(`500;2758.0;16516.0;1000142.0`) all belong to a column this tree no longer
computes. Its ledger row was recorded and has been **removed** —
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails until the launcher re-runs Gate E and a receipt session records the new
row, and that failure is expected (`GATE_E_PENDING_OK=1` makes it a "Gate E
owed" skip on the way to `dev`).

| | |
|---|---|
| universe (unchanged) | the 89 frozen ALTPORT-1 BIST frames, **398,849** pooled bars |
| comparators (unchanged) | **687** — 329 `compute_all` and 358 `ml_features` manifest `1d`; 1 dropped as degenerate (`squeeze_SQZ_NO`, constant) |
| parameters | defaults (`kwargs` empty, so `length` 100) |
| bands | `r3-perframe-0.90` — STRUCK at pooled \|ρ\| ≥ 0.90 or a top-5 comparator's per-frame median ≥ 0.90, DISCLOSE from 0.76, SHIP below |

### E1. What the WITHDRAWN run found, as the expectation for the re-run

⚠ Every figure in this subsection was measured on the PRE-FIX column
(run `is126-c22_periodicity-c73140e9`, canary bit-equal, 2026-11-20). That
column agrees with the shipped one on 2,796 of 2,802 sampled windows (§A5),
so these are a well-founded EXPECTATION and not a result for
`C22PERIODICITY_100` as it now stands.

| column (**PRE-FIX, withdrawn**) | max \|ρ\| | against | set | n | per-frame max median | its comparator | frames ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|---|
| `C22PERIODICITY_100` | 0.041467817149024776 | `cdl_doji` | `compute_all` | 389,949 | 0.09503141020334058 | `EMA_200` | 0 of 89 | SHIP |

The strongest manifest comparator was weaker than the strongest
`compute_all` one: max |ρ| 0.0239 vs `pdist_pct` (n = 389,949). The pooled
top three and the five comparators that run carried to the per-frame stage:

| comparator | pooled \|ρ\| | n | per-frame median | per-frame max cell |
|---|---|---|---|---|
| `cdl_doji` | 0.0415 | 389,949 | 0.0365 | 0.1937 |
| `BODY_PCT` | 0.0392 | 388,703 | 0.0396 | 0.1727 |
| `ROLLING_LOW_250` | 0.0392 | 376,599 | 0.0797 | 0.3851 |
| `ROLLING_HIGH_250` | 0.0372 | 376,599 | 0.0926 | 0.4216 |
| `EMA_200` | 0.0364 | 381,138 | 0.0950 | 0.4335 |

Read with §C2: the two comparators that led pooled are the SAME tell —
`cdl_doji` flags a zero body and `BODY_PCT` is the body's share of the bar's
range, so both read how small the body is, which on a low-priced BIST stock
is tick rounding — and the price levels the issue named led the per-frame
medians. The ranking was therefore the shape the issue warned about, and the
magnitude is what decided it: 0.0950 against a 0.90 strike and a 0.76
disclose line. The largest single per-frame CELL over the five was 0.4335,
on one frame of 89, and 0 of 89 frames reached 0.90 against any of them.
`mcgd` — the issue's other named tell — was ninth at 0.0314, and no volume
column appeared in the pooled top 25.

⚠ **This is existence, not evidence**, and now also an expectation rather
than a measurement. A pooled 0.04 says the column is not a restatement of
anything the engine already computes; it says nothing about whether it
predicts a BIST return. Nothing in this repository tests that.

### E2. The withdrawn figure against the screen PROTOTYPE's

| | pooled max \|ρ\| | against | n | top-5 per-frame max median |
|---|---|---|---|---|
| the PRE-FIX port, 2026-11-20 (withdrawn) | 0.0415 | `cdl_doji` | 389,949 | 0.0950 (`EMA_200`) |
| the 2026-10-24 PROTOTYPE | 0.0413 | `cdl_doji` | 389,949 | 0.0941 |

The prototype IS the GPL-3.0 reference's column, and the SHIPPED port is
**not bit-identical to it**: 8,387 of 8,400 sampled windows read the same
value, Spearman +0.9993 (§P1) — closer than the pre-fix column's 8,376 and
+0.9980, which is the measurement that decided the fix. The two runs above
agreeing to three decimals on the same top comparator is a RESULT and not a
tautology. The prototype's next two, `ROLLING_LOW_250` 0.0392 and
`BODY_PCT` 0.0391, were the withdrawn run's third and second at 0.0392 each:
the pair swapped order inside a gap of 1e-4.

The owner's stage-2 fork overlap (12 frames, scale-free `Category` outputs at
defaults, NOT Gate E) put the prototype at max |ρ| 0.0834 vs
`ht_dcperiod:HT_DCPERIOD`, per-frame max median 0.0879. `HT_DCPERIOD` was not
in the withdrawn run's top 25.

### E3. In-fork overlap, measured here (6 synthetic frames, 1,500 bars each)

Gate E's 687 comparators are the engine's `compute_all` and the `ml_features`
manifest, so this fork's own shape and cycle columns are mostly not in it.
Measured against **18** of them, pooled and per frame — all 18 tabulated,
because a top-N cut here would read as "these are the ones that matter" when
the ranking is by the pooled figure the section goes on to disown:

| comparator | pooled ρ | n | per-frame median \|ρ\| | per-frame max \|ρ\| |
|---|---|---|---|---|
| `TFDFA_100` | +0.6667 | 8,400 | 0.1581 | 0.2386 |
| `TFSPECENT_64` | −0.6405 | 8,400 | 0.0466 | 0.1501 |
| `TS_AC1_60` | +0.6223 | 8,400 | 0.1527 | 0.2559 |
| `TS_CID_CE_20` | −0.6037 | 8,400 | 0.0127 | 0.0639 |
| `TS_PERMENT_20_3` | −0.5486 | 8,400 | 0.0309 | 0.1327 |
| `DIFF2ACF1_100` | +0.5278 | 8,400 | 0.3219 | 0.4233 |
| `C22AMITIMESCALE_100` | +0.5081 | 8,400 | 0.1902 | **0.5175** |
| `FIRSTZEROAC_100` | +0.4303 | 8,400 | 0.1505 | 0.2137 |
| `TS_BINENT_20_5` | +0.4078 | 8,400 | 0.0303 | 0.0829 |
| `TFAUTOCORR1E_60` | −0.3288 | 8,400 | 0.0818 | 0.1324 |
| `TS_AGGAC_60_10` | −0.2270 | 8,400 | 0.1422 | 0.1484 |
| `LEAN_HURST_100_20` | +0.1703 | **7,000** | 0.1298 | 0.2824 |
| `ENTLZ_20` | +0.0644 | 8,400 | 0.0929 | 0.1303 |
| `HLIFE_100` | +0.0612 | **7,906** | 0.1478 | 0.1950 |
| `HT_DCPERIOD` | −0.0286 | 8,400 | 0.0839 | 0.1517 |
| `SEAS_21_1` | −0.0190 | **7,488** | 0.0327 | 0.0761 |
| `TS_C3_20_1` | −0.0023 | 8,400 | 0.0581 | 0.1895 |
| `TFCENTROID_20` | −0.0003 | 8,400 | 0.0372 | 0.0725 |

`n` is the bars where both columns are present, so three rows are smaller
than the rest: those comparators carry their own blanks.

⚠ **The pooled column is the misleading one and is printed only because
leaving it out would look like hiding it.** Pooling six frames with different
medians measures between-frame differences, not co-movement: the per-frame
cells behind `TFDFA_100`'s +0.6667 are 0.239, 0.125, 0.158, 0.191, nan (the
constant cosine frame) and 0.036. **The largest single per-frame |ρ| over all
18 × 6 cells is 0.5175** (`C22AMITIMESCALE_100`, the sibling catch22 port, on
the AR(1) frame), under the 0.76 ship line, and the highest per-frame median
is 0.3219. `HT_DCPERIOD` — the owner's stage-2 top comparator for the
prototype — sits at a per-frame median of 0.0839 here.

### E4. **OWED RULE** — two catch22 relatives that are not in this tree

`CO_FirstMin_ac` (issue **#130**, candidate `c22_acf_first_min`) and
`SP_Summaries_fft_wq_50` (issue **#137**, `c22_median_freq`) read the SAME
100 returns' autocorrelation and spectrum. Neither exists in this tree, so
neither Gate E's run nor §E3 can see them. Measured here as PROXIES — a
plausible spelling of each, written in the harness, **not** its port, so
these are an advance warning and not a measurement of #130 or #137:

| proxy | walk | tick-rounded | penny | ar1 | cosine | student-t | pooled |
|---|---|---|---|---|---|---|---|
| #130, first minimum of the return ACF | 0.559 | 0.497 | 0.528 | 0.582 | nan | 0.578 | 0.807 |
| #137, median frequency of the return spectrum | 0.124 | 0.046 | 0.004 | 0.310 | nan | 0.209 | 0.626 |

**The rule:** when #130 or #137 is ported, measure its column against
`C22PERIODICITY_100` over the 89 ALTPORT-1 frames, read the result against
`r3-perframe-0.90`, and if a pair is STRUCK, one of the two is reverted or
waived. A test asserts this receipt keeps naming both issues.

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest tests/test_c22_periodicity.py -q` | **261 passed** at the port's final state, **262 passed** in the receipt session, **268 passed** after the divisor fix of 2026-11-20 |
| the same module under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_periodicity_cpu.py`, which refuses to run if the environment edit did not take) | **261 passed**, **262 passed** in the receipt session, **268 passed** after the divisor fix |
| `python docs/measure_c22_periodicity_cpu.py A C D` and `… G` — sections A, C, D and G re-measured under the same disabled dispatch | ran clean; what moved is in §F1 |
| `python -m pytest -q` (full suite), at the port's first complete state | **2 failed, 13,219 passed, 86 skipped** |
| the same after review round 1 added three tests | **3 failed, 13,222 passed, 86 skipped** |
| `python -m pytest tests/test_pine_coverage_csv.py -q` after fixing that third failure | **38 passed, 1 skipped** |
| `python -m pytest -q` again, on the final tree (9 min 18 s) | **2 failed, 13,223 passed, 86 skipped** |
| `python -m pytest -q --tb=no -p no:warnings -rf` on the committed tree, after the divisor fix (8 min 36 s) | **2 failed, 13,230 passed, 86 skipped** — the failures named by `-rf` being exactly the two expected ones below |

The two expected failures are
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout; CI deselects it by name)
and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reporting exactly `['c22_periodicity']` — the owed measurement of §E, which
CI into `dev` reports as "Gate E owed" rather than a failure.

⚠ The **third** failure in the second run was this port's own, and it is worth
recording rather than hiding: `01-c22-periodicity.md` quotes a reviewer
verbatim, the quote contained five slash-joined counts, and
`tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
reads any such run of five numbers anywhere in the fork as a retyped PINEBI
verdict split. Spacing the numbers inside the quote fixes it; the third row
above is that module re-run and the fourth is the whole suite again on the
final tree, back to the two expected failures and nothing else. The round-1
heading in the review log says what was changed and why.
Backtesting's suite is run by issue-solver in a clean worktree.

### F1. What moves under the CI CPU dispatch

With `AVX512F AVX512_SKX AVX2 FMA3` disabled (still enabled: SSSE3, SSE41,
POPCNT, SSE42, AVX, F16C, AVX512CD, AVX512_CLX, AVX512_CNL, AVX512_ICL), the
test module passes — **268 passed** — and sections **A, C, D and G were
re-run in full** rather than assumed, after the divisor fix as well as
before. Two groups of figures move, both of them rounding:

| figure | default dispatch | AVX-512 / AVX2 / FMA3 off |
|---|---|---|
| §A1 worst relative residual difference, `lstsq` / normal / `scipy`, over all six frames | 1.31e-14 .. 4.11e-14 / 4.93e-13 .. 1.30e-12 / 8.82e-15 .. 2.47e-14 | 1.35e-14 .. 4.29e-14 / 4.93e-13 .. 1.30e-12 / 1.04e-14 .. 2.79e-14 |
| §C3 the geometric ladder's rounding: distinct returns per window at step +1%, and the window sd range over the three steps | 4, 1.19e-16 .. 1.51e-16 | 3, 1.25e-16 .. 1.44e-16 |

The second row is the frame built out of rounding noise, so its noise moving
is the expected result rather than a surprise; the tests bound it (≤ 6
distinct returns, unguarded values inside [2, 33]) instead of pinning it.
⚠ §C3's third figure — the values the unguarded spelling reads, printed for
the three steps as "4 .. 10 / 4 .. 9 / 4 .. 8" by default and
"3 .. 9 / 3 .. 10 / 3 .. 8" with the dispatch off — mixes two effects and is
therefore not in the table: §C3 samples every 29th window where §G
enumerates all 1,400, and the full set moves too (the ladder reads
`{3 .. 10}` by default and `{3 .. 11}` with the dispatch off). Both documents
therefore state that frame as a SPAN — [3, 11] — which holds under both
dispatches, and the tests bound it rather than pinning it. The cubic frame
needs no span any more: it reads the sentinel 0 on all 1,400 windows under
both dispatches.

Everything else is identical, digit for digit: the exact oracle's 648
agreements, every `0 moved` cell in §A1 / §A4 / §A5 / §A7, the whole
divisor table of §A5 (including the 6 bars the biased reading moves), the
whole detrend table of §A5b, §A3's cosine table, §A6's threshold counts,
§A6b's two ablations, §A8's 0 flat slopes in 15,411 lag
pairs, every fired-bar / distinct-value / zero count and the walk's whole
value distribution in §C1, §C2's three paths, §C3's 399-of-700 flat-run
count and 0-of-9,800 residual check, the 24 bit-identities of §D1, the
0-bars-moved rows of §D2 and §D3, all twelve of §D5's margins, and every
row of §G but the ladder's. The tests nevertheless pin bounds and bands
rather than digits for the figures that *could* move.

## G. The floor, and what it buys

`NOISE_FLOOR = 4096 * eps = 9.095e-13`, on the root mean square of the
DETRENDED window. An ABSOLUTE constant, because what it bounds is a
dimensionless RETURN with no rolling scale of its own to keep causal — the
same habit as `c22_ami_timescale`, `tf_autocorr_1e_60`, `ts_binent_20`,
`ts_strike_20`, `ts_c3_20`.

| input | guarded (shipped) | unguarded | `c22_ami_timescale` |
|---|---|---|---|
| six realistic frames | 1,400 fire each | **0 bars differ** | — |
| price flat at 1e6 except ONE 1-ulp step | 0 fire | 100 fire, reading 0 and every value from 16 to 33 | 0 fire |
| one 1-kurus tick per bar at 1e6 | 0 fire | 1,400 fire, all reading 0 | 0 fire |
| one 1-kurus tick per bar at 1e9 | 0 fire | 0 fire (the window's returns are one double, so there is no z-score to take) | 0 fire |
| **one 1-kurus tick per bar at 100** (a 1e-4 return) | **0 fire** | 1,400 fire, all reading 0 | **1,400 fire** |
| 400 identical closes | 0 fire | 0 fire | 0 fire |
| returns that ARE a cubic | 0 fire | 1,400 fire, all reading 0 | **1,400 fire** |
| exact geometric ladder | 0 fire | 1,400 fire, reading inside [3, 11] | 0 fire |

The `unguarded` column is the WHOLE set of values over all 1,400 windows, not
a sample of it, and the last row is given as a span because the exact set
moves with the CPU dispatch — that frame IS rounding noise, so that is the
expected result: `{3 .. 10}` by default and `{3 .. 11}` with AVX-512 / AVX2 /
FMA3 disabled (§F1). The other rows' sets are identical under both
dispatches: `{0, 16 .. 33}`, `{0}`, empty, `{0}`, empty, `{0}`.

What the floor buys is the band where the unguarded failure is
ordinary-looking rather than absurd: the geometric ladder and the one-ulp
step read values inside the scale, indistinguishable from a real period. On
the other deterministic frames the unguarded reading is the SENTINEL 0 — not
absurd either, and still a claim ("no periodicity") about a window whose
autocorrelations are the shape of the fit's own rounding.

⚠ **The cost, stated rather than hidden** (the two bolded rows): on a
DETERMINISTICALLY SMOOTH path this column is blank where the sibling catch22
port fires. A price rising by exactly one kurus a bar from 100.00 has returns
`0.01 / (100 + 0.01k)`, a smooth hyperbola the cubic spline fits to below the
floor; the same is true of a polynomial drift. Those paths have a defined
mathematical answer and this column refuses it. Nothing with noise in it is
near the band — the six realistic frames differ from the unguarded spelling
on 0 bars.

## H. Bad data, and the wiring

| input | behaviour |
|---|---|
| `close[700]` = NaN / ±inf / 0 / −5 / 1e−310 | exactly **101** bars blank beyond the warm-up, 700 .. 800 (the bad close kills the returns on both sides of it) |
| `close[700]` = 1e−300 then `close[701]` = 1e100 | **100** bars blank, 701 .. 800 (the ratio overflows) |
| `close[700]` = 1e−100 then `close[701]` = 1e100 — a FINITE return of 1e200 | **100** bars blank, 701 .. 800. The return is finite, so the earlier rule does not catch it; what does is the `~isfinite` limb, because both the residual's sum of squares and the window's variance are +inf. ⚠ Without that limb those 100 bars read the **sentinel 0** — "no periodicity", a value and not a blank — measured by exec'ing the module without the guard |
| the same pair at ratio 1e77 (1e−50 → 1e27) or 1e40 (1e−20 → 1e20) | nothing blanks, and the guarded and unguarded spellings are bit-equal: the sums of squares stay finite |
| `n` = 99, 100 | `None` — `length` returns need `length + 1` closes |
| `n` = 101, 102 | 1 and 2 bars fire |
| `length` = None / 0 / 1 / 29 | falls back to 100 (`MIN_LENGTH` is 30: at 30 the lag scan still has eight interior lags and the 5-parameter spline leaves 25 residual degrees of freedom) |
| `length` = 30 / 250 / 250.7 | `C22PERIODICITY_30` (1,470 fired) / `_250` (1,250) / `_250` |
| `offset=2` | bit-equal to the unshifted column shifted by 2 |
| `fillna=-1` | 0 NaNs left, −1 on exactly the 100 warm-up bars. ⚠ −1 is OUTSIDE this column's scale, which is what a fill should be here: 0 is already a legal reading |

**Five wiring touch points**, all measured live: the module exists; it is
exported from `pandas_ta.statistics`; `"c22_periodicity"` is in
`Category["statistics"]`; `df.ta.c22_periodicity()` returns
`C22PERIODICITY_100` bit-equal to the function and forwards `length` and
`offset`; `tests/test_c22_periodicity.py` exists. The README's three counts
move 360 → 361, 368 → 369 and statistics 58 → 59, `CATEGORY_TOTAL` in
`tests/test_altport2_ports.py` 360 → 361, `docs/MLCompanionContract.md`'s
tagged-column counts 705 → 706 and `ORD` 56 → 57, and
`docs/IndicatorDictionary.md` was regenerated by its own generator (`ORD`,
warm-up 100).

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_periodicity.py P`. Not run by a bare invocation, and
the module is not imported unless the section runs.

### P1. Shipped against the reference, EVERY window of six frames

| frame | windows | equal | mine < ref | mine > ref | Spearman | worst gap |
|---|---|---|---|---|---|---|
| walk | 1,400 | 1,399 | 1 | 0 | +0.9995 | 2 |
| tick-rounded | 1,400 | 1,399 | 1 | 0 | +0.9973 | 5 |
| penny | 1,400 | 1,398 | 0 | 2 | +0.9985 | 6 |
| ar1 | 1,400 | **1,391** | 3 | 6 | +0.9961 | **23** |
| cosine | 1,400 | 1,400 | 0 | 0 | (constant) | 0 |
| student-t | 1,400 | **1,400** | 0 | 0 | +1.0000 | 0 |
| **TOTAL** | **8,400** | **8,387** (99.85%) | 5 | 8 | **+0.9993** | |

**This is the headline difference from `c22_ami_timescale`, which matched its
reference on 1,200 of 1,200.** 13 windows in 8,400 read a different period,
and on the AR(1) frame one of them differs by 23 lags. The column is the same
quantity to Spearman +0.9993 and it is not the same column.

All **13** are printed by the harness, not a sample of them — 1 on the walk
(bar 1462), 1 on the tick-rounded walk (1468), 2 on the penny frame (888,
1306), 9 on the AR(1) frame and 0 on the Student-t frame — with this port's
value and the reference's beside each.

(The pre-fix biased divisor stood at 8,376 of 8,400 and +0.9980, with 24
disagreements including 2 on the Student-t frame. Comparing the two printed
lists bar by bar: fixing the divisor **removed 14** of those 24 — 1 on the
walk, 1 on the tick-rounded frame, 1 on the penny frame, 9 on the AR(1) one
and both Student-t ones — and **added 3**: tick-rounded bar 1468 and AR(1)
bars 1082 and 1191. 24 − 14 + 3 = 13.)

### P1b. WHICH reading the reference implements

Every third window above (2,802 windows both score), scored by this port and
by **seventeen** other defensible readings. The count is windows where that
reading equals the reference:

| reading | equals the reference |
|---|---|
| **shipped** (two-piece cubic spline, z-score, `n − k` divisor, demeaned) | **2,798 / 2,802 (99.86%)** |
| the same, spelled z-score-first instead of one division by `var` | 2,798 |
| the same, population z-score (`ddof = 0`) | 2,798 |
| the same, residual not re-demeaned (the literal source line) | 2,798 |
| non-strict extrema | 2,798 |
| scipy B-spline detrend | 2,798 |
| `acmax = floor(n / 3)` | 2,797 |
| biased acf — divisor = the RESIDUAL's sum of squares (**the pre-fix reading**) | 2,794 |
| biased acf, no demean | 2,794 |
| `n − k` divisor but normalised on the residual | 2,794 |
| two-limb normalisation, one mean | 2,791 |
| lagged-pair Pearson acf | 2,788 |
| `th = 0` | 2,772 |
| detrend with the knot at ⅓ | 2,675 (95.5%) |
| detrend by one cubic, no knot | 2,608 (93.1%) |
| detrend with three pieces | 2,581 (92.1%) |
| detrend by a straight line | 2,406 (85.9%) |
| no detrend at all | 2,330 (83.2%) |

Two conclusions, and they are different in kind:

1. **The DETREND reading is pinned by measurement.** Every alternative knot
   structure is 4.4 to 16.7 percentage points worse against the reference —
   123 windows for the knot at ⅓, 190 for one cubic, 217 for three pieces,
   392 for a line, 468 for no detrend at all. `spap2(2, 4, 1:N, y)` means a
   least-squares cubic on two pieces with the knot at the middle, and that is
   what ships.
2. **The ACF's DIVISOR is pinned by the sources and corroborated here.** The
   source line is `acf(i) = mean(y(1:N-i).*y(i+1:N))` on a z-scored series
   (`acf[tau-1] /= size - tau` in catch22's C), and that reading scores
   2,798 against the biased one's 2,794 — 4 windows better, which is small
   but is the right sign and is not what decided it. What decided it is the
   source line (§A5). ⚠ This receipt's earlier draft had it backwards: it
   shipped the biased divisor, attributed it to `CO_AutoCorr(.., 'Fourier')`
   — a function `PD_PeriodicityWang` does not call — and wrote that "neither
   source pins the divisor". Both do. The three readings that tie at 2,798
   are the SAME quantity under conventions the source line genuinely leaves
   open (§A5's second table), not rival divisors.

⚠ **The 4 disagreements on this subsample are a real difference whose cause
is NOT identified, and here is everything the harness knows about them.** All
4 are printed per window with the readings that match the reference on each,
and counted:

| reading | disagreements it matches |
|---|---|
| detrend with the knot at ⅓ | **4 / 4** |
| detrend with three pieces | 3 / 4 |
| no detrend at all | 3 / 4 |
| detrend by one cubic, no knot | 3 / 4 |
| detrend by a straight line | 3 / 4 |
| biased acf (the pre-fix reading) | 1 / 4 |
| biased acf, no demean | 1 / 4 |
| lagged-pair Pearson acf | 1 / 4 |
| **explained by NO reading tried** | **0 / 4** |

Read that carefully, because it is easy to over-read:

* **Every one of the 4 is matched by at least one alternative.** None is
  unexplainable.
* **No alternative is better overall.** The reading that matches all four —
  the knot at ⅓ — disagrees with the reference on 127 of the 2,802 windows
  (2,802 − 2,675), and since it matches all 4 of the shipped reading's
  disagreements, **every one of those 127** is a window where the shipped
  reading agrees and it does not. It is not what the reference computes
  either. The disagreements are where the detrend's details DECIDE the
  answer, not evidence that the reference fits a different structure.
* **Two of the four hang on a near-boundary quantity**, measured per window:
  a rise 2.6e-05 above the 0.01 threshold (tick-rounded bar 1468, which is
  also the smallest margin in all of §D5), and a deciding peak 1.8e-04 above
  zero whose rise clears the threshold by 1.1e-03 (walk bar 1462).
* **Two are not near any boundary**, and they do not point the same way.
  Penny bar 1306 (8 against 5, margin 0.208) is matched **only by other
  detrends** — no detrend, one cubic, the knot at ⅓, three pieces, a
  straight line — so that one is structural in the detrend. AR(1) bar 358
  (13 against 7, margin 0.022) is matched by the lagged-pair Pearson acf and
  by four detrends, so on that window the record does not decide between a
  different detrend and a different autocorrelation. Both are copied from
  the harness's per-window print, not summarised from it.

What the difference is NOT is this module's own conditioning: §A1 measures
four spellings of the SAME fit against each other at 2.5e-14 relative for
the independent B-spline implementation and 1.3e-12 for the worst-conditioned
of them (the normal equations), with **0** of 1,200 windows moved in every
case, while the quantities above need 2.6e-05 to 2e-01 to move. So the
reference is computing
something slightly different rather than rounding differently. Which detail
is not identifiable from the outside, and identifying it would mean reading
GPL-3.0 code, which this port may not do.

### P2. Entry points, and the z-score

| probe | result |
|---|---|
| single-feature function vs `catch22_all` | 61 / 61 windows equal |
| the reference on raw vs z-scored returns | 61 / 61 equal |

The second row is what makes §P1 a fair comparison: the prototype feeds raw
returns to `catch22_all`, which z-scores internally, and the feature does not
see it (neither does this port, §A4).

### P3. The windows this port BLANKS and the reference scores

| frame | blank windows | sampled | the reference scores | its values |
|---|---|---|---|---|
| walk, penny | 0 | 0 | — | — |
| 400-bar walk + 300 flat closes | 201 | 67 | **67** | 0 on all 67 |
| exact geometric ladder | 1,400 | 467 | **467** | 3 .. 10 |
| returns that ARE a cubic | 1,400 | 467 | **467** | 0 on all 467 |

So where a window is flat, geometric or a disguised spline, this port blanks
and the reference returns a number. That is why §C4's real-data limb has to
come from the port's own Gate E run rather than be inferred from the screen.
On the PRE-FIX column that run said the difference costs nothing on BIST —
389,949 of 398,849 bars non-NaN, the warm-up and not one bar more — so no
BIST window in the 89 frames was flat, geometric or a disguised spline over
all 100 returns. The blanking rule did not change with the divisor (§A5
touches the autocorrelation only), so the re-run is expected to repeat it.

## T. Chunking and cost

`CHUNK_VALUES = 1 << 19` → 5,242 windows per block at `length` 100. Budgets
of 100, 400, 1,024 and the default are **bit-equal** to each other, so the
chunk boundary is invisible — which is also what keeps the spline fit, the
demean and the window variance per-row. At n = 400,000: 399,900 bars fired,
**6.7 s**, traced peak **23.9 MB** (tracemalloc). Wall clock is not quoted as
a band because it does not reproduce.

## What a consumer must know

1. It is an **ordinal lag in bars**, not a continuous statistic: `ORD`,
   `{0} ∪ {2 .. 33}`, tied on roughly nine bars in ten. Feed it as an
   ordinal or one-hot.
2. **0 is a SENTINEL and the FLOOR** — "no peak passed Wang's three
   conditions" — and it is RARE (0.0% to 0.7% of fired bars here), so a
   consumer cannot learn its meaning from the data.
3. **A cycle longer than a third of the window is invisible**: the
   autocorrelations stop at `ceil(length / 3)`, so at the default the
   reportable range ends at 33 and an exact 40-bar cosine reads 0 (§A3).
4. On near-iid returns it is mostly reading the **sampling noise** of the
   autocorrelation (median 5, lags 3 .. 9 on 98% of walk bars). Its
   information, if any, is in the tail where a real cycle pushes it out — the
   cosine law in §A3 is the clean case.
5. **NaN, never a sentinel,** on a window whose DETRENDED root mean square is
   at most 9.09e-13: a flat run, an exactly geometric path, a polynomial
   drift, and ⚠ any deterministically SMOOTH path, where
   `c22_ami_timescale` fires and this column does not (§G).
6. The **detrend** is a two-piece least-squares cubic spline and it is
   load-bearing: five other knot structures move up to 202 bars in 467, and
   the shipped one is what the reference measurably implements (§A5b, §P1b).
7. The **autocorrelation is the source's**: the lagged products averaged over
   the `n − k` pairs that exist, on a window z-scored BEFORE the detrend, so
   condition (b)'s absolute 0.01 is in z-scored units (§A5). A consumer
   reading an older copy of this receipt should know the divisor changed on
   2026-11-20 and the values moved on 6 of 2,802 sampled windows.
8. **This port is not bit-identical to the catch22 reference**: 8,387 of
   8,400 sampled windows equal, Spearman +0.9993, worst single-window gap 23
   lags (§P1). The 2026-10-24 screen's Gate E figure was measured on the
   reference's column, so it is an expectation and not a result (§E2).
9. **Gate E is pending** — run by issue-solver after this session; the
   2026-11-20 run measured the pre-fix column and is withdrawn (§E). There is
   therefore **no real BIST measurement of the shipped column in this
   receipt**: everything here is synthetic, the withdrawn run's figures are
   labelled as expectations, and nothing anywhere tests whether the column
   predicts a return.
