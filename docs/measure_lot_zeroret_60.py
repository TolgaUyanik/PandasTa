# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/LotZeroret60Measured.md for
`pandas_ta.statistics.lot_zeroret_60`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.statistics.lot_zeroret_60 import lot_zeroret_60


def _walk(n=1600, seed=11, zero_at=()):
    rng = np.random.default_rng(seed)
    close = Series(100 + np.cumsum(rng.normal(0, 1, n)))
    for i in zero_at:
        close.iloc[i] = close.iloc[i - 1]
    return close


def main():
    # A handful of forced exact-tie bars so zero returns actually fire.
    close = _walk(zero_at=[80, 81, 200, 500, 500 + 1, 1400])
    out = lot_zeroret_60(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"first_valid_index={out.first_valid_index()}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"nonzero_count={int((out > 0).sum())}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = lot_zeroret_60(close * k)
        mask_match = bool((out.isna() == scaled.isna()).all())
        bit_identical = bool((out[m] == scaled[m]).all())
        max_diff = float((out[m] - scaled[m]).abs().max())
        print(f"x{k} close bit-identical={bit_identical} max|diff|={max_diff} "
              f"nan-mask-match={mask_match}")

    # Gate B: future-perturbation leak count, real module vs. a mutant whose
    # rolling window is centered (reads into the future) -- see
    # tests/test_lot_zeroret_60.py for the exec'd mutant. Zero-return days
    # are rare on a plain random walk, so a sparse series makes most
    # perturbed windows carry zero ties in both arms by luck, not by
    # causality -- too weak a check. `_ticky` forces a tie every 4th bar so
    # virtually every 60-bar window actually contains ties whose count can
    # change; `_tickless` (used as the perturbation's replacement tail) has
    # none, so splicing it in changes the tie count inside any window that
    # reads into the spliced region.
    def _ticky(n, seed, period=4):
        rng = np.random.default_rng(seed)
        steps = np.abs(rng.normal(0, 1, n)) + 0.01
        close = np.empty(n)
        close[0] = 100.0
        for i in range(1, n):
            close[i] = close[i - 1] if i % period == 0 else close[i - 1] + steps[i]
        return Series(close)

    def _tickless(n, seed):
        rng = np.random.default_rng(seed)
        steps = np.abs(rng.normal(0, 1, n)) + 0.01
        return Series(100.0 + np.cumsum(steps))

    base_close = _ticky(1600, seed=5)
    other = _tickless(1600, seed=99)
    offsets = range(100, 1500, 50)

    def leaks(fn):
        base = fn(base_close)
        hits = 0
        for j in offsets:
            pc = base_close.copy()
            pc.iloc[j:] = other.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    def mutant(c):
        length = 60
        r = c.pct_change(fill_method=None)
        zero = (r == 0).astype(float)
        counts = zero.rolling(length, min_periods=length, center=True).sum()
        result = counts / length
        return result.where(r.shift(length - 1).notna())

    print(f"real-module leaks: {leaks(lot_zeroret_60)} of {len(offsets)}")
    print(f"mutant leaks: {leaks(mutant)} of {len(offsets)}")


if __name__ == "__main__":
    main()
