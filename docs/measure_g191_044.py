# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191044Measured.md for
`pandas_ta.statistics.g191_044`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.statistics.g191_044 import g191_044

_REAL = importlib.import_module("pandas_ta.statistics.g191_044")


def _ohlcv(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(seed + 2)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n))
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx), Series(close, index=idx),
            Series(volume, index=idx))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_044_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _term1_at(l, v, t, mean_v_length, corr_length, decay1_length, tsrank1_length):
    """Independent per-bar computation of the correlation-rank branch,
    using plain numpy (np.corrcoef, np.dot over explicit slices), not the
    module's own vectorised .rolling() calls."""
    w1 = np.arange(1, decay1_length + 1, dtype=float)
    w1 = w1 / w1.sum()

    def corr1_at(tt):
        mv_window = np.array([v[mt - mean_v_length + 1:mt + 1].mean()
                               for mt in range(tt - corr_length + 1, tt + 1)])
        l_window = l[tt - corr_length + 1:tt + 1]
        return np.corrcoef(l_window, mv_window)[0, 1]

    def decay1_at(tt):
        vals = [corr1_at(tt - back) for back in range(decay1_length - 1, -1, -1)]
        return float(np.dot(vals, w1))

    window = [decay1_at(t - back) for back in range(tsrank1_length - 1, -1, -1)]
    return float(pd.Series(window).rank(pct=True).iloc[-1])


def _term2_at(tp, t, delta_length, decay2_length, tsrank2_length):
    """Independent per-bar computation of the VWAP-momentum-rank branch."""
    w2 = np.arange(1, decay2_length + 1, dtype=float)
    w2 = w2 / w2.sum()

    def delta_at(tt):
        return tp[tt] - tp[tt - delta_length]

    def decay2_at(tt):
        vals = [delta_at(tt - back) for back in range(decay2_length - 1, -1, -1)]
        return float(np.dot(vals, w2))

    window = [decay2_at(t - back) for back in range(tsrank2_length - 1, -1, -1)]
    return float(pd.Series(window).rank(pct=True).iloc[-1])


def main():
    high, low, close, volume = _ohlcv()
    out = g191_044(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_044(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_044(high, low, close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} VOLUME max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: spot-check the full output against an independent per-bar
    # computation of both branches, small lengths to keep the python loop
    # fast (mean_v_length=3, corr_length=3, decay1_length=2,
    # tsrank1_length=2, delta_length=1, decay2_length=2, tsrank2_length=2).
    small_h, small_l, small_c, small_v = _ohlcv(60, seed=5)
    out_small = g191_044(small_h, small_l, small_c, small_v,
                          mean_v_length=3, corr_length=3, decay1_length=2,
                          tsrank1_length=2, delta_length=1, decay2_length=2,
                          tsrank2_length=2)
    l_np = small_l.to_numpy(dtype=float)
    v_np = small_v.to_numpy(dtype=float)
    tp_np = ((small_h + small_l + small_c) / 3.0).to_numpy(dtype=float)
    for t in (20, 40, 59):
        expected = (_term1_at(l_np, v_np, t, 3, 3, 2, 2)
                    + _term2_at(tp_np, t, 1, 2, 2))
        actual = out_small.iloc[t]
        print(f"t={t} module={actual!r} independent={expected!r}")

    # Gate A: spot-check the shipped default against the same independent
    # per-bar computation, on a longer frame.
    big_h, big_l, big_c, big_v = _ohlcv(900, seed=5)
    out_big = g191_044(big_h, big_l, big_c, big_v)
    l_np = big_l.to_numpy(dtype=float)
    v_np = big_v.to_numpy(dtype=float)
    tp_np = ((big_h + big_l + big_c) / 3.0).to_numpy(dtype=float)
    for t in (300, 600, 899):
        expected = (_term1_at(l_np, v_np, t, 10, 7, 6, 4)
                    + _term2_at(tp_np, t, 3, 10, 15))
        actual = out_big.iloc[t]
        print(f"t={t} module={actual!r} independent={expected!r}")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    high2, low2, close2, volume2 = _ohlcv(1500)
    oh, ol, oc, ov = _ohlcv(1500, seed=97)
    offsets = range(150, 1500, 40)

    def leaks(fn, debug=False):
        base = fn(high2, low2, close2, volume2)
        hits = 0
        misses = []
        for j in offsets:
            ph, pl, pc, pv = high2.copy(), low2.copy(), close2.copy(), volume2.copy()
            ph.iloc[j:] = oh.iloc[j:].values
            pl.iloc[j:] = ol.iloc[j:].values
            pc.iloc[j:] = oc.iloc[j:].values
            pv.iloc[j:] = ov.iloc[j:].values
            o = fn(ph, pl, pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
            elif debug:
                misses.append(j)
        if debug:
            print(f"  missed offsets: {misses}")
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_044)} of {total}")
    shipped = _load_mutant(
        "result = term1 + term2",
        "result = (term1 + term2).shift(-tsrank2_length)",
    )
    print(f"write-shift mutant leaks: {leaks(shipped.g191_044)} of {total}")
    weaker = _load_mutant(
        "    delta_tp = tp - tp.shift(delta_length)",
        "    delta_tp = tp - tp.shift(-delta_length)",
    )
    print(f"forward-delta mutant leaks: {leaks(weaker.g191_044, debug=True)} of {total}")

    # Investigate the misses: delta_tp changes by tens of units (confirmed
    # above), yet the mutant's FULL output at those bars is bit-identical.
    # Isolate term2 itself (not just delta_tp) by subtracting the
    # independently-computed term1 (identical at t < j: term1's own
    # lookback window, mean_v_length+corr_length+decay1_length+
    # tsrank1_length-3 = 24 bars, never reaches the perturbation boundary
    # j for these t) from the mutant's full output, for both the base and
    # the perturbed run, at the bars actually touched (t = j-delta_length
    # .. j-1).
    l_np_full = low2.to_numpy(dtype=float)
    v_np_full = volume2.to_numpy(dtype=float)
    out_base = weaker.g191_044(high2, low2, close2, volume2)
    for j in (270, 590, 710, 1150):
        ph, pl, pc, pv = high2.copy(), low2.copy(), close2.copy(), volume2.copy()
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        pv.iloc[j:] = ov.iloc[j:].values
        out_pert = weaker.g191_044(ph, pl, pc, pv)
        for t in range(j - 3, j):
            term1_t = _term1_at(l_np_full, v_np_full, t, 10, 7, 6, 4)
            term2_base = out_base.iloc[t] - term1_t
            term2_pert = out_pert.iloc[t] - term1_t
            print(f"j={j} t={t} term2_base={term2_base!r} term2_pert={term2_pert!r} "
                  f"tied={term2_base == term2_pert} at_ceiling={term2_base == 1.0}")


if __name__ == "__main__":
    main()
