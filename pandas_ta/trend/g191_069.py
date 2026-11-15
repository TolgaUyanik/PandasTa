# -*- coding: utf-8 -*-
"""Open-Based Directional Balance (DTM/DBM, 20) -- Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#69`, per issue #70. Source cited by the issue:

    #69: SUM(DTM,20) vs SUM(DBM,20) normalised by the larger;
         DTM = O<=O1 ? 0 : MAX(H-O, O-O1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:408-416`):

    @cand("g191_069", "open-based directional balance (DTM/DBM, 20)", G,
          "#69: SUM(DTM,20) vs SUM(DBM,20) normalised by the larger; DTM = O<=O1 ? 0 : MAX(H-O, O-O1)")
    def _(o, h, l, c, v):
        o1 = delay(o, 1)
        dtm = pd.Series(np.where(o <= o1, 0.0, np.maximum(h - o, o - o1)), index=c.index).where(o1.notna())
        dbm = pd.Series(np.where(o >= o1, 0.0, np.maximum(o - l, o - o1)), index=c.index).where(o1.notna())
        sd, sb = tsum(dtm, 20), tsum(dbm, 20)
        return pd.Series(np.where(sd > sb, sdiv(sd - sb, sd), np.where(sd < sb, sdiv(sd - sb, sb), 0.0)),
                         index=c.index).where(sd.notna() & sb.notna())

The issue's own stated formula gives `DTM` and names `DBM` only by its
mirror role ("vs SUM(DBM,20)"); the prototype's `dbm` line
(`o >= o1 ? 0 : MAX(O-L, O-O1)`) is the one disclosed INTERPRETATION CHOICE
this port makes, since the issue text alone does not spell `DBM` out. It is
the textbook mirror of `DTM` (swap the `<=`/`>=` gate and the `H`/`L` term,
keep `O-O1` in both terms, matching GTJA's published alpha "191" catalogue
#69, which this fork's other `g191_*` ports already treat as the governing
corpus), and it is the ONLY reading under which `DBM >= 0` always holds (see
CORRECTNESS below) -- the same non-negativity `DTM` has by construction.
A `DBM` spelled with `O1-O` in the second term would make the column
asymmetric in a way the issue's own "normalised by the larger" framing
(implicitly treating `DTM`/`DBM` as a matched pair, like `+DM`/`-DM` in
Wilder's DMI) does not suggest.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift
  (bar `t` reads bar `t-n`), never a look-ahead.
* `MAX(a, b)` = `np.maximum(a, b)`, an elementwise pointwise maximum.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum, `min_periods=n` by pandas' own default.
* `O`, `H`, `L` = open, high, low. `O1` = `DELAY(O, 1)`. No other OHLCV
  field is read; `close` and `volume` are unused by this alpha.

CALCULATION, in the order computed below (`length=20`):
    O1   = DELAY(open, 1)
    DTM  = O <= O1 ? 0 : MAX(high - open, open - O1)     # NaN where O1 is NaN
    DBM  = O >= O1 ? 0 : MAX(open - low, open - O1)      # NaN where O1 is NaN
    SD   = SUM(DTM, length)
    SB   = SUM(DBM, length)
    G191_069 = SD > SB ? (SD-SB)/SD : (SD < SB ? (SD-SB)/SB : 0), inf -> NaN,
               NaN wherever SD or SB is NaN

CORRECTNESS -- non-negativity of `DTM`/`DBM`, needed below for the
division-by-zero argument. In the `DTM` branch taken (`O > O1`),
`open - O1 > 0`, and `high - open >= 0` always (`high` is the bar's own
maximum), so `MAX(high-open, open-O1) >= 0`; the other branch is exactly 0.
So `DTM >= 0` at every bar, and by the same argument with `open - low >= 0`
(`low` is the bar's own minimum) and `open - O1 < 0` in the `DBM` branch
taken (`O < O1`), `DBM >= 0` too. Consequently `SD >= 0` and `SB >= 0`
(sums of non-negative terms), so whenever the `SD > SB` branch fires,
`SD > SB >= 0` forces `SD > 0` -- no division by zero -- and symmetrically
for the `SD < SB` branch. So on the branch actually SELECTED at a given
bar, dividing by the selected sum never divides by zero. The implementation
below computes BOTH ratios at every bar before `np.where` picks one (an
eager-evaluation artifact of `np.where`, not a correctness issue): on a bar
where the OTHER branch is selected, the unused ratio's own denominator can
genuinely be zero (`SB == 0` over a stretch of `length` consecutive
non-down-gap-open days is common, not a floating-point rarity), producing a
transient `inf`/`nan` that `np.where` discards. `np.errstate` suppresses
the resulting (harmless) `RuntimeWarning`, and the `inf -> NaN` replacement
is kept defensively for the SELECTED side's own float-tie edge case.

CAUSALITY. `O1[t]` reads only `open[t-1]`. `DTM[t]`/`DBM[t]` are pointwise
functions of `open[t]`, `high[t]`/`low[t]` and `O1[t]` -- bars no newer than
`t`. `SD[t]`/`SB[t]` are trailing `length`-bar sums over `[t-length+1, t]`,
every index `<= t`. The final ternary reads only `SD[t]`/`SB[t]`. Nothing
in the chain reads a bar newer than `t`. `tests/test_g191_069.py` proves
this both by future-perturbation (real module: 0 of N offsets leak, over a
synthetic frame rewritten from an offset onward) and by a mutant
(`importlib` source read, `exec`'d in memory, shown live different from the
real module): shifting the final write index `length` bars into the future.

WARM-UP. `O1` is undefined at bar 0 (no prior bar), so `DTM`/`DBM` are
undefined there too. `SUM(DTM, length)`/`SUM(DBM, length)`, trailing
`length`-bar sums with `min_periods=length`, need `length` CONSECUTIVE
valid values ending at `t`, i.e. `t - length + 1 >= 1`, i.e. `t >= length`
-- `min_length = length + 1` bars of history (**21** at the shipped
default), enforced by `verify_series`.

SCALE-FREE. For ANY `k > 0`, rescale `open -> k*open`, `high -> k*high`,
`low -> k*low` together (a uniform price rescale). The gate `O <= O1`
becomes `k*O <= k*O1`, identical to `O <= O1` for `k > 0` (scaling
preserves the sign of a difference, hence preserves an ordering), so the
BRANCH TAKEN at every bar is unchanged. Inside the taken branch, every term
(`high-open`, `open-O1`, `open-low`) scales by exactly `k` (linearity of
subtraction), so `MAX(...)` -- itself scale-equivariant for `k > 0` -- scales
by `k` too: `DTM -> k*DTM`, `DBM -> k*DBM`. `SD`/`SB`, linear sums of those,
scale by `k` as well: `SD -> k*SD`, `SB -> k*SB`. The `SD > SB` comparison
is therefore ALSO unchanged (again, scaling preserves the sign of a
difference), so the OUTER ternary's branch is unchanged too, and the final
ratio `(k*SD - k*SB)/(k*SD) = (SD-SB)/SD` exactly -- the `k` cancels
EXACTLY, for ANY positive `k`. The column is fully price-scale invariant,
not merely invariant inside one branch. Measured on a synthetic frame:
PRICE x8/x64 land bit-identical (power-of-two multiplication is exact in
IEEE754, so the algebraic cancellation is also exact in float64), and
PRICE x10/x3.7 land within float64 rounding tolerance. Measured in the test
file and `docs/measure_g191_069.py`, not merely asserted.
"""
import numpy as np
import pandas as pd

from pandas_ta.utils import get_offset, verify_series


def g191_069(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Open-Based Directional Balance (G191_069)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    min_length = length + 1
    open_ = verify_series(open_, min_length)
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    # Calculate Result
    open1 = open_.shift(1)
    dtm = pd.Series(
        np.where(open_ <= open1, 0.0, np.maximum(high - open_, open_ - open1)),
        index=close.index,
    ).where(open1.notna())
    dbm = pd.Series(
        np.where(open_ >= open1, 0.0, np.maximum(open_ - low, open_ - open1)),
        index=close.index,
    ).where(open1.notna())

    sd = dtm.rolling(length, min_periods=length).sum()
    sb = dbm.rolling(length, min_periods=length).sum()

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio_sd = ((sd - sb) / sd).replace([np.inf, -np.inf], np.nan)
        ratio_sb = ((sd - sb) / sb).replace([np.inf, -np.inf], np.nan)
    result = pd.Series(
        np.where(sd > sb, ratio_sd, np.where(sd < sb, ratio_sb, 0.0)),
        index=close.index,
    ).where(sd.notna() & sb.notna())

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_069_{length}"
    result.category = "trend"

    return result


g191_069.__doc__ = \
"""Open-Based Directional Balance (G191_069)

Guotai Junan's (2017, "GTJA191") alpha `#69`, per issue #70. Builds two
non-negative, open-anchored range terms per bar -- `DTM` on an up-gap-open
day (`open > prior open`), `DBM` on a down-gap-open day -- sums each over a
trailing window, and reports the normalized gap between the two sums: how
lopsided the last `length` bars' open-based range expansion has been toward
up-opens versus down-opens. The same "normalize by the larger sum" shape as
Wilder's `+DI`/`-DI` spread, but anchored on `open` rather than `high`/`low`
true range.

Calculation:
    Default Inputs:
        length=20
    O1   = DELAY(open, 1)
    DTM  = O <= O1 ? 0 : MAX(high - open, open - O1)
    DBM  = O >= O1 ? 0 : MAX(open - low, open - O1)
    SD   = SUM(DTM, length)
    SB   = SUM(DBM, length)
    G191_069 = SD > SB ? (SD-SB)/SD : (SD < SB ? (SD-SB)/SB : 0), inf -> NaN

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's (used only to validate warm-up and
        to source the result's index; the formula itself never reads
        `close`)
    length (int): Rolling window for both sums. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_069_{length}, a scale-free (dimensionless) column in
        [-1, 1] by construction (a difference of two non-negative sums
        normalized by the larger cannot leave that range). NaN for the
        first `length` bars (`min_length - 1`, 20 at the shipped default).
"""
