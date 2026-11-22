# -*- coding: utf-8 -*-
"""C22-FORECAST-ERROR (PandasTa issue #137): every number in
`docs/C22ForecastErrorMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_forecast_error.py` and
`tests/test_c22_forecast_error.py`.

    python docs/measure_c22_forecast_error.py            # sections A-D, G
    python docs/measure_c22_forecast_error.py A D         # just those
    python docs/measure_c22_forecast_error.py P           # the GPL-3.0 black box

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
import math
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402,F401
from pandas_ta.statistics.c22_forecast_error import (  # noqa: E402
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, RESID_DDOF, TRAIN, ZSCORE_DDOF,
    _forecast_error_rows, c22_forecast_error)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_forecast_error")
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
        _BASE[name] = c22_forecast_error(FRAMES[name])
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
def value_from_exact(window, zddof=ZSCORE_DDOF, resddof=RESID_DDOF):
    """The definition re-spelled in plain Python with `math.fsum` and no
    numpy vectorisation: an independently re-derived oracle, not a copy of
    the shipped kernel's code path."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - zddof)
    if not (var >= 0.0):
        return float("nan")
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan")
    z = [(v - mean) / sd for v in w]
    resid = []
    for i in range(TRAIN, n):
        f = math.fsum(z[i - TRAIN:i]) / TRAIN
        resid.append(z[i] - f)
    rn = len(resid)
    rmean = math.fsum(resid) / rn
    rvar = math.fsum((v - rmean) ** 2 for v in resid) / (rn - resddof)
    if not (rvar >= 0.0):
        return float("nan")
    return math.sqrt(rvar)


# =================================================================== A
def section_a():
    head("A. Gate A -- correctness, against the exact fsum oracle")
    total = disagree = 0
    worst = 0.0
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        n_ran = 0
        local_worst = 0.0
        for i in range(0, win.shape[0], 23):
            mine = float(base(name).iloc[int(bars[i])])
            other = value_from_exact(win[i])
            total += 1
            n_ran += 1
            if math.isnan(mine) or math.isnan(other):
                if not (math.isnan(mine) and math.isnan(other)):
                    disagree += 1
                    continue
            else:
                gap = abs(mine - other)
                local_worst = max(local_worst, gap)
                worst = max(worst, gap)
                if gap > 1e-9:
                    disagree += 1
        row(name, "windows", n_ran, "worst |diff|", local_worst)
    row("TOTAL", "windows", total, "disagree(>1e-9)", disagree, "worst |diff|", worst)


# =================================================================== B
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b] = _forecast_error_rows(win[a:b])",
        "out[length - 1 + a:length - 1 + b] = _forecast_error_rows(win[a:b])"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
    "chunk-wide-mean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))"),
    "no-overflow-guard": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                          "bad |= ~(sd > NOISE_FLOOR)"),
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
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
        p.iloc[j:] *= 1.0003
        out = fn(p)
        a, bb = b.iloc[:j], out.iloc[:j]
        if not (a.isna() == bb.isna()).all() or (a[a.notna()] != bb[a.notna()]).any():
            hits += 1
    return hits


def section_b():
    head("B. Gate B -- causality")
    offsets = list(range(130, 1400, 30))
    for name in FRAMES:
        n = leaks(c22_forecast_error, FRAMES[name], offsets)
        row(name, f"{n} / {len(offsets)} leaking offsets")

    for mname, (old, new) in MUTANTS.items():
        mod = _load_mutant(old, new)
        live = not mod.c22_forecast_error(FRAMES["walk"]).equals(
            c22_forecast_error(FRAMES["walk"]))
        n = leaks(mod.c22_forecast_error, FRAMES["walk"], offsets)
        row("mutant", mname, "live?", live, "walk", f"{n} / {len(offsets)}")


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
    for name in FRAMES:
        close = FRAMES[name]
        b_ = base(name)
        for k in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            same = b_.equals(c22_forecast_error(close * k))
            row(name, f"x{k}", "bit-identical" if same else "MOVED")

    base_f = FRAMES["walk"]
    r = returns(base_f)
    for factor in (10.0, 3.7, 0.1, 1.0000001):
        scaled = np.empty(len(base_f))
        scaled[0] = 100.0
        scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
        a = base("walk").to_numpy()
        b = c22_forecast_error(pd.Series(scaled)).to_numpy()
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
        g = c22_forecast_error(f)
        win, _ = windows(f)
        sd_max = float(win.std(axis=1, ddof=ZSCORE_DDOF).max())
        row("ladder", step, "fires", int(g.notna().sum()), "max sd", sd_max,
            "< floor", sd_max < NOISE_FLOOR)
    for name, series in cases.items():
        g = c22_forecast_error(series)
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
        out = pycatch22.catch22_all([float(v) for v in window], catch24=False)
        i = out["names"].index("FC_LocalSimple_mean3_stde")
        return float(out["values"][i])

    total_windows = total_disagree_6 = total_disagree_9 = 0
    worst = 0.0
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        theirs = np.array([ref(w) for w in win])
        both = ~np.isnan(mine) & ~np.isnan(theirs)
        diff = np.abs(mine[both] - theirs[both])
        disagree_6 = int(np.sum(diff > 1e-6))
        disagree_9 = int(np.sum(diff > 1e-9))
        total_windows += int(both.sum())
        total_disagree_6 += disagree_6
        total_disagree_9 += disagree_9
        worst = max(worst, float(diff.max()) if diff.size else 0.0)
        row(name, "windows", int(both.sum()), "disagree(>1e-6)", disagree_6,
            "disagree(>1e-9)", disagree_9, "worst |diff|",
            float(diff.max()) if diff.size else 0.0)
    row("TOTAL", "windows", total_windows, "disagree(>1e-6)", total_disagree_6,
        "disagree(>1e-9)", total_disagree_9, "worst |diff|", worst)

    head("P1. The candidate fit that settled ZSCORE_DDOF and RESID_DDOF")
    row("Of six (z-ddof, resid-ddof-or-mode) candidates tried against the "
        "reference on 366 sampled windows (every 23rd of six frames):")

    def candidate(window, zddof, resddof, divide_by_sqrt_n):
        w = np.asarray(window, float)
        n = w.size
        if zddof is None:
            z = w
        else:
            z = (w - w.mean()) / w.std(ddof=zddof)
        forecast = sum(z[k:n - TRAIN + k] for k in range(TRAIN)) / TRAIN
        resid = z[TRAIN:] - forecast
        val = resid.std(ddof=resddof if resddof is not None else 1)
        if divide_by_sqrt_n:
            val = val / np.sqrt(resid.size)
        return float(val)

    fit_candidates = {
        "(1, 1) -- SHIPPED": (1, 1, False),
        "(1, 0)": (1, 0, False),
        "(0, 1)": (0, 1, False),
        "no z-score, (-, 1)": (None, 1, False),
        "(1, 1) / sqrt(length - 3) -- literal 'std ERROR'": (1, 1, True),
        "(0, 0)": (0, 0, False),
    }
    for label, (zddof, resddof, errscale) in fit_candidates.items():
        disagree = total = 0
        worst = 0.0
        for name in FRAMES:
            win, idx = windows(FRAMES[name])
            for i in range(0, win.shape[0], 23):
                mine = candidate(win[i], zddof, resddof, errscale)
                theirs = ref(win[i])
                total += 1
                gap = abs(mine - theirs)
                worst = max(worst, gap)
                if gap > 1e-6:
                    disagree += 1
        row(f"  {label}", f"{disagree} / {total} disagree(>1e-6)",
            f"worst {worst:.4g}")


SECTIONS = {
    "A": section_a, "B": section_b, "C": section_c, "D": section_d,
    "G": section_g, "P": section_p,
}


if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]]
    keys = args if args else [k for k in SECTIONS if k != "P"]
    for k in keys:
        if k not in SECTIONS:
            raise SystemExit(f"unknown section {k!r}; pick from {list(SECTIONS)}")
        SECTIONS[k]()
