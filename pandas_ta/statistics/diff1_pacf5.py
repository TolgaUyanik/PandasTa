# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window whose returns have a standard deviation of at most NOISE_ULPS
# machine epsilons times (1 + its largest |log return|) varies only by the
# rounding of log(c / c1): no variation. Same rule as diff2_acf1, one
# differencing level earlier (there it guards the return CHANGES; here it
# guards the returns themselves, since this column reads them directly).
NOISE_ULPS = 64
NLAGS = 5
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk
MIN_LENGTH = 14


def _pacf5_sumsq(rho):
    """Sum of squares of partial-autocorrelation lags 1..5, from the
    unadjusted sample ACF lags 1..5 (`rho`, one row per window), via the
    Durbin-Levinson recursion (Yule-Walker form, statsmodels'
    `pacf(..., method="ywm")`):

        phi[1,1] = rho[1]
        phi[k,k] = (rho[k] - sum_{j=1}^{k-1} phi[k-1,j] * rho[k-j])
                   / (1 - sum_{j=1}^{k-1} phi[k-1,j] * rho[j])
        phi[k,j] = phi[k-1,j] - phi[k,k] * phi[k-1,k-j],  j = 1..k-1

    `phi[k,k]` is the lag-k partial autocorrelation."""
    phi = [rho[:, 0]]  # phi[0] holds phi_{1,1} = rho_1
    pacf = [phi[0]]
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(2, NLAGS + 1):
            num = rho[:, k - 1] - sum(phi[j - 1] * rho[:, k - j - 1] for j in range(1, k))
            den = 1 - sum(phi[j - 1] * rho[:, j - 1] for j in range(1, k))
            phi_kk = num / den
            phi = [phi[j - 1] - phi_kk * phi[k - j - 1] for j in range(1, k)] + [phi_kk]
            pacf.append(phi_kk)
    return (np.column_stack(pacf) ** 2).sum(axis=1)


def _diff1_pacf5_rows(d, rmax):
    """`d`: one row per window, the window's log returns. Unadjusted ACF
    lags 1..5 (each lag divided by the row's own c0, as statsmodels'
    `acovf` with no adjustment does), fed to `_pacf5_sumsq`. Rows whose
    returns do not vary beyond rounding (see NOISE_ULPS) are NaN."""
    x = d - d.mean(axis=1, keepdims=True)
    c0 = (x * x).sum(axis=1)
    sd = np.sqrt(c0 / d.shape[1])
    real = sd > NOISE_ULPS * np.finfo(float).eps * (1.0 + rmax)
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = np.column_stack([(x[:, :-k] * x[:, k:]).sum(axis=1) / c0 for k in range(1, NLAGS + 1)])
        out = _pacf5_sumsq(rho)
    return np.where(real, out, np.nan)


def diff1_pacf5(close, length=None, offset=None, **kwargs):
    """Indicator: Sum of squares of the first 5 return partial autocorrelations (DIFF1PACF5)"""
    # Validate Arguments
    # 14 closes is the shortest window Kats' own call returns a value on
    # (shares the guard at L1107 with diff2_acf1, see its docstring).
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        r = np.log(c[1:] / c[:-1])  # diff of log close; exact under a x2^k rescale
        r[~np.isfinite(r)] = np.nan  # a ratio that overflows or underflows: missing

    # Bar T reads closes T - length + 1 .. T: length - 1 log returns. One
    # window at a time, evaluated in chunks so memory does not grow with
    # n * length. A window holding a NaN return is NaN.
    m = length - 1
    win = sliding_window_view(r, m)
    rabs = np.abs(win)
    step = max(1, CHUNK_CELLS // m)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _diff1_pacf5_rows(chunk[ok], rabs[start:start + step][ok].max(axis=1))
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    pacf5 = Series(values, index=close.index)

    # Offset
    if offset != 0:
        pacf5 = pacf5.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pacf5.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    pacf5.name = f"DIFF1PACF5_{length}"
    pacf5.category = "statistics"

    return pacf5


diff1_pacf5.__doc__ = \
"""Sum of squares of the first 5 return partial autocorrelations (DIFF1PACF5)

The sum of the squares of partial-autocorrelation lags 1-5 of the rolling
window's log returns, via the Durbin-Levinson recursion on the window's own
unadjusted sample autocorrelation. Partial autocorrelation at lag k is the
correlation between a return and the one k bars back after removing what the
shorter lags already explain, so this reads the dynamics an AR(5) would
pick up: non-zero only while a genuinely new lag still adds information.

Source: Kats tsfeatures (Meta, MIT), `get_acfpacf_features` ->
`diff1y_pacf5 = sum(pacf(diff(x))[1:6] ** 2)` (issue #151), after Hyndman's
tsfeatures `acf_features`. The same function shares its guards with
`diff2y_acf1` (see diff2_acf1.py's docstring for the cited line numbers of
the length-10/14 guard, `nlag` and `diff1x`); the `diff1y_pacf5` assembly
line itself is not independently re-confirmed in this session (no network
access to the Kats source), and the formula above is taken from the issue
text. Kats applies it to a whole series; the 100-bar window and log close
as the input are the choices of the 2026-10-25 screen prototype (candidate
kats_diff1_pacf5_100, docs/issues/screen/ind_screen_r5.py, local to the
owner's machine), which also specifies the scale-free form ported here:
Durbin-Levinson on the *unadjusted* ACF (each lag divided by the window's
own c0, not by n - lag), matching statsmodels'
`pacf(..., method="ywm")` rather than its historical default
(`method="ywadjusted"`), measured in docs/measure_diff1_pacf5.py.
PandasTa issue #151.

Only the `diff1y_pacf5` line is ported; the companion `diff1y_acf5` (sum of
squares of the plain ACF, not partial) is a separate candidate
(`kats_diff1_acf5_100`), not ported here.

Causal: bar T reads closes T - length + 1 .. T. Scale-free: log returns are
logs of price ratios, exact under a x8/x64 rescale; partial autocorrelation
is a ratio of covariances, unaffected by a constant price factor. A window
with a close that is NaN, infinite, zero, negative or subnormal (below
2.2e-308), or a price ratio that overflows, is NaN. So is a window whose
returns do not vary beyond the rounding of log(c / c1): standard deviation
at most 64 machine epsilons times (1 + the window's largest |log return|),
about 1.4e-14 for ordinary returns -- the same guard diff2_acf1 uses, one
differencing level earlier. Each window is computed on its own, in chunks,
so memory does not grow with n * length.

Calculation:
    Default Inputs:
        length=100
    r = LN(close / close.shift(1))            (the window's length - 1 log returns)
    x = r - MEAN(r)
    rho[k] = SUM(x[t] * x[t-k]) / SUM(x^2)     for k = 1..5
    phi[k,k] = Durbin-Levinson recursion on rho[1..5]
    DIFF1PACF5 = SUM(phi[k,k]^2, k = 1..5)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 14 (the shortest input Kats'
        own call returns a value on); a smaller or missing value falls
        back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: DIFF1PACF5_{length}, in [0, 5)
"""
