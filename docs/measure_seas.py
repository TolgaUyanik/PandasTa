# -*- coding: utf-8 -*-
"""Measurement script for `pandas_ta.performance.seas` (issue #27, SEAS).

Gate C (reachability) and Gate D (scale-free) numbers on synthetic data, run
on this machine and quoted verbatim in `docs/SeasMeasured.md` and
`tests/test_seas.py`. No real-data (BIST) frame is available in this
worktree; Gate E (real-data attribution) and the real-data half of Gate C
are owed to the launcher's run per the issue's Gate E instructions.

Run: `python docs/measure_seas.py`
"""
import numpy as np
from pandas import Series

from pandas_ta.performance.percent_return import percent_return
from pandas_ta.performance.seas import seas

YEAR = 252


def _walk(n=1200, seed=11, sigma=0.015, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def main():
    close = _walk()
    out = seas(close)
    fires = out.dropna()
    print("Gate C (seed=11, n=1200, length=21, years=1, no tick rounding):")
    print(f"  non-NaN bars: {len(fires)} of {len(close)}")
    print(f"  nonzero bars: {int((fires != 0).sum())}")
    print(f"  positive / negative / zero: {int((fires > 0).sum())} / "
          f"{int((fires < 0).sum())} / {int((fires == 0).sum())}")
    print(f"  distinct values: {out.nunique()}")
    print(f"  min / max: {fires.min():.6f} / {fires.max():.6f}")

    close_tick = _walk(tick=0.05)
    out_tick = seas(close_tick)
    fires_tick = out_tick.dropna()
    print("\nGate C (same walk, tick=0.05):")
    print(f"  non-NaN bars: {len(fires_tick)} of {len(close_tick)}")
    print(f"  nonzero bars: {int((fires_tick != 0).sum())}")
    print(f"  positive / negative / zero: {int((fires_tick > 0).sum())} / "
          f"{int((fires_tick < 0).sum())} / {int((fires_tick == 0).sum())}")

    print("\nGate D (scale-free, tick=0.05 walk):")
    base = out_tick
    for k in (8.0, 64.0):
        scaled = seas(close_tick * k)
        same_nan = bool((base.isna() == scaled.isna()).all())
        m = base.notna()
        bit_eq = bool((base[m] == scaled[m]).all())
        print(f"  x{k}: nan masks match={same_nan}, bit-identical={bit_eq}")
    for k in (10.0, 3.7):
        scaled = seas(close_tick * k)
        same_nan = bool((base.isna() == scaled.isna()).all())
        diff = float((base - scaled).abs().max())
        print(f"  x{k}: nan masks match={same_nan}, max abs diff={diff:.3e}")

    print("\nProxy overlap (NOT Gate E) -- the issue's own flagged engine"
          " overlap candidate, `Ret_252d_pct` (the cumulative 12-month"
          " return == percent_return(close, 252)), plus the unlagged"
          " same-length return, on the seed=11 walk, no tick rounding:")
    sv = seas(close).dropna()
    ret252 = percent_return(close, length=YEAR).reindex(sv.index)
    ret21 = percent_return(close, length=21).reindex(sv.index)
    for name, comp in (("percent_return(252) ~ Ret_252d_pct", ret252),
                       ("percent_return(21), unlagged", ret21)):
        both = sv.to_frame("seas").join(comp.rename("comp")).dropna()
        rho = both["seas"].corr(both["comp"], method="spearman")
        print(f"  {name}: rho={rho:.4f}, n={len(both)}")

    print("\nGate A sanity -- hand-computed (length=21, years=1):")
    hand = Series([1.0] * 253)
    hand[0] = 100.0
    hand[21] = 110.0
    print(f"  close[0]=100, close[21]=110, rest 1.0 -> bar 252 = "
          f"{seas(hand, length=21, years=1).iloc[252]:.6f} (expect 0.10)")


if __name__ == "__main__":
    main()
