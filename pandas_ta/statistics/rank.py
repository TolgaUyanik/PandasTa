# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series

#: Alpha158's own five windows were (qlib `Alpha158DL.get_feature_config`)
#: 5, 10, 20, 30, 60. Gate E (issue #34, measured 2026-11-02, see
#: docs/Alpha158Measured.md) STRUCK 20/30/60 against the engine's own
#: `BB_%B` (0.9767), `zscore` (0.9788) and `Range_Pos_60` (0.9403) -- all
#: pooled |rho| >= 0.90 on the 89 BIST frames -- and they were removed.
#: Only 5 and 10 survive, at DISCLOSE_GAP.
DEFAULT_LENGTHS = (5, 10)
#: Gate E STRUCK lengths (see above): refused outright, not merely absent
#: from the default, so `rank(close, lengths=[20])` cannot resurrect them.
STRUCK_LENGTHS = (20, 30, 60)


def _rolling_pct_rank(values: np.ndarray, length: int) -> np.ndarray:
    """Percentile rank of the LAST bar of each trailing `length`-bar window:
    count(window <= last) / length. Reads only the window ending at the
    current bar -- no bar past `t` is ever touched."""
    n = len(values)
    out = np.full(n, np.nan)
    if length > n:
        return out
    windows = sliding_window_view(values, length)
    last = windows[:, -1]
    valid = np.all(np.isfinite(windows), axis=1)
    counts = np.sum(windows <= last[:, None], axis=1)
    out[length - 1:] = np.where(valid, counts / length, np.nan)
    return out


def rank(close, lengths=None, offset=None, **kwargs):
    """Indicator: Rolling Percentile Rank (RANK)"""
    # Validate Arguments
    lengths = DEFAULT_LENGTHS if lengths is None else lengths
    lengths = sorted(set(int(L) for L in lengths))
    if not lengths or lengths[0] < 2:
        raise ValueError(f"rank: need at least one length >= 2; got {lengths}")
    struck = [L for L in lengths if L in STRUCK_LENGTHS]
    if struck:
        raise ValueError(f"rank: lengths {struck} are Gate E STRUCK (issue #34, "
                          "docs/Alpha158Measured.md) and were removed from this port")
    max_len = lengths[-1]
    close = verify_series(close, max_len)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    values = close.to_numpy(dtype=float)
    data = {f"RANK_{length}": _rolling_pct_rank(values, length) for length in lengths}
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
    df.name = f"RANK_{tag}"
    df.category = "statistics"

    return df


rank.__doc__ = \
"""Rolling Percentile Rank (RANK)

qlib Alpha158's `RANK$d = Rank($close, d)`: today's close ranked against the
trailing `d` closes, as a fraction in (0, 1] (ties and the current bar itself
counted in the denominator). One column per window in `lengths`, each named
`RANK_<d>`.

Alpha158 gives five windows: 5, 10, 20, 30, 60. Gate E (issue #34, measured
2026-11-02, `docs/Alpha158Measured.md`) STRUCK the three slower ones against
columns the engine already ships -- `RANK_20` vs `BB_%B` (pooled |rho|
0.9767), `RANK_30` vs `zscore` (0.9788), `RANK_60` vs `Range_Pos_60`
(0.9403) -- and they were removed; `lengths=[20]` etc. now raises
`ValueError` rather than reproducing a struck column. Only `RANK_5` and
`RANK_10` ship, both DISCLOSE_GAP (0.8895 / 0.8786 vs `Dist_to_FWMA_pct`).

Source: Microsoft qlib, `qlib/contrib/data/loader.py`,
`Alpha158DL.get_feature_config` (fetched read-only from GitHub `main`,
2026-10-24; PandasTa issue #34). qlib is released under the MIT License
(public knowledge of the project's licensing; not re-verified by a live fetch
in this session -- web access was unavailable). This is an independent
implementation from the published formula, not a copy of qlib's source.

Scale-free: an order statistic, so invariant to ANY positive rescale of
`close`, not merely a power of two -- measured bit-identical under x8, x64,
x10 AND x3.7 (no ties hit on the test walk; a tie-flip would move a column
by a full `1/length`, not a small amount, which is why this is checked as
bit-identical rather than a tolerance). See `tests/test_rank.py`.

Calculation:
    Default Inputs:
        lengths=(5, 10)
    For each d in lengths:
        RANK_d[t] = count(close[t-d+1 .. t] <= close[t]) / d

Args:
    close (pd.Series): Series of 'close's
    lengths (Sequence[int]): Trailing windows, each >= 2 and not in
        (20, 30, 60) (Gate E STRUCK, issue #34).
        Default: (5, 10)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: One RANK_<d> column per window in `lengths`.
"""
