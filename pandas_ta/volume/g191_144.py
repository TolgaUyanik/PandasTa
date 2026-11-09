# -*- coding: utf-8 -*-
"""Down-day illiquidity share -- Guotai Junan's (2017, "GTJA191", internal
quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#144`, per
issue #57. Source cited by the issue:

    #144: SUMIF(|C/C1-1|/AMOUNT, C<C1, 20) / COUNT(C<C1, 20)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (which is itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. `C1` is GTJA notation for the previous close,
`DELAY(C,1)` -- confirmed by every other alpha in the issue's own screening
registry that defines `C1` the same way (`docs/issues/screen/ind_screen.py`,
e.g. `#53: COUNT(C>C1,12)/12*100`, `#76: STD(|C/C1-1|/V,20) / MEAN(same,20)`).
`AMOUNT` is a daily traded-VALUE field (currency, not shares); daily OHLCV
here has no such field, so the issue's own parenthetical states the proxy
used: "AMOUNT -> TP*V" (typical price times volume). `SUMIF(X, cond, n)` is a
trailing `n`-bar sum of `X` restricted to bars where `cond` holds (0
elsewhere); `COUNT(cond, n)` is a trailing `n`-bar count of bars where `cond`
holds -- both read directly off the prototype's own unambiguous
implementations (`docs/issues/screen/ind_screen.py:54`,
`tsum(x.where(dn, 0.0), 20)` / `count(dn, 1).rolling(n).sum()`-equivalent).

Let `r = C/C1 - 1` (one-bar return) and `x = |r| / AMOUNT` (illiquidity: a
large move on thin traded value reads large). The raw formula's left side,
`SUMIF(x, C<C1, 20) / COUNT(C<C1, 20)`, is the AVERAGE illiquidity on down
days only, over the trailing 20 bars -- but `x` carries units of
`1 / (price * volume)`, so this average is NOT scale-free: it shrinks under
either a price or a volume rescale. The issue's own parenthetical states the
conversion applied before Gate E ever ran: "divided by the all-day mean of
|r|/AMOUNT over 20 bars" -- i.e. divide by `MEAN(x, 20)`, which carries the
SAME units and so cancels them in the ratio. The issue's own prototype
(`docs/issues/screen/ind_screen.py:485`) spells out the identical scale-free
form directly:

    x = sdiv(ret(c).abs(), tp(h, l, c) * v)
    dn = c < delay(c, 1)
    sdiv(sdiv(tsum(x.where(dn, 0.0), 20), count(dn, 20)), mean(x, 20))

so this port ships:

    G191_144 = [SUMIF(x, C<C1, length) / COUNT(C<C1, length)] / MEAN(x, length)
    where x = |C/C1 - 1| / (TP * V),  TP = (H+L+C)/3,  C1 = DELAY(C,1)

reading as: how much more (or less) illiquid down days have been, relative
to the bar's own trailing 20-bar average illiquidity. 1.0 means down days
were exactly as illiquid as the average day; > 1.0 means down days were
thinner-traded than average.

OPERATORS, each read directly off the prototype's own (unambiguous) module
docstring, the same source `g191_191` (issue #53) and `g191_026` (issue #56)
relied on for `MEAN`/`DELAY`:

* `DELAY(X, n)` = `X.shift(n)`, matching the prototype's own
  `delay(x, n): return x.shift(n)` -- a BACKWARD-looking shift (bar `t`
  reads bar `t-n`), never a look-ahead.
* `MEAN(X, n)` = a trailing `n`-bar rolling mean, `X.rolling(n).mean()`.
  Matches the prototype's own `mean(x, n): return x.rolling(n).mean()`.
* `H`, `L`, `C`, `V` = high, low, close, volume. `TP` = `(H+L+C)/3`, the
  prototype's own typical-price proxy for VWAP/AMOUNT
  (`tp(h, l, c): return (h + l + c) / 3`), used here as `AMOUNT = TP * V`.

WARM-UP, a disclosed decision this port had to make that the screening
prototype did not: bar 0 has no `C1` (`DELAY(C,1)` is undefined there), so
whether bar 0 is a "down day" is itself undefined, not merely false. Naively
coding `close < close.shift(1)` would read `False` there (pandas/numpy
compare `NaN` as `False`, not as `NaN`), silently treating an UNDEFINED bar
as a known "not a down day" and letting a contaminated value enter the very
first rolling window. This port masks bar 0 out of BOTH `SUMIF` and `COUNT`
explicitly (`np.where(prior_close.isna(), np.nan, ...)`), so the EARLIEST a
valid output can appear needs `length` bars with a DEFINED down/up status
(bars `1..length`), i.e. `length + 1` bars of history in total --
`min_length = length + 1`, enforced by `verify_series`. This is a NECESSARY
but not SUFFICIENT condition: if that first `length`-bar window happens to
contain zero down days, `down_avg` is `0/0` and the output stays NaN one
(or more) bars longer -- measured on both a small hand-derived frame
(`length=3`, extends by one bar) and the shipped default on a 1500-bar
synthetic frame (`length=20`, does not extend). See
docs/G191144Measured.md.

CALCULATION, in the order computed below (`length=20`):
    tp           = (H + L + C) / 3
    amount       = tp * V
    prior_close  = DELAY(C, 1)
    ret_abs      = |C / prior_close - 1|
    x            = ret_abs / amount, inf -> NaN
    down         = C < prior_close, NaN where prior_close is NaN (bar 0)
    sumif        = SUM(x where down else 0, length), NaN where any bar in
                   the window has undefined down-status
    count        = SUM(down as 0/1, length), same NaN rule
    down_avg     = sumif / count, inf -> NaN (no down day in the window)
    all_avg      = MEAN(x, length)
    G191_144     = down_avg / all_avg, inf -> NaN (all_avg == 0)

CAUSALITY. `tp[t]`, `amount[t]`, `ret_abs[t]`, `x[t]` and `down[t]` are each
pointwise in `H[t]`, `L[t]`, `C[t]`, `V[t]` and `C[t-1]` -- reading no bar
past `t`. `sumif[t]` and `count[t]` are trailing rolling aggregates of
`x`/`down` over `[t-length+1, t]`, again reading no bar past `t`; by
induction, bars no older than `t-length` on the `down`/`x` side, and no
older than `t-length-1` through the embedded `C[t-1]` reads. `all_avg[t]` is
a trailing rolling mean of `x[t-length+1..t]`, same bound. Nothing in the
chain is shifted forward. `tests/test_g191_144.py` proves this both by
future-perturbation and by two independent mutants (`importlib` source
read, `exec`'d in memory), each shown live (differs from the real module)
and then caught at every offset past the warm-up: shifting the final write
index `length` bars into the future, and replacing the backward `DELAY`
(`close.shift(1)`) with a FORWARD shift (`close.shift(-1)`) -- turning `C1`
itself into a look-ahead at the NEXT close rather than the previous one.

SCALE-FREE. Let `k > 0` rescale price (`H, L, C -> k*H, k*L, k*C`) and
`j > 0` rescale volume (`V -> j*V`), independently or together. `ret_abs` is
exactly invariant under a price rescale: `|k*C / (k*prior_close) - 1| =
|C / prior_close - 1|`, the `k` cancels inside the ratio before the `-1`;
it does not involve `V` at all, so a volume rescale leaves it untouched too.
`tp -> k*tp` (linearity), so `amount = tp * V -> k*j*amount`. Therefore
`x = ret_abs / amount -> x / (k*j)` under ANY positive price and/or volume
rescale. `down = C < prior_close` is a pure inequality between two
quantities both scaled by the SAME positive `k` (price only; volume plays
no part), so the comparison's truth value is unchanged under a price
rescale, and is untouched by a volume rescale (volume does not appear in
`down` at all) -- `sumif` and `count` are built only from `x` (which scales
uniformly by `1/(k*j)`) and this unchanged `down` mask, so `sumif -> sumif /
(k*j)` and `count` is unchanged. `down_avg = sumif / count -> down_avg /
(k*j)`. `all_avg = MEAN(x, length) -> all_avg / (k*j)`, the SAME factor. The
final ratio `down_avg / all_avg` therefore has `1/(k*j)` cancel EXACTLY,
leaving `G191_144` invariant under ANY positive price rescale, ANY positive
volume rescale, or both together. Measured on a synthetic frame: `x8`/`x64`
land bit-identical for price alone, volume alone, and both together
(power-of-two multiplication is exact in IEEE754, so the algebraic
cancellation is also exact in float64), while `x10`/`x3.7` come out within
float64 rounding tolerance. Measured in the test file and
`docs/measure_g191_144.py`, not merely asserted.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def g191_144(high, low, close, volume, length=None, offset=None, **kwargs):
    """Indicator: Down-Day Illiquidity Share (G191_144)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    min_length = length + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    # Calculate Result
    tp = (high + low + close) / 3.0
    amount = tp * volume
    prior_close = close.shift(1)
    ret_abs = (close / prior_close - 1.0).abs()
    x = (ret_abs / amount).replace([np.inf, -np.inf], np.nan)

    undefined = prior_close.isna()
    is_down = close < prior_close
    contribution = np.where(undefined, np.nan, np.where(is_down, x, 0.0))
    count_contribution = np.where(undefined, np.nan, is_down.astype(float))
    sumif = Series(contribution, index=close.index).rolling(
        length, min_periods=length).sum()
    count = Series(count_contribution, index=close.index).rolling(
        length, min_periods=length).sum()

    down_avg = (sumif / count).replace([np.inf, -np.inf], np.nan)
    all_avg = x.rolling(length, min_periods=length).mean()
    result = (down_avg / all_avg).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_144_{length}"
    result.category = "volume"

    return result


g191_144.__doc__ = \
"""Down-Day Illiquidity Share (G191_144)

Guotai Junan's (2017, "GTJA191") alpha `#144`, per issue #57. The average
illiquidity (absolute one-bar return per unit of traded value, `TP * V`) on
DOWN days only, over the trailing window, as a ratio to the bar's own
trailing all-day average illiquidity: 1.0 reads "down days were exactly as
illiquid as the average day"; above 1.0 reads "down days moved more per
unit of traded value than a typical day" (thinner-traded selling). Full
Gate A derivation, causality and scale-free arguments are in the module
source above; see docs/G191144Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=20
    tp          = (high + low + close) / 3
    amount      = tp * volume
    prior_close = DELAY(close, 1)
    ret_abs     = |close / prior_close - 1|
    x           = ret_abs / amount, inf -> NaN
    down        = close < prior_close (undefined, hence excluded, at bar 0)
    sumif       = SUM(x where down else 0, length)
    count       = SUM(down as 0/1, length)
    down_avg    = sumif / count, inf -> NaN
    all_avg     = MEAN(x, length)
    G191_144    = down_avg / all_avg, inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for SUMIF/COUNT/MEAN. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_144_{length}, a scale-free (dimensionless) ratio of two
        same-unit illiquidity averages. NaN for AT LEAST the first `length`
        bars (bar 0's undefined down-status pushes the structural warm-up
        to `length + 1` bars of input), and for any later bar whose
        trailing `length`-bar window happens to contain zero down days
        (0/0 in `down_avg`) -- measured: at `length=3` on a 6-bar
        hand-derived frame this extends the warm-up by one extra bar; at
        the shipped default (`length=20`) on a 1500-bar synthetic frame it
        does not, firing exactly at bar 20 (see docs/G191144Measured.md).
"""
