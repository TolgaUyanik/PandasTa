# -*- coding: utf-8 -*-
"""C22-WHITEN-TIMESCALE (PandasTa issue #139): every number in
`docs/C22WhitenTimescaleMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_whiten_timescale.py` and
`tests/test_c22_whiten_timescale.py`.

    python docs/measure_c22_whiten_timescale.py          # every section
    python docs/measure_c22_whiten_timescale.py A D      # just those

No section imports the reference implementation (pycatch22, GPL-3.0); it is
not installed on the machine this port was written on, and section A's
reference is a literal re-spelling of the published DEFINITION (FFT
autocorrelation, `while acf > 0`), written for this script.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import math
import sys
import time
import tracemalloc
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_whiten_timescale import (  # noqa: E402
    CHUNK_VALUES, NOISE_FLOOR, c22_whiten_timescale)

MODULE = importlib.import_module("pandas_ta.statistics.c22_whiten_timescale")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
N = 1500


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return pd.Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return pd.Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: many returns are exactly 0."""
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


def linear_returns(n=N, a=0.001, b=1e-5):
    """Returns that are an exact LINE in the bar index: the window varies,
    the 1-step residual is a constant up to rounding."""
    r = a + b * np.arange(n, dtype=float)
    return pd.Series(100.0 * np.cumprod(1.0 + r))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
_BASE: dict[str, pd.Series] = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_whiten_timescale(FRAMES[name])
    return _BASE[name]


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


def diff_bars(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(x[both] != y[both])),
            int(np.sum(np.isnan(x) != np.isnan(y))))


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
def ref_acf(y):
    """catch22's `co_autocorrs` as defined: FFT of the demeaned series padded
    to twice the next power of two, power spectrum, inverse FFT, divided by
    lag 0."""
    y = np.asarray(y, float)
    m = y - y.mean()
    nfft = 1 << int(math.ceil(math.log2(len(y))))
    f = np.fft.fft(m, 2 * nfft)
    a = np.fft.ifft(f * np.conj(f)).real
    return a / a[0]


def ref_firstzero(y, maxtau=None):
    """catch22's `co_firstzero`: `while (acf[z] > 0 && z < maxtau) z++`."""
    acf = ref_acf(y)
    maxtau = len(y) if maxtau is None else maxtau
    z = 0
    while acf[z] > 0 and z < maxtau:
        z += 1
    return z


def ref_value(window, train=1, zscore=True):
    """`FC_LocalSimple_mean_tauresrat(y, train)` as defined, on a z-scored
    window (catch22 z-scores every input)."""
    y = np.asarray(window, float)
    if zscore:
        y = (y - y.mean()) / y.std(ddof=1)
    res = np.array([y[i + train] - y[i:i + train].mean()
                    for i in range(len(y) - train)])
    return ref_firstzero(res) / ref_firstzero(y)


def exact_firstzero(y):
    """The same crossing in exact rationals: the input doubles, the mean, the
    deviations and every lagged sum as `Fraction`s, so nothing rounds."""
    q = [Fraction(float(v)) for v in y]
    mu = sum(q) / len(q)
    d = [v - mu for v in q]
    for k in range(1, len(d)):
        if not sum(d[i] * d[i + k] for i in range(len(d) - k)) > 0:
            return k
    return len(d)


def exact_value(window):
    y = [float(v) for v in window]
    res = [y[i + 1] - y[i] for i in range(len(y) - 1)]
    return exact_firstzero(res) / exact_firstzero(y)


def taus(window):
    w = np.asarray(window, float)
    return ref_firstzero(np.diff(w)), ref_firstzero(w)


# ===================================================================== S
def section_s():
    head("S. What the column is, per frame (1,500 bars, length 100)")
    row("frame", "fired", "distinct", "min", "median", "max",
        "share == 1", "numerator == 1 (windows)", "tie rate", "largest lag")
    for k in FRAMES:
        s = base(k).dropna().to_numpy()
        win, _ = windows(FRAMES[k])
        tt = [taus(win[i]) for i in range(win.shape[0])]
        num = [t[0] for t in tt]
        row(k, s.size, len(set(s.tolist())), f"{s.min():.4f}",
            f"{np.median(s):.4f}", f"{s.max():.4f}",
            f"{np.mean(s == 1.0):.3f}",
            f"{sum(v == 1 for v in num)}/{len(num)}",
            f"{np.mean(s[1:] == s[:-1]):.3f}", max(max(t) for t in tt))
    print()
    row("values on the walk", sorted(set(np.round(base("walk").dropna(), 6).tolist())))


# ===================================================================== A
def section_a():
    head("A1. Shipped against the literal catch22 spelling, EVERY window")
    tot = agree = 0
    for k in FRAMES:
        win, bars = windows(FRAMES[k])
        mine = base(k).to_numpy()[bars]
        ref = np.array([ref_value(w) for w in win])
        moved, mask = diff_bars(mine, ref)
        tot += win.shape[0]
        agree += win.shape[0] - moved - mask
        split = np.where(mine != ref)[0]
        module_right = sum(mine[i] == exact_value(win[i]) for i in split)
        row(k, f"windows {win.shape[0]}", f"moved {moved}", f"mask {mask}",
            f"exact oracle sides with the module on {module_right} of {split.size}")
        for i in split:
            row(f"  split: {k} window {int(i)} (bar {int(bars[i])})",
                f"module {mine[i]:.4f}", f"FFT spelling {ref[i]:.4f}",
                f"exact {exact_value(win[i]):.4f}")
    row("total", f"{agree} of {tot} agree")

    head("A2. Exact rational oracle (stride 13)")
    tot = bad = 0
    for k in FRAMES:
        win, bars = windows(FRAMES[k])
        mine = base(k).to_numpy()[bars]
        for i in range(0, win.shape[0], 13):
            tot += 1
            bad += mine[i] != exact_value(win[i])
    row(f"{bad} disagreements of {tot} windows")

    head("A3. Why the numerator is almost always 1")
    for k in FRAMES:
        win, _ = windows(FRAMES[k])
        ac1 = [ref_acf(np.diff(w))[1] for w in win]
        row(k, f"lag-1 acf of the residual: max {max(ac1):+.4f}",
            f"median {np.median(ac1):+.4f}")
    # For a stationary r the residual's lag-1 autocorrelation is
    # (2 rho1 - 1 - rho2) / (2 (1 - rho1)): -1/2 for white noise, -(1 - phi)/2
    # for an AR(1), so it nears zero -- and sampling noise can flip it -- only
    # as phi nears 1; a smooth r (the cosine) makes it positive outright.
    for phi in (0.3, 0.6, 0.8, 0.9, 0.95):
        f = ar1(phi=phi)
        win, _ = windows(f)
        n1 = sum(taus(w)[0] == 1 for w in win)
        row(f"ar1 phi {phi}", f"numerator == 1 on {n1} of {len(win)}")
    for p in (20, 40, 60, 100, 200):
        f = cosine_returns(period=p)
        s = c22_whiten_timescale(f).dropna()
        win, _ = windows(f)
        t = [taus(w) for w in win[::50]]
        row(f"cosine P={p}", f"values {sorted(set(np.round(s, 4).tolist()))[:6]}",
            f"(tau_e, tau_r) sample {t[:3]}")

    head("A4. z-scoring the window changes nothing")
    for k in FRAMES:
        win, bars = windows(FRAMES[k])
        a = [ref_value(w, zscore=True) for w in win[::7]]
        b = [ref_value(w, zscore=False) for w in win[::7]]
        row(k, f"moved {diff_bars(a, b)[0]} of {len(a)}")

    head("A5. `> 0` against `>= 0`: does an EXACT zero ever decide?")
    for k in FRAMES:
        win, _ = windows(FRAMES[k])
        zeros = 0
        for w in win:
            for y in (w, np.diff(w)):
                d = y - y.mean()
                z = 0
                for kk in range(1, len(d)):
                    p = float(np.dot(d[:-kk], d[kk:]))
                    if p == 0.0:
                        zeros += 1
                    if not p > 0:
                        break
        row(k, f"exact-zero lagged sums met in the scan: {zeros}")

    head("A6. The divergence from FIRSTZEROAC_100 (Kats' rule)")
    for k in FRAMES:
        win, bars = windows(FRAMES[k])
        mine = base(k).to_numpy()[bars]
        fz = ta.firstzero_ac(FRAMES[k]).to_numpy()[bars]
        tau_r = np.array([taus(w)[1] for w in win])
        row(k, f"windows with tau_r == 1: {int(np.sum(tau_r == 1))}",
            f"spearman vs FIRSTZEROAC {spearman(mine, fz):+.4f}")


# ===================================================================== B
MUTANTS = {
    "write-back-dated": ("out[length + a:length + b]",
                         "out[length - 1 + a:length - 1 + b]"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
    "chunk-wide-demean": ("d = x - x.mean(axis=1, keepdims=True)",
                          "d = x - x.mean()"),
    "no-overflow-guard": ("bad |= ~np.isfinite(ss_r) | ~np.isfinite(ss_e)",
                          "bad |= np.zeros_like(bad)"),
}


def mutant(name):
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_whiten_timescale"]


def _spliced(close, j, seed=909):
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return pd.Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=35):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=8):
    bad = np.asarray(fn(close), float)
    hits = []
    for j in offsets:
        for s in range(splices):
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s)), float)
            if not same(bad[:j], other[:j]):
                hits.append(j)
                break
    return hits


def section_b():
    head("B1. Future-perturbation sweep, real module (35 offsets x 8 splices)")
    for k in FRAMES:
        f = FRAMES[k]
        row(k, f"leaks {len(_leaks(c22_whiten_timescale, f, _offsets(len(f))))} of 35")
    for L in (10, 30, 250):
        f = FRAMES["walk"]
        h = _leaks(lambda s: c22_whiten_timescale(s, length=L), f,
                   _offsets(len(f), L), splices=4)
        row(f"walk, length {L}", f"leaks {len(h)} of 35")

    head("B2. Mutants (walk, tick-rounded, ar1)")
    for name in MUTANTS:
        fn = mutant(name)
        cells = []
        for k in ("walk", "tick-rounded", "ar1"):
            f = FRAMES[k]
            cells.append(f"{k} {len(_leaks(fn, f, _offsets(len(f))))}/35")
        row(name, *cells)

    head("B3. The mask mutant on a dirty frame")
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    row("clean walk bit-equal", same(c22_whiten_timescale(clean), fn(clean)))
    caught, first = 0, set()
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_whiten_timescale(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            first.add(int(moved.min()) - j)
    row(f"caught {caught} of 12", f"first moved bar - J: {sorted(first)}")

    head("B4. One-bar mutant: first moved bar relative to the splice")
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    rel = []
    for j in _offsets(len(f)):
        other = np.asarray(fn(_spliced(f, j)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            rel.append(int(moved.min()) - j)
    row(f"offsets with a pre-splice move {len(rel)} of 35", f"J offsets {sorted(set(rel))}")


# ===================================================================== C
def section_c():
    head("C1. Reachability on six synthetic frames")
    for k in FRAMES:
        s = base(k)
        row(k, f"fired {int(s.notna().sum())} of {len(s)}",
            f"first fired bar {int(s.notna().values.argmax())}",
            f"distinct {s.nunique()}")
    head("C2. The issue's worry: tick rounding")
    for k in ("walk", "tick-rounded", "penny"):
        r = returns(FRAMES[k])
        s = base(k).dropna()
        row(k, f"zero returns {np.mean(r == 0):.3f}", f"median {s.median():.4f}",
            f"share == 1 {np.mean(s == 1):.3f}")


# ===================================================================== D
def section_d():
    head("D1. Exact binary rescales")
    for k in FRAMES:
        cells = [f"x{fac:g} {same(base(k), c22_whiten_timescale(FRAMES[k] * fac))}"
                 for fac in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40)]
        row(k, *cells)
    for L in (10, 30, 250):
        f = FRAMES["walk"]
        row(f"walk length {L}", *[same(c22_whiten_timescale(f, length=L),
                                        c22_whiten_timescale(f * fac, length=L))
                                   for fac in (8.0, 64.0)])
    for lvl in (1e-6, 1e6, 1e100):
        f = walk(level=lvl)
        b = c22_whiten_timescale(f)
        row(f"level {lvl:g}", f"fired {int(b.notna().sum())}",
            f"x8 {same(b, c22_whiten_timescale(f * 8.0))}")
    head("D2. Inexact rescales (bars moved, NaN-mask differences)")
    for k in FRAMES:
        row(k, *[f"x{fac:g} {diff_bars(base(k), c22_whiten_timescale(FRAMES[k] * fac))}"
                 for fac in (10.0, 3.7, 0.1, 1.0000001)])
    head("D3. Smallest |lagged sum| / sum of squares at the deciding lag")
    for k in FRAMES:
        win, _ = windows(FRAMES[k])
        worst = math.inf
        for w in win:
            for y in (w, np.diff(w)):
                d = y - y.mean()
                ss = float(d @ d)
                for kk in range(1, len(d)):
                    p = float(np.dot(d[:-kk], d[kk:]))
                    worst = min(worst, abs(p) / ss)
                    if not p > 0:
                        break
        row(k, f"{worst:.2e}")
    head("D4. Order matters (walk, stride 3)")
    win, bars = windows(FRAMES["walk"])
    rng = np.random.default_rng(5)
    mine = base("walk").to_numpy()[bars][::3]
    perm = [ref_value(rng.permutation(w)) for w in win[::3]]
    row(f"permuted windows moved {diff_bars(mine, perm)[0]} of {len(mine)}")


# ===================================================================== E
def section_e():
    head("E3. In-fork overlap (6 synthetic frames): Spearman per frame")
    comps = {
        "FIRSTZEROAC_100": lambda f: ta.firstzero_ac(f),
        "TS_AC1_60": lambda f: ta.ts_ac1_60(f),
        "DIFF2ACF1_100": lambda f: ta.diff2_acf1(f),
        "TF_AC1E_60": lambda f: ta.tf_autocorr_1e_60(f),
        "C22AMI_100": lambda f: ta.c22_ami_timescale(f),
        "C22PERIODICITY_100": lambda f: ta.c22_periodicity(f),
        "HLIFE_100": lambda f: ta.halflife(f),
    }
    for name, fn in comps.items():
        rhos = []
        for k in FRAMES:
            s = fn(FRAMES[k])
            s = s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
            rhos.append(spearman(base(k), s))
        a = [abs(x) for x in rhos if not math.isnan(x)]
        row(name, " ".join(f"{x:+.3f}" for x in rhos),
            f"median |rho| {np.median(a):.4f}" if a else "n/a")


# ===================================================================== G
def section_g():
    head("G. The floor, and what it buys")
    flat = FRAMES["walk"].copy()
    flat.iloc[400:] = flat.iloc[400]
    s = c22_whiten_timescale(flat)
    lst = np.where(s.notna().to_numpy())[0]
    row("flat from bar 400", f"last fired bar {int(lst.max())}",
        f"fired {int(s.notna().sum())}")
    for step in (0.01, 0.001, -0.005):
        f = ladder(step=step)
        win, _ = windows(f)
        live = sum(not math.isnan(ref_value(w)) for w in win[::7])
        row(f"ladder {step}", f"fired {int(c22_whiten_timescale(f).notna().sum())}",
            f"window sd max {max(np.std(w) for w in win):.2e}",
            f"unguarded reference reads a value on {live} of {len(win[::7])}")
    f = linear_returns()
    win, _ = windows(f)
    row("linear returns", f"fired {int(c22_whiten_timescale(f).notna().sum())}",
        f"window sd min {min(np.std(w) for w in win):.2e}",
        f"residual sd max {max(np.std(np.diff(w)) for w in win):.2e}")
    f = pd.Series(100.0 + 0.01 * np.arange(N, dtype=float))
    row("one kurus a bar", f"fired {int(c22_whiten_timescale(f).notna().sum())}",
        f"c22_periodicity fired {int(ta.c22_periodicity(f).notna().sum())}")
    for k in FRAMES:
        win, bars = windows(FRAMES[k])
        mine = base(k).to_numpy()[bars]
        unguarded = np.array([ref_value(w) for w in win[::23]])
        row(k, f"guarded vs unguarded moved {diff_bars(mine[::23], unguarded)}")


# ===================================================================== H
def section_h():
    head("H. Bad data")
    for bad in (np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310):
        f = FRAMES["walk"].copy()
        f.iloc[700] = bad
        s = c22_whiten_timescale(f)
        blank = np.where(s.isna().to_numpy())[0]
        after = blank[blank >= LENGTH]
        row(f"close = {bad}", f"blank {after.size}", f"{after.min()}..{after.max()}")
    for lo, hi in ((1e-300, 1e100), (1e-100, 1e100), (1e-50, 1e27)):
        f = FRAMES["walk"].copy()
        f.iloc[700] = lo
        f.iloc[701] = hi
        s = c22_whiten_timescale(f)
        blank = np.where(s.isna().to_numpy())[0]
        after = blank[blank >= LENGTH]
        row(f"pair {lo:g}, {hi:g}", f"blank {after.size}",
            f"{after.min() if after.size else '-'}..{after.max() if after.size else '-'}")
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-100
    f.iloc[701] = 1e100
    a = c22_whiten_timescale(f).to_numpy()
    b = np.asarray(mutant("no-overflow-guard")(f), float)
    saved = np.where(np.isnan(a) & ~np.isnan(b))[0]
    row("without the overflow guard", f"{saved.size} bars read",
        sorted(set(b[saved].tolist())))
    row("overflow guard inert on the six frames",
        all(same(base(k), mutant("no-overflow-guard")(FRAMES[k])) for k in FRAMES))
    for n in (99, 100, 101, 102):
        s = c22_whiten_timescale(FRAMES["walk"].iloc[:n])
        row(f"n = {n}", None if s is None else int(s.notna().sum()))


# ===================================================================== T / Z
def section_t():
    head("T. Cost")
    rng = np.random.default_rng(3)
    big = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, 400_000))))
    tracemalloc.start()
    t0 = time.perf_counter()
    s = c22_whiten_timescale(big)
    dt = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    row(f"n = {len(big):,}", f"fired {int(s.notna().sum()):,}",
        f"{dt:.1f}s", f"traced peak {peak / 1e6:.1f} MB")


def section_z():
    head("Z. The chunk boundary is invisible")
    want = base("walk")
    for budget in (100, 400, 1024, CHUNK_VALUES):
        MODULE.CHUNK_VALUES = budget
        try:
            got = c22_whiten_timescale(FRAMES["walk"])
        finally:
            MODULE.CHUNK_VALUES = CHUNK_VALUES
        row(f"CHUNK_VALUES = {budget}", f"bit-equal {same(want, got)}")


# ===================================================================== X
def section_x():
    head("X. The module against the exact oracle on EVERY cosine window")
    win, bars = windows(FRAMES["cosine"])
    mine = base("cosine").to_numpy()[bars]
    bad = [i for i in range(win.shape[0]) if mine[i] != exact_value(win[i])]
    row(f"{len(bad)} disagreements of {win.shape[0]} windows", bad[:5])


SECTIONS = {
    "S": section_s, "A": section_a, "B": section_b, "C": section_c,
    "D": section_d, "E": section_e, "G": section_g, "H": section_h,
    "T": section_t, "X": section_x, "Z": section_z,
}
DEFAULT = list(SECTIONS)


def main(argv):
    want = [a.upper() for a in argv] or DEFAULT
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
    for key in want:
        SECTIONS[key]()


if __name__ == "__main__":
    main(sys.argv[1:])
