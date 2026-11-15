# -*- coding: utf-8 -*-
"""Every number in `docs/TfZeroCross20Measured.md` and in the docstrings of
`pandas_ta/statistics/tf_zero_cross_20.py` and
`tests/test_tf_zero_cross_20.py` is printed by this script.

    python docs/measure_tf_zero_cross_20.py            # every section
    python docs/measure_tf_zero_cross_20.py A1 D L     # named sections

Sections: A1 the screen prototype, A2 the prototype at other lengths,
A3 the window-by-window oracle, A4 the readings this port did NOT take,
A5 the anchors (what a known process must read), A6 whether the source is
readable here, A7 the flat return, B causality, C reachability, D scale,
G the guards, L what the column reads and what it overlaps, W the dictionary
cut, Z cost.

The run ends with a DIGEST line, the sha1 of everything the deterministic
sections printed. `docs/measure_tf_zero_cross_20_cpu.py` prints the digest of
the same sections with numpy's AVX-512/AVX2/FMA3 dispatch disabled: the two
digests being EQUAL is how this port claims that not one printed figure moves
with the CPU, rather than claiming it from the arithmetic. Z is left out of
the digest because it reports traced memory peaks, which are a property of
the run.
"""
from __future__ import annotations

import hashlib
import io
import re
import sys
import tracemalloc
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series, date_range

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20  # noqa: E402
from pandas_ta.statistics.mad import mad  # noqa: E402
from pandas_ta.statistics.stdev import stdev  # noqa: E402
from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20  # noqa: E402
from pandas_ta.statistics.ts_cross_mean_20 import ts_cross_mean_20  # noqa: E402
from pandas_ta.statistics.tf_zero_cross_20 import (  # noqa: E402
    MIN_LENGTH, tf_zero_cross_20,
)

N = 1500
LEVEL = 100.0
LENGTH = 20
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_zero_cross_20.py"


# ------------------------------------------------------------------ frames

def _series(close):
    return Series(close, index=date_range("2020-01-01", periods=close.size,
                                          freq="h"))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))))


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _series(level * np.exp(x))


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    """A walk rounded to a tick, so consecutive closes can be EQUAL -- the
    only way a simple return reaches exactly 0.0, and the regime this
    column's three-valued sign is decided in."""
    return np.round(_walk(seed, n, level) / tick) * tick


def _coarse(seed=17, n=N, level=LEVEL, tick=0.5):
    """The same walk on a far coarser grid: 0.5 against a 1% daily move, so
    flat bars are common rather than rare."""
    return _grid(seed, n, level, tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)))


def _jump(seed=23, n=N, level=LEVEL):
    c = _walk(seed, n, level)
    return c * Series(np.where(np.arange(n) >= n // 2, 1.5, 1.0), index=c.index)


def _from_returns(r, level=LEVEL):
    """A close path whose `pct_change` IS `r`, so a claim about the RETURN
    process is not confounded by `exp(r) - 1`."""
    return _series(level * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _persistent(seed=29, n=N, level=LEVEL, phi=0.6, sigma=0.01):
    """AR(1) returns with phi > 0: a sign tends to repeat, so the count of
    sign changes must read BELOW a walk's."""
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + rng.normal(0.0, sigma)
    return _from_returns(r, level)


def _mean_reverting(seed=31, n=N, level=LEVEL, phi=-0.6, sigma=0.01):
    """AR(1) returns with phi < 0: the sign tends to flip, so the count must
    read ABOVE a walk's."""
    return _persistent(seed, n, level, phi, sigma)


def _flat(n=N, level=LEVEL):
    """Every return exactly 0.0, so every sign is 0 and the count is 0 --
    a reading, not a gap."""
    return _series(np.full(n, level))


def _ramp(n=200, level=LEVEL, step=2.0):
    """A geometric ramp whose returns are all exactly 1.0: every sign is +1,
    so the count is 0 from the other side. `step` is a power of two so
    consecutive ratios do not differ in their last bits."""
    return _series(level * step ** np.arange(n))


def _alternating(n=N, level=LEVEL, size=0.01):
    """Returns +size, -size, +size, ...: every adjacent pair differs, so the
    count is its maximum, `length - 1`."""
    return _from_returns(size * (-1.0) ** np.arange(n), level)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "coarse-grid": _coarse, "heavy-tailed": _heavy,
    "jump": _jump, "persistent": _persistent,
    "mean-reverting": _mean_reverting, "flat": _flat, "ramp": _ramp,
    "alternating": _alternating,
}
#: The frames whose column is not a constant. A causality sweep or a mutant
#: cannot be caught on a frame whose every window reads the same number.
VARIED = [k for k in FRAMES if k not in ("flat", "ramp", "alternating")]


# ----------------------------------------------------------------- helpers

def _module():
    """The tf_zero_cross_20 MODULE, not the function.

    `pandas_ta/statistics/__init__.py` binds the name on the package to the
    function, so `import pandas_ta.statistics.tf_zero_cross_20 as m` can hand
    back the function instead (Python resolves `as` by attribute first).
    `import_module` reads `sys.modules` and cannot."""
    import importlib
    return importlib.import_module("pandas_ta.statistics.tf_zero_cross_20")


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


def _absdiff(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    return float((a[m] - b[m]).abs().max())


def _both(a, b):
    return int((a.notna() & b.notna()).sum())


def _only(a, b):
    """Bars `a` reads and `b` does not."""
    return int((a.notna() & b.isna()).sum())


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _returns(close):
    """The prototype's `ret(c) = c / c.shift(1) - 1`, as a numpy array."""
    return (close / close.shift(1) - 1.0).to_numpy(dtype=float)


def _place(close, length, vals):
    out = np.full(close.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


# ----------------------------------------------------------------- oracles

def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen_r2.py:216-217`, retyped:

        roll(ret(c), 20,
             lambda W: (np.diff(np.sign(W), axis=1) != 0).sum(1).astype(float))

    with the screen's `_fin` (+-inf -> NaN) applied as `screen()` applies it.
    `_fin` is a no-op on a count, which is never infinite."""
    r = _returns(close)
    if r.size < length:
        return Series(np.full(close.size, np.nan), index=close.index)
    W = sliding_window_view(r, length)
    vals = (np.diff(np.sign(W), axis=1) != 0).sum(1).astype(float)
    return _place(close, length, vals).replace([np.inf, -np.inf], np.nan)


def _window_oracle(close, length=LENGTH):
    """TSFEL's one line applied to one window at a time, in a Python loop and
    sharing no code with the module: `len(np.where(np.diff(np.sign(w)))[0])`,
    with this port's gap rule (a window holding a non-finite return is NaN).
    """
    r = _returns(close)
    out = np.full(close.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        out[t] = len(np.where(np.diff(np.sign(w)))[0])
    return Series(out, index=close.index)


def _two_valued(close, length=LENGTH):
    """The reading NOT taken: a two-valued sign, where a return of exactly
    0.0 counts as positive (`np.sign` replaced by `np.where(r < 0, -1, 1)`),
    so a flat bar is not its own camp."""
    r = _returns(close)
    out = np.full(close.size, np.nan)
    if r.size <= length:
        return Series(out, index=close.index)
    W = sliding_window_view(r, length)
    S = np.where(W < 0.0, -1.0, 1.0)
    vals = (np.diff(S, axis=1) != 0).sum(1).astype(float)
    fin = np.isfinite(W).all(axis=1)
    out[length - 1:] = np.where(fin, vals, np.nan)
    out[length - 1] = np.nan          # the window that holds the first return
    return Series(out, index=close.index)


def _windowed_spelling(close, length=LENGTH):
    """The module's own rule, spelled over a `(rows, length)` window block
    instead of over two prefix sums. Behaviourally the same column; §Z is
    what separates them."""
    r = _returns(close)
    out = np.full(close.size, np.nan)
    if r.size <= length:
        return Series(out, index=close.index)
    W = sliding_window_view(r, length)
    fin = np.isfinite(W).all(axis=1)
    S = np.sign(np.where(np.isfinite(W), W, 0.0))
    vals = (np.diff(S, axis=1) != 0).sum(1).astype(float)
    out[length - 1:] = np.where(fin, vals, np.nan)
    return Series(out, index=close.index)


# ----------------------------------------------------------------- mutants

RETURN_LINE = \
    "    r = close.pct_change(fill_method=None).to_numpy(dtype=float)"
SIGN_LINE = "    sign = np.sign(np.where(finite, r, 0.0))"
WRITE_LINE = \
    "    out[length:] = np.where(n_finite == length, count, np.nan)"

#: Four mutants that each make the column read a bar it must not: tomorrow's
#: return, a sign series rolled one bar forward, a window CENTRED on the
#: current bar (the `bos` failure mode), and a value written one bar early.
LOOKAHEAD_MUTANTS = {
    "tomorrow": (RETURN_LINE, RETURN_LINE.replace(
        "    r = ", "    r = np.roll(").replace(
        "(dtype=float)", "(dtype=float), -1)")),
    "sign rolled": (SIGN_LINE,
                    "    sign = np.roll(np.sign(np.where(finite, r, 0.0)), -1)"),
    "centred": (SIGN_LINE,
                "    sign = np.roll(np.sign(np.where(finite, r, 0.0)),"
                " -(length // 2))"),
    "early write": (WRITE_LINE, WRITE_LINE.replace("out[length:]",
                                                   "out[length - 1:-1]")),
}
#: The fifth: it back-dates the GAP MASK by one bar. A back-dated gap does not
#: depend on any future VALUE, so a future-perturbation sweep is blind to it
#: by construction and it has to be caught by planting a NaN.
MASK_MUTANT = (WRITE_LINE, WRITE_LINE.replace(
    "n_finite == length", "np.roll(n_finite == length, -1)"))


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tf_zero_cross_20"]


def _futures(close, j, size=0.03):
    """Two closes that agree BIT FOR BIT below bar `j` and whose return AT
    `j` has the OPPOSITE SIGN: A rises every bar, B alternates starting down.
    (Only the return at `j` is guaranteed opposite; from `j + 1` on A is
    always up and B alternates, so some later bars share a sign. The
    guarantee at `j` is what the sweep needs.)

    Opposite signs at `j` make the pair `(r[j-1], r[j])` a change in exactly
    one of the two futures, so a reader of bar `j` must separate them --
    unless `r[j-1]` is itself FLAT, in which case the pair is a change in
    both and the offset proves nothing. That is what `_offsets` drops, and
    §B5 measures it: at a usable offset the fork's usual random futures
    catch exactly what these do, and at a dropped one neither catches a
    one-bar reader."""
    a = close.to_numpy(dtype=float).copy()
    b = a.copy()
    base = a[j - 1]
    steps = np.arange(1, a.size - j + 1, dtype=float)
    a[j:] = base * (1.0 + size) ** steps
    b[j:] = base * (1.0 + size * (-1.0) ** steps)
    return Series(a, index=close.index), Series(b, index=close.index)


def _random_futures(close, j, spread=3.0):
    """The futures the fork's other ports sweep with: one scaled up by a
    random factor from `j` on, one scaled down by its reciprocal. Kept only
    so §B5 can measure what they miss on this column."""
    n = close.size
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return (close * Series(up, index=close.index),
            close * Series(dn, index=close.index))


def _caught_at(fn, close, j, futures=None):
    a, b = (fn(f).iloc[:j] for f in (futures or _futures)(close, j))
    return not _bit_equal(a, b)


OFFSETS = [int(round(x)) for x in np.linspace(LENGTH + 5, N - 5, 8)]


def _offsets(close):
    """The swept offsets whose previous return is signed. On a continuous
    frame that is all of them; on a coarse grid a flat `r[j-1]` makes the
    two futures agree whatever a mutant reads, so such an offset proves
    nothing either way."""
    r = _returns(close)
    return [j for j in OFFSETS if np.isfinite(r[j - 1]) and r[j - 1] != 0.0]


# ---------------------------------------------------------------- sections

def section_A1():
    print("\n== A1  the screen prototype ==")
    print("ind_screen_r2.py candidate `tf_zero_cross_20`, retyped in")
    print("_prototype(). The arithmetic is a COUNT, so 'agrees' here means")
    print("EXACTLY equal and never a tolerance.")
    print("\n-- the return spelling, first: the module calls pct_change and")
    print("   the prototype writes c / c.shift(1) - 1 --")
    for name in FRAMES:
        c = FRAMES[name]()
        a = c.pct_change(fill_method=None).to_numpy(dtype=float)
        b = _returns(c)
        same = bool(np.array_equal(a, b, equal_nan=True))
        print(f"{name:15s} bit-equal returns: {same}")

    print("\n-- the column --")
    print(f"{'frame':15s} {'bars both':>9s} {'differ':>7s} "
          f"{'only module':>11s} {'only proto':>10s}")
    total = [0, 0, 0, 0]
    for name in FRAMES:
        c = FRAMES[name]()
        mod, pro = tf_zero_cross_20(c), _prototype(c)
        row = [_both(mod, pro),
               int((mod.notna() & pro.notna() & (mod != pro)).sum()),
               _only(mod, pro), _only(pro, mod)]
        total = [a + b for a, b in zip(total, row)]
        print(f"{name:15s} {row[0]:9d} {row[1]:7d} {row[2]:11d} {row[3]:10d}")
    print(f"{'TOTAL':15s} {total[0]:9d} {total[1]:7d} {total[2]:11d} "
          f"{total[3]:10d}")
    print("\n'only proto' is the ONE deliberate divergence: the prototype")
    print("reads a window that holds a non-finite return, because")
    print("`np.sign(NaN)` is NaN and `NaN != 0` is True, so the NaN's two")
    print("comparisons are COUNTED. Bar `length - 1` of every frame holds")
    print("r[0], which no close precedes, so every frame has at least that")
    print("one. What the prototype reads there, against the count over the")
    print("19 returns of that window that are KNOWN (18 pairs):")
    for name in ("walk", "grid", "alternating"):
        c = FRAMES[name]()
        r = _returns(c)
        known = int((np.diff(np.sign(r[1:LENGTH])) != 0).sum())
        print(f"{name:15s} prototype at bar {LENGTH - 1}: "
              f"{_prototype(c).iloc[LENGTH - 1]:.0f}, count over the known "
              f"18 pairs: {known}")


def section_A2():
    print("\n== A2  the prototype at other lengths ==")
    print(f"{'length':>6s} " + " ".join(f"{k:>15s}" for k in
                                        ("walk", "grid", "heavy-tailed")))
    for length in (MIN_LENGTH, 5, LENGTH, 60, 250):
        row = []
        for name in ("walk", "grid", "heavy-tailed"):
            c = FRAMES[name]()
            mod = tf_zero_cross_20(c, length=length)
            pro = _prototype(c, length=length)
            diff = int((mod.notna() & pro.notna() & (mod != pro)).sum())
            row.append(f"{_both(mod, pro)} both, {diff} differ".rjust(15))
        print(f"{length:6d} " + " ".join(row))


def section_A3():
    print("\n== A3  the window-by-window oracle ==")
    print("TSFEL's line, `len(np.where(np.diff(np.sign(w)))[0])`, applied to")
    print("one window at a time in a Python loop that shares no code with")
    print("the module, with this port's gap rule.")
    print(f"{'frame':15s} {'bars both':>9s} {'differ':>7s} {'masks equal':>11s}")
    total_both = total_diff = 0
    for name in FRAMES:
        c = FRAMES[name]()
        mod, orc = tf_zero_cross_20(c), _window_oracle(c)
        diff = int((mod.notna() & orc.notna() & (mod != orc)).sum())
        total_both += _both(mod, orc)
        total_diff += diff
        print(f"{name:15s} {_both(mod, orc):9d} {diff:7d} "
              f"{str(bool((mod.isna() == orc.isna()).all())):>11s}")
    print(f"{'TOTAL':15s} {total_both:9d} {total_diff:7d}")


def section_A4():
    print("\n== A4  the readings this port did NOT take ==")
    print("-- A4a  a two-valued sign, where a flat return counts as positive")
    print(f"{'frame':15s} {'zero returns':>12s} {'differ':>7s} "
          f"{'max |diff|':>10s} {'spearman':>9s}")
    for name in FRAMES:
        c = FRAMES[name]()
        r = _returns(c)
        zeros = int((r[np.isfinite(r)] == 0.0).sum())
        mod, two = tf_zero_cross_20(c), _two_valued(c)
        diff = int((mod.notna() & two.notna() & (mod != two)).sum())
        print(f"{name:15s} {zeros:12d} {diff:7d} {_absdiff(mod, two):10.0f} "
              f"{_spearman(mod, two):9.6f}")
    print("A flat return is its own sign in `np.sign`, which the issue's")
    print("formula names, so a lone flat bar between two rises counts TWO")
    print("changes where the two-valued reading counts none.")

    print("\n-- A4b  `length` is 20 RETURNS, not 20 closes --")
    for name in ("walk", "grid"):
        c = FRAMES[name]()
        a = tf_zero_cross_20(c, length=LENGTH)
        b = tf_zero_cross_20(c, length=LENGTH - 1)
        print(f"{name:15s} 20 returns vs 19: {_differs(a, b)} of "
              f"{_both(a, b)} shared bars differ, spearman "
              f"{_spearman(a, b):.6f}, max |diff| {_absdiff(a, b):.0f}")

    print("\n-- A4c  the RAW count, the source function's own return value --")
    for name in ("walk", "heavy-tailed"):
        c = FRAMES[name]()
        v = tf_zero_cross_20(c)
        print(f"{name:15s} spearman against v / (length - 1): "
              f"{_spearman(v, v / (LENGTH - 1)):.6f}")


def section_A5():
    print("\n== A5  anchors: what a known process must read ==")
    print("A sign change between two independent continuous returns has")
    print("probability 1/2, so 19 pairs centre on 9.5.")
    rng = np.random.default_rng(4242)
    draws = 4000
    r = rng.normal(0.0, 0.01, draws * LENGTH)
    W = r.reshape(draws, LENGTH)
    counts = (np.diff(np.sign(W), axis=1) != 0).sum(1)
    print(f"iid normal returns, {draws} DISJOINT windows: mean "
          f"{counts.mean():.4f}, sd {counts.std(ddof=1):.4f}, median "
          f"{np.median(counts):.1f}, min {counts.min()}, max {counts.max()}")
    print("\nmedian over 1,500-bar frames:")
    for name in FRAMES:
        v = tf_zero_cross_20(FRAMES[name]()).dropna()
        if v.empty:
            print(f"{name:15s} no fired bar")
            continue
        print(f"{name:15s} median {v.median():6.1f}  mean {v.mean():7.4f}  "
              f"min {v.min():4.0f}  max {v.max():4.0f}")
    print("\nThe ordering the column exists for: mean-reverting above walk")
    print("above persistent, and the two constructed ends at 19 and 0.")


def section_A6():
    print("\n== A6  is the source readable here? ==")
    try:
        import tsfel  # noqa: F401
        print("tsfel IS importable -- Gate A can read the source directly,")
        print("and this port's 'the formula is the issue's two lines'")
        print("caveat is out of date.")
    except ImportError as exc:
        print(f"import tsfel -> ImportError: {exc}")
    hits = sorted(p.name for p in (ROOT / "docs").glob("*tsfel*"))
    print(f"docs/*tsfel* : {hits}")
    print("So Gate A checks the quantity the issue's line names, spelled")
    print("three ways, and NOT TSFEL's own code.")


def section_A7():
    print("\n== A7  the flat return, which is the whole of the sign choice ==")
    print("A single flat bar between two rises. Closes 100, 101, 101, 102,")
    print("103 ... so the returns are NaN, +, 0, +, + ...")
    c = _series(np.array([100.0, 101.0, 101.0] +
                         list(102.0 + np.arange(5))))
    v = tf_zero_cross_20(c, length=MIN_LENGTH)
    print(f"returns: {[None if np.isnan(x) else round(x, 6) for x in _returns(c)]}")
    print(f"at length {MIN_LENGTH}, every reading: "
          f"{[None if np.isnan(x) else int(x) for x in v.to_numpy()]}")
    print("(bar 2 is the pair (+, 0) and bar 3 the pair (0, +): one change")
    print("each, so one flat bar costs two.)")
    print("\nHow often that happens, by grid:")
    for name in ("walk", "grid", "coarse-grid", "flat"):
        c = FRAMES[name]()
        r = _returns(c)
        fin = np.isfinite(r)
        share = float((r[fin] == 0.0).mean())
        print(f"{name:15s} zero returns: {share:7.2%} of {int(fin.sum())}")
    print("⚠ Real BIST daily data is a TICK grid, not a continuous walk, so")
    print("   the live share is the grid frames' regime and not the walk's.")
    print("   The real-data count is owed from the Gate E run.")


def section_B():
    print("\n== B  causality ==")
    print(f"offsets swept: {OFFSETS}")
    print("\n-- the real module, and the four look-ahead mutants --")
    print(f"{'frame':15s} {'usable':>6s} {'real':>6s} " +
          " ".join(f"{k:>15s}" for k in LOOKAHEAD_MUTANTS))
    mutants = {k: _mutant(*v) for k, v in LOOKAHEAD_MUTANTS.items()}
    for name in VARIED:
        c = FRAMES[name]()
        offsets = _offsets(c)
        row = [f"{len(offsets):6d}",
               f"{sum(_caught_at(tf_zero_cross_20, c, j) for j in offsets):6d}"]
        for fn in mutants.values():
            caught = sum(_caught_at(fn, c, j) for j in offsets)
            live = not _bit_equal(fn(c), tf_zero_cross_20(c))
            row.append(f"{caught:d}/{len(offsets)} live={int(live):d}".rjust(15))
        print(f"{name:15s} " + " ".join(row))
    print("'caught' = the prefix below the perturbation moved. 'usable' is")
    print("how many of the 8 swept offsets have a signed previous return --")
    print("at an offset whose previous return is FLAT the two futures agree")
    print("whatever a one-bar reader does, so it proves nothing either way")
    print("(§B5 measures that). The real module must read 0 of the usable")
    print("offsets and each live mutant all of them.")

    print("\n-- B2  the mutant the blind sweep cannot see --")
    mask = _mutant(*MASK_MUTANT)
    for name in VARIED[:3]:
        c = FRAMES[name]()
        print(f"{name:15s} live={not _bit_equal(mask(c), tf_zero_cross_20(c))} "
              f"caught={sum(_caught_at(mask, c, j) for j in _offsets(c))}/"
              f"{len(_offsets(c))}")
    print("Planting one NaN close instead, and reading where the gap lands:")
    print(f"{'at':>6s} {'real first gap':>15s} {'mutant first gap':>17s}")
    for at in (200, 600, 1000):
        c = _walk()
        c.iloc[at] = np.nan
        real = [int(i) for i in
                np.flatnonzero(tf_zero_cross_20(c).isna().to_numpy())
                if i >= LENGTH]
        mut = [int(i) for i in np.flatnonzero(mask(c).isna().to_numpy())
               if i >= LENGTH]
        print(f"{at:6d} {min(real):15d} {min(mut):17d}")

    print("\n-- B3  prefix truncation --")
    for name in FRAMES:
        c = FRAMES[name]()
        full = tf_zero_cross_20(c)
        offsets = [j for j in OFFSETS if j < c.size]
        ok = all(_bit_equal(full.iloc[:j], tf_zero_cross_20(c.iloc[:j]))
                 for j in offsets)
        print(f"{name:15s} unchanged at every offset: {ok}")
    print("⚠ Prefix truncation is the WEAK check -- it cannot see a value")
    print("   back-dated inside the prefix, which is what B2 is for.")

    print("\n-- B5  why the futures are deterministic and opposite-signed --")
    print("The same four mutants, swept with the RANDOM futures the fork's")
    print("other ports use (one future scaled up by 1 + 3u, the other by its")
    print("reciprocal), against the deterministic pair. This column returns a")
    print("small integer, so two arbitrary futures can produce the same")
    print("COUNT below the offset even from a reader of bar j.")
    print("Run at BOTH scales: these 1,500-bar frames, and the 400-bar")
    print("frames `tests/test_tf_zero_cross_20.py` builds, with that")
    print("module's own eight offsets. The miss is at the shorter one.")
    for bars in (N, 400):
        offsets = [int(round(x)) for x in np.linspace(LENGTH + 5, bars - 5, 8)]
        print(f"\n{bars}-bar frames, offsets {offsets}")
        print(f"{'frame':15s} {'usable':>6s} {'futures':>13s} " +
              " ".join(f"{k:>12s}" for k in LOOKAHEAD_MUTANTS))
        for name in ("walk", "grid", "coarse-grid"):
            c = FRAMES[name](n=bars)
            r = _returns(c)
            usable = [j for j in offsets
                      if np.isfinite(r[j - 1]) and r[j - 1] != 0.0]
            for label, builder in (("deterministic", _futures),
                                   ("random", _random_futures)):
                row = [f"{len(usable):6d}", f"{label:>13s}"]
                for spec in LOOKAHEAD_MUTANTS.values():
                    fn = _mutant(*spec)
                    caught = sum(_caught_at(fn, c, j, builder)
                                 for j in usable)
                    row.append(f"{caught:d}/{len(usable)}".rjust(12))
                print(f"{name:15s} " + " ".join(row))
    print("\nAnything below the full count is a mutant that DOES read the")
    print("future and is not caught. What the two builders show is that at a")
    print("USABLE offset they agree everywhere above, so the determinism is")
    print("belt and braces; the DROPPED offsets are what matters, and here")
    print("is why. On the 400-bar 0.5-grid frame two of the eight offsets")
    print("have a flat previous return:")
    c = FRAMES["coarse-grid"](n=400)
    r = _returns(c)
    offsets = [int(round(x)) for x in np.linspace(LENGTH + 5, 400 - 5, 8)]
    dropped = [j for j in offsets if r[j - 1] == 0.0]
    print(f"dropped offsets: {dropped} (r[j-1] == 0.0 at each)")
    for label, spec in LOOKAHEAD_MUTANTS.items():
        fn = _mutant(*spec)
        for builder, bname in ((_futures, "deterministic"),
                               (_random_futures, "random")):
            caught = sum(_caught_at(fn, c, j, builder) for j in dropped)
            print(f"{label:13s} {bname:13s} caught {caught}/{len(dropped)} "
                  f"at the dropped offsets")
    print("A flat r[j-1] makes the pair (r[j-1], r[j]) a change in BOTH")
    print("futures whatever sign r[j] takes, so for a mutant that reads ONE")
    print("bar ahead the two prefixes agree and the offset proves nothing.")
    print("The `centred` mutant reads length // 2 bars ahead and so is")
    print("still caught there by the deterministic pair, which is the one")
    print("place the two builders part.")

    print("\n-- B4  one changed close moves only the windows that hold it --")
    print("A close at bar `at` enters the returns at `at` and `at + 1`, so")
    print("it can move only the windows at `at` .. `at + length`. Nothing")
    print("outside that span may move, in EITHER direction.")
    c = _walk()
    base = tf_zero_cross_20(c)
    for at in (200, 800):
        for factor in (1.5, 1.0 / 1.5):
            d = c.copy()
            d.iloc[at] = d.iloc[at] * factor
            v = tf_zero_cross_20(d)
            moved = [int(i) for i in np.flatnonzero(
                (base != v).to_numpy() & base.notna().to_numpy())]
            span = range(at, at + LENGTH + 1)
            outside = [i for i in moved if i not in span]
            print(f"close x{factor:.3f} at bar {at:4d}: {len(moved):3d} bars "
                  f"move, {len(outside)} of them outside "
                  f"{at}..{at + LENGTH}")


def section_C():
    print("\n== C  reachability, synthetic frames ==")
    print("⚠ Gate C's real-data limb is owed: it comes off the Gate E run,")
    print("   which issue-solver runs after this session.")
    print(f"{'frame':15s} {'bars':>6s} {'fires':>6s} {'distinct':>8s} "
          f"{'min':>5s} {'median':>7s} {'max':>5s}")
    for name in FRAMES:
        c = FRAMES[name]()
        v = tf_zero_cross_20(c)
        fired = v.dropna()
        if fired.empty:
            print(f"{name:15s} {len(v):6d} {0:6d} {0:8d}")
            continue
        print(f"{name:15s} {len(v):6d} {int(fired.size):6d} "
              f"{int(fired.nunique()):8d} {fired.min():5.0f} "
              f"{fired.median():7.1f} {fired.max():5.0f}")
    print("\nWarm-up: the first reading is at bar `length`, because `length`")
    print("returns need `length + 1` closes.")
    for name in ("walk", "heavy-tailed"):
        v = tf_zero_cross_20(FRAMES[name]())
        print(f"{name:15s} first fired bar: "
              f"{int(np.flatnonzero(v.notna().to_numpy())[0])}")
    print("\nThe reachable set is 0 .. length - 1. Which of the 20 values")
    print("the frames here actually show, pooled:")
    seen = set()
    for name in FRAMES:
        seen |= set(int(x) for x in tf_zero_cross_20(FRAMES[name]()).dropna())
    print(f"pooled distinct values: {sorted(seen)}")
    print(f"missing from 0..{LENGTH - 1}: "
          f"{sorted(set(range(LENGTH)) - seen)}")


def section_D():
    print("\n== D  scale-free ==")
    print("-- exact binary factors: bit-identical --")
    factors = {"x8": 8.0, "x64": 64.0, "2**-40": 2.0 ** -40,
               "2**40": 2.0 ** 40, "2**100": 2.0 ** 100}
    print(f"{'frame':15s} " + " ".join(f"{f:>8s}" for f in factors))
    for name in FRAMES:
        c = FRAMES[name]()
        base = tf_zero_cross_20(c)
        row = [f"{str(_bit_equal(base, tf_zero_cross_20(c * k))):>8s}"
               for k in factors.values()]
        print(f"{name:15s} " + " ".join(row))

    print("\n-- x8 at every length --")
    for length in (MIN_LENGTH, 5, LENGTH, 60, 250):
        c = _walk()
        print(f"length {length:4d}: bit-identical "
              f"{_bit_equal(tf_zero_cross_20(c, length=length), tf_zero_cross_20(c * 8.0, length=length))}")

    print("\n-- inexact factors: the count is an integer, so 'agrees' is")
    print("   still EXACT equality, and what could break it is a return")
    print("   whose sign the rescale flips --")
    print(f"{'frame':15s} " + " ".join(f"{f:>12s}" for f in
                                       ("x10", "x3.7", "x0.1", "x1.0000001")))
    for name in FRAMES:
        c = FRAMES[name]()
        base = tf_zero_cross_20(c)
        row = []
        for k in (10.0, 3.7, 0.1, 1.0000001):
            v = tf_zero_cross_20(c * k)
            row.append(f"{_differs(base, v)} differ".rjust(12))
        print(f"{name:15s} " + " ".join(row))

    print("\n-- a monotone map of the PRICE, which cannot reorder two closes")
    print("   (and 1/price reverses every return, which leaves the number of")
    print("   CHANGES alone) --")
    for name in ("walk", "grid", "heavy-tailed"):
        c = FRAMES[name]()
        base = tf_zero_cross_20(c)
        for label, d in (("price**2", c ** 2), ("sqrt(price)", c ** 0.5),
                         ("1/price", 1.0 / c)):
            v = tf_zero_cross_20(d)
            print(f"{name:15s} {label:12s} differ "
                  f"{_differs(base, v):4d} of {_both(base, v)}")

    print("\n-- a level SHIFT: the usual anti-vacuity check, and here it")
    print("   does NOT hold, which is a property and not a defect. The")
    print("   column reads the sign of `c[t] / c[t-1] - 1`, i.e. the ORDER")
    print("   of two consecutive closes, and `c + k > c' + k` exactly when")
    print("   `c > c'`. Only a shift that makes the path STRADDLE zero")
    print("   moves it: where the two closes of a pair have opposite signs")
    print("   the ratio's order flips, and where they are both negative it")
    print("   flips for every pair at once, which leaves the number of")
    print("   CHANGES alone. --")
    c = _walk()
    base = tf_zero_cross_20(c)
    for shift in (10.0, 100.0, -50.0, -200.0, -1000.0):
        d = c + shift
        v = tf_zero_cross_20(d)
        print(f"{shift:>+9.1f}: {_differs(base, v)} of {_both(base, v)} bars "
              f"move, max |diff| {_absdiff(base, v):.0f}, "
              f"min close {float(d.min()):8.2f}, "
              f"{int((d < 0).sum()):4d} of {len(d)} closes negative")

    print("\n-- so the check that bit-identity is not vacuous is that the")
    print("   column is NOT CONSTANT, stated per frame --")
    for name in FRAMES:
        c = FRAMES[name]()
        v = tf_zero_cross_20(c)
        fired = v.dropna()
        print(f"{name:15s} fires {int(v.notna().sum()):5d} of {len(v):5d}, "
              f"{int(fired.nunique())} distinct values")


def section_G():
    print("\n== G  guards: what a bad close does ==")
    print("One close replaced at bar 200 of a 1,500-bar walk. A close of 0")
    print("makes the NEXT return infinite, not its own; a NEGATIVE close is")
    print("a price here and not a gap, because nothing takes a logarithm.")
    print(f"{'close[200] =':>16s} {'fires':>6s} {'gap bars':>9s} "
          f"{'first gap':>9s} {'last gap':>8s} {'values moved':>12s} "
          f"{'of them before 200':>18s}")
    base = tf_zero_cross_20(_walk())
    for label, value in (("NaN", np.nan), ("inf", np.inf), ("-inf", -np.inf),
                         ("0.0", 0.0), ("-100.0", -100.0),
                         ("1e-310", 1e-310), ("x1.5", None)):
        c = _walk()
        c.iloc[200] = c.iloc[200] * 1.5 if value is None else value
        v = tf_zero_cross_20(c)
        gaps = [int(i) for i in np.flatnonzero(
            v.isna().to_numpy() & base.notna().to_numpy())]
        moved = ((v != base) & v.notna() & base.notna()).to_numpy()
        earlier = int((moved & (np.arange(len(v)) < 200)).sum())
        print(f"{label:>16s} {int(v.notna().sum()):6d} {len(gaps):9d} "
              f"{(min(gaps) if gaps else -1):9d} "
              f"{(max(gaps) if gaps else -1):8d} {int(moved.sum()):12d} "
              f"{earlier:18d}")
    print("A gap spans the windows that hold the affected RETURN, which is")
    print("why a bad close at bar 200 can empty bars 200..220 (two returns)")
    print("or 201..220 (one), depending on which returns it breaks.")

    print("\n-- no warning and no floating-point error is reachable --")
    for name in FRAMES:
        c = FRAMES[name]()
        with np.errstate(all="raise"):
            tf_zero_cross_20(c)
    c = _walk()
    c.iloc[200] = 0.0
    c.iloc[400] = np.nan
    c.iloc[600] = np.inf
    with np.errstate(all="raise"):
        v = tf_zero_cross_20(c)
    print(f"every frame and a frame with 0.0, NaN and inf planted: no raise "
          f"under errstate(all='raise'); that frame fires "
          f"{int(v.notna().sum())} of {len(v)}")

    print("\n-- the input Series is not mutated --")
    c = _walk()
    before = c.to_numpy().copy()
    tf_zero_cross_20(c)
    print(f"close unchanged: {bool(np.array_equal(before, c.to_numpy()))}")

    print("\n-- the shortest input that produces a value --")
    for length in (MIN_LENGTH, LENGTH):
        short = _walk(n=length)
        exact = _walk(n=length + 1)
        print(f"length {length:3d}: {length} closes -> "
              f"{tf_zero_cross_20(short, length=length)}, "
              f"{length + 1} closes -> "
              f"{int(tf_zero_cross_20(exact, length=length).notna().sum())} "
              f"value(s)")

    print("\n-- a length below the minimum falls back to the default --")
    c = _walk()
    for length in (None, 0, 1, -5, MIN_LENGTH):
        print(f"length={str(length):>5s} -> "
              f"{tf_zero_cross_20(c, length=length).name}")


def section_L():
    print("\n== L  what the column reads, and what it overlaps ==")
    print("-- L1  the fork columns nearest to it, Spearman on synthetic")
    print("   frames. ⚠ SYNTHETIC: the number that decides ship or revert is")
    print("   the launcher's Gate E run on the 89 BIST frames. --")
    names = ["LEAN_MOMERSION_20", "TS_CROSS_MEAN_20", "TFCENTROID_20",
             "STDEV_20", "MAD_20", "|ret|"]
    print(f"{'frame':15s} {'flat?':>5s} " +
          " ".join(f"{k:>18s}" for k in names))
    band = []
    for name in VARIED:
        c = FRAMES[name]()
        v = tf_zero_cross_20(c)
        r = _returns(c)
        # Whether the frame has an exactly-zero return at all. A band quoted
        # over "the continuous frames" has to be read off THIS column and
        # not inferred, which is what the first review round caught.
        continuous = not bool((r[np.isfinite(r)] == 0.0).any())
        others = [lean_momersion_20(c), ts_cross_mean_20(c), tf_centroid_20(c),
                  stdev(c, 20), mad(c, 20),
                  (c / c.shift(1) - 1.0).abs().rolling(20).mean()]
        if continuous:
            band.append(_spearman(v, others[0]))
        print(f"{name:15s} {'-' if continuous else 'flat':>5s} " +
              " ".join(f"{_spearman(v, o):18.4f}" for o in others))
    print(f"\nmomersion over the {len(band)} frames with NO flat bar "
          f"('-' above): {min(band):.4f} .. {max(band):.4f}")
    print("⚠ LEAN_MOMERSION_20 is the one to read. It counts the SAME events")
    print("   on a window one pair longer and reports the share that AGREE,")
    print("   so it must run strongly negative against a count of the pairs")
    print("   that DISAGREE. See L1b.")

    print("\n-- L1b  how close momersion is, exactly --")
    print("On a frame with no flat bar, momersion over 20 pairs is")
    print("100 * (20 - MRC) / 20 and this column is MRC over 19 pairs, so")
    print("the two are the same count on windows that differ by one pair.")
    for name in ("walk", "grid", "coarse-grid", "heavy-tailed"):
        c = FRAMES[name]()
        v = tf_zero_cross_20(c)
        m = lean_momersion_20(c)
        # The same window: momersion's 20 pairs are this column at length 21.
        v21 = tf_zero_cross_20(c, length=LENGTH + 1)
        implied = 100.0 * (LENGTH - v21) / LENGTH
        print(f"{name:15s} spearman(TFZEROCROSS_20, momersion) "
              f"{_spearman(v, m):8.4f};  same window (length 21): "
              f"{_spearman(v21, m):8.4f};  "
              f"100*(20-count21)/20 equals momersion on "
              f"{int((implied.round(10) == m.round(10)).sum())} of "
              f"{_both(implied, m)} shared bars")

    print("\n-- L1c  what separates the two is FLAT BARS, so the overlap is")
    print("   a function of the price grid. The same walk, rounded to a")
    print("   coarser and coarser tick: --")
    print(f"{'tick':>6s} {'zero returns':>12s} {'vs momersion':>12s} "
          f"{'at length 21':>12s}")
    for tick in (0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0):
        c = _grid(tick=tick)
        r = _returns(c)
        share = float((r[np.isfinite(r)] == 0.0).mean())
        m = lean_momersion_20(c)
        print(f"{tick:6.3f} {share:11.2%} "
              f"{_spearman(tf_zero_cross_20(c), m):12.4f} "
              f"{_spearman(tf_zero_cross_20(c, length=LENGTH + 1), m):12.4f}")
    print("⚠ Which column of that table real BIST daily data sits in is NOT")
    print("   measured here -- no real frame is reachable from this")
    print("   worktree. It comes off the Gate E run.")

    print("\n-- L2  it is blind to the SIZE of the returns, and to a")
    print("   monotone map of them --")
    print("   Both frames are rebuilt from the same return array, so the")
    print("   comparison is bar for bar.")
    r = _returns(_walk())[1:]
    base = tf_zero_cross_20(_from_returns(r))
    for label, k in (("returns x0.5", 0.5), ("returns x2", 2.0),
                     ("returns x-1", -1.0), ("returns x1e-6", 1e-6)):
        v = tf_zero_cross_20(_from_returns(r * k))
        print(f"{label:16s} differ {_differs(base, v):4d} of "
              f"{_both(base, v)} shared bars")
    print("(x-1 flips every sign, which leaves every DISAGREEMENT a")
    print(" disagreement, so the count cannot move.)")

    print("\n-- L3  it is NOT blind to a constant drift: drift makes one sign")
    print("   likelier, and so removes changes --")
    r = _returns(_walk())[1:]
    for drift in (0.0, 0.002, 0.01, 0.05):
        v = tf_zero_cross_20(_from_returns(r + drift)).dropna()
        print(f"drift {drift:6.3f} a bar: median {v.median():5.1f}, mean "
              f"{v.mean():7.4f}")

    print("\n-- L4  it IS blind to a time REVERSAL, which no other order")
    print("   change is: reversing a window keeps every adjacency --")
    c = _walk()
    v = tf_zero_cross_20(c)
    rev = tf_zero_cross_20(_from_returns(_returns(c)[1:][::-1]))
    print(f"reversed frame: the two columns are not aligned bar to bar, so")
    print(f"the claim is on the SET of counts: sorted values equal "
          f"{np.array_equal(np.sort(v.dropna().to_numpy())[::-1][:1], np.sort(rev.dropna().to_numpy())[::-1][:1])}"
          f" at the maximum; max {v.max():.0f} vs {rev.max():.0f}, "
          f"min {v.min():.0f} vs {rev.min():.0f}")
    rng = np.random.default_rng(5150)
    r = _returns(c)[1:]
    same_rev = same_perm = 0
    trials = 500
    for _ in range(trials):
        j = int(rng.integers(0, r.size - LENGTH))
        w = r[j:j + LENGTH]
        n_w = int((np.diff(np.sign(w)) != 0).sum())
        same_rev += n_w == int((np.diff(np.sign(w[::-1])) != 0).sum())
        p = rng.permutation(w)
        same_perm += n_w == int((np.diff(np.sign(p)) != 0).sum())
    print(f"over {trials} sampled windows: a reversal leaves the count "
          f"unchanged on {same_rev}, a permutation on {same_perm}")

    print("\n-- L5  it is a STATE, not an event: neighbouring windows share")
    print("   19 of their 20 returns --")
    v = tf_zero_cross_20(_walk()).dropna()
    for lag in (1, 5, 10, 20, 40):
        print(f"lag {lag:3d}: autocorrelation {v.autocorr(lag):7.4f}")


def section_W():
    print("\n== W  the dictionary cut ==")
    from pandas_ta.statistics.tf_zero_cross_20 import tf_zero_cross_20 as fn
    first = fn.__doc__.split("\n\n")[1].strip()
    # The limit is read out of the generator rather than quoted, so the
    # margin below cannot go stale if the generator changes.
    gen = (ROOT / "docs" / "gen_indicator_dictionary.py").read_text(
        encoding="utf-8")
    limit = int(re.search(r"def desc\(rec, limit=(\d+)\)", gen).group(1))
    squeezed = re.sub(r"\s+", " ", first).strip()
    print(f"gen_indicator_dictionary.desc truncates at {limit} characters")
    print(f"first paragraph after the title, {len(first)} characters "
          f"({len(squeezed)} squeezed), so it is "
          f"{'truncated' if len(squeezed) > limit else 'shown whole'}:")
    print(first)
    print(f"LEAN_MOMERSION_20 inside the cut: "
          f"{'LEAN_MOMERSION_20' in squeezed[:limit]}")


def section_Z():
    print("\n== Z  cost ==")
    print("Two prefix sums and two subtractions, against the same rule")
    print("spelled over a (rows, length) window block.")
    big = _walk(n=400_000)
    print(f"{'length':>6s} {'prefix-sum peak':>16s} {'windowed peak':>14s} "
          f"{'equal':>6s}")
    for length in (20, 250):
        tracemalloc.start()
        a = tf_zero_cross_20(big, length=length)
        peak_a = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        tracemalloc.start()
        b = _windowed_spelling(big, length=length)
        peak_b = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"{length:6d} {peak_a / 1e6:14.1f} MB {peak_b / 1e6:12.1f} MB "
              f"{str(_bit_equal(a, b)):>6s}")
    print("⚠ Peaks are a property of THIS run and are left out of the")
    print("   digest; the two columns being equal is not.")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A6": section_A6, "A7": section_A7, "B": section_B,
    "C": section_C, "D": section_D, "G": section_G, "L": section_L,
    "W": section_W, "Z": section_Z,
}
#: Everything but Z: Z reports traced memory peaks, which are a property of
#: the run rather than of the column.
DIGESTED = [k for k in SECTIONS if k != "Z"]


def run(keys):
    """Run each section once, print everything, and return the digest of the
    deterministic ones. Each section is captured so Z's traced peaks can be
    shown to the reader and kept out of the digest, without running anything
    twice."""
    digest = hashlib.sha1()
    for key in keys:
        buf = io.StringIO()
        with redirect_stdout(buf):
            SECTIONS[key]()
        print(buf.getvalue(), end="")
        if key in DIGESTED:
            digest.update(buf.getvalue().encode("utf-8"))
    return digest.hexdigest()


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
    keys = [k for k in SECTIONS if k in want]
    sha = run(keys)
    print(f"\nDIGEST {','.join(k for k in keys if k in DIGESTED)} {sha}")
