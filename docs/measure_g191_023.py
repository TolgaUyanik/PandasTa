# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191023Measured.md for
`pandas_ta.volatility.g191_023`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.volatility.g191_023 import g191_023

_REAL = importlib.import_module("pandas_ta.volatility.g191_023")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_023_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    out = g191_023(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_023(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 8-bar example at std_length=3, smooth_length=3,
    # smooth_weight=1 (alpha=1/3). min_length = 3+3-1 = 5, so bars 4..7 are
    # valid (see tests/test_g191_023.py::test_hand_derived_bars).
    hand_close = Series([10.0, 12.0, 9.0, 15.0, 7.0, 20.0, 5.0, 25.0])
    hand_out = g191_023(hand_close, std_length=3, smooth_length=3, smooth_weight=1)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))

    c1 = hand_close.shift(1)
    std_c = hand_close.rolling(3).std()
    up = hand_close > c1
    up_vol = std_c.where(up, 0.0).where(std_c.notna())
    dn_vol = std_c.where(~up, 0.0).where(std_c.notna())
    u = up_vol.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()
    d = dn_vol.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()
    print("c1:", list(c1))
    print("std_c:", list(std_c))
    print("up_vol:", list(up_vol))
    print("dn_vol:", list(dn_vol))
    print("u:", list(u))
    print("d:", list(d))
    print("100*u/(u+d):", list(100.0 * u / (u + d)))

    # Independent per-bar replay using plain numpy (np.std(ddof=1)), not
    # pandas' own .rolling()/.ewm(), spot-checking the shipped defaults.
    big_close = _walk(900, seed=3)
    out_defaults = g191_023(big_close)
    c = big_close.to_numpy(dtype=float)
    nn = len(c)
    std_length, smooth_length, smooth_weight = 20, 20, 1.0
    alpha = smooth_weight / smooth_length
    std_c_np = [float("nan")] * nn
    for t in range(std_length - 1, nn):
        std_c_np[t] = float(np.std(c[t - std_length + 1:t + 1], ddof=1))
    up_vol_np = [float("nan")] * nn
    dn_vol_np = [float("nan")] * nn
    for t in range(nn):
        if std_c_np[t] != std_c_np[t]:
            continue
        if c[t] > c[t - 1]:
            up_vol_np[t], dn_vol_np[t] = std_c_np[t], 0.0
        else:
            up_vol_np[t], dn_vol_np[t] = 0.0, std_c_np[t]

    def _sma_loop(x):
        y = None
        count = 0
        out_ = [float("nan")] * nn
        for t in range(nn):
            if x[t] != x[t]:
                continue
            y = x[t] if y is None else alpha * x[t] + (1 - alpha) * y
            count += 1
            if count >= smooth_length:
                out_[t] = y
        return out_

    u_np = _sma_loop(up_vol_np)
    d_np = _sma_loop(dn_vol_np)
    result_np = [float("nan")] * nn
    for t in range(nn):
        if u_np[t] == u_np[t] and d_np[t] == d_np[t]:
            result_np[t] = 100.0 * u_np[t] / (u_np[t] + d_np[t])
    for t in (300, 600, 899):
        diff = abs(float(out_defaults.iloc[t]) - result_np[t])
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={result_np[t]!r} diff={diff:.3e}")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    other_c = _walk(seed=97)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(close)
        hits = 0
        for j in offsets:
            pc = close.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_023)} of {total}")
    write_shift = _load_mutant(
        "        result = 100.0 * u / (u + d)",
        "        result = (100.0 * u / (u + d)).shift(-smooth_length)",
    )
    print(f"write-shift mutant (smooth_length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_023)} of {total}")
    centered_std = _load_mutant(
        "std_c = close.rolling(std_length).std()",
        "std_c = close.rolling(std_length, center=True).std()",
    )
    print(f"centered-std mutant leaks: {leaks(centered_std.g191_023)} of {total}")


if __name__ == "__main__":
    main()
