# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191109Measured.md for
`pandas_ta.volatility.g191_109`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.volatility.g191_109 import g191_109

_REAL = importlib.import_module("pandas_ta.volatility.g191_109")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    return (Series(high), Series(low))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_109_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, low = _walk()
    out = g191_109(high, low)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")
    print(f"any-negative={(bool((out.dropna() < 0).any()))}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_109(high * k, low * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 8-bar example at smooth1_length=3, smooth1_weight=1,
    # smooth2_length=2, smooth2_weight=1. min_length = 3+2-1 = 4, so bars 0..2
    # are NaN and bars 3..7 are the first five valid values.
    hand_high = Series([12.0, 14.0, 11.0, 18.0, 10.0, 22.0, 9.0, 26.0])
    hand_low = Series([8.0, 10.0, 8.0, 12.0, 6.0, 15.0, 5.0, 18.0])
    hand_out = g191_109(hand_high, hand_low, smooth1_length=3, smooth1_weight=1,
                         smooth2_length=2, smooth2_weight=1)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))

    r = hand_high - hand_low
    print("r (H-L):", list(r))
    e = r.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()
    print("e (unmasked ewm):", list(r.ewm(alpha=1 / 3, adjust=False).mean()))
    print("e (masked, min_periods=3):", list(e))
    s = e.ewm(alpha=1 / 2, adjust=False, min_periods=2).mean()
    print("s (masked, min_periods=2):", list(s))
    print("e/s:", list(e / s))

    # Independent per-bar replay using plain numpy, not pandas' own
    # .rolling()/.ewm() calls, spot-checking the shipped defaults.
    big_high, big_low = _walk(900, seed=3)
    out_defaults = g191_109(big_high, big_low)
    h, l = big_high.to_numpy(dtype=float), big_low.to_numpy(dtype=float)
    nn = len(h)
    s1n, s1w, s2n, s2w = 10, 2, 10, 2
    a1, a2 = s1w / s1n, s2w / s2n

    r_np = h - l

    def _sma_loop(x, alpha, min_periods):
        y = None
        count = 0
        out_ = [float("nan")] * nn
        for t in range(nn):
            if x[t] != x[t]:
                continue
            y = x[t] if y is None else alpha * x[t] + (1 - alpha) * y
            count += 1
            if count >= min_periods:
                out_[t] = y
        return out_

    e_np = _sma_loop(r_np, a1, s1n)
    s_np = _sma_loop(np.array(e_np, dtype=float), a2, s2n)
    result_np = [float("nan")] * nn
    for t in range(nn):
        if s_np[t] == s_np[t] and e_np[t] == e_np[t]:
            result_np[t] = e_np[t] / s_np[t]
    for t in (300, 600, 899):
        diff = abs(float(out_defaults.iloc[t]) - result_np[t])
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={result_np[t]!r} diff={diff:.3e}")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    other_h, other_l = _walk(1500, seed=97)
    offsets = range(50, 1500, 40)

    def leaks(fn):
        base = fn(high, low)
        hits = 0
        for j in offsets:
            ph, pl = high.copy(), low.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pl.iloc[j:] = other_l.iloc[j:].values
            o = fn(ph, pl)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_109)} of {total}")
    write_shift = _load_mutant(
        "    result = (e / s).replace([np.inf, -np.inf], np.nan)",
        "    result = ((e / s).replace([np.inf, -np.inf], np.nan)).shift(-smooth2_length)",
    )
    print(f"write-shift mutant (smooth2_length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_109)} of {total}")
    lookahead_range = _load_mutant(
        "    e = _gtja_sma(high - low, smooth1_length, smooth1_weight)",
        "    e = _gtja_sma(high.shift(-1) - low.shift(-1), smooth1_length, smooth1_weight)",
    )
    print(f"look-ahead-range mutant leaks: "
          f"{leaks(lookahead_range.g191_109)} of {total}")


if __name__ == "__main__":
    main()
