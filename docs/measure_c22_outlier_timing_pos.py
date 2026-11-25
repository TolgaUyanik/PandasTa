# -*- coding: utf-8 -*-
"""C22-OUTLIER-TIMING-POS (PandasTa issue #143): every number in
`docs/C22OutlierTimingPosMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_outlier_timing_pos.py` and
`tests/test_c22_outlier_timing_pos.py`.

    python docs/measure_c22_outlier_timing_pos.py            # sections A-D, G, T
    python docs/measure_c22_outlier_timing_pos.py A D         # just those

No reference implementation is run: pycatch22 is GPL-3.0 and is not even
installed in this environment (not a declared dependency of this fork), and
the only local trace of it, `docs/issues/screen/ind_screen_r3.py`, calls the
library for MEASUREMENT ONLY and carries no algorithm. Gate A is against an
independent SECOND SPELLING (plain Python, `statistics.median`, no numpy,
no shared code with the shipped vectorised kernel) -- it checks the
IMPLEMENTATION against the chosen reading of the definition, not the
reading itself against a ground truth this session has no access to.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import math
import statistics
import sys
import time
import tracemalloc
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402,F401
from pandas_ta.statistics.c22_outlier_timing_pos import (  # noqa: E402
    INC, NOISE_FLOOR, TRIM_PCT, ZSCORE_DDOF, c22_outlier_timing_pos)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_outlier_timing_pos")
LENGTH = 100
N = 1500


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return pd.Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return pd.Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=23, level=2.0, sigma=0.012):
    return pd.Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=N, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return pd.Series(100.0 * np.cumprod(1.0 + r))


def jump_cluster(n=N, seed=31, sigma=0.008):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    r[::17] += 0.03
    return pd.Series(100.0 * np.cumprod(1.0 + r))


def student_t(n=N, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return pd.Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def ladder(n=N, step=0.01, start=100.0):
    return pd.Series(start * (1.0 + step) ** np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "jump-cluster": jump_cluster(),
    "student-t": student_t(),
}
STOCHASTIC = list(FRAMES)
_BASE: dict = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_outlier_timing_pos(FRAMES[name])
    return _BASE[name]


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def row(*cells):
    print(" | ".join(str(c) for c in cells))


# ---------------------------------------------------- independent spelling
def direct_threshold_sweep(window, inc=INC, ddof=ZSCORE_DDOF):
    """The definition re-spelled with no numpy: `math.fsum` mean/sd, a plain
    Python threshold sweep, `statistics.median` for both the per-step median
    position and the outer median. Positions are 1-indexed (MATLAB/hctsa
    `find()` convention)."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    sd = math.sqrt(var) if var > 0.0 else 0.0
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan")
    y = [((v - mean) / sd) for v in w]
    max_y = max(y)
    if not (max_y > 0.0):
        return float("nan")
    tot = sum(1 for v in y if v >= 0.0)
    nth = int(max_y / inc) + 1
    half = n / 2.0
    gap_nan, share, ranks = [], [], []
    for k in range(nth):
        thr = k * inc
        idx = [i + 1 for i in range(n) if y[i] >= thr]
        gap_nan.append(len(idx) < 2)
        share.append((len(idx) - 1) * 100.0 / tot)
        ranks.append(statistics.median(idx) / half - 1.0 if idx else float("nan"))
    # The reference's cut: the last step still including more than
    # TRIM_PCT percent, or the first step with fewer than two points.
    mj = max([k for k in range(nth) if share[k] > TRIM_PCT], default=0)
    fbi = min([k for k in range(nth) if gap_nan[k]], default=nth - 1)
    return statistics.median(ranks[:min(mj, fbi) + 1])


# =================================================================== A
def section_a():
    head("A. Gate A -- agreement with the independent plain-Python sweep")
    tot = agree = 0
    worst = 0.0
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        n_ok = n_bad = 0
        for i in range(0, win.shape[0], 11):
            ref = direct_threshold_sweep(win[i])
            a = mine[i]
            if math.isnan(a) and math.isnan(ref):
                n_ok += 1
                continue
            diff = abs(a - ref)
            worst = max(worst, diff)
            if diff < 1e-9:
                n_ok += 1
            else:
                n_bad += 1
        tot += n_ok + n_bad
        agree += n_ok
        row(name, "windows", n_ok + n_bad, "agree(<1e-9)", n_ok, "disagree", n_bad)
    row("TOTAL", tot, "agree", agree, "worst |diff|", worst)

    head("A2. ddof sensitivity (which positions clear an absolute threshold)")
    win, _ = windows(FRAMES["ar1"])
    moved = 0
    for i in range(0, win.shape[0], 13):
        a = direct_threshold_sweep(win[i], ddof=1)
        b = direct_threshold_sweep(win[i], ddof=0)
        if not (math.isnan(a) and math.isnan(b)) and a != b:
            moved += 1
    row("ar1", "windows moved between ddof=1 and ddof=0", moved)


# =================================================================== B
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b] = _outlier_timing_pos_rows(win[a:b])",
        "out[length - 1 + a:length - 1 + b] = _outlier_timing_pos_rows(win[a:b])"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "chunk-wide-mean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
}


def _load_mutant(old, new):
    src = Path(MODULE.__file__).read_text(encoding="utf-8")
    assert src.count(old) == 1, old
    mod = types.ModuleType("_mutant")
    mod.__file__ = MODULE.__file__
    exec(compile(src.replace(old, new), MODULE.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close, offsets):
    b = fn(close)
    hits = 0
    for j in offsets:
        p = close.copy()
        rng = np.random.default_rng(j)
        p.iloc[j:] = p.iloc[j - 1] * np.cumprod(
            1.0 + rng.normal(0.0005, 0.02, len(p) - j))
        out = fn(p)
        a, bb = b.iloc[:j], out.iloc[:j]
        if not (a.isna() == bb.isna()).all() or (a[a.notna()] != bb[a.notna()]).any():
            hits += 1
    return hits


def section_b():
    head("B. Gate B -- causality (future spliced away at each offset)")
    offsets = list(range(130, 1400, 60))
    for name in FRAMES:
        n = leaks(c22_outlier_timing_pos, FRAMES[name], offsets)
        row(name, f"{n} / {len(offsets)} leaking offsets")

    for mname, (old, new) in MUTANTS.items():
        mod = _load_mutant(old, new)
        n = leaks(mod.c22_outlier_timing_pos, FRAMES["walk"], offsets)
        row("mutant", mname, "walk", f"{n} / {len(offsets)} leaking offsets")


# =================================================================== C
def section_c():
    head("C. Gate C -- reachability")
    for name in FRAMES:
        out = base(name)
        v = out.dropna()
        row(name, f"{v.size} / {len(out)} fired", f"{v.nunique()} distinct",
            f"{v.min():.2f} .. {v.max():.2f}", f"median {v.median():.2f}")
    r = returns(FRAMES["penny"])
    row("penny zero-return fraction", round(float(np.mean(r == 0.0)), 4))


# =================================================================== D
def section_d():
    head("D. Gate D -- scale-free")
    for name in FRAMES:
        close = FRAMES[name]
        for k in (8.0, 64.0):
            same = base(name).equals(c22_outlier_timing_pos(close * k))
            row(name, f"x{k}", "bit-identical" if same else "MOVED")

    for name in FRAMES:
        close = FRAMES[name]
        r = returns(close)
        for factor in (10.0, 3.7):
            scaled = np.empty(len(close))
            scaled[0] = 100.0
            scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
            a = base(name).to_numpy()
            b = c22_outlier_timing_pos(pd.Series(scaled)).to_numpy()
            both = ~np.isnan(a) & ~np.isnan(b)
            moved = int(np.sum(np.abs(a[both] - b[both]) > 1e-9))
            mask = int(np.sum(np.isnan(a) != np.isnan(b)))
            row(name, f"returns x{factor}", "bars moved", moved, "of",
                int(both.sum()), "NaN-mask diffs", mask)
        for factor in (10.0, 3.7):
            a = base(name).to_numpy()
            b = c22_outlier_timing_pos(close * factor).to_numpy()
            both = ~np.isnan(a) & ~np.isnan(b)
            moved = int(np.sum(np.abs(a[both] - b[both]) > 1e-9))
            mask = int(np.sum(np.isnan(a) != np.isnan(b)))
            row(name, f"price x{factor}", "bars moved", moved, "NaN-mask diffs", mask)

    head("D3. A negative return rescale flips which tail is read")
    close = FRAMES["ar1"]
    r = returns(close)
    scaled = np.empty(len(close))
    scaled[0] = 100.0
    scaled[1:] = scaled[0] * np.cumprod(1.0 - r)
    a = base("ar1").to_numpy()
    b = c22_outlier_timing_pos(pd.Series(scaled)).to_numpy()
    both = ~np.isnan(a) & ~np.isnan(b)
    moved = int(np.sum(np.abs(a[both] - b[both]) > 1e-9))
    row("ar1", "r -> -r", "bars moved", moved, "of", int(both.sum()))


# =================================================================== G
def section_g():
    head("G. The floor, and what it buys")
    for step in (0.01, 0.001, -0.005):
        f = ladder(step=step)
        g = c22_outlier_timing_pos(f)
        win, _ = windows(f)
        sd_max = float(win.std(axis=1, ddof=ZSCORE_DDOF).max())
        row("ladder", step, "fires", int(g.notna().sum()), "max sd", sd_max,
            "< floor", sd_max < NOISE_FLOOR)
    g = c22_outlier_timing_pos(pd.Series(np.full(400, 100.0)))
    row("400 identical closes", "fires", int(g.notna().sum()))


# =================================================================== T
def section_t():
    """`reset_peak()`, not `stop()`: stopping would end the `__main__`
    trace that wraps every section, which is why an earlier version of this
    harness always read 0.0 MB for the global figure once T had run."""
    head("T. Cost")
    n = 100_000
    close = walk(n=n, seed=99)
    if tracemalloc.is_tracing():
        tracemalloc.reset_peak()
    else:
        tracemalloc.start()
    t0 = time.time()
    out = c22_outlier_timing_pos(close)
    dt = time.time() - t0
    peak = tracemalloc.get_traced_memory()[1]
    row(f"n={n}", f"wall {dt:.2f} s", f"peak {peak / 1e6:.1f} MB (since last reset)",
        "fired", int(out.notna().sum()))


SECTIONS = {"A": section_a, "B": section_b, "C": section_c, "D": section_d,
            "G": section_g, "T": section_t}

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]]
    keys = args if args else list(SECTIONS)
    t0 = time.time()
    tracemalloc.start()
    for k in keys:
        SECTIONS[k]()
    peak = tracemalloc.get_traced_memory()[1]
    print()
    print(f"peak traced memory: {peak / 1e6:.1f} MB, wall {time.time() - t0:.1f} s")
