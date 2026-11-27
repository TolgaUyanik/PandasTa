# -*- coding: utf-8 -*-
"""Last-bar residual of a 20-bar quadratic fit, in residual sd -- issue #180
(RD-QUADFIT-RESID-20). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:vgulql (2022-06-20) https://www.reddit.com/r/algotrading/comments/vgulql/.

POSTER'S WORDS (tier 4, untested by the poster): "(observed - predicted) of a
2nd-order polynomial fit on a trailing window." Claimed use: "The reason this
works for breakpoint detection is that a sudden reversal can not be captured
by a low order polynomial" -- detect a trend reversal when the fit error
grows -- NOT independently tested here; this port ships existence (causal,
scale-free, reachable on real data), not evidence it predicts anything.

GATE A -- the issue's own formula, read bar-by-bar (not the screen prototype;
the issue's own instruction is "Gate A starts from the source formula, not
the prototype"):

    For a trailing window of `length` bars of y = LN(close), t = 0..length-1
    (t=0 the oldest bar in the window, t=length-1 the current bar):
        model(t) = a + b*t + c*t^2      (ordinary least squares)
        residual(t) = y(t) - model(t)
        RD_QUADFIT_RESID_20 = residual(length-1) / STDEV(residual(0..length-1))

STDEV here is the POPULATION standard deviation (ddof=0, numpy's own
`.ndarray.std()` default) over the window's own `length` residuals, not
pandas' ddof=1 default -- the poster's words give the model and the residual
but not an estimator for "residual sd," so this port reads it off the one
concrete recipe the issue discloses: the screen prototype's own
`_quad_resid` helper (`docs/issues/screen/ind_screen_r6.py`), `R.std(1)`,
numpy's default ddof=0. The issue's own "scale-free form" clause --
"on log close, 20 bars; residual over the window's residual sd" -- is this
same disclosed recipe, not the poster's words, matching how issue #179's
"p = 20" / "3p" substitution and issue #166's "40 bars, knots 5..34" were
each read off the prototype rather than the Reddit post.

A length < 4 leaves fewer than one residual degree of freedom for a
quadratic's 3 fitted parameters (length=3 fits every window exactly, so
every residual -- and the sd dividing them -- is always exactly zero,
`0/0 = NaN` on every bar); this port raises rather than silently emitting
an all-NaN column.

NON-REDUNDANCY. Gate E run `is180-rd_quadfit_resid_20-2e3d7c9e` (2026-11-27,
89 ALTPORT-1 frames, 687 comparators, this module's current sha1) put this
column's nearest comparator at `cfo_ta_Pctl` (max |rho| 0.834300363578934,
n = 392,886, perframe max median 0.8356157515953884) -- an already-shipped
momentum-family column this fork carries (`pandas_ta.momentum.cfo`), read
here as evidence the new column sits in the same neighbourhood as existing
ones, not as evidence it restates one exactly (DISCLOSE_GAP, below the 0.90
STRUCK line). This reproduced the screen prototype's own measurement (issue
#180) to the digit; recorded in `docs/gate_e_ledger.csv`
(docs/RdQuadfitResid20Measured.md).
A stage-2 fork-overlap check (not Gate E) on scale-free `Category` outputs
at defaults put the nearest comparator at `cfo:CFO_9` (0.8313) -- again
below the 0.90 restatement line.

CAUSALITY. Bar T's output reads only `LN(close[T-length+1 .. T])` -- the
trailing `length`-bar window ending AT T, nothing later; the design matrix
`X = [1, t, t^2]` and its residual-maker `M = I - X @ pinv(X)` are a pure
function of `length`, built once per call, not derived from the data.
`tests/test_rd_quadfit_resid_20.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical regardless of what
the frame's tail past J is replaced with) and a look-ahead mutant
(`importlib`-read source, the final `pd.Series` construction given a
`.shift(-1)` before being returned, `exec`'d in memory -- never a
hand-written copy): the real module leaks 0 bars at every swept J; the
mutant is live and leaks at a majority of the same J
(docs/RdQuadfitResid20Measured.md has the measured counts).

SCALE-FREE. The fitted quadratic has an intercept term `a`, so in EXACT
(real-number) arithmetic the OLS residual vector of ANY window is invariant
to any additive shift of `y`: shifting every `y` in the window by a
constant only moves the fitted intercept, leaving every residual -- and so
the output ratio, a residual over its own window's residual sd --
unchanged. A positive price rescale by a constant `k` adds the constant
`LN(k)` to every `y = LN(close)` in the window, so `RD_QUADFIT_RESID_20` is
scale-invariant mathematically, the same argument `rd_knot_pos_40`
(`pandas_ta/statistics/rd_knot_pos_40.py`) makes for its own intercept-
carrying hinge fit.

⚠ `LN` is evaluated by libm's own transcendental routine: computing
`LN(close*k)` is NOT the same floating-point operation as computing
`LN(close) + LN(k)`, even when `k` is an exact power of two -- so feeding
the fit `LN(close)` directly (an earlier version of this module did) could
only be measured to a tiny tolerance (~5e-9 relative), not claimed
bit-identical, under any rescale. This module instead feeds the fit
`y = LN(window / window's own first close)` -- the ratio-to-first-bar
device `level_shift_size` (`pandas_ta/statistics/level_shift_size.py`)
uses for the same reason, also adopted by the sibling port
`rd_knot_dslope_40` (`pandas_ta/statistics/rd_knot_dslope_40.py`) after an
identical "`log` is transcendental" defence was tried and rejected there
(`docs/RdKnotDslope40Measured.md`): under an exactly-representable rescale
by `k`, both the numerator and the denominator of the ratio are multiplied
by the same exact factor (a power-of-two multiply is exact, only the
exponent shifts), so IEEE-754 division returns bit-identical results, and
`LN` of a bit-identical input returns a bit-identical output. Since OLS is
invariant to the per-window additive shift this ratio introduces (see
above), the reported residual ratio is bit-identical under x8/x64 --
measured, not merely argued: max absolute difference 0.0 on every
co-finite cell
(`tests/test_rd_quadfit_resid_20.py::test_power_of_two_scale_is_bit_identical`,
`docs/measure_rd_quadfit_resid_20.py`). Under a non-power-of-two rescale
(x10, x3.7) the division itself is no longer exact, so those stay a
tiny-tolerance claim (measured in `test_other_scales_stay_within_a_tiny_tolerance`).
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from pandas_ta.utils import get_offset, verify_series


def _quad_basis(length):
    """(length, length) residual-maker M = I - X @ pinv(X) for the
    quadratic design X = [1, t, t**2], t = 0..length-1 -- a pure function
    of `length`, built once per call (the design is the same for every
    window of a call, not once per window)."""
    t = np.arange(length, dtype=float)
    X = np.column_stack([np.ones(length), t, t ** 2])
    P = np.linalg.pinv(X)
    return np.eye(length) - X @ P


def _quad_resid(windows, M):
    """windows: (rows, length) causal windows, oldest bar first. Returns
    the last bar's OLS residual over the window's own residual sd
    (population, ddof=0), NaN where the window holds a non-finite value or
    the residual sd is exactly zero (a perfect quadratic fit has no scale
    to divide by)."""
    valid = np.all(np.isfinite(windows), axis=1)
    resid = windows @ M.T
    sd = resid.std(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = resid[:, -1] / sd
    ratio = np.where(sd == 0, np.nan, ratio)
    return np.where(valid, ratio, np.nan)


def rd_quadfit_resid_20(close, length=None, offset=None, **kwargs):
    """Indicator: Last-Bar Residual of a Quadratic Fit, in Residual SD (RD_QUADFIT_RESID)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    if length < 4:
        raise ValueError(
            f"rd_quadfit_resid_20: length={length} leaves fewer than one "
            f"residual degree of freedom for a 3-parameter quadratic fit "
            f"(need length >= 4)"
        )
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    close_values = close.to_numpy(dtype=float)
    n = len(close_values)
    out = np.full(n, np.nan)

    if n >= length:
        M = _quad_basis(length)
        raw_windows = sliding_window_view(close_values, length)  # (n-length+1, length) raw close, causal, oldest-first
        # log(close / the window's own first close), not log(close) directly --
        # the ratio-to-first-bar device `level_shift_size` uses: under a
        # power-of-two price rescale both operands scale by the same exactly-
        # representable factor, so the ratio (and hence every y) is bit-identical.
        with np.errstate(invalid="ignore", divide="ignore"):
            windows = np.log(raw_windows / raw_windows[:, :1])
        out[length - 1:] = _quad_resid(windows, M)

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
    result.name = f"RD_QUADFIT_RESID_{length}"
    result.category = "statistics"

    return result


rd_quadfit_resid_20.__doc__ = \
"""Last-Bar Residual of a Quadratic Fit, in Residual SD (RD_QUADFIT_RESID)

Over a trailing window of `length` bars of log close, fits a 2nd-order
polynomial (quadratic) by ordinary least squares and reports the LAST bar's
residual (observed minus predicted), divided by the standard deviation of
all `length` residuals in that same window. A Reddit crowd-talk definition
(tier 4, untested by the poster, issue #180): "(observed - predicted) of a
2nd-order polynomial fit on a trailing window," claimed use is detecting a
trend reversal when a low-order fit's error grows ("a sudden reversal can
not be captured by a low order polynomial") -- NOT independently tested
here; this port ships existence (causal, scale-free, reachable on real
data), not evidence it predicts anything. See the module source above for
the full source citation, the Gate A derivation (why the residual sd is
population, ddof=0) and the causality/scale-free argument;
docs/RdQuadfitResid20Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:vgulql
    (2022-06-20) https://www.reddit.com/r/algotrading/comments/vgulql/

Calculation:
    Default Inputs:
        length=20
    y = LN(close)
    (implemented as y = LN(close / the window's first close) -- the same
    fit, since the intercept makes OLS residuals invariant to a per-window
    additive shift, and it makes a power-of-two rescale bit-identical)
    for each window of `length` bars (t = 0..length-1, t=0 oldest):
        a, b, c = OLS fit of y on [1, t, t**2]
        resid(t) = y(t) - (a + b*t + c*t**2)
    RD_QUADFIT_RESID = resid(length-1) / STDEV(resid(0..length-1), ddof=0)
    (0/0 from an exactly-zero residual sd -> NaN)

Args:
    close (pd.Series): Series of 'close's
    length (int): The quadratic fit's trailing window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_QUADFIT_RESID_{length}, a scale-free (dimensionless)
        z-score-like ratio, unbounded. NaN for the first `length - 1` bars
        (the rolling window's warm-up), for any window containing a
        non-finite log close, and for any window whose fit is exact
        (residual sd exactly zero).
"""
