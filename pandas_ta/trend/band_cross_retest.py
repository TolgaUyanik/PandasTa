# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.overlap.ma import ma
from pandas_ta.overlap.vwma import vwma
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _band_ma(kind, source, length, close=None, volume=None):
    if kind == "vwma":
        return vwma(close=close, volume=volume, length=length)
    return ma(kind, source, length=length)


def band_cross_retest(high, low, close, volume=None, ma_type=None, len_fast=None,
                       len_slow=None, atr_length=None, min_ext_atr=None,
                       min_vel_atr=None, min_sep_atr=None, offset=None, **kwargs):
    """Indicator: Band Cross Retest (BANDXR)"""
    ma_type = ma_type.lower() if ma_type and isinstance(ma_type, str) else "ema"
    len_fast = int(len_fast) if len_fast and len_fast > 0 else 66
    len_slow = int(len_slow) if len_slow and len_slow > 0 else 288
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 14
    min_ext_atr = float(min_ext_atr) if min_ext_atr and min_ext_atr > 0 else 2.0
    min_vel_atr = float(min_vel_atr) if min_vel_atr and min_vel_atr > 0 else 0.10
    min_sep_atr = float(min_sep_atr) if min_sep_atr is not None and min_sep_atr >= 0 else 0.3
    high = verify_series(high, len_slow)
    low = verify_series(low, len_slow)
    close = verify_series(close, len_slow)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return
    if ma_type not in ("rma", "ema", "sma", "wma", "vwma"): return
    if ma_type == "vwma" and volume is None: return

    b_h = _band_ma(ma_type, high, len_fast, close=close, volume=volume)
    b_l = _band_ma(ma_type, low, len_fast, close=close, volume=volume)
    r_h = _band_ma(ma_type, high, len_slow, close=close, volume=volume)
    r_l = _band_ma(ma_type, low, len_slow, close=close, volume=volume)
    atr_val = atr(high, low, close, length=atr_length)

    bands_touch = (b_l <= r_h) & (r_l <= b_h)
    bands_separation = (~bands_touch) & bands_touch.shift(1).fillna(False)
    blue_above_red = b_l > r_h
    red_above_blue = r_l > b_h
    cross_up = (bands_separation & blue_above_red).to_numpy()
    cross_down = (bands_separation & red_above_blue).to_numpy()
    bands_touch_v = bands_touch.to_numpy()

    n = len(close)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    bl_h = b_h.to_numpy(dtype=float)
    bl_l = b_l.to_numpy(dtype=float)
    rd_h = r_h.to_numpy(dtype=float)
    rd_l = r_l.to_numpy(dtype=float)
    a = atr_val.to_numpy(dtype=float)

    retest_fast = np.zeros(n, dtype=int)
    retest_slow = np.zeros(n, dtype=int)
    band_gap_atr = np.full(n, np.nan)

    # After a cross, track the price EXTREME reached since the cross (the
    # "impulse") to measure its size (extension) and speed (velocity) in
    # ATR units, independent of how long the RETRACEMENT back to the
    # bands takes. If the bands re-touch before either band is retested,
    # the whole setup is invalidated (a re-touch means the "separation"
    # never held). A retest of a given band only fires ONCE per cross
    # ("first touch only"), matching the source's wait-flag reset.
    wait_fast = False
    wait_slow = False
    cross_dir = 0
    extreme_since_cross = np.nan
    cross_anchor = np.nan
    cross_bar = -1
    extreme_bar = -1

    for t in range(n):
        if cross_up[t] or cross_down[t]:
            wait_fast = True
            wait_slow = True
            cross_dir = 1 if cross_up[t] else -1
            extreme_since_cross = h[t] if cross_dir == 1 else l[t]
            cross_anchor = c[t]
            cross_bar = t
            extreme_bar = t
        elif bands_touch_v[t]:
            wait_fast = False
            wait_slow = False
        elif cross_dir == 1 and h[t] > extreme_since_cross:
            extreme_since_cross = h[t]
            extreme_bar = t
        elif cross_dir == -1 and l[t] < extreme_since_cross:
            extreme_since_cross = l[t]
            extreme_bar = t

        if cross_dir == 1:
            extension_now = extreme_since_cross - cross_anchor
        elif cross_dir == -1:
            extension_now = cross_anchor - extreme_since_cross
        else:
            extension_now = 0.0
        bars_to_extreme = max(extreme_bar - cross_bar, 1) if (extreme_bar >= 0 and cross_bar >= 0) else 0
        velocity_now = extension_now / bars_to_extreme if bars_to_extreme else 0.0

        atr_t = a[t]
        extension_atr = extension_now / atr_t if atr_t and not np.isnan(atr_t) and atr_t != 0 else 0.0
        velocity_atr = velocity_now / atr_t if atr_t and not np.isnan(atr_t) and atr_t != 0 else 0.0

        if cross_dir == 1:
            band_gap_now = bl_l[t] - rd_h[t]
        elif cross_dir == -1:
            band_gap_now = rd_l[t] - bl_h[t]
        else:
            band_gap_now = 0.0
        gap_atr = band_gap_now / atr_t if atr_t and not np.isnan(atr_t) and atr_t != 0 else 0.0
        band_gap_atr[t] = gap_atr

        dynamic_ok = (extension_atr >= min_ext_atr) and (velocity_atr >= min_vel_atr) and (gap_atr >= min_sep_atr)

        touch_fast = (h[t] >= bl_l[t]) and (l[t] <= bl_h[t])
        touch_slow = (h[t] >= rd_l[t]) and (l[t] <= rd_h[t])

        if wait_fast and touch_fast and dynamic_ok:
            retest_fast[t] = 1
            wait_fast = False
        if wait_slow and touch_slow and dynamic_ok:
            retest_slow[t] = 1
            wait_slow = False

    cross_up_s = Series(cross_up.astype(int), index=close.index)
    cross_down_s = Series(cross_down.astype(int), index=close.index)
    retest_fast_s = Series(retest_fast, index=close.index)
    retest_slow_s = Series(retest_slow, index=close.index)
    band_gap_atr_s = Series(band_gap_atr, index=close.index)

    # Offset
    if offset != 0:
        cross_up_s = cross_up_s.shift(offset)
        cross_down_s = cross_down_s.shift(offset)
        retest_fast_s = retest_fast_s.shift(offset)
        retest_slow_s = retest_slow_s.shift(offset)
        band_gap_atr_s = band_gap_atr_s.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        for s in (cross_up_s, cross_down_s, retest_fast_s, retest_slow_s, band_gap_atr_s):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (cross_up_s, cross_down_s, retest_fast_s, retest_slow_s, band_gap_atr_s):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{ma_type.upper()}_{len_fast}_{len_slow}"
    cross_up_s.name = f"BANDXR_CROSS_UP{_props}"
    cross_down_s.name = f"BANDXR_CROSS_DN{_props}"
    retest_fast_s.name = f"BANDXR_RETEST_FAST{_props}"
    retest_slow_s.name = f"BANDXR_RETEST_SLOW{_props}"
    band_gap_atr_s.name = f"BANDXR_GAP_ATR{_props}"

    df = DataFrame({
        cross_up_s.name: cross_up_s,
        cross_down_s.name: cross_down_s,
        retest_fast_s.name: retest_fast_s,
        retest_slow_s.name: retest_slow_s,
        band_gap_atr_s.name: band_gap_atr_s,
    })
    df.name = f"BANDXR{_props}"
    df.category = "trend"

    return df


band_cross_retest.__doc__ = \
"""Band Cross Retest (BANDXR)

Two "bands" (each a high/low pair of moving averages at a fast and a slow
period) that overlap most of the time; a genuine CROSS is only recognized
when they separate cleanly after having touched (`bands_touch`), not on
every momentary overlap. Once separated, the price EXTREME reached since
the cross defines the "impulse" -- its size (`extension`) and speed
(`velocity`), both in ATR units, gate whether a later RETEST (first touch
back into either band) counts as a valid signal; the setup is invalidated
if the bands re-touch before a retest happens. This impulse-then-
qualified-retest state machine (extension/velocity/band-gap filters, "the
retracement itself may be arbitrarily slow, only the impulse is judged")
is not a duplicate of any crossover/band indicator in the catalog.

Source: TradingView community indicator "HTS - Wstęgi PRO 4 Alerty [v7]"
(polish: "HTS - Bands PRO 4 Alerts") by xwaytheory (see
`datastore/source/pine_triage.csv` for the exact attribution row) (ported
into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Ported in full -- the
detection logic is the entire substance; the source's steep-band-warning
label styling is decorative and not replicated.

Calculation:
    Default Inputs:
        ma_type="ema" (or "rma"/"sma"/"wma"/"vwma"), len_fast=66,
        len_slow=288, atr_length=14, min_ext_atr=2.0, min_vel_atr=0.10,
        min_sep_atr=0.3
    B_H/B_L = MA(high/low, len_fast); R_H/R_L = MA(high/low, len_slow)
    bands_touch = B_L <= R_H and R_L <= B_H
    A genuine cross fires when bands_touch goes from true to false AND
        the bands are now cleanly on one side of each other.
    Since the cross, track extreme_since_cross (running max/min);
        extension = |extreme - cross_anchor|; velocity = extension /
        bars_to_extreme; both divided by ATR(atr_length).
    band_gap_atr = gap between the bands' near edges, in ATR units,
        tracked every bar since the cross (not only at the cross).
    BANDXR_RETEST_FAST/SLOW = 1 on the first bar since the cross that
        price touches back into that band, IF extension/velocity/gap all
        clear their minimums; invalidated (never fires) if the bands
        re-touch first.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's. Required only if
        ma_type="vwma".
    ma_type (str): "rma", "ema", "sma", "wma", or "vwma". Default: "ema"
    len_fast (int): Fast band MA period. Default: 66
    len_slow (int): Slow band MA period. Default: 288
    atr_length (int): ATR period for all impulse filters. Default: 14
    min_ext_atr (float): Minimum impulse size, in ATR. Default: 2.0
    min_vel_atr (float): Minimum impulse speed, in ATR/bar. Default: 0.10
    min_sep_atr (float): Minimum band separation at retest, in ATR.
        Default: 0.3
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: BANDXR_CROSS_UP, BANDXR_CROSS_DN, BANDXR_RETEST_FAST,
        BANDXR_RETEST_SLOW, BANDXR_GAP_ATR columns.
"""
