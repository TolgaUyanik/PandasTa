# -*- coding: utf-8 -*-
"""Reproduce every number in docs/FirstzeroAcMeasured.md (issue #152).

Run from the repository root with an interpreter that has statsmodels
(the Gate A oracle) and scipy:

    python docs/measure_firstzero_ac.py [section ...]

Sections: gate_a, guard, semantics, sentinel, causality, scale, family,
cost. With no argument every section runs. Synthetic data only; the
medians depend on numpy's RNG stream (NEP 19 does not freeze it).
"""
import os
import sys
import time
import types
import warnings

import numpy as np
import pandas as pd
from pandas import Series

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

import pandas_ta as ta  # noqa: E402
MOD = __import__("importlib").import_module("pandas_ta.statistics.firstzero_ac")

fz = MOD.firstzero_ac
EPS = np.finfo(float).eps


def ar1_returns(n, seed, phi, sd=0.02):
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n) * sd * np.sqrt(1 - phi * phi)
    r = np.empty(n)
    p = 0.0
    for t in range(n):
        p = phi * p + e[t]
        r[t] = p
    return r


def ar1(n, seed, phi=0.0):
    return Series(100 * np.cumprod(1 + ar1_returns(n, seed, phi)))


def garch(n, seed, a=0.2, b=0.75):
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n)
    r = np.empty(n)
    h = 4e-4
    for t in range(n):
        r[t] = np.sqrt(h) * z[t]
        h = 4e-4 * (1 - a - b) + a * r[t] ** 2 + b * h
    return Series(100 * np.cumprod(1 + r))


def kats_firstzero(x, acf):
    """Kats tsfeatures.py (a6b7e88) L1316 and L1331-1338, debug print left out."""
    AC = acf(x, fft=True, nlags=len(x))[1:]
    j = 0
    while j < len(AC) - 1:
        if AC[j] > 0 and AC[j + 1] < 0:
            break
        else:
            j += 1
    return j + 2


def gate_frames(n=600):
    rng = np.random.default_rng(7)
    out = {f"AR(1) phi={p:+.1f}": ar1(n, 70 + i, p).to_numpy() for i, p in enumerate((-0.3, 0.0, 0.3, 0.8))}
    out["GARCH(0.20, 0.75)"] = garch(n, 75).to_numpy()
    out["tick-rounded to 0.1, sd 0.4%"] = np.round(100 * np.cumprod(1 + rng.standard_normal(n) * 0.004), 1)
    k = np.arange(n)
    out["sine returns, period 22"] = 100 * np.cumprod(1 + 0.01 * np.sin(2 * np.pi * k / 22))
    out["150 flat bars, then iid 1%"] = np.r_[np.full(150, 50.0), 50 * np.cumprod(1 + rng.standard_normal(n - 150) * 0.01)]
    return out


def gate_a():
    from statsmodels.tsa.stattools import acf
    from statsmodels.compat.scipy import _next_regular
    print("## gate_a")
    same = all(MOD._next_regular(t) == _next_regular(t) for t in range(1, 5000))
    print(f"_next_regular equal to statsmodels' for 1..4999: {same}")
    lengths = (5, 10, 63, 100, 252)
    print("| frame | " + " | ".join(f"L={L}" for L in lengths) + " |")
    tot = equal = guard = guard_real = 0
    for name, c in gate_frames().items():
        cells = []
        r = c[1:] / c[:-1] - 1
        for L in lengths:
            out = fz(Series(c), length=L).to_numpy()
            n_eq = n_g = n = 0
            for t in range(L, c.size):
                x = r[t - L:t]
                with np.errstate(invalid="ignore", divide="ignore"):
                    ref = kats_firstzero(x, acf)
                n += 1
                if np.isnan(out[t]):
                    n_g += 1
                    guard_real += x.std() > 1e-12
                elif out[t] == ref:
                    n_eq += 1
            tot += n
            equal += n_eq
            guard += n_g
            cells.append(f"{n_eq}/{n - n_g} ({n_g} NaN)")
        print(f"| {name} | " + " | ".join(cells) + " |")
    print(f"windows {tot}: equal to Kats {equal}, NaN by the guard {guard} "
          f"(of which with return sd > 1e-12: {guard_real}), different {tot - equal - guard}")
    # the autocorrelations themselves
    worst = 0.0
    for c in gate_frames().values():
        r = c[1:] / c[:-1] - 1
        for L in lengths:
            for t in range(L, c.size, 7):
                x = r[t - L:t]
                if x.std() < 1e-12:
                    continue
                xo = x - x.mean()
                f = np.fft.fft(xo[None, :], n=_next_regular(2 * L + 1), axis=1)
                a = (np.fft.ifft(f * np.conj(f), axis=1)[:, :L].real / L)[0]
                worst = max(worst, np.abs(a[1:] / a[0] - acf(x, fft=True, nlags=L)[1:]).max())
    print(f"max |AC(module FFT) - AC(statsmodels)| over every 7th window: {worst:.3g}")


def units(c, L=100):
    r = c[1:] / c[:-1] - 1
    return np.array([r[t - L:t].std() / (EPS * np.abs(1 + r[t - L:t]).max()) for t in range(L, c.size)])


def unguarded(c, L=100):
    old = MOD.NOISE_ULPS
    MOD.NOISE_ULPS = -1.0  # sd > -floor is always true: the guard is off
    try:
        return fz(Series(c), length=L)
    finally:
        MOD.NOISE_ULPS = old


def guard():
    print("## guard")
    t = np.arange(300.0)
    rng = np.random.default_rng(0)
    jit = np.full(300, 10.0)
    jit[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    noise = {**{f"100 * (1 + {g:g})^t": 100 * (1 + g) ** t for g in (1e-2, 1e-4, 1e-7, 1e-8, 1e-10)},
             "exp(linspace(0, 30, 300)), 10% a bar": np.exp(np.linspace(0, 30, 300)),
             "1.1^t": 1.1 ** t,
             "flat 10.0, one-ulp jitter": jit}
    print("| series (300 bars) | shipped fires | unguarded fires | unguarded values | max units |")
    print("|---|---|---|---|---|")
    for k, c in noise.items():
        ug = unguarded(c).dropna()
        vals = np.unique(ug).astype(int).tolist()
        shown = vals if len(vals) <= 6 else vals[:3] + ["..."] + vals[-2:]
        print(f"| {k} | {fz(Series(c)).notna().sum()} | {ug.size} | {shown} | {units(c).max():.2f} |")
    rng = np.random.default_rng(0)
    rng.standard_normal(300)  # the stream position test_the_guard_keeps_very_small_real_returns uses
    real = {"iid returns, sd 1e-13": 100 * np.cumprod(1 + 1e-13 * rng.standard_normal(300))}
    rng = np.random.default_rng(1)
    real["iid returns, sd 1e-12"] = 100 * np.cumprod(1 + 1e-12 * rng.standard_normal(300))
    for k, c in real.items():
        print(f"| {k} | {fz(Series(c)).notna().sum()} of 200 | | | min {units(c).min():.0f} |")


def semantics():
    print("## semantics (40 paths x 1100 bars per row, every 25th bar from 100)")
    print("| returns | median | p10 .. p90 | mean | share 2 | share = length |")
    print("|---|---|---|---|---|---|")
    rows = [(f"AR(1) phi = {p:+.1f}", lambda s, p=p: ar1(1100, s, p)) for p in (-0.3, -0.1, 0.0, 0.1, 0.3, 0.6, 0.9)]
    rows.append(("GARCH(0.20, 0.75)", lambda s: garch(1100, s)))
    rows.append(("Student-t(3) iid", lambda s: Series(100 * np.cumprod(
        1 + 0.02 / np.sqrt(3) * np.random.default_rng(s).standard_t(3, 1100)))))
    for name, make in rows:
        v = np.concatenate([fz(make(s)).to_numpy()[100::25] for s in range(40)])
        q = np.percentile(v, [10, 50, 90])
        print(f"| {name} | {q[1]:.0f} | {q[0]:.0f} .. {q[2]:.0f} | {v.mean():.2f} | {np.mean(v == 2):.3f} | {np.mean(v == 100):.4f} |")
    print("sine returns 0.01 sin(2 pi k / P), 800 bars:")
    k = np.arange(800)
    for per in (10, 22, 40, 70):
        v = fz(Series(100 * np.cumprod(1 + 0.01 * np.sin(2 * np.pi * k / per)))).to_numpy()[100:]
        print(f"  P = {per}: values {np.unique(v).astype(int).tolist()}")
    rng = np.random.default_rng(3)
    k = np.arange(5000)
    v = fz(Series(100 * np.cumprod(1 + 0.01 * np.sin(2 * np.pi * k / 40) + 0.01 * rng.standard_normal(5000)))).to_numpy()[100:]
    print(f"  P = 40 plus iid noise of the same sd: median {np.median(v):.0f}, p10 .. p90 "
          f"{np.percentile(v, 10):.0f} .. {np.percentile(v, 90):.0f}")
    # against the window's own lag-1 return autocorrelation, phi -0.3 / 0 / +0.3
    from scipy.stats import spearmanr
    xs, ys = [], []
    for s in range(30):
        close = ar1(1100, 100 + s, (-0.3, 0.0, 0.3)[s % 3]).to_numpy()
        v = fz(Series(close)).to_numpy()
        r = close[1:] / close[:-1] - 1
        ac1 = np.full(close.size, np.nan)
        for t in range(100, close.size, 10):
            w = r[t - 100:t] - r[t - 100:t].mean()
            ac1[t] = np.dot(w[1:], w[:-1]) / np.dot(w, w)
        m = ~np.isnan(ac1) & ~np.isnan(v)
        xs.append(ac1[m])
        ys.append(v[m])
    print(f"Spearman vs the window's lag-1 return autocorrelation (30 paths, phi -0.3 / 0 / +0.3, "
          f"every 10th bar): {spearmanr(np.concatenate(xs), np.concatenate(ys))[0]:.3f}")
    # the 8 paths the tests pool (seeds 500..507, 600 bars, every bar)
    for phi in (-0.3, 0.0, 0.6, 0.9):
        v = np.concatenate([fz(ar1(600, 500 + i, phi)).dropna().to_numpy() for i in range(8)])
        print(f"test paths, phi = {phi:+.1f}: median {np.median(v):.0f}")
    # persistence of the column itself
    v = fz(ar1(5000, 99, 0.0)).to_numpy()[100:]
    print(f"iid, 4900 bars: the value changes on {np.mean(v[1:] != v[:-1]):.3f} of bars; "
          f"{np.unique(v).size} distinct values")


def sentinel():
    print("## sentinel (no crossing: the value is `length`)")
    c = np.r_[np.full(150, 100.0), np.full(150, 101.0)]
    o = fz(Series(c)).to_numpy()
    print(f"flat, one step at bar 150: bars 150..249 read {np.unique(o[150:250]).astype(int).tolist()}")
    # why: the sign pattern of a single move at each position p of n returns
    for n in (5, 20, 100, 252):
        ok = True
        for p in range(n):
            x = np.zeros(n)
            x[p] = 0.01
            x = x - x.mean()
            ac = np.array([np.dot(x[k:], x[:-k]) for k in range(1, n)]) / np.dot(x, x)
            k = np.arange(1, n)
            neg = k <= max(p, n - 1 - p)
            ok &= bool((ac[neg] < 0).all() and (ac[~neg] > 0).all())
            hit = (ac[:-1] > 0) & (ac[1:] < 0)
            ok &= not hit.any()
        print(f"one move at every position of {n} returns: negative exactly for k <= max(p, n - 1 - p), "
              f"positive beyond, no positive-to-negative pair: {ok}")
    rng = np.random.default_rng(5)
    for p_move in (0.5, 0.2, 0.05, 0.02):
        cnt = n = 0
        for s in range(20):
            moves = rng.random(1100) < p_move
            r = np.where(moves, rng.choice([-0.01, 0.01], 1100), 0.0)
            v = fz(Series(100 * np.cumprod(1 + r))).dropna().to_numpy()
            cnt += (v == 100).sum()
            n += v.size
        print(f"returns of +-1% on {p_move:.0%} of bars, 0 otherwise (20 paths): "
              f"share reading 100 = {cnt / n:.4f} of {n} fired bars")


def causality():
    print("## causality")
    src = open(MOD.__file__, encoding="utf-8").read()
    mut = types.ModuleType("mut")
    mut.__file__ = MOD.__file__
    exec(compile(src.replace("lo = length + start", "lo = length - 1 + start"), MOD.__file__, "exec"), mut.__dict__)
    offsets = range(130, 600, 30)

    def leaks(fn, how):
        c0, other = ar1(600, 11), ar1(600, 99)
        b = fn(c0)
        hits = 0
        for j in offsets:
            p = c0.copy()
            if how == "path":
                p.iloc[j:] = other.iloc[j:].to_numpy() * (c0.iloc[j - 1] / other.iloc[j - 1])
            else:
                p.iloc[j:] *= 1e3
            o = fn(p)
            a, bb = b.iloc[:j], o.iloc[:j]
            hits += bool(not (a.isna() == bb.isna()).all() or (a[a.notna()] != bb[a.notna()]).any())
        return hits

    for how, label in (("path", "another path from the offset on"), ("jump", "x1000 from the offset on")):
        print(f"{label}: real module leaks {leaks(fz, how)}/16, mutant caught {leaks(mut.firstzero_ac, how)}/16")
    close = ar1(600, 4)
    base = fz(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = fz(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    print(f"close x1000 at bar 300: bars moved {moved.min()}..{moved.max()} ({moved.size})")


def scale():
    print("## scale")
    for seed in (4, 5, 6):
        close = ar1(600, seed)
        base = fz(close)
        cells = []
        for k in (8.0, 64.0, 10.0, 3.7):
            s = fz(close * k)
            cells.append(f"x{k:g}: masks equal {bool((base.isna() == s.isna()).all())}, "
                         f"bars differing {int(((base != s) & base.notna()).sum())}")
        print(f"seed {seed}: " + "; ".join(cells))
    out = fz(ar1(600, 4)).dropna()
    print(f"seed 4: fires {out.size} of 600, distinct {out.nunique()}, range {out.min():.0f}..{out.max():.0f}")


def ohlcv(n, seed, phi):
    rng = np.random.default_rng(seed + 1000)
    close = ar1(n, seed, phi).to_numpy()
    spread = np.abs(rng.standard_normal(n)) * 0.01
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    vol = rng.integers(1_000, 100_000, n).astype(float)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol})


def family():
    """Spearman of FIRSTZEROAC_100 against every numeric column of
    every `Category` indicator at its defaults, pooled over 8 synthetic
    paths (phi 0, 0.3, 0.6, 0.9, two seeds each)."""
    from scipy.stats import spearmanr
    print("## family (synthetic, 8 paths x 1100 bars, pooled)")
    frames = [ohlcv(1100, 300 + i, (0.0, 0.3, 0.6, 0.9)[i % 4]) for i in range(8)]
    target = np.concatenate([fz(df["close"]).to_numpy() for df in frames])
    cols = {}
    failed = []
    for cat, names in ta.Category.items():
        for name in names:
            if name == "firstzero_ac":
                continue
            parts = []
            try:
                for df in frames:
                    res = getattr(df.ta, name)()
                    if isinstance(res, pd.Series):
                        res = res.to_frame()
                    parts.append(res.apply(pd.to_numeric, errors="coerce"))
            except Exception:
                failed.append(name)
                continue
            for col in parts[0].columns:
                try:
                    v = np.concatenate([p[col].to_numpy(dtype=float) for p in parts])
                except Exception:
                    continue
                if v.size == target.size:
                    cols[f"{name}:{col}"] = v
    rows = []
    for k, v in cols.items():
        m = np.isfinite(v) & np.isfinite(target)
        if m.sum() < 1000 or np.unique(v[m]).size < 3:
            continue
        rows.append((abs(spearmanr(v[m], target[m])[0]), k, int(m.sum())))
    rows.sort(reverse=True)
    print(f"columns compared: {len(rows)}; indicators that raised at defaults: {len(failed)} {sorted(failed)}")
    # Pooling paths of different phi adds a between-path term (a high-phi
    # path trends and reads late lags), so each top column is also shown on
    # the two iid paths alone and as the median of the 8 per-path values.
    n1 = 1100
    iid = np.zeros(target.size, bool)
    for i in (0, 4):
        iid[i * n1:(i + 1) * n1] = True
    print("| column | pooled, 8 paths | 2 iid paths | per-path median |")
    print("|---|---|---|---|")
    for rho, k, n in rows[:10]:
        v = cols[k]
        m = np.isfinite(v) & np.isfinite(target)
        r_iid = spearmanr(v[m & iid], target[m & iid])[0]
        per = []
        for i in range(8):
            s = slice(i * n1, (i + 1) * n1)
            mi = m[s]
            if mi.sum() > 100 and np.unique(v[s][mi]).size > 2:
                per.append(spearmanr(v[s][mi], target[s][mi])[0])
        print(f"| `{k}` | {rho:.3f} (n = {n}) | {abs(r_iid):.3f} | {abs(np.median(per)):.3f} |")


def cost():
    import tracemalloc
    print("## cost (tracemalloc off for timings)")
    for n in (2_000, 20_000, 200_000):
        close = ar1(n, 1)
        for L in (100, 252):
            ts = []
            for _ in range(3):
                t0 = time.perf_counter()
                fz(close, length=L)
                ts.append(time.perf_counter() - t0)
            tracemalloc.start()
            fz(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"n = {n}, length = {L}: {min(ts) * 1e3:.0f} .. {max(ts) * 1e3:.0f} ms, peak {peak / 2**20:.1f} MiB")


SECTIONS = {f.__name__: f for f in (gate_a, guard, semantics, sentinel, causality, scale, family, cost)}

if __name__ == "__main__":
    for name in sys.argv[1:] or SECTIONS:
        SECTIONS[name]()
