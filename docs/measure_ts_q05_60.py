# -*- coding: utf-8 -*-
"""TS-Q05-60 (PandasTa issue #101) -- every number in
`docs/TsQ0560Measured.md` and in `tests/test_ts_q05_60.py`.

    python docs/measure_ts_q05_60.py            # every section
    python docs/measure_ts_q05_60.py A1 D       # named sections

Sections
    A1  the module against an independent reimplementation of pandas'
        own `rolling.quantile` spelling -- BIT-equality
    A2  against the source's spelling (`pandas.Series.quantile`, which is
        `np.quantile`) applied window by window -- a tolerance, and why
    A3  against an EXACT rational oracle, in ulps
    A4  what the column reads: the 3rd and 4th smallest returns, nothing
        else
    A5  the readings the issue's line leaves open, priced
    A6  the screen prototype
    B   the causality sweep on the real module
    M   the six mutants: five live, one dead on a clean frame
    C   reachability: fires, distinct values, range
    D   scale-freedom: x8 / x64 bit-identity, x10 / x3.7 tolerance
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

from pandas_ta.statistics.osap_retskew_21 import osap_retskew_21
from pandas_ta.statistics.quantile import quantile
from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
from pandas_ta.statistics.ts_kurt_60 import ts_kurt_60
from pandas_ta.statistics.ts_q05_60 import MIN_LENGTH, Q, ts_q05_60
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
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


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
}


# ---------------------------------------------------------------- helpers


def _ret(close):
    return close / close.shift(1) - 1.0


def _ohlc(close, band=0.004):
    return close * (1.0 + band), close * (1.0 - band)


def _spearman(a, b):
    m = a.notna() & b.notna()
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
    return np.abs(x - y) / ulp


def _head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------- oracles


def _pandas_spelling(close, length=LENGTH, q=Q):
    """pandas' `roll_quantile` with `interpolation='linear'`, retyped from
    its documented behaviour and sharing no code with the module: sort the
    window, take the two order statistics around `q * (n - 1)`, and blend
    them as `vlow + (vhigh - vlow) * frac`."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i = q * (length - 1)
    lo, frac = int(i), i % 1
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        vlow, vhigh = s[lo], s[lo + 1]
        out[t] = vlow + (vhigh - vlow) * frac
    return Series(out, index=close.index)


def _source_windowed(close, length=LENGTH, q=Q):
    """tsfresh's `quantile(x, q)` -- `pandas.Series(x).quantile(q)` -- over
    the trailing `length` returns, one window at a time."""
    r = _ret(close)
    out = np.full(len(close), np.nan)
    for t in range(length, len(close)):
        w = r.iloc[t - length + 1:t + 1]
        if not np.isfinite(w.to_numpy()).all():
            continue
        out[t] = w.quantile(q)
    return Series(out, index=close.index)


def _numpy_spelling(close, length=LENGTH, q=Q):
    """numpy's `_lerp`, which for `t >= 0.5` evaluates `b - (b - a)*(1 - t)`
    rather than `a + (b - a)*t`."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i = q * (length - 1)
    lo, frac = int(i), i % 1
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        a, b = s[lo], s[lo + 1]
        out[t] = b - (b - a) * (1.0 - frac)
    return Series(out, index=close.index)


def _exact(close, length=LENGTH, q=None):
    """The correctly rounded answer. Every return is a double, so a
    rational; the sort is exact, the blend is done in `Fraction` and the
    result is rounded exactly once, at the end.

    `q` defaults to `Fraction(Q)` -- the EXACT value of the double 0.05,
    which is what the source is handed -- and not to 1/20."""
    qf = Fraction(Q) if q is None else q
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i = qf * (length - 1)
    lo = int(i)
    frac = i - lo
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = sorted(Fraction(float(v)) for v in w)
        out[t] = float(s[lo] + (s[lo + 1] - s[lo]) * frac)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH, q=Q):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_q05_60`, retyped:
    `ret(c).rolling(60).quantile(0.05)` with `ret(c) = c / c.shift(1) - 1`.
    No guards of any kind."""
    return (close / close.shift(1) - 1.0).rolling(length).quantile(q)


# ===================================================================== A1


def section_A1():
    _head("A1  the module against pandas' own spelling, retyped (BIT-equal)")
    print(f"{'frame':14s} {'masks':6s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>12s}")
    for name, make in FRAMES.items():
        close = make()
        masks, shared, same, d = _agree(ts_q05_60(close),
                                        _pandas_spelling(close))
        print(f"{name:14s} {str(masks):6s} {shared:7d} {same:10d} {d:12.3e}")

    print()
    print("the same, at other lengths, on the walk")
    close = _walk()
    for length in (MIN_LENGTH, 5, 20, 21, 250):
        masks, shared, same, d = _agree(
            ts_q05_60(close, length=length),
            _pandas_spelling(close, length=length))
        print(f"length {length:4d}   masks {masks}  shared {shared:5d}"
              f"  bit-equal {same:5d}  max |diff| {d:.3e}")

    print()
    print("which order statistics each `length` reads")
    for length in (MIN_LENGTH, 5, 20, 21, 22, LENGTH, 250):
        i = Q * (length - 1)
        print(f"  length {length:4d}  q*(n-1) = {i!r:24s} floor {int(i):3d}"
              f"  frac {i % 1!r}")
    print("  at the default that is the 3rd and 4th SMALLEST returns")


# ===================================================================== A2


def section_A2():
    _head("A2  against the source's spelling (Series.quantile == np.quantile)")
    print(f"{'frame':14s} {'masks':6s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>12s} {'max rel':>10s} {'max ulp':>8s}"
          f" {'spearman':>10s}")
    for name, make in FRAMES.items():
        close = make()
        col, src = ts_q05_60(close), _source_windowed(close)
        masks, shared, same, d = _agree(col, src)
        m = col.notna() & src.notna()
        rel = float(((col[m] - src[m]).abs() / src[m].abs()).max())
        u = _ulps(col, src)
        print(f"{name:14s} {str(masks):6s} {shared:7d} {same:10d} {d:12.3e}"
              f" {rel:10.3e} {float(u.max()):8.2f} {_spearman(col, src):10.6f}")

    print()
    print("Series.quantile against np.quantile, window by window (the walk):")
    close = _walk()
    src, nup = _source_windowed(close), _numpy_spelling(close)
    masks, shared, same, d = _agree(src, nup)
    print(f"  masks {masks}  shared {shared}  bit-equal {same}"
          f"  max |diff| {d:.3e}")


# ===================================================================== A3


def section_A3():
    _head("A3  against an EXACT rational oracle, in ulps")
    print(f"{'frame':14s} {'bars':>6s} | {'module: bit-eq':>14s} {'max ulp':>8s}"
          f" {'mean ulp':>9s} | {'numpy: bit-eq':>14s} {'max ulp':>8s}"
          f" {'mean ulp':>9s}")
    for name, make in FRAMES.items():
        close = make()
        col, ex, nup = ts_q05_60(close), _exact(close), _numpy_spelling(close)
        m = col.notna() & ex.notna()
        um, un = _ulps(col, ex), _ulps(nup, ex)
        print(f"{name:14s} {int(m.sum()):6d} |"
              f" {int((col[m] == ex[m]).sum()):14d} {float(um.max()):8.2f}"
              f" {float(um.mean()):9.4f} |"
              f" {int((nup[m] == ex[m]).sum()):14d} {float(un.max()):8.2f}"
              f" {float(un.mean()):9.4f}")

    print()
    print("the double 0.05 against the ideal 1/20, both EXACT (the walk):")
    close = _walk()
    a, b = _exact(close), _exact(close, q=Fraction(1, 20))
    masks, shared, same, d = _agree(a, b)
    print(f"  shared {shared}  bit-equal {same}  max |diff| {d:.3e}"
          f"  max ulp {float(_ulps(a, b).max()):.2f}")
    print(f"  Fraction(0.05)      = {Fraction(Q)}")
    print(f"  Fraction(0.05)*59   = {Fraction(Q) * 59} "
          f"= {float(Fraction(Q) * 59)!r}")


# ===================================================================== A4


def _pow2_window(exponents, price=100.0):
    """A `length + 1`-close frame whose returns are exactly `2**e - 1`.
    Every step is a multiplication by a power of two, so the closes, and
    the returns recovered from them, are EXACT -- which is what lets the
    two frames below be compared bit for bit."""
    c = [float(price)]
    for e in exponents:
        c.append(c[-1] * 2.0 ** e)
    return Series(np.array(c))


def section_A4():
    _head("A4  the column reads the 3rd and 4th smallest returns, and "
          "nothing else")
    # Ranks 0..3 are the only ones the blend can touch. Everything above
    # rank 3 is moved from +1.0 (2**1 - 1) to +3.0 (2**2 - 1), and the two
    # BELOW the pair from -0.96875 / -0.9375 to -0.999999 / -0.999998;
    # ranks 2 and 3 (-0.875 and -0.75) stay. The order inside the window is
    # scrambled differently in the two frames as well, because a quantile
    # does not read it.
    low_a, low_b = [-5, -4], [-20, -19]
    pair, rest_a, rest_b = [-3, -2], [1] * 56, [2] * 56
    rng = np.random.default_rng(3)
    ea = np.array(low_a + pair + rest_a, dtype=int)
    eb = np.array(low_b + pair + rest_b, dtype=int)
    rng.shuffle(ea)
    rng.shuffle(eb)
    a = ts_q05_60(_pow2_window(ea)).iloc[-1]
    b = ts_q05_60(_pow2_window(eb)).iloc[-1]
    i = Q * (LENGTH - 1)
    lo, frac = int(i), i % 1
    s2, s3 = 2.0 ** -3 - 1.0, 2.0 ** -2 - 1.0
    want = s2 + (s3 - s2) * frac
    print(f"  a window of exact returns 2**e - 1, 56 of 60 of them moved")
    print(f"    frame A  {a!r}")
    print(f"    frame B  {b!r}")
    print(f"    bit-equal: {a == b}")
    print(f"    the closed form s[{lo}] + (s[{lo + 1}] - s[{lo}]) * "
          f"{frac!r} = {want!r}  equal: {a == want}")

    print()
    print("how many DISTINCT returns a window has, and what that costs:")
    for name in ("walk", "tick-rounded", "two-point"):
        close = FRAMES[name]()
        col = ts_q05_60(close).dropna()
        rr = _ret(close).dropna().to_numpy()
        nd = [np.unique(rr[k:k + LENGTH]).size
              for k in range(0, rr.size - LENGTH + 1)]
        print(f"  {name:14s} distinct returns per window"
              f" min {min(nd):3d} median {int(np.median(nd)):3d}"
              f" | distinct column values {col.unique().size:5d}"
              f" of {col.size}")


# ===================================================================== A5


def section_A5():
    _head("A5  the readings the issue's line leaves open, priced")
    close = _walk()
    base = ts_q05_60(close)
    r = _ret(close)

    print("1. SIMPLE returns (the prototype's `ret`) against LOG returns")
    lr = np.log(close / close.shift(1))
    alt = lr.rolling(LENGTH, min_periods=LENGTH).quantile(Q)
    masks, shared, same, d = _agree(base, alt)
    print(f"   spearman {_spearman(base, alt):.6f}  max |diff| {d:.3e}"
          f"  bit-equal {same} of {shared}")

    print()
    print("2. the interpolation. `linear` is pandas' and numpy's default "
          "and so tsfresh's")
    for how in ("lower", "higher", "nearest", "midpoint"):
        alt = r.rolling(LENGTH, min_periods=LENGTH).quantile(
            Q, interpolation=how)
        masks, shared, same, d = _agree(base, alt)
        print(f"   {how:9s} spearman {_spearman(base, alt):.6f}"
              f"  max |diff| {d:.3e}  bit-equal {same} of {shared}")

    print()
    print("3. 60 RETURNS (61 closes) against 60 CLOSES (59 returns)")
    alt = r.rolling(LENGTH - 1, min_periods=LENGTH - 1).quantile(Q)
    masks, shared, same, d = _agree(base, alt)
    print(f"   spearman {_spearman(base, alt):.6f}  max |diff| {d:.3e}")
    print(f"   first fired bar {int(base.notna().to_numpy().argmax())}"
          f" against {int(alt.notna().to_numpy().argmax())}")

    print()
    print("4. the SIGN. A quantile is negative; VaR is usually quoted as a "
          "positive loss")
    alt = -base
    print(f"   spearman {_spearman(base, alt):.6f}"
          f"  share of fired bars below zero"
          f" {float((base.dropna() < 0).mean()):.6f}")
    tr = ts_q05_60(_trending())
    print(f"   on the trending frame, share below zero"
          f" {float((tr.dropna() < 0).mean()):.6f}"
          f"  max {float(tr.max()):+.6f}")

    print()
    print("5. q = 0.05 against its neighbours")
    for q in (0.01, 0.10, 0.25, 0.50):
        alt = r.rolling(LENGTH, min_periods=LENGTH).quantile(q)
        i = q * (LENGTH - 1)
        print(f"   q={q:<5} reads s[{int(i)}]/s[{int(i) + 1}]"
              f"  spearman {_spearman(base, alt):.6f}"
              f"  max |diff| {float((base - alt).abs().max()):.6f}")

    print()
    print("6. `rolling.quantile` against `Series.quantile` -- see A2/A3. "
          "The module keeps the ROLLING spelling, which is the prototype's.")


# ===================================================================== A6


def section_A6():
    _head("A6  the screen prototype")
    print(f"{'frame':14s} {'masks':6s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>12s}")
    for name, make in FRAMES.items():
        close = make()
        masks, shared, same, d = _agree(ts_q05_60(close), _prototype(close))
        print(f"{name:14s} {str(masks):6s} {shared:7d} {same:10d} {d:12.3e}")

    print()
    print("where the two part company: the guards this module adds")
    for label, bad in [("NaN", np.nan), ("inf", np.inf), ("zero", 0.0),
                       ("negative", -100.0), ("subnormal", 1e-310)]:
        close = _walk(400)
        close.iloc[200] = bad
        col, pro = ts_q05_60(close), _prototype(close)
        print(f"  close[200] = {label:9s} module fires {int(col.notna().sum()):4d}"
              f"  prototype {int(pro.notna().sum()):4d}")

    close = _walk(400)
    c = close.to_numpy().copy()
    c[200], c[201] = 1e-300, 1e50       # the ratio is 1e+350, so inf
    close = Series(c, index=close.index)
    col, pro = ts_q05_60(close), _prototype(close)
    print(f"  a ratio that OVERFLOWS   module fires {int(col.notna().sum()):4d}"
          f"  prototype {int(pro.notna().sum()):4d}")

    flat = _flat()
    print(f"  a FLAT frame             module fires {int(ts_q05_60(flat).notna().sum()):4d}"
          f"  prototype {int(_prototype(flat).notna().sum()):4d}"
          f"  (both 0.0 -- no floor here)")


# ====================================================================== B


OFFSETS = range(120, N, 40)     # 35 offsets, past the 60-bar warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}


def _caught(fn, close, other, offsets=OFFSETS, **kwargs):
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
    _head("B  the causality sweep on the real module "
          f"({len(list(OFFSETS))} offsets)")
    for name, (close, other) in PAIRS.items():
        print(f"{name:14s} leaks {len(_caught(ts_q05_60, close, other))}"
              f" of {len(list(OFFSETS))}")
    close, other = PAIRS["walk"]
    for length in (MIN_LENGTH, 5, 250):
        hits = _caught(ts_q05_60, close, other, length=length)
        print(f"length {length:4d}     leaks {len(hits)}"
              f" of {len(list(OFFSETS))}"
              f"  first fired bar"
              f" {int(ts_q05_60(close, length=length).notna().to_numpy().argmax())}")

BACK_DATE_TWO = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.rolling(length, min_periods=length).quantile(Q).shift(-2)")
BACK_DATE_FULL = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)"
    ".shift(-(length - 1))")
FORWARD_RETURN = (
    "        r = px / px.shift(1) - 1.0",
    "        r = px.shift(-1) / px - 1.0")
CENTERED_WINDOW = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.rolling(length, min_periods=length, center=True)"
    ".quantile(Q)")
ROLLED_WINDOW = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.shift(-(length // 2)).rolling(length, min_periods=length)"
    ".quantile(Q)")
#: The NaN mask's own index. A real look-ahead -- bar T's mask would read
#: whether bar T+1's return is finite -- and DEAD on a clean frame, where
#: every return but the first is finite. Caught by a designed frame.
FORWARD_MASK = (
    "    r = r.where(np.isfinite(r))",
    "    r = r.where(np.isfinite(r).shift(-1, fill_value=True))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "centered_window": CENTERED_WINDOW,
    "rolled_window": ROLLED_WINDOW,
}
BAD_OFFSETS = range(120, N, 120)        # 12 offsets, >= length + 1 apart


def _load_mutant(old, new):
    import importlib
    import types
    real = importlib.import_module("pandas_ta.statistics.ts_q05_60")
    src = open(real.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_q05_60_mutant")
    mod.__file__ = real.__file__
    exec(compile(src.replace(old, new), real.__file__, "exec"), mod.__dict__)
    return mod


def _bad_close_frame(seed=23):
    """A walk with a NaN close at every offset the designed sweep splices
    at. 120 bars apart, so each one empties its 61 windows and the frame
    still fires in between."""
    c = _walk(N, seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = np.nan
    return Series(c)


def section_M():
    _head("M  the mutants")
    print(f"{'mutant':16s} {'frame':14s} {'live':5s} {'caught':>7s}"
          f" of {len(list(OFFSETS))}")
    for name, pair in MUTANTS.items():
        mod = _load_mutant(*pair)
        for frame, (close, other) in PAIRS.items():
            live = not mod.ts_q05_60(close).equals(ts_q05_60(close))
            hits = _caught(mod.ts_q05_60, close, other)
            print(f"{name:16s} {frame:14s} {str(live):5s} {len(hits):7d}")

    print()
    print("the sixth: the NaN mask's own index, DEAD on a clean frame")
    mod = _load_mutant(*FORWARD_MASK)
    for frame, (close, other) in PAIRS.items():
        same = mod.ts_q05_60(close).equals(ts_q05_60(close))
        hits = _caught(mod.ts_q05_60, close, other)
        print(f"  {frame:14s} identical to the real module {same}"
              f"  caught {len(hits)} of {len(list(OFFSETS))}")

    print()
    print("and the designed probe that gives it something to change: a NaN "
          "close at each offset")
    close, other = _bad_close_frame(), _walk(N, 97)
    real = ts_q05_60(close)
    print(f"  the frame fires {int(real.notna().sum())} of {N}")
    print(f"  the real module leaks"
          f" {len(_caught(ts_q05_60, close, other, BAD_OFFSETS))}"
          f" of {len(list(BAD_OFFSETS))}")
    hits = _caught(mod.ts_q05_60, close, other, BAD_OFFSETS)
    print(f"  the mutant is caught {len(hits)} of {len(list(BAD_OFFSETS))}")
    j = list(BAD_OFFSETS)[1]
    p = close.copy()
    p.iloc[j:] = other.iloc[j:].values
    a, b = mod.ts_q05_60(close), mod.ts_q05_60(p)
    moved = np.flatnonzero(
        (a.iloc[:j].isna() != b.iloc[:j].isna()).to_numpy()).tolist()
    print(f"  at offset {j} the bar it moves is {moved} (derived: J - 1)")


# ====================================================================== C


def section_C():
    _head("C  reachability")
    print(f"{'frame':14s} {'fires':>6s}/{'n':<5s} {'distinct':>8s}"
          f" {'min':>11s} {'median':>11s} {'max':>11s} {'<0':>7s}")
    for name, make in FRAMES.items():
        close = make()
        col = ts_q05_60(close)
        v = col.dropna()
        print(f"{name:14s} {int(col.notna().sum()):6d}/{len(close):<5d}"
              f" {v.unique().size:8d} {float(v.min()):11.6f}"
              f" {float(v.median()):11.6f} {float(v.max()):11.6f}"
              f" {float((v < 0).mean()):7.3f}")

    print()
    for name, close in [("flat", _flat()), ("ladder", _ladder()),
                        ("quiet 1e-6", _quiet())]:
        col = ts_q05_60(close)
        v = col.dropna()
        print(f"{name:14s} fires {int(col.notna().sum()):4d}/{len(close):<5d}"
              f"  distinct {v.unique().size:4d}"
              f"  range [{float(v.min()):.3e}, {float(v.max()):.3e}]")

    print()
    print("the coarsest frame, in full: the two-point one")
    v = ts_q05_60(_two_point()).dropna()
    counts = v.value_counts().sort_index()
    for value, n in counts.items():
        print(f"  {value!r:26s} on {n:5d} bars")
    print(f"  spread {float(counts.index.max() - counts.index.min()):.3e}"
          f"  relative {float((counts.index.max() - counts.index.min()) / abs(counts.index.min())):.3e}")

    print()
    print("the bound: every close is positive and normal, so every return"
          " is at least -1 -- and the bound is")
    print("CLOSED, because a ratio can underflow to 0.0 (section G)")
    worst = min(float(ts_q05_60(FRAMES[f]()).min()) for f in FRAMES)
    print(f"  the lowest value over the nine frames: {worst:.6f}")
    crash = _from_returns(np.r_[np.full(80, -0.5), np.full(80, 0.01)])
    print(f"  a frame of -50% bars reads {float(ts_q05_60(crash).min()):.6f}")


# ====================================================================== D


def section_D():
    _head("D  scale-freedom")
    print("x8 and x64: bit-identical BY CONSTRUCTION (8a/8b is the same "
          "double as a/b)")
    print(f"{'frame':14s} {'x8 masks':9s} {'x8 bit-eq':>10s}"
          f" {'x64 masks':10s} {'x64 bit-eq':>11s} {'of':>6s}")
    for name, make in FRAMES.items():
        close = make()
        base = ts_q05_60(close)
        m8, s8, e8, _ = _agree(base, ts_q05_60(close * 8.0))
        m64, s64, e64, _ = _agree(base, ts_q05_60(close * 64.0))
        print(f"{name:14s} {str(m8):9s} {e8:10d} {str(m64):10s} {e64:11d}"
              f" {s8:6d}")

    print()
    print("x8 at other lengths, on the walk")
    close = _walk()
    for length in (MIN_LENGTH, 5, 20, 250):
        masks, shared, same, d = _agree(ts_q05_60(close, length=length),
                                        ts_q05_60(close * 8.0, length=length))
        print(f"  length {length:4d}  masks {masks}  bit-equal {same} of {shared}")

    print()
    print("x10 / x3.7 / x0.1 / x1.0000001: masks must match, values to a "
          "tolerance")
    print(f"{'frame':14s} {'factor':>10s} {'masks':6s} {'bit-eq':>7s}"
          f" {'of':>6s} {'max |diff|':>12s} {'max rel':>10s} {'spearman':>10s}")
    for name in ("walk", "tick-rounded", "heavy-tailed", "two-point"):
        close = FRAMES[name]()
        base = ts_q05_60(close)
        for k in (10.0, 3.7, 0.1, 1.0000001):
            o = ts_q05_60(close * k)
            masks, shared, same, d = _agree(base, o)
            m = base.notna() & o.notna()
            rel = float(((base[m] - o[m]).abs() / base[m].abs()).max())
            print(f"{name:14s} {k:10} {str(masks):6s} {same:7d} {shared:6d}"
                  f" {d:12.3e} {rel:10.3e} {_spearman(base, o):10.6f}")

    print()
    print("a rescale is NOT the same as a transform: price**2 changes the "
          "returns, so the column moves")
    close = _walk()
    base = ts_q05_60(close)
    for power in (2.0, 0.5):
        o = ts_q05_60(close ** power)
        print(f"  price ** {power}: spearman {_spearman(base, o):.6f}"
              f"  max |diff| {float((base - o).abs().max()):.6f}")

    print()
    print("and at a very large / very small PRICE level, x8 is still exact")
    for price in (1e-6, 1e6, 1e100):
        close = _walk() * (price / 100.0)
        masks, shared, same, d = _agree(ts_q05_60(close),
                                        ts_q05_60(close * 8.0))
        print(f"  price ~ {price:.0e}  masks {masks}  bit-equal {same}"
              f" of {shared}")


# ====================================================================== G


def section_G():
    _head("G  the guards")
    base = ts_q05_60(_walk(400))
    print("a bad close empties the windows it sits in "
          "(`length + 1` = 61, two spoiled returns)")
    for label, bad in [("NaN", np.nan), ("inf", np.inf), ("-inf", -np.inf),
                       ("zero", 0.0), ("negative", -100.0),
                       ("subnormal 1e-310", 1e-310)]:
        for pos in (0, 1, 60, 200, 399):
            close = _walk(400)
            close.iloc[pos] = bad
            col = ts_q05_60(close)
            emptied = [i for i in range(400)
                       if col.isna().iloc[i] and not base.isna().iloc[i]]
            before = [i for i in emptied if i < pos]
            if pos == 200:
                print(f"  {label:17s} at {pos:3d}: {len(emptied):3d} windows"
                      f" emptied {emptied[:1]}..{emptied[-1:]}"
                      f"  before the bad bar: {len(before)}")
            else:
                print(f"  {label:17s} at {pos:3d}: {len(emptied):3d} windows"
                      f"  before the bad bar: {len(before)}")
        print()

    print("a ratio that OVERFLOWS (1e-300 then 1e50): one spoiled return")
    close = _walk(400)
    c = close.to_numpy().copy()
    c[200], c[201] = 1e-300, 1e50
    col = ts_q05_60(Series(c, index=close.index))
    emptied = [i for i in range(400) if col.isna().iloc[i]
               and not base.isna().iloc[i]]
    print(f"  emptied {len(emptied)} windows, {emptied[:1]}..{emptied[-1:]}")

    print()
    print("the MIRROR of the overflow: a ratio that UNDERFLOWS to zero")
    c = _walk(400).to_numpy().copy()
    c[200], c[201] = 1e308, 1e-300      # both finite, positive and normal
    col = ts_q05_60(Series(c))
    r = Series(c) / Series(c).shift(1) - 1.0
    print(f"  the ratio {c[201] / c[200]!r}, so the return"
          f" {float(r.iloc[201])!r}")
    print(f"  finite: {bool(np.isfinite(r.iloc[201]))}"
          f"   >  -1: {bool(r.iloc[201] > -1.0)}"
          f"   == -1: {bool(r.iloc[201] == -1.0)}")
    print(f"  the module fires {int(col.notna().sum())} of 400;"
          f" unspiked minimum {float(base.min())!r},"
          f" spiked minimum {float(col.min())!r}")
    print(f"  the OTHER perturbation this frame makes: the return at 200 is"
          f" {float(r.iloc[200]):.3e}, finite and kept (the window maximum)")
    print(f"  bars reading exactly -1.0: {int((col == -1.0).sum())}")
    print("  -1.0 is the CORRECT answer here (the true return is"
          " -1 + 1e-608), so it is kept, not guarded away;")
    print("  it is reachable only when close[t]/close[t-1] rounds to 0.0,"
          " i.e. a fall of ~324 orders of magnitude.")
    print("  ONE such return is the window's smallest, and q = 0.05 reads"
          " the 3rd and 4th, so it does not reach the column.")
    # It does MOVE the column, though, and by exactly the mechanism that
    # keeps it off the floor: a -1.0 at s[0] demotes every ordinary return
    # by one rank, so the window reads the 2nd and 3rd smallest ordinary
    # returns where it used to read the 3rd and 4th.
    moved = [i for i in range(400)
             if not (base.isna().iloc[i] == col.isna().iloc[i]
                     and (base.isna().iloc[i] or base.iloc[i] == col.iloc[i]))]
    print(f"  bars it MOVES: {len(moved)}"
          f" ({moved[:1]}..{moved[-1:]}), none of them to -1.0")
    # Four of them do. The three-bar cycle keeps every close finite,
    # positive and normal and every OTHER ratio inside the float range:
    # 1e308 -> 1e-300 underflows (r = -1), 1e-300 -> 1e8 is 1e+308 and
    # 1e8 -> 1e308 is 1e+300, both finite.
    cycle = np.array([1e308, 1e-300, 1e8])
    c = np.tile(cycle, 30)
    col = ts_q05_60(Series(c))
    r = Series(c) / Series(c).shift(1) - 1.0
    print(f"  a 90-bar frame of [1e308, 1e-300, 1e8] cycles:"
          f" {int((r == -1.0).sum())} returns of exactly -1.0,"
          f" {int(np.isfinite(r.to_numpy()).sum())} finite of 89")
    print(f"  the column fires {int(col.notna().sum())} and its minimum is"
          f" {float(col.min())!r}  (== -1.0:"
          f" {bool(float(col.min()) == -1.0)})")
    print("  so the bound is CLOSED at -1, and reachable -- but only by a"
          " frame no market can print.")

    print()
    print("there is NO accumulator here, so one huge return stays LOCAL")
    for mag in (1e10, 1e100, 1e200, 1e300):
        close = _walk(400)
        spiked = close.copy()
        spiked.iloc[200] = spiked.iloc[200] * mag
        a, b = ts_q05_60(close), ts_q05_60(spiked)
        late = slice(263, 400)      # past the last window holding bar 201
        # The spike changes TWO returns (bars 200 and 201), so the windows
        # HOLDING a spiked return are the 61 ending at bars 200..260. The
        # 122 below is the number of BARS in the slice checked, 141..262,
        # which brackets those 61 windows on both sides.
        print(f"  x{mag:.0e}: bars 141..262 that fire"
              f" {int(b.iloc[141:263].notna().sum())}/122"
              f" (so all 61 windows holding a spiked return fire),"
              f" later bars bit-equal to the unspiked frame"
              f" {int((a.iloc[late] == b.iloc[late]).sum())}/{len(a.iloc[late])}")

    print()
    print("there is NO dispersion floor, and that is a decision:")
    for name, close in [("flat", _flat()), ("ladder", _ladder()),
                        ("quiet 1e-6", _quiet())]:
        col = ts_q05_60(close)
        v = col.dropna()
        ex = _exact(close)
        u = _ulps(col, ex)
        print(f"  {name:12s} fires {int(col.notna().sum()):4d}"
              f"  distinct {v.unique().size:4d}"
              f"  range [{float(v.min()):.6e}, {float(v.max()):.6e}]"
              f"  max ulp vs the exact oracle {float(u.max()):.2f}")
    for name, close in [("flat", _flat()), ("ladder", _ladder()),
                        ("crash -50%", _from_returns(np.r_[np.full(80, -0.5),
                                                           np.full(80, 0.01)]))]:
        rr = _ret(close).dropna().to_numpy()
        v = sorted(set(ts_q05_60(close).dropna().tolist()))
        print(f"  {name:12s} distinct returns {np.unique(rr).size:3d}"
              f" {sorted(set(rr.tolist()))[:2]!r:48s} column {v!r}")
    print("  a window with no dispersion has a well-defined 5% quantile "
          "(its own constant return);")
    print("  nothing is divided by it, so there is nothing for a floor to "
          "protect.")

    print()
    print("what the SIBLINGS' floor (return range <= 4096 eps) would cost "
          "here")
    floor = 4096 * np.finfo(float).eps
    print(f"  the floor is {floor:.3e}")
    for name, close in ([("flat", _flat()), ("ladder", _ladder()),
                         ("quiet 1e-6", _quiet())]
                        + [(n, FRAMES[n]()) for n in FRAMES]):
        col = ts_q05_60(close)
        r = _ret(close)
        rng_ = (r.rolling(LENGTH, min_periods=LENGTH).max()
                - r.rolling(LENGTH, min_periods=LENGTH).min())
        would = col.notna() & (rng_ <= floor)
        print(f"  {name:14s} fires {int(col.notna().sum()):5d}"
              f"  the floor would empty {int(would.sum()):5d}"
              f"  smallest window return range {float(rng_.min()):.3e}")


# ====================================================================== O


def section_O():
    _head("O  overlap -- what the column restates, and what it does not")
    print("against the window's OWN return standard deviation (the thing it "
          "is closest to)")
    for name in ("walk", "tick-rounded", "heavy-tailed", "trending", "ar1+",
                 "ar1-"):
        close = FRAMES[name]()
        col = ts_q05_60(close)
        r = _ret(close)
        sd = r.rolling(LENGTH, min_periods=LENGTH).std()
        mn = r.rolling(LENGTH, min_periods=LENGTH).min()
        mean = r.rolling(LENGTH, min_periods=LENGTH).mean()
        print(f"  {name:14s} sd {_spearman(col, sd):+.4f}"
              f"  min return {_spearman(col, mn):+.4f}"
              f"  mean return {_spearman(col, mean):+.4f}")

    print()
    print("against the fork's own columns (synthetic high/low = close "
          "x 1.004 / x 0.996)")
    cols = ["NATR_60", "UI_60", "QTL_60_0.05", "STDEV_60/close",
            "TS_KURT_60", "TS_AC1_60", "OSAP_RETSKEW"]
    print(f"  {'frame':12s}" + "".join(f" {c:>14s}" for c in cols))
    for name in ("walk", "tick-rounded", "heavy-tailed", "trending", "ar1+",
                 "ar1-"):
        close = FRAMES[name]()
        high, low = _ohlc(close)
        col = ts_q05_60(close)
        row = [
            _spearman(col, natr(high, low, close, length=LENGTH)),
            _spearman(col, ui(close, length=LENGTH)),
            _spearman(col, quantile(close, length=LENGTH, q=Q)),
            _spearman(col, stdev(close, length=LENGTH) / close),
            _spearman(col, ts_kurt_60(close)),
            _spearman(col, ts_ac1_60(close)),
            _spearman(col, osap_retskew_21(close)),
        ]
        print(f"  {name:12s}" + "".join(f" {v:+14.4f}" for v in row))

    print()
    print("the sign is the point: a BIG number means a QUIET window.")
    close = _walk()
    col = ts_q05_60(close)
    r = _ret(close)
    sd = r.rolling(LENGTH, min_periods=LENGTH).std()
    print(f"  spearman against -sd: {_spearman(col, -sd):+.4f}")
    print(f"  against the window's 5%-quantile MAGNITUDE (-col): "
          f"{_spearman(-col, sd):+.4f}")


# ====================================================================== S


def section_S():
    _head("S  the statistic itself")
    rng = np.random.default_rng(2026)
    i = Q * (LENGTH - 1)
    lo, frac = int(i), i % 1
    for label, draw in [
            ("gaussian", lambda n: rng.standard_normal((n, LENGTH))),
            ("student-t(2)", lambda n: rng.standard_t(2.0, (n, LENGTH))),
            ("exponential-1", lambda n: rng.standard_exponential((n, LENGTH))
             - 1.0)]:
        W = np.sort(draw(20000), axis=1)
        v = W[:, lo] + (W[:, lo + 1] - W[:, lo]) * frac
        print(f"  {label:14s} 20,000 INDEPENDENT windows:"
              f" mean {v.mean():+.4f}  sd {v.std():.4f}"
              f"  [{v.min():+.3f}, {v.max():+.3f}]")
    print("  (the gaussian 5% point itself is -1.6449)")

    print()
    print("it is a STATE, not an event flag: consecutive windows share 59 "
          "of their 60 returns")
    col = ts_q05_60(_walk())
    for lag in (1, 5, 30, 60, 120):
        print(f"  lag {lag:4d}  autocorrelation"
              f" {float(col.autocorr(lag)):.4f}")

    print()
    print("how long one bar moves the column")
    close = _walk()
    base = ts_q05_60(close)
    spiked = close.copy()
    spiked.iloc[700:] = spiked.iloc[700:] * 0.80      # a -20% bar at 700
    col = ts_q05_60(spiked)
    moved = np.flatnonzero(((base - col).abs() > 1e-12).to_numpy())
    print(f"  a -20% bar at 700 moves bars {moved.min()}..{moved.max()}"
          f" ({moved.size} bars)")


# ====================================================================== Z


def section_Z():
    _head("Z  cost")
    big = _walk(400000, seed=5)
    for length in (5, 60, 250):
        best = float("inf")
        for _ in range(3):
            t0 = time.perf_counter()
            ts_q05_60(big, length=length)
            best = min(best, time.perf_counter() - t0)
        tracemalloc.start()
        ts_q05_60(big, length=length)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"  length {length:4d}  400,000 bars  best of 3"
              f" {best * 1000:8.1f} ms  traced peak {peak / 1e6:6.1f} MB")
    print("  (wall-clock moves between runs and machines; the PEAK is the "
          "claim)")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A6": section_A6, "B": section_B, "M": section_M,
    "C": section_C, "D": section_D, "G": section_G, "O": section_O,
    "S": section_S, "Z": section_Z,
}

if __name__ == "__main__":
    print(f"pandas {pd.__version__}  numpy {np.__version__}")
    wanted = sys.argv[1:] or list(SECTIONS)
    for key in wanted:
        SECTIONS[key]()
