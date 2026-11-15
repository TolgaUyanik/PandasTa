# -*- coding: utf-8 -*-
"""Up-Volume / Down-Volume Ratio (VR) -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#40`, per issue #77. Source cited by the issue:

    #40: SUM(C>C1 ? V : 0, 26) / SUM(C<=C1 ? V : 0, 26) * 100

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:350-354`):

    @cand("g191_040", "up-volume / down-volume ratio (VR)", G,
          "#40: SUM(C>C1 ? V : 0, 26) / SUM(C<=C1 ? V : 0, 26) * 100")
    def _(o, h, l, c, v):
        up = c > delay(c, 1)
        return 100 * sdiv(tsum(v.where(up, 0.0), 26), tsum(v.where(~up, 0.0), 26))

DISCLOSED INTERPRETATION CHOICE -- the one place this port deviates from
the prototype, not from the issue's own string. The prototype computes the
down-bucket as `v.where(~up, 0.0)`, i.e. "whatever `up` is not". At bar 0,
`C1 = DELAY(C, 1)` is undefined (no prior bar), so `up = C > C1` evaluates
to `False` (a comparison against `NaN` is `False`, never `NaN`, under
pandas/numpy). `~up` is then `True` at bar 0, so the prototype's own
formula silently counts bar 0's entire volume as a DOWN bar -- a day whose
direction is actually unknown, not down. This fork does not repeat that:
both buckets are made explicitly `NaN` wherever the one-bar direction is
undefined (`close_prior.isna() | close.isna()`), so such a bar
contributes to NEITHER the up-sum nor the down-sum, and -- because
`rolling(length, min_periods=length).sum()` needs `length` genuinely valid
(non-`NaN`) observations in its window -- every window touching it comes
out `NaN` too, exactly the same warm-up shape `g191_043` already ships
(`min_length = length + 1`).

The mask covers BOTH closes of the comparison, not just the prior one. A
`NaN` at `C[t]` for `t > 0` makes `C > C1` and `C <= C1` BOTH `False` by
the same pandas rule quoted above, which without the mask would drop bar
`t`'s volume silently out of both buckets while the `length` windows
containing it still fired over `length - 1` defined bars. `g191_043`'s
`signed_series(close)` (a `close.diff()`) propagates that `NaN` by
construction; this module's two comparisons do not, so the mask does it
explicitly. Pinned by
`tests/test_g191_040.py::test_a_nan_close_blanks_only_the_windows_that_contain_it`.

Measured, not asserted, on the 1,500-bar frame of
`docs/measure_g191_040.py`: the prototype's own expression and this
module's output disagree on their NaN masks at exactly ONE index, `[25]`
(the single full `length`-bar window that touches bar 0), and where both
are defined the largest difference is `2.84e-14` -- float64 rounding, not
a semantic gap: pandas' rolling sum accumulates in a different order once
a `NaN` sits at bar 0 of the summed series. So no bar whose window
excludes the undefined bar changes value beyond float64 noise; only the
last leading warm-up bar, which the prototype reported from a fabricated
direction, is withheld.

One `NaN` close at `t` blanks `length + 1` output bars, not `length`: it
makes the direction of bar `t` undefined AND the direction of bar `t+1`
(whose `C1` is that same `NaN`), so the windows containing either run from
`t` to `t + length`. Measured on the 1,500-bar frame with `close[700]` set
to `NaN`: output bars `700..726` (27 bars at `length=26`) turn `NaN`, no
bar becomes defined that was not, and of the 1,447 bars that stay defined
the largest move is `5.68e-14` -- the same rolling-accumulation-order
rounding as the `[25]` comparison above, not a semantic change.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1` denotes `C` delayed one bar, `DELAY(C, 1) = C.shift(1)`
  (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never a
  look-ahead.
* `C>C1 ? V : 0` / `C<=C1 ? V : 0` split each bar's volume into an
  up-bucket and a down-bucket by the sign of the one-bar price change,
  with a flat day (`C==C1`) landing in the down-bucket (`C<=C1` is true on
  a tie) -- the issue's own string, not a disclosed choice.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum, `min_periods=n` by pandas' own default.
* `C` = close, `V` = volume. No other OHLCV field is read.

CALCULATION, in the order computed below (`length=26`):
    C1          = DELAY(C, 1)
    up_volume   = V where C  > C1, else 0; NaN at bar 0 (C1 undefined)
    down_volume = V where C <= C1, else 0; NaN at bar 0 (C1 undefined)
    G191_040    = 100 * SUM(up_volume, length) / SUM(down_volume, length)
                  inf -> NaN (an all-up window has zero down-volume)

CAUSALITY. `C1[t]` reads only `C[t-1]`. `up_volume[t]` / `down_volume[t]`
are pointwise functions of `C[t]`, `C1[t]` and `V[t]` -- bars no newer than
`t`. `SUM(up_volume, length)[t]` and `SUM(down_volume, length)[t]` are both
trailing `length`-bar sums over the window `[t-length+1, t]`, every index
`<= t`. The final division and the `*100` read only bar `t`'s two sums.
Nothing in the chain reads a bar newer than `t`. `tests/test_g191_040.py`
proves this both by future-perturbation (real module: 0 of N offsets leak,
over a synthetic walk rewritten from an offset onward) and by a mutant
(`importlib` source read, `exec`'d in memory, shown live different from
the real module): shifting the final write index `length` bars into the
future.

WARM-UP. `C1` is undefined at bar 0, so `up_volume`/`down_volume` are
`NaN` there too. `SUM(up_volume, length)` and `SUM(down_volume, length)`,
trailing `length`-bar sums with `min_periods=length`, each need `length`
CONSECUTIVE valid observations ending at `t`; the window `[0, length-1]`
has only `length-1` valid bars (bar 0 excluded), so it is `NaN`, and the
first fully-valid window is `[1, length]` at `t = length`, i.e.
`min_length = length + 1` bars of history (**27** at the shipped default),
enforced by `verify_series` -- the same shape `g191_043` already ships.

SCALE-FREE. Algebraically, for ANY `k > 0`: scaling volume (`V -> k*V`)
scales both sums linearly (the bucket split depends only on the SIGN of
`C - C1`, which does not change), so the ratio `(k*SUM(up_volume,length)) /
(k*SUM(down_volume,length)) = SUM(up_volume,length)/SUM(down_volume,length)`
is identical -- the `k` cancels, and the `*100` constant is untouched
either way. Scaling price (`C -> k*C`) changes nothing in exact arithmetic:
`SIGN(k*C - k*C1) = SIGN(C - C1)` for any `k > 0`, so the bucket split and
both sums are unchanged. **What the code actually computes, measured, not
merely asserted:** `k*C` and `k*C1` are each rounded independently in
float64 before the `>`/`<=` comparison, so a pair of closes separated by
less than roughly one ULP after scaling could in principle flip a
near-tied comparison -- this is not ruled out by the algebra above, only
by measurement on the tested cases. Measured on a synthetic walk: VOLUME
x8/x64 land bit-identical (power-of-two multiplication is exact in
IEEE754, so the algebraic cancellation is also exact in float64), VOLUME
x10/x3.7 land within float64 rounding tolerance, and PRICE x8/x64/x10/x3.7
all land bit-identical on that walk (no comparison flip was observed).
Measured in the test file and `docs/measure_g191_040.py`, not merely
asserted.

ZERO-DOWN-VOLUME. The denominator is zero exactly when the DOWN-BUCKET
SUM over the window is zero, which has TWO distinct causes, not one:
every bar in the window is an up-day (no bar lands in the `C<=C1`
bucket), OR every non-up bar in the window carries zero volume (bars land
in the bucket but contribute nothing). The second is the one a real
exchange produces: a halted or zero-turnover session prints a flat close,
`C<=C1` puts it in the down bucket, and `V = 0` keeps the sum at zero.
`(100 * numerator / denominator)` is `+inf` in both cases WHENEVER the
up-bucket sum is non-zero -- as it is in both pinned fixtures -- and
`.replace([np.inf, -np.inf], np.nan)` then maps it to `NaN`. A window
whose up-sum is zero as well divides `0/0`, which is already `NaN` before
the `.replace` ever sees it. The column is `NaN` either way.

How often either happens on real data is NOT measured here -- that waits
on Gate E, the only real-data run in this protocol. What IS measured: the
two synthetic frames whose fire counts are pinned do not reach the branch
at the shipped `length=26` -- the 1,500-bar frame of
`docs/measure_g191_040.py` (`fires = 1474 = 1500 - 26`, no interior gap,
longest run of consecutive up-days 16, short of the 26 a rally would
need) and the 900-bar frame of
`tests/test_g191_040.py::test_fires_and_is_not_constant` (`fires = 874 =
900 - 26`). The other synthetic frames in those two files are not checked
for it. Both causes are therefore pinned on dedicated small
fixtures rather than on a random walk:
`tests/test_g191_040.py::test_all_up_window_divides_by_zero_down_volume_to_nan`
(5 strictly-increasing closes) and
`::test_zero_volume_down_bars_also_divide_by_zero_to_nan` (a flat down-bar
carrying `V = 0`), both also printed by `docs/measure_g191_040.py`.

NON-REDUNDANCY (disclosed, and partly unmeasured). This fork already ships
`g191_043` -- `SUM(SIGN(C-C1)*V, 6) / SUM(V, 6)` -- over the same two
buckets. Write `U` for the up-bucket sum, `D` for the strictly-down sum
and `F` for the flat-day sum over one window. Then
`G191_043 = (U - D) / (U + D + F)` and `G191_040 = 100 * U / (D + F)`.
With NO flat bars (`F = 0`) both are strictly increasing functions of the
single ratio `r = U/D` (`100r` and `(r-1)/(r+1)`), hence RANK-IDENTICAL:
Spearman `|rho| = 1` at equal `length`. The shipped defaults differ (26
vs 6) and real data does print flat closes (`F > 0`), which breaks the
single-ratio form, so the shipped pair is not a restatement by
construction -- but it is the nearest comparator in this package and the
launcher's Gate E comparator set (the engine's `compute_all` plus the
`ml_features` manifest) need not contain `G191_043_6` at all. Measured on
the 1,500-bar synthetic frame of `docs/measure_g191_040.py` (0 flat bars
on it, so `F = 0` holds exactly): Spearman `rho = 1.000000` against
`G191_043_26` over 1,474 overlapping bars -- the rank identity above,
confirmed -- and `rho = 0.451774` against the SHIPPED `G191_043_6`.
Real-data overlap against the engine's comparators is Gate E's, run by
the launcher.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_040(close, volume, length=None, offset=None, **kwargs):
    """Indicator: Up-Volume / Down-Volume Ratio (G191_040)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 26
    min_length = length + 1
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    # Calculate Result
    close_prior = close.shift(1)
    undefined = close_prior.isna() | close.isna()
    up_volume = volume.where(close > close_prior, 0.0).mask(undefined, np.nan)
    down_volume = volume.where(close <= close_prior, 0.0).mask(undefined, np.nan)

    numerator = up_volume.rolling(length, min_periods=length).sum()
    denominator = down_volume.rolling(length, min_periods=length).sum()
    result = (100 * numerator / denominator).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_040_{length}"
    result.category = "volume"

    return result


g191_040.__doc__ = \
"""Up-Volume / Down-Volume Ratio (G191_040)

Guotai Junan's (2017, "GTJA191") alpha `#40`, per issue #77. Splits each
bar's volume into an up-bucket (close above the prior close) and a
down-bucket (close at or below the prior close, so a flat day counts as
down), sums each bucket over a trailing window, and reports the up-sum as
a percentage of the down-sum: a running measure of how lopsided buying
pressure has been versus selling pressure, bounded below by 0 and
unbounded above. Full Gate A derivation, causality and scale-free
arguments are in the module source above; see docs/G191040Measured.md for
the measured numbers.

Calculation:
    Default Inputs:
        length=26
    C1          = DELAY(close, 1)
    up_volume   = volume where close > C1, else 0 (NaN at bar 0)
    down_volume = volume where close <= C1, else 0 (NaN at bar 0)
    G191_040    = 100 * SUM(up_volume, length) / SUM(down_volume, length)
                  inf -> NaN

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for both sums. Default: 26
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_040_{length}, a scale-free (dimensionless) column,
        bounded below by 0 (a sum of volume cannot be negative) and
        unbounded above. NaN for the first `length` bars (`min_length - 1`,
        26 at the shipped default), and wherever the down-volume sum over
        the whole window is exactly zero -- either every bar in the window
        is an up-day, or every non-up bar in it carries zero volume --
        leaving no down bucket to divide by. Also NaN for the `length + 1`
        bars whose window reads a bar of undefined direction (a NaN close
        makes both its own bar and the next one undefined).
"""
