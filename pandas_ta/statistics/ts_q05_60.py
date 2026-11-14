# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of ONE return is that return itself -- the quantile of a single
# value is the value, for every `q` -- so it is `percent_return` under
# another name rather than a quantile. Two returns is the smallest window on
# which this is a quantile at all.
MIN_LENGTH = 2
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
#: The source's `q`. A module constant and not an argument: the issue asks
#: for ONE quantile, `q = 0.05`, and the column name carries the `05`, so a
#: second argument could not reach the name without renaming the column for
#: every caller. `docs/TsQ0560Measured.md` (A5) prices the other `q`.
Q = 0.05


def ts_q05_60(close, length=None, offset=None, **kwargs):
    """Indicator: 5% return quantile, historical VaR (TS_Q05)"""
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
    # same double as `a / b`, so a x2^k rescale of the price cancels exactly
    # rather than to rounding, and the window's SORT ORDER -- which is all a
    # quantile reads -- cannot move at all.
    #
    # Both ends are finite, positive and normal by now, so the ratio can
    # still go wrong in exactly TWO ways, and they are treated differently
    # because they are not the same kind of event.
    #
    # OVERFLOW: 1e-300 followed by 1e50 is a ratio of 1e+350, so an infinite
    # return. There is no return to take there, in the same sense as a NaN
    # close, so it is silenced here and dropped on the next line.
    #
    # UNDERFLOW: 1e308 followed by 1e-300 is a ratio of 1e-608, which
    # flushes to 0.0, so the return is exactly -1.0 -- finite, and KEPT.
    # That is not a failure: the true return is -1 + 1e-608, and -1.0 is its
    # correctly rounded value. It is why the column's lower bound is CLOSED
    # at -1 rather than open (docs/TsQ0560Measured.md, G2b). numpy's
    # underflow state is "ignore" by default, so this raises nothing.
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    # An infinity in the window would be an order statistic like any other --
    # the largest one -- so it would not reach `q = 0.05` by itself, and
    # dropping it is about the window being trustworthy rather than about the
    # arithmetic surviving. There is NO sum and NO accumulator here, so one
    # unbounded return cannot leak into a later bar the way it does in
    # `ts_kurt_60`: measured, a x1e+300 return leaves all 137 later bars of a
    # 400-bar frame BIT-IDENTICAL to the unspiked frame
    # (docs/TsQ0560Measured.md, G3).
    r = r.where(np.isfinite(r))

    # pandas' own `rolling.quantile` IS the statistic the source names:
    # tsfresh's `quantile(x, q)` is `pandas.Series(x).quantile(q)`, and the
    # screen prototype is `ret(c).rolling(60).quantile(0.05)`. It is kept
    # rather than re-derived so that this port and the screened prototype are
    # the same arithmetic to the last bit where both fire (bit-equal on
    # 1,440 of 1,440 bars of each of nine frames); what this module adds is
    # the NaN discipline above, not a second spelling of the quantile.
    #
    # `interpolation` is left at pandas' default, which is `"linear"` and so
    # also numpy's and the source's. It is NOT spelled out here because the
    # keyword has moved between pandas versions while the default has not;
    # `tests/test_ts_q05_60.py::test_the_default_interpolation_is_linear`
    # pins that the default is what this module means.
    #
    # ⚠ `rolling.quantile` and `Series.quantile` are not the same double.
    # pandas' rolling blends the two order statistics as
    # `vlow + (vhigh - vlow) * frac` and numpy (so `Series.quantile`) as
    # `vhigh - (vhigh - vlow) * (1 - frac)`; measured against an EXACT
    # rational oracle, numpy's branch is correctly rounded on 1,406 to 1,440
    # bars of each of nine frames and this one on 1,247 to 1,440, with every
    # disagreement in either direction at most ONE ulp
    # (docs/TsQ0560Measured.md, A2/A3). Prototype parity decides it.
    q05 = r.rolling(length, min_periods=length).quantile(Q)

    # Offset
    if offset != 0:
        q05 = q05.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        q05.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    q05.name = f"TS_Q05_{length}"
    q05.category = "statistics"

    return q05


ts_q05_60.__doc__ = \
"""5% return quantile, historical VaR (TS_Q05)

How bad a bad day is: the 5% quantile of the last `length` simple returns
-- a one-day historical VaR. ⚠ NEGATIVE volatility: -0.58..-0.74 vs NATR.
(That paragraph is short on purpose:
`docs/gen_indicator_dictionary.py` keeps only its first 150 characters for
`docs/IndicatorDictionary.md`, which CLAUDE.md sends a reader to first, so
the warning has to fit inside them.)

    r        = close / close.shift(1) - 1
    s        = the window's `length` returns, SORTED
    i        = q * (length - 1),  lo = floor(i),  frac = i - lo
    TS_Q05   = s[lo] + (s[lo + 1] - s[lo]) * frac

At `length` 60 that is `i = 2.95`, so the column is a fixed blend of the
**3rd and 4th smallest** returns of the window -- `s[2] + 0.95 * (s[3] -
s[2])` -- and of nothing else. Measured rather than asserted: on a window
of exact returns `2**e - 1`, moving 56 of the 60 returns arbitrarily far
away while keeping each one's rank leaves the value BIT-identical, and
equal to that closed form (docs/TsQ0560Measured.md, A4).

Source: tsfresh feature_calculators (MIT), `quantile`, and QuantConnect
Lean's `ValueAtRisk`, as the formula is stated by PandasTa issue #101:
`quantile(q=0.05) on 60 returns`, in the form of the screen prototype
`docs/issues/screen/ind_screen.py` candidate `ts_q05_60` (local to the
owner's machine), `ret(c).rolling(60).quantile(0.05)`.
⚠ Neither tsfresh nor Lean is installed in this worktree and web access is
unavailable, so the formula under test is the issue's line plus the
published definition of `feature_calculators.quantile`
(`pandas.Series.quantile`, linear interpolation), not a read of either
project's code; anything tsfresh or Lean does that the line does not say
(how a series shorter than one sample is treated, whether NaNs are dropped
rather than returning NaN, Lean's own windowing and sign convention) is
unverified here. The 60 and the `q = 0.05` are the issue's own parameters.

⚠ **It is NEGATIVE VOLATILITY, and that is the first thing to know.** A
window with a wide return distribution has a low 5% quantile, so the column
falls when volatility rises. Measured Spearman on six synthetic 1,500-bar
frames: **-0.5804 .. -0.7406** against `NATR_60` (synthetic high/low =
close x 1.004 / x 0.996), **-0.2513 .. -0.6120** against `UI_60` (the ulcer
index, the fork's other downside-risk column), and **-0.2974 .. -0.6907**
against the window's own return standard deviation. The 2026-10-24 screen
found the same thing on real data and on the PROTOTYPE: Gate E's top
comparator was `natr` at |rho| 0.6455 (n = 393,509), under the 0.76 ship
line but the highest of the 687. Read it as "how quiet has this window
been, with the sign flipped and the tail doing the talking".

⚠ **It is NOT the fork's `quantile`**, which is the SAME pandas machinery
applied to the price LEVEL: -0.0273 .. +0.2006 against `QTL_60_0.05` on
those six frames. A quantile of a price level is a support line; a quantile
of returns is a risk reading. Nor is it the other 60-return statistics
columns: -0.1803 .. +0.1094 against `TS_KURT_60`, -0.2787 .. +0.4315
against `TS_AC1_60`, +0.0360 .. +0.3468 against `OSAP_RETSKEW_21`.

⚠ **It reads 2 of the 60 returns, so it is a COARSE STEP function.** Two
neighbouring windows usually have the same 3rd and 4th smallest returns, so
the column plateaus: on a 1,500-bar walk it takes **149** distinct values
over its 1,440 fired bars, and 139 to 170 on eight of nine frames. Where
the returns themselves are few it collapses: on a two-point frame (every
return +-1%) it reaches **5** distinct values over 1,440 bars, one of them
on 1,305, and the five SPAN 2.2e-16 (2.2e-14 relative) around -0.01 --
numerically a constant.
A tree sees a slow ordinal, not a continuum.

⚠ **The sign is not guaranteed, and the bound is -1, CLOSED.** Every close
is finite, positive and normal by the time the ratio is taken, so every
return is at least -1 and so is the column: a frame of -50% bars reads
exactly -0.5, bit for bit, because `1 + r` is a power of two there. The
bound is closed and not open because a ratio can UNDERFLOW: 1e308 followed
by 1e-300 is 1e-608, which flushes to 0.0, so the return is exactly -1.0 --
the correctly rounded value of -1 + 1e-608, and kept rather than guarded
away. Reaching it in the COLUMN takes four such returns in one window,
since `q = 0.05` reads the 3rd and 4th smallest. ONE of them is the
window's own minimum, `s[0]`, so it never reaches `s[2]`/`s[3]` and the
column's FLOOR is untouched (measured: the unspiked and the spiked column
share a minimum of -0.032628306936088716, and 0 bars read -1.0) -- though
it does MOVE 60 bars, because a -1.0 at `s[0]` demotes every ordinary
return by one rank. FOUR of them do reach it: a 90-bar frame cycling
[1e308, 1e-300, 1e8] -- 30 returns of exactly -1.0, every close normal,
every other ratio finite -- reads exactly **-1.0** on all 30 of its fired
bars (docs/TsQ0560Measured.md, G2b, which also records that the probe
frame perturbs two returns and not one).
Above zero there is no bound: a constant-rate 1%-a-bar ladder reads
**+0.009999999999999787** on every one of its 240 windows and a flat frame
reads **0.0**, so "the 5% quantile is positive" is a reachable reading and
means "95% of the last 60 bars were up". It is still negative on all 1,440
fired bars of each of the nine frames measured, including a strongly
trending one (whose maximum is -0.005264).

⚠ **It needs 61 closes and it is a slow state.** Two consecutive windows
share 59 of their 60 returns, so the column autocorrelates at **0.9672** at
lag 1, 0.3287 at lag 30 and **-0.3241** at lag 60 -- the sign flips because
the window has moved past the bars that set the old reading. One extreme
bar moves exactly `length` = 60 bars and then leaves (measured: a -20% bar
at 700 moves bars 700..759 and nothing else). It is not an event flag.

The level to expect, from 20,000 INDEPENDENT windows of 60 draws: a
gaussian window reads a mean of **-1.5664 sigma** (sd 0.2555), not the
-1.6449 of the distribution's own 5% point, because the estimator reads the
3rd and 4th of 60 draws; a student-t(2) window -2.8003 (sd 0.9387) and a
one-sided exponential one -0.9329 (sd 0.0336). The SPREAD is what the law's
tails change, which is the other side of it being an order statistic.

**This column IS the screen prototype**, bit-equal on 1,440 of 1,440 bars
of each of nine 1,500-bar frames with IDENTICAL NaN masks. They part
company only on the guards: with a close of inf, 0 or 1e-310 at bar 200 of
a 400-bar walk the prototype reports 280 bars to this module's 279, with a
NEGATIVE close there 340 to 279, and with a NaN close they report the same
279 (a NaN needs no guard -- pandas propagates it). Because Gate E's
statistic is a Spearman over the bars where both fire, the screen's figures
are expected to carry over; the launcher's Gate E run on THIS module is
still the number that decides ship or revert.

The arithmetic is checked independently rather than trusted, in three
steps, and the first of them is BIT-equality. pandas' `roll_quantile`
retyped from its documented behaviour -- sort the window, take the two
order statistics around `q * (n - 1)`, blend them `vlow + (vhigh - vlow) *
frac` -- sharing no code with this module, agrees on **1,440 of 1,440**
bars of each of nine frames and at `length` 2, 5, 20, 21 and 250. Then
tsfresh's own spelling, `pandas.Series.quantile` applied window by window
(bit-equal to `np.quantile`, measured), agrees to at most **ONE ulp**: max
|difference| 6.9e-18, max relative difference 2.1e-16, Spearman 1.000000 on
each of the nine. Then an EXACT rational oracle -- every return is a
double, so a rational; the sort is exact and the blend is done in
`fractions.Fraction` and rounded once -- puts this module at most 1.00 ulp
and on average 0.00 .. 0.13 ulp from the correctly rounded answer, and
numpy's branch at most 1.00 ulp and on average 0.00 .. 0.024.
⚠ So the ONE thing this spelling costs is the last bit, in pandas' favour
on no frame and in numpy's on seven of nine. The same oracle prices the
other float detail the formula hides: `q` is the double 0.05 and not 1/20,
and the two exact answers differ on 92 of 1,440 bars of a walk, again by at
most one ulp.

Five readings the issue's line leaves open, priced in
docs/TsQ0560Measured.md (A5) rather than assumed:
* The returns are SIMPLE (`close / close.shift(1) - 1`), the prototype's
  `ret`. LOG returns give the same RANKS -- a quantile commutes with a
  monotone transform, measured Spearman 1.000000 -- but values up to
  5.4e-04 apart, which a threshold rule can see and a rank miner cannot.
* LINEAR interpolation, pandas' and numpy's default and so tsfresh's. The
  alternatives are different columns: `lower` (take `s[2]`) reads Spearman
  0.891866 and up to 1.1e-02 away, `higher` and `nearest` (both `s[3]`
  here) 0.998307 / 5.8e-04, `midpoint` 0.965027 / 5.2e-03.
* `length` is 60 RETURNS, so 61 closes, and the first value lands at bar
  60. Rejected: 60 CLOSES, i.e. 59 returns, which is the off-by-one a
  reader makes rather than a different question (Spearman 0.983016, max
  |difference| 9.4e-03, first fired bar 59).
* The QUANTILE and not the positive loss. VaR is usually quoted as
  `-quantile`; this column keeps the quantile's own sign, so a worse tail
  is a SMALLER number. A rank miner sees a pure sign flip (Spearman
  -1.000000) and a rule with a threshold does not.
* `q = 0.05`, the issue's. Its neighbours are genuinely different columns
  rather than rescalings: Spearman 0.662418 at q = 0.01 (which reads
  `s[0]`/`s[1]`), 0.673904 at 0.10, 0.442682 at 0.25 and 0.291534 at the
  median.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 35 offsets on each of three frames and at
`length` 2, 5 and 250 -- and by six mutants in `tests/test_ts_q05_60.py`.
Five of them are live and caught 6 to 35 of those 35 offsets; the sixth
shifts the NaN mask's own index by one bar, which is a real look-ahead and
is DEAD on a clean frame (every return there is finite, so the shifted mask
admits the same bars), and is caught 12 of 12 on a frame built with a bad
close at every offset, where the bar it moves is exactly J - 1.
Scale-free: every input is a price ratio and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8 / x64 rescale of the
price -- 1,440 of 1,440 fired bars on each of nine frames at both factors,
1,498 / 1,495 / 1,480 / 1,250 at `length` 2 / 5 / 20 / 250, and 1,440 of
1,440 again at price levels of 1e-6, 1e+6 and 1e+100.
x10, x3.7, x0.1 and x1.0000001 are NOT bit-identical -- they perturb the
returns in their last bits, which can swap two nearly equal order
statistics -- but the NaN masks match exactly and the values agree to max
|difference| 2.2e-16, max relative difference 1.3e-14.
⚠ Spearman is 1.000000 under all four factors on a walk, a tick-rounded
walk and a heavy-tailed frame, and 0.0401 .. 0.3352 on the TWO-POINT frame.
That is not a scale failure: there the column's 1,440 bars hold 5 distinct
doubles spanning 2.2e-16 (2.2e-14 relative), so a rank correlation is
reading rounding and nothing else -- which is why Gate D's reading on that
frame is the relative difference and not the Spearman.
A quantile is equivariant under any INCREASING transform of the return, not
only a rescale, so `price ** 2` and `price ** 0.5` -- which are linear in
the log return -- also leave Spearman at 1.000000, while moving values by
up to 0.0316.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close spoils two returns, so
it empties the `length + 1` = 61 windows it sits in -- measured at bars 0,
1, 60, 200 and 399 of a 400-bar walk for each of six bad values, 30 pairs,
giving 1 / 2 / 61 / 61 / 1 emptied windows and 0 bars moved BEFORE the bad
bar in all 30); and on any window holding a close pair whose ratio
OVERFLOWS (one spoiled return, so 60 windows).

⚠ **There is NO dispersion floor here, and that is a decision.** Siblings
`statistics/ts_kurt_60.py`, `ts_medskew_20.py` and `ts_above_mean_20.py`
refuse a window whose returns span 4096 ulps or less, because each divides
by a centre or a spread whose own rounding the statistic then amplifies.
This column divides by nothing: it selects two order statistics and blends
them with a FIXED weight, so a window with no dispersion has a perfectly
good 5% quantile -- its own constant return. Measured against the exact
rational oracle: a flat frame reads 0.0 on all 240 windows and a 1%-a-bar
ladder reads ONE value on all 240, both at 0.00 ulp of error, and a quiet
frame whose returns are 1e-6 fires on 540 of 600 bars over 48 distinct
values at a worst error of 1.00 ulp. The siblings' ABSOLUTE floor (window
return range <= 4096 eps = 9.095e-13) would empty 480 of those 1,020 -- all
240 flat windows and all 240 ladder ones, whose return range is 4.441e-16
-- and 0 dishonest ones; the quiet frame survives it, its smallest window
return range being 3.751e-06, and so do all nine ordinary frames, whose
smallest is 2.000e-02.
⚠ The ladder is the case worth reading, because its return is only
MATHEMATICALLY constant: float64 renders it as FOUR distinct doubles
(0.009999999999999565 up). An order statistic PICKS one of them, so the
jitter reaches the column as a choice between four nearly equal numbers
rather than as an amplified error -- which is the whole reason a statistic
that divides by a spread needs a floor and this one does not.

Cost: one `rolling.quantile` over an `(n,)` array, which pandas evaluates
with a skiplist, and two vectorised passes for the returns and the mask.
Nothing allocated here grows with `length` -- the traced peak is **19.2 MB**
on 400,000 bars at each of `length` 5, 60 and 250 -- but the TIME does,
because the skiplist is O(n log length): measured 67 / 116 / 149 ms for
those three (best of three). ⚠ Wall-clock moves between runs and machines;
docs/TsQ0560Measured.md (Z) keeps the one copy of these and the PEAK is the
claim.

Calculation:
    Default Inputs:
        length=60, q=0.05 (a module constant, not an argument)
    r[t]       = close[t] / close[t-1] - 1
    TS_Q05[T]  = r.rolling(length).quantile(0.05)   -- linear interpolation

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 2 -- the quantile of a single
        return is that return -- so a smaller or missing value falls back to
        the default. ⚠ `q * (length - 1)` decides WHICH order statistics are
        read, so `length` changes the column's meaning and not only its
        smoothness: below 21 it reads the smallest and the second smallest
        return, at exactly 21 the second smallest alone (the fraction is
        0.0), and at 250 the 13th and 14th. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_Q05_{length}, a return, so dimensionless and scale-free,
        in [-1, +inf) -- negative on every bar of every ordinary frame
        measured, 0.0 on a flat one and positive on a monotone rise. The
        bound is CLOSED: -1.0 is reachable, though only through four
        underflowing price ratios in one window (see above).
"""
