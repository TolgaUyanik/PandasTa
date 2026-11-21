# -*- coding: utf-8 -*-
"""C22-ENTROPY-PAIRS (PandasTa issue #133): every number in
`docs/C22EntropyPairsMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_entropy_pairs.py` and
`tests/test_c22_entropy_pairs.py`.

    python docs/measure_c22_entropy_pairs.py              # S, A-D, G, H
    python docs/measure_c22_entropy_pairs.py A D          # just those
    python docs/measure_c22_entropy_pairs.py P            # the GPL-3.0 black box

Section **P** is OPT-IN and is the only part of this repository that runs the
reference implementation (pycatch22, **GPL-3.0**). It is MEASUREMENT only --
the same use the owner's own screen prototype makes of it
(`docs/issues/screen/ind_screen_r3.py`) -- and no shipped module imports it. A
bare run skips P and does not import it; `importlib.util.find_spec` is used to
report whether it is installed at all, which does not execute the package.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import importlib.util
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402,F401
from pandas_ta.statistics.c22_entropy_pairs import (  # noqa: E402
    MAX_ENTROPY, MIN_LENGTH, NOISE_FLOOR, NUM_LETTERS, NUM_WORD_TYPES,
    WORD_LENGTH, ZSCORE_DDOF, _entropy_pairs_rows, c22_entropy_pairs)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_entropy_pairs")
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
_BASE: dict[str, pd.Series] = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_entropy_pairs(FRAMES[name])
    return _BASE[name]


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def diff_bars(a, b, tol=0.0):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(np.abs(x[both] - y[both]) > tol)),
            int(np.sum(np.isnan(x) != np.isnan(y))))


def worst_gap(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return float(np.max(np.abs(x[both] - y[both]))) if both.any() else 0.0


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def row(*cells):
    print(" | ".join(str(c) for c in cells))


# ------------------------------------------------- independent spellings
def shipped_letters(window, ddof=ZSCORE_DDOF):
    w = np.asarray(window, float)
    sd = float(w.std(ddof=ddof))
    z = (w - w.mean()) / sd
    q1, q2 = np.quantile(z, [1.0 / 3.0, 2.0 / 3.0])
    letter = (z > q1).astype(np.int64) + (z > q2).astype(np.int64)
    return letter, (q1, q2)


def entropy_of(letter):
    code = letter[:-1] * NUM_LETTERS + letter[1:]
    counts = np.bincount(code, minlength=NUM_WORD_TYPES)
    p = counts / float(letter.size - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(-np.sum(np.where(p > 0, p * np.log(p), 0.0)))


def exact_letters(window, ddof=ZSCORE_DDOF):
    y = [Fraction(float(v)) for v in window]
    n = len(y)
    mean = sum(y) / n
    u = [v - mean for v in y]
    if sum(v * v for v in u) == 0:
        return None

    def quantile(p):
        s = sorted(u)
        pos = Fraction(p) * (n - 1)
        k = int(pos)
        frac = pos - k
        if k + 1 >= n:
            return s[-1]
        return s[k] + frac * (s[k + 1] - s[k])

    q1, q2 = quantile(Fraction(1, 3)), quantile(Fraction(2, 3))
    return np.array([(1 if v > q1 else 0) + (1 if v > q2 else 0)
                     for v in u], dtype=np.int64)


def value_exact(window):
    letter = exact_letters(window)
    if letter is None:
        return float("nan")
    return entropy_of(letter)


def value_def(window, ddof=ZSCORE_DDOF, zscore=True, reverse=False):
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > 0.0):
        return float("nan")
    z = [(v - mean) / sd for v in w] if zscore else list(w)

    def quantile(p):
        s = sorted(z)
        pos = p * (n - 1)
        k = int(math.floor(pos))
        frac = pos - k
        if k + 1 >= n:
            return s[-1]
        return s[k] + frac * (s[k + 1] - s[k])

    q1, q2 = quantile(1.0 / 3.0), quantile(2.0 / 3.0)
    letter = [(1 if v > q1 else 0) + (1 if v > q2 else 0) for v in z]
    pairs = list(zip(letter[1:], letter[:-1])) if reverse \
        else list(zip(letter[:-1], letter[1:]))
    counts: dict = {}
    for pr in pairs:
        counts[pr] = counts.get(pr, 0) + 1
    p_n = n - 1
    out = 0.0
    for cnt in counts.values():
        p = cnt / p_n
        out -= p * math.log(p)
    return out


# ------------------------------------------------------------------ S
def section_s():
    head("S. Setup")
    print(f"numpy {np.__version__}, pandas {pd.__version__}, "
          f"python {sys.version.split()[0]}")
    print(f"MIN_LENGTH={MIN_LENGTH} NUM_LETTERS={NUM_LETTERS} "
          f"WORD_LENGTH={WORD_LENGTH} NUM_WORD_TYPES={NUM_WORD_TYPES} "
          f"MAX_ENTROPY={MAX_ENTROPY!r} NOISE_FLOOR={NOISE_FLOOR!r} "
          f"ZSCORE_DDOF={ZSCORE_DDOF}")


# ------------------------------------------------------------------ A
def section_a():
    head("A1. Exact rational oracle -- letters, zero rounding")
    for frame in FRAMES:
        win, bars = windows(FRAMES[frame])
        ok = 0
        worst = 0.0
        ran = 0
        for i in range(0, win.shape[0], 97):
            letter, _ = shipped_letters(win[i])
            exact = exact_letters(win[i])
            if exact is not None and np.array_equal(letter, exact):
                ok += 1
            mine = float(base(frame).iloc[int(bars[i])])
            worst = max(worst, abs(mine - value_exact(win[i])))
            ran += 1
        row(frame, ran, ok, f"{worst:.2e}")

    head("A2. Plain-Python re-spelling (math.fsum)")
    for frame in FRAMES:
        win, bars = windows(FRAMES[frame])
        worst = 0.0
        ran = 0
        for i in range(0, win.shape[0], 7):
            mine = float(base(frame).iloc[int(bars[i])])
            worst = max(worst, abs(mine - value_def(win[i])))
            ran += 1
        row(frame, ran, f"{worst:.2e}")

    head("A3. Z-score and its divisor are inert")
    for frame in FRAMES:
        win, bars = windows(FRAMES[frame])
        idx = list(range(0, win.shape[0], 3))
        mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
        for label, other in (
                ("ddof0", [value_def(win[i], ddof=0) for i in idx]),
                ("no-zscore", [value_def(win[i], zscore=False) for i in idx]),
                ("shift+1", [value_def(win[i] + 1.0) for i in idx])):
            moved, mask = diff_bars(mine, other, tol=1e-9)
            row(frame, label, len(idx), moved, mask)

    head("A4. Word order reversed (transpose, permutation-invariant)")
    for frame in FRAMES:
        win, bars = windows(FRAMES[frame])
        idx = list(range(0, win.shape[0], 3))
        mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
        other = [value_def(win[i], reverse=True) for i in idx]
        moved, mask = diff_bars(mine, other, tol=1e-9)
        row(frame, len(idx), moved, mask, f"{worst_gap(mine, other):.2e}")


# ------------------------------------------------------------------ B
def section_b():
    head("B. Distinct values / tie density (Gate B sweep power)")
    for frame in FRAMES:
        a = base(frame).dropna().to_numpy()
        tie = float(np.mean(a[1:] == a[:-1])) if a.size > 1 else float("nan")
        row(frame, a.size, len(set(a.tolist())), f"{tie:.4f}",
            f"{float(a.min()):.6f}", f"{float(a.max()):.6f}")


# ------------------------------------------------------------------ C
def section_c():
    head("C1. Reachability on synthetic frames")
    for frame in FRAMES:
        s = base(frame)
        a = s.dropna().to_numpy()
        row(frame, int(s.notna().sum()), len(set(a.tolist())),
            f"{float(a.min()):.6f}", f"{float(np.median(a)):.6f}",
            f"{float(a.max()):.6f}")

    head("C2. The issue's own worry -- tick rounding")
    f = FRAMES["penny"]
    r = returns(f)
    row("zero-return share", f"{float(np.mean(r == 0.0)):.4f}")
    win, _ = windows(f)
    letter, _ = shipped_letters(win[0])
    row("first-window letter counts", np.bincount(letter, minlength=3).tolist())

    head("C3. What the floor costs")
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_entropy_pairs(pd.Series(c[:700]))
    row("flat-from-400 fired", int(s.notna().sum()))

    for step in (0.01, 0.001, -0.005):
        ladd = ladder(step=step)
        win, _ = windows(ladd)
        sd = win.std(axis=1, ddof=ZSCORE_DDOF)
        row("ladder", step, "max window sd", f"{float(sd.max()):.3e}",
            "fired", int(c22_entropy_pairs(ladd).notna().sum()))


# ------------------------------------------------------------------ D
def section_d():
    head("D1. Bit-identical under a power-of-two price rescale")
    for frame in FRAMES:
        for factor in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            a = c22_entropy_pairs(FRAMES[frame])
            b = c22_entropy_pairs(FRAMES[frame] * factor)
            x, y = a.to_numpy(), b.to_numpy()
            eq = bool(np.array_equal(x, y, equal_nan=True))
            row(frame, factor, "bit-equal" if eq else "DIFFERS")

    head("D2. Inexact RETURN rescale (not bit-identical by construction)")
    base_f = FRAMES["walk"]
    r = returns(base_f)
    for factor in (10.0, 3.7, 0.1, 1.0000001):
        scaled = np.empty(len(base_f))
        scaled[0] = 100.0
        scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
        a = base("walk").to_numpy()
        b = c22_entropy_pairs(pd.Series(scaled)).to_numpy()
        moved, mask = diff_bars(a, b, tol=1e-9)
        row("walk", factor, "moved", moved, "mask", mask,
            f"{worst_gap(a, b):.2e}")

    head("D3. fires strictly between 0 and n")
    s = base("walk")
    row("walk", int(s.notna().sum()), len(s))


# ------------------------------------------------------------------ G
def section_g():
    head("G. The floor, unguarded (no-floor mutant)")
    src = Path(MODULE.__file__).read_text(encoding="utf-8")
    old = "bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)"
    new = "bad |= ~(sd > 0.0)"
    assert src.count(old) == 1
    ns: dict = {}
    exec(compile(src.replace(old, new), "<nofloor>", "exec"), ns)
    unguarded_fn = ns["c22_entropy_pairs"]
    for step in (0.01, 0.001, -0.005):
        ladd = ladder(step=step)
        unguarded = np.asarray(unguarded_fn(ladd), float)
        live = unguarded[~np.isnan(unguarded)]
        row("ladder", step, "unguarded fired", live.size,
            "min/median/max",
            f"{float(live.min()):.4f}/{float(np.median(live)):.4f}/"
            f"{float(live.max()):.4f}" if live.size else "n/a")


# ------------------------------------------------------------------ P
def section_p():
    head("P. The GPL-3.0 reference -- OPT-IN, measurement only")
    if importlib.util.find_spec("pycatch22") is None:
        print("pycatch22 is not installed in this environment; skipping.")
        return
    import pycatch22  # noqa: WPS433  (opt-in, measurement only)
    probe = pycatch22.catch22_all([0.0] * LENGTH, short_names=True)
    idx = probe["short_names"].index("entropy_pairs")

    def value_with_quantile_method(window, method):
        w = np.asarray(window, float)
        sd = float(w.std(ddof=ZSCORE_DDOF))
        z = (w - w.mean()) / sd
        q1, q2 = np.quantile(z, [1.0 / 3.0, 2.0 / 3.0], method=method)
        letter = (z > q1).astype(np.int64) + (z > q2).astype(np.int64)
        return entropy_of(letter)

    methods = ["linear", "lower", "higher", "nearest", "midpoint",
               "median_unbiased", "normal_unbiased", "hazen", "weibull"]
    worst = {m: 0.0 for m in methods}
    gaps = {m: [] for m in methods}
    agree = {m: 0 for m in methods}
    ran = 0
    rows_by_frame = {}
    for frame in FRAMES:
        win, bars = windows(FRAMES[frame])
        mine_f, ref_f = [], []
        for i in range(0, win.shape[0], 97):
            w = win[i].tolist()
            ref = float(pycatch22.catch22_all(w)["values"][idx])
            mine_f.append(float(base(frame).iloc[int(bars[i])]))
            ref_f.append(ref)
            for m in methods:
                other = value_with_quantile_method(win[i], m)
                gap = abs(other - ref)
                worst[m] = max(worst[m], gap)
                gaps[m].append(gap)
                if gap < 1e-9:
                    agree[m] += 1
            ran += 1
        mf, rf = pd.Series(mine_f), pd.Series(ref_f)
        sp = float(np.corrcoef(mf.rank(), rf.rank())[0, 1]) \
            if mf.std() > 0 and rf.std() > 0 else float("nan")
        rows_by_frame[frame] = sp
        row(frame, "spearman(mine, pycatch22)", f"{sp:.4f}")
    row("windows compared", ran)
    head("P1. Candidate quantile interpolation methods fit to the black box")
    for m in methods:
        row(m, "agree<1e-9", agree[m], "of", ran, "mean gap",
            f"{float(np.mean(gaps[m])):.4f}", "median gap",
            f"{float(np.median(gaps[m])):.4f}", "max gap", f"{worst[m]:.4f}")

    head("P2. Candidate structural readings fit to the black box")

    def value_nonoverlap(window):
        letter, _ = shipped_letters(window)
        n = letter.size
        pairs = [(letter[2 * k], letter[2 * k + 1]) for k in range(n // 2)]
        counts: dict = {}
        for pr in pairs:
            counts[pr] = counts.get(pr, 0) + 1
        p_n = len(pairs)
        out = 0.0
        for cnt in counts.values():
            p = cnt / p_n
            out -= p * math.log(p)
        return out

    def value_log2(window):
        letter, _ = shipped_letters(window)
        return entropy_of(letter) / math.log(2.0)

    def value_normalized(window):
        letter, _ = shipped_letters(window)
        v = entropy_of(letter)
        n_types = len(set(zip(letter[:-1].tolist(), letter[1:].tolist())))
        return v / math.log(n_types) if n_types > 1 else 0.0

    def entropy_with_divisor(letter, divisor):
        code = letter[:-1] * NUM_LETTERS + letter[1:]
        counts = np.bincount(code, minlength=NUM_WORD_TYPES)
        p = counts / float(divisor)
        with np.errstate(divide="ignore", invalid="ignore"):
            return float(-np.sum(np.where(p > 0, p * np.log(p), 0.0)))

    def value_divide_by_length(window):
        letter, _ = shipped_letters(window)
        return entropy_with_divisor(letter, letter.size)

    def value_divide_by_length_minus_2(window):
        letter, _ = shipped_letters(window)
        return entropy_with_divisor(letter, letter.size - 2)

    candidates = {
        "shipped (overlap, ln, raw)": lambda w: float(base("walk").iloc[0])
            if False else entropy_of(shipped_letters(w)[0]),
        "non-overlapping pairs": value_nonoverlap,
        "log2 instead of ln": value_log2,
        "normalized by log(#observed types)": value_normalized,
        "divide by length (100) not length-1": value_divide_by_length,
        "divide by length-2 (98) not length-1": value_divide_by_length_minus_2,
    }
    worst2 = {k: 0.0 for k in candidates}
    med2 = {k: [] for k in candidates}
    ran2 = 0
    for frame in FRAMES:
        win, bars = windows(FRAMES[frame])
        for i in range(0, win.shape[0], 97):
            w = win[i].tolist()
            ref = float(pycatch22.catch22_all(w)["values"][idx])
            for name, fn in candidates.items():
                gap = abs(fn(win[i]) - ref)
                worst2[name] = max(worst2[name], gap)
                med2[name].append(gap)
            ran2 += 1
    for name in candidates:
        row(name, "median gap", f"{float(np.median(med2[name])):.4f}",
            "max gap", f"{worst2[name]:.4f}")


SECTIONS = {"S": section_s, "A": section_a, "B": section_b, "C": section_c,
            "D": section_d, "G": section_g, "P": section_p}

if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]]
    if not want:
        want = [k for k in SECTIONS if k != "P"]
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
        SECTIONS[key]()
