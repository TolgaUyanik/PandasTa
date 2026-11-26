# -*- coding: utf-8 -*-
"""Volume-weighted imbalance oscillator (10) -- Reddit (tier 4, ResearchIntel
kb/reddit.db), per issue #173: r/algotrading rd:algotrading:1c261v8
(2024-04-12, https://www.reddit.com/r/algotrading/comments/1c261v8/). The
issue cites the formula directly, not a script, so there is no source line
number -- Gate A reads the formula from the issue's own statement (its own
instruction: "Gate A starts from the source formula, not the prototype"),
not from the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_vwio_10`, which is mathematically the same reading but is not what
Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster): "buys = volume *
(close > open)` `sells = volume * (close < open)` `VWIO = EMA(buys - sells,
10) / EMA(volume, 10)". Claimed use: predominant buying vs selling pressure,
sign used as entry confirmation -- NOT independently tested here. This port
ships existence (the column is causal, scale-free and reachable on real
data), not evidence that the sign confirms entries.

GATE A -- the issue's own formula:

    buys  = volume IF close > open ELSE 0
    sells = volume IF close < open ELSE 0
    RD_VWIO_10 = EMA(buys - sells, 10) / EMA(volume, 10)

read per-bar as `buys - sells == volume * sign(close - open)` (0 on a tie,
`close == open`): a doji contributes 0 to the imbalance, matching both
`close > open` and `close < open` evaluating False in the poster's own
pseudocode.

"EMA" in the poster's pseudocode is a Reddit comment's name for a standard
recursion, not a script with a committed implementation -- there is no single
"the" EMA to transcribe. This port reads it as this fork's own
`pandas_ta.overlap.ema` (SMA-seeded warm-up of `length - 1` NaN bars, then the
recursive EMA), the same reading `pzo`/`vzo` take for their own "EMA of a
signed source over EMA of the source" shape (`pandas_ta/momentum/_zone.py`).
That reading matters for Gate D: a plain `pandas.Series.ewm(adjust=False)`
with no SMA seed (the screen prototype's own reading) starts emitting from
bar 0 with no warm-up NaN at all, so EVERY bar would be non-NaN and the
"0 < fires < n" scale-free guard could not distinguish a constant column from
a real one on a frame without its own NaNs. `docs/measure_rd_vwio_10.py`
measures the two readings against each other: identical after the warm-up
bars, to float tolerance.

The "(10)" in the issue's own title fixes the window, so `length` is a
parameter with that default, not a hard constant -- this fork's convention
for a fixed-suffix port (`osap_retskew_21`, `rd_wick_pressure_10`).

NON-REDUNDANCY WITH `vzo` (this fork's other EMA-of-signed-volume ratio,
`pandas_ta/volume/vzo.py`). `vzo` signs volume by `sign(close.diff())` -- the
direction close moved from the PRIOR bar's close, an inter-bar comparison.
This port signs volume by `sign(close - open)` -- the direction the SAME
bar's own body ran, an intrabar comparison. The two read different pairs of
prices (prior close vs. same bar) through the same EMA-ratio shape, and the
issue's own stage-2 fork-overlap screen (scale-free `Category` outputs at
defaults, 12 frames) reads this column against `imi:IMI_14` at its overlap
max (0.6546), not against `vzo`.

CAUSALITY. `buys`/`sells` at bar T read only `open[T]`, `close[T]` and
`volume[T]` -- no other bar. The EMA recursion (both the SMA seed and the
subsequent recursive step) reads only bars `<= T`. Nothing in the formula
shifts an index toward the future. `tests/test_rd_vwio_10.py` proves this
with a future-perturbation probe (bars before a perturbation point J stay
bit-identical) and a mutant that shifts the final ratio `.shift(-1)` (reading
one bar ahead) before returning it.

SCALE-FREE. `buys`/`sells`/`imbalance` are built from `volume` alone, gated
by the SIGN of `close - open` -- in EXACT real-number arithmetic this
comparison is invariant to any POSITIVE rescale of `open` and `close`
together, since `(open*k)` and `(close*k)` keep the same order as `open` and
`close` for `k > 0`. In FLOATING-POINT arithmetic this is not a universal
guarantee: a non-power-of-two `k` rounds `open*k` and `close*k`
independently, so a pair sitting within a few ULPs of each other could in
principle have its comparison flipped by that rounding. What is actually
MEASURED, on the frame `tests/test_rd_vwio_10.py` builds: bit-identical
under x8, x64, x10 AND x3.7 price rescales (`docs/measure_rd_vwio_10.py`),
which is stronger than most of this fork's other price/volume ratios
(`rd_wick_pressure_10`, `rd_corr_c_obv_20`), whose denominators are
themselves price-built and only match to float tolerance (not bit-identity)
at a non-power-of-two factor -- but this is a measured fact about the tested
frame and factors, not a proof that no input could ever flip a comparison.
A volume rescale by `k` scales `buys`, `sells`,
`imbalance` and the `EMA(volume, length)` denominator all by exactly `k` (EMA
is linear: `EMA(k*x) = k*EMA(x)`), so the ratio is unchanged -- bit-identical
at x8/x64, within float tolerance at x10/x3.7 (each scaled operand carries
its own last-bit rounding). `tests/test_rd_vwio_10.py` /
`docs/measure_rd_vwio_10.py` measure both separately.
"""
import numpy as np

from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def rd_vwio_10(open_, close, volume, length=None, offset=None, **kwargs):
    """Indicator: Volume-Weighted Imbalance Oscillator (RD_VWIO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    open_ = verify_series(open_, length)
    close = verify_series(close, length)
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if open_ is None or close is None or volume is None:
        return

    # Calculate Result
    buys = volume.where(close > open_, 0.0)
    sells = volume.where(close < open_, 0.0)
    imbalance = buys - sells

    num = ema(imbalance, length=length)
    den = ema(volume, length=length)
    if num is None or den is None:
        return

    out = (num / den).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = f"RD_VWIO_{length}"
    out.category = "volume"

    return out


rd_vwio_10.__doc__ = \
"""Volume-Weighted Imbalance Oscillator (RD_VWIO)

The EMA of volume signed by the direction of the SAME bar's own body
(`close` vs. `open`), divided by the EMA of volume itself -- a smoothed read
of "what share of recent volume traded on bullish-bodied bars". A Reddit
crowd-talk definition (tier 4, untested by the poster, issue #173): "buys =
volume * (close > open), sells = volume * (close < open), VWIO = EMA(buys -
sells, 10) / EMA(volume, 10)". Claimed use: predominant buying vs selling
pressure, sign used as entry confirmation -- NOT independently tested here.
See the module source above for the full source citation, the Gate A
derivation (including which concrete "EMA" this reads the poster's pseudocode
as) and the non-redundancy argument against this fork's other EMA-of-signed-
volume ratio, `vzo` (`sign(close.diff())` vs. this column's
`sign(close - open)`). docs/RdVwio10Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1c261v8
    (2024-04-12) https://www.reddit.com/r/algotrading/comments/1c261v8/

Calculation:
    Default Inputs:
        length=10
    buys       = volume IF close > open ELSE 0
    sells      = volume IF close < open ELSE 0
    imbalance  = buys - sells
    RD_VWIO    = EMA(imbalance, length) / EMA(volume, length)

Args:
    open_ (pd.Series): Series of 'open's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The EMA period. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_VWIO_<length>, roughly bounded on [-1, 1] (an EMA ratio of a
        signed volume to itself; not exactly bounded since the EMA weights
        differ from a simple trailing sum). NaN for the first `length - 1`
        bars (the EMA warm-up) and wherever the window's EMA of volume is
        exactly 0.
"""
