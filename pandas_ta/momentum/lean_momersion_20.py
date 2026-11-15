# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# One pair is `sign(r[t]) * sign(r[t-1])`, so a window of `length` pairs is
# the smallest unit the share is taken over. A one-pair window can only read
# 0 or 100, which is a flag and not a share.
MIN_LENGTH = 2
# `length` pairs need `length + 1` returns, and those need `length + 2`
# closes: the oldest pair in the window reads back two bars.
EXTRA_CLOSES = 2


def lean_momersion_20(close, length=None, offset=None, **kwargs):
    """Indicator: Momersion (LEAN_MOMERSION)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return
    # to take the sign of, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    px = Series(c, index=close.index)

    # The simple return, spelled as a price RATIO minus one: scale-free, and
    # `8a / 8b` is the same double as `a / b`, so a x2^k rescale cancels
    # exactly. Only the SIGN of this reaches the counts, which is why the
    # log-return and raw-difference spellings give the same column
    # (measured, docs/LeanMomersion20Measured.md Gate A).
    r = px / px.shift(1) - 1.0
    # +1 when two consecutive returns share a sign (momentum), -1 when they
    # oppose (mean reversion), 0 when either return is exactly zero -- a flat
    # bar has no sign, so its pairs are neither, and NaN while unknown.
    pair = np.sign(r) * np.sign(r).shift(1)

    def count(mask):
        """Bars in the trailing window where `mask` holds. The COMPARISON is
        what stops an unknown pair propagating -- `NaN > 0` is False, so it
        counts neither way -- and the cast only keeps the rolling sum in
        float. The window is the module's ONLY rolling call, so it is the
        only thing whose causality Gate B has to pin."""
        return mask.astype(float).rolling(length, min_periods=length).sum()

    momentum, reversion = count(pair > 0), count(pair < 0)
    signed = momentum + reversion
    # `signed == 0` is a window of nothing but flat bars: there is no share
    # of anything, so it is NaN rather than a made-up 50 or 0. Emptying the
    # denominator first means no zero ever reaches the division, so there is
    # nothing for an `errstate` to suppress.
    # The multiplication comes FIRST, as the source formula writes it:
    # `100 * MC / (MC + MRC)` is exact wherever the quotient of the two
    # integers times 100 is a double, where `100 * (MC / (MC + MRC))` rounds
    # twice (measured: the two agree to 7.1e-15 and differ on 281 of 1,479
    # bars of a walk, Spearman 1.000000).
    values = 100.0 * momentum / signed.where(signed > 0)

    # A window holding an unknown pair -- the warm-up, or a bad close -- would
    # otherwise read as a SHORTER window silently, because an unknown pair
    # counts neither way. It is missing instead.
    momersion = values.where(count(pair.notna()) == length)

    # Offset
    if offset != 0:
        momersion = momersion.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        momersion.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    momersion.name = f"LEAN_MOMERSION_{length}"
    momersion.category = "momentum"

    return momersion


lean_momersion_20.__doc__ = \
"""Momersion (LEAN_MOMERSION)

How much of the recent past was momentum rather than mean reversion. Take
the sign of each bar's simple return; a PAIR is two consecutive returns.
Over a rolling window of `length` pairs, count the pairs whose two returns
share a sign (MC, momentum) and the pairs whose returns oppose (MRC, mean
reversion), and report

    100 * MC / (MC + MRC)

so 100 is a window of pure continuation, 0 a window of pure alternation and
50 the coin-flip line. A pair in which either return is exactly zero has no
sign to agree or disagree with and is counted in NEITHER, which is why the
denominator is MC + MRC rather than `length`.

The column is a percentage of a count: dimensionless, bounded to [0, 100],
and DISCRETE -- `100 * MC / (MC + MRC)` with `MC + MRC <= length` has 129
reachable values at `length=20`, and on a frame whose returns are never
exactly zero every pair is signed, so the denominator is 20 and the value is
a multiple of 5 (measured: 14 distinct values over a 1,500-bar walk; 25 and
87 on a second walk rounded to 0.01 and put on a 0.5 grid, where flat bars
shrink the denominator -- a comparison between grids, not within one path).
docs/LeanMomersion20Measured.md carries every number.

⚠ The SPREAD is wide, and the ordering is the claim. Measured on synthetic
paths only: over 2,000 independent 20-pair windows of iid returns, whose
population value is exactly 50, the column's median is 50.0000 (mean
50.1300, sd 11.2276, p10 35.0000, p90 65.0000) -- unbiased in the median but
+-15 points at the deciles, so one reading of 60 says very little. The
ordering does hold: on 1,500-bar paths of AR(1) returns driven by ONE set of
innovations the median is 80.0000 at phi = +0.8, 65.0000 at +0.4, 35.0000 at
-0.4 and 20.0000 at -0.8, an iid gaussian walk reads 50.0000, and a hard
alternating path reads 0.0000 on all 1,479 of its fired bars. It is NOT drift-invariant -- drift makes up-moves
likelier and so changes the signs: Spearman 0.3829 against the same walk
given +0.004 of log drift a bar.

Source: QuantConnect Lean indicators (Apache-2.0), `MomersionIndicator`, as
the formula is stated by PandasTa issue #86: `MomersionIndicator(20):
100*MC/(MC+MRC), MC/MRC = same/opposite-sign consecutive return pairs`.
⚠ Lean's own C# source is NOT in this worktree and web access is
unavailable, so this port is derived from the issue's stated formula, not
read off Lean's code; anything Lean does that the issue's line does not say
(its warm-up value, whether its window counts pairs or returns, which side
a zero return falls on) is unverified here. The 20 is the issue's own
parameter, and the screen prototype is `docs/issues/screen/ind_screen.py`
candidate `lean_momersion_20` (local to the owner's machine).

Four readings the formula's wording leaves open, decided and priced in
docs/LeanMomersion20Measured.md rather than assumed:
* A zero return is counted in NEITHER MC nor MRC, as "same/opposite sign"
  says. The `if (p > 0) MC++ else MRC++` reading, which puts every flat bar
  into MEAN REVERSION, is a different column wherever prices repeat: max
  |difference| 5.5556 and Spearman 0.9974 on a walk rounded to 0.01 (0.27%
  zero returns), 55.7143 and 0.8399 on that walk on a 0.5 grid (14.01%). On
  a continuous walk, which has no exact ties, the two agree bit-for-bit.
* The window holds `length` PAIRS, so it reads `length + 2` closes. Holding
  `length` RETURNS instead (one pair fewer) is a different column: max
  |difference| 4.4737, Spearman 0.9685, and it fires one bar earlier.
* The warm-up is NaN. An implementation that emits the neutral 50 before its
  window fills would make the first 21 bars a constant, which this fork's ML
  contract reads as a value; NaN is the fork's convention.
* A window with no signed pair at all (every pair flat) is NaN, not 50 and
  not 0: there is no share to report. Measured: an exactly flat 300-bar
  frame fires 0 bars, and so does a staircase that steps once every 10 bars,
  whose steps are never adjacent.

Causal: bar T reads closes T - length - 1 .. T. Scale-free: the only input
is the sign of a price ratio, so the column is bit-identical under x8/x64
AND under x10/x3.7 (measured: 1,479 of 1,479 fired bars on each of a walk, a
0.01 grid and a 0.5 grid). The x10/x3.7 half of that is bounded, not
universal: a rescale cannot reorder two closes and the ratio of two distinct
doubles never rounds to 1.0, but a non-power-of-two k CAN round two closes
that are a single ulp apart to the SAME double, which turns a signed pair
flat. Measured on a frame of adjacent doubles straddling 1.0: x8/x64 fuse 0
of 299 pairs and stay bit-identical, x10 fuses 58 (19.40% of returns read as
zero) and agrees on 141 of 279 bars, x3.7 fuses 10 (3.34%) and agrees on
224. Only closes exactly ONE ulp apart can fuse: the widest fusion window is
1.5 ulp (at a power of two) and two ulps of separation land outside it for
every k. One tick over the price is 1e-9 even at a price of 1e6, seven
orders above an ulp, so no price feed reaches that frame. NaN on the first `length + 1` bars, on any
window holding a close that is NaN, infinite, zero, negative or subnormal,
and on any window whose every pair is flat.

Calculation:
    Default Inputs:
        length=20
    r[t]      = close[t] / close[t-1] - 1
    pair[t]   = sign(r[t]) * sign(r[t-1])        # +1, -1, or 0 if flat
    MC[t]     = count of pair > 0 over the trailing `length` pairs
    MRC[t]    = count of pair < 0 over the same window
    LEAN_MOMERSION = 100 * MC / (MC + MRC)       # NaN if MC + MRC == 0

Args:
    close (pd.Series): Series of 'close's
    length (int): Pairs per window. At least 2; a smaller or missing value
        falls back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: LEAN_MOMERSION_{length}, a percentage in [0, 100]
"""
