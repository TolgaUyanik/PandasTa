# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def har_park(high, low, close, short_length=None, medium_length=None, long_length=None,
             fit_window=None, offset=None, **kwargs):
    """Indicator: HAR-Parkinson Volatility Forecast (HARPARK)"""
    # Validate Arguments
    short_length = int(short_length) if short_length and short_length > 0 else 1
    medium_length = int(medium_length) if medium_length and medium_length > 0 else 5
    long_length = int(long_length) if long_length and long_length > 0 else 22
    fit_window = int(fit_window) if fit_window and fit_window > 0 else 500
    high = verify_series(high, fit_window)
    low = verify_series(low, fit_window)
    close = verify_series(close, fit_window)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Parkinson range-based volatility, percent of price, causal (current
    # bar's own H/L only -- no look-ahead).
    ln2 = np.log(2.0)
    hl_valid = (high > 0) & (low > 0) & (high >= low)
    park_pct = np.where(hl_valid, np.sqrt(np.log(high / low) ** 2 / (4 * ln2)) * 100, 0.0)
    park_pct = Series(park_pct, index=close.index)

    # HAR components: short/medium/long SMAs of Parkinson vol (source
    # defaults 1/5/22 bars, "daily/weekly/monthly-equivalent").
    x1 = park_pct.rolling(short_length).mean()
    x2 = park_pct.rolling(medium_length).mean()
    x3 = park_pct.rolling(long_length).mean()

    # Regression training pairs: predict today's park_pct from YESTERDAY's
    # (x1, x2, x3) -- the source's own causality note ("lagged by one bar
    # -- keeps the fit strictly causal"). Rows with any NaN predictor are
    # zeroed rather than dropped, matching the source's na-guard (`valid ?
    # p : 0.0`), so rolling sums stay aligned to a fixed bar count.
    y = park_pct
    p1, p2, p3 = x1.shift(1), x2.shift(1), x3.shift(1)
    valid = p1.notna() & p2.notna() & p3.notna() & y.notna()
    v1 = p1.where(valid, 0.0)
    v2 = p2.where(valid, 0.0)
    v3 = p3.where(valid, 0.0)
    vy = y.where(valid, 0.0)
    vc = valid.astype(float)

    # Rolling sums for the 4x4 normal-equations system (intercept + 3
    # slopes), refit every bar over the trailing fit_window.
    s00 = vc.rolling(fit_window).sum()
    s01 = v1.rolling(fit_window).sum()
    s02 = v2.rolling(fit_window).sum()
    s03 = v3.rolling(fit_window).sum()
    s0y = vy.rolling(fit_window).sum()
    s11 = (v1 * v1).rolling(fit_window).sum()
    s12 = (v1 * v2).rolling(fit_window).sum()
    s13 = (v1 * v3).rolling(fit_window).sum()
    s1y = (v1 * vy).rolling(fit_window).sum()
    s22 = (v2 * v2).rolling(fit_window).sum()
    s23 = (v2 * v3).rolling(fit_window).sum()
    s2y = (v2 * vy).rolling(fit_window).sum()
    s33 = (v3 * v3).rolling(fit_window).sum()
    s3y = (v3 * vy).rolling(fit_window).sum()

    n = len(close)
    b0 = np.full(n, np.nan)
    b1 = np.full(n, np.nan)
    b2 = np.full(n, np.nan)
    b3 = np.full(n, np.nan)

    cols = (s00, s01, s02, s03, s0y, s11, s12, s13, s1y, s22, s23, s2y, s33, s3y)
    (s00v, s01v, s02v, s03v, s0yv, s11v, s12v, s13v, s1yv,
     s22v, s23v, s2yv, s33v, s3yv) = (c.to_numpy() for c in cols)

    # Solve the symmetric 4x4 system per bar. The source hand-rolls
    # Gaussian elimination with partial pivoting inside a Pine-array UDF
    # (necessary there -- Pine has no linear-algebra library); numpy's
    # solve() computes the same result without reimplementing pivoting by
    # hand, but `LinAlgError` alone only fires on an EXACTLY singular
    # matrix -- Pine's guard (`ok := false` whenever a post-pivot entry's
    # |value| < 1e-12) also catches the NEAR-singular band, which numpy's
    # solve() would happily return numerically unstable, arbitrarily
    # amplified coefficients for instead of NaN. x1/x2/x3 are three SMAs
    # of the same series (correlated by construction) and a BIST
    # limit-lock streak (constant H/L ratio for several bars) pushes
    # toward exactly this near-singular regime, so the smallest-singular-
    # value check below is a real guard, not defensive-only boilerplate.
    for t in range(n):
        if np.isnan(s00v[t]):
            continue
        a = np.array([
            [s00v[t], s01v[t], s02v[t], s03v[t]],
            [s01v[t], s11v[t], s12v[t], s13v[t]],
            [s02v[t], s12v[t], s22v[t], s23v[t]],
            [s03v[t], s13v[t], s23v[t], s33v[t]],
        ])
        rhs = np.array([s0yv[t], s1yv[t], s2yv[t], s3yv[t]])
        singular_values = np.linalg.svd(a, compute_uv=False)
        if singular_values.min() < 1e-12:
            continue
        try:
            coeffs = np.linalg.solve(a, rhs)
        except np.linalg.LinAlgError:
            continue
        b0[t], b1[t], b2[t], b3[t] = coeffs

    b0 = Series(b0, index=close.index)
    b1 = Series(b1, index=close.index)
    b2 = Series(b2, index=close.index)
    b3 = Series(b3, index=close.index)

    # Forecast: today's fitted (b0..b3) applied to TODAY's (x1,x2,x3) to
    # predict NEXT bar's Parkinson vol -- distinct from the lagged training
    # step above. fit_ready mirrors the source's extra causal margin
    # (`bar_index > longLB + fitWindow/2 + 60`) on top of b0 existing;
    # deliberately NOT relaxed to "as soon as b0 exists" even though that
    # would pass earlier -- matching the source's own conservative gate,
    # not a reformulation.
    bar_index = np.arange(n)
    # Pine's `fitWindow / 2` on two ints performs INTEGER division (`//`
    # here, not `/`) -- matched exactly, not just "close enough": at
    # fit_window=501 the two differ by half a bar (332 vs 332.5), shifting
    # the first-ready bar by one.
    fit_ready = (bar_index > (long_length + fit_window // 2 + 60)) & b0.notna().to_numpy()
    fpct_raw = b0 + b1 * x1 + b2 * x2 + b3 * x3
    fpct = fpct_raw.clip(lower=0.0)
    fpct = fpct.where(fit_ready, np.nan)

    result = fpct

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it. fit_window is included -- it's the single
    # most consequential parameter (sets both the refit window and, via
    # fit_ready, the warm-up gate); two calls differing only in
    # fit_window produce numerically different series and must not share
    # a column name (a silent collision risk in a parameter sweep).
    result.name = f"HARPARK_{short_length}_{medium_length}_{long_length}_{fit_window}"
    result.category = "volatility"

    return result


har_park.__doc__ = \
"""HAR-Parkinson Volatility Forecast (HARPARK)

A causal, rolling-refit HAR (Heterogeneous AutoRegressive) regression that
forecasts NEXT-bar Parkinson range-based volatility (as a % of price,
already scale-free -- no distance-form reformulation needed) from three
SMA components of trailing Parkinson volatility (short/medium/long
"daily/weekly/monthly-equivalent" lookbacks). The regression is refit every
bar via a 4x4 normal-equations solve over a rolling fit_window of
(lagged-predictor, target) pairs -- genuinely novel per-bar computation,
not a duplicate of any existing indicator in this catalog (`natr`/`atr` are
single-scale range measures with no multi-horizon regression component).

Source: TradingView community indicator "HAR-Parkinson Volume Forecast" by
jqu2, https://www.tradingview.com/script/WnzgKfOS-HAR-Parkinson-Volume-Forecast/
(ported into AwakenAnalytics/Backtesting TVPTA-6, 2026-08-10; MPL-2.0 per
TradingView's open-source publication convention). Only the forecast value
itself (`fpct`, the scale-free % output) is ported. NOT replicated: the
price-scale `expRange` conversion (`fpct/100 * close * sqrt(4ln2)`, a raw
price-magnitude reformulation of the same signal -- excluded per the
Indicator Book's "raw price-level forms earn nothing by design" law, the
scale-free `fpct` this function returns is the correct form already), and
all display/table/alert logic (info table, plots).

⚠ The source's rolling `percentrank`/regime-threshold classification is
GENUINE per-bar math (not display) and is NOT ported here, for a
different reason: the source computes it on the price-scale `expRange`,
which entangles price drift into a 500-bar percentile ranking -- a
reformulation question (should it rank the scale-free `fpct` instead?),
deliberately deferred rather than guessed at in this pass.

Calculation:
    Default Inputs:
        short_length=1, medium_length=5, long_length=22, fit_window=500
    park_pct = sqrt(ln(high/low)^2 / (4*ln(2))) * 100          (Parkinson %)
    x1, x2, x3 = SMA(park_pct, short/medium/long_length)
    Rolling OLS, refit every bar over fit_window trailing bars:
        park_pct[t] ~ b0 + b1*x1[t-1] + b2*x2[t-1] + b3*x3[t-1]
    HARPARK[t] = max(b0 + b1*x1[t] + b2*x2[t] + b3*x3[t], 0)   (NaN until
        bar_index > long_length + fit_window//2 + 60 and the fit exists)

Requires >= fit_window bars of history (verify_series's own floor); on a
shorter frame this function returns None and the caller's `_attach`-style
wiring silently omits the column entirely -- not an error, just absent.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    short_length (int): Short HAR component SMA length. Default: 1
    medium_length (int): Medium HAR component SMA length. Default: 5
    long_length (int): Long HAR component SMA length. Default: 22
    fit_window (int): Rolling OLS refit window. Default: 500
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
