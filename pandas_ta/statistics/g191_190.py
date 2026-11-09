# -*- coding: utf-8 -*-
"""Above/Below Geometric-Mean Return Dispersion (20) -- Guotai Junan's
(2017, "GTJA191", internal quant report, read via the HKUDS/Vibe-Trading
copy, MIT) alpha `#190`, per issue #59. Source cited by the issue:

    #190: LOG((COUNT(r>g,20)-1)*SUMIF((r-g)^2, r<g, 20)
          / (COUNT(r<g,20)*SUMIF((r-g)^2, r>g, 20))),
          g = (C/C19)^(1/20)-1

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (which is itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. `r` is the ordinary one-bar simple return and `g` is
a 20-bar GEOMETRIC-MEAN daily return -- not the plain "nth root of the
total change", but literally what the issue's formula spells out: the
total return over the bars `t-19..t` (`C/C19`, a 19-bar backward ratio, so
20 closes wide), raised to the `1/20` power. (The `19`-bar lookback paired
with a `1/20` exponent is the issue's own formula, not a typo this port
silently "corrects" -- it is read literally.)

    r = C/DELAY(C,1) - 1                                  # one-bar return
    g = (C/DELAY(C,19))^(1/20) - 1                         # 20-bar geometric-mean return
    up = r > g                                             # above-average-return bars
    dn = r < g                                             # below-average-return bars
    e2 = (r-g)^2                                           # each bar's squared deviation from g
    num = (COUNT(up,20) - 1) * SUMIF(e2, dn, 20)
    den =  COUNT(dn,20)      * SUMIF(e2, up, 20)
    G191_190 = LOG(num/den)

Reading each term: `SUMIF(e2, dn, 20)` sums the squared deviation ONLY over
the bars in the trailing 20-bar window where `dn` (`r < g`) holds, zero
elsewhere -- the total squared dispersion contributed by the BELOW-average
days. `COUNT(up,20)` counts the ABOVE-average days in that same window. The
numerator is therefore "how many above-average days there were (less one,
a small-sample correction) times how much the below-average days
dispersed"; the denominator is the mirror image. The ratio of these two
cross-terms, logged, is a SIGNED, scale-free read on which side of the
window's own geometric mean return dispersed more, weighted by how often
the OTHER side occurred -- positive when the below-average days are the
quieter/rarer tail relative to the above-average ones, negative the other
way round.

The issue's own prototype (`docs/issues/screen/ind_screen.py:570-579`,
candidate `g191_190`) spells out the identical formula directly:

    r = ret(c)                                    # ret(c) = c/c.shift(1)-1, ind_screen.py:108
    g = (c / delay(c, 19)) ** (1 / 20) - 1
    up, dn = r > g, r < g
    e2 = (r - g) ** 2
    num = (count(up, 20) - 1) * tsum(e2.where(dn, 0.0), 20)
    den = count(dn, 20) * tsum(e2.where(up, 0.0), 20)
    return _fin(np.log(sdiv(num, den).where(lambda x: x > 0)))

No disclosed interpretation choice was needed for the formula itself -- the
issue's own string and the prototype agree exactly, including the `19`/`20`
asymmetry. This port ships the identical ratio, with the identical domain
guard (`LOG`'s argument is undefined for `<= 0`; the prototype already
masks that with `.where(lambda x: x > 0)` before `np.log`, `ind_screen.py:
579` -- this port applies the SAME guard, down to the same masking point,
not merely a generic inf-safety net).

OPERATORS, each read directly off the prototype's own (unambiguous) module
docstring, the same source `g191_098` (issue #58) and `g191_144` (issue
#57) relied on for the same operator family:

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift
  (bar `t` reads bar `t-n`), never a look-ahead.
* `COUNT(cond, n)` = `cond.astype(float).rolling(n).sum()`
  (`ind_screen.py:54`), the trailing `n`-bar count of a boolean condition.
* `SUMIF(x, cond, n)` has no single named operator in the prototype; it is
  built, as the prototype itself builds it, from `SUM` (`ind_screen.py:49`,
  `x.rolling(n).sum()`, aliased `tsum`) applied to `x` ZEROED wherever
  `cond` is false (`x.where(cond, 0.0)`) -- the trailing `n`-bar sum of `x`
  restricted to the bars where `cond` holds.
* `r` (one-bar return) = `ind_screen.py:108`'s `ret(c) = c/c.shift(1)-1`.
* `C` = close. The formula uses no other OHLCV field.

CALCULATION, in the order computed below (`length=20`; the geometric-mean
lookback is `length-1=19`, per the issue's own literal `C19`/`1/20` pairing,
so it is NOT a separate tunable -- it is fixed to `length-1`):
    r          = C / DELAY(C,1) - 1
    g          = (C / DELAY(C,length-1))^(1/length) - 1
    up, dn     = r > g, r < g
    e2         = (r-g)^2
    num        = (COUNT(up,length) - 1) * SUM(e2.where(dn,0), length)
    den        =  COUNT(dn,length)      * SUM(e2.where(up,0), length)
    G191_190   = LOG(num/den), undefined (NaN) wherever num/den <= 0 or den == 0

WARM-UP. `r[t]` needs `C[t-1]`, valid from `t >= 1`. `g[t]` needs
`C[t-(length-1)]`, valid from `t >= length-1` -- the binding constraint
(looser than `r`'s). `up[t]`/`dn[t]`/`e2[t]` are therefore only MEANINGFUL
from `t >= length-1` (pandas evaluates a comparison against a `NaN` `g[t]`
as plain `False`, so `up`/`dn` would otherwise be silently `False`, not
`NaN`, before that point -- a trap this port avoids explicitly, see below).
`COUNT`/`SUM` over a trailing `length`-bar window ending at `t` need EVERY
bar in `[t-length+1, t]` to be a meaningful one, i.e. `t-length+1 >=
length-1`, i.e. `t >= 2*length-2`. So the whole column is NaN for strictly
fewer than `2*length-1` bars of history; `min_length = 2*length-1`,
enforced by `verify_series` (39 at the shipped default).

This port masks `up`/`dn` to `NaN` (not `False`/`0.0`) wherever `g` itself
is `NaN`, THEN rolls `COUNT`/`SUM` with `min_periods=length` -- so a window
touching even one pre-warm-up bar comes out `NaN` (pandas' rolling
`min_periods` demands that many NON-NULL observations in the window),
rather than silently treating an undefined bar as "not up, not dn, zero
contribution" the way the prototype's raw `np.where`-free boolean
comparisons would if run on a shorter frame. The prototype itself never
hits this edge (Gate E's harness only ever calls it on frames far longer
than the warm-up), so this is a disclosed hardening, not an observed
behaviour change.

CAUSALITY. `r[t]` reads `C[t]` and `C[t-1]`. `g[t]` reads `C[t]` and
`C[t-(length-1)]`. `up[t]`, `dn[t]`, `e2[t]` are pure functions of `r[t]`
and `g[t]` -- bars no newer than `t`. `COUNT`/`SUM` at `t` read the window
`[t-length+1, t]`, every index `<= t`. `num[t]`, `den[t]` and the final
`LOG` combine only these -- nothing in the chain reads a bar newer than
`t`. `tests/test_g191_190.py` proves this both by future-perturbation and
by two independent mutants (`importlib` source read, `exec`'d in memory),
each shown live (differs from the real module) and then caught at every
offset past the warm-up: shifting the final write index `length` bars into
the future, and replacing the backward `DELAY` in `g` (`close.shift(length
- 1)`) with a FORWARD shift (`close.shift(-(length-1))`).

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). `r = C/DELAY(C,
1) - 1` is EXACTLY invariant: `(k*C)/(k*DELAY(C,1)) - 1 = C/DELAY(C,1) - 1`,
the `k` cancels inside the ratio before any arithmetic on it runs, for ANY
`k > 0` -- not merely a power-of-two special case. `g` is invariant by the
identical argument: `((k*C)/(k*DELAY(C,length-1)))^(1/length) - 1 =
(C/DELAY(C,length-1))^(1/length) - 1`. Since `r` and `g` are both exactly
invariant, every term built from them (`up`, `dn`, `e2`, `COUNT`, `SUM`,
`num`, `den`, their ratio, and its `LOG`) is untouched by the rescale --
the whole column is scale-free BY CONSTRUCTION (it is built entirely from
return RATIOS, never from a price level), not merely algebraically
invariant after cancellation. Measured on a synthetic frame: `x8`/`x64`
land bit-identical (power-of-two multiplication is exact in IEEE754, so
the already-exact algebraic invariance carries through exactly in
float64), while `x10`/`x3.7` come out within float64 rounding tolerance
(the scalar multiply itself rounds, not the cancellation). Measured in the
test file and `docs/measure_g191_190.py`, not merely asserted.
"""
import numpy as np
import pandas as pd

from pandas_ta.utils import get_offset, verify_series


def g191_190(close, length=None, offset=None, **kwargs):
    """Indicator: Above/Below Geometric-Mean Return Dispersion (G191_190)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    g_lookback = length - 1
    min_length = 2 * length - 1
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    r = close / close.shift(1) - 1.0
    g = (close / close.shift(g_lookback)) ** (1.0 / length) - 1.0
    valid = g.notna()

    up = (r > g).astype(float).where(valid)
    dn = (r < g).astype(float).where(valid)
    e2 = (r - g) ** 2

    e2_dn = e2.where(dn == 1.0, 0.0).where(valid)
    e2_up = e2.where(up == 1.0, 0.0).where(valid)

    count_up = up.rolling(length, min_periods=length).sum()
    count_dn = dn.rolling(length, min_periods=length).sum()
    sumif_dn = e2_dn.rolling(length, min_periods=length).sum()
    sumif_up = e2_up.rolling(length, min_periods=length).sum()

    num = (count_up - 1.0) * sumif_dn
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = (num / (count_dn * sumif_up)).replace([np.inf, -np.inf], np.nan)
        result = np.log(ratio.where(ratio > 0))
    result = pd.Series(result, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_190_{length}"
    result.category = "statistics"

    return result


g191_190.__doc__ = \
"""Above/Below Geometric-Mean Return Dispersion (G191_190)

Guotai Junan's (2017, "GTJA191") alpha `#190`, per issue #59. Splits a
trailing 20-bar window into days whose one-bar return beat the window's own
20-bar geometric-mean return and days that fell short, then compares how
much each side's returns dispersed around that geometric mean, weighted by
how often the OTHER side occurred, and takes the log of the ratio. Full
Gate A derivation, causality and scale-free arguments are in the module
source above; see docs/G191190Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=20 (geometric-mean lookback fixed to length-1=19, per the
        issue's own formula, not a separate tunable)
    r        = close / DELAY(close,1) - 1
    g        = (close / DELAY(close,length-1))^(1/length) - 1
    up, dn   = r > g, r < g
    e2       = (r-g)^2
    num      = (COUNT(up,length) - 1) * SUM(e2 where dn, length)
    den      =  COUNT(dn,length)      * SUM(e2 where up, length)
    G191_190 = LOG(num/den), NaN wherever num/den <= 0 or undefined

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the return split, the count and the
        sum-if terms. The geometric-mean lookback is fixed to `length - 1`.
        Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_190_{length}, a scale-free (dimensionless, signed) log
        ratio, built entirely from return ratios (never a price level). NaN
        for the first `2 * length - 2` bars (the geometric-mean lookback's
        own warm-up folded into the rolling count/sum windows), plus
        wherever the ratio inside the log is non-positive or its
        denominator is zero.
"""
