# -*- coding: utf-8 -*-
"""TS-AGGAC-60: `ts_aggac_60`, tsfresh's `agg_autocorrelation` with
`f_agg='mean'` and `maxlag=10` on 60 simple returns (PandasTa issue #96).

What this module pins, in order of how much it would hurt to lose.

1. **Causality, as a mutant test** (Gate B). The real module leaks on 0 of 35
   future-perturbation offsets on each of three frames; eight mutants -- a
   back-dated write, a forward return, a forward `head`, a forward `tail`, a
   centred variance, a centred mean, a centred gap and a forward lagged
   difference -- are each caught on 35 of 35, on each frame. Prefix truncation
   alone cannot see back-dating, which is why the sweep is a perturbation and
   a test here shows truncation staying silent on the mutant the sweep catches.
   A NINTH mutant centres `span`, the one write index the other eight cannot
   reach, and it is pinned for what it exposes rather than for passing:
   because `span` feeds only the trust test, and the trust test costs 0 bars
   on a clean frame, that mutant is live and still caught 0/35 on a clean
   walk. It is caught 13/35 on a frame with a planted 1e+8 return, where the
   guard fires, and that is the frame the test uses.

2. **The source formula** (Gate A). The issue names `agg_autocorrelation`,
   which reaches its numbers through `statsmodels`'
   `acf(x, adjusted=True)`, while `feature_calculators.autocorrelation` spells
   the same quotient directly. Those are the same number -- `acovf[k]` divides
   by `length - k` and `acovf[0]` by `length` -- and that identity is MEASURED
   here over 200 random windows (agreement 3.5e-17), not asserted. statsmodels
   is installed in this worktree, and the retyped adjusted `acf` reproduces
   `statsmodels.tsa.stattools.acf(..., adjusted=True, fft=False)` bit-exactly;
   a test skips if it is ever absent. The module then agrees with the source
   applied window by window (`sliding_window_view`, no pandas rolling) to
   5.7e-15 on a walk, and with an exact `fractions.Fraction` oracle to
   2.4e-15.

3. **The window's single mean and variance.** The alternative -- a Pearson
   correlation per lag over the same window -- is a DIFFERENT column
   (Spearman 0.996854, max |difference| 1.1e-02), and so is the screen
   prototype (`sum(corr(r, delay(r, k), 60) for k in 1..10)/10`: Spearman
   0.902932, max |difference| 4.7e-02, first fired bar 70 against this
   module's 60). The prototype is retyped here and, when `docs/issues/` is
   present, checked against the owner's own registry entry bit-for-bit.

4. **The reachable bounds, and their asymmetry.** The column is `length`
   times a Rayleigh quotient of the lag-weighted product form on the demeaned
   subspace, so [-0.310043, +0.915798] at `length` 60 / `maxlag` 10, attained
   by the module on the matching eigenvector window. No frame here leaves it.
   An alternating window reads exactly **0** at an even `maxlag` -- every
   `AC[k]` is `(-1)**k` -- which is a bit-exact assertion on
   `close = [1, 2, 1, 2, ...]`.

5. **The guards, each priced in both directions.** The 4096-eps variance
   floor (tsfresh's own `var < 1e-10` branch would instead FABRICATE 0.0, a
   perfectly ordinary reading of this column, on every window of a
   sigma = 1e-6 walk). The per-return square bound, which keeps an
   unrepresentable square local: 60 emptied bars instead of 199 on a 400-bar
   frame. The accumulator trust test, which turns a planted 1e+8 return into
   NaN where it would otherwise be 1.149 wrong, and costs 0 bars on NINE
   clean frames. Six of those nine are re-run by
   `test_the_trust_test_costs_nothing_on_a_clean_frame` below; the volatility
   collapse is pinned by
   `test_a_volatility_collapse_is_caught_by_the_floor_not_the_trust_test`,
   the fine-tick ladder by
   `test_the_floor_is_on_the_dispersion_and_not_on_the_price`, and the
   `ar1(-0.5)` frame only in `docs/measure_ts_aggac_60.py`.

6. **Scale-freedom** (Gate D). Bit-identical at x8 / x64 on three frames and
   at three lengths; identical NaN masks and 9.5e-15 agreement at x10 / x3.7;
   invariant to any affine map of the RETURNS, not only of the price.

7. **The wiring**, all five touch points, and the column name
   `TS_AGGAC_{length}_{maxlag}` with the EFFECTIVE `maxlag` after clamping.

8. **What Gate E cannot see.** Its 687 comparators hold no pandas_ta port, so
   the in-fork overlap is measured here, against the seven `Category` modules
   whose value is a function of the same series at a fixed offset -- listed
   by hand from `pandas_ta/__init__.py`, because grepping for `.corr(`
   against a `shift(` misses `lean_momersion_20` (a product of two signs) and
   `ts_cid_ce_20` (a sum of squared successive differences). 26 of the 28
   frame/column pairs produce a usable number -- `lean_momersion_20` is
   constant on the seasonal frame and `roll_spread` overlaps on 26 bars of
   the AR(1) one -- and the largest |Spearman| of those 26 is 0.5335
   (`ts_c3_20` on the seasonal frame); `ts_ac1_60` reads 0.373855 / 0.000844
   / 0.378744 / -0.202691. Run at `maxlag` 1 this module IS `ts_ac1_60` to
   5.6e-17.

9. **A blind spot that is the source's, not the port's.** Averaging lags
   1..10 cancels a seasonality whose period DIVIDES 10: paths repeating every
   2, 5 and 10 bars read medians of +0.000000 / +0.000008 / +0.000067 where
   the lag-1 column reads -1.0000 / -0.5872 / -0.5674.

Every number above comes from `docs/measure_ts_aggac_60.py`, whose run is
transcribed in `docs/TsAggac60Measured.md`. Numbers that depend on the CPU's
floating-point kernels are pinned as bounds or tolerances, never as exact
counts of moved or bit-equal bars.

Gate E is OWED: the launcher runs
`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py` after this
session and a later receipt session records the row. A test below asserts
that `docs/gate_e_ledger.csv` has NO row yet, so it fails the moment the row
lands and the receipt session is forced to come back here.
"""
import importlib
import inspect
import os
import types
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
from pandas_ta.statistics.ts_aggac_60 import ts_aggac_60

LENGTH, MAXLAG = 60, 10
#: Fewest overlapping bars an in-fork overlap comparison is allowed to rest
#: on. The 0.76 ship line is meaningless on a handful of bars, and one pair
#: (`roll_spread` on the AR(1) frame) really does overlap on 26 -- see
#: `test_the_column_does_not_restate_an_already_shipped_serial_statistic`.
MIN_OVERLAP = 200

_REAL = importlib.import_module("pandas_ta.statistics.ts_aggac_60")
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- frames


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.5):
    """A path whose LOG returns are an AR(1), `rlog[t] = phi*rlog[t-1] + eps`,
    whose population lag-`k` autocorrelation is exactly `phi**k`."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _seasonal(n=1500, seed=19, period=10, amp=0.01):
    """Returns that repeat exactly with `period`."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0, amp, period)
    r = np.tile(base, n // period + 1)[:n]
    return Series(100.0 * np.cumprod(1.0 + r))


def _alternating(n=1500, amp=0.01):
    r = np.where(np.arange(n) % 2 == 0, amp, -amp)
    return Series(100.0 * np.cumprod(1.0 + r))


def _mean_dominated(n=300, seed=3, mu=0.01, ratio=1e5):
    """Returns with a large MEAN and a tiny DISPERSION, well above the
    variance floor: the shape on which a raw product sum cancels."""
    rng = np.random.default_rng(seed)
    r = mu + rng.normal(0.0, abs(mu) / ratio, n)
    return Series(100.0 * np.cumprod(1.0 + r))


FRAMES = {"walk": _walk, "tick-rounded": _tick_rounded, "ar1(+0.5)": _ar1,
          "seasonal(10)": _seasonal}


# ------------------------------------------------------------- the source


def _tsfresh_autocorrelation(x, lag):
    """tsfresh `feature_calculators.autocorrelation`, retyped from its
    published definition:

        y1 = x[:len(x)-lag]; y2 = x[lag:]
        x_mean = np.mean(x)
        sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
        v = np.var(x)
        return np.NaN if np.isclose(v, 0) else \
            sum_product / ((len(x) - lag) * v)

    ⚠ tsfresh is NOT installed in this worktree and web access is
    unavailable, so this is the issue's line plus that published definition,
    not a read of tsfresh's own code."""
    x = np.asarray(x, dtype=float)
    y1, y2 = x[:len(x) - lag], x[lag:]
    x_mean = np.mean(x)
    sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
    v = np.var(x)
    if np.isclose(v, 0):
        return np.nan
    return sum_product / ((len(x) - lag) * v)


def _acf_adjusted(x, nlags):
    """`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False)[1:]`,
    retyped: `acovf[k] = sum_{t>=k} (x[t]-m)(x[t-k]-m) / (n-k)`, then divided
    by `acovf[0]`, whose own divisor is `n` -- so the quotient IS
    `sum / ((n-k) * population variance)`. This is the path
    `agg_autocorrelation` takes."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    xo = x - x.mean()
    acov = np.correlate(xo, xo, "full")[n - 1:] / np.arange(n, 0, -1)
    return (acov / acov[0])[1:nlags + 1]


def _source_windowed(close, length=LENGTH, maxlag=MAXLAG, guard="floor",
                     log_returns=False, closes_not_returns=False, ddof=0,
                     biased=False, lags=None, path="autocorrelation"):
    """The source formula applied window by window with
    `sliding_window_view`: no pandas rolling anywhere, so it shares no window
    machinery with the module. The keywords are the rejected readings."""
    px = close.astype(float)
    if log_returns:
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.log(px / px.shift(1)).to_numpy()
    else:
        with np.errstate(over="ignore"):
            r = (px / px.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    width = length - 1 if closes_not_returns else length
    if len(r) < width + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], width)
    ks = list(range(1, maxlag + 1)) if lags is None else list(lags)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        v = W.var(axis=1, ddof=ddof)
        if path == "acf":
            vals = np.array([float(np.mean(_acf_adjusted(w, maxlag)))
                             for w in W])
        else:
            m = W.mean(axis=1, keepdims=True)
            dev = W - m
            terms = []
            for k in ks:
                num = (dev[:, k:] * dev[:, :W.shape[1] - k]).sum(axis=1)
                norm = width if biased else width - k
                terms.append(num / (norm * v))
            vals = np.mean(terms, axis=0)
    if guard == "floor":                 # this module's guard
        vals = np.where(v > _REAL.VAR_FLOOR, vals, np.nan)
    elif guard == "isclose":             # tsfresh `autocorrelation`'s own
        vals = np.where(np.isclose(v, 0.0), np.nan, vals)
    elif guard == "tsfresh":             # `agg_autocorrelation`'s own
        vals = np.where(np.abs(v) < 1e-10, 0.0, vals)
    elif guard != "none":
        raise ValueError(guard)          # so a typo cannot mean "unguarded"
    out[width:] = vals
    return Series(out, index=close.index)


def _exact_loop(close, length=LENGTH, maxlag=MAXLAG, bars=40):
    """The EXACT value in `fractions.Fraction`: every close is a rational, so
    every return and the whole statistic is one. The only rounding is the
    final conversion. `bars` keeps the cost down -- it is the number of
    trailing bars evaluated."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(max(length, len(c) - bars), len(c)):
        x = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        m = sum(x) / length
        v = sum((u - m) ** 2 for u in x) / length
        if v != 0:
            total = 0
            for k in range(1, maxlag + 1):
                num = sum((x[i] - m) * (x[i - k] - m)
                          for i in range(k, length))
                total += num / ((length - k) * v)
            out[t] = float(total / maxlag)
    return Series(out, index=close.index)


def _plain_expansion(close, length=LENGTH, maxlag=MAXLAG):
    """The spelling the module REJECTS: each lag's numerator as a raw product
    sum with the mean subtracted afterwards. Algebraically identical, and it
    cancels when a window's mean dwarfs its dispersion."""
    px = close.astype(float)
    r = px / px.shift(1) - 1.0
    rolling = r.rolling(length, min_periods=length)
    mean, var = rolling.mean(), rolling.var(ddof=0)
    total = tail = head = 0.0
    for k in range(1, maxlag + 1):
        products = (r * r.shift(k)).rolling(length - k,
                                            min_periods=length - k).sum()
        tail = tail + r.shift(k - 1)
        head = head + r.shift(length - k)
        late, early = length * mean - head, length * mean - tail
        num = products - mean * (late + early) + (length - k) * mean * mean
        total = total + num / ((length - k) * var.where(var > _REAL.VAR_FLOOR))
    return total / maxlag


def _prototype(close, length=LENGTH, maxlag=MAXLAG):
    """`docs/issues/screen/ind_screen.py` candidate `ts_aggac_60`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            r = ret(c)
            return sum(corr(r, delay(r, k), 60) for k in range(1, 11)) / 10

    with `ret(c) = c / c.shift(1) - 1`, `delay(x, n) = x.shift(n)` and
    `corr(x, y, n) = (x.rolling(n).corr(y)).replace([inf, -inf], nan)`."""
    r = close / close.shift(1) - 1
    total = 0.0
    for k in range(1, maxlag + 1):
        total = total + r.rolling(length).corr(r.shift(k)).replace(
            [np.inf, -np.inf], np.nan)
    return total / maxlag


def _pearson_same_window(close, length=LENGTH, maxlag=MAXLAG):
    """`pandas.Series.autocorr` per lag on the module's OWN window: the same
    history, the Pearson normalisation (two means, two standard deviations)."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    W = sliding_window_view(r[1:], length)
    out[length:] = [float(np.mean([Series(w).autocorr(k)
                                   for k in range(1, maxlag + 1)])) for w in W]
    return Series(out, index=close.index)


# ------------------------------------------------------------- the bounds


def _lag_form(n, maxlag):
    """`x' M x = sum_k N_k / (n - k)` over the window's lag-`k` product sums:
    half on each of the `k`-th off-diagonals, weighted and averaged."""
    t = np.zeros((n, n))
    for k in range(1, maxlag + 1):
        i = np.arange(n - k)
        t[i, i + k] += 0.5 / (n - k)
        t[i + k, i] += 0.5 / (n - k)
    return t / maxlag


def _ortho_basis(n):
    """An orthonormal basis of the subspace orthogonal to the all-ones
    vector: the demeaned windows are exactly that subspace."""
    q, _ = np.linalg.qr(np.eye(n) - np.ones((n, n)) / n)
    keep = [c for c in range(n) if abs(float(np.ones(n) @ q[:, c])) < 1e-10]
    return q[:, keep[:n - 1]]


def _bounds(n, maxlag=MAXLAG):
    q = _ortho_basis(n)
    w = np.linalg.eigvalsh(q.T @ _lag_form(n, maxlag) @ q)
    return float(w.min() * n), float(w.max() * n)


def _extreme_closes(n, want_max, amp=0.01, maxlag=MAXLAG):
    q = _ortho_basis(n)
    w, vecs = np.linalg.eigh(q.T @ _lag_form(n, maxlag) @ q)
    y = q @ vecs[:, int(np.argmax(w)) if want_max else int(np.argmin(w))]
    r = amp * y / float(np.abs(y).max())
    return Series(np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + r)]))


# ------------------------------------------------------------ Gate A tests


@pytest.mark.parametrize("length,maxlag", [(4, 2), (20, 2), (60, 2),
                                           (60, 4), (60, 10), (60, 58)])
def test_an_alternating_window_is_exactly_zero_at_an_even_maxlag(length,
                                                                 maxlag):
    """`close = [1, 2, 1, 2, ...]` holds returns alternating between +1 and
    -1/2, i.e. `m +- d` with `d = 3/4` exactly. Every deviation is `+-d`, so
    every one of the `length - k` lag-`k` products is `(-1)**k * d**2` and the
    population variance is `d**2`: `AC[k] = (-1)**k` EXACTLY, and the mean
    over an even `maxlag` is a sum of `+-d**2` that cancels pair by pair to a
    true zero. Nothing here is a difference of unequal floats, so the
    assertion is bit-exact rather than a tolerance."""
    closes = Series(np.where(np.arange(4 * length) % 2 == 0, 1.0, 2.0))
    out = ts_aggac_60(closes, length=length, maxlag=maxlag)
    assert out.name == f"TS_AGGAC_{length}_{maxlag}"
    assert out.iloc[:length].isna().all()
    fired = out.dropna()
    assert len(fired) > 0
    assert (fired == 0.0).all(), sorted(set(fired.to_numpy().tolist()))


@pytest.mark.parametrize("maxlag", [1, 3, 9])
def test_an_alternating_window_reads_minus_one_over_maxlag_at_an_odd_one(
        maxlag):
    """The same `AC[k] = (-1)**k`, summed over an ODD `maxlag`: one unpaired
    `-1` survives, so the mean is `-1/maxlag`. `-1/9` is not a binary
    fraction, so this one is a tolerance."""
    col = ts_aggac_60(_alternating(300), length=LENGTH,
                      maxlag=maxlag).dropna()
    assert len(col) > 100
    assert float((col + 1.0 / maxlag).abs().max()) < 1e-13


def test_the_two_published_spellings_of_the_source_are_the_same_number():
    """The issue names `agg_autocorrelation`, which goes through
    `statsmodels`' `acf(adjusted=True)`; `feature_calculators.autocorrelation`
    spells the quotient directly. `acovf[k]` divides by `n - k` and `acovf[0]`
    by `n`, so the two are algebraically identical -- and this measures it
    instead of resting on that sentence."""
    rng = np.random.default_rng(5)
    worst = 0.0
    for _ in range(200):
        x = rng.normal(0.0, 1.0, LENGTH)
        direct = float(np.mean([_tsfresh_autocorrelation(x, k)
                                for k in range(1, MAXLAG + 1)]))
        viaacf = float(np.mean(_acf_adjusted(x, MAXLAG)))
        worst = max(worst, abs(direct - viaacf))
    assert worst < 1e-14, worst


def test_the_retyped_adjusted_acf_matches_statsmodels_when_it_is_installed():
    """statsmodels IS installed in this worktree and the retype reproduces it
    bit-exactly; the skip keeps the suite green where it is not, since the
    package is not a dependency of this fork."""
    sm = pytest.importorskip("statsmodels.tsa.stattools")
    rng = np.random.default_rng(17)
    for _ in range(20):
        x = rng.normal(0.0, 1.0, LENGTH)
        mine = _acf_adjusted(x, MAXLAG)
        theirs = sm.acf(x, adjusted=True, fft=False, nlags=MAXLAG)[1:]
        assert float(np.abs(mine - theirs).max()) < 1e-15


@pytest.mark.parametrize("name", list(FRAMES))
@pytest.mark.parametrize("path", ["autocorrelation", "acf"])
def test_the_module_matches_the_source_formula_window_by_window(name, path):
    """`sliding_window_view`, no pandas rolling anywhere, through BOTH
    published spellings. Measured max |difference| 5.7e-15 on the walk.

    The absolute agreement is the pin; the Spearman floor is loose on
    purpose. On `seasonal(10)` the returns repeat exactly every 10 bars, so
    the column repeats too and the frame is full of NEAR-TIES that a 3e-15
    disagreement reorders -- the measured Spearman there is 0.9909 where the
    other three frames read 1.000000. A rank statistic says nothing useful
    about a tied column; the second assertion below, which scales the
    difference by the column's own range, is what carries the claim."""
    frame = FRAMES[name]()
    base, other = ts_aggac_60(frame), _source_windowed(frame, path=path)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) > 1000
    worst = float((base[m] - other[m]).abs().max())
    assert worst < 1e-12
    assert worst < 1e-9 * float(base[m].max() - base[m].min())
    assert float(base[m].corr(other[m], method="spearman")) > 0.98


@pytest.mark.parametrize("name,frame_fn", [
    ("walk", lambda: _walk(300, seed=11)),
    ("tick-rounded", lambda: _tick_rounded(300, seed=55)),
])
def test_the_module_is_close_to_an_exact_rational_oracle(name, frame_fn):
    """Against `fractions.Fraction`, the module measures 2.4e-15 on the walk
    and 1.2e-15 tick-rounded, where a `math.fsum` loop is 3.3e-16 -- the
    rewritten numerator costs about seven times an exact summation on an
    ordinary frame, and buys the mean-dominated case below."""
    frame = frame_fn()
    exact = _exact_loop(frame)
    m = exact.notna()
    assert int(m.sum()) == 40
    assert float((ts_aggac_60(frame)[m] - exact[m]).abs().max()) < 1e-13


def test_the_raw_sum_expansion_loses_the_statistic_when_the_mean_dominates():
    """The whole justification for the `2uv = u^2 + v^2 - (u-v)^2` spelling.
    On returns with `|mean| / sd = 1e5` the module measured 2.0e-10 from the
    exact rational value and the plain raw-sum expansion 1.3e-06, about
    6.8e+03 times worse. Pinned as an ORDER-of-magnitude gap, not as either
    number: both move with the CPU's kernels, their ratio does not."""
    frame = _mean_dominated()
    exact = _exact_loop(frame)
    m = exact.notna()
    mine = float((ts_aggac_60(frame)[m] - exact[m]).abs().max())
    plain = float((_plain_expansion(frame)[m] - exact[m]).abs().max())
    assert mine < 1e-8
    assert plain > 100 * mine, (mine, plain)


@pytest.mark.parametrize("length,maxlag", [(12, 10), (20, 10), (60, 10),
                                           (60, 1), (60, 5)])
def test_the_reachable_bounds_are_attained_on_the_eigenvector_window(length,
                                                                     maxlag):
    """The column is `length` times a Rayleigh quotient of the lag-weighted
    product form restricted to the demeaned subspace, so its extremes are that
    form's extreme eigenvalues. Measured agreement 6.7e-16 at the default."""
    lo, hi = _bounds(length, maxlag)
    assert lo < 0.0 < hi
    for want_max, target in ((True, hi), (False, lo)):
        closes = _extreme_closes(length, want_max, maxlag=maxlag)
        got = float(ts_aggac_60(closes, length=length,
                                maxlag=maxlag).iloc[-1])
        assert abs(got - target) < 1e-12, (got, target)


def test_the_default_bounds_are_asymmetric_and_nothing_leaves_them():
    """[-0.310043, +0.915798] at `length` 60 / `maxlag` 10. The floor is three
    times nearer zero than the ceiling because a window cannot be negative at
    ten lags at once -- an alternating path is negative at the odd lags and
    POSITIVE at the even ones."""
    lo, hi = _bounds(LENGTH, MAXLAG)
    assert abs(lo - (-0.310042715573)) < 1e-9
    assert abs(hi - 0.915797875473) < 1e-9
    for frame_fn in list(FRAMES.values()) + [_alternating, _mean_dominated]:
        col = ts_aggac_60(frame_fn()).dropna()
        assert len(col) > 0
        assert float(col.min()) >= lo - 1e-12
        assert float(col.max()) <= hi + 1e-12


def test_the_screen_prototype_is_a_different_column():
    """Issue #96's prototype is ten PEARSON correlations of two 60-pair
    slices, so its lag-10 term reads 70 returns and the whole thing starts 10
    bars later. Gate A starts from the source formula, not from it."""
    close = _walk()
    base, proto = ts_aggac_60(close), _prototype(close)
    assert int(base.notna().idxmax()) == LENGTH
    assert int(proto.notna().idxmax()) == LENGTH + MAXLAG
    m = base.notna() & proto.notna()
    assert float((base[m] - proto[m]).abs().max()) > 1e-2
    rho = float(base[m].corr(proto[m], method="spearman"))
    assert 0.85 < rho < 0.95, rho


@pytest.mark.skipif(
    not os.path.isfile(os.path.join(_HERE, "docs", "issues", "screen",
                                    "ind_screen.py")),
    reason="docs/issues/ is gitignored; a clone does not carry the screen")
def test_the_retyped_prototype_reproduces_the_owners_registry_entry():
    """`_prototype` above is a retype. When the owner's tree is present, the
    retype and `REG['ts_aggac_60']['fn']` agree bit-for-bit, so the comparison
    in the test above is against the real prototype and not a paraphrase."""
    import importlib.util
    import sys

    path = os.path.join(_HERE, "docs", "issues", "screen", "ind_screen.py")
    spec = importlib.util.spec_from_file_location("_ind_screen_aggac", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen_aggac"] = mod
    spec.loader.exec_module(mod)
    close = _walk()
    theirs = mod.REG["ts_aggac_60"]["fn"](close, close, close, close, close)
    mine = _prototype(close)
    assert (mine.isna() == theirs.isna()).all()
    m = mine.notna()
    assert (mine[m] == theirs[m]).all()


def test_including_lag_zero_is_an_affine_map_the_rank_miner_cannot_see():
    """`acf(...)[1:]` then `a[:maxlag]` is lags 1..10. Including lag 0, which
    is identically 1, maps the column to `1/11 + (10/11)*TS_AGGAC`: Spearman
    exactly 1, max |difference| 9.7e-02. Priced so the off-by-one is not
    re-argued, and so a threshold rule is known to be able to see it."""
    close = _walk()
    base = ts_aggac_60(close)
    withzero = _source_windowed(close, lags=range(0, MAXLAG + 1))
    m = base.notna() & withzero.notna()
    affine = 1.0 / (MAXLAG + 1) + (MAXLAG / (MAXLAG + 1.0)) * base[m]
    assert float((withzero[m] - affine).abs().max()) < 1e-12
    assert float((base[m] - withzero[m]).abs().max()) > 1e-2


@pytest.mark.parametrize("label,kwargs,lo,hi", [
    ("log returns", {"log_returns": True}, 0.999, 0.99999),
    ("60 closes, not 60 returns", {"closes_not_returns": True}, 0.95, 0.99),
    ("length*v divisor (biased)", {"biased": True}, 0.99, 0.999),
    ("sample variance", {"ddof": 1}, 0.9999999, 1.0000001),
])
def test_the_rejected_readings_are_measurably_different_columns(label, kwargs,
                                                                lo, hi):
    """Each reading the issue's one-line formula leaves open, priced by its
    Spearman against the shipped column so none of them is re-argued from
    first principles. The `ddof=1` row is the one that is NOT a different
    ORDER: it is one constant factor, `59/60`."""
    close = _walk()
    base, other = ts_aggac_60(close), _source_windowed(close, **kwargs)
    m = base.notna() & other.notna()
    assert int(m.sum()) > 1000
    rho = float(base[m].corr(other[m], method="spearman"))
    assert lo <= rho <= hi, (label, rho)
    assert float((base[m] - other[m]).abs().max()) > 1e-4


def test_a_pearson_correlation_per_lag_is_a_different_column():
    """The source divides every lag by ONE window mean and ONE population
    variance. `pandas.Series.autocorr` uses two means and two standard
    deviations per lag -- the prototype's normalisation on this port's
    window."""
    close = _walk()
    base, other = ts_aggac_60(close), _pearson_same_window(close)
    m = base.notna() & other.notna()
    assert 0.99 < float(base[m].corr(other[m], method="spearman")) < 0.999
    assert float((base[m] - other[m]).abs().max()) > 1e-3


def test_at_maxlag_one_this_module_is_the_shipped_lag_1_column():
    """A cross-check against code that was reviewed separately: at `maxlag` 1
    the aggregate has one term and must BE `ts_ac1_60`. The two differ only in
    division order -- `/(maxlag*v)` here, `/((length-lag)*v)` there -- so the
    bound is a few ulps and not bit-equality."""
    close = _walk()
    mine = ts_aggac_60(close, maxlag=1)
    theirs = ts_ac1_60(close)
    assert mine.name == "TS_AGGAC_60_1"
    assert (mine.isna() == theirs.isna()).all()
    m = mine.notna()
    assert float((mine[m] - theirs[m]).abs().max()) < 1e-14


def _siblings():
    """Every `Category` module whose value is a function of the SAME series at
    a fixed offset, enumerated by hand from `pandas_ta/__init__.py` rather
    than by grepping for `.corr(` against a `shift(` -- that grep misses
    `lean_momersion_20` (a product of two signs) and `ts_cid_ce_20` (a sum of
    squared successive differences), which are serial-dependence statistics
    with no correlation call in them."""
    from pandas_ta.momentum.a101_048 import a101_048
    from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20
    from pandas_ta.statistics.g191_026 import g191_026
    from pandas_ta.statistics.ts_c3_20 import ts_c3_20
    from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20
    from pandas_ta.volatility.roll_spread import roll_spread
    return {"ts_ac1_60": ts_ac1_60, "ts_cid_ce_20": ts_cid_ce_20,
            "lean_momersion_20": lean_momersion_20, "ts_c3_20": ts_c3_20,
            "g191_026": lambda c: g191_026(c, c, c),
            "a101_048": a101_048, "roll_spread": roll_spread}


@pytest.mark.parametrize("name", list(FRAMES))
@pytest.mark.parametrize("sibling", ["ts_ac1_60", "ts_cid_ce_20",
                                     "lean_momersion_20", "ts_c3_20",
                                     "g191_026", "a101_048", "roll_spread"])
def test_the_column_does_not_restate_an_already_shipped_serial_statistic(
        sibling, name):
    """Gate E's 687 comparators hold no pandas_ta port, so this fork's own
    overlap has to be measured here or nowhere. Averaging ten lags is not a
    restatement of the lag-1 column (measured Spearman 0.3739 / 0.0008 /
    0.3787 / -0.2027 against `ts_ac1_60`), and the worst of the 28
    frame/column pairs is 0.5335, `ts_c3_20` on the seasonal frame. The bound
    asserted here is the repo's 0.76 SHIP line, which is the line that would
    actually matter if these columns were in Gate E's comparator set.

    Two of the 28 pairs are skipped rather than passed, because passing them
    would be passing on nothing. `lean_momersion_20` is CONSTANT on the
    seasonal frame -- every return pair has the same sign pattern -- so its
    Spearman there is NaN. And `roll_spread`'s `ROLL_20` is NaN wherever the
    window's lag-1 autocovariance is non-negative, which a +0.5-AR(1) path
    almost never produces: it overlaps this column on 26 of 1,440 bars there,
    where a Spearman carries a standard error of about 0.2. `MIN_OVERLAP`
    rejects that instead of asserting a bound on it."""
    frame = FRAMES[name]()
    a, b = ts_aggac_60(frame), _siblings()[sibling](frame)
    m = a.notna() & b.notna()
    if int(m.sum()) < MIN_OVERLAP:
        pytest.skip(f"{sibling} overlaps this column on {int(m.sum())} bars "
                    f"of {name}; too few for a Spearman to mean anything")
    if float(b[m].std()) == 0.0:
        pytest.skip(f"{sibling} is constant on {name}; no rank to compare")
    rho = float(a[m].corr(b[m], method="spearman"))
    assert abs(rho) < 0.76, (sibling, name, rho)


@pytest.mark.parametrize("period,divides", [(2, True), (3, False), (5, True),
                                            (7, False), (10, True)])
def test_a_seasonality_whose_period_divides_maxlag_is_invisible(period,
                                                                divides):
    """A property of `f_agg='mean'`, not a defect of the port: the lag-`k`
    autocorrelations of an exactly periodic window sum to zero over a whole
    cycle of rotations, so a period dividing 10 cancels. The lag-1 column
    sees all five of these paths; this one sees only the two that do not
    divide, and then only faintly."""
    frame = _seasonal(1500, period=period)
    agg = float(ts_aggac_60(frame).dropna().median())
    one = float(ts_aggac_60(frame, maxlag=1).dropna().median())
    assert abs(one) > 0.4
    if divides:
        assert abs(agg) < 1e-3, agg
    else:
        assert 1e-3 < abs(agg) < 0.2, agg


# ------------------------------------------------------------ Gate B tests


OFFSETS = range(100, 1500, 40)

MUTANTS = {
    "write_shift": ("    tsaggac = weighted / (maxlag * var.where(",
                    "    tsaggac = weighted.shift(-length) / (maxlag * "
                    "var.where("),
    "forward_return": ("        r = px / px.shift(1) - 1.0",
                       "        r = px.shift(-1) / px - 1.0"),
    "forward_head": ("        head = head + (r.shift(length - k) - mean) ** 2",
                     "        head = head + (r.shift(-(length - k)) - mean) "
                     "** 2"),
    "forward_tail": ("        tail = tail + (r.shift(k - 1) - mean) ** 2",
                     "        tail = tail + (r.shift(-(k - 1)) - mean) ** 2"),
    "centered_var": ("    var = rolling.var(ddof=0)",
                     "    var = r.rolling(length, min_periods=length, "
                     "center=True).var(ddof=0)"),
    "centered_mean": ("    mean = rolling.mean()",
                      "    mean = r.rolling(length, min_periods=length, "
                      "center=True).mean()"),
    "centered_gap": ("        gap = gap.rolling(length - k, "
                     "min_periods=length - k).sum()",
                     "        gap = gap.rolling(length - k, "
                     "min_periods=length - k, center=True).sum()"),
    "forward_diff": ("        gap = Series(np.square(r.diff(k).to_numpy()), "
                     "index=r.index)",
                     "        gap = Series(np.square(r.diff(-k).to_numpy()), "
                     "index=r.index)"),
}

#: `span` feeds ONLY the trust test, which costs 0 bars on a clean frame, so
#: a look-ahead confined to it moves nothing on the three frames above. It
#: gets its own mutant and its own frame -- one where the guard fires.
SPAN_MUTANT = ("    span = rolling.max() - rolling.min()",
               "    _c = r.rolling(length, min_periods=length, center=True)\n"
               "    span = _c.max() - _c.min()")


def _spiked(n=1500, seed=21, at=200, factor=1e8):
    """A walk with one planted return of about 1e+8: the frame on which the
    accumulator trust test actually fires."""
    frame = _walk(n, seed=seed)
    frame.iloc[at] = float(frame.iloc[at - 1]) * factor
    return frame


def _load_mutant(label):
    """`importlib`-read the module's own source, replace one write index, and
    `exec` the result in memory. Nothing on disk changes."""
    old, new = SPAN_MUTANT if label == "centered_span" else MUTANTS[label]
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_ts_aggac_60_mutant_{label}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn, close, other):
    """Replace every bar from J onward with a different path; count the J
    values at which anything strictly before J moves."""
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        moved = not (a.isna() == b.isna()).all()
        if not moved:
            mask = a.notna()
            moved = bool((a[mask] != b[mask]).any())
        hits += int(moved)
    return hits


PAIRS = {"walk": (_walk, lambda: _walk(seed=97)),
         "tick-rounded": (_tick_rounded, lambda: _tick_rounded(seed=56)),
         "ar1(+0.5)": (_ar1, lambda: _ar1(seed=8))}


@pytest.mark.parametrize("name", list(PAIRS))
def test_the_module_never_reads_the_future(name):
    """A future-perturbation sweep, not prefix truncation: every bar from J on
    is replaced by a different path and nothing before J may move."""
    a, b = PAIRS[name]
    assert _leaks(ts_aggac_60, a(), b()) == 0


@pytest.mark.parametrize("label", list(MUTANTS))
@pytest.mark.parametrize("name", list(PAIRS))
def test_every_mutant_that_reads_forward_is_caught(label, name):
    """Gate B proper. Each mutation moves one write index earlier (or widens
    one window to `center=True`); the sweep must catch it at EVERY offset, and
    the mutation must be live -- a mutant that computes the same column would
    pass the sweep for the wrong reason."""
    a, b = PAIRS[name]
    close, other = a(), b()
    mod = _load_mutant(label)
    assert not mod.ts_aggac_60(close).equals(ts_aggac_60(close))
    assert _leaks(mod.ts_aggac_60, close, other) == len(list(OFFSETS))


def test_the_span_mutant_is_invisible_on_a_clean_frame_and_caught_where_the_trust_test_fires():
    """The one write index the eight mutants above cannot reach. `span` feeds
    only `trusted`, and the guards section measures that the trust test costs
    0 bars on every clean frame -- so a `center=True` on the two extrema is
    LIVE (it changes the column) and still invisible to a sweep run on a
    clean walk: measured 0 of 35 offsets. On a frame with a planted 1e+8
    return, where `trusted` actually bites, the same mutant is caught at 13 of
    35 offsets -- the ones whose J sits within reach of the spike.

    This is pinned because it is a real hole in Gate B's usual shape, not
    because it is comfortable: a future edit that centres the extrema would
    be a NaN-mask look-ahead that the three clean frames would not see."""
    mod = _load_mutant("centered_span")
    clean, other = _walk(), _walk(seed=97)
    assert not mod.ts_aggac_60(clean).equals(ts_aggac_60(clean))
    assert _leaks(mod.ts_aggac_60, clean, other) == 0
    spiked, spiked_other = _spiked(), _spiked(seed=97)
    assert _leaks(ts_aggac_60, spiked, spiked_other) == 0
    assert _leaks(mod.ts_aggac_60, spiked, spiked_other) > 0


def test_prefix_truncation_alone_would_not_catch_a_back_dated_mutant():
    """Why the sweep above is a perturbation and not a truncation. The
    `write_shift` mutant back-dates the whole column by `length` bars: fed a
    truncated prefix it still returns a self-consistent series, so
    `fn(close[:j])` agrees with `fn(close)[:j]` on the bars both produce -- and
    only replacing the FUTURE with a different path exposes it."""
    close = _walk()
    mod = _load_mutant("write_shift")
    j = 600
    full = mod.ts_aggac_60(close).iloc[:j]
    cut = mod.ts_aggac_60(close.iloc[:j])
    m = full.notna() & cut.notna()
    assert int(m.sum()) > 400
    assert (full[m] == cut[m]).all(), "truncation would have caught it"
    assert _leaks(mod.ts_aggac_60, close, _walk(seed=97)) == len(list(OFFSETS))


# ---------------------------------------------------------- Gate C/D tests


@pytest.mark.parametrize("name", list(FRAMES))
def test_every_bar_after_the_warm_up_fires_and_the_column_is_not_constant(
        name):
    """Gate C on synthetic frames, and the `0 < fires < n` half of Gate D. The
    real-data counts are owed with Gate E, which the launcher runs."""
    frame = FRAMES[name]()
    out = ts_aggac_60(frame)
    fired = out.dropna()
    assert out.iloc[:LENGTH].isna().all()
    assert len(fired) == len(frame) - LENGTH
    assert 0 < len(fired) < len(frame)
    assert fired.nunique() > len(fired) // 2
    assert float(fired.std()) > 1e-6


@pytest.mark.parametrize("k", [8.0, 64.0])
@pytest.mark.parametrize("name", list(PAIRS))
def test_the_column_is_scale_free_and_bit_identical_at_a_power_of_two(name, k):
    """Gate D's strong half. Every input is a price RATIO and `8a / 8b` is the
    same double as `a / b`, so a x2^k rescale cancels exactly rather than to
    rounding."""
    close = PAIRS[name][0]()
    base, scaled = ts_aggac_60(close), ts_aggac_60(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) > 1000
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("length,maxlag", [(12, 10), (20, 10), (250, 10),
                                           (60, 1), (60, 30)])
def test_the_column_is_scale_free_at_other_lengths_too(length, maxlag):
    close = _walk()
    base = ts_aggac_60(close, length=length, maxlag=maxlag)
    scaled = ts_aggac_60(close * 8.0, length=length, maxlag=maxlag)
    m = base.notna()
    assert int(m.sum()) > 100
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_the_column_is_scale_free_within_tolerance_at_a_non_power_of_two(k):
    """x10 and x3.7 perturb the returns in their last bits, so this is the
    tolerance reading: identical NaN masks, 9.5e-15 agreement, Spearman 1."""
    close = _walk()
    base, scaled = ts_aggac_60(close), ts_aggac_60(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-12
    assert float(base[m].corr(scaled[m], method="spearman")) > 0.9999999


@pytest.mark.parametrize("label,factor", [("x2", 2.0), ("x0.5", 0.5)])
def test_the_column_is_invariant_to_an_affine_map_of_the_returns(label,
                                                                 factor):
    """Stronger than price scale-freedom, and the property a consumer should
    read first: doubling every RETURN leaves the column where it was."""
    close = _walk()
    r = (close / close.shift(1) - 1.0).to_numpy()[1:]
    rebuilt = Series(np.concatenate(
        [[float(close.iloc[0])],
         float(close.iloc[0]) * np.cumprod(1.0 + factor * r)]))
    base, other = ts_aggac_60(close), ts_aggac_60(rebuilt)
    m = base.notna() & other.notna()
    assert float((base[m] - other[m]).abs().max()) < 1e-12
    assert float(base[m].corr(other[m], method="spearman")) > 0.9999999


def test_adding_a_constant_drift_to_every_return_leaves_the_column():
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    base, other = ts_aggac_60(close), ts_aggac_60(drifted)
    m = base.notna() & other.notna()
    assert float((base[m] - other[m]).abs().max()) < 1e-12


def test_the_ratio_return_is_what_makes_the_x8_rescale_bit_identical():
    """A difference of logarithms would not be: measured bit-equal on 821 of
    1,499 bars at x8 where the ratio spelling is bit-equal on all of them.
    Pinned as 'the ratio is exact and the log difference is not', because the
    821 is a CPU-dependent count."""
    close = _walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    assert (ratio[m] == ratio8[m]).all()
    assert not (plain[m] == plain8[m]).all()


# ------------------------------------------------------------ guard tests


def _module_variant(close, length=LENGTH, maxlag=MAXLAG, overflow=True,
                    trust=True, finite=False):
    """The module's own computation with one guard switchable, so each can be
    priced against the shipped code rather than argued for. `finite=True`
    ADDS the `r.where(np.isfinite(r))` line that `ts_ac1_60` spells and this
    module does not."""
    px = close.astype(float).to_numpy()
    px = np.where(np.isfinite(px) & (px >= np.finfo(float).tiny), px, np.nan)
    px = Series(px, index=close.index)
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    if finite:
        r = r.where(np.isfinite(r))
    if overflow:
        with np.errstate(over="ignore"):
            square = np.square(r.to_numpy())
        r = r.where(square < np.finfo(float).max / (8 * length))
    rolling = r.rolling(length, min_periods=length)
    mean, var = rolling.mean(), rolling.var(ddof=0)
    span = rolling.max() - rolling.min()
    bound = span * span
    with np.errstate(over="ignore", invalid="ignore"):
        ok = var > _REAL.VAR_FLOOR
        if trust:
            ok = ok & (var <= 0.25 * bound * (1.0 + _REAL.NOISE_FLOOR))
        head = tail = weighted = 0.0
        for k in range(1, maxlag + 1):
            tail = tail + (r.shift(k - 1) - mean) ** 2
            head = head + (r.shift(length - k) - mean) ** 2
            gap = Series(np.square(r.diff(k).to_numpy()), index=r.index)
            gap = gap.rolling(length - k, min_periods=length - k).sum()
            if trust:
                ok = ok & (gap <= (length - k) * bound
                           * (1.0 + _REAL.NOISE_FLOOR))
            weighted = weighted + (length * var
                                   - 0.5 * (head + tail + gap)) / (length - k)
        return weighted / (maxlag * var.where(ok))


def test_a_window_with_no_dispersion_is_nan_and_not_a_fabricated_zero():
    """tsfresh's `agg_autocorrelation` takes an `np.abs(var) < 1e-10` branch
    and returns the mean of zeros, i.e. exactly 0.0 -- a reading this column
    produces all the time, so the fabrication is invisible downstream. This
    module reports nothing instead."""
    flat = Series([100.0] * 300)
    assert int(ts_aggac_60(flat).notna().sum()) == 0
    tsf = _source_windowed(flat, guard="tsfresh")
    assert int((tsf == 0.0).sum()) == 300 - LENGTH


def test_a_geometric_ladder_is_nan_here_and_rounding_noise_unguarded():
    """Returns that are mathematically constant but vary at rounding level in
    float64. Unguarded, the quotient is the ratio of two roundings and reads
    an ordinary-looking number out of nothing."""
    ladder = Series(100.0 * np.exp(np.arange(300) * 0.01))
    assert int(ts_aggac_60(ladder).notna().sum()) == 0
    loose = _source_windowed(ladder, guard="none").dropna()
    assert len(loose) == 300 - LENGTH
    assert float(loose.abs().max()) > 1e-3


@pytest.mark.parametrize("sigma", [1e-6, 1e-9])
def test_a_low_volatility_walk_still_reports_here_where_tsfresh_would_not(
        sigma):
    """tsfresh's threshold is on the variance of RETURNS, so it fires at a
    return sd below 1e-5 -- an ordinary low-volatility series. This module's
    floor is 8.27e-25 on that variance, so the walk reports."""
    frame = _walk(300, sigma=sigma)
    col = ts_aggac_60(frame).dropna()
    assert len(col) == 300 - LENGTH
    assert float(col.abs().max()) > 1e-3
    assert int(_source_windowed(frame, guard="isclose").notna().sum()) == 0
    assert int((_source_windowed(frame, guard="tsfresh") == 0.0).sum()) == \
        300 - LENGTH


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_one_bad_close_empties_its_own_windows_and_no_earlier_bar(bad):
    """A close that is not a finite, normal, positive float has no return to
    take. It spoils two returns, so it empties the `length + 1` windows it
    sits in -- and nothing before it."""
    base_frame = _walk(400, seed=21)
    base = ts_aggac_60(base_frame)
    holed = base_frame.copy()
    holed.iloc[200] = bad
    out = ts_aggac_60(holed)
    lost = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(lost) == LENGTH + 1
    assert (int(lost.min()), int(lost.max())) == (200, 200 + LENGTH)
    earlier = base.iloc[:200]
    assert (earlier[earlier.notna()] == out.iloc[:200][earlier.notna()]).all()


@pytest.mark.parametrize("label,planted", [
    ("close 1e-300 (next return ~1e+302)", {200: 1e-300}),
    ("an INFINITE ratio", {200: 1e-300, 201: 1e+300}),
    ("close inf", {200: np.inf}),
    ("close nan", {200: np.nan}),
    ("nothing planted", {}),
])
def test_the_isfinite_filter_this_module_omits_would_change_nothing(label,
                                                                    planted):
    """`ts_ac1_60` spells `r.where(np.isfinite(r))` between the ratio and the
    square bound; this module does not, because the bound already rejects the
    same values -- an infinite return squares to infinity and a NaN compares
    False. That is a claim about the shipped code, so it is measured: adding
    the line back is bit-identical on every frame that can produce a
    non-finite return, and still bit-identical with the square bound REMOVED,
    where the filter would be the only thing left to catch an infinity."""
    frame = _walk(400, seed=21)
    for idx, v in planted.items():
        frame.iloc[idx] = v
    # The absence itself, not only its consequence: a future edit that
    # re-adds the line would otherwise leave this test comparing one filtered
    # spelling against another. Comments and the docstring are skipped --
    # both discuss the line by name.
    body = open(_REAL.__file__, encoding="utf-8").read().split(
        "ts_aggac_60.__doc__")[0]
    code = [ln for ln in body.splitlines() if not ln.strip().startswith("#")]
    assert not any("np.isfinite(r)" in ln for ln in code), (
        "the shipped module grew back the filter this test prices as a no-op")
    shipped, with_filter = ts_aggac_60(frame), _module_variant(frame,
                                                               finite=True)
    assert (shipped.isna() == with_filter.isna()).all()
    m = shipped.notna()
    assert (shipped[m] == with_filter[m]).all()
    # The sub-case where the filter would be the only thing left: values, not
    # just masks. A mask can agree while the numbers behind it do not.
    a = _module_variant(frame, overflow=False, finite=True)
    b = _module_variant(frame, overflow=False)
    assert (a.isna() == b.isna()).all()
    mb = a.notna() & b.notna()
    assert (a[mb] == b[mb]).all()


def test_the_square_bound_keeps_an_unrepresentable_return_local():
    """pandas accumulates `rolling.var` and `rolling.sum` ONLINE, so an
    infinite accumulator never leaves the window and every LATER bar comes
    back NaN too. With the bound, one close of 1e-300 at bar 200 of a 400-bar
    frame costs 60 bars; without it, 199 -- the rest of the frame."""
    base_frame = _walk(400, seed=21)
    base = ts_aggac_60(base_frame)
    holed = base_frame.copy()
    holed.iloc[200] = 1e-300
    guarded = ts_aggac_60(holed)
    unguarded = _module_variant(holed, overflow=False)
    lost_g = int((base.notna() & guarded.isna()).sum())
    lost_u = int((base.notna() & unguarded.isna()).sum())
    assert lost_g == LENGTH
    assert lost_u > 3 * lost_g


def test_the_trust_test_turns_a_gross_accumulator_residue_into_nan():
    """One planted return of 1e+8 -- a decimal-point error in a feed, well
    inside the overflow bound. The 139 bars after it has left every window are
    NaN here; without the test they are up to 1.149 away from a per-window
    oracle, with no NaN to mark them."""
    base_frame = _walk(400, seed=21)
    holed = base_frame.copy()
    holed.iloc[200] = float(base_frame.iloc[199]) * 1e8
    tail = slice(261, 400)
    strict = ts_aggac_60(holed).iloc[tail]
    loose = _module_variant(holed, trust=False).iloc[tail]
    oracle = _source_windowed(holed).iloc[tail]
    assert strict.isna().all()
    assert loose.notna().all()
    assert float((loose - oracle).abs().max()) > 1.0


@pytest.mark.parametrize("name,frame_fn", [
    ("walk", _walk), ("tick-rounded", _tick_rounded), ("ar1(+0.5)", _ar1),
    ("seasonal(10)", _seasonal), ("alternating", _alternating),
    ("low-vol walk", lambda: _walk(1500, sigma=1e-6)),
])
def test_the_trust_test_costs_nothing_on_a_clean_frame(name, frame_fn):
    """It has to be free where it is not needed, or it is a reachability bug.
    The alternating frame is the EQUALITY case -- its variance attains
    `(span/2)**2` exactly -- so it is the one that proves the slack is
    enough."""
    frame = frame_fn()
    strict, loose = ts_aggac_60(frame), _module_variant(frame, trust=False)
    assert int((loose.notna() & strict.isna()).sum()) == 0
    assert int(strict.notna().sum()) == len(frame) - LENGTH


def test_a_volatility_collapse_is_caught_by_the_floor_not_the_trust_test():
    """`ts_cid_ce_20` found a regime COLLAPSE -- sigma 0.3 for 200 bars, then
    sigma 1e-9 -- to be the shape pandas' online accumulators really lose, and
    its trust test is what saved it there. This column's does not have to:
    the variance floor gets there first, because the online variance comes
    back at or below 8.27e-25 on 141 of the 200 post-collapse bars. The trust
    test costs 0 bars here too, and the bars that do report are 3.6e-14 from
    the per-window oracle with it or without it."""
    rng = np.random.default_rng(5)
    r = np.concatenate([rng.normal(0.0, 0.3, 200),
                        rng.normal(0.0, 1e-9, 200)])
    collapse = Series(100.0 * np.exp(np.cumsum(r)))
    strict = ts_aggac_60(collapse)
    loose = _module_variant(collapse, trust=False)
    oracle = _source_windowed(collapse)
    assert int((loose.notna() & strict.isna()).sum()) == 0
    rc = collapse / collapse.shift(1) - 1.0
    v = rc.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
    assert int((v.iloc[200:400] <= _REAL.VAR_FLOOR).sum()) > 100
    m = strict.iloc[200:400].notna() & oracle.iloc[200:400].notna()
    assert int(m.sum()) > 10
    assert float((strict.iloc[200:400][m]
                  - oracle.iloc[200:400][m]).abs().max()) < 1e-12


def test_a_long_enough_flat_run_empties_exactly_its_own_windows():
    """`length` identical closes leave `length - 1` zero returns and one
    non-zero one, so the window still has dispersion; `length + 1` is the
    first run that empties a window."""
    base_frame = _walk(400, seed=21)
    base = ts_aggac_60(base_frame)
    for run, expected in ((LENGTH, 0), (LENGTH + 1, 1), (LENGTH + 5, 5)):
        flat = base_frame.copy()
        flat.iloc[200:200 + run] = float(base_frame.iloc[200])
        out = ts_aggac_60(flat)
        assert int((base.notna() & out.isna()).sum()) == expected


def test_the_floor_is_on_the_dispersion_and_not_on_the_price():
    """A fine-tick ladder at a high price has returns of 1e-9: the dispersion,
    not the level, is what the floor reads."""
    coarse = Series(50.0 + 0.01 * np.arange(300))
    fine = Series(1e6 + 0.001 * np.arange(300))
    assert int(ts_aggac_60(coarse).notna().sum()) == 300 - LENGTH
    assert int(ts_aggac_60(fine).notna().sum()) == 0


# --------------------------------------------------------- parameter tests


@pytest.mark.parametrize("length", [None, 0, -5, 2, 0.5, 2.9])
def test_an_unusable_length_falls_back_to_the_default(length):
    out = ts_aggac_60(_walk(400, seed=31), length=length)
    assert out.name == f"TS_AGGAC_{LENGTH}_{MAXLAG}"


@pytest.mark.parametrize("maxlag", [None, 0, -3])
def test_an_unusable_maxlag_falls_back_to_the_default(maxlag):
    out = ts_aggac_60(_walk(400, seed=31), maxlag=maxlag)
    assert out.name == f"TS_AGGAC_{LENGTH}_{MAXLAG}"


@pytest.mark.parametrize("length,maxlag,name", [
    (3, None, "TS_AGGAC_3_1"),       # maxlag clamped to length - 2
    (3.9, None, "TS_AGGAC_3_1"),
    (12, None, "TS_AGGAC_12_10"),
    (60, 1.9, "TS_AGGAC_60_1"),
    (60, 59, "TS_AGGAC_60_58"),
    (60, 1000, "TS_AGGAC_60_58"),
    (250, None, "TS_AGGAC_250_10"),
])
def test_the_name_carries_the_effective_parameters(length, maxlag, name):
    """Naming is API: the column name must say which lags were actually
    averaged, so a clamped `maxlag` has to show up in it. This is the reason
    `maxlag` can be a parameter at all where `ts_ac1_60`'s `lag` cannot."""
    out = ts_aggac_60(_walk(400, seed=31), length=length, maxlag=maxlag)
    assert out.name == name
    assert int(out.notna().sum()) > 0


def test_the_signature_is_the_four_arguments_the_wiring_forwards():
    """`core.py`'s accessor forwards `close`, `length`, `maxlag`, `offset`;
    a fifth positional parameter here would be silently unreachable through
    `df.ta.ts_aggac_60()`."""
    assert list(inspect.signature(ts_aggac_60).parameters) == \
        ["close", "length", "maxlag", "offset", "kwargs"]


def test_too_short_an_input_returns_none_and_the_shortest_one_fires_once():
    assert ts_aggac_60(_walk(LENGTH, seed=2)) is None
    assert int(ts_aggac_60(_walk(LENGTH + 1, seed=2)).notna().sum()) == 1


def test_the_offset_shifts_the_column_and_nothing_else():
    close = _walk(400, seed=31)
    base = ts_aggac_60(close)
    pd.testing.assert_series_equal(ts_aggac_60(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_aggac_60(close, offset=-2),
                                   base.shift(-2), check_names=False)


def test_fillna_replaces_the_warm_up():
    out = ts_aggac_60(_walk(400, seed=31), fillna=0.0)
    assert out.notna().all()
    assert float(out.iloc[0]) == 0.0


# ----------------------------------------------------------- wiring tests


def test_the_five_wiring_touch_points():
    """A port that misses one computes correctly and is invisible."""
    assert "ts_aggac_60" in ta.Category["statistics"]
    assert hasattr(ta, "ts_aggac_60")
    assert hasattr(ta.AnalysisIndicators, "ts_aggac_60")
    close = _walk(400, seed=31)
    df = pd.DataFrame({"close": close})
    out = df.ta.ts_aggac_60()
    assert out.name == f"TS_AGGAC_{LENGTH}_{MAXLAG}"
    pd.testing.assert_series_equal(out, ts_aggac_60(close))


def test_the_accessor_forwards_maxlag_under_the_right_name():
    """The `supertrend` failure mode: a keyword forwarded under the wrong name
    is invisible to `hasattr`."""
    df = pd.DataFrame({"close": _walk(400, seed=31)})
    assert df.ta.ts_aggac_60(maxlag=3).name == "TS_AGGAC_60_3"
    assert df.ta.ts_aggac_60(length=30, maxlag=4).name == "TS_AGGAC_30_4"


def test_the_column_is_tagged_scale_free_in_the_dictionary():
    doc = open(os.path.join(_HERE, "docs", "IndicatorDictionary.md"),
               encoding="utf8").read()
    assert "`TS_AGGAC_60_10` SF" in doc


# ------------------------------------------------------------ Gate E owed


def test_gate_e_is_owed_and_has_no_ledger_row_yet():
    """The launcher runs Gate E after this session; a later receipt session
    records the row and writes the numbers into docs/TsAggac60Measured.md.
    This test fails the moment the row lands, which is that session's cue to
    come back here and replace it with the measured verdict."""
    ledger = open(os.path.join(_HERE, "docs", "gate_e_ledger.csv"),
                  encoding="utf8").read()
    assert "ts_aggac_60" not in ledger
    doc = open(os.path.join(_HERE, "docs", "TsAggac60Measured.md"),
               encoding="utf8").read()
    assert "Gate E: pending, run by issue-solver after this session" in doc
