# -*- coding: utf-8 -*-
"""5-day volume change -- Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#80`, per issue
#64. Source cited by the issue:

    #80: (V-V5)/V5*100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is taken
directly from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype").

GATE A -- DERIVATION. `V5` is GTJA191's own delayed-volume notation, the
same spelling the issue uses for `C5` (`g191_018`: `CLOSE/DELAY(CLOSE,5)`)
and `C6`/`C20` elsewhere in the report -- `V5 = DELAY(VOLUME, 5)`, i.e.
volume 5 bars ago, NOT a 5-bar moving average. Confirmed against the
prototype's own candidate function (`docs/issues/screen/ind_screen.py:426-427`,
`cand("g191_080", ...)`):

    def _(o, h, l, c, v): return 100 * sdiv(v - delay(v, 5), delay(v, 5))

-- `delay(x, n) = x.shift(n)` (`ind_screen.py:45`) and `sdiv(a, b) = (a /
b).replace([inf, -inf], nan)` (`ind_screen.py:41-42`), both read directly
off the prototype's own (unambiguous) module code, matching the issue's own
notation -- no disclosed ASSUMPTION needed. The `sdiv` guard is reused here
for the identical reason as `g191_076`/`g191_191`: a zero-volume bar 5 bars
back would otherwise make the ratio `+-inf` rather than a defined number.

CALCULATION, in the order computed below:
    v5       = VOLUME.shift(5)
    G191_080 = 100 * (VOLUME - v5) / v5, inf -> NaN

CAUSALITY. `v5[t]` reads `VOLUME[t-5]` only; the result at bar `t` reads
`VOLUME[t]` and `VOLUME[t-5]`, nothing past `t`. No rolling window is
involved -- a shift, a subtraction, a division and a multiplication by 100
-- so there is no `center=True` failure mode to mutate; the one way this chain can look ahead
is writing the result at the wrong bar, which `tests/test_g191_080.py`'s
write-shift mutant (`importlib` source read, `exec`'d in memory) proves is
caught, with the real module shown to leak 0 of its perturbation offsets.

SCALE-FREE. For ANY `k > 0`: `100 * (k*V - k*V5) / (k*V5) = 100 * (V - V5) /
V5` algebraically -- the `k` cancels inside the division itself, not merely
for a power-of-two multiplier. The column reads no price input at all, so a
close/high/low/open rescale cannot reach it. Measured on a synthetic frame:
volume x8/x64 land bit-identical (power-of-two multiplication is exact in
IEEE754, so the algebraic cancellation is also exact in float64); x10/x3.7
land within float64 rounding tolerance. Measured in the test file and
`docs/measure_g191_080.py`, not merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_080(volume, length=None, offset=None, **kwargs):
    """Indicator: 5-Day Volume Change (G191_080)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 5
    min_length = length + 1
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if volume is None:
        return

    # Calculate Result
    v5 = volume.shift(length)
    result = (100.0 * (volume - v5) / v5).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_080_{length}"
    result.category = "volume"

    return result


g191_080.__doc__ = \
"""5-Day Volume Change (G191_080)

Guotai Junan's (2017, "GTJA191") alpha `#80`, per issue #64. The percent
change of volume against its value `length` bars ago: `V5` in the source is
delayed volume (`VOLUME.shift(length)`), not a moving average. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191080Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=5
    v5       = volume.shift(length)
    G191_080 = 100 * (volume - v5) / v5, inf -> NaN

Args:
    volume (pd.Series): Series of 'volume's
    length (int): How many bars back `V5` reads. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_080_{length}, a scale-free (dimensionless) percent
        change of volume. NaN for the first `length` bars, and wherever
        volume `length` bars back is exactly zero.
"""
