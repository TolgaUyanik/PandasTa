# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Lags searched, 1 .. NLAGS. Fixed, not a function of `length`: 20 is the
#: issue's own parameter and so the ladder the 2026-10-24 screen measured.
NLAGS = 20
#: What a window with no crossing in 1 .. NLAGS reads. A sentinel, but a
#: MONOTONE one: it sits above every real answer, and a window that would
#: cross at lag 25 reads the same 21 as one that never crosses at all.
NO_CROSSING = NLAGS + 1
#: The 1/e the feature is named for, spelled as the screen prototype spells it
#: (`np.exp(-1)`) so that both read the same double inside one process.
#: ⚠ It is NOT the same double on every CPU: measured, this is
#: 0.3678794411714424 on this machine's default numpy dispatch and
#: 0.36787944117144233 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX
#: AVX2 FMA3"` -- one ulp apart. No shipped value moves with it, because the
#: nearest any window's deciding autocorrelation comes to the threshold is
#: 5.5e-06 (docs/TfAutocorr1E60Measured.md section D), nine orders of
#: magnitude away from a last-bit question.
THRESHOLD = np.exp(-1.0)
#: Fewest log prices a window may hold: two per lag at the longest lag, so the
#: adjusted estimator still averages NLAGS products there. A smaller or
#: missing `length` falls back to the default.
MIN_LENGTH = 2 * NLAGS
#: A window of log prices whose standard deviation is at most NOISE_ULPS
#: machine epsilons does not vary: what is left is the rounding of
#: `log(c / c1)`, whose autocorrelations -- and so the lag this column reports
#: -- are the shape of that noise. NaN instead. The floor is an ABSOLUTE
#: constant because what it bounds is a dimensionless log price RATIO, which
#: has no rolling scale of its own to keep causal; 4096 eps is this fork's
#: existing habit on such a quantity (`statistics/ts_binent_20.py`,
#: `statistics/ts_strike_20.py`, `statistics/ts_c3_20.py`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. The block of log prices and the
#: demeaned copy are each `(rows, length)`, so this budget is what keeps the
#: peak off the product `len(close) * length`.
CHUNK_VALUES = 1 << 21


def _first_1e_rows(block):
    """First lag whose adjusted ACF drops below 1/e, for each row of `block`.

    `block` is a `(rows, length - 1)` slab of one-bar LOG RETURNS, oldest
    first. Each row is cumulated into the `length` log prices of its window
    (relative to the window's own first close, which the demeaning removes),
    demeaned, and searched lag by lag. Rows holding a non-finite log return,
    and rows that do not vary beyond `NOISE_FLOOR`, come back as NaN.
    """
    rows, steps = block.shape
    # Log price relative to the window's first close. Built from the window's
    # own log returns rather than read off `log(close)`, so that an exact
    # binary rescale of the price cancels in `c[1:] / c[:-1]` before any
    # transcendental runs: see this module's `__doc__`.
    x = np.empty((rows, steps + 1))
    x[:, 0] = 0.0
    np.cumsum(block, axis=1, out=x[:, 1:])

    d = x - x.mean(axis=1, keepdims=True)
    var = (d * d).mean(axis=1)              # ACF(0) with divisor `length`
    sd = np.sqrt(var)
    # `var` is 0 on an exactly flat window and NaN on one holding a bad bar;
    # both are dropped by the floor below, so this substitute never reaches a
    # shipped value. It is here so the division cannot warn.
    safe = np.where(var > 0.0, var, 1.0)

    out = np.full(rows, float(NO_CROSSING))
    done = np.zeros(rows, dtype=bool)
    for k in range(1, NLAGS + 1):
        # The ADJUSTED estimator: the lag-k products are averaged over the
        # `length - k` pairs that exist, while the divisor `var` is averaged
        # over all `length` points.
        acf = (d[:, :-k] * d[:, k:]).mean(axis=1) / safe
        hit = (acf < THRESHOLD) & ~done     # False for NaN, which is wanted
        out[hit] = k
        done |= hit
    # NaN beats the sentinel: `sd` is NaN on a window holding a bad bar.
    return np.where(sd > NOISE_FLOOR, out, np.nan)


def tf_autocorr_1e_60(close, length=None, offset=None, **kwargs):
    """Indicator: First 1/e crossing of the log price ACF (TFAUTOCORR1E)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 60
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no log price
    # to take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar log return, spelled as the log of a price RATIO: `8a / 8b`
    # is the same double as `a / b`, so a x2**k rescale cancels EXACTLY here
    # and nothing downstream can see it. Both ends are finite, positive and
    # normal by now, so the ratio can still overflow or underflow to zero --
    # 1e-300 followed by 1e50, say -- and such a pair is bad data in the same
    # way a NaN close is.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        g = np.log(c[1:] / c[:-1])
    g = np.where(np.isfinite(g), g, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length:
        # The window ending at bar T holds the `length - 1` log returns
        # g[T-length+1 .. T-1], which read closes T - length + 1 .. T: bar
        # `length - 1` is the first that fires.
        win = sliding_window_view(g, length - 1)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length - 1 + a:length - 1 + b] = _first_1e_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"TFAUTOCORR1E_{length}"
    result.category = "statistics"

    return result


tf_autocorr_1e_60.__doc__ = \
"""First 1/e crossing of the log price ACF (TFAUTOCORR1E)

How long the last `length` bars of log price stay correlated with
themselves: take the window's adjusted autocorrelation at lags 1, 2, ...
and report the FIRST lag whose value falls below 1/e. A window with no
such lag in 1 .. 20 reads 21.

    TFAUTOCORR1E = min{k in 1..20 : ACF(k) < 1/e}, else 21

The output is a small INTEGER, not a continuous statistic, and it TIES
heavily: 1,014 of 1,440 consecutive bar pairs of a 1,500-bar walk carry
the same value. Over four 1,500-bar synthetic frames (a walk, a
tick-rounded walk, an AR(1) path, a log-price cosine) it takes 15, 15, 15
and 3 distinct values and runs 2 .. 17, median 8 to 10.

**What it reads is how STRAIGHT the window is, not how volatile.** It is
bit-identical when the whole window's log returns are rescaled by x0.5,
x2 or x10 (1,441 of 1,441 fired bars each), so it is NOT a volatility
feature; the two deterministic extremes are the scale:
* an exactly geometric path -- log price a straight line -- reads **16**
  on every fired bar, at step +1%, +0.1% and -0.5%, and 16 is what the
  closed form of the adjusted ACF of a ramp gives in exact rational
  arithmetic (docs/TfAutocorr1E60Measured.md §A4);
* a path alternating up and down every bar reads a constant **1**.
Between them: a cosine in log price of period P reads 1 / 2 / 4 / 7 / 16
at P = 4 / 10 / 20 / 40 / 120, and adding drift to an iid walk lifts the
median from 8 (no drift) through 12, 14, 15 to 16 at +2% a bar. An AR(1)
in the log RETURNS moves it far less -- median 12 at phi +0.8 down to 9
at phi -0.8 -- because the window's log PRICE is an integrated series
either way.

⚠ **21 is a sentinel, and at `length` 60 nothing measured here reaches
it.** It means "no crossing in 20 lags", which is MONOTONE with the rest
of the scale (a window that would cross at lag 25 reads the same 21 as
one that never crosses), so it is not a hole in the ordering. But over
5,764 fired bars of four frames, 4,000 iid-increment windows, three exact
geometric ladders, seven deterministic cosines and a 30,000-window
directed search the largest value seen at `length` 60 is **18**, and 21
appears 0 times. Whether it is reachable at all at this length is OPEN:
the per-lag bound (the top eigenvalue of the lag-k product form on the
demeaned subspace, times `length / (length - k)`) is 1.0607 at k = 20, so
nothing rules it out, but a NO_CROSSING window needs all twenty lags at
or above 1/e at once. At longer windows it is ordinary: an exact
geometric ladder reads 21 at `length` 100 and at 250, and a walk at
`length` 100 reaches 21 too. ⚠ Do not read "21" as "20 + a bit" at the
default; read it as "never seen here".

Source: TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py` `autocorr`, which PandasTa issue
#114 quotes as "features.py autocorr: first lag with ACF < 1/e" with the
scale-free form "on log close, 60-bar window, lags 1..20 (21 = none)".
⚠ Those two lines are the WHOLE of the source text available here. TSFEL
is not a dependency of this package, dev or otherwise, it is not
installed in this worktree, `docs/pine/` does not carry it and web access
is unavailable -- its existence and licence are cited, per the issue
("Library code (TSFEL, BSD-3-Clause): existence, not evidence"), but the
library is neither vendored nor run as an oracle, so Gate A checks the
QUANTITY those lines name and NOT TSFEL's own code. Anything TSFEL does
that the issue's line does not state -- how it treats NaNs, an empty
series, a constant series, which lag count it defaults to -- is
UNVERIFIED here and nothing in this module describes it. The 60 and the
20 lags are the issue's own parameters.

What IS checked, on four frames, is that this module is bit-equal on
1,441 of 1,441 fired bars to each of four independent spellings: the
owner's screen prototype (`docs/issues/screen/ind_screen_r2.py` candidate
`tf_autocorr_1e_60`, `roll(np.log(c), 60, _acf_first_1e)` -- gitignored,
so it is both retyped and, when present, imported); a plain-Python
`math.fsum` loop over explicit slices with no numpy windowing; and
`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False)` applied to
`log(close)` window by window (statsmodels IS installed here).

⚠ **THE ONE DIFFERENCE IN THE ARITHMETIC** is where the window's log
prices come from. The prototype reads `np.log(close)`; this module
cumulates the window's OWN log returns, `log(close/close[1])`, from zero.
The two are the same series up to an additive constant, which the
demeaning removes, so this is a spelling and not a reading -- and it is
measured as one: bit-equal on 1,441 of 1,441 bars on each of the four
frames and at price levels 1e-6, 1, 1e3, 1e6 and 1e9. What it buys is
exactness: `8a / 8b` is the same double as `a / b`, so a x2**k rescale of
the price cancels BEFORE any transcendental runs and the column is
bit-identical under one by construction rather than by luck.

⚠ **It is not the only difference -- the other two are BEHAVIOURAL, on
inputs a clean frame never contains, and they are measured too** (§A6b).
The prototype's only guard is `np.where(var == 0, np.nan, out)`, and a
window holding a bad close has `var` NaN rather than 0, so `var == 0` is
False and the prototype reports the **21 sentinel** where this module
reports NaN: measured, one NaN / zero / negative / infinite close at bar
700 of a walk makes the prototype read 21 on the 60 bars this module
empties, with the two bit-equal on all 1,381 bars either side (a
SUBNORMAL close reads 1 rather than 21 there, because `log(1e-310)` is a
large finite number and the lag-1 autocorrelation collapses). The third
difference is the noise floor, which the prototype does not have: on a
price flat at 1e6 stepping one double ulp a bar this module fires no bar
and the prototype fires all 1,441, reading 17 to 21. So "the port and the
screened quantity are the same column" holds on every window whose closes
are finite, normal and positive, and not beyond that.

Three readings the issue's line leaves open, decided and priced in
docs/TfAutocorr1E60Measured.md rather than assumed:
* **ADJUSTED, not biased.** The lag-k products are averaged over the
  `length - k` pairs that exist (the prototype's `.mean(1)`, and
  statsmodels' `adjusted=True`), while the divisor is the variance over
  all `length` points. The biased reading -- divide by `length` -- is a
  genuinely different column, not a rescaling: bit-equal on 424 to 589 of
  1,441 bars on the three stochastic frames and on 720 of 1,441 on the
  cosine, up to 9 lags apart, with Spearman 0.977 to 0.982 and 0.694
  respectively.
* **Strict `<`.** The `<=` reading is bit-equal on 1,441 of 1,441 bars of
  all four frames, with 0 exact ties with 1/e in 5,764 windows; it is
  kept strict because that is what the issue's line and the prototype
  say, and the difference is unreachable rather than cosmetic.
* **The ACF of LOG PRICE, not of returns.** The issue fixes this and it
  matters more than anything else here: on a walk and on a tick-rounded
  walk the same construction applied to log RETURNS is the CONSTANT 1 --
  returns are near-uncorrelated, so lag 1 is already below 1/e on every
  one of 1,440 windows -- which would fail Gate D's "not constant" on the
  spot. Log price is an integrated series, which is why its ACF decays
  slowly enough to carry information.

The noise floor is `sd(log price in window) > 9.09e-13` (4096 eps). On
everything with a real price shape it is INERT -- 0 of 1,441 windows
reach it on each of the four frames, 0 of 1,441 on a monotone
one-tick-per-bar path even at price 1e9 with a 0.01 tick (where the log
step is 1e-11), and guarded and unguarded agree on every bar of all of
those. What it buys is the ULP band, where the unguarded failure is
ordinary-looking rather than absurd: a price flat at 1e6 that steps up by
one double ulp every bar is mathematically an exact geometric ladder and
reads 16 unguarded -- the strongest-trend value on the scale,
indistinguishable from a real trend -- and a price flat except for a
SINGLE 1-ulp step reads 1 to 15 unguarded, every one of those inside the
live range of a walk. Both are NaN here. The cost is stated rather than
hidden: those same ulp paths have a defined mathematical answer and this
column refuses it. The floor is an ABSOLUTE constant because what it
bounds is a dimensionless log price ratio, which has no rolling scale of
its own to keep causal.

Causal: bar T reads closes T - length + 1 .. T. Measured by
future-perturbation sweep -- 0 of 35 offsets leak on a walk, a
tick-rounded walk and an AR(1) path, and 0 of 35 at `length` 40, 100 and
250 -- and by six mutants read off this file, edited and exec'd in
memory. Scale-free: bit-identical under x8, x64, 2**-40 and 2**40 on each
of the four frames and at each of `length` 40, 45, 100 and 250 -- sixteen
cells each way, all of them run -- by construction (see the arithmetic
difference above); x10, x3.7, x0.1 and x1.0000001 come out
bit-identical too, which the arithmetic does not promise for an integer
decided by a float comparison -- what makes it hold is measured, the
smallest margin any window has to 1/e at its deciding lag being 2.1e-05
on the walk, 1.4e-05 tick-rounded, 5.5e-06 on the AR(1) path and 6.5e-03
on the cosine, with 0 exact ties in 5,764 windows.
NaN on the first `length - 1` bars; on every window holding a close that
is NaN, infinite, zero, negative or subnormal (60 bars at the default);
on a window holding a close PAIR whose ratio overflows (59 bars); and on
a window that does not clear the floor, which `length` identical closes
reach.

Cost: the module walks the windows in chunks, so the peak is set by
`CHUNK_VALUES` and not by `len(close) * length`: at n = 400,000 the
traced peak is 61.2 MB (tracemalloc) and the run takes about 1.3 s.
Wall clock is not quoted as a band because it does not reproduce.

Calculation:
    Default Inputs:
        length=60, NLAGS=20
    g[t]  = log(close[t] / close[t-1])
    X     = 0, g[T-length+2], g[T-length+2] + g[T-length+3], ...
            (the window's `length` log prices, from its own first close)
    d     = X - mean(X)
    v     = mean(d * d)
    ACF(k) = (sum over the length - k pairs of d[i] * d[i+k])
             / (length - k) / v
    TFAUTOCORR1E = the smallest k in 1 .. NLAGS with ACF(k) < 1/e,
                   else NLAGS + 1; NaN when sqrt(v) <= 9.09e-13

Args:
    close (pd.Series): Series of 'close's
    length (int): Log prices per window. At least 40 -- two points per
        lag at the longest lag, so the adjusted estimator still averages
        20 products there -- and a smaller or missing value falls back to
        the default. ⚠ NLAGS does NOT scale with it: 20 is the issue's
        own parameter, so a longer window searches the same 20 lags and
        reaches the 21 sentinel much more often (0 of 1,441 bars of a
        walk at `length` 60, and the maximum at `length` 100 and 250 is
        21). Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFAUTOCORR1E_{length}, a whole number in [1, 21]
"""
