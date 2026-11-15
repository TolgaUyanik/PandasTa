# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsAggac60Measured.md for `ts_aggac_60`
(PandasTa issue #96, TS-AGGAC-60).

Run from the repository root:

    python docs/measure_ts_aggac_60.py            # every section
    python docs/measure_ts_aggac_60.py a          # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import math
import time
import tracemalloc
import types
from fractions import Fraction

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_aggac_60 import ts_aggac_60

LENGTH, MAXLAG = 60, 10
REAL = importlib.import_module("pandas_ta.statistics.ts_aggac_60")


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------------ frames


def walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.5):
    """A path whose LOG returns are an AR(1): `rlog[t] = phi*rlog[t-1] + eps`,
    whose population lag-`k` autocorrelation is exactly `phi**k`. The column
    reads SIMPLE returns, which is a different (monotone) transform of it."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def seasonal(n=1500, seed=19, period=10, amp=0.01):
    """Returns that repeat exactly with `period`: every lag that is a multiple
    of the period is positively correlated and the ones in between are
    negative."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0, amp, period)
    r = np.tile(base, n // period + 1)[:n]
    return Series(100.0 * np.cumprod(1.0 + r))


def alternating(n=1500, amp=0.01):
    """Returns alternate +amp / -amp exactly, so every window of an even
    length holds equal counts of the two: the lag-`k` autocorrelation is
    exactly `(-1)**k` and their mean over an EVEN `maxlag` is exactly 0."""
    r = np.where(np.arange(n) % 2 == 0, amp, -amp)
    return Series(100.0 * np.cumprod(1.0 + r))


def geometric_ladder(n=300, step=0.01):
    return Series(100.0 * np.exp(np.arange(n) * step))


def two_scale(n_hi=200, n_lo=200, sigma_hi=0.3, sigma_lo=1e-9, seed=5):
    """Volatile, then frozen. `ts_cid_ce_20` found this -- a volatility
    regime COLLAPSE, not a spike -- to be the shape pandas' online
    accumulators actually lose, so the trust test is priced on it too."""
    rng = np.random.default_rng(seed)
    r = np.concatenate([rng.normal(0.0, sigma_hi, n_hi),
                        rng.normal(0.0, sigma_lo, n_lo)])
    return Series(100.0 * np.exp(np.cumsum(r)))


def mean_dominated(n=400, seed=3, mu=0.01, ratio=1e5):
    """Returns with a large MEAN and a tiny DISPERSION: `|mean| / sd` is
    `ratio`. This is the shape that breaks the plain raw-sum spelling of the
    numerator, and it is still well above the variance floor."""
    rng = np.random.default_rng(seed)
    r = mu + rng.normal(0.0, abs(mu) / ratio, n)
    return Series(100.0 * np.cumprod(1.0 + r))


def _planted(frame, values):
    holed = frame.copy()
    for idx, v in values.items():
        holed.iloc[idx] = v
    return holed


def compare(name, a, b):
    """Max |difference|, bit-equal count and Spearman over the shared
    non-NaN bars, plus whether the NaN masks agree."""
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    rho = float(x.corr(y, method="spearman")) if len(x) > 2 else float("nan")
    print(f"  {name}: n={int(m.sum())} max|diff|={float(diff.max()):.6e} "
          f"bit-equal={bit}/{int(m.sum())} spearman={rho:.6f} "
          f"nan-masks-agree={masks_agree}")
    return float(diff.max()), bit, rho, masks_agree


# ------------------------------------------------- the source, three ways


def tsfresh_autocorrelation(x, lag):
    """tsfresh `feature_calculators.autocorrelation`, retyped from its
    published definition:

        y1 = x[:len(x)-lag]; y2 = x[lag:]
        x_mean = np.mean(x)
        sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
        v = np.var(x)
        return np.NaN if np.isclose(v, 0) else \
            sum_product / ((len(x) - lag) * v)

    ⚠ tsfresh is NOT installed in this worktree and web access is
    unavailable, so this is the formula the issue states plus the published
    definition of that function, not a read of tsfresh's own code."""
    x = np.asarray(x, dtype=float)
    if len(x) < lag:
        return np.nan
    y1, y2 = x[:len(x) - lag], x[lag:]
    x_mean = np.mean(x)
    sum_product = np.sum((y1 - x_mean) * (y2 - x_mean))
    v = np.var(x)
    if np.isclose(v, 0):
        return np.nan
    return sum_product / ((len(x) - lag) * v)


def statsmodels_acf_adjusted(x, nlags):
    """`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False,
    nlags=nlags)[1:]`, retyped from its published definition, because
    `agg_autocorrelation` -- not `autocorrelation` -- is what the issue names
    and THAT function goes through statsmodels:

        acovf(x, adjusted=True)[k] = sum_{t=k}^{n-1} (x[t]-m)*(x[t-k]-m)
                                     / (n - k)
        acf[k] = acovf[k] / acovf[0]

    `acovf[0]` divides by `n - 0 = n`, so it IS the population variance, and
    the quotient is `sum / ((n-k) * var)` -- the same expression
    `feature_calculators.autocorrelation` spells directly. Gate A3 measures
    the two against each other rather than resting on this paragraph."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    xo = x - x.mean()
    acov = np.correlate(xo, xo, "full")[n - 1:] / np.arange(n, 0, -1)
    return (acov / acov[0])[1:nlags + 1]


def tsfresh_agg_autocorrelation(x, maxlag=MAXLAG, f_agg="mean",
                                guard="tsfresh"):
    """tsfresh `feature_calculators.agg_autocorrelation`, retyped from its
    published definition:

        var = np.var(x); n = len(x)
        if np.abs(var) < 10**-10 or n == 1:
            a = [0] * len(x)
        else:
            a = acf(x, adjusted=True, fft=n > 1250, nlags=max_maxlag)[1:]
        return getattr(np, f_agg)(a[:maxlag])

    `guard` switches that `var < 1e-10` branch: "tsfresh" fabricates the
    zeros it specifies, "nan" reports nothing, "none" divides anyway."""
    x = np.asarray(x, dtype=float)
    var = np.var(x)
    if abs(var) < 10 ** -10 or len(x) == 1:
        if guard == "tsfresh":
            return float(getattr(np, f_agg)(np.zeros(len(x))[:maxlag]))
        if guard == "nan":
            return np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        a = statsmodels_acf_adjusted(x, maxlag)
    return float(getattr(np, f_agg)(a[:maxlag]))


def source_windowed(close, length=LENGTH, maxlag=MAXLAG, guard="floor",
                    log_returns=False, closes_not_returns=False, ddof=0,
                    biased=False, lags=None, path="autocorrelation"):
    """The source formula applied window by window with
    `sliding_window_view`: no pandas rolling anywhere, so it shares no window
    machinery with the module. The keywords are the rejected readings of
    section A6; `path` picks which retype of the source does the arithmetic."""
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
    ks = list(range(1, maxlag + 1)) if lags is None else list(lags)
    # A planted giant return overflows this spelling, which is one reason it
    # is the oracle and not the module.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        v = W.var(axis=1, ddof=ddof)
        if path == "acf":
            vals = np.array([float(np.mean(statsmodels_acf_adjusted(w, maxlag)))
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
        vals = np.where(v > REAL.VAR_FLOOR, vals, np.nan)
    elif guard == "isclose":             # tsfresh `autocorrelation`'s own
        vals = np.where(np.isclose(v, 0.0), np.nan, vals)
    elif guard == "tsfresh":             # tsfresh `agg_autocorrelation`'s own
        vals = np.where(np.abs(v) < 1e-10, 0.0, vals)
    elif guard != "none":
        raise ValueError(guard)
    out[width:] = vals
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH, maxlag=MAXLAG):
    """Plain-Python scalars, `math.fsum` for every sum: no numpy, no pandas
    rolling, and the summation is exact to one rounding."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        x = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        m = math.fsum(x) / length
        v = math.fsum((u - m) ** 2 for u in x) / length
        if v > REAL.VAR_FLOOR:
            acs = []
            for k in range(1, maxlag + 1):
                num = math.fsum((x[i] - m) * (x[i - k] - m)
                                for i in range(k, length))
                acs.append(num / ((length - k) * v))
            out[t] = math.fsum(acs) / maxlag
    return Series(out, index=close.index)


def exact_loop(close, length=LENGTH, maxlag=MAXLAG, bars=None):
    """The EXACT value, in `fractions.Fraction`: every close is a rational,
    so every return and the whole statistic is one. No float arithmetic
    anywhere until the final conversion, which is the only rounding."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    first = length if bars is None else max(length, len(c) - bars)
    for t in range(first, len(c)):
        x = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        m = sum(x) / length
        v = sum((u - m) ** 2 for u in x) / length
        if v != 0:
            total = 0
            for k in range(1, maxlag + 1):
                num = sum((x[i] - m) * (x[i - k] - m) for i in range(k, length))
                total += num / ((length - k) * v)
            out[t] = float(total / maxlag)
    return Series(out, index=close.index)


def exact_variance(close, length=LENGTH, bars=None):
    """The window's EXACT population variance as a `Fraction`, per bar, or
    None where the window is not complete. Used to isolate whose rounding the
    mean-dominated error belongs to."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [None] * len(c)
    first = length if bars is None else max(length, len(c) - bars)
    for t in range(first, len(c)):
        x = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        m = sum(x) / length
        out[t] = sum((u - m) ** 2 for u in x) / length
    return out


def plain_expansion(close, length=LENGTH, maxlag=MAXLAG):
    """The spelling the module REJECTS: each lag's numerator as the raw sum
    `sum x[i]*x[i-k] - m*(sum of the window's x except the k oldest)
                      - m*(sum except the k newest) + (length-k)*m**2`,
    which is algebraically identical and cancels when a window's mean dwarfs
    its dispersion."""
    px = close.astype(float)
    r = px / px.shift(1) - 1.0
    rolling = r.rolling(length, min_periods=length)
    mean = rolling.mean()
    var = rolling.var(ddof=0)
    total = 0.0
    tail = head_ = 0.0
    for k in range(1, maxlag + 1):
        products = (r * r.shift(k)).rolling(length - k,
                                            min_periods=length - k).sum()
        tail = tail + r.shift(k - 1)
        head_ = head_ + r.shift(length - k)
        late = length * mean - head_     # the window minus its k oldest
        early = length * mean - tail     # the window minus its k newest
        num = products - mean * (late + early) + (length - k) * mean * mean
        total = total + num / ((length - k) * var.where(var > REAL.VAR_FLOOR))
    return total / maxlag


def screen_candidate():
    """`REG["ts_aggac_60"]["fn"]` out of the screen's own registry, when this
    worktree has `docs/issues/` (gitignored, so a clone does not)."""
    import importlib.util
    import os
    import sys

    path = os.path.join("docs", "issues", "screen", "ind_screen.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_aggac_60"]["fn"]


def prototype(close, length=LENGTH, maxlag=MAXLAG):
    """`docs/issues/screen/ind_screen.py` candidate `ts_aggac_60`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            r = ret(c)
            return sum(corr(r, delay(r, k), 60) for k in range(1, 11)) / 10

    with `ret(c) = c / c.shift(1) - 1`, `delay(x, n) = x.shift(n)` and
    `corr(x, y, n) = (x.rolling(n).corr(y)).replace([inf, -inf], nan)`. Each
    term is a PEARSON correlation of two 60-pair slices -- two means, two
    standard deviations, `60 + k` returns of history -- and not the source
    formula."""
    r = close / close.shift(1) - 1
    total = 0.0
    for k in range(1, maxlag + 1):
        total = total + r.rolling(length).corr(r.shift(k)).replace(
            [np.inf, -np.inf], np.nan)
    return total / maxlag


def pearson_same_window(close, length=LENGTH, maxlag=MAXLAG):
    """`pandas.Series.autocorr` applied to the module's OWN window of
    `length` returns, averaged over the same lags: the same history, the
    Pearson normalisation."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    if len(r) < length + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], length)
    vals = np.array([float(np.mean([Series(w).autocorr(k)
                                    for k in range(1, maxlag + 1)]))
                     for w in W])
    out[length:] = vals
    return Series(out, index=close.index)


# ----------------------------------------------------------------- Gate A


def gate_a():
    head("Gate A1. windows with a closed form")
    # An alternating window: deviations are +-d, every one of the length-k
    # lag-k products is (-1)**k * d**2 and the population variance is d**2,
    # so the lag-k autocorrelation is exactly (-1)**k and the mean over an
    # EVEN maxlag is exactly 0.
    for length in (4, 10, 60):
        for maxlag in (1, 2, 9, 10):
            if maxlag > length - 2:
                continue
            col = ts_aggac_60(alternating(300), length=length,
                              maxlag=maxlag).dropna()
            target = 0.0 if maxlag % 2 == 0 else -1.0 / maxlag
            print(f"  alternating, length={length} maxlag={maxlag}: "
                  f"max|module - {target:+.6f}| = "
                  f"{float((col - target).abs().max()):.3e} "
                  f"bit-equal {int((col == target).sum())}/{len(col)}")
    exact = Series([1.0, 2.0] * 40)
    for maxlag in (2, 10):
        col = ts_aggac_60(exact, length=60, maxlag=maxlag).dropna()
        print(f"  close=[1,2,1,2,...] length=60 maxlag={maxlag}: "
              f"values {sorted(set(col.to_numpy().tolist()))} "
              f"(bit-exact 0: {int((col == 0.0).sum())}/{len(col)})")

    head("Gate A2. the two spellings of the source agree")
    # `agg_autocorrelation` goes through statsmodels' adjusted acf;
    # `autocorrelation` spells the quotient directly. They must be the same
    # number, and this is where that is measured rather than asserted.
    rng = np.random.default_rng(5)
    worst = 0.0
    for trial in range(200):
        x = rng.normal(0.0, 1.0, LENGTH)
        a = float(np.mean([tsfresh_autocorrelation(x, k)
                           for k in range(1, MAXLAG + 1)]))
        b = tsfresh_agg_autocorrelation(x)
        worst = max(worst, abs(a - b))
    print(f"  200 random 60-point windows: max |mean of autocorrelation(k) - "
          f"agg_autocorrelation| = {worst:.3e}")
    try:
        from statsmodels.tsa.stattools import acf as sm_acf
        x = rng.normal(0.0, 1.0, LENGTH)
        mine = statsmodels_acf_adjusted(x, MAXLAG)
        theirs = sm_acf(x, adjusted=True, fft=False, nlags=MAXLAG)[1:]
        print(f"  statsmodels IS installed: max |retyped acf - "
              f"statsmodels acf| = {float(np.abs(mine - theirs).max()):.3e}")
    except ImportError:
        print("  statsmodels is NOT installed here, so the adjusted acf is "
              "the retype above and not a read of its code")

    head("Gate A3. against the source formula, window by window")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.5)", ar1()), ("seasonal(10)", seasonal())):
        compare(f"{name} vs autocorrelation(k) averaged",
                ts_aggac_60(frame), source_windowed(frame))
        compare(f"{name} vs the adjusted-acf path",
                ts_aggac_60(frame), source_windowed(frame, path="acf"))
    compare("walk vs the math.fsum scalar loop",
            ts_aggac_60(walk(400, seed=21)), scalar_loop(walk(400, seed=21)))

    head("Gate A4. accuracy against an EXACT rational oracle")
    for name, frame in (("walk", walk(300, seed=11)),
                        ("tick-rounded", tick_rounded(300, seed=55)),
                        ("mean-dominated |mean|/sd=1e5", mean_dominated(300))):
        exact = exact_loop(frame)
        m = exact.notna()
        for label, other in (("module", ts_aggac_60(frame)),
                             ("math.fsum loop", scalar_loop(frame)),
                             ("window-by-window oracle", source_windowed(frame)),
                             ("plain raw-sum expansion", plain_expansion(frame))):
            d = float((other[m] - exact[m]).abs().max())
            print(f"  {name}: {label} is {d:.3e} from the exact value")

    head("Gate A4b. whose error is the mean-dominated 2e-10?")
    # The module's NUMERATOR divided by the EXACT rational variance instead of
    # pandas' accumulated one, the division done in `Fraction` so the only
    # float left in it is the numerator. If the residue collapses, the error
    # was the DIVISOR's; if it does not, it is the numerator's -- which itself
    # holds `length * var`, so pandas' accumulator can still be the cause,
    # just not through the division.
    for name, frame in (("walk", walk(300, seed=11)),
                        ("mean-dominated |mean|/sd=1e5", mean_dominated(300))):
        exact = exact_loop(frame)
        vexact = exact_variance(frame)
        col = ts_aggac_60(frame)
        num = module_variant(frame, numerator=True)
        rows = [t for t in range(len(frame))
                if not np.isnan(exact.iloc[t]) and vexact[t]]
        shipped = max(abs(col.iloc[t] - exact.iloc[t]) for t in rows)
        exact_divisor = max(abs(float(Fraction(float(num.iloc[t]))
                                      / (MAXLAG * vexact[t])) - exact.iloc[t])
                            for t in rows)
        print(f"  {name}: the shipped column is {shipped:.3e} out; its "
              f"numerator over the EXACT variance is {exact_divisor:.3e} out "
              f"({len(rows)} bars)")

    head("Gate A5. the two degeneracy guards")
    for name, frame in (("flat (every close 100)", Series([100.0] * 300)),
                        ("1%-a-bar geometric ladder", geometric_ladder()),
                        ("walk sigma=1e-6", walk(300, sigma=1e-6)),
                        ("walk sigma=1e-9", walk(300, sigma=1e-9))):
        this = ts_aggac_60(frame)
        isclose = source_windowed(frame, guard="isclose")
        tsf = source_windowed(frame, guard="tsfresh")
        none = source_windowed(frame, guard="none")
        print(f"  {name}: this module fires {int(this.notna().sum())}/300 "
              f"(max |value| {float(this.abs().max()):.4f}), tsfresh's "
              f"`autocorrelation` isclose guard "
              f"{int(isclose.notna().sum())}/300, tsfresh's "
              f"`agg_autocorrelation` var<1e-10 branch fabricates "
              f"{int((tsf == 0.0).sum())} exact zeros, unguarded "
              f"{int(none.notna().sum())}/300 (max |value| "
              f"{float(none.abs().max()):.4f})")
    print("  the fabricated value is 0.0, which is an ORDINARY reading of "
          "this column -- see the iid distribution in the `meaning` section")

    head("Gate A6. the readings the wording leaves open")
    close = walk()
    base = ts_aggac_60(close)
    compare("log returns instead of simple", base,
            source_windowed(close, log_returns=True))
    compare("60 CLOSES (59 returns) instead of 60 returns", base,
            source_windowed(close, closes_not_returns=True))
    compare("length*v divisor (the biased estimator)", base,
            source_windowed(close, biased=True))
    compare("SAMPLE variance (ddof=1) in the divisor", base,
            source_windowed(close, ddof=1))
    compare("lags 0..10 instead of 1..10", base,
            source_windowed(close, lags=range(0, MAXLAG + 1)))
    compare("Pearson per lag on the SAME window (Series.autocorr)", base,
            pearson_same_window(close))
    compare("the screen prototype (Pearson, 60 pairs per lag)", base,
            prototype(close))

    head("Gate A7. the screen prototype, read from the owner's registry")
    fn = screen_candidate()
    close = walk()
    mine = prototype(close)
    if fn is None:
        print("  docs/issues/ is absent in this tree: retype only")
    else:
        theirs = fn(close, close, close, close, close)
        compare("retype vs the registry's own function", mine, theirs)
    print(f"  first fired bar: module {int(base.notna().idxmax())}, "
          f"prototype {int(mine.notna().idxmax())}")

    head("Gate A8. the reachable bounds")
    for n, L in ((12, 10), (20, 10), (60, 10), (60, 1), (60, 5)):
        lo, hi = _bounds(n, L)
        print(f"  length={n} maxlag={L}: constrained Rayleigh bounds, "
              f"tsfresh scaled: min={lo:.12f} max={hi:.12f} "
              f"(Cauchy-Schwarz ceiling {_cs_ceiling(n, L):.6f})")
        for label, target in (("max", hi), ("min", lo)):
            y = _extreme_window(n, target, maxlag=L)
            closes = Series(np.concatenate([[100.0],
                                            100.0 * np.cumprod(1.0 + y)]))
            got = float(ts_aggac_60(closes, length=n, maxlag=L).iloc[-1])
            print(f"    {label}: module={got!r} target={target!r} "
                  f"|difference|={abs(got - target):.3e}")

    head("Gate A9. against this fork's own serial-dependence columns")
    # Not "every module with a .corr( against a shift(" -- that grep is the
    # wrong net. These are the `Category` modules whose value is a function of
    # the SAME series at a fixed offset, enumerated by hand from
    # `pandas_ta/__init__.py`: the three tsfresh return-window ports, the
    # Lean momersion sign product, the two close-DIFFERENCE lag-1 statistics
    # and the one GTJA alpha that correlates a price against its own lag.
    for label, fn in list(_siblings().items()):
        for name, frame in (("walk", walk()),
                            ("tick-rounded", tick_rounded()),
                            ("ar1(+0.5)", ar1()),
                            ("seasonal(10)", seasonal())):
            a, b = ts_aggac_60(frame), fn(frame)
            m = a.notna() & b.notna()
            print(f"  {label} / {name}: spearman={float(a[m].corr(b[m], method='spearman')):+.6f} "
                  f"pearson={float(a[m].corr(b[m])):+.6f} n={int(m.sum())}")
    from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
    compare("maxlag=1 against ts_ac1_60 at the same length",
            ts_aggac_60(walk(), maxlag=1), ts_ac1_60(walk()))


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
    from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
    from pandas_ta.statistics.ts_c3_20 import ts_c3_20
    from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20
    from pandas_ta.volatility.roll_spread import roll_spread
    return {
        "ts_ac1_60 TS_AC1_60 (this column's lag-1 term, same window)":
            ts_ac1_60,
        "ts_cid_ce_20 TS_CID_CE_20 (sum of squared successive return "
        "differences; a monotone restatement of the lag-1 autocorrelation "
        "AT ITS OWN 20-return window)": ts_cid_ce_20,
        "lean_momersion_20 LEAN_MOMERSION_20 (share of return pairs with "
        "the same SIGN over 20 bars -- lag-1 serial dependence, no "
        "correlation call)": lean_momersion_20,
        "ts_c3_20 TS_C3_20_1 (a lag-1 TRIPLE product over 20 returns)":
            ts_c3_20,
        "g191_026 (typical price against its own 5-bar lag, 230-bar "
        "correlation)": lambda c: g191_026(c, c, c),
        "a101_048 (250-bar lag-1 autocorrelation of close DIFFERENCES)":
            a101_048,
        "roll_spread ROLL_20 (20-bar lag-1 autoCOVARIANCE of close "
        "differences, kept only where negative)": roll_spread,
    }


def _lag_form(n, maxlag):
    """The symmetric matrix `M` with `x' M x = sum_k N_k / (n - k)`, where
    `N_k` is the lag-`k` product sum: half on each of the `k`-th
    off-diagonals, weighted by `1 / (n - k)` and averaged over the lags."""
    t = np.zeros((n, n))
    for k in range(1, maxlag + 1):
        i = np.arange(n - k)
        t[i, i + k] += 0.5 / (n - k)
        t[i + k, i] += 0.5 / (n - k)
    return t / maxlag


def _ortho_basis(n):
    """An orthonormal basis of the subspace orthogonal to the all-ones
    vector: the demeaned windows are exactly that subspace."""
    a = np.eye(n) - np.ones((n, n)) / n
    q, _ = np.linalg.qr(a)
    # Keep the n-1 columns that stay inside the subspace.
    keep = [c for c in range(n)
            if abs(float(np.ones(n) @ q[:, c])) < 1e-10]
    return q[:, keep[:n - 1]]


def _bounds(n, maxlag=MAXLAG):
    """The reachable minimum and maximum of the column at `length = n`: the
    column is `n` times a Rayleigh quotient of `_lag_form` restricted to the
    demeaned subspace, so its extremes are that form's extreme eigenvalues."""
    q = _ortho_basis(n)
    w = np.linalg.eigvalsh(q.T @ _lag_form(n, maxlag) @ q)
    return float(w.min() * n), float(w.max() * n)


def _cs_ceiling(n, maxlag=MAXLAG):
    """Cauchy-Schwarz on each lag separately: `|N_k| <= n*v`, so the column is
    inside `(n / maxlag) * sum_k 1/(n-k)`. Looser than `_bounds`, because no
    single window maximises every lag at once."""
    return (n / maxlag) * sum(1.0 / (n - k) for k in range(1, maxlag + 1))


def _extreme_window(n, target, amp=0.01, maxlag=MAXLAG):
    """The return window attaining `target`: the matching eigenvector, scaled
    to a plausible return amplitude."""
    q = _ortho_basis(n)
    w, vecs = np.linalg.eigh(q.T @ _lag_form(n, maxlag) @ q)
    idx = int(np.argmax(w)) if target > 0 else int(np.argmin(w))
    y = q @ vecs[:, idx]
    return amp * y / float(np.abs(y).max())


# ----------------------------------------------------------------- Gate B


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
    # The two extrema feed only the trust test, which costs 0 bars on a clean
    # frame -- so a look-ahead confined to them would move nothing on the
    # three frames the sweep uses. That is exactly why it needs its own
    # mutant, and why the sweep below also runs it on a frame where the trust
    # test FIRES.
    "centered_span": ("    span = rolling.max() - rolling.min()",
                      "    _c = r.rolling(length, min_periods=length, "
                      "center=True)\n    span = _c.max() - _c.min()"),
}


def spiked(n=400, seed=21, at=200, factor=1e8):
    """A 400-bar walk with one planted return of about 1e+8 at `at`: the
    frame on which the accumulator trust test actually fires, and therefore
    the only one on which a look-ahead inside `span` can move a value."""
    frame = walk(n, seed=seed)
    frame.iloc[at] = float(frame.iloc[at - 1]) * factor
    return frame


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_aggac_60_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close, other, detail=False):
    """Replace every bar from J onward with a different path; count the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits, quiet = 0, []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        moved = not (a.isna() == b.isna()).all()
        if not moved:
            mask = a.notna()
            moved = bool((a[mask] != b[mask]).any())
        if moved:
            hits += 1
        else:
            quiet.append((j, int(a.notna().sum()), int(b.notna().sum()),
                          bool(np.isnan(float(a.iloc[-1]))),
                          bool(np.isnan(float(b.iloc[-1])))))
    if detail:
        return hits, quiet
    return hits


def gate_b():
    head("Gate B. the real module never reads the future")
    frames = {"walk": (walk(), walk(seed=97)),
              "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
              "ar1(+0.5)": (ar1(), ar1(seed=8))}
    for name, (close, other) in frames.items():
        print(f"  {name}: real module leaks at "
              f"{leaks(ts_aggac_60, close, other)}/{len(list(OFFSETS))} "
              f"offsets")

    head("Gate B. every mutant, every frame, at the default length")
    for label, mutant in MUTANTS.items():
        mod = load_mutant(*mutant)
        for name, (close, other) in frames.items():
            live = not mod.ts_aggac_60(close).equals(ts_aggac_60(close))
            print(f"  {label} / {name}: caught "
                  f"{leaks(mod.ts_aggac_60, close, other)}/"
                  f"{len(list(OFFSETS))}, mutation live={live}")

    head("Gate B. the span mutant on a frame where the trust test FIRES")
    # OFFSETS runs to 1500, so the sweep needs a frame that long; the spike is
    # planted at 200 and the trust test empties the 139 bars after it leaves
    # every window.
    close, other = spiked(1500, at=200), spiked(1500, seed=97, at=200)
    print(f"  real module on the spiked frame: "
          f"{leaks(ts_aggac_60, close, other)}/{len(list(OFFSETS))}")
    mod = load_mutant(*MUTANTS["centered_span"])
    print(f"  centered_span: caught {leaks(mod.ts_aggac_60, close, other)}/"
          f"{len(list(OFFSETS))}, mutation live="
          f"{not mod.ts_aggac_60(close).equals(ts_aggac_60(close))}")

    head("Gate B. the length-dependent mutants at non-default lengths")
    close, other = frames["walk"]
    for label in ("write_shift", "forward_head", "centered_var",
                  "centered_gap"):
        mod = load_mutant(*MUTANTS[label])
        for length in (12, 60, 250):
            def real(c, n=length):
                return ts_aggac_60(c, length=n)

            def mutated(c, n=length):
                return mod.ts_aggac_60(c, length=n)

            real_hits = leaks(real, close, other)
            hits, quiet = leaks(mutated, close, other, detail=True)
            print(f"  {label} at length={length}: real {real_hits}/"
                  f"{len(list(OFFSETS))}, mutant caught {hits}/"
                  f"{len(list(OFFSETS))}")
            if quiet:
                last_nan = all(x and y for *_, x, y in quiet)
                print(f"      {len(quiet)} quiet offsets, fired bars before J "
                      f"{[a for _, a, _, _, _ in quiet][:4]}..., bar J-1 NaN "
                      f"in both at every one of them: {last_nan}")


# --------------------------------------------------------------- Gate C/D


def gate_c_d():
    head("Gate C. reachability on synthetic frames")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.5)", ar1()), ("ar1(-0.5)", ar1(phi=-0.5)),
                        ("seasonal(10)", seasonal())):
        out = ts_aggac_60(frame)
        fired = out.dropna()
        print(f"  {name}: fires {len(fired)}/{len(frame)} "
              f"distinct={int(fired.nunique())} "
              f"non-zero={int((fired != 0).sum())} "
              f"min={float(fired.min()):.6f} max={float(fired.max()):.6f}")
    print("  real-data counts are owed with Gate E (the launcher's run)")

    head("Gate D. scale")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.5)", ar1())):
        for k in (8.0, 64.0):
            base, scaled = ts_aggac_60(frame), ts_aggac_60(frame * k)
            m = base.notna() & scaled.notna()
            print(f"  {name} x{k:g}: bit-equal "
                  f"{int((base[m] == scaled[m]).sum())}"
                  f"/{int(m.sum())} masks-agree="
                  f"{bool((base.isna() == scaled.isna()).all())}")
        for k in (10.0, 3.7):
            base, scaled = ts_aggac_60(frame), ts_aggac_60(frame * k)
            m = base.notna() & scaled.notna()
            print(f"  {name} x{k:g}: max|diff|="
                  f"{float((base[m] - scaled[m]).abs().max()):.3e} "
                  f"spearman="
                  f"{float(base[m].corr(scaled[m], method='spearman')):.6f} "
                  f"masks-agree={bool((base.isna() == scaled.isna()).all())}")
    close = walk()
    for length in (12, 20, 250):
        base = ts_aggac_60(close, length=length)
        scaled = ts_aggac_60(close * 8.0, length=length)
        m = base.notna() & scaled.notna()
        print(f"  walk x8 at length={length}: bit-equal "
              f"{int((base[m] == scaled[m]).sum())}/{int(m.sum())}")

    head("Gate D. invariance to an AFFINE map of the RETURNS")
    close = walk()
    base = ts_aggac_60(close)
    for label, other in (
            ("+0.004 of log drift a bar",
             Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))),
            ("returns x2 (closes rebuilt)", _rescaled_returns(close, 2.0)),
            ("returns x0.5 (closes rebuilt)", _rescaled_returns(close, 0.5))):
        compare(label, base, ts_aggac_60(other))

    head("Gate D. why the return is a RATIO and not a difference of logs")
    close = walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    print(f"  returns bit-equal at x8: ratio "
          f"{int((ratio[m] == ratio8[m]).sum())}"
          f"/{int(m.sum())}, log difference "
          f"{int((plain[m] == plain8[m]).sum())}/{int(m.sum())}")


def _rescaled_returns(close, k):
    r = (close / close.shift(1) - 1.0).to_numpy()[1:]
    return Series(np.concatenate(
        [[float(close.iloc[0])],
         float(close.iloc[0]) * np.cumprod(1.0 + k * r)]))


# ------------------------------------------------- what the column means


def meaning():
    head("What the column means")
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(
        rng.normal(0.0, 0.01, (2000, LENGTH + 1)), axis=1))
    est = np.array([float(ts_aggac_60(Series(p)).iloc[-1]) for p in paths])
    print(f"  iid returns, {len(est)} independent 60-return windows: "
          f"median={np.median(est):.4f} mean={est.mean():.4f} "
          f"sd={est.std(ddof=1):.4f} p10={np.percentile(est, 10):.4f} "
          f"p90={np.percentile(est, 90):.4f} "
          f"positive={100 * (est > 0).mean():.2f}% "
          f"finite={int(np.isfinite(est).sum())}/{len(est)}")
    # The lag-1 column on the SAME 2,000 paths, so the comparison in the
    # docstring is a measurement and not a recollection of its own docstring.
    from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
    one = np.array([float(ts_ac1_60(Series(p)).iloc[-1]) for p in paths])
    print(f"  ts_ac1_60 on the SAME paths: median={np.median(one):.4f} "
          f"mean={one.mean():.4f} sd={one.std(ddof=1):.4f} "
          f"positive={100 * (one > 0).mean():.2f}% -- so this column's sd is "
          f"{est.std(ddof=1) / one.std(ddof=1):.3f} of it and its median "
          f"{np.median(est) / np.median(one):.2f} times it")
    print(f"  the small-sample bias of this normalisation is about "
          f"-1/(n-1) = {-1 / (LENGTH - 1):.4f} per lag and the spread of ONE "
          f"lag about 1/sqrt(n) = {1 / math.sqrt(LENGTH):.4f} (arithmetic); "
          f"averaging {MAXLAG} overlapping lags shrinks the spread but not "
          f"by sqrt({MAXLAG}), because they are not independent")
    for phi in (0.5, 0.25, 0.0, -0.25, -0.5):
        col = ts_aggac_60(ar1(phi=phi)).dropna()
        theory = sum(phi ** k for k in range(1, MAXLAG + 1)) / MAXLAG
        print(f"  AR(1) log returns phi={phi:+.2f}: median={col.median():.4f} "
              f"p10={np.percentile(col, 10):.4f} "
              f"p90={np.percentile(col, 90):.4f} "
              f"(population mean of phi**k over the 10 lags: {theory:+.4f})")
    print("  the small-sample bias at other lengths, on IID windows -- the "
          "high lags are estimated from few pairs, so the bias grows as "
          "`length` approaches `2*maxlag`:")
    for n in (12, 20, 30, 60, 200):
        paths = 100.0 * np.exp(np.cumsum(
            rng.normal(0.0, 0.01, (500, n + 1)), axis=1))
        e = np.array([float(ts_aggac_60(Series(p), length=n).iloc[-1])
                      for p in paths])
        print(f"    iid, length={n}: median={np.median(e):+.4f} "
              f"sd={e.std(ddof=1):.4f} (one lag's bias -1/(n-1) = "
              f"{-1 / (n - 1):+.4f})")
    for n in (20, 60, 200, 1000):
        col = ts_aggac_60(ar1(n=20000, phi=0.5), length=n).dropna()
        print(f"  AR(1) phi=+0.50 on 20,000 bars at length={n}: "
              f"median={col.median():.4f} (population mean of phi**k over the "
              f"10 lags: {sum(0.5 ** k for k in range(1, MAXLAG + 1)) / MAXLAG:+.4f})")
    print("  a seasonal path. A window that repeats with period `p` has "
          "lag-`k` autocorrelations summing to 0 over any whole cycle of "
          "rotations, so a `p` that DIVIDES maxlag averages to ~0 and the "
          "column cannot see the seasonality at all:")
    for period in (2, 3, 5, 7, 10):
        col = ts_aggac_60(seasonal(1500, period=period)).dropna()
        one = ts_aggac_60(seasonal(1500, period=period), maxlag=1).dropna()
        print(f"    period={period} ({'divides' if MAXLAG % period == 0 else 'does NOT divide'}"
              f" maxlag={MAXLAG}): maxlag=10 median={col.median():+.6f}, "
              f"maxlag=1 median={one.median():+.4f}")
    close = walk()
    base = ts_aggac_60(close)
    r = close / close.shift(1) - 1.0
    for label, other in (
            ("window sd", r.rolling(LENGTH, min_periods=LENGTH).std()),
            ("mean return", r.rolling(LENGTH, min_periods=LENGTH).mean()),
            ("abs mean return",
             r.rolling(LENGTH, min_periods=LENGTH).mean().abs())):
        m = base.notna() & other.notna()
        print(f"  spearman against the same window's {label}: "
              f"{float(base[m].corr(other[m], method='spearman')):.4f}")
    for label, fn in _siblings().items():
        other = fn(close)
        m = base.notna() & other.notna()
        print(f"  spearman against {label}: n={int(m.sum())} "
              f"{float(base[m].corr(other[m], method='spearman')):+.4f}")
    print("  persistence of one window: ")
    col = ts_aggac_60(walk(1500)).dropna()
    for lag in (1, 30, 60):
        print(f"    autocorrelation of the COLUMN at lag {lag}: "
              f"{float(col.autocorr(lag)):.4f}")


# ---------------------------------------------------------------- guards


def guards():
    head("Guards. the overflow bound, and what it keeps local")
    print(f"  per-return ceiling: sqrt(max/(8*length)) = "
          f"{math.sqrt(np.finfo(float).max / (8 * LENGTH)):.3e}")
    base_frame = walk(400, seed=21)
    base = ts_aggac_60(base_frame)
    for label, planted in (
            ("one close of 1e-300 at bar 200: the NEXT return is about "
             "1e+302, so ONE return is over the ceiling", {200: 1e-300}),
            ("closes of 1e-200 at bars 200 and 230: TWO returns over it, 30 "
             "bars apart, so two windows' worth of damage overlaps",
             {200: 1e-200, 230: 1e-200}),
    ):
        holed = base_frame.copy()
        for idx, v in planted.items():
            holed.iloc[idx] = v
        guarded = ts_aggac_60(holed)
        unguarded = module_variant(holed, overflow=False)
        lost_g = np.flatnonzero((base.notna() & guarded.isna()).to_numpy())
        lost_u = np.flatnonzero((base.notna() & unguarded.isna()).to_numpy())
        print(f"  {label}: guarded empties {len(lost_g)} bars "
              f"{(int(lost_g.min()), int(lost_g.max())) if len(lost_g) else None}"
              f", unguarded empties {len(lost_u)} bars "
              f"{(int(lost_u.min()), int(lost_u.max())) if len(lost_u) else None}")
    print("  magnitude sweep of ONE planted giant return. 'emptied' counts "
          "bars the base frame fires and this one does not; 'oracle gap' is "
          "max |module - per-window oracle| over bars 261..399, i.e. AFTER "
          "the planted return has left every window:")
    for exp in (2, 4, 6, 8, 20, 100, 140, 152, 153, 160, 200, 300):
        holed = base_frame.copy()
        holed.iloc[200] = float(base_frame.iloc[199]) * 10.0 ** exp
        g = ts_aggac_60(holed)
        no_trust = module_variant(holed, trust=False)
        oracle = source_windowed(holed)
        tail = slice(261, 400)
        d = (g.iloc[tail] - oracle.iloc[tail]).abs()
        dn = (no_trust.iloc[tail] - oracle.iloc[tail]).abs()
        print(f"    return ~1e+{exp}: module empties "
              f"{int((base.notna() & g.isna()).sum())} bars, of 139 tail bars "
              f"{int(g.iloc[tail].isna().sum())} are NaN and the rest are "
              f"{float(d.max()):.3e} from the per-window oracle; WITHOUT the "
              f"trust test {int(no_trust.iloc[tail].isna().sum())} NaN and "
              f"{float(dn.max()):.3e} from it")

    head("Guards. the isfinite filter this module does NOT spell")
    # `ts_ac1_60` has an `r.where(np.isfinite(r))` between the ratio and the
    # square bound. This module does not, because `square < max/(8*length)`
    # already rejects the same values -- inf squares to inf and NaN compares
    # False. `finite=True` adds the line back; if it changed anything, the
    # omission would be a bug. Measured rather than argued, on every frame
    # that can produce a non-finite return.
    for label, holed in (
            ("one close of 1e-300 at 200 (next return ~1e+302)",
             _planted(base_frame, {200: 1e-300})),
            ("closes of 1e-300 at 200 and 1e+300 at 201 (an INFINITE ratio)",
             _planted(base_frame, {200: 1e-300, 201: 1e+300})),
            ("close inf at 200", _planted(base_frame, {200: np.inf})),
            ("close nan at 200", _planted(base_frame, {200: np.nan})),
            ("clean walk", base_frame)):
        shipped = ts_aggac_60(holed)
        with_it = module_variant(holed, finite=True)
        same_mask = bool((shipped.isna() == with_it.isna()).all())
        m = shipped.notna() & with_it.notna()
        print(f"  {label}: NaN masks identical={same_mask}, bit-equal "
              f"{int((shipped[m] == with_it[m]).sum())}/{int(m.sum())}")
    # And with the square bound GONE, so the filter would be the only thing
    # left to reject an infinity.
    inf_frame = _planted(base_frame, {200: 1e-300, 201: 1e+300})
    a = module_variant(inf_frame, overflow=False, finite=True)
    b = module_variant(inf_frame, overflow=False)
    mb = a.notna() & b.notna()
    print(f"  with the square bound removed, adding the filter changes "
          f"{int(a.isna().sum()) - int(b.isna().sum())} bars "
          f"({int(a.isna().sum())} vs {int(b.isna().sum())} NaN of {len(a)}) "
          f"and the values it still reports are bit-equal on "
          f"{int((a[mb] == b[mb]).sum())}/{int(mb.sum())}")

    head("Guards. a volatility regime COLLAPSE, not a spike")
    # `ts_cid_ce_20` records this as the shape pandas' online accumulators
    # really lose: sigma 0.3 for 200 bars, then sigma 1e-9. The variance that
    # leaves the window is enormous against the one that stays.
    collapse = two_scale()
    strict = ts_aggac_60(collapse)
    loose = module_variant(collapse, trust=False)
    oracle = source_windowed(collapse)
    tail = slice(200, 400)
    lost = int((loose.notna() & strict.isna()).sum())
    m = loose.iloc[tail].notna() & oracle.iloc[tail].notna()
    err = (loose.iloc[tail][m] - oracle.iloc[tail][m]).abs()
    ms = strict.iloc[tail].notna() & oracle.iloc[tail].notna()
    kept = (strict.iloc[tail][ms] - oracle.iloc[tail][ms]).abs()
    # Which guard does the work here: count the post-collapse windows whose
    # UNGUARDED online variance has already come back at or below the floor.
    rc = collapse / collapse.shift(1) - 1.0
    vc = rc.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
    floored = int((vc.iloc[tail] <= REAL.VAR_FLOOR).sum())
    print(f"  of the 200 post-collapse bars, pandas' online variance is at "
          f"or below the {REAL.VAR_FLOOR:.2e} floor on {floored} -- the floor, "
          f"not the trust test, is what empties them")
    print(f"  fires {int(strict.notna().sum())}/{len(collapse)}, the trust "
          f"test empties {lost} bars; WITHOUT it {int(m.sum())} of the 200 "
          f"post-collapse bars are up to {float(err.max()):.3e} from the "
          f"per-window oracle (their own values run to "
          f"{float(loose.iloc[tail][m].abs().max()):.3f}); WITH it the "
          f"{int(ms.sum())} bars it still reports are "
          f"{float(kept.max()) if int(ms.sum()) else float('nan'):.3e} out")

    head("Guards. the trust test's margin on clean frames")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.5)", ar1()), ("ar1(-0.5)", ar1(phi=-0.5)),
                        ("seasonal(10)", seasonal()),
                        ("alternating (the equality case)", alternating()),
                        ("volatility collapse 0.3 -> 1e-9", two_scale()),
                        ("low-vol walk sigma=1e-6", walk(1500, sigma=1e-6)),
                        ("fine tick 50/0.01",
                         Series(50.0 + 0.01 * np.arange(300)))):
        strict, loose = ts_aggac_60(frame), module_variant(frame, trust=False)
        ratio = module_variant(frame, margin=True).dropna()
        lost = int((loose.notna() & strict.isna()).sum())
        print(f"  {name}: fires {int(strict.notna().sum())}, bars the trust "
              f"test costs: {lost}, max var/(span/2)^2 = "
              f"{float(ratio.max()):.12f}")

    head("Guards. a bad close, and a flat run")
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = base_frame.copy()
        holed.iloc[200] = bad
        out = ts_aggac_60(holed)
        lost = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        moved = int((base.notna() & out.notna()
                     & (base != out)).iloc[:200].sum())
        print(f"  close={bad!r}: empties {len(lost)} bars "
              f"{(int(lost.min()), int(lost.max()))}, bars before it that "
              f"moved: {moved}")
    for identical in (LENGTH, LENGTH + 1, LENGTH + 5):
        flat = base_frame.copy()
        flat.iloc[200:200 + identical] = float(base_frame.iloc[200])
        out = ts_aggac_60(flat)
        lost = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        print(f"  {identical} identical closes at 200: empties {len(lost)} "
              f"bars "
              f"{(int(lost.min()), int(lost.max())) if len(lost) else None}")

    head("Guards. monotone fine-tick paths (the floor is on the DISPERSION)")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = closes / closes.shift(1) - 1.0
        v = r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
        print(f"  price={price:g} tick={tick:g}: |r|~{float(r.iloc[-1]):.3e} "
              f"var~{float(v.iloc[-1]):.3e} fires "
              f"{int(ts_aggac_60(closes).notna().sum())}/300")

    head("Guards. parameters")
    close = walk(400, seed=31)
    for length in (None, 0, -5, 2, 0.5, 2.9, 3, 3.9, 12, 250):
        out = ts_aggac_60(close, length=length)
        print(f"  length={length!r}: name={out.name} "
              f"fires={int(out.notna().sum())}")
    for maxlag in (None, 0, -3, 1, 1.9, 10, 58, 59, 1000):
        out = ts_aggac_60(close, maxlag=maxlag)
        print(f"  maxlag={maxlag!r}: name={out.name} "
              f"fires={int(out.notna().sum())}")
    print(f"  short input (length+1 closes exactly): "
          f"{int(ts_aggac_60(walk(LENGTH + 1, seed=2)).notna().sum())} fired; "
          f"{LENGTH} closes -> {ts_aggac_60(walk(LENGTH)) is None}")


def module_variant(close, length=LENGTH, maxlag=MAXLAG, overflow=True,
                   trust=True, margin=False, numerator=False, finite=False):
    """The module's own computation with one guard switchable, so each can be
    priced. `margin=True` returns the ratio of pandas' online variance to its
    exact local upper bound `(span/2)**2` instead of the column;
    `numerator=True` returns the summed weighted numerators before the single
    division by `maxlag * var`."""
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
    if margin:
        return var / (0.25 * bound)
    with np.errstate(over="ignore", invalid="ignore"):
        ok = var > REAL.VAR_FLOOR
        if trust:
            ok = ok & (var <= 0.25 * bound * (1.0 + REAL.NOISE_FLOOR))
        head_ = tail = 0.0
        weighted = 0.0
        for k in range(1, maxlag + 1):
            tail = tail + (r.shift(k - 1) - mean) ** 2
            head_ = head_ + (r.shift(length - k) - mean) ** 2
            gap = Series(np.square(r.diff(k).to_numpy()), index=r.index)
            gap = gap.rolling(length - k, min_periods=length - k).sum()
            if trust:
                ok = ok & (gap <= (length - k) * bound
                           * (1.0 + REAL.NOISE_FLOOR))
            weighted = weighted + (length * var
                                   - 0.5 * (head_ + tail + gap)) / (length - k)
        if numerator:
            return weighted
        out = weighted / (maxlag * var.where(ok))
    return out


# ------------------------------------------------------------------ cost


def cost():
    head("Cost")
    big = walk(400_000, seed=4)
    for length, maxlag in ((12, 10), (60, 1), (60, 10), (250, 10)):
        best = min(_timed(big, length, maxlag) for _ in range(3))
        print(f"  length={length} maxlag={maxlag}: {best[0] * 1e3:.0f} ms, "
              f"peak {best[1] / 1e6:.1f} MB (400,000 bars)")
    print("  what the trust test costs, same code path, flag flipped:")
    for label, trust in (("with the trust test", True),
                         ("without it", False)):
        best = min(_timed_variant(big, trust) for _ in range(3))
        print(f"    {label}: {best[0] * 1e3:.0f} ms, peak "
              f"{best[1] / 1e6:.1f} MB")
    print("  the sliding-window oracle on the same input, for contrast:")
    tracemalloc.start()
    t0 = time.perf_counter()
    source_windowed(big)
    ms = (time.perf_counter() - t0) * 1e3
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"    sliding-window source: {ms:.0f} ms, peak {peak / 1e6:.1f} MB")


def _timed_variant(close, trust):
    tracemalloc.start()
    t0 = time.perf_counter()
    module_variant(close, trust=trust)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return elapsed, peak


def _timed(close, length, maxlag):
    tracemalloc.start()
    t0 = time.perf_counter()
    ts_aggac_60(close, length=length, maxlag=maxlag)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return elapsed, peak


# ------------------------------------------------- the CI CPU's kernels


def cpu():
    """Re-run `tests/test_ts_aggac_60.py` with numpy's AVX-512/AVX2/FMA3
    kernels disabled, which is what a GitHub runner gives us. Float results
    differ in their last bits by CPU, so a tolerance that only holds on this
    machine is a real defect and this is where it shows up.

    It lives here because the variable has to be set BEFORE numpy is
    imported, so it cannot be done from inside a test."""
    import os
    import subprocess
    import sys

    head("The test module on CI's CPU kernels")
    env = dict(os.environ)
    env["NPY_DISABLE_CPU_FEATURES"] = "AVX512F AVX512_SKX AVX2 FMA3"
    print("  NPY_DISABLE_CPU_FEATURES=" + env["NPY_DISABLE_CPU_FEATURES"])
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_ts_aggac_60.py", "-q"],
        env=env, capture_output=True, text=True)
    print("\n".join(out.stdout.strip().splitlines()[-3:]))
    print(f"  exit code {out.returncode}")


if __name__ == "__main__":
    print("pandas_ta.statistics.ts_aggac_60 -- measurements for issue #96")
    print(f"NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR:.6e} "
          f"VAR_FLOOR={REAL.VAR_FLOOR:.6e} MIN_LENGTH={REAL.MIN_LENGTH}")
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    sections = {"a": gate_a, "b": gate_b, "cd": gate_c_d, "meaning": meaning,
                "guards": guards, "cost": cost, "cpu": cpu}
    for key, fn in sections.items():
        if only in (None, key):
            fn()
