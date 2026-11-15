# -*- coding: utf-8 -*-
"""Sign Changes of Returns (TFZEROCROSS) -- port of TSFEL's `zero_cross`
(BSD-3-Clause), https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py`, as PandasTa issue #113 states it:

    features.py zero_cross: #diff(sign(x)) != 0

⚠ That one line, quoted from the issue, is the WHOLE of the source text
available here. TSFEL is not installed in this worktree, `docs/pine/` does
not carry it, and web access is unavailable, so Gate A does NOT read TSFEL's
own code: `tests/test_tf_zero_cross_20.py::test_the_source_library_is_not_readable_here`
asserts that, so the limitation fails loudly if the environment ever changes.
What Gate A checks is the quantity that line names -- how many of the
adjacent pairs inside the window hold two returns of DIFFERENT sign, with
`sign` the three-valued `np.sign` the line names and not a two-way split --
against the owner's screen prototype and against a window-by-window Python
retype of the same line. Nothing here is evidence about anything TSFEL does
that the line does not state.

The scale-free form is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py:216-217` (candidate `tf_zero_cross_20`,
local to the owner's machine -- `docs/issues/` is gitignored):

    @cand("tf_zero_cross_20", "sign changes of daily returns (20)", TF,
          "features.py zero_cross: #diff(sign(x)) != 0")
    def _(o, h, l, c, v):
        return roll(ret(c), 20,
                    lambda W: (np.diff(np.sign(W), axis=1) != 0)
                    .sum(1).astype(float))

CALCULATION.  Over the `length` simple returns ending at, and including, the
current bar: take the sign of each return, and count how many of the
`length - 1` adjacent pairs hold two different signs. The result is an
integer on `0 .. length - 1`.

⚠ THE ONE DELIBERATE DIVERGENCE FROM THE PROTOTYPE is what a window holding
a non-finite return reads. `np.sign(NaN)` is NaN and `NaN != 0` is True, so
the prototype COUNTS a missing return's two comparisons as sign changes;
this module reports the window as missing instead, which is the fork's
convention. Every frame has at least one such window -- the one at bar
`length - 1`, which holds `r[0]`, the return of the first close, which no
close precedes. Measured over twelve synthetic frames: on the 16,460 bars
both define the two are EQUAL (not to a tolerance -- the arithmetic is an
integer count), and the prototype reads 12 bars this module does not, one
per frame; at bar 19 of a walk the prototype reads 8 where the 18 KNOWN
pairs of that window hold 7 changes (§A1 of `docs/TfZeroCross20Measured.md`).

⚠ THE SIGN IS THREE-VALUED, and on a tick grid that is the whole of the
column. `np.sign(0.0)` is 0, so a return of exactly zero -- an unchanged
close -- is its OWN sign, and a lone flat bar between two rises counts TWO
changes where a two-way split (`-1` below zero, `+1` at or above) counts
none. On a continuous frame the two readings are the same column, bit for
bit; on the same walk rounded to a 0.01 tick (0.40% flat returns) they
differ on 96 of 1,480 bars by up to 2, and on a 0.5 grid (21.75% flat) on
1,418 of 1,480 bars by up to 10, Spearman 0.6176 (§A4a). The three-valued
form is the one the issue's line names.

⚠ IT IS A NEAR-RESTATEMENT OF `LEAN_MOMERSION_20`, WHICH THIS FORK ALREADY
SHIPS, and that is the one thing to read before using both. Momersion counts
the same events over `length` PAIRS and reports the share that AGREE:
`100 * MC / (MC + MRC)`. With no flat bar in the window every pair is signed,
so `MC + MRC` is 20 and momersion is exactly `100 * (20 - MRC) / 20` -- an
affine function of this column at `length` 21. Measured: at `length` 21 the
identity holds on 1,479 of 1,479 bars of a walk and of a heavy-tailed frame,
Spearman -1.0000; at the shipped default of 20 returns (19 pairs, one pair
fewer than momersion's window) Spearman runs -0.9655 to -0.9795 over the
seven 1,500-bar frames with no flat bar in them. What separates the two
columns is flat bars, and the overlap decays with the grid: -0.9733 /
-0.9622 / -0.9146 / -0.8322 / -0.7586 / -0.6647 at 0.07% / 0.40% / 4.40% /
11.47% / 21.75% / 37.63% flat returns (§L1, §L1b, §L1c). ⚠ The 2026-10-24
screen this issue quotes could NOT have seen this: `lean_momersion_20`
landed on 2026-11-11 (commit `2213dc9`, read from `git log`), eighteen days
after the screen's stage-2 fork overlap measured a maximum of 0.2420. Which
end of that gradient real BIST daily data sits at is NOT measurable from
this worktree, and Gate E will not answer it either -- its 687 comparators
are the engine's, not this fork's. So the receipt session OWES one more
measurement, stated as a rule in §E of `docs/TfZeroCross20Measured.md` and
pinned by
`tests/test_tf_zero_cross_20.py::test_the_overlap_measurement_is_still_owed_from_the_gate_e_run`:
Spearman against `LEAN_MOMERSION_20` over the same 89 ALTPORT-1 frames,
read against the same `r3-perframe-0.90` band, and a revert if it is
STRUCK.

THE SPELLING IS TWO PREFIX SUMS, not a window block, and the two are the
same column: the pair `(t - 1, t)` either changes sign or does not, whatever
window reads it, so the count over a window is a difference of two running
totals. Measured equal to the `(rows, length)` block spelling on a
400,000-bar frame at `length` 20 and 250; what separates them is memory, and
the gap grows with `length`: a traced peak of 29.7 MB at both lengths
against 139.2 MB and 1,702.1 MB (§Z). The totals are `int64`, so the
subtraction is exact at any frame length.

CAUSALITY.  Bar `T` reads the returns `T - length + 1 .. T`, i.e. the closes
`T - length .. T`; nothing is shifted forward.
`tests/test_tf_zero_cross_20.py` proves this by future-perturbation sweeps,
by prefix truncation, and by five mutants read off this file, edited and
`exec`'d in memory.

SCALE-FREE.  The input is `close.pct_change(fill_method=None)`, a ratio, so
a uniform price rescale cancels before anything else happens, and only the
SIGN of that ratio reaches the output: bit-identical under x8, x64, 2**-40,
2**40 and 2**100 on all twelve frames, under x8 at `length` 2, 5, 20, 60 and
250, and -- unlike every port whose arithmetic is floating point --
bit-identical under the INEXACT factors x10, x3.7, x0.1 and x1.0000001 as
well, on all twelve (§D). ⚠ A level SHIFT does not move it either, which is
the usual anti-vacuity check and does not work here: `c + k > c' + k`
exactly when `c > c'`, so adding 10.0 or 100.0 to a level-100 walk moves 0
of 1,480 bars. What makes the bit-identity above non-vacuous is that the
column is NOT constant -- 13 to 15 distinct values on each of the nine
varied frames, and 0 .. 19 all reached pooled (§C, §D).
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Fewest returns a window may hold. One return has no adjacent pair at all,
#: so the count would be a constant 0; two returns give exactly one pair, so
#: two is the shortest window on which this column varies.
MIN_LENGTH = 2


def tf_zero_cross_20(close, length=None, offset=None, **kwargs):
    """Indicator: Sign Changes of Returns (TFZEROCROSS)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    # length + 1 closes: the window holds `length` RETURNS, and a return needs
    # a previous close.
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # fill_method=None: a gap must propagate as NaN, never be padded over.
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)
    n = r.size
    finite = np.isfinite(r)
    # The source's `sign(x)`, three-valued: -1.0, 0.0 and +1.0, with a return
    # of exactly 0.0 its OWN sign rather than a member of either camp -- see
    # the module docstring, which prices the other reading. A non-finite
    # return would make `np.sign` a NaN that compares unequal to everything;
    # it is replaced by 0.0 here and every window that holds it is dropped
    # below, so the substitute never reaches a shipped value.
    sign = np.sign(np.where(finite, r, 0.0))

    # `np.diff(sign) != 0` for ONE pair of adjacent returns, laid out along
    # the whole series instead of inside each window: `changed[t]` is the pair
    # `(t - 1, t)`. Two signs differ exactly when their difference is
    # non-zero, so this is the source's test and not an approximation of it --
    # and it is integer arithmetic, which is why the agreement with the
    # prototype is EXACT rather than a tolerance.
    changed = np.zeros(n, dtype=np.int64)
    changed[1:] = sign[1:] != sign[:-1]

    # Prefix sums, with a leading 0 so that `cs[b + 1] - cs[a]` is the sum
    # over `a .. b` for every a and b, including a = 0. `int64` throughout:
    # the counts stay exact at any frame length, where a float prefix sum
    # would not.
    cross_cs = np.concatenate(([0], np.cumsum(changed)))
    finite_cs = np.concatenate(([0], np.cumsum(finite, dtype=np.int64)))

    # Bar T reads the returns T - length + 1 .. T (so the closes
    # T - length .. T) and the length - 1 pairs T - length + 2 .. T between
    # them. T runs from `length`, not `length - 1`: the window at `length - 1`
    # would hold `r[0]`, which no close precedes.
    #     count[T]    = cross_cs[T + 1]  - cross_cs[T - length + 2]
    #     n_finite[T] = finite_cs[T + 1] - finite_cs[T - length + 1]
    # written as slices over T = length .. n - 1. Every pair counted lies
    # inside the returns the second line checks, so a non-finite return can
    # never reach a window that is reported.
    count = cross_cs[length + 1:] - cross_cs[2:n - length + 2]
    n_finite = finite_cs[length + 1:] - finite_cs[1:n - length + 1]

    out = np.full(n, np.nan)
    # A window holding a non-finite return is a gap, not a count of zero.
    # This is the one DELIBERATE divergence from the screen prototype, which
    # counts the NaN's own unequal comparisons instead; see the module
    # docstring.
    out[length:] = np.where(n_finite == length, count, np.nan)
    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"TFZEROCROSS_{length}"
    result.category = "statistics"

    return result


tf_zero_cross_20.__doc__ = \
"""Sign Changes of Returns (TFZEROCROSS)

Sign changes among the last `length` daily returns, an integer
0 .. `length - 1`. ⚠ Nearly restates `LEAN_MOMERSION_20`: Spearman
-0.97 on a walk.

0 is a window that never turned and 19 at `length` 20 one that
alternated every bar. A choppiness reading of the RETURNS, blind to
how big they were. The first paragraph above is what
`docs/IndicatorDictionary.md` shows, which is why the overlap is in
it: 150 characters is all a reader of the dictionary gets.

⚠ **It nearly restates `LEAN_MOMERSION_20`, which this fork already
ships.** Momersion counts the same sign agreements over `length`
PAIRS and reports the share that agree, so on a window with no flat
bar it is exactly `100 * (20 - this count) / 20` at `length` 21
(measured: the identity holds on 1,479 of 1,479 bars of a walk and
of a heavy-tailed frame, Spearman -1.0000). At the shipped default
-- 20 returns, one pair fewer than momersion's window -- Spearman
runs -0.9655 to -0.9795 over the seven 1,500-bar frames with no flat
bar in them, and the overlap falls as flat bars become common:
-0.9146 at 4.40% flat returns, -0.8322 at 11.47%, -0.7586 at 21.75%,
-0.6647 at 37.63%.
⚠ The 2026-10-24 screen behind issue #113 could not have seen this:
`lean_momersion_20` landed on 2026-11-11, eighteen days later. Where
real BIST daily data sits on that gradient is NOT measured here, and
Gate E will not say either -- its comparators are the engine's, not
this fork's. So the receipt session OWES one more measurement:
Spearman against `LEAN_MOMERSION_20` over the same 89 frames, read
against the same `r3-perframe-0.90` band, and a REVERT if it is
STRUCK (`docs/TfZeroCross20Measured.md` §E). Until that lands, using
both columns double-weights one signal in a miner.

Source: TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py` `zero_cross`, which PandasTa
issue #113 quotes as "features.py zero_cross: #diff(sign(x)) != 0".
⚠ That is the entire source text available in this worktree: TSFEL
is not installed and web access is unavailable, so Gate A checks the
quantity that line names -- against the owner's screen prototype and
against a window-by-window retype of the line -- and NOT TSFEL's own
code. The 20 is the issue's own parameter, and the input is the
simple return, the prototype's own reading of "daily returns".

**This column IS the screen prototype wherever BOTH are defined**:
equal on all 16,460 bars of twelve synthetic frames, and
EXACTLY equal, not to a tolerance, because the arithmetic is an
integer count. They part only at the windows holding a non-finite
return, which the prototype counts (``np.sign(NaN)`` is NaN and
``NaN != 0`` is True) and this port reports as missing -- 12 bars
over those twelve frames, one per frame.

⚠ **A flat bar is its own sign.** `np.sign(0.0)` is 0, which the
issue's line names, so an unchanged close counts a change on the way
in AND on the way out: a lone flat bar between two rises adds two.
On a continuous frame that choice is invisible; on a 0.01-tick copy
of the same walk (0.40% flat returns) it moves 96 of 1,480 bars, and
on a 0.5 grid (21.75% flat) 1,418 of 1,480, by up to 10. ⚠ Real
daily data is a tick grid, so this is not an edge case there.

**What moves it.** Measured on 1,500-bar synthetic frames
(`python docs/measure_tf_zero_cross_20.py`): AR(1) returns with
phi = -0.6 read a median of 13.0, a Gaussian random walk 9.0, and
AR(1) with phi = +0.6 reads 6.0 -- the ordering the count exists
for. The centre for independent continuous returns is 9.5, and
4,000 disjoint windows of iid normal returns read a mean of 9.5077
(sd 2.1991, min 2, max 17), so a single reading says little. It is
blind to the SIZE of the returns (rescaling the whole return window
by 0.5, 2, 1e-6 or -1 moves 0 of 1,479 bars) but NOT to a constant
drift, which makes one sign likelier: adding 0.002 a bar to a walk's
returns takes the mean from 9.3245 to 9.0223, 0.010 to 5.2847 and
0.050 to 0.0000. It is also blind to a time REVERSAL -- reversing a
window keeps every adjacency -- which no other order change is: over
500 sampled windows a reversal left the count unchanged on 500 and a
permutation on 70.

⚠ **It is coarse and heavily tied, and it is a STATE.** 20 reachable
values at `length` 20, of which a 1,500-bar walk shows 13.
Neighbouring windows share 19 of their 20 returns, so the column
autocorrelates at 0.9406 at lag 1, 0.6871 at lag 5, 0.3817 at lag 10
and -0.1183 at lag 20 on that walk.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep and by the mutant tests in
`tests/test_tf_zero_cross_20.py`.
Scale-free, and more strongly than a floating-point column can be:
only the SIGN of a price ratio reaches the output, so the column is
bit-identical under x8, x64, 2**-40, 2**40 and 2**100 on all twelve
frames AND under the inexact x10, x3.7, x0.1 and x1.0000001. ⚠ A
level shift does not move it either (0 of 1,480 bars at +10.0 and
+100.0 on a level-100 walk): `c + k > c' + k` exactly when
`c > c'`. A shift that makes the path STRADDLE zero does move it --
74 of 1,480 bars at -50.0, where 970 of 1,500 closes go negative --
but one that takes every close negative does not (0 bars at -200.0
and -1000.0), because then every sign flips at once and every
disagreement stays one. So bit-identity here is not evidence of a live
column;
that the column is not constant is, and it is measured separately.
NaN on the first `length` bars -- `length` returns need `length + 1`
closes -- and on any window holding a return that is not finite.
⚠ That is NOT the same as "any window holding a bad close", and §G
measures the difference: a NaN close breaks the two returns it
enters (21 windows), a zero or subnormal close breaks only the NEXT
one (20, starting a bar later, because its own return is `-1`), an
infinite close breaks only its own (20, ending a bar earlier), and a
NEGATIVE close breaks none at all -- nothing here takes a logarithm,
so it is a price and is read.

Calculation:
    Default Inputs:
        length=20
    r[t]         = close[t] / close[t-1] - 1
    s[t]         = sign(r[t])                 # -1, 0 or +1
    TFZEROCROSS  = how many of the length - 1 adjacent pairs of
                   s[T - length + 1 .. T] hold two different signs,
                   i.e. TSFEL's np.sum(np.diff(np.sign(w)) != 0),
                   NaN if any of those returns is not finite

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 2 -- one return has
        no adjacent pair -- so a smaller or missing value falls back
        to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFZEROCROSS_{length}, a dimensionless integer count on
        0 .. length - 1, i.e. 0 .. 19 at length 20
"""
