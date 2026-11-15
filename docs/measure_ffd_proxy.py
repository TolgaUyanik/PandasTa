# -*- coding: utf-8 -*-
"""Print every number in docs/FfdMeasured.md: weight width and sum, head
behaviour, scale tolerance, Gate C synthetic counts, and the proxy overlap
against existing columns.

    python docs/measure_ffd_proxy.py

Synthetic GBM walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set and real BIST frames (run by the
issue-solver launcher outside this worktree).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
ffd_mod = sys.modules["pandas_ta.statistics.ffd"]

PARAMS = [(0.4, 1e-5), (0.3, 1e-5), (0.5, 1e-5), (0.4, 1e-4)]


def walk(n=3000, sigma=0.02, seed=1, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def _raw_weights(d, threshold):
    """AFML Snippet 5.1 exactly as published, with NO re-centring -- the
    "before" side of the before/after defect measurement below."""
    w = [1.0]
    k = 1
    while True:
        wk = -w[-1] * (d - k + 1) / k
        if abs(wk) < threshold:
            break
        w.append(wk)
        k += 1
    return w


def _ffd_with_weights(close, w):
    """The module's convolution, parameterised on an explicit weight vector,
    so the same head-stability experiment can be run on the raw (pre-fix)
    and re-centred (post-fix) weights at an IDENTICAL (d, threshold)."""
    width = len(w)
    vals = close.to_numpy(dtype=float)
    mask = np.isfinite(vals) & (vals > 0)
    usable = vals[mask]
    if len(usable) <= width:
        return None
    anchor = usable[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.log(vals / anchor)
    y[~mask] = np.nan
    out = np.full(len(y), np.nan)
    win = np.lib.stride_tricks.sliding_window_view(y, width)
    coef = np.array(w[::-1])
    with np.errstate(invalid="ignore"):
        out[width - 1:] = win @ coef
    return pd.Series(out, index=close.index)


def comparators(c):
    out = {f"close/EMA_{n} - 1": 100 * (c / ta.ema(c, n) - 1) for n in (5, 10, 20)}
    out.update({
        "BIAS_SMA_26": ta.bias(c), "ROC_1": ta.roc(c, 1), "ROC_5": ta.roc(c, 5),
        "ROC_10": ta.roc(c, 10), "ROC_20": ta.roc(c, 20), "SLOPE_10": ta.slope(c, 10),
        "PPO_12_26_9": ta.ppo(c).iloc[:, 0], "TRIX_30_9": ta.trix(c).iloc[:, 0],
        "CMO_14": ta.cmo(c), "RSI_14": ta.rsi(c), "CUSUM_100": ta.cusum(c),
        "KPSS_100": ta.kpss(c),
    })
    return out


def main():
    print("== weights: d, threshold -> width, sum(w), |w[0]|, |w[-1]|")
    for d, thr in PARAMS:
        w = ffd_mod._ffd_weights(d, thr)
        print(f"  d={d} thr={thr}: width={len(w)} sum={sum(w):.6g} w0={w[0]:.6g} wlast={w[-1]:.6g}")

    print("== scale: max |diff| vs x1 (3000 bars, seed 11, tick 0.05), default d/threshold")
    c = walk(3000, seed=11, tick=0.05)
    base = ta.ffd(c)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = ta.ffd(c * k)
        same_mask = (base.isna() == scaled.isna()).all()
        print(f"  x{k}: max|diff| {(base - scaled).abs().max():.3e}  nan-masks-match {same_mask}"
              f"  bit-identical {base.equals(scaled)}")

    print("== Gate C synthetic (3000 bars, seed 11, tick 0.05), default d/threshold")
    out = ta.ffd(c).dropna()
    print(f"  finite {len(out)} / {len(c)}  nonzero {int((out != 0).sum())}"
          f"  pos {int((out > 0).sum())}  neg {int((out < 0).sum())}  distinct {out.nunique()}")

    print("== head: filter started at bar s vs bar 0, worst |diff| from first comparable bar")
    c = walk(4000, seed=7)
    full = ta.ffd(c)
    w = len(ffd_mod._ffd_weights(0.4, 1e-4))
    for s in (100, 500, 900):
        part = ta.ffd(c.iloc[s:])
        i = part.first_valid_index()
        assert i == s + w - 1, (i, s + w - 1)
        worst = (part.loc[i:] - full.loc[i:]).abs().max()
        print(f"  s={s}: first valid at {i} (= s + width - 1), worst |diff| {worst:.3e}")

    print("== Gate D defect, raw AFML weights vs re-centred, at d=0.4, threshold=1e-5"
          " (identical config, before vs after the fix -- the number the docstrings cite)")
    d, thr = 0.4, 1e-5
    raw, fixed = _raw_weights(d, thr), ffd_mod._ffd_weights(d, thr)
    assert len(raw) == len(fixed)
    print(f"  width {len(raw)}  sum(raw) {sum(raw):.6g}  sum(re-centred) {sum(fixed):.3e}")
    c = walk(4000, seed=7)
    full_raw, full_fixed = _ffd_with_weights(c, raw), _ffd_with_weights(c, fixed)
    for s in (100, 500, 900):
        part_raw = _ffd_with_weights(c.iloc[s:], raw)
        part_fixed = _ffd_with_weights(c.iloc[s:], fixed)
        i = part_raw.first_valid_index()
        worst_raw = (part_raw.loc[i:] - full_raw.loc[i:]).abs().max()
        worst_fixed = (part_fixed.loc[i:] - full_fixed.loc[i:]).abs().max()
        print(f"  s={s}: worst|diff| raw(before) {worst_raw:.3e}  re-centred(after) {worst_fixed:.3e}")

    print("== proxy overlap (sigma 0.02, seed 1), default d/threshold")
    c = walk(5000)
    f = ta.ffd(c)
    n_comp = int(f.notna().sum())
    print("  n comparable", n_comp)
    for name, x in comparators(c).items():
        print(f"  {name:22s} rho {rho(f, x):8.4f}")

    print("volatility sweep: sigma, max|rho| (comparator)")
    for s in (0.005, 0.01, 0.02, 0.05):
        c = walk(5000, sigma=s)
        f = ta.ffd(c)
        r = {n: rho(f, x) for n, x in comparators(c).items()}
        best = max(r, key=lambda n: abs(r[n]))
        print(" ", s, r[best], best)


if __name__ == "__main__":
    main()
