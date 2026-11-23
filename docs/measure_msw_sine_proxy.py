# -*- coding: utf-8 -*-
"""Print every number docs/MswSineMeasured.md and tests/test_msw_sine.py quote:
warm-up/bound/fire counts, scale tolerances, an independent-loop correctness
check, and a synthetic proxy overlap (NOT Gate E, which needs the parent
repo's production column set and runs on the launcher side).

    python docs/measure_msw_sine_proxy.py
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
        out[t] = np.sin(phase)
    return out


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def main():
    c = walk()
    out = ta.msw_sine(c)
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
    base = ta.msw_sine(ct)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = ta.msw_sine(ct * k)
        masks = (base.isna() == scaled.isna()).all()
        d = (base - scaled).abs().max()
        print(f"  x{k}: NaN masks match {masks}  max|diff| {d:.3e}")

    print("== length sweep fires/bound")
    for length in (10, 20, 40):
        o = ta.msw_sine(c, length=length).dropna()
        print(f"  length={length}: n={len(o)} min={o.min():.4f} max={o.max():.4f}")

    print("== mutant liveness (imag-shift degenerate check)")
    close = walk()
    base_out = ta.msw_sine(close)
    imag_shift_out = _imag_shift_variant(close)
    diff_mask = (base_out != imag_shift_out) & base_out.notna() & imag_shift_out.notna()
    print("  imag-shift differs on", int(diff_mask.sum()), "of", int(base_out.notna().sum()), "bars")

    print("== proxy overlap (sigma 0.02, seed 1), NOT Gate E")
    c2 = walk(seed=1)
    m = ta.msw_sine(c2)
    comparators = {
        "RSI_14": ta.rsi(c2),
        "HT_SINE": ta.ht_sine(c2).iloc[:, 0], "HT_LEADSINE": ta.ht_sine(c2).iloc[:, 1],
        "MSW_LEAD_20": ta.msw_lead(c2),
        "STOCHk_14_3_3": ta.stoch(c2, c2, c2).iloc[:, 0],
        "CC_ANGLE_20": ta.correlation_cycle(c2).iloc[:, 1],
        "ROC_10": ta.roc(c2, 10),
    }
    for name, x in comparators.items():
        print(f"  {name:16s} rho {rho(m, x)}")


def _imag_shift_variant(close, length=20):
    """Same as the module, but the IMAGINARY part's rolling input is shifted
    one bar early -- the degenerate mutant rejected by the causality test
    because count=0's sine weight is sin(0) = 0."""
    k = np.arange(length)[::-1]
    cos_wave = np.cos(2 * np.pi * k / length)
    sin_wave = np.sin(2 * np.pi * k / length)
    real = close.rolling(length).apply(lambda y: np.dot(y, cos_wave), raw=True)
    imag = close.shift(-1).rolling(length).apply(lambda y: np.dot(y, sin_wave), raw=True)
    eps = 0.001 * close
    with np.errstate(divide="ignore", invalid="ignore"):
        phase = np.where(real.abs() > eps, np.arctan(imag / real), (np.pi / 2) * np.sign(imag))
    phase = phase + np.where(real < 0, np.pi, 0.0) + np.pi / 2
    phase = np.mod(phase, 2 * np.pi)
    return pd.Series(np.sin(phase), index=close.index)


if __name__ == "__main__":
    main()
