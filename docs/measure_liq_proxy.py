# -*- coding: utf-8 -*-
"""Print every number quoted in docs/LiquidityMeasured.md: Gate C (synthetic)
fire/clip/NaN counts, Gate D scale tolerances, and a proxy overlap against
existing columns.

    python docs/measure_liq_proxy.py

Synthetic walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set and the 89 real BIST frames (measured:
docs/LiquidityMeasured.md, Gate E).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def ohlcv(n=1200, seed=11, sigma=0.02, tick=None, spread_sigma=0.004):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = close * np.abs(rng.normal(0.0, spread_sigma, n))
    high = close + spread
    low = close - spread
    volume = rng.integers(1e5, 1e6, n).astype(float)
    if tick:
        close = np.round(close / tick) * tick
        high = np.round(high / tick) * tick
        low = np.round(low / tick) * tick
        high = np.maximum(high, close)
        low = np.minimum(low, close)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return (pd.Series(high, index=idx), pd.Series(low, index=idx),
            pd.Series(close, index=idx), pd.Series(volume, index=idx))


def rho(a, b):
    m = a.notna() & b.notna()
    if m.sum() < 20:
        return None
    return round(a[m].corr(b[m], method="spearman"), 4)


def _report_scale(name, base, scaled_by):
    """scaled_by: dict of k -> rescaled output Series, same index as base."""
    for k, out in scaled_by.items():
        m = base.notna() & out.notna()
        nan_match = bool((base.isna() == out.isna()).all())
        maxdiff = float((base[m] - out[m]).abs().max()) if m.any() else float("nan")
        print(f"  {name} x{k}: nan masks match={nan_match} max|diff|={maxdiff:.3e}")


def measure_corwin_schultz():
    print("== corwin_schultz (CS_1), n=1200 seed=11 tick=0.01")
    high, low, close, _ = ohlcv(tick=0.01)
    cs = ta.corwin_schultz(high, low)
    print("  fires (non-NaN):", int(cs.notna().sum()), "/", len(cs))
    print("  range:", float(cs.min()), float(cs.max()))
    print("  nonzero:", int((cs.dropna() != 0.0).sum()), "zero (clipped alpha):",
          int((cs.dropna() == 0.0).sum()))
    print("  distinct values:", cs.dropna().nunique())
    scaled = {k: ta.corwin_schultz(high * k, low * k) for k in (8.0, 64.0, 10.0, 3.7)}
    _report_scale("CS", cs, scaled)

    high_nt, low_nt, _, _ = ohlcv(tick=None)
    cs_nt = ta.corwin_schultz(high_nt, low_nt)
    print("  no tick rounding: zero (clipped alpha):", int((cs_nt.dropna() == 0.0).sum()),
          "nonzero:", int((cs_nt.dropna() != 0.0).sum()), "/", int(cs_nt.notna().sum()))


def measure_roll_spread():
    print("\n== roll_spread (ROLL_20), n=1200 seed=12 tick=0.01")
    _, _, close, _ = ohlcv(seed=12, tick=0.01)
    roll = ta.roll_spread(close)
    post_warmup = roll.iloc[21:]
    print("  fires (non-NaN):", int(roll.notna().sum()), "/", len(roll))
    print("  NaN from cov >= 0 among post-warmup bars:",
          int(post_warmup.isna().sum()), "/", len(post_warmup))
    print("  range:", float(roll.dropna().min()), float(roll.dropna().max()))
    print("  distinct values:", roll.dropna().nunique())
    scaled = {k: ta.roll_spread(close * k) for k in (8.0, 64.0, 10.0, 3.7)}
    _report_scale("ROLL", roll, scaled)


def measure_amihud():
    print("\n== amihud (AMIHUD_21), n=1200 seed=13 tick=0.01")
    _, _, close, volume = ohlcv(seed=13, tick=0.01)
    am = ta.amihud(close, volume)
    print("  fires (non-NaN):", int(am.notna().sum()), "/", len(am))
    print("  range:", float(am.dropna().min()), float(am.dropna().max()))
    print("  distinct values:", am.dropna().nunique())
    price_scaled = {k: ta.amihud(close * k, volume) for k in (8.0, 64.0, 10.0, 3.7)}
    _report_scale("AMIHUD price-axis", am, price_scaled)
    vol_scaled = {k: ta.amihud(close, volume * k) for k in (8.0, 64.0, 10.0, 3.7)}
    _report_scale("AMIHUD volume-axis", am, vol_scaled)


def measure_proxy_overlap():
    print("\n== proxy overlap (NOT Gate E)")
    high, low, close, volume = ohlcv(seed=1, n=3000, sigma=0.02, tick=0.01)
    cs = ta.corwin_schultz(high, low)
    roll = ta.roll_spread(close)
    am = ta.amihud(close, volume)
    price_comparators = {
        "NATR_14": ta.natr(high, low, close),
        "TRUE_RANGE (pct of close)": ta.true_range(high, low, close) / close * 100,
        "RVI_14": ta.rvi(high, low, close),
    }
    for name, x in price_comparators.items():
        print(f"  CS_1 vs {name}: {rho(cs, x)}")
        print(f"  ROLL_20 vs {name}: {rho(roll, x)}")
    vol_comparators = {
        "MFI_14": ta.mfi(high, low, close, volume),
        "CMF_20": ta.cmf(high, low, close, volume),
        "VFI_14": ta.vfi(close, volume),
    }
    for name, x in vol_comparators.items():
        print(f"  AMIHUD_21 vs {name}: {rho(am, x)}")
    print("  n (CS & ROLL both finite):", int((cs.notna() & roll.notna()).sum()))
    print("  n (AMIHUD finite):", int(am.notna().sum()))


if __name__ == "__main__":
    import platform
    print(f"pandas {pd.__version__}, numpy {np.__version__}, Python {platform.python_version()}")
    measure_corwin_schultz()
    measure_roll_spread()
    measure_amihud()
    measure_proxy_overlap()
