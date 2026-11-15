# -*- coding: utf-8 -*-
"""Print the step-1 equivalence and NaN-rate numbers in docs/GapmMeasured.md.

    python docs/measure_gapm_equivalence.py

Rebuilds the screen whose original scripts (`equiv.py` / `equiv_overnight.py`)
lived only in a session scratchpad. Synthetic frames with fixed seeds -- not
Gate E, which needs the parent repo's production column set.

Step 1: GAPM_40_20 against every `Category` column that is scale-free at
defaults on all six frames (equal under price x8 within 1e-6 of the column's
max |value|, NaN masks matching, at least 2 distinct values), pooled Spearman rho over six 2,000-bar frames
(seeds 1-3, each raw and tick-rounded to 0.01), on two generators:
`make_df` (docs/gen_indicator_dictionary.py's, open = close x noise) and an
overnight/intraday walk (open = prior close x overnight move).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.momentum.gapm import gapm

N, SEEDS, TICK, SCALE = 2000, (1, 2, 3), 0.01, 8.0
SKIP = {"gapm", "beta"}  # gapm is the subject; beta needs a benchmark series


def make_df(seed, level=100.0):
    """docs/gen_indicator_dictionary.py's generator, seeded per frame."""
    rng = np.random.default_rng(seed)
    close = level * np.exp(np.cumsum(rng.normal(0, 0.012, N)))
    spread = close * np.abs(rng.normal(0, 0.006, N))
    openp = close * (1 + rng.normal(0, 0.004, N))
    high = np.maximum.reduce([close + spread, openp, close])
    low = np.minimum.reduce([close - spread, openp, close])
    return openp, high, low, close, rng.integers(1e5, 1e6, N).astype(float)


def overnight(seed, level=100.0):
    rng = np.random.default_rng(seed)
    on, intra = rng.normal(0, 0.004, N), rng.normal(0, 0.011, N)
    close = level * np.exp(np.cumsum(on + intra))
    openp = np.r_[level, close[:-1]] * np.exp(on)
    spread = close * np.abs(rng.normal(0, 0.006, N))
    high = np.maximum.reduce([close + spread, openp, close])
    low = np.minimum.reduce([close - spread, openp, close])
    return openp, high, low, close, rng.integers(1e5, 1e6, N).astype(float)


def frame(arrays, tick):
    o, h, l, c, v = (np.asarray(a, float).copy() for a in arrays)
    if tick:
        o, h, l, c = (np.round(a / tick) * tick for a in (o, h, l, c))
    idx = pd.date_range("2022-01-03", periods=N, freq="B")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)


def columns(df):
    out = {}
    for cat, names in ta.Category.items():
        for name in names:
            if name in SKIP:
                continue
            try:
                res = getattr(df.ta, name)()
            except Exception:
                continue
            if isinstance(res, pd.Series):
                res = res.to_frame()
            if not isinstance(res, pd.DataFrame):
                continue
            for col in res.columns:
                s = pd.to_numeric(res[col], errors="coerce").astype(float)
                if len(s) == len(df):
                    out[f"{name}:{col}"] = s.reset_index(drop=True)
    return out


def scale_free(a, b):
    if not (a.isna() == b.isna()).all() or a.nunique() < 2:
        return False
    m = a.notna()
    # relative to the column's scale: per-element rtol fails zero-crossing oscillators (TRIX) on float noise
    return bool((b[m] - a[m]).abs().max() <= 1e-6 * a[m].abs().max())


def screen(gen):
    pooled, keep = {}, None
    for seed in SEEDS:
        for tick in (None, TICK):
            arrays = gen(seed)
            df = frame(arrays, tick)
            big = df.copy()
            big[["open", "high", "low", "close"]] *= SCALE
            cols, cols8 = columns(df), columns(big)
            ok = {k for k in cols if k in cols8 and scale_free(cols[k], cols8[k])}
            keep = ok if keep is None else keep & ok
            g = gapm(df["open"], df["close"]).reset_index(drop=True)
            for k in ok:
                pooled.setdefault(k, []).append(pd.DataFrame({"g": g, "x": cols[k]}))
    rows = []
    for k in keep:
        both = pd.concat(pooled[k]).dropna()
        r = abs(both["g"].corr(both["x"], method="spearman")) if len(both) > 1 else np.nan
        if not np.isnan(r):  # NaN: constant over the pooled frames (squeeze:SQZ_NO)
            rows.append((r, k, len(both)))
    return len(keep), sorted(rows, reverse=True)


def nan_rate():
    """Windows with no down gap on a tick walk with open == prior close forced on p of bars."""
    def walk(seed, p):
        rng = np.random.default_rng(seed)
        on, intra = rng.normal(0, 0.004, N), rng.normal(0, 0.011, N)
        on[rng.random(N) < p] = 0.0
        c = np.round(np.exp(np.log(50.0) + np.cumsum(on + intra)) / TICK) * TICK
        o = np.round(np.r_[c[0], c[:-1]] * np.exp(on) / TICK) * TICK
        return pd.Series(o), pd.Series(c)

    def count(frames):
        hits = total = 0
        for o, c in frames:
            dn = (c.shift(1) - o).clip(lower=0)
            no_down = ((dn > 0).rolling(40).sum() == 0).iloc[40:]  # full windows only
            hits, total = hits + int(no_down.sum()), total + len(no_down)
        return f"{hits} / {total} ({100 * hits / total:.2f}%)"

    for tick in (None, TICK):
        dfs = [frame(make_df(seed), tick) for seed in range(5)]
        print(f"  make_df, tick {tick}: {count((d['open'], d['close']) for d in dfs)}")
    for p in (0.0, 0.3, 0.5, 0.7, 0.8, 0.9):
        print(f"  tick walk, p = {p}: {count(walk(seed, p) for seed in range(5))}")


def main():
    warnings.filterwarnings("ignore")
    for label, gen in (("make_df", make_df), ("overnight walk", overnight)):
        n, rows = screen(gen)
        print(f"== {label}: {n} scale-free comparators")
        for r, k, m in rows[:5]:
            print(f"  {r:.4f} {k} (n = {m})")
    print("== windows with no down gap, seeds 0-4")
    nan_rate()


if __name__ == "__main__":
    main()
