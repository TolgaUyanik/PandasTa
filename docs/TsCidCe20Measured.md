# `ts_cid_ce_20` — measured

Issue #95 (TS-CID-CE-20), ported 2026-11-13 on branch `issue-95-ts-cid-ce-20`.
Column: **`TS_CID_CE_20`**, `pandas_ta/statistics/ts_cid_ce_20.py`.
**Status: SHIPPED, Gates A–F.** Gate E was measured on 2026-11-13 by the
launcher's run `is95-ts_cid_ce_20-524cb24a` — **SHIP**, max |ρ| 0.2641 vs
`chop` over n = 396,927, per-frame max median 0.2647 over 89 frames — and
recorded in `docs/gate_e_ledger.csv`. Nothing was struck, so nothing was
removed.

Every Gate A–D number in this file is printed by

    python docs/measure_ts_cid_ce_20.py          # every section
    python docs/measure_ts_cid_ce_20.py a        # one section: a b cd meaning guards cost

(pandas 2.3.3 / numpy 1.26.4) or asserted by

    python -m pytest tests/test_ts_cid_ce_20.py -q     # 133 tests

Nothing here was typed from expectation; where a number is *not* measured — a
piece of arithmetic, a derivation — the line says so.

## What it is

    r[t]           = close[t] / close[t-1] - 1
    v              = POPULATION variance of the trailing `length` r
    g              = sum of (r[i] - r[i-1])**2 over the length-1 pairs
    TS_CID_CE[T]   = sqrt(g / v)

NaN where `v <= 8.27e-25` or where the accumulator trust test below fails. At
the default `length = 20` the window is 20 returns, so **21 closes**, and the
first value lands on bar 20.

tsfresh z-normalises the window first and then takes
`sqrt(dot(diff(z), diff(z)))`. The normalisation's mean cancels inside a
difference and its standard deviation factors out of the whole sum, so
dividing the SUM by the variance once is the same number as dividing each of
the `length` returns — measured in A5 below, including against the exact
rational value, where neither spelling is closer.

`length` is the only parameter. There is no `normalize` keyword: the issue
fixes it at `True`, and `normalize=False` is a different column — a
volatility reading (A6).

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue names tsfresh's `feature_calculators` (MIT) and states the formula:

> `cid_ce(x, normalize=True) on 20 returns`

⚠ **tsfresh is not installed in this worktree and web access is
unavailable** — `python docs/measure_ts_cid_ce_20.py a` prints
`tsfresh is NOT importable (No module named 'tsfresh')` as section A8, and
the script compares against it automatically if that ever changes. Its own
code was not read in this session. So the attribution is an attribution, not
an oracle: Gate A below is against the issue's line plus the published
definition of that function —

```python
if normalize:
    s = np.std(x)
    if s != 0:
        x = (x - np.mean(x)) / s
    else:
        return 0.0
x = np.diff(x)
return np.sqrt(np.dot(x, x))
```

— and anything tsfresh does that those do not state (how it treats NaNs) is
**unverified here**. `np.std` is the POPULATION standard deviation
(`ddof=0`); the `s == 0` branch is discussed under Guards, where this port
differs from it on purpose.

### This column IS what issue #95's screen measured, up to one constant

The screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_cid_ce_20`, gitignored and local to the owner's machine) is

    def _(o, h, l, c, v):
        r = ret(c)
        return sdiv(np.sqrt(tsum(delta(r, 1) ** 2, 19)), std(r, 20))

with `std(x, n) = x.rolling(n).std()` — pandas' default `ddof=1`, the
**sample** standard deviation, where the source divides by the population
one. That is the only difference, and it is a positive constant:
`sqrt(20/19) = 1.025978352085`. Measured on a 1,500-bar walk, port against
prototype:

| | value |
|---|---|
| Spearman | **1.000000** |
| max \|difference\| | 1.988470e-01 (a level shift only) |
| port / prototype | min **1.025978352085**, max **1.025978352085** |
| max \|port − sqrt(20/19) · prototype\|, the factor at full float precision | **2.665e-15** (Gate A7; the 3.642e-14 that A6 prints is the same quantity against the `ddof=1` window-by-window oracle, a different series) |
| NaN masks agree | yes — first fired bar 20 in both |

The prototype was read, retyped here and also imported out of the owner's
tree: the retype and the registry entry agree **bit-for-bit on 1,480 of 1,480
bars**, so this comparison is against the real candidate and not a paraphrase
of it.

⚠ **What follows from that, and what does not.** Gate E's statistic is a
*Spearman*, which no positive rescaling can move, so the screen's figures
(max \|ρ\| **0.2641** vs `chop`, n = 396,927, top-5 per-frame max median
0.2647, SHIP) are expected to carry over to this column **wherever both
columns fire** — unlike issue #94's, whose prototype was a different
statistic. They are still not a receipt for this module, for one measured
reason: this port's guards (the variance floor, the per-return square bound,
the accumulator trust test) empty windows the prototype reports on, and the
prototype's own `sdiv` only drops infinities. Any difference in the fired
set is a difference in the ranked sample. The launcher's run on
`pandas_ta.statistics.ts_cid_ce_20` is what decides.

**It has since decided, and the transfer held.** Run
`is95-ts_cid_ce_20-524cb24a` (Gate E below) reads max |ρ| 0.2640577551656063
vs `chop` at n = **396,927** — the screen's own sample size — because the
guards emptied **0** windows beyond the 20-bar warm-up on the 89 BIST frames.
That is why the figures match; it was not knowable before the run.

## Gate A — correctness

**A1. Windows with a closed form.** An alternating window — returns that
alternate between two values `m0 ± d` — has every squared successive
difference equal to the square of the window's whole range, `(2d)²`. Two
exact answers follow, both derived by hand:

* **even `n`**: equal counts of the two values, `var = d²`, so the quotient is
  `4(n-1)` and the column is `2·sqrt(n-1)`;
* **odd `n`**: one extra of the first value, the window mean sits `d/n` off
  centre, `var = d²(n²-1)/n²`, so the quotient is `4n²/(n+1)` and the column
  is `2n/sqrt(n+1)`.

On `close = [1, 2, 1, 2, …]`, whose returns are `+1` and `−1/2`:

| `length` | closed form | module | bit-equal |
|---|---|---|---|
| 3 | 2·3/√4 = 3.0 | 3.0 | yes |
| 4 | 2√3 = 3.4641016151377544 | 3.4641016151377544 | yes |
| 5 | 2·5/√6 = 4.08248290463863 | 4.0824829046386295 | no — **1 ulp** |
| 20 | 2√19 = 8.717797887081348 | 8.717797887081348 | yes |
| 21 | 2·21/√22 = 8.954430086935638 | 8.954430086935638 | yes |

Everything before the square root is an exact binary fraction, so the module
hits the correctly-rounded `sqrt`; at `length` 5 the two float *spellings* of
the same number differ in the last bit, which is a float detail and is
recorded rather than asserted.

On the 1,500-bar alternating frame (closes built by a cumulative product, so
the returns are no longer exactly ±amp) at `length` 20: 1,480 bars fire,
max \|value − 2√19\| = **1.065814e-14**, 520 of 1,480 bars bit-equal.

A window of **two** returns has one squared difference `(a-b)²` over a
variance `(a-b)²/4`, so it is exactly **2.0** for every `a ≠ b` — measured on
38 windows of a non-geometric frame, which all read exactly 2.0. That is why
`MIN_LENGTH = 3` and why `length=2` falls back to the default.

**A2. The reachable range, in closed form and attained.** The squared column
is `gap / var` = `n` times the Rayleigh quotient of the free-end path
Laplacian `L` (for which `x'Lx = sum (x[i]-x[i-1])²`) on the subspace
orthogonal to the all-ones vector. `L`'s eigenvectors are the DCT-II basis
`cos(πk(j+½)/n)` with eigenvalues `4 sin(πk/2n)²`, and the `k = 0` eigenvector
**is** that all-ones vector, so centring removes exactly it and the
restricted spectrum is `k = 1 … n-1` (derivation, not a measurement):

    min = sqrt(4n) · sin(π/(2n))        max = sqrt(4n) · sin(π(n-1)/(2n))

| `length` | closed form | module on the matching cosine window | \|error\| |
|---|---|---|---|
| 3 | [1.732050807569, 3.000000000000] | [1.732050807569, 3.000000000000] | 2.2e-16, 4.4e-16 |
| 4 | [1.530733729460, 3.695518130045] | same | 0.0, 0.0 |
| 10 | [0.989378428154, 6.246689549346] | same | 1.1e-16, 8.9e-16 |
| **20** | **[0.701759486002, 8.916699704700]** | same | 1.1e-16, 1.8e-15 |
| 60 | [0.405531539404, 15.486624686178] | same | 5.6e-17, 1.8e-15 |

So the column **cannot be 0** and cannot be unbounded. Observed on ordinary
frames at `length` 20: walk [4.352711, 7.853182], tick-rounded
[4.021300, 7.899372], AR(1) φ=+0.5 [2.581282, 6.501561], alternating
8.717798 flat.

**A3. The source function, window by window.** Every window is handed to a
retype of `cid_ce` itself — the z-normalisation per return, `np.diff`,
`sqrt(dot)` — with `sliding_window_view` and no pandas rolling anywhere, so
it shares no window machinery with the module:

| frame | n | max \|difference\| | Spearman | NaN masks |
|---|---|---|---|---|
| walk | 1,480 | 3.463896e-14 | 1.000000 | agree |
| tick-rounded | 1,480 | 2.220446e-14 | 1.000000 | agree |
| AR(1) | 1,480 | 4.085621e-14 | 1.000000 | agree |
| mean-dominated (\|mean\|/sd = 1e5) | 380 | 2.887965e-10 | 1.000000 | agree |

**A4. Against an exact rational oracle.** Every close is a rational, so the
whole *squared* statistic is one; `fractions.Fraction` computes it with no
float arithmetic and the square root is the only rounding. 40 bars per frame:

| frame | module | `math.fsum` loop | windowed oracle | z-normalise first |
|---|---|---|---|---|
| walk | **4.441e-15** | 4.441e-15 | 4.441e-15 | 4.441e-15 |
| tick-rounded | **7.994e-15** | 8.882e-15 | 7.994e-15 | 7.994e-15 |
| mean-dominated | **1.142e-09** | 1.147e-09 | 1.147e-09 | 1.147e-09 |

The third row is the load-bearing one: on a path whose returns have a huge
mean and a tiny dispersion every spelling is 1.1e-09 out, so that error
belongs to the **variance** and not to this column's numerator. There is no
better numerator to reach for — unlike `ts_ac1_60`, whose numerator contains
the window mean and loses 2.3e+04 times more accuracy in its raw-sum form,
this one holds no mean at all, because a difference of two returns does not
contain one.

**A5. The two spellings of the normalisation.** Dividing the sum by the
variance once (the module) against z-normalising each of the `length` returns
first (tsfresh's order):

| frame | n | max \|difference\| | Spearman |
|---|---|---|---|
| walk | 1,480 | 3.463896e-14 | 1.000000 |
| tick-rounded | 1,480 | 2.309264e-14 | 1.000000 |
| mean-dominated | 380 | 2.887965e-10 | 1.000000 |

and A4 shows neither is closer to the exact value. So the cheaper spelling is
free; it is one division instead of `length`.

**A6. The readings the wording leaves open**, each measured on the same
1,500-bar walk rather than dismissed:

| reading | max \|difference\| | Spearman | verdict |
|---|---|---|---|
| LOG returns instead of simple | 4.757028e-02 | 0.999909 | rejected — the prototype's `ret` is simple |
| 20 **closes** (19 returns) | 1.417889e+00 | 0.949216 | rejected — a different column; masks differ by a bar |
| SAMPLE sd (`ddof=1`) | 1.988470e-01 | 1.000000 | rejected — the source says `np.std`; this is the prototype's constant. Rescaling it back: max \|port − sqrt(20/19) · oracle\| = **3.642e-14** |
| **`normalize=False`** | 7.751885e+00 | 0.545430 | rejected — the issue says `True`, and this one is volatility |

The last row is the one a consumer can get wrong in the other direction:
`cid_ce(x, normalize=False)` is `sqrt(sum (x[i]-x[i-1])²)` with no divisor,
and it reads Spearman **0.824308** against the same window's standard
deviation, where the normalised column reads **0.007243**.

**A7. The prototype** — see the section above; measured in the same run.

**A8. tsfresh is not importable here**, printed by the script so the claim
cannot rot silently.

## Gate B — causality, by mutant

A future-perturbation sweep: replace every bar from `J` onward with a
different path and check that nothing strictly before `J` moved. 35 offsets,
`J = 100, 140, …, 1460` — all past the 20-bar warm-up. Prefix truncation
cannot see back-dating, which is why the sweep is a perturbation and not a
truncation.

Each mutant is read out of the module with `importlib`, one line replaced,
and `exec`'d in memory, so the shipped file is what is being mutated.

| mutant | what it does | walk | tick-rounded | AR(1) |
|---|---|---|---|---|
| *(the real module)* | — | **0/35** | **0/35** | **0/35** |
| `write_shift` | `.shift(-length)` on the output | 35/35 | 35/35 | 35/35 |
| `forward_return` | reads the NEXT close's return | 35/35 | 35/35 | 35/35 |
| `forward_diff` | `r.diff(-1)` instead of `r.diff()` | 35/35 | 35/35 | 35/35 |
| `centered_var` | `center=True` on the variance | 35/35 | 35/35 | 35/35 |
| `centered_gap` | `center=True` on the squared-difference sum | 35/35 | 35/35 | 35/35 |
| `centered_span` | `center=True` on the two extrema | **0/35** | **0/35** | **0/35** |

⚠ **The sixth mutant is a real look-ahead the sweep does not catch, and the
reason is measured rather than argued.** `span` enters nothing but the trust
test's two booleans, and that test rejects **0 bars** of each clean frame
(Guards below), so on clean data the mutation can only turn a number into a
NaN — never change a number, which is what the sweep looks for. Measured on
each frame: every bar on which the mutant differs is a bar the real module
reports and the mutant does not, and there is no bar where the real module is
NaN and the mutant is not. On a walk and a tick-rounded walk those are
exactly the last `(length-1)//2 = 9` bars (the centred window's own NaN
tail); on the AR(1) path **7 body bars** join them — the look-ahead showing
itself — and the sweep is still quiet, because the perturbed runs do not flip
a verdict inside the 9 bars a centred window can reach.

Where the trust test **bites**, it is caught: on a frame with a planted 1e+8
return at bar 150, whose bars 170–199 are all NaN in the real module (30 of
30), the real module still leaks **0/35** and the centred-span mutant is
caught **33/35**. The two quiet offsets are `J = 100` and `J = 140`, both at
or below the planted bar.

**Non-default lengths.** `length` is reachable from 3 upward and the sweep
above runs the default only, so the **five** mutants whose behaviour depends
on it are re-run at 3 and 250 — every mutant except `forward_return`, which
does not read `length`. The real module leaks 0/35 at every setting.
**Eight** of those ten cells are not 35/35 — `write_shift` is the only mutant
caught 35/35 at both lengths — under four explanations, and the eight cells
of the four mutants that are *not* `centered_span` are each asserted in
`tests/test_ts_cid_ce_20.py`:

| mutant | `length` | caught | why not 35 |
|---|---|---|---|
| `write_shift` | 3 / 250 | 35 / 35 | — |
| `forward_diff` | 3 | 25 | bar `J-1` is NaN in BOTH runs at 10 offsets |
| `forward_diff` | 250 | 31 | the four offsets below a 250-bar warm-up |
| `centered_var` | 3 | 22 | bar `J-1` is NaN in BOTH runs at 13 offsets |
| `centered_var` | 250 | 31 | the four offsets below the warm-up |
| `centered_gap` | 3 | **0** | the window is `length-1 = 2` wide and pandas centres it by `(2-1)//2 = 0` bars — the mutation is a no-op, asserted with `equals()` |
| `centered_gap` | 250 | 31 | the four offsets below the warm-up |
| `centered_span` | 3 | 18 | the same reason as at the default: the span feeds only the trust test's booleans, which reject 0 bars of a clean frame at any `length`, so the mutation can change no value the sweep looks at |
| `centered_span` | 250 | **0** | the same, and the look-ahead is `(length-1)//2 = 124` bars wide there (arithmetic, pandas' centring rule) — this port's one admitted causality hole, at a second user-reachable setting |

`offset` is this fork's standard parameter and a negative one is a
user-reachable look-ahead — the caller's explicit request, not a property of
the formula: `offset=2` and `offset=-2` are exactly `base.shift(±2)`.

## Gate C — reachability

**Real data, from Gate E's run `is95-ts_cid_ce_20-524cb24a` (2026-11-13):**
`TS_CID_CE_20` is non-NaN on **397,069** of **398,849** pooled bars over the
89 ALTPORT-1 BIST frames, and **397,069** of those are non-zero. The 1,780 NaN
bars are exactly `20 × 89`, the warm-up, so **none** of this port's guards
emptied a window on real data — see Gate E, open item 1.

The synthetic frames below are what the porting session measured; they remain
the only evidence about where the guards bite, because on this universe they
did not.

| frame | fires | distinct | non-zero | min | median | max |
|---|---|---|---|---|---|---|
| walk | 1,480 / 1,500 | 1,480 | 1,480 | 4.352711 | 6.247127 | 7.853182 |
| tick-rounded | 1,480 / 1,500 | 1,480 | 1,480 | 4.021300 | 6.378859 | 7.899372 |
| AR(1) φ=+0.5 | 1,480 / 1,500 | 1,480 | 1,480 | 2.581282 | 4.686532 | 6.501561 |
| alternating | 1,480 / 1,500 | 13 | 1,480 | 8.717798 | 8.717798 | 8.717798 |

`0 < fires < n` on every frame, and no fired bar is 0.0 — which the reachable
minimum of 0.701759 (A2) says it cannot be. The alternating frame's 13
distinct values are 2√19 to within 1.1e-14; that is a float detail, not a
range.

The 20 NaN bars of each 1,500-bar frame are exactly the warm-up.

## Gate D — scale

A ×2^k rescale of price cancels **exactly** in a price ratio: `8a / 8b` is
the same double as `a / b`.

| frame | ×8 | ×64 | NaN masks |
|---|---|---|---|
| walk | 1,480 / 1,480 bit-equal | 1,480 / 1,480 | agree |
| tick-rounded | 1,480 / 1,480 | 1,480 / 1,480 | agree |
| AR(1) | 1,480 / 1,480 | 1,480 / 1,480 | agree |

and at other lengths on the walk: `length` 3 → 1,497 / 1,497 fired bars
bit-equal, 20 → 1,480, 60 → 1,440, 250 → 1,250, at both ×8 and ×64.

×10 and ×3.7 are not bit-identical — they perturb the returns in their last
bits — but the NaN masks match exactly and the values agree at Spearman
1.000000: max \|difference\| 5.417888e-14 / 6.572520e-14 on the walk,
4.263256e-14 / 3.286260e-14 tick-rounded, 7.371881e-14 / 7.283063e-14 on the
AR(1) path. That is the Gate D tolerance reading.

**Why the return is a ratio and not a difference of logarithms.** On the same
frame at ×8 the ratio returns are bit-equal on **1,499 of 1,499** bars and the
difference-of-logarithms returns on **821 of 1,499**. The exact count is CPU
float detail; "some but not all" is what the test pins.

## What the column means

**Invariant to an affine map of the returns.** The numerator scales by `a²`
under `x → a·x + b`, the variance does too, and the shift cancels in both a
difference and a deviation:

| frame | n | max \|difference\| | Spearman | NaN masks |
|---|---|---|---|---|
| returns ×2 | 1,480 | 9.681145e-14 | 1.000000 | agree |
| returns ×0.5 | 1,480 | 8.437695e-14 | 1.000000 | agree |
| +0.004 log drift a bar | 1,480 | 1.110223e-13 | 1.000000 | agree |

**So it is NOT volatility and not direction.** Spearman against the same
window's statistics on a 1,500-bar walk:

| against | Spearman |
|---|---|
| standard deviation of the same 20 returns | **0.007243** |
| mean return | −0.073315 |
| \|mean return\| | −0.009703 |
| `close / close[-20] - 1` | −0.073095 |

(tsfresh's `normalize=False` mode reads 0.824308 against that same standard
deviation — A6.)

**The level, and why two lengths are not one scale.** For iid returns of
finite variance the RATIO OF EXPECTATIONS is exactly `2·length` = 40:
`E[gap] = 2(length-1)σ²` and `E[var] = (length-1)σ²/length` (arithmetic, not
measured, and distribution-free — no Gaussian assumption). The expectation of
a ratio is not the ratio of the expectations, so the column need not sit at
`sqrt(40) = 6.3246` — and which side it lands on is **measured, not derived**
(`sqrt` pulls a mean down, `1/var` pulls it up, and the two are dependent).
It lands just below. Over 2,000 independent 20-return windows:

| | value |
|---|---|
| finite | 2,000 / 2,000 |
| median | **6.2848** |
| mean | 6.2599 |
| sd | **0.6723** |
| p01 / p10 / p90 / p99 | 4.5745 / 5.4033 / 7.1126 / 7.6130 |
| min / max | 3.4785 / 8.0608 |

The level grows with the window: on a 20,000-bar AR(1) path at φ = +0.5 the
median is 4.8186 / 7.9344 / 14.2868 / 31.6863 at `length` 20 / 60 / 200 /
1000, i.e. 0.7619 / 0.7243 / 0.7143 / 0.7085 of `sqrt(2·length)`.

**What it orders is persistence, downward.** A persistent (positively
autocorrelated) return series is a smooth path and reads LOW; an alternating
one reads HIGH. On 1,500-bar paths whose log returns are an AR(1) with
coefficient φ:

| φ | median | p10 | p90 |
|---|---|---|---|
| +0.50 | **4.6865** | 3.6775 | 5.7630 |
| +0.25 | 5.5166 | 4.5251 | 6.4617 |
| 0 | 6.2276 | 5.2617 | 7.0800 |
| −0.25 | 6.8905 | 6.0104 | 7.6122 |
| −0.50 | **7.5389** | 6.6740 | 8.0895 |

The φ = 0 median sits 0.097 below `sqrt(40)`. Only the ORDERING is claimed.

**It is a slow state, not an event flag.** Two consecutive windows share 19
of their 20 returns, so the column autocorrelates at **0.8876** at lag 1,
0.3662 at lag 10, −0.1284 at lag 20 and −0.0455 at lag 40 (walk).

## ⚠ The redundancy disclosure: it restates the lag-1 return autocorrelation

With `y` the demeaned window,

    sum (y[i]-y[i-1])² = 2·length·v − y[oldest]² − y[newest]² − 2·sum y[i]y[i-1]

and `ts_ac1_60`'s value `A` at the same `length` is
`sum y[i]y[i-1] / ((length-1)·v)`, so

    TS_CID_CE² = 2·length − (y[oldest]² + y[newest]²)/v − 2·(length-1)·A

— an affine function of `A` up to the two end deviations. **Measured**:
max \|column² − identity\| = **2.132e-14** over 1,480 bars. What follows:

| against | frame | Spearman | Pearson | n |
|---|---|---|---|---|
| `ts_ac1_60` at `length` 20 | walk | **−0.977743** | −0.975446 | 1,480 |
| `TS_AC1_60` (the SHIPPED column) | walk | **−0.421800** | −0.426853 | 1,440 |
| `TS_AC1_60` | tick-rounded | −0.534166 | | |
| `TS_AC1_60` | AR(1) | −0.433943 | | |

Gate E's comparator set is the engine's `compute_all` ∪ the `ml_features`
manifest — 687 columns, none of them a pandas_ta port — so **nothing
downstream will catch this**, which is why it is stated here. The two columns
ship at different windows (20 returns against 60), and at that pairing the
overlap is −0.42 to −0.53 on these frames, well inside the ship band. A
consumer who runs both at the SAME `length` is double-weighting one signal,
and the end-deviation term is all that would separate them.

Two readings this does *not* support: that the column is redundant as shipped
(the measured pairing is the one above, not the same-length one), and that
`sqrt` of an affine function of `A` is a monotone transform of `A` (it is not
exactly — the end-deviation term is what makes the Spearman −0.9777 rather
than −1).

## Guards

### The variance floor

`NOISE_ULPS = 4096`, `NOISE_FLOOR = 9.094947e-13` on the standard deviation,
`VAR_FLOOR = 8.271806e-25` on the variance — this fork's existing habit on a
dimensionless quantity (`ts_c3_20` floors a return sd with the same 4096 eps;
`ts_ac1_60` squares it into a variance exactly as here).

| 300-bar frame | module fires | unguarded fires | unguarded max |
|---|---|---|---|
| flat 50.0 | **0** | 0 (variance exactly 0) | — |
| 1%-a-bar geometric ladder | **0** | **280** | **8.6372** |

The ladder is the case `var != 0` does not catch: its returns are
mathematically constant and vary only at float rounding level, and an
unguarded spelling reports 280 of 300 bars out of that rounding, reaching
8.6372 — *inside* the reachable range [0.701759, 8.916700], i.e. a
plausible-looking number, which is worse than a wild one.

The floor bounds the DISPERSION of the returns, not their size. A tick grid
quantises the return level at `tick/price` but the dispersion of consecutive
returns at about `(tick/price)²`, so "one tick over a price of 1e6 is 1e-9" is
not a comparison against this floor:

| one-tick-a-bar ladder | window variance | fires |
|---|---|---|
| price 50, tick 0.01 | 4.251e-14 | 280 / 300 |
| price 1e6, tick 0.001 | 1.220e-32 | 0 |
| price 1e6, tick 0.01 | 3.268e-31 | 0 |

And it is not tsfresh's guard. A `sigma = 1e-6` walk (ordinary
low-volatility data) fires on all 280 windows here with a median of 6.1882;
an `isclose(sd, 0)` guard at numpy's default `atol` also fires on all 280, so
unlike `ts_ac1_60` — whose divisor is a variance and so compares against
`atol` at a different magnitude — that variant is not what separates this
port from the source here. What separates them is the next item.

### ⚠ tsfresh's `0.0` is below the reachable minimum

tsfresh's own degenerate branch is `if s == 0: return 0.0`. **0.0 is not a
value this statistic can take**: the reachable minimum at `length` 20 is
0.701759 (A2). A tree reading a column of 0.0s reads "the calmest window ever
seen", not "missing data", so this module returns NaN. Measured on a flat
300-bar frame: that branch fills all 280 windows with exactly 0.0 where this
column reports on none.

### The accumulator trust test

`rolling.var` and `rolling.sum` are ONLINE in pandas — a value is added when
it enters the window and subtracted when it leaves — so a volatile stretch
leaves a residue in both long after it has left. The test is exact algebra on
the window's own range `s = max - min`, which `rolling.max`/`rolling.min`
compute by a deque and therefore LOCALLY: a population variance cannot exceed
`(s/2)²` (equality at equal mass on the two ends, which an alternating window
reaches at an EVEN `length`; at an odd one it is just inside — A1), and
`length-1` squared successive differences cannot exceed `(length-1)·s²`.
Slack: 4096 eps, relative.

**Where it earns its place.** A frame whose returns run at `sigma = hi` for
200 bars and then at `sigma = lo` — a stock that crashes and then freezes.
All three pairs the script runs, so a reader can see where it stops biting:

| hi → lo | fires with the test | without | bars NaN *only* because of it | max \|without − oracle\| on bars 221… | unguarded `var` ≤ 0 on bars 221… |
|---|---|---|---|---|---|
| 0.3 → 1e-9 | 199 | 380 | **181** (219…399) | **6.323** | 0 |
| 0.3 → 1e-7 | 380 | 380 | **0** | 1.291e-02 | 0 |
| 0.05 → 1e-9 | 199 | 199 | **0** | — | **179** |

The per-window oracle fires on all 380 of each and its median over bars 221…
is 5.757, so on the first row the error without the test is the **size of the
value**. The second row is the honest limit: close the sigma gap by two
orders of magnitude and the test stops rejecting, while the error is already
down to 1.3e-02. On the third the test is not what empties the bars — the
accumulator comes back non-positive on 179 of them and the FLOOR does it, as
the last column measures rather than infers.

What the test cannot do is recover the value — the per-window oracle still
has one; the trade is a plausible number for a missing one, which is the
right way round for an ML feature.

**Where it does nothing.** On seven clean frames — walk, tick-rounded, AR(1)
at φ = ±0.5, the alternating frame, a `sigma = 1e-6` walk and a fine-tick
ladder — it costs **0 bars** (1,480 fires on each). The alternating frame
attains BOTH bounds EXACTLY, at measured ratios of
`var/bound = 1.000000000000` and `gap/bound = 1.000000000000`, which is why
the slack is 4096 eps relative rather than zero.

**Where it is not a cure.** A single planted return, bar 200 of a 400-bar
walk, tail = bars 222…399 (which hold no part of it):

| planted | tail NaN with the test | without | max \|without − oracle\| | caught by the test |
|---|---|---|---|---|
| 1e+2 | 0 | 0 | 4.753e-09 | no |
| 1e+4 | 0 | 0 | 5.559e-05 | no |
| 1e+6 | 0 | 0 | **7.859e-01** | no |
| 1e+8 | 178 | 178 | — | no — see below |

A window that still remembers a wide range allows the residue, so the bound
is satisfied. A 100× bar is a thing a market can do; 1e+6 is a broken feed.
At 1e+8 the bars are NaN for a different reason, measured: on all 178 of
them the variance accumulator itself comes back **≤ 0**, so the floor empties
them (0 bars have `0 < var <= floor`, 0 have a negative squared-difference
sum, 0 pass both). Between those two magnitudes, at 1e+7, this test is
exactly what empties the bars — the next section measures all four.

There is deliberately **no `gap >= 0` test** in the module. Every term of the
sum is a square, and rather than assert that no sum goes negative, the script
counts them (Guard 3b): **0 negative sums over 20,680 windows of 18 frames**
— the clean ones, the degenerate ones, the two-scale frame, the four planted
spikes and three bad-close frames. And if an online accumulator ever did land
below zero, the quotient is negative and its square root is NaN — the right
answer — so such a test would change no output and would be a guard with no
measurement behind it. What the module does have is an
`errstate(invalid="ignore")` around the square root, so that NaN would arrive
without a RuntimeWarning out of library code.

### ⚠ One huge return empties — or corrupts — the rest of the series

The per-return square bound below keeps an **unrepresentable** square local.
It does nothing about a *representable* return that ruins the accumulator's
conditioning, and that is the worst thing about this column. There is **no
single threshold**: the behaviour and the mechanism both change with the
magnitude. Measured on a 2,000-bar walk with one return planted at bar 200,
so 1,799 bars follow it, and the error scored on bars 221… (the first window
that holds no part of the planted return), by index, so every row is scored
on the same bars:

| planted return | later bars emptied | bars that still fire | last bar that fires | max \|column − oracle\| on bars 221… | unguarded `rolling.var` ≤ 0 on bars 221… | which guard emptied them |
|---|---|---|---|---|---|---|
| 1e+6 | **0** / 1,799 | 1,799 (201…1999) | 1999 | **7.859e-01** over 1,779 bars | 0 / 1,779 | none — it reports, and it is WRONG |
| 1e+7 | **1,643** / 1,799 | **156** (201…1859) | 1859 | **3.868e+00** over 136 bars | 0 / 1,779 | the **trust test** — the variance is positive, so the floor is not involved |
| 1e+8 | **1,779** / 1,799 | **20** (201…220) | 220 | — (nothing fires there) | **1,779** / 1,779 | the **floor**: the accumulator itself is non-positive |
| 1e+10 | **1,780** / 1,799 | 19 (201…219) | 219 | — | 1,779 / 1,779 | the floor |

Read the rows, not a threshold:

* at **1e+6** nothing is emptied and the column is silently 0.786 wrong —
  the worst outcome of the four, and nothing here catches it;
* at **1e+7** the trust test empties 1,643 bars and the 156 that survive are
  up to 3.868 out, so the column half recovers with corrupt values;
* at **1e+8 and above** the 20 bars that fire are exactly the windows that
  still hold the planted return (201…220), and **nothing fires after bar
  220** for the remaining 1,779 bars.

**The cause is pandas' ONLINE `rolling.var`, not this module's arithmetic**,
and the evidence is the `var ≤ 0` column above — taken on the raw returns
with no guard in front of it. The same frames through `ts_ac1_60` empty
exactly the same bars (0 / 1,643 / 1,779 / 1,780), but that is **expected
rather than independent**: the sibling shares this port's floor and its trust
test verbatim, so equal masks are guaranteed by construction, not evidence.

`tests/test_ts_cid_ce_20.py::test_one_huge_return_empties_or_corrupts_the_rest_of_the_series`
pins all four rows — the emptied count, the firing count, the last firing
bar, the `var ≤ 0` count and the error where it fires — plus the fact that
nothing BEFORE the planted bar moves.

**Not fixed, disclosed** — and the reasons are on the record rather than
implied:

* a magnitude bound that made the damage local would be an arbitrary constant
  (the crossover measured here is between 1e+6 and 1e+7 on one frame shape,
  and it is a function of the window's own scale, not a universal number);
* the only spelling that is structurally local is a per-window pass, which
  costs 35.7 s against this module's 55–59 ms on 400,000 bars (Cost);
* every return-window statistic in this fork that divides by a rolling
  variance has the same behaviour, so "fixing" it here alone would make this
  port disagree with its neighbours on a shape none of them has met in real
  data.

What would settle how much it matters is the Gate E run, which is why it was
listed as an open item there. **It has now run, and it did not happen**: all
1,780 NaN bars of the 89 BIST frames are the warm-up (Gate C above), so no
window on 398,849 real bars was emptied by the floor or the trust test. That
bounds how often this shape occurs on this universe, at this timeframe, on
these 89 symbols. It does not make the failure mode go away — the 1e+6 row,
where the column reports and is 0.786 wrong, leaves no trace in a NaN count
at all.

### The per-return square bound

Every kept return has `r² < max/(8·length)`, which is a ceiling of
**1.0600e+153** on a return at `length` 20 — nothing a market can produce.
Its job is to keep an unrepresentable square LOCAL, because an infinite
online accumulator never leaves the window:

| planted close | guarded: bars lost | unguarded |
|---|---|---|
| 1e-300 at bar 200 | **20** (201…220) | **199** (201…399) — the whole remainder |
| 1e-200 at bars 200 and 230 | **40** (201…250) — the union of their windows | 199 (201…399) |

The two-hole row is what makes the locality structural rather than measured
on one shape.

### NaN rules, measured

| cause | bars emptied |
|---|---|
| warm-up | the first `length` = 20 |
| close NaN / 0.0 / −5.0 / inf / 1e-310 at bar 200 | exactly **21** (200…220) = `length + 1`, with **0** earlier bars moved, for each of the five |
| 19 or 20 identical closes at bar 200 | 0 |
| 21 identical closes | 1 (bar 220) |
| 25 identical closes | 5 (bars 220…224) |
| **a single enormous return** | magnitude-dependent, and NOT a clean rule — 0 of the 1,799 later bars at 1e+6 (they fire and are 0.786 wrong), 1,643 at 1e+7 (156 still fire, up to 3.868 out), 1,779 at 1e+8 with nothing firing after bar 220, measured on a 2,000-bar frame: see "One huge return empties — or corrupts — the rest of the series" above |

A bad close spoils two returns, which is why it empties `length + 1` windows
and not `length`. A flat run needs all `length + 1` closes to empty one bar.

Warm-up boundary: 20 closes returns `None`; exactly 21 closes fires 1 bar, at
bar 20.

### Parameters

| `length` | name | fires on a 400-bar walk |
|---|---|---|
| `None`, 0, −5, 1, 2, 0.5, 2.9 | `TS_CID_CE_20` | 380 |
| 3 | `TS_CID_CE_3` | 397 |
| 50.9 | `TS_CID_CE_50` | 350 |

`length` 10 against 250 on the same frame: Spearman **0.033329** over 150
shared bars — distinct columns, not a rescaling. `fillna=-9.0` fills exactly
the 20 warm-up bars.

## Gate E — attribution

**Measured: SHIP.** The launcher ran
`gate_e_overlap.py run --module pandas_ta.statistics.ts_cid_ce_20` on the code
at this branch's porting commit; the run is `is95-ts_cid_ce_20-524cb24a`,
measured **2026-11-13**, and it is recorded in `docs/gate_e_ledger.csv` by
`python docs/gate_e_ledger.py record`, which refuses a run whose
`pandas_ta_src_sha1` is not this tree's.

Run facts, from the outputs' `meta.json`: default parameters (`kwargs` empty,
no `end`, nothing excluded, no rename), **89** frozen ALTPORT-1 BIST frames,
**398,849** pooled bars, **687** comparators (**329** `compute_all` ∪ **358**
`ml_features` manifest `1d`), canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS
bit-equal`, pandas 2.3.3 / numpy 1.26.4, module sha1
`413370d24efe0b1a0c26bf166096c741bd7fa161`, tree sha1
`4b82af1ac4766458facff575a9f82246f2ed5c7d`, data stamp
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`.

**The verdict, under `r3-perframe-0.90`:**

| | value |
|---|---|
| column | `TS_CID_CE_20` |
| max \|ρ\| | **0.2640577551656063** |
| against | **`chop`** (`compute_all`) |
| n | **396,927** |
| per-frame max median \|ρ\| | **0.2646621871502909** (against `chop`, over 89 frames) |
| verdict | **SHIP** |

Both legs are far below the 0.76 ship line and the 0.90 per-frame line, and
the pooled and per-frame readings agree on the same comparator. The verdict is
`SHIP` on the pooled statistic alone as well (`verdict_pooled_only`).

The maximum over each comparator set separately: **0.2640577551656063** vs
`chop` over `compute_all` at n = 396,927, and **0.2107305498561499** vs
`squeeze_SQZ_OFF` over the manifest at n = 397,069. **One** of the 687
comparators was degenerate — `squeeze_SQZ_NO`, constant over the pooled
sample.

**The top five, pooled and per frame** (`top25.csv`, `perframe.csv`; the sign
is the signed ρ, the ranking is on \|ρ\|):

| against | set | ρ | n | per-frame median | per-frame max | % frames ≥ 0.90 | ≥ 0.80 |
|---|---|---|---|---|---|---|---|
| `chop` | compute_all | **+0.264058** | 396,927 | 0.264662 | 0.425008 | **0.0** | **0.0** |
| `BB_BWidth` | compute_all | −0.224964 | 397,069 | 0.223973 | 0.480469 | 0.0 | 0.0 |
| `CHOP` | compute_all | +0.223876 | 396,311 | 0.218391 | 0.418931 | 0.0 | 0.0 |
| `squeeze_SQZ_OFF` | manifest | −0.210731 | 397,069 | 0.204187 | 0.330375 | 0.0 | 0.0 |
| `squeeze_SQZ_ON` | manifest | +0.210731 | 397,069 | 0.204187 | 0.330375 | 0.0 | 0.0 |

So **no** frame reaches 0.80, let alone 0.90, against any of the top five: 0.0
on all ten of those cells. The highest single frame anywhere in the top five
is 0.480469 against `BB_BWidth`. The 25th row of `top25.csv` is
`mad_pct_State` at 0.1328633866577621, so the whole visible tail is under
0.14.

**What the neighbours are** — the five are range-efficiency and
volatility-width readings (`chop`, `CHOP`, `BB_BWidth`, the two `squeeze`
flags), and the rest of `top25.csv` is the same family through percentiles,
states and regime flags (`Swing_Range_pct`, `BB_BWidth_Pctl`, `THERMO_pct`,
`mad_pct`, `ui`, `EFFICIENCY_RATIO`/`er`, `Range_ATR`) plus two ages
(`kama_Cross_Age`, `Supertrend_Flip_Age`). That reading is from their **names**
and is an interpretation; the numbers are the measurement. It is worth setting
against this file's synthetic figure of Spearman **0.007243** between this
column and the same 20 returns' standard deviation on a walk: the pooled
+0.2641 against `chop` is a bigger number than "not volatility" would suggest,
and the synthetic frames are not BIST prices — both are recorded, neither is
reconciled here.

### The three open items the porting session left, answered

1. **Gate C on real data — the guards cost 0 bars.** The run reports
   **397,069** non-NaN and **397,069** non-zero of **398,849** pooled bars, so
   `pooled_bars − non_nan` is **1,780**, which is exactly `20 × 89` — the
   warm-up, one window per frame. None of this port's three guards (the
   8.27e-25 variance floor, the per-return square bound, the accumulator trust
   test) emptied a single window on the 89 BIST frames. The synthetic tables
   above could only show they cost 0 bars on seven synthetic frames; this
   shows 0 bars on 398,849 real ones, and it means the accumulator failure
   disclosed above did not occur on this universe. No fired bar is exactly
   0.0 either, which A2's reachable minimum of 0.701759 says it cannot be.
2. **The overlap against the shipped `TS_AC1_60` stays SYNTHETIC-ONLY.** It is
   not in this run: **no** `TS_AC1` column appears in any of the run's four
   output files (`overlap_max.csv`, `top25.csv`, `perframe.csv`,
   `degenerate.csv`), the comparator set is the engine's and not this fork's,
   and a receipt session cannot reach `../Backtesting` to join the two runs.
   So the redundancy section's −0.4218 / −0.5342 / −0.4339 remain measured on
   three synthetic shapes, and **nothing here measures that pairing on real
   data**. It stays the disclosure it was.
3. **The screen's figures carried over, to four decimal places.** Issue #95's
   prototype is this column times `sqrt(20/19)`, a positive constant a
   Spearman cannot see, and the run lands on the same comparators in the same
   order:

   | | screen (prototype, run `screen_20261024`) | this run (the module) |
   |---|---|---|
   | max \|ρ\| | 0.2641 vs `chop` | **0.2640577551656063** vs `chop` |
   | n | 396,927 | **396,927** |
   | top-5 per-frame max median | 0.2647 | **0.2646621871502909** |
   | next comparators | `BB_BWidth` 0.2250, `CHOP` 0.2239 | **0.2249644**, **0.2238765** |
   | verdict | SHIP | **SHIP** |

   The identical n is the thing to read: the porting session's open worry was
   that this port's guards would empty windows the prototype reports on, which
   would move the ranked sample. Item 1 measures that they emptied **0**, so
   the two columns are ranked over the same bars and a positive rescaling
   cannot move a Spearman. The agreement is a result of that, not a licence to
   have copied the screen's numbers in: nothing before the run bounded the gap
   between two maxima taken over 687 comparators.

### What is NOT claimed about this run

* It does not re-measure the issue's **stage-2 fork overlap** (0.2676 vs
  `chop:CHOP_14_1_100` over 12 frames). No `CHOP_14_1_100` column appears in
  this run's outputs; the engine's `chop` and `CHOP` are its own columns. The
  run neither confirms nor refutes that figure.
* It says nothing about **non-default lengths**. `record` refuses a run with
  non-default parameters, so `length` other than 20 is unmeasured at Gate E.
* The 687 comparators contain no pandas_ta port column that this run surfaced,
  so Gate E cannot see the redundancy disclosed above — item 2.

## Gate F — suites

This session ran, in this worktree, on the code as it now stands:

* `python -m pytest tests/test_ts_cid_ce_20.py -q` → **133 passed** (128
  before the review rounds in `docs/reviews/auto-2026-11-13-ts-cid-ce-20/`
  added the four that pin the accumulator failure above; 132 before this
  receipt session replaced the "no ledger row yet" assertion with the two
  that pin the row);
* `python -m pytest -q -p no:randomly` → **3 failed, 6,716 passed, 83
  skipped** in 147 s. The three failures are the two `CLAUDE.md` *Known
  breaks* — `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  (the untracked `docs/pine/` corpus) and
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  (needs the sibling `../AlternativeRepos` checkout, which CI deselects) —
  plus `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  which reports exactly `['mtd_ret']`: #206's owed row on `dev`. **This port
  is no longer on that list** — the porting session's run reported
  `['mtd_ret', 'ts_cid_ce_20']` and the recorded row removed the second.
  `ci.yml` skips that test on the way to `dev` under `GATE_E_PENDING_OK=1`.

⚠ One ORDER-DEPENDENT failure exists in this suite and it is **not** this
port's: `tests/test_altport2_ports.py::test_the_category_count_moved_by_exactly_three`
fails if any test that runs a category-mode `df.ta.strategy(...)` ran first,
because `pandas_ta/core.py:453` hands out the live `Category[name]` list and
`core.py:692` removes the excluded names from it. Reproduced and written up
in `docs/reviews/auto-2026-11-13-ts-cid-ce-20/01-ts-cid-ce-20.md`; the
arithmetic is −3 either way, so `dev` behaves the same. Owner's call.

The Backtesting suite is not reachable from this worktree. The launcher runs
both repos' suites in clean worktrees after this session, which is Gate F
proper.

## Cost

On 400,000 bars (`python docs/measure_ts_cid_ce_20.py cost`):

Measured on the code **as it ships**, i.e. after the review rounds deleted
the `gap >= 0` branch — that deletion took one input-length array out of the
peak, 3.2 MB on this input, so the figures below replace an earlier run's
32.4 MB:

| | `length` 3 | 20 | 60 | 250 |
|---|---|---|---|---|
| runs 1–3 | 56 / 55 / 59 ms | 57 / 57 / 57 ms | 59 / 57 / 56 ms | 58 / 57 / 56 ms |
| traced peak, every run | 29.2 MB | 29.2 MB | 29.2 MB | 29.2 MB |

Four O(n) rolling passes (the variance, the squared-difference sum and the
two extrema) and no allocation that grows with `length`. The time is a
**band of 55–59 ms** across those 12 calls and is flat in `length`; the peak
reproduced exactly on all 12.

The trust test's two extrema are about **half** of that, in four paired runs
with the flag flipped: **54–55 ms against 26–27 ms** (two in this session,
two when the review re-ran the section). That is the price
of not reporting a plausible number on a volatile-then-frozen frame (Guards),
and it is disclosed rather than buried: this is the most expensive thing in
the module.

The window-by-window oracle the module is checked against is **35.7 s** and
peaks at **80.1 MB** on the same input — unchanged by the deletion, since it
is a different code path — which is why it lives in
`docs/measure_ts_cid_ce_20.py` and not in the module.

## Wiring

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_cid_ce_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_cid_ce_20 import ts_cid_ce_20` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | discovery / `df.ta.strategy()` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_cid_ce_20()` |
| 5 | `tests/test_ts_cid_ce_20.py` | 133 tests |

Plus the counts those move: `README.md` (328 in `Category`, 336 accessors,
statistics 37), `docs/IndicatorDictionary.md` (regenerated by its own
generator — 330 probed, `TS_CID_CE_20` tagged `SF` with a 20-bar warm-up),
`docs/MLCompanionContract.md` (673 tagged columns, 315 `SF`) and
`tests/test_altport2_ports.py::CATEGORY_TOTAL` (328).

`tests/test_ts_cid_ce_20.py::test_name_registration_and_accessor` asserts
that the direct call and `df.ta.ts_cid_ce_20()` return the same Series under
the same name.
