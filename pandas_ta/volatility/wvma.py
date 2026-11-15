# -*- coding: utf-8 -*-
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series

#: Alpha158's own five windows (qlib `Alpha158DL.get_feature_config`,
#: `WVMA$d` for `d` in 5, 10, 20, 30, 60) -- not this port's choice. See
#: docs/Alpha158Measured.md.
DEFAULT_LENGTHS = (5, 10, 20, 30, 60)


def wvma(close, volume, lengths=None, offset=None, **kwargs):
    """Indicator: Volume-Weighted Moving Average deviation (WVMA)"""
    # Validate Arguments
    lengths = DEFAULT_LENGTHS if lengths is None else lengths
    lengths = sorted(set(int(L) for L in lengths))
    if not lengths or lengths[0] < 2:
        raise ValueError(f"wvma: need at least one length >= 2; got {lengths}")
    max_len = lengths[-1]
    close = verify_series(close, max_len + 1)
    volume = verify_series(volume, max_len + 1)
    offset = get_offset(offset)

    if close is None or volume is None: return

    # Calculate Result: coefficient of variation of the volume-weighted
    # absolute return. `vwret` reads bar `t` and `t-1` only (the `.shift(1)`
    # in the return), so every rolling window below ends at the current bar.
    ret = (close / close.shift(1) - 1).abs()
    vwret = ret * volume

    data = {}
    for length in lengths:
        std = vwret.rolling(length).std()
        mean = vwret.rolling(length).mean()
        data[f"WVMA_{length}"] = std / (mean + 1e-12)
    df = DataFrame(data, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        if kwargs["fill_method"] == "ffill":
            df.ffill(inplace=True)
        elif kwargs["fill_method"] == "bfill":
            df.bfill(inplace=True)

    # Name and Categorize it
    tag = "-".join(str(L) for L in lengths)
    df.name = f"WVMA_{tag}"
    df.category = "volatility"

    return df


wvma.__doc__ = \
"""Volume-Weighted Moving Average deviation (WVMA)

qlib Alpha158's `WVMA$d`: the coefficient of variation of the
volume-weighted absolute return,
`Std(|close/Ref(close,1)-1| * volume, d) / (Mean(|close/Ref(close,1)-1| *
volume, d) + 1e-12)` -- how erratic volume-weighted price swings are over the
window, relative to their own average size. One column per window in
`lengths`, each named `WVMA_<d>`.

Scale-free: the `close/close.shift(1)` return ratio cancels any common
price-axis factor exactly, so this is bit-identical under a x8/x64 price
rescale and within 1e-9 under x10/x3.7. A volume rescale is NOT
bit-identical even at x8/x64 (measured max|diff| 6.66e-16) because the
`+1e-12` floor does not commute exactly with it; still well inside the
1e-9 bound used for all four volume-axis factors. See `tests/test_wvma.py`.

Categorised here (volatility) rather than volume: the shipped analogue is
`volvol` (`pandas_ta/volatility/volvol.py`), a std/mean dispersion ratio;
`VSUMD` (`pandas_ta/volume/vsumd.py`, also issue #34) is the one of this
trio computed from volume alone and lives in `volume` instead.

Source: Microsoft qlib, `qlib/contrib/data/loader.py`,
`Alpha158DL.get_feature_config` (fetched read-only from GitHub `main`,
2026-10-24; PandasTa issue #34). qlib is released under the MIT License
(public knowledge of the project's licensing; not re-verified by a live fetch
in this session -- web access was unavailable). This is an independent
implementation from the published formula, not a copy of qlib's source.

Calculation:
    Default Inputs:
        lengths=(5, 10, 20, 30, 60)
    ret = ABS(close / close.shift(1) - 1)
    vwret = ret * volume
    For each d in lengths:
        WVMA_d = STDEV(vwret, d) / (SMA(vwret, d) + 1e-12)

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    lengths (Sequence[int]): Trailing windows, each >= 2.
        Default: (5, 10, 20, 30, 60)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: One WVMA_<d> column per window in `lengths`.
"""
