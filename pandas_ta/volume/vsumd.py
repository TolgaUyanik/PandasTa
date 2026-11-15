# -*- coding: utf-8 -*-
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series

#: Alpha158's own five windows (qlib `Alpha158DL.get_feature_config`,
#: `VSUMD$d` for `d` in 5, 10, 20, 30, 60) -- not this port's choice. See
#: docs/Alpha158Measured.md.
DEFAULT_LENGTHS = (5, 10, 20, 30, 60)


def vsumd(volume, lengths=None, offset=None, **kwargs):
    """Indicator: Volume Sum Delta (VSUMD)"""
    # Validate Arguments
    lengths = DEFAULT_LENGTHS if lengths is None else lengths
    lengths = sorted(set(int(L) for L in lengths))
    if not lengths or lengths[0] < 2:
        raise ValueError(f"vsumd: need at least one length >= 2; got {lengths}")
    max_len = lengths[-1]
    volume = verify_series(volume, max_len + 1)
    offset = get_offset(offset)

    if volume is None: return

    # Calculate Result: an RSI-style balance of volume increases vs
    # decreases, in [-1, 1]. `dv` reads bar `t` and `t-1` only (the
    # `.diff()`), so every rolling window below ends at the current bar.
    dv = volume.diff()
    up = dv.clip(lower=0)
    down = (-dv).clip(lower=0)
    absdv = dv.abs()

    data = {}
    for length in lengths:
        num = up.rolling(length).sum() - down.rolling(length).sum()
        den = absdv.rolling(length).sum() + 1e-12
        data[f"VSUMD_{length}"] = num / den
    df = DataFrame(data, index=volume.index)

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
    df.name = f"VSUMD_{tag}"
    df.category = "volume"

    return df


vsumd.__doc__ = \
"""Volume Sum Delta (VSUMD)

qlib Alpha158's `VSUMD$d`:
`(Sum(Greater(volume-Ref(volume,1),0),d) -
Sum(Greater(Ref(volume,1)-volume,0),d)) /
(Sum(Abs(volume-Ref(volume,1)),d) + 1e-12)` -- a Cutler's-RSI-style balance
of volume increases against volume decreases, bounded in [-1, 1]. One
column per window in `lengths`, each named `VSUMD_<d>`.

Note: `Sum(Greater(dv,0),d) - Sum(Greater(-dv,0),d)` telescopes algebraically
to `Sum(dv,d) = volume[t] - volume[t-d]`, but this port computes the two
rolling sums of qlib's formula directly (not the telescoped form), to stay
line-by-line checkable against the published expression. `test_vsumd.py`
checks both forms agree.

Depends only on `volume` -- the one of this trio (with `WVMA`,
`pandas_ta/volatility/wvma.py`, and `RANK`, `pandas_ta/statistics/rank.py`,
both issue #34) with no price input at all, so it ships in `volume`, next to
`volcv` (`pandas_ta/volume/volcv.py`), the closest existing shape.

Source: Microsoft qlib, `qlib/contrib/data/loader.py`,
`Alpha158DL.get_feature_config` (fetched read-only from GitHub `main`,
2026-10-24; PandasTa issue #34). qlib is released under the MIT License
(public knowledge of the project's licensing; not re-verified by a live fetch
in this session -- web access was unavailable). This is an independent
implementation from the published formula, not a copy of qlib's source.

Scale-free: price plays no role in the formula (this function takes no
`close` argument), so only a volume rescale applies. NOT quite
bit-identical even at x8/x64 -- measured max|diff| ~1.1e-16 -- because the
`+1e-12` floor does not commute exactly with a volume rescale (the same
floor effect as `wvma`); well within the 1e-9 tolerance used for all four
factors (x8, x64, x10, x3.7). See `tests/test_vsumd.py`.

Calculation:
    Default Inputs:
        lengths=(5, 10, 20, 30, 60)
    dv = volume.diff()
    up, down = MAX(dv, 0), MAX(-dv, 0)
    For each d in lengths:
        VSUMD_d = (SUM(up, d) - SUM(down, d)) / (SUM(ABS(dv), d) + 1e-12)

Args:
    volume (pd.Series): Series of 'volume's
    lengths (Sequence[int]): Trailing windows, each >= 2.
        Default: (5, 10, 20, 30, 60)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: One VSUMD_<d> column per window in `lengths`.
"""
