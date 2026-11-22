# -*- coding: utf-8 -*-
"""Reproduce every number in docs/C22StretchDecreasingMeasured.md for
`c22_stretch_decreasing` (PandasTa issue #140, C22-STRETCH-DECREASING).

Run from the repository root:

    python docs/measure_c22_stretch_decreasing.py            # every section
    python docs/measure_c22_stretch_decreasing.py gate_b     # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.

No reference implementation is run: pycatch22 and hctsa are GPL-3.0. Gate A
is against an independent `itertools.groupby` spelling written below, which
shares no array machinery or constant with the shipped module.
"""
import importlib
import itertools
import sys
import time
import tracemalloc
import types

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.c22_stretch_decreasing import c22_stretch_decreasing

LENGTH = 100
REAL = importlib.import_module("pandas_ta.statistics.c22_stretch_decreasing")


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


def penny(n=1500, seed=23, level=2.0, sigma=0.012):
    rng = np.random.default_rng(seed)
    w = level * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(np.round(w, 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def geometric_ladder(n=300, step=0.01):
    return Series(100.0 * np.exp(np.arange(n) * step))


def closes_from_returns(r):
    return Series(np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r, float))]))


def compare(name, a, b):
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    rho = float(x.corr(y, method="spearman")) if len(x) > 2 else float("nan")
    print(f"  {name}: n={int(m.sum())} bit-equal={bit}/{int(m.sum())} "
          f"max|diff|={float(diff.max()) if len(x) else float('nan'):.6g} "
          f"spearman={rho:.6f} nan-masks-agree={masks_agree}")
    return float(diff.max()) if len(x) else float("nan"), bit, rho, masks_agree


# ----------------------------------------------------------------- oracles
def longest_falling_run(x):
    """`max(run lengths of True in groupby(diff(x) < 0))`, 0 when there is
    no run. Independent spelling -- not a copy of any GPL-3.0 reference
    code, which this session cannot read."""
    x = np.asarray(x, dtype=float)
    d = np.diff(x)
    runs = [len(list(g)) for v, g in itertools.groupby(d < 0.0) if v]
    return float(max(runs)) if runs else 0.0


def oracle_series(close, length=LENGTH):
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        r = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        if not all(np.isfinite(v) for v in r):
            continue
        out[t] = longest_falling_run(r)
    return Series(out, index=close.index)


# ----------------------------------------------------------------- Gate A
def gate_a():
    head("Gate A1 -- windows whose answer is derived by hand")
    cases = [
        ([5.0, 4.0, 3.0, 2.0, 1.0], 4.0, "strictly falling: all 4 diffs "
         "negative, the maximum a 5-return window can score"),
        ([1.0, 2.0, 3.0, 4.0, 5.0], 0.0, "strictly rising: no diff negative"),
        ([1.0, 1.0, 1.0, 1.0, 1.0], 0.0, "constant: every diff is exactly 0 "
         "-- flat, not falling"),
        ([3.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0, 0.0], 3.0, "two falling runs "
         "(2 and 3 diffs): the longest is 3"),
        ([1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0], 1.0, "alternating: every "
         "other diff negative, no run reaches 2"),
        ([5.0, 4.0, 3.0, 3.0, 2.0, 1.0], 2.0, "a flat step mid-fall breaks "
         "the run into 2 and 2"),
        ([0.0, 0.0, 5.0, 4.0, 3.0, 2.0, 1.0], 4.0, "a falling run at the "
         "far end of the window"),
        ([5.0, 4.0, 3.0, 2.0, 1.0, 0.0, 0.0], 5.0, "a falling run then flat "
         "-- the last diff (0-0) is the only non-negative one"),
    ]
    for r, expected, why in cases:
        n = len(r)
        out = c22_stretch_decreasing(closes_from_returns(r), length=n)
        got = float(out.iloc[-1])
        print(f"  length={n} returns={r} -> {got:g} (expected {expected:g}) "
              f"[{'OK' if got == expected else 'MISMATCH'}]  {why}")

    head("Gate A2 -- an independent groupby spelling, window by window")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.6)", ar1())):
        base, orc = c22_stretch_decreasing(frame), oracle_series(frame)
        compare(name, base, orc)
        r = (frame / frame.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        span = W.max(axis=1) - W.min(axis=1)
        print(f"    windows reaching the floor: "
              f"{int((span <= REAL.NOISE_FLOOR).sum())} of {len(span)}")

    head("Gate A3 -- the attainable set")
    reached = []
    for k in range(1, LENGTH):
        r = [float(LENGTH - i) for i in range(k)] + [0.0] * (LENGTH - k)
        got = float(c22_stretch_decreasing(closes_from_returns(r)).iloc[-1])
        reached.append(got)
        if got != float(k):
            print(f"    k={k}: MISMATCH got {got:g}")
    print(f"  k consecutive strictly-falling returns among zeros reaches "
          f"{sorted(set(reached))[:5]} .. {sorted(set(reached))[-5:]}")


# ----------------------------------------------------------------- Gate B
WRITE_BACK_DATED = (
    "    out[length - 1:] = np.where(bad, np.nan, body)",
    "    out[length - 2:-1] = np.where(bad, np.nan, body)")
FORWARD_RETURN = ("        r[1:] = c[1:] / c[:-1] - 1.0",
                  "        r[:-1] = c[1:] / c[:-1] - 1.0")
FORWARD_DIFF_SIGN = ("    falling = diffs < 0.0",
                     "    falling = np.roll(diffs < 0.0, -1, axis=0)")
FORWARD_WINDOW = (
    "        current = np.where(falling[:, j], current + 1.0, 0.0)",
    "        current = np.where(np.roll(falling, -1, axis=0)[:, j], "
    "current + 1.0, 0.0)")
FORWARD_SPAN = ("    span = windows.max(axis=1) - windows.min(axis=1)",
               "    span = np.roll(windows.max(axis=1) - windows.min(axis=1), -1)")

MUTANTS = [WRITE_BACK_DATED, FORWARD_RETURN, FORWARD_DIFF_SIGN,
           FORWARD_WINDOW, FORWARD_SPAN]
MUTANT_IDS = ["write_back_dated", "forward_return", "forward_diff_sign",
              "forward_window", "forward_span"]
OFFSETS = range(140, 1500, 40)
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "ar1(+0.6)": (ar1(), ar1(seed=8)),
}


def flat_planted(n=1500, seed=11):
    c = walk(n, seed).to_numpy().copy()
    for j in OFFSETS:
        c[j - LENGTH:j + 1] = c[j - LENGTH]
    return Series(c)


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_c22_stretch_decreasing_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def _spliced(close, j, seed):
    """`close` with everything from bar `j` onward replaced by an
    independent random path starting from `close[j - 1]`. The level jump at
    the splice boundary plants an extreme return right where a one-bar
    look-ahead would first be able to read it."""
    rng = np.random.default_rng(seed)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def leak_offsets(fn, close, offsets=OFFSETS, splices=8):
    """A hit at J means at least one of `splices` independent random futures
    moved something strictly before J. This run-length statistic is far more
    tie-heavy than a continuous one (`ts_strike_20`'s mean-based comparator),
    so ONE fixed future frequently fails to move the (low-cardinality)
    longest run even under a real look-ahead; several independent splices
    per offset is what the `c22_median_freq` test suite uses for the same
    reason."""
    base = fn(close)
    hit = []
    for j in offsets:
        caught = False
        for s in range(splices):
            out = fn(_spliced(close, j, seed=909 + 7919 * s))
            a, b = base.iloc[:j], out.iloc[:j]
            if not (a.isna() == b.isna()).all():
                caught = True
                break
            m = a.notna()
            if (a[m] != b[m]).any():
                caught = True
                break
        if caught:
            hit.append(j)
    return hit


def leaks(fn, close, other=None, splices=8):
    return len(leak_offsets(fn, close, splices=splices))


def gate_b():
    head("Gate B -- future-perturbation sweep, real module and five mutants")
    n = len(list(OFFSETS))
    print(f"  {n} offsets J = {OFFSETS.start}..{max(OFFSETS)} step "
          f"{OFFSETS.step}, 8 independent random splices tried per offset")
    for frame in sorted(FRAMES):
        close, _ = FRAMES[frame]
        print(f"  {frame}: real module {leaks(c22_stretch_decreasing, close)}/{n}")
    for mid, mutant in zip(MUTANT_IDS, MUTANTS):
        mod = load_mutant(*mutant)
        for frame in sorted(FRAMES):
            close, _ = FRAMES[frame]
            live = not mod.c22_stretch_decreasing(close).equals(
                c22_stretch_decreasing(close))
            hit = leak_offsets(mod.c22_stretch_decreasing, close)
            missed = [j for j in OFFSETS if j not in hit]
            print(f"  {mid} on {frame}: caught {len(hit)}/{n} "
                  f"(live mutation={live})")
            if missed:
                print(f"    missed J = {missed}")

    head("Gate B -- the sixth-style mutant: span taken from the next window")
    frame = flat_planted()
    print(f"  real module on flat-planted: {leaks(c22_stretch_decreasing, frame)}/{n}")
    mod = load_mutant(*FORWARD_SPAN)
    hit = leak_offsets(mod.c22_stretch_decreasing, frame)
    print(f"  forward_span on flat-planted: caught {len(hit)}/{n}")


# ------------------------------------------------------- the noise floor
def noise_floor():
    head("The noise floor -- an exactly geometric path")
    for name, frame in (("1%-a-bar ladder", geometric_ladder()),
                        ("-0.5%-a-bar ladder", geometric_ladder(step=-0.005)),
                        ("x1.5 ladder", Series(np.cumprod(np.full(300, 1.5))))):
        guarded = c22_stretch_decreasing(frame)
        gv = sorted(set(guarded.dropna().tolist()))
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}/"
              f"{len(frame)} values {gv}")
        r = frame / frame.shift(1) - 1.0
        span = (r.rolling(LENGTH).max() - r.rolling(LENGTH).min()).iloc[-1]
        print(f"    window return span {float(span):.3e} vs floor "
              f"{REAL.NOISE_FLOOR:.3e}")

    head("The noise floor on real-shaped data -- what it costs")
    for name, frame in (("walk", walk(300)), ("tick-rounded", tick_rounded(300))):
        guarded = c22_stretch_decreasing(frame)
        r = (frame / frame.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        span = W.max(axis=1) - W.min(axis=1)
        print(f"  {name}: fires {int(guarded.notna().sum())}/{len(frame)}, "
              f"windows reaching the floor {int((span <= REAL.NOISE_FLOOR).sum())}"
              f" of {len(span)}")

    head("The noise floor against a monotone one-tick-per-bar path")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = closes / closes.shift(1) - 1.0
        span = float((r.rolling(LENGTH).max() - r.rolling(LENGTH).min()).iloc[-1])
        guarded = c22_stretch_decreasing(closes)
        gv = sorted(set(guarded.dropna().tolist()))
        print(f"  price={price:g} tick={tick:g}: span {span:.3e} vs floor "
              f"{REAL.NOISE_FLOOR:.3e}, guarded values {gv}")


# ---------------------------------------------------------------- Gate C/D
def gate_c_d():
    head("Gate D -- a power-of-two price rescale")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1), ("penny", penny)):
        close = fn()
        for k in (8.0, 64.0):
            compare(f"{name} x{k:g}", c22_stretch_decreasing(close),
                    c22_stretch_decreasing(close * k))

    head("Gate D -- a price rescale that is NOT a power of two")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded)):
        close = fn()
        for k in (10.0, 3.7, 0.1):
            compare(f"{name} x{k:g}", c22_stretch_decreasing(close),
                    c22_stretch_decreasing(close * k))

    head("Gate D -- a positive affine rescale of the RETURNS themselves")
    close = walk()
    base = c22_stretch_decreasing(close)
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    for factor in (10.0, 3.7, 0.1, 2.5):
        scaled = Series(100.0 * np.cumprod(1.0 + factor * r), index=close.index)
        compare(f"returns x{factor:g}", base, c22_stretch_decreasing(scaled))

    head("Gate C/D -- fires, and is not constant")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1), ("penny", penny)):
        out = c22_stretch_decreasing(fn())
        vals, counts = np.unique(out.dropna().to_numpy(), return_counts=True)
        print(f"  {name}: fires {int(out.notna().sum())}/{len(out)}, "
              f"distinct {int(out.nunique())}")
        print(f"    values {vals.astype(int).tolist()} counts {counts.tolist()}")


def cost():
    head("Cost at 400,000 bars")
    close = walk(400000, seed=77)
    t0 = time.perf_counter()
    c22_stretch_decreasing(close)
    t1 = time.perf_counter()
    tracemalloc.start()
    c22_stretch_decreasing(close)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"  n=400,000: {1000.0 * (t1 - t0):.0f} ms, traced peak "
          f"{peak / 1e6:.1f} MB")


def engineered_boundary():
    """A single HAND-CONSTRUCTED window, built to be maximally sensitive to
    a one-bar look-ahead -- the broad random-splice sweep above is mostly
    blind to this bug class because the column's value range is narrow and
    heavily tied (see Gate C), so a one-bar perturbation rarely touches
    whichever segment happens to hold the window's own longest run.

    15 alternating returns (no run of negative diffs longer than 1), then a
    STRICTLY DECREASING tail of 5 values (4 negative diffs: a run of 4),
    then one more strictly smaller value that extends the decline (a run of
    5 once it enters the window). The window ending just BEFORE that last
    value must read 4; the window ending AT it must read 5. A one-bar
    look-ahead mutant reports the second number for the first window."""
    head("Gate B -- a single engineered window, built for maximum sensitivity")
    length = 20
    R = [0, 10] * 7 + [0] + [9, 8, 7, 6, 5] + [4]
    assert len(R) == 21
    closes = closes_from_returns(R)
    out = c22_stretch_decreasing(closes, length=length)
    print(f"  R = {R}")
    print(f"  bar 20 (pre-boundary window, R[0:20]) -> {float(out.iloc[20]):g} "
          f"(must be 4)")
    print(f"  bar 21 (one bar later, R[1:21])        -> {float(out.iloc[21]):g} "
          f"(must be 5)")
    assert float(out.iloc[20]) == 4.0
    assert float(out.iloc[21]) == 5.0
    for mid, mutant in zip(MUTANT_IDS[:4], MUTANTS[:4]):
        mod = load_mutant(*mutant)
        mutated = mod.c22_stretch_decreasing(closes, length=length)
        print(f"  {mid} mutant at bar 20 -> {float(mutated.iloc[20]):g} "
              f"(the real module's bar-21 answer, read one bar early)")
        assert float(mutated.iloc[20]) == 5.0


SECTIONS = {"gate_a": gate_a, "gate_b": gate_b, "noise_floor": noise_floor,
            "gate_c_d": gate_c_d, "cost": cost,
            "engineered_boundary": engineered_boundary}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SECTIONS)
    for name in wanted:
        SECTIONS[name]()
    print()
