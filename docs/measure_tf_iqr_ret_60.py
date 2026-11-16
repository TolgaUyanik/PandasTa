# -*- coding: utf-8 -*-
"""TF-IQR-RET-60 (PandasTa issue #117) -- every number in
`docs/TfIqrRet60Measured.md` and in `tests/test_tf_iqr_ret_60.py`.

    python docs/measure_tf_iqr_ret_60.py            # every section
    python docs/measure_tf_iqr_ret_60.py A1 D       # named sections

Sections
    A1  the module against an independent reimplementation of pandas' own
        `rolling.quantile` spelling -- BIT-equality
    A2  against the SOURCE's spelling (TSFEL's `np.percentile(x, 75) -
        np.percentile(x, 25)`) applied window by window -- a tolerance
    A3  against an EXACT rational oracle, in ulps
    A4  what the column reads: four of the 60 returns, nothing else
    A5  the readings the source's line leaves open, priced
    A6  the screen prototype
    B   the causality sweep on the real module
    M   the mutants: five live, one dead on a clean frame
    C   reachability: fires, distinct values, range, sign
    D   scale-freedom: x8 / x64 bit-identity, x10 / x3.7 tolerance, and the
        level SHIFT that is NOT invariant
    G   the guards, and the floor this module does NOT have
    O   overlap: what the column restates and what it does not
    S   the statistic itself: the level to expect, the autocorrelation
    Z   cost
"""
import sys
import time
import tracemalloc
from fractions import Fraction

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.statistics.lot_zeroret_60 import lot_zeroret_60
from pandas_ta.statistics.mad import mad
from pandas_ta.statistics.quantile import quantile
from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20
from pandas_ta.statistics.tf_dfa_100 import tf_dfa_100
from pandas_ta.statistics.tf_higuchi_30 import tf_higuchi_30
from pandas_ta.statistics.tf_iqr_ret_60 import (
    MIN_LENGTH,
    Q_HIGH,
    Q_LOW,
    tf_iqr_ret_60,
)
from pandas_ta.statistics.tf_spec_entropy_64 import tf_spec_entropy_64
from pandas_ta.statistics.tf_zero_cross_20 import tf_zero_cross_20
from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
from pandas_ta.statistics.ts_aggac_60 import ts_aggac_60
from pandas_ta.statistics.ts_imq_20 import ts_imq_20
from pandas_ta.statistics.ts_kurt_60 import ts_kurt_60
from pandas_ta.statistics.ts_q05_60 import ts_q05_60
from pandas_ta.statistics.ts_strike_20 import ts_strike_20
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.ui import ui

LENGTH = 60
N = 1500
FIRED = N - LENGTH          # `length` RETURNS, so `length + 1` closes


# ----------------------------------------------------------------- frames


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
    """Every return is +-1%, so every window's q25 is -0.01 and its q75 is
    +0.01 and the column sits at 0.02 -- measured, 5 doubles spanning
    2.220e-16, numerically a constant. The Gate D tie frame."""
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


def _vol_cycle(n=N, seed=19, lo=0.004, hi=0.03, period=250):
    """Volatility that breathes: the column's own signal, so the frame the
    overlap section needs most."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    sigma = lo + 0.5 * (hi - lo) * (1.0 + np.sin(2 * np.pi * t / period))
    return _from_returns(np.clip(sigma * rng.standard_normal(n), -0.5, 0.5))


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A constant-rate rise: every return is mathematically the same number,
    and float64 reproduces it only to rounding."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _quiet(n=600, price=100.0, step=1e-6, seed=13):
    """Honest but tiny returns: 1e-6 a bar."""
    rng = np.random.default_rng(seed)
    return _from_returns(step * rng.standard_normal(n)) * (price / 100.0)


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
    "vol-cycle": _vol_cycle,
}
#: `tests/test_tf_iqr_ret_60.py` runs the EXACT oracle on these four, to
#: keep the suite quick; this script runs it on all ten (A3).
EXACT_FRAMES = ["walk", "tick-rounded", "heavy-tailed", "two-point"]


# ---------------------------------------------------------------- helpers


def _ret(close):
    return close / close.shift(1) - 1.0


def _ohlc(close, band=0.004):
    return close * (1.0 + band), close * (1.0 - band)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    d = float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")
    return masks, int(m.sum()), int((a[m] == b[m]).sum()), d


def _ulps(a, b):
    """|a - b| in units of the last place of `b`."""
    m = a.notna() & b.notna()
    x, y = a[m].to_numpy(), b[m].to_numpy()
    ulp = np.abs(np.nextafter(y, np.inf) - y)
    ulp = np.where(ulp == 0.0, np.finfo(float).tiny, ulp)
    return np.abs(x - y) / ulp


def _max_rel(a, b):
    m = a.notna() & b.notna() & (b != 0.0)
    if not int(m.sum()):
        return 0.0
    return float(((a[m] - b[m]).abs() / b[m].abs()).max())


def _head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------- oracles


def _pandas_spelling(close, length=LENGTH, q_lo=Q_LOW, q_hi=Q_HIGH):
    """pandas' `roll_quantile` with `interpolation='linear'`, retyped from
    its documented behaviour and sharing no code with the module: sort the
    window, take the two order statistics around `q * (n - 1)`, and blend
    them as `vlow + (vhigh - vlow) * frac`. Then subtract."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i_hi, i_lo = q_hi * (length - 1), q_lo * (length - 1)
    hi_k, hi_f = int(i_hi), i_hi % 1
    lo_k, lo_f = int(i_lo), i_lo % 1
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        a, b = s[hi_k], s[min(hi_k + 1, length - 1)]
        hi = a + (b - a) * hi_f
        a, b = s[lo_k], s[min(lo_k + 1, length - 1)]
        lo = a + (b - a) * lo_f
        out[t] = hi - lo
    return Series(out, index=close.index)


def _source_windowed(close, length=LENGTH, q_lo=Q_LOW, q_hi=Q_HIGH):
    """TSFEL's `interq_range`: `np.percentile(signal, 75) -
    np.percentile(signal, 25)`, over the trailing `length` returns, one
    window at a time."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        out[t] = np.percentile(w, 100.0 * q_hi) - np.percentile(w,
                                                                100.0 * q_lo)
    return Series(out, index=close.index)


def _exact(close, length=LENGTH, q_lo=None, q_hi=None):
    """The correctly rounded answer. Every return is a double, so a
    rational; the sort is exact, each blend and the subtraction are done in
    `Fraction`, and the result is rounded exactly ONCE, at the end.

    The quantiles default to `Fraction(0.75)` and `Fraction(0.25)` -- both
    are exact binary fractions, so the EXACT value of the doubles the
    source is handed is 3/4 and 1/4 and there is no 0.05-style surprise
    here (A5 shows the contrast)."""
    qh = Fraction(Q_HIGH) if q_hi is None else q_hi
    ql = Fraction(Q_LOW) if q_lo is None else q_lo
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i_hi, i_lo = qh * (length - 1), ql * (length - 1)
    hi_k, hi_f = int(i_hi), i_hi - int(i_hi)
    lo_k, lo_f = int(i_lo), i_lo - int(i_lo)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = sorted(Fraction(float(v)) for v in w)
        hi = s[hi_k] + (s[min(hi_k + 1, length - 1)] - s[hi_k]) * hi_f
        lo = s[lo_k] + (s[min(lo_k + 1, length - 1)] - s[lo_k]) * lo_f
        out[t] = float(hi - lo)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `tf_iqr_ret_60`,
    retyped (that tree is the owner's and gitignored, so it is copied rather
    than imported):
    `ret(c).rolling(60).quantile(0.75) - ret(c).rolling(60).quantile(0.25)`
    with `ret(c) = c / c.shift(1) - 1`. No guards of any kind."""
    r = close / close.shift(1) - 1.0
    return r.rolling(length).quantile(0.75) - r.rolling(length).quantile(0.25)


# ===================================================================== A1


def section_A1():
    _head("A1  the module against pandas' own spelling, retyped (BIT-equal)")
    print(f"{'frame':14s} {'masks':6s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>12s}")
    for name, make in FRAMES.items():
        close = make()
        masks, shared, same, d = _agree(tf_iqr_ret_60(close),
                                        _pandas_spelling(close))
        print(f"{name:14s} {str(masks):6s} {shared:7d} {same:10d} {d:12.3e}")

    print()
    print("the same, at other lengths, on the walk")
    close = _walk()
    for length in (MIN_LENGTH, 5, 20, 21, 250):
        masks, shared, same, d = _agree(
            tf_iqr_ret_60(close, length=length),
            _pandas_spelling(close, length=length))
        print(f"length {length:4d}   masks {masks}  shared {shared:5d}"
              f"  bit-equal {same:5d}  max |diff| {d:.3e}")

    print()
    print("one `rolling` object reused vs two, on the walk")
    r = _ret(close)
    one = r.rolling(LENGTH, min_periods=LENGTH)
    reused = one.quantile(Q_HIGH) - one.quantile(Q_LOW)
    masks, shared, same, d = _agree(tf_iqr_ret_60(close), reused)
    print(f"  masks {masks}  shared {shared}  bit-equal {same}"
          f"  max |diff| {d:.3e}")


# ===================================================================== A2


def section_A2():
    _head("A2  against the SOURCE's spelling (np.percentile), window by window")
    print(f"{'frame':14s} {'masks':6s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max ulps':>9s} {'max |diff|':>12s} {'rho':>9s}")
    for name in FRAMES:
        close = FRAMES[name]()
        mod, src = tf_iqr_ret_60(close), _source_windowed(close)
        masks, shared, same, d = _agree(mod, src)
        u = _ulps(mod, src)
        print(f"{name:14s} {str(masks):6s} {shared:7d} {same:10d}"
              f" {u.max():9.2f} {d:12.3e} {_spearman(mod, src):9.6f}")

    print()
    print("np.percentile vs Series.quantile vs np.quantile, one window")
    rng = np.random.default_rng(5)
    w = rng.normal(0.0, 0.01, LENGTH)
    a = np.percentile(w, 75.0) - np.percentile(w, 25.0)
    b = float(Series(w).quantile(0.75) - Series(w).quantile(0.25))
    c = float(np.quantile(w, 0.75) - np.quantile(w, 0.25))
    print(f"  np.percentile {a!r}")
    print(f"  Series.quantile {b!r}   same bits: {a == b}")
    print(f"  np.quantile {c!r}   same bits: {a == c}")

    print()
    print("is the bit-equality PER QUANTILE, or a cancellation in the")
    print("difference? pandas' rolling quartile vs np.percentile, alone:")
    def single(close, q, length=LENGTH):
        r = _ret(close)
        rr = r.to_numpy()
        roll = r.rolling(length, min_periods=length).quantile(q)
        out = np.full(rr.size, np.nan)
        for t in range(length, rr.size):
            win = rr[t - length + 1:t + 1]
            if np.isfinite(win).all():
                out[t] = np.percentile(win, 100.0 * q)
        return roll, Series(out, index=close.index)

    total = agreed = 0
    for frame in FRAMES:
        close = FRAMES[frame]()
        for q in (Q_LOW, Q_HIGH):
            roll, one = single(close, q)
            _, shared, same, d = _agree(roll, one)
            u = _ulps(roll, one)
            total += shared
            agreed += same
            print(f"  {frame:14s} q{q:4.2f}  bit-equal {same} of {shared}"
                  f"  max ulp {u.max():.2f}  max |diff| {d:.3e}")
    print(f"  TOTAL single-quartile readings {agreed} of {total} bit-equal")

    print()
    print("the same at other lengths, on the walk")
    close = _walk()
    tot2 = ag2 = 0
    for length in (MIN_LENGTH, 5, 20, 21, 250):
        for q in (Q_LOW, Q_HIGH):
            roll, one = single(close, q, length)
            _, shared, same, d = _agree(roll, one)
            tot2 += shared
            ag2 += same
            print(f"  length {length:4d} q{q:4.2f}  bit-equal {same}"
                  f" of {shared}  max |diff| {d:.3e}")
    print(f"  TOTAL {ag2} of {tot2} bit-equal")
    print()
    print("WHICH branch does numpy take? Probed, not recalled: for each")
    print("quartile, compare np.percentile against BOTH spellings over")
    print("20,000 random 60-draw windows.")
    rng = np.random.default_rng(907)
    for q, k, f in ((Q_LOW, 14, 0.75), (Q_HIGH, 44, 0.25)):
        same_pandas = same_numpy = 0
        for _ in range(20000):
            s = np.sort(rng.normal(0.0, 0.01, LENGTH))
            a, b = s[k], s[k + 1]
            d = b - a
            pandas_form = a + d * f
            numpy_form = b - d * (1.0 - f)
            got = np.percentile(s, 100.0 * q)
            same_pandas += int(got == pandas_form)
            same_numpy += int(got == numpy_form)
        print(f"  q{q:4.2f} (frac {f}):  np.percentile == `a + d*f`"
              f" {same_pandas:6d}/20000,  == `b - d*(1-f)`"
              f" {same_numpy:6d}/20000")
    print("  t = frac, so the `b - d*(1-t)` branch is the one taken at")
    print("  t >= 0.5 -- i.e. at q0.25 here, and NOT at q0.75, whose")
    print("  spelling is already identical to pandas'. The q0.25 agreement")
    print("  above is therefore the only non-trivial half of A2.")

    print()
    print("so how often do the two SPELLINGS disagree on the windows this")
    print("column actually sees? (the question that decides whether A2's")
    print("bit-equality is robust or lucky)")
    for frame in FRAMES:
        rr = _ret(FRAMES[frame]()).to_numpy()
        diff_lo = diff_hi = n = 0
        for t in range(LENGTH, rr.size):
            w = rr[t - LENGTH + 1:t + 1]
            if not np.isfinite(w).all():
                continue
            s = np.sort(w)
            n += 1
            a, b = s[14], s[15]
            diff_lo += int((a + (b - a) * 0.75) != (b - (b - a) * 0.25))
            a, b = s[44], s[45]
            diff_hi += int((a + (b - a) * 0.25) != (b - (b - a) * 0.75))
        print(f"  {frame:14s} of {n:5d} windows: q0.25 spellings differ"
              f" {diff_lo:4d}, q0.75 {diff_hi:4d}")
    print("  ⚠ Where they DO differ, pandas and numpy would differ too, so")
    print("  A2's zero is a property of these frames and not a theorem.")


# ===================================================================== A3


def section_A3():
    _head("A3  against an EXACT rational oracle, in ulps")
    print(f"{'frame':14s} {'shared':>7s} {'bit-equal':>10s} {'max ulp':>8s}"
          f" {'mean ulp':>9s} | {'numpy max':>9s} {'numpy mean':>10s}")
    for name in FRAMES:
        close = FRAMES[name]()
        mod = tf_iqr_ret_60(close)
        src = _source_windowed(close)
        orc = _exact(close)
        um, us = _ulps(mod, orc), _ulps(src, orc)
        _, shared, same, _ = _agree(mod, orc)
        print(f"{name:14s} {shared:7d} {same:10d} {um.max():8.2f}"
              f" {um.mean():9.4f} | {us.max():9.2f} {us.mean():10.4f}")

    print()
    print("the two quartiles are EXACT binary fractions, unlike 0.05")
    for q in (0.25, 0.75, 0.05):
        print(f"  Fraction({q}) = {Fraction(q)}")


# ===================================================================== A4


def section_A4():
    _head("A4  what the column reads: four of the 60 returns, nothing else")
    for length in (MIN_LENGTH, 5, 20, 21, 60, 250):
        i_hi, i_lo = Q_HIGH * (length - 1), Q_LOW * (length - 1)
        print(f"  length {length:4d}  0.75*(n-1) = {i_hi!r:8s} -> s[{int(i_hi)}]"
              f" frac {i_hi % 1!r:6s}   0.25*(n-1) = {i_lo!r:8s}"
              f" -> s[{int(i_lo)}] frac {i_lo % 1!r}")
    print("  at the default that is ranks 15, 16, 45 and 46 of 60 (1-based)")

    print()
    print("moving the OTHER 56 returns, keeping every rank: bit-identical?")
    rng = np.random.default_rng(31)
    base = np.sort(rng.normal(0.0, 0.02, LENGTH))
    # Ranks read at length 60 (0-based): 14, 15, 44, 45.
    read = (14, 15, 44, 45)
    spread = base.copy()
    for i in range(LENGTH):
        if i in read:
            continue
        # Push each unread value far away, in its own direction, keeping the
        # sort order: below rank 14 goes down, above rank 45 goes up, and
        # the middle is squeezed between s[15] and s[44].
        if i < 14:
            spread[i] = base[14] - (14 - i) * 7.0
        elif i > 45:
            spread[i] = base[45] + (i - 45) * 7.0
        else:
            t = (i - 15) / (44 - 15)
            spread[i] = base[15] + t * (base[44] - base[15])
    print(f"  ranks still sorted: {bool(np.all(np.diff(spread) >= 0))}")
    hi = base[44] + (base[45] - base[44]) * 0.25
    lo = base[14] + (base[15] - base[14]) * 0.75
    closed = hi - lo
    for label, w in (("base", base), ("spread", spread)):
        v = float(Series(w).quantile(0.75) - Series(w).quantile(0.25))
        print(f"  {label:7s} np/Series.quantile {v!r}")
    for label, w in (("base", base), ("spread", spread)):
        s = np.sort(w)
        v = (s[44] + (s[45] - s[44]) * 0.25) - (s[14] + (s[15] - s[14]) * 0.75)
        print(f"  {label:7s} pandas blend      {v!r}"
              f"   == closed form: {v == closed}")

    print()
    print("coarseness: distinct values over the fired bars")
    for name, make in FRAMES.items():
        v = tf_iqr_ret_60(make()).dropna()
        print(f"  {name:14s} fired {len(v):5d}  distinct {len(set(v)):5d}"
              f"  min {v.min():.6e}  max {v.max():.6e}")


# ===================================================================== A5


def section_A5():
    _head("A5  the readings the source's line leaves open, priced")
    close = _walk()
    mod = tf_iqr_ret_60(close)

    print("1. SIMPLE returns (the prototype's `ret`) vs LOG returns")
    lr = np.log(close) - np.log(close.shift(1))
    log_iqr = (lr.rolling(LENGTH, min_periods=LENGTH).quantile(Q_HIGH)
               - lr.rolling(LENGTH, min_periods=LENGTH).quantile(Q_LOW))
    print(f"   rho {_spearman(mod, log_iqr):.6f}   max |diff|"
          f" {float((mod - log_iqr).abs().max()):.3e}")
    print("   ⚠ a quantile commutes with a monotone transform but a"
          " DIFFERENCE of two does not,")
    print("   so unlike ts_q05_60 the ranks are NOT preserved exactly.")

    print()
    print("2. interpolation: the alternatives are different columns")
    r = _ret(close)
    for how in ("lower", "higher", "nearest", "midpoint"):
        roll = r.rolling(LENGTH, min_periods=LENGTH)
        alt = (roll.quantile(Q_HIGH, interpolation=how)
               - roll.quantile(Q_LOW, interpolation=how))
        print(f"   {how:9s} rho {_spearman(mod, alt):.6f}"
              f"   max |diff| {float((mod - alt).abs().max()):.3e}")
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    dflt = roll.quantile(Q_HIGH) - roll.quantile(Q_LOW)
    lin = (roll.quantile(Q_HIGH, interpolation="linear")
           - roll.quantile(Q_LOW, interpolation="linear"))
    print(f"   default IS linear: {bool(dflt.equals(lin))}")

    print()
    print("3. 60 RETURNS (61 closes) vs 60 CLOSES (59 returns)")
    off = (r.rolling(LENGTH - 1, min_periods=LENGTH - 1).quantile(Q_HIGH)
           - r.rolling(LENGTH - 1, min_periods=LENGTH - 1).quantile(Q_LOW))
    print(f"   rho {_spearman(mod, off):.6f}   max |diff|"
          f" {float((mod - off).abs().max()):.3e}"
          f"   first fired bar {int(off.notna().to_numpy().argmax())}"
          f" vs {int(mod.notna().to_numpy().argmax())}")

    print()
    print("4. the SPREAD of returns, not of the price LEVEL")
    lvl = (close.rolling(LENGTH, min_periods=LENGTH).quantile(Q_HIGH)
           - close.rolling(LENGTH, min_periods=LENGTH).quantile(Q_LOW))
    print(f"   rho {_spearman(mod, lvl):.6f}  (and the level form is not"
          f" scale-free at all)")
    print(f"   same, as a RATIO to the close: rho"
          f" {_spearman(mod, lvl / close):.6f}")

    print()
    print("5. the other quartile pairs: genuinely different columns")
    for ql, qh in ((0.10, 0.90), (0.05, 0.95), (0.20, 0.80), (0.30, 0.70),
                   (0.40, 0.60)):
        alt = (r.rolling(LENGTH, min_periods=LENGTH).quantile(qh)
               - r.rolling(LENGTH, min_periods=LENGTH).quantile(ql))
        print(f"   q{ql:.2f}..q{qh:.2f}  rho {_spearman(mod, alt):.6f}"
              f"   max |diff| {float((mod - alt).abs().max()):.3e}")

    print()
    print("6. TSFEL applies `interq_range` to the SIGNAL; the screen applies")
    print("   it to the RETURNS. The signal form, for the record:")
    print(f"   rho vs the price-level form {_spearman(mod, lvl):.6f}")


# ===================================================================== A6


def section_A6():
    _head("A6  the screen prototype")
    print(f"{'frame':14s} {'masks':6s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>12s}")
    for name, make in FRAMES.items():
        close = make()
        masks, shared, same, d = _agree(tf_iqr_ret_60(close),
                                        _prototype(close))
        print(f"{name:14s} {str(masks):6s} {shared:7d} {same:10d} {d:12.3e}")

    print()
    print("where the two part company: the guards")
    for label, bad in (("inf", np.inf), ("zero", 0.0), ("subnormal", 1e-310),
                       ("negative", -100.0), ("nan", np.nan)):
        close = _walk(400)
        close.iloc[200] = bad
        m = int(tf_iqr_ret_60(close).notna().sum())
        p = int(_prototype(close).notna().sum())
        print(f"  {label:10s} module fires {m:4d}   prototype fires {p:4d}")


# ====================================================================== B


OFFSETS = range(120, N, 40)     # 35 offsets, past the 60-bar warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
BAD_OFFSETS = range(120, N, 120)        # 12 offsets, >= length + 1 apart


def _caught(fn, close, other, offsets=OFFSETS, **kwargs):
    """Offsets J at which replacing every close from bar J on moves a bar
    BEFORE J -- which a causal column cannot do."""
    base = fn(close, **kwargs)
    hits = []
    for j in offsets:
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


def section_B():
    _head("B  the causality sweep on the real module")
    for name, (close, other) in PAIRS.items():
        hits = _caught(tf_iqr_ret_60, close, other)
        print(f"  {name:14s} leaked {len(hits):3d} of"
              f" {len(list(OFFSETS)):3d} offsets   {hits}")
    print()
    close, other = PAIRS["walk"]
    for length in (MIN_LENGTH, 5, 250):
        hits = _caught(tf_iqr_ret_60, close, other, length=length)
        first = int(tf_iqr_ret_60(close, length=length)
                    .notna().to_numpy().argmax())
        print(f"  length {length:4d}      leaked {len(hits):3d} of"
              f" {len(list(OFFSETS)):3d}   first fired bar {first}")
    print()
    print("prefix truncation (necessary, not sufficient -- see the mutants)")
    full = tf_iqr_ret_60(PAIRS["walk"][0])
    bad = 0
    for j in OFFSETS:
        pre = tf_iqr_ret_60(PAIRS["walk"][0].iloc[:j])
        a, b = full.iloc[:j], pre
        if not (a.isna() == b.isna()).all() or not bool(
                (a[a.notna()] == b[b.notna()]).all()):
            bad += 1
    print(f"  prefixes that differ: {bad} of {len(list(OFFSETS))}")


# ====================================================================== M


import importlib                                               # noqa: E402
import types                                                   # noqa: E402

_REAL = importlib.import_module("pandas_ta.statistics.tf_iqr_ret_60")

WINDOW_BLOCK = (
    "    hi = r.rolling(length, min_periods=length).quantile(Q_HIGH)\n"
    "    lo = r.rolling(length, min_periods=length).quantile(Q_LOW)")
BACK_DATE_TWO = ("    iqr = hi - lo", "    iqr = (hi - lo).shift(-2)")
BACK_DATE_FULL = ("    iqr = hi - lo",
                  "    iqr = (hi - lo).shift(-(length - 1))")
FORWARD_RETURN = ("        r = px / px.shift(1) - 1.0",
                  "        r = px.shift(-1) / px - 1.0")
CENTERED_WINDOW = (
    WINDOW_BLOCK,
    "    hi = r.rolling(length, min_periods=length, center=True)"
    ".quantile(Q_HIGH)\n"
    "    lo = r.rolling(length, min_periods=length, center=True)"
    ".quantile(Q_LOW)")
ROLLED_WINDOW = (
    WINDOW_BLOCK,
    "    rr = r.shift(-(length // 2))\n"
    "    hi = rr.rolling(length, min_periods=length).quantile(Q_HIGH)\n"
    "    lo = rr.rolling(length, min_periods=length).quantile(Q_LOW)")
#: The NaN mask's own index. A real look-ahead -- bar T's mask would read
#: whether bar T+1's return is finite -- and DEAD on a clean frame, where
#: every return but the first is finite.
FORWARD_MASK = ("    r = r.where(np.isfinite(r))",
                "    r = r.where(np.isfinite(r).shift(-1, fill_value=True))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "centered_window": CENTERED_WINDOW,
    "rolled_window": ROLLED_WINDOW,
}


def _load_mutant(old, new):
    with open(_REAL.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_tf_iqr_ret_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _bad_close_frame(seed=23):
    c = _walk(N, seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = np.nan
    return Series(c)


def section_M():
    _head("M  the mutants")
    n = len(list(OFFSETS))
    print(f"{'mutant':17s} {'frame':14s} {'live':5s} {'caught':>7s} / {n}")
    for name, edit in MUTANTS.items():
        mod = _load_mutant(*edit)
        for frame, (close, other) in PAIRS.items():
            live = not mod.tf_iqr_ret_60(close).equals(tf_iqr_ret_60(close))
            hits = _caught(mod.tf_iqr_ret_60, close, other)
            print(f"{name:17s} {frame:14s} {str(live):5s} {len(hits):7d}")

    print()
    print("the sixth: the NaN mask's own index, DEAD on a clean frame")
    mod = _load_mutant(*FORWARD_MASK)
    for frame, (close, other) in PAIRS.items():
        same = mod.tf_iqr_ret_60(close).equals(tf_iqr_ret_60(close))
        hits = _caught(mod.tf_iqr_ret_60, close, other)
        print(f"  {frame:14s} bit-identical to the real module {same}"
              f"   caught {len(hits)} of {n}")

    print()
    print("the DESIGNED probe: a bad close at every swept offset")
    close, other = _bad_close_frame(), _walk(N, 97)
    nb = len(list(BAD_OFFSETS))
    print(f"  the real module fires {int(tf_iqr_ret_60(close).notna().sum())}"
          f" bars and leaks"
          f" {len(_caught(tf_iqr_ret_60, close, other, BAD_OFFSETS))} of {nb}")
    hits = _caught(mod.tf_iqr_ret_60, close, other, BAD_OFFSETS)
    print(f"  the mask mutant is caught {len(hits)} of {nb}")
    base = mod.tf_iqr_ret_60(close)
    moved = []
    for j in BAD_OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        a, b = base.iloc[:j], mod.tf_iqr_ret_60(p).iloc[:j]
        changed = (a.isna() != b.isna()) | ((a - b).abs().fillna(0.0) > 0.0)
        moved.append((j, np.flatnonzero(changed.to_numpy()).tolist()))
    print(f"  and the bars it moves are exactly J-1:"
          f" {all(m == [j - 1] for j, m in moved)}")


# ====================================================================== C


def section_C():
    _head("C  reachability")
    print(f"{'frame':14s} {'n':>5s} {'fired':>6s} {'distinct':>9s}"
          f" {'min':>13s} {'median':>13s} {'max':>13s} {'>=0':>5s}")
    for name, make in FRAMES.items():
        close = make()
        v = tf_iqr_ret_60(close)
        d = v.dropna()
        print(f"{name:14s} {len(close):5d} {len(d):6d} {len(set(d)):9d}"
              f" {d.min():13.6e} {d.median():13.6e} {d.max():13.6e}"
              f" {str(bool((d >= 0).all())):>5s}")

    print()
    print("the degenerate frames")
    for label, close in (("flat", _flat()), ("ladder", _ladder()),
                         ("quiet 1e-6", _quiet())):
        d = tf_iqr_ret_60(close).dropna()
        print(f"  {label:11s} fired {len(d):5d}  distinct {len(set(d)):4d}"
              f"  min {d.min():.6e}  max {d.max():.6e}")

    print()
    print("first fired bar, and a frame of exactly `length` + 1 closes")
    col = tf_iqr_ret_60(_walk())
    print(f"  first fired bar {int(col.notna().to_numpy().argmax())}"
          f"   (length = {LENGTH}, so `length` + 1 closes)")
    print(f"  {LENGTH + 1} closes -> fires"
          f" {int(tf_iqr_ret_60(_walk(n=LENGTH + 1)).notna().sum())}")
    print(f"  {LENGTH} closes -> {tf_iqr_ret_60(_walk(n=LENGTH))!r}")

    print()
    print("the two-point frame: numerically a CONSTANT, which is why Gate D")
    print("reads the relative difference there and not the Spearman")
    v = sorted(set(tf_iqr_ret_60(_two_point()).dropna()))
    print(f"  {len(v)} distinct doubles, span {v[-1] - v[0]:.3e}"
          f" ({(v[-1] - v[0]) / v[0]:.3e} relative)")
    print(f"  {[repr(x) for x in v]}")

    print()
    print("the statistic is SIGN-SYMMETRIC: negating every return leaves it")
    print("unchanged in exact arithmetic (q75(-x) = -q25(x)), so a crash and")
    print("a melt-up of the same shape read the same.")
    rng = np.random.default_rng(41)
    r = np.clip(rng.standard_t(3.0, N) * 0.01, -0.5, 0.5)
    up, down = _from_returns(r), _from_returns(-r)
    a, b = tf_iqr_ret_60(up), tf_iqr_ret_60(down)
    masks, shared, same, d = _agree(a, b)
    print(f"  masks {masks}  shared {shared}  bit-equal {same}"
          f"  max |diff| {d:.3e}  rho {_spearman(a, b):.6f}")
    # Windows of EXACT doubles, where the price path cannot reintroduce
    # rounding, isolate the symmetry from the frame construction.
    hits, worst = 0, 0.0
    for k in range(300):
        w = rng.standard_normal(LENGTH)
        s, t = np.sort(w), np.sort(-w)
        f = (lambda z: (z[44] + (z[45] - z[44]) * 0.25)
             - (z[14] + (z[15] - z[14]) * 0.75))
        hits += int(f(s) == f(t))
        worst = max(worst, abs(f(s) - f(t)))
    print(f"  300 exact windows: {hits} bit-equal under negation,"
          f" worst |diff| {worst:.3e}")

    print()
    print("the search for a NEGATIVE reading: tie-heavy windows")
    rng = np.random.default_rng(77)
    worst, trials, neg = 0.0, 0, 0
    for k in range(400):
        # Windows built to put ranks 15..46 (indices 14..45) on ONE value,
        # the only arrangement in which the two blends can round into each
        # other.
        base = rng.normal(0.0, 0.01)
        w = np.r_[np.sort(rng.normal(0.0, 0.01, 14)) - 1.0,
                  np.full(32, base),
                  np.sort(rng.normal(0.0, 0.01, 14)) + 1.0]
        s = np.sort(w)
        v = (s[44] + (s[45] - s[44]) * 0.25) - (s[14] + (s[15] - s[14]) * 0.75)
        trials += 1
        neg += int(v < 0.0)
        worst = min(worst, v)
    print(f"  {trials} all-tied-middle windows: {neg} negative,"
          f" worst {worst!r}")
    rng = np.random.default_rng(78)
    neg2, worst2 = 0, 0.0
    for k in range(2000):
        w = rng.normal(0.0, 1e-8, LENGTH)
        w = np.round(w / 1e-9) * 1e-9        # heavy ties at a coarse grid
        s = np.sort(w)
        v = (s[44] + (s[45] - s[44]) * 0.25) - (s[14] + (s[15] - s[14]) * 0.75)
        neg2 += int(v < 0.0)
        worst2 = min(worst2, v)
    print(f"  2000 grid-rounded windows: {neg2} negative, worst {worst2!r}")


# ====================================================================== D


def section_D():
    _head("D  scale-freedom")
    print("x8 / x64: BIT-identical by construction (8a/8b is the double a/b)")
    print(f"{'frame':14s} {'x8 masks':9s} {'x8 bit-equal':>13s}"
          f" {'x64 masks':10s} {'x64 bit-equal':>14s}")
    for name, make in FRAMES.items():
        close = make()
        row = [name]
        for k in (8.0, 64.0):
            masks, shared, same, _ = _agree(tf_iqr_ret_60(close),
                                            tf_iqr_ret_60(close * k))
            row += [str(masks), f"{same} of {shared}"]
        print(f"{row[0]:14s} {row[1]:9s} {row[2]:>13s} {row[3]:10s}"
              f" {row[4]:>14s}")

    print()
    print("x8 at other lengths, and at extreme price levels, on the walk")
    close = _walk()
    for length in (MIN_LENGTH, 5, 20, 250):
        masks, shared, same, _ = _agree(
            tf_iqr_ret_60(close, length=length),
            tf_iqr_ret_60(close * 8.0, length=length))
        print(f"  length {length:4d}  masks {masks}  bit-equal"
              f" {same} of {shared}")
    for price in (1e-6, 1e6, 1e100):
        base = close * (price / float(close.iloc[0]))
        masks, shared, same, _ = _agree(tf_iqr_ret_60(base),
                                        tf_iqr_ret_60(base * 8.0))
        print(f"  price {price:7.0e}  masks {masks}  bit-equal"
              f" {same} of {shared}")

    print()
    print("x10 / x3.7 / x0.1 / x1.0000001: masks plus a tolerance")
    print("⚠ `max ulp` is the same distance as `max |diff|`, expressed in")
    print("units of the last place of the COLUMN's own value -- the honest")
    print("unit for 'how far apart are these two readings'.")
    print(f"{'frame':14s} {'k':>10s} {'masks':6s} {'max |diff|':>12s}"
          f" {'max rel':>11s} {'max ulp':>8s} {'rho':>10s}")
    for name in ("walk", "tick-rounded", "heavy-tailed", "two-point"):
        close = FRAMES[name]()
        for k in (10.0, 3.7, 0.1, 1.0000001):
            a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(close * k)
            masks, shared, same, d = _agree(a, b)
            print(f"{name:14s} {k:10.7f} {str(masks):6s} {d:12.3e}"
                  f" {_max_rel(a, b):11.3e} {_ulps(b, a).max():8.1f}"
                  f" {_spearman(a, b):10.6f}")

    print()
    print("a level SHIFT is NOT invariant -- the anti-vacuity check")
    close = _walk()
    for shift in (1.0, 50.0, 1000.0):
        a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(close + shift)
        m = a.notna() & b.notna()
        print(f"  +{shift:7.1f}  bars moved {int((a[m] != b[m]).sum())}"
              f" of {int(m.sum())}   max |diff| {float((a[m] - b[m]).abs().max()):.3e}")

    print()
    print("0 < fires < n, and the column is not constant")
    for name, make in FRAMES.items():
        v = tf_iqr_ret_60(make())
        d = v.dropna()
        print(f"  {name:14s} 0 < {len(d)} < {len(v)}:"
              f" {0 < len(d) < len(v)}   distinct {len(set(d))}")


# ====================================================================== G


def section_G():
    _head("G  the guards, and the floor this module does NOT have")
    print("a bad close empties the windows it sits in, and nothing earlier")
    print(f"{'value':12s} {'pos':>5s} {'fired':>6s} {'emptied':>8s}"
          f" {'moved before':>13s}")
    base_frame = _walk(400)
    base = tf_iqr_ret_60(base_frame)
    for bad in (np.nan, np.inf, -np.inf, 0.0, -100.0, 1e-310):
        for pos in (0, 1, LENGTH, 200, 399):
            close = base_frame.copy()
            close.iloc[pos] = bad
            v = tf_iqr_ret_60(close)
            emptied = int(base.notna().sum()) - int(v.notna().sum())
            before = int(((base.iloc[:pos] != v.iloc[:pos])
                          & base.iloc[:pos].notna()).sum())
            print(f"{bad!r:12s} {pos:5d} {int(v.notna().sum()):6d}"
                  f" {emptied:8d} {before:13d}")

    print()
    print("an OVERFLOWING ratio: 1e-300 then 1e50")
    close = _walk(400)
    close.iloc[200] = 1e-300
    close.iloc[201] = 1e50
    v = tf_iqr_ret_60(close)
    print(f"  fired {int(v.notna().sum())} vs {int(base.notna().sum())}"
          f"  emptied {int(base.notna().sum()) - int(v.notna().sum())}")

    print()
    print("what does pandas' own rolling.quantile DO with an infinity in")
    print("the window? (the question the `where(isfinite)` line answers)")
    w = np.arange(1.0, LENGTH + 1.0)
    for label, win in (("no inf", w.copy()),
                       ("one +inf", np.r_[np.inf, w[1:]]),
                       ("one -inf", np.r_[-np.inf, w[1:]]),
                       ("sixteen +inf", np.r_[np.full(16, np.inf), w[16:]])):
        s = Series(win)
        roll = s.rolling(LENGTH, min_periods=LENGTH)
        q75 = float(roll.quantile(Q_HIGH).iloc[-1])
        q25 = float(roll.quantile(Q_LOW).iloc[-1])
        print(f"  {label:14s} q75 {q75!r:10s} q25 {q25!r:10s}"
              f" q75 - q25 {q75 - q25!r}")
    print("  so pandas blanks the WHOLE window on a single infinity, at")
    print("  both quartiles -- which means the module's own mask line is")
    print("  defence in depth rather than the thing that does the work.")

    print()
    print("what the `r.where(np.isfinite(r))` line changes, measured by")
    print("deleting it (a mutant) and comparing")
    nomask = _load_mutant("    r = r.where(np.isfinite(r))", "    r = r")
    probes = {}
    base = _walk(400)
    probes["clean walk"] = base
    over = base.copy()
    over.iloc[200], over.iloc[201] = 1e-300, 1e50
    probes["overflowing ratio"] = over
    cyc = Series(np.tile([1e308, 1e-300, 1e8], 30))
    probes["1e308 cycle"] = cyc
    for label, close in probes.items():
        with np.errstate(over="ignore"):
            a, b = tf_iqr_ret_60(close), nomask.tf_iqr_ret_60(close)
        masks, shared, same, d = _agree(a, b)
        print(f"  {label:20s} masks equal {str(masks):5s} shared {shared:4d}"
              f"  bit-equal {same:4d}  max |diff| {d:.3e}")

    print()
    print("an UNDERFLOWING ratio is KEPT: 1e308 then 1e-300 is exactly -1.0")
    r = 1e-300 / 1e308 - 1.0
    print(f"  1e-300 / 1e308 - 1 = {r!r}   is finite: {np.isfinite(r)}")
    cyc = Series(np.tile([1e308, 1e-300, 1e8], 30))
    v = tf_iqr_ret_60(cyc)
    d = v.dropna()
    print(f"  a 90-bar cycle [1e308, 1e-300, 1e8]: fires {len(d)},"
          f" distinct {sorted(set(d))[:3]}")
    print("  so the column is UNBOUNDED ABOVE and 1e308 is reachable.")

    print()
    print("can the SUBTRACTION overflow? Only if q75 - q25 exceeds the")
    print("largest double. q25 is a return, so it is > -1 whenever both")
    print("closes are positive and normal -- which the guard enforces -- so")
    print("the gap is at most max(return) + 1, and adding 1 to a number of")
    print("that size is a no-op. Probed BOTH ways -- the blend arithmetic at")
    print("its worst corner, and a frame that actually reaches 1e308:")
    mx = float(np.finfo(float).max)
    # The worst corner the guard allows: every order statistic the column
    # reads is either the largest double or the smallest return there is.
    hi = mx + (mx - mx) * 0.25
    lo = -1.0 + (-1.0 - -1.0) * 0.75
    print(f"  q75 = {hi!r}  q25 = {lo!r}  q75 - q25 = {hi - lo!r}"
          f"  finite: {np.isfinite(hi - lo)}")
    print(f"  and the widest SPAN a blend can see is"
          f" {mx - -1.0!r}, which is finite:"
          f" {np.isfinite(mx - -1.0)} -- because a return is > -1")
    probe = Series(np.tile([1e-300, 1.5e8, 1e-300, 1.0], 25))
    r2 = _ret(probe)
    v = tf_iqr_ret_60(probe)
    print(f"  the frame probe: largest finite return"
          f" {float(r2.max()):.6e}, fires {int(v.notna().sum())}"
          f" of {len(v)}, max {float(v.max()):.6e}, any inf:"
          f" {bool(np.isinf(v.dropna()).any())}")

    print()
    print("NO dispersion floor: the exact oracle on the degenerate frames")
    for label, close in (("flat", _flat()), ("ladder", _ladder()),
                         ("quiet 1e-6", _quiet())):
        v = tf_iqr_ret_60(close)
        orc = _exact(close, LENGTH)
        d = v.dropna()
        u = _ulps(v, orc)
        print(f"  {label:11s} fired {len(d):5d}  distinct {len(set(d)):4d}"
              f"  max ulp {u.max() if u.size else float('nan'):.2f}"
              f"  values {sorted(set(d))[:2]}")
    print()
    print("how many distinct RETURN doubles each degenerate frame holds")
    for label, close in (("flat", _flat()), ("ladder", _ladder()),
                         ("quiet 1e-6", _quiet())):
        r = _ret(close).dropna()
        u = sorted(set(r))
        print(f"  {label:11s} {len(u)} distinct returns,"
              f" span {u[-1] - u[0]:.3e}, first two {u[:2]}")

    print()
    print("  the siblings' absolute 4096-ulp return-range floor would empty:")
    degenerate = (("flat", _flat()), ("ladder", _ladder()),
                  ("quiet 1e-6", _quiet()))
    for label, close in degenerate + tuple(
            (name, make()) for name, make in FRAMES.items()):
        r = _ret(close)
        rng_ = (r.rolling(LENGTH, min_periods=LENGTH).max()
                - r.rolling(LENGTH, min_periods=LENGTH).min())
        thr = 4096 * np.finfo(float).eps
        fired = tf_iqr_ret_60(close).notna()
        n_empty = int((fired & (rng_ <= thr)).sum())
        print(f"    {label:11s} {n_empty} of {int(fired.sum())}"
              f"   window return range: smallest"
              f" {float(rng_[fired].min()):.3e}  widest"
              f" {float(rng_[fired].max()):.3e}")

    print()
    print("no warning is raised on bad closes")
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        close = _walk(400)
        close.iloc[100] = np.inf
        close.iloc[150] = 0.0
        close.iloc[200] = -5.0
        close.iloc[250] = 1e-310
        tf_iqr_ret_60(close)
    print("  clean")


# ====================================================================== O


def _comparators(close):
    """Every comparator keyed by the column's OWN `.name`, so a label here
    cannot drift from the column it names (an earlier draft typed
    `TS_AGGAC_60_5` for a column whose default `maxlag` is 10)."""
    high, low = _ohlc(close)
    out = {}
    for series in (
        ts_q05_60(close),
        ts_kurt_60(close),
        ts_ac1_60(close),
        ts_aggac_60(close),
        lot_zeroret_60(close),
        ts_imq_20(close),
        ts_strike_20(close),
        tf_zero_cross_20(close),
        tf_centroid_20(close),
        tf_spec_entropy_64(close),
        tf_dfa_100(close),
        tf_higuchi_30(close),
        natr(high, low, close, length=LENGTH),
        ui(close, length=LENGTH),
        quantile(close, length=LENGTH, q=Q_HIGH),
        mad(close, length=LENGTH),
        stdev(close, length=LENGTH),
    ):
        if series is None:
            continue
        if not isinstance(series, Series):
            series = series.iloc[:, 0]
        out[str(series.name)] = series
    # The return standard deviation of the SAME window: not a fork column,
    # but the textbook alternative to an IQR and so the one number a reader
    # will want most.
    out["ret sd (not a column)"] = _ret(close).rolling(
        LENGTH, min_periods=LENGTH).std()
    return out


def section_O():
    _head("O  overlap: what the column restates and what it does not")
    names = sorted(_comparators(_walk()))
    rows = {}
    for name, make in FRAMES.items():
        close = make()
        mod = tf_iqr_ret_60(close)
        comp = _comparators(close)
        for label in names:
            rows.setdefault(label, []).append(_spearman(mod, comp[label]))

    print(f"{'comparator':24s} {'min rho':>9s} {'max rho':>9s}"
          f" {'median |rho|':>13s} {'max |rho|':>10s}")
    order = sorted(names, key=lambda L: -np.nanmax(np.abs(rows[L])))
    for label in order:
        v = np.array(rows[label], dtype=float)
        print(f"{label:24s} {np.nanmin(v):9.4f} {np.nanmax(v):9.4f}"
              f" {np.nanmedian(np.abs(v)):13.4f} {np.nanmax(np.abs(v)):10.4f}")

    print()
    print("pooled Spearman over the concatenated frames")
    pooled = {}
    for label in names:
        a, b = [], []
        for make in FRAMES.values():
            close = make()
            mod = tf_iqr_ret_60(close)
            comp = _comparators(close)[label]
            m = mod.notna() & comp.notna()
            a.append(mod[m].to_numpy())
            b.append(comp[m].to_numpy())
        pooled[label] = float(Series(np.concatenate(a)).corr(
            Series(np.concatenate(b)), method="spearman"))
    for label in sorted(pooled, key=lambda L: -abs(pooled[L])):
        print(f"  {label:24s} pooled {pooled[label]:9.4f}")

    print()
    print("per-frame detail, EVERY comparator, in the frame order")
    print(f"  {'(frames)':24s} " + ", ".join(f"{n:>8s}"[:8]
                                             for n in FRAMES))
    for label in order:
        v = ", ".join("     nan" if np.isnan(x) else f"{x:8.4f}"
                      for x in rows[label])
        print(f"  {label:24s} {v}")

    print()
    print("WHY is a rho undefined? Measured, not inferred: the distinct")
    print("values each comparator takes, for the ones that go NaN anywhere.")
    for label in order:
        if not any(np.isnan(x) for x in rows[label]):
            continue
        for name, make in FRAMES.items():
            comp = _comparators(make())[label].dropna()
            print(f"  {label:20s} {name:14s} {len(set(comp)):5d} distinct"
                  f"  values {sorted(set(comp))[:3]}")

    print()
    print("which frame holds each comparator's max |rho|, and where rho is")
    print("UNDEFINED (a constant comparator has no rank correlation)")
    names_list = list(FRAMES)
    for label in order:
        v = np.array(rows[label], dtype=float)
        undefined = [names_list[i] for i in range(len(v)) if np.isnan(v[i])]
        if np.all(np.isnan(v)):
            print(f"  {label:24s} undefined on every frame")
            continue
        at = names_list[int(np.nanargmax(np.abs(v)))]
        print(f"  {label:24s} max |rho| {np.nanmax(np.abs(v)):.4f} on"
              f" {at:14s} defined on {len(v) - len(undefined)} of {len(v)}"
              f"{'' if not undefined else '  undefined: ' + ','.join(undefined)}")


# ====================================================================== S


def section_S():
    _head("S  the statistic itself")
    print("the level to expect, from 20,000 INDEPENDENT windows of 60 draws")
    rng = np.random.default_rng(101)
    for label, draw in (
            ("gaussian", lambda: rng.standard_normal((20000, LENGTH))),
            ("student-t(2)", lambda: rng.standard_t(2.0, (20000, LENGTH))),
            ("exponential", lambda: rng.standard_exponential(
                (20000, LENGTH)))):
        W = draw()
        s = np.sort(W, axis=1)
        v = ((s[:, 44] + (s[:, 45] - s[:, 44]) * 0.25)
             - (s[:, 14] + (s[:, 15] - s[:, 14]) * 0.75))
        print(f"  {label:14s} mean {v.mean():8.4f}  sd {v.std():8.4f}"
              f"  min {v.min():8.4f}  max {v.max():8.4f}")
    print("  the gaussian's own interquartile range is"
          f" {2 * 0.6744897501960817:.4f} sigma")

    print()
    print("autocorrelation of the column (a slow state, not an event flag)")
    v = tf_iqr_ret_60(_walk()).dropna()
    for lag in (1, 5, 30, 60, 120):
        print(f"  lag {lag:4d}  {float(v.autocorr(lag)):8.4f}")

    print()
    print("one extreme bar moves exactly `length` bars")
    print("  the factor is 0.5, a POWER OF TWO, so every return after bar")
    print("  700 is the same double and exactly ONE return changes.")
    close = _walk()
    spiked = close.copy()
    spiked.iloc[700:] = spiked.iloc[700:] * 0.5     # a -50% bar at 700
    a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(spiked)
    m = a.notna() & b.notna()
    moved = np.flatnonzero((a[m] != b[m]).to_numpy())
    idx = a[m].index.to_numpy()[moved]
    ra, rb = _ret(close), _ret(spiked)
    rm = ra.notna() & rb.notna()
    print(f"  returns that changed {int((ra[rm] != rb[rm]).sum())}"
          f" of {int(rm.sum())}")
    print(f"  bars moved {len(moved)}   first {idx.min()}   last {idx.max()}")

    print()
    print("it RISES with volatility (the sign ts_q05_60 does not have)")
    for name in ("walk", "vol-cycle", "heavy-tailed"):
        close = FRAMES[name]()
        high, low = _ohlc(close)
        print(f"  {name:14s} rho vs NATR_60"
              f" {_spearman(tf_iqr_ret_60(close), natr(high, low, close, length=LENGTH)):8.4f}"
              f"   rho vs TS_Q05_60"
              f" {_spearman(tf_iqr_ret_60(close), ts_q05_60(close)):8.4f}")


# ====================================================================== Z


def section_Z():
    _head("Z  cost")
    rng = np.random.default_rng(3)
    close = Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, 400_000))))
    for length in (5, LENGTH, 250):
        best = min(_timed(close, length) for _ in range(3))
        tracemalloc.start()
        tf_iqr_ret_60(close, length=length)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"  length {length:4d}  best of three {best * 1e3:7.1f} ms"
              f"   traced peak {peak / 1e6:6.1f} MB")
    print("  ⚠ wall-clock moves between runs and machines; the PEAK is the"
          " claim.")


def _timed(close, length):
    t0 = time.perf_counter()
    tf_iqr_ret_60(close, length=length)
    return time.perf_counter() - t0


# ======================================================================


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A6": section_A6, "B": section_B, "M": section_M,
    "C": section_C, "D": section_D, "G": section_G, "O": section_O,
    "S": section_S, "Z": section_Z,
}


def main(argv):
    pd.set_option("display.width", 120)
    wanted = [a.upper() for a in argv[1:]] or list(SECTIONS)
    unknown = [w for w in wanted if w not in SECTIONS]
    if unknown:
        raise SystemExit(f"unknown section(s): {unknown}; "
                         f"known: {list(SECTIONS)}")
    for name in wanted:
        SECTIONS[name]()


if __name__ == "__main__":
    main(sys.argv)
