# -*- coding: utf-8 -*-
import numpy as np
from numpy import log as npLog
from pandas import Series
from pandas_ta.utils import get_offset, verify_series

SYMBOLS = (-1.0, 0.0, 1.0)


def entlz(close, length=None, base=None, offset=None, **kwargs):
    """Indicator: Entropy of sign-encoded returns (ENTLZ), plug-in estimator"""
    # Validate Arguments
    length = int(length) if length and int(length) > 1 else 20
    base = float(base) if base and base > 0 else 2.0
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Encode each bar-to-bar return as one of three symbols: up (+1), down
    # (-1), flat (0). sign(k * x) == sign(x) for any k > 0, so this encoding
    # -- and everything built on it -- is invariant to any positive rescaling
    # of close, not merely a power of two.
    returns = close.diff()
    symbol = np.sign(returns)
    valid = symbol.notna()

    # Plug-in Shannon entropy of the symbol distribution over the trailing
    # `length` returns: bar T reads returns T-length+1 .. T, never a future
    # one. Range [0, log(3, base)]: 0 when one symbol dominates the window,
    # maximal when all three are equally frequent.
    log_base = npLog(base)
    h = np.zeros(len(close))
    nan_mask = np.zeros(len(close), dtype=bool)
    for s in SYMBOLS:
        indicator = (symbol == s).astype(float)
        indicator[~valid] = np.nan
        freq = indicator.rolling(length).mean().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            term = np.where(freq > 0, -freq * npLog(freq) / log_base, 0.0)
        h += term
        nan_mask |= np.isnan(freq)
    h[nan_mask] = np.nan

    entropy = Series(h, index=close.index)

    # Offset
    if offset != 0:
        entropy = entropy.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        entropy.fillna(kwargs["fillna"], inplace=True)

    # Name & Category
    entropy.name = f"ENTLZ_{length}"
    entropy.category = "statistics"

    return entropy


entlz.__doc__ = \
"""Entropy of sign-encoded returns (ENTLZ)

AFML ch. 18 "Entropy Features" encodes returns as a symbol sequence (sign,
or k quantile bins) and estimates its entropy over a rolling window; low
entropy means a more predictable sequence. This port encodes each bar's
return by its SIGN (up / down / flat) and estimates the entropy of that
3-symbol alphabet with the PLUG-IN estimator: the Shannon entropy of the
observed symbol frequencies in the trailing window. PandasTa issue #11.

Decisions made here (the issue leaves them open):

* Encoding: sign, not k quantile bins. Quantile bins need a boundary fit on
  past data only, which is a second causality surface for no benefit this
  port's scope needs; sign has none, and it is the encoding the issue's
  "scale-free by construction" line describes.
* Estimator: plug-in, not Lempel-Ziv or Kontoyiannis. The issue states
  plug-in is simplest and LZ needs a longer window; LZ is not shipped here.
* Window: `length=20`, an unexamined default matching this fork's other
  short-lookback rolling statistics (momentum defaults cluster at 10-14);
  not tuned or measured against another choice.

This is NOT `pandas_ta.statistics.entropy` (`ENTP`), which is the Shannon
entropy of the price LEVEL's share of a rolling window
(`p = close / close.rolling(n).sum()`) -- a different object entirely, not
a function of returns at all.

Scale-free by construction, and more strongly than the usual x8/x64 check:
`sign(k * x) == sign(x)` for any `k > 0`, exactly, so every input to the
entropy calculation -- and the column itself -- is unchanged by ANY
positive rescaling of `close`, not only a power of two. See
`docs/EntlzMeasured.md` for the measured confirmation.

Sources:
    Lopez de Prado, Advances in Financial Machine Learning (2018), ch. 18
    "Entropy Features" (plug-in, Lempel-Ziv, Kontoyiannis estimators)

Calculation:
    Default Inputs:
        length=20, base=2

    r = close.diff()
    symbol = SIGN(r)                      in {-1, 0, +1}
    freq_s = mean(symbol == s, length)     for each s in {-1, 0, +1}
    ENTLZ = SUM(-freq_s * log(freq_s, base))   (0 * log(0) := 0)

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window of returns. Default: 20
    base (float): Logarithmic base. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: ENTLZ_{length}, bounded in [0, log(3, base)]
"""
