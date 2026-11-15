# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191165Measured.md for
`pandas_ta.statistics.g191_165`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.statistics.g191_165 import g191_165

_REAL = importlib.import_module("pandas_ta.statistics.g191_165")


def _cv(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    idx = pd.RangeIndex(n)
    return Series(close, index=idx)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_165_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _independent_rs(x, length):
    """Plain-python per-bar loop, NOT the module's vectorised sliding-window
    code: for each t, explicit window slice, explicit mean/cumsum/std."""
    n = len(x)
    out = [float("nan")] * n
    for t in range(length - 1, n):
        w = x[t - length + 1:t + 1]
        m = sum(w) / length
        dev = [v - m for v in w]
        z = []
        running = 0.0
        for d in dev:
            running += d
            z.append(running)
        rng = max(z) - min(z)
        var = sum((d - 0.0) ** 2 for d in dev) / (length - 1)
        s = var ** 0.5
        out[t] = float("nan") if s == 0 else rng / s
    return out


def main():
    import inspect

    import pandas_ta as ta
    from pandas_ta.core import AnalysisIndicators

    NOT_INDICATORS = {
        "above", "above_value", "below", "below_value", "cross", "cross_value",
        "constants", "indicators", "strategy", "ticker",
    }
    total = sum(len(v) for v in ta.Category.values())
    accessors = {n for n, v in vars(AnalysisIndicators).items()
                 if not n.startswith("_") and inspect.isfunction(v)} - NOT_INDICATORS
    print(f"Category total={total} statistics={len(ta.Category['statistics'])} "
          f"accessors={len(accessors)}")

    close = _cv()
    out = g191_165(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_165(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, length=4, 7 bars.
    hc = Series([1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0])
    hout = g191_165(hc, length=4)
    print("hand result:", list(hout))

    indep = _independent_rs(list(hc), 4)
    print("independent loop:", indep)
    for t in range(len(hc)):
        a, b = hout.iloc[t], indep[t]
        if pd.isna(a) and pd.isna(b):
            continue
        assert abs(a - b) < 1e-9, (t, a, b)
    print("hand-derived matches independent loop: OK")

    # Gate A: spot-check the shipped default (length=48) against the same
    # independent loop, on a bigger frame.
    big = _cv(900, seed=5)
    out_big = g191_165(big)
    indep_big = _independent_rs(list(big), 48)
    for t in (300, 600, 899):
        a, b = out_big.iloc[t], indep_big[t]
        rel = abs(a - b) / abs(b)
        print(f"t={t} module={a!r} independent={b!r} rel_diff={rel:.3e}")
        assert rel < 1e-9

    # ddof sensitivity: report the size of the ddof=1 vs ddof=0 choice at the
    # shipped default, on the same frame.
    a_arr = big.to_numpy(dtype=float)
    from numpy.lib.stride_tricks import sliding_window_view
    W = sliding_window_view(a_arr, 48)
    dev = W - W.mean(axis=1, keepdims=True)
    z = np.cumsum(dev, axis=1)
    rng = z.max(axis=1) - z.min(axis=1)
    std1 = W.std(axis=1, ddof=1)
    std0 = W.std(axis=1, ddof=0)
    rs1 = rng / std1
    rs0 = rng / std0
    ratio = rs1 / rs0
    print(f"ddof=1 vs ddof=0 ratio: mean={ratio.mean():.6f} "
          f"(expected sqrt(47/48)={(47 / 48) ** 0.5:.6f})")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    close = _cv(1500)
    other_c = _cv(1500, seed=97)
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
    print(f"real-module leaks: {leaks(g191_165)} of {total}")
    shipped = _load_mutant(
        "result = pd.Series(out, index=close.index)",
        "result = pd.Series(out, index=close.index).shift(-length)",
    )
    print(f"shipped mutant (length-bar write shift) leaks: "
          f"{leaks(shipped.g191_165)} of {total}")
    weaker = _load_mutant(
        "out[length - 1:] = rs",
        "out[(length - 1) // 2:(length - 1) // 2 + len(rs)] = rs",
    )
    print(f"weaker mutant (center-write) leaks: {leaks(weaker.g191_165)} of {total}")


if __name__ == "__main__":
    main()
