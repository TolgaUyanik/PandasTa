# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191040Measured.md for
`pandas_ta.volume.g191_040`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.volume.g191_040 import g191_040

_REAL = importlib.import_module("pandas_ta.volume.g191_040")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _volume(n=1500, seed=97, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_040_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    volume = _volume()
    out = g191_040(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_040(close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_040(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 9-bar example at length=3 (includes a flat-day
    # boundary bar, which lands in the down-bucket per the issue's own
    # C<=C1 string).
    hand_close = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0, 110.0, 100.0, 120.0])
    hand_volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0])
    hand_out = g191_040(hand_close, hand_volume, length=3)
    print("hand-derived bars 0..8:", list(hand_out.iloc[0:9]))
    delta = hand_close.diff()
    print("delta:", list(delta))

    # Gate A (disclosed interpretation): the prototype's own `v.where(~up,
    # 0.0)` down-bucket silently counts bar 0 as DOWN; this port makes bar
    # 0 NaN in both buckets instead.
    up = hand_close > hand_close.shift(1)
    prototype_down_volume_bar0 = hand_volume.where(~up, 0.0).iloc[0]
    print(f"prototype down-bucket bar0 (buggy, counts as DOWN)="
          f"{prototype_down_volume_bar0}")
    # Read off the OUTPUT of the shipped function, never off a re-typed
    # copy of its buckets: at length=3 the window at bar 2 is the first
    # full window and it touches bar 0. Three readings, all different.
    proto_up3 = hand_volume.where(up, 0.0).rolling(3).sum()
    proto_down3 = hand_volume.where(~up, 0.0).rolling(3).sum()
    proto3 = 100 * proto_up3 / proto_down3
    mask_removed = _load_mutant(
        "    up_volume = volume.where(close > close_prior, 0.0).mask(undefined, np.nan)\n"
        "    down_volume = volume.where(close <= close_prior, 0.0).mask(undefined, np.nan)",
        "    up_volume = volume.where(close > close_prior, 0.0)\n"
        "    down_volume = volume.where(close <= close_prior, 0.0)",
    )
    print(f"bar2 (window touches bar 0): prototype={proto3.iloc[2]!r} "
          f"mask-removal-mutant={mask_removed.g191_040(hand_close, hand_volume, length=3).iloc[2]!r} "
          f"shipped={hand_out.iloc[2]!r}")

    # Zero-down-volume, first cause: a length-bar all-up window zeroes the
    # denominator. The 1,500-bar frame above does not reach it -- fires =
    # n - 26 with no interior gap, longest up-run 16 against the 26 needed
    # (both printed below) -- so the branch is exercised on this dedicated
    # fixture instead. How often it occurs on real data is not measured
    # here; that is Gate E's.
    allup_close = Series([100.0, 105.0, 110.0, 115.0, 120.0])
    allup_volume = Series([10.0, 20.0, 30.0, 40.0, 50.0])
    allup_out = g191_040(allup_close, allup_volume, length=3)
    print("all-up-window bars 0..4:", list(allup_out.iloc[0:5]))

    # Zero-down-volume, second cause: the window DOES contain a non-up bar,
    # but that bar carries zero volume, so the down-bucket sum is still
    # exactly zero. (A halted / zero-turnover session prints a flat close,
    # which `C<=C1` puts in the down bucket.)
    zerovol_close = Series([100.0, 101.0, 100.0, 101.0, 102.0])
    zerovol_volume = Series([10.0, 20.0, 0.0, 30.0, 40.0])
    zerovol_out = g191_040(zerovol_close, zerovol_volume, length=3)
    print("zero-volume-down-bar bars 0..4:", list(zerovol_out.iloc[0:5]))

    # A NaN close for t > 0: both comparisons are False there, so without
    # the `close.isna()` half of the mask the bar's volume would vanish from
    # BOTH buckets while its windows kept firing.
    nan_close = close.copy()
    nan_close.iloc[700] = np.nan
    nan_out = g191_040(nan_close, volume)
    blanked = [int(i) for i in nan_out.index[nan_out.isna() & out.notna()]]
    # 27 bars, not 26: the NaN close leaves bar 700's OWN direction
    # undefined and bar 701's too (its C1 is that NaN), so every window
    # reading either one is blank.
    nan_both = out.notna() & nan_out.notna()
    nan_max_diff = float((out[nan_both] - nan_out[nan_both]).abs().max())
    newly_defined = int((nan_out.notna() & out.isna()).sum())
    print(f"nan-close at 700: {len(blanked)} newly-NaN output bars, "
          f"{blanked[0]}..{blanked[-1]} (expected 700..726); "
          f"newly-DEFINED bars={newly_defined}; still-defined bars "
          f"n={int(nan_both.sum())} max|diff|={nan_max_diff} "
          f"bit-identical={bool((out[nan_both] == nan_out[nan_both]).all())}")

    # Gate A (disclosed interpretation, full-series): how far the port's
    # output actually departs from the prototype's own expression on a real
    # frame, rather than at bar 0 alone.
    proto_up = volume.where(close > close.shift(1), 0.0)
    proto_down = volume.where(~(close > close.shift(1)), 0.0)
    proto = 100 * proto_up.rolling(26).sum() / proto_down.rolling(26).sum()
    proto = proto.replace([np.inf, -np.inf], np.nan)
    disagree = [int(i) for i in out.index[(out.isna() != proto.isna())]]
    both = out.notna() & proto.notna()
    print(f"prototype vs port: disagreeing indices={disagree} "
          f"max|diff| where both defined={float((out[both] - proto[both]).abs().max())}")

    # Zero-down-volume reachability on the 1,500-bar frame: the longest run
    # of consecutive up-days, against the 26 a rally would need.
    is_up = (close > close.shift(1)).to_numpy()
    longest = run = 0
    for flag in is_up[1:]:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    print(f"longest consecutive up-run on the 1500-bar frame={longest} "
          f"(needs {26} to zero the down bucket)")

    # Non-redundancy against the nearest already-shipped sibling, g191_043
    # (same two buckets): rank-identical at equal length when no bar is
    # flat, which is the case on this continuous-float frame.
    from pandas_ta.volume.g191_043 import g191_043

    flat_bars = int((close == close.shift(1)).sum())
    for n in (26, 6):
        sib = g191_043(close, volume, length=n)
        mm = out.notna() & sib.notna()
        rho = float(out[mm].corr(sib[mm], method="spearman"))
        print(f"spearman(G191_040_26, G191_043_{n})={rho:.6f} "
              f"(n={int(mm.sum())} overlapping bars, flat bars on frame={flat_bars})")

    # Independent per-bar replay using plain numpy array slicing, not
    # pandas' own .rolling() calls, spot-checking the shipped defaults
    # (length=26).
    big_close = _walk(900, seed=5)
    big_volume = _volume(900, seed=13)
    out_defaults = g191_040(big_close, big_volume)
    c = big_close.to_numpy(dtype=float)
    v = big_volume.to_numpy(dtype=float)
    length = 26
    for t in (300, 600, 899):
        up_sum = 0.0
        down_sum = 0.0
        for i in range(t - length + 1, t + 1):
            if c[i] > c[i - 1]:
                up_sum += v[i]
            else:
                down_sum += v[i]
        expected = 100 * up_sum / down_sum
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={expected!r}")

    # Gate B: future-perturbation leak counts, real module vs. one mutant.
    other_c = _walk(seed=41)
    other_v = _volume(seed=59)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(close, volume)
        hits = 0
        for j in offsets:
            pc, pv = close.copy(), volume.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_040)} of {total}")
    write_shift = _load_mutant(
        "result = (100 * numerator / denominator).replace([np.inf, -np.inf], np.nan)",
        "result = (100 * numerator / denominator).replace([np.inf, -np.inf], np.nan).shift(-length)",
    )
    print(f"write-shift mutant (length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_040)} of {total}")


if __name__ == "__main__":
    main()
