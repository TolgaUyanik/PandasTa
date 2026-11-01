# -*- coding: utf-8 -*-
"""Measurement script for `pandas_ta.statistics.ie_asym` (issue #28, IEASYM).

Gate C (reachability) and Gate D (scale-free) numbers on synthetic data, run
on this machine and quoted verbatim in `docs/IeAsymMeasured.md` and
`tests/test_ie_asym.py`. No real-data (BIST) frame is available in this
worktree; Gate E (real-data attribution) and the real-data half of Gate C
are owed to the launcher's run per the issue's Gate E instructions.

Run: `python docs/measure_ie_asym.py`
"""
import numpy as np
from pandas import Series

from pandas_ta.performance.max_return import max_return
from pandas_ta.statistics.ie_asym import ie_asym
from pandas_ta.statistics.skew import skew
from pandas_ta.volatility.natr import natr


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def main():
    close = _walk()
    out = ie_asym(close)
    fires = out.dropna()
    print(f"Gate C (seed=11, n=1200, length=260, no tick rounding):")
    print(f"  non-NaN bars: {len(fires)} of {len(close)}")
    print(f"  nonzero bars: {int((fires != 0).sum())}")
    print(f"  positive / negative / zero: {int((fires > 0).sum())} / "
          f"{int((fires < 0).sum())} / {int((fires == 0).sum())}")
    print(f"  distinct values: {out.nunique()}")
    print(f"  min / max: {fires.min():.6f} / {fires.max():.6f}")

    close_tick = _walk(tick=0.05)
    out_tick = ie_asym(close_tick)
    fires_tick = out_tick.dropna()
    print(f"\nGate C (same walk, tick=0.05):")
    print(f"  non-NaN bars: {len(fires_tick)} of {len(close_tick)}")
    print(f"  nonzero bars: {int((fires_tick != 0).sum())}")
    print(f"  positive / negative / zero: {int((fires_tick > 0).sum())} / "
          f"{int((fires_tick < 0).sum())} / {int((fires_tick == 0).sum())}")

    print("\nGate D (scale-free, tick=0.05 walk):")
    base = out_tick
    for k in (8.0, 64.0):
        scaled = ie_asym(close_tick * k)
        same_nan = bool((base.isna() == scaled.isna()).all())
        m = base.notna()
        bit_eq = bool((base[m] == scaled[m]).all())
        print(f"  x{k}: nan masks match={same_nan}, bit-identical={bit_eq}")
    for k in (10.0, 3.7):
        scaled = ie_asym(close_tick * k)
        same_nan = bool((base.isna() == scaled.isna()).all())
        diff = float((base - scaled).abs().max())
        print(f"  x{k}: nan masks match={same_nan}, max abs diff={diff:.3e}")

    print("\nProxy overlap (NOT Gate E) -- the issue's own guessed comparators,"
          " on the seed=11 walk, no tick rounding:")
    ie = ie_asym(close).dropna()
    skw = skew(close).reindex(ie.index)
    mret = max_return(close).reindex(ie.index)
    high, low = close * 1.001, close * 0.999
    ntr = natr(high, low, close).reindex(ie.index)
    for name, comp in (("skew (SKEW_30)", skw), ("max_return (MAXRET_21)", mret),
                       ("natr (NATR_14)", ntr)):
        both = ie.to_frame("ie").join(comp.rename("comp")).dropna()
        rho = both["ie"].corr(both["comp"], method="spearman")
        print(f"  {name}: rho={rho:.4f}, n={len(both)}")

    print("\nGate A sanity -- hand-computed window (length=10, mult=2.0):")
    hand_up = Series([1.0] * 10 + [1.0 * np.exp(10.0)])
    print(f"  9 zero returns + one +10 return -> {ie_asym(hand_up, length=10).iloc[10]:.6f}"
          " (expect 0.1)")
    hand_down = Series([1.0] * 10 + [1.0 * np.exp(-10.0)])
    print(f"  9 zero returns + one -10 return -> {ie_asym(hand_down, length=10).iloc[10]:.6f}"
          " (expect -0.1)")


if __name__ == "__main__":
    main()
