# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# Relative singular-value cutoff: the same 1e-15 statsmodels' pinv uses, but
# applied to the centred lag matrix, not to statsmodels' uncentred [1, X].
RCOND = 1e-15
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk


def _lm_rows(r, lags):
    """Engle's ARCH LM statistic for each row of `r` (one window of returns
    per row): OLS of e_t = r_t^2 on a constant and e_{t-1} .. e_{t-lags},
    LM = (rows used) * centred R^2, as statsmodels `het_arch(r, nlags=lags)`
    computes it. The constant is removed by centring y and every regressor;
    the projection uses the SVD with a relative cutoff of RCOND."""
    n = r.shape[1]
    m = n - lags
    e = r * r
    y = e[:, lags:]
    x = np.stack([e[:, lags - j:n - j] for j in range(1, lags + 1)], axis=2)
    y = y - y.mean(axis=1, keepdims=True)
    x = x - x.mean(axis=1, keepdims=True)
    u, s, _ = np.linalg.svd(x, full_matrices=False)
    keep = s > RCOND * s[:, :1]
    proj = np.einsum("kml,km->kl", u, y) * keep
    ess = (proj * proj).sum(axis=1)
    tss = (y * y).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        # a regressand (the window's last m squared returns) that does not
        # vary has no R^2: NaN
        return np.where(tss > 0, m * ess / tss, np.nan)


def arch_lm(close, length=None, offset=None, **kwargs):
    """Indicator: ARCH LM statistic of returns (ARCHLM)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= 10 else 100
    lags = min(10, length // 5)
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c > 0), c, np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0  # one-bar return; exact under a x2^k rescale
        # a return whose square overflows (an extreme close) would reach the
        # SVD as inf and fail the whole series: treat it as missing
        r[~np.isfinite(r * r)] = np.nan

    # Bar T reads the `length` returns ending at T (closes T - length .. T).
    # Windows are evaluated in chunks so peak memory does not grow with
    # n * length; a window holding a NaN return is NaN.
    win = sliding_window_view(r, length)
    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _lm_rows(chunk[ok], lags)
        lo = length + start
        values[lo:lo + rows.size] = rows

    archlm = Series(values, index=close.index)

    # Offset
    if offset != 0:
        archlm = archlm.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        archlm.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    archlm.name = f"ARCHLM_{length}"
    archlm.category = "statistics"

    return archlm


arch_lm.__doc__ = \
"""ARCH LM statistic of returns (ARCHLM)

Engle's Lagrange-multiplier test for autoregressive conditional
heteroskedasticity, over a rolling window of one-bar returns: regress the
squared return on a constant and its own previous `lags` values; the
statistic is the number of regression rows times the R^2. Asymptotically
chi-squared with `lags` degrees of freedom when the squared returns carry
no memory (measured mean 8.9 on iid normal returns at length 100, below
the asymptotic 10); large when big moves cluster, i.e. when volatility is
itself predictable inside the window. At 10 lags the chi-squared 5%
critical value is 18.31. Read it as a ranking, not a p-value: see
docs/ArchLmMeasured.md for how iid normal and fat-tailed returns read.

Source: Kats tsfeatures (Meta, MIT), `get_het_arch` ("heterogeneity"):
`statsmodels.stats.diagnostic.het_arch(x, nlags=min(10, len(x) // 5))[0]`,
after Engle (1982), Econometrica 50(4); statsmodels 0.15.0
`stats/diagnostic.py` L936-999 (`het_arch` -> `acorr_lm(resid**2)`) and
L784-933 (`acorr_lm`: lagmat trim="both" L892, nobs L893, OLS L899,
LM = (nobs - ddof) * R^2 L905). Kats applies it to a whole series;
the 100-bar window and one-bar returns as the input are the choices of the
2026-10-25 screen prototype (candidate kats_arch_lm_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine).
PandasTa issue #154.

Causal: bar T reads closes T - length .. T (`length` returns). Scale-free:
returns are price ratios, exact under a x8/x64 rescale. A window with a
NaN, zero or negative close, or a return whose square overflows, is NaN.
So is a window whose last length - lags squared returns are all equal (the
regressand has no variance), e.g. after length - lags or more unchanged
closes: a run of R zero returns blanks R - (length - lags) + 1 bars, which
starts `lags` bars before the window is entirely flat. Each window is computed on its
own, not from rolling sums; windows are evaluated in chunks so memory does
not grow with n * length.

Calculation:
    Default Inputs:
        length=100
    lags = MIN(10, length // 5)
    r = close / close.shift(1) - 1;  e = r^2      (the window's `length` returns)
    OLS: e[t] = b0 + b1 e[t-1] + ... + b_lags e[t-lags] + u[t],
         t over the window's last length - lags returns
    ARCHLM = (length - lags) * R^2                 (centred R^2)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 10 (2 lags, 8 regression
        rows); a smaller or missing value falls back to the default.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: ARCHLM_{length}, in [0, length - lags]
"""
