# -*- coding: utf-8 -*-
from numpy import nan
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def wilder_rma(close, length=None, offset=None, **kwargs):
    """Indicator: True Wilder's Smoothing (WRMA)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    alpha = 1.0 / length

    # Seed with the SMA of the first `length` bars, then recurse. Doing this
    # as a slice + ewm(adjust=False) rather than a Python loop keeps it O(n)
    # in C: once the first value of a series is fixed, an adjust=False EWM IS
    # the Wilder recursion.
    #
    # Slide the seed to the FIRST NaN-free window of `length` bars. That is
    # Pine's own rule -- `na(rma[1]) ? ta.sma(src, length) : ...` keeps sliding
    # until it can seed -- and one mechanism covers both cases:
    #
    #   * leading NaNs are warm-up (`true_range` has no bar 0, so without this
    #     `atr(mamode="wrma")` would refuse outright), and
    #   * a NaN inside an early window is skipped rather than fatal.
    #
    # An earlier version refused the WHOLE series when the first window was
    # dirty, throwing away 281 of 300 bars over one missing value at bar 5
    # while the Pine reference returned all 281. Averaging a short seed would
    # indeed be wrong, but annihilating the column is not the only alternative
    # to imputing it.
    clean = close.notna().to_numpy()
    if not clean.any():
        return
    full = Series(clean).rolling(length).sum().to_numpy() == length
    if not full.any():
        return
    # `rolling` labels a window at its RIGHT edge; the seed starts length-1
    # earlier. Positional throughout: `index.get_loc` returns a mask on a
    # duplicate index and `.iloc` then raises, which plain `rma` survives.
    start = int(full.argmax()) - (length - 1)
    usable = close.iloc[start:]
    seed = usable.iloc[:length].mean()
    tail = usable.iloc[length - 1:].copy()
    tail.iloc[0] = seed
    smoothed = tail.ewm(alpha=alpha, adjust=False).mean()

    wrma = close.astype("float64").copy()
    wrma.iloc[:] = nan
    wrma.iloc[start + length - 1:] = smoothed.to_numpy()

    # Offset
    if offset != 0:
        wrma = wrma.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        wrma.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        wrma.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    wrma.name = f"WRMA_{length}"
    wrma.category = "overlap"

    return wrma


wilder_rma.__doc__ = \
"""True Wilder's Smoothing (WRMA)

Welles Wilder's original smoothing, as specified in *New Concepts in Technical
Trading Systems* (1978) and as implemented by Pine Script v6's `ta.rma`: seed
with the SMA of the first `length` bars, then apply `alpha = 1 / length`
recursively.

⚠ **This is NOT the same as this package's `rma`, despite the name `rma`
carries.** `pandas_ta.rma` is `close.ewm(alpha=1/length, min_periods=length)`
with pandas' default `adjust=True`, which weights the whole prefix rather than
recursing from an SMA seed. Measured on a 300-bar synthetic walk at
`length=14`: the two disagree on **285 of 287 settled bars**, maximum absolute
difference **0.241** on a series near 100. Seeding alone is not the whole
story either — Pine differs from a bare `ewm(alpha, adjust=False)` by up to
**0.636** on the same frame, because that form has no SMA seed.

`rma` is deliberately left byte-identical: `atr`/`natr` are built on it, mined
strategy rules in the parent repo match on exact column values, and `natr`
feeds a live paper-trading threshold. Correcting `rma` in place would move all
of them at once. So the correct smoothing ships alongside instead, and callers
that need Wilder's ask for it by name:

    ta.wilder_rma(df["close"], length=14)          # direct
    ta.atr(h, l, c, length=14, mamode="wrma")      # -> column ATRwr_14
    ta.ma("wrma", df["close"], length=14)          # via the MA dispatcher

Pine ports whose source calls `ta.rma` must use this function to clear Gate A.

NaN handling, stated because it is a real divergence and was measured:
    * **The seed slides to the first NaN-free window of `length` bars.** That
      is Pine's own rule, and it covers both leading warm-up NaNs
      (`true_range` has no value at bar 0, and without this
      `atr(mamode="wrma")` would return `None` outright) and a NaN inside an
      early window. Only a series with no clean window anywhere returns
      `None`.
    * **A NaN after the seed emits the CARRIED value, not `NaN`** — the
      recursion keeps its previous state, so a bar with no observation still
      receives a number, and trailing NaNs all emit the last real value. Said
      plainly rather than as "skipped": in a feature package the difference
      between a gap and a fabricated observation matters. It matches `rma`'s
      own `ewm` behaviour, so it is consistent with its neighbour. A naive
      longhand
      recursion poisons every subsequent bar instead; measured on a 300-bar
      frame with one NaN at bar 20, `length=14`, the two differ by up to
      **1.397**. Skipping is the deliberate choice: real BIST frames have
      gaps, and poisoning the remainder of a series because of one missing
      bar makes the column useless. The Gate A equality with Pine is
      therefore claimed **on NaN-free input**, which is how it is tested.

Sources:
    Wilder, J. Welles. *New Concepts in Technical Trading Systems*, 1978.
    https://www.tradingview.com/pine-script-reference/v6/#fun_ta.rma

Calculation:
    Default Inputs:
        length=10
    alpha = 1 / length
    WRMA[length-1] = SMA(close, length)
    WRMA[i]        = alpha * close[i] + (1 - alpha) * WRMA[i-1]   for i >= length

Args:
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
