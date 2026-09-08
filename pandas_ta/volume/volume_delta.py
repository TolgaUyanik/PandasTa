# -*- coding: utf-8 -*-
from numpy import nan
from pandas import DataFrame, Series

from .up_and_down_volume import (
    _anchor_key, _check_ltf, _classify_intrabar, _require_frame,
)


def volume_delta(lower=None, anchor=None, cumulative_period=None, **kwargs):
    """Indicator: Volume Delta / Cumulative Volume Delta (VD)"""
    lower = _require_frame(lower, "volume_delta")
    key = _anchor_key(lower, anchor)
    _check_ltf(key, "volume_delta")

    direction = _classify_intrabar(lower)
    volume = lower["volume"].astype("float64")
    pos = volume.where(direction > 0, 0.0)
    neg = (-volume).where(direction < 0, 0.0)

    # Pine's running delta WITHIN the main bar, and the high/low water marks it
    # reaches on the way (`RA2vGpkA-ta.pine:398-403`). Both marks are seeded at
    # 0.0 and reset with the bar, so hiVol >= 0 >= loVol by construction --
    # they are excursions from the bar's open, not the delta's own extremes.
    frame = DataFrame({"pos": pos, "neg": neg})
    running = (frame["pos"] + frame["neg"]).groupby(key, sort=False).cumsum()
    per_bar = running.groupby(key, sort=False)
    delta = per_bar.last()
    max_excursion = per_bar.max().clip(lower=0.0)
    min_excursion = per_bar.min().clip(upper=0.0)
    total = volume.groupby(key, sort=False).sum()

    # The cumulative period. Pine resets the running sum when
    # `timeframe.change(cumulativePeriod)` fires, and treats an EMPTY period
    # string as "reset every bar" (`:483-485`), which makes CVD collapse to
    # plain delta -- not an error, and the default.
    if cumulative_period is None:
        open_volume = Series(0.0, index=delta.index)
        last_volume = delta
    else:
        if not isinstance(delta.index, type(lower.index)) or \
                not hasattr(delta.index, "floor"):
            raise ValueError(
                "volume_delta: cumulative_period needs a DatetimeIndex on the "
                "main-timeframe axis to floor the period against."
            )
        period = delta.index.floor(cumulative_period)
        # sort=False here too: `delta.index` is already first-appearance
        # chronological, so re-sorting by period value can only undo that.
        cumulative = delta.groupby(period, sort=False).cumsum()
        open_volume = cumulative - delta
        last_volume = cumulative

    vd = DataFrame({
        "VD_OPEN": open_volume,
        "VD_HIGH": open_volume + max_excursion,
        "VD_LOW": open_volume + min_excursion,
        "VD_LAST": last_volume,
        # The scale-free companion; see the docstring's warning.
        "VD_DELTA_PCT": (delta / total.where(total != 0)).fillna(0.0),
    })
    if isinstance(anchor, str):
        vd.index.name = lower.index.name
    vd.name = "VD"
    vd.category = "volume"
    return vd


volume_delta.__doc__ = \
"""Volume Delta / Cumulative Volume Delta (VD)

The net difference between up and down intrabar volume for each
main-timeframe bar, and -- when `cumulative_period` is given -- the running
sum of that delta across the period (CVD), with the high and low water marks
it reached on the way.

Ported from TradingView's `TradingView/ta` library, `requestVolumeDelta()`
(`docs/pine/RA2vGpkA-ta.pine:474-489`) and the `upAndDownVolumeCalc()` helper
it wraps (`:381-404`). **© TradingView, Mozilla Public License 2.0.**

**It does not fetch anything.** Pine calls `request.security()`; this takes the
lower-timeframe frame as an argument and raises if it is absent, because how
much intrabar history exists is the caller's fact to state. The engine's floor
is 1h and yfinance serves sub-hourly bars for roughly 60 days only — see
`docs/LowerTimeframeData.md`.

Columns:
    VD_OPEN       CVD at the start of the bar; 0.0 when a period starts
    VD_HIGH       VD_OPEN + the bar's maximum upward excursion
    VD_LOW        VD_OPEN + the bar's maximum downward excursion
    VD_LAST       VD_OPEN + the bar's delta
    VD_DELTA_PCT  the bar's delta / its total volume, bounded [-1, 1]; **0.0
                  when the bar has no volume**, indistinguishable from a
                  perfectly balanced bar

⚠ **Main bars with no lower-timeframe rows produce NO ROW**, not a NaN row.
Reindex against your main frame if you need 1:1 alignment.

⚠ An anchor not strictly coarser than the lower frame RAISES, per Pine's
`checkLTF` (`RA2vGpkA-ta.pine:410-417`).

⚠ `VD_HIGH >= VD_OPEN >= VD_LOW` always holds. That is not a discovered
property, it is construction: Pine seeds `hiVol`/`loVol` at 0.0 and resets them
with the bar (`:387-392`, `:401-402`), so they are excursions FROM the open,
never the delta's own extremes. A port that treated them as running max/min of
the delta would produce different — and more plausible-looking — numbers.

⚠ **Only `VD_DELTA_PCT` is a model feature.** The four CVD columns scale with
liquidity and, being running sums, also drift without bound within a period;
they are the Pine contract, not features.

⚠ `cumulative_period=None` means "reset every bar", which makes `VD_LAST`
equal to the plain delta and `VD_OPEN` zero. Pine does the same for an empty
period string (`:483-485`).

Args:
    lower (pd.DataFrame): The lower-timeframe OHLCV frame. REQUIRED.
    anchor (str | pd.Series): How lower-timeframe rows group into main bars.
        REQUIRED; never guessed.
    cumulative_period (str): Offset alias the CVD accumulates over and resets
        at, e.g. "1D". Default: None (no accumulation).

Returns:
    pd.DataFrame: 5 columns, indexed by main-timeframe bar.
"""
