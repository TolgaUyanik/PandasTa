# `c22_ami_timescale` — measured

PandasTa issue **#125** (C22-AMI-TIMESCALE), ported 2026-11-20 on branch
`issue-125-c22-ami-timescale`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_ami_timescale.py` |
| column | `C22AMITIMESCALE_100` (`ORD`, a whole number in [2, 40]) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `IN_AutoMutualInfoStats_40_gaussian_fmmi`; reference code pycatch22 1.x, **GPL-3.0** — ported from the definitions |
| tests | `tests/test_c22_ami_timescale.py` (196 tests) |
| harness | `docs/measure_c22_ami_timescale.py` (sections A–E, G, H, P, T, Z; **P is opt-in** and is the only one that imports the GPL-3.0 reference), `docs/measure_c22_ami_timescale_cpu.py` |
| Gate A | correct against four independent oracles, 0 disagreements — §A |
| Gate B | causal; 0 of 35 offsets leak on six frames × eight splices; seven mutants — §B |
| Gate C | fires on every bar with a full window, 6–10 distinct values; real data 389,949 non-NaN and 389,949 non-zero of 398,849 — §C |
| Gate D | ×8/×64/2^±40 bit-identical; `0 < fires < n`; not constant on five of six frames — §D |
| Gate E | **SHIP** — max \|ρ\| **0.0280** vs `ROLLING_LOW_250` (n = 376,599), per-frame max median 0.0701 vs `EMA_200`, 0 of 89 frames ≥ 0.90 — §E |
| Gate F | PandasTa green (196 module tests; full suite 1 failed / 12,320 passed / 86 skipped, the known `../AlternativeRepos` test); Backtesting's suite **pending, run by issue-solver** — §F |

Every number below was produced by `python docs/measure_c22_ami_timescale.py`
on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11), with four
exceptions: the §F suite counts (`python -m pytest -q`), §F1's no-AVX column
and §F's rows 2–3 (`docs/measure_c22_ami_timescale_cpu.py`), §E and §C4's
real-data counts (issue-solver's Gate E run `is125-c22_ami_timescale-896a6570`,
2026-11-20), and the 2026-10-24 screen figures quoted in §A5 — the owner's
PROTOTYPE measurements, labelled as such wherever they appear. Figures that
move between numpy's CPU dispatches are tabulated in §F1.

---

## 0. What the column is

For each lag `tau` in 1 .. 40, take the window's two overlapping limbs
`X[:-tau]` and `X[tau:]`, correlate them, and read the correlation as the
mutual information a bivariate Gaussian would carry:

```
r[t]  = close[t] / close[t-1] - 1
X     = r[T-99 .. T]                            (the 100 returns ending at T)
A     = X[:-tau] - mean(X[:-tau])
B     = X[tau:]  - mean(X[tau:])
rho   = sum(A*B) / sqrt(sum(A*A) * sum(B*B))
AMI   = -0.5 * ln(1 - min(rho**2, 1))
C22AMITIMESCALE = min{tau in 2..39 : AMI(tau) < AMI(tau-1) and AMI(tau) < AMI(tau+1)}
                  else 40
```

Lag 1 cannot be tested (a minimum needs a neighbour on each side) and 40 is a
**sentinel**, "no dip in 40 lags". The column is a small integer, and that is
the first thing a consumer needs to know: it is tagged `ORD`, it ties on 77.6%
to 100% of neighbouring bar pairs, and its floor (2) is not a zero.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository tests
it on BIST: the feature's presence here is existence, not evidence. The issue
says so and this receipt repeats it.

The reference implementation is GPL-3.0 and this fork is MIT. The port was
written from the definitions — the paper's feature name and the hctsa
operation it names, `IN_AutoMutualInfoStats(y, 40, 'gaussian')`, field `fmmi`.
No shipped module imports the reference; the test
`test_the_reference_implementation_is_not_imported_by_shipped_code` sweeps
every `.py` file under `pandas_ta/` (394 on this tree) for an import statement
mentioning it and finds none. ⚠ pycatch22 **is installed in this worktree**,
so that guard is not vacuous.

The one place the reference is run is `docs/measure_c22_ami_timescale.py`
section **P**, which is opt-in (a bare run skips it) and is MEASUREMENT only —
the same use the owner's own screen prototype makes of it
(`docs/issues/screen/ind_screen_r3.py`: "it is used here only to MEASURE, on
the owner's machine"). It answers one question the definitions cannot: is the
column this port ships the column the 2026-10-24 screen's Gate E numbers were
measured on? See §A5.

## A. Gate A — correctness

### A1. The estimator is a choice, and measurement decided it

The Gaussian AMI needs a correlation and the sources do not pin its sample
form. Three readings are defensible:

| reading | `rho(tau)` |
|---|---|
| **lagged-pair Pearson** (shipped) | `corr(X[:-tau], X[tau:])`, each limb demeaned by its own mean and scaled by its own sum of squares |
| biased ACF | `sum(d[:-tau]*d[tau:]) / sum(d*d)`, one mean, one variance, divisor `n` |
| adjusted ACF | the same products averaged over the `n - tau` pairs that exist, divisor `n - tau` |

The first draft of this module shipped the **biased ACF**. Section P then
measured the reference as a black box and found 17 disagreements in 1,200
sampled windows — and on **17 of 17** the reference's value was the one the
lagged-pair Pearson reading gives, with gaps of 1.3e-06 to 8.4e-04 in `rho**2`
at the disputed lag, far too large to be a last-bit flip. The estimator was
switched, which is also what hctsa's `CO_AutoMutualInfo(..., 'gaussian')`
spells (`corr(y(1:end-tau), y(1+tau:end))`).

The other two readings are REAL columns, not roundings. Against the shipped
one, over all 1,400 fired bars of each frame:

| frame | biased: equal | Spearman | adjusted: equal | Spearman |
|---|---|---|---|---|
| walk | 1,390 / 1,400 | +0.9932 | 1,388 / 1,400 | +0.9937 |
| tick-rounded | 1,385 / 1,400 | +0.9907 | 1,391 / 1,400 | +0.9950 |
| penny | 1,384 / 1,400 | +0.9913 | 1,389 / 1,400 | +0.9929 |
| ar1 | 1,349 / 1,400 | +0.9743 | 1,355 / 1,400 | +0.9800 |
| cosine | 1,400 / 1,400 | (constant) | 1,400 / 1,400 | (constant) |
| student-t | 1,383 / 1,400 | +0.9870 | 1,385 / 1,400 | +0.9852 |

So a later "simplification" to an ACF spelling would change up to 51 bars in
1,400. Two tests fail if either alternative becomes indistinguishable.
statsmodels 0.14.4 confirms this file's own spelling of the biased
alternative: `max |rho - acf(adjusted=False)| = 5.551e-16`.

### A2. The exact rational oracle — zero roundings

`AMI` is strictly increasing in `rho**2`, and
`rho**2 = (sum A*B)**2 / (sum A*A * sum B*B)` over exactly representable
doubles is a ratio of integers, so the first minimum can be decided by exact
`fractions.Fraction` comparisons with no rounding at all. Every 13th window of
all six frames — 648 windows:

| frame | agree | disagree |
|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 108 / 108 each | **0** |

### A3. Three more independent spellings

| oracle | windows | disagreements | worst difference |
|---|---|---|---|
| plain-Python `math.fsum`, explicit slices, `log(1 - r*r)` | 200 per frame × 6 | **0** | — |
| `np.corrcoef` per lag | 200 per frame × 6 | **0** | max \|rho²−library\| 2.1e-15 |
| `pandas.Series.corr` per lag | 200 per frame × 6 | **0** | max \|rho²−library\| 2.1e-15 |

Scanning `rho**2` instead of the AMI (the monotone equivalence the exact
oracle leans on) **disagrees on 0 of 1,400** windows of each frame — i.e. the
two spellings pick the same lag on all 1,400, which is measured rather than
assumed because `log1p` is not strictly monotone on doubles.
`log1p(-r2)` versus `log(1 - r2)`: worst AMI difference 3.5e-17 to 3.6e-15.

### A4. The quarter-period law, and where it stops

Returns that are an exact cosine of period P read exactly `P / 4`, constant on
every fired bar:

| P | 8 | 12 | 20 | 40 | 80 | 120 |
|---|---|---|---|---|---|---|
| column | 2 | 3 | 5 | 10 | 20 | **17 distinct values, 21 .. 40** |

At P = 120 the 100-return window no longer holds a full period and the law
breaks — which is also the only frame measured here where the sentinel 40 is
reached. An AR(1) in the returns moves it the other way: median 3 at
φ = −0.4, 0.0, +0.4, and 8 (range 2 .. 21) at φ = −0.8, 7 (4 .. 19) at +0.8.

### A5. Against the screened quantity (black box, GPL-3.0, opt-in)

`python docs/measure_c22_ami_timescale.py P`, after the estimator switch, over
every 7th window of the six frames:

| frame | equal | off by one | other |
|---|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 200 / 200 each | 0 | 0 |

**1,200 of 1,200 windows, 0 disagreements**, through both of that library's
entry points (`catch22_all` and the single-feature function).

⚠ **That is 1,200 of the windows BOTH columns score, and the comparison is
blind by construction to the windows this port blanks.** Section P skips a
window where this module is NaN, because the two then differ deliberately
(§C3, §G): the reference scans a degenerate window and returns a number where
this port refuses. Measured, every 3rd blank window:

| frame | blank windows | the reference scores | reading |
|---|---|---|---|
| walk | 0 | 0 | — |
| penny | 0 | 0 | — |
| 400-bar walk + 300 flat closes | 80 | **80** | 40 on 67, 2 on 13 |
| exact geometric ladder | 467 | **467** | 2 .. 8 |

So: on every window SAMPLED that both columns score — 1,200 of 1,200, every
7th window of six SYNTHETIC frames, no real BIST window among them — this port
IS the screened quantity; where a window is flat, suspended or geometric, this
port blanks and the reference does not. On real BIST frames with suspended runs that makes this
column's non-NaN count LOWER than the prototype's, so the prototype's
n = 376,599 is not this column's n, and §C4's real-data limb had to come from
the port's own Gate E run rather than being inferred. It now has: **389,949**
of 398,849 bars, measured (§C4).

The screen's Gate E figure (max |ρ| 0.0280 vs `ROLLING_LOW_250`,
n = 376,599, SHIP) is therefore about this quantity on the bars both score —
a PROTOTYPE measurement. The port's own run (§E) lands on the same comparator,
the same n and the same figure to four decimals — a result that agrees with it,
not a transfer of it. Whether the port's blanking rules cost any real BIST bar
against the prototype is not answerable from these two numbers: the ρ sample
sizes match (376,599 both), and the prototype's own non-NaN count over the 89
frames was never recorded, so there is nothing to subtract it from.

### A6. The clip is load-bearing

Cauchy–Schwarz bounds `rho**2` by 1; rounding does not. Raw (unclipped)
`rho**2` per (window, lag) cell, every 7th window × 40 lags = 8,000 cells per
frame:

| frame | cells > 1 | cells == 1 (AMI = +inf) | max raw |
|---|---|---|---|
| walk / tick-rounded / penny / ar1 / student-t | 0 | 0 | 0.157 / 0.172 / 0.167 / 0.527 / 0.201 |
| cosine (P = 20) | **218** | 367 | 1.0000000000000009 |
| alternating ±2% | **2,319** | 3,340 | 1.0000000000000018 |
| cosine (P = 120) | 0 | 0 | 0.998 |

Without `np.minimum(rho**2, 1.0)` each of those 218 cells is
`log1p(x < -1)` = NaN, handed straight to the scan. The clip turns them into
+inf, which is a maximum and cannot be a first minimum.

### A7. The degenerate corner, disclosed

Returns that alternate exactly +2% / −2% make the two limbs of every lag the
same sequence up to a sign, so in exact arithmetic `rho**2` is 1 at all 40
lags. Measured over the 40 lags of one window: min 0.99999999999999933,
max 1. The AMI is then the same ≈ +17.5 everywhere and WHICH lag is reported
is decided by the last bits: **31 distinct values** over 1,400 fired bars, and
a ×10 rescale of that frame moves **1,197** of them (§D2 shows 0 on every
realistic frame). Nothing with a real return shape is near the corner — the
largest `rho**2` the sampled walk / AR(1) / Student-t windows produce is 0.53
(the §A6 table's `max raw` column, same sample).

An exactly geometric path fires **0** bars, and the mechanism is the **floor**,
not the constant-limb rule — measured, because the obvious story is wrong.
`start * (1 + step)**k` rounds every power on its own, so the consecutive
ratios are NOT identical doubles: 3 to 5 distinct returns per window at
step +1%, +0.1% and −0.5%, every limb varying, window sd 9.6e-17 to 1.4e-16
against the 9.09e-13 floor. Unguarded, all three ladders fire all 1,400 bars
and read inside [2, 14] with medians 2 to 3 — values a reader could not tell
from a real frame's, off 1e-16 of rounding (harness §G4).

### A8. Strictness

`<=` in place of `<` picks the same lag on every window sampled (200 per
frame × 6), and there are **0** exact ties between neighbouring lags' AMI in
those windows. The strictness is kept because that is what a local minimum
means; the difference is unreachable rather than cosmetic.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a different
path, and no bar before J may move. 35 offsets per frame, **eight** different
futures at each:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 35** each |
| walk at `length` 80, 120, 250 | **0 / 35** each |

### B2. Seven mutants, read off this module's source, edited and exec'd in memory

| mutant | edit | walk | tick-rounded | cosine |
|---|---|---|---|---|
| `write-back-dated` | `out[length + a:...]` → `out[length - 1 + a:...]` | 22 / 35 | 16 / 35 | 0 / 35 |
| `window-one-ahead` | the window takes one more future return | 22 / 35 | 16 / 35 | 0 / 35 |
| `window-ten-ahead` | ten more | **35 / 35** | **35 / 35** | **35 / 35** |
| `returns-rolled` | the return series shifted one bar earlier | 22 / 35 | 16 / 35 | 0 / 35 |
| `chunk-wide-demean` | a limb demeaned by the whole block's mean | 0 / 35, and it differs from the real module on **1** bar of 1,400 (0 and 0 on the other two frames) |
| `chunk-wide-floor` | the floor's own demean, same edit | 0 / 35, and 0 bars differ on all three frames |
| `mask-back-dated` | the bad-data mask reads the next bar | dead on a clean frame — see B3 |

With a single splice instead of eight the same mutants are caught at 9 / 8 / 0
(one-bar) and 33 / 31 / 24 (ten-bar). Where a one-bar mutant moves anything it
moves **exactly bar J − 1 and nothing else**: over 12 offsets of the walk with
one splice each, 4 offsets move a pre-splice bar and every one of those moves
a single bar, J − 1 (harness §B2c, each mutant compared against itself so its
own standing difference cannot be mistaken for a leak).

**The counts below 35 are a finding, not a defect, and they are the reason
mutants are here at all.** A one-bar back-dating can only be seen on a bar
whose value differs from its neighbour's, and this column ties on 79.7%
(walk), 80.0% (tick-rounded) and 100% (cosine, a constant column) of
neighbouring pairs. A constant column cannot witness a one-bar shift by any
means; the ten-bar mutant is caught there only because the NaN mask moves.
Prefix truncation would have proved less than any of this.

The two demean mutants (rows 5 and 6) are near-DEAD and that is also measured
rather than excused: replacing a limb's own mean with the whole block's changes
1 bar of 1,400 on the walk and 0 on the other two frames, because
`|window mean| / window sd` has median 0.054 and max 0.248 — a limb demeaned
by the wrong near-zero number is almost the same limb. They are kept because
the edit is the one a future refactor would make, and they are counted in the
seven rather than quietly dropped.

### B3. The mask mutant

On a clean walk it is **bit-equal** on all 1,500 bars — invisible, not merely
weak. On a frame with one bad close it is caught at **12 of 12** offsets, and
the bar it moves is exactly **J − 1** every time.

### B4. Tie density

| frame | walk | tick-rounded | penny | ar1 | cosine | student-t |
|---|---|---|---|---|---|---|
| neighbouring pairs equal | 79.7% | 80.0% | 77.6% | 81.7% | 100% | 82.7% |

## C. Gate C — reachability

### C1. Synthetic frames (1,500 bars each)

| frame | fired | distinct | range | median | first bar |
|---|---|---|---|---|---|
| walk | 1,400 / 1,500 | 7 | 2 .. 8 | 3 | 100 |
| tick-rounded | 1,400 | 7 | 2 .. 8 | 3 | 100 |
| penny | 1,400 | 6 | 2 .. 7 | 3 | 100 |
| ar1 | 1,400 | 10 | 2 .. 11 | 5 | 100 |
| cosine (P = 20) | 1,400 | **1** (constant 5) | 5 .. 5 | 5 | 100 |
| student-t | 1,400 | 7 | 2 .. 8 | 3 | 100 |

Every bar with a full window fires, and no fired bar is 0 (the floor of the
scale is 2). The value distribution on the walk is
`{2: 298, 3: 474, 4: 378, 5: 184, 6: 57, 7: 5, 8: 4}` — i.e. a near-iid return
window has no cycle, so the first dip of `rho**2` lands where the sampling
noise of the correlation puts it, lag 2 on 21% of bars. The sentinel 40 is
reached on **0** of those 8,400 bars.

### C2. The issue's own worry: BIST tick rounding

The issue says to check whether this is a tick-rounding reading. A 2-lira
stock on a 1-kurus tick (`penny`) prints **325 of 1,499** returns (21.7%) as
exactly 0.00%, against 0.3% on a DIFFERENT 100-lira walk rounded to the kurus
(seed 55, σ 0.015, where `penny` is seed 23, σ 0.012, level 2.0) and 0.0% on
a third, unrounded 100-lira walk (seed 11, σ 0.015) — three paths, not one at
three price levels. The column's behaviour across the three is the same shape:
median 3, 6 to 7 distinct values, 1,400 of 1,400 bars fired. Zero returns do
not blank a window; only a window with no variation at all, or one with a
constant limb, does.

⚠ What this does NOT settle is Gate E's question. Whether the column's top
real-data comparator is a price level or `Volume` — the issue's tell for a
rounding artefact — was decided by the Gate E run. It **is** a price level,
`ROLLING_LOW_250`, exactly the tell the issue named, at |ρ| **0.0280**. The
tell fires on the RANKING and not on the magnitude; §E reads that out.

### C3. The two blanking rules, with their costs

* **noise floor**, `sd(returns) > 9.09e-13`: 0 bars differ from the unguarded
  spelling on each of the six frames, so it costs nothing on a real shape.
* **constant limb**: a price that goes flat at bar 400 blanks bar **460**
  onward — the lag-40 limb of bar T is the returns of bars T−59 .. T, so this
  bites 40 bars before the whole window is flat. Measured: 360 of 700 bars
  fire on a 400-bar walk followed by 300 flat closes; bar 459 reads 2, bar 460
  is NaN.

### C4. Real data

Everything above is synthetic. These two counts are from the Gate E run
`is125-c22_ami_timescale-896a6570` (2026-11-20; 89 frozen ALTPORT-1 BIST
frames, 398,849 pooled bars):

| | `C22AMITIMESCALE_100` |
|---|---|
| non-NaN | **389,949** of 398,849 (97.77%) |
| non-zero | **389,949** of 398,849 |

The two counts are equal because **2 is the floor of the scale** (§0): the
column cannot read 0, so every bar that is not blank is non-zero. 398,849 −
389,949 = 8,900 blank bars, which is exactly 89 frames × the 100 warm-up bars
each — so on these 89 frames the three blanking rules of §C3 and §G cost **0
bars beyond the warm-up**. That is arithmetic on the two measured counts and
the frame count, and it is the only real-data evidence here that the noise
floor and the constant-limb rule do not bite on BIST dailies. ⚠ It does assume
every frame is longer than 100 bars; the shortest of the 89 is not measured in
this receipt, and a frame of ≤ 100 bars would make the identity coincidental.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64, ×2^−40, ×2^40) | 24 of 24 **bit-identical** |
| walk at `length` 80 / 120 / 250 × (×8, ×64) | 6 of 6 **bit-identical** |
| price levels 1e−6 / 1e+6 / 1e+100, ×8 | 3 of 3 bit-identical, 1,400 bars fired at each |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`.

### D2. Inexact rescales

| frame | ×10 | ×3.7 | ×0.1 | ×1.0000001 |
|---|---|---|---|---|
| all six | 0 bars, 0 mask | 0 | 0 | 0 |

Not promised by the arithmetic — the output is an integer decided by float
comparisons — and the tests bound it (≤ 5 bars) rather than pinning 0.

### D3. Blind to amplitude, not to shape

Rescaling the window's returns themselves by ×0.5 / ×2 / ×10 moves **0** of
1,400 fired bars (a correlation cannot see a rescale of both limbs). The same
returns in a different ORDER move **1,049**. So this is not a volatility
column, and the bit-identity in D1 is not vacuous.

### D4. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on all six frames. Distinct values > 1 on five of six;
the cosine frame is constant at 5 **by construction** (`P / 4`, §A4), which is
the feature working rather than a dead column, and the tests name it rather
than averaging it away.

### D5. How close the decision runs to a rounding flip

Smallest gap in `rho**2` between the deciding lag and the better of its
neighbours:

| frame | walk | tick-rounded | penny | ar1 | cosine | student-t |
|---|---|---|---|---|---|---|
| min gap | 7.3e-08 | 6.0e-07 | **3.6e-09** | 2.1e-07 | 7.6e-02 | 1.5e-07 |

Seven orders of magnitude above a last-bit question, which is why D2 comes out
clean and why no test pins a ρ to 1e-6.

## E. Gate E — **SHIP**

Gate E: measured 2026-11-20 by issue-solver, verdict **SHIP**.

Run `is125-c22_ami_timescale-896a6570`, on
the code at this branch's first commit, and recorded in
`docs/gate_e_ledger.csv` by
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-20`.

| | |
|---|---|
| column | `C22AMITIMESCALE_100` |
| max \|ρ\| | **0.0280** (ρ = +0.028040679431830865) |
| against | `ROLLING_LOW_250` (`compute_all`) |
| n | **376,599** |
| per-frame max median \|ρ\| | **0.0701** (0.07013351426940281) vs `EMA_200`, over 89 frames |
| frames ≥ 0.90 | **0 of 89** (0.0%) on each of the top five comparators, and 0 of 89 ≥ 0.80 on each (`perframe.csv`) |
| verdict | **SHIP** under `r3-perframe-0.90` |

Run facts (`meta.json`): default parameters (`kwargs: {}`), 89 frames, 398,849
pooled bars, 329 `compute_all` + 358 manifest = **687** comparators, canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, data stamp
`1be6495e`, pandas 2.3.3 / numpy 1.26.4, module sha1 `523a337c`.
One comparator was degenerate and dropped: `squeeze_SQZ_NO` (constant over the
pooled sample), listed in the run's `degenerate.csv`. It was the comparator
that was constant, not this column.

The split by comparator set: `compute_all` **0.0280** vs `ROLLING_LOW_250`
(n = 376,599); the `ml_features` manifest **0.0220** vs `ADX_Pctl`
(n = 389,949). 0.0280 is the max of the two, a factor of **27** under the 0.76
ship line.

### E2. The issue's tick-rounding tell, read out

The issue said a top comparator that is a price level (`mcgd`,
`ROLLING_LOW_250`) or `Volume` would point at BIST tick rounding rather than at
return dynamics. The measured top-25 (`top25.csv`) is price levels almost
end to end:

| rank | against | \|ρ\| | n |
|---|---|---|---|
| 1 | `ROLLING_LOW_250` | 0.0280 | 376,599 |
| 2 | `ROLLING_HIGH_250` | 0.0260 | 376,599 |
| 3 | `SMA_200` | 0.0255 | 381,138 |
| 4 | `EMA_200` | 0.0254 | 381,138 |
| 5 | `Senkou_A` | 0.0243 | 389,949 |
| … | | | |
| 23 | `mcgd` | 0.0231 | 389,949 |

So the tell fires on the RANKING and the issue's two named columns are both in
it — `ROLLING_LOW_250` first, `mcgd` 23rd. What it does not do is fire on the
MAGNITUDE: rank 1 is 0.0280 and rank 25 is 0.0231, a spread of 0.005 across 25
comparators. A ranking that flat is a ranking of noise — the top is a price
level because 20-odd price levels are all mutually ~1.0 correlated and one of
them had to come first, not because the column reads a price. `Volume` is not
in the top 25. Reading this as "no tick-rounding artefact detected at Gate E's
resolution" is a judgement on the magnitudes above, not a measurement of
rounding itself; §C2 is the part of this receipt that probes rounding directly,
on three synthetic paths.

The column's own per-frame figures say the same: median 0.0635 against
`ROLLING_LOW_250` over 89 frames, max single-frame 0.4343, min 0.0008.

The 2026-10-24 screen measured the PROTOTYPE at max |ρ| 0.0280 vs
`ROLLING_LOW_250`, n = 376,599, per-frame max median 0.0701 → SHIP (run
`screen_r3_20261024`). The port's run above lands on the same comparator, the
same n and the same figures to four decimals. §A5 is why that was expected.

### E3. In-fork overlap, measured here (6 synthetic frames, 1,500 bars each)

Gate E's 687 comparators include the engine's `compute_all` and the
`ml_features` manifest, so several of this fork's own ACF-family columns are
not in it. Measured against **15** of them, per frame and pooled — all 15
tabulated, because a top-N cut here would read as "these are the ones that
matter" when the ranking is by the pooled figure the section goes on to
disown:

| comparator | pooled ρ | n | per-frame median \|ρ\| |
|---|---|---|---|
| `TS_AC1_60` | +0.5061 | 8,400 | 0.1067 |
| `DIFF2ACF1_100` | +0.5054 | 8,400 | 0.0611 |
| `TS_CID_CE_20` | −0.5030 | 8,400 | 0.0577 |
| `TFSPECENT_64` | −0.5017 | 8,400 | 0.0513 |
| `TFDFA_100` | +0.4922 | 8,400 | 0.0590 |
| `TS_PERMENT_20_3` | −0.4204 | 8,400 | 0.0270 |
| `FIRSTZEROAC_100` | +0.3947 | 8,400 | 0.0383 |
| `LEAN_HURST_100_20` | +0.3014 | **7,000** | 0.0573 |
| `TS_BINENT_20_5` | +0.2879 | 8,400 | 0.0781 |
| `TFAUTOCORR1E_60` | −0.2127 | 8,400 | 0.1351 |
| `HLIFE_100` | +0.1461 | **7,906** | 0.0947 |
| `TS_AGGAC_60_10` | −0.0981 | 8,400 | 0.0911 |
| `ENTLZ_20` | −0.0275 | 8,400 | 0.0379 |
| `TS_C3_20_1` | −0.0090 | 8,400 | 0.0405 |
| `TFCENTROID_20` | −0.0019 | 8,400 | 0.0360 |

`n` is the bars where both columns are present, so the two bolded rows are
smaller than the rest: those comparators carry their own blanks — 1,400 bars
of the pooled 8,400 have no `LEAN_HURST_100_20` and 494 have no `HLIFE_100`.

⚠ **The pooled column is the misleading one and is printed only because
leaving it out would look like hiding it.** Pooling six frames with different
medians measures between-frame differences, not co-movement: the per-frame
figures behind `TS_AC1_60`'s +0.5061 are +0.1067, +0.0311, −0.2635, +0.4556,
nan (the constant cosine frame) and +0.0596. The harness prints all six cells
for every row; the **largest single per-frame |ρ| over all 15 × 6 cells is
0.4797** (`FIRSTZEROAC_100`, AR(1) frame), well under the 0.76 ship line, and
the highest per-frame median is 0.1351.

### E4. **OWED RULE** — issue #130's `CO_FirstMin_ac`

catch22's `CO_FirstMin_ac` (issue **#130**, candidate `c22_acf_first_min`) is
the first minimum of the SIGNED autocorrelation over the SAME 100 returns —
the nearest relative this column has, and it does not exist in this tree yet,
so neither Gate E's run nor §E3 can see it. Measured here as a function:

| frame | walk | tick-rounded | penny | ar1 | cosine | student-t |
|---|---|---|---|---|---|---|
| Spearman | −0.1533 | −0.3105 | +0.0858 | **+0.7172** | nan (const) | −0.1070 |
| equal values | 14.5% | 8.2% | 21.6% | 31.1% | 0% | 16.8% |

They are different columns on every frame measured (the SIGNED ACF's first dip
is where the correlation turns most NEGATIVE; this column's is where it is
closest to ZERO in either direction). **The rule:** when #130 is ported,
measure its column against `C22AMITIMESCALE_100` over the 89 ALTPORT-1 frames,
read the result against `r3-perframe-0.90`, and if the pair is STRUCK, one of
the two is reverted or waived. A test asserts this receipt keeps naming #130.

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest tests/test_c22_ami_timescale.py -q` | **196 passed** (195 before the receipt session: −2 pending-Gate-E tests, +3 that pin the recorded row) |
| the same module under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_ami_timescale_cpu.py`, which refuses to run if the environment edit did not take) | **196 passed** (2026-11-20, after the receipt session's test swap) |
| `python docs/measure_c22_ami_timescale_cpu.py A B C D` — sections A, B, C and D re-measured under the same disabled dispatch | ran clean; what moved is in §F1 |
| with `tests/test_gate_e_ledger.py` | **1,302 passed** — the owed-row failure is gone now the row is recorded |
| `python -m pytest -q` (full suite) | **1 failed, 12,320 passed, 86 skipped** |

The one failure is
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout; CI deselects it by name) and
nothing else. Before the Gate E row was recorded this run was 2 failed /
12,311 passed, the second being
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reporting `['c22_ami_timescale']` — the owed measurement, now paid.
Backtesting's suite is run by issue-solver in a clean worktree.

### F1. What moves under the CI CPU dispatch

With `AVX512F AVX512_SKX AVX2 FMA3` disabled (still enabled: SSSE3, SSE41,
POPCNT, SSE42, AVX, F16C, AVX512CD, AVX512_CLX, AVX512_CNL, AVX512_ICL), the
test module passes and sections **A, B, C and D were re-run in full** rather
than assumed. ⚠ That re-run predates the `~isfinite(den)` limb of the `bad`
mask (§H), and the sections were not re-measured after it: what justifies that
is a test rather than an argument —
`test_the_overflow_guard_is_inert_on_every_realistic_frame` asserts the
guarded and unguarded spellings are bit-equal on all 1,400 fired bars of each
of the six frames, so no §A–§D figure can have moved.
**Three figures move between dispatches, all of them last bits:**

| figure | default dispatch | AVX-512 / AVX2 / FMA3 off |
|---|---|---|
| §A3 max \|ρ²−library\|, walk (both libraries) | 1.527e-16 | 1.665e-16 |
| §A3 log1p−log worst gap, ar1 / cosine | 1.110e-16 / 3.553e-15 | 5.551e-17 / 2.220e-16 |
| §A6 max raw ρ², walk | 0.15663451871144743 | 0.15663451871144932 |

Everything else is identical, digit for digit: all four oracles' agreement
counts, every bit-identity in §D1, the 0-bars-moved rows of §D2/§D3, every
fired-bar and distinct-value count in §C, §D5's margins, §B's 0-of-35 sweeps
and every mutant catch count, **and §A6's 218 / 367 / 2,319 / 3,340 cells
above and at 1** — the most dispatch-sensitive tallies in the receipt, which
is why they were re-run rather than reasoned about.

The tests nevertheless pin bounds and bands rather than digits for the figures
that *could* move: distinct-value counts, bars moved under an inexact rescale
(≤ 5, measured 0), the ρ figures in §A1/§E, and the wall clock in §Z.

## G. The noise floor, and what it buys

`NOISE_FLOOR = 4096 * eps = 9.095e-13` on the window's return standard
deviation. An ABSOLUTE constant, because what it bounds is a dimensionless
RETURN with no rolling scale of its own to keep causal — the same habit as
`tf_autocorr_1e_60`, `ts_binent_20`, `ts_strike_20`, `ts_c3_20`.

| input | guarded (shipped) | unguarded |
|---|---|---|
| six realistic frames | — | **0 bars differ** |
| price flat at 1e6 except ONE 1-ulp step | 0 bars fire | 20 bars fire, every one reading the **sentinel 40** |
| one 1-kurus tick per bar at price 1e6 (a 1e-11 return) | 0 bars fire | 1,400 bars fire |
| one 1-kurus tick per bar at price 1e9 | 0 fire | 0 fire (the constant-limb rule, not the floor: consecutive returns round to the same double) |
| one 1-kurus tick per bar at price 100 (a 1e-4 return) | 1,400 fire | 1,400 fire |
| 400 identical closes | 0 fire | 0 fire |

What the floor buys is the ULP band, where the unguarded failure is
ordinary-looking rather than absurd: a price flat except for one 1-ulp step
reads the top of the scale, indistinguishable from a real "no dip in 40 lags".
The cost is stated rather than hidden — those paths have a defined
mathematical answer and this column refuses it.

## H. Bad data, and the wiring

| input | behaviour |
|---|---|
| `close[700]` = NaN / ±inf / 0 / −5 / 1e−310 | exactly **101** bars blank, 700 .. 800 (the bad close kills the returns on both sides of it) |
| `close[700]` = 1e−300 then `close[701]` = 1e100 | **100** bars blank, 701 .. 800 (the ratio overflows) |
| `close[700]` = 1e−100 then `close[701]` = 1e100 — a FINITE return of 1e200 | **100** bars blank, 701 .. 800. The return is finite, so the earlier rule does not catch it; what does is `~isfinite(den)`, because the lag-1 limb's sum of squared deviations is +inf. ⚠ Without that limb of the mask those 100 bars read the **sentinel 40** instead — measured, and the reason the guard is in the code |
| the same pair at ratio 1e77 (1e−50 → 1e27) or 1e40 (1e−20 → 1e20) | nothing blanks: the sums of squares stay finite (1.0e154 and 1.0e80), the guarded and unguarded spellings are bit-equal, and 25 bars read the sentinel — a genuine reading of a window one astronomic return dominates, not an overflow |
| `n` = 99, 100 | `None` — `length` returns need `length + 1` closes |
| `n` = 101, 102 | 1 and 2 bars fire |
| `length` = None / 0 / 1 / 79 | falls back to 100 (`MIN_LENGTH` is 2 × 40: two returns per lag at the longest lag) |
| `length` = 80 / 250 / 250.7 | `C22AMITIMESCALE_80` (1,420 fired) / `_250` (1,250) / `_250` |
| `offset=2` | bit-equal to the unshifted column shifted by 2 |
| `fillna=-1` | 0 NaNs left, −1 on exactly the 100 warm-up bars |

**Five wiring touch points**, all measured live: the module exists; it is
exported from `pandas_ta.statistics`; `"c22_ami_timescale"` is in
`Category["statistics"]`; `df.ta.c22_ami_timescale()` returns
`C22AMITIMESCALE_100` bit-equal to the function and forwards `length` and
`offset`; `tests/test_c22_ami_timescale.py` exists. The README's three counts
move 357 → 358 and 365 → 366, `CATEGORY_TOTAL` in
`tests/test_altport2_ports.py` 357 → 358, and `docs/IndicatorDictionary.md`
was regenerated by its own generator (`ORD`, warm-up 100).

## Z. Chunking and cost

`CHUNK_VALUES = 1 << 19` → 5,242 windows per block at `length` 100. Budgets of
100, 400, 1,024 and the default are **bit-equal** to each other, so the chunk
boundary is invisible — which is also what keeps the per-limb demean per-row.
At n = 400,000: 399,900 bars fired, **11.8 s**, traced peak **28.2 MB**
(tracemalloc). The time goes on 40 lags each needing two demeaned limbs; wall
clock is not quoted as a band because it does not reproduce.

## What a consumer must know

1. It is an **ordinal lag**, not a continuous statistic: `ORD`, [2, 40], tied
   on four bars in five. Feed it as an ordinal or one-hot.
2. **2 is the floor and 40 is a sentinel** ("no dip in 40 lags"), not a lag of
   40. The sentinel is monotone with the rest of the scale but was reached by
   0 of 8,400 bars here.
3. It reads the **shape** of the return autocorrelation, not its size: blind
   to a rescale of the returns, moved by a reshuffle of them.
4. On near-iid returns it is mostly reading the **sampling noise** of the
   correlation (median 3, lag 2 on 21%–45% of bars). Its information, if any,
   is in the tail where a real cycle pushes it out — the cosine law in §A4 is
   the clean case.
5. **NaN, never a sentinel,** on a flat window, a constant limb (40 bars
   earlier than a reader expects), a bad close, an overflowing close pair, and
   a window whose limb sums of squares overflow — three blanking rules and the
   bad-return filter, enumerated in §G and §H.
6. The **estimator** is the lagged pair's own Pearson correlation; the two ACF
   spellings are different columns (§A1).
7. **Gate E is measured: SHIP**, max |ρ| 0.0280 vs `ROLLING_LOW_250` over
   376,599 pooled bars, per-frame max median 0.0701, 0 of 89 frames ≥ 0.90
   (§E). It is nearly orthogonal to all 687 comparators — which is not the
   same as useful; see point 4 and §1.
8. On real BIST data it fires on **389,949 of 398,849** bars, i.e. everywhere
   outside the 100-bar warm-up of each frame (§C4), and its one rounding tell
   — a price level as top comparator — fires on the ranking only (§E2).
9. The nearest relative, catch22's `CO_FirstMin_ac` (issue **#130**), is not
   in this tree, so no run has priced the pair over real frames. §E4 carries
   the rule for when it lands.
