# -*- coding: utf-8 -*-
"""20-Day Sum Of Open-Down Moves (DBM) -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#93`, per issue #62. Source cited by the issue:

    #93: SUM(O>=O1 ? 0 : MAX(O-L, O-O1), 20)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. `O1` is GTJA notation for the previous bar's open,
`DELAY(O,1)` -- the same `X1 = DELAY(X,1)` convention every other alpha in
the issue's own screening registry uses (e.g. `#53: COUNT(C>C1,12)/12*100`
uses `C1` for `DELAY(C,1)`). The ternary reads: on a day the open did NOT
fall from the prior day's open (`O >= O1`), there is no "open-down move",
so the day contributes `0`; on a day the open DID fall (`O < O1`), the day
contributes `MAX(O-L, O-O1)` -- the larger of two nonnegative-in-the-usual-
case distances: how far the open sits above the day's own low (`O-L`,
`>= 0` since a bar's low is by definition `<= ` its open), and how far the
open fell from the prior open (`O-O1`, `< 0` in this branch, since `O < O1`
here). `O-L` in fact ALWAYS wins this particular `MAX` under ordinary OHLC
consistency (`L <= O` at every bar, by definition): `O-O1` can only exceed
`O-L` when `O1 < L`, but the branch itself already requires `O < O1`, so
`O1 < L <= O < O1` would have to hold simultaneously -- a contradiction.
So within the branch, `MAX(O-L, O-O1)` collapses exactly to `O-L`, and the
`O-O1` term never changes the OUTPUT, only (via the `O>=O1` gate) which
bars get `0` vs. `O-L`. This is measured, not merely argued algebraically:
`python docs/measure_g191_093.py` confirms `O-L` is the selected term at
every down-branch bar on a 1,500-bar synthetic OHLC frame. The ternary's
second branch therefore reads as "how far the open sat above today's low,
on days the open gapped down" -- summed over the trailing 20 bars, it is a
running tally of downside-gap-day intraday range, zero-filled on days the
open did not gap down. The issue's own prototype
(`docs/issues/screen/ind_screen.py:438-442`, candidate `g191_093`) spells
out the identical formula directly, including the issue's own scale-free
conversion ("/close"):

    @cand("g191_093", "20-day sum of open-down moves (DBM)", G,
          "#93: SUM(O>=O1 ? 0 : MAX(O-L, O-O1), 20)", "/close")
    def _(o, h, l, c, v):
        o1 = delay(o, 1)
        return tsum(pd.Series(np.where(o >= o1, 0.0, np.maximum(o - l, o - o1)),
                               index=c.index).where(o1.notna()), 20) / c

No disclosed interpretation choice was needed for the formula itself -- the
issue's own string and the prototype agree exactly, including the window
length and the scale-free conversion. The prototype additionally masks bar
0 (where `O1` is undefined) to `NaN` with an explicit `.where(o1.notna())`,
and this port keeps that same explicit mask. On the CURRENT arithmetic the
mask is not load-bearing -- `down_move[0] = np.maximum(O[0]-L[0], NaN)` is
already `NaN` (`np.maximum` propagates `NaN`, unlike `np.fmax`), so bar 0
reads `NaN` either way, measured on both the masked and an unmasked variant
(`python docs/measure_g191_093.py`). The mask is kept anyway as a
documentation device and a guard against a future rewrite of `down_move`
that stops relying on `np.maximum`'s NaN-propagation (e.g. a fill applied
upstream) silently turning bar 0 into a real, wrong number instead of
flagging it.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift (bar
  `t` reads bar `t-n`), never a look-ahead.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum.
* `MAX(a, b)` = elementwise `np.maximum(a, b)` -- a POINTWISE maximum of
  two series at each bar, not a rolling-window maximum (`TSMAX`, a
  different, unused operator in the same registry).
* `O`, `L` = open, low. No other OHLCV field is read.

CALCULATION, in the order computed below (`length=20`):
    O1           = DELAY(O, 1)
    down_move    = MAX(O-L, O-O1)
    contribution = O >= O1 ? 0 : down_move, NaN where O1 is undefined (bar 0)
    DBM          = SUM(contribution, length)
    G191_093     = DBM / C

CAUSALITY. `O1[t]` reads only `O[t-1]`. `down_move[t]` reads `O[t]`,
`L[t]` and `O1[t]` (itself only `O[t-1]`) -- bars no newer than `t`.
`contribution[t]` is a pure function of `O[t]`, `O1[t]` and `down_move[t]`
-- still only bars `<= t`. `DBM[t]` is a trailing `length`-bar sum of
`contribution`, reading the window `[t-length+1, t]`, every index `<= t`.
The final division by `C[t]` reads only bar `t`. Nothing in the chain
reads a bar newer than `t`. `tests/test_g191_093.py` proves this both by
future-perturbation (real module: 0 of N offsets leak, across OHLC inputs
rewritten jointly from an offset onward) and by two mutants (`importlib`
source read, `exec`'d in memory, each shown live different from the real
module): shifting the final rolling-sum write index `length` bars into the
future, and flipping the backward `DELAY(O,1)` into a FORWARD shift
(`open_.shift(-1)`) -- turning the previous-open reference into a
look-ahead at the NEXT open. The forward-DELAY mutant needs a DEDICATED
deterministic construction, not the same random future-perturbation sweep
the write-shift mutant uses: since `MAX(O-L, O-O1)` always collapses to
`O-L` (above), the DELAY direction only ever changes the OUTPUT through
the `O>=O1` branch GATE, a binary choice that can coincidentally agree
between the base and perturbed series at any one random offset -- measured
on the write-shift sweep's own 34 offsets, this coincidence hid the
forward-DELAY leak at 13 of them (`python docs/measure_g191_093.py`), so
the test instead builds a strictly increasing `open` series (gate always
False on the unperturbed data) and perturbs only the suffix to flip that
one gate deterministically.

WARM-UP. `O1` is undefined at bar 0 (no prior bar), valid from `t >= 1`.
`contribution` is therefore only meaningful from `t >= 1` as well (masked
to `NaN` at bar 0, not silently read as "no down move"). `DBM`, a trailing
`length`-bar sum, needs `length` CONSECUTIVE meaningful `contribution`
values ending at `t`, i.e. `t - length + 1 >= 1`, i.e. `t >= length` --
`min_length = length + 1` bars of history (**21** at the shipped default),
enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`open, low, close -> k*open,
k*low, k*close`). `O1 = DELAY(O,1)` is linear (a shift carries no
arithmetic), so it scales to `k*O1`. The comparison `O >= O1` is UNCHANGED
by a positive rescale (multiplying both sides of an inequality by the same
positive `k` preserves its direction), so the branch taken at every bar is
identical before and after the rescale. `O-L` and `O-O1` each scale to
`k*(O-L)` and `k*(O-O1)` (both linear in the rescaled inputs), so
`MAX(k*(O-L), k*(O-O1)) = k*MAX(O-L, O-O1)` for any `k > 0` (scaling a pair
by a positive constant scales their maximum by that same constant).
`contribution` therefore scales to `k*contribution` at every bar (the `0`
branch scales trivially, `k*0=0`). `DBM`, a plain linear sum, scales to
`k*DBM`. The final division `DBM/C` therefore scales to `(k*DBM)/(k*C) =
DBM/C` -- the `k` cancels EXACTLY. The whole column is scale-free BY
CONSTRUCTION for a positive rescale of price. Measured on a synthetic
frame: PRICE x8/x64 land bit-identical (power-of-two multiplication is
exact in IEEE754, so the scaled computation retraces the exact same
floating-point operations up to an exact exponent shift), while x10/x3.7
come out within float64 rounding tolerance (the rolling-sum and division
arithmetic itself rounds differently at a non-power-of-two multiplier,
even though the true mathematical ratio is identical). Measured in the
test file and `docs/measure_g191_093.py`, not merely asserted.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def g191_093(open_, low, close, length=None, offset=None, **kwargs):
    """Indicator: 20-Day Sum Of Open-Down Moves (G191_093)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    min_length = length + 1
    open_ = verify_series(open_, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if open_ is None or low is None or close is None:
        return

    # Calculate Result
    prior_open = open_.shift(1)
    undefined = prior_open.isna()
    down_move = np.maximum(open_ - low, open_ - prior_open)
    contribution = np.where(
        undefined, np.nan, np.where(open_ >= prior_open, 0.0, down_move)
    )
    dbm = Series(contribution, index=close.index).rolling(
        length, min_periods=length).sum()
    result = dbm / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_093_{length}"
    result.category = "momentum"

    return result


g191_093.__doc__ = \
"""20-Day Sum Of Open-Down Moves (G191_093)

Guotai Junan's (2017, "GTJA191") alpha `#93`, per issue #62. On days the
open did not fall from the prior day's open, contributes zero; on days it
did, contributes the larger of (open minus low) and (open minus prior
open) -- in the ordinary case this is the distance from the open down to
the day's own low. Summed over a trailing window and divided by close to
make the result scale-free: a running tally of downside-gap-day intraday
range. Full Gate A derivation, causality and scale-free arguments are in
the module source above; see docs/G191093Measured.md for the measured
numbers.

Calculation:
    Default Inputs:
        length=20
    O1           = DELAY(open, 1)
    down_move    = MAX(open-low, open-O1)
    contribution = open >= O1 ? 0 : down_move, NaN where O1 is undefined
    DBM          = SUM(contribution, length)
    G191_093     = DBM / close

Args:
    open_ (pd.Series): Series of 'open's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the sum. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_093_{length}, a scale-free (dimensionless) column,
        non-negative in the typical case (constructed from distances that
        are usually nonnegative, see the module docstring). NaN for the
        first `length` bars (`min_length - 1`, 20 at the shipped default).
"""
