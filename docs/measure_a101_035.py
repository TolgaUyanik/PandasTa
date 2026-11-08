# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101035Measured.md for
`pandas_ta.volume.a101_035`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.a101_035 import a101_035, _ts_rank


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
    out = a101_035(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = a101_035(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")
        scaled_v = a101_035(high, low, close, volume * k)
        max_diff_v = float((out[m] - scaled_v[m]).abs().max())
        mask_match_v = bool((out.isna() == scaled_v.isna()).all())
        print(f"x{k} volume max|diff|={max_diff_v} nan-mask-match={mask_match_v}")

    for k in (10.0, 3.7):
        scaled = a101_035(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")
        scaled_v = a101_035(high, low, close, volume * k)
        max_diff_v = float((out[m] - scaled_v[m]).abs().max())
        mask_match_v = bool((out.isna() == scaled_v.isna()).all())
        print(f"x{k} volume max|diff|={max_diff_v} nan-mask-match={mask_match_v}")

    # Gate B: future-perturbation leak count, real module vs. a mutant that
    # shifts the final write index 1 bar into the future (result.shift(-1))
    # -- see tests/test_a101_035.py.
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

    def _base_result(h, l, c, v):
        returns = c.pct_change(fill_method=None)
        price_term = c + h - l
        vol_rank = Series(_ts_rank(v.to_numpy(dtype=float), 32), index=v.index)
        pr_rank = Series(_ts_rank(price_term.to_numpy(dtype=float), 16), index=price_term.index)
        ret_rank = Series(_ts_rank(returns.to_numpy(dtype=float), 32), index=returns.index)
        return vol_rank * (1 - pr_rank) * (1 - ret_rank)

    def mutant_1bar(h, l, c, v):
        # Tried FIRST and rejected: see docs/A101035Measured.md -- ts_rank's
        # bucket quantisation sometimes absorbs a 1-bar perturbation.
        return _base_result(h, l, c, v).shift(-1)  # 1-bar look-ahead

    def mutant_32bar(h, l, c, v):
        return _base_result(h, l, c, v).shift(-32)  # full-window look-ahead

    print(f"real-module leaks: {leaks(a101_035)} of {len(list(offsets))}")
    print(f"rejected single-bar-shift mutant leaks: {leaks(mutant_1bar)} of {len(list(offsets))}")
    print(f"shipped 32-bar-shift mutant leaks: {leaks(mutant_32bar)} of {len(list(offsets))}")


if __name__ == "__main__":
    main()
