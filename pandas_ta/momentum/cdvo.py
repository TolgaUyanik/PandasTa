# -*- coding: utf-8 -*-
from pandas_ta.overlap.sma import sma
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def cdvo(high, low, close, atr_length=None, smooth=None, rank_length=None, offset=None, **kwargs):
    """Indicator: ATR-Adjusted Varadi Oscillator (CDVO)"""
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 10
    smooth = int(smooth) if smooth and smooth > 0 else 2
    rank_length = int(rank_length) if rank_length and rank_length > 1 else 126
    min_bars = max(atr_length, rank_length) + smooth
    high = verify_series(high, min_bars)
    low = verify_series(low, min_bars)
    close = verify_series(close, min_bars)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Step 1-2: how far (in ATRs) close sits from the bar's own median
    # price -- an ATR-normalized "stretch" (David Varadi's DVO, ATR-
    # adjusted variant), scale-free by construction (a price-scale
    # quantity divided by another price-scale quantity).
    # Fletcher round 1 (TVPTA-3-volatility): the source's `atrVal != 0 ?
    # ... : 0.0` ternary defines stretch=0.0 on a zero-ATR bar (a real
    # BIST case -- a name frozen at its price-limit for `atr_length`
    # sessions has True Range 0 every bar, hence ATR 0), not NaN. A bare
    # `.replace(0, nan)` diverged from the source on exactly that case and
    # would poison the trailing SMA/percent-rank windows with an
    # avoidable NaN. Compute the safe ratio, then patch zero-ATR bars back
    # to 0.0 to match the source exactly.
    median_price = (high + low) / 2.0
    atr_val = atr(high, low, close, length=atr_length)
    stretch = (close - median_price) / atr_val.replace(0, float("nan"))
    stretch = stretch.where(atr_val != 0, 0.0)

    # Step 3: light smoothing (SMA; smooth=1 passes stretch through
    # unchanged, matching the source's "s=1" no-op case).
    smoothed_stretch = sma(stretch, length=smooth) if smooth > 1 else stretch

    # Step 4: adaptive percent rank over the trailing `rank_length` bars --
    # the % of those PRIOR bars whose stretch was below today's, i.e. an
    # already-bounded [0, 100] oscillator (no separate normalization step
    # needed downstream).
    # ⚠ Known simplification (Fletcher round 1 flagged, not fully
    # resolved): `.rolling(rank_length + 1).apply(...)` uses pandas'
    # default `min_periods=window size`, so this only starts firing once
    # `rank_length + 1` CONSECUTIVE bars are all non-NaN -- a stricter,
    # later warmup boundary than Pine's `ta.percentrank`/`ta.sma` may use
    # (unverified against an actual Pine run; TradingView execution is not
    # available in this environment). Accepted as-is for this port: the
    # practical effect is a slightly delayed first valid value, not a
    # wrong one. `_percentrank` is written with no internal NaN handling
    # because pandas' `.rolling(window).apply(...)` with the default
    # `min_periods=window size` NEVER invokes the callback on a window
    # containing a NaN ANYWHERE (verified directly, not just for a leading
    # warmup NaN) -- this protects against a hypothetical mid-series NaN
    # too (e.g. a halted-session bar), not only the initial ATR/SMA
    # warmup. Do not add defensive NaN checks back in here; pandas already
    # guarantees they'd be unreachable.
    def _percentrank(window):
        cur = window[-1]
        prior = window[:-1]
        return (prior < cur).sum() / len(prior) * 100.0

    cdvo_val = smoothed_stretch.rolling(rank_length + 1).apply(_percentrank, raw=True)

    # Offset
    if offset != 0:
        cdvo_val = cdvo_val.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        cdvo_val.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        cdvo_val.fillna(method=kwargs["fill_method"], inplace=True)

    cdvo_val.name = f"CDVO_{atr_length}_{smooth}_{rank_length}"
    cdvo_val.category = "momentum"

    return cdvo_val


cdvo.__doc__ = \
"""ATR-Adjusted Varadi Oscillator (CDVO)

David Varadi's DVO (Dynamic Volatility Oscillator), ATR-adjusted variant:
close's distance from its own bar median `(high+low)/2`, expressed in ATR
units (a volatility-normalized "stretch"), lightly smoothed, then
converted to a percent-rank over a long lookback -- a bounded [0, 100]
mean-reversion oscillator, distinct from `rsi`/`stochrsi` (which rank
CLOSE-TO-CLOSE changes, not the ATR-normalized distance from the bar's own
median) and from `cci` (which uses a rolling mean-deviation denominator,
not ATR).

Source: TradingView community indicator "Custom DVO (ATR-Adjusted Varadi
Oscillator)" (see `datastore/source/pine_triage.csv` for the exact
attribution row) (ported into AwakenAnalytics/Backtesting TVPTA-3,
2026-08-04; MPL-2.0 per TradingView's open-source publication
convention). Ported in full -- the entire source is this one calculation
plus 3 `hline()` reference levels, no additional UI to scope out.

Calculation:
    Default Inputs:
        atr_length=10, smooth=2, rank_length=126
    median_price = (high + low) / 2
    stretch = ATR(atr_length) != 0 ? (close - median_price) / ATR(atr_length) : 0.0
        (matches the source's ternary exactly -- a zero-ATR bar, e.g. a
        BIST name frozen at its price limit, is a real 0.0, not NaN)
    smoothed_stretch = SMA(stretch, smooth)
    CDVO = PERCENTRANK(smoothed_stretch, rank_length)
        (% of the trailing rank_length bars whose value is below today's)

⚠ Known simplification: the percent-rank only starts producing a value
once `rank_length + 1` CONSECUTIVE bars are non-NaN (pandas' rolling
`min_periods=window` default), a possibly later warmup boundary than
Pine's own `ta.percentrank` -- unverified against a live Pine run (no
TradingView execution available in this environment). Only affects how
many of the very first bars are NaN, not any value once warmed up.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    atr_length (int): ATR period. Default: 10
    smooth (int): SMA smoothing period applied to the stretch. Default: 2
    rank_length (int): Percent-rank lookback. Default: 126
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: CDVO_{atr_length}_{smooth}_{rank_length}
"""
