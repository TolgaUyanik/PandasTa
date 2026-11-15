# -*- coding: utf-8 -*-
"""Gate C/D measurement script for `median_ad_hl2`: real-data reachability
counts and the Category total, used to fill docs/MedianAdHl2Measured.md and
to re-sync tests/test_altport2_ports.py::CATEGORY_TOTAL after adding the
indicator. Run: `python docs/measure_median_ad_hl2.py`.
"""
import numpy as np
import pandas as pd

import pandas_ta as ta
from pandas_ta.statistics.median_ad_hl2 import median_ad_hl2


def main():
    total = sum(len(v) for v in ta.Category.values())
    print(f"Category total: {total}")
    print(f"Category['statistics'] ({len(ta.Category['statistics'])}): {ta.Category['statistics']}")

    rng = np.random.default_rng(7)
    n = 3000
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    tick = 0.05
    close = np.round(close / tick) * tick
    high = close + rng.uniform(0.0, 0.5, n)
    low = close - rng.uniform(0.0, 0.5, n)
    close_s, high_s, low_s = pd.Series(close), pd.Series(high), pd.Series(low)

    out = median_ad_hl2(high_s, low_s, close_s)
    fires = int(out.notna().sum())
    print(f"n={n}, fires={fires}, zero_count={int((out.dropna() == 0).sum())}, "
          f"nunique={out.dropna().nunique()}")
    print(f"min={out.min():.8f} max={out.max():.8f} median={out.median():.8f}")


if __name__ == "__main__":
    main()
