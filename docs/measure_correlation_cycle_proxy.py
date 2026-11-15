# -*- coding: utf-8 -*-
"""Measurement script for `docs/CorrelationCycleMeasured.md`. Synthetic-only
(no real BIST data in this environment): fires/bounds/scale numbers on a
seeded random walk, plus a NOT-Gate-E proxy overlap against a handful of
already-shipped Ehlers-family columns the issue names as likely restated
(`cti`, `ebsw`, `fisher`, `lrsi`) and `ht_sine`'s SINE/LEADSINE. Run with
`python docs/measure_correlation_cycle_proxy.py`.
"""
import numpy as np
import pandas as pd

import pandas_ta as ta
from pandas_ta.cycles.correlation_cycle import correlation_cycle


def walk(n=3000, seed=1, sigma=0.02, tick=0.05):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return pd.Series(np.round(c / tick) * tick)


def main():
    close = walk()
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": 1.0})
    out = correlation_cycle(close)
    n = len(close)

    print(f"pandas={pd.__version__} numpy={np.__version__}")
    print(f"n={n}")
    for col in out.columns:
        s = out[col]
        finite = s.notna().sum()
        print(f"{col}: finite={finite}/{n} nunique={s.nunique()} "
              f"min={s.min():.6f} max={s.max():.6f}")

    for k in (8.0, 64.0):
        scaled = correlation_cycle(close * k)
        for col in out.columns:
            same = (out[col].dropna() == scaled[col].dropna()).all()
            print(f"x{k} bit-identical {col}: {same}")

    for k in (10.0, 3.7):
        scaled = correlation_cycle(close * k)
        for col in out.columns:
            diff = (out[col] - scaled[col]).abs().max()
            print(f"x{k} max abs diff {col}: {diff:.3e}")

    comparators = {
        "cti": lambda: df.ta.cti(),
        "ebsw": lambda: df.ta.ebsw(),
        "fisher": lambda: df.ta.fisher().iloc[:, 0],
        "lrsi": lambda: df.ta.lrsi(),
        "ht_sine_sine": lambda: df.ta.ht_sine().iloc[:, 0],
    }
    print("\nProxy overlap (NOT Gate E), Spearman rho vs CC_ANGLE_20 / CC_REAL_20:")
    for name, fn in comparators.items():
        try:
            comp = fn()
        except Exception as e:  # pragma: no cover -- diagnostic script
            print(f"{name}: ERROR {e}")
            continue
        for col in ("CC_REAL_20", "CC_IMAG_20", "CC_ANGLE_20"):
            joined = pd.concat([out[col], comp], axis=1).dropna()
            if len(joined) < 2:
                print(f"{col} vs {name}: n/a (no overlap)")
                continue
            rho = joined.iloc[:, 0].corr(joined.iloc[:, 1], method="spearman")
            print(f"{col} vs {name}: rho={rho:.4f} n={len(joined)}")


if __name__ == "__main__":
    main()
