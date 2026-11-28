# -*- coding: utf-8 -*-
"""C22-MODE-10 (PandasTa issue #136): every number in
`docs/C22Mode10Measured.md` and in the docstrings of
`pandas_ta/statistics/c22_mode_10.py` and `tests/test_c22_mode_10.py`.

    python docs/measure_c22_mode_10.py            # sections A-D, G, SHIFT
    python docs/measure_c22_mode_10.py A D        # just those
    python docs/measure_c22_mode_10.py P          # the GPL-3.0 black box

Section **P** is OPT-IN and is the only part of this repository that runs
the reference implementation (pycatch22, **GPL-3.0**). It is MEASUREMENT
only and no shipped module imports it. A bare run skips P and does not
import it; `importlib.util.find_spec` reports whether it is installed at
all, which does not execute the package. Section **SHIFT** checks the
additive-shift invariance claim over EVERY window of all six frames (the
test module only samples every 11th); see `docs/C22Mode10Measured.md`
section P2 for why it moves 40 of 1,400 `penny` windows and 0 elsewhere.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import importlib.util
import math
import sys
import time
import tracemalloc
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402,F401
from pandas_ta.statistics.c22_mode_10 import (  # noqa: E402
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, NUM_BINS, ZSCORE_DDOF,
    _mode10_rows, c22_mode_10)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_mode_10")
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


def cosine_returns(n=N, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return pd.Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


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
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
_BASE: dict = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_mode_10(FRAMES[name])
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


# ---------------------------------------------------- reference spellings
def exact_bin_assignment(window):
    """Which of the 10 bins each element falls into, with ZERO rounding
    (Fraction), plus the tied max-count bin set. Bin membership is
    affine-invariant to z-scoring, so the raw window settles it exactly."""
    y = [Fraction(float(v)) for v in window]
    mn, mx = min(y), max(y)
    width = (mx - mn) / NUM_BINS
    if width == 0:
        return None
    idx = []
    for v in y:
        i = int((v - mn) / width)
        if i >= NUM_BINS:
            i = NUM_BINS - 1
        idx.append(i)
    counts = [idx.count(i) for i in range(NUM_BINS)]
    m = max(counts)
    tied = tuple(i for i in range(NUM_BINS) if counts[i] == m)
    return mn, width, tied


def value_from_exact(window, ddof=ZSCORE_DDOF):
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    if not (var >= 0.0):
        return float("nan")
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan")
    exact = exact_bin_assignment(w)
    if exact is None:
        return float("nan")
    mn, width, tied = exact
    centres = [float(mn + width * Fraction(2 * i + 1, 2)) for i in tied]
    z_centres = [(c - mean) / sd for c in centres]
    return float(math.fsum(z_centres) / len(z_centres))


# =================================================================== A
def section_a():
    head("A. Gate A -- correctness against the exact bin-assignment oracle")
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        ref = np.array([value_from_exact(w) for w in win[::7]])
        got = mine[::7]
        both = ~np.isnan(got) & ~np.isnan(ref)
        worst = float(np.max(np.abs(got[both] - ref[both]))) if both.any() else 0.0
        row(name, "windows", int(both.sum()), "worst |diff|", worst)

    head("A2. The designed 4-way tie")
    window = [0.1, 0.2, 0.3, 1.2, 1.3, 2.2, 2.3, 2.4, 3.2,
              4.2, 5.2, 5.3, 5.4, 6.2, 7.2, 8.2, 8.3, 8.4, 9.0, 9.9]
    exact = exact_bin_assignment(window)
    mine = float(_mode10_rows(np.asarray(window, float).reshape(1, -1))[0])
    other = value_from_exact(window)
    row("tied bins", exact[2] if exact else None, "shipped", mine,
        "oracle", other)


# =================================================================== B
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b] = _mode10_rows(win[a:b])",
        "out[length - 1 + a:length - 1 + b] = _mode10_rows(win[a:b])"),
    "chunk-wide-mean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))"),
    "chunk-wide-minmax": (
        "        mn = z.min(axis=1)\n        mx = z.max(axis=1)",
        "        mn = np.full(rows, z.min())\n        mx = np.full(rows, z.max())"),
}


def _load_mutant(old, new):
    src = Path(MODULE.__file__).read_text(encoding="utf-8")
    assert src.count(old) == 1, old
    import types
    mod = types.ModuleType("_mutant")
    mod.__file__ = MODULE.__file__
    exec(compile(src.replace(old, new), MODULE.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close, offsets):
    b = fn(close)
    hits = 0
    for j in offsets:
        p = close.copy()
        p.iloc[j:] *= 1.0003
        out = fn(p)
        a, bb = b.iloc[:j], out.iloc[:j]
        if not (a.isna() == bb.isna()).all() or (a[a.notna()] != bb[a.notna()]).any():
            hits += 1
    return hits


def section_b():
    head("B. Gate B -- causality")
    offsets = range(130, 1400, 30)
    for name in STOCHASTIC + ["cosine"]:
        n = leaks(c22_mode_10, FRAMES[name], offsets)
        row(name, f"{n} / {len(list(offsets))} leaking offsets")

    for mname, (old, new) in MUTANTS.items():
        mod = _load_mutant(old, new)
        live = not mod.c22_mode_10(FRAMES["walk"]).equals(c22_mode_10(FRAMES["walk"]))
        row("mutant", mname, "live?", live)
        n = leaks(mod.c22_mode_10, FRAMES["walk"], offsets)
        row("mutant", mname, "walk", f"{n} / {len(list(offsets))}")


# =================================================================== C
def section_c():
    head("C. Gate C -- reachability")
    for name in FRAMES:
        out = base(name)
        v = out.dropna()
        row(name, f"{v.size} / {len(out)} fired", f"{v.nunique()} distinct",
            f"{v.min():.4f} .. {v.max():.4f}", f"median {v.median():.4f}")

    f = FRAMES["penny"]
    r = returns(f)
    row("penny zero-return fraction", float(np.mean(r == 0.0)))


# =================================================================== D
def section_d():
    head("D. Gate D -- scale-free")
    for name in STOCHASTIC + ["cosine"]:
        close = FRAMES[name]
        b_ = base(name)
        for k in (8.0, 64.0):
            same = b_.equals(c22_mode_10(close * k))
            row(name, f"x{k}", "bit-identical" if same else "MOVED")

    base_f = FRAMES["walk"]
    r = returns(base_f)
    for factor in (10.0, 3.7, 0.1, 1.0000001):
        scaled = np.empty(len(base_f))
        scaled[0] = 100.0
        scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
        a = base("walk").to_numpy()
        b = c22_mode_10(pd.Series(scaled)).to_numpy()
        both = ~np.isnan(a) & ~np.isnan(b)
        worst = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
        row("walk", f"x{factor}", "worst |diff|", worst)

    out = base("ar1").dropna()
    row("ar1 fires", out.size, "distinct", out.nunique(),
        "0 < fires < n", 0 < out.size < len(FRAMES["ar1"]))


# =================================================================== G
def section_g():
    head("G. The floor, and what it buys")
    cases = {
        "price flat except one 1-ulp step": pd.Series(
            np.r_[np.full(200, 1e6), np.nextafter(1e6, 2e6), np.full(199, 1e6)]),
        "one 1-kurus tick per bar at 100": pd.Series(
            100.0 + 0.01 * (np.arange(300) % 2)),
        "400 identical closes": pd.Series(np.full(400, 100.0)),
    }
    for step in (0.01, 0.001, -0.005):
        f = ladder(step=step)
        g = c22_mode_10(f)
        win, _ = windows(f)
        sd_max = float(win.std(axis=1, ddof=ZSCORE_DDOF).max())
        row("ladder", step, "fires", int(g.notna().sum()), "max sd", sd_max,
            "< floor", sd_max < NOISE_FLOOR)
    for name, series in cases.items():
        g = c22_mode_10(series)
        row(name, "fires", int(g.notna().sum()), "of", len(series))


# =================================================================== P
def section_p():
    head("P. The reference implementation as a black box (GPL-3.0, opt-in)")
    installed = importlib.util.find_spec("pycatch22") is not None
    row("pycatch22 installed in this worktree", installed)
    if not installed:
        row("pycatch22", "ABSENT -- section P cannot run")
        return
    import pycatch22  # noqa: E402  (opt-in, GPL-3.0, measurement only)

    def ref(window):
        out = pycatch22.catch22_all([float(v) for v in window],
                                    catch24=False)
        i = out["names"].index("DN_HistogramMode_10")
        return float(out["values"][i])

    total_windows = total_disagree_9 = total_disagree_5 = 0
    worst = 0.0
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        theirs = np.array([ref(w) for w in win])
        got = mine
        both = ~np.isnan(got) & ~np.isnan(theirs)
        diff = np.abs(got[both] - theirs[both])
        disagree_9 = int(np.sum(diff > 1e-9))
        disagree_5 = int(np.sum(diff > 1e-5))
        total_windows += int(both.sum())
        total_disagree_9 += disagree_9
        total_disagree_5 += disagree_5
        worst = max(worst, float(diff.max()) if diff.size else 0.0)
        row(name, "windows", int(both.sum()), "disagree(>1e-9)", disagree_9,
            "disagree(>1e-5)", disagree_5, "worst |diff|",
            float(diff.max()) if diff.size else 0.0)
    row("TOTAL", "windows", total_windows, "disagree(>1e-9)", total_disagree_9,
        "disagree(>1e-5)", total_disagree_5, "worst |diff|", worst)

    head("P2. Root-causing the large-gap windows (all on the `penny` frame)")
    win, idx = windows(FRAMES["penny"])
    mine = base("penny").to_numpy()[idx]
    theirs = np.array([ref(w) for w in win])
    diff = np.abs(mine - theirs)
    bad = np.where(diff > 1e-5)[0]
    row("penny windows disagreeing beyond 1e-5", len(bad), "of", len(win))

    repeat_counts = []
    for b in bad:
        _, counts = np.unique(np.round(win[b], 6), return_counts=True)
        repeat_counts.append(int(counts.max()))
    row("repeat count of the dominant value across all", len(bad),
        "bad windows: min", min(repeat_counts), "max", max(repeat_counts))

    for b in bad[:3]:
        w = win[b]
        uniq, counts = np.unique(np.round(w, 6), return_counts=True)
        mode_val = uniq[np.argmax(counts)]
        row("window idx", int(b), "mine", mine[b], "theirs", theirs[b],
            "repeated value", mode_val, "repeat count", int(counts.max()),
            "of", len(w))

        mean64, sd64 = w.mean(), w.std(ddof=ZSCORE_DDOF)
        z64 = (w - mean64) / sd64
        width64 = (z64.max() - z64.min()) / NUM_BINS
        bin64 = int(np.floor(((mode_val - mean64) / sd64 - z64.min()) / width64))

        w32 = w.astype(np.float32)
        mean32, sd32 = w32.mean(), w32.std(ddof=ZSCORE_DDOF)
        z32 = (w32 - mean32) / sd32
        width32 = (z32.max() - z32.min()) / NUM_BINS
        bin32 = int(np.floor(
            ((np.float32(mode_val) - mean32) / sd32 - z32.min()) / width32))
        row("  the repeated value's own bin: float64", bin64,
            "vs a float32 re-run of the SAME formula", bin32)


def section_shift():
    head("SHIFT. Additive-shift invariance, every window, all six frames")
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        mine = base(name).to_numpy()[bars]
        moved = 0
        worst = 0.0
        for i in range(win.shape[0]):
            other = value_from_exact(win[i] + 5.0)
            a, b = mine[i], other
            if math.isnan(a) or math.isnan(b):
                if not (math.isnan(a) and math.isnan(b)):
                    moved += 1
                continue
            d = abs(a - b)
            worst = max(worst, d)
            if d > 1e-9:
                moved += 1
        row(name, "windows", win.shape[0], "moved beyond 1e-9", moved,
            "worst |diff|", worst)


SECTIONS = {
    "A": section_a, "B": section_b, "C": section_c, "D": section_d,
    "G": section_g, "P": section_p, "SHIFT": section_shift,
}

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]]
    keys = args if args else [k for k in SECTIONS if k != "P"]
    t0 = time.time()
    tracemalloc.start()
    for k in keys:
        SECTIONS[k]()
    peak = tracemalloc.get_traced_memory()[1]
    print()
    print(f"peak traced memory: {peak / 1e6:.1f} MB, wall {time.time() - t0:.1f} s")
