# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# The bias correction divides by `(length - 2) * (length - 3)`, so a window of
# four returns is the smallest one the sample estimator is defined on at all.
MIN_LENGTH = 4
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# A window whose returns vary only at rounding level has no dispersion to
# standardise by: `m4 / m2**2` would be the ratio of two roundings, which is
# an ordinary-looking number rather than an obviously broken one. The floor
# can be an absolute constant -- no rolling scale, so no second window to keep
# causal -- because what is floored is the range of DIMENSIONLESS price
# ratios. The same 4096 eps is this fork's existing habit on a dimensionless
# quantity: `statistics/ts_binent_20.py` floors a return range with it, and
# `statistics/ts_c3_20.py` and `statistics/lean_hurst_100.py` float it against
# a standard deviation and a log price ratio.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def ts_kurt_60(close, length=None, offset=None, **kwargs):
    """Indicator: excess kurtosis of returns (TS_KURT)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 60
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    px = Series(c, index=close.index)

    # The simple return, spelled as a price RATIO minus one: `8a / 8b` is the
    # same double as `a / b`, so a x2^k rescale cancels exactly rather than to
    # rounding.
    #
    # Both ends are finite, positive and normal by now, so OVERFLOW is the one
    # float error the ratio can still raise -- 1e-300 followed by 1e50 gives
    # an infinite return. Such a pair is bad data in the same way a NaN close
    # is (there is no return to take), so it is silenced here and dropped on
    # the next line rather than carried into the moments.
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    # A return whose fourth power cannot be SUMMED `length` times without
    # overflowing is not usable data, and keeping it is not a local mistake:
    # `rolling.kurt` accumulates the raw power sums ONLINE, so an infinite sum
    # of fourth powers never leaves the accumulator and every LATER bar comes
    # back NaN. Measured on a 400-bar walk: closes 1e-200 then 1e-100 at bars
    # 200/201 (returns of 1.0e+100 and 1.0e+102) empty bars 201..399 without
    # this line and bars 201..261 with it. Two such pairs 30 bars apart, whose
    # fourth powers are 1.0e+308 each -- finite -- and sum past the float
    # maximum, are the case a plain `isfinite(fourth)` misses: measured, it
    # empties 199 bars there against this guard's 91
    # (docs/TsKurt60Measured.md, Guards).
    #
    # The bound is what makes the locality structural rather than measured on
    # one shape: every kept return has `r**4 < max/(2*length)`, so a window of
    # `length` of them sums to less than half the float maximum -- the factor
    # two is headroom for the accumulation's own rounding and for pandas
    # summing `val*val*val*val` (three roundings) where this tests one. The
    # same per-term ceiling leaves pandas' other accumulators far from
    # trouble: it caps |r| at 3.50e+76, so `sum(r)` cannot pass 2.1e+78,
    # `sum(r**2)` 7.4e+154 and `sum(|r|**3)` 2.6e+231, all 75+ orders of
    # magnitude inside the float range. A comparison against NaN or inf is
    # False, so this one test also rejects a non-finite fourth power.
    # Spelled as two squarings rather than `** 4`: the same quantity to within
    # a rounding the factor two above absorbs (bit-equal columns on 1,940 of
    # 1,940 bars, measured), and it is the multiply chain pandas itself
    # accumulates, but it costs two vectorised multiplies instead of `n` libm
    # `pow` calls -- which is most of this guard's price rather than a
    # rounding detail (see Cost).
    with np.errstate(over="ignore"):
        fourth = np.square(np.square(r.to_numpy()))
    r = r.where(fourth < np.finfo(float).max / (2 * length))

    rolling = r.rolling(length, min_periods=length)
    # pandas' own `rolling.kurt` IS the statistic the source names: tsfresh's
    # `kurtosis` is `pandas.Series.kurtosis`, the bias-corrected G2, and the
    # screen prototype is `ret(c).rolling(60).kurt()`. It is kept rather than
    # re-derived in numpy so the port and the screened prototype are the same
    # arithmetic to the last bit where both fire -- what this module adds is
    # the NaN discipline below, not a second spelling of the moments. An
    # independent two-pass numpy form, a plain-Python scalar loop and an EXACT
    # rational oracle all agree with it (docs/TsKurt60Measured.md, Gate A).
    kurt = rolling.kurt()

    # A window needs two returns that differ by more than rounding before the
    # fourth standardised moment means anything. pandas has an absolute
    # degenerate test of its own (inherited, see the docstring), but on a
    # window of IDENTICAL returns `rolling.kurt` returns exactly -3.0 --
    # measured on 240 of 300 bars of a flat frame and on 10 bars of a 70-bar
    # flat run planted in a walk. -3.0 is below this statistic's own algebraic
    # floor of -2(n-1)/(n-3), so it is not a value the corrected form can
    # otherwise take (docs/TsKurt60Measured.md, Gate A2).
    spread = rolling.max() - rolling.min()
    tskurt = kurt.where(spread > NOISE_FLOOR)
    # A labelled BACKSTOP: with the sum bound above in place, no input swept
    # for docs/TsKurt60Measured.md leaves a non-finite value here. The column
    # emits 0 on every row whose count that file prints -- fifteen rows over
    # fourteen distinct frames (five bad closes, two overflowing pairs, seven
    # magnitudes of a planted giant return, the two-spike frame; the
    # 1e-200/1e-100 pair and the 1e100 magnitude are the same frame). It is
    # kept because it costs one pass and `rolling.kurt` is a compiled
    # extension whose other accumulators this module does not bound -- not
    # because a witness exists. A term-only guard DOES leave one: 1 bar,
    # measured (docs/TsKurt60Measured.md, Guards).
    tskurt = tskurt.where(np.isfinite(tskurt))

    # Offset
    if offset != 0:
        tskurt = tskurt.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        tskurt.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    tskurt.name = f"TS_KURT_{length}"
    tskurt.category = "statistics"

    return tskurt


ts_kurt_60.__doc__ = \
"""Excess kurtosis of returns (TS_KURT)

How much of the recent squared dispersion sits in the window's few largest
moves: the sample (bias-corrected) standardised fourth moment of the trailing
`length` simple returns, minus the 3 a gaussian would score.

    m2, m4   = the window's 2nd and 4th CENTRED moments (divided by n)
    g2       = m4 / m2**2 - 3
    TS_KURT  = ((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3))

⚠ **It is close to a single-outlier reading, and it is NOT volatility.**
Measured on a 1,500-bar gaussian walk: Spearman 0.8698 against
`max|r - mean| / sd` of the same window, 0.7753 against the SECOND largest
deviation, and 0.0505 against the window's own standard deviation. A single
planted +10-sigma return takes the 60 windows holding it to a median of
22.1696 against the frame's -0.1283, and a +50-sigma one to 57.1866 -- 95% of
the hard ceiling below. It is scale-free in the returns themselves, so
doubling every return leaves it unchanged (Spearman 1.000000 and max
|difference| 5.4e-14 under a x2 rescale of the returns, 8.5e-14 under x0.5).
Read it as "is one move dominating", not as "are these returns wild".

⚠ **It is BOUNDED, and the bound is reachable.** The biased ratio is bounded
by `m4 / m2**2 <= n - 2 + 1/(n-1)` -- 58.016949 at n = 60 -- attained by a
one-hot window, and the sample correction maps exactly that bound to `n`. So
at `length` 60 the column cannot exceed **60.0**, and it cannot fall below
**-2.0702**, which is `-2*(n-1)/(n-3)` and is attained by any window
alternating two values in equal counts. Both are measured (a one-hot window
reads 59.999999999999986, 1.4e-14 under the ceiling; a +-0.5 zigzag reads the
floor bit-exactly on 1,195 of 1,440 bars), and the column itself stays inside
them on heavy-tailed frames at each of six lengths. A
1,500-bar gaussian walk spans [-1.2434, 2.8643], 4.8% of the ceiling, while a
student-t(2) path reaches 56.2111: a saturated value means one bar, not a
wild month.

⚠ **It needs 61 closes and it is a slow state.** Two consecutive windows
share 59 of their 60 returns, so the column autocorrelates at 0.9861 at lag 1
and 0.3371 at lag 60 (measured on a walk). One extreme bar moves exactly
`length` = 60 bars and then leaves (measured: bars 700..759 move by more than
1e-9 for a spike planted at bar 700). It is not an event flag.

Source: tsfresh feature_calculators (MIT), `kurtosis`, as the formula is
stated by PandasTa issue #93: `kurtosis on 60 returns`, in the form of the
screen prototype `docs/issues/screen/ind_screen.py` candidate `ts_kurt_60`
(local to the owner's machine), `ret(c).rolling(60).kurt()`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable, so
the formula under test is the issue's line plus the published definition of
`feature_calculators.kurtosis` (`pandas.Series.kurtosis`, the bias-corrected
G2, Fisher's excess), not a read of tsfresh's own code; anything tsfresh does
that the line does not say (how it treats a series shorter than four samples,
whether it drops NaNs rather than returning NaN) is unverified here. The 60
is the issue's own parameter.

`pandas.rolling.kurt` is kept as the arithmetic rather than re-derived in
numpy, so this port and the screened prototype are the SAME column where both
fire: bit-equal on 1,440 of 1,440 bars on each of a walk, a tick-rounded walk
and a student-t path, both against the prototype retyped and against the
owner's own registry entry imported from `docs/issues/screen/ind_screen.py`
(six comparisons, all six run). That does not transfer issue #93's Gate
E figures (0.2501 vs `ZIGZAG`, n = 33,246), which were taken by a different
harness run on a prototype; the launcher's Gate E run on this module is the
number that decides ship or revert. What the module adds is the NaN
discipline, and it is the one place the two part company (see below).

The arithmetic is checked independently rather than trusted, starting with
the function the source attribution actually names: `pandas.Series.kurtosis`
(`nanops.nankurt`, a TWO-PASS implementation, not the online one
`rolling.kurt` uses) applied window by window agrees with this column to
5.3e-15 on a walk, 4.0e-15 tick-rounded and 8.5e-14 on a student-t path. Then
a numpy two-pass form over the centred moments (5.3e-15 / 4.3e-15 /
9.9e-14), a `ddof=1` spelling of the textbook G2 (6.0e-15), a plain-Python
`math.fsum` loop (2.8e-15 over 340 bars), and an EXACT rational oracle --
every close is a rational, so the whole statistic is.

Against that oracle, five spellings agree with the true value of their own
inputs to within a factor of 1.5 of each other: on a walk `rolling.kurt` is
6.994e-15 out, `Series.kurtosis` 6.717e-15, the `ddof=1` form 6.717e-15, the
numpy two-pass 7.216e-15 and the `fsum` loop 6.509e-15. The `fsum` loop is
the closest on all three frames and `rolling.kurt` is within 1.31x of it
(6.994/6.509 on the walk, 8.341/7.820 tick-rounded, 6.040/4.619 on the
student-t path, where this spelling is the worst of the five). So the
cancellation that makes an online raw-moment form suspect on PRICE levels
does not materialise on returns at these lengths -- the simpler spelling is
not materially the less accurate one here, which is a measurement on returns
and not a guarantee (docs/TsKurt60Measured.md, Gate A4).

Four readings the wording leaves open, decided and priced in
docs/TsKurt60Measured.md (Gate A5) rather than assumed:
* The returns are SIMPLE (`close/close.shift(1) - 1`), the prototype's `ret`.
  Log returns are a different column, though not by much: Spearman 0.998596
  on a walk, max |difference| 0.2526, and the 10 bars of largest
  disagreement all sit above 1.8 -- it disagrees most exactly where the
  column is interesting.
* The sample (bias-corrected) G2, which is `pandas.Series.kurtosis` and so
  tsfresh's. For a fixed `length` the biased g2 is an exact affine
  rescaling -- `((n+1)*g2 + 6)*(n-1)/((n-2)*(n-3))` rebuilds this column to
  5.3e-15, Spearman 1.000000 -- so a rank miner cannot see the choice, but a
  rule with a threshold can: the two differ by up to 0.3315 on the same walk.
* EXCESS kurtosis, the `- 3` the issue asks for by name. The raw (Pearson)
  form is this column plus exactly 3, so Spearman 1.000000 again.
* `length` is 60 RETURNS, so 61 closes, and the first value lands at bar 60.
  Rejected: 60 CLOSES, i.e. 59 returns, which is a near-copy rather than a
  different question (Spearman 0.992198, max |difference| 1.0212) -- it is
  the off-by-one a reader makes, priced so it is not re-argued.

It is NOT the fork's existing `kurtosis`, which takes the same moment of the
CLOSE: measured on the same walk, Spearman -0.0847 against
`kurtosis(close, 60)` and -0.1090 against its default `KURT_30`. Kurtosis of
a price LEVEL reads the shape of a trend, not of a return distribution.

A window with no dispersion to standardise is NaN, not a number -- and the
three spellings of the source disagree about that, which is why the module
decides it rather than inheriting it. On a flat 300-close frame:
`rolling.kurt` (so the prototype) reports on 240 bars, all exactly **-3.0**,
which is BELOW this statistic's own floor of -2.0702 and so is not a value
the corrected form can take; `pandas.Series.kurtosis`, the literal tsfresh
spelling, reports on the same 240 bars and reads exactly **0.0**, the value a
gaussian would score; this column reports on **none** of them. The same split
shows on 10 bars of a 70-bar flat run planted in a walk. The floor is
`max(r) - min(r) > 9.09e-13` rather than `== 0` so that a path whose returns
vary only at rounding level is emptied too; on this column pandas' own guard
already covers most of those (a 1%-a-bar geometric ladder fires 0 of 300 bars
either way), and the one measured case where the floor is what empties the
window is a monotone fine-tick path at a high price (price 1e6, tick 0.001,
return range 2.2e-16: 0 of 300 bars here against the prototype's 47).

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 36 offsets in each of the six
configurations run (three frames at the default, plus `length` 20, 120 and 4
on the walk).
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale of price
(1,440 of 1,440 fired bars on each of a walk, a tick-rounded walk and a
student-t path; also at `length` 20 (1,480), 120 (1,380), 250 (1,250) and 4
(1,496)). x10 and x3.7 are NOT bit-identical -- they perturb the returns in
their last bits and a fourth moment amplifies that -- but the NaN masks match
exactly and the values agree to 1.2e-13 at Spearman 1.000000, which is the
Gate D tolerance reading.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close empties the
`length + 1` = 61 windows it sits in, because it spoils two returns);
on any window holding a close pair whose ratio OVERFLOWS, or whose return's
FOURTH POWER overflows (one spoiled return, so 60-61 windows); on any window
whose `length` returns span 9.09e-13 or less; and on any window pandas' own
degenerate test rejects. That last one is ABSOLUTE in the size of the returns
rather than relative, so it also empties a genuinely fine low-volatility
path: a 1e-7-sigma return path fires on 47 of 300 bars here, a 1e-8-sigma one
on none, and the SAME 1e-7 path with its returns x100 on 240. The threshold
itself is not quoted here -- `rolling.kurt` ships as a compiled extension in
this environment, so the boundary above is measured, not read.

⚠ The fourth-power guard is what keeps that list WINDOW-LOCAL. `rolling.kurt`
accumulates the raw power sums online, so an infinite sum of fourth powers
never leaves the accumulator. Measured on a 400-bar walk: with closes 1e-200
then 1e-100 at bars 200/201, the module WITHOUT that guard empties 199 bars
(201..399, the whole remainder of the frame) and with it 61 (201..261). Seven
magnitudes from 1.0e+102 to 1.0e+132 were swept: the damage runs to the end of
the frame in all seven without the guard, and with it is 60 bars when one
return is spoiled and 61 when the pair spoils two. The guard bounds the
window SUM (`r**4 < max/(2*length)`) and not just the single term, because
two returns of 1.0e+77 thirty bars apart have individually finite fourth
powers that sum past the float maximum: with a term-only `isfinite` test that
frame empties 199 bars, with the sum bound 91 -- the union of two 61-bar
spans. The ceiling it enforces on a return is 3.499e+76, so nothing a market
can produce reaches it, and on every ordinary frame measured it changes
nothing (docs/TsKurt60Measured.md, Guards).

Cost: `rolling.kurt` is a single O(n) pass, the two extrema and the
fourth-power guard are three more, so nothing here grows with `length` --
measured 43 ms at the default and 36-38 ms at each of `length` 20, 60 and 250,
with a traced peak of 25.6 MB in all four. The guard costs 3.2 MB -- the
fourth-power array -- and about 2 ms of a 34 ms call (best of nine,
alternating with the same call having that block rewritten out in memory:
36 ms against 34 ms, 25.6 MB against 22.4 MB). Spelling it `r ** 4` instead
of two squarings takes the whole call to 55 ms, about ten times the guard's
own cost, for a column that is bit-equal on 1,940 of 1,940 bars -- which is
why it is two squarings. ⚠ These absolutes move: the same three measurements
read 38 / 34 / 84 ms earlier in the same session, so it is the ORDERING and
the gaps that reproduce, not the numbers (docs/TsKurt60Measured.md, Cost).
The numpy two-pass oracle this was checked against peaks at 144 / 400 /
1,615 MB on the same input, which is why it lives in
docs/measure_ts_kurt_60.py and not here.

Calculation:
    Default Inputs:
        length=60
    r[t]      = close[t] / close[t-1] - 1
    TS_KURT[T] = r.rolling(length).kurt()   -- pandas' bias-corrected G2
                 masked where max(r) - min(r) <= 9.09e-13 over the window

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 4 -- the bias correction
        divides by `(length - 2) * (length - 3)` -- so a smaller or missing
        value falls back to the default. At 4 the column lives in
        [-6.0, 4.0], both ends measured on hand-built windows. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_KURT_{length}, dimensionless, in [-2.0702, 60.0] at
        length 60
"""
