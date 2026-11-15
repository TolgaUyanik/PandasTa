# -*- coding: utf-8 -*-
"""Print every number in docs/KalmanTrendMeasured.md: steady state, warm-up,
head transient, scale tolerance, proxy overlap and Gate C (synthetic).

    python docs/measure_kalman_trend_proxy.py

Synthetic GBM walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set.
"""
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
kft = sys.modules["pandas_ta.overlap.kalman_trend"]  # `import ... as` binds the function, not the module

PARAMS = [(0.01, 0.0001), (0.0, 0.001), (0.1, 0.001)]


def walk(n=3000, sigma=0.02, seed=1, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def variant(old, new):
    """The module with one source edit, exec'd in memory (as the tests do)."""
    src = open(kft.__file__, encoding="utf-8").read()
    assert src.count(old) == 1
    mod = types.ModuleType("_kft_variant")
    exec(compile(src.replace(old, new), kft.__file__, "exec"), mod.__dict__)
    return mod.kalman_trend


def comparators(c):
    out = {f"close/EMA_{n} - 1": 100 * (c / ta.ema(c, n) - 1) for n in (5, 10, 20)}
    out.update({
        "BIAS_SMA_26": ta.bias(c), "ROC_1": ta.roc(c, 1), "ROC_5": ta.roc(c, 5),
        "ROC_10": ta.roc(c, 10), "ROC_20": ta.roc(c, 20), "SLOPE_10": ta.slope(c, 10),
        "PPO_12_26_9": ta.ppo(c).iloc[:, 0], "TRIX_30_9": ta.trix(c).iloc[:, 0],
        "CMO_14": ta.cmo(c), "RSI_14": ta.rsi(c), "PFE_10_5": ta.pfe(c),
    })
    return out


def head_worst(q_level, q_slope):
    worst = 0.0
    for seed in range(10):
        for s_ in (0.005, 0.02, 0.05):
            c = walk(1500, sigma=s_, seed=seed)
            full = ta.kalman_trend(c, q_level, q_slope)
            for s in (100, 500, 900):
                part = ta.kalman_trend(c.iloc[s:], q_level, q_slope)
                i = part.first_valid_index()
                worst = max(worst, (part.loc[i:] - full.loc[i:]).abs().max().max())
    return worst


def main():
    print("== steady state: params, gain (level, slope), spectral radius, warm-up, head worst |diff| (90 runs)")
    for p in PARAMS:
        (k0, k1), r = kft._steady_state(*p)
        print(f"  {p}: K ({k0:.4f}, {k1:.4f})  rho {r:.4f}  warm-up {kft._steady_warmup(*p)}"
              f"  head worst {head_worst(*p):.1e}")
    for p in ((0.1, 1e-5), (0.01, 1e-5)):
        print(f"  {p}: warm-up {kft._steady_warmup(*p)}")

    print("== transient at the defaults (unmasked filter, start-at-s vs start-at-0, same 90 runs)")
    unmasked = variant("isfinite(y))[warmup]", "isfinite(y))[0]")
    worst = np.zeros(400)
    for seed in range(10):
        for s_ in (0.005, 0.02, 0.05):
            c = walk(1500, sigma=s_, seed=seed)
            full = unmasked(c).to_numpy()
            for s in (100, 500, 900):
                part = unmasked(c.iloc[s:]).to_numpy()
                worst = np.maximum(worst, np.abs(part[:400] - full[s:s + 400]).max(axis=1))
    r = kft._steady_state(0.01, 0.0001)[1]
    tail_max = np.maximum.accumulate(worst[::-1])[::-1]
    print(f"  worst at the first bar {worst[0]:.1f}; first bar after which it stays < 1e-3:"
          f" {int(np.argmax(tail_max < 1e-3))}; predicted ceil(ln(1e-3/{worst[0]:.1f}) / ln rho):"
          f" {int(np.ceil(np.log(1e-3 / worst[0]) / np.log(r)))}")
    half = variant("isfinite(y))[warmup]", "isfinite(y))[warmup // 2]")
    c = walk(1500, seed=3)
    i = 500 + 213 // 2
    print(f"  half warm-up (seed 3, s=500, bar {i}): |diff| DIST"
          f" {abs(half(c.iloc[500:]).loc[i].iloc[0] - ta.kalman_trend(c).loc[i].iloc[0]):.1e}")

    print("== scale: max |diff| vs x1 (1200 bars, seed 11, tick 0.05)")
    c = walk(1200, seed=11, tick=0.05)
    base = ta.kalman_trend(c)
    for k in (8.0, 64.0, 10.0, 3.7):
        print(f"  x{k}: {(base - ta.kalman_trend(c * k)).abs().max().max():.1e}")

    c = walk()
    k = ta.kalman_trend(c)
    d, v = k.iloc[:, 0], k.iloc[:, 1]
    print("== proxy overlap (sigma 0.02, seed 1): n comparable", int(d.notna().sum()), "DIST vs VEL", rho(d, v))
    for name, x in comparators(c).items():
        print(f"  {name:22s} DIST {rho(d, x):8.4f}   VEL {rho(v, x):8.4f}")

    print("volatility sweep: sigma, max|rho| DIST (comparator), max|rho| VEL (comparator)")
    for s in (0.005, 0.01, 0.02, 0.05):
        c = walk(sigma=s)
        k = ta.kalman_trend(c)
        r = {n: (rho(k.iloc[:, 0], x), rho(k.iloc[:, 1], x)) for n, x in comparators(c).items()}
        bd = max(r, key=lambda n: abs(r[n][0]))
        bv = max(r, key=lambda n: abs(r[n][1]))
        print(" ", s, r[bd][0], bd, "|", r[bv][1], bv)

    c = walk(1200, seed=11, tick=0.05)
    k = ta.kalman_trend(c).dropna()
    for col in k:
        x = k[col]
        print(f"Gate C synthetic {col}: finite {len(x)} nonzero {int((x != 0).sum())} "
              f"pos {int((x > 0).sum())} neg {int((x < 0).sum())}")


if __name__ == "__main__":
    main()
