# -*- coding: utf-8 -*-
"""Reproduce every number in docs/C22HighFluctuationMeasured.md for
`c22_high_fluctuation` (PandasTa issue #144, C22-HIGH-FLUCTUATION).

Run from the repository root:

    python docs/measure_c22_high_fluctuation.py            # every section
    python docs/measure_c22_high_fluctuation.py gate_b      # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.

No reference implementation is run: pycatch22 and hctsa are GPL-3.0. Gate A
is against an independent spelling using Python's stdlib `statistics`
module (a different mean/variance algorithm than numpy's), written below.
"""
import importlib
import statistics
import sys
import time
import tracemalloc
import types

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.c22_high_fluctuation import c22_high_fluctuation

LENGTH = 100
THRESHOLD = 0.04
REAL = importlib.import_module("pandas_ta.statistics.c22_high_fluctuation")


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
def oracle_share(returns, threshold=THRESHOLD, ddof=1, floor=None):
    """`statistics.mean`/`statistics.stdev` (stdlib, a different algorithm
    than numpy's) z-score the window, then a plain Python loop counts diffs
    over `threshold`. No shared array machinery or constant with the
    shipped module."""
    floor = REAL.NOISE_FLOOR if floor is None else floor
    r = [float(v) for v in returns]
    if not all(np.isfinite(v) for v in r):
        return float("nan")
    sd = statistics.stdev(r) if ddof == 1 else statistics.pstdev(r)
    if not (sd > floor):
        return float("nan")
    mu = statistics.mean(r)
    z = [(v - mu) / sd for v in r]
    d = [z[i + 1] - z[i] for i in range(len(z) - 1)]
    hits = sum(1 for v in d if abs(v) > threshold)
    return hits / len(d)


def oracle_series(close, length=LENGTH):
    """Mirrors the module's own return convention exactly: `r[0]` is a NaN
    SENTINEL (the first return is undefined), not `c[0] / c[-1]`
    (Python negative-index wraparound -- the `ssf` bug class `CLAUDE.md`
    warns about), and the window ending at output index `t` holds returns
    `t - length + 1 .. t`."""
    c = [float(v) for v in close.to_numpy()]

    def ret(i):
        return float("nan") if i == 0 else c[i] / c[i - 1] - 1.0

    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        r = [ret(i) for i in range(t - length + 1, t + 1)]
        if not all(np.isfinite(v) for v in r):
            continue
        out[t] = oracle_share(r)
    return Series(out, index=close.index)


# ----------------------------------------------------------------- Gate A
def gate_a():
    head("Gate A1 -- windows whose answer is derived by hand")
    cases = [
        ([0.0, 0.0, 0.0], float("nan"), "constant returns: sd is 0, no "
         "z-score to take -- NaN, not a share read off rounding noise"),
        ([0.0, 1.0, 2.0], 1.0, "strictly monotone: z = [-1, 0, 1], both "
         "diffs are exactly 1.0, far above 0.04"),
        ([0.0, 1.0, 1.001], None, "a tiny final step: one big diff, one "
         "diff that lands below threshold -- see printed share"),
    ]
    for r, expected, why in cases:
        n = len(r)
        out = c22_high_fluctuation(closes_from_returns(r), length=n)
        got = float(out.iloc[-1])
        orc = oracle_share(r)
        both_nan = np.isnan(got) and np.isnan(orc)
        ok = both_nan or got == orc
        print(f"  length={n} returns={r} -> port={got:g} oracle={orc:g} "
              f"[{'OK' if ok else 'MISMATCH'}]  {why}")

    head("Gate A2 -- an independent stdlib-statistics spelling, window by "
         "window")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.6)", ar1())):
        base, orc = c22_high_fluctuation(frame), oracle_series(frame)
        compare(name, base, orc)
        r = (frame / frame.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        sd = W.std(axis=1, ddof=1)
        print(f"    windows reaching the floor: "
              f"{int((sd <= REAL.NOISE_FLOOR).sum())} of {len(sd)}")


# --------------------------------------------------------------- min_length
def min_length():
    head("min_length -- is a 2-return window a forced constant?")
    rng = np.random.default_rng(0)
    vals2 = set()
    for _ in range(3000):
        r = rng.normal(0.0, 1.0, 2)
        vals2.add(round(oracle_share(r), 6))
    print(f"  n=2, 3000 random draws -> distinct shares {sorted(vals2)}")

    head("min_length -- is a 3-return window genuinely data-dependent?")
    vals3 = set()
    for _ in range(30000):
        r = rng.normal(0.0, 1.0, 3)
        vals3.add(round(oracle_share(r), 6))
    print(f"  n=3, 30000 random draws -> distinct shares {sorted(vals3)}")


# ----------------------------------------------------------------- Gate B
WRITE_BACK_DATED = (
    "    out[length - 1:] = np.where(bad, np.nan, share)",
    "    out[length - 2:-1] = np.where(bad, np.nan, share)")
FORWARD_RETURN = (
    "    with np.errstate(over=\"ignore\"):\n        r[1:] = c[1:] / c[:-1] - 1.0",
    "    with np.errstate(over=\"ignore\"):\n        r[:-1] = c[1:] / c[:-1] - 1.0")
FORWARD_DIFF = ("    d = z[:, 1:] - z[:, :-1]",
                "    d = np.roll(z[:, 1:] - z[:, :-1], -1, axis=0)")
FORWARD_SD = ("        sd = windows.std(axis=1, ddof=ZSCORE_DDOF)",
             "        sd = np.roll(windows.std(axis=1, ddof=ZSCORE_DDOF), -1)")

MUTANTS = [WRITE_BACK_DATED, FORWARD_RETURN, FORWARD_DIFF, FORWARD_SD]
MUTANT_IDS = ["write_back_dated", "forward_return", "forward_diff",
              "forward_sd"]
OFFSETS = range(140, 1500, 40)
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "ar1(+0.6)": (ar1(), ar1(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_c22_high_fluctuation_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def _spliced(close, j, seed):
    rng = np.random.default_rng(seed)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def leak_offsets(fn, close, offsets=OFFSETS, splices=8):
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


def gate_b():
    head("Gate B -- future-perturbation sweep, real module and four mutants")
    n = len(list(OFFSETS))
    print(f"  {n} offsets J = {OFFSETS.start}..{max(OFFSETS)} step "
          f"{OFFSETS.step}, 8 independent random splices tried per offset")
    for frame in sorted(FRAMES):
        close, _ = FRAMES[frame]
        hits = leak_offsets(c22_high_fluctuation, close)
        print(f"  {frame}: real module {len(hits)}/{n}")
    for mid, mutant in zip(MUTANT_IDS, MUTANTS):
        mod = load_mutant(*mutant)
        for frame in sorted(FRAMES):
            close, _ = FRAMES[frame]
            live = not mod.c22_high_fluctuation(close).equals(
                c22_high_fluctuation(close))
            hit = leak_offsets(mod.c22_high_fluctuation, close)
            missed = [j for j in OFFSETS if j not in hit]
            print(f"  {mid} on {frame}: caught {len(hit)}/{n} "
                  f"(live mutation={live})")
            if missed:
                print(f"    missed J = {missed}")


# ------------------------------------------------------- the noise floor
def noise_floor():
    head("The noise floor -- an exactly geometric path")
    for name, frame in (("1%-a-bar ladder", geometric_ladder()),
                        ("-0.5%-a-bar ladder", geometric_ladder(step=-0.005)),
                        ("x1.5 ladder", Series(np.cumprod(np.full(300, 1.5))))):
        guarded = c22_high_fluctuation(frame)
        gv = sorted(set(guarded.dropna().tolist()))
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}/"
              f"{len(frame)} values {gv}")
        r = (frame / frame.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        sd = W.std(axis=1, ddof=1)
        print(f"    window sd max {float(np.nanmax(sd)):.3e} vs floor "
              f"{REAL.NOISE_FLOOR:.3e}")


# ---------------------------------------------------------------- Gate C/D
def gate_c_d():
    head("Gate D -- a power-of-two price rescale")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1), ("penny", penny)):
        close = fn()
        for k in (8.0, 64.0):
            compare(f"{name} x{k:g}", c22_high_fluctuation(close),
                    c22_high_fluctuation(close * k))

    head("Gate D -- a price rescale that is NOT a power of two")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded)):
        close = fn()
        for k in (10.0, 3.7, 0.1):
            compare(f"{name} x{k:g}", c22_high_fluctuation(close),
                    c22_high_fluctuation(close * k))

    head("Gate D -- a positive affine rescale of the RETURNS themselves "
         "(tolerance, not bit-identical)")
    close = walk()
    base = c22_high_fluctuation(close)
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    for factor in (10.0, 3.7, 0.1, 2.5):
        for shift in (0.0, 0.01):
            scaled = Series(100.0 * np.cumprod(1.0 + factor * r + shift),
                            index=close.index)
            compare(f"returns x{factor:g}+{shift:g}", base,
                    c22_high_fluctuation(scaled))

    head("Gate D -- a NEGATIVE rescale of the returns (sign flips, "
         "magnitude doesn't)")
    negated = Series(100.0 * np.cumprod(1.0 - r), index=close.index)
    compare("returns x-1", base, c22_high_fluctuation(negated))

    head("Gate C/D -- fires, and is not constant")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1), ("penny", penny)):
        out = c22_high_fluctuation(fn())
        vals = np.unique(out.dropna().to_numpy())
        print(f"  {name}: fires {int(out.notna().sum())}/{len(out)}, "
              f"distinct {int(out.nunique())}, min/max "
              f"{float(vals.min()):.4f}/{float(vals.max()):.4f}")


def cost():
    head("Cost at 400,000 bars")
    close = walk(400000, seed=77)
    t0 = time.perf_counter()
    c22_high_fluctuation(close)
    t1 = time.perf_counter()
    tracemalloc.start()
    c22_high_fluctuation(close)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"  n=400,000: {1000.0 * (t1 - t0):.0f} ms, traced peak "
          f"{peak / 1e6:.1f} MB")


SECTIONS = {"gate_a": gate_a, "min_length": min_length, "gate_b": gate_b,
            "noise_floor": noise_floor, "gate_c_d": gate_c_d, "cost": cost}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SECTIONS)
    for name in wanted:
        SECTIONS[name]()
    print()
