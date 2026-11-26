# -*- coding: utf-8 -*-
"""Upper wick in ATR5 units -- Reddit (tier 4, ResearchIntel kb/reddit.db),
per issue #172: r/Daytrading rd:Daytrading:1rjq7kd (2026-03-03,
https://www.reddit.com/r/Daytrading/comments/1rjq7kd/). The issue cites the
formula directly, not a script, so there is no source line number -- Gate A
reads the formula from the issue's own statement (its own instruction:
"Gate A starts from the source formula, not the prototype"), not from the
screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_uwick_atr`,
which is mathematically the same reading but is not what Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster): "I divide parameters like
the MAEs for both sides, candle range, body and wick sizes by my chosen ATR
period." Claimed use: size stops/buffers in ATR terms -- NOT independently
tested here; this port ships existence (the column is causal, scale-free and
reachable on real data), not evidence that it sizes anything correctly. The
MAE part of the poster's words needs forward bars (a label, not a feature)
and is out of scope for this port.

GATE A -- the issue's own formula:

    (high - max(open, close)) / ATR(5)

read per-bar as:
    upper_wick = high - MAX(open, close)
    RD_UWICK_ATR = upper_wick / ATR(5)

The poster's words name "ATR" without saying which smoothing -- the screen
prototype's own disclosed choice (`atr_wilder`, Wilder's recursive mean,
`ewm(alpha=1/5, adjust=False)`) is the only concrete answer on the record for
what "my chosen ATR period" computes, so this port carries that choice
through via this fork's own shipped Wilder smoothing (`mamode="wrma"`,
`pandas_ta.overlap.wilder_rma`, SMA-seeded rather than the prototype's
raw-`ewm`-seeded recursion -- the two converge but are not bit-identical in
the first few bars after warm-up) rather than re-implementing the recursion
inline, per CLAUDE.md's "import a helper from its own module" rule. The
period "5" is the formula's own constant (`ATR(5)`), not a title suffix, so
it is kept as a `length` parameter with that default rather than hard-coded
into the name, this fork's convention for a fixed-period port whose title
carries no numeric suffix (`rd_body_atr`, `rd_lwick_atr` in the same
candidate screen use the same pattern).

CAUSALITY. Bar T's output reads only open/high/low/close at `T` and the
Wilder-smoothed true range over `[..., T]`, nothing shifted toward the
future. `tests/test_rd_uwick_atr.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical) and a mutant that
appends `.shift(-1)` to the final ratio (reading one bar ahead).

SCALE-FREE. `upper_wick` is a difference of two like-for-like price terms on
the same bar; the Wilder-smoothed true range is built the same way bar by
bar (`true_range`'s own max of three like-for-like price differences,
recursively averaged). Multiplying open/high/low/close by one positive
constant `k` scales both the numerator and every term feeding the
denominator by exactly `k`, leaving the ratio unchanged. Under an exact
power-of-two rescale (x8, x64) this is bit-identical, since `(a*k)/(b*k)` on
exactly-representable scaled operands is a correctly-rounded division equal
in every bit to `a/b` -- CONDITIONAL on no bar in the series having an exact
`high == low` tie: `true_range`'s own `non_zero_range` floors a tie at a
FIXED (unscaled) machine epsilon rather than `k * epsilon`, which would break
bit-identity on such a bar (see Decision 4 in docs/RdUwickAtrMeasured.md;
not observed on the measured synthetic frames, whose continuous-valued
wicks essentially never tie exactly). Under a non-power-of-two rescale (x10,
x3.7) each scaled operand carries its own last-bit rounding, so the ratio
can move by a tiny relative amount -- measured, not merely argued, in
`tests/test_rd_uwick_atr.py` / `docs/measure_rd_uwick_atr.py`.
"""
import numpy as np

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def rd_uwick_atr(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Upper Wick in ATR Units (RD_UWICK_ATR)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 5
    open_ = verify_series(open_, length)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    # Calculate Result
    upper_wick = high - np.maximum(open_, close)
    atr5 = atr(high=high, low=low, close=close, length=length, mamode="wrma")

    out = (upper_wick / atr5).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = "RD_UWICK_ATR"
    out.category = "candles"

    return out


rd_uwick_atr.__doc__ = \
"""Upper Wick in ATR Units (RD_UWICK_ATR)

The current bar's upper wick (`high` minus the body top), divided by a
Wilder-smoothed Average True Range -- a scale-free read of how far price
pushed above the body relative to recent volatility. A Reddit crowd-talk
definition (tier 4, untested by the poster, issue #172): "I divide
parameters like the MAEs for both sides, candle range, body and wick sizes
by my chosen ATR period" -- claimed use is sizing stops/buffers in ATR
terms. NOT independently tested here either way. See the module source above
for the full source citation, Gate A derivation and the causality/scale-free
argument; docs/RdUwickAtrMeasured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1rjq7kd
    (2026-03-03) https://www.reddit.com/r/Daytrading/comments/1rjq7kd/

Calculation:
    Default Inputs:
        length=5
    ATR = Wilder-smoothed Average True Range (this fork's atr(mamode="wrma"))
    upper_wick = high - MAX(open, close)
    RD_UWICK_ATR = upper_wick / ATR(length)

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The ATR period. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_UWICK_ATR, a scale-free (ratio of like-for-like price
        differences) column. NaN during the ATR warm-up. `true_range`'s own
        `non_zero_range` floors an exactly-equal high/low pair at machine
        epsilon rather than leaving it 0 (this fork's crypto-data defence),
        so a fully flat run reads 0 / epsilon = 0.0, not NaN; the inf-guard
        in this module exists for the in-principle exact-zero-ATR case that
        floor otherwise forecloses.
"""
