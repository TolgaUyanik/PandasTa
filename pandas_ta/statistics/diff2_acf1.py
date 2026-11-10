# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window whose return changes have a standard deviation of at most
# NOISE_ULPS machine epsilons times (1 + its largest |log return|) varies
# only by the rounding of log(c / c1): no variation.
NOISE_ULPS = 64
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk


def _acf1_rows(d, rmax):
    """Lag-1 autocorrelation of each row of `d`, as statsmodels
    `acf(d, fft=True)[1]` defines it: acovf[1] / acovf[0] with the row
    demeaned once by its own full mean (the two divisors n cancel)."""
    x = d - d.mean(axis=1, keepdims=True)
    den = (x * x).sum(axis=1)
    num = (x[:, 1:] * x[:, :-1]).sum(axis=1)
    # No variation, or variation at floating-point rounding level (a steady
    # drift of any size, a flat price jittering by one ulp): the ratio would
    # be the autocorrelation of rounding noise. The rounding of log(c / c1)
    # is absolute -- about eps * (1 + |r|) -- so the floor is too. NaN.
    sd = np.sqrt(den / d.shape[1])
    real = sd > NOISE_ULPS * np.finfo(float).eps * (1.0 + rmax)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(real, num / den, np.nan)


def diff2_acf1(close, length=None, offset=None, **kwargs):
    """Indicator: Lag-1 autocorrelation of return changes (DIFF2ACF1)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= 10 else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c > 0), c, np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        r = np.log(c[1:] / c[:-1])  # diff of log close; exact under a x2^k rescale
        r[~np.isfinite(r)] = np.nan  # a ratio that overflows or underflows: missing
    d2 = r[1:] - r[:-1]  # diff(diff(log close)): the change of the log return

    # Bar T reads closes T - length + 1 .. T: length - 1 log returns and
    # length - 2 return changes. One window at a time, evaluated in chunks so
    # memory does not grow with n * length. A window holding a NaN is NaN.
    m = length - 2
    win = sliding_window_view(d2, m)
    rabs = sliding_window_view(np.abs(r), m + 1)
    step = max(1, CHUNK_CELLS // m)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _acf1_rows(chunk[ok], rabs[start:start + step][ok].max(axis=1))
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    acf1 = Series(values, index=close.index)

    # Offset
    if offset != 0:
        acf1 = acf1.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        acf1.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    acf1.name = f"DIFF2ACF1_{length}"
    acf1.category = "statistics"

    return acf1


diff2_acf1.__doc__ = \
"""Lag-1 autocorrelation of return changes (DIFF2ACF1)

The lag-1 autocorrelation of the twice-differenced log close over a rolling
window: difference log price once to get log returns, again to get the
change of the return from one bar to the next, and correlate that change
with its own previous value.

For returns with no memory it sits near -0.5, not 0: differencing an
uncorrelated series makes consecutive changes share a term with opposite
signs. In population it is (2*rho1 - 1 - rho2) / (2 * (1 - rho1)) for
return autocorrelations rho1, rho2 -- for AR(1) returns, -(1 - phi) / 2 --
so it reads above -0.5 when returns trend and below when they reverse.

Measured (docs/Diff2Acf1Measured.md): it ranks bars almost exactly as that
identity evaluated on the window's own lag-1 and lag-2 sample return
autocorrelations does (Spearman 0.99), so it carries the information of
those two autocorrelations and little else; against lag-1 alone the
Spearman is 0.61 to 0.71. Its centre does not move with volatility
clustering or fat tails (GARCH and Student-t returns read a median of
-0.49, as iid normal returns do).

Source: Kats tsfeatures (Meta, MIT), `get_acfpacf_features` ->
`diff2y_acf1` (`kats/tsfeatures/tsfeatures.py` L1049-1151, L973-975 at
commit a6b7e88): `acf(diff2x, fft=True, nlags=nlag)[1:][0]` with
`diff2x = diff(diff(x))`, after Hyndman's tsfeatures `diff2_acf1`.
statsmodels 0.15.0 `tsa/stattools.py`: `acf` L847-1060 (acovf / acovf[0]),
`acovf` L488-623 (demeaned once, divisor n). Kats applies it to a whole
series; the 100-bar window and log close as the input are the choices of
the 2026-10-25 screen prototype (candidate kats_diff2_acf1_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine).
PandasTa issue #153.

Causal: bar T reads closes T - length + 1 .. T. Scale-free: log returns are
logs of price ratios, exact under a x8/x64 rescale. A window with a NaN,
zero or negative close, or a price ratio that overflows, is NaN. So is a
window whose return changes do not vary beyond the rounding of
log(c / c1): standard deviation at most 64 machine epsilons times
(1 + the window's largest |log return|), about 1.4e-14 for ordinary
returns. That covers a flat price, a steady drift of any size, a
constant return change, and a flat price jittering by one ulp; Kats
returns NaN only when that variance is exactly 0 and otherwise reports the
autocorrelation of the rounding noise. Each window is computed on its own,
in chunks, so memory does not grow with n * length.

Calculation:
    Default Inputs:
        length=100
    r = LN(close / close.shift(1))          (the window's length - 1 log returns)
    d = r - r.shift(1)                      (length - 2 return changes)
    x = d - MEAN(d)
    DIFF2ACF1 = SUM(x[t] * x[t-1]) / SUM(x^2)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 10 (Kats' own minimum); a
        smaller or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: DIFF2ACF1_{length}, in (-1, 1)
"""
