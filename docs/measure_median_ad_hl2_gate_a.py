# -*- coding: utf-8 -*-
"""Gate A oracle for `median_ad_hl2`: compares against scipy's own
`median_abs_deviation` (the function jesse's `median_ad.py` calls), not the
prototype. `scipy` is a DEV-ONLY dependency (setup.py extras_require["dev"]);
this script is never imported by shipped code. Run:
`python docs/measure_median_ad_hl2_gate_a.py`.
"""
import numpy as np
import pandas as pd
from scipy.stats import median_abs_deviation

from pandas_ta.statistics.median_ad_hl2 import median_ad_hl2


def main():
    rng = np.random.default_rng(3)
    n = 400
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    high = close + rng.uniform(0.0, 0.5, n)
    low = close - rng.uniform(0.0, 0.5, n)
    hl2 = (high + low) / 2
    length = 5

    oracle = np.full(n, np.nan)
    for t in range(length - 1, n):
        w = hl2[t - length + 1: t + 1]
        oracle[t] = median_abs_deviation(w, scale=1.0) / close[t]

    out = median_ad_hl2(pd.Series(high), pd.Series(low), pd.Series(close), length=length).to_numpy()

    nan_match = (np.isnan(oracle) == np.isnan(out)).all()
    m = ~np.isnan(oracle)
    max_diff = np.nanmax(np.abs(oracle[m] - out[m]))
    print(f"n={n}, nan_masks_match={nan_match}, max_abs_diff_vs_scipy={max_diff:.3e}")
    assert nan_match and max_diff < 1e-12, "module diverges from scipy.stats.median_abs_deviation(scale=1.0)"
    print("Gate A: matches scipy.stats.median_abs_deviation(scale=1.0) to 1e-12")


if __name__ == "__main__":
    main()
