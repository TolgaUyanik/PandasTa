# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Lags the automutual information is evaluated at, 1 .. TAU_MAX. The 40 is
#: the catch22 operation's OWN parameter -- it is the number in the name
#: `IN_AutoMutualInfoStats_40_gaussian_fmmi` -- so it is a module constant and
#: not a function of `length`.
TAU_MAX = 40
#: What a window with no interior local minimum reads. The scan can only test
#: lags 2 .. TAU_MAX - 1 (a local minimum needs a neighbour on both sides), so
#: TAU_MAX is the fallback, exactly as the hctsa operation's own fallback is
#: its `tau`. It is a SENTINEL: read it as "no dip in 40 lags", not as "40".
NO_MINIMUM = TAU_MAX
#: Fewest returns a window may hold: two per lag at the longest lag, so the
#: lag-40 correlation is still taken over 40 pairs. It also puts TAU_MAX at or
#: below `ceil(length / 2)`, the cap hctsa's own operation applies, so that cap
#: can never bind here. A smaller or missing `length` falls back to the default.
MIN_LENGTH = 2 * TAU_MAX
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: what is left is the rounding of `c / c1 - 1`, whose
#: autocorrelations -- and so the lag this column reports -- are the shape of
#: that noise. NaN instead. The floor is an ABSOLUTE constant because what it
#: bounds is a dimensionless RETURN, which has no rolling scale of its own to
#: keep causal; 4096 eps is this fork's existing habit on such a quantity
#: (`statistics/tf_autocorr_1e_60.py`, `statistics/ts_binent_20.py`,
#: `statistics/ts_strike_20.py`, `statistics/ts_c3_20.py`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each lag allocates two
#: `(rows, length - lag)` demeaned limbs, so this budget is what keeps the peak
#: off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def _fmmi_rows(block):
    """First minimum of the Gaussian AMI, for each row of `block`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. For each lag 1 .. TAU_MAX the row is split into the two
    overlapping limbs `x[:-tau]` and `x[tau:]`, their PEARSON correlation is
    taken, and that becomes the Gaussian automutual information
    `-0.5 * ln(1 - rho**2)`. The lags are then scanned for the first one that
    is strictly below both of its neighbours.

    Comes back as NaN for a row holding a non-finite return, a row that does
    not vary beyond `NOISE_FLOOR`, and a row in which either limb of some lag
    is CONSTANT -- the correlation, and so the AMI, is undefined there.
    """
    rows, n = block.shape
    # Kept for the floor: the window's own standard deviation.
    d = block - block.mean(axis=1, keepdims=True)
    ss = (d * d).sum(axis=1)
    sd = np.sqrt(ss / n)

    ami = np.empty((rows, TAU_MAX))
    # A row whose correlation is undefined at ANY lag has no first minimum.
    # `~isfinite` also carries the rows holding a bad return.
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(1, TAU_MAX + 1):
            # Each limb is demeaned by its OWN mean and scaled by its OWN sum
            # of squares: `corr(x(1:end-tau), x(1+tau:end))`, which is what
            # the hctsa operation this ports means by the Gaussian estimator.
            # It is NOT the window's autocorrelation function, which demeans
            # once and divides by one variance -- see this module's __doc__
            # for what that difference is worth.
            a = block[:, :n - k]
            b = block[:, k:]
            da = a - a.mean(axis=1, keepdims=True)
            db = b - b.mean(axis=1, keepdims=True)
            den = np.sqrt((da * da).sum(axis=1) * (db * db).sum(axis=1))
            # True for 0.0, for NaN, and for the +inf a window of enormous
            # (but finite) returns produces -- the PRODUCT of the two sums of
            # squares overflows at a return of order 1e77, which a legal
            # close pair can reach (1e-50 followed by 1e27). Without the
            # `isfinite` limb such a row would read the SENTINEL rather than
            # NaN: `rho` comes out 0, every AMI is 0, no lag is below both
            # neighbours, and `sd` is inf, which clears the floor.
            bad |= ~(den > 0.0) | ~np.isfinite(den)
            rho = (da * db).sum(axis=1) / np.where(den > 0.0, den, 1.0)
            # `np.minimum(.., 1.0)` is LOAD-BEARING, not decoration.
            # Cauchy-Schwarz bounds `rho**2` by 1 in exact arithmetic, and a
            # rounding overshoot is real: on a frame whose returns are an
            # exact 20-bar cosine, 218 of 8,000 (window, lag) cells come out
            # above 1 (worst 1 + 9e-16) and 2,319 of 8,000 do on an
            # alternating frame. The clip turns those into +inf -- a maximum,
            # which the scan ignores -- where `log1p` of a number below -1
            # would hand the scan a NaN instead.
            ami[:, k - 1] = -0.5 * np.log1p(-np.minimum(rho * rho, 1.0))

    out = np.full(rows, float(NO_MINIMUM))
    done = np.zeros(rows, dtype=bool)
    # Column `i` of `ami` is lag `i + 1`, so this tests lags 2 .. TAU_MAX - 1
    # in order and keeps the FIRST hit. NaN comparisons are False, which is
    # wanted: such a row falls through to the sentinel and is then emptied by
    # the `bad` mask below.
    for i in range(1, TAU_MAX - 1):
        hit = (ami[:, i] < ami[:, i - 1]) & (ami[:, i] < ami[:, i + 1]) & ~done
        out[hit] = i + 1
        done |= hit

    return np.where(~bad & (sd > NOISE_FLOOR), out, np.nan)


def c22_ami_timescale(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 first minimum of the Gaussian automutual information (C22AMITIMESCALE)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one: `8a / 8b`
    # is the same double as `a / b`, so a x2**k rescale of the price cancels
    # EXACTLY here and nothing downstream can see it. Both ends are finite,
    # positive and normal by now, so the ratio can still overflow or underflow
    # to zero -- 1e-300 followed by 1e50, say -- and such a pair is bad data in
    # the same way a NaN close is.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _fmmi_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22AMITIMESCALE_{length}"
    result.category = "statistics"

    return result


c22_ami_timescale.__doc__ = \
"""catch22 first minimum of the Gaussian automutual information (C22AMITIMESCALE)

How soon the last `length` daily returns stop looking like their own
lagged copy: for each lag 1 .. 40, correlate the window with itself
shifted by that lag, turn the correlation into the mutual information a
bivariate Gaussian with that correlation would carry,
`AMI(tau) = -0.5 * ln(1 - rho(tau)**2)`, and report the FIRST lag whose
AMI is strictly below both of its neighbours. A window with no such lag
reads 40.

    C22AMITIMESCALE = min{tau in 2..39 : AMI(tau) < AMI(tau-1)
                                     and AMI(tau) < AMI(tau+1)}, else 40

The output is a small INTEGER in [2, 40] and it TIES heavily: 77.6% to
100% of neighbouring bar pairs carry the same value on the six frames
below. Over four stochastic 1,500-bar frames (an iid walk, a second walk
rounded to the kurus, a 2-lira stock on a 1-kurus tick, a Student-t(3)
path) it takes 6 to 7 distinct values, runs 2 .. 8 and has median 3; on
an AR(1)-in-returns path, 10 values, 2 .. 11, median 5. **A lag 1 is not
in the range** -- a minimum needs a neighbour on each side, so the scan
starts at 2 -- and **40 is a SENTINEL**, "no dip in 40 lags", reached by
0 of the 8,400 fired bars of all six frames.

**What it reads is the SHAPE of the return autocorrelation, not its
size.** Rescaling the whole window's returns by x0.5, x2 or x10 moves 0
of 1,400 fired bars (a correlation cannot see a rescale of both limbs),
while the same returns in a different ORDER move 1,049. The
deterministic scale is a cosine: returns that are an exact cosine of
period P read exactly `P / 4` on every fired bar at P = 8, 12, 20, 40
and 80. The law needs the window to hold a full period -- at P = 120
against 100 returns it breaks (17 distinct values, 21 .. 40) -- and it
is what the small median on a real-looking frame means: a near-iid
return window has no cycle, so the first dip of `rho**2` lands wherever
the sampling noise of the autocorrelation puts it, which is lag 2 on 21%
to 45% of bars.

**THE ESTIMATOR IS A CHOICE, AND IT IS THE LAGGED PAIR'S OWN PEARSON
CORRELATION.** The definitions name a correlation without pinning its
sample form, and three readings are defensible: `corr(x[:-tau],
x[tau:])` with each limb demeaned by its OWN mean (what hctsa's
`CO_AutoMutualInfo(..., 'gaussian')` spells, and what this module
ships); the window's BIASED autocorrelation, one mean and one variance,
divisor `n`; and the ADJUSTED one, divisor `n - k`. They are close but
NOT the same column -- against this one, over the 1,400 bars of each of
the five non-deterministic frames, the biased reading is equal on 1,349
to 1,390 (Spearman +0.974 to +0.993) and the adjusted on 1,355 to 1,391
(+0.980 to +0.995); on the cosine frame all three coincide, 1,400 of
1,400, because a clean cycle moves every estimator the same way. Which
is to say: a
later "simplification" to an ACF-based spelling would change shipped
values on up to 51 bars in 1,400, and `tests/test_c22_ami_timescale.py`
fails if it does.

⚠ **The scan is strict (`<`), and the strictness is unreachable rather
than cosmetic**: 0 exact ties between neighbouring lags' AMI in the
windows sampled (`<=` picks the same lag on every one of them).

⚠ **One degenerate corner, disclosed.** Returns that alternate exactly
+2% / -2% make the two limbs of every lag the same sequence up to a
sign, so `rho**2` is 1 to within 7e-16 at all 40 lags, the AMI is the
same enormous number everywhere, and WHICH lag is reported is decided by
the last bits: 31 distinct values over 1,400 bars, and a x10 rescale of
that frame moves 1,197 of them. Nothing with a real return shape is
near it -- the largest `rho**2` the sampled windows of the walk, AR(1)
and Student-t frames produce is 0.53 -- but a synthetic test frame can be,
and a reader comparing this column across two rescales of such a frame
should expect noise, not stability.

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature
`IN_AutoMutualInfoStats_40_gaussian_fmmi` -- the hctsa operation
`IN_AutoMutualInfoStats(y, 40, 'gaussian')`, field `fmmi`, applied by
PandasTa issue #125 to the last 100 daily simple returns. The reference
implementation (pycatch22 1.x) is **GPL-3.0** and this fork is MIT: this
module was written from the DEFINITIONS, no shipped module imports the
reference (a test asserts that over the whole package), and the one
place it is run at all is `docs/measure_c22_ami_timescale.py` section P
-- opt-in, measurement only, the same use the owner's own screen
prototype makes of it -- to answer whether this port is the column the
2026-10-24 screen measured. It is, on every window both columns score:
1,200 of 1,200 sampled windows of six frames read the same value,
through both of that library's entry points, with 0 disagreements. ⚠ Not
on the windows this module BLANKS -- the reference scores a degenerate
window where this one refuses, measured at 80 of 80 blank windows on a
frame with a flat run and 467 of 467 on a geometric ladder -- so this
column's non-NaN count on real data is LOWER than the prototype's.

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return prediction, and
nothing here tests it on BIST: its presence in this fork is existence,
not evidence.

Gate A also checks the quantity three further ways that share no code
with this module: an exact `fractions.Fraction` oracle that rounds ZERO
times (the AMI is strictly increasing in `rho**2`, which is a ratio of
integers over exactly representable doubles, so the first minimum is
decided by exact rational comparisons -- 0 disagreements on 648
windows), a plain-Python `math.fsum` spelling with `log(1 - r*r)` in
place of `log1p(-r2)` (0 disagreements on 1,200), and the correlation
taken by `np.corrcoef` and by `pandas.Series.corr` (0 disagreements on
1,200 each, max |rho**2 - library| 2.1e-15).

Two blanking rules, both measured rather than asserted:
* **the noise floor**, `sd(returns in window) > 9.09e-13` (4096 eps).
  INERT on anything price-shaped -- 0 bars differ from the unguarded
  spelling on each of the six frames. What it buys: a price flat at 1e6
  except for ONE 1-ulp step reads the SENTINEL 40 unguarded, the top of
  the scale and indistinguishable from a real "no dip", and a 1-kurus
  step at a price of 1e6 (a 1e-11 return) fires on all 1,400 bars
  unguarded. Both are NaN here; the same 1-kurus step at a price of 100
  is a real 1e-4 return and fires.
* **a CONSTANT limb**, which has no correlation to take. This empties
  more than a reader expects, and earlier: the lag-40 limb of bar T is
  the returns of bars T-59 .. T, so a price that goes flat at bar 400
  blanks bar 460 onward -- 40 bars before the whole window is flat.
⚠ An exactly geometric path never fires either, and it is the FLOOR that
empties it rather than the limb rule: `start * (1 + step)**k` rounds
every power on its own, so the window holds 3 to 5 distinct returns with
a standard deviation of about 1e-16. Unguarded it fires all 1,400 bars
of a 1,500-bar frame and reads inside [2, 14] with a median of 2 to 3 --
values a reader could not tell from a real frame's, off 1e-16 of
rounding.

Causal: bar T reads closes T - length .. T. Measured by
future-perturbation sweep -- 0 of 35 offsets leak on each of six frames
with eight splices apiece, and 0 of 35 at `length` 80, 120 and 250 --
and by seven mutants read off this file, edited and exec'd in memory
(four look-ahead, one that back-dates the bad-data mask, and two that
replace a per-row mean with the chunk's, which are near-DEAD for a
measured reason -- a return window's mean is 0.05 of its own standard
deviation).
⚠ The sweep's POWER is limited by the ties: a one-bar look-ahead mutant
is caught at 22 of 35 offsets (walk), 16 of 35 (tick-rounded) and 0 of
35 on a frame where the column is constant, while a ten-bar one is
caught 35 of 35 everywhere.
Scale-free: bit-identical under x8, x64, 2**-40 and 2**40 on all six
frames, at `length` 80 / 120 / 250 and at price levels 1e-6, 1e+6 and
1e+100, BY CONSTRUCTION -- the price enters only as `c[t] / c[t-1]`, and
`8a / 8b` is the double `a / b`. x10, x3.7, x0.1 and x1.0000001 come out
bit-identical too, which the arithmetic does not promise for an integer
decided by float comparisons; what makes it hold is measured, the
smallest gap in `rho**2` between the deciding lag and the neighbour it
beats being 3.6e-09 (penny frame) and 7.3e-08 (walk).
NaN on the first `length` bars; on every window holding a close that is
NaN, infinite, zero, negative or subnormal (101 bars at the default);
on a window holding a close PAIR whose ratio overflows (100 bars); on a
window whose sums of squared deviations OVERFLOW although the returns
themselves are finite, which a close pair of ratio 1e200 reaches and
one of ratio 1e77 does not (100 bars; without that guard those bars
would read the SENTINEL instead, measured); and under the two rules
above.

Cost: the windows are walked in chunks, so the peak is set by
`CHUNK_VALUES` and not by `len(close) * length`: at n = 400,000 the
traced peak is 28.2 MB (tracemalloc) and the run takes about 12 s -- 40
lags each needing two demeaned limbs, which is where the time goes. Wall
clock is not quoted as a band because it does not reproduce.

Calculation:
    Default Inputs:
        length=100, TAU_MAX=40
    r[t]   = close[t] / close[t-1] - 1
    X      = r[T-length+1 .. T]                 (the window)
    for tau in 1 .. 40:
        A  = X[:-tau] - mean(X[:-tau])
        B  = X[tau:]  - mean(X[tau:])
        rho(tau)  = sum(A*B) / sqrt(sum(A*A) * sum(B*B))
        AMI(tau)  = -0.5 * log(1 - min(rho(tau)**2, 1))
    C22AMITIMESCALE = the smallest tau in 2 .. 39 with AMI(tau) below
                      both neighbours, else 40; NaN when the window's
                      return sd is at most 9.09e-13 or any limb is
                      constant

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        80 -- two returns per lag at the longest lag -- and a smaller or
        missing value falls back to the default. ⚠ TAU_MAX does NOT
        scale with it: 40 is the catch22 operation's own parameter, so a
        longer window searches the same 40 lags. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22AMITIMESCALE_{length}, a whole number in [2, 40]
"""
