# -*- coding: utf-8 -*-
"""TS-CROSS-MEAN-20 (PandasTa issue #100): every number in
`docs/TsCrossMean20Measured.md` and in `tests/test_ts_cross_mean_20.py`.

    python docs/measure_ts_cross_mean_20.py            # everything
    python docs/measure_ts_cross_mean_20.py A D        # named sections

Sections: A (the source and the readings), B (causality by mutant),
C (reachability), D (scale), G (the guards), O (what the column overlaps),
Z (cost). Gate E is run by issue-solver on the shipped module and is NOT
here.

Nothing in this file is imported by the package. It exists so that every
sentence of the receipt can be re-derived by running it.
"""
from __future__ import annotations

import importlib
import math
import sys
import time
import tracemalloc
import types
from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20
from pandas_ta.statistics.ts_cross_mean_20 import NOISE_FACTOR, ts_cross_mean_20
from pandas_ta.statistics.ts_peaks_20 import ts_peaks_20
from pandas_ta.statistics.ts_perment_20 import ts_perment_20
from pandas_ta.trend.chop import chop
from pandas_ta.trend.vhf import vhf

LENGTH = 20
N = 1500
FIRED = N - LENGTH + 1          # 20 CLOSES, so the first value lands at bar 19

_REAL = importlib.import_module("pandas_ta.statistics.ts_cross_mean_20")


# ------------------------------------------------------------------ frames


def _walk(n=N, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=N, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _ar1(n=N, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=N, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=N, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A constant-rate rise: the log closes are MONOTONE, so every window
    reads exactly 1 crossing. Unlike the sibling return-based ports, this is
    a legitimate reading and not a degenerate one."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _patches(n=N, seed=23, sigma=0.015, patch=25, every=40):
    """A walk interrupted every `every` bars by `patch` bars of an UNCHANGED
    close -- a halted stock. Those windows have zero log spread, so the floor
    is the only thing that empties them."""
    c = _walk(n, seed, sigma).to_numpy()
    for start in range(every, n - patch, every + patch):
        c[start:start + patch] = c[start]
    return Series(c)


def _halted(n=N, seed=23, sigma=0.015, length=LENGTH, offsets=None):
    """A walk in which every bar the Gate B sweep splices at is the LAST bar
    of a `length`-bar halt. Designed, and the design is the point: the
    shifted-floor mutant can only ever move bar `J - 1`, and only when the
    floor's verdict on window `J` flips -- so the probe has to put a
    floor-emptied window exactly at each `J`."""
    c = _walk(n, seed, sigma).to_numpy()
    for j in (OFFSETS if offsets is None else offsets):
        c[j - length + 1:j + 1] = c[j - length + 1]
    return Series(c)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
}


# ----------------------------------------------------------------- helpers


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0, 0.0
    return (masks, int(m.sum()), int((a[m] == b[m]).sum()),
            float((a[m] - b[m]).abs().max()))


def _ramped_vol(n=6000, seed=5, price=100.0, lo=-18.0, hi=-8.0):
    """A frame whose per-bar volatility sweeps from 1e-18 to 1e-08, so that
    its windows span the whole range of dispersions the floor has to judge
    -- roughly 1 to 1e+10 ulps of the window's own magnitude."""
    rng = np.random.default_rng(seed)
    sigma = np.logspace(lo, hi, n)
    return Series(price * np.exp(np.cumsum(rng.normal(0.0, 1.0, n) * sigma)))


def _ulps_and_agreement(close, length=LENGTH):
    """Per WINDOW: its `(hi - lo) / (eps * max|x|)`, and whether the
    unguarded float count equals the 60-digit exact one."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    amax = np.maximum(W.max(1), -W.min(1))
    ulps = (W.max(1) - W.min(1)) / (np.finfo(float).eps * amax)
    un = _prototype(close, length).to_numpy()[length - 1:]
    ex = _exact_windowed(close, length).to_numpy()[length - 1:]
    return ulps, un == ex


def _ohlc(close, band=0.004):
    """Deterministic synthetic high/low around a close-only frame, for the
    neighbours that need them. Labelled synthetic wherever it is used."""
    return close * (1.0 + band), close * (1.0 - band)


# ------------------------------------------------------------- the oracles


def _source_windowed(close, length=LENGTH):
    """tsfresh's `number_crossing_m(x, m)` retyped and applied one window at
    a time, with `m` the window's own mean. Shares no code with the module:
    a Python loop, `np.mean`, and the source's own
    `np.where(np.diff(positive))[0].size`."""
    a = np.log(close.to_numpy(dtype=float))
    out = np.full(a.size, np.nan)
    for t in range(length - 1, a.size):
        x = a[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        positive = x > np.mean(x)
        out[t] = float(np.where(np.diff(positive))[0].size)
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH):
    """`math.log` (the C library's, not numpy's) and `math.fsum`, which is
    exact up to a single final rounding."""
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = np.full(len(c), np.nan)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if not all(math.isfinite(v) and v > 0.0 for v in w):
            continue
        x = [math.log(v) for v in w]
        m = math.fsum(x) / length
        s = [v > m for v in x]
        out[t] = float(sum(1 for a, b in zip(s, s[1:]) if a != b))
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH, prec=60):
    """The EXACT answer, to `prec` significant digits -- about 44 beyond a
    double. Every close is a rational, `Decimal.ln()` is correctly rounded at
    `prec` digits, and the mean and the comparisons are then decided at that
    precision. This is the only oracle here that can see the one thing the
    float pipeline can get wrong: deciding a comparison the wrong way.

    `localcontext` and not `getcontext().prec = ...`: the decimal context
    is process-global and an oracle should not leave 60 digits behind."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    with localcontext() as ctx:
        ctx.prec = prec
        n = Decimal(length)
        logs = [Decimal(float(v)).ln() if np.isfinite(v) and v > 0.0 else None
                for v in c]
        for t in range(length - 1, c.size):
            x = logs[t - length + 1:t + 1]
            if any(v is None for v in x):
                continue
            m = sum(x) / n
            s = [v > m for v in x]
            out[t] = float(sum(1 for a, b in zip(s, s[1:]) if a != b))
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_cross_mean_20`,
    retyped: `roll(np.log(c), 20, w_crossings_mean)` with

        w_crossings_mean(W): s = W > W.mean(1, keepdims=True)
                             return (s[:, 1:] != s[:, :-1]).sum(1)

    and `roll` placing the value at bar `n - 1`. No guards of any kind, so
    this is ALSO the unguarded spelling of this module."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    s = W > W.mean(1, keepdims=True)
    out = np.full(a.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _absolute_floor(close, length=LENGTH):
    """This module with the sibling ports' ABSOLUTE `4096 eps` floor on the
    window's log range, instead of the relative one."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    s = W > (W.sum(axis=1) / length)[:, None]
    v = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    rep = W.max(axis=1) - W.min(axis=1) > NOISE_FACTOR
    out = np.full(a.size, np.nan)
    out[length - 1:] = np.where(rep, v, np.nan)
    return Series(out, index=close.index)


# ------------------------------------------------------------- the readings


def _on_raw_closes(close, length=LENGTH):
    """The same count on the closes themselves: the threshold becomes the
    ARITHMETIC mean of the window instead of its geometric mean."""
    a = close.to_numpy(dtype=float)
    W = sliding_window_view(a, length)
    s = W > (W.sum(axis=1) / length)[:, None]
    out = np.full(a.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _on_returns(close, length=LENGTH):
    """The count over 20 simple RETURNS instead of 20 log closes."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r, length)
    s = W > (W.sum(axis=1) / length)[:, None]
    out = np.full(r.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _weak_comparison(close, length=LENGTH):
    """`>=` where the source has `>`."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    s = W >= (W.sum(axis=1) / length)[:, None]
    out = np.full(a.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _crossings_of_zero(close, length=LENGTH):
    """`number_crossing_m(x, m=0)` on log RETURNS -- the other way the source
    function is usually called: how often the window's returns change sign."""
    r = np.log(close / close.shift(1)).to_numpy()
    W = sliding_window_view(r, length)
    s = W > 0.0
    out = np.full(r.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _tie_candidates(kmax=2000, fmax=12):
    """Closes `[k*p, k, k*q, k/(p*q)]` for integers `p, q >= 2` with
    `p*q | k`. Their product is `k**4`, so the EXACT mean of the four logs is
    `log(k)` and the second close ties it -- in real arithmetic. Which of
    them also ties in BINARY arithmetic is what the search is for."""
    rows = []
    for k in range(4, kmax + 1):
        for p in range(2, fmax + 1):
            for q in range(2, fmax + 1):
                if k % (p * q) == 0:
                    rows.append([k * p, k, k * q, k // (p * q)])
    return np.asarray(rows, dtype=float)


def _find_tied_window():
    """The first quadruple whose window mean is BIT-EQUAL to its second log
    close, checked through the shipped function and not only on paper."""
    cand = _tie_candidates()
    x = np.log(cand)
    tied = np.flatnonzero(x[:, 1] == x.sum(axis=1) / 4.0)
    for i in tied:
        closes = Series(cand[i])
        strict = float(ts_cross_mean_20(closes, length=4).iloc[-1])
        weak = float(_weak_comparison(closes, length=4).iloc[-1])
        if strict != weak:
            return [int(v) for v in cand[i]], strict, weak
    return None


# ------------------------------------------------------------------ Gate A


def section_a():
    print("=" * 78)
    print("A. GATE A -- the source formula, and the readings it leaves open")
    print("=" * 78)

    print("\nA0 -- what the oracle actually is")
    try:
        importlib.import_module("tsfresh")
        print("  tsfresh IS importable here -- compare directly.")
    except ImportError as exc:
        print(f"  tsfresh is NOT installed here: {exc}")
    print("  So the formula under test is the issue's line plus the published")
    print("  definition of feature_calculators.number_crossing_m:")
    print("      positive = x > m;  return np.where(np.diff(positive))[0].size")
    print("  with m = the window's own mean, and x = 20 log closes.")

    print("\nA1 -- the source applied window by window (BIT-equality: a count")
    print("      is either right or wrong)")
    print(f"  {'frame':<14}{'masks':>7}{'shared':>8}{'bit-equal':>11}"
          f"{'max |diff|':>12}")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        masks, shared, same, mx = _agree(ts_cross_mean_20(close),
                                         _source_windowed(close))
        print(f"  {name:<14}{str(masks):>7}{shared:>8}{same:>11}{mx:>12.1e}")

    print("\nA2 -- a math.fsum scalar loop with the C library's log")
    print(f"  {'frame':<14}{'masks':>7}{'shared':>8}{'bit-equal':>11}")
    for name in ["walk", "tick-rounded", "heavy-tailed"]:
        close = FRAMES[name]()
        masks, shared, same, _ = _agree(ts_cross_mean_20(close),
                                        _fsum_windowed(close))
        print(f"  {name:<14}{str(masks):>7}{shared:>8}{same:>11}")

    print("\nA3 -- the EXACT oracle, 60 significant digits (Decimal.ln)")
    print("      the only check that can see a comparison decided the wrong way")
    print(f"  {'frame':<14}{'masks':>7}{'shared':>8}{'bit-equal':>11}"
          f"{'max |diff|':>12}")
    for name in ["walk", "tick-rounded", "two-point", "trending"]:
        close = FRAMES[name]()
        masks, shared, same, mx = _agree(ts_cross_mean_20(close),
                                         _exact_windowed(close))
        print(f"  {name:<14}{str(masks):>7}{shared:>8}{same:>11}{mx:>12.1e}")

    print("\nA3b -- the exact oracle where cancellation is worst: a quiet frame")
    print("       at a LARGE price level, so |log c| is big and the spread tiny")
    for price, sigma in [(1.0e6, 1e-7), (1.0e6, 1e-9), (1.0e-6, 1e-7)]:
        rng = np.random.default_rng(31)
        close = Series(price * np.exp(np.cumsum(rng.normal(0, sigma, 600))))
        col = ts_cross_mean_20(close)
        masks, shared, same, mx = _agree(col, _exact_windowed(close))
        a = np.log(close.to_numpy())
        W = sliding_window_view(a, LENGTH)
        spread = float(np.median(W.max(1) - W.min(1)))
        print(f"  price {price:>8.0e} sigma {sigma:.0e}: fired {int(col.notna().sum()):>4}"
              f"  median log spread {spread:.3e}  floor "
              f"{NOISE_FACTOR * abs(math.log(price)):.3e}"
              f"  masks {masks}  bit-equal {same}/{shared}  max |diff| {mx:.1e}")

    print("\nA4 -- the range the floor buys: 1 <= count <= length - 1, counted")
    lo_all, hi_all = [], []
    for name in sorted(FRAMES):
        col = ts_cross_mean_20(FRAMES[name]()).dropna()
        lo_all.append(float(col.min()))
        hi_all.append(float(col.max()))
        print(f"  {name:<14} min {col.min():>5.0f}  max {col.max():>5.0f}  "
              f"distinct {col.nunique():>3}  fired {col.size}")
    print(f"  over all nine frames: min {min(lo_all):.0f}, max {max(hi_all):.0f}"
          f" (the derivation says 1 and {LENGTH - 1})")
    print("  the UNGUARDED spelling, on a 300-bar flat frame:")
    un = _prototype(_flat()).dropna()
    print(f"    reports {un.size} windows, values {sorted(set(un.tolist()))}"
          f" -- the arithmetically impossible 0 among them: "
          f"{0.0 in set(un.tolist())}")

    print("\nA4b -- both ends of the range are attained by construction")
    mono = Series(100.0 * np.exp(np.arange(40, dtype=float) * 0.01))
    alt = Series(100.0 * np.exp(
        np.array([0.0, 0.01] * 20, dtype=float)))
    print(f"  a monotone 20-bar window  -> {ts_cross_mean_20(mono).dropna().unique()}")
    print(f"  an alternating one        -> {ts_cross_mean_20(alt).dropna().unique()}")

    print("\nA5 -- the readings the one-line formula leaves open, priced")
    close = _walk()
    base = ts_cross_mean_20(close)
    for label, other in [
            ("log closes vs RAW closes", _on_raw_closes(close)),
            ("20 log closes vs 20 RETURNS", _on_returns(close)),
            ("strict > vs >=", _weak_comparison(close)),
            ("m = mean vs m = 0 on log returns", _crossings_of_zero(close)),
    ]:
        masks, shared, same, mx = _agree(base, other)
        print(f"  {label:<36} rho {_spearman(base, other):+.6f}  "
              f"bit-equal {same}/{shared}  max |diff| {mx:.0f}")
    share = base / (LENGTH - 1)
    print(f"  {'the raw COUNT vs the share /(n-1)':<36} rho "
          f"{_spearman(base, share):+.6f}  an exact rescaling "
          f"(rank-identical)")

    print("\nA5b -- strict vs >= needs a constructed tie, because none happens")
    ties = 0
    pairs = 0
    for name in ["walk", "tick-rounded", "two-point"]:
        a = np.log(FRAMES[name]().to_numpy())
        W = sliding_window_view(a, LENGTH)
        m = (W.sum(axis=1) / LENGTH)[:, None]
        ties += int((W == m).sum())
        pairs += W.size
    print(f"  exact ties with the window mean: {ties} in {pairs} "
          f"window/close pairs of three frames")
    print("  A tie is impossible at length 3 -- a tied value is NOT above the")
    print("  mean, and its two neighbours cannot both be: with x1 = m the")
    print("  three values sum to 3m, so x0 + x2 is exactly 2m, and two")
    print("  values both strictly above m would sum to MORE. Length 4 is the")
    print("  smallest window where `>` and `>=` can disagree, and the")
    print("  construction is integral: closes [a, k, b, d] with a*b*d = k**3")
    print("  put the exact mean of the logs at log(k).")
    hit = _find_tied_window()
    if hit is None:
        print("  no exact float tie found in the search")
    else:
        closes, strict, weak = hit
        print(f"  found closes {closes}: strict > reads {strict:.0f}, "
              f">= reads {weak:.0f}")

    print("\nA7 -- against the screen prototype")
    print(f"  {'frame':<14}{'masks':>7}{'shared':>8}{'bit-equal':>11}"
          f"{'rho':>10}")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        masks, shared, same, _ = _agree(ts_cross_mean_20(close),
                                        _prototype(close))
        print(f"  {name:<14}{str(masks):>7}{shared:>8}{same:>11}"
              f"{_spearman(ts_cross_mean_20(close), _prototype(close)):>10.6f}")
    for label, close in [("flat", _flat()), ("ladder", _ladder())]:
        col, pro = ts_cross_mean_20(close), _prototype(close)
        print(f"  {label}: port fires {int(col.notna().sum())}, prototype fires "
              f"{int(pro.notna().sum())} "
              f"(prototype values {sorted(set(pro.dropna().tolist()))})")
    bad = _walk()
    bad.iloc[200] = np.nan
    col, pro = ts_cross_mean_20(bad), _prototype(bad)
    diff = int((col.isna() != pro.isna()).sum())
    print(f"  one NaN close at bar 200: masks differ on {diff} bars "
          f"(port empties {int(col.isna().sum())}, prototype "
          f"{int(pro.isna().sum())})")


# ------------------------------------------------------------------ Gate B


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(reported, count, np.nan)",
    "    out[length - 3:c.size - 2] = np.where(reported, count, np.nan)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(reported, count, np.nan)",
    "    out[:windows.shape[0]] = np.where(reported, count, np.nan)")
FORWARD_WINDOW = (
    "    windows = sliding_window_view(x, length)",
    "    windows = sliding_window_view(np.roll(x, -1), length)")
FORWARD_CLOSE = (
    "    x = np.log(c)",
    "    x = np.log(np.roll(c, -1))")
FUTURE_MEAN = (
    "    mean = windows.sum(axis=1) / length",
    "    mean = np.roll(windows.sum(axis=1) / length, -1)")
SHIFTED_FLOOR = (
    "    hi, lo = windows.max(axis=1), windows.min(axis=1)",
    "    hi, lo = (np.roll(windows.max(axis=1), -1),\n"
    "              np.roll(windows.min(axis=1), -1))")

#: Not a causality mutant: the sibling `ts_above_mean_20`'s spelling of the
#: same count, used by section Z to price the two against each other as two
#: MODULES rather than as a module against a bare function.
MATRIX_SPELLING = (
    "    count = np.zeros(windows.shape[0], dtype=np.int64)\n"
    "    prev = windows[:, 0] > mean\n"
    "    for j in range(1, length):\n"
    "        cur = windows[:, j] > mean\n"
    "        count += cur != prev\n"
    "        prev = cur",
    "    above = windows > mean[:, None]\n"
    "    count = np.count_nonzero(above[:, 1:] != above[:, :-1], axis=1)")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_window": FORWARD_WINDOW,
    "forward_close": FORWARD_CLOSE,
    "future_mean": FUTURE_MEAN,
}
OFFSETS = range(40, N, 40)      # 37 offsets
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_cross_mean_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, **kwargs):
    base = fn(close, **kwargs)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p, **kwargs)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


def section_b():
    print("=" * 78)
    print("B. GATE B -- causality, by mutant")
    print("=" * 78)
    print(f"\n  {len(list(OFFSETS))} offsets, three frames.")

    print("\nB1 -- the real module leaks nothing")
    for name in sorted(PAIRS):
        close, other = PAIRS[name]
        print(f"  {name:<14} caught {len(_caught(ts_cross_mean_20, close, other))}"
              f" of {len(list(OFFSETS))}")
    for length in [5, 60, 250]:
        close, other = PAIRS["walk"]
        hits = _caught(ts_cross_mean_20, close, other, length=length)
        first = int(ts_cross_mean_20(close, length=length)
                    .notna().to_numpy().argmax())
        print(f"  length {length:<7} caught {len(hits)} of {len(list(OFFSETS))}"
              f", first fired bar {first}")

    print("\nB2 -- each mutant: live, and what the blind sweep scores")
    for mutant in sorted(MUTANTS):
        mod = _load_mutant(*MUTANTS[mutant])
        row = []
        for name in sorted(PAIRS):
            close, other = PAIRS[name]
            live = not mod.ts_cross_mean_20(close).equals(
                ts_cross_mean_20(close))
            row.append((name, live, len(_caught(mod.ts_cross_mean_20,
                                                close, other))))
        print(f"  {mutant:<16} " + "  ".join(
            f"{n}: live={l} caught={c}" for n, l, c in row))

    print("\nB3 -- the floor's own index: live, and INVISIBLE on a clean frame")
    mod = _load_mutant(*SHIFTED_FLOOR)
    for name in sorted(PAIRS):
        close, other = PAIRS[name]
        real, mut = ts_cross_mean_20(close), mod.ts_cross_mean_20(close)
        moved = np.flatnonzero(
            (real.isna() != mut.isna()).to_numpy()
            | (real.fillna(-99.0) != mut.fillna(-99.0)).to_numpy()).tolist()
        print(f"  {name:<14} live={not mut.equals(real)}  moved bars {moved}"
              f"  sweep caught {len(_caught(mod.ts_cross_mean_20, close, other))}")

    print("\nB4 -- what the shifted floor can move AT ALL, derived then counted")
    print("  The mutant reads `reported[T + 1]` for bar T. Bar T's COUNT")
    print("  still reads closes T-19..T, so a splice at J cannot touch it for")
    print("  T < J; and window T + 1 holds a close at or after J only when")
    print("  T + 1 >= J. So bar J - 1 is the ONLY bar before J that can move,")
    print("  and it moves only when the floor's verdict on window J flips.")
    print("  Counted, on a frame built so that every J IS such a flip:")
    close, other = _halted(), _halted(seed=24)
    col = ts_cross_mean_20(close)
    pro = _prototype(close)
    emptied = int(col.iloc[LENGTH:].isna().sum())
    finite = int(pro.iloc[LENGTH:][col.iloc[LENGTH:].isna()].notna().sum())
    print(f"  bars the floor empties: {emptied}; of those, bars the unguarded")
    print(f"  spelling reports a value on: {finite}, values "
          f"{sorted(set(pro.iloc[LENGTH:][col.iloc[LENGTH:].isna()].dropna().tolist()))}")
    print(f"  real module caught {len(_caught(ts_cross_mean_20, close, other))}"
          f" of {len(list(OFFSETS))}")
    hits = _caught(mod.ts_cross_mean_20, close, other)
    print(f"  shifted-floor mutant caught {len(hits)} of "
          f"{len(list(OFFSETS))}")
    print(f"  and the bar it moves at the first offset: ", end="")
    j = list(OFFSETS)[0]
    p = close.copy()
    p.iloc[j:] = other.iloc[j:].values
    a, b = ts_cross_mean_20(close), ts_cross_mean_20(p)
    am, bm = mod.ts_cross_mean_20(close), mod.ts_cross_mean_20(p)
    print(f"real {np.flatnonzero((a.iloc[:j].isna() != b.iloc[:j].isna()).to_numpy()).tolist()}"
          f", mutant {np.flatnonzero((am.iloc[:j].isna() != bm.iloc[:j].isna()).to_numpy()).tolist()}")

    print("\nB4b -- the UNDESIGNED halt frame, for contrast")
    close, other = _patches(), _patches(seed=24)
    col = ts_cross_mean_20(close)
    pro = _prototype(close)
    emptied = int(col.iloc[LENGTH:].isna().sum())
    finite = int(pro.iloc[LENGTH:][col.iloc[LENGTH:].isna()].notna().sum())
    print(f"  bars the floor empties: {emptied}, all of which the unguarded")
    print(f"  spelling reports on: {finite == emptied} (values "
          f"{sorted(set(pro.iloc[LENGTH:][col.iloc[LENGTH:].isna()].dropna().tolist()))})")
    print(f"  real module caught {len(_caught(ts_cross_mean_20, close, other))}"
          f" of {len(list(OFFSETS))}")
    print(f"  shifted-floor mutant caught "
          f"{len(_caught(mod.ts_cross_mean_20, close, other))} of "
          f"{len(list(OFFSETS))} -- its 25-bar halts start at bars 40, 105,")
    print("  170, ... and the sweep's offsets are multiples of 40, so only a")
    print("  few land on a window the floor empties. A probe built the")
    print("  obvious way scores near zero and proves almost nothing.")

    print("\nB5 -- the first fired bar is length - 1 (20 CLOSES, not 20 returns)")
    col = ts_cross_mean_20(_walk())
    print(f"  first non-NaN bar {int(col.notna().to_numpy().argmax())}, "
          f"bar {LENGTH - 2} is NaN: {bool(np.isnan(col.iloc[LENGTH - 2]))}")


# ------------------------------------------------------------ Gates C and D


def section_c():
    print("=" * 78)
    print("C. GATE C -- reachability on synthetic frames")
    print("=" * 78)
    print(f"\n  {'frame':<14}{'fired':>7}{'of':>6}{'non-zero':>10}"
          f"{'distinct':>10}{'min':>5}{'max':>5}{'modal':>7}{'mode n':>8}")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        col = ts_cross_mean_20(close)
        v = col.dropna()
        counts = v.value_counts()
        print(f"  {name:<14}{int(col.notna().sum()):>7}{col.size:>6}"
              f"{int((v != 0).sum()):>10}{v.nunique():>10}"
              f"{v.min():>5.0f}{v.max():>5.0f}"
              f"{counts.index[0]:>7.0f}{int(counts.iloc[0]):>8}")
    for label, close in [("flat", _flat()), ("ladder", _ladder())]:
        col = ts_cross_mean_20(close)
        v = col.dropna()
        print(f"  {label:<14}{int(col.notna().sum()):>7}{col.size:>6}"
              f"  values {sorted(set(v.tolist()))}")
    print("\n  autocorrelation of the column on a walk (overlapping windows):")
    col = ts_cross_mean_20(_walk()).dropna()
    for lag in [1, 5, 10, 20]:
        print(f"    lag {lag:>3}: {float(col.autocorr(lag)):+.4f}")


def section_d():
    print("=" * 78)
    print("D. GATE D -- scale")
    print("=" * 78)
    print("\n  ⚠ NOTHING here is bit-identical BY CONSTRUCTION. log(8p) is not")
    print("    log(8) + log(p) in binary floating point, so every rescale")
    print("    perturbs the log closes in their last bits; what keeps the")
    print("    COUNT fixed is the margin between |x - mean| and that")
    print("    perturbation, measured in D3.")

    print("\nD1 -- x8 and x64")
    print(f"  {'frame':<14}{'k=8 masks':>11}{'bit-equal':>11}"
          f"{'k=64 masks':>12}{'bit-equal':>11}")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        row = [name]
        for k in (8.0, 64.0):
            masks, shared, same, _ = _agree(ts_cross_mean_20(close),
                                            ts_cross_mean_20(close * k))
            row += [str(masks), f"{same}/{shared}"]
        print(f"  {row[0]:<14}{row[1]:>11}{row[2]:>11}{row[3]:>12}{row[4]:>11}")

    print("\nD1b -- x8 at other lengths, on the walk")
    close = _walk()
    for length in [3, 5, 60, 250]:
        masks, shared, same, _ = _agree(ts_cross_mean_20(close, length=length),
                                        ts_cross_mean_20(close * 8.0,
                                                         length=length))
        print(f"  length {length:>4}: masks {masks}  bit-equal {same}/{shared}")

    print("\nD2 -- x10, x3.7, x0.1 and x1.0000001 (not even nominally exact)")
    print(f"  {'frame':<14}" + "".join(f"{f'x{k}':>14}"
                                       for k in (10.0, 3.7, 0.1, 1.0000001)))
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        cells = []
        for k in (10.0, 3.7, 0.1, 1.0000001):
            masks, shared, same, _ = _agree(ts_cross_mean_20(close),
                                            ts_cross_mean_20(close * k))
            cells.append(f"{same}/{shared}{'' if masks else '*'}")
        print(f"  {name:<14}" + "".join(f"{c:>14}" for c in cells))

    print("\nD3 -- the margin: min |x_i - mean| / max|x| over every window")
    for name in sorted(FRAMES):
        a = np.log(FRAMES[name]().to_numpy())
        W = sliding_window_view(a, LENGTH)
        m = (W.sum(axis=1) / LENGTH)[:, None]
        amax = np.maximum(W.max(1), -W.min(1))[:, None]
        gap = np.abs(W - m) / amax
        print(f"  {name:<14} min {gap.min():.3e}  median {np.median(gap):.3e}")
    rng = np.random.default_rng(77)
    big = Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.015, 200000))))
    a = np.log(big.to_numpy())
    W = sliding_window_view(a, LENGTH)
    m = (W.sum(axis=1) / LENGTH)[:, None]
    amax = np.maximum(W.max(1), -W.min(1))[:, None]
    gap = np.abs(W - m) / amax
    print(f"  200,000-bar walk ({W.shape[0]} windows): min {gap.min():.3e}, "
          f"one ulp is {np.finfo(float).eps:.1e}")
    masks, shared, same, _ = _agree(ts_cross_mean_20(big),
                                    ts_cross_mean_20(big * 8.0))
    print(f"  and x8 on that frame: masks {masks}, bit-equal {same}/{shared}")
    masks, shared, same, _ = _agree(ts_cross_mean_20(big),
                                    ts_cross_mean_20(big * 10.0))
    print(f"  x10 on that frame:    masks {masks}, bit-equal {same}/{shared}")

    print("\nD4 -- a tick-rounded frame at 200,000 bars, where closes repeat")
    tick = Series(np.round(big.to_numpy(), 2))
    col = ts_cross_mean_20(tick)
    print(f"  fired {int(col.notna().sum())} of {col.size}")
    for k in (8.0, 64.0, 10.0):
        masks, shared, same, _ = _agree(col, ts_cross_mean_20(tick * k))
        print(f"  x{k}: masks {masks}, bit-equal {same}/{shared}")

    print("\nD5 -- what the column is INVARIANT to, beyond a price rescale")
    close = _walk()
    base = ts_cross_mean_20(close)
    # x -> a*x + b on the LOG closes is price**a * exp(b): a power transform.
    for label, px in [("price ** 2", close ** 2.0),
                      ("price ** 0.5", close ** 0.5),
                      ("1 / price", 1.0 / close)]:
        masks, shared, same, mx = _agree(base, ts_cross_mean_20(px))
        print(f"  {label:<14} masks {masks}  bit-equal {same}/{shared}  "
              f"max |diff| {mx:.0f}  rho {_spearman(base, ts_cross_mean_20(px)):+.6f}")
    print("  (1/price flips every comparison and leaves the number of")
    print("   SWITCHES unchanged -- that is the symmetry, not an accident)")


# ------------------------------------------------------------- the guards


def section_g():
    print("=" * 78)
    print("G. THE GUARDS, each priced in both directions")
    print("=" * 78)

    print("\nG1 -- what the floor costs on a clean frame")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        col, pro = ts_cross_mean_20(close), _prototype(close)
        print(f"  {name:<14} port fires {int(col.notna().sum()):>5}, "
              f"unguarded {int(pro.notna().sum()):>5}, cost "
              f"{int(pro.notna().sum()) - int(col.notna().sum()):>3} bars")

    print("\nG2 -- what it buys: a flat frame")
    flat = _flat()
    col, pro = ts_cross_mean_20(flat), _prototype(flat)
    print(f"  port fires {int(col.notna().sum())}, unguarded fires "
          f"{int(pro.notna().sum())} with values "
          f"{sorted(set(pro.dropna().tolist()))}")
    print(f"  a window of 20 identical log closes: sum/20 == the value itself? "
          f"{np.log(100.0) * 20 / 20 == np.log(100.0)}")
    a = np.full(LENGTH, np.log(100.0))
    print(f"  numpy's windowed sum/20 of it: "
          f"{sliding_window_view(a, LENGTH).sum(axis=1)[0] / LENGTH!r} vs "
          f"{np.log(100.0)!r}")

    print("\nG3 -- the floor is RELATIVE, and on the ordinary frames that")
    print("      costs and buys NOTHING against an absolute 4096 eps one")
    for label, close in [("flat", _flat()), ("walk", _walk()),
                         ("ladder", _ladder()), ("patches", _patches())]:
        rel, ab = ts_cross_mean_20(close), _absolute_floor(close)
        print(f"  {label:<10} relative fires {int(rel.notna().sum()):>5}, "
              f"absolute fires {int(ab.notna().sum()):>5}")
    print("  They separate only where |log c| is far from 1, which is the")
    print("  whole argument for the relative form:")
    for label, price, step in [("price ~ 1.0 (|log c| ~ 1e-13)", 1.0, 1e-13),
                               ("price 100  (|log c| = 4.6)", 100.0, 1e-15),
                               ("price 1e+6 (|log c| = 13.8)", 1e6, 1e-15)]:
        rng = np.random.default_rng(5)
        close = Series(price * np.exp(np.cumsum(
            rng.normal(0, step, 600))))
        a = np.log(close.to_numpy())
        W = sliding_window_view(a, LENGTH)
        spread = float(np.median(W.max(1) - W.min(1)))
        amax = float(np.median(np.maximum(W.max(1), -W.min(1))))
        ex = _exact_windowed(close)
        pro = _prototype(close)
        masks, shared, same, _ = _agree(pro, ex)
        print(f"  {label:<30} median spread {spread:.3e}  "
              f"relative floor {NOISE_FACTOR * amax:.3e}  "
              f"absolute floor {NOISE_FACTOR:.3e}")
        print(f"    relative fires {int(ts_cross_mean_20(close).notna().sum()):>4}"
              f", absolute fires {int(_absolute_floor(close).notna().sum()):>4}"
              f", and the UNGUARDED count agrees with the exact oracle on "
              f"{same}/{shared}")

    print("\nG3b -- where float actually breaks, bucketed by EACH WINDOW's")
    print("       own `(hi - lo) / (eps * max|x|)`: the exact quantity the")
    print("       floor thresholds, so the buckets are the floor's own axis")
    for label, price in [("price 100", 100.0), ("price 1e+6", 1e6)]:
        close = _ramped_vol(price=price)
        ulps, ok = _ulps_and_agreement(close)
        print(f"  {label}, {ulps.size} windows")
        print(f"  {'bucket (ulps)':>18}{'windows':>9}{'float == exact':>16}"
              f"{'share':>9}")
        edges = [0, 16, 64, 256, 1024, 4096, 16384, 1e6, 1e8, np.inf]
        for lo, hi in zip(edges, edges[1:]):
            m = (ulps >= lo) & (ulps < hi)
            n = int(m.sum())
            if not n:
                continue
            good = int(ok[m].sum())
            print(f"  {f'[{lo:g}, {hi:g})':>18}{n:>9}{good:>16}"
                  f"{good / n:>9.4f}")
    print("  the floor refuses every window below 4096 ulps. Where the nine")
    print("  ordinary frames actually sit on this axis -- min and median")
    print("  ulps per frame, so the table above can be read against them:")
    for name in sorted(FRAMES):
        a = np.log(FRAMES[name]().to_numpy())
        W = sliding_window_view(a, LENGTH)
        amax = np.maximum(W.max(1), -W.min(1))
        u = (W.max(1) - W.min(1)) / (np.finfo(float).eps * amax)
        print(f"    {name:<14} min {u.min():.2e}  median {np.median(u):.2e}")

    print("\nG4 -- a bad close empties exactly the windows holding it")
    for value in [np.nan, np.inf, 0.0, -1.0, 1e-310]:
        close = _walk(400)
        close.iloc[200] = value
        col = ts_cross_mean_20(close)
        base = ts_cross_mean_20(_walk(400))
        emptied = int((col.isna() & base.notna()).sum())
        print(f"  close[200] = {value!r:<8} empties {emptied} bars "
              f"(the {LENGTH} windows holding bar 200)")
    for bar, in [(0,), (1,), (18,), (200,), (398,), (399,)]:
        close = _walk(400)
        close.iloc[bar] = np.nan
        col = ts_cross_mean_20(close)
        base = ts_cross_mean_20(_walk(400))
        print(f"  a NaN at bar {bar:>3}: {int((col.isna() & base.notna()).sum())}"
              f" bars emptied, earliest moved bar "
              f"{int(np.flatnonzero((col.isna() != base.isna()).to_numpy())[0]) if (col.isna() != base.isna()).any() else None}")

    print("\nG5 -- no magnitude bound is needed, and the derivation")
    print(f"  |log c| for the smallest normal double: {math.log(np.finfo(float).tiny):.2f}")
    print(f"  |log c| for the largest double:         {math.log(np.finfo(float).max):.2f}")
    print(f"  so a window of 250 of them sums to at most "
          f"{250 * 709.79:.0f} -- a long way below 1.8e+308")

    print("\nG6 -- one enormous close stays LOCAL")
    base = _walk(2000)
    ref = ts_cross_mean_20(base)
    for mag in [1e2, 1e6, 1e8, 1e100, 1e300]:
        close = base.copy()
        close.iloc[200] = float(close.iloc[200]) * mag
        col = ts_cross_mean_20(close)
        tail_same = int((col.iloc[220:] == ref.iloc[220:]).sum())
        spike = col.iloc[200:220].dropna()
        print(f"  x{mag:<8.0e} bars 220.. bit-identical {tail_same}/1780, "
              f"the 20 windows holding it read "
              f"{sorted(set(spike.tolist()))}")
    print("  the PROTOTYPE is local here too (it is the same windowed form):")
    close = base.copy()
    close.iloc[200] = float(close.iloc[200]) * 1e8
    pro, pro_ref = _prototype(close), _prototype(base)
    print(f"    prototype bars 220.. bit-identical "
          f"{int((pro.iloc[220:] == pro_ref.iloc[220:]).sum())}/1780")


# ----------------------------------------------------- what the column IS


def section_o():
    print("=" * 78)
    print("O. IN-FORK OVERLAP -- what Gate E's 687 comparators cannot see")
    print("=" * 78)
    print("\n  ⚠ SYNTHETIC frames. The real-frame figures are the screen's")
    print("    (2026-10-24, prototype) and the launcher's Gate E run.")

    print("\nO1 -- it is a CHOPPINESS reading: 1 on a monotone window, 19 on an")
    print("      alternating one. Against the fork's choppiness family:")
    names = ["walk", "tick-rounded", "heavy-tailed", "trending", "ar1+", "ar1-"]
    print(f"  {'frame':<14}{'chop':>9}{'vhf':>9}{'momersion':>11}"
          f"{'perment':>9}{'peaks':>8}")
    for name in names:
        close = FRAMES[name]()
        high, low = _ohlc(close)
        base = ts_cross_mean_20(close)
        row = [
            _spearman(base, chop(high, low, close)),
            _spearman(base, vhf(close)),
            _spearman(base, lean_momersion_20(close)),
            _spearman(base, ts_perment_20(close)),
            _spearman(base, ts_peaks_20(close)),
        ]
        print(f"  {name:<14}" + "".join(f"{v:>+9.4f}" if i < 3
                                        else f"{v:>+9.4f}"
                                        for i, v in enumerate(row[:4]))
              + f"{row[4]:>+8.4f}")
    print("  (high/low are SYNTHETIC: close x (1 +- 0.004), so `chop`'s ATR")
    print("   term is a fixed fraction of the close on every bar)")

    print("\nO2 -- against the window's own statistics")
    close = _walk()
    base = ts_cross_mean_20(close)
    a = np.log(close.to_numpy())
    W = sliding_window_view(a, LENGTH)
    # The 19 log returns inside each 20-close window: one row per window.
    rwin = sliding_window_view(np.diff(a), LENGTH - 1)
    assert rwin.shape[0] == W.shape[0]
    stat = {
        "log-close sd": W.std(1, ddof=1),
        "return sd (realised vol)": rwin.std(1, ddof=1),
        "|window drift|": np.abs(W[:, -1] - W[:, 0]),
        "window drift": W[:, -1] - W[:, 0],
        "the close itself": close.to_numpy()[LENGTH - 1:],
        "|drift| / return sd": np.abs(W[:, -1] - W[:, 0]) / rwin.std(1, ddof=1),
    }
    for label, v in stat.items():
        s = Series(np.concatenate([np.full(LENGTH - 1, np.nan), v]),
                   index=close.index)
        print(f"  {label:<18} {_spearman(base, s):+.4f}")

    print("\nO3 -- what the SCREEN measured on real frames (2026-10-24,")
    print("      on the PROTOTYPE, not on this module)")
    print("  Gate E     : max |rho| 0.5500 vs BB_BWidth_Pctl (manifest),")
    print("               n = 391,907; per-frame max median 0.5495 -> SHIP")
    print("  next       : BB_BWidth 0.5095, chop 0.4925")
    print("  fork stage2: max |rho| 0.5684 vs squeeze_pro:SQZPRO_ON_WIDE,")
    print("               12 frames, per-frame max median 0.5708")
    print("  candidate pairs at |rho| >= 0.8019 (cand_pairs.csv, 55 pairs):")
    print("               ts_cross_mean_20 appears in NONE of them")

    print("\nO4 -- a state, not an event flag")
    col = ts_cross_mean_20(_walk()).dropna()
    print(f"  {col.nunique()} distinct values on a walk, modal "
          f"{col.value_counts().index[0]:.0f} taking "
          f"{int(col.value_counts().iloc[0])} of {col.size} bars")

    print("\nO5 -- the level to expect, on INDEPENDENT windows")
    rng = np.random.default_rng(2026)
    for label, W in [
            ("iid gaussian log returns",
             np.cumsum(rng.standard_normal((20000, LENGTH)), axis=1)),
            ("iid, with a +1 sd/bar drift",
             np.cumsum(rng.standard_normal((20000, LENGTH))
                       + 1.0, axis=1)),
            ("white noise log closes (no walk)",
             rng.standard_normal((20000, LENGTH))),
    ]:
        s = W > W.mean(1, keepdims=True)
        v = (s[:, 1:] != s[:, :-1]).sum(1)
        print(f"  {label:<34} mean {v.mean():.4f}  sd {v.std():.4f}  "
              f"min {v.min()}  max {v.max()}")


def section_z():
    print("=" * 78)
    print("Z. COST")
    print("=" * 78)
    rng = np.random.default_rng(4)
    close = Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.015, 400000))))

    # The two spellings are compared as two MODULES differing in exactly
    # those two lines -- not as the module against a bare local function,
    # which would charge the module for its mask, its output array and its
    # Series and so measure the wrong thing.
    matrix = _load_mutant(*MATRIX_SPELLING).ts_cross_mean_20

    def _matrix_form(c, length):
        return matrix(c, length=length)

    def _best_ms(fn, length, repeats=3):
        fn(close, length)                       # warm up, then best of N
        best = float("inf")
        for _ in range(repeats):
            t0 = time.perf_counter()
            fn(close, length)
            best = min(best, (time.perf_counter() - t0) * 1e3)
        return best

    def _peak_mb(fn, length):
        tracemalloc.start()
        fn(close, length)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        return peak

    def _shipped(c, length):
        return ts_cross_mean_20(c, length=length)

    print(f"\n  400,000 bars. 'ms' is the BEST of three after a warm-up call")
    print(f"  (the first call of a process is systematically slower, which is")
    print(f"  how an ordered A/B here reads backwards); 'peak' is")
    print(f"  tracemalloc's peak for one call.")
    print(f"  {'length':>7}{'shipped ms':>12}{'peak MB':>10}"
          f"{'matrix ms':>11}{'peak MB':>10}{'counts equal':>14}")
    for length in [3, 20, 60, 250]:
        a = ts_cross_mean_20(close, length=length)
        b = _matrix_form(close, length)
        m = a.notna() & b.notna()
        print(f"  {length:>7}{_best_ms(_shipped, length):>12.1f}"
              f"{_peak_mb(_shipped, length):>10.1f}"
              f"{_best_ms(_matrix_form, length):>11.1f}"
              f"{_peak_mb(_matrix_form, length):>10.1f}"
              f"{int((a[m] == b[m]).sum()):>9}/{int(m.sum()):<5}")
    print("\n  the window-by-window oracle, for scale:")
    small = Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.015, 20000))))
    t0 = time.perf_counter()
    ts_cross_mean_20(small)
    t1 = time.perf_counter()
    _source_windowed(small)
    t2 = time.perf_counter()
    print(f"    20,000 bars: module {(t1 - t0) * 1e3:.1f} ms, "
          f"window-by-window oracle {(t2 - t1) * 1e3:.1f} ms")


SECTIONS = {"A": section_a, "B": section_b, "C": section_c, "D": section_d,
            "G": section_g, "O": section_o, "Z": section_z}

if __name__ == "__main__":
    wanted = [s.upper() for s in sys.argv[1:]] or list(SECTIONS)
    print(f"numpy {np.__version__}  pandas {pd.__version__}")
    for key in wanted:
        SECTIONS[key]()
        print()
