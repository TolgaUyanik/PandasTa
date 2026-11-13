# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191111Measured.md for
`pandas_ta.volume.g191_111`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.volume.g191_111 import g191_111

_REAL = importlib.import_module("pandas_ta.volume.g191_111")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    volume = rng2.uniform(1000.0, 5000.0, n)
    return (Series(high), Series(low), Series(close), Series(volume))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_111_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, low, close, volume = _walk()
    out = g191_111(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_111(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE-only max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_111(high, low, close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} VOLUME-only max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_111(high * k, low * k, close * k, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} BOTH max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 8-bar example, smooth1_length=3/weight=1,
    # smooth2_length=2/weight=1, mean_length=3. No H==L ties.
    hand_high = Series([12.0, 14.0, 11.0, 18.0, 10.0, 22.0, 9.0, 26.0])
    hand_low = Series([8.0, 10.0, 8.0, 12.0, 6.0, 15.0, 5.0, 18.0])
    hand_close = Series([10.0, 13.0, 9.0, 15.0, 7.0, 20.0, 6.0, 25.0])
    hand_volume = Series([100.0, 150.0, 80.0, 200.0, 60.0, 300.0, 50.0, 400.0])
    hand_out = g191_111(hand_high, hand_low, hand_close, hand_volume,
                         smooth1_length=3, smooth1_weight=1,
                         smooth2_length=2, smooth2_weight=1, mean_length=3)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))

    clv = ((hand_close - hand_low) - (hand_high - hand_close)) / (hand_high - hand_low)
    x = hand_volume * clv
    sma1 = x.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()
    sma2 = x.ewm(alpha=1 / 2, adjust=False, min_periods=2).mean()
    mean_v = hand_volume.rolling(3).mean()
    print("clv:", list(clv))
    print("x:", list(x))
    print("sma1:", list(sma1))
    print("sma2:", list(sma2))
    print("mean_v:", list(mean_v))
    print("(sma1-sma2)/mean_v:", list((sma1 - sma2) / mean_v))

    # A tie bar (H==L) injected mid-warm-up, shipped defaults.
    tie_high = high.copy()
    tie_low = low.copy()
    tie_close = close.copy()
    tie_idx = 5
    tie_high.iloc[tie_idx] = 100.0
    tie_low.iloc[tie_idx] = 100.0
    tie_close.iloc[tie_idx] = 100.0
    tie_out = g191_111(tie_high, tie_low, tie_close, volume)
    print("tie-bar first_valid_index:", int(tie_out.notna().idxmax()))
    print("no-tie first_valid_index:", first_valid)

    # Independent per-bar replay using plain numpy, not pandas' own
    # .rolling()/.ewm(), spot-checking the shipped defaults.
    big_high, big_low, big_close, big_volume = _walk(900, seed=3)
    out_defaults = g191_111(big_high, big_low, big_close, big_volume)
    h = big_high.to_numpy(dtype=float)
    l = big_low.to_numpy(dtype=float)
    c = big_close.to_numpy(dtype=float)
    v = big_volume.to_numpy(dtype=float)
    nn = len(c)
    s1n, s1w, s2n, s2w, mn = 11, 2, 4, 2, 20
    a1, a2 = s1w / s1n, s2w / s2n
    clv_np = np.where(h != l, ((c - l) - (h - c)) / (h - l), np.nan)
    x_np = v * clv_np
    y1 = y2 = None
    count1 = count2 = 0
    sma1_np = [float("nan")] * nn
    sma2_np = [float("nan")] * nn
    for t in range(nn):
        if x_np[t] == x_np[t]:
            y1 = x_np[t] if y1 is None else a1 * x_np[t] + (1 - a1) * y1
            count1 += 1
            if count1 >= s1n:
                sma1_np[t] = y1
            y2 = x_np[t] if y2 is None else a2 * x_np[t] + (1 - a2) * y2
            count2 += 1
            if count2 >= s2n:
                sma2_np[t] = y2
        elif y1 is not None:
            sma1_np[t] = y1 if count1 >= s1n else float("nan")
            sma2_np[t] = y2 if count2 >= s2n else float("nan")
    result_np = [float("nan")] * nn
    for t in range(mn - 1, nn):
        mean_v_t = float(np.mean(v[t - mn + 1:t + 1]))
        if sma1_np[t] == sma1_np[t] and sma2_np[t] == sma2_np[t]:
            result_np[t] = (sma1_np[t] - sma2_np[t]) / mean_v_t
    for t in (300, 600, 899):
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={result_np[t]!r}")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    other_h, other_l, other_c, other_v = _walk(seed=97)
    offsets = range(50, 1500, 40)

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

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_111)} of {total}")
    write_shift = _load_mutant(
        "result = ((sma1 - sma2) / mean_v).replace([np.inf, -np.inf], np.nan)",
        "result = (((sma1 - sma2) / mean_v).replace([np.inf, -np.inf], np.nan)).shift(-mean_length)",
    )
    print(f"write-shift mutant (mean_length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_111)} of {total}")
    centered_mean = _load_mutant(
        "mean_v = volume.rolling(mean_length).mean()",
        "mean_v = volume.rolling(mean_length, center=True).mean()",
    )
    print(f"centered-mean_v mutant leaks: {leaks(centered_mean.g191_111)} of {total}")


if __name__ == "__main__":
    main()
