# -*- coding: utf-8 -*-
"""Print the Gate A/C/D numbers and a pre-screen (NOT Gate E) in docs/EntlzMeasured.md.

    python docs/measure_entlz_proxy.py

A PROXY screen only -- Gate E needs the parent repo's production column set
and the 89-frame BIST universe and is run by the launcher.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.statistics.entlz import entlz

LOG2_3 = np.log2(3.0)


def walk(n=1200, seed=11, sigma=0.015, tick=0.01):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def reference(close, length, base=2.0):
    r = np.diff(np.asarray(close, dtype=float))
    sign = np.sign(r)
    out = np.full(len(close), np.nan)
    for t in range(length, len(close)):
        window = sign[t - length:t]
        counts = {s: 0 for s in (-1.0, 0.0, 1.0)}
        for v in window:
            counts[v] += 1
        h = 0.0
        for v in counts.values():
            if v == 0:
                continue
            p = v / length
            h -= p * np.log(p) / np.log(base)
        out[t] = h
    return out


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def main():
    close = walk()

    print("== Gate A: against the independent reference loop")
    for length in (20, 9, 2):
        out = entlz(close, length=length)
        ref = reference(close, length)
        mask = ~np.isnan(ref)
        diff = np.abs(out.values[mask] - ref[mask])
        print(f"  length={length}: max|diff| {diff.max():.3e}  n {int(mask.sum())}")

    print("== Gate D: scale invariance (sign(k*x) == sign(x) for k > 0)")
    base = entlz(close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = entlz(close * k)
        same_nan = (base.isna() == scaled.isna()).all()
        m = base.notna()
        bit_identical = bool((base[m] == scaled[m]).all())
        print(f"  k={k}: NaN masks match {same_nan}  bit-identical {bit_identical}")

    print("== Gate C: synthetic reachability (1200 bars, seed 11, sigma 1.5%, tick 0.01)")
    out = entlz(close).dropna()
    print("  non-NaN", len(out), "distinct", out.nunique(),
          "zero", int((out == 0.0).sum()), "min", round(out.min(), 6), "max", round(out.max(), 6),
          "bound log2(3)", round(LOG2_3, 6))

    print("== Gate C: composite reachability (50-bar trend + 200-bar chop, length 20)")
    trend = np.arange(1.0, 51.0)
    chop = walk(200, seed=3).to_numpy() + trend[-1]
    composite = pd.Series(np.concatenate([trend, chop]))
    comp_out = entlz(composite, length=20).dropna()
    print("  non-NaN", len(comp_out), "distinct", comp_out.nunique(),
          "zero", int((comp_out == 0.0).sum()), ">=0.99", int((comp_out >= 0.99).sum()))

    print("== Pre-screen (NOT Gate E): Spearman rho vs in-package candidates, same walk")
    e = entlz(close)
    comparators = {
        "ENTP_10 (price-level entropy)": ta.entropy(close),
        "CMO_14": ta.cmo(close),
        "RSX_14": ta.rsx(close),
        "RSI_14": ta.rsi(close),
        "STDEV_20": ta.stdev(close, 20),
        "SKEW_20": ta.skew(close, 20),
        "ER_10": ta.er(close),
        "CUSUM_100": ta.cusum(close),
        "KPSS_100": ta.kpss(close),
    }
    for name, x in comparators.items():
        print(f"  ENTLZ_20 vs {name}: {rho(e, x)}")


if __name__ == "__main__":
    main()
