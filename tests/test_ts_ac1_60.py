# -*- coding: utf-8 -*-
"""TS-AC1-60: `ts_ac1_60`, tsfresh's lag-1 autocorrelation on returns
(PandasTa issue #94).

    TS_AC1_60 = sum((x[i] - m)*(x[i-1] - m)) / ((60 - 1) * v), over a window
                of 60 simple returns, with `m` and `v` that window's mean and
                POPULATION variance -- tsfresh's `autocorrelation(x, lag=1)`

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **That the shipped column is the SOURCE formula and not the screen
   prototype.** The two are different statistics, and issue #94's own "Gates
   owed" line says Gate A starts from the source formula. The prototype,
   `corr(r, delay(r, 1), 60)`, is a Pearson correlation of two 60-pair slices
   over 61 returns: measured against it on a 1,500-bar walk, Spearman
   **0.988839**, max |difference| **0.1013**, bit-equal on **0 of 1,439**
   bars, first fired bar 60 here against 61 there. So issue #94's screen
   figures (Gate E max |rho| 0.2534 vs `mad_pct`) belong to a different
   column, which `test_the_prototype_is_a_different_statistic` exists to keep
   nobody from forgetting.

2. **Gate A, and that the formula under test is the ISSUE's line.** tsfresh
   is NOT installed in this worktree and web access is unavailable, so
   "tsfresh (MIT)" is an attribution, not an oracle. What IS checkable is
   pinned five ways:

   * an EXACT closed form: a window whose returns alternate between two
     values in equal counts is exactly **-1.0** for every `length` -- derived
     (each of the `length - 1` products is `-d**2`, the population variance
     is `d**2`) and bit-exact on `close = [1, 2, 1, 2, 1]` at `length` 4;
   * the reachable **bounds**, [-1.015601, +1.011559] at `length` 60,
     [-1.078689, +0.412023] at 4 and [-1.066103, +0.934726] at 10, computed
     as the extreme eigenvalues of the lag-1 product form on the demeaned
     subspace and attained by the module on the matching eigenvector window
     to 8.9e-16;
   * the source formula applied window by window with `sliding_window_view`,
     sharing no window machinery with the module: max |difference| 4.9e-15 on
     a walk, 2.8e-15 tick-rounded, 2.1e-15 on an AR(1) path, Spearman
     1.000000;
   * an exact rational oracle in `fractions.Fraction`: the module is 3.1e-15
     out on a walk against a `math.fsum` scalar loop's 1.0e-15, and on a path
     with `|mean| / sd` = 1e5 the module is 2.1e-10 where the plain raw-sum
     expansion of the same numerator is **4.1e-06**, which is why the
     numerator is spelled the way it is;
   * the prototype imported from the owner's own registry when the worktree
     has `docs/issues/` -- bit-equal to the retype on 1,439 of 1,439 bars.

3. **Gate B, by mutant, on three frames.** Six mutants, each `importlib`-read
   and `exec`'d in memory: the column back-dated by `length`; the return read
   one bar ahead; the window's oldest return read from the future; a
   `center=True` on the variance, on the mean, and on the squared-difference
   sum. Measured over 35 J values of a future-perturbation sweep: the real
   module leaks at **0/35** and all eighteen mutant-frame cells are
   **35/35** on a walk, a tick-rounded walk and an AR(1) path. The four
   `length`-dependent mutants are re-run at `length` 3 and 250, where the
   real module still leaks 0/35 and **six of the eight cells** are not 35/35,
   under three explanations: 31/35 in all four `length` 250 cells (the four
   offsets below its warm-up), 22/35 for the centred variance at `length` 3
   (a one-bar look-ahead whose only reachable bar is NaN in both runs at 13
   offsets), and 0/35 for the centred squared-difference sum at `length` 3
   (a 2-wide window, which pandas centres by 0 bars, so the mutation is a
   no-op). Each explanation is asserted, not argued.

4. **The two guards, both of which change the column.**
   * The variance floor is 4096 eps SQUARED (8.27e-25), not tsfresh's
     `np.isclose(var, 0)`. That guard is absolute at numpy's default
     `atol = 1e-8`, so it empties any window whose return sd is below 1e-4:
     measured, it reports on **0 of 240** windows of a sigma = 1e-6 walk
     where this column reports on all 240 and reads +-0.27. Both agree that a
     flat frame and a 1%-a-bar geometric ladder are empty, where an
     unguarded spelling reports 240 of the ladder's windows up to **0.8328**
     out of float rounding alone.
   * The accumulator trust test. `rolling.var` and `rolling.sum` are ONLINE,
     so one enormous return leaves a residue after it has left the window;
     the test compares both against exact bounds from the window's own range.
     Measured: with a planted return of 1e+8, the 139 bars after it has left
     every window are NaN with the test and up to **1.280** away from a
     per-window oracle without it. It is not a cure at every magnitude
     (1.3e-09 at 1e+2, 3.3e-06 at 1e+4, 8.5e-03 at 1e+6 all pass it), and it
     costs **0 bars** on seven clean frames including the alternating frame
     that attains its bound exactly.

5. **Gate D, and that x8 is bit-identical rather than merely close.** Every
   input is a price RATIO and `8a / 8b` is the same double as `a / b`: 1,440
   of 1,440 bars bit-identical at x8 and x64 on each of three frames, and
   1,497 / 1,480 / 1,250 at `length` 3 / 20 / 250. x10 / x3.7 agree to
   8.8e-15 with identical NaN masks. The difference-of-logarithms spelling of
   the return would not be (821 of 1,499 bars bit-equal at x8, against
   1,499 of 1,499 for the ratio).

6. **What the column means, and what it is not.** It is invariant to an
   AFFINE map of the returns -- x2, x0.5 and +0.004 of log drift a bar all
   leave it at Spearman 1.000000 and within 2.7e-14 -- so it is neither
   volatility (Spearman -0.0965 against the window's own sd) nor direction
   (0.0560 against the window's mean return). For iid returns it is centred
   just below zero (median -0.0106 over 2,000 independent windows, against
   the arithmetic small-sample bias `-1/(n-1)` = -0.0169) and wide (sd
   0.1222, p10 -0.1797, p90 0.1418). It ORDERS the AR(1) coefficient:
   medians 0.5030 / 0.2699 / 0.0283 / -0.2180 / -0.4683 at `phi` = +0.50 /
   +0.25 / 0 / -0.25 / -0.50.

7. **The guard bands and the NaN rules.** `length` below 3 (including 0,
   negatives and fractions that truncate below 3) falls back to 60; a window
   of two returns is identically -1, which is why the minimum is 3. A bad
   close -- NaN, zero, negative, infinite or subnormal -- empties exactly the
   61 windows that contain it and moves nothing before it; a flat run needs
   all `length + 1` closes to empty one bar.

8. **Five-point wiring** (`Category`, the accessor, the export, the name) and
   that `lag` is NOT a parameter: the name says lag 1, so there is no keyword
   that could make it something else.

Every number above comes from `docs/measure_ts_ac1_60.py`, whose run is
transcribed in `docs/TsAc160Measured.md`. Gate E is owed: the launcher runs
`gate_e_overlap.py` after this session and a later session records the
`docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.
"""
import importlib
import inspect
import types
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60

LENGTH, LAG = 60, 1

_REAL = importlib.import_module("pandas_ta.statistics.ts_ac1_60")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.5):
    """A path whose LOG returns are an AR(1), `rlog[t] = phi*rlog[t-1] + eps`,
    whose population lag-1 autocorrelation is exactly `phi`."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _alternating(n=1500, amp=0.01):
    r = np.where(np.arange(n) % 2 == 0, amp, -amp)
    return Series(100.0 * np.cumprod(1.0 + r))


def _mean_dominated(n=340, seed=3, mu=0.01, ratio=1e5):
    """Returns with a large MEAN and a tiny DISPERSION, well above the
    variance floor: the shape that breaks a raw-sum numerator."""
    rng = np.random.default_rng(seed)
    r = mu + rng.normal(0.0, abs(mu) / ratio, n)
    return Series(100.0 * np.cumprod(1.0 + r))


# ------------------------------------------------------------- Gate A


def test_an_alternating_window_is_exactly_minus_one():
    """`close = [1, 2, 1, 2, 1]` at `length=4` holds the returns
    [+1, -1/2, +1, -1/2], whose deviations from the mean 1/4 are
    [+3/4, -3/4, +3/4, -3/4]:

        the three products   (+3/4)(-3/4) etc = -9/16 each, sum -27/16
        population variance  9/16
        value                (-27/16) / (3 * 9/16) = -1 exactly

    Derived by hand for any `length` and any pair of alternating values: each
    of the `length - 1` products is `-d**2` and the variance is `d**2`. Every
    quantity here is an exact binary fraction, so the module hits it
    bit-exactly rather than nearly."""
    out = ts_ac1_60(Series([1.0, 2.0, 1.0, 2.0, 1.0]), length=4)
    assert out.name == "TS_AC1_4"
    assert out.iloc[:4].isna().all()
    assert float(out.iloc[4]) == -1.0


def test_an_alternating_frame_sits_at_minus_one_at_the_default_length():
    """The same algebra at `length` 60 on a 1,500-bar frame. The closes are
    built by a cumulative PRODUCT, so the returns are no longer exactly +-amp
    and the value is -1 to 5.4e-15 rather than bit-exact on every bar -- 25
    of 1,440 bars are bit-equal to -1.0, which is a float detail and is not
    asserted."""
    col = ts_ac1_60(_alternating()).dropna()
    assert len(col) == 1440
    assert float((col + 1.0).abs().max()) < 1e-13


def _source_windowed(close, length=LENGTH, lag=LAG, log_returns=False,
                     closes_not_returns=False, ddof=0, biased=False,
                     guard="floor"):
    """tsfresh's `autocorrelation`, retyped from its published definition and
    applied window by window with `sliding_window_view`:

        y1 = x[:len(x)-lag]; y2 = x[lag:]
        x_mean = np.mean(x)
        sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
        v = np.var(x)
        return np.NaN if np.isclose(v, 0) else \
            sum_product / ((len(x) - lag) * v)

    No pandas rolling anywhere, so it shares no window machinery with the
    module. The keywords are the rejected readings."""
    px = close.astype(float)
    if log_returns:
        r = np.log(px / px.shift(1)).to_numpy()
    else:
        r = (px / px.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    width = length - 1 if closes_not_returns else length
    if len(r) < width + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], width)
    norm = width if biased else width - lag
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        m = W.mean(axis=1, keepdims=True)
        dev = W - m
        num = (dev[:, lag:] * dev[:, :W.shape[1] - lag]).sum(axis=1)
        v = W.var(axis=1, ddof=ddof)
        vals = num / (norm * v)
    if guard == "floor":                 # this module's guard
        vals = np.where(v > _REAL.VAR_FLOOR, vals, np.nan)
    elif guard == "isclose":             # tsfresh's own: absolute, atol 1e-8
        vals = np.where(np.isclose(v, 0.0), np.nan, vals)
    elif guard != "none":
        raise ValueError(guard)          # so a typo cannot mean "unguarded"
    out[width:] = vals
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn,tol", [(_walk, 1e-14),
                                          (_tick_rounded, 1e-14),
                                          (_ar1, 1e-14)])
def test_matches_the_source_formula_window_by_window(frame_fn, tol):
    frame = frame_fn()
    base, other = ts_ac1_60(frame), _source_windowed(frame)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1440
    assert float((base[m] - other[m]).abs().max()) < tol
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


def _exact(close, length=LENGTH, lag=LAG, bars=40):
    """The EXACT value in `fractions.Fraction`: every close is a rational, so
    every return and the whole statistic is one. The only rounding is the
    final conversion to float."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(max(length, len(c) - bars), len(c)):
        x = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        m = sum(x) / length
        v = sum((u - m) ** 2 for u in x) / length
        num = sum((x[i] - m) * (x[i - lag] - m) for i in range(lag, length))
        if v != 0:
            out[t] = float(num / ((length - lag) * v))
    return Series(out, index=close.index)


def test_the_module_is_as_accurate_as_an_fsum_loop_against_the_exact_value():
    """On a walk, against the exact rational value of the same closes: the
    module 3.1e-15, a `math.fsum` scalar loop 1.0e-15, the window-by-window
    oracle 1.0e-15. The same order of magnitude; `docs/measure_ts_ac1_60.py`
    prints all three on three frames."""
    close = _walk(340, seed=11)
    exact = _exact(close)
    m = exact.notna()
    assert int(m.sum()) == 40
    module = ts_ac1_60(close)
    assert float((module[m] - exact[m]).abs().max()) < 1e-13


def _plain_expansion(close, length=LENGTH, lag=LAG):
    """The numerator spelling the module REJECTS -- algebraically identical,
    `sum x[i]*x[i-1] - m*((length+1)*m - oldest - newest)`."""
    r = close.astype(float) / close.astype(float).shift(1) - 1.0
    rolling = r.rolling(length, min_periods=length)
    mean, var = rolling.mean(), rolling.var(ddof=0)
    products = (r * r.shift(lag)).rolling(length - lag,
                                          min_periods=length - lag).sum()
    num = products - mean * ((length + 1) * mean - r.shift(length - 1) - r)
    return num / ((length - lag) * var.where(var > _REAL.VAR_FLOOR))


def test_the_raw_sum_numerator_loses_the_statistic_when_the_mean_dominates():
    """Why the numerator is spelled with `(x[i]-x[i-1])**2` instead of a raw
    product sum. On a path whose returns have `|mean| / sd` = 1e5 -- still
    far above the variance floor -- the module is 2.1e-10 from the exact
    rational value and the raw-sum expansion 4.1e-06, about 2.3e+04 times
    worse. On an ordinary walk the two are indistinguishable (1.2e-15), so
    the choice shows up only on this shape, which is the point of testing
    it."""
    frame = _mean_dominated()
    exact = _exact(frame)
    m = exact.notna()
    module = float((ts_ac1_60(frame)[m] - exact[m]).abs().max())
    plain = float((_plain_expansion(frame)[m] - exact[m]).abs().max())
    assert module < 1e-8
    assert plain > 1e-7
    assert plain > 1e3 * module
    walk = _walk(340, seed=11)
    wm = _exact(walk).notna()
    assert float((ts_ac1_60(walk)[wm] - _plain_expansion(walk)[wm])
                 .abs().max()) < 1e-13


def _tridiagonal(n):
    t = np.zeros((n, n))
    i = np.arange(n - 1)
    t[i, i + 1] = 0.5
    t[i + 1, i] = 0.5
    return t


def _ortho_basis(n):
    a = np.eye(n) - np.ones((n, n)) / n
    q, _ = np.linalg.qr(a)
    keep = [c for c in range(n) if abs(float(np.ones(n) @ q[:, c])) < 1e-10]
    return q[:, keep[:n - 1]]


def _bounds(n, lag=LAG):
    """The reachable [min, max] of the column at `length = n`: the numerator
    is `y' T y` with `T` the lag-1 product form and `y` the demeaned window,
    and the divisor is `(n - lag) * y'y / n`, so the column is a Rayleigh
    quotient of `T` on the subspace orthogonal to the all-ones vector, scaled
    by `n / (n - lag)`."""
    q = _ortho_basis(n)
    w = np.linalg.eigvalsh(q.T @ _tridiagonal(n) @ q)
    scale = n / (n - lag)
    return float(w.min() * scale), float(w.max() * scale)


def _extreme_window(n, want_max, amp=0.01):
    q = _ortho_basis(n)
    w, vecs = np.linalg.eigh(q.T @ _tridiagonal(n) @ q)
    idx = int(np.argmax(w)) if want_max else int(np.argmin(w))
    y = q @ vecs[:, idx]
    return amp * y / float(np.abs(y).max())


@pytest.mark.parametrize("length,lo,hi", [(4, -1.078689325833, 0.412022659167),
                                          (10, -1.066103304016, 0.934726147590),
                                          (60, -1.015600769374, 1.011559195540)])
def test_the_reachable_bounds_are_attained_and_not_exceeded(length, lo, hi):
    """Both ends, derived and then attained by the module on the matching
    eigenvector window. They are inside tsfresh's `n/(n-lag)` scaling of
    [-1, 1] because the window is demeaned first, and at short lengths they
    are much tighter on the positive side (+0.412 at `length` 4). The column
    also stays inside them on three ordinary frames."""
    assert _bounds(length) == pytest.approx((lo, hi), abs=1e-9)
    for want_max, target in ((True, hi), (False, lo)):
        y = _extreme_window(length, want_max)
        closes = Series(np.concatenate([[100.0],
                                        100.0 * np.cumprod(1.0 + y)]))
        got = float(ts_ac1_60(closes, length=length).iloc[-1])
        assert got == pytest.approx(target, abs=1e-12)
    for frame_fn in (_walk, _tick_rounded, _ar1):
        col = ts_ac1_60(frame_fn(), length=length).dropna()
        assert float(col.min()) >= lo
        assert float(col.max()) <= hi


def _prototype(close, length=LENGTH, lag=LAG):
    """`docs/issues/screen/ind_screen.py` candidate `ts_ac1_60`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            r = ret(c)
            return corr(r, delay(r, 1), 60)

    with `ret(c) = c / c.shift(1) - 1`, `delay(x, n) = x.shift(n)` and
    `corr(x, y, n) = (x.rolling(n).corr(y)).replace([inf, -inf], nan)`."""
    r = close / close.shift(1) - 1
    return r.rolling(length).corr(r.shift(lag)).replace(
        [np.inf, -np.inf], np.nan)


def test_the_prototype_is_a_different_statistic():
    """The screen measured a PEARSON correlation of two 60-pair slices -- two
    means, two standard deviations, 61 returns of history. This port is the
    source formula, which the issue's "Gates owed" asks for by name. The
    difference is visible, so issue #94's Gate E figures (0.2534 vs
    `mad_pct`) do not transfer to this column: Spearman 0.988839, max
    |difference| 0.1013, no bar bit-equal, and the warm-up differs by one
    bar."""
    close = _walk()
    base, proto = ts_ac1_60(close), _prototype(close)
    m = base.notna() & proto.notna()
    assert int(m.sum()) == 1439
    assert int((base[m] == proto[m]).sum()) == 0
    assert 0.09 < float((base[m] - proto[m]).abs().max()) < 0.12
    assert 0.98 < float(base[m].corr(proto[m], method="spearman")) < 0.995
    assert int(base.notna().to_numpy().argmax()) == LENGTH
    assert int(proto.notna().to_numpy().argmax()) == LENGTH + 1


@pytest.mark.parametrize("kwargs,lo,hi,rho_lo,rho_hi", [
    ({"log_returns": True}, 1e-3, 1e-1, 0.999, 0.99999),
    ({"closes_not_returns": True}, 0.05, 0.5, 0.95, 0.995),
    ({"ddof": 1}, 1e-3, 1e-2, 1.0 - 1e-12, 1.1),
    ({"biased": True}, 1e-3, 1e-2, 1.0 - 1e-12, 1.1),
])
def test_the_rejected_readings_are_each_priced(kwargs, lo, hi, rho_lo, rho_hi):
    """Each is a reading the issue's wording leaves open and this port
    rejects, so each is measured rather than dismissed. The two rescalings
    (`ddof=1`, and dividing by `length * v`) are rank-identical and differ
    only in level; log returns and the 60-CLOSES reading are different
    columns."""
    close = _walk()
    base, other = ts_ac1_60(close), _source_windowed(close, **kwargs)
    m = base.notna() & other.notna()
    diff = float((base[m] - other[m]).abs().max())
    assert lo < diff < hi
    rho = float(base[m].corr(other[m], method="spearman"))
    assert rho_lo <= rho <= rho_hi


def test_the_two_rescalings_are_the_same_column():
    """Dividing by `length * v` instead of `(length - 1) * v`, and keeping
    `(length - 1)` but using the SAMPLE variance, are the same reading twice:
    both multiply this column by exactly `59/60`. Measured: `port * 59/60`
    reproduces each to 4.8e-15 and the two agree with each other to
    5.6e-17."""
    close = _walk()
    base = ts_ac1_60(close)
    biased = _source_windowed(close, biased=True)
    ddof1 = _source_windowed(close, ddof=1)
    m = base.notna() & biased.notna() & ddof1.notna()
    factor = (LENGTH - LAG) / LENGTH
    assert float((base[m] * factor - biased[m]).abs().max()) < 1e-13
    assert float((base[m] * factor - ddof1[m]).abs().max()) < 1e-13
    assert float((biased[m] - ddof1[m]).abs().max()) < 1e-15


def test_the_pearson_normalisation_on_the_same_window_is_a_near_copy():
    """`pandas.Series.autocorr` on the module's own 60-return window is the
    prototype's normalisation without the prototype's extra bar of history:
    Spearman 0.999901, max |difference| 1.4e-02 -- closer than the prototype
    (0.988839 / 0.1013) and still not this column."""
    close = _walk()
    base = ts_ac1_60(close)
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r[1:], LENGTH)
    pearson = np.full(len(r), np.nan)
    pearson[LENGTH:] = [float(Series(w).autocorr(LAG)) for w in W]
    other = Series(pearson, index=close.index)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1440
    assert 5e-3 < float((base[m] - other[m]).abs().max()) < 5e-2
    assert 0.9995 < float(base[m].corr(other[m], method="spearman")) < 0.99999


def test_lag_is_not_a_parameter():
    """The column's NAME says lag 1, so there is no keyword that could make
    it something else -- an unknown keyword would reach `**kwargs` and be
    ignored silently, which is why this is asserted on the SIGNATURE."""
    assert _REAL.LAG == 1
    params = list(inspect.signature(ts_ac1_60).parameters)
    assert params == ["close", "length", "offset", "kwargs"]


# ------------------------------------------------------------- Gate B

WRITE_SHIFT_MUTANT = (
    "    tsac1 = numerator / ((length - LAG)",
    "    tsac1 = (numerator).shift(-length) / ((length - LAG)")
FORWARD_RETURN_MUTANT = (
    "        r = px / px.shift(1) - 1.0",
    "        r = px.shift(-1) / px - 1.0")
FORWARD_OLDEST_MUTANT = (
    "    oldest = r.shift(length - 1)",
    "    oldest = r.shift(-(length - 1))")
CENTERED_VAR_MUTANT = (
    "    var = rolling.var(ddof=0)",
    "    var = r.rolling(length, min_periods=length, center=True).var(ddof=0)")
CENTERED_MEAN_MUTANT = (
    "    mean = rolling.mean()",
    "    mean = r.rolling(length, min_periods=length, center=True).mean()")
CENTERED_GAP_MUTANT = (
    "    gap = gap.rolling(length - LAG, min_periods=length - LAG).sum()",
    "    gap = gap.rolling(length - LAG, min_periods=length - LAG, "
    "center=True).sum()")

MUTANTS = [WRITE_SHIFT_MUTANT, FORWARD_RETURN_MUTANT, FORWARD_OLDEST_MUTANT,
           CENTERED_VAR_MUTANT, CENTERED_MEAN_MUTANT, CENTERED_GAP_MUTANT]
MUTANT_IDS = ["write_shift", "forward_return", "forward_oldest",
              "centered_var", "centered_mean", "centered_gap"]
OFFSETS = range(100, 1500, 40)  # past the 60-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "ar1": (_ar1(), _ar1(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_ac1_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _quiet_offsets(fn, close, other):
    """Replace every bar from J onward with a different path; return the J
    values at which NOTHING strictly before J moved, each with whether bar
    J - 1 -- the only bar a one-bar look-ahead can reach -- was NaN in both
    runs. Prefix truncation cannot see back-dating, which is why this is a
    perturbation sweep."""
    base = fn(close)
    quiet = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        moved = not (a.isna() == b.isna()).all()
        if not moved:
            m = a.notna()
            moved = bool((a[m] != b[m]).any())
        if not moved:
            quiet.append((j, bool(np.isnan(float(a.iloc[-1]))),
                          bool(np.isnan(float(b.iloc[-1])))))
    return quiet


def _leaks(fn, close, other):
    """How many of the sweep's offsets show a leak."""
    return len(list(OFFSETS)) - len(_quiet_offsets(fn, close, other))


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _leaks(ts_ac1_60, close, other) == 0


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("mutant", MUTANTS, ids=MUTANT_IDS)
def test_each_mutant_is_caught_on_each_frame(mutant, frame):
    mod = _load_mutant(*mutant)
    close, other = FRAMES[frame]
    assert not mod.ts_ac1_60(close).equals(ts_ac1_60(close))  # live mutation
    assert _leaks(mod.ts_ac1_60, close, other) == len(list(OFFSETS))


NON_DEFAULT = [
    # (mutant, name, length, caught)
    (WRITE_SHIFT_MUTANT, "write_shift", 3, 35),
    (WRITE_SHIFT_MUTANT, "write_shift", 250, 31),
    (FORWARD_OLDEST_MUTANT, "forward_oldest", 3, 35),
    (FORWARD_OLDEST_MUTANT, "forward_oldest", 250, 31),
    (CENTERED_VAR_MUTANT, "centered_var", 3, 22),
    (CENTERED_VAR_MUTANT, "centered_var", 250, 31),
    (CENTERED_GAP_MUTANT, "centered_gap", 3, 0),
    (CENTERED_GAP_MUTANT, "centered_gap", 250, 31),
]


@pytest.mark.parametrize("mutant,name,length,caught", NON_DEFAULT,
                         ids=[f"{n}-{le}" for _, n, le, _ in NON_DEFAULT])
def test_the_length_dependent_mutants_at_non_default_lengths(
        mutant, name, length, caught):
    """`length` is user-reachable from 3 upward and the sweep above runs the
    default only. The four mutants whose behaviour depends on it are re-run
    here at 3 and 250. The real module leaks 0/35 at every setting. SIX of
    the eight cells are not 35/35 -- the four `length` 250 cells, plus two at
    `length` 3 -- under three explanations, and each explanation is ASSERTED
    rather than argued:

    * **31/35 at `length` 250** misses exactly the four offsets below a
      250-bar warm-up (J = 100, 140, 180, 220), where the whole prefix is
      NaN and there was nothing to move. Asserted by checking that the first
      250 bars are NaN and that exactly four offsets sit below them.
    * **22/35 for the centred variance at `length` 3**: a 3-wide centred
      window reads exactly one bar ahead, so the only bar it can move is
      J - 1, and at 13 of the 35 offsets that bar is NaN in BOTH the real
      module and the mutant -- at `length` 3 the column's own NaN rate is
      high (62 of the first 100 bars fire). Asserted by checking that bar
      J - 1 is NaN in both at every quiet offset. ⚠ This is a limit of the
      sweep, not a clean bill: the look-ahead is real and is caught at the
      other 22 offsets.
    * **0/35 for the centred squared-difference sum at `length` 3** is a
      mutation that does nothing: that window is `length - LAG` = 2 wide and
      pandas centres by `(window - 1) // 2` = 0 bars, so `center=True` is
      `center=False`. Asserted with `equals()`."""
    close, other = FRAMES["walk"]
    mod = _load_mutant(*mutant)

    def real(c):
        return ts_ac1_60(c, length=length)

    def mutated(c):
        return mod.ts_ac1_60(c, length=length)

    assert int(real(close).notna().to_numpy().argmax()) == length
    assert _leaks(real, close, other) == 0
    quiet = _quiet_offsets(mutated, close, other)
    assert len(list(OFFSETS)) - len(quiet) == caught
    if caught == 0:
        assert mutated(close).equals(real(close))  # the mutation is a no-op
        assert (length - LAG - 1) // 2 == 0        # pandas centres by 0 bars
        return
    assert not mutated(close).equals(real(close))  # live mutation
    if caught == 31:
        assert real(close).iloc[:length].isna().all()
        assert [j for j, _, _ in quiet] == [100, 140, 180, 220]
    # Nothing moved because bar J - 1, the only bar reachable, was NaN in
    # both runs -- not because the mutant is causal.
    assert all(clean and perturbed for _, clean, perturbed in quiet)


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep above
    covers."""
    close = _walk(400, seed=3)
    base = ts_ac1_60(close)
    pd.testing.assert_series_equal(ts_ac1_60(close, offset=2), base.shift(2),
                                   check_names=False)
    pd.testing.assert_series_equal(ts_ac1_60(close, offset=-2), base.shift(-2),
                                   check_names=False)


# ------------------------------------------------------- the two guards


def test_the_variance_floor_is_an_absolute_constant_not_a_window():
    """It is deliberately NOT a rolling quantity: what it floors is the
    dispersion of dimensionless price ratios, so a constant works and the
    floor has no window of its own whose causality would need pinning. It is
    the SQUARE of the 4096 eps this fork floors a return standard deviation
    with in `statistics/ts_c3_20.py`, because the divisor here is a
    variance."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    assert _REAL.VAR_FLOOR == _REAL.NOISE_FLOOR ** 2
    src = open(_REAL.__file__, encoding="utf-8").read()
    # Two rolling calls: the `length`-wide object reused for the mean, the
    # variance and the two extrema, and the `length - 1`-wide sum of squared
    # successive differences. That is what Gate B's three centred mutants
    # cover.
    assert src.count(".rolling(") == 2


@pytest.mark.parametrize("frame_fn,fires,unguarded_fires,fabricated", [
    (lambda: Series(np.full(300, 50.0)), 0, 0, 0.0),
    (lambda: Series(100.0 * np.exp(np.arange(300) * 0.01)), 0, 240, 0.5),
])
def test_a_window_with_no_dispersion_is_nan_rather_than_a_ratio_of_roundings(
        frame_fn, fires, unguarded_fires, fabricated):
    """A flat frame and a 1%-a-bar geometric ladder both have mathematically
    constant returns, so there is no autocorrelation to report. The ladder is
    the case `var != 0` does not catch: its returns vary at float rounding
    level, and an unguarded spelling reports 240 of 300 bars from that
    rounding alone, reaching 0.8328 -- a plausible-looking number, which is
    worse than a wild one. The flat frame's variance is exactly 0, so even
    unguarded it reports nothing: the two frames are therefore pinned with
    their own counts, not with one count that would pass either way."""
    frame = frame_fn()
    assert int(ts_ac1_60(frame).notna().sum()) == fires
    unguarded = _source_windowed(frame, guard="none")
    assert int(unguarded.notna().sum()) == unguarded_fires
    if unguarded_fires:
        assert float(unguarded.abs().max()) > fabricated


def test_the_floor_is_not_tsfreshs_isclose_guard():
    """tsfresh's own guard is `np.isclose(var, 0)`, absolute at numpy's
    default `atol = 1e-8`, so it empties every window whose return sd is
    under 1e-4 -- genuinely fine low-volatility data. Measured on a
    sigma = 1e-6 walk (variance 6.0e-13): that guard reports on 0 of 240
    windows where this column reports on all 240 and reads an ordinary
    +-0.27."""
    frame = _walk(300, sigma=1e-6)
    ours = ts_ac1_60(frame)
    theirs = _source_windowed(frame, guard="isclose")
    assert int(ours.notna().sum()) == 240
    assert int(theirs.notna().sum()) == 0
    assert float(ours.abs().max()) < 1.0


@pytest.mark.parametrize("price,tick,fires", [(50.0, 0.01, 240),
                                              (1e6, 0.001, 0),
                                              (1e6, 0.01, 0)])
def test_the_floor_bounds_the_dispersion_of_the_returns_not_their_size(
        price, tick, fires):
    """What the floor is and is not compared against. A tick grid quantises
    the return LEVEL at `tick / price` but the DISPERSION of consecutive
    returns at about `(tick / price)**2`, so the familiar "one tick over a
    price of 1e6 is 1e-9" is not a comparison against this floor. On a
    monotone one-tick-per-bar path: at price 50 with a 0.01 tick the window
    variance is 3.9e-13 and 240 of 300 bars fire; at price 1e6 with a 0.001
    tick it is 1.2e-32 and none do -- which is the right answer, because a
    window whose returns are that nearly constant has no autocorrelation to
    measure."""
    closes = Series(price + tick * np.arange(300))
    r = closes / closes.shift(1) - 1.0
    v = float(r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0).iloc[-1])
    assert int(ts_ac1_60(closes).notna().sum()) == fires
    assert (v > _REAL.VAR_FLOOR) == (fires > 0)


def _no_trust_test(close, length=LENGTH, lag=LAG):
    """The module without the accumulator trust test, to price it."""
    px = close.astype(float)
    r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    rolling = r.rolling(length, min_periods=length)
    mean, var = rolling.mean(), rolling.var(ddof=0)
    gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(length - lag, min_periods=length - lag).sum()
    num = length * var - 0.5 * ((r.shift(length - 1) - mean) ** 2
                                + (r - mean) ** 2 + gap)
    return num / ((length - lag) * var.where(var > _REAL.VAR_FLOOR))


def test_the_trust_test_turns_a_contaminated_accumulator_into_nan():
    """`rolling.var` and `rolling.sum` are ONLINE -- a value is added when it
    enters the window and subtracted when it leaves -- so one enormous return
    leaves a residue in both after it has gone. With a planted return of 1e+8
    at bar 200 of a 400-bar walk, the 139 bars from 261 on hold NO part of it
    and are nonetheless up to 1.280 away from a per-window oracle without
    this test; with it they are NaN. The test is exact algebra on the
    window's own range: a population variance cannot exceed `(span/2)**2` and
    `length - 1` squared successive differences cannot exceed
    `(length - 1) * span**2`."""
    frame = _walk(400, seed=21)
    holed = frame.copy()
    holed.iloc[200] = float(frame.iloc[199]) * 1e8
    tail = slice(261, 400)
    oracle = _source_windowed(holed)
    strict, loose = ts_ac1_60(holed), _no_trust_test(holed)
    assert int(oracle.iloc[tail].isna().sum()) == 0
    assert int(strict.iloc[tail].isna().sum()) == 139
    assert int(loose.iloc[tail].isna().sum()) == 0
    assert float((loose.iloc[tail] - oracle.iloc[tail]).abs().max()) > 1.0


@pytest.mark.parametrize("exponent,bound", [(2, 1e-8), (4, 1e-5), (6, 1e-2)])
def test_the_trust_test_is_not_a_cure_at_every_magnitude(exponent, bound):
    """Disclosed rather than implied: a planted return of 1e+2, 1e+4 or 1e+6
    passes the trust test, because the window's variance stays inside the
    bound its range allows, and the bars after it still differ from a
    per-window oracle -- by 1.3e-09, 3.3e-06 and 8.5e-03 respectively. A
    100x bar is a thing a market can do; 1e+6 is a broken feed."""
    frame = _walk(400, seed=21)
    holed = frame.copy()
    holed.iloc[200] = float(frame.iloc[199]) * 10.0 ** exponent
    tail = slice(261, 400)
    col, oracle = ts_ac1_60(holed), _source_windowed(holed)
    assert int(col.iloc[tail].isna().sum()) == 0
    gap = float((col.iloc[tail] - oracle.iloc[tail]).abs().max())
    assert bound / 1e3 < gap < bound


@pytest.mark.parametrize("frame_fn,fires", [(_walk, 1440),
                                            (_tick_rounded, 1440),
                                            (_ar1, 1440),
                                            (_alternating, 1440)])
def test_the_trust_test_costs_nothing_on_clean_frames(frame_fn, fires):
    """It must not eat ordinary data, and the alternating frame is the case
    that attains its variance bound EXACTLY (measured ratio
    1.000000000000), which is why the slack is 4096 eps relative rather than
    zero."""
    frame = frame_fn()
    strict, loose = ts_ac1_60(frame), _no_trust_test(frame)
    assert int(strict.notna().sum()) == fires
    assert int((loose.notna() & strict.isna()).sum()) == 0


@pytest.mark.parametrize("planted,emptied,span", [
    ({200: 1e-300}, 60, (201, 260)),
    ({200: 1e-200, 230: 1e-200}, 90, (201, 290)),
])
def test_a_return_over_the_square_bound_is_dropped_rather_than_poisoning_on(
        planted, emptied, span):
    """The overflow bound keeps a giant return's damage to its own windows.
    One close of 1e-300 in a 400-bar walk makes a NEXT return of about
    1e+302, whose square is not representable: guarded, 60 bars go
    (201..260). Two such closes 30 bars apart spoil two returns and cost the
    UNION of their windows, 90 bars (201..290), which is what makes the
    locality structural rather than a one-shape measurement. Unguarded, the
    infinite accumulator never leaves and 199 bars go in both cases -- the
    whole remainder of the frame (measured in `docs/measure_ts_ac1_60.py`,
    Guards). The ceiling the bound puts on a return is 6.12e+152, which
    nothing a market can produce reaches."""
    frame = _walk(400, seed=21)
    base = ts_ac1_60(frame)
    holed = frame.copy()
    for idx, value in planted.items():
        holed.iloc[idx] = value
    guarded = ts_ac1_60(holed)
    lost = np.flatnonzero((base.notna() & guarded.isna()).to_numpy())
    assert len(lost) == emptied
    assert (int(lost.min()), int(lost.max())) == span
    ceiling = np.sqrt(np.finfo(float).max / (8 * LENGTH))
    assert ceiling == pytest.approx(6.1197e152, rel=1e-3)


# ------------------------------------------------------------- Gate C/D


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_ac1_60(close), ts_ac1_60(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1440
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("length,fires", [(3, 1497), (20, 1480), (250, 1250)])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical_at_other_lengths(
        length, fires, k):
    """The default is not the only reachable setting: `length` is free from 3
    upward."""
    close = _walk()
    base = ts_ac1_60(close, length=length)
    scaled = ts_ac1_60(close * k, length=length)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == fires
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_are_within_tolerance(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_ac1_60(close), ts_ac1_60(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-13
    assert float(base[m].corr(scaled[m], method="spearman")) >= 1.0 - 1e-12


def test_the_difference_of_logarithms_spelling_would_not_be_scale_identical():
    """Why the module spells the return as a price RATIO. `8a / 8b` is the
    same double as `a / b`, but `log(8a) - log(8b)` is not
    `log(a) - log(b)`: on this frame the ratio returns are bit-equal on all
    1,499 bars at x8 and the difference-of-logarithms returns on 821."""
    close = _walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    assert int(m.sum()) == 1499
    assert (ratio[m] == ratio8[m]).all()
    # 821 locally; the exact count is CPU float detail, so only "some but not
    # all" is pinned.
    assert 0 < int((plain[m] == plain8[m]).sum()) < 1499


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
def test_fires_and_is_not_constant(frame_fn):
    close = frame_fn()
    out = ts_ac1_60(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1440
    assert int(out.nunique()) == 1440
    assert int((out.dropna() != 0).sum()) == 1440


# ------------------------------------------------- what the column means


def test_it_is_invariant_to_an_affine_map_of_the_returns():
    """The strongest property of the column, and the reason it is neither a
    volatility nor a direction reading: both the numerator and the divisor
    scale by `a**2` under `x -> a*x + b`, and the shift cancels in the
    deviations. Measured on a walk whose returns are rebuilt at x2 and x0.5,
    and on the same walk given +0.004 of log drift a bar (an affine map of
    the simple returns): Spearman 1.000000 and max |difference| 4.0e-15,
    9.6e-15 and 2.7e-14."""
    close = _walk()
    base = ts_ac1_60(close)
    r = (close / close.shift(1) - 1.0).to_numpy()[1:]
    first = float(close.iloc[0])
    others = {
        "x2": Series(np.concatenate([[first],
                                     first * np.cumprod(1.0 + 2.0 * r)])),
        "x0.5": Series(np.concatenate([[first],
                                       first * np.cumprod(1.0 + 0.5 * r)])),
        "drift": Series(close.to_numpy()
                        * np.exp(0.004 * np.arange(len(close)))),
    }
    for other in others.values():
        out = ts_ac1_60(other)
        assert (base.isna() == out.isna()).all()
        m = base.notna()
        assert float((base[m] - out[m]).abs().max()) < 1e-13
        assert float(base[m].corr(out[m], method="spearman")) >= 1.0 - 1e-12


def test_it_is_not_volatility_and_not_direction():
    """Pinned where a consumer reads first, because the nearest statistics
    ports are volatility-flavoured and this one is not: Spearman -0.0965
    against the same window's standard deviation, 0.0560 against its mean
    return, -0.0073 against the absolute mean return."""
    close = _walk()
    base = ts_ac1_60(close)
    r = close / close.shift(1) - 1.0
    rolling = r.rolling(LENGTH, min_periods=LENGTH)
    for other in (rolling.std(), rolling.mean(), rolling.mean().abs()):
        m = base.notna() & other.notna()
        assert abs(float(base[m].corr(other[m], method="spearman"))) < 0.2


def test_the_level_is_centred_just_below_zero_for_iid_returns_and_wide():
    """The population value for iid returns is 0 and this estimator's
    small-sample bias is about `-1/(n-1)` = -0.0169 (arithmetic), which is
    where the column sits. The spread is the number a reader needs before
    treating one value as a signal: `docs/measure_ts_ac1_60.py` runs 2,000
    independent windows and reports median -0.0106, sd 0.1222, p10 -0.1797,
    p90 0.1418, positive on 45.70%. Pinned loosely here on 300 windows."""
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (300, LENGTH + 1)),
                                     axis=1))
    est = np.array([float(ts_ac1_60(Series(p)).iloc[-1]) for p in paths])
    assert np.isfinite(est).all()
    assert -0.06 < float(np.median(est)) < 0.0
    assert 0.35 < float((est > 0).mean()) < 0.55
    assert 0.08 < float(est.std(ddof=1)) < 0.18


def test_it_orders_the_ar1_coefficient():
    """The column's actual claim. The generator's LOG returns are an AR(1)
    with coefficient `phi`, whose population lag-1 autocorrelation is exactly
    `phi`; the column reads SIMPLE returns, a monotone transform of them. The
    medians come out in the order of `phi` and near it: 0.5030 / 0.2699 /
    0.0283 / -0.2180 / -0.4683 at +0.50 / +0.25 / 0 / -0.25 / -0.50. The
    LEVEL is shrunk by a 60-bar window and grows with it (measured on a
    20,000-bar `phi` = +0.5 path: 0.3797 / 0.4655 / 0.4871 / 0.4975 at
    `length` 20 / 60 / 200 / 1000), so only the ordering is pinned."""
    medians = [float(ts_ac1_60(_ar1(phi=phi)).median())
               for phi in (0.5, 0.25, 0.0, -0.25, -0.5)]
    assert medians == sorted(medians, reverse=True)
    assert medians[0] > 0.3
    assert abs(medians[2]) < 0.1
    assert medians[-1] < -0.3


def test_it_is_a_slow_state_and_not_an_event_flag():
    """Two consecutive windows share 59 of their 60 returns, so the column
    autocorrelates at 0.9760 at lag 1, 0.2813 at lag 30 and -0.2129 at lag
    60 (measured on a walk)."""
    col = ts_ac1_60(_walk()).dropna()
    assert float(col.autocorr(1)) > 0.9
    assert abs(float(col.autocorr(60))) < 0.5


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    assert ts_ac1_60(_walk(LENGTH)) is None


def test_exact_min_history_fires_at_the_warmup_boundary():
    out = ts_ac1_60(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH


@pytest.mark.parametrize("length", [None, 0, -5, 1, 2, 0.5, 2.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """A window of two returns is identically -1 -- `(a-b)**2/4` over
    `-(a-b)**2/4` -- so three is the smallest window on which the statistic
    varies, and anything below it is the default instead of a constant
    column."""
    out = ts_ac1_60(_walk(400, seed=31), length=length)
    assert out.name == "TS_AC1_60"
    assert _REAL.MIN_LENGTH == 3


def test_the_minimum_length_fires_and_varies():
    out = ts_ac1_60(_walk(400, seed=31), length=3)
    assert out.name == "TS_AC1_3"
    assert int(out.notna().sum()) == 397
    assert int(out.nunique()) > 300


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = ts_ac1_60(close, length=10), ts_ac1_60(close, length=250)
    assert (a.name, b.name) == ("TS_AC1_10", "TS_AC1_250")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert float(a[m].corr(b[m], method="spearman")) < 0.9


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(ts_ac1_60(close, length=50.9),
                                   ts_ac1_60(close, length=50))


def test_fillna_applies():
    out = ts_ac1_60(_walk(200, seed=13), fillna=-9.0)
    assert int((out == -9.0).sum()) == LENGTH


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data: each empties exactly the 61 windows that contain it, which is the
    `length + 1` closes one value reads (it spoils two returns). Nothing
    before the hole moves."""
    close = _walk(400, seed=21)
    base = ts_ac1_60(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = ts_ac1_60(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 260)
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0


@pytest.mark.parametrize("identical,emptied", [(60, 0), (61, 1), (65, 5)])
def test_a_flat_run_needs_length_plus_one_identical_closes_to_empty_a_bar(
        identical, emptied):
    """The NaN cause that belongs to THIS column rather than to bad data: a
    window of `length` returns has no dispersion when its returns are
    constant to rounding level, and identical closes are one way there (an
    exactly geometric path, whose closes are all distinct, is the other). It
    needs all `length + 1` of them: planted at bar 200 of a 400-bar walk, 60
    identical closes empty nothing, 61 empty exactly bar 260, 65 empty bars
    260..264."""
    close = _walk(400, seed=21)
    base = ts_ac1_60(close)
    flat = close.copy()
    flat.iloc[200:200 + identical] = float(close.iloc[200])
    out = ts_ac1_60(flat)
    holes = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(holes) == emptied
    if emptied:
        assert (int(holes.min()), int(holes.max())) == (260, 260 + emptied - 1)


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "ts_ac1_60" in ta.Category["statistics"]
    assert hasattr(df.ta, "ts_ac1_60")
    direct = ts_ac1_60(close)
    through = df.ta.ts_ac1_60()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "TS_AC1_60"
    assert direct.category == "statistics"


def test_the_gate_e_ledger_carries_no_row_for_this_column_yet():
    """Gate E is the launcher's: it runs `gate_e_overlap.py` after this
    session and a later session records the row. Asserted so that the
    screen's prototype figures cannot be mistaken for this column's
    measurement."""
    import csv
    import os

    path = os.path.join("docs", "gate_e_ledger.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "the ledger should not be empty"
    assert not [r for r in rows if r["indicator"] == "ts_ac1_60"]
