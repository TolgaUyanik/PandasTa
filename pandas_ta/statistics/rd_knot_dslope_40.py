# -*- coding: utf-8 -*-
"""Slope change at the best one-knot spline break, trailing 40 bars --
issue #175 (RD-KNOT-DSLOPE-40). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:smxy8i (2022-02-07) https://www.reddit.com/r/algotrading/comments/smxy8i/.
The same post as issue #166's `rd_knot_pos_40` (`pandas_ta/statistics/rd_knot_pos_40.py`):
that port ships WHERE the best knot sits (its age); this port ships HOW
MUCH the fitted slope changes there -- the hinge coefficient itself, on log
close, i.e. the change in log return per bar.

POSTER'S WORDS (tier 4, untested by the poster): "Linear splines with 1
knot. Fit that model while trying all possible values for the knot and
record the mean squared error in each knot/model." Claimed use: locate
where a trend changes slope -- NOT independently tested here; this port
ships existence (causal, scale-free, reachable on real data), not evidence
that it predicts anything.

GATE A -- the issue's own formula, read bar-by-bar (not the screen
prototype; the issue's instruction is "Gate A starts from the source
formula, not the prototype"):
    For a trailing window of `length` bars of y = LN(close), t = 0..length-1
    (t=0 the oldest bar in the window, t=length-1 the current bar), and a
    candidate knot k in [knot_margin, length-1-knot_margin]:
        model_k(t) = a_k + b_k*t + c_k*MAX(t - k, 0)      (continuous hinge)
    fit a_k, b_k, c_k by ordinary least squares over the window;
        SSE_k = SUM((y - model_k)^2)
    Every model has the same 3 free parameters over the same `length` points,
    so MSE_k = SSE_k / (length - 3) is minimised by the same k that minimises
    SSE_k -- this port compares SSE directly, the same equivalence
    `rd_knot_pos_40` uses.
        best = argmin_k SSE_k
        RD_KNOT_DSLOPE_40 = c_best
    `b_k` is the slope BEFORE the knot and `b_k + c_k` the slope AFTER it, so
    `c_k` is exactly the slope CHANGE at the knot -- "change in log return
    per bar" per the issue's own scale-free form.
The knot search range [5, 34] at length=40 (knot_margin=5) is the issue's own
disclosed choice ("knots 5..34"), not the poster's words -- the issue's text
attributes it to the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_knot_dslope_40`), not to the Reddit post. Kept here as the `knot_margin`
default, not hard-coded, matching `rd_knot_pos_40`'s own convention.

CAUSALITY. Bar T's output reads only `LN(close[T-length+1 .. T])` -- the
trailing `length`-bar window ending AT T, nothing later.
`tests/test_rd_knot_dslope_40.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical whether or not the
frame's tail is an unrelated series) and a mutant that appends `.shift(-1)`
to the final write (reading one bar ahead): the real module leaks 0 bars
before J at every swept J; the mutant is live and leaks at a majority of the
same J (measured, docs/RdKnotDslope40Measured.md).

SCALE-FREE. The fitted hinge model has an intercept term `a_k`, with `t` and
`MAX(t-k,0)` as the OTHER two design columns. In exact arithmetic, for a
design matrix `X` whose first column is exactly the all-ones vector, OLS
coefficients are given by `pinv(X) @ y`; adding a constant `d*1` to `y` adds
`d * (pinv(X) @ 1)` to the fitted coefficients, and `pinv(X) @ 1 = e_1` (the
intercept unit vector) exactly, because `1` is literally `X`'s own first
column and `pinv(X) @ X = I` for a full-rank `X`. So shifting every `y` in
the window by a constant moves ONLY the intercept `a_k` -- `b_k` and `c_k`
(hence every knot's SSE, the argmin knot, AND the reported `c_best` itself)
are all exactly unchanged IN EXACT ARITHMETIC. A positive price rescale by
a constant `m` adds the constant `LN(m)` to every `y = LN(close)` in the
window, so `RD_KNOT_DSLOPE_40` is scale-invariant algebraically.
⚠ Unlike a port whose arithmetic is a single ratio (e.g. `rd_gap_fill`'s
`open/close[1]`, exactly reproducible bit-for-bit under a power-of-two
rescale), `LN` is evaluated by libm's own transcendental routine: computing
`LN(close*k)` is NOT the same floating-point operation as computing
`LN(close) + LN(k)`, even when `k` is an exact power of two, so this port is
NOT claimed bit-identical under ANY rescale, including x8/x64 -- that would
overstate what floating-point `LN` guarantees. Measured in
`tests/test_rd_knot_dslope_40.py` and `docs/measure_rd_knot_dslope_40.py`
on a 1,600-bar synthetic frame (1,561 co-finite cells): max absolute
difference ~1.8e-15 and max relative difference ~8e-13 under x8/x64, x10
and x3.7 alike -- all four land at the same noise floor, consistent with
the algebraic invariance argument above holding up to `LN`'s own rounding,
not with a weaker, scale-dependent error.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from pandas_ta.utils import get_offset, verify_series


def _hinge_basis(length, knot_margin):
    """For every candidate knot k in [knot_margin, length-1-knot_margin], the
    (length, length) residual-maker M_k = I - X_k @ pinv(X_k) of the
    continuous one-knot hinge design X_k = [1, t, MAX(t-k, 0)], t = 0..length-1,
    and the pseudoinverse row `pinv(X_k)[2]` that maps a window of y onto the
    OLS hinge coefficient c_k. A pure function of (length, knot_margin) -- the
    same basis fits every window of a call, so it is built once per call,
    not once per window."""
    t = np.arange(length, dtype=float)
    knots = np.arange(knot_margin, length - knot_margin)
    basis = np.empty((len(knots), length, length))
    coef_row = np.empty((len(knots), length))
    for i, k in enumerate(knots):
        hinge = np.maximum(t - k, 0.0)
        X = np.column_stack([np.ones(length), t, hinge])
        P = np.linalg.pinv(X)
        basis[i] = np.eye(length) - X @ P
        coef_row[i] = P[2]
    return knots, basis, coef_row


def _knot_dslope(windows, knots, basis, coef_row):
    """windows: (rows, length) causal windows, oldest bar first. Returns the
    OLS hinge coefficient of the lowest-SSE knot for each row, NaN where the
    window holds a non-finite value (such a row's SSE and argmin are
    meaningless, so they are discarded rather than trusted)."""
    valid = np.all(np.isfinite(windows), axis=1)
    n_knots = len(knots)
    sse = np.empty((windows.shape[0], n_knots))
    for i in range(n_knots):
        resid = windows @ basis[i].T
        sse[:, i] = np.einsum("ij,ij->i", resid, resid)
    best = sse.argmin(axis=1)
    dslope_all = windows @ coef_row.T  # (rows, n_knots): every candidate knot's own hinge coefficient
    dslope = dslope_all[np.arange(len(windows)), best]
    return np.where(valid, dslope, np.nan)


def rd_knot_dslope_40(close, length=None, knot_margin=None, offset=None, **kwargs):
    """Indicator: Slope Change at the Best One-Knot Spline Break (RD_KNOT_DSLOPE)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 40
    knot_margin = int(knot_margin) if knot_margin and knot_margin > 0 else 5
    if length - 2 * knot_margin < 1:
        raise ValueError(
            f"rd_knot_dslope_40: knot_margin={knot_margin} leaves no candidate "
            f"knot inside length={length}"
        )
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    log_close = np.log(close.to_numpy(dtype=float))
    n = len(log_close)
    out = np.full(n, np.nan)

    if n >= length:
        knots, basis, coef_row = _hinge_basis(length, knot_margin)
        windows = sliding_window_view(log_close, length)  # (n-length+1, length), causal, oldest-first
        out[length - 1:] = _knot_dslope(windows, knots, basis, coef_row)

    result = pd.Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            result = result.ffill()
        elif method in ("bfill", "backfill"):
            result = result.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    result.name = f"RD_KNOT_DSLOPE_{length}_{knot_margin}"
    result.category = "statistics"

    return result


rd_knot_dslope_40.__doc__ = \
"""Slope Change at the Best One-Knot Spline Break (RD_KNOT_DSLOPE)

Over a trailing window of `length` bars of log close, fits a continuous
one-knot piecewise-linear ("hinge") model for every candidate knot position
and keeps the knot with the lowest mean-squared error, then reports that
knot's hinge coefficient -- the change in the fitted slope (log return per
bar) right at the break. A Reddit crowd-talk definition (tier 4, untested by
the poster, issue #175): "fit a continuous one-knot piecewise line for every
knot, keep the lowest-MSE knot," claimed use is locating where a trend
changes slope -- NOT independently tested here; this port ships existence
(causal, scale-free, reachable on real data), not evidence it predicts
anything. Shares its knot search with the sibling port `rd_knot_pos_40`
(issue #166), which reports the knot's AGE instead of its slope change. See
the module source above for the full source citation, Gate A derivation and
the causality/scale-free argument; docs/RdKnotDslope40Measured.md has the
measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:smxy8i
    (2022-02-07) https://www.reddit.com/r/algotrading/comments/smxy8i/

Calculation:
    Default Inputs:
        length=40, knot_margin=5
    y = LN(close)
    for each window of `length` bars (t = 0..length-1, t=0 oldest):
        for each knot k in [knot_margin, length-1-knot_margin]:
            model_k(t) = OLS fit of y on [1, t, MAX(t-k, 0)] -> coefficients a_k, b_k, c_k
            SSE_k = SUM((y - model_k)^2)
        best = argmin_k SSE_k
    RD_KNOT_DSLOPE = c_best

Args:
    close (pd.Series): Series of 'close's
    length (int): The rolling window. Default: 40
    knot_margin (int): Candidate knots are restricted to
        [knot_margin, length-1-knot_margin], keeping at least knot_margin
        points on each side of the break for a stable fit. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_KNOT_DSLOPE_{length}_{knot_margin}, a scale-free
        (dimensionless, in log-return-per-bar units) continuous value, sign
        and magnitude both meaningful (positive = slope steepens upward at
        the break, negative = it flattens or reverses). NaN for the first
        `length - 1` bars (the rolling window's warm-up) and for any window
        containing a non-finite log close.
"""
