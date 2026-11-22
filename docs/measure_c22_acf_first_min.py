# -*- coding: utf-8 -*-
"""C22-ACF-FIRST-MIN (PandasTa issue #131): every number in
`docs/C22AcfFirstMinMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_acf_first_min.py` and
`tests/test_c22_acf_first_min.py`.

    python docs/measure_c22_acf_first_min.py            # sections A-G
    python docs/measure_c22_acf_first_min.py A D         # just those
    python docs/measure_c22_acf_first_min.py P           # the GPL-3.0 black box

Section **P** is OPT-IN and is the only part of this repository that runs
the reference implementation (pycatch22, **GPL-3.0**). It is MEASUREMENT
only and no shipped module imports it. A bare run skips P and does not
import it; `importlib.util.find_spec` reports whether it is installed at
all, which does not execute the package.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_acf_first_min import (  # noqa: E402
    CHUNK_CELLS, MIN_LENGTH, NOISE_ULPS, _acf_first_min_rows,
    c22_acf_first_min)
from pandas_ta.statistics.c22_periodicity import c22_periodicity  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_acf_first_min")
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
        _BASE[name] = c22_acf_first_min(FRAMES[name])
    return _BASE[name]


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def spearman(a, b):
    x, y = pd.Series(np.asarray(a, float)), pd.Series(np.asarray(b, float))
    m = x.notna() & y.notna()
    if int(m.sum()) < 3:
        return float("nan")
    rx, ry = x[m].rank(), y[m].rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def row(*cells):
    print(" | ".join(str(c) for c in cells))


# ---------------------------------------------------- reference spellings
def loop_first_min(window):
    """A plain double loop, no FFT, no vectorisation: the direct
    sum-of-products autocorrelation at every lag, then the scan."""
    x = np.asarray(window, float)
    m = x.size
    d = x - x.mean()
    a0 = float(np.dot(d, d))
    acf = [1.0]
    for k in range(1, m):
        acf.append(float(np.dot(d[:m - k], d[k:])) / a0 if a0 > 0 else float("nan"))
    for k in range(1, m - 1):
        if acf[k - 1] > acf[k] and acf[k] < acf[k + 1]:
            return float(k)
    return float(m)


# =================================================================== A
def section_a():
    head("A. Gate A -- correctness against an independent loop")
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        ref = np.array([loop_first_min(w) for w in win[::7]])
        got = mine[::7]
        both = ~np.isnan(got) & ~np.isnan(ref)
        disagree = int(np.sum(got[both] != ref[both]))
        row(name, "windows", both.sum(), "disagree", disagree)

    head("A2. Closed forms")
    r = 0.01 * np.where(np.arange(150) % 2, -1.0, 1.0)
    out = c22_acf_first_min(pd.Series(100 * np.cumprod(np.r_[1.0, 1 + r])))
    row("alternating returns, all fired bars read", sorted(set(out.iloc[100:])))

    r2 = np.linspace(0.02, -0.02, 400)
    out2 = c22_acf_first_min(pd.Series(100 * np.cumprod(1 + r2)), length=100)
    row("linear ramp, all fired bars read", sorted(set(out2.iloc[100:])))


# =================================================================== B
MUTANT = ("out[length + a:length + b] = vals",
          "out[length - 1 + a:length - 1 + b] = vals")


def _load_mutant(old, new):
    src = Path(MODULE.__file__).read_text(encoding="utf-8")
    assert src.count(old) == 1
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
        p.iloc[j:] *= 1e3
        out = fn(p)
        a, bb = b.iloc[:j], out.iloc[:j]
        if not (a.isna() == bb.isna()).all() or (a[a.notna()] != bb[a.notna()]).any():
            hits += 1
    return hits


def section_b():
    head("B. Gate B -- causality")
    offsets = range(130, 1400, 30)
    for name in STOCHASTIC + ["cosine"]:
        n = leaks(c22_acf_first_min, FRAMES[name], offsets)
        row(name, f"{n} / {len(list(offsets))} leaking offsets")

    mod = _load_mutant(*MUTANT)
    row("mutant live?",
        not mod.c22_acf_first_min(FRAMES["walk"]).equals(
            c22_acf_first_min(FRAMES["walk"])))
    for name in ("walk", "cosine"):
        n = leaks(mod.c22_acf_first_min, FRAMES[name], offsets)
        row("mutant", name, f"{n} / {len(list(offsets))}")


# =================================================================== C
def section_c():
    head("C. Gate C -- reachability")
    for name in FRAMES:
        out = base(name)
        v = out.dropna()
        row(name, f"{v.size} / {len(out)} fired", f"{v.nunique()} distinct",
            f"{v.min()} .. {v.max()}", f"median {v.median()}",
            f"sentinel(==100) {int((v == 100).sum())}")


# =================================================================== D
def section_d():
    head("D. Gate D -- scale-free")
    for name in STOCHASTIC + ["cosine"]:
        close = FRAMES[name]
        b_ = base(name)
        for k in (8.0, 64.0):
            same = b_.equals(c22_acf_first_min(close * k))
            row(name, f"x{k}", "bit-identical" if same else "MOVED")
        v8 = c22_acf_first_min(close * 10.0)
        moved = int(((b_ != v8) & b_.notna() & v8.notna()).sum())
        row(name, "x10", f"{moved} moved")

    out = base("ar1").dropna()
    row("ar1 fires", out.size, "distinct", out.nunique(),
        "0 < fires < n", 0 < out.size < len(FRAMES["ar1"]))


# =================================================================== E
def section_e():
    head("E. The OWED rule -- against C22PERIODICITY_100 (synthetic, NOT Gate E)")
    pooled_mine, pooled_other = [], []
    for name in STOCHASTIC:
        mine = base(name)
        other = c22_periodicity(FRAMES[name])
        rho = spearman(mine, other)
        row(name, f"spearman {rho:.4f}" if not np.isnan(rho) else "nan")
        pooled_mine.append(mine)
        pooled_other.append(other)
    pm = pd.concat(pooled_mine)
    po = pd.concat(pooled_other)
    row("pooled", f"spearman {spearman(pm, po):.4f}")
    print("This is a synthetic-frame advisory only. Gate E's real BIST run,")
    print("against C22PERIODICITY_100 specifically, is the launcher's job;")
    print("docs/C22PeriodicityMeasured.md section E4 named this exact pair.")


# =================================================================== G
def section_g():
    head("G. The floor, and what it buys")

    def unguarded(close, length=LENGTH):
        win, idx = windows(close, length)
        out = np.full(len(close), np.nan)
        for i, w in enumerate(win):
            out[idx[i]] = loop_first_min(w)
        return out

    cases = {
        "six realistic frames": None,
        "price flat except one 1-ulp step": pd.Series(
            np.r_[np.full(200, 1e6), np.nextafter(1e6, 2e6), np.full(199, 1e6)]),
        "one 1-kurus tick per bar at 100": pd.Series(
            100.0 + 0.01 * (np.arange(300) % 2)),
        "400 identical closes": pd.Series(np.full(400, 100.0)),
    }
    for name in FRAMES:
        g = base(name)
        u = unguarded(FRAMES[name])
        diff = int(np.sum((g.to_numpy() != u) & g.notna().to_numpy()
                           & ~np.isnan(u)))
        row(name, "guarded fires", int(g.notna().sum()), "vs unguarded",
            int(np.sum(~np.isnan(u))), "differ", diff)
    for name, series in cases.items():
        if series is None:
            continue
        g = c22_acf_first_min(series)
        row(name, "guarded fires", int(g.notna().sum()), "of", len(series))


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
        return float(pycatch22.CO_FirstMin_ac([float(v) for v in window]))

    total_windows = total_disagree = 0
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        theirs = np.array([ref(w) for w in win])
        got = mine
        both = ~np.isnan(got) & ~np.isnan(theirs)
        disagree = int(np.sum(got[both] != theirs[both]))
        total_windows += int(both.sum())
        total_disagree += disagree
        row(name, "windows", int(both.sum()), "disagree", disagree,
            "spearman", f"{spearman(got[both], theirs[both]):.4f}")
    row("TOTAL", "windows", total_windows, "disagree", total_disagree)


SECTIONS = {
    "A": section_a, "B": section_b, "C": section_c, "D": section_d,
    "E": section_e, "G": section_g, "P": section_p,
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
