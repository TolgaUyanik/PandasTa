# -*- coding: utf-8 -*-
"""6-Day Signed Volume (OBV Slope) -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#43`, per issue #69. Source cited by the issue:

    #43: SUM(C>C1 ? V : (C<C1 ? -V : 0), 6)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:357-359`):

    @cand("g191_043", "6-day signed volume (OBV slope)", G,
          "#43: SUM(C>C1 ? V : (C<C1 ? -V : 0), 6)", "/SUM(V,6)")
    def _(o, h, l, c, v): return sdiv(tsum(np.sign(delta(c, 1)) * v, 6), tsum(v, 6))

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including the window length and the issue's
own scale-free conversion ("/SUM(V,6)").

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1` denotes `C` delayed one bar, `DELAY(C, 1) = C.shift(1)`
  (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never a
  look-ahead.
* `C>C1 ? V : (C<C1 ? -V : 0)` is a per-bar ternary on the SIGN of the
  one-bar price change: `+V` on an up day, `-V` on a down day, `0` on a
  flat day (`C==C1`). `np.sign(delta(c, 1))` -- the prototype's own
  spelling -- returns exactly `+1`/`-1`/`0` for those three cases (and
  `NaN` where `delta` itself is `NaN`, bar 0), so `np.sign(delta(c, 1)) *
  v` reproduces the ternary exactly at every bar, no edge-case divergence.
  This fork's own `pandas_ta.utils.signed_series(close)` (used by
  `pandas_ta/volume/obv.py`'s OBV) computes the identical thing without
  `numpy`: `close.diff(1)` with `>0 -> 1`, `<0 -> -1`, bar 0 left as its
  `initial` (default `None`, i.e. `NaN` -- matching `np.sign(NaN) ==
  NaN`). Measured on a synthetic walk in `docs/measure_g191_043.py`:
  `signed_series(close) * volume` and `np.sign(close.diff(1)) * volume`
  agree bit-for-bit, NaN masks matching, including the `delta == 0`
  boundary pinned on a dedicated 5-bar frame in
  `tests/test_g191_043.py::test_signed_series_matches_an_explicit_sign_ternary_at_the_zero_boundary`.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum, `min_periods=n` by pandas' own default.
* `C` = close, `V` = volume. No other OHLCV field is read.

CALCULATION, in the order computed below (`length=6`):
    C1          = DELAY(C, 1)
    signed_vol  = SIGN(C - C1) * V      # NaN at bar 0, where C1 is undefined
    G191_043    = SUM(signed_vol, length) / SUM(V, length), inf -> NaN

CAUSALITY. `C1[t]` reads only `C[t-1]`. `signed_vol[t]` is a pointwise
function of `C[t]`, `C1[t]` and `V[t]` -- bars no newer than `t`.
`SUM(signed_vol, length)[t]` and `SUM(V, length)[t]` are both trailing
`length`-bar sums over the window `[t-length+1, t]`, every index `<= t`.
The final division reads only bar `t`'s two sums. Nothing in the chain
reads a bar newer than `t`. `tests/test_g191_043.py` proves this both by
future-perturbation (real module: 0 of N offsets leak, over a synthetic
walk rewritten from an offset onward) and by a mutant (`importlib` source
read, `exec`'d in memory, shown live different from the real module):
shifting the final rolling-sum write index `length` bars into the future.

WARM-UP. `C1` is undefined at bar 0 (no prior bar), so `signed_vol` is
undefined there too (`signed_series`'s own `NaN` at bar 0 propagates
through the multiplication by `V`). `SUM(signed_vol, length)`, a trailing
`length`-bar sum with `min_periods=length`, needs `length` CONSECUTIVE
valid `signed_vol` values ending at `t`, i.e. `t - length + 1 >= 1`, i.e.
`t >= length` -- `min_length = length + 1` bars of history (**7** at the
shipped default), enforced by `verify_series`. `SUM(V, length)` alone
would be ready one bar earlier (no dependency on `C1`), but the division
by it is still gated by the numerator's later warm-up.

SCALE-FREE. For ANY `k > 0`: scaling volume (`V -> k*V`) scales both sums
linearly (`SUM(signed_vol, length) -> k*SUM(signed_vol, length)` and
`SUM(V, length) -> k*SUM(V, length)`, since `signed_vol`'s `SIGN(...)`
factor is unitless and does not change), so the ratio
`(k*SUM(signed_vol,length))/(k*SUM(V,length)) = SUM(signed_vol,length)/
SUM(V,length)` is identical -- the `k` cancels EXACTLY, for ANY positive
`k`. Scaling price (`C -> k*C`) changes nothing: `SIGN(k*C - k*C1) =
SIGN(C - C1)` for any `k > 0` (scaling preserves the sign of a
difference), so `signed_vol` and both sums are unchanged. Measured on a
synthetic walk: VOLUME x8/x64 land bit-identical (power-of-two
multiplication is exact in IEEE754, so the algebraic cancellation is also
exact in float64), VOLUME x10/x3.7 land within float64 rounding tolerance,
and PRICE x8/x64/x10/x3.7 all land bit-identical (the sign ternary reads
only the SIGN of a price difference, never its magnitude). Measured in the
test file and `docs/measure_g191_043.py`, not merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, signed_series, verify_series


def g191_043(close, volume, length=None, offset=None, **kwargs):
    """Indicator: 6-Day Signed Volume / OBV Slope (G191_043)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 6
    min_length = length + 1
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    # Calculate Result
    signed_volume = signed_series(close) * volume
    numerator = signed_volume.rolling(length, min_periods=length).sum()
    denominator = volume.rolling(length, min_periods=length).sum()
    result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_043_{length}"
    result.category = "volume"

    return result


g191_043.__doc__ = \
"""6-Day Signed Volume / OBV Slope (G191_043)

Guotai Junan's (2017, "GTJA191") alpha `#43`, per issue #69. On an up day
(close above the prior close), the bar contributes `+volume`; on a down
day, `-volume`; on a flat day, `0`. Summed over a trailing window and
divided by the unsigned volume sum over the same window for a scale-free
result: a running measure of buying/selling pressure imbalance, the same
sign-ternary OBV uses but windowed and ratio-normalized instead of
cumulative. Full Gate A derivation, causality and scale-free arguments are
in the module source above; see docs/G191043Measured.md for the measured
numbers.

Calculation:
    Default Inputs:
        length=6
    C1          = DELAY(close, 1)
    signed_vol  = SIGN(close - C1) * volume
    G191_043    = SUM(signed_vol, length) / SUM(volume, length), inf -> NaN

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for both sums. Default: 6
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_043_{length}, a scale-free (dimensionless) column in
        [-1, 1] by construction (a sum of signed volume cannot exceed the
        sum of its own unsigned magnitude). NaN for the first `length`
        bars (`min_length - 1`, 6 at the shipped default), and wherever
        volume is exactly zero over the whole window.
"""
