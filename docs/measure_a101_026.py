# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101026Measured.md for
`pandas_ta.volume.a101_026`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.a101_026 import a101_026


def _frame(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    noise = np.abs(rng.normal(0.0, 0.3, n))
    high = close + noise
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    return Series(high), Series(volume)


def _check_hand_example():
    V = Series([10.0, 12.0, 9.0, 15.0, 20.0, 11.0, 25.0, 18.0])
    H = Series([100.0, 90.0, 150.0, 60.0, 200.0, 30.0, 300.0, 400.0])
    out = a101_026(H, V, vol_rank_length=3, high_rank_length=3, corr_length=3, max_length=2)
    print("hand example:", out.to_dict())


def _check_independent_loop(n=900, seed=3):
    high, volume = _frame(n, seed=seed)
    out = a101_026(high, volume)
    h = high.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    vol_rank_length = high_rank_length = corr_length = 5
    max_length = 3

    def rank_at(x, t, length):
        window = x[t - length + 1:t + 1]
        current = window[-1]
        return float(np.count_nonzero(window <= current)) / length

    def corr_at(t):
        a = np.array([rank_at(v, i, vol_rank_length) for i in range(t - corr_length + 1, t + 1)])
        b = np.array([rank_at(h, i, high_rank_length) for i in range(t - corr_length + 1, t + 1)])
        return np.corrcoef(a, b)[0, 1]

    def expected_at(t):
        vals = [corr_at(i) for i in range(t - max_length + 1, t + 1)]
        if any(np.isnan(v) for v in vals):
            return np.nan  # rolling().max() with min_periods=window needs every value non-null
        return -max(vals)

    for t in (300, 500, 899):
        exp = expected_at(t)
        got = float(out.iloc[t])
        print(f"independent loop t={t}: expected={exp} got={got} diff={abs(exp - got)}")


def main():
    _check_hand_example()
    _check_independent_loop()
    high, volume = _frame()
    out = a101_026(high, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")
    # `first_valid` (== min_length - 1) is the count of LEADING NaN bars, not
    # min_length itself -- min_length is the series length needed for one
    # valid output, one more than the number of leading NaNs it leaves behind.
    leading_nan = first_valid
    expected_max_fires = n - leading_nan
    mid_stream_nan = expected_max_fires - fires
    print(f"leading_nan={leading_nan} expected_max_fires={expected_max_fires} "
          f"mid_stream_nan(zero-variance corr windows)={mid_stream_nan} "
          f"({100 * mid_stream_nan / expected_max_fires:.1f}% of post-warmup bars)")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = a101_026(high * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} high max|diff|={max_diff} nan-mask-match={mask_match}")
        scaled_v = a101_026(high, volume * k)
        max_diff_v = float((out[m] - scaled_v[m]).abs().max())
        mask_match_v = bool((out.isna() == scaled_v.isna()).all())
        print(f"x{k} volume max|diff|={max_diff_v} nan-mask-match={mask_match_v}")

    for k in (10.0, 3.7):
        scaled = a101_026(high * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} high max|diff|={max_diff} nan-mask-match={mask_match}")
        scaled_v = a101_026(high, volume * k)
        max_diff_v = float((out[m] - scaled_v[m]).abs().max())
        mask_match_v = bool((out.isna() == scaled_v.isna()).all())
        print(f"x{k} volume max|diff|={max_diff_v} nan-mask-match={mask_match_v}")

    # Gate B: future-perturbation leak count, real module vs. a mutant that
    # shifts the final write index `max_length` bars into the future
    # (result = -peak.shift(-max_length)) -- see tests/test_a101_026.py.
    other_h, other_v = _frame(seed=97)
    offsets = range(300, 1500, 40)

    def leaks(fn):
        base = fn(high, volume)
        hits = 0
        for j in offsets:
            ph, pv = high.copy(), volume.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(ph, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    def make_mutant(shift_by):
        def mutant(h, v):
            from pandas_ta.utils._pine import correlation as _rolling_pearson
            from pandas_ta.volume.a101_026 import _ts_rank
            vol_rank = Series(_ts_rank(v.to_numpy(dtype=float), 5), index=v.index)
            high_rank = Series(_ts_rank(h.to_numpy(dtype=float), 5), index=h.index)
            corr_series = _rolling_pearson(vol_rank, high_rank, 5)
            peak = corr_series.rolling(3, min_periods=3).max()
            return -peak.shift(-shift_by)
        return mutant

    # A single-bar lookahead (shift=1) is caught only 10/30 times -- the
    # rolling max absorbs a 1-bar forward peek whenever the shifted value
    # isn't the new window maximum, so a smaller shift is not a reliable
    # mutant here. shift=(corr_length + max_length)=8 widens the affected
    # window enough to be caught every time -- measured below, not assumed.
    print(f"real-module leaks: {leaks(a101_026)} of {len(list(offsets))}")
    print(f"rejected 1-bar-lookahead mutant leaks: {leaks(make_mutant(1))} of {len(list(offsets))}")
    print(f"shipped mutant (shift=8) leaks: {leaks(make_mutant(8))} of {len(list(offsets))}")


if __name__ == "__main__":
    main()
