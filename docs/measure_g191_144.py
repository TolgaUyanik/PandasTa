# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191144Measured.md for
`pandas_ta.volume.g191_144`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.volume.g191_144 import g191_144

_REAL = importlib.import_module("pandas_ta.volume.g191_144")


def _ohlcv(n=1500, seed=11, sigma=0.015, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(close, index=idx), Series(volume, index=idx))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_144_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, low, close, volume = _ohlcv()
    out = g191_144(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_144(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_144(high, low, close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} VOLUME max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_144(high * k, low * k, close * k, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} BOTH max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, length=3.
    # high = close+1, low = close-1 so tp == close exactly.
    hc = Series([10.0, 20.0, 30.0, 40.0, 22.0, 5.0])
    hh = hc + 1.0
    hl = hc - 1.0
    hv = Series([100.0, 200.0, 150.0, 300.0, 250.0, 400.0])
    hout = g191_144(hh, hl, hc, hv, length=3)
    tp = (hh + hl + hc) / 3.0
    amount = tp * hv
    prior_close = hc.shift(1)
    ret_abs = (hc / prior_close - 1.0).abs()
    x = ret_abs / amount
    down = hc < prior_close
    print("hand tp:", list(tp))
    print("hand amount:", list(amount))
    print("hand ret_abs:", list(ret_abs))
    print("hand x:", list(x))
    print("hand down:", list(down))
    print("hand result:", list(hout))

    # Gate A: spot-check the shipped default against an independent
    # per-bar computation using plain numpy, not pandas' own rolling ops.
    big_h, big_l, big_c, big_v = _ohlcv(900, seed=5, vol_seed=71)
    out_big = g191_144(big_h, big_l, big_c, big_v)
    h = big_h.to_numpy(dtype=float)
    l = big_l.to_numpy(dtype=float)
    c = big_c.to_numpy(dtype=float)
    v = big_v.to_numpy(dtype=float)
    tp_arr = (h + l + c) / 3.0
    amount_arr = tp_arr * v
    length = 20

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)  # all >= 1 since t >= length
        xi = np.abs(c[idx] / c[idx - 1] - 1.0) / amount_arr[idx]
        downi = c[idx] < c[idx - 1]
        sumif = np.sum(np.where(downi, xi, 0.0))
        count = np.sum(downi.astype(float))
        down_avg = sumif / count
        all_avg = np.mean(xi)
        return down_avg / all_avg

    for t in (300, 600, 899):
        a, b = out_big.iloc[t], expected_at(t)
        rel = abs(a - b) / abs(b)
        print(f"t={t} module={a!r} independent={b!r} rel_diff={rel:.3e}")
        assert rel < 1e-9

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    high, low, close, volume = _ohlcv(1500)
    other_h, other_l, other_c, other_v = _ohlcv(1500, seed=97, vol_seed=71)
    offsets = range(150, 1500, 40)

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
    print(f"real-module leaks: {leaks(g191_144)} of {total}")
    shipped = _load_mutant(
        "result = (down_avg / all_avg).replace([np.inf, -np.inf], np.nan)",
        "result = (down_avg / all_avg).replace([np.inf, -np.inf], np.nan).shift(-length)",
    )
    print(f"shipped mutant (length-bar write shift) leaks: "
          f"{leaks(shipped.g191_144)} of {total}")
    weaker = _load_mutant(
        "prior_close = close.shift(1)",
        "prior_close = close.shift(-1)",
    )
    print(f"weaker mutant (forward DELAY / C1) leaks: {leaks(weaker.g191_144)} of {total}")


if __name__ == "__main__":
    main()
