# `ts_aggac_60` — measured (PandasTa issue #96, TS-AGGAC-60)

`TS_AGGAC_60_10` is the MEAN of the lag-1..lag-10 autocorrelations of the
trailing 60 simple returns, in tsfresh's normalisation — tsfresh
`feature_calculators.agg_autocorrelation(x, [{'f_agg': 'mean', 'maxlag': 10}])`
applied to 60 returns, which is what issue #96 asks for.

    x        = the window's 60 simple returns
    m, v     = their mean and their POPULATION variance (ddof=0)
    AC[k]    = sum over the 60-k pairs of (x[i]-m)*(x[i-k]-m) / ((60-k) * v)
    TS_AGGAC = (AC[1] + ... + AC[10]) / 10

Everything below is reproduced by `python docs/measure_ts_aggac_60.py`
(sections `a b cd meaning guards cost`). Every number in this file, in the
module docstring and in `tests/test_ts_aggac_60.py` comes from that script's
run on this machine, on 2026-11-13 — EXCEPT the Gate E section and the
real-data counts in Gate C, which come from the launcher's harness run
`is96-ts_aggac_60-d6ed198b` and are quoted from its `overlap_max.csv`,
`top25.csv`, `perframe.csv`, `degenerate.csv` and `meta.json`. Figures that depend on the CPU's
floating-point kernels are quoted as measured here and pinned in the tests as
bounds, never as exact counts.

**Gate E: SHIP.** Run `is96-ts_aggac_60-d6ed198b`, measured 2026-11-13 by the
launcher on this module at default parameters: `TS_AGGAC_60_10` reads a pooled
max |ρ| of **0.2676** against `mad_pct` over n = 393,509, and a top-5 per-frame
max median of **0.2634** against `MACD_Cross_Age` over the 89 frames. The
section *Gate E* below has the numbers; `docs/gate_e_ledger.csv` carries the
row and `tests/test_ts_aggac_60.py` pins both its identity and its figures.

---

## Gate A — correctness against the source

### A1. Windows with a closed form

An alternating window has deviations `±d`, so every one of its `60-k` lag-`k`
products is `(-1)**k * d**2` and its population variance is `d**2`:
`AC[k] = (-1)**k` exactly. The mean over an EVEN `maxlag` is then a sum of
`±d**2` that cancels pair by pair, and over an odd one it is `-1/maxlag`.

| frame | length | maxlag | target | max \|module − target\| |
|---|---|---|---|---|
| alternating (cumprod) | 4 | 1 | −1.000000 | 9.326e-15 |
| alternating | 4 | 2 | 0 | 4.540e-15 |
| alternating | 10 | 1 | −1.000000 | 4.663e-15 |
| alternating | 10 | 2 | 0 | 2.507e-15 |
| alternating | 60 | 1 | −1.000000 | 1.110e-15 |
| alternating | 60 | 2 | 0 | 5.421e-16 |
| alternating | 60 | 9 | −0.111111 | 3.886e-16 |
| alternating | 60 | 10 | 0 | 3.659e-16 |

On `close = [1, 2, 1, 2, ...]`, where the returns are exactly +1 and −1/2 and
nothing in the arithmetic is a difference of unequal floats, the module reads
**bit-exact 0.0 on 20 of 20 fired bars** at `maxlag` 2 and at `maxlag` 10.
That is the assertion in
`test_an_alternating_window_is_exactly_zero_at_an_even_maxlag`.

### A2. The two published spellings of the source are the same number

The issue names `agg_autocorrelation`, which reaches its numbers through
`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=len(x) > 1250,
nlags=maxlag)[1:]`. `feature_calculators.autocorrelation(x, lag)` spells the
quotient directly. They are algebraically the same, because
`acovf(adjusted=True)[k]` divides by `len(x) - k` while `acovf[0]` divides by
`len(x)` — so `acovf[k]/acovf[0]` is `sum / ((n-k) * population variance)`.

That identity is the one place the two definitions could have disagreed, so
it is measured rather than asserted:

* over 200 random 60-point windows, `mean(autocorrelation(x, k) for k in
  1..10)` and `agg_autocorrelation(x)` agree to **3.469e-17**;
* **statsmodels IS installed in this worktree**, and the retyped adjusted
  `acf` used above reproduces `statsmodels.tsa.stattools.acf(x,
  adjusted=True, fft=False, nlags=10)[1:]` with max difference **0.000e+00**,
  i.e. bit-exactly. `tests/test_ts_aggac_60.py` skips that check if the
  package is ever absent, since it is not a dependency of this fork.

⚠ tsfresh itself is NOT installed here and web access is unavailable, so the
formula under test is the issue's line plus the published definitions of
those two functions, not a read of tsfresh's own code. Anything tsfresh does
that those do not state — how it treats NaNs, which `fft` branch it takes
above 1,250 points — is unverified here. The `fft` branch cannot matter at
`length` 60, which is the parameter the issue fixes.

### A3. Against the source formula, window by window

`sliding_window_view` over the returns, no pandas rolling anywhere, through
BOTH spellings of the source:

| frame | vs `autocorrelation(k)` averaged | vs the adjusted-`acf` path |
|---|---|---|
| walk | 5.666e-15, Spearman 1.000000 | 5.674e-15, Spearman 1.000000 |
| tick-rounded | 2.442e-15, Spearman 1.000000 | 2.456e-15, Spearman 1.000000 |
| ar1(+0.5) | 3.421e-15, Spearman 1.000000 | 3.435e-15, Spearman 1.000000 |
| seasonal(10) | 3.183e-15, Spearman 0.990891 | 3.183e-15, Spearman 0.990912 |

NaN masks identical on all four. The seasonal frame's Spearman is lower
because its returns repeat exactly every 10 bars, so the column repeats too
and the frame is full of NEAR-TIES that a 3e-15 disagreement reorders; the
absolute agreement there is the same 3e-15 as everywhere else, and it is
6e-12 of that frame's own range. A `math.fsum` scalar loop — plain Python,
no numpy, exact summation — agrees with the module to **3.338e-15** over 340
bars of a 400-bar walk.

### A4. Accuracy against an exact rational oracle

Every close is a rational, so the whole statistic is one: `fractions.Fraction`
all the way to a single final conversion.

| frame | module | `math.fsum` loop | window-by-window oracle | plain raw-sum expansion |
|---|---|---|---|---|
| walk (300 bars) | 2.384e-15 | 3.305e-16 | 3.391e-16 | 3.747e-16 |
| tick-rounded (300) | 1.200e-15 | 4.129e-16 | 4.111e-16 | 4.181e-16 |
| `|mean|/sd = 1e5` | **1.961e-10** | 7.981e-11 | 7.981e-11 | **1.326e-06** |

Read honestly: on an ordinary frame the module's rewritten numerator is about
**seven times** the error of an exact summation, and that is the price of the
rewrite. What it buys is the last row — on returns whose mean dwarfs their
dispersion the plain raw-sum expansion is **6.8e+03 times worse** than the
module, because it subtracts the window mean from a raw product sum and the
two cancel.

**Whose rounding is the 1.961e-10?** Not the divisor's. Feeding the module's
own numerator to the EXACT rational variance, with the division done in
`Fraction` so the only float left in it is the numerator, leaves the error at
**1.927e-10** (240 bars) — and on the walk the same substitution leaves
2.463e-15 against the shipped column's 2.384e-15. The error is therefore in
the numerator, and it is the cancellation in `x[i] - m` that every spelling
pays: the `math.fsum` loop, which holds no accumulated variance at all, still
lands at 7.981e-11 on the same frame. The module is 2.4× that floor; the
plain expansion is 1.7e+04× it.

An earlier draft of this file asserted the opposite — "the variance's error,
not the numerator's" — on the grounds that `math.fsum` and the oracle land
together. That was an inference, not a measurement, and the measurement above
(section `a`, *Gate A4b*) says it was wrong.

The rewrite is
`2*u*v = u**2 + v**2 - (u-v)**2` with `u = x[i]-m`, `v = x[i-k]-m`, whose
difference `x[i] - x[i-k]` contains no `m` at all, giving

    sum u*v = length*var - head[k]/2 - tail[k]/2 - gap[k]/2

with `head[k]` the squared deviations of the `k` oldest returns in the window,
`tail[k]` the `k` newest and `gap[k]` the sum of `(x[i] - x[i-k])**2` over the
window's `length - k` lag-`k` pairs. `head` and `tail` grow by one term per
lag, so the loop is `maxlag` passes and not `maxlag**2`.

### A5. The degeneracy guards — and the one that fabricates a value

300-bar frames, 240 fired windows each:

| frame | this module | tsfresh `autocorrelation` (`isclose(var,0)`) | tsfresh `agg_autocorrelation` (`abs(var) < 1e-10`) | unguarded |
|---|---|---|---|---|
| flat (every close 100) | 0/300 | 0/300 | **240 fabricated 0.0** | 0/300 |
| 1%-a-bar geometric ladder | 0/300 | 0/300 | **240 fabricated 0.0** | 240/300, up to 0.0603 |
| walk, sigma = 1e-6 | 240/300, up to 0.0663 | 0/300 | **240 fabricated 0.0** | 240/300, up to 0.0663 |
| walk, sigma = 1e-9 | 240/300, up to 0.0663 | 0/300 | **240 fabricated 0.0** | 240/300, up to 0.0663 |

Two things to take from that table.

1. `agg_autocorrelation`'s own guard does not skip a degenerate window — it
   returns the mean of a vector of zeros, i.e. **exactly 0.0**. That is an
   ORDINARY reading of this column: 25.50% of iid 60-return windows sit above
   it (section *What the column means*). A fabricated 0.0 is therefore
   invisible downstream, which is why this port reports NaN instead.
2. The threshold is on the variance of RETURNS, so it fires at a return
   standard deviation below 1e-5 — an ordinary low-volatility series. On the
   two walks above, where this column reports a perfectly normal ±0.066,
   tsfresh would hand the miner 240 zeros.

This module's floor is the fork's `4096 eps` on the standard deviation
(9.09e-13), squared into 8.27e-25 on the variance — the same constant
`statistics/ts_ac1_60.py` puts on exactly this variance. On the two genuinely
degenerate frames it agrees with both tsfresh guards; an UNGUARDED spelling
reports on 240 of the ladder's windows, up to 0.0603, out of nothing but
rounding.

### A6. Five readings the wording leaves open

All on the same 1,500-bar walk, against the shipped column:

| reading | Spearman | max \|difference\| | decided |
|---|---|---|---|
| log returns instead of simple | 0.999781 | 2.175e-03 | SIMPLE (the prototype's `ret`) |
| 60 CLOSES (59 returns) | 0.979126 | 4.026e-02 | 60 RETURNS, so 61 closes |
| `length*v` divisor (biased) | 0.995068 | 1.247e-02 | `(length-k)*v`, the source's |
| SAMPLE variance (ddof=1) | 1.000000 | 2.139e-03 | POPULATION, the source's |
| lags 0..10 instead of 1..10 | 1.000000 | 9.726e-02 | lags 1..10 |
| Pearson per lag, same window | 0.996854 | 1.070e-02 | one window mean and variance |

Notes on the three that are easy to get wrong.

* **The biased divisor is NOT one constant factor here.** At `maxlag` 1 it
  would be — `ts_ac1_60` prices it as exactly `59/60`. Averaging ten lags
  with per-lag weights `length/(length-k)` makes it a genuinely different
  ordering, Spearman 0.995068, which a rank miner can see.
* **`ddof=1` IS one constant factor**, `59/60`: Spearman exactly 1.000000, so
  only a threshold rule can see it, by up to 2.1e-03.
* **Lag 0 is identically 1.** Including it maps the column to
  `1/11 + (10/11)*TS_AGGAC` — an affine map, so Spearman is exactly 1 and the
  values move by up to 9.7e-02. `tests/test_ts_aggac_60.py::
  test_including_lag_zero_is_an_affine_map_the_rank_miner_cannot_see`
  reproduces that affine relation to 1e-12, so the off-by-one in
  `acf(...)[1:]` is not re-argued.

### A7. The screen prototype — a different column, read not guessed

Issue #96's prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_aggac_60`; that tree is gitignored, so a clone does not carry it) is

    r = ret(c)
    return sum(corr(r, delay(r, k), 60) for k in range(1, 11)) / 10

— ten PEARSON correlations of two 60-pair slices, each with two means and two
standard deviations, the lag-10 term reading 70 returns and so 71 closes.
The issue's own *Gates owed* says Gate A starts from the source formula and
not from the prototype, so the source formula is what ships.

* retype vs the owner's own registry entry: **bit-equal on 1,430 of 1,430
  bars**, identical NaN masks, so the comparison below is against the real
  prototype and not a paraphrase;
* module vs prototype: n = 1,430, max \|difference\| **4.722e-02**, bit-equal
  0/1,430, Spearman **0.902932**, NaN masks differ;
* first fired bar: **60** here, **70** for the prototype.

The screen's Gate E figures (max \|ρ\| 0.2815 vs `mad_pct`, n = 392,619,
per-frame max median 0.2814) were therefore measured on a DIFFERENT column.
The launcher's Gate E run on this module is the number that decides ship or
revert; a Spearman of 0.90 between the two is close enough that the screen's
figure is a reasonable prior and far enough that it is not a receipt.

### A8. The reachable bounds

The column is `length` times a Rayleigh quotient of the lag-weighted product
form `M = (1/maxlag) * sum_k A_k/(length-k)` (with `A_k` carrying ½ on each
`k`-th off-diagonal) restricted to the subspace orthogonal to the all-ones
vector, which is exactly what a demeaned window spans. Its reachable extremes
are therefore that form's extreme eigenvalues, and the module attains them on
the matching eigenvector window:

| length | maxlag | min | max | module − target (min, max) | Cauchy-Schwarz ceiling |
|---|---|---|---|---|---|
| 12 | 10 | −0.483954838541 | +0.185126534794 | 6.1e-16, 5.3e-16 | 2.423853 |
| 20 | 10 | −0.292703147946 | +0.259700334337 | 6.7e-16, 3.9e-16 | 1.437543 |
| **60** | **10** | **−0.310042715573** | **+0.915797875473** | 5.6e-17, 6.7e-16 | 1.103990 |
| 60 | 1 | −1.015600769374 | +1.011559195540 | 6.7e-16, 0.0 | 1.016949 |
| 60 | 5 | −0.367632424038 | +0.996051015834 | 1.7e-16, 4.4e-16 | 1.053280 |

The `maxlag` 1 row is `ts_ac1_60`'s own published range, which is a check on
both modules at once.

**The asymmetry is the interesting part.** At the default the floor is three
times nearer zero than the ceiling, because a window cannot be negative at
ten lags at once: the path that drives lag 1 to −1 alternates, and an
alternating path is **+1** at every even lag. A window CAN be positive at all
ten (a slow, smooth path), which is why the ceiling is near 1. Consumers who
expect a symmetric ±1 range will mis-scale this column.

The looser Cauchy-Schwarz ceiling `(length/maxlag) * sum_k 1/(length-k)` is
1.103990 at the default and is not attained, for the same reason.

### A9. Against this fork's own serial-dependence columns

Gate E's 687 comparators hold no pandas_ta port, so the in-fork overlap is
measured here or nowhere.

**Which columns.** The seven `Category` modules whose value is a function of
the SAME series at a fixed offset, enumerated by hand from
`pandas_ta/__init__.py`. An earlier draft of this file said "every shipped
module that takes a serial dependence of its own input, found by scanning
`pandas_ta/` for `.corr(`/`.cov(` against a `shift(` argument". That was
wrong twice: the grep missed `pandas_ta/statistics/g191_026.py:112-113`,
which is literally `close.shift(lag)` then `.corr(lagged_close)`, and the
criterion itself excludes the two columns that matter most here —
`lean_momersion_20`, whose value is `sign(r[t]) * sign(r[t-1])` averaged, and
`ts_cid_ce_20`, a sum of squared successive differences that
`docs/MLCompanionContract.md` itself calls a near-monotone restatement of the
lag-1 return autocorrelation. Neither contains a correlation call.

Spearman, on the four synthetic frames:

| column | walk | tick-rounded | ar1(+0.5) | seasonal(10) | n per cell |
|---|---|---|---|---|---|
| `ts_ac1_60` `TS_AC1_60` — this column's lag-1 term, same window | **+0.373855** | +0.000844 | **+0.378744** | −0.202691 | 1,440 each |
| `ts_c3_20` `TS_C3_20_1` — a lag-1 TRIPLE product over 20 returns | +0.098361 | −0.014184 | +0.031473 | **−0.533538** | 1,440 each |
| `g191_026` — typical price against its own 5-bar lag, 230-bar correlation | −0.283911 | −0.035710 | +0.097997 | +0.088153 | 1,266 each |
| `ts_cid_ce_20` `TS_CID_CE_20` — squared successive return differences, 20 returns | +0.037691 | −0.049566 | +0.055454 | +0.267978 | 1,440 each |
| `lean_momersion_20` — share of same-sign return pairs over 20 bars | −0.016117 | −0.047855 | +0.040824 | constant | 1,440 each |
| `a101_048` — 250-bar lag-1 autocorrelation of close DIFFERENCES | +0.028449 | +0.028332 | +0.006285 | −0.041912 | 1,249 each |
| `roll_spread` `ROLL_20` — 20-bar lag-1 autoCOVARIANCE, kept where negative | +0.024486 | −0.048445 | *+0.262906* | +0.089672 | 800 / 865 / **26** / 1,440 |

⚠ **The `roll_spread` / ar1(+0.5) cell is not evidence of anything.**
`ROLL_20` is NaN wherever the window's lag-1 autocovariance of close
differences is non-negative, and a path built to be positively autocorrelated
almost never produces a negative one — so that column fires on **26** of the
1,440 bars, and the +0.262906 printed beside it carries a standard error of
about 0.2. It is shown so the table is the whole run rather than its
comfortable part; it is excluded from the maximum below, and
`tests/test_ts_aggac_60.py` skips any pair with fewer than 200 overlapping
bars instead of passing a 0.76 bound on 26 samples.

Of the 28 frame/column pairs, **26 produce a usable number**: the
`lean_momersion_20` / seasonal pair is constant and so undefined, and the
`roll_spread` / ar1 pair has n = 26. The largest \|Spearman\| of those 26 is
**0.5335** (`ts_c3_20` on the seasonal frame), well below the 0.76 ship line
and far below the 0.90 strike line. Two readings worth keeping:

* the two lag-1 return statistics on the same window (`ts_ac1_60`,
  `ts_cid_ce_20`) are the ones a reader would expect to be high and are not —
  averaging ten lags genuinely moves the column;
* `lean_momersion_20` is CONSTANT on the seasonal frame (every return pair
  has the same sign pattern), so its Spearman there is NaN; the test skips
  that pair rather than passing on a NaN comparison, and this table says
  "constant" rather than quoting a number.

Run at `maxlag` 1 this module IS `ts_ac1_60`: max \|difference\| 5.551e-17,
bit-equal on 936 of 1,440 bars, identical NaN masks. The residue is the
division order — one `/(maxlag*v)` here against one `/((length-lag)*v)`
there — and it is a cross-check against code reviewed separately.

---

## Gate B — causality, as a mutant test

35 perturbation offsets (`range(100, 1500, 40)`): every bar from J onward is
replaced by a DIFFERENT path, and anything strictly before J that moves is a
leak. Prefix truncation cannot see back-dating, which is why the sweep is a
perturbation; `test_prefix_truncation_alone_would_not_catch_a_back_dated_
mutant` shows the `write_shift` mutant passing a truncation check that the
sweep fails it on.

**The real module leaks at 0 of 35 offsets** on each of a walk, a
tick-rounded walk and an AR(1) path.

Eight mutants, each `importlib`-read from the module's own source, one write
index moved, `exec`'d in memory. All eight are **live** (they compute a
different column) and all are caught **35/35 on every one of the three
frames**:

| mutant | what it does |
|---|---|
| `write_shift` | back-dates the whole column by `length` bars |
| `forward_return` | `px.shift(-1) / px` instead of `px / px.shift(1)` |
| `forward_head` | reads the window's oldest deviations from the FUTURE |
| `forward_tail` | reads the window's newest deviations from the future |
| `centered_var` | `center=True` on the variance |
| `centered_mean` | `center=True` on the mean |
| `centered_gap` | `center=True` on the per-lag squared-difference sum |
| `forward_diff` | `r.diff(-k)` instead of `r.diff(k)` |

### The ninth mutant, and the hole it exposes

`span = rolling.max() - rolling.min()` is the one write index none of those
eight perturbs, and it is not an oversight that can be closed by adding a
mutant to the list: `span` feeds ONLY the accumulator trust test, and the
guards section below measures that the trust test costs **0 bars on every
clean frame**. So a `center=True` on the two extrema is **live** — it changes
the column — and still caught **0 of 35** offsets on each of the walk, the
tick-rounded walk and the AR(1) path. Nothing moves there because nothing was
being rejected there.

On a 1,500-bar walk with one planted return of 1e+8 at bar 200, where
`trusted` actually bites, the same mutant is caught at **13 of 35** offsets —
the ones whose J sits within a centred window's reach of the spike — and the
real module is **0 of 35** on that frame too. That is the frame
`test_the_span_mutant_is_invisible_on_a_clean_frame_and_caught_where_the_
trust_test_fires` uses, and the test pins both halves: live-and-silent on the
clean frame, caught on the spiked one. A future edit that centres the extrema
would be a NaN-mask look-ahead that a clean-frame sweep cannot see, and that
is recorded here rather than papered over.

### Non-default lengths

At non-default lengths (12, 60, 250) the four length-dependent mutants are
caught 35/35 at 12 and 60, and **31/35 at 250**. The four quiet offsets there
are J = 100, 140, 180 and 220, all of them BEFORE the first fired bar at 250:
the script prints `fired bars before J [0, 0, 0, 0]` and `bar J-1 NaN in both
at every one of them: True`, so there is nothing to move. The real module is
0/35 at every one of those lengths.

---

## Gate C — reachability

1,500-bar frames, so 1,440 windows:

| frame | fires | distinct | non-zero | min | max |
|---|---|---|---|---|---|
| walk | 1440/1500 | 1440 | 1440 | −0.069897 | +0.128352 |
| tick-rounded | 1440/1500 | 1440 | 1440 | −0.089260 | +0.082897 |
| ar1(+0.5) | 1440/1500 | 1440 | 1440 | −0.108450 | +0.354113 |
| ar1(−0.5) | 1440/1500 | 1440 | 1440 | −0.073438 | +0.023363 |
| seasonal(10) | 1440/1500 | 1429 | 1440 | −0.000276 | +0.000197 |

`0 < fires < n` on every frame, and the column is never constant.

**On real data**, from Gate E's run `is96-ts_aggac_60-d6ed198b` over the 89
frozen ALTPORT-1 BIST frames: `TS_AGGAC_60_10` is **non-NaN on 393,509 of
398,849 pooled bars**, and **393,509 of those are non-zero** — not one fired
bar is exactly 0.0, although A1 shows a bit-exact 0.0 is reachable on an
alternating window at an even `maxlag`.

The 5,340 NaN bars are **exactly 60 × 89**, the warm-up (the first fired bar
is 60, section A7), so **none** of this port's three guards — the 8.27e-25
variance floor, the per-return square bound and the accumulator trust test —
emptied a window on those 89 frames. The synthetic tables above could only
show those guards cost 0 bars on nine clean synthetic frames; this shows 0
bars on 398,849 real ones. It does not retire the accumulator failure mode
disclosed under *Guards*: its 1e+6 row, where the column reports and is
9.1e-03 wrong, leaves no trace in a NaN count at all.

---

## Gate D — scale

**Bit-identical at a power of two.** Every input is a price RATIO, and
`8a / 8b` is the same double as `a / b`:

| frame | x8 | x64 |
|---|---|---|
| walk | 1440/1440 bit-equal | 1440/1440 |
| tick-rounded | 1440/1440 | 1440/1440 |
| ar1(+0.5) | 1440/1440 | 1440/1440 |

NaN masks agree in all six. At other parameters, x8 on the walk: 1488/1488 at
`length` 12, 1480/1480 at 20, 1250/1250 at 250.

**Tolerance at a non-power of two.** x10 and x3.7 perturb the returns in their
last bits; masks still agree exactly:

| frame | x10 | x3.7 |
|---|---|---|
| walk | 5.773e-15, Spearman 1.000000 | 9.485e-15, Spearman 1.000000 |
| tick-rounded | 7.334e-15, Spearman 1.000000 | 3.380e-15, Spearman 1.000000 |
| ar1(+0.5) | 3.088e-15, Spearman 1.000000 | 7.903e-15, Spearman 1.000000 |

**Stronger than price scale-freedom:** the column is invariant to any AFFINE
map of the RETURNS. On the walk, with identical NaN masks and Spearman
1.000000 throughout: +0.004 of log drift a bar moves it by 1.285e-14, returns
×2 by 4.906e-15, returns ×0.5 by 4.982e-15.

**Why the return is a ratio and not a difference of logs.** At x8 the ratio
spelling of the return is bit-equal on 1,499 of 1,499 bars; the
`log(c) - log(c.shift(1))` spelling is bit-equal on 821 of 1,499, which would
cost the bit-identical Gate D reading above.

---

## Gate E — overlap against the engine's 687 comparators

Run **`is96-ts_aggac_60-d6ed198b`**, made by the launcher (not by this
worktree) with
`gate_e_overlap.py run --module pandas_ta.statistics.ts_aggac_60`, measured
**2026-11-13**: default parameters (`kwargs {}`), the 89 frozen ALTPORT-1 BIST
frames, 398,849 pooled bars, **687 comparators** (329 `compute_all` + 358
`ml_features` manifest `1d`), canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS
bit-equal`, pandas 2.3.3 / numpy 1.26.4. Verdict schema `r3-perframe-0.90`.

### **`TS_AGGAC_60_10` — SHIP**

| reading | value |
|---|---|
| pooled max \|ρ\| | **0.26763631965371043** |
| against | `mad_pct` (manifest set) |
| n | **393,509** |
| best `compute_all` comparator | `BB_BWidth`, 0.23668050378589767, n = 393,509 |
| per-frame max median \|ρ\| | **0.26342055037139966** against `MACD_Cross_Age` |
| frames | 89 |
| frames ≥ 0.90 on any top-5 comparator | **0 of 89** (`pct_frames_ge_090` 0.0 on all five) |
| frames ≥ 0.80 on any top-5 comparator | **0 of 89** (`pct_frames_ge_080` 0.0 on all five) |
| degenerate comparators | 1 — `squeeze_SQZ_NO`, constant over the pooled sample |

0.2676 is below the 0.76 SHIP line and nowhere near the 0.90 strike line, on
both the pooled and the per-frame reading, so nothing is struck and nothing is
removed.

**The top five, pooled and per frame** (`top25.csv`, `perframe.csv`):

| comparator | set | pooled ρ | per-frame median | per-frame max | per-frame min |
|---|---|---|---|---|---|
| `mad_pct` | manifest | +0.267636 | 0.259585 | **0.574814** | 0.045534 |
| `MACD_Cross_Age` | manifest | +0.262157 | **0.263421** | 0.406136 | 0.128184 |
| `BB_BWidth` | compute_all | +0.236681 | 0.234671 | 0.489972 | 0.063604 |
| `ADX` | compute_all | +0.225521 | 0.222987 | 0.472581 | 0.041667 |
| `mad_pct_Pctl` | manifest | +0.224917 | 0.226733 | 0.430370 | 0.007715 |

The single worst frame anywhere in that table is 0.5748 (`mad_pct`), which is
still under the 0.76 ship line, and the 25th row of `top25.csv` is
`Supertrend_Flip_Age` at 0.1622 — so the whole visible tail is under 0.17.

**What the comparators are.** The five are a mean-absolute-deviation width, a
MACD cross age, a Bollinger bandwidth, an ADX and the percentile of the first;
the rest of `top25.csv` is that same volatility-width / range-efficiency family
through percentiles, states and regime flags (`EFFICIENCY_RATIO`, `er`, `chop`,
`CHOP`, `ATR_Bars_Above`, `PSAR_AF`, `CKSP_Width_pct`, …). That reading is an
INTERPRETATION of their names, not a measurement. It is worth setting against
the synthetic Spearman of **−0.0069** between this column and its own window's
standard deviation (*What the column means*): a pooled +0.27 against four
volatility-width readings is larger than "it is not a volatility column" would
suggest. Both numbers are recorded; neither is reconciled here, and the
synthetic one is one 1,500-bar random walk while this one is 393,509 real
bars.

### What this run does NOT say

* **It does not measure the overlap against this fork's own `TS_AC1_60`.** The
  687 comparators are the engine's columns and the `ml_features` manifest; no
  `TS_AC1` column appears anywhere in the run's four output files. The A9
  table's +0.3739 / +0.0008 / +0.3787 / −0.2027 against `ts_ac1_60` therefore
  remain **synthetic-only**, and a receipt session cannot reach
  `../Backtesting` to join the two runs. What the ledger does show is that the
  two columns read 0.2676 and 0.25357121838081886 against the SAME comparator
  `mad_pct` at the SAME n = 393,509 — which is a statement about each one's
  overlap with `mad_pct`, not about their overlap with each other.
* **It says nothing about non-default parameters.** `gate_e_ledger.py record`
  refuses a run with non-default kwargs, and this one has none.
* **It does not re-measure the issue's stage-2 fork overlap** (max \|ρ\| 0.3787
  vs `ht_dcperiod:HT_DCPERIOD` over 12 frames): no `HT_DCPERIOD` column appears
  in the run's outputs, so the run neither confirms nor refutes it.

### Against the screen's prototype figure

Issue #96's screen measured the PROTOTYPE — a different column, Spearman
0.902932 against this module on a 1,500-bar walk (section A7) — at max \|ρ\|
**0.2815** vs `mad_pct`, n = **392,619**, per-frame max median 0.2814. This
module reads **0.2676** vs the SAME comparator at n = **393,509**.

Both sample sizes are the arithmetic of the two warm-ups over the same 398,849
pooled bars: the prototype's lag-10 term reads 71 closes and first fires at bar
70, so `398,849 − 70 × 89 = 392,619`; this module first fires at bar 60, so
`398,849 − 60 × 89 = 393,509`. The 890-bar difference is the 10 extra warm-up
bars per frame and nothing else — i.e. this port's guards emptied no window
that the prototype reports on (Gate C above).

So the screen's figure was a reasonable prior and the port lands 0.0139 below
it on the same comparator. That agreement was not available before the run:
nothing bounds the gap between two maxima taken over 687 comparators by two
columns that disagree by up to 4.7e-02 (A7).

---

## What the column means

**Under iid returns**, 2,000 independent 60-return windows: median −0.0227,
mean −0.0182, sd 0.0351, p10 −0.0577, p90 +0.0299, positive on **25.50%**,
finite on 2,000 of 2,000.

That centre is not noise. Each lag carries a small-sample bias of about
`-1/(length-1)` = −0.0169 and the ten do not cancel. Run on the SAME 2,000
paths, `ts_ac1_60` reads median −0.0106, mean −0.0134, sd 0.1222, positive
45.70% — so averaging ten OVERLAPPING lags shrinks the spread to **0.287** of
the lag-1 column's and roughly **doubles** the negative centre (**2.14×** its
median). A reading of 0 is therefore mildly POSITIVE evidence of
autocorrelation, not neutral.

**Under AR(1) log returns** (population lag-`k` autocorrelation exactly
`phi**k`, so the population value of this column is `mean(phi**k, k=1..10)`):

| phi | median | p10 | p90 | population |
|---|---|---|---|---|
| +0.50 | +0.0448 | −0.0416 | +0.2012 | +0.0999 |
| +0.25 | +0.0044 | −0.0508 | +0.1048 | +0.0333 |
| 0 | −0.0161 | −0.0520 | +0.0490 | 0 |
| −0.25 | −0.0286 | −0.0534 | +0.0118 | −0.0200 |
| −0.50 | −0.0362 | −0.0552 | −0.0154 | −0.0333 |

Monotone in `phi`, which is what a miner needs, and shrunk toward the
negative bias, which is what a threshold rule needs to know.

**⚠ At a short `length` the bias swamps the signal and can flip the sign.**
The high lags are estimated from few pairs, so the bias grows as `length`
approaches `2*maxlag`. On iid windows (500 per row):

| length | median | sd | one lag's bias `-1/(n-1)` |
|---|---|---|---|
| 12 | −0.0772 | 0.0640 | −0.0909 |
| 20 | −0.0537 | 0.0389 | −0.0526 |
| 30 | −0.0424 | 0.0383 | −0.0345 |
| 60 | −0.0220 | 0.0330 | −0.0169 |
| 200 | −0.0061 | 0.0222 | −0.0050 |

And on a 20,000-bar AR(1) path with `phi` = +0.50, whose population value is
+0.0999, the median reads +0.1054 / +0.0871 / +0.0431 at `length`
1000 / 200 / 60 and **−0.0514** at `length` 20 — *negative, for a positively
autocorrelated path*. Do not compare readings across lengths, and do not run
this column at a `length` near `2*maxlag`.

**⚠ It is blind to a seasonality whose period divides `maxlag`.** The lag-`k`
autocorrelations of an exactly periodic window sum to zero over any whole
cycle of rotations, so averaging lags 1..10 cancels a period of 2, 5 or 10
almost exactly. On 1,500-bar paths whose returns repeat exactly:

| period | divides 10 | this column (median) | `maxlag=1` (median) |
|---|---|---|---|
| 2 | yes | +0.000000 | −1.0000 |
| 3 | no | −0.050649 | −0.5058 |
| 5 | yes | +0.000008 | −0.5872 |
| 7 | no | −0.050173 | −0.5808 |
| 10 | yes | +0.000067 | −0.5674 |

This is a property of the `f_agg='mean'` aggregation the issue specifies, not
a defect of the port, and it is why the column should not be read as "is this
series periodic".

**Against the same window's other statistics** (walk): Spearman −0.0069 vs
the window standard deviation, +0.1132 vs the mean return, −0.1357 vs the
absolute mean return. It is neither a volatility nor a direction column. The
in-fork overlap table is A9 above.

**Persistence.** Two consecutive windows share 59 of their 60 returns, so the
column autocorrelates at 0.9665 at lag 1, 0.3686 at lag 30 and 0.0683 at lag
60. It is a slow state, not an event flag.

---

## Guards, each priced in both directions

### The per-return square bound

`r**2 < max/(8*length)`, a ceiling of **6.120e+152** on a return at
`length` 60. It is not a local nicety: pandas accumulates `rolling.var` and
`rolling.sum` ONLINE, so an unrepresentable square never leaves the
accumulator and every LATER bar comes back NaN too. On a 400-bar walk:

| planted | guarded empties | unguarded empties |
|---|---|---|
| one close of 1e-300 at bar 200 (next return ~1e+302) | 60 bars (201–260) | 199 bars (201–399) |
| closes of 1e-200 at bars 200 and 230 (two over the ceiling) | 90 bars (201–290) | 199 bars (201–399) |

The bound is structural, not fitted: with `B**2 = max/(8*length)`, the window
mean is at most `B`, every squared deviation at most `4*B**2`, every lag-`k`
difference at most `2*B` — so `length*var`, each `gap[k]` and each partial sum
of squared deviations all stay under `max/2`, the halving being headroom for
the accumulation's own rounding.

### The accumulator trust test

A population variance cannot exceed `(span/2)**2`, and `length - k` squared
lag-`k` differences cannot exceed `(length-k) * span**2`. `span` is
`rolling.max() - rolling.min()`, which pandas computes by a deque and
therefore LOCALLY, so both bounds are exact algebra on the window itself.
Slack is the same 4096 eps, relative.

Magnitude sweep, one planted return at bar 200 of a 400-bar walk, measured
over bars 261–399 — i.e. AFTER it has left every window:

All twelve swept exponents, none dropped — the rows where the guard is NOT
what saves the column are the point of the table as much as the rows where it
is:

| planted return | module | without the trust test |
|---|---|---|
| ~1e+2 | 0 NaN, 1.414e-09 from the oracle | same |
| ~1e+4 | 0 NaN, 3.522e-06 | same |
| ~1e+6 | 0 NaN, 9.055e-03 | same |
| ~1e+8 | **139 of 139 NaN** | 0 NaN, **1.149** from the oracle |
| ~1e+20 | 139 NaN | 0 NaN, 1.151 |
| ~1e+100 | 139 NaN | **139 NaN** — the accumulator has already gone non-finite; the trust test is redundant here |
| ~1e+140 | 139 NaN | **139 NaN** — same |
| ~1e+152 | 139 NaN | 0 NaN, 1.151 |
| ~1e+153 | 0 NaN in the tail, 5.324e-14 | same — the square bound dropped the return instead |
| ~1e+160 | 0 NaN, 5.324e-14 | same |
| ~1e+200 | 0 NaN, 5.324e-14 | same |
| ~1e+300 | 0 NaN, 5.324e-14 | same |

So the test catches the gross case, is REDUNDANT at 1e+100 and 1e+140, and
does NOT catch the subtle one. That is stated rather than excused: a planted
1e+6 return leaves 139 later bars up to 9.1e-03 wrong with nothing to mark
them, because the variance stays inside its own bound. The same limit is
recorded for `ts_ac1_60` and `ts_cid_ce_20`; it is pandas' online
accumulator, and the only structurally local spelling is the sliding-window
oracle, ~1.24 s against ~240 ms on the same 400,000-bar input (individual
runs on this machine, see *Cost*).

### The `isfinite` filter this module does NOT spell

`ts_ac1_60` has an `r.where(np.isfinite(r))` between the price ratio and the
square bound. This module omits it, and that omission is measured rather than
argued: the square bound rejects the same values, because an infinite return
squares to infinity and a NaN compares False. Adding the line back
(`module_variant(..., finite=True)`) is **bit-identical** on every frame that
can produce a non-finite return —

| planted | NaN masks identical | bit-equal |
|---|---|---|
| one close of 1e-300 at 200 (next return ~1e+302) | yes | 280/280 |
| closes of 1e-300 at 200 and 1e+300 at 201 (an INFINITE ratio) | yes | 280/280 |
| close `inf` at 200 | yes | 279/279 |
| close `nan` at 200 | yes | 279/279 |
| nothing planted (clean walk) | yes | 340/340 |

— and it stays bit-identical with the square bound REMOVED, where the filter
would be the only thing left to catch an infinity: 120 NaN of 400 either way,
a difference of 0 bars, and the 280 values that still report are bit-equal on
280 of 280. (A mask agreeing does not imply the numbers behind it agree,
which is why that sub-case is compared on values and not only on NaNs.)

Structurally, not only on these frames: an infinite return squares to
infinity and a NaN compares False, so `square < max/(8*length)` rejects every
non-finite return along with every merely enormous one. The filter can only
ever reject a subset of what the bound already rejects.

### A volatility regime COLLAPSE, not a spike

`ts_cid_ce_20` records a different shape as the one pandas' accumulators
really lose: sigma 0.3 for 200 bars, then sigma 1e-9. On that frame it
measured 181 bars up to 6.323 from the oracle against values of 5.757, and
its trust test is what saved them. **This column does not need the trust test
there**, and the reason is measured rather than assumed: pandas' online
variance comes back at or below the 8.27e-25 floor on **141 of the 200**
post-collapse bars, so the VARIANCE FLOOR empties them first. The column
fires on 199 of 400 bars, the trust test costs **0** of them, and the 59
post-collapse bars that do report are **3.579e-14** from the per-window
oracle — with the trust test or without it.

### What the trust test costs where it is not needed

0 bars on every clean frame tried:

| frame | fires | bars the trust test costs | max `var/(span/2)**2` |
|---|---|---|---|
| walk | 1440 | 0 | 0.316482281433 |
| tick-rounded | 1440 | 0 | 0.279397409815 |
| ar1(+0.5) | 1440 | 0 | 0.277267242971 |
| ar1(−0.5) | 1440 | 0 | 0.296542423523 |
| seasonal(10) | 1440 | 0 | 0.364148680537 |
| **alternating (the equality case)** | 1440 | 0 | **1.000000000000** |
| volatility collapse 0.3 → 1e-9 | 199 | 0 | 0.266159559129 |
| low-vol walk sigma = 1e-6 | 1440 | 0 | 0.316448900686 |
| fine tick 50/0.01 | 240 | 0 | 0.344627535409 |

The alternating frame attains the bound exactly, which is what proves the
4096-eps slack is enough rather than merely generous.

### Bad closes and flat runs

A close that is not a finite, normal, positive float has no return to take.
It spoils two returns, so it empties the `length + 1` = 61 windows it sits in
and nothing earlier — measured for each of `nan`, `0.0`, `-5.0`, `inf` and
`1e-310` on a 400-bar walk: **61 bars emptied (200–260), 0 earlier bars
moved**.

A flat run of `length` identical closes leaves 59 zero returns and one
non-zero one, so the window still has dispersion: **0 bars emptied**. 61
identical closes empty 1 bar, 65 empty 5.

### The floor is on the dispersion, not the price

| price | tick | \|r\| | window variance | fires |
|---|---|---|---|---|
| 50 | 0.01 | 1.888e-04 | 3.893e-13 | 240/300 |
| 1e+06 | 0.001 | 1.000e-09 | 1.198e-32 | 0/300 |
| 1e+06 | 0.01 | 1.000e-08 | 2.987e-30 | 0/300 |

### Parameters

`length` falls back to 60 when it is missing or below 3 (`None`, `0`, `-5`,
`2`, `0.5`, `2.9` all give `TS_AGGAC_60_10`); `3` and `3.9` give
`TS_AGGAC_3_1`. `maxlag` falls back to 10 when it is missing or below 1, and
is clamped to `length - 2`: `1.9` gives `TS_AGGAC_60_1`, `59` and `1000` both
give `TS_AGGAC_60_58`. **The effective value is always the one in the column
name** — `ts_c3_20`'s habit with its own `lag`, and the reason `maxlag` can be
a parameter at all where `ts_ac1_60`'s `lag` could not: the name carries it,
so no caller can emit a mislabelled column.

61 closes fire exactly 1 bar; 60 closes return `None`.

---

## Cost

400,000 bars, best of three calls each, and the whole section run twice
against the SHIPPED module (i.e. after the redundant `isfinite` pass was
removed; the earlier 232 ms figure was measured on code that no longer
exists and is not quoted here). **These are individual runs on this machine,
not bounds** — a later run landing outside them is run-to-run noise, not a
regression. The peaks, unlike the times, reproduce exactly.

| parameters | time (run A / run B) | traced peak |
|---|---|---|
| length 12, maxlag 10 | 238 / 240 ms | 45.2 MB |
| length 60, maxlag 1 | 75 / 75 ms | 42.0 MB |
| **length 60, maxlag 10 (default)** | **246 / 237 ms** | **45.2 MB** |
| length 250, maxlag 10 | 237 / 235 ms | 45.2 MB |

The cost tracks `maxlag`, not `length`: four O(n) passes are shared by every
lag (mean, variance, the two extrema) and four are per lag (two shifts, a
lagged difference and its rolling sum). The `maxlag` 1 row is in the same
place as `ts_ac1_60`'s own 70–90 ms, as it should be. Removing the redundant
`isfinite` pass did not make the call measurably faster — the difference is
inside the run-to-run spread above, which is why single runs are quoted with
that caveat rather than a range presented as a bound.

The trust test's comparisons cost roughly 30 ms of that (238 with / 209
without on run A, 235 / 208 on run B, same code path, flag flipped). The
sliding-window oracle the module is checked against is **~1.24 s and peaks at
403.2 MB** on the same input (1,242 and 1,237 ms), which is why it lives in
`docs/measure_ts_aggac_60.py` and not in the module.

---

## Gate F

Re-run by the receipt session on 2026-11-13, after the ledger row landed and
the owed-Gate-E test was replaced by the two that pin it:

* `python -m pytest tests/test_ts_aggac_60.py -q` → **168 passed, 2 skipped**
  in 25.3 s (the porting session's 167 plus one: the single owed-Gate-E test
  became two). The two skips are the two A9 pairs that have nothing to
  measure: `lean_momersion_20` on the seasonal frame (constant, so no rank)
  and `roll_spread` on the AR(1) frame (26 overlapping bars, below the test's
  `MIN_OVERLAP` of 200).
* `python -m pytest -q` (full suite) → **3 failed, 6,892 passed, 85 skipped**
  in 176 s. The three failures are the two `CLAUDE.md` *Known breaks* —
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` and
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  (the latter needs the sibling `../AlternativeRepos` checkout, and CI
  deselects it) — plus `test_gate_e_ledger.py::
  test_every_indicator_that_needs_a_row_has_one`, which now reports exactly
  `no Gate E ledger row for ['mtd_ret']`. `ts_aggac_60` is off that list; the
  `mtd_ret` row is pre-existing and owed on `dev`.
* `python docs/measure_ts_aggac_60.py cpu` re-runs the module's tests with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, which is what a
  GitHub runner without AVX-512 gives: **168 passed, 2 skipped, exit code 0**.
  The variable has to be set before numpy is imported, so it cannot be done
  from inside a test — hence the section in the measure script.

The launcher re-runs both repos' suites in clean worktrees and repeats the
disabled-AVX run itself.

---

## What the receipt session closed (2026-11-13)

The porting session left five things owed. All five are answered above:

1. The Gate E verdict for `TS_AGGAC_60_10` — **SHIP**, 0.26763631965371043 vs
   `mad_pct` at n = 393,509, per-frame max median 0.26342055037139966 vs
   `MACD_Cross_Age`, 0 of 89 frames at or above either the 0.80 or the 0.90
   line on any of the top five comparators (section *Gate E*).
2. The row in `docs/gate_e_ledger.csv`, recorded with
   `python docs/gate_e_ledger.py record <run dir> --measured 2026-11-13`.
3. The real-data reachability counts — 393,509 non-NaN and 393,509 non-zero of
   398,849 pooled bars, the 5,340 NaN bars being exactly the 60 × 89 warm-up
   (section *Gate C*).
4. `test_gate_e_is_owed_and_has_no_ledger_row_yet` in
   `tests/test_ts_aggac_60.py` is replaced by two tests that pin the row's
   identity and its numbers.
5. The run is not STRUCK, so nothing is removed and the module ships.

Nothing in Gates A–D was re-measured here; those numbers are the porting
session's and still come from `python docs/measure_ts_aggac_60.py`.
