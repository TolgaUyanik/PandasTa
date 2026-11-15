# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsAc160Measured.md for `ts_ac1_60`
(PandasTa issue #94, TS-AC1-60).

Run from the repository root:

    python docs/measure_ts_ac1_60.py

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

from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60

LENGTH, LAG = 60, 1
REAL = importlib.import_module("pandas_ta.statistics.ts_ac1_60")


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------------ frames


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.5):
    """A path whose LOG returns are an AR(1): `rlog[t] = phi*rlog[t-1] + eps`,
    whose population lag-1 autocorrelation is exactly `phi`. The column reads
    SIMPLE returns, which is a different (monotone) transform of it."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def alternating(n=1500, amp=0.01):
    """Returns alternate +amp / -amp exactly, so every window of an even
    length holds equal counts of the two and the statistic is exactly -1."""
    r = np.where(np.arange(n) % 2 == 0, amp, -amp)
    return Series(100.0 * np.cumprod(1.0 + r))


def geometric_ladder(n=300, step=0.01):
    return Series(100.0 * np.exp(np.arange(n) * step))


def mean_dominated(n=400, seed=3, mu=0.01, ratio=1e5):
    """Returns with a large MEAN and a tiny DISPERSION: `|mean| / sd` is
    `ratio`. This is the shape that breaks the plain raw-sum spelling of the
    numerator, and it is still well above the variance floor."""
    rng = np.random.default_rng(seed)
    r = mu + rng.normal(0.0, abs(mu) / ratio, n)
    return Series(100.0 * np.cumprod(1.0 + r))


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


def tsfresh_autocorrelation(x, lag=LAG):
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


def source_windowed(close, length=LENGTH, lag=LAG, guard="floor",
                    log_returns=False, closes_not_returns=False, ddof=0,
                    biased=False):
    """The source formula applied window by window with
    `sliding_window_view`: no pandas rolling anywhere, so it shares no window
    machinery with the module. The keywords are the rejected readings of
    section A6."""
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
    # A planted giant return overflows this spelling, which is one reason it
    # is the oracle and not the module.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        m = W.mean(axis=1, keepdims=True)
        dev = W - m
        num = (dev[:, lag:] * dev[:, :W.shape[1] - lag]).sum(axis=1)
        v = W.var(axis=1, ddof=ddof)
        vals = num / (norm * v)
    if guard == "floor":                 # this module's guard
        vals = np.where(v > REAL.VAR_FLOOR, vals, np.nan)
    elif guard == "isclose":             # tsfresh's own: absolute, atol 1e-8
        vals = np.where(np.isclose(v, 0.0), np.nan, vals)
    elif guard != "none":
        raise ValueError(guard)
    out[width:] = vals
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH, lag=LAG):
    """Plain-Python scalars, `math.fsum` for every sum: no numpy, no pandas
    rolling, and the summation is exact to one rounding."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        x = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        m = math.fsum(x) / length
        v = math.fsum((u - m) ** 2 for u in x) / length
        num = math.fsum((x[i] - m) * (x[i - lag] - m)
                        for i in range(lag, length))
        if v > REAL.VAR_FLOOR:
            out[t] = num / ((length - lag) * v)
    return Series(out, index=close.index)


def exact_loop(close, length=LENGTH, lag=LAG, bars=None):
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
        num = sum((x[i] - m) * (x[i - lag] - m) for i in range(lag, length))
        if v != 0:
            out[t] = float(num / ((length - lag) * v))
    return Series(out, index=close.index)


def plain_expansion(close, length=LENGTH, lag=LAG):
    """The spelling the module REJECTS: the same numerator as the raw sum
    `sum x[i]*x[i-1] - m*((length+1)*m - oldest - newest)`, which is
    algebraically identical and cancels when a window's mean dwarfs its
    dispersion."""
    px = close.astype(float)
    r = px / px.shift(1) - 1.0
    rolling = r.rolling(length, min_periods=length)
    mean = rolling.mean()
    var = rolling.var(ddof=0)
    products = (r * r.shift(lag)).rolling(length - lag,
                                          min_periods=length - lag).sum()
    oldest = r.shift(length - 1)
    num = products - mean * ((length + 1) * mean - oldest - r)
    return num / ((length - lag) * var.where(var > REAL.VAR_FLOOR))


def screen_candidate():
    """`REG["ts_ac1_60"]["fn"]` out of the screen's own registry, when this
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
    return mod.REG["ts_ac1_60"]["fn"]


def prototype(close, length=LENGTH, lag=LAG):
    """`docs/issues/screen/ind_screen.py` candidate `ts_ac1_60`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            r = ret(c)
            return corr(r, delay(r, 1), 60)

    with `ret(c) = c / c.shift(1) - 1`, `delay(x, n) = x.shift(n)` and
    `corr(x, y, n) = (x.rolling(n).corr(y)).replace([inf, -inf], nan)`. It is
    a PEARSON correlation of two 60-pair slices -- two means, two standard
    deviations, 61 returns of history -- and not the source formula."""
    r = close / close.shift(1) - 1
    return r.rolling(length).corr(r.shift(lag)).replace(
        [np.inf, -np.inf], np.nan)


def pearson_same_window(close, length=LENGTH, lag=LAG):
    """`pandas.Series.autocorr` applied to the module's OWN window of
    `length` returns: the same history, the Pearson normalisation."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    if len(r) < length + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], length)
    vals = np.array([float(Series(w).autocorr(lag)) for w in W])
    out[length:] = vals
    return Series(out, index=close.index)


# ----------------------------------------------------------------- Gate A


def gate_a():
    head("Gate A1. windows with a closed form")
    # An alternating window: deviations are +-d, every one of the length-1
    # products is -d**2 and the population variance is d**2, so the ratio is
    # exactly -1 regardless of length.
    out = ts_ac1_60(Series([1.0, 2.0, 1.0, 2.0, 1.0]), length=4)
    print(f"  closes [1,2,1,2,1] length=4: name={out.name} "
          f"warmup-nan={bool(out.iloc[:4].isna().all())} "
          f"value={float(out.iloc[4])!r} exactly-minus-one="
          f"{float(out.iloc[4]) == -1.0}")
    col = ts_ac1_60(alternating(), length=LENGTH).dropna()
    print(f"  alternating frame at length={LENGTH}: n={len(col)} "
          f"distinct={int(col.nunique())} "
          f"bit-equal-to-minus-one={int((col == -1.0).sum())} "
          f"max|value+1|={float((col + 1.0).abs().max()):.3e}")
    # A window of two returns is identically -1 (arithmetic, below the
    # module's own minimum length of 3, so it is computed by the oracle).
    two = [float(source_windowed(walk(200, seed=s), length=2).dropna().iloc[-1])
           for s in (1, 2, 3)]
    print(f"  length=2 by the oracle, three seeds: {two} "
          f"(module minimum length is {REAL.MIN_LENGTH})")

    head("Gate A2. against the screen prototype -- a DIFFERENT statistic")
    close = walk()
    base = ts_ac1_60(close)
    fn = screen_candidate()
    if fn is None:
        print("  docs/issues/screen/ind_screen.py absent -- skipped")
    else:
        o = h = l = close
        proto = fn(o, h, l, close, Series(np.full(len(close), 1000.0)))
        compare("imported prototype", base, Series(proto, index=close.index))
    compare("retyped prototype", base, prototype(close))
    if fn is not None:
        imported = Series(fn(close, close, close, close,
                             Series(np.full(len(close), 1000.0))),
                          index=close.index)
        compare("imported vs retyped prototype", imported, prototype(close))
    p = prototype(close)
    print(f"  first fired bar: module={int(base.notna().to_numpy().argmax())} "
          f"prototype={int(p.notna().to_numpy().argmax())}")

    head("Gate A3. against the source formula, window by window")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.5)", ar1())):
        compare(f"sliding-window source, {name}",
                ts_ac1_60(frame), source_windowed(frame))

    head("Gate A4. accuracy against an EXACT rational oracle")
    for name, frame in (("walk", walk(340, seed=11)),
                        ("tick-rounded", tick_rounded(340, seed=55)),
                        ("mean-dominated |m|/sd=1e5", mean_dominated(340))):
        exact = exact_loop(frame, bars=120)
        m = exact.notna()
        for label, series in (("module", ts_ac1_60(frame)),
                              ("fsum loop", scalar_loop(frame)),
                              ("sliding-window", source_windowed(frame)),
                              ("plain raw-sum expansion",
                               plain_expansion(frame))):
            d = (series[m] - exact[m]).abs()
            print(f"  {name} / {label}: n={int(m.sum())} "
                  f"max|error|={float(d.max()):.6e}")

    head("Gate A5. the two degeneracy guards")
    for name, frame in (("walk", walk(300)),
                        ("tick-rounded", tick_rounded(300)),
                        ("1%-a-bar geometric ladder", geometric_ladder()),
                        ("flat 50.0", Series(np.full(300, 50.0))),
                        ("low-vol walk sigma=1e-6", walk(300, sigma=1e-6)),
                        ("low-vol walk sigma=1e-9", walk(300, sigma=1e-9))):
        mod = ts_ac1_60(frame)
        tsf = source_windowed(frame, guard="isclose")
        unguarded = source_windowed(frame, guard="none")
        r = (frame / frame.shift(1) - 1.0)
        v = r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
        print(f"  {name}: module fires {int(mod.notna().sum())}, "
              f"tsfresh's isclose(v,0) guard fires {int(tsf.notna().sum())}, "
              f"unguarded fires {int(unguarded.notna().sum())} "
              f"(max|value| {float(unguarded.abs().max()):.3e}), "
              f"min var={float(v.min()):.3e}")

    head("Gate A6. the readings the wording leaves open")
    close = walk()
    base = ts_ac1_60(close)
    compare("prototype: Pearson corr over 60 PAIRS (61 returns)",
            base, prototype(close))
    compare("Pearson (Series.autocorr) over the same 60 returns",
            base, pearson_same_window(close))
    compare("biased: divide by length*var, not (length-1)*var",
            base, source_windowed(close, biased=True))
    compare("sample variance (ddof=1) in the divisor",
            base, source_windowed(close, ddof=1))
    compare("log returns", base, source_windowed(close, log_returns=True))
    compare("60 CLOSES (59 returns) instead of 60 returns",
            base, source_windowed(close, closes_not_returns=True))
    biased = source_windowed(close, biased=True)
    m = base.notna() & biased.notna()
    factor = (LENGTH - LAG) / LENGTH
    print(f"  biased is an exact rescale: max|port*{factor:.6f} - biased|="
          f"{float((base[m] * factor - biased[m]).abs().max()):.3e}")
    ddof1 = source_windowed(close, ddof=1)
    m = base.notna() & ddof1.notna()
    factor = (LENGTH - 1) / LENGTH
    print(f"  ddof=1 is an exact rescale: max|port*{factor:.6f} - ddof1|="
          f"{float((base[m] * factor - ddof1[m]).abs().max()):.3e}")
    compare("the two rescalings against each other", biased, ddof1)

    head("Gate A7. the reachable bounds")
    for n in (4, 10, 60):
        lo, hi = _bounds(n)
        print(f"  length={n}: constrained Rayleigh bounds, tsfresh scaled: "
              f"min={lo:.12f} max={hi:.12f} (n/(n-1)={n/(n-1):.6f})")
        for label, target in (("max", hi), ("min", lo)):
            y = _extreme_window(n, target)
            closes = Series(np.concatenate([[100.0],
                                            100.0 * np.cumprod(1.0 + y)]))
            got = float(ts_ac1_60(closes, length=n).iloc[-1])
            print(f"    {label}: module={got!r} target={target!r} "
                  f"|difference|={abs(got - target):.3e}")


def _tridiagonal(n):
    t = np.zeros((n, n))
    i = np.arange(n - 1)
    t[i, i + 1] = 0.5
    t[i + 1, i] = 0.5
    return t


def _ortho_basis(n):
    """An orthonormal basis of the subspace orthogonal to the all-ones
    vector: the demeaned windows are exactly that subspace."""
    a = np.eye(n) - np.ones((n, n)) / n
    q, _ = np.linalg.qr(a)
    # Keep the n-1 columns that stay inside the subspace.
    keep = [c for c in range(n)
            if abs(float(np.ones(n) @ q[:, c])) < 1e-10]
    return q[:, keep[:n - 1]]


def _bounds(n, lag=LAG):
    """The reachable minimum and maximum of the column at `length = n`: the
    extreme eigenvalues of the lag-1 product form restricted to the demeaned
    subspace, scaled by tsfresh's `n / (n - lag)`."""
    q = _ortho_basis(n)
    w = np.linalg.eigvalsh(q.T @ _tridiagonal(n) @ q)
    scale = n / (n - lag)
    return float(w.min() * scale), float(w.max() * scale)


def _extreme_window(n, target, amp=0.01, lag=LAG):
    """The return window attaining `target`: the matching eigenvector, scaled
    to a plausible return amplitude."""
    q = _ortho_basis(n)
    w, vecs = np.linalg.eigh(q.T @ _tridiagonal(n) @ q)
    idx = int(np.argmax(w)) if target > 0 else int(np.argmin(w))
    y = q @ vecs[:, idx]
    return amp * y / float(np.abs(y).max())


# ----------------------------------------------------------------- Gate B


OFFSETS = range(100, 1500, 40)

MUTANTS = {
    "write_shift": ("    tsac1 = numerator / ((length - LAG)",
                    "    tsac1 = (numerator).shift(-length) / ((length - LAG)"),
    "forward_return": ("        r = px / px.shift(1) - 1.0",
                       "        r = px.shift(-1) / px - 1.0"),
    "forward_oldest": ("    oldest = r.shift(length - 1)",
                       "    oldest = r.shift(-(length - 1))"),
    "centered_var": ("    var = rolling.var(ddof=0)",
                     "    var = r.rolling(length, min_periods=length, "
                     "center=True).var(ddof=0)"),
    "centered_mean": ("    mean = rolling.mean()",
                      "    mean = r.rolling(length, min_periods=length, "
                      "center=True).mean()"),
    "centered_gap": ("    gap = gap.rolling(length - LAG, "
                     "min_periods=length - LAG).sum()",
                     "    gap = gap.rolling(length - LAG, "
                     "min_periods=length - LAG, center=True).sum()"),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_ac1_60_mutant")
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
              f"{leaks(ts_ac1_60, close, other)}/{len(list(OFFSETS))} offsets")

    head("Gate B. every mutant, every frame, at the default length")
    for label, mutant in MUTANTS.items():
        mod = load_mutant(*mutant)
        for name, (close, other) in frames.items():
            live = not mod.ts_ac1_60(close).equals(ts_ac1_60(close))
            print(f"  {label} / {name}: caught "
                  f"{leaks(mod.ts_ac1_60, close, other)}/"
                  f"{len(list(OFFSETS))}, mutation live={live}")

    head("Gate B. the length-dependent mutants at non-default lengths")
    close, other = frames["walk"]
    for label in ("write_shift", "forward_oldest", "centered_var",
                  "centered_gap"):
        mod = load_mutant(*MUTANTS[label])
        for length in (3, 60, 250):
            def real(c, n=length):
                return ts_ac1_60(c, length=n)

            def mutated(c, n=length):
                return mod.ts_ac1_60(c, length=n)

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
                        ("ar1(+0.5)", ar1()), ("ar1(-0.5)", ar1(phi=-0.5))):
        out = ts_ac1_60(frame)
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
            base, scaled = ts_ac1_60(frame), ts_ac1_60(frame * k)
            m = base.notna() & scaled.notna()
            print(f"  {name} x{k:g}: bit-equal {int((base[m] == scaled[m]).sum())}"
                  f"/{int(m.sum())} masks-agree="
                  f"{bool((base.isna() == scaled.isna()).all())}")
        for k in (10.0, 3.7):
            base, scaled = ts_ac1_60(frame), ts_ac1_60(frame * k)
            m = base.notna() & scaled.notna()
            print(f"  {name} x{k:g}: max|diff|="
                  f"{float((base[m] - scaled[m]).abs().max()):.3e} "
                  f"spearman={float(base[m].corr(scaled[m], method='spearman')):.6f} "
                  f"masks-agree={bool((base.isna() == scaled.isna()).all())}")
    close = walk()
    for length in (3, 20, 250):
        base = ts_ac1_60(close, length=length)
        scaled = ts_ac1_60(close * 8.0, length=length)
        m = base.notna() & scaled.notna()
        print(f"  walk x8 at length={length}: bit-equal "
              f"{int((base[m] == scaled[m]).sum())}/{int(m.sum())}")

    head("Gate D. invariance to an AFFINE map of the RETURNS")
    close = walk()
    base = ts_ac1_60(close)
    for label, other in (
            ("+0.004 of log drift a bar",
             Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))),
            ("returns x2 (closes rebuilt)", _rescaled_returns(close, 2.0)),
            ("returns x0.5 (closes rebuilt)", _rescaled_returns(close, 0.5))):
        compare(label, base, ts_ac1_60(other))

    head("Gate D. why the return is a RATIO and not a difference of logs")
    close = walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    print(f"  returns bit-equal at x8: ratio {int((ratio[m] == ratio8[m]).sum())}"
          f"/{int(m.sum())}, log difference "
          f"{int((plain[m] == plain8[m]).sum())}/{int(m.sum())}")


def _rescaled_returns(close, k):
    r = (close / close.shift(1) - 1.0).to_numpy()[1:]
    return Series(np.concatenate([[float(close.iloc[0])],
                                  float(close.iloc[0]) * np.cumprod(1.0 + k * r)]))


# ------------------------------------------------- what the column means


def meaning():
    head("What the column means")
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(
        rng.normal(0.0, 0.01, (2000, LENGTH + 1)), axis=1))
    est = np.array([float(ts_ac1_60(Series(p)).iloc[-1]) for p in paths])
    print(f"  iid returns, {len(est)} independent 60-return windows: "
          f"median={np.median(est):.4f} mean={est.mean():.4f} "
          f"sd={est.std(ddof=1):.4f} p10={np.percentile(est, 10):.4f} "
          f"p90={np.percentile(est, 90):.4f} "
          f"positive={100 * (est > 0).mean():.2f}% "
          f"finite={int(np.isfinite(est).sum())}/{len(est)}")
    print(f"  the small-sample bias of this normalisation is about "
          f"-1/(n-1) = {-1 / (LENGTH - 1):.4f} and the spread about "
          f"1/sqrt(n) = {1 / math.sqrt(LENGTH):.4f} (arithmetic)")
    for phi in (0.5, 0.25, 0.0, -0.25, -0.5):
        col = ts_ac1_60(ar1(phi=phi)).dropna()
        print(f"  AR(1) log returns phi={phi:+.2f}: median={col.median():.4f} "
              f"p10={np.percentile(col, 10):.4f} "
              f"p90={np.percentile(col, 90):.4f}")
    for n in (20, 60, 200, 1000):
        col = ts_ac1_60(ar1(n=20000, phi=0.5), length=n).dropna()
        print(f"  AR(1) phi=+0.50 on 20,000 bars at length={n}: "
              f"median={col.median():.4f}")
    close = walk()
    base = ts_ac1_60(close)
    r = close / close.shift(1) - 1.0
    for label, other in (
            ("window sd", r.rolling(LENGTH, min_periods=LENGTH).std()),
            ("mean return", r.rolling(LENGTH, min_periods=LENGTH).mean()),
            ("abs mean return",
             r.rolling(LENGTH, min_periods=LENGTH).mean().abs())):
        m = base.notna() & other.notna()
        print(f"  spearman against the same window's {label}: "
              f"{float(base[m].corr(other[m], method='spearman')):.4f}")
    # Every shipped module that takes a lag-1 serial dependence of its own
    # input, found by scanning `pandas_ta/` for `.corr(`/`.cov(` against a
    # `shift(1)` argument: `momentum/a101_048.py:68` and
    # `volatility/roll_spread.py:20`. Both read close DIFFERENCES, not
    # returns, and both wrap the statistic in something else.
    from pandas_ta.momentum.a101_048 import a101_048
    from pandas_ta.volatility.roll_spread import roll_spread
    for label, other in (("a101_048 (250-bar lag-1 autocorrelation of close "
                          "differences, times d/close over a squared-change "
                          "sum)", a101_048(close)),
                         ("roll_spread ROLL_20 (20-bar lag-1 autoCOVARIANCE "
                          "of close differences, kept only where negative)",
                          roll_spread(close))):
        m = base.notna() & other.notna()
        print(f"  spearman against {label}: n={int(m.sum())} "
              f"{float(base[m].corr(other[m], method='spearman')):.4f}")
    print("  persistence of one window: ")
    col = ts_ac1_60(walk(1500)).dropna()
    for lag in (1, 30, 60):
        print(f"    autocorrelation of the COLUMN at lag {lag}: "
              f"{float(col.autocorr(lag)):.4f}")


# ---------------------------------------------------------------- guards


def guards():
    head("Guards. the overflow bound, and what it keeps local")
    print(f"  per-return ceiling: sqrt(max/(8*length)) = "
          f"{math.sqrt(np.finfo(float).max / (8 * LENGTH)):.3e}")
    base_frame = walk(400, seed=21)
    base = ts_ac1_60(base_frame)
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
        guarded = ts_ac1_60(holed)
        unguarded = module_variant(holed, overflow=False)
        lost_g = np.flatnonzero((base.notna() & guarded.isna()).to_numpy())
        lost_u = np.flatnonzero((base.notna() & unguarded.isna()).to_numpy())
        print(f"  {label}: guarded empties {len(lost_g)} bars "
              f"{(int(lost_g.min()), int(lost_g.max())) if len(lost_g) else None}, "
              f"unguarded empties {len(lost_u)} bars "
              f"{(int(lost_u.min()), int(lost_u.max())) if len(lost_u) else None}")
    print("  magnitude sweep of ONE planted giant return. 'emptied' counts "
          "bars the base frame fires and this one does not; 'oracle gap' is "
          "max |module - per-window oracle| over bars 261..399, i.e. AFTER "
          "the planted return has left every window:")
    for exp in (2, 4, 6, 8, 20, 100, 140, 152, 153, 160, 200, 300):
        holed = base_frame.copy()
        holed.iloc[200] = float(base_frame.iloc[199]) * 10.0 ** exp
        g = ts_ac1_60(holed)
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

    head("Guards. the trust test's margin on clean frames")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.5)", ar1()), ("ar1(-0.5)", ar1(phi=-0.5)),
                        ("alternating (the equality case)", alternating()),
                        ("low-vol walk sigma=1e-6", walk(1500, sigma=1e-6)),
                        ("fine tick 50/0.01", Series(50.0 + 0.01 * np.arange(300)))):
        strict, loose = ts_ac1_60(frame), module_variant(frame, trust=False)
        ratio = module_variant(frame, margin=True).dropna()
        lost = int((loose.notna() & strict.isna()).sum())
        print(f"  {name}: fires {int(strict.notna().sum())}, bars the trust "
              f"test costs: {lost}, max var/(span/2)^2 = "
              f"{float(ratio.max()):.12f}")

    head("Guards. a bad close, and a flat run")
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = base_frame.copy()
        holed.iloc[200] = bad
        out = ts_ac1_60(holed)
        lost = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        moved = int((base.notna() & out.notna()
                     & (base != out)).iloc[:200].sum())
        print(f"  close={bad!r}: empties {len(lost)} bars "
              f"{(int(lost.min()), int(lost.max()))}, bars before it that "
              f"moved: {moved}")
    for identical in (LENGTH, LENGTH + 1, LENGTH + 5):
        flat = base_frame.copy()
        flat.iloc[200:200 + identical] = float(base_frame.iloc[200])
        out = ts_ac1_60(flat)
        lost = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        print(f"  {identical} identical closes at 200: empties {len(lost)} "
              f"bars {(int(lost.min()), int(lost.max())) if len(lost) else None}")

    head("Guards. monotone fine-tick paths (the floor is on the DISPERSION)")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = closes / closes.shift(1) - 1.0
        v = r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
        print(f"  price={price:g} tick={tick:g}: |r|~{float(r.iloc[-1]):.3e} "
              f"var~{float(v.iloc[-1]):.3e} fires "
              f"{int(ts_ac1_60(closes).notna().sum())}/300")

    head("Guards. parameters")
    close = walk(400, seed=31)
    for length in (None, 0, -5, 2, 0.5, 2.9, 3, 3.9, 250):
        out = ts_ac1_60(close, length=length)
        print(f"  length={length!r}: name={out.name} "
              f"fires={int(out.notna().sum())}")
    print(f"  short input (length+1 closes exactly): "
          f"{int(ts_ac1_60(walk(LENGTH + 1, seed=2)).notna().sum())} fired; "
          f"{LENGTH} closes -> {ts_ac1_60(walk(LENGTH)) is None}")


def module_variant(close, length=LENGTH, lag=LAG, overflow=True, trust=True,
                   margin=False):
    """The module's own computation with one guard switchable, so each can be
    priced. `margin=True` returns the ratio of pandas' online variance to its
    exact local upper bound `(span/2)**2` instead of the column."""
    px = close.astype(float).to_numpy()
    px = np.where(np.isfinite(px) & (px >= np.finfo(float).tiny), px, np.nan)
    px = Series(px, index=close.index)
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    if overflow:
        with np.errstate(over="ignore"):
            square = np.square(r.to_numpy())
        r = r.where(square < np.finfo(float).max / (8 * length))
    rolling = r.rolling(length, min_periods=length)
    mean, var = rolling.mean(), rolling.var(ddof=0)
    with np.errstate(over="ignore"):
        gap = Series(np.square(r.diff().to_numpy()), index=r.index)
        gap = gap.rolling(length - lag, min_periods=length - lag).sum()
        num = length * var - 0.5 * ((r.shift(length - 1) - mean) ** 2
                                    + (r - mean) ** 2 + gap)
        span = rolling.max() - rolling.min()
        bound = span * span
        if margin:
            return var / (0.25 * bound)
        ok = var > REAL.VAR_FLOOR
        if trust:
            ok = ok & (var <= 0.25 * bound * (1.0 + REAL.NOISE_FLOOR)) \
                & (gap <= (length - lag) * bound * (1.0 + REAL.NOISE_FLOOR))
        out = num / ((length - lag) * var.where(ok))
    return out


# ------------------------------------------------------------------ cost


def cost():
    head("Cost")
    big = walk(400_000, seed=4)
    for length in (3, 20, 60, 250):
        best = min(_timed(big, length) for _ in range(3))
        print(f"  length={length}: {best[0] * 1e3:.0f} ms, peak "
              f"{best[1] / 1e6:.1f} MB (400,000 bars)")
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


def _timed(close, length):
    tracemalloc.start()
    t0 = time.perf_counter()
    ts_ac1_60(close, length=length)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return elapsed, peak


if __name__ == "__main__":
    print(f"pandas_ta.statistics.ts_ac1_60 -- measurements for issue #94")
    print(f"NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR:.6e} "
          f"VAR_FLOOR={REAL.VAR_FLOOR:.6e} MIN_LENGTH={REAL.MIN_LENGTH}")
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    sections = {"a": gate_a, "b": gate_b, "cd": gate_c_d, "meaning": meaning,
                "guards": guards, "cost": cost}
    for key, fn in sections.items():
        if only in (None, key):
            fn()
