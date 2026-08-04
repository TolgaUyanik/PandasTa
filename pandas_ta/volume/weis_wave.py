# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.volatility.true_range import true_range
from pandas_ta.utils import get_offset, verify_series


def weis_wave(high, low, close, open_, volume=None, method=None, value=None,
              price_source=None, use_true_range=None, oscillating=False,
              normalize=False, offset=None, **kwargs):
    """Indicator: Weis Wave Effort vs Result (WEISWAVE)"""
    method = method.lower() if method and isinstance(method, str) else "traditional"
    value = float(value) if value and value > 0 else 3.0
    price_source = price_source.lower() if price_source and isinstance(price_source, str) else "close"
    use_true_range = use_true_range.lower() if use_true_range and isinstance(use_true_range, str) else "auto"

    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    open_ = verify_series(open_)
    offset = get_offset(offset)

    if high is None or low is None or close is None or open_ is None: return
    if method not in ("atr", "traditional", "part_of_price"): return
    if price_source not in ("close", "open_close", "high_low"): return
    if use_true_range not in ("always", "auto", "never"): return

    # Effort measure per bar: True Range or Volume. "Auto" falls back to
    # True Range only where volume itself is NaN (source Pine semantics --
    # on this project's data every bar has volume, so Auto == Volume in
    # practice; kept configurable for fidelity to the source).
    tr = true_range(high, low, close)
    if use_true_range == "always" or volume is None:
        effort = tr
    elif use_true_range == "never":
        effort = verify_series(volume)
    else:
        vol = verify_series(volume)
        effort = vol.where(vol.notna(), tr)

    # Renko "price" used for box-break/direction detection, per price_source.
    if price_source == "close":
        hi_src = close
        lo_src = close
    elif price_source == "open_close":
        hi_src = close.where(close >= open_, open_)
        lo_src = close.where(close <= open_, open_)
    else:  # high_low
        hi_src = high
        lo_src = low

    # Box (assignment) size per bar. "Part of Price" (a divisor, e.g. 20 ==
    # 5% of price) from the source is NOT ported -- scoped down to the two
    # most common sizing modes, matching this batch's precedent
    # (`zigzag_fib` similarly drops a secondary source option).
    if method == "atr":
        assignment = atr(high, low, close, length=max(1, round(value)))
    else:
        assignment = Series(value, index=close.index)

    n = len(close)
    hi_v = hi_src.to_numpy(dtype=float)
    lo_v = lo_src.to_numpy(dtype=float)
    assign_v = assignment.to_numpy(dtype=float)
    eff_v = effort.to_numpy(dtype=float)

    # Sequential Renko-close construction: each bar's synthetic Renko close
    # only ever moves when price breaks the current box (prevclose +/-
    # assignment); direction flips only on a break in the opposite sense.
    # This recursive dependency (currclose[i] needs currclose[i-1]) is
    # inherently stateful, same class of problem as `swing_equilibrium`'s
    # pivot confirmation and `zigzag_fib`'s leg alternation -- implemented
    # as an explicit sequential scan rather than forced into a vectorized
    # form that would obscure the causality.
    direction = np.zeros(n, dtype=int)
    barcount = np.ones(n, dtype=int)
    wave_effort = np.full(n, np.nan)

    prevclose = 0.0
    prevdir = 0
    prev_wave_effort = 0.0
    for i in range(n):
        if np.isnan(hi_v[i]) or np.isnan(lo_v[i]) or np.isnan(assign_v[i]) or np.isnan(eff_v[i]):
            direction[i] = prevdir
            barcount[i] = 1
            wave_effort[i] = np.nan
            continue

        prevhigh = prevclose + assign_v[i]
        prevlow = prevclose - assign_v[i]
        if hi_v[i] > prevhigh:
            cur = hi_v[i]
        elif lo_v[i] < prevlow:
            cur = lo_v[i]
        else:
            cur = prevclose

        if cur > prevclose:
            d = 1
        elif cur < prevclose:
            d = -1
        else:
            d = prevdir

        # First valid bar always starts a fresh wave (no prior direction to
        # compare against yet).
        changed = (d != prevdir) or (i == 0)

        barcount[i] = (barcount[i - 1] + 1) if (not changed and normalize and i > 0) else 1
        wave_effort[i] = eff_v[i] if changed else prev_wave_effort + eff_v[i]

        direction[i] = d
        prevclose = cur
        prevdir = d
        prev_wave_effort = wave_effort[i]

    res = np.where(barcount > 1, wave_effort / barcount, wave_effort)
    if oscillating:
        res = np.where(direction < 0, -res, res)

    wave = Series(res, index=close.index)

    # Offset
    if offset != 0:
        wave = wave.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        wave.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        wave.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{method.upper()[:4]}_{value}"
    wave.name = f"WEISWAVE{_props}"
    wave.category = "volume"

    return wave


weis_wave.__doc__ = \
"""Weis Wave Effort vs Result (WEISWAVE)

The Weis Wave (David Weis, "Trades About to Happen"): price is collapsed
into a synthetic Renko series (a break of a fixed or ATR-sized box moves
the Renko close and, on a reversal, flips direction); the effort measure
(volume, or True Range where volume is unavailable) is then summed for
every bar belonging to the SAME directional wave, resetting on each
direction flip. The result is a volume/effort oscillator gated by price
structure rather than by a fixed rolling window -- a genuinely distinct
concept from every existing accumulation/distribution-style volume
indicator in this package (`ad`, `obv`, `cmf`, ...), all of which
accumulate over FIXED windows, not variable-length price-structure waves.

Source: TradingView community indicator "Weis Wave Renko - Effort vs
Result" by paulgill28, forked from modhelius' original Weis Wave Volume
script (see `datastore/source/pine_triage.csv` for the exact attribution
row) (ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0
per TradingView's open-source publication convention). Confirmed by a full
read that only ONE `plot()` call exists in the 947-line source (the
"Existing exportable Weis Wave plot retained unchanged" at the source's
own line 156) -- everything else (pivot statistics labels, wave comment
callouts, scenario-key table, permanent-note box) is drawing/table UI with
no additional per-bar numeric series, and is NOT ported. The source's
"Part of Price" box-sizing mode is also NOT ported (scoped down to the two
most common sizing modes: fixed price-unit and ATR-sized).

⚠ Scale caveat: like the existing `ad`/`obv`/`cmf` volume indicators, this
is NOT price-scale-free -- its magnitude is set by each ticker's own
volume (or, in True-Range-effort mode, by its own price scale). Compare
within a single ticker's own history, not across tickers of different
liquidity/price, the same caveat class that already applies to every
un-normalized volume indicator in this package.

Calculation:
    Default Inputs:
        method="traditional" (or "atr"), value=3.0 (price units, or ATR
        length when method="atr"), price_source="close" (or "open_close",
        "high_low"), use_true_range="auto" (or "always", "never"),
        oscillating=False, normalize=False
    effort = True Range, or Volume where available (per use_true_range)
    hi_src/lo_src = per price_source (close-only / max,min(open,close) /
        high,low)
    Sequential Renko close: on each bar, if hi_src breaks above
        prevclose + box, currclose = hi_src (direction flips up if it
        wasn't already); if lo_src breaks below prevclose - box,
        currclose = lo_src (direction flips down); else currclose holds.
    wave_effort = running sum of `effort` across all bars sharing the
        CURRENT direction, resetting to `effort` on every direction flip.
    barcount = running count of bars in the current wave (only relevant
        when normalize=True; else always 1).
    WEISWAVE = wave_effort / barcount if barcount > 1 else wave_effort,
        negated on down-waves if oscillating=True.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    open_ (pd.Series): Series of 'open's
    volume (pd.Series): Series of 'volume's. Optional -- if omitted, True
        Range is used regardless of use_true_range.
    method (str): "traditional" (fixed box) or "atr" (ATR-sized box).
        Default: "traditional"
    value (float): Box size in price units (method="traditional") or ATR
        length (method="atr"). Default: 3.0
    price_source (str): "close", "open_close", or "high_low". Default: "close"
    use_true_range (str): "always", "auto", or "never". Default: "auto"
    oscillating (bool): Negate down-wave values. Default: False
    normalize (bool): Divide by the wave's bar count. Default: False
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: WEISWAVE_{METHOD}_{value}
"""
