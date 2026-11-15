# -*- coding: utf-8 -*-
"""TS-REOCCUR-20 (PandasTa issue #103) -- every number in
`docs/TsReoccur20Measured.md` and in `tests/test_ts_reoccur_20.py`.

    python docs/measure_ts_reoccur_20.py            # every section
    python docs/measure_ts_reoccur_20.py A1 D       # named sections

Sections
    A1  the module against a per-window `value_counts()` oracle and
        against the screen prototype: BIT equality
    A2  the same at other lengths
    A3  the lattice `k / length`, and why `k = 1` is unreachable
    A4  the readings the issue's line leaves open, priced
    A5  the continuous-float frame, where the column is identically 0.0
    A6  order-blindness: the window's multiset is all it reads
    B   the causality sweep on the real module
    M   the six mutants: five the blind sweep catches, one it cannot
    C   reachability: fires, distinct values, the value histogram
    D   scale-freedom: x8 / x64 exactness, x10 / x3.7 and the merge that
        is a measurement rather than a theorem
    G   the guards: a bad close, the chunk budget, the degenerate frames
    O   overlap: what the column restates and what it does not
    L   the statistic itself: the level to expect against the tick, the
        autocorrelation, how far one close reaches
    W   what `docs/IndicatorDictionary.md` keeps of the docstring's first
        paragraph, which is 150 characters
    Z   cost
"""
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.lot_zeroret_60 import lot_zeroret_60
from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.ts_above_mean_20 import ts_above_mean_20
from pandas_ta.statistics.ts_binent_20 import ts_binent_20
from pandas_ta.statistics.ts_cross_mean_20 import ts_cross_mean_20
from pandas_ta.statistics.ts_perment_20 import ts_perment_20
from pandas_ta.statistics.ts_reoccur_20 import (CHUNK_VALUES, MIN_LENGTH,
                                                ts_reoccur_20)
from pandas_ta.volatility.natr import natr

LENGTH = 20
N = 1500
FIRED = N - LENGTH + 1      # `length` CLOSES, so the warm-up is length - 1

#: The MODULE, not the function of the same name that
#: `pandas_ta/statistics/__init__.py` binds over it in the package
#: namespace -- `import pandas_ta.statistics.ts_reoccur_20 as m` hands out
#: the function. Section G rebinds its `CHUNK_VALUES` and section M reads
#: its source off disk, so both need the module object.
mod_reoccur = __import__("importlib").import_module(
    "pandas_ta.statistics.ts_reoccur_20")


# ----------------------------------------------------------------- frames
#
# Every frame that matters here is on a TICK GRID, because exact price
# equality is what the column reads: see section A5 for the continuous
# frame, where it is identically zero. The frames are named by how many
# TICKS the price moves in a bar, which is the column's real argument --
# `price * sigma / tick` -- and the four grid frames are one 2% walk read
# at four BIST-like price levels on the same 0.01 grid.


def _walk(n=N, seed=11, sigma=0.02, price=100.0, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(price * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _grid(close, tick=0.01):
    """Quantise to a tick grid. Equal inputs give equal outputs, so the
    grid's own rounding cannot invent or destroy a repeat."""
    return Series(np.round(close.to_numpy() / tick) * tick,
                  index=close.index)


def _level(price, seed=11, tick=0.01, sigma=0.02, n=N):
    return _grid(_walk(n, seed, sigma, price), tick)


def _range_bound(n=N, seed=7, price=2.0, tick=0.01, sigma=0.02, phi=0.90):
    """An AR(1) in the LOG price, so the path keeps coming back to the
    same grid points instead of wandering off them."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal(0.0, sigma)
    return _grid(Series(price * np.exp(x)), tick)


def _heavy_tailed(n=N, seed=3, df=2.0, sigma=0.01, price=2.0, tick=0.01):
    rng = np.random.default_rng(seed)
    r = np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5)
    return _grid(Series(price * np.cumprod(1.0 + r)), tick)


def _round_numbers(n=N, seed=9, price=1000.0, tick=1.0, sigma=0.003):
    return _grid(_walk(n, seed, sigma, price), tick)


def _continuous(n=N, seed=11, price=100.0):
    """No grid at all -- the disclosure frame of section A5."""
    return _walk(n, seed, price=price)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, tick=0.01):
    """One tick up a bar: every close in a window is distinct."""
    return Series(price + tick * np.arange(n, dtype=float))


def _two_level(n=300, seed=4, price=100.0, tick=0.01):
    rng = np.random.default_rng(seed)
    return Series(np.where(rng.random(n) < 0.5, price, price + tick))


FRAMES = {
    "grid-2tick": lambda: _level(1.0),
    "grid-10tick": lambda: _level(5.0),
    "grid-40tick": lambda: _level(20.0),
    "grid-200tick": lambda: _level(100.0),
    "range-bound": _range_bound,
    "round-1000": _round_numbers,
    "heavy-tailed": _heavy_tailed,
}
NAMES = list(FRAMES)
#: Gate A / B / D read the continuous frame too, where the column is a
#: constant 0.0 -- which is a value and bit-equality still means something.
ALL_FRAMES = dict(FRAMES, **{"continuous": _continuous})
ALL_NAMES = list(ALL_FRAMES)


# ---------------------------------------------------------------- helpers


def _ohlc(close, band=0.004):
    return close * (1.0 + band), close * (1.0 - band)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    d = float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")
    return masks, int(m.sum()), int((a[m] == b[m]).sum()), d


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _pooled(pairs):
    """Spearman over the concatenation of several frames' columns."""
    a = pd.concat([p[0].reset_index(drop=True) for p in pairs],
                  ignore_index=True)
    b = pd.concat([p[1].reset_index(drop=True) for p in pairs],
                  ignore_index=True)
    return _spearman(a, b)


# ---------------------------------------------------------------- oracles


TINY = np.finfo(float).tiny


def _good(w):
    return np.isfinite(w) & (w >= TINY)


def _source_windowed(close, length=LENGTH):
    """The quantity the source's name states --
    `value_counts()[value_counts() > 1].sum() / len(x)` -- over the
    trailing `length` closes, one window at a time, through pandas' own
    counter. Shares no code with the module.

    The `_good` test is this fork's missing-data rule, not the source's:
    section A4 prices the source-literal reading separately."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not _good(w).all():
            continue
        vc = Series(w).value_counts()
        out[t] = vc[vc > 1].sum() / w.size
    return Series(out, index=close.index)


def _source_literal(close, length=LENGTH):
    """The same, with NO missing-data rule: `value_counts()` drops a NaN
    and `len(x)` keeps counting it, so a window holding a bad close reads
    a DEFLATED share instead of nothing."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = Series(c[t - length + 1:t + 1])
        vc = w.value_counts()
        out[t] = vc[vc > 1].sum() / w.size
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_reoccur_20`:
    `roll(c, 20, w_pct_reoccurring)`, retyped from that file."""
    a = close.to_numpy(dtype=float)
    W = sliding_window_view(a, length) if len(a) >= length \
        else np.empty((0, length))
    S = np.sort(W, 1)
    eq = S[:, 1:] == S[:, :-1]
    dup = np.zeros_like(S, dtype=bool)
    dup[:, 1:] |= eq
    dup[:, :-1] |= eq
    out = np.full(len(a), np.nan)
    out[length - 1:] = dup.mean(1)
    return Series(out, index=close.index)


def _windowed(close, length, f):
    """`f` over each trailing window of `length` closes, masked by this
    fork's missing-data rule -- the frame every variant below is read in."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not _good(w).all():
            continue
        out[t] = f(w)
    return Series(out, index=close.index)


def _values_variant(close, length=LENGTH):
    """tsfresh's SIBLING function
    `percentage_of_reoccurring_values_to_all_values`: the share of the
    window's DISTINCT values that are repeated, not of its bars."""
    def f(w):
        _, counts = np.unique(w, return_counts=True)
        return np.sum(counts > 1) / float(counts.size)
    return _windowed(close, length, f)


def _distinct_variant(close, length=LENGTH):
    """tsfresh's `ratio_value_number_to_time_series_length`: distinct
    values over `length`."""
    return _windowed(close, length,
                     lambda w: np.unique(w).size / float(w.size))


def _tolerant(close, length=LENGTH, rel=1e-12):
    """The same count with equality relaxed to a RELATIVE tolerance --
    the reading that would make this a dispersion measure."""
    def f(w):
        s = np.sort(w)
        eq = np.isclose(s[1:], s[:-1], rtol=rel, atol=0.0)
        dup = np.zeros(s.size, dtype=bool)
        dup[1:] |= eq
        dup[:-1] |= eq
        return dup.sum() / float(s.size)
    return _windowed(close, length, f)


def _on_returns(close, length=LENGTH):
    """The same statistic over `length` RETURNS instead of closes. A
    return can be negative, so the `_good` rule above does not apply to
    it; and `length` returns need `length + 1` closes, so this variant's
    warm-up is one bar longer than the module's -- which is why its NaN
    mask is reported as differing rather than as a failure."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        eq = s[1:] == s[:-1]
        dup = np.zeros(s.size, dtype=bool)
        dup[1:] |= eq
        dup[:-1] |= eq
        out[t] = dup.sum() / float(s.size)
    return Series(out, index=close.index)


# ===================================================== Gate A, the source


def section_A1():
    _head("A1  the module against the source's own quantity, and against "
          "the screen prototype")
    print("  tsfresh importable here:",
          __import__("importlib").util.find_spec("tsfresh") is not None)
    print(f"  {'frame':<14} {'fired':>6} {'=oracle':>8} {'=proto':>8} "
          f"{'masks':>6} {'max|d|':>8}  mean")
    total = same_o = same_p = 0
    for name in ALL_NAMES:
        close = ALL_FRAMES[name]()
        col = ts_reoccur_20(close)
        mo, no, so, do = _agree(col, _source_windowed(close))
        mp, _, sp, _ = _agree(col, _prototype(close))
        total += no
        same_o += so
        same_p += sp
        print(f"  {name:<14} {no:>6} {so:>8} {sp:>8} {str(mo and mp):>6} "
              f"{do:>8.1e}  {col.mean():.4f}")
    print(f"  pooled: {same_o} of {total} bit-equal to the oracle, "
          f"{same_p} of {total} to the prototype")


def section_A2():
    _head("A2  the same at other lengths")
    close = _level(1.0)
    print(f"  {'length':>6} {'fired':>6} {'=oracle':>8} {'=proto':>8} "
          f"{'masks':>6}  mean")
    for length in (MIN_LENGTH, 3, 5, 21, 60, 250):
        col = ts_reoccur_20(close, length=length)
        mo, no, so, _ = _agree(col, _source_windowed(close, length))
        mp, _, sp, _ = _agree(col, _prototype(close, length))
        print(f"  {length:>6} {no:>6} {so:>8} {sp:>8} {str(mo and mp):>6}"
              f"  {col.mean():.4f}")
        assert no == N - length + 1, (length, no)


def section_A3():
    _head("A3  the lattice k / length, and k = 1")
    for length in (MIN_LENGTH, 3, LENGTH, 60):
        ks, off = set(), 0.0
        for name in ALL_NAMES:
            k = ts_reoccur_20(ALL_FRAMES[name](),
                              length=length).dropna().to_numpy() * length
            ks |= set(np.round(k).astype(int).tolist())
            off = max(off, float(np.abs(k - np.round(k)).max()))
        print(f"  length {length:>3}: {len(ks)} k values reached, "
              f"{sorted(ks)}")
        print(f"              1 present: {1 in ks}   max |k - round(k)| "
              f"over all eight frames: {off:.1e}  (the lattice is exact as "
              f"a RATIONAL; multiplying the share back by `length` rounds "
              f"a second time)")
    print("  the closed forms:")
    for length in (MIN_LENGTH, 3, LENGTH, 60):
        flat = ts_reoccur_20(_flat(300), length=length).dropna()
        lad = ts_reoccur_20(_ladder(300), length=length).dropna()
        print(f"    length {length:>3}: flat frame max |x - 1.0| "
              f"{float((flat - 1.0).abs().max()):.1e} on {flat.size} bars, "
              f"ladder max |x| {float(lad.abs().max()):.1e} on {lad.size}")
    print("  two grid points only -- the reachable set is {1.0, "
          "(length - 1) / length}, and at length 2 {1.0, 0.0}:")
    for length in (MIN_LENGTH, 3, LENGTH, 60):
        two = ts_reoccur_20(_two_level(300), length=length).dropna()
        h = two.value_counts(normalize=True).sort_index()
        print(f"    length {length:>3}: {two.size} bars, "
              + "  ".join(f"{k:.4f}:{v:.4f}" for k, v in h.items()))


def section_A4():
    _head("A4  the readings the issue's line leaves open, priced")
    rows = []
    for name in NAMES:
        close = FRAMES[name]()
        base = ts_reoccur_20(close)
        for key, other in (
                ("values_to_all_values", _values_variant(close)),
                ("distinct/length", _distinct_variant(close)),
                ("has_duplicate (x > 0)", (base > 0).astype(float)
                 .where(base.notna())),
                ("tolerance 1e-12", _tolerant(close, rel=1e-12)),
                ("tolerance 1e-4", _tolerant(close, rel=1e-4)),
                ("on 20 RETURNS", _on_returns(close)),
        ):
            masks, shared, same, d = _agree(base, other)
            rows.append((name, key, masks, shared, same, d,
                         _spearman(base, other), other.dropna().nunique()))
    print(f"  {'frame':<13} {'variant':<22} {'masks':>5} {'shared':>7} "
          f"{'bit-eq':>7} {'max|d|':>8} {'rho':>8} {'distinct':>8}")
    for name, key, masks, shared, same, d, rho, nu in rows:
        print(f"  {name:<13} {key:<22} {str(masks):>5} {shared:>7} "
              f"{same:>7} {d:>8.4f} {rho:>8.4f} {nu:>8}")
    const = sorted(name for name, key, *_rest, nu in rows
                   if key.startswith("has_duplicate") and nu == 1)
    print(f"  (`rho` is nan where the VARIANT is constant on that frame. "
          f"`has_duplicate` is constant on {len(const)} of {len(NAMES)} "
          f"grid frames: {const} -- counted here rather than by eye)")

    print("\n  the missing-data rule, which is the fork's and not the "
          "source's:")
    base = _level(1.0, n=400)
    for value in (np.nan, np.inf, 0.0, -100.0, 5e-324):
        c = base.copy()
        c.iloc[200] = value
        mine = ts_reoccur_20(c)
        lit = _source_literal(c)
        m = mine.isna() & lit.notna()
        vals = lit[m]
        print(f"    close[200] = {value!r:<10} module fires "
              f"{int(mine.notna().sum()):>4}, source-literal "
              f"{int(lit.notna().sum()):>4}, the {int(m.sum())} bars they "
              f"differ on read "
              f"{(f'{vals.min():.2f} .. {vals.max():.2f}' if int(m.sum()) else '-')}")


def section_A5():
    _head("A5  the continuous-float frame: identically zero, and that is "
          "the feature")
    for price in (1.0, 100.0, 1e6):
        close = _continuous(price=price)
        col = ts_reoccur_20(close)
        print(f"  continuous walk at price {price:>9.0f}: fires "
              f"{int(col.notna().sum())}, distinct values "
              f"{col.dropna().nunique()}, max {float(col.max()):.4f}")
    close = _continuous()
    print(f"  the SAME path on a 0.01 grid at price 1: "
          f"mean {float(ts_reoccur_20(_grid(close / 100.0)).mean()):.4f}")
    print("  float ties in the raw walk itself:",
          f"{int(_continuous().duplicated().sum())} duplicated closes of "
          f"{N}")


def section_A6():
    _head("A6  order-blindness: the multiset is all it reads")
    rng = np.random.default_rng(5)
    close = _level(1.0)
    w = close.iloc[:LENGTH].to_numpy()
    base = float(ts_reoccur_20(Series(w)).iloc[-1])
    same = 0
    trials = 2000
    for _ in range(trials):
        p = rng.permutation(w)
        same += float(ts_reoccur_20(Series(p)).iloc[-1]) == base
    print(f"  one window, {trials} random permutations: {same} of {trials} "
          f"bit-identical (value {base})")
    # The frame-level consequence: a window of the REVERSED frame is a
    # window of the original, reversed, so the whole column reverses.
    rev = Series(close.to_numpy()[::-1])
    a = ts_reoccur_20(close).dropna().to_numpy()
    b = ts_reoccur_20(rev).dropna().to_numpy()
    print(f"  the frame reversed: the column is the original REVERSED, "
          f"bit for bit on {int((b == a[::-1]).sum())} of {a.size} fired "
          f"bars -- so the column cannot tell a window from its reverse")
    for name in NAMES:
        c2 = FRAMES[name]()
        x = ts_reoccur_20(c2).dropna().to_numpy()
        y = ts_reoccur_20(Series(c2.to_numpy()[::-1])).dropna().to_numpy()
        print(f"    {name:<13} {int((y == x[::-1]).sum())} of {x.size}")


# ========================================================= Gate B, by mutant


OFFSETS = range(60, N, 40)              # 36 offsets, past the 19-bar warm-up
BAD_OFFSETS = range(60, N, 120)         # 12 offsets, >= length apart
PAIRS = {
    "grid-2tick": (_level(1.0), _level(1.0, seed=97)),
    "grid-10tick": (_level(5.0), _level(5.0, seed=97)),
    "grid-40tick": (_level(20.0), _level(20.0, seed=97)),
    "range-bound": (_range_bound(), _range_bound(seed=44)),
}

BACK_DATE_TWO = (
    "    share = Series(out, index=close.index)",
    "    share = Series(out, index=close.index).shift(-2)")
BACK_DATE_FULL = (
    "    share = Series(out, index=close.index)",
    "    share = Series(out, index=close.index).shift(-(length - 1))")
WRITE_INDEX_EARLIER = (
    "    out[length - 1:] = val",
    "    out[length - 2:-1] = val")
FORWARD_WINDOW = (
    "    w = sliding_window_view(c, length)",
    "    w = sliding_window_view(np.roll(c, -1), length)")
CENTRED_WINDOW = (
    "    w = sliding_window_view(c, length)",
    "    w = sliding_window_view(np.roll(c, -(length // 2)), length)")
#: The bad-close mask's own index. A real look-ahead, and INVISIBLE to the
#: blind sweep: see section M.
SHIFTED_BAD_MASK = (
    "    holds_bad = (nbad[length:] - nbad[:rows]) > 0",
    "    holds_bad = np.roll((nbad[length:] - nbad[:rows]) > 0, -1)")

#: Each look-ahead mutant with the number of bars it back-dates the column
#: by -- DERIVED from the edit, and then checked bit for bit by
#: `_back_dated_by`, which is a stronger statement than the blind sweep's
#: count and does not depend on the column happening to change at an
#: offset. `write_index_earlier` writes each value one bar early;
#: `forward_window` reads each window one bar late, which is the same
#: displacement by a different route; `centred_window` reads `length // 2`
#: bars late.
MUTANTS = {
    "back_date_two": (BACK_DATE_TWO, 2),
    "back_date_full": (BACK_DATE_FULL, LENGTH - 1),
    "write_index_earlier": (WRITE_INDEX_EARLIER, 1),
    "forward_window": (FORWARD_WINDOW, 1),
    "centred_window": (CENTRED_WINDOW, LENGTH // 2),
}


def _load_mutant(old, new):
    import types
    with open(mod_reoccur.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    m = types.ModuleType("_ts_reoccur_20_mutant")
    m.__file__ = mod_reoccur.__file__
    exec(compile(src.replace(old, new), m.__file__, "exec"), m.__dict__)
    return m


def _caught(fn, close, other, offsets=OFFSETS, **kwargs):
    """Offsets at which replacing bars `j:` moves anything BEFORE `j`."""
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
        hits = _caught(ts_reoccur_20, close, other)
        first = int(ts_reoccur_20(close).notna().to_numpy().argmax())
        print(f"  {name:<13} leaks at {len(hits)} of "
              f"{len(list(OFFSETS))} offsets {hits}, first fired bar {first}")
    close, other = PAIRS["grid-2tick"]
    for length in (MIN_LENGTH, 7, 60, 250):
        hits = _caught(ts_reoccur_20, close, other, length=length)
        first = int(ts_reoccur_20(close, length=length)
                    .notna().to_numpy().argmax())
        print(f"  length {length:>3}:   leaks at {len(hits)} offsets, "
              f"first fired bar {first} (length - 1 = {length - 1})")


def _bad_close_frame(seed=23, value=np.nan):
    """A grid walk with a BAD close at every designed offset -- what the
    shifted-mask mutant needs in order to mis-read anything."""
    c = _level(1.0, seed=seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = value
    return Series(c)


def _back_dated_by(mutant, real, k, length=LENGTH):
    """(bars compared, bars where the mutant IS the real column read `k`
    bars later).

    The tail is excluded because `np.roll` wraps: a row that would read
    past the last bar reads the first ones instead, so only bars
    `length - 1 .. n - 1 - k` are the clean statement."""
    hi = real.size - 1 - k
    a = mutant.iloc[length - 1:hi + 1].to_numpy()
    b = real.iloc[length - 1 + k:hi + 1 + k].to_numpy()
    return a.size, int(((a == b) | (np.isnan(a) & np.isnan(b))).sum())


def _changes(col):
    """How often the column differs from its own previous bar -- the rate
    the blind sweep's catch count is bounded by."""
    d = col.dropna().to_numpy()
    return float((d[1:] != d[:-1]).mean())


def section_M():
    _head("M  the mutants")
    print("  the churn that bounds a blind sweep: share of adjacent fired "
          "bars where the column CHANGES")
    for name in PAIRS:
        print(f"    {name:<13} {_changes(ts_reoccur_20(PAIRS[name][0])):.4f}")
    print()
    for key, ((old, new), k) in MUTANTS.items():
        m = _load_mutant(old, new)
        line = []
        for name, (close, other) in PAIRS.items():
            real = ts_reoccur_20(close)
            got = m.ts_reoccur_20(close)
            live = not got.equals(real)
            hits = _caught(m.ts_reoccur_20, close, other)
            n, same = _back_dated_by(got, real, k)
            line.append(f"{name} live={live} caught={len(hits)} "
                        f"=real(+{k}) {same}/{n}")
        print(f"  {key:<20} " + "\n" + "".join(
            f"      {c}\n" for c in line), end="")

    print("\n  the sixth, which the blind sweep cannot catch:")
    m = _load_mutant(*SHIFTED_BAD_MASK)
    for name, (close, other) in PAIRS.items():
        live = not m.ts_reoccur_20(close).equals(ts_reoccur_20(close))
        hits = _caught(m.ts_reoccur_20, close, other)
        print(f"    {name:<13} live on a clean frame={live}, "
              f"caught at {len(hits)} of {len(list(OFFSETS))} offsets")
    close, other = _bad_close_frame(), _level(1.0, seed=97)
    print(f"    on a frame with a bad close at each of "
          f"{len(list(BAD_OFFSETS))} offsets:")
    print(f"      real module  caught at "
          f"{len(_caught(ts_reoccur_20, close, other, BAD_OFFSETS))}")
    hits = _caught(m.ts_reoccur_20, close, other, BAD_OFFSETS)
    print(f"      mutant       caught at {len(hits)} of "
          f"{len(list(BAD_OFFSETS))}")
    moved_all = []
    for j in BAD_OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        a, b = m.ts_reoccur_20(close).iloc[:j], m.ts_reoccur_20(p).iloc[:j]
        mm = (a.notna() & b.notna()).to_numpy()
        changed = (a.isna() != b.isna()).to_numpy()
        changed[mm] |= (a[a.notna() & b.notna()]
                        != b[a.notna() & b.notna()]).to_numpy()
        moved_all.append(np.flatnonzero(changed).tolist())
    print(f"      the bars it moves, per offset: "
          f"{[[x - j for x in mv] for mv, j in zip(moved_all, BAD_OFFSETS)]}"
          f" (relative to the offset)")


# ============================================================ Gate C and D


def section_C():
    _head("C  reachability")
    print(f"  {'frame':<14} {'fires':>6} {'of':>6} {'distinct':>9} "
          f"{'min':>6} {'max':>6} {'mean':>7}  {'zeros':>6}")
    for name in ALL_NAMES:
        col = ts_reoccur_20(ALL_FRAMES[name]())
        d = col.dropna()
        print(f"  {name:<14} {int(col.notna().sum()):>6} {col.size:>6} "
              f"{d.nunique():>9} {float(d.min()):>6.2f} "
              f"{float(d.max()):>6.2f} {float(d.mean()):>7.4f} "
              f"{int((d == 0.0).sum()):>6}")
    print("\n  the value histogram on the grid frames (share of fired "
          "bars):")
    for name in NAMES:
        col = ts_reoccur_20(FRAMES[name]()).dropna()
        h = col.value_counts().sort_index()
        print(f"    {name:<13} " + "  ".join(
            f"{k:.2f}:{n / col.size:.3f}({n})"
            for k, n in list(h.items())[:8]))
    print("    (share of fired bars, then the raw bar count -- a share "
          "printed to three places cannot be read back as a count)")


def section_D():
    _head("D  scale-freedom")
    print("  x8 / x64, which are EXACT and so cannot merge or split a tie:")
    print(f"  {'frame':<14} {'fired':>6} {'=x8':>6} {'=x64':>6} {'masks':>6}")
    for name in ALL_NAMES:
        close = ALL_FRAMES[name]()
        base = ts_reoccur_20(close)
        m8, n8, s8, _ = _agree(base, ts_reoccur_20(close * 8.0))
        m64, _, s64, _ = _agree(base, ts_reoccur_20(close * 64.0))
        print(f"  {name:<14} {n8:>6} {s8:>6} {s64:>6} "
              f"{str(m8 and m64):>6}")
    close = _level(1.0)
    print("  at other lengths (grid-2tick):", end=" ")
    for length in (MIN_LENGTH, 3, 5, 21, 60, 250):
        base = ts_reoccur_20(close, length=length)
        _, n, s, _ = _agree(base, ts_reoccur_20(close * 8.0, length=length))
        print(f"{length}:{s}/{n}", end="  ")
    print()
    print("  at extreme price levels (the frame itself moved there, then "
          "x8):", end=" ")
    for factor in (1e-6, 1e6, 1e100):
        f = Series(close.to_numpy() * factor)
        _, n, s, _ = _agree(ts_reoccur_20(f), ts_reoccur_20(f * 8.0))
        print(f"{factor:.0e}:{s}/{n}", end="  ")
    print()

    print("\n  x10 / x3.7 / x0.1 / x1.0000001 -- NOT exact, and a merge is "
          "the failure mode:")
    print(f"  {'frame':<14} " + " ".join(f"{k:>18}" for k in
                                         ("x10", "x3.7", "x0.1",
                                          "x1.0000001")))
    for name in ALL_NAMES:
        close = ALL_FRAMES[name]()
        base = ts_reoccur_20(close)
        cells = []
        for k in (10.0, 3.7, 0.1, 1.0000001):
            masks, n, s, d = _agree(base, ts_reoccur_20(close * k))
            # The merge count is its OWN measurement: bit-equality does
            # not imply it. Two closes that merge inside a window where
            # both already had a twin leave the duplicate count -- and so
            # the column -- untouched.
            merged = (np.unique(close.to_numpy()).size
                      - np.unique((close * k).to_numpy()).size)
            cells.append(f"{s}/{n} m{merged}{'' if masks else ' MASK'}")
        print(f"  {name:<14} " + " ".join(f"{c:>18}" for c in cells))
    print("  (a cell is bit-equal bars over shared bars, then `m` the "
          "number of distinct closes the rescale LOST on the whole frame; "
          "a scale can only MERGE two closes, never split a tie, because "
          "equal doubles scale to the same double)")

    print("\n  a frame built to FORCE a merge -- 20 CONSECUTIVE doubles, "
          "so neighbours are one ulp apart:")
    for p in (1.9, 1.0):
        vals = [p]
        for _ in range(19):
            vals.append(float(np.nextafter(vals[-1], np.inf)))
        c = Series(vals)
        cells = []
        for k in (1.0, 8.0, 64.0, 10.0, 3.7, 0.1):
            u = np.unique((c * k).to_numpy()).size
            cells.append(f"x{k:g}: {u}/20 distinct, "
                         f"{float(ts_reoccur_20(c * k).iloc[-1]):.2f}")
        print(f"    from {p}: " + "  ".join(cells))

    print("\n  power maps, which are monotone but round:")
    for name in NAMES:
        close = FRAMES[name]()
        base = ts_reoccur_20(close)
        for power in (2.0, 0.5):
            masks, n, s, d = _agree(base, ts_reoccur_20(close ** power))
            print(f"    {name:<13} price ** {power}: {s} of {n} bit-equal, "
                  f"masks {masks}, max |d| {d:.4f}")

    print("\n  the tick grid is NOT part of the column: the same path "
          "quantised at two price levels")
    path = _walk(seed=11)
    for price in (5.0, 500.0):
        f = _grid(path * (price / 100.0))
        col = ts_reoccur_20(f)
        print(f"    price {price:>6.0f} on a 0.01 grid: mean "
              f"{float(col.mean()):.4f}, fires "
              f"{int(col.notna().sum())}, distinct {col.dropna().nunique()}")


# ===================================================== guards and locality


def section_G():
    _head("G  the guards")
    base = _level(1.0, n=400)
    print("  a bad close empties the windows it sits in and nothing "
          "earlier:")
    for value in (np.nan, np.inf, -np.inf, 0.0, -100.0, 5e-324):
        for pos in (0, 1, 18, 200, 398, 399):
            c = base.copy()
            c.iloc[pos] = value
            col = ts_reoccur_20(c)
            clean = ts_reoccur_20(base)
            emptied = int(clean.notna().sum()) - int(col.notna().sum())
            before = 0
            if pos > 0:
                a, b = clean.iloc[:pos], col.iloc[:pos]
                mm = a.notna() & b.notna()
                before = int((a.isna() != b.isna()).sum()) \
                    + int((a[mm] != b[mm]).sum())
            print(f"    {value!r:<10} at {pos:>3}: "
                  f"{emptied:>3} windows emptied, {before} earlier bars "
                  f"moved")
    print("  (a bad close spoils the `length` windows that hold it, fewer "
          "near either end)")

    print("\n  the chunk budget cannot change a value:")
    close = _level(1.0, n=600)
    want = ts_reoccur_20(close)
    try:
        for budget in (1, 20, 999, 10 ** 9):
            mod_reoccur.CHUNK_VALUES = budget
            got = ts_reoccur_20(close)
            print(f"    CHUNK_VALUES = {budget:>10}: identical "
                  f"{got.equals(want)}  (rows per chunk "
                  f"{max(1, budget // LENGTH)})")
    finally:
        mod_reoccur.CHUNK_VALUES = CHUNK_VALUES

    print("\n  the degenerate frames, which are READINGS and not NaN:")
    for key, frame in (("flat (300 x 100.0)", _flat(300)),
                       ("one tick a bar", _ladder(300)),
                       ("two grid points", _two_level(300))):
        col = ts_reoccur_20(frame)
        d = col.dropna()
        print(f"    {key:<20} fires {int(col.notna().sum()):>3}, "
              f"{float(d.min()):.2f} .. {float(d.max()):.2f}, distinct "
              f"{d.nunique()}")

    print("\n  float errors on a frame of nothing but bad closes, under "
          "np.errstate(all='raise') -- the module's only arithmetic is an "
          "integer division, so there is nothing to raise:")
    with np.errstate(all="raise"):
        for key, frame in (("all-NaN", Series(np.full(400, np.nan))),
                           ("400 zeros", Series(np.zeros(400))),
                           ("400 negatives", Series(np.full(400, -1.0)))):
            print(f"    {key:<14} fires "
                  f"{int(ts_reoccur_20(frame).notna().sum())} of 400, "
                  f"0 float errors raised")

    print("\n  too short an input, and the shortest that fires:")
    print(f"    {LENGTH - 1} closes: {ts_reoccur_20(_level(1.0, n=LENGTH - 1))}")
    print(f"    {LENGTH} closes: fires "
          f"{int(ts_reoccur_20(_level(1.0, n=LENGTH)).notna().sum())}")


# ===================================================== overlap, section O


def section_O():
    _head("O  overlap")
    comparators = {}
    per_frame = {}
    pooled_pairs = {}
    for name in NAMES:
        close = FRAMES[name]()
        high, low = _ohlc(close)
        r = close / close.shift(1) - 1.0
        base = ts_reoccur_20(close)
        others = {
            "LOT_ZERORET_20": lot_zeroret_60(close, length=LENGTH),
            "LOT_ZERORET_60": lot_zeroret_60(close),
            "NATR_20": natr(high, low, close, length=LENGTH),
            "stdev(r, 20)": stdev(r, length=LENGTH),
            "stdev(close, 20)": stdev(close, length=LENGTH),
            "TS_BINENT_20": ts_binent_20(close),
            "TS_PERMENT_20": ts_perment_20(close),
            "TS_ABOVE_MEAN_20": ts_above_mean_20(close),
            "TS_CROSS_MEAN_20": ts_cross_mean_20(close),
            "distinct/20": _distinct_variant(close),
        }
        for key, col in others.items():
            per_frame.setdefault(key, {})[name] = _spearman(base, col)
            pooled_pairs.setdefault(key, []).append((base, col))
        comparators[name] = others
    print(f"  {'comparator':<18} {'pooled':>8} {'median':>8} {'min':>8} "
          f"{'max':>8}   per frame")
    for key in pooled_pairs:
        vals = [v for v in per_frame[key].values() if np.isfinite(v)]
        a = np.abs(vals)
        print(f"  {key:<18} {_pooled(pooled_pairs[key]):>8.4f} "
              f"{np.median(a):>8.4f} {a.min():>8.4f} {a.max():>8.4f}   "
              + " ".join(f"{v:+.3f}" for v in vals))
    print(f"  (n per frame {FIRED}, {len(NAMES)} frames; pooled is the "
          f"signed Spearman over the concatenation, the rest are |rho|)")

    # The EXACT relation to the zero-return share, which is what makes
    # "not the same feature" a derivation rather than a correlation. At
    # length 19 the two read the same 20 closes (19 returns need 20), and
    # a run of k zero returns is k+1 equal closes, so with m runs the
    # count is at least sum(k) + m.
    print("\n  against LOT_ZERORET at length 19, which reads the SAME 20 "
          "closes:")
    for name in NAMES:
        close = FRAMES[name]()
        a = ts_reoccur_20(close)
        b = lot_zeroret_60(close, length=LENGTH - 1)
        m = a.notna() & b.notna()
        zeros = np.round(b[m].to_numpy() * (LENGTH - 1)).astype(int)
        count = np.round(a[m].to_numpy() * LENGTH).astype(int)
        hit = zeros > 0
        print(f"    {name:<13} bound count >= zeros + 1 holds on "
              f"{int((count[hit] >= zeros[hit] + 1).sum())} of "
              f"{int(hit.sum())} bars with a zero return; "
              f"{int((count[~hit] > 0).sum())} of {int((~hit).sum())} bars "
              f"with NO zero return still fire")

    # Why the pooled figure above is NOT the per-frame one. Four of the
    # seven frames are the same path read at four price levels, so a pooled
    # correlation partly measures the LEVEL each regime sits at, which both
    # this column and any other tick-grid column share. Pooling seven
    # frames of the SAME regime takes that term out.
    print("\n  pooling across tick regimes vs pooling within one "
          "(7 frames each):")
    one = [_level(1.0, seed=s) for s in (11, 97, 5, 23, 44, 56, 8)]
    for key, fn in (("LOT_ZERORET_20",
                     lambda c: lot_zeroret_60(c, length=LENGTH)),
                    ("LOT_ZERORET_60", lot_zeroret_60),
                    ("stdev(close, 20)",
                     lambda c: stdev(c, length=LENGTH)),
                    ("distinct/20", _distinct_variant)):
        pairs = [(ts_reoccur_20(c), fn(c)) for c in one]
        per = [abs(_spearman(a, b)) for a, b in pairs]
        mixed = _pooled(pooled_pairs[key])
        print(f"    {key:<18} same-regime pooled {_pooled(pairs):>8.4f}, "
              f"per-frame median {np.median(per):.4f} "
              f"({min(per):.4f} .. {max(per):.4f}),   "
              f"mixed-regime pooled {mixed:>8.4f}")


# ============================================= the statistic, section L


def section_L():
    _head("L  the statistic itself")
    print("  the level against the tick, on independent-ish grid walks "
          "(n = 20,000 bars each):")
    print(f"  {'ticks/bar':>10} {'mean':>8} {'sd':>8} {'share 0':>8} "
          f"{'share 1':>8} {'distinct':>9}")
    for ticks in (1, 2, 3, 5, 10, 20, 50, 100):
        sigma = ticks * 0.01 / 100.0        # price 100, tick 0.01
        col = ts_reoccur_20(_grid(_walk(20000, 31, sigma, 100.0))).dropna()
        print(f"  {ticks:>10} {float(col.mean()):>8.4f} "
              f"{float(col.std()):>8.4f} {float((col == 0).mean()):>8.4f} "
              f"{float((col == 1).mean()):>8.4f} {col.nunique():>9}")

    print("\n  how long it remembers (autocorrelation of the column "
          "itself):")
    print(f"  {'frame':<14} {'lag1':>8} {'lag5':>8} {'lag19':>8} "
          f"{'lag20':>8} {'lag40':>8}")
    for name in NAMES:
        col = ts_reoccur_20(FRAMES[name]())
        cells = []
        for lag in (1, 5, 19, 20, 40):
            cells.append(_spearman(col, col.shift(lag)))
        print(f"  {name:<14} " + " ".join(f"{v:>8.4f}" for v in cells))

    print("\n  how far one close reaches:")
    close = _level(1.0, n=600)
    base = ts_reoccur_20(close)
    for j in (100, 300, 500):
        for bump in (0.01, 0.50):
            c = close.copy()
            c.iloc[j] = c.iloc[j] + bump
            got = ts_reoccur_20(c)
            m = base.notna() & got.notna()
            moved = np.flatnonzero((base[m] != got[m]).to_numpy()
                                   | (base.isna() != got.isna()).to_numpy()
                                   [m.to_numpy()])
            idx = base.index[m][moved]
            span = (int(idx.min()) - j, int(idx.max()) - j) if len(idx) \
                else None
            print(f"    close[{j}] += {bump}: {len(idx)} bars moved, "
                  f"relative span {span} (length = {LENGTH})")


# ================================================================== cost


def section_Z():
    _head("Z  cost")
    lengths = (MIN_LENGTH, LENGTH, 60, 250)
    big = _grid(_walk(400000, 17))
    print("  traced peak on 400,000 bars:")
    for length in lengths:
        tracemalloc.start()
        ts_reoccur_20(big, length=length)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"    length {length:>4}: {peak / 1e6:>7.1f} MB")
    mid = _grid(_walk(100000, 17))
    print("  best of 3, on 100,000 bars, three whole runs:")
    for run in range(3):
        best = {}
        for length in lengths:
            t = []
            for _ in range(3):
                t0 = time.perf_counter()
                ts_reoccur_20(mid, length=length)
                t.append(time.perf_counter() - t0)
            best[length] = min(t)
        order = list(lengths)
        print(f"    run {run}: "
              + "  ".join(f"{k}:{best[k] * 1e3:.0f}ms" for k in order)
              + f"   monotone {all(best[a] <= best[b] for a, b in zip(order, order[1:]))}"
              f"   250/{MIN_LENGTH} = {best[250] / best[MIN_LENGTH]:.2f}x")


def _generator():
    """`docs/gen_indicator_dictionary.py`, imported by path. §W calls its
    `desc()` rather than modelling it: the cut is NOT `d[:150]`, it is
    `d[:150].rsplit(" ", 1)[0] + "…"` (line 294), which drops the last
    word -- so a reimplementation off by one word is a reimplementation
    off by one character of slack, and that is the whole thing §W
    exists to get right."""
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    spec = importlib.util.spec_from_file_location("_gen_dict", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _grown(flat, k):
    """The same paragraph with `k` characters added to the warning's last
    word, so the two sentences are `k` longer and nothing else moves."""
    i = flat.index("prices.")
    return flat[:i] + "prices" + "x" * k + flat[i + len("prices"):]


def section_W():
    """What the generated dictionary keeps of the docstring. A character
    count written by hand is the kind of claim this repo is bad at, and
    it is the one that decides whether the ⚠ warning survives the
    150-character cut in `docs/gen_indicator_dictionary.py`."""
    _head("W  the first paragraph, as docs/IndicatorDictionary.md cuts it")
    gen = _generator()
    para = ts_reoccur_20.__doc__.split("\n\n")[1]
    flat = " ".join(para.split())
    # Everything before the parenthetical, whatever that parenthetical
    # currently says: the two sentences hold no "(" of their own.
    warning = flat[:flat.index("(")].rstrip()
    kept = gen.desc({"desc": flat})
    print(f"  the two sentences that have to survive are {len(warning)} "
          f"characters, and the generator keeps {len(kept) - 1} of the "
          f"paragraph (its limit is 150, then rsplit on a space)")
    print(f"  the generator's own desc() returns: {kept!r}")
    print(f"  the warning survives it: {warning in kept}")
    # The slack, found by GROWING the warning until the generator's own
    # cut loses it -- not by subtracting from 150.
    slack = 0
    while True:
        grown = _grown(flat, slack + 1)
        if ("prices" + "x" * (slack + 1) + ".") not in gen.desc(
                {"desc": grown}):
            break
        slack += 1
        if slack > 40:                      # a runaway guard, never hit
            break
    print(f"  characters the warning could still grow by: {slack} "
          f"(so its usable length is {len(warning) + slack}, not 150: "
          f"the trailing word is dropped whole)")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A6": section_A6, "B": section_B, "M": section_M,
    "C": section_C, "D": section_D, "G": section_G, "O": section_O,
    "L": section_L, "W": section_W, "Z": section_Z,
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
