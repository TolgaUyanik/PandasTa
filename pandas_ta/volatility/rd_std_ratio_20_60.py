# -*- coding: utf-8 -*-
"""Close's rolling stdev over its own 60-bar average -- issue #179
(RD-STD-RATIO-20-60). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:1lezs3n (2025-06-19)
https://www.reddit.com/r/algotrading/comments/1lezs3n/.

POSTER'S WORDS (tier 4, untested by the poster): "normalized_vol =
price_std / avg_volatility." Claimed use: detect a flat/range market
relative to its own recent volatility -- NOT independently tested here;
this port ships existence (causal, scale-free, reachable on real data),
not evidence that it predicts anything.

GATE A -- the issue's own formula, read literally (its own instruction:
"Gate A starts from the source formula, not the prototype"
`docs/issues/screen/ind_screen_r6.py`'s `rd_std_ratio_20_60`, which is
mathematically the same reading but is not what Gate A cites):

    normalized_vol = std(close, p) / mean(std(close, p), 3p)

with p=20 (the issue's own scale-free form, "p = 20"). `3p` is the issue's
own substitution, not a judgment call: p=20 gives a 60-bar average, which is
this candidate's own name, `rd_std_ratio_20_60`. `std` here is this fork's
own `pandas_ta.statistics.stdev` (pandas' rolling `.std()`, ddof=1 by
default) -- the poster's "price_std" is unspecified beyond "std", and the
screen prototype's own helper (`c.rolling(20).std()`, pandas default ddof=1)
confirms ddof=1 as the intended reading, not ddof=0. `mean` is a plain
rolling SMA, matching both the prototype's `mean()` helper
(`x.rolling(n).mean()`) and this fork's `pandas_ta.overlap.sma`. Division by
a zero 60-bar average stdev (e.g. a dead-flat market with zero variance for
60 consecutive bars) -> NaN, not inf: see the `replace` below.

NON-REDUNDANCY. The issue's own prototype measurement (below) puts this
column's nearest comparators at `BB_BWidth_Pctl` (0.8274), `CHOP` (0.7091)
and `BB_BWidth` (0.7001) -- all already-shipped volatility-regime columns
this fork carries (`pandas_ta.volatility.bbands`, `pandas_ta.volatility.chop`),
read here as evidence the new column sits in the same neighbourhood as
existing ones, not as evidence it restates one exactly (DISCLOSE_GAP, not
STRUCK, at the measured 0.8274).

CAUSALITY. `stdev(close, length)` at bar T is a plain trailing rolling
window ending AT T (`pandas.Series.rolling` with no `center` argument reads
only the current and PRIOR rows); `sma` of that series is the same kind of
trailing window one level up. Composing two causal trailing windows (stdev,
then a rolling mean of stdev) stays causal.
`tests/test_rd_std_ratio_20_60.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical regardless of what
the frame's tail past J is replaced with) and a look-ahead mutant
(`importlib`-read source, the stdev series shifted one bar toward the
future with `.shift(-1)` before the SMA is taken, `exec`'d in memory --
never a hand-written copy): the real module leaks 0 bars at every swept J;
the mutant is live and leaks at every one.

SCALE-FREE. For a positive price rescale by an exactly-representable factor
`k` (a power of two): pandas' rolling `.var()` computes a sum of squared
deviations from the window mean, divided by `(n - ddof)`; scaling every
element of a window by an exact `k` scales every deviation by exactly `k`
(subtraction of two exactly-k-scaled operands is itself exact for a
power-of-two `k`), so each squared deviation scales by exactly `k**2` and
their sum does too (summing exactly-scaled terms stays exactly scaled) --
`variance' = k**2 * variance` exactly, and `stdev' = sqrt(k**2 * variance) =
k * stdev` exactly, since IEEE-754 `sqrt` is correctly rounded and `k` being
a power of two means `k * round(sqrt(variance))` and `round(sqrt(k**2 *
variance))` are the same unique correctly-rounded value. `sma` of the
now-`k`-scaled stdev series is linear (`SMA(k*x) = k*SMA(x)` exactly, same
argument as the sum above), so the final ratio `(k*num)/(k*denom)` is
IEEE-754 division of two operands both scaled by the same exact `k`, which
returns a bit-identical quotient to the unscaled `num/denom` -- the same
cancellation `rd_range_contraction` (`pandas_ta/volatility/rd_range_contraction.py`)
relies on for its own ratio of two rolling means. This relies on `variance`
(`pandas_ta/statistics/variance.py`) computing `close.rolling(length,
min_periods=...).var(ddof)` -- a deviation-FROM-THE-MEAN reduction -- rather
than the naive `E[X**2] - E[X]**2` sum-of-squares form; the latter is the
form `avwap_z` (`pandas_ta/volume/avwap_z.py`) documents losing precision on
(catastrophic cancellation when the true variance is small relative to
price**2), so that risk does not apply to this module's stdev computation.
Measured bit-identical
under x8/x64 (max absolute difference 0.0), and within a tight tolerance
under the non-power-of-two x10/x3.7 rescale, in
`tests/test_rd_std_ratio_20_60.py` and `docs/measure_rd_std_ratio_20_60_cpu.py`
(see docs/RdStdRatio2060Measured.md for the measured numbers).

Prototype measured this on the screen (2026-10-25, issue #179, NOT re-run in
this session -- quoted, not re-measured). Gate E: max |rho| 0.8274 vs
`BB_BWidth_Pctl` (manifest, n = 391,907), top-5 per-frame max median 0.8332
-- DISCLOSE_GAP. Next comparators: `CHOP` 0.7091, `BB_BWidth` 0.7001. Stage-2
fork overlap (not Gate E): max |rho| 0.6675 vs `squeeze_pro:SQZPRO_OFF`, per-
frame max median 0.6714 -- not a restatement at the 0.90 line. This session's
own Gate E run is owed; see docs/RdStdRatio2060Measured.md.
"""
import numpy as np

from pandas_ta.overlap.sma import sma
from pandas_ta.statistics.stdev import stdev
from pandas_ta.utils import get_offset, verify_series


def rd_std_ratio_20_60(close, length=None, avg_length=None, offset=None, **kwargs):
    """Indicator: Close Stdev over its own Average Stdev (RD_STD_RATIO_20_60)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    avg_length = int(avg_length) if avg_length and avg_length > 0 else 60
    min_bars = length + avg_length - 1
    close = verify_series(close, min_bars)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    std_series = stdev(close, length=length)
    avg_std = sma(std_series, length=avg_length)
    if std_series is None or avg_std is None:
        return

    with np.errstate(invalid="ignore", divide="ignore"):
        out = (std_series / avg_std).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            out = out.ffill()
        elif method in ("bfill", "backfill"):
            out = out.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    out.name = f"RD_STD_RATIO_20_60_{length}_{avg_length}"
    out.category = "volatility"

    return out


rd_std_ratio_20_60.__doc__ = \
"""Close Stdev over its own Average Stdev (RD_STD_RATIO_20_60)

Close's rolling standard deviation, divided by a rolling average of that
same stdev series -- below 1 when the recent price is quieter than its own
longer-run volatility (a flat/range market), above 1 when it is noisier. A
Reddit crowd-talk definition (tier 4, untested by the poster), issue #179:
"normalized_vol = price_std / avg_volatility," claimed use is to detect a
flat/range market relative to its own recent volatility -- NOT independently
tested here; this port ships existence (causal, scale-free, reachable on
real data), not evidence it predicts anything.

See the module source above for the full source citation, the Gate A
derivation (why the divisor is a 60-bar average of the 20-bar stdev, per the
issue's own "p = 20" / "3p" substitution) and the scale-free argument.
docs/RdStdRatio2060Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1lezs3n
    (2025-06-19) https://www.reddit.com/r/algotrading/comments/1lezs3n/

Calculation:
    Default Inputs:
        length=20, avg_length=60
    STD        = pandas_ta.statistics.stdev(close, length)
    AVG_STD    = pandas_ta.overlap.sma(STD, avg_length)
    RD_STD_RATIO_20_60 = STD / AVG_STD
    (+-inf from a zero `avg_length`-bar average stdev -> NaN)

Args:
    close (pd.Series): Series of 'close's
    length (int): The stdev's own lookback. Default: 20
    avg_length (int): The average-of-stdev window in the denominator. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_STD_RATIO_20_60_{length}_{avg_length}, a scale-free
        (dimensionless) ratio, NaN for the first `length + avg_length - 2`
        bars (the combined warm-up of the stdev and its own average) and
        wherever the average stdev is exactly zero.
"""
