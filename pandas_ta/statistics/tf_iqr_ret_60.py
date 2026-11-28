# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of ONE return has q75 == q25 == that return, so the column is
# exactly 0.0 everywhere: not an interquartile range but a constant. Two
# returns is the smallest window on which this is a spread at all -- there
# `0.75 * (n - 1)` is 0.75 and `0.25 * (n - 1)` is 0.25, so the value is
# half the gap between the two returns.
MIN_LENGTH = 2
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
#: The source's two quantiles. Module constants and not arguments: the
#: source names the INTERQUARTILE range, so 0.25 and 0.75 are the statistic
#: rather than a setting, and the column name carries neither of them.
#: `docs/TfIqrRet60Measured.md` (A5) prices the other quartile pairs.
Q_LOW = 0.25
Q_HIGH = 0.75


def tf_iqr_ret_60(close, length=None, offset=None, **kwargs):
    """Indicator: interquartile range of daily returns (TFIQRRET)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 60
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return
    # to take, so it is missing. Same guard, same reasons, as the sibling
    # `statistics/ts_q05_60.py`, which reads the same 60 returns.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    px = Series(c, index=close.index)

    # The simple return, spelled as a price RATIO minus one: `8a / 8b` is
    # the same double as `a / b`, so a x2^k rescale of the price cancels
    # exactly rather than to rounding, and the window's SORT ORDER -- which
    # is all a quantile reads -- cannot move at all.
    #
    # Both ends are finite, positive and normal by now, so the ratio can
    # still go wrong in exactly TWO ways, and they are treated differently.
    #
    # OVERFLOW: 1e-300 followed by 1e50 is a ratio of 1e+350, so an infinite
    # return. There is no return to take there, in the same sense as a NaN
    # close, so it is silenced here and dropped on the next line.
    #
    # UNDERFLOW: 1e308 followed by 1e-300 is a ratio of 1e-608, which
    # flushes to 0.0, so the return is exactly -1.0 -- finite, and KEPT.
    # That is the correctly rounded value of -1 + 1e-608, not a failure.
    # numpy's underflow state is "ignore" by default, so this raises
    # nothing.
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    # ⚠ DEFENCE IN DEPTH, and measured to be exactly that rather than
    # claimed to do work. pandas' own `rolling.quantile` already returns NaN
    # for the WHOLE window on a single infinity, at both quartiles and not
    # only the one near it (measured: a 60-point window with one +inf, one
    # -inf, or sixteen +inf reads NaN at q0.25 and q0.75 alike), so a mutant
    # with this line deleted is bit-identical to the module on a clean walk,
    # on a frame with an overflowing ratio and on the 1e308 cycle -- 650
    # shared bars, 0 differences (docs/TfIqrRet60Measured.md, G2).
    #
    # The line stays for two reasons that are not about today's output: it
    # states the intent where a reader looks for it, and it does not depend
    # on a pandas version continuing to blank such a window. There is NO sum
    # and NO accumulator here either way, so one spoiled return cannot leak
    # past the windows that hold it.
    r = r.where(np.isfinite(r))

    # pandas' own `rolling.quantile` IS the statistic the source names:
    # TSFEL's `interq_range` is `np.percentile(signal, 75) -
    # np.percentile(signal, 25)`, both at numpy's default LINEAR
    # interpolation, and the screen prototype is
    # `ret(c).rolling(60).quantile(0.75) - ret(c).rolling(60).quantile(0.25)`.
    # It is kept rather than re-derived so that this port and the screened
    # prototype are the same arithmetic to the last bit where both fire;
    # what this module adds is the NaN discipline above, not a second
    # spelling of the quantile.
    #
    # `interpolation` is left at pandas' default, which is `"linear"` and so
    # also numpy's and the source's. It is NOT spelled out here because the
    # keyword has moved between pandas versions while the default has not;
    # `tests/test_tf_iqr_ret_60.py::test_the_default_interpolation_is_linear`
    # pins that the default is what this module means.
    #
    # ⚠ `rolling.quantile` and `np.percentile` are not the same ARITHMETIC:
    # pandas' rolling blends the two order statistics as
    # `vlow + (vhigh - vlow) * frac`, and numpy's `_lerp` takes
    # `vhigh - (vhigh - vlow) * (1 - frac)` whenever `frac >= 0.5`, so at
    # `length` 60 the two quartiles here even take different branches from
    # each other (q0.75 has frac 0.25, q0.25 has frac 0.75). They are
    # nevertheless the same DOUBLE on every bar measured: bit-equal on
    # 1,440 of 1,440 bars of each of ten frames for the difference, and on
    # 28,800 single-quartile readings so the equality is not a cancellation
    # (docs/TfIqrRet60Measured.md, A2). ⚠ "Every bar measured" and not
    # "always": the two ALGEBRAIC FORMS differ on 16 of 20,000 random
    # 60-draw windows at q0.25 and 17 at q0.75, and on 0 of the 14,400
    # windows these ten frames produce. The pandas-versus-numpy count is
    # 16 and 0, because at q0.75 numpy takes the form that IS pandas'.
    # Prototype parity decides the spelling anyway; the measurement says it
    # costs nothing here.
    #
    # Two `rolling` objects and not one reused, matching the prototype
    # literally; `tests/test_tf_iqr_ret_60.py` pins that the one-object
    # spelling is bit-equal, so this is legibility and not arithmetic.
    hi = r.rolling(length, min_periods=length).quantile(Q_HIGH)
    lo = r.rolling(length, min_periods=length).quantile(Q_LOW)
    # The SPREAD. The price level has already cancelled, in the ratio
    # above, so both quartiles are dimensionless and so is their
    # difference; what the subtraction adds is that a common SHIFT of the
    # returns cancels too, which is why this reads dispersion and not level.
    iqr = hi - lo

    # Offset
    if offset != 0:
        iqr = iqr.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        iqr.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    iqr.name = f"TFIQRRET_{length}"
    iqr.category = "statistics"

    return iqr


tf_iqr_ret_60.__doc__ = \
"""Interquartile range of daily returns (TFIQRRET)

How wide the middle half of the last `length` daily returns is: q75 - q25.
⚠ A VOLATILITY reading: 0.0735..0.9511 vs NATR_60 on ten frames.

(That paragraph is short on purpose:
`docs/gen_indicator_dictionary.py` keeps only its first 150 characters for
`docs/IndicatorDictionary.md`, which CLAUDE.md sends a reader to first, so
the warning has to fit inside them.)

    r         = close / close.shift(1) - 1
    s         = the window's `length` returns, SORTED
    i(q)      = q * (length - 1),  k = floor(i(q)),  f = i(q) - k
    Q(q)      = s[k] + (s[k + 1] - s[k]) * f
    TFIQRRET  = Q(0.75) - Q(0.25)

At `length` 60 that is `i(0.75) = 44.25` and `i(0.25) = 14.75`, so the
column is a fixed blend of **four** of the window's 60 returns -- ranks
15, 16, 45 and 46 counting up from the smallest -- and of nothing else:
`(s[44] + 0.25*(s[45] - s[44])) - (s[14] + 0.75*(s[15] - s[14]))`.
Measured rather than asserted: on a window of 60 doubles, pushing the
other 56 arbitrarily far away while keeping each one's rank leaves the
value BIT-identical and equal to that closed form
(docs/TfIqrRet60Measured.md, A4).

Source: TSFEL (BSD-3-Clause), `features.py` `interq_range`
(`np.percentile(signal, 75) - np.percentile(signal, 25)`), as the formula
is stated by PandasTa issue #117: `q75 - q25` on 60 daily returns, in the
form of the screen prototype `docs/issues/screen/ind_screen_r2.py`
candidate `tf_iqr_ret_60` (local to the owner's machine),
`ret(c).rolling(60).quantile(0.75) - ret(c).rolling(60).quantile(0.25)`.
⚠ TSFEL is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line plus the published
definition of `interq_range`, not a read of TSFEL's code; anything TSFEL
does that the line does not say (how it treats NaNs, whether it has its
own windowing) is unverified here, and
`tests/test_tf_iqr_ret_60.py::test_the_source_library_is_not_installed_here`
asserts the limitation so it cannot rot into "checked against TSFEL".
⚠ TSFEL applies `interq_range` to the SIGNAL; the 60 and the daily
RETURNS are the screen's framing, and they matter -- the same statistic on
the price LEVEL is a different column (Spearman 0.0620 on a walk) and is
not scale-free at all.

⚠ **It is a VOLATILITY reading, and that is the first thing to know.** A
window with a wide return distribution has a wide interquartile range, so
the column rises when volatility rises. Measured Spearman over ten
synthetic 1,500-bar frames: **+0.0735 .. +0.9511** against `NATR_60`
(synthetic high/low = close x 1.004 / x 0.996), per-frame median 0.5641,
pooled 0.7858; -0.4672 .. +0.6489 against `UI_60`; and -0.0609 .. +0.9687
against the window's own return standard deviation, the textbook
alternative to an IQR. ⚠ The high end of each range is one frame --
`vol-cycle`, built so that volatility is the ONLY thing that moves -- and
on that frame every volatility measure agrees with every other; it is in
the set to show the ceiling, not as a typical reading. The 2026-10-24
screen measured the PROTOTYPE on real data and found the same shape: Gate
E's top comparator was `natr` at |rho| 0.6730 (n = 393,509), under the
0.76 ship line but the highest of the 687.

⚠ **It nearly mirrors `ts_q05_60` on a volatility-driven frame, and the
2026-10-24 Gate E run could not have seen that** -- `ts_q05_60` was
merged on 2026-11-14, three weeks after the screen. `TS_Q05_60` reads the
5% quantile of the SAME 60 returns, so it is the same window's lower tail
where this column is the same window's middle spread. Measured on the ten
frames: pooled Spearman **-0.6238**, per-frame -0.9364 .. +0.3075 with a
median |rho| of **0.3246** -- below the owner's 0.90 line on nine of ten
frames and at -0.9364 on `vol-cycle`. The two are NOT the same column:
this one is sign-blind (below) and that one is a signed tail, so a crash
and a melt-up separate them completely. The overlap is disclosed rather
than assumed away, and `docs/TfIqrRet60Measured.md` (E) carries an OWED
item with a rule: check whether `ts_q05_60` is among the Gate E run's 687
comparators and, if it is not, measure rho against `TS_Q05_60` over the
same 89 frames, read it against the same `r3-perframe-0.90` band, and
revert this column if it is STRUCK.
Also measured, for the other fork columns that landed AFTER the screen --
every `ts_*` and `tf_*` column below entered the tree between 2026-10-30
and 2026-11-16, read out of `git log --diff-filter=A` one file at a time
rather than assumed, and the same on either date field
(docs/TfIqrRet60Measured.md, E0, which tabulates both):
`TS_KURT_60` pooled -0.5789 (per-frame median |rho| 0.4203),
`TFSPECENT_64` -0.3066 / 0.1351, `TFHIGUCHI_30` +0.1362 / 0.1478,
`TFDFA_100` -0.0310 / 0.1076, `TS_STRIKE_20` +0.0194 / 0.1220,
`TS_IMQ_20` -0.0346 / 0.0210, `TFCENTROID_20` -0.0373 / 0.0270,
`TFZEROCROSS_20` +0.1178 / 0.1107, `TS_AC1_60` +0.0228 / 0.1769,
`TS_AGGAC_60_10` +0.1273 / 0.0956. `LOT_ZERORET_60` takes exactly ONE
value (0.0) on nine of the ten frames -- measured, not inferred -- so a
rank correlation against it is undefined there and its rho is defined on
one frame only (tick-rounded, +0.1450), the one whose returns can be
exactly zero.

⚠ **It is SIGN-BLIND.** Negating every return leaves the statistic
unchanged in exact arithmetic, because `q75(-x) = -q25(x)`, so a crash and
a melt-up of the same shape read the SAME value. Measured on a Student-t(3)
frame and its exact negation: identical NaN masks, Spearman 1.000000, 89 of
1,440 bars bit-equal and the rest within 5.829e-16 (the price path
re-rounds the returns); on 300 windows of exact doubles, where no price
path intervenes, 298 of 300 are bit-equal under negation and the worst
difference is 2.220e-16. A direction feature this is not -- pair it with
`osap_retskew_21` or `ts_q05_60` if the sign matters.

⚠ **It is a MIDDLE-of-the-distribution reading, so it ignores the tails.**
Ranks 15, 16, 45 and 46 of 60 are the only returns it reads, so the
largest and smallest 14 returns of every window are invisible to it: a
crash day enters only by demoting the ordinary returns one rank. That is
the opposite trade from `ts_q05_60`, which reads the 3rd and 4th smallest
and nothing else. The other quartile pairs are genuinely different
columns rather than rescalings: Spearman 0.8205 at q0.20..q0.80, 0.8507 at
q0.30..q0.70, 0.5583 at q0.40..q0.60, 0.4877 at q0.10..q0.90 and 0.1563 at
q0.05..q0.95 on a walk (docs/TfIqrRet60Measured.md, A5).

⚠ **It needs 61 closes and it is a slow state.** Two consecutive windows
share 59 of their 60 returns, so the column autocorrelates at **0.9718**
at lag 1, 0.8801 at lag 5, 0.5401 at lag 30 and 0.1849 at lag 60. One
extreme bar moves exactly `length` = 60 bars and then leaves (measured: a
-50% bar at 700 -- a power of two, so exactly ONE return changes -- moves
bars 700..759 and nothing else). It is not an event flag.

**The sign and the bounds.** The column is non-negative on every one of
the 1,440 fired bars of each of the ten frames, and that is a measurement
and not a proof: `q75 >= q25` holds exactly in real arithmetic, and the
two blends could in principle round into each other only where ranks 15
to 46 collapse onto one value, where both blends return that value
exactly. 2,400 windows built for exactly that collapse -- 400 with ranks
15..46 tied and 2,000 rounded onto a coarse grid -- produced **0** negative
readings and a worst value of 0.0. A flat frame reads exactly **0.0** on
all 240 of its windows. Above zero there is no bound: a 90-bar cycle of
[1e308, 1e-300, 1e8] closes -- every close finite, positive and normal --
reads **1e+308** on all 30 of its fired bars. The subtraction itself
cannot overflow, because a return is greater than -1 whenever both closes
are positive and normal, so the widest span a blend can see is
`DBL_MAX + 1`, which IS `DBL_MAX` (probed both ways,
docs/TfIqrRet60Measured.md, G4).

**This column IS the screen prototype**, bit-equal on 1,440 of 1,440 bars
of each of the ten frames with IDENTICAL NaN masks. They part company only
on the guards: with a close of inf, 0 or 1e-310 at bar 200 of a 400-bar
walk the prototype reports 280 bars to this module's 279, with a NEGATIVE
close there 340 to 279, and with a NaN close they report the same 279 (a
NaN needs no guard -- pandas propagates it).
Because Gate E's statistic is a Spearman over the bars where both fire,
the screen's figures are expected to carry over; the launcher's Gate E run
on THIS module is still the number that decides ship or revert.

The arithmetic is checked independently rather than trusted, in three
steps, and all three are BIT-equality -- which is unusual here. Only the
THIRD is explained by the quartiles being exact binary fractions; the
second is the `_lerp` branch question below and has its own answer.
* pandas' `roll_quantile` retyped from its documented behaviour -- sort the
  window, take the two order statistics around `q * (n - 1)`, blend them
  `vlow + (vhigh - vlow) * frac`, subtract -- sharing no code with this
  module: **1,440 of 1,440** bars of each of the ten frames, and at
  `length` 2, 5, 20, 21 and 250.
* the SOURCE's own spelling, `np.percentile(w, 75) - np.percentile(w, 25)`
  applied window by window: also **1,440 of 1,440** on each of the ten.
  ⚠ That is NOT what `ts_q05_60` found, and the difference is instructive.
  numpy's `_lerp` evaluates `b - (b - a) * (1 - t)` for `t >= 0.5` and
  `a + (b - a) * t` below it -- measured, not recalled: over 20,000 random
  60-draw windows `np.percentile` is the `b - d*(1 - f)` form on
  20,000 of 20,000 at q0.25 (frac 0.75) and the `a + d*f` form on 20,000
  of 20,000 at q0.75 (frac 0.25). So q0.75's spelling is already pandas'
  and q0.25's is not -- and q0.25 still agrees bit-for-bit, on all 28,800
  single-quartile readings of the ten frames and 14,404 more at five other
  lengths, so the equality is per quantile and not a cancellation in the
  difference. ⚠ It is a measurement and not a theorem: the two ALGEBRAIC
  FORMS differ on 16 of those 20,000 random windows at q0.25 and 17 at
  q0.75, and on 0 of the 14,400 windows these ten frames produce. At
  q0.75 numpy takes the form that IS pandas', so those 17 are not
  pandas/numpy disagreements: that count is 16 at q0.25 and 0 at q0.75.
* an EXACT rational oracle -- every return is a double, so a rational; the
  sort is exact, both blends and the subtraction are done in
  `fractions.Fraction`, and the result is rounded exactly ONCE at the end:
  bit-equal on **1,440 of 1,440** bars of each of the ten frames, max
  0.00 ulp. The module rounds seven times where the oracle rounds once and
  still lands on the same double every time, because `0.25` and `0.75` are
  exact (`Fraction(0.25) == 1/4`, `Fraction(0.75) == 3/4`) where
  `ts_q05_60`'s `Fraction(0.05)` is `3602879701896397/72057594037927936`.

Three readings the source's line leaves open, priced in
docs/TfIqrRet60Measured.md (A5) rather than assumed:
* The returns are SIMPLE (`close / close.shift(1) - 1`), the prototype's
  `ret`. LOG returns are Spearman 0.999890 and up to 1.067e-04 away -- and
  ⚠ unlike `ts_q05_60`, the ranks are NOT preserved exactly: a quantile
  commutes with a monotone transform but a DIFFERENCE of two quantiles
  does not.
* LINEAR interpolation, pandas' and numpy's default and so the source's.
  The alternatives are different columns: `lower` reads Spearman 0.978853
  and up to 2.720e-03 away, `higher` 0.984061 / 3.372e-03, `nearest`
  0.994839 / 2.058e-03, `midpoint` 0.995164 / 2.058e-03.
* `length` is 60 RETURNS, so 61 closes, and the first value lands at bar
  60. Rejected: 60 CLOSES, i.e. 59 returns, which is the off-by-one a
  reader makes rather than a different question (Spearman 0.983863, max
  |difference| 2.878e-03, first fired bar 59).

The level to expect, from 20,000 INDEPENDENT windows of 60 draws: a
gaussian window reads a mean of **1.3187 sigma** (sd 0.1982) against the
distribution's own 1.3490 sigma, a student-t(2) window 1.6140 (sd 0.2757)
and a one-sided exponential one 1.0751 (sd 0.2044). The estimator is
mildly low on the gaussian because it blends ranks 15/16 and 45/46 of 60
rather than the true quartiles.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 35 offsets on each of three frames and
at `length` 2, 5 and 250 -- and by six mutants in
`tests/test_tf_iqr_ret_60.py`. Five of them are live and caught 24 to 35
of those 35 offsets; the sixth shifts the NaN mask's own index by one bar,
which is a real look-ahead and is DEAD on a clean frame (every return
there is finite, so the shifted mask admits the same bars), and is caught
12 of 12 on a frame built with a bad close at every offset, where the bar
it moves is exactly J - 1.
Scale-free: every input is a price ratio and `8a / 8b` is the same double
as `a / b`, so the column is bit-identical under a x8 / x64 rescale of the
price -- 1,440 of 1,440 fired bars on each of the ten frames at both
factors, 1,498 / 1,495 / 1,480 / 1,250 at `length` 2 / 5 / 20 / 250, and
1,440 of 1,440 again at price levels of 1e-6, 1e+6 and 1e+100.
x10, x3.7, x0.1 and x1.0000001 are NOT bit-identical -- they perturb the
returns in their last bits, which can swap two nearly equal order
statistics -- but the NaN masks match exactly and the values agree to max
|difference| 4.163e-16, max relative difference 2.672e-14, those two being
the bounds across BOTH numpy dispatches measured.
⚠ Spearman is 1.000000 under all four factors on a walk, a tick-rounded
walk and a heavy-tailed frame, and 0.3417 .. 0.7377 on the TWO-POINT
frame. That is not a scale failure: there the column's 1,440 bars hold 5
distinct doubles spanning 2.220e-16 (1.110e-14 relative) around 0.02, so a
rank correlation is reading rounding and nothing else -- which is why
Gate D's reading on that frame is the relative difference and not the
Spearman.
A level SHIFT is NOT invariant, which is what makes Gate D's bit-identity
a real check here rather than a vacuous one: `close + 1` moves all 1,440
fired bars of a walk (max |difference| 2.744e-04), `+ 50` all 1,440
(9.200e-03) and `+ 1000` all 1,440 (2.747e-02).
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
This column divides by nothing: it selects four order statistics, blends
them with FIXED weights and subtracts, so a window with no dispersion has
a perfectly good interquartile range -- zero. Measured against the exact
rational oracle: a flat frame reads 0.0 on all 240 windows at 0.00 ulp of
error, a 1%-a-bar ladder reads two values (0.0 and 5.551e-17) on its 240 at
0.00 ulp, and a quiet frame whose returns are 1e-6 fires on 540 of 600
bars over 289 distinct values, also at 0.00 ulp.
⚠ The ladder's two values move between numpy dispatches: with `AVX512F
AVX512_SKX AVX2 FMA3` disabled it reads ONE value, exactly 0.0, because
the dispatched divide that builds the return renders the ladder's constant
rate as three doubles instead of four and a different one lands on the
read ranks. 0.00 ulp of oracle error either way, and the tests pin the
BOUND rather than either value. That and the Gate D per-cell tolerance
figures (three walk cells: x3.7 1.890e-14 -> 1.972e-14 relative and
3.331e-16 -> 4.163e-16 absolute, x0.1 1.923e-14 -> 2.223e-14, and
x1.0000001 160 -> 176 ulps with its other two figures unchanged) are the
two groups measured to move between the dispatches;
docs/TfIqrRet60Measured.md (F2) tabulates them, and every other figure in
this port except the wall-clock and those walk cells is identical either
way.
The siblings' ABSOLUTE
floor (window return range <= 4096 eps = 9.095e-13) would empty 480 of
those 1,020 -- all 240 flat windows and all 240 ladder ones, whose window
return range runs 4.441e-16 to 6.661e-16 -- and 0 dishonest ones; the
quiet frame survives it,
its smallest window return range being 3.751e-06, and so do all ten
ordinary frames, whose smallest window return ranges run 2.000e-02
(two-point) to 6.913e-02 (heavy-tailed), the walk's being 4.470e-02.
⚠ The ladder is the case worth reading, because its return is only
MATHEMATICALLY constant: float64 renders it as four distinct doubles
(0.009999999999999565 up, frame span 6.661e-16; its 60-bar windows span
4.441e-16 at the narrowest and 6.661e-16 at the widest), so the column
reads a 5.551e-17 spread where the mathematics says 0. An order statistic
PICKS one of those doubles, so the jitter
reaches the column as a choice between nearly equal numbers rather than as
an amplified error -- which is the whole reason a statistic that divides by
a spread needs a floor and this one does not.

Cost: two `rolling.quantile` passes over an `(n,)` array, which pandas
evaluates with a skiplist, plus two vectorised passes for the returns and
the mask and one subtraction. Nothing allocated here grows with `length`
-- the traced peak is **22.4 MB** on 400,000 bars at each of `length` 5,
60 and 250 -- but the TIME does, because the skiplist is O(n log length):
measured 124 / 257 / 319 ms for those three (best of three) on an idle box
and 150..180 / 272..351 / 327..432 ms on the same machine under load, a
35-45% spread between the extremes. ⚠ Wall-clock moves between runs and
machines, which is why the ORDERING and the PEAK are the claims and the
milliseconds are not;
docs/TfIqrRet60Measured.md (Z) keeps the one copy of them.

Calculation:
    Default Inputs:
        length=60, q=0.25 and 0.75 (module constants, not arguments)
    r[t]          = close[t] / close[t-1] - 1
    TFIQRRET[T]   = r.rolling(length).quantile(0.75)
                    - r.rolling(length).quantile(0.25)   -- linear interp

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 2 -- a window of one return
        has q75 == q25, so the column would be the constant 0.0 -- so a
        smaller or missing value falls back to the default. ⚠ `q *
        (length - 1)` decides WHICH order statistics are read, so `length`
        changes which ranks the column sees and not only its smoothness:
        at 5 and at 21 both fractions are 0.0, so it reads two returns
        exactly rather than blending four. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFIQRRET_{length}, a difference of two returns, so
        dimensionless and scale-free, in [0, +inf) -- 0.0 exactly on a flat
        frame, non-negative on every fired bar of every frame measured, and
        unbounded above (1e+308 is reachable; see above).
"""
