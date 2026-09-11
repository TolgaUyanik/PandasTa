# -*- coding: utf-8 -*-
"""The shared ``zone()`` calculation behind ``pzo`` and ``vzo``.

PINEBI-1b.  Ported from TradingView's ``ta`` library, publication ``RA2vGpkA``,
line 315.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    zone(series float source, simple int length) =>
        float result = 100 * nz(ta.ema(math.sign(ta.change(close)) * source, length) / ta.ema(source, length))

ONE MODULE, NOT TWO COPIES.  Pine declares this as a private helper used by
both `pzo()` and `vzo()`, and it is kept as one here for the same reason
``PandasTa/CLAUDE.md`` gives for `fvg`: "Do not add a fourth copy: import the
function."  Two transcriptions of one recursion drift.

THE TRAP, pinned by the test module: the sign term reads **`close`**, not
`source`.  `vzo` passes `volume` as the source, so its numerator is
``ema(sign(change(close)) * volume)`` -- volume signed by the PRICE direction.
Reading `sign(change(source))` instead turns `vzo` into a function of volume's
own first difference, which is a different indicator that happens to look
plausible.
"""
from numpy import sign
from pandas_ta.overlap.ema import ema


def zone(close, source, length):
    """Pine's `zone()`: EMA of direction-signed source over EMA of source."""
    signed = sign(close.diff()) * source
    num = ema(signed, length=length)
    den = ema(source, length=length)
    if num is None or den is None:
        return None

    out = 100.0 * (num / den)

    # Pine's nz() maps na to 0, and that is right for the DIVISION guard: a
    # zero denominator (a flat all-zero volume window) is a real bar with no
    # zone reading, and Pine calls it 0.
    #
    # It is NOT right for the WARM-UP.  The first `length`-ish bars are NaN
    # because the EMA has not started, not because the zone is zero, and
    # zeroing them plants a synthetic reading on every one of them -- the
    # defect PINEBI-1e removed from `normalize`, where a flat window was
    # returning 0.5 on 17.7% of settled bars.  So the two cases are separated:
    # guard the division, leave the warm-up NaN.
    warm = num.isna() | den.isna()
    out = out.replace([float("inf"), float("-inf")], 0.0)
    out[(~warm) & out.isna()] = 0.0
    out[warm] = float("nan")
    return out
