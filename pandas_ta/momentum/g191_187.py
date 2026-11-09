# -*- coding: utf-8 -*-
"""20-Day Sum Of Open-Up Moves (DTM) -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#187`, per issue #65. Source cited by the issue:

    #187: SUM(O<=O1 ? 0 : MAX(H-O, O-O1), 20)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own
named copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula
below is derived from the issue's own stated text (itself a quote of the
GTJA191 report), per the issue's own instruction ("Gate A starts from the
source formula, not the prototype").

GATE A -- DERIVATION. `O1` is GTJA notation for the previous bar's open,
`DELAY(O,1)` -- the same `X1 = DELAY(X,1)` convention every other alpha in
the issue's own screening registry uses (e.g. `#93: SUM(O>=O1 ? 0 :
MAX(O-L, O-O1), 20)`, already shipped as `g191_093`, uses `O1` for
`DELAY(O,1)` identically). The ternary reads: on a day the open did NOT
rise above the prior day's open (`O <= O1`), there is no "open-up move",
so the day contributes `0`; on a day it DID rise (`O > O1`), the day
contributes `MAX(H-O, O-O1)` -- the larger of two nonnegative-in-the-
usual-case distances: how far the day's high ran above its own open
(`H-O`, `>= 0` since a bar's high is by definition `>= ` its open), and
how far the open rose from the prior open (`O-O1`, `> 0` in this branch,
since `O > O1` here).

Unlike its mirror alpha `#93` (`g191_093`), this `MAX` does **not**
collapse to a single term: in `#93`'s down-branch `O < O1`, the `O-O1`
term is negative while `O-L` is nonnegative, so `O-L` always wins by
construction. Here BOTH terms are nonnegative in the branch (`H-O >= 0`
always; `O-O1 > 0` in this branch), so which one is larger depends on the
data -- a genuine elementwise comparison, not a disguised constant.
Measured, not merely argued: on a 1,500-bar synthetic OHLC frame
(`python docs/measure_g191_187.py`), `H-O` wins at some up-branch bars and
`O-O1` wins at others (counts printed by the script) -- neither term
dominates structurally. The up-branch therefore reads as "the larger of
today's own intraday run-up above the open, or the size of the opening
gap up" -- summed over the trailing 20 bars, zero-filled on days the open
did not gap/run up. The issue's own prototype
(`docs/issues/screen/ind_screen.py:554-557`, candidate `g191_187`) spells
out the identical formula directly, including the issue's own scale-free
conversion ("/close"):

    @cand("g191_187", "20-day sum of open-up moves (DTM)", G,
          "#187: SUM(O<=O1 ? 0 : MAX(H-O, O-O1), 20)", "/close")
    def _(o, h, l, c, v):
        o1 = delay(o, 1)
        return tsum(pd.Series(np.where(o <= o1, 0.0, np.maximum(h - o, o - o1)),
                               index=c.index).where(o1.notna()), 20) / c

No disclosed interpretation choice was needed for the formula itself --
the issue's own string and the prototype agree exactly, including the
window length and the scale-free conversion. The prototype additionally
masks bar 0 (where `O1` is undefined) to `NaN` with an explicit
`.where(o1.notna())`, and this port keeps that same explicit mask. On the
CURRENT arithmetic the mask is not load-bearing -- `up_move[0] =
np.maximum(H[0]-O[0], NaN)` is already `NaN` (`np.maximum` propagates
`NaN`, unlike `np.fmax`), so bar 0 reads `NaN` either way, measured on
both the masked and an unmasked variant (`python docs/measure_g191_187.py`).
The mask is kept anyway as a documentation device and a guard against a
future rewrite of `up_move` that stops relying on `np.maximum`'s
NaN-propagation silently turning bar 0 into a real, wrong number instead
of flagging it.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift (bar
  `t` reads bar `t-n`), never a look-ahead.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum.
* `MAX(a, b)` = elementwise `np.maximum(a, b)` -- a POINTWISE maximum of
  two series at each bar, not a rolling-window maximum (`TSMAX`, a
  different, unused operator in the same registry).
* `O`, `H` = open, high. No other OHLCV field is read.

CALCULATION, in the order computed below (`length=20`):
    O1           = DELAY(O, 1)
    up_move      = MAX(H-O, O-O1)
    contribution = O <= O1 ? 0 : up_move, NaN where O1 is undefined (bar 0)
    DTM          = SUM(contribution, length)
    G191_187     = DTM / C

CAUSALITY. `O1[t]` reads only `O[t-1]`. `up_move[t]` reads `H[t]`, `O[t]`
and `O1[t]` (itself only `O[t-1]`) -- bars no newer than `t`.
`contribution[t]` is a pure function of `O[t]`, `O1[t]` and `up_move[t]`
-- still only bars `<= t`. `DTM[t]` is a trailing `length`-bar sum of
`contribution`, reading the window `[t-length+1, t]`, every index `<= t`.
The final division by `C[t]` reads only bar `t`. Nothing in the chain
reads a bar newer than `t`. `tests/test_g191_187.py` proves this both by
future-perturbation (real module: 0 of N offsets leak, across OHLC inputs
rewritten jointly from an offset onward) and by a mutant (`importlib`
source read, `exec`'d in memory, shown live different from the real
module): shifting the final rolling-sum write index `length` bars into
the future. Because `MAX(H-O, O-O1)` does NOT collapse to one term here
(unlike `#93`), flipping the backward `DELAY(O,1)` into a FORWARD shift
changes the `O-O1` term's OWN magnitude directly (not merely a branch
gate), so the same random future-perturbation sweep catches that mutant
too -- measured leak counts for both mutants are in
`docs/measure_g191_187.py`'s output and `tests/test_g191_187.py`.

WARM-UP. `O1` is undefined at bar 0 (no prior bar), valid from `t >= 1`.
`contribution` is therefore only meaningful from `t >= 1` as well (masked
to `NaN` at bar 0, not silently read as "no up move"). `DTM`, a trailing
`length`-bar sum, needs `length` CONSECUTIVE meaningful `contribution`
values ending at `t`, i.e. `t - length + 1 >= 1`, i.e. `t >= length` --
`min_length = length + 1` bars of history (**21** at the shipped default),
enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`open, high, close -> k*open,
k*high, k*close`). `O1 = DELAY(O,1)` is linear (a shift carries no
arithmetic), so it scales to `k*O1`. The comparison `O <= O1` is
UNCHANGED by a positive rescale (multiplying both sides of an inequality
by the same positive `k` preserves its direction), so the branch taken at
every bar is identical before and after the rescale. `H-O` and `O-O1`
each scale to `k*(H-O)` and `k*(O-O1)` (both linear in the rescaled
inputs), so `MAX(k*(H-O), k*(O-O1)) = k*MAX(H-O, O-O1)` for any `k > 0`
(scaling a pair by a positive constant scales their maximum by that same
constant). `contribution` therefore scales to `k*contribution` at every
bar (the `0` branch scales trivially, `k*0=0`). `DTM`, a plain linear
sum, scales to `k*DTM`. The final division `DTM/C` therefore scales to
`(k*DTM)/(k*C) = DTM/C` -- the `k` cancels EXACTLY. The whole column is
scale-free BY CONSTRUCTION for a positive rescale of price. Measured on a
synthetic frame: PRICE x8/x64 land bit-identical (power-of-two
multiplication is exact in IEEE754, so the scaled computation retraces
the exact same floating-point operations up to an exact exponent shift),
while x10/x3.7 come out within float64 rounding tolerance (the
rolling-sum and division arithmetic itself rounds differently at a
non-power-of-two multiplier, even though the true mathematical ratio is
identical). Measured in the test file and `docs/measure_g191_187.py`, not
merely asserted.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def g191_187(open_, high, close, length=None, offset=None, **kwargs):
    """Indicator: 20-Day Sum Of Open-Up Moves (G191_187)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    min_length = length + 1
    open_ = verify_series(open_, min_length)
    high = verify_series(high, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if open_ is None or high is None or close is None:
        return

    # Calculate Result
    prior_open = open_.shift(1)
    undefined = prior_open.isna()
    up_move = np.maximum(high - open_, open_ - prior_open)
    contribution = np.where(
        undefined, np.nan, np.where(open_ <= prior_open, 0.0, up_move)
    )
    dtm = Series(contribution, index=close.index).rolling(
        length, min_periods=length).sum()
    result = dtm / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_187_{length}"
    result.category = "momentum"

    return result


g191_187.__doc__ = \
"""20-Day Sum Of Open-Up Moves (G191_187)

Guotai Junan's (2017, "GTJA191") alpha `#187`, per issue #65. On days the
open did not rise above the prior day's open, contributes zero; on days
it did, contributes the larger of (high minus open) and (open minus prior
open) -- the bigger of the day's own intraday run-up or the size of the
opening gap up. Summed over a trailing window and divided by close to
make the result scale-free. The mirror alpha `#93` (`g191_093`, down-move
version) collapses its MAX to a single term under OHLC consistency; this
one does not -- both terms are genuinely compared. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191187Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=20
    O1           = DELAY(open, 1)
    up_move      = MAX(high-open, open-O1)
    contribution = open <= O1 ? 0 : up_move, NaN where O1 is undefined
    DTM          = SUM(contribution, length)
    G191_187     = DTM / close

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the sum. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_187_{length}, a scale-free (dimensionless) column,
        non-negative in the typical case (constructed from distances that
        are usually nonnegative, see the module docstring). NaN for the
        first `length` bars (`min_length - 1`, 20 at the shipped default).
"""
