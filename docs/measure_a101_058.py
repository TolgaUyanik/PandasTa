# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101058Measured.md for
`pandas_ta.volume.a101_058`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.a101_058 import a101_058


def _frame(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    noise = np.abs(rng.normal(0.0, 0.3, n))
    high = close + noise
    low = close - noise
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    return Series(high), Series(low), Series(close), Series(volume)


def main():
    high, low, close, volume = _frame()
    out = a101_058(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")
    print(f"value_counts=\n{out.value_counts().sort_index()}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = a101_058(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")
        scaled_v = a101_058(high, low, close, volume * k)
        max_diff_v = float((out[m] - scaled_v[m]).abs().max())
        mask_match_v = bool((out.isna() == scaled_v.isna()).all())
        print(f"x{k} volume max|diff|={max_diff_v} nan-mask-match={mask_match_v}")

    for k in (10.0, 3.7):
        scaled = a101_058(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")
        scaled_v = a101_058(high, low, close, volume * k)
        max_diff_v = float((out[m] - scaled_v[m]).abs().max())
        mask_match_v = bool((out.isna() == scaled_v.isna()).all())
        print(f"x{k} volume max|diff|={max_diff_v} nan-mask-match={mask_match_v}")

    # Gate B: future-perturbation leak count, real module vs. a mutant that
    # shifts the final write index `rank_length` bars into the future
    # (result = -ranked.shift(-rank_length)) -- see tests/test_a101_058.py.
    other_h, other_l, other_c, other_v = _frame(seed=97)
    offsets = range(300, 1500, 40)

    def leaks(fn):
        base = fn(high, low, close, volume)
        hits = 0
        for j in offsets:
            ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pl.iloc[j:] = other_l.iloc[j:].values
            pc.iloc[j:] = other_c.iloc[j:].values
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(ph, pl, pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    def mutant(h, l, c, v):
        from pandas_ta.overlap.wma import wma
        from pandas_ta.utils._pine import correlation as _rolling_pearson
        typical = (h + l + c) / 3
        corr_series = _rolling_pearson(typical, v, 4)
        decayed = wma(corr_series, length=8, asc=True)
        from pandas_ta.volume.a101_058 import _ts_rank
        ranked = Series(_ts_rank(decayed.to_numpy(dtype=float), 6), index=decayed.index)
        return -ranked.shift(-6)

    print(f"real-module leaks: {leaks(a101_058)} of {len(list(offsets))}")
    print(f"mutant leaks: {leaks(mutant)} of {len(list(offsets))}")


if __name__ == "__main__":
    main()
