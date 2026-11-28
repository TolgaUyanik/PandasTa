# -*- coding: utf-8 -*-
"""Age of the best one-knot spline break, trailing 40 bars -- issue #166
(RD-KNOT-POS-40). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:smxy8i (2022-02-07) https://www.reddit.com/r/algotrading/comments/smxy8i/.

POSTER'S WORDS (tier 4, untested by the poster): "Linear splines with 1 knot.
Fit that model while trying all possible values for the knot and record the
mean squared error in each knot/model." Claimed use: locate where a trend
changes slope -- NOT independently tested here; this port ships existence
(causal, scale-free, reachable on real data), not evidence that it predicts
anything.

GATE A -- the issue's own formula, read bar-by-bar (not the screen prototype;
the issue's instruction is "Gate A starts from the source formula, not the
prototype"):
    For a trailing window of `length` bars of y = LN(close), t = 0..length-1
    (t=0 the oldest bar in the window, t=length-1 the current bar), and a
    candidate knot k in [knot_margin, length-1-knot_margin]:
        model_k(t) = a_k + b_k*t + c_k*MAX(t - k, 0)      (continuous hinge)
    fit a_k, b_k, c_k by ordinary least squares over the window;
        SSE_k = SUM((y - model_k)^2)
    Every model has the same 3 free parameters over the same `length` points,
    so MSE_k = SSE_k / (length - 3) is minimised by the same k that minimises
    SSE_k -- this port compares SSE directly, per the issue's own equivalence.
        best = argmin_k SSE_k
        RD_KNOT_POS_40 = (length - 1 - best) / (length - 1)
    0 would mean the lowest-MSE knot sits at the current bar (a break just
    now); 1 would mean it sits at the window's oldest usable knot position
    -- neither endpoint is ever actually reached, since `knot_margin`
    restricts `best` to [knot_margin, length-1-knot_margin]: at the
    defaults below, the reachable range is [5/39, 34/39] = [0.1282, 0.8718].
The knot search range [5, 34] at length=40 (knot_margin=5) is the issue's own
disclosed choice ("knots 5..34"), not the poster's words -- the issue's text
attributes it to the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_knot_pos_40`), not to the Reddit post. Kept here as the `knot_margin`
default, not hard-coded, matching the fork's convention for every other
rolling-window parameter (`rd_gap_fill_rate_60`'s `length`/`min_gap`).

CAUSALITY. Bar T's output reads only `LN(close[T-length+1 .. T])` -- the
trailing `length`-bar window ending AT T, nothing later.
`tests/test_rd_knot_pos_40.py` proves this with a future-splice probe (bars
before a perturbation point J stay bit-identical whether or not the frame's
tail is an unrelated series) and a mutant that appends `.shift(-1)` to the
final write (reading one bar ahead): the real module leaks 0 bars before J at
every swept J; the mutant is live and leaks at a majority of the same J
(measured, docs/RdKnotPos40Measured.md).

SCALE-FREE. The fitted model has an intercept term `a_k`, so in EXACT
arithmetic the SSE of every knot -- and therefore the knot that minimises
it -- is invariant to ANY additive shift of `y`: shifting every `y` by a
constant only moves the intercept, leaving every residual (hence every SSE)
unchanged. A positive price rescale by a constant `m` adds the constant
`LN(m)` to every `y = LN(close)` in the window, so `RD_KNOT_POS_40` is
scale-invariant by construction. Measured empirically in
`tests/test_rd_knot_pos_40.py` and `docs/measure_rd_knot_pos_40.py`: bit-
identical under an exact power-of-two rescale (x8, x64), and within a tiny
measured tolerance under a non-power-of-two rescale (x10, x3.7), where each
scaled `close` carries its own last-bit rounding before `LN` is even called.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from pandas_ta.utils import get_offset, verify_series


def _hinge_basis(length, knot_margin):
    """For every candidate knot k in [knot_margin, length-1-knot_margin], the
    (length, length) residual-maker M_k = I - X_k @ pinv(X_k) of the
    continuous one-knot hinge design X_k = [1, t, MAX(t-k, 0)], t = 0..length-1.
    A pure function of (length, knot_margin) -- the same basis fits every
    window of a call, so it is built once per call, not once per window."""
    t = np.arange(length, dtype=float)
    knots = np.arange(knot_margin, length - knot_margin)
    basis = np.empty((len(knots), length, length))
    for i, k in enumerate(knots):
        hinge = np.maximum(t - k, 0.0)
        X = np.column_stack([np.ones(length), t, hinge])
        P = np.linalg.pinv(X)
        basis[i] = np.eye(length) - X @ P
    return knots, basis


def _knot_age(windows, knots, basis, length):
    """windows: (rows, length) causal windows, oldest bar first. Returns the
    normalised age of the lowest-SSE knot for each row, NaN where the window
    holds a non-finite value (such a row's SSE and argmin are meaningless, so
    they are discarded rather than trusted)."""
    valid = np.all(np.isfinite(windows), axis=1)
    sse = np.empty((windows.shape[0], len(knots)))
    for i in range(len(knots)):
        resid = windows @ basis[i].T
        sse[:, i] = np.einsum("ij,ij->i", resid, resid)
    best = knots[sse.argmin(axis=1)]
    age = (length - 1 - best) / (length - 1)
    return np.where(valid, age, np.nan)


def rd_knot_pos_40(close, length=None, knot_margin=None, offset=None, **kwargs):
    """Indicator: Age of the Best One-Knot Spline Break (RD_KNOT_POS)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 40
    knot_margin = int(knot_margin) if knot_margin and knot_margin > 0 else 5
    if length - 2 * knot_margin < 1:
        raise ValueError(
            f"rd_knot_pos_40: knot_margin={knot_margin} leaves no candidate "
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
        knots, basis = _hinge_basis(length, knot_margin)
        windows = sliding_window_view(log_close, length)  # (n-length+1, length), causal, oldest-first
        out[length - 1:] = _knot_age(windows, knots, basis, length)

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
    result.name = f"RD_KNOT_POS_{length}_{knot_margin}"
    result.category = "statistics"

    return result


rd_knot_pos_40.__doc__ = \
"""Age of the Best One-Knot Spline Break (RD_KNOT_POS)

Over a trailing window of `length` bars of log close, fits a continuous
one-knot piecewise-linear ("hinge") model for every candidate knot position
and keeps the knot with the lowest mean-squared error, then reports how many
bars ago that knot sits, as a fraction of the window. A Reddit crowd-talk
definition (tier 4, untested by the poster, issue #166): "fit a continuous
one-knot piecewise line for every knot, keep the lowest-MSE knot," claimed
use is locating where a trend changes slope -- NOT independently tested
here; this port ships existence (causal, scale-free, reachable on real
data), not evidence it predicts anything. See the module source above for
the full source citation, Gate A derivation and the causality/scale-free
argument; docs/RdKnotPos40Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:smxy8i
    (2022-02-07) https://www.reddit.com/r/algotrading/comments/smxy8i/

Calculation:
    Default Inputs:
        length=40, knot_margin=5
    y = LN(close)
    for each window of `length` bars (t = 0..length-1, t=0 oldest):
        for each knot k in [knot_margin, length-1-knot_margin]:
            model_k(t) = OLS fit of y on [1, t, MAX(t-k, 0)]
            SSE_k = SUM((y - model_k)^2)
        best = argmin_k SSE_k
    RD_KNOT_POS = (length - 1 - best) / (length - 1)

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
    pd.Series: RD_KNOT_POS_{length}_{knot_margin}, a scale-free
        (dimensionless) fraction in [0, 1]. NaN for the first `length - 1`
        bars (the rolling window's warm-up) and for any window containing a
        non-finite log close.
"""
