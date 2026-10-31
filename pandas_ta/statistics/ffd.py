# -*- coding: utf-8 -*-
from numpy import abs as npabs, errstate, full, isfinite, log, nan
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series
from pandas_ta.utils import get_offset, verify_series

_MAX_WIDTH = 20000  # safety cap; d close to 0 with a tiny threshold decays too slowly to be usable anyway


def _ffd_weights(d, threshold):
    """AFML Snippet 5.1 (getWeights_FFD): the binomial-series weights of
    (1 - x)^d, truncated the moment a weight's magnitude drops below
    `threshold`. w[0] is the lag-0 (current bar) weight; w[-1] the most-lagged
    one kept. Data-independent -- it is a function of (d, threshold) only, so
    the window it defines cannot leak the future.

    The raw AFML weights do not sum to zero (truncation stops a decaying
    series early). This re-centres them by moving the whole residual onto
    the most-lagged weight -- the smallest in magnitude, so this is the
    minimal single-weight correction -- so sum(w) is zero to float
    precision. See the module docstring, decision 1."""
    w = [1.0]
    k = 1
    while True:
        wk = -w[-1] * (d - k + 1) / k
        if npabs(wk) < threshold:
            break
        if k > _MAX_WIDTH:
            raise ValueError(f"ffd: d={d}, threshold={threshold} needs > {_MAX_WIDTH} weights to decay below threshold")
        w.append(wk)
        k += 1
    w[-1] -= sum(w)
    return w


def ffd(close, d=None, threshold=None, offset=None, **kwargs):
    """Indicator: AFML Fixed-Width Window Fractional Differencing (FFD)"""
    # Validate Arguments
    d = 0.4 if d is None else float(d)
    threshold = 1e-4 if threshold is None else float(threshold)
    if not (isfinite(d) and 0 < d < 1):
        raise ValueError(f"ffd: need 0 < d < 1; got {d}")
    if not (isfinite(threshold) and threshold > 0):
        raise ValueError(f"ffd: need threshold > 0; got {threshold}")
    w = _ffd_weights(d, threshold)
    width = len(w)
    close = verify_series(close, width + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result. y is log price relative to the first usable (finite,
    # positive) close, not raw log price: under a power-of-two rescale the
    # ratio is bit-identical (correctly-rounded division cancels the common
    # factor exactly), so y does not move at all and the scale test is exact
    # regardless of any residual weight-sum rounding. See the module
    # docstring, decision 1.
    vals = close.to_numpy(dtype=float)
    mask = isfinite(vals) & (vals > 0)
    usable = vals[mask]
    if len(usable) <= width: return
    anchor = usable[0]
    with errstate(divide="ignore", invalid="ignore"):
        y = log(vals / anchor)
    y[~mask] = nan

    n = len(y)
    out = full(n, nan)
    win = sliding_window_view(y, width)  # win[i] = y[i : i + width], oldest (lag width-1) .. newest (lag 0)
    coef = w[::-1]  # coef[j] = w[width-1-j], the lag matching win[i, j]
    with errstate(invalid="ignore"):
        out[width - 1:] = win @ coef

    ffd = Series(out, index=close.index)

    # Offset
    if offset != 0:
        ffd = ffd.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        ffd.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    ffd.name = f"FFD_{d}_{threshold}"
    ffd.category = "statistics"

    return ffd


ffd.__doc__ = \
"""AFML Fixed-Width Window Fractional Differencing (FFD)

A rolling linear filter of log price that keeps more memory than a one-bar
return: `FFD_t = sum_{k=0}^{W-1} w_k * y_{t-k}`, where `y = log(close /
anchor)` and the weights `w_k` are the binomial-series coefficients of
`(1 - x)^d` (AFML Snippet 5.1, `getWeights_FFD`), truncated the moment
`|w_k|` drops below `threshold` and then re-centred (decision 1 below). `d`
close to 0 keeps almost all of the series' memory (and is close to log
price itself); `d` close to 1 is close to a one-bar log return. AFML's own
worked example picks the smallest `d` whose FFD series passes an ADF
stationarity test.

Source: Lopez de Prado, *Advances in Financial Machine Learning* (2018),
ch. 5 "Fractionally Differentiated Features", Snippets 5.1-5.2. PandasTa
issue #13.

Two problems the book's own recipe does not solve, and this port's answers:

1.  **The truncated weights do not sum to zero.** Truncation stops a
    decaying series early, leaving a fixed non-zero `s = sum(w_k)` for a
    given `(d, threshold)` -- see docs/FfdMeasured.md for its measured
    value before correction. Left alone, `s != 0` causes two failures, not
    one: `FFD(log(c * close)) = FFD(log close) + log(c) * s` is not
    scale-free, AND because a window's constant term never cancels, the
    series is shifted by `log(reference) * s` for whatever reference the
    log price happens to be measured from -- which, if that reference is
    the window's own first bar, makes the output depend on where the
    caller's series happens to start. Measured directly, raw weights vs
    re-centred at the SAME (d=0.4, threshold=1e-5): slicing 100/500/900
    bars into a 4,000-bar synthetic walk and re-anchoring moves the
    filtered value, vs the un-sliced run, by 1.3e-02 / 4.7e-02 / 6.3e-02
    with the raw weights and by 1.1e-15 / 1.3e-15 / 1.3e-15 with the
    weights `_ffd_weights` actually ships -- both printed by
    `docs/measure_ffd_proxy.py`'s "Gate D defect" block, which runs both
    weight vectors through the identical slice experiment so the
    before/after numbers are comparable. `_ffd_weights`
    re-centres by moving the whole residual `s` onto the most-lagged kept
    weight (the smallest in magnitude, the minimal single-weight fix), so
    `sum(w) = 0` to float precision; a constant added to the whole input
    series (any reference, any anchor) now contributes `0 * constant = 0`
    to the output instead of `s * constant`. This also fixes the anchor
    dependence above, since that bug was `s != 0` acting on a per-call
    constant, not a defect of the anchor device itself.
    On top of the re-centred weights, this port still measures `y = log(close
    / anchor)` (`anchor` the series' first finite positive close, the same
    device `kalman_trend` uses) rather than raw log price: a power-of-two
    price rescale leaves the close/anchor ratio bit-identical (correctly-
    rounded division cancels an exact common factor, regardless of `sum(w)`),
    so x8/x64 is exact rather than merely small. Re-centring alone would
    only get x8/x64 to the ~1e-15 floating-point noise floor of evaluating
    `log` on two different numbers that happen to differ by an exact power
    of two -- still well inside this repo's 1e-9 tolerance band, but the
    ratio device makes it exact instead of small, at no extra cost.
2.  **Causality of `d`.** AFML's own worked example picks the smallest `d`
    whose FFD series passes an ADF test on the FULL sample -- a look-ahead.
    This port makes `d` a FIXED parameter the caller supplies (default 0.4,
    AFML's own examples put the ADF-passing `d` for a daily equity/futures
    series in roughly the 0.3-0.5 range); it is never estimated from the
    series being transformed. A trailing-window ADF-based picker was not
    built: it is a second indicator's worth of machinery, and CLAUDE.md asks
    for the narrowest change, not a generic re-estimation layer.

Causal: bar T reads bars `T - W + 1 .. T` only, where `W` is the number of
weights `_ffd_weights` keeps -- a function of `(d, threshold)` alone, so it
cannot depend on the data. Scale-free: bit-identical under x8/x64, within
tolerance under x10/x3.7. A window with a non-finite, zero or negative
close is NaN, and so is any window containing one.

The default `threshold=1e-4` trades a little weight-tail precision (AFML's
own worked example uses 1e-5) for a usable window: 1e-5 needs 1,458 bars
just to emit a first value -- almost 6 years of daily bars -- and does not
fit this repo's 600-bar live-probe frame at all (measured; 1e-4 needs 282).
A caller who wants AFML's own cutoff can still pass `threshold=1e-5`.

Memory: every window is held at once, about 8 * n * width bytes (~45 MB at
n = 20,000 bars, width = 282 -- the default `d, threshold`'s measured
width). To bound it on a long history, call it on chunks that each start
`width - 1` bars early.

Calculation:
    Default Inputs:
        d=0.4, threshold=1e-4
    y = log(close / first finite positive close)
    w_0 = 1; w_k = -w_{k-1} * (d - k + 1) / k, kept while |w_k| >= threshold;
        w_last -= sum(w)
    FFD_t = sum_k w_k * y_{t-k}

Args:
    close (pd.Series): Series of 'close's
    d (float): Differencing order, 0 < d < 1. Fixed -- never fit on the
        series. Default: 0.4
    threshold (float): Weight-truncation cutoff, > 0. Default: 1e-4
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: FFD_{d}_{threshold}
"""
