# -*- coding: utf-8 -*-
"""TS-ABOVE-MEAN-20 (PandasTa issue #97) -- every number in
`docs/TsAboveMean20Measured.md` and in `pandas_ta/statistics/ts_above_mean_20.py`'s
docstring comes from a section of this script.

    python docs/measure_ts_above_mean_20.py            # everything
    python docs/measure_ts_above_mean_20.py gate_a     # one section

Sections: gate_a, gate_b, gate_c, gate_d, guards, overlap, shape, cost.

Gate E is NOT here: it needs the parent repo's engine and the 89 frozen BIST
frames, and issue-solver runs it after this session.
"""
import math
import sys
import time
import tracemalloc
from fractions import Fraction

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_above_mean_20 import (NOISE_FACTOR,
                                                   ts_above_mean_20)

LENGTH = 20


# --------------------------------------------------------------------- frames


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=11):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def window_frame(rs):
    """`len(rs) + 1` closes whose returns are `rs` -- one window exactly, so
    the column's last bar is the hand-derived answer."""
    body = np.cumprod(1.0 + np.asarray(rs, dtype=float))
    return Series(100.0 * np.concatenate([[1.0], body]))


def ar1(n=1500, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return from_returns(np.clip(x, -0.5, 0.5))


def heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def right_skewed(n=1500, seed=5, sigma=0.01):
    """Lottery-shaped returns: many small losses, few large gains. This is the
    frame on which the column is NOT 0.5."""
    rng = np.random.default_rng(seed)
    r = sigma * (rng.standard_exponential(n) - 1.0)
    return from_returns(np.clip(r, -0.5, 0.5))


def left_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * (1.0 - rng.standard_exponential(n))
    return from_returns(np.clip(r, -0.5, 0.5))


def two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def trending(n=1500, seed=9):
    return walk(n, seed, sigma=0.004, drift=0.01)


def flat(n=300, price=100.0):
    return Series(np.full(n, price))


def ladder(n=300, price=100.0, rate=0.01):
    """A mathematically CONSTANT return, which float64 reproduces only to
    rounding: the window's returns differ in their last bits, so an unguarded
    count is decided by that rounding."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


FRAMES = {
    "walk": walk,
    "tick-rounded": tick_rounded,
    "ar1+": lambda: ar1(phi=0.5),
    "ar1-": lambda: ar1(phi=-0.5, seed=17),
    "heavy-tailed": heavy_tailed,
    "right-skewed": right_skewed,
    "left-skewed": left_skewed,
    "two-point": two_point,
    "trending": trending,
}


def returns_of(close):
    return (close / close.shift(1) - 1.0).to_numpy()


def spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def bit_equal(a, b):
    """(masks agree, equal fired bars, shared fired bars)."""
    same_mask = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    return same_mask, int((a[m] == b[m]).sum()), int(m.sum())


def max_abs_diff(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


# -------------------------------------------------------------- the oracles


def source_windowed(close, length=LENGTH):
    """tsfresh's `count_above_mean` retyped and handed one window at a time,
    then divided by the window size -- the issue's `count_above_mean / n`.
    Shares no code with the module: a Python loop, `np.mean`, and the source's
    own `np.where(x > m)[0].size`."""
    r = returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        m = np.mean(x)
        out[t] = np.where(x > m)[0].size / length
    return Series(out, index=close.index)


def fsum_windowed(close, length=LENGTH):
    """The same statistic with the mean taken by `math.fsum`, which is exact
    up to one final rounding. Scalar Python throughout."""
    r = [float(v) for v in returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        m = math.fsum(x) / length
        out[t] = sum(1 for v in x if v > m) / length
    return Series(out, index=close.index)


def exact_windowed(close, length=LENGTH):
    """The EXACT count: every float return is a rational, so the window mean
    is a rational and every comparison is decided with no rounding at all."""
    r = [float(v) for v in returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        q = [Fraction(v) for v in x]
        m = sum(q) / length
        out[t] = sum(1 for v in q if v > m) / length
    return Series(out, index=close.index)


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_above_mean_20`,
    retyped: `roll(ret(c), 20, w_count_above_mean)` with
    `w_count_above_mean(W) = (W > W.mean(1, keepdims=True)).mean(1)` and
    `_from_win` writing at `out[n - 1:]`. No guards of any kind."""
    r = returns_of(close)
    W = sliding_window_view(r, length)
    vals = (W > W.mean(1, keepdims=True)).mean(1)
    out = np.full(r.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


def unguarded(close, length=LENGTH):
    """This module without its floor -- the same windows, the same mean, no
    `reported` test. Isolates what the floor buys."""
    r = returns_of(close)
    W = sliding_window_view(r, length)
    vals = (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
    out = np.full(r.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


def absolute_floor(close, length=LENGTH):
    """The floor the sibling tsfresh ports use -- `4096 eps` ABSOLUTE on the
    window's return range -- instead of this module's relative one."""
    r = returns_of(close)
    W = sliding_window_view(r, length)
    hi, lo = W.max(axis=1), W.min(axis=1)
    vals = np.where(hi - lo > NOISE_FACTOR,
                    (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length,
                    np.nan)
    out = np.full(r.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


# ------------------------------------------------------------------- Gate A


def gate_a():
    print("=" * 78)
    print("GATE A -- correctness against the source formula")
    print("=" * 78)
    print("The oracle is issue #97's line (`count_above_mean / n on 20 returns`)")
    print("plus the published definition of `feature_calculators.count_above_mean`")
    print("(`np.where(x > np.mean(x))[0].size`). tsfresh is NOT installed here and")
    print("web access is unavailable, so this is not a read of tsfresh's own code.")

    print("\nA1. Against the source applied WINDOW BY WINDOW (no shared code)")
    for name, fn in FRAMES.items():
        close = fn()
        base, other = ts_above_mean_20(close), source_windowed(close)
        same, eq, shared = bit_equal(base, other)
        print(f"  {name:<13} masks {'identical' if same else 'DIFFER'}  "
              f"bit-equal {eq}/{shared}  rho {spearman(base, other):.6f}")

    print("\nA2. Against a math.fsum scalar loop (exact-to-one-rounding mean)")
    for name in ("walk", "heavy-tailed", "right-skewed"):
        close = FRAMES[name]()
        base, other = ts_above_mean_20(close), fsum_windowed(close)
        same, eq, shared = bit_equal(base, other)
        print(f"  {name:<13} masks {'identical' if same else 'DIFFER'}  "
              f"bit-equal {eq}/{shared}")

    print("\nA3. Against an EXACT rational oracle (fractions.Fraction)")
    print("    i.e. how often the float mean's own rounding flips a comparison")
    for name in ("walk", "tick-rounded", "two-point", "right-skewed"):
        close = FRAMES[name]()
        base, other = ts_above_mean_20(close), exact_windowed(close)
        same, eq, shared = bit_equal(base, other)
        print(f"  {name:<13} masks {'identical' if same else 'DIFFER'}  "
              f"exact on {eq}/{shared}  max |diff| {max_abs_diff(base, other):.3e}")
    print("    and a MEAN-DOMINATED path, |mean|/sd = 1e5, where the sum's")
    print("    cancellation is worst:")
    rng = np.random.default_rng(99)
    r = 0.5 + 0.5e-5 * rng.standard_normal(600)
    close = from_returns(r)
    base, other = ts_above_mean_20(close), exact_windowed(close)
    same, eq, shared = bit_equal(base, other)
    print(f"  mean-dominated  masks {'identical' if same else 'DIFFER'}  "
          f"exact on {eq}/{shared}  max |diff| {max_abs_diff(base, other):.3e}")

    print("\nA4. The reachable range: 1 <= count <= length - 1 on every window")
    print("    (a count of 0 or `length` needs all `length` returns equal, which")
    print("    the floor refuses -- so the column lives on [1/20, 19/20])")
    lo_seen, hi_seen, total = 1.0, 0.0, 0
    for name, fn in FRAMES.items():
        x = ts_above_mean_20(fn()).dropna()
        lo_seen, hi_seen = min(lo_seen, float(x.min())), max(hi_seen, float(x.max()))
        total += int(x.size)
        print(f"  {name:<13} min {float(x.min()):.2f}  max {float(x.max()):.2f}  "
              f"distinct {int(x.nunique())}  fired {int(x.size)}")
    print(f"  pooled over {total} fired bars of {len(FRAMES)} frames: "
          f"min {lo_seen:.2f}, max {hi_seen:.2f}")
    print("  and the two ends are ATTAINED by a hand-built window:")
    for label, rs in (("19 above", [0.0] + [0.01] * 19),
                      ("1 above", [0.01] + [0.0] * 19)):
        col = ts_above_mean_20(window_frame(rs))
        print(f"    {label:<9} -> {float(col.iloc[-1]):.2f}")

    print("\nA5. Readings the one-line formula leaves open, PRICED not assumed")
    close = walk()
    base = ts_above_mean_20(close)

    def log_returns(cl, length=LENGTH):
        r = np.log(cl.to_numpy()) - np.log(cl.shift(1).to_numpy())
        W = sliding_window_view(r, length)
        out = np.full(r.size, np.nan)
        out[length - 1:] = (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
        return Series(out, index=cl.index)

    def closes_not_returns(cl, length=LENGTH):
        """`20 CLOSES` instead of 20 returns: 19 returns a window."""
        return ts_above_mean_20(cl, length=length - 1)

    def ge(cl, length=LENGTH):
        r = returns_of(cl)
        W = sliding_window_view(r, length)
        out = np.full(r.size, np.nan)
        out[length - 1:] = (W >= (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
        return Series(out, index=cl.index)

    def raw_count(cl, length=LENGTH):
        return ts_above_mean_20(cl, length=length) * length

    def on_closes(cl, length=LENGTH):
        """`count_above_mean` of the 20 CLOSES, not of the returns."""
        x = cl.to_numpy(dtype=float)
        W = sliding_window_view(x, length)
        out = np.full(x.size, np.nan)
        out[length - 1:] = (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
        return Series(out, index=cl.index)

    for label, fn in (("log returns", log_returns),
                      ("20 closes = 19 returns", closes_not_returns),
                      (">= instead of >", ge),
                      ("raw count, not share", raw_count),
                      ("of CLOSES, not returns", on_closes)):
        other = fn(close)
        same, eq, shared = bit_equal(base, other)
        print(f"  {label:<24} rho {spearman(base, other):8.6f}  "
              f"max |diff| {max_abs_diff(base, other):.4f}  "
              f"bit-equal {eq}/{shared}")
    print("  `>=` is INVISIBLE on every frame above, including a tick-rounded")
    print("  one: a tie with the window MEAN (a 20-way average, not another")
    print("  return) does not happen by accident. Counted:")
    for name in ("walk", "tick-rounded", "two-point"):
        cl = FRAMES[name]()
        r = returns_of(cl)
        W = sliding_window_view(r[1:], LENGTH)
        ties = int((W == (W.sum(axis=1) / LENGTH)[:, None]).sum())
        same, eq, shared = bit_equal(ts_above_mean_20(cl), ge(cl))
        print(f"    {name:<13} {ties} exact ties in "
              f"{W.shape[0] * LENGTH} window/return pairs; "
              f"`>=` bit-equal {eq}/{shared}")
    print("  so the choice is pinned by a CONSTRUCTED window instead:")
    print("  closes [100, 50, 50, 75] have returns [-0.5, 0.0, +0.5], which sum")
    print("  to exactly 0.0, so the middle return ties the mean exactly.")
    tie = Series([100.0, 50.0, 50.0, 75.0])
    print(f"    strict `>` (shipped) -> {float(ts_above_mean_20(tie, length=3).iloc[-1]):.6f}"
          f"   `>=` -> {float(ge(tie, length=3).iloc[-1]):.6f}")

    print("\nA6. Hand-derived windows")
    cases = (
        ("alternating +-1%", [0.01, -0.01] * 10, 0.5),
        ("one big gain", [0.5] + [0.0] * 19, 1 / 20),
        ("one big loss", [-0.5] + [0.0] * 19, 19 / 20),
        ("ramp 1..20", [0.001 * k for k in range(1, 21)], 10 / 20),
    )
    for label, rs, want in cases:
        got = float(ts_above_mean_20(window_frame(rs)).iloc[-1])
        print(f"  {label:<18} -> {got:.6f}  expected {want:.6f}  "
              f"{'OK' if got == want else 'MISMATCH'}")
    print("  20 identical returns -> ", end="")
    v = ts_above_mean_20(Series(100.0 * np.ones(21))).iloc[-1]
    print("NaN" if np.isnan(v) else f"{float(v)}")

    print("\nA7. Against the screen prototype (`ind_screen.py`, ts_above_mean_20)")
    for name, fn in FRAMES.items():
        close = fn()
        base, proto = ts_above_mean_20(close), prototype(close)
        same, eq, shared = bit_equal(base, proto)
        print(f"  {name:<13} masks {'identical' if same else 'DIFFER'}  "
              f"bit-equal {eq}/{shared}  rho {spearman(base, proto):.6f}")
    close = walk()
    base, proto = ts_above_mean_20(close), prototype(close)
    first_b = int(base.notna().to_numpy().argmax())
    first_p = int(proto.notna().to_numpy().argmax())
    print(f"  first fired bar: port {first_b}, prototype {first_p} "
          f"(the prototype's bar {first_p} reads "
          f"{float(proto.iloc[first_p]):.2f} from a window whose oldest return "
          f"is NaN)")
    holed = walk()
    holed.iloc[200] = np.nan
    bp, pp = ts_above_mean_20(holed), prototype(holed)
    disagree = int(((bp.isna() != pp.isna())).sum())
    m = bp.notna() & pp.notna()
    print(f"  with one NaN close at bar 200: {disagree} bars where one is NaN "
          f"and the other is not, {int((bp[m] == pp[m]).sum())}/{int(m.sum())} "
          f"bit-equal elsewhere")


# ------------------------------------------------------------------- Gate B


def gate_b():
    """The mutants themselves live in `tests/test_ts_above_mean_20.py`; this
    section reports the catch counts the test's bands are drawn around."""
    import tests.test_ts_above_mean_20 as T

    print("=" * 78)
    print("GATE B -- the blind future-perturbation sweep, 37 offsets")
    print("=" * 78)
    print("The real module, on three frames and at four lengths:")
    for name, (close, other) in sorted(T.PAIRS.items()):
        print(f"  {name:<13} leaks {len(T._caught(ts_above_mean_20, close, other))}/37")
    close, other = T.PAIRS["walk"]
    for length in (5, 60, 250):
        hits = T._caught(ts_above_mean_20, close, other, length=length)
        print(f"  walk, length {length:<4} leaks {len(hits)}/37")

    print("\nEach mutant, live and caught:")
    for mutant in sorted(T.MUTANTS):
        mod = T._load_mutant(*T.MUTANTS[mutant])
        cells = []
        for name, (close, other) in sorted(T.PAIRS.items()):
            live = not mod.ts_above_mean_20(close).equals(
                ts_above_mean_20(close))
            cells.append(f"{name} {len(T._caught(mod.ts_above_mean_20, close, other))}/37"
                         + ("" if live else " NOT LIVE"))
        print(f"  {mutant:<16} " + "  ".join(cells))

    print("\nThe sixth mutant -- the FLOOR's own index (`hi`/`lo` rolled by")
    print("one window, so bar T's NaN mask would read window T+1).")
    mod = T._load_mutant(*T.SHIFTED_FLOOR)
    for name, (close, other) in sorted(T.PAIRS.items()):
        real, mut = ts_above_mean_20(close), mod.ts_above_mean_20(close)
        differ = [int(i) for i in np.flatnonzero(
            (real.isna() != mut.isna()).to_numpy()
            | (real.fillna(-1.0) != mut.fillna(-1.0)).to_numpy())]
        print(f"  {name:<13} live {not mut.equals(real)};  bars moved "
              f"{differ};  bar {T.LENGTH - 1} NaN -> "
              f"{float(mut.iloc[T.LENGTH - 1])};  last bar "
              f"{float(real.iloc[-1]):.2f} -> "
              f"{'NaN' if np.isnan(mut.iloc[-1]) else float(mut.iloc[-1])};"
              f"  sweep {len(T._caught(mod.ts_above_mean_20, close, other))}/37")
    print("  It is LIVE on every frame and moves exactly TWO bars, and the")
    print("  blind sweep still scores 0/37 -- for two different reasons.")
    print("   * bar 19 (NaN -> 0.0, the impossible value) is a genuine")
    print("     look-ahead, and it PRECEDES every offset: the sweep's offsets")
    print("     start at 40, and bar 19 reads 0.0 in the perturbed run too.")
    print("   * the LAST bar (a value -> NaN) is a `np.roll` WRAP and not a")
    print("     look-ahead -- the rolled extrema of window 0, which hold the")
    print("     undefined first return, land on the last window -- and it is")
    print("     after every offset, so `_caught`, which only inspects bars")
    print("     BEFORE the offset, never looks at it either.")
    print("  So it is caught by a DESIGNED frame instead: a walk interrupted")
    print("  every 40 bars by 25 bars of exactly-zero returns, which makes the")
    print("  floor bite on INTERIOR windows.")
    close, other = T._floored_patches(), T._floored_patches(seed=24)
    col = ts_above_mean_20(close)
    print(f"    floored-patches frame: {int(col.notna().sum())} fired of "
          f"{len(close)};  {int(col.iloc[T.LENGTH:].isna().sum())} INTERIOR "
          f"windows empty, plus the {T.LENGTH} warm-up bars = "
          f"{int(col.isna().sum())} NaN in all")
    print(f"    real module {len(T._caught(ts_above_mean_20, close, other))}/37"
          f"   shifted_floor "
          f"{len(T._caught(mod.ts_above_mean_20, close, other))}/37")


# ------------------------------------------------------------------- Gate C


def gate_c():
    print("=" * 78)
    print("GATE C -- reachability on synthetic frames (real data is Gate E's)")
    print("=" * 78)
    for name, fn in FRAMES.items():
        close = fn()
        x = ts_above_mean_20(close)
        fired = int(x.notna().sum())
        nz = int((x.dropna() != 0).sum())
        print(f"  {name:<13} fires {fired}/{len(close)}  non-zero {nz}  "
              f"distinct {int(x.nunique())}  median {float(x.median()):.4f}")
    print("  flat (300 bars, one price)      fires "
          f"{int(ts_above_mean_20(flat()).notna().sum())}")
    print("  ladder (constant 1% return)     fires "
          f"{int(ts_above_mean_20(ladder()).notna().sum())}")


# ------------------------------------------------------------------- Gate D


def gate_d():
    print("=" * 78)
    print("GATE D -- scale invariance")
    print("=" * 78)
    print("\nD1. x8 and x64 -- bit-identical (the return is a price RATIO)")
    for name, fn in FRAMES.items():
        close = fn()
        base = ts_above_mean_20(close)
        row = []
        for k in (8.0, 64.0):
            same, eq, shared = bit_equal(base, ts_above_mean_20(close * k))
            row.append(f"x{int(k)} {'masks OK' if same else 'MASKS DIFFER'} "
                       f"{eq}/{shared}")
        print(f"  {name:<13} " + "   ".join(row))

    print("\nD2. x10, x3.7, x0.1 and x1.0000001 -- NOT bit-identical by")
    print("    construction (they perturb the returns' last bits), yet measured")
    print("    bit-equal: a count only moves when a perturbation reorders a")
    print("    return and its window mean, which these do not do here. This is")
    print("    a MEASUREMENT, not a guarantee -- D6 is how much margin it has.")
    for name, fn in FRAMES.items():
        close = fn()
        base = ts_above_mean_20(close)
        cells = []
        for k in (10.0, 3.7, 0.1, 1.0000001):
            other = ts_above_mean_20(close * k)
            same, eq, shared = bit_equal(base, other)
            cells.append(f"x{k:g} {eq}/{shared}" + ("" if same else " MASKS DIFFER"))
        print(f"  {name:<13} " + "  ".join(cells))

    print("\nD6. HOW MUCH margin D2 has, rather than another frame of it.")
    print("    A COUNT moves only when a perturbation reorders a return and its")
    print("    own window mean, so the question is how close those two get. A")
    print("    non-power-of-two rescale moves a return by about one ulp, i.e.")
    print("    about 2.2e-16 of its own size, so a window is at risk only if")
    print("    its smallest gap |r - mean| / max|r| is near that. On a")
    print("    200,000-bar walk:")
    big_walk = walk(200000, seed=4)
    base = ts_above_mean_20(big_walk)
    rr = returns_of(big_walk)[1:]
    W = sliding_window_view(rr, LENGTH)
    gap = np.abs(W - (W.sum(axis=1) / LENGTH)[:, None])
    amax = np.abs(W).max(axis=1)
    print(f"    smallest gap ratio over {W.shape[0]} windows: "
          f"{float((gap.min(axis=1) / amax).min()):.3e}")
    for k in (10.0, 3.7, 0.1, 1.0000001):
        other = ts_above_mean_20(big_walk * k)
        m = base.notna() & other.notna()
        print(f"    x{k:<12.8g} bars that MOVE: {int((base[m] != other[m]).sum())}"
              f" of {int(m.sum())}")
    print("    (x8 and x64 cannot move any window, ever: a power of two rescales")
    print("     the ratio exactly, so the returns are bit-identical -- D1)")

    print("\nD3. 0 < fires < n, and the column is not constant")
    for name, fn in FRAMES.items():
        close = fn()
        x = ts_above_mean_20(close)
        fired, n = int(x.notna().sum()), len(close)
        print(f"  {name:<13} 0 < {fired} < {n}: "
              f"{'OK' if 0 < fired < n else 'FAIL'}   distinct "
              f"{int(x.nunique())} (> 1: {'OK' if x.nunique() > 1 else 'FAIL'})")

    print("\nD4. other lengths, x8 bit-identity")
    close = walk()
    for length in (3, 5, 60, 250):
        base = ts_above_mean_20(close, length=length)
        same, eq, shared = bit_equal(base, ts_above_mean_20(close * 8.0,
                                                            length=length))
        print(f"  length {length:<4} masks {'identical' if same else 'DIFFER'}  "
              f"bit-equal {eq}/{shared}  distinct {int(base.nunique())}  "
              f"min {float(base.min()):.4f} max {float(base.max()):.4f}")

    print("\nD5. stronger than a price scale: an AFFINE map of the RETURNS")
    print("    (exactly invariant in real arithmetic; in float64 it is a")
    print("    tolerance, because the returns are rebuilt from new closes)")
    rng = np.random.default_rng(11)
    r = 0.015 * rng.standard_normal(1500)
    base = ts_above_mean_20(from_returns(r))
    for label, rr in (("r x 2", 2.0 * r), ("r x 0.5", 0.5 * r),
                      ("r + 0.004", r + 0.004)):
        other = ts_above_mean_20(from_returns(rr))
        same, eq, shared = bit_equal(base, other)
        print(f"  {label:<10} masks {'identical' if same else 'DIFFER'}  "
              f"bit-equal {eq}/{shared}  max |diff| {max_abs_diff(base, other):.4f}"
              f"  rho {spearman(base, other):.6f}")


# ------------------------------------------------------------------- guards


def guards():
    print("=" * 78)
    print("GUARDS -- what each one costs and what it buys")
    print("=" * 78)

    print("\nG1. The floor on a CONSTANT-return ladder (returns equal in exact")
    print("    arithmetic, differing only in their last bits in float64)")
    print("    (bar `length - 1` is excluded throughout: its window holds the")
    print("    undefined first return, where the unguarded spelling reads a")
    print("    NaN mean, no comparison true, and emits 0.0 on EVERY frame --")
    print("    an artefact of the warm-up and not of the ladder)")
    lad = ladder()
    g, u = ts_above_mean_20(lad), unguarded(lad)
    uu = u.iloc[LENGTH:].dropna()
    print(f"  guarded fires {int(g.notna().sum())}/{len(lad)};  "
          f"unguarded fires {int(uu.size)}, "
          f"distinct {int(uu.nunique())}, min {float(uu.min()):.2f}, "
          f"max {float(uu.max()):.2f}, median {float(uu.median()):.2f}")
    print(f"  unguarded windows reading the ARITHMETICALLY IMPOSSIBLE 0.0: "
          f"{int((uu == 0.0).sum())}; reading 1.0: {int((uu == 1.0).sum())}")
    print(f"  the warm-up bar {LENGTH - 1} itself: unguarded reads "
          f"{float(u.iloc[LENGTH - 1])}, this module reads "
          f"{'NaN' if np.isnan(g.iloc[LENGTH - 1]) else g.iloc[LENGTH - 1]}")
    print("  a FLAT frame (all returns exactly 0):")
    fl = flat()
    gf, uf = ts_above_mean_20(fl), unguarded(fl).iloc[LENGTH:].dropna()
    print(f"    guarded fires {int(gf.notna().sum())}; unguarded fires "
          f"{int(uf.size)}, all equal to {float(uf.min()):.1f} -- a value this"
          f" column cannot otherwise reach")

    print("\nG2. What the floor costs on clean frames")
    print("    `warm-up` is bar `length - 1`, which every frame loses and which")
    print("    is the window with the undefined first return; `body` is the rest")
    for name, fn in FRAMES.items():
        close = fn()
        g, u = ts_above_mean_20(close), unguarded(close)
        lost = g.isna() & u.notna()
        print(f"  {name:<13} warm-up {int(lost.iloc[:LENGTH].sum())}  "
              f"body {int(lost.iloc[LENGTH:].sum())}")

    print("\nG3. RELATIVE floor vs the siblings' ABSOLUTE 4096 eps")
    print("    a quiet-but-honest frame: returns about 1e-6 with a 1e-13 spread")
    rng = np.random.default_rng(5)
    r = 1e-6 + 1e-13 * rng.standard_normal(600)
    close = from_returns(r)
    rel, absf = ts_above_mean_20(close), absolute_floor(close)
    print(f"    relative floor (shipped) fires {int(rel.notna().sum())}/600")
    print(f"    absolute floor           fires {int(absf.notna().sum())}/600")
    ex = exact_windowed(close)
    same, eq, shared = bit_equal(rel, ex)
    print(f"    and the shipped column is exact on {eq}/{shared} of them "
          f"(masks {'identical' if same else 'DIFFER'})")
    print("    the mirror case: returns about 0.5 with a 1e-14 spread, where")
    print("    the count IS rounding and both floors must refuse")
    r = 0.5 + 1e-14 * rng.standard_normal(600)
    close = from_returns(r)
    print(f"    relative floor fires {int(ts_above_mean_20(close).notna().sum())}"
          f"/600,  absolute floor fires "
          f"{int(absolute_floor(close).notna().sum())}/600")

    print("\nG4. A non-finite close empties exactly the windows holding it")
    close = walk(400)
    base = ts_above_mean_20(close)
    for bar in (0, 1, 19, 200, 398, 399):
        holed = close.copy()
        holed.iloc[bar] = np.nan
        out = ts_above_mean_20(holed)
        extra = int((out.isna() & base.notna()).sum())
        moved = int((out.notna() & base.notna()
                     & (out != base)).sum())
        print(f"  NaN at bar {bar:<4} empties {extra} further bar(s), "
              f"moves {moved} value(s)")
    print("  a zero, a negative and a subnormal close are treated the same way:")
    for label, v in (("0.0", 0.0), ("-100.0", -100.0), ("1e-310", 1e-310)):
        holed = close.copy()
        holed.iloc[200] = v
        out = ts_above_mean_20(holed)
        print(f"    close[200] = {label:<8} empties "
              f"{int((out.isna() & base.notna()).sum())} further bar(s)")

    print("\nG5. One ENORMOUS return stays LOCAL (no online accumulator here)")
    print("    The frame is priced at about 1e-198 so that even a 1e+307 jump")
    print("    leaves every close a normal float: what engages at the top of")
    print("    the sweep is this module's per-return bound and not an overflow")
    print("    of the price itself.")
    close = walk(2000, seed=21) * 1e-200
    base = ts_above_mean_20(close)
    for mag in (1e2, 1e6, 1e8, 1e100, 1e300, 1e307):
        spiked = close.copy()
        spiked.iloc[200:] = spiked.iloc[200:] * mag
        out = ts_above_mean_20(spiked)
        later = slice(220, None)
        same_tail = bool((out.iloc[later].isna() == base.iloc[later].isna()).all()
                         and (out.iloc[later].dropna()
                              == base.iloc[later].dropna()).all())
        held = out.iloc[200:220]
        reading = ("all NaN" if bool(held.isna().all())
                   else f"all {float(held.min()):.2f}"
                   if float(held.min()) == float(held.max())
                   else f"{float(held.min()):.2f}..{float(held.max()):.2f}")
        print(f"  return x{mag:<7.0e} at bar 200: bars 220.. bit-identical "
              f"{same_tail};  the 20 windows holding it read {reading}")
    print("  (the per-return bound refuses only |r| >= "
          f"{np.finfo(float).max / (2 * LENGTH):.3e}, which is why 1e+307 is the"
          f" first magnitude above that empties them)")

    print("\nG6. The floor is scale-invariant but NOT shift-invariant, so the")
    print("    affine invariance of D5 belongs to the COUNT and not to the")
    print("    reported MASK. `hi - lo` is unchanged by `r -> r + c` while")
    print("    `NOISE_FACTOR * max|r|` grows with `c`, so a drift can empty a")
    print("    window the undrifted frame reports on. Measured, on returns of")
    print("    about 1e-6 whose spread is near the threshold a 0.004 drift")
    print("    would impose (3.64e-15):")
    rng = np.random.default_rng(13)
    noise = 3e-16 * rng.standard_normal(600)
    for label, drift in (("no drift", 0.0), ("+0.004 a bar", 0.004)):
        close = from_returns(1e-6 + drift + noise)
        r = returns_of(close)[1:]
        W = sliding_window_view(r, LENGTH)
        spread = W.max(axis=1) - W.min(axis=1)
        amax = np.abs(W).max(axis=1)
        print(f"    {label:<14} fires "
              f"{int(ts_above_mean_20(close).notna().sum())}/600;  median"
              f" window spread {float(np.median(spread)):.3e}, median floor"
              f" {float(np.median(NOISE_FACTOR * amax)):.3e}")
    print("    The COUNT itself is unaffected -- D5 measures that separately.")

    print("\nG7. Short input and a bad `length`")
    print(f"  {LENGTH} closes at length {LENGTH} -> "
          f"{ts_above_mean_20(walk(LENGTH))}")
    print(f"  {LENGTH + 1} closes -> fires "
          f"{int(ts_above_mean_20(walk(LENGTH + 1)).notna().sum())}")
    for bad in (None, 0, 2, -5):
        print(f"  length={bad!r:<5} -> "
              f"{ts_above_mean_20(walk(400), length=bad).name}")


# ------------------------------------------------------------------ overlap


def overlap():
    print("=" * 78)
    print("IN-FORK OVERLAP -- what Gate E's 687 engine comparators cannot see")
    print("=" * 78)
    print("The column is a coarse, rank-based reading of the window's return")
    print("SKEWNESS, so the fork's own skewness columns are the redundancy risk.")
    import pandas_ta as ta
    for name, fn in FRAMES.items():
        close = fn()
        base = ts_above_mean_20(close)
        r = Series(returns_of(close), index=close.index)
        row = {
            "skew(r,20)": r.rolling(LENGTH).skew(),
            "OSAP_RETSKEW_21": ta.osap_retskew_21(close),
            "TS_KURT_60": ta.ts_kurt_60(close),
            "TS_AC1_60": ta.ts_ac1_60(close),
            "TS_CID_CE_20": ta.ts_cid_ce_20(close),
            "LEAN_MOMERSION_20": ta.lean_momersion_20(close),
            "mean(r,20)": r.rolling(LENGTH).mean(),
            "stdev(r,20)": r.rolling(LENGTH).std(),
        }
        print(f"  {name}")
        for label, other in row.items():
            print(f"    {label:<20} rho {spearman(base, other):8.4f}")


# -------------------------------------------------------------------- shape


def shape():
    print("=" * 78)
    print("WHAT THE COLUMN ACTUALLY ORDERS")
    print("=" * 78)

    print("\nS1. Independent windows: the distribution of the column")
    rng = np.random.default_rng(2026)
    for label, draw in (
            ("gaussian", lambda m: rng.standard_normal((m, LENGTH))),
            ("student-t(2)", lambda m: rng.standard_t(2.0, (m, LENGTH))),
            ("right-skewed", lambda m: rng.standard_exponential((m, LENGTH))),
            ("left-skewed", lambda m: -rng.standard_exponential((m, LENGTH)))):
        W = draw(20000)
        v = (W > W.mean(1, keepdims=True)).sum(1) / LENGTH
        print(f"  {label:<13} mean {v.mean():.4f}  median {np.median(v):.4f}  "
              f"sd {v.std():.4f}  p10 {np.quantile(v, 0.1):.2f}  "
              f"p90 {np.quantile(v, 0.9):.2f}")

    print("\nS2. It is a SKEWNESS reading, on 20,000 independent windows")
    W = rng.standard_normal((20000, LENGTH))
    sk = np.linspace(-3.0, 3.0, 20000)
    # skew each window by mixing in an exponential tail of varying weight
    E = rng.standard_exponential((20000, LENGTH))
    W = W + sk[:, None] * (E - 1.0)
    v = (W > W.mean(1, keepdims=True)).sum(1) / LENGTH
    m, s = W.mean(1), W.std(1)
    skewness = (((W - m[:, None]) / s[:, None]) ** 3).mean(1)
    print(f"  Spearman(column, window skewness) = "
          f"{float(pd.Series(v).corr(pd.Series(skewness), method='spearman')):.4f}")

    print("\nS3. Persistence: two neighbouring windows share 19 of 20 returns")
    col = ts_above_mean_20(walk()).dropna()
    for lag in (1, 5, 10, 20):
        print(f"  autocorrelation at lag {lag:<3} {float(col.autocorr(lag)):.4f}")

    print("\nS4. How coarse it is")
    for name, fn in FRAMES.items():
        x = ts_above_mean_20(fn()).dropna()
        counts = x.value_counts().sort_index()
        print(f"  {name:<13} distinct {int(x.nunique())}/19 reachable, "
              f"modal value {float(counts.idxmax()):.2f} on "
              f"{int(counts.max())}/{int(x.size)} bars")


# --------------------------------------------------------------------- cost


def cost():
    print("=" * 78)
    print("COST")
    print("=" * 78)
    big = walk(400000, seed=3)
    for length in (3, 20, 60, 250):
        tracemalloc.start()
        ts_above_mean_20(big, length=length)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            ts_above_mean_20(big, length=length)
            times.append((time.perf_counter() - t0) * 1e3)
        print(f"  n = 400,000, length {length:<4} peak {peak:6.1f} MB   "
              f"{min(times):6.1f}-{max(times):6.1f} ms")
    print("\n  The peak does NOT grow with `length`, because the shipped count")
    print("  is one `(rows,)` comparison per window position in a Python loop")
    print("  of `length` iterations. The one-liner it replaced -- ")
    print("  `(windows > mean[:, None]).sum(axis=1)` -- materialises a")
    print("  (rows, length) bool array and IS what would grow it. Both")
    print("  spellings, same input, same answer:")

    def by_column(x, length):
        W = sliding_window_view(x, length)
        m = W.sum(axis=1) / length
        c = np.zeros(W.shape[0], dtype=np.int64)
        for j in range(length):
            c += W[:, j] > m
        return c

    def by_matrix(x, length):
        W = sliding_window_view(x, length)
        return (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1, dtype=np.int64)

    arr = returns_of(big)[1:]
    for length in (20, 60, 250):
        same = bool((by_column(arr, length) == by_matrix(arr, length)).all())
        row = []
        for label, fn in (("matrix", by_matrix), ("by-column", by_column)):
            tracemalloc.start()
            fn(arr, length)
            peak = tracemalloc.get_traced_memory()[1] / 1e6
            tracemalloc.stop()
            ts = []
            for _ in range(3):
                t0 = time.perf_counter()
                fn(arr, length)
                ts.append((time.perf_counter() - t0) * 1e3)
            row.append(f"{label} {peak:5.1f} MB {min(ts):6.1f} ms")
        print(f"    length {length:<4} " + "   ".join(row) +
              f"   identical counts: {same}")

    print("\n  the window-by-window oracle, on 20,000 bars:")
    small = walk(20000, seed=3)
    t0 = time.perf_counter()
    source_windowed(small)
    print(f"    {(time.perf_counter() - t0):.2f} s "
          f"(this module on the same input: ", end="")
    t0 = time.perf_counter()
    ts_above_mean_20(small)
    print(f"{(time.perf_counter() - t0) * 1e3:.1f} ms)")


SECTIONS = {
    "gate_a": gate_a,
    "gate_b": gate_b,
    "gate_c": gate_c,
    "gate_d": gate_d,
    "guards": guards,
    "overlap": overlap,
    "shape": shape,
    "cost": cost,
}


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SECTIONS)
    for key in wanted:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
        SECTIONS[key]()
        print()
