# -*- coding: utf-8 -*-
"""Print every number docs/MswLeadMeasured.md and tests/test_msw_lead.py quote:
warm-up/bound/fire counts, scale tolerances, an independent-loop correctness
check, and a synthetic proxy overlap (NOT Gate E, which needs the parent
repo's production column set and runs on the launcher side).

    python docs/measure_msw_lead_proxy.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def loop_reference(close, length=20):
    """Independent re-derivation: plain Python loops, not the module's
    vectorized rolling/dot-product form."""
    c = close.to_numpy(dtype=float)
    n = len(c)
    out = np.full(n, np.nan)
    for t in range(length - 1, n):
        window = c[t - length + 1: t + 1]  # oldest first, window[-1] = current bar
        real = imag = 0.0
        for count in range(length):  # Ehlers' Count: 0 = current bar, going back
            price = window[length - 1 - count]
            real += price * np.cos(2 * np.pi * count / length)
            imag += price * np.sin(2 * np.pi * count / length)
        eps = 0.001 * c[t]
        if abs(real) > eps:
            phase = np.arctan(imag / real)
        else:
            phase = (np.pi / 2) * np.sign(imag)
        phase += (np.pi / 2) + (np.pi if real < 0 else 0.0)
        phase = phase % (2 * np.pi)
        out[t] = np.sin(phase + np.pi / 4)
    return out


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def main():
    c = walk()
    out = ta.msw_lead(c)
    print("== warm-up / bound / fires (1200 bars, seed 11, sigma 0.02)")
    print("  first valid index:", out.first_valid_index())
    valid = out.dropna()
    print("  n valid:", len(valid), "min", valid.min(), "max", valid.max())
    print("  nunique:", valid.nunique(), "positive", int((valid > 0).sum()), "negative", int((valid < 0).sum()))

    print("== independent-loop correctness (same frame)")
    ref = loop_reference(c)
    diff = np.nanmax(np.abs(out.to_numpy() - ref))
    mask_match = (np.isnan(out.to_numpy()) == np.isnan(ref)).all()
    print("  NaN masks match:", mask_match, " max|diff|:", diff)

    print("== scale (tick-rounded, 1200 bars)")
    ct = walk(tick=0.05)
    base = ta.msw_lead(ct)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = ta.msw_lead(ct * k)
        masks = (base.isna() == scaled.isna()).all()
        d = (base - scaled).abs().max()
        print(f"  x{k}: NaN masks match {masks}  max|diff| {d:.3e}")

    print("== length sweep fires/bound")
    for length in (10, 20, 40):
        o = ta.msw_lead(c, length=length).dropna()
        print(f"  length={length}: n={len(o)} min={o.min():.4f} max={o.max():.4f}")

    print("== proxy overlap (sigma 0.02, seed 1), NOT Gate E")
    c2 = walk(seed=1)
    m = ta.msw_lead(c2)
    comparators = {
        "RSI_14": ta.rsi(c2),
        "HT_SINE": ta.ht_sine(c2).iloc[:, 0], "HT_LEADSINE": ta.ht_sine(c2).iloc[:, 1],
        "STOCHk_14_3_3": ta.stoch(c2, c2, c2).iloc[:, 0],
        "CC_ANGLE_20": ta.correlation_cycle(c2).iloc[:, 1],
        "ROC_10": ta.roc(c2, 10),
    }
    for name, x in comparators.items():
        print(f"  {name:16s} rho {rho(m, x)}")


if __name__ == "__main__":
    main()
