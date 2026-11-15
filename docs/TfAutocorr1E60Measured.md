# `tf_autocorr_1e_60` — measured

PandasTa issue **#114**, TF-AUTOCORR-1E-60: *first 1/e crossing of the ACF of
log price (60)*. Source: TSFEL (BSD-3-Clause), `features.py autocorr: first
lag with ACF < 1/e`; scale-free form "on log close, 60-bar window, lags 1..20
(21 = none)".

| | |
|---|---|
| module | `pandas_ta/statistics/tf_autocorr_1e_60.py` |
| column | `TFAUTOCORR1E_60` (a whole number in `[1, 21]`) |
| category | `statistics` |
| tests | `tests/test_tf_autocorr_1e_60.py`, 199 tests |
| harness | `docs/measure_tf_autocorr_1e_60.py` |
| environment | numpy 1.26.4, pandas 2.3.3, statsmodels present |

Reproduce with `python docs/measure_tf_autocorr_1e_60.py <SECTION>`. The
harness sections are `A B C D E F G H T Z`. **The doc's headings and the
harness's letters are not one-to-one** — the mapping is:

| this document | run |
|---|---|
| §A (incl. A6, A6b), §B, §C, §E1, §G, §H, §Z | harness `A`, `B`, `C`, `E`, `G`, `H`, `Z` |
| §D | harness `D` for the rescales, margins and `0 < fires < n`; harness **`F`** for the amplitude/drift table and the drivers quoted in the module docstring |
| §F (suite counts) | `python -m pytest -q`, and `python docs/measure_tf_autocorr_1e_60.py --no-avx T` for the AVX-disabled run |

`--no-avx` re-executes the file with
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` set before numpy is
imported, which is what a GitHub runner without AVX-512 gives numpy's kernels.
It is spelled as a flag because the shell this ran under cannot put a variable
in front of a command.

**Verdict: SHIP, pending Gate E.** Gates A, B, C (synthetic), D and F are met
below. Gate E is owed — the launcher runs
`gate_e_overlap.py run --module pandas_ta.statistics.tf_autocorr_1e_60` after
this session and a later session records the `docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.

---

## 0. What the column is

Over the `length` log prices ending at the current bar, take the **adjusted**
autocorrelation at lags 1, 2, … and report the **first lag whose value falls
below 1/e**. No crossing in 1..20 reads 21.

    g[t]   = log(close[t] / close[t-1])
    X      = 0, g, g+g, …                       (the window's log prices,
                                                 from its own first close)
    d      = X - mean(X)
    v      = mean(d*d)
    ACF(k) = (sum of the length-k products d[i]*d[i+k]) / (length-k) / v
    TFAUTOCORR1E = min{k in 1..20 : ACF(k) < 1/e}, else 21
                   NaN when sqrt(v) <= 9.09e-13

**It reads how STRAIGHT the window is, not how volatile.** Rescaling every log
return of the window by x0.5, x2 or x10 leaves the column bit-identical on all
1,441 fired bars (§D), because `d` scales by the same constant and it cancels
in `ACF(k)/ACF(0)`. The two deterministic extremes fix the scale: an exactly
geometric path (log price a straight line) reads **16** on every bar, and a
path alternating up and down every bar reads **1**.

## 1. Attribution, and what it is NOT evidence of

TSFEL is **not a dependency** of this package, dev or otherwise. It is not
installed in this worktree, `docs/pine/` does not carry it and web access is
unavailable. Per the issue, "Library code (TSFEL, BSD-3-Clause): existence,
not evidence": the licence and the project are cited, the library is neither
vendored nor run as an oracle.

So the formula under test is **the issue's two lines**, not a read of TSFEL's
source. Nothing in this port, this document, the module docstring or the test
file describes TSFEL's source text. How TSFEL treats NaNs, an empty series, a
constant series, or which lag count it defaults to is **unverified here**.
`tests/test_tf_autocorr_1e_60.py::test_the_source_library_is_not_readable_here`
asserts `import tsfel` raises, so this limitation fails loudly if the
environment ever changes.

The `60` and the `20` lags are the issue's own parameters.

---

## A. Gate A — correctness

### A1. Against the screen prototype, retyped

The prototype is `docs/issues/screen/ind_screen_r2.py:190-206` (candidate
`tf_autocorr_1e_60`), `roll(np.log(c), 60, _acf_first_1e)`. `docs/issues/` is
gitignored, so the prototype is retyped in both the harness and the test file.
Bit-equality on four 1,500-bar frames:

| frame | bit-equal | masks equal | max abs difference | windows reaching the floor |
|---|---|---|---|---|
| walk | 1441/1441 | yes | 0 | 0/1441 |
| tick-rounded | 1441/1441 | yes | 0 | 0/1441 |
| ar1 | 1441/1441 | yes | 0 | 0/1441 |
| sine | 1441/1441 | yes | 0 | 0/1441 |

The floor column matters: the prototype carries **no** noise floor, so the
comparison would be contaminated if the module's floor ever fired. It fires on
0 of 5,764 windows, so the oracle and the module are compared floor-free.

### A1b. Against the owner's own registry entry, imported

When `docs/issues/screen/ind_screen_r2.py` is present, the harness imports
`REG["tf_autocorr_1e_60"]["fn"]` and runs it. Module vs import: **1,441 of
1,441** on each of the four frames, masks equal. Retype vs import: **1,441 of
1,441** on each, masks equal — the retype is faithful.

### A2. Against a plain-Python `math.fsum` spelling

No numpy windowing, explicit slices, `math.log` of the **absolute** price, no
noise floor; written from the formula text. Bit-equal **1,441 of 1,441** on
each of the four frames, masks equal, max difference 0.

### A3. Against statsmodels

`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False, nlags=20)[1:]`
applied to `log(close)` window by window. statsmodels **is** installed here.
Bit-equal **1,441 of 1,441** on each of the four frames. This is the one place
the "adjusted" reading could have been wrong, so it is measured and not
assumed.

### A4. Hand-derived, in exact rational arithmetic

On an exactly geometric path the window's log price is a straight line
`d[t] = t - (n-1)/2`, whose adjusted ACF is a closed form evaluated in
`fractions.Fraction` against a 60-digit rational for 1/e — **no float
anywhere**:

| `length` | closed form | module reads | fired |
|---|---|---|---|
| 40 | 11 | `{11}` | 1461/1500 |
| 45 | 12 | `{12}` | 1456/1500 |
| 60 | **16** | `{16}` | 1441/1500 |
| 100 | 21 (none) | `{21}` | 1401/1500 |
| 250 | 21 (none) | `{21}` | 1251/1500 |

And 16 is the shape of a straight line, not the size of its slope: ladder
steps of +1%, +0.1% and -0.5% all read `{16}` on every fired bar.

### A5. The attainable set

* a path alternating up and down every bar: `{1}` on all 1,441 bars;
* 4,000 iid-increment 60-bar windows: **2 … 18**, counts 38 / 159 / 282 / 357
  / 385 / 365 / 349 / 314 / 296 / 239 / 239 / 259 / 259 / 267 / 166 / 24 / 2;
* a cosine in log price of period P, one window each: P = 4 → 1, 6 → 2, 10 →
  2, 20 → 4, 40 → 7, 120 → 16, 400 → 15.

### A5b. Is the 21 sentinel reachable at `length` 60?

**Not settled, and nothing produced one here.** A single-lag upper bound is
exact: the largest ACF(k) any demeaned window can have is `n/(n-k)` times the
top eigenvalue of the lag-k product form restricted to the demeaned subspace.

| `length` | k=1 | k=10 | k=20 |
|---|---|---|---|
| 40 | 1.0136 | 1.0787 | 1.0000 |
| 60 | 1.0116 | 1.0812 | **1.0607** |
| 100 | 1.0081 | 1.0661 | 1.0825 |
| 250 | 1.0037 | 1.0341 | 1.0597 |

1.0607 is far above 1/e, so no bound here rules the sentinel out — but a
NO_CROSSING window needs **all twenty** lags at or above 1/e at once. A
directed search over 30,000 smooth random windows (a ramp plus six
low-frequency cosines, biased toward trend) reached a best of **18**. Combined
with the frames and the sampling above: **0 of 5,764 fired bars, 0 of 4,000
iid windows, 0 of 30,000 searched windows** read 21 at `length` 60. At
`length` 100 and 250 it is ordinary — the exact geometric ladder reads 21 at
both, and so does the maximum of a plain walk.

This is stated as a measurement, not a theorem, in the module docstring, in
the test docstring and here.

### A6. The one difference in the ARITHMETIC

The prototype reads `np.log(close)`; the module cumulates the window's own
`log(close/close[1])` from zero. The two are the same series up to an additive
constant, which the demeaning removes — a spelling, not a reading. Measured as
one:

| frame | bit-equal | masks equal | max abs difference |
|---|---|---|---|
| walk | 1441/1441 | yes | 0 |
| tick-rounded | 1441/1441 | yes | 0 |
| ar1 | 1441/1441 | yes | 0 |
| sine | 1441/1441 | yes | 0 |

and at price levels 1e-6, 1, 1e3, 1e6 and 1e9 (where `log(close)` runs to 20.7
and the window is 0.05 wide, so the direct spelling loses roughly two decimal
digits to cancellation that the ratio form never forms): **1,441 of 1,441** at
every level, max difference 0.

What it buys is Gate D by construction: `8a / 8b` is the same double as
`a / b`, so an exact binary rescale cancels **before** any transcendental
runs. The direct `log(close)` spelling would have to be measured frame by
frame instead.

### A6b. The two BEHAVIOURAL divergences from the prototype

A6 is the only difference in the arithmetic. It is **not** the only
difference, and a clean synthetic frame cannot show either of the other two.

**(1) Bad data: the prototype reports the sentinel, this module reports NaN.**
The prototype's only guard is `np.where(var == 0, np.nan, out)`. A window
holding a bad close has `var` **NaN**, not 0, and `NaN == 0` is False — so the
prototype emits a number. One bad close at bar 700 of a 1,500-bar walk:

| close[700] | bars this module empties and the prototype fires | the reverse | what the prototype reads there | bit-equal either side |
|---|---|---|---|---|
| NaN | 60 | 0 | 21 | 1381/1381 |
| 0.0 | 60 | 0 | 21 | 1381/1381 |
| -5.0 | 60 | 0 | 21 | 1381/1381 |
| +inf | 60 | 0 | 21 | 1381/1381 |
| 1e-310 | 60 | 0 | **1** | 1381/1381 |

The subnormal row is the odd one: `log(1e-310)` is a large *finite* number, so
the window is dominated by a single outlier and the lag-1 autocorrelation
collapses below 1/e instead of the ACF never crossing.

**(2) The noise floor, which the prototype does not have.** On a price flat at
1e6 stepping one double ulp a bar, this module fires **0** bars and the
prototype fires **1,441**, reading 17, 18, 19, 20 and 21 — the shape of
`log(close)`'s own rounding. (§G measures what the floor buys and costs on the
module's own unguarded form, which reads a constant 16 on the same path: the
two unguarded readings do not even agree with each other, which is the point
of refusing the window.)

Both are pinned by
`tests/test_tf_autocorr_1e_60.py::test_the_prototype_reports_the_sentinel_where_this_module_reports_nan`
and `::test_the_prototype_has_no_floor_and_reads_rounding_noise`.

### A7. The readings the issue's line leaves open

**(a) ADJUSTED, not biased.** The lag-k products are divided by `length - k`
(the prototype's `.mean(1)` over a width-`length-k` slice; statsmodels'
`adjusted=True`), while the divisor `v` is over all `length` points. The
biased reading — divide by `length` — is a **genuinely different column**, not
a rescaling:

| frame | bit-equal | max abs difference | Spearman |
|---|---|---|---|
| walk | 519/1441 | 6 | +0.981376 |
| tick-rounded | 589/1441 | 7 | +0.982642 |
| ar1 | 424/1441 | 9 | +0.977481 |
| sine | 720/1441 | 1 | +0.694492 |

**(b) Strict `<`, not `<=`.** Bit-equal on 1,441 of 1,441 bars of all four
frames, with **0 exact ties** with 1/e in 5,764 windows (§D). The difference
is unreachable on these frames rather than cosmetic; `<` is kept because it is
what the issue's line and the prototype say.

**(c) The ACF of LOG PRICE, not of returns.** This is the reading that decides
the column exists at all. The same construction applied to log **returns** is
the **constant 1** on a walk and on a tick-rounded walk — returns are near
uncorrelated, so lag 1 is already below 1/e on every one of 1,440 windows —
which fails Gate D's "not constant" outright (Spearman is undefined against a
constant). On the AR(1) path it varies and its Spearman against this column is
-0.168701; on the cosine, +648 of 1,440 bars agree and Spearman is -0.908688.
Log price is an *integrated* series, which is why its ACF decays slowly enough
to carry information.

---

## B. Gate B — causality

A future-perturbation sweep: replace every bar from `J` onward with a
different path and look for any change strictly before `J`. 35 offsets,
`J = 120, 160, … 1480`. Prefix truncation cannot see back-dating, which is why
this is a perturbation sweep and not a truncation.

**The real module leaks 0 of 35 on every configuration run**: a walk, a
tick-rounded walk, an AR(1) path, and again at `length` 40, 100 and 250.

Six mutants, each `importlib`-read off the shipped file, edited and `exec`'d
in memory. Offsets caught of 35:

| mutant | what it moves | walk | tick-rounded | ar1 |
|---|---|---|---|---|
| `write_shift` | the whole column back-dated by `length` | 35 | 35 | 35 |
| `write_early` | the chunk written one bar early | 34 | 32 | 35 |
| `forward_return` | the log return read one bar ahead | 33 | 28 | 34 |
| `forward_mean` | the window mean taken from the next window | 25 | 20 | 23 |
| `forward_product` | the lag product taken from the next window | 31 | 31 | 34 |

At non-default lengths, on the walk:

| `length` | real | write_shift | write_early | forward_return | forward_mean | forward_product |
|---|---|---|---|---|---|---|
| 40 | 0 | 35 | 35 | 35 | 27 | 31 |
| 100 | 0 | 35 | 34 | 28 | 13 | 31 |
| 250 | 0 | 34 | 16 | 13 | **5** | 14 |

**The cells under 35 are asserted with their mechanism, not excused.** A
one-bar look-ahead can move exactly ONE bar of the prefix — `J - 1`, the only
bar whose window reaches `close[J]` — and the harness measures that directly:
for `write_early`, `forward_return`, `forward_mean` and `forward_product` the
set of moved-bar offsets over all 35 cuts is exactly `{(), (-1,)}`. So a
missed offset is one where that single **integer** did not change. The density
behind it:

| frame / length | consecutive bar pairs carrying the same value |
|---|---|
| walk | 1,014 / 1,440 (70%) |
| tick-rounded | 1,058 / 1,440 (73%) |
| ar1 | 1,041 / 1,440 (72%) |
| sine | 1,152 / 1,440 (80%) |
| walk, `length` 40 | 1,013 / 1,460 (69%) |
| walk, `length` 100 | 1,088 / 1,400 (78%) |
| walk, `length` 250 | 1,153 / 1,250 (92%) |

That 92% is why `forward_mean` falls to 5 of 35 at `length` 250, and why the
test file asserts the back-dating mutant there and leaves the one-bar mutants
to the mechanism test.

**The sixth mutant** covers `sd`, the module's other windowed quantity and the
one the noise floor reads. It is a no-op on a continuous frame (the floor never
fires there), so it is swept on a walk carrying 61 identical closes ending at
each offset: the real module still leaks **0 of 35** planted frames and the
mutant is caught on **35 of 35**. It leaks at exactly one offset per frame —
the plant position — because reading the next window's `sd` can only change a
bar whose neighbour sits on the other side of the floor.

---

## C. Gate C — reachability

Synthetic only. **Real-data counts are owed with Gate E.**

| frame | fired | first bar | distinct | min | max | median | mean |
|---|---|---|---|---|---|---|---|
| walk | 1441/1500 | 59 | 15 | 3 | 17 | 8 | 8.8890 |
| tick-rounded | 1441/1500 | 59 | 15 | 2 | 16 | 8 | 8.6149 |
| ar1 | 1441/1500 | 59 | 15 | 3 | 17 | 10 | 10.1520 |
| sine | 1441/1500 | 59 | 3 | 7 | 9 | 8 | 8.1006 |

Every bar with a full window fires; the first is bar `length - 1` = 59, which
needs `length` closes and not `length + 1` (the window holds log **prices**).

Counts on the walk: 3→50, 4→98, 5→109, 6→131, 7→134, 8→200, 9→125, 10→135,
11→131, 12→90, 13→78, 14→63, 15→50, 16→43, 17→4.

The 21 sentinel: **0 of 1,441 on each of the four frames** (§A5b).

Non-default lengths on the walk:

| `length` | fired | distinct | min | max | mean |
|---|---|---|---|---|---|
| 40 | 1461 | 10 | 2 | 11 | 6.1684 |
| 45 | 1456 | 12 | 2 | 13 | 6.8620 |
| 100 | 1401 | 17 | 5 | **21** | 13.2684 |
| 250 | 1251 | 14 | 8 | **21** | 18.8801 |

On the dictionary generator's own probe frame (`docs/gen_indicator_dictionary.py`,
`N = 600`, `rng(7).normal(0, 0.012)`): fired 541/600, **15 distinct** values
3..17. The "`<= 12` distinct integers" rule at line 147 therefore does not
fire and the column is tagged `SF` rather than `ORD` — by three values, not by
a wide margin, so a flatter probe frame could flip the tag.

Guard band: `length` of `None`, 0, -5, 1, 39 and 39.9 all fall back to
`TFAUTOCORR1E_60`; 40 gives `TFAUTOCORR1E_40`. `MIN_LENGTH = 2 * NLAGS = 40`
is two points per lag at the longest lag, so the adjusted estimator still
averages 20 products there.

---

## D. Gate D — scale-free

**Exact binary factors are bit-identical BY CONSTRUCTION.** Every input to the
window is `log(c[1:] / c[:-1])`, and `8a / 8b` is the same double as `a / b`,
so the rescale cancels before any transcendental runs.

| frame | x8 | x64 | 2**-40 | 2**40 |
|---|---|---|---|---|
| walk | 1441/1441 | 1441/1441 | 1441/1441 | 1441/1441 |
| tick-rounded | 1441/1441 | 1441/1441 | 1441/1441 | 1441/1441 |
| ar1 | 1441/1441 | 1441/1441 | 1441/1441 | 1441/1441 |
| sine | 1441/1441 | 1441/1441 | 1441/1441 | 1441/1441 |

NaN masks equal in all sixteen cells. The same four factors at the four
non-default lengths — sixteen more cells, all bit-identical with masks equal:

| `length` | x8 | x64 | 2**-40 | 2**40 |
|---|---|---|---|---|
| 40 | 1461/1461 | 1461/1461 | 1461/1461 | 1461/1461 |
| 45 | 1456/1456 | 1456/1456 | 1456/1456 | 1456/1456 |
| 100 | 1401/1401 | 1401/1401 | 1401/1401 | 1401/1401 |
| 250 | 1251/1251 | 1251/1251 | 1251/1251 | 1251/1251 |

**Inexact factors** (x10, x3.7, x0.1, x1.0000001) come out bit-identical too —
**1,441 of 1,441 in all sixteen cells, masks equal** — which the arithmetic
does *not* promise for an integer decided by a float comparison. What makes it
hold is measured rather than asserted: the smallest `|ACF(k) - 1/e|` at the
lag each window's answer turns on is

| frame | smallest margin | exact ties | windows |
|---|---|---|---|
| walk | 2.107e-05 | 0 | 1441 |
| tick-rounded | 1.365e-05 | 0 | 1441 |
| ar1 | 5.452e-06 | 0 | 1441 |
| sine | 6.531e-03 | 0 | 1441 |

— nine orders of magnitude from a last-bit decision. The test for the inexact
case is deliberately loose (**at most one bar may differ**) because that
margin is a measurement on four frames, not a guarantee.

**`0 < fires < n`, and not constant:** `0 < 1441 < 1500` on each frame, with
15 / 15 / 15 / 3 distinct values.

**Blind to amplitude, not to drift.** Rescaling the window's log returns x0.5,
x2 or x10 is bit-identical on 1,441 of 1,441 bars; adding a constant log drift
moves almost everything:

| log drift a bar | bars that move, of 1,441 | max abs difference |
|---|---|---|
| +0.001 | 1,271 | 11 lags |
| +0.004 | 1,381 | 14 lags |
| +0.02 | 1,406 | 13 lags |

---

## E. Gate E — **pending, run by issue-solver after this session**

The launcher runs
`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.statistics.tf_autocorr_1e_60` after this session; a later session
records the `docs/gate_e_ledger.csv` row and fills in the measured numbers
here. Until then
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally and is a "Gate E owed" skip in CI.

**What the screen measured on the PROTOTYPE** (2026-10-24, run
`screen_r2_20261024`; a prototype is not a port): max |ρ| **0.4279** vs `ADX`
over 393,598 bars, top-5 per-frame max median 0.4378 → SHIP. Next comparators
`ICHI_TK_CROSS_AGE` 0.3542, `ADX_Pctl` 0.3494. §A1/§A1b above show this module
is bit-equal to that prototype on 1,441 of 1,441 bars of each of four frames,
so the port and the screened quantity are the same column **on every window
whose closes are finite, normal and positive** — §A6b measures where they part
company (a bad close reads 21 in the prototype and NaN here; the prototype has
no noise floor), which matters because the screen ran on 89 real BIST frames
and this port did not. And the screen's figure is **not** this port's Gate E
result and does not stand in for it.

### E1. In-fork overlap, which Gate E's 687 comparators cannot see

Gate E compares against the engine's `compute_all` and the `ml_features`
manifest, neither of which holds a pandas_ta port. So the overlap against this
fork's own autocorrelation/memory columns is measured here instead, by hand
from `pandas_ta/__init__.py`. Spearman, four frames:

| column | walk | tick-rounded | ar1 | sine |
|---|---|---|---|---|
| `ts_ac1_60` | -0.1030 | -0.2455 | -0.2984 | **-0.9036** |
| `ts_aggac_60` | +0.0190 | +0.2967 | +0.1478 | **-0.9017** |
| `firstzero_ac` | +0.0633 | +0.1049 | -0.0190 | -0.7028 |
| `diff2_acf1` | -0.1308 | -0.0914 | -0.2784 | **+0.9166** |
| `tf_dfa_100` | -0.0584 | -0.1197 | -0.2130 | +0.7140 |
| `lean_hurst_100` | +0.3820 | +0.1824 | +0.1123 | **-0.9166** |
| `halflife` | +0.4226 | **+0.4748** | +0.3821 | -0.2639 |
| `lumpiness` | -0.1582 | +0.0330 | -0.0859 | -0.6023 |
| `ts_cid_ce_20` | +0.0595 | +0.0634 | +0.3126 | **-0.9031** |

⚠ **Disclosed rather than buried: the `sine` column.** On the three stochastic
frames the largest |ρ| is **0.4748** (`halflife`, tick-rounded) — comfortably
below the 0.76 ship line. On the deterministic `sine` frame four comparators
exceed 0.90. That frame is a single-frequency path on which *every* memory
statistic collapses to a function of the same phase, so it is not evidence
about redundancy on real data and it is not a Gate E verdict (Gate E's bands
apply to the 89 frozen BIST frames). It is reported because a reader who ran
only the stochastic frames would not know it exists.

⚠ The closest neighbours by construction are `ts_ac1_60` and `ts_aggac_60`,
and both are autocorrelations of **returns**, not of log price — §A7(c)
measures how far apart those two inputs are: on a walk the returns form of
*this very construction* is the constant 1.

Against ADX, the issue's top prototype comparator, on the same synthetic
frames (high/low synthesised as close x1.01 / x0.99, so these are shape
figures and not the Gate E number): walk +0.3148, tick-rounded +0.5030, ar1
+0.5396, sine -0.6958, n = 1,441 each.

---

## F. Gate F — suites

`python -m pytest -q` in this worktree, after the last of the four review
rounds' fixes: **2 failed, 10,971 passed, 85 skipped**. Both failures are
expected:

1. `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
   — it regenerates `docs/altrepo_talib.csv` from the sibling
   `../AlternativeRepos` checkout, which this worktree does not have. It
   touches nothing this port changed, and CI deselects it by name (CLAUDE.md,
   *CI*).
2. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
   — owed Gate E rows. The failure names eight indicators,
   `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'lumpiness',
   'mtd_ret', 'tf_autocorr_1e_60']`: seven were already owed on this branch
   point and `tf_autocorr_1e_60` is this port's. Expected; CI into `dev` runs
   with `GATE_E_PENDING_OK=1`, where it is a "Gate E owed" skip.

An intermediate run before the README counts were updated had three more
failures, all in `tests/test_readme_counts.py`; they are fixed, not waived.

This port's own module:
**199 tests, all passing**, and all 199 pass again under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
(`python docs/measure_tf_autocorr_1e_60.py --no-avx T`).

### F1. What moved under the CI CPU dispatch

Sections C and D were re-run with AVX-512, AVX2 and FMA3 disabled. **Every
figure in both sections is identical** — fired counts, distinct counts, value
histograms, the sixteen exact-binary cells on the frames, the sixteen more at
the non-default lengths, the sixteen inexact cells, the four decision margins
and the zero tie counts. That is expected rather than lucky: the output is an
integer, and §D measures the decision running no closer than 5.5e-06 to the
threshold.

⚠ **One thing DOES move, and it is the threshold itself.** `THRESHOLD =
np.exp(-1.0)` prints as `0.3678794411714424` on this machine's default numpy
dispatch and `0.36787944117144233` with AVX-512, AVX2 and FMA3 disabled —
**one ulp apart** (harness section A's header line prints it, so this is
reproducible rather than asserted). Not one shipped value moves with it, for
the same reason: the margin is 5.5e-06 at worst, nine orders of magnitude from
a last-bit question. It is spelled `np.exp(-1.0)` rather than as a literal
because that is the screen prototype's spelling, so the module and the Gate A
oracle read the same double inside one process whichever dispatch is active —
which is what makes §A1's bit-equality meaningful on either CPU.

Counts that *are* counts of last bits are nonetheless asserted as **bounds**
in the test file (the mutant-catch cells, the tie densities), not as
equalities.

---

## G. The noise floor

`sd(window log price) > 4096 * eps = 9.09e-13`, an absolute constant because
what it bounds is a dimensionless log price ratio, which has no rolling scale
of its own to keep causal. (The same 4096 eps is this fork's habit on such a
quantity: `ts_binent_20`, `ts_strike_20`, `ts_c3_20`.)

**It is inert on anything price-shaped.** 0 of 1,441 windows reach it on each
of the four frames, and guarded and unguarded agree bit-for-bit on every bar
of all four. A monotone one-tick-per-bar path does not reach it either, at any
price tried:

| price | tick | mean log step | windows at the floor | guarded | unguarded |
|---|---|---|---|---|---|
| 50 | 0.01 | 1.749e-04 | 0/1441 | `{16}` | `{16}` |
| 1e4 | 0.01 | 9.993e-07 | 0/1441 | `{16}` | `{16}` |
| 1e6 | 0.01 | 1.000e-08 | 0/1441 | `{16}` | `{16}` |
| 1e6 | 0.001 | 1.000e-09 | 0/1441 | `{16}` | `{16}` |
| 1e9 | 0.01 | 1.000e-11 | 0/1441 | `{16}` | `{16}` |

**What it buys is the ULP band, where the unguarded failure is
ordinary-looking rather than absurd.**

| path | windows at the floor | guarded | unguarded |
|---|---|---|---|
| flat at 1e6, one 1-ulp step at bar 700 | 1441/1441 | no bar fires | 59 bars, values **1 … 15** |
| flat at 1e6, 1 ulp every bar | 1441/1441 | no bar fires | 1441 bars, `{16}` |
| flat at 1e6, 1 ulp every 10 bars | 1441/1441 | no bar fires | 1441 bars, `{15, 16}` |

The single-step row is the dangerous one: a window carrying no information at
all reads an ordinary lag, right inside the live range of a walk (3..17). The
ladder rows are the **cost**, stated rather than hidden: a 1-ulp-per-bar
ladder *is* mathematically an exact geometric path, its answer *is* 16, and
this column refuses it. The band where that happens is a relative price
variation below about 1e-12, which is below any price feed's resolution by
orders of magnitude.

An exactly **flat** window is NaN either way — the variance is exactly 0, so
there is no ACF at all. A flat run planted in a walk: 59 identical closes
empty 0 extra bars, 60 empty 1, 61 empty 2, 65 empty 6.

---

## H. Bad data, and the wiring

A close that is not a finite, normal, positive float is missing. Measured on a
walk with one bar replaced at index 700:

| close[700] | extra NaN bars | prefix unchanged |
|---|---|---|
| NaN | 60 | yes |
| 0.0 | 60 | yes |
| -5.0 | 60 | yes |
| +inf | 60 | yes |
| 1e-310 (subnormal) | 60 | yes |

A close **pair** whose ratio overflows (1e-300 followed by 1e50) spoils one
log return rather than two, so 59 bars.

Short input: 0, 1 and 59 closes return `None` (`verify_series(close, length)`);
60 closes fire 1 bar; 61 fire 2.

Wiring, all five touch points:
`pandas_ta/statistics/tf_autocorr_1e_60.py` · the export in
`pandas_ta/statistics/__init__.py` · `Category["statistics"]` in
`pandas_ta/__init__.py` · the `df.ta.tf_autocorr_1e_60()` accessor in
`pandas_ta/core.py` · `tests/test_tf_autocorr_1e_60.py`. Measured live:
`df.ta.tf_autocorr_1e_60()` returns `TFAUTOCORR1E_60` with 1,441 fired bars
and category `statistics`; `tf_autocorr_1e_60 in ta.Category["statistics"]` is
True; `ta.tf_autocorr_1e_60` is callable. Documents updated: README (353 in
`Category`, 361 accessors, `statistics (55)`),
`docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
(698 tagged columns, 336 `SF`), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL = 353`).

---

## Z. Chunking and cost

The module walks the windows in chunks of `CHUNK_VALUES = 1 << 21` doubles,
because the demeaned block and the lag products are each `(rows, length)` and
would otherwise grow with `len(close) * length`. Every chunk is an independent
run of rows and the arithmetic is row-wise, so where a bar lands must not
matter — if it did, no causality sweep over a single-chunk frame could see it.
Measured on a 4,000-bar walk at budgets **1, 64, 999 and 10\*\*9**: bit-equal
3,941 of 3,941, masks equal, in all four.

At n = 400,000: traced peak **61.2 MB** (tracemalloc), about **1.3 s**, 399,941
bars fired. Wall clock is not quoted as a band because it does not reproduce.

---

## What a consumer must know

1. **21 is a sentinel**, not a measurement — "no crossing in 20 lags". It is
   monotone with the rest of the scale, but at `length` 60 nothing measured
   here produced it (§A5b), and at `length` 100 or 250 it is common.
2. **The column carries no volatility information.** It is bit-identical under
   any rescale of the window's log returns (§D). Pairing it with a volatility
   feature is not double-counting.
3. **It is a slow state.** Consecutive bars tie 70% of the time and its own
   autocorrelation on a walk is +0.9833 at lag 1, +0.6044 at lag 10 and
   -0.1057 at lag 30. It is not an event flag.
4. **It is an ACF, so order inside the window matters**: over 400 sampled
   windows a permutation of the log returns moves it on 361 and a time
   reversal on 117.
5. **Read it against its measured centre**, not against a nominal one: median
   8 on an iid walk of sigma 1.5%, rising to 16 under a +2%-a-bar drift.
