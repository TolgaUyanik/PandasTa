# `ts_ac1_60` — measured

Issue #94 (TS-AC1-60), ported 2026-11-13 on branch `issue-94-ts-ac1-60`.
Column: **`TS_AC1_60`**, `pandas_ta/statistics/ts_ac1_60.py`.
**Status: SHIPPED. Gates A–F measured. Gate E SHIP — max \|ρ\| 0.2536 vs
`mad_pct` over n = 393,509, per-frame max median 0.2545, run
`is94-ts_ac1_60-c9a3e8db` (2026-11-13) in `docs/gate_e_ledger.csv`. Nothing
struck, nothing removed.**

Every Gate A–D number in this file is printed by
`python docs/measure_ts_ac1_60.py`
(pandas 2.3.3 / numpy 1.26.4, Python 3.11) or by
`python -m pytest tests/test_ts_ac1_60.py -q`; every Gate E number, and the
real-data counts in Gate C, are copied out of the run's own
`overlap_max.csv`, `top25.csv`, `perframe.csv`, `degenerate.csv` and
`meta.json`. Nothing here was typed from expectation; where a number is *not*
measured — a piece of arithmetic, a derivation — the line says so.

## What it is

    r[t]      = close[t] / close[t-1] - 1
    m, v      = mean and POPULATION variance of the trailing `length` r
    TS_AC1[T] = sum((r[i] - m) * (r[i-1] - m)) / ((length - 1) * v)

over the `length - 1` pairs inside the window, NaN where `v <= 8.27e-25` or
where the accumulator trust test below fails. At the default `length = 60`
the window is 60 returns, so **61 closes**, and the first value lands on bar
60.

`lag` is deliberately **not** a parameter: the issue fixes it at 1 and the
column's name says so, so a `lag` keyword would let a caller emit a
`TS_AC1_*` column that is not a lag-1 autocorrelation
(`tests/test_ts_ac1_60.py::test_lag_is_not_a_parameter` asserts the
signature).

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue names tsfresh's `feature_calculators` (MIT) and states the formula:

> `autocorrelation(x, lag=1) on 60 returns`

⚠ **tsfresh is not installed in this worktree and web access is
unavailable.** Its own code was not read in this session. So the attribution
is an attribution, not an oracle: Gate A below is against the issue's line
plus the published definition of that function —

```python
y1, y2 = x[:len(x) - lag], x[lag:]
x_mean = np.mean(x)
sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
v = np.var(x)
return np.NaN if np.isclose(v, 0) else sum_product / ((len(x) - lag) * v)
```

— and anything tsfresh does that those do not state (how it treats NaNs,
what it returns for a series shorter than `lag`) is **unverified here**.

### ⚠ This column is NOT what issue #94's screen measured

The screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_ac1_60`, gitignored and local to the owner's machine) is

    def _(o, h, l, c, v):
        r = ret(c)
        return corr(r, delay(r, 1), 60)

— a **Pearson** correlation of two 60-pair slices, with two means and two
standard deviations, reading 61 returns and so 62 closes. tsfresh's
`autocorrelation` uses the window's *single* mean, the *population* variance
and a `(n - lag)` denominator over 60 returns. The issue's own "Gates owed"
line says *Gate A starts from the source formula, not the prototype*, so the
source formula is what ships. Measured on a 1,500-bar walk, port against
prototype:

| | value |
|---|---|
| Spearman | **0.988839** |
| max \|difference\| | **1.012516e-01** |
| bit-equal | **0 / 1,439** |
| NaN masks agree | no — first fired bar 60 here, 61 there |

So the screen's Gate E figures (max \|ρ\| 0.2534 vs `mad_pct`,
n = 393,420, SHIP) were measured on a **different column**, and were
indicative only. The run that decided ship or revert is the one in Gate E
below, on this module: 0.253571 vs the same comparator over n = 393,509,
SHIP — within 0.0003 of the screen, which is a result and not a reason the
screen's figures could have been copied. The prototype was read, retyped here and also
imported out of the owner's tree: the retype and the registry entry agree
**bit-for-bit on 1,439 of 1,439 bars**, so the comparison above is against
the real candidate and not against a paraphrase of it.

## Gate A — correctness

**A1. Windows with a closed form.**

| window | derivation | module |
|---|---|---|
| `close = [1, 2, 1, 2, 1]` at `length=4` | returns [+1, −1/2, +1, −1/2], deviations ±3/4, three products of −9/16, variance 9/16 → **exactly −1** | `-1.0`, **bit-exact**; bars 0..3 NaN |
| any window alternating two values in equal counts, any `length` | every one of the `length − 1` products is `−d²` and the variance is `d²` → **exactly −1** (derivation) | 1,500-bar alternating frame at `length` 60: max \|value + 1\| **5.440e-15** over 1,440 bars, 25 of them bit-equal to −1.0 (the closes are built by a cumulative product, so the returns are no longer exactly ±d) |
| `length = 2` | mean `(a+b)/2`, one product `−(a−b)²/4`, variance `(a−b)²/4` → **identically −1** (derivation) | the oracle reads exactly −1.0 at three seeds; the module's minimum `length` is **3** precisely because of this |

**A2. The reachable bounds, derived and attained.** The numerator is
`y'Ty` with `y` the demeaned window and `T` the lag-1 product form
(zero diagonal, ½ on the first off-diagonals), and the divisor is
`(length − 1)·y'y/length`, so the column is a Rayleigh quotient of `T` on the
subspace orthogonal to the all-ones vector, scaled by
`length/(length − 1)`. That scaling is 1.016949 at `length` 60; the demeaning
makes the reachable ends slightly tighter:

| `length` | min | max | module on the matching eigenvector window |
|---|---|---|---|
| 4 | **−1.078689325833** | **+0.412022659167** | 6.7e-16 / 5.6e-17 away |
| 10 | **−1.066103304016** | **+0.934726147590** | 4.4e-16 / 0.0 away |
| 60 | **−1.015600769374** | **+1.011559195540** | 6.7e-16 / 8.9e-16 away |

At short lengths the positive end is far from +1 (+0.412 at `length` 4),
which is why both ends are quoted per length rather than as "about ±1". The
column also stays inside these bounds on a walk, a tick-rounded walk and an
AR(1) path at each of the three lengths (asserted in the test module).

**A3. Against the source formula applied window by window** with
`sliding_window_view` — the mean, variance and products formed inside each
window, no pandas rolling anywhere, so it shares no window machinery with the
module:

| frame | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| walk | 4.926615e-15 | 3/1440 | 1.000000 | equal |
| tick-rounded walk | 2.831069e-15 | 10/1440 | 1.000000 | equal |
| AR(1), φ = +0.5 | 2.109424e-15 | 98/1440 | 1.000000 | equal |

**A4. Against an EXACT rational oracle** in `fractions.Fraction` (every close
is a rational, so every return and the whole statistic is one; the only
rounding is the final conversion), 120 bars per frame:

| frame | module | `math.fsum` scalar loop | window-by-window | **plain raw-sum expansion** |
|---|---|---|---|---|
| walk | 3.136380e-15 | 9.992007e-16 | 1.026956e-15 | 1.165734e-15 |
| tick-rounded | 1.040834e-15 | 1.602017e-15 | 1.607655e-15 | 1.600716e-15 |
| `|mean| / sd` = 1e5 | **2.089262e-10** | 1.749473e-10 | 1.749474e-10 | **4.109100e-06** |

Two things come out of that table.

* On ordinary frames the four spellings are the same to within a factor of
  about three, and the module is not the most accurate of them — it is
  3.1e-15 on the walk against the `fsum` loop's 1.0e-15. That is the claim:
  same order, not best.
* The last row is why the numerator is spelled
  `length*var − ((oldest−m)² + (newest−m)² + Σ(x[i]−x[i-1])²)/2` instead of
  the algebraically identical `Σx[i]x[i-1] − m((length+1)m − oldest −
  newest)`. On a path whose returns have a mean 1e5 times their dispersion —
  still far above the variance floor — the raw-sum expansion is **2.3e+04
  times worse** than this spelling, and this spelling is within 1.2× of the
  `fsum` loop. The identity used is `2uv = u² + v² − (u−v)²` with
  `u = x[i] − m`, `v = x[i-1] − m`, whose difference `x[i] − x[i-1]` does not
  contain `m` at all.

**A5. The degeneracy guard, which is NOT the source's.** tsfresh returns NaN
when `np.isclose(v, 0)`, which at numpy's default `atol = 1e-8` empties every
window whose return **sd** is below 1e-4. This port floors the variance at
`(4096 eps)²` = 8.27e-25 (an sd of 9.09e-13) instead — the same comparison
`statistics/ts_c3_20.py` makes on a return standard deviation, squared
because the divisor here is a variance. Measured on 300-bar frames (240
windows each):

| frame | this module | tsfresh's `isclose` guard | unguarded | min window variance |
|---|---|---|---|---|
| walk | 240 | 240 | 240 (max \|value\| 0.2711) | 1.359e-04 |
| tick-rounded walk | 240 | 240 | 240 (0.1381) | 2.014e-04 |
| 1%-a-bar geometric ladder | **0** | 0 | **240** (0.8328) | 1.211e-32 |
| flat 50.0 | 0 | 0 | 0 | 0.000e+00 |
| walk, σ = 1e-6 | **240** (max 0.2701) | **0** | 240 | 6.049e-13 |
| walk, σ = 1e-9 | **240** (max 0.2701) | **0** | 240 | 6.049e-19 |

The two rows that matter: the ladder, whose returns are mathematically
constant but vary at float rounding level, is reported on by an unguarded
spelling 240 times with values up to 0.8328 — plausible-looking numbers out
of nothing — and the low-volatility walks, which are genuinely fine data that
tsfresh's absolute threshold would throw away entirely.

**A6. The readings the wording leaves open**, each decided and each priced
against the port on the same 1,500-bar walk:

| reading, and what this port does | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|
| the window's **single mean and population variance** (the source's). Rejected: the prototype's Pearson correlation over 60 **pairs** / 61 returns | 1.012516e-01 | 0/1439 | 0.988839 |
| the same, against a Pearson correlation (`pandas.Series.autocorr`) over this port's **own** 60 returns | 1.405030e-02 | 0/1440 | 0.999901 |
| divide by **`(length − lag)·v`** (the source's). Rejected: `length·v`, the usual biased estimator | 4.650237e-03 | 0/1440 | **1.000000** |
| **population** variance (`ddof=0`, the source's `np.var`). Rejected: the sample variance | 4.650237e-03 | 0/1440 | **1.000000** |
| returns are **simple** (`close/close.shift(1) − 1`), the prototype's `ret`. Rejected: log returns | 5.501444e-03 | 0/1440 | 0.999883 |
| `length` is 60 **returns** (61 closes). Rejected: 60 closes, i.e. 59 returns | 1.110808e-01 | 0/1440 | 0.989106 |

Three notes on that table:

* **Rows 3 and 4 are the same reading twice.** `v_sample = v_pop·n/(n−1)`, so
  dividing by `(n−1)·v_sample` is dividing by `n·v_pop`: both variants are
  this column times exactly `59/60`. Measured: `port · 0.983333` reproduces
  each to **4.843e-15**, and the two variants agree with each other to
  **5.551115e-17** (bit-equal on 1,351 of 1,440 bars). Invisible to anything
  ranking the column; worth up to 4.7e-03 to a rule with a threshold.
* The Pearson normalisation on the *same* window (row 2) is closer to this
  port than the prototype is (0.999901 against 0.988839), so most of the
  prototype gap is the extra bar of history and not the normalisation.
* The 60-CLOSES reading needs one close less of history and so has a
  different NaN mask; it is the off-by-one a reader makes, priced here so it
  is not re-argued.

## Gate B — causality, by mutant

A future-perturbation sweep: replace every bar from `J` onward with a
different path and check whether anything strictly before `J` moved.
35 values of `J` (100 to 1,460 in steps of 40). Prefix truncation alone
cannot see back-dating, which is why this is a perturbation sweep.

**The real module leaks at 0 of 35 offsets** on each of a walk, a
tick-rounded walk and an AR(1) path.

Six mutants, each `importlib`-read and `exec`'d in memory, all 18
mutant × frame cells **35/35 caught**, every mutation verified live
(`not mutant.equals(real)`):

| mutant | what it does |
|---|---|
| `write_shift` | the numerator back-dated by `length` |
| `forward_return` | `r = px.shift(-1) / px - 1` |
| `forward_oldest` | the window's oldest return read from the future |
| `centered_var` | `center=True` on the variance |
| `centered_mean` | `center=True` on the mean |
| `centered_gap` | `center=True` on the squared-difference sum |

The four `length`-dependent mutants re-run at `length` 3 and 250, where the
real module still leaks **0/35**:

| mutant | `length` 3 | `length` 60 | `length` 250 |
|---|---|---|---|
| `write_shift` | 35/35 | 35/35 | 31/35 |
| `forward_oldest` | 35/35 | 35/35 | 31/35 |
| `centered_var` | **22/35** | 35/35 | 31/35 |
| `centered_gap` | **0/35** | 35/35 | 31/35 |

**Six** of those eight non-default cells are not 35/35 — all four at
`length` 250, plus two at `length` 3 — under three explanations, and each
explanation is **asserted** in the test rather than argued:

* **31/35 at `length` 250** misses exactly J = 100, 140, 180 and 220, the
  four offsets below a 250-bar warm-up, where the whole prefix is NaN and
  there was nothing to move.
* **22/35 for the centred variance at `length` 3**: a 3-wide centred window
  reads exactly one bar ahead, so the only bar it can move is `J − 1`, and at
  13 of the 35 offsets that bar is NaN in *both* runs — at `length` 3 the
  column's own NaN rate is high (62 of the first 100 bars fire). ⚠ This is a
  limit of the sweep, not a clean bill: the look-ahead is real and is caught
  at the other 22 offsets.
* **0/35 for the centred squared-difference sum at `length` 3** is a mutation
  that does nothing: that window is `length − 1` = 2 wide and pandas centres
  by `(window − 1) // 2` = 0 bars, so `center=True` is `center=False`.
  Asserted with `equals()`.

`offset` is this fork's standard parameter; a negative one is a user-reachable
look-ahead that the caller asks for explicitly, pinned by
`test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask`.

## Gate C — reachability

**Synthetic frames** (1,500 bars each, `length` 60):

| frame | fires | distinct | non-zero | min | max |
|---|---|---|---|---|---|
| walk | 1440/1500 | 1440 | 1440 | −0.243484 | +0.279014 |
| tick-rounded walk | 1440/1500 | 1440 | 1440 | −0.383535 | +0.333779 |
| AR(1), φ = +0.5 | 1440/1500 | 1440 | 1440 | +0.155686 | +0.690665 |
| AR(1), φ = −0.5 | 1440/1500 | 1440 | 1440 | −0.698196 | −0.118671 |

**Real data**, from Gate E's run `is94-ts_ac1_60-c9a3e8db` over the 89 frozen
ALTPORT-1 BIST frames (2026-11-13):

| | measured |
|---|---|
| pooled bars | 398,849 |
| `TS_AC1_60` non-NaN | **393,509** |
| non-zero | **393,509** |
| NaN | 5,340 |

So the column fires, and no fired bar is exactly 0.0.

**The 5,340 NaN bars are exactly 60 × 89** (arithmetic: 60 × 89 = 5,340),
i.e. the warm-up and nothing else — so **none** of the three things that make
this port differ from the source formula off clean data emptied a window on
real BIST data: the variance floor of 8.27e-25, the per-return square bound,
and the accumulator trust test. On the 89 frames every post-warm-up window
had a return variance above the floor, every return inside the square bound,
and an online variance and squared-difference sum inside the bounds their own
window range allows. Pinned by
`tests/test_ts_ac1_60.py::test_the_ledger_row_carries_the_measured_gate_e_numbers`.

That is the claim the synthetic tables above could not make: they show the
guards are *harmless on seven clean synthetic frames* (0 bars cost), and this
shows they cost 0 bars on 398,849 real ones.

## Gate D — scale

**Bit-identical** under ×8 and ×64, because every input is a price ratio and
`8a / 8b` is the same double as `a / b`:

| frame | ×8 | ×64 | NaN masks |
|---|---|---|---|
| walk | 1440/1440 | 1440/1440 | equal |
| tick-rounded walk | 1440/1440 | 1440/1440 | equal |
| AR(1), φ = +0.5 | 1440/1440 | 1440/1440 | equal |

and at non-default lengths on the walk: **1,497/1,497** at `length` 3,
1,480/1,480 at 20, 1,250/1,250 at 250 (both ×8 and ×64).

**Within tolerance** under ×10 and ×3.7 — they perturb the returns in their
last bits — with NaN masks equal and Spearman 1.000000 everywhere:

| frame | ×10 | ×3.7 |
|---|---|---|
| walk | 7.522e-15 | 8.382e-15 |
| tick-rounded walk | 8.826e-15 | 4.358e-15 |
| AR(1), φ = +0.5 | 4.274e-15 | 6.273e-15 |

**Why the return is a ratio and not a difference of logs.** On the walk the
ratio returns are bit-equal at ×8 on **1,499 of 1,499** bars and the
difference-of-logarithms returns on **821** (that count is CPU float detail;
only "some but not all" is pinned in the test).

`0 < fires < n` on every frame above (1,440 of 1,500), with 1,440 distinct
values, so no constant column can pass.

## What the column means

**It is invariant to an AFFINE map of the returns**, which is its strongest
property: both numerator and divisor scale by `a²` under `x → a·x + b`, and
the shift cancels in the deviations. Measured on a 1,500-bar walk, with NaN
masks equal and Spearman 1.000000 in all three cases:

| transform | max \|difference\| |
|---|---|
| returns ×2 (closes rebuilt) | 3.982925e-15 |
| returns ×0.5 | 9.617307e-15 |
| +0.004 of log drift a bar | 2.738088e-14 |

So it is neither volatility nor direction. Against the **same window's** other
statistics on that walk: Spearman **−0.0965** against the window's standard
deviation, **+0.0560** against its mean return, **−0.0073** against the
absolute mean return.

Against the fork's existing columns that take a lag-1 serial dependence of
their own input. `git grep -n "shift(1))" -- pandas_ta` returns exactly two
modules that feed `shift(1)` to `.corr(` or `.cov(`:
`momentum/a101_048.py:68` and `volatility/roll_spread.py:20` (the other hits
are `close / close.shift(1)` returns and `shift(1)` comparisons). Both read
close **differences** rather than returns, and both wrap the statistic in
something else:

| column | what it is | Spearman | n |
|---|---|---|---|
| `a101_048` | 250-bar lag-1 autocorrelation of close differences, times `d/close` over a squared-change sum | **−0.0201** | 1,249 |
| `roll_spread`'s `ROLL_20` | 20-bar lag-1 auto**covariance** of close differences, kept only where it is negative, then `2·sqrt(−cov)/close·100` | **−0.2349** | 800 |

Neither is this column. Redundancy against the 687 comparators is decided in
Gate E below: SHIP at 0.2536, and neither `a101_048` nor `ROLL_20` appears
anywhere in that run's `top25.csv` — whether either is in a comparator set at
all is not something this worktree can see, so no claim is made about it.

**For iid returns it is centred just below zero and wide.** 2,000 independent
60-return windows: median **−0.0106**, mean −0.0134, sd **0.1222**, p10
−0.1797, p90 +0.1418, positive on 45.70%, finite on 2,000 of 2,000. The
small negative centre is this estimator's own small-sample bias, about
`−1/(length − 1)` = −0.0169, and the spread about `1/sqrt(length)` = 0.1291
(both arithmetic, not measured). A single reading of ±0.1 therefore says
almost nothing.

**It orders the AR(1) coefficient**, which is the claim. Paths whose LOG
returns are an AR(1) with coefficient φ (population lag-1 autocorrelation
exactly φ); the column reads simple returns, a monotone transform:

| φ | median | p10 | p90 |
|---|---|---|---|
| +0.50 | +0.5030 | +0.3490 | +0.6114 |
| +0.25 | +0.2699 | +0.0999 | +0.3906 |
| 0 | +0.0283 | −0.1437 | +0.1676 |
| −0.25 | −0.2180 | −0.3733 | −0.0652 |
| −0.50 | −0.4683 | −0.6122 | −0.3296 |

The **level** is shrunk by a short window and grows with it — on a
20,000-bar φ = +0.5 path the median is 0.3797 / 0.4655 / 0.4871 / 0.4975 at
`length` 20 / 60 / 200 / 1000 — so only the ordering is claimed.

**It is a slow state, not an event flag.** Two consecutive windows share 59
of their 60 returns, so the column autocorrelates at **0.9760** at lag 1,
0.2813 at lag 30 and −0.2129 at lag 60 (measured on a walk).

## Guards

### The per-return square bound

Every kept return satisfies `r² < max/(8·length)`, a ceiling of
**6.120e+152** on `|r|`, so `length·var` and the summed squared differences
each stay inside half the float range — pandas accumulates both ONLINE, and
an infinite accumulator never leaves the window. Measured on a 400-bar walk:

| planted in a 400-bar walk | guarded | unguarded |
|---|---|---|
| one close of 1e-300 at bar 200, whose NEXT return is about 1e+302 — **one** return over the ceiling | 60 bars emptied (201..260) | **199** bars (201..399, the rest of the frame) |
| closes of 1e-200 at bars 200 **and** 230 — **two** returns over it, 30 bars apart | 90 bars (201..290), the union of two 60-bar spans | **199** bars (201..399) |

The second row is what makes the locality claim structural rather than a
one-shape measurement: two spoiled returns cost the union of their own
windows and nothing more, while the unguarded spelling runs to the end of the
frame in both cases.

### The accumulator trust test

`rolling.var` and `rolling.sum` are online, so a single enormous return
leaves a **finite** residue in both long after it has left the window — a
plausible-looking number rather than a NaN. The test compares both against
exact bounds from the window's own range `s = max − min`, which
`rolling.max`/`rolling.min` compute by a deque and therefore locally: a
population variance cannot exceed `(s/2)²`, and `length − 1` squared
successive differences cannot exceed `(length − 1)·s²`. The slack is 4096 eps
relative, the same constant as the floor.

Magnitude sweep of ONE planted giant return at bar 200 of a 400-bar walk. The
"oracle gap" is max \|module − per-window oracle\| over bars 261..399, i.e.
**after** the planted return has left every window:

| planted return | module: bars emptied | tail NaN | tail oracle gap | without the trust test |
|---|---|---|---|---|
| ~1e+2 | 0 | 0 | 1.324e-09 | same |
| ~1e+4 | 0 | 0 | 3.296e-06 | same |
| ~1e+6 | 0 | 0 | 8.463e-03 | same |
| ~1e+8 | 139 | 139 | — | 0 NaN, gap **1.280** |
| ~1e+20 | 140 | 139 | — | 0 NaN, gap 1.282 |
| ~1e+100 | 139 | 139 | — | 139 NaN |
| ~1e+140 | 139 | 139 | — | 139 NaN |
| ~1e+152 | 140 | 139 | — | 0 NaN, gap 1.282 |
| ~1e+153 (over the square bound) | 60 | 0 | 4.910e-14 | same |
| ~1e+160 | 60 | 0 | 4.910e-14 | same |
| ~1e+200 | 60 | 0 | 4.910e-14 | same |
| ~1e+300 | 60 | 0 | 4.910e-14 | same |

That is every exponent the script sweeps, in order; none is dropped.

Read that table as two facts, not one:

* The trust test turns the gross case into NaN. A planted return of 1e+8 — a
  decimal-point error in a feed, well inside the square bound — otherwise
  moves **139 bars that hold no part of it** by up to 1.280, on a column
  whose whole range is about ±1.
* ⚠ **It is not a cure at every magnitude.** 1e+2, 1e+4 and 1e+6 all pass it,
  because the variance stays inside the bound its range allows, and the tail
  is still 1.3e-09 / 3.3e-06 / 8.5e-03 away from a per-window oracle. A 100×
  bar is a thing a market can do, and it costs 1.3e-09; 1e+6 is a broken
  feed. This is an inherited pandas limit, disclosed with its numbers rather
  than implied away.

**What it costs on clean data: nothing measured.** Bars lost to the trust
test, and the ratio of pandas' online variance to its exact bound:

| frame | fires | bars the test costs | max `var / (s/2)²` |
|---|---|---|---|
| walk | 1440 | 0 | 0.316482281433 |
| tick-rounded walk | 1440 | 0 | 0.279397409815 |
| AR(1), φ = +0.5 | 1440 | 0 | 0.277267242971 |
| AR(1), φ = −0.5 | 1440 | 0 | 0.296542423523 |
| alternating (the equality case) | 1440 | 0 | **1.000000000000** |
| walk, σ = 1e-6 | 1440 | 0 | 0.316448900686 |
| fine tick 50 / 0.01 | 240 | 0 | 0.344627535409 |

The alternating frame attains the variance bound exactly, which is why the
slack is 4096 eps relative rather than zero.

### NaN rules, measured

A bad close is missing data: NaN, zero, negative, infinite and subnormal
(1e-310) closes each empty exactly **61 bars (200..260)** when planted at bar
200 of a 400-bar walk — the `length + 1` closes one value reads, because it
spoils two returns — and **0 bars before the hole move**, for all five.

A flat run empties a window only when it covers all `length + 1` closes:
**60 identical closes empty 0 bars, 61 empty exactly bar 260, 65 empty bars
260..264.**

The floor bounds the **dispersion** of the returns, not their size. A tick
grid quantises the return level at `tick/price` but the dispersion of
consecutive returns at about `(tick/price)²`, so the familiar "one tick over
a price of 1e6 is 1e-9" is not a comparison against this floor. On monotone
one-tick-per-bar paths:

| price / tick | \|r\| | window variance | fires |
|---|---|---|---|
| 50 / 0.01 | 1.888e-04 | 3.893e-13 | 240/300 |
| 1e6 / 0.001 | 1.000e-09 | 1.198e-32 | **0**/300 |
| 1e6 / 0.01 | 1.000e-08 | 2.987e-30 | **0**/300 |

The last two are the right answer: a window whose returns are that nearly
constant has no autocorrelation to measure.

### Parameters

| `length` | column name | fires on a 400-bar walk |
|---|---|---|
| `None`, 0, −5, 2, 0.5, 2.9 | `TS_AC1_60` (fallback) | 340 |
| 3, 3.9 | `TS_AC1_3` | 397 |
| 250 | `TS_AC1_250` | 150 |

`length + 1` closes exactly gives 1 fired bar; `length` closes returns
`None`.

## Gate E — attribution

**SHIP.** Run `is94-ts_ac1_60-c9a3e8db`, measured 2026-11-13 by issue-solver
on the committed module with
`gate_e_overlap.py run --module pandas_ta.statistics.ts_ac1_60`, recorded in
`docs/gate_e_ledger.csv` by `python docs/gate_e_ledger.py record`.

| | measured |
|---|---|
| column | `TS_AC1_60` |
| max \|ρ\| | **0.25357121838081886** |
| against | **`mad_pct`** (the `ml_features` manifest set) |
| n | **393,509** |
| per-frame max median \|ρ\| | **0.25448160586504526**, also against `mad_pct` |
| frames | 89 |
| verdict | **SHIP** under `r3-perframe-0.90` (0.2536 < 0.76 pooled, 0.2545 < 0.90 per-frame) |

The pooled maximum **within each comparator set separately**: `mad_pct`
0.25357121838081886 over the 358 manifest columns, `BB_BWidth`
0.25288878184999175 over the 329 `compute_all` columns, both over n = 393,509.
687 comparators were read and **1** was degenerate — `squeeze_SQZ_NO`,
constant over the pooled sample, so it carries no ρ.

Run facts, from `meta.json`: default parameters (`kwargs` empty, so
`length = 60`), 89 frames, 398,849 pooled bars, 329 + 358 = 687 comparators,
canary **`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS` bit-equal**, data stamp
`1be6495e`, module sha1 `20b9f3c7`, `pandas_ta` tree sha1 `001b1a2b`,
pandas 2.3.3 / numpy 1.26.4.

**The top five, and why nothing here is close to the line.** Each row is the
pooled ρ with the per-frame distribution over the 89 frames:

| against | set | pooled ρ | n | per-frame median | per-frame max | frames ≥ 0.90 | ≥ 0.80 |
|---|---|---|---|---|---|---|---|
| `mad_pct` | manifest | +0.253571 | 393,509 | 0.254482 | 0.454113 | **0.0%** | **0.0%** |
| `BB_BWidth` | compute_all | +0.252889 | 393,509 | 0.249630 | 0.488434 | 0.0% | 0.0% |
| `Swing_Range_pct` | manifest | +0.246651 | 393,509 | 0.246632 | 0.490319 | 0.0% | 0.0% |
| `chop` | compute_all | −0.188402 | 393,407 | 0.192673 | 0.350084 | 0.0% | 0.0% |
| `natr` | compute_all | +0.182591 | 393,509 | 0.175794 | 0.508893 | 0.0% | 0.0% |

The single worst per-frame \|ρ\| anywhere in the top five is **0.508893**
(`natr`) — 0.391 below the 0.90 line (arithmetic) — and `pct_frames_ge_090`
and `pct_frames_ge_080` are **0.0 on all five rows**, so no frame reaches
even 0.80 against any of them. The band applies to the per-frame *median*,
which tops out at 0.254482.

**The five are volatility-width measures — read from their names and
definitions, not measured here.** `mad_pct`, `BB_BWidth`, `Swing_Range_pct`
and `natr` are dispersion columns and `chop` is a range-efficiency one. The
next rows of `top25.csv` repeat that family through percentiles, states and
regime flags — `BB_BWidth_Pctl` 0.1646, `mad_pct_Pctl` 0.1638,
`mad_pct_State` 0.1579, `Swing_Range_pct_State` 0.1571, `BB_Width_Regime`
0.1399 — alongside distance-to-level columns (`dist_low_60` 0.1652,
`Dist_to_BB_Lower_pct` 0.1595, `Dist_to_Nearest_Fib_pct` 0.1436) and two
ages (`Supertrend_Flip_Age` −0.1386, `BB_Squeeze_Age` 0.1312); the 25th and
last row is `THERMO_pct` at 0.1239, so the whole list the harness prints lies
under 0.254. So the comparator nearest a lag-1 return autocorrelation is a
**volatility width**, at about 0.25 — which the synthetic section above would
not have predicted: it measured Spearman **−0.0965** against the *same
window's* standard deviation, the opposite sign and a third the size.

Those two are not in conflict, and the difference is worth naming rather than
averaging away: the synthetic figure is one 1,500-bar walk against the window's
own sd, the Gate E figure is 89 real frames and 393,509 bars against a
398,849-bar engine column. Taken at face value the run says that on real BIST
data a **positive** reading of this column — persistent, trending returns —
co-occurs with a wider `mad_pct`, weakly (pooled ρ = +0.253571; the per-frame
file records absolute values only, so per-frame sign is not measured here).
That reading is an interpretation of the pooled sign, not
a measurement; what is measured is 0.253571, and it is a long way under the
0.76 line, so the column is not a restatement of a volatility width.

⚠ **The issue's screen numbers were measured on the prototype, and they
nearly reproduced anyway.** The screen reported max \|ρ\| 0.2534 vs
`mad_pct`, n = 393,420, top-5 per-frame max median 0.2559, SHIP; this run
reports 0.253571 vs the same comparator, n = 393,509, per-frame max median
0.254482, SHIP. Its next two comparators were `BB_BWidth` 0.2526 and
`Swing_Range_pct` 0.2469 against this run's 0.252889 and 0.246651 — the same
three columns in the same order, each within 0.0003. The two sample sizes
differ by exactly **89 bars, one per frame** (393,509 − 393,420, arithmetic),
which is the extra close the prototype's 61-return window needs.

That agreement is a **result, not a licence**: the two statistics differ by up
to 0.1013 bar-to-bar at Spearman 0.988839 (above), so the screen's figures
were correctly called indicative rather than a receipt — a 0.9888 rank
correlation does not bound the gap between two maxima over 687 comparators,
it just happened to be small here. The receipt is this run.

The issue's stage-2 fork overlap (max \|ρ\| 0.2310 vs `vhf:VHF_28` over 12
frames) was also measured on the prototype, on the fork's own `Category`
outputs rather than on the two Gate E comparator sets, and is **not**
re-measured here. No `vhf` column appears anywhere in this run's
`top25.csv`, `perframe.csv` or `degenerate.csv`, so the run neither confirms
nor refutes that figure.

## Gate F — suites

`python -m pytest tests/test_ts_ac1_60.py -q` → **116 passed** (115 at the
porting commit; the receipt replaced the one test that asserted the ledger
carried no row with two that pin the row it now carries).

Full suite, this worktree, after recording the row: **3 failed, 6,575
passed, 83 skipped** (147 s). The three failures are the two `CLAUDE.md`
*Known breaks*
(`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, and
`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
which needs the sibling `../AlternativeRepos` checkout and is deselected in
CI) plus `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
which now reports exactly `['mtd_ret']` — issue #206's, owed on `dev` — where
at the porting commit it reported `['mtd_ret', 'ts_ac1_60']`. So this port
owes Gate E nothing. (A local run fails there; CI into `dev` sets
`GATE_E_PENDING_OK=1` and skips it.) The launcher runs both repositories'
suites in clean worktrees.

## Cost

400,000-bar input, best of three, `tracemalloc` peak:

| | time | peak |
|---|---|---|
| `length` 3 | 71 / 73 / 71 ms | 38.8 MB |
| `length` 20 | 73 / 80 / 72 ms | 38.8 MB |
| `length` 60 | 73 / 88 / 72 ms | 38.8 MB |
| `length` 250 | 72 / 90 / 73 ms | 38.8 MB |
| the trust test's two extrema (same code path, flag flipped) | 73 against 66 ms, then 71 against 64 ms | 36.0 MB against 35.6 MB |
| the window-by-window oracle, for contrast | 292 ms, then 300 ms | **406.4 MB**, both times |

Three runs of the same four lengths are quoted because the first two
disagreed: 71/73/73/72, then 73/80/88/90 (a round-1 reviewer's run on the
same machine), then 71/72/72/73.

What does not grow with `length` is the **traced peak — 38.8 MB at every one
of the four, in all three runs** — and the work, which is five O(n) passes
(mean, variance, the squared-difference sum, and the two extrema) whatever
the window. The wall-clock times do NOT reproduce to the millisecond, so read
them as a band of roughly 70–90 ms rather than as four numbers, and read the
comparison against the oracle (about 4× the time and 10× the memory, the
memory reproducing exactly) as the claim. That memory is why the oracle lives
in `docs/measure_ts_ac1_60.py` and not in the module.

## Wiring

Five touch points, all five done:

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_ac1_60.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_ac1_60 import ts_ac1_60` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `"ts_ac1_60"` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_ac1_60()` accessor |
| 5 | `tests/test_ts_ac1_60.py` | 116 tests |

Plus the counts that are asserted elsewhere: `README.md` (327 in `Category`,
335 accessors, statistics 36), `docs/IndicatorDictionary.md` (regenerated by
`python docs/gen_indicator_dictionary.py`, which tags `TS_AC1_60` **SF**),
`docs/MLCompanionContract.md` (672 tagged columns, 314 `SF`) and
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL = 327`).

And the ledger: `docs/gate_e_ledger.csv` carries one `ts_ac1_60` row, SHIP,
run `is94-ts_ac1_60-c9a3e8db`, measured 2026-11-13, no waiver. Nothing was
struck and nothing was removed, so the counts above are unchanged by the
Gate E run.
