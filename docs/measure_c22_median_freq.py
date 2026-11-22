# -*- coding: utf-8 -*-
"""C22-MEDIAN-FREQ (PandasTa issue #138): every number in
`docs/C22MedianFreqMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_median_freq.py` and
`tests/test_c22_median_freq.py`.

    python docs/measure_c22_median_freq.py            # sections A-D, G, X
    python docs/measure_c22_median_freq.py A D        # just those

No reference implementation is run: hctsa and pycatch22 are GPL-3.0, and
`SP_Summaries_fft_wq_50` is an hctsa feature that pycatch22 does not
expose (catch22 ships the Welch-spectrum `SP_Summaries` read-outs only).
Gate A is against an independent DIRECT DFT (`math.fsum` over explicit
cos/sin sums, no FFT) written below.

Section **X** is the owed rule from `docs/C22PeriodicityMeasured.md` §E4
(measure this column against `C22PERIODICITY_100`), on the six synthetic
frames only: an advance warning, not Gate E.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import math
import sys
import time
import tracemalloc
import types
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_median_freq import (  # noqa: E402
    NOISE_FLOOR, QUANTILE, ZSCORE_DDOF, _median_freq_rows, c22_median_freq,
    nfft_for)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_median_freq")
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
        _BASE[name] = c22_median_freq(FRAMES[name])
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


# ---------------------------------------------------- reference spelling
def direct_dft_median_freq(window, quantile=QUANTILE, ddof=ZSCORE_DDOF):
    """The definition re-spelled without an FFT: `math.fsum` mean/sd, an
    explicit O(N * NFFT/2) DFT with the angle reduced modulo NFFT before
    `cos`/`sin`, `math.fsum` running sums. Returns `(w, margin)`: the
    output, and the smallest |running sum - quantile * total| / total over
    all bins -- how close this window came to a bin-boundary tie."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan"), float("nan")
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((v - mean) ** 2 for v in w) / (n - ddof))
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan"), float("nan")
    z = [(v - mean) / sd for v in w]
    nfft = nfft_for(n)
    half = nfft // 2
    power = []
    for k in range(half + 1):
        re = math.fsum(z[t] * math.cos(2 * math.pi * ((k * t) % nfft) / nfft)
                       for t in range(n))
        im = math.fsum(z[t] * math.sin(2 * math.pi * ((k * t) % nfft) / nfft)
                       for t in range(n))
        power.append(re * re + im * im)
    total = math.fsum(power)
    if not (total > 0.0):
        return float("nan"), float("nan")
    margin = float("inf")
    j = None
    for k in range(half + 1):
        cum = math.fsum(power[:k + 1])
        margin = min(margin, abs(cum - quantile * total) / total)
        if j is None and cum > quantile * total:
            j = k
    return math.pi * j / half, margin


# =================================================================== A
def section_a():
    head("A. Gate A -- correctness against the direct-DFT oracle (every 7th window)")
    tot = agree = 0
    worst_margin_disagree = 0.0
    min_margin = float("inf")
    for name in FRAMES:
        win, idx = windows(FRAMES[name])
        mine = base(name).to_numpy()[idx]
        n_ok = n_bad = 0
        for i in range(0, win.shape[0], 7):
            ref, margin = direct_dft_median_freq(win[i])
            a = mine[i]
            if math.isnan(a) and math.isnan(ref):
                n_ok += 1
                continue
            if math.isfinite(margin):
                min_margin = min(min_margin, margin)
            if a == ref:
                n_ok += 1
            else:
                n_bad += 1
                worst_margin_disagree = max(worst_margin_disagree, margin)
        tot += n_ok + n_bad
        agree += n_ok
        row(name, "windows", n_ok + n_bad, "exact agree", n_ok, "disagree", n_bad)
    row("TOTAL", tot, "exact agree", agree,
        "smallest tie margin seen", f"{min_margin:.3e}",
        "largest margin on a disagreeing window", worst_margin_disagree)

    head("A2. Designed windows with a known answer")
    t = np.arange(128, dtype=float)
    for k in (5, 20, 40, 63):
        x = np.cos(2 * np.pi * k * t / 128)
        got = float(_median_freq_rows(x.reshape(1, -1), 128)[0])
        row(f"pure cosine at bin {k}, length 128", "shipped", got,
            "expected pi*k/64", math.pi * k / 64, "equal", got == math.pi * k / 64)
    alt = np.where(np.arange(100) % 2 == 0, 1.0, -1.0)
    got = float(_median_freq_rows(alt.reshape(1, -1), 128)[0])
    ref, margin = direct_dft_median_freq(alt)
    row("alternating +1/-1, length 100", "shipped", got, "oracle", ref)

    head("A3. Direction: AR(1) returns, phi -> median of the column (1,400 bars)")
    for phi in (-0.6, -0.3, 0.0, 0.3, 0.6):
        s = c22_median_freq(ar1(phi=phi, seed=3)).dropna()
        row("phi", phi, "median", round(float(s.median()), 4),
            "mean", round(float(s.mean()), 4))


# =================================================================== B
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b] = _median_freq_rows(win[a:b], nfft)",
        "out[length - 1 + a:length - 1 + b] = _median_freq_rows(win[a:b], nfft)"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "chunk-wide-mean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-total": ("total = cum[:, -1]",
                         "total = np.full(cum.shape[0], cum[:, -1].mean())"),
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
    offsets = list(range(130, 1400, 30))
    for name in FRAMES:
        n = leaks(c22_median_freq, FRAMES[name], offsets)
        row(name, f"{n} / {len(offsets)} leaking offsets")

    for mname, (old, new) in MUTANTS.items():
        mod = _load_mutant(old, new)
        n = leaks(mod.c22_median_freq, FRAMES["walk"], offsets)
        row("mutant", mname, "walk", f"{n} / {len(offsets)} leaking offsets")


# =================================================================== C
def section_c():
    head("C. Gate C -- reachability")
    for name in FRAMES:
        out = base(name)
        v = out.dropna()
        row(name, f"{v.size} / {len(out)} fired", f"{v.nunique()} distinct",
            f"{v.min():.4f} .. {v.max():.4f}", f"median {v.median():.4f}")
    r = returns(FRAMES["penny"])
    row("penny zero-return fraction", round(float(np.mean(r == 0.0)), 4))


# =================================================================== D
def section_d():
    head("D. Gate D -- scale-free")
    for name in FRAMES:
        close = FRAMES[name]
        b_ = base(name)
        for k in (8.0, 64.0):
            same = b_.equals(c22_median_freq(close * k))
            row(name, f"x{k}", "bit-identical" if same else "MOVED")

    for name in FRAMES:
        close = FRAMES[name]
        r = returns(close)
        for factor in (10.0, 3.7):
            scaled = np.empty(len(close))
            scaled[0] = 100.0
            scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
            a = base(name).to_numpy()
            b = c22_median_freq(pd.Series(scaled)).to_numpy()
            both = ~np.isnan(a) & ~np.isnan(b)
            moved = int(np.sum(a[both] != b[both]))
            mask = int(np.sum(np.isnan(a) != np.isnan(b)))
            worst = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
            row(name, f"returns x{factor}", "bars moved", moved, "of", int(both.sum()),
                "NaN-mask diffs", mask, "worst |diff|", worst,
                "returns with 1 + factor*r <= 0 (price goes non-positive)",
                int(np.sum(1.0 + factor * r <= 0.0)))
        # the price-level rescale x10 / x3.7 (not exact in float)
        for factor in (10.0, 3.7):
            a = base(name).to_numpy()
            b = c22_median_freq(close * factor).to_numpy()
            both = ~np.isnan(a) & ~np.isnan(b)
            moved = int(np.sum(a[both] != b[both]))
            mask = int(np.sum(np.isnan(a) != np.isnan(b)))
            row(name, f"price x{factor}", "bars moved", moved, "NaN-mask diffs", mask)


# =================================================================== G
def section_g():
    head("G. The floor, and what it buys")
    for step in (0.01, 0.001, -0.005):
        f = ladder(step=step)
        g = c22_median_freq(f)
        win, _ = windows(f)
        sd_max = float(win.std(axis=1, ddof=ZSCORE_DDOF).max())
        row("ladder", step, "fires", int(g.notna().sum()), "max sd", sd_max,
            "< floor", sd_max < NOISE_FLOOR)
    g = c22_median_freq(pd.Series(np.full(400, 100.0)))
    row("400 identical closes", "fires", int(g.notna().sum()))


# =================================================================== X
def section_x():
    head("X. Advance warning (NOT Gate E): per-frame Spearman vs shipped neighbours")
    names = ["c22_periodicity", "ts_ac1_60", "diff2_acf1", "c22_acf_first_min",
             "tf_spec_entropy_64", "tf_autocorr_1e_60", "firstzero_ac"]
    for nm in names:
        cells = []
        for fr in FRAMES:
            a = base(fr)
            b = getattr(ta, nm)(FRAMES[fr])
            m = a.notna() & b.notna()
            if m.sum() < 50 or b[m].nunique() < 2 or a[m].nunique() < 2:
                cells.append("nan")
                continue
            cells.append(f"{spearmanr(a[m], b[m])[0]:+.3f}")
        row(f"{nm:20s}", *cells)
    row("frames:", *FRAMES)


SECTIONS = {"A": section_a, "B": section_b, "C": section_c, "D": section_d,
            "G": section_g, "X": section_x}

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
