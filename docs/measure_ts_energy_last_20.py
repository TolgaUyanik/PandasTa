# -*- coding: utf-8 -*-
"""TS-ENERGY-LAST-20 (PandasTa issue #102) -- every number in
`docs/TsEnergyLast20Measured.md` and in `tests/test_ts_energy_last_20.py`.

    python docs/measure_ts_energy_last_20.py            # every section
    python docs/measure_ts_energy_last_20.py A1 D       # named sections

Sections
    A1  the module against tsfresh's own spelling -- `np.array_split` and
        `np.sum(chunk ** 2.0) / np.sum(x ** 2)` -- window by window: BIT
        equality
    A2  against a LEFT-TO-RIGHT accumulation of the same view, in ulps
    A3  against an EXACT rational oracle, in ulps -- which is what rules
        the left-to-right spelling out
    A4  the tail is `np.array_split`'s last chunk, and the two closed forms
    A5  the readings the issue's line leaves open, priced
    A6  the screen prototype (two `rolling().sum()` calls)
    B   the causality sweep on the real module
    M   the six mutants: five the blind sweep catches, one it cannot
    C   reachability: fires, distinct values, range
    D   scale-freedom: x8 / x64 bit-identity, x10 / x3.7 tolerance
    G   the guards, the floor this module does NOT have, and locality
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

from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20
from pandas_ta.statistics.ts_above_mean_20 import ts_above_mean_20
from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20
from pandas_ta.statistics.ts_energy_last_20 import (MIN_LENGTH, SEGMENTS,
                                                    SEGMENT_FOCUS, _tail,
                                                    ts_energy_last_20)
from pandas_ta.statistics.ts_imq_20 import ts_imq_20
from pandas_ta.statistics.ts_medskew_20 import ts_medskew_20
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.ui import ui

LENGTH = 20
TAIL = _tail(LENGTH)        # 5
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


def _clustered(n=N, seed=21, quiet=0.002, loud=0.03, run=25):
    """GARCH-like, by hand: alternating runs of quiet and loud bars, so the
    energy really does pile up at one end of a window. The frame this column
    is FOR."""
    rng = np.random.default_rng(seed)
    sig = np.where((np.arange(n) // run) % 2 == 0, quiet, loud)
    return _from_returns(np.clip(sig * rng.standard_normal(n), -0.5, 0.5))


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
    "clustered": _clustered,
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


def _source_windowed(close, length=LENGTH):
    """tsfresh's `energy_ratio_by_chunks(num_segments=4, segment_focus=3)`
    as published, over the trailing `length` returns, one window at a time:

        full = np.sum(x ** 2)
        NaN if full == 0 else
            np.sum(np.array_split(x, num_segments)[segment_focus] ** 2.0)
            / full

    It shares no code with the module -- `np.array_split` picks the chunk and
    numpy's PAIRWISE reduction does both sums."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        full = np.sum(w ** 2)
        if full == 0:
            continue
        chunk = np.array_split(w, SEGMENTS)[SEGMENT_FOCUS]
        out[t] = np.sum(chunk ** 2.0) / full
    return Series(out, index=close.index)


def _sequential_view(close, length=LENGTH):
    """The same windows as the module, accumulated LEFT TO RIGHT instead of
    through numpy's pairwise reduction. This is the spelling the module does
    NOT use; it is kept because it is the one a reader reaches for first and
    because §A3 is what rules it out."""
    from numpy.lib.stride_tricks import sliding_window_view
    r = _ret(close).to_numpy()
    e = r * r
    ew = sliding_window_view(e, length)
    tail = _tail(length)
    rows = ew.shape[0]
    den = np.zeros(rows)
    for j in range(length):
        den += ew[:, j]
    num = np.zeros(rows)
    for j in range(length - tail, length):
        num += ew[:, j]
    with np.errstate(invalid="ignore"):
        val = np.where(den > 0.0, num / den, np.nan)
    out = np.full(r.size, np.nan)
    out[length - 1:] = val
    return Series(out, index=close.index)


def _exact(close, length=LENGTH):
    """The correctly rounded answer. Every return is a double, so a
    rational; the square and both sums are exact in `fractions.Fraction` and
    the ratio is rounded exactly once, at the end."""
    r = _ret(close).to_numpy()
    tail = _tail(length)
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        sq = [Fraction(float(v)) ** 2 for v in w]
        den = sum(sq)
        if den == 0:
            continue
        out[t] = float(sum(sq[length - tail:]) / den)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_energy_last_20`,
    retyped:

        r2 = ret(c) ** 2
        return sdiv(tsum(r2, 5), tsum(r2, 20))

    with `ret(c) = c / c.shift(1) - 1`, `tsum(x, n) = x.rolling(n).sum()`
    and `sdiv(a, b) = (a / b).replace([inf, -inf], nan)`. The 5 is the
    prototype's literal; `length // SEGMENTS` reproduces it at the default
    and generalises it."""
    r2 = _ret(close) ** 2
    tail = _tail(length)
    out = r2.rolling(tail).sum() / r2.rolling(length).sum()
    return out.replace([np.inf, -np.inf], np.nan)


# ===================================================================== A1


def section_A1():
    _head("A1  the module against tsfresh's own spelling, window by window")
    print(f"{'frame':14s} {'masks':>5s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>11s} {'max ulp':>8s}")
    for name, make in FRAMES.items():
        close = make()
        col, src = ts_energy_last_20(close), _source_windowed(close)
        masks, shared, same, d = _agree(col, src)
        u = _ulps(col, src)
        print(f"{name:14s} {str(masks):>5s} {shared:7d} {same:10d}"
              f" {d:11.3e} {float(u.max()):8.2f}")

    print()
    print("at other lengths, on a walk")
    close = _walk()
    for length in (MIN_LENGTH, 5, 7, 21, 40, 250):
        col = ts_energy_last_20(close, length=length)
        src = _source_windowed(close, length=length)
        masks, shared, same, d = _agree(col, src)
        print(f"length {length:4d} (tail {_tail(length):3d})"
              f"  masks {str(masks):5s} shared {shared:5d}"
              f" bit-equal {same:5d} max |diff| {d:.3e}")


# ===================================================================== A2


def section_A2():
    _head("A2  the module against a LEFT-TO-RIGHT accumulation of the same "
          "windows")
    print(f"{'frame':14s} {'shared':>7s} {'bit-equal':>10s} {'max ulp':>8s}"
          f" {'mean ulp':>9s} {'spearman':>9s}")
    for name, make in FRAMES.items():
        close = make()
        col, sq = ts_energy_last_20(close), _sequential_view(close)
        _, shared, same, _ = _agree(col, sq)
        u = _ulps(col, sq)
        print(f"{name:14s} {shared:7d} {same:10d} {float(u.max()):8.2f}"
              f" {float(u.mean()):9.4f} {_spearman(col, sq):9.6f}")


# ===================================================================== A3


def section_A3():
    _head("A3  against an EXACT rational oracle, in ulps")
    print(f"{'frame':14s} {'bars':>6s} | {'module (pairwise)':>21s} |"
          f" {'left-to-right':>21s}")
    print(f"{'':14s} {'':6s} | {'bit-eq':>7s} {'max':>6s} {'mean':>6s} |"
          f" {'bit-eq':>7s} {'max':>6s} {'mean':>6s}")
    for name, make in FRAMES.items():
        close = make()
        col, ex, pw = (ts_energy_last_20(close), _exact(close),
                       _sequential_view(close))
        um, up = _ulps(col, ex), _ulps(pw, ex)
        print(f"{name:14s} {um.size:6d} |"
              f" {int((um == 0).sum()):7d} {float(um.max()):6.2f}"
              f" {float(um.mean()):6.3f} |"
              f" {int((up == 0).sum()):7d} {float(up.max()):6.2f}"
              f" {float(up.mean()):6.3f}")


# ===================================================================== A4


def section_A4():
    _head("A4  the tail IS numpy's last chunk, and the two closed forms")
    bad = [length for length in range(MIN_LENGTH, 241)
           if len(np.array_split(np.arange(length), SEGMENTS)[SEGMENT_FOCUS])
           != _tail(length)]
    print(f"lengths {MIN_LENGTH}..240 where `_tail` != "
          f"len(np.array_split(...)[{SEGMENT_FOCUS}]): {bad}")
    offs = [length for length in range(MIN_LENGTH, 241)
            if list(np.array_split(np.arange(length), SEGMENTS)
                    [SEGMENT_FOCUS]) != list(range(length - _tail(length),
                                                   length))]
    print(f"...and where that chunk is not the TRAILING `_tail` values:"
          f" {offs}")

    print()
    print("closed form 1: the oldest `length - tail` returns exactly zero")
    # `length + 1` closes: the first `length - tail` returns are exactly 0,
    # so the window's energy is its tail's energy and the share is exactly 1.
    for length in (MIN_LENGTH, 8, LENGTH, 60):
        tail = _tail(length)
        c = np.concatenate([np.full(length - tail + 1, 100.0),
                            100.0 * np.cumprod(np.full(tail, 1.01))])
        v = ts_energy_last_20(Series(c), length=length).iloc[-1]
        print(f"  length {length:3d} (tail {tail:3d})  reads {v!r}"
              f"  exactly 1.0: {v == 1.0}")

    print()
    print("closed form 2: the newest `tail` returns exactly zero")
    for length in (MIN_LENGTH, 8, LENGTH, 60):
        tail = _tail(length)
        rise = 100.0 * np.cumprod(np.full(length - tail + 1, 1.01))
        c = np.concatenate([rise, np.full(tail, rise[-1])])
        v = ts_energy_last_20(Series(c), length=length).iloc[-1]
        print(f"  length {length:3d} (tail {tail:3d})  reads {v!r}"
              f"  exactly 0.0: {v == 0.0}")

    print()
    print("closed form 3: all `length` returns the same MAGNITUDE "
          "(a two-point window) -> exactly tail / length")
    for length in (MIN_LENGTH, 8, LENGTH, 60):
        tail = _tail(length)
        rng = np.random.default_rng(7)
        s = np.where(rng.random(length) < 0.5, 1.0, -1.0)
        c = _from_returns(np.concatenate([[0.0], s * 0.5]))
        v = ts_energy_last_20(Series(c), length=length).iloc[-1]
        print(f"  length {length:3d}  reads {v!r}"
              f"  == tail/length ({tail / length!r}): {v == tail / length}")

    print()
    print("the bound [0, 1], which rounding could in principle escape: "
          "`num` and `den` are reduced over DIFFERENT subsets, so `num <= "
          "den` is exact arithmetic and not a float theorem")
    worst_lo, worst_hi, bad, bars = 1.0, 0.0, 0, 0
    for name, make in FRAMES.items():
        v = ts_energy_last_20(make()).dropna().to_numpy()
        worst_lo, worst_hi = min(worst_lo, float(v.min())), max(worst_hi,
                                                                float(v.max()))
        bad += int(((v < 0.0) | (v > 1.0)).sum())
        bars += v.size
    print(f"  over the {len(FRAMES)} frames: min {worst_lo:.6f}"
          f" max {worst_hi:.6f}; bars outside [0, 1]: {bad} of {bars}")
    close = _walk()
    for length in (MIN_LENGTH, 5, 7, 21, 40, 250):
        v = ts_energy_last_20(close, length=length).dropna().to_numpy()
        print(f"  length {length:4d}  min {float(v.min()):.3e}"
              f"  max {float(v.max()):.17f}"
              f"  outside [0, 1]: {int(((v < 0.0) | (v > 1.0)).sum())}"
              f" of {v.size}")
    rng = np.random.default_rng(3)
    esc, worst = 0, 0.0
    for _ in range(2000):
        # Windows built to make `num` round up and `den` round down: a tail
        # that carries all the energy and a body of values too small to
        # change the total.
        body = 10.0 ** rng.uniform(-30, -8, LENGTH - TAIL)
        tail = 1.0 + rng.uniform(-0.3, 0.3, TAIL)
        c = _from_returns(np.concatenate([[0.0], body, tail * 0.1]))
        v = float(ts_energy_last_20(Series(c)).iloc[-1])
        worst = max(worst, v)
        esc += int(not (0.0 <= v <= 1.0))
    print(f"  2,000 windows built to straddle 1.0: {esc} escaped,"
          f" the largest reads {worst!r}")


# ===================================================================== A5


def section_A5():
    _head("A5  the readings the issue's line leaves open")
    close = _walk()
    col = ts_energy_last_20(close)

    print("1. simple vs LOG returns (the issue says 'returns')")
    lr = np.log(close / close.shift(1))
    e = lr ** 2
    alt = (e.rolling(TAIL).sum() / e.rolling(LENGTH).sum())
    masks, shared, same, d = _agree(col, alt)
    print(f"   masks {masks} shared {shared} bit-equal {same}"
          f" max |diff| {d:.3e} spearman {_spearman(col, alt):.6f}")

    print()
    print("2. squared returns vs |returns| (energy is the SQUARE)")
    a = _ret(close).abs()
    alt = a.rolling(TAIL).sum() / a.rolling(LENGTH).sum()
    print(f"   spearman {_spearman(col, alt):.6f}"
          f" max |diff| {float((col - alt).abs().max()):.4f}")

    print()
    print("3. other segment counts, all at the LAST chunk")
    for segments in (2, 4, 5, 10, 20):
        tail = LENGTH // segments
        e = _ret(close) ** 2
        alt = e.rolling(tail).sum() / e.rolling(LENGTH).sum()
        print(f"   {segments:2d} segments (tail {tail:2d})"
              f"  spearman {_spearman(col, alt):9.6f}"
              f"  mean {float(alt.mean()):.6f}")

    print()
    print("4. the other three chunks of the SAME split (segment_focus 0..3)")
    e = _ret(close) ** 2
    den = e.rolling(LENGTH).sum()
    for focus in range(SEGMENTS):
        lo = LENGTH - (SEGMENTS - focus) * TAIL
        num = e.shift(LENGTH - TAIL - lo).rolling(TAIL).sum()
        alt = num / den
        print(f"   focus {focus}  spearman {_spearman(col, alt):9.6f}")

    print()
    print("5. the SIGN of the returns, which this column cannot see: it "
          "reads squares")
    rng = np.random.default_rng(99)
    r = _ret(close).to_numpy()
    flip = np.where(rng.random(r.size) < 0.5, -1.0, 1.0)
    flipped = _from_returns(np.nan_to_num(r * flip, nan=0.0))
    masks, shared, same, d = _agree(ts_energy_last_20(flipped),
                                    ts_energy_last_20(close))
    print(f"   every return's sign flipped at random: shared {shared}"
          f" bit-equal {same} max |diff| {d:.3e}"
          f" spearman {_spearman(ts_energy_last_20(flipped), ts_energy_last_20(close)):.6f}")
    rs, ls = _right_skewed(), _left_skewed()
    masks, shared, same, d = _agree(ts_energy_last_20(rs),
                                    ts_energy_last_20(ls))
    print(f"   the right- and left-skewed frames, whose RETURNS are exact"
          f" negatives of each other: shared {shared} bit-equal {same}"
          f" max |diff| {d:.3e}"
          f" spearman {_spearman(ts_energy_last_20(rs), ts_energy_last_20(ls)):.6f}")
    print("   ⚠ neither is bit-equality, and the reason is the FRAME and not")
    print("     the column: a sign-flipped frame is rebuilt from closes, so")
    print("     its returns are re-rounded. That the sign cannot reach the")
    print("     output is read in the code (`e = r * r`), not measured.")

    print()
    print("6. the `length` the issue gives, against its neighbours")
    for length in (10, 16, LENGTH, 40, 60):
        alt = ts_energy_last_20(close, length=length)
        print(f"   length {length:3d} (tail {_tail(length):2d})"
              f"  spearman {_spearman(col, alt):9.6f}")


# ===================================================================== A6


def section_A6():
    _head("A6  the screen prototype (two rolling sums)")
    print(f"{'frame':14s} {'masks':>5s} {'shared':>7s} {'bit-equal':>10s}"
          f" {'max |diff|':>11s} {'max ulp':>8s} {'spearman':>9s}")
    for name, make in FRAMES.items():
        close = make()
        col, pro = ts_energy_last_20(close), _prototype(close)
        masks, shared, same, d = _agree(col, pro)
        u = _ulps(col, pro)
        print(f"{name:14s} {str(masks):>5s} {shared:7d} {same:10d}"
              f" {d:11.3e} {float(u.max()):8.2f} {_spearman(col, pro):9.6f}")

    print()
    print("which of the two is closer to the correctly rounded answer, in "
          "ulps against the EXACT rational oracle")
    print(f"{'frame':14s} {'module max':>11s} {'module mean':>12s}"
          f" {'proto max':>10s} {'proto mean':>11s}")
    for name, make in FRAMES.items():
        close = make()
        ex = _exact(close)
        um = _ulps(ts_energy_last_20(close), ex)
        up = _ulps(_prototype(close), ex)
        print(f"{name:14s} {float(um.max()):11.2f} {float(um.mean()):12.3f}"
              f" {float(up.max()):10.2f} {float(up.mean()):11.3f}")

    print()
    print("the three frames built to break it")
    for name, close in (("flat", _flat()), ("ladder", _ladder()),
                        ("quiet 1e-6", _quiet())):
        col, pro = ts_energy_last_20(close), _prototype(close)
        print(f"  {name:11s} module fires {int(col.notna().sum()):4d}"
              f"  prototype {int(pro.notna().sum()):4d}"
              f"  bit-equal {_agree(col, pro)[2]:4d}")

    print()
    print("where the two part company: the guards the screen has no need of")
    base = _walk(400)
    for label, value in (("NaN", np.nan), ("inf", np.inf), ("zero", 0.0),
                         ("negative", -100.0), ("subnormal", 1e-310)):
        c = base.copy()
        c.iloc[200] = value
        print(f"  close {label:10s} at bar 200   module"
              f" {int(ts_energy_last_20(c).notna().sum()):4d}"
              f"  prototype {int(_prototype(c).notna().sum()):4d}")


# ====================================================================== B


OFFSETS = range(60, N, 40)      # 36 offsets, past the 20-bar warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
    "clustered": (_clustered(), _clustered(seed=44)),
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
        print(f"{name:14s} leaks {len(_caught(ts_energy_last_20, close, other))}"
              f" of {len(list(OFFSETS))}")
    close, other = PAIRS["walk"]
    for length in (MIN_LENGTH, 7, 60, 250):
        hits = _caught(ts_energy_last_20, close, other, length=length)
        first = int(ts_energy_last_20(close, length=length)
                    .notna().to_numpy().argmax())
        print(f"length {length:4d}     leaks {len(hits)}"
              f" of {len(list(OFFSETS))}  first fired bar {first}")


BACK_DATE_TWO = (
    "    energy = Series(out, index=close.index)",
    "    energy = Series(out, index=close.index).shift(-2)")
BACK_DATE_FULL = (
    "    energy = Series(out, index=close.index)",
    "    energy = Series(out, index=close.index).shift(-(length - 1))")
FORWARD_RETURN = (
    "        r = (px / px.shift(1) - 1.0).to_numpy()",
    "        r = (px.shift(-1) / px - 1.0).to_numpy()")
#: The write index, moved one bar earlier -- the protocol's own mutation.
WRITE_INDEX_EARLIER = (
    "    out[length - 1:] = val",
    "    out[length - 2:-1] = val")
ROLLED_WINDOW = (
    "    e = r * r",
    "    e = np.roll(r * r, -(length // 2))")
#: The BOUND's own index. A real look-ahead -- bar T's return would be kept
#: or dropped by whether bar T+1's return is in bound -- and INVISIBLE to the
#: blind sweep: on a frame where every return is in bound, `np.roll`'s wrap
#: makes it drop only the LAST return, which is never before an offset. It
#: takes the designed frame below to catch it.
FORWARD_BOUND = (
    "    r = np.where(np.abs(r) < bound, r, np.nan)",
    "    r = np.where(np.abs(np.roll(r, -1)) < bound, r, np.nan)")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "write_index_earlier": WRITE_INDEX_EARLIER,
    "rolled_window": ROLLED_WINDOW,
}
BAD_OFFSETS = range(60, N, 120)         # 12 offsets, >= length + 1 apart


def _load_mutant(old, new):
    import importlib
    import types
    real = importlib.import_module("pandas_ta.statistics.ts_energy_last_20")
    src = open(real.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_energy_last_20_mutant")
    mod.__file__ = real.__file__
    exec(compile(src.replace(old, new), real.__file__, "exec"), mod.__dict__)
    return mod


def _out_of_bound_frame(seed=23):
    """A walk whose return at every designed offset is above the module's
    own bound (|r| >= 2.120e+153), which is what the forward-bound mutant
    needs to have something to mis-read. 120 bars apart, so the frame still
    fires in between."""
    c = _walk(N, seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = c[j - 1] * 1e200
        c[j + 1] = c[j] / 1e200
    return Series(c)


def section_M():
    _head("M  the mutants")
    print(f"{'mutant':20s} {'frame':14s} {'live':5s} {'caught':>7s}"
          f" of {len(list(OFFSETS))}")
    for name, pair in MUTANTS.items():
        mod = _load_mutant(*pair)
        for frame, (close, other) in PAIRS.items():
            live = not mod.ts_energy_last_20(close).equals(
                ts_energy_last_20(close))
            hits = _caught(mod.ts_energy_last_20, close, other)
            print(f"{name:20s} {frame:14s} {str(live):5s} {len(hits):7d}")

    print()
    print("the sixth: the BOUND's own index, which the blind sweep cannot "
          "see")
    mod = _load_mutant(*FORWARD_BOUND)
    for frame, (close, other) in PAIRS.items():
        same = mod.ts_energy_last_20(close).equals(ts_energy_last_20(close))
        hits = _caught(mod.ts_energy_last_20, close, other)
        print(f"  {frame:14s} identical to the real module {same}"
              f"  caught {len(hits)} of {len(list(OFFSETS))}")

    print()
    print("and the designed probe that gives it something to change: an "
          "out-of-bound return at each offset")
    close, other = _out_of_bound_frame(), _walk(N, 97)
    real = ts_energy_last_20(close)
    print(f"  the frame fires {int(real.notna().sum())} of {N}")
    print(f"  the real module leaks"
          f" {len(_caught(ts_energy_last_20, close, other, BAD_OFFSETS))}"
          f" of {len(list(BAD_OFFSETS))}")
    # The mutant keeps an out-of-bound return, so ITS square overflows.
    # The module's own cannot -- that is what G2's warning count pins.
    with np.errstate(over="ignore"):
        hits = _caught(mod.ts_energy_last_20, close, other, BAD_OFFSETS)
        print(f"  the mutant is caught {len(hits)}"
              f" of {len(list(BAD_OFFSETS))}")
        for j in BAD_OFFSETS:
            p = close.copy()
            p.iloc[j:] = other.iloc[j:].values
            a, b = mod.ts_energy_last_20(close), mod.ts_energy_last_20(p)
            a, b = a.iloc[:j], b.iloc[:j]
            # Mask flips UNION value changes, the same definition
            # `tests/test_ts_energy_last_20.py` asserts on.
            m = a.notna() & b.notna()
            changed = (a.isna() != b.isna()).to_numpy()
            changed[m.to_numpy()] |= (a[m] != b[m]).to_numpy()
            moved = np.flatnonzero(changed).tolist()
            print(f"  at offset {j:5d} the bars it moves are {moved}"
                  f"   (derived: [J - 1] = [{j - 1}])")


# ====================================================================== C


def section_C():
    _head("C  reachability")
    print(f"{'frame':14s} {'fires':>6s}/{'n':<5s} {'distinct':>8s}"
          f" {'min':>9s} {'median':>9s} {'max':>9s} {'> 0.25':>7s}")
    for name, make in FRAMES.items():
        close = make()
        col = ts_energy_last_20(close)
        v = col.dropna()
        print(f"{name:14s} {int(col.notna().sum()):6d}/{len(close):<5d}"
              f" {v.unique().size:8d} {float(v.min()):9.6f}"
              f" {float(v.median()):9.6f} {float(v.max()):9.6f}"
              f" {int((v > TAIL / LENGTH).sum()):7d}")

    print()
    print("the two-point frame is where the distinct count is ROUNDING: "
          "every |return| is the same size, so the exact answer is "
          f"tail/length = {TAIL / LENGTH} on every window")
    v = ts_energy_last_20(_two_point()).dropna()
    u = np.sort(v.unique())
    print(f"  {u.size} distinct doubles spanning"
          f" {float(u[-1] - u[0]):.3e}, all within"
          f" {float(np.abs(u - TAIL / LENGTH).max()):.3e} of {TAIL / LENGTH}")

    print()
    print("at other lengths, on a walk")
    close = _walk()
    for length in (MIN_LENGTH, 5, 7, 21, 60, 250):
        col = ts_energy_last_20(close, length=length)
        v = col.dropna()
        print(f"length {length:4d} (tail {_tail(length):3d})"
              f"  fires {int(col.notna().sum()):5d}/{N}"
              f"  distinct {v.unique().size:5d}"
              f"  range [{float(v.min()):.3e}, {float(v.max()):.6f}]"
              f"  median {float(v.median()):.6f}")


# ====================================================================== D


def section_D():
    _head("D  scale-freedom")
    print("x8 / x64 -- bit-identical BY CONSTRUCTION (`8a / 8b` is the same "
          "double as `a / b`)")
    print(f"{'frame':14s} {'masks':>5s} {'shared':>7s} {'x8 bit-eq':>10s}"
          f" {'x64 bit-eq':>11s}")
    for name, make in FRAMES.items():
        close = make()
        base = ts_energy_last_20(close)
        m8, s8, e8, _ = _agree(base, ts_energy_last_20(close * 8.0))
        m64, s64, e64, _ = _agree(base, ts_energy_last_20(close * 64.0))
        print(f"{name:14s} {str(m8 and m64):>5s} {s8:7d} {e8:10d} {e64:11d}")

    print()
    print("at other lengths, on a walk, x8")
    close = _walk()
    for length in (MIN_LENGTH, 5, 7, 21, 60, 250):
        masks, shared, same, d = _agree(
            ts_energy_last_20(close, length=length),
            ts_energy_last_20(close * 8.0, length=length))
        print(f"length {length:4d}  masks {str(masks):5s} shared {shared:5d}"
              f" bit-equal {same:5d}")

    print()
    print("x10 / x3.7 / x0.1 / x1.0000001 -- NOT bit-identical by "
          "construction")
    print(f"{'frame':14s} {'factor':>11s} {'masks':>5s} {'bit-eq':>7s}"
          f" {'max |diff|':>11s} {'max rel':>9s} {'spearman':>9s}")
    for name, make in FRAMES.items():
        close = make()
        base = ts_energy_last_20(close)
        for k in (10.0, 3.7, 0.1, 1.0000001):
            o = ts_energy_last_20(close * k)
            masks, shared, same, d = _agree(base, o)
            m = base.notna() & o.notna()
            rel = float(((base[m] - o[m]).abs()
                         / base[m].abs().clip(lower=1e-300)).max())
            print(f"{name:14s} {k:11.7f} {str(masks):>5s} {same:7d}"
                  f" {d:11.3e} {rel:9.2e} {_spearman(base, o):9.6f}")

    print()
    print("price LEVELS, x8")
    close = _walk()
    for price in (1e-6, 1e6, 1e100):
        c = close * (price / 100.0)
        masks, shared, same, d = _agree(ts_energy_last_20(c),
                                        ts_energy_last_20(c * 8.0))
        print(f"  price {price:7.0e}  masks {masks} shared {shared}"
              f" bit-equal {same}")

    print()
    print("`price ** 2` and `price ** 0.5` are NOT rescales, and this column "
          "is NOT invariant to them")
    base = ts_energy_last_20(close)
    for power in (2.0, 0.5):
        o = ts_energy_last_20(close ** power)
        masks, shared, same, d = _agree(base, o)
        print(f"  power {power:4.1f}  bit-equal {same:5d} of {shared}"
              f"  max |diff| {d:.4f}  spearman {_spearman(base, o):.6f}")


# ====================================================================== G


def section_G():
    _head("G  the guards, the floor this module does NOT have, and locality")

    print("G1  a bad close empties the windows it sits in, and nothing "
          "earlier")
    base_close = _walk(400)
    base = ts_energy_last_20(base_close)
    worst_earlier = 0
    pairs = 0
    for label, value in (("NaN", np.nan), ("inf", np.inf), ("-inf", -np.inf),
                         ("zero", 0.0), ("negative", -100.0),
                         ("subnormal", 1e-310)):
        for j in (0, 1, 19, 200, 398, 399):
            c = base_close.copy()
            c.iloc[j] = value
            col = ts_energy_last_20(c)
            emptied = int(base.notna().sum()) - int(col.notna().sum())
            # Every bar before `j`, which is the earliest window that can
            # hold close `j` (bar T reads closes T - length .. T). The bar
            # at `j - 1` is INCLUDED on purpose: it is the one an off-by-one
            # in the window-to-bar mapping would move first. Compared
            # mask-aware, because `NaN != NaN` is True.
            a, b = base.iloc[:j], col.iloc[:j]
            earlier = int((a.isna() != b.isna()).sum())
            m = a.notna() & b.notna()
            earlier += int((a[m] != b[m]).sum())
            worst_earlier = max(worst_earlier, earlier)
            pairs += 1
            if j == 200:
                print(f"  {label:10s} at bar 200  empties {emptied:3d}"
                      f"  earlier bars moved {earlier}")
    print(f"  over {pairs} (value, position) pairs: worst earlier-bar "
          f"movement {worst_earlier}")
    for j in (0, 1, 19, 200, 398, 399):
        c = base_close.copy()
        c.iloc[j] = np.nan
        emptied = int(base.notna().sum()) - int(
            ts_energy_last_20(c).notna().sum())
        print(f"  a NaN close at bar {j:3d} empties {emptied:3d} windows")

    print()
    print("G2  the per-return bound, and what it refuses")
    bound = float(np.sqrt(np.finfo(float).max / (2 * LENGTH)))
    print(f"  bound at length {LENGTH}: {bound:.4e}")
    c = _walk(400).to_numpy().copy()
    c[200] = c[199] * (bound * 2)
    col = ts_energy_last_20(Series(c))
    print(f"  one return of {bound * 2:.3e} at bar 200:"
          f" fires {int(col.notna().sum())} of 400"
          f" (unspiked {int(base.notna().sum())})")
    # Just inside the bound: kept, and the total is still finite.
    c = _walk(400).to_numpy().copy()
    c[200] = c[199] * (bound * 0.5)
    col = ts_energy_last_20(Series(c))
    print(f"  one return of {bound * 0.5:.3e} at bar 200:"
          f" fires {int(col.notna().sum())} of 400"
          f"  value at bar 200 {float(col.iloc[200]):.6f}")
    # The bound is taken BEFORE the square, so the square cannot overflow:
    # no numpy warning escapes the module on a frame built of nothing but
    # out-of-bound returns.
    import warnings
    c = _walk(400).to_numpy().copy()
    for j in range(1, 400, 2):
        c[j] = c[j - 1] * 1e200
        c[j + 1 if j + 1 < 400 else j] = c[j] / 1e200
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        col = ts_energy_last_20(Series(c))
    print(f"  a frame of nothing but out-of-bound returns:"
          f" {len(caught)} numpy warnings, fires"
          f" {int(col.notna().sum())} of 400")

    print()
    print("G3  there is NO dispersion floor, and this is what that costs")
    for name, close in (("flat", _flat()), ("ladder", _ladder()),
                        ("quiet 1e-6", _quiet())):
        col = ts_energy_last_20(close)
        v = col.dropna()
        ex = _exact(close)
        u = _ulps(col, ex)
        print(f"  {name:11s} fires {int(col.notna().sum()):4d}"
              f"/{len(close):<4d} distinct {v.unique().size:4d}"
              f"  range [{(float(v.min()) if v.size else float('nan')):.6f},"
              f" {(float(v.max()) if v.size else float('nan')):.6f}]"
              f"  max ulp vs exact"
              f" {(float(u.max()) if u.size else float('nan')):.2f}")
    # The two siblings floor DIFFERENT statistics of the same window at the
    # same 4096 ulps: `ts_binent_20` the return RANGE (`high - low`,
    # ts_binent_20.py:75) and `ts_aggac_60` the return SD
    # (ts_aggac_60.py:27). Both are priced, because the sentence that
    # justifies shipping with no floor names both modules.
    print("  what the siblings' absolute 4096-ulp floors would empty:")
    floor = 4096 * np.finfo(float).eps
    print(f"  {'frame':11s} {'fired':>5s} {'range floor':>12s}"
          f" {'sd floor':>9s}")
    for name, close in (("flat", _flat()), ("ladder", _ladder()),
                        ("quiet 1e-6", _quiet())):
        r = _ret(close)
        rng = r.rolling(LENGTH).max() - r.rolling(LENGTH).min()
        sd = r.rolling(LENGTH).std(ddof=0)
        col = ts_energy_last_20(close)
        fired = col.notna()
        print(f"  {name:11s} {int(fired.sum()):5d}"
              f" {int((fired & (rng <= floor)).sum()):12d}"
              f" {int((fired & (sd <= floor)).sum()):9d}")

    print()
    print("G4  LOCALITY: a rolling sum carries a residue, this spelling does "
          "not")
    close = _walk(2000, seed=31) * 1e-198
    for mag in (1e2, 1e6, 1e8, 1e100, 1e300):
        c = close.to_numpy().copy()
        c[200] = c[199] * mag
        c[201] = c[200] / mag
        spiked = Series(c)
        mine_b, mine_s = ts_energy_last_20(close), ts_energy_last_20(spiked)
        pro_b, pro_s = _prototype(close), _prototype(spiked)
        # The spike sits at bars 200 and 201, so the last window that holds
        # it ends at bar 221. Everything from 222 on is a window the spike
        # has LEFT, and a local spelling must be untouched there.
        tailbars = slice(202 + LENGTH, None)
        mine_same = int((mine_b.iloc[tailbars] == mine_s.iloc[tailbars]).sum())
        pro_same = int((pro_b.iloc[tailbars] == pro_s.iloc[tailbars]).sum())
        later = int(mine_b.iloc[tailbars].notna().sum())
        print(f"  x{mag:7.0e}  module bit-identical on {mine_same:5d}"
              f" of the {later} later bars"
              f"   rolling-sum prototype on {pro_same:5d}"
              f"  (prototype fires {int(pro_s.iloc[tailbars].notna().sum())})")

    print()
    print("G5  an UNDERFLOWING square: a return below 1.49e-154 squares to "
          "zero")
    tiny = float(np.sqrt(np.finfo(float).tiny))
    print(f"  sqrt(tiny) = {tiny:.4e}; ({tiny / 2:.4e}) ** 2 ="
          f" {(tiny / 2) ** 2!r}")
    c = _from_returns(np.full(60, 1e-200))
    col = ts_energy_last_20(c)
    print(f"  60 returns of 1e-200: fires {int(col.notna().sum())} of 60"
          f" (every square underflows to 0, so the window has no energy)")
    c = _from_returns(np.concatenate([np.full(40, 1e-200),
                                      np.full(20, 1e-3)]))
    col = ts_energy_last_20(c)
    v = col.dropna()
    print(f"  40 of those then 20 honest ones: fires {int(col.notna().sum())}"
          f" of 60, range"
          f" [{(float(v.min()) if v.size else float('nan')):.6f},"
          f" {(float(v.max()) if v.size else float('nan')):.6f}]")


# ====================================================================== O


def section_O():
    _head("O  overlap")
    print("the two in-fork columns that read the SAME 20 returns' energy")
    print(f"{'frame':14s} {'TFCENTROID_20':>14s} {'TS_IMQ_20':>10s}"
          f" {'TS_CID_CE_20':>13s} {'TS_ABOVE_MEAN':>14s}"
          f" {'TS_MEDSKEW':>11s}")
    pooled = {k: [] for k in ("tf", "imq")}
    mine_pool = {k: [] for k in ("tf", "imq")}
    for name, make in FRAMES.items():
        close = make()
        col = ts_energy_last_20(close)
        tf, imq = tf_centroid_20(close), ts_imq_20(close)
        print(f"{name:14s} {_spearman(col, tf):14.6f}"
              f" {_spearman(col, imq):10.6f}"
              f" {_spearman(col, ts_cid_ce_20(close)):13.6f}"
              f" {_spearman(col, ts_above_mean_20(close)):14.6f}"
              f" {_spearman(col, ts_medskew_20(close)):11.6f}")
        for key, other in (("tf", tf), ("imq", imq)):
            m = col.notna() & other.notna()
            pooled[key].append(other[m])
            mine_pool[key].append(col[m])
    for key, label in (("tf", "TFCENTROID_20"), ("imq", "TS_IMQ_20")):
        a = pd.concat(mine_pool[key], ignore_index=True)
        b = pd.concat(pooled[key], ignore_index=True)
        per = sorted(abs(_spearman(ts_energy_last_20(make()),
                                   (tf_centroid_20 if key == "tf"
                                    else ts_imq_20)(make())))
                     for make in FRAMES.values())
        print(f"  pooled over the {len(FRAMES)} frames vs {label}:"
              f" {float(a.corr(b, method='spearman')):.6f} (n = {len(a)});"
              f" per-frame |rho| median {float(np.median(per)):.4f},"
              f" max {per[-1]:.4f},"
              f" {sum(1 for p in per if p >= 0.90)} of {len(per)} >= 0.90")

    print()
    print("vs TFCENTROID at the lengths they share, on a walk and on the "
          "clustered frame")
    for name in ("walk", "clustered"):
        close = FRAMES[name]()
        row = "  ".join(
            f"length {length}: "
            f"{_spearman(ts_energy_last_20(close, length=length), tf_centroid_20(close, length=length)):.4f}"
            for length in (8, LENGTH, 60))
        print(f"  {name:11s} {row}")

    print()
    print("volatility, which this column is NOT (it is a RECENCY of "
          "volatility)")
    print(f"{'frame':14s} {'NATR_20':>9s} {'UI_20':>9s} {'ret sd 20':>10s}"
          f" {'close':>9s} {'natr chg 5d*':>12s} {'|r| 5/20*':>10s}")
    for name, make in FRAMES.items():
        close = make()
        col = ts_energy_last_20(close)
        high, low = _ohlc(close)
        nat = natr(high=high, low=low, close=close, length=LENGTH)
        r = _ret(close)
        a = r.abs()
        ratio = a.rolling(TAIL).mean() / a.rolling(LENGTH).mean()
        print(f"{name:14s} {_spearman(col, nat):9.6f}"
              f" {_spearman(col, ui(close=close, length=LENGTH)):9.6f}"
              f" {_spearman(col, stdev(close=r, length=LENGTH)):10.6f}"
              f" {_spearman(col, close):9.6f}"
              f" {_spearman(col, nat / nat.shift(5) - 1.0):12.6f}"
              f" {_spearman(col, ratio):10.6f}")
    print("  * stand-ins for the engine's `natr_Chg_5d` and the")
    print("    `ATR_Ratio_5_20` family, built here from this fork's own")
    print("    `natr`; they are NOT the engine's columns, which only Gate E")
    print("    can see.")


# ====================================================================== S


def section_S():
    _head("S  the statistic itself")
    print("the level to expect on INDEPENDENT windows of iid returns")
    rng = np.random.default_rng(2026)
    for label, draw in (("gaussian", lambda n: rng.standard_normal(n)),
                        ("student-t(2)", lambda n: rng.standard_t(2.0, n)),
                        ("exponential",
                         lambda n: rng.standard_exponential(n) - 1.0)):
        W = draw((20000, LENGTH)) ** 2
        v = W[:, LENGTH - TAIL:].sum(axis=1) / W.sum(axis=1)
        print(f"  {label:14s} mean {v.mean():.6f} sd {v.std():.6f}"
              f"  (tail/length = {TAIL / LENGTH})")

    print()
    print("autocorrelation: windows 1 apart share 19 of their 20 returns")
    for name in ("walk", "heavy-tailed", "clustered"):
        col = ts_energy_last_20(FRAMES[name]())
        print(f"  {name:14s} lag 1 {float(col.autocorr(1)):9.6f}"
              f"  lag 5 {float(col.autocorr(TAIL)):9.6f}"
              f"  lag 20 {float(col.autocorr(LENGTH)):9.6f}"
              f"  lag 21 {float(col.autocorr(LENGTH + 1)):9.6f}")

    print()
    print("one bar moves exactly `length` bars, and only the first `tail` of "
          "them hold it in the NUMERATOR")
    close = _walk()
    base = ts_energy_last_20(close)
    spiked = close.copy()
    # x0.5 and not x0.8: a power of two rescales every LATER ratio to the
    # same double, so the only return that changes is the one at bar 700 and
    # the count below is exact rather than a threshold.
    spiked.iloc[700:] = spiked.iloc[700:] * 0.5
    out = ts_energy_last_20(spiked)
    moved = np.flatnonzero((base != out).to_numpy()
                           & base.notna().to_numpy()).tolist()
    print(f"  a -50% bar at 700 moves bars {moved[0]}..{moved[-1]}"
          f" ({len(moved)} bars, length = {LENGTH})")
    d = out - base
    print(f"  the move is POSITIVE on bars 700..{700 + TAIL - 1}"
          f" ({int((d.iloc[700:700 + TAIL] > 0).sum())} of {TAIL})"
          f" and NEGATIVE after"
          f" ({int((d.iloc[700 + TAIL:700 + LENGTH] < 0).sum())}"
          f" of {LENGTH - TAIL})")

    print()
    print("what it is FOR: it separates a frame whose energy clusters from "
          "one whose does not")
    for name in ("walk", "clustered", "two-point"):
        v = ts_energy_last_20(FRAMES[name]()).dropna()
        print(f"  {name:14s} sd {float(v.std()):.6f}"
              f"  p05 {float(v.quantile(0.05)):.6f}"
              f"  p95 {float(v.quantile(0.95)):.6f}")


# ====================================================================== Z


#: Repeats for the timing. One call per `length` is not enough: a single
#: scheduler hiccup is enough to print a non-monotone table, which review
#: round 3 caught by re-running this section four times. The MINIMUM of the
#: repeats is the figure -- it is the one a competing process can only move
#: upward -- and what §Z claims is the ORDERING and the RATIO of those
#: minima, never a millisecond.
TIME_REPEATS = 5


def section_Z():
    _head("Z  cost")
    big = _walk(400_000, seed=5)
    best = {}
    for length in (MIN_LENGTH, LENGTH, 60, 250):
        ts_energy_last_20(big, length=length)       # warm
        tracemalloc.start()
        times = []
        for _ in range(TIME_REPEATS):
            t0 = time.perf_counter()
            ts_energy_last_20(big, length=length)
            times.append((time.perf_counter() - t0) * 1000.0)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        best[length] = min(times)
        print(f"length {length:4d}  best of {TIME_REPEATS}"
              f" {min(times):7.1f} ms  (worst {max(times):7.1f})"
              f"  traced peak {peak / 1e6:6.1f} MB")
    order = list(best)
    print(f"  monotone in `length`:"
          f" {all(best[a] <= best[b] for a, b in zip(order, order[1:]))}")
    print(f"  ratio best(250) / best({MIN_LENGTH}):"
          f" {best[250] / best[MIN_LENGTH]:.2f}x")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A6": section_A6, "B": section_B, "M": section_M,
    "C": section_C, "D": section_D, "G": section_G, "O": section_O,
    "S": section_S, "Z": section_Z,
}


if __name__ == "__main__":
    # The receipt quotes these; printing them is what stops the quote from
    # being a guess about the environment it was measured in.
    print(f"pandas {pd.__version__}  numpy {np.__version__}")
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
