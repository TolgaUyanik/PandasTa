# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191145Measured.md for
`pandas_ta.volume.g191_145`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import importlib.util
import types
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.volume.g191_145 import g191_145

_REAL = importlib.import_module("pandas_ta.volume.g191_145")

#: The issue's own prototype registry. `docs/issues/` is a read-only,
#: GITIGNORED copy of the owner's local tracker, so this file exists on the
#: owner's machine and in an issue-solver worktree but NOT in a clone. Every
#: comparison against it below degrades to the retyped copy when it is absent.
_SCREEN = Path(__file__).resolve().parent / "issues" / "screen" / "ind_screen.py"


def _screen_prototype(open_, high, low, close, volume):
    """Call the REAL `g191_145` candidate out of `ind_screen.py`, loaded by
    path, rather than a hand-retyped copy of it. Returns None when the
    gitignored screen is not present."""
    if not _SCREEN.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen_for_g191_145", _SCREEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.REG["g191_145"]["fn"](open_, high, low, close, volume)


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
    mod = types.ModuleType("_g191_145_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    volume = _volume()
    close = _walk()
    out = g191_145(volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    zero_volume_bars = int((volume == 0).sum())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid} zero_volume_bars={zero_volume_bars}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")
    interior_gap = int((out.isna().to_numpy()[first_valid:]).sum())
    print(f"interior NaN bars after the first fire={interior_gap}")

    # Gate D: volume rescaling. There is no price input to rescale.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_145(volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        bit = bool((out[m] == scaled[m]).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match} "
              f"bit-identical={bit}")

    # Gate A: the prototype. Two readings of it, so a transcription slip in
    # the retyped copy cannot pass unnoticed as agreement.
    #   (a) the REAL candidate, executed out of ind_screen.py itself;
    #   (b) a retyped copy of lines 494-495, which is all a clone can do.
    def sdiv(a, b):
        return (a / b).replace([np.inf, -np.inf], np.nan)

    def mean(x, nn):
        return x.rolling(nn).mean()

    retyped = 100 * sdiv(mean(volume, 9) - mean(volume, 26), mean(volume, 12))
    real_proto = _screen_prototype(close, close, close, close, volume)
    if real_proto is None:
        print(f"prototype file {_SCREEN} ABSENT (gitignored): "
              "only the retyped copy was compared")
    else:
        rb = out.notna() & real_proto.notna()
        print("prototype vs port (REAL ind_screen.py candidate): "
              f"mask-equal={bool((out.isna() == real_proto.isna()).all())} "
              f"n_both={int(rb.sum())} "
              f"max|diff|={float((out[rb] - real_proto[rb]).abs().max())} "
              f"bit-identical={bool((out[rb] == real_proto[rb]).all())}")
        rr = retyped.notna() & real_proto.notna()
        print("  retyped copy vs REAL candidate: "
              f"mask-equal={bool((retyped.isna() == real_proto.isna()).all())} "
              f"bit-identical={bool((retyped[rr] == real_proto[rr]).all())}")
    both = out.notna() & retyped.notna()
    print(f"prototype vs port (retyped copy): "
          f"mask-equal={bool((out.isna() == retyped.isna()).all())} "
          f"n_both={int(both.sum())} "
          f"max|diff|={float((out[both] - retyped[both]).abs().max())} "
          f"bit-identical={bool((out[both] == retyped[both]).all())}")

    # Gate A: the three possible association orders of `(A-B)/C*100`.
    fm = mean(volume, 9)
    sm = mean(volume, 26)
    nm = mean(volume, 12)
    order_shipped = 100.0 * ((fm - sm) / nm)          # the module's own order
    order_source = ((fm - sm) / nm) * 100.0           # the source string's order
    order_mul_first = (100.0 * (fm - sm)) / nm        # multiply before dividing
    bb = order_shipped.notna()
    print("association orders, bit-identical to the shipped one: "
          f"source-order={bool((order_shipped[bb] == order_source[bb]).all())} "
          f"multiply-first={bool((order_shipped[bb] == order_mul_first[bb]).all())} "
          f"max|diff| multiply-first="
          f"{float((order_shipped[bb] - order_mul_first[bb]).abs().max())}")

    # Gate A: hand-derived example at fast=2, slow=4, norm=3.
    hand_volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 10.0])
    hand_out = g191_145(hand_volume, fast=2, slow=4, norm=3)
    print("hand-derived bars 0..6:", list(hand_out))

    # Zero-denominator, case 1: the norm window is all-zero while the slow
    # window still carries volume, so the quotient is -inf before the
    # replace. fast=2, slow=4, norm=3.
    zv = Series([10.0, 20.0, 0.0, 0.0, 0.0])
    zv_out = g191_145(zv, fast=2, slow=4, norm=3)
    print("zero-norm-window bars 0..4:", list(zv_out))
    inf_mutant = _load_mutant(
        "    result = (100.0 * ((fast_mean - slow_mean) / norm_mean)).replace(\n"
        "        [np.inf, -np.inf], np.nan)",
        "    result = (100.0 * ((fast_mean - slow_mean) / norm_mean))",
    )
    raw = inf_mutant.g191_145(zv, fast=2, slow=4, norm=3)
    print("  with the inf->NaN replace deleted:", list(raw))

    # Zero-denominator, case 2: every window is all-zero, so it is 0/0 and
    # already NaN before the replace ever runs.
    allzero = Series([0.0, 0.0, 0.0, 0.0, 0.0])
    az_out = g191_145(allzero, fast=2, slow=4, norm=3)
    az_raw = inf_mutant.g191_145(allzero, fast=2, slow=4, norm=3)
    print("all-zero-volume bars 0..4:", list(az_out),
          "| with the replace deleted:", list(az_raw))

    # Zero-denominator, case 3: reachable ONLY when fast > norm, which the
    # shipped defaults (9 <= 12) exclude. fast=4, slow=6, norm=2: at bar 6
    # the norm window is all-zero while the fast mean (500) exceeds the
    # slow mean (333.33), so the numerator is POSITIVE and the quotient is
    # +inf rather than -inf.
    posinf = Series([0.0, 0.0, 0.0, 1000.0, 1000.0, 0.0, 0.0])
    pi_out = g191_145(posinf, fast=4, slow=6, norm=2)
    pi_raw = inf_mutant.g191_145(posinf, fast=4, slow=6, norm=2)
    print("fast>norm positive-numerator bars 0..6:", list(pi_out),
          "| with the replace deleted:", list(pi_raw))

    # A NaN volume propagates through min_periods into every window that
    # contains it: max(fast, slow, norm) = slow = 26 output bars.
    nan_volume = volume.copy()
    nan_volume.iloc[700] = np.nan
    nan_out = g191_145(nan_volume)
    blanked = [int(i) for i in nan_out.index[nan_out.isna() & out.notna()]]
    nan_both = out.notna() & nan_out.notna()
    newly_defined = int((nan_out.notna() & out.isna()).sum())
    print(f"nan-volume at 700: {len(blanked)} newly-NaN output bars, "
          f"{blanked[0]}..{blanked[-1]}; newly-DEFINED bars={newly_defined}; "
          f"still-defined bars n={int(nan_both.sum())} "
          f"max|diff|={float((out[nan_both] - nan_out[nan_both]).abs().max())} "
          f"bit-identical={bool((out[nan_both] == nan_out[nan_both]).all())}")

    # The "26 bars" figure is the INTERIOR case. Near either end the window
    # that would have been blanked runs off the frame, so fewer bars move.
    for t in (1495, 10):
        edge = volume.copy()
        edge.iloc[t] = np.nan
        edge_out = g191_145(edge)
        edge_blanked = [int(i) for i in edge_out.index[edge_out.isna() & out.notna()]]
        span = f"{edge_blanked[0]}..{edge_blanked[-1]}" if edge_blanked else "none"
        print(f"nan-volume at {t} (edge case): {len(edge_blanked)} newly-NaN "
              f"output bars, {span}")

    # Independent per-bar replay using plain numpy slicing, not pandas'
    # own .rolling() calls, at the shipped defaults.
    big_volume = _volume(900, seed=13)
    out_defaults = g191_145(big_volume)
    v = big_volume.to_numpy(dtype=float)
    for t in (300, 600, 899):
        fast_mean = v[t - 8:t + 1].sum() / 9.0
        slow_mean = v[t - 25:t + 1].sum() / 26.0
        norm_mean = v[t - 11:t + 1].sum() / 12.0
        expected = 100.0 * ((fast_mean - slow_mean) / norm_mean)
        got = float(out_defaults.iloc[t])
        print(f"independent-loop bar {t}: module={got!r} loop={expected!r} "
              f"bit-identical={got == expected} |diff|={abs(got - expected)}")

    # Non-redundancy against the nearest already-shipped column, pvo's
    # PVO_12_26_9 (same shape, EMA-built, self-normalised).
    from pandas_ta.momentum.pvo import pvo

    pvo_df = pvo(big_volume)
    pvo_col = pvo_df["PVO_12_26_9"]
    base = g191_145(big_volume)
    mm = base.notna() & pvo_col.notna()
    print(f"spearman(G191_145_9_26_12, PVO_12_26_9)="
          f"{float(base[mm].corr(pvo_col[mm], method='spearman')):.6f} "
          f"(n={int(mm.sum())})")
    # ... and against the same formula with an EMA denominator, to separate
    # "which average" from "which denominator".
    ema_denom = 100.0 * ((big_volume.ewm(span=9, adjust=False).mean()
                          - big_volume.ewm(span=26, adjust=False).mean())
                         / big_volume.ewm(span=12, adjust=False).mean())
    mm2 = base.notna() & ema_denom.notna()
    print(f"spearman(G191_145_9_26_12, same windows but EMA)="
          f"{float(base[mm2].corr(ema_denom[mm2], method='spearman')):.6f} "
          f"(n={int(mm2.sum())})")
    # ... and against pvo recomputed on this column's own windows, which
    # isolates the denominator choice alone (EMA 9/26 over EMA 26).
    pvo_9_26 = pvo(big_volume, fast=9, slow=26)["PVO_9_26_9"]
    mm3 = base.notna() & pvo_9_26.notna()
    print(f"spearman(G191_145_9_26_12, PVO_9_26_9)="
          f"{float(base[mm3].corr(pvo_9_26[mm3], method='spearman')):.6f} "
          f"(n={int(mm3.sum())})")

    # Gate B: future-perturbation leak counts, real module vs. one mutant.
    other_v = _volume(seed=59)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base_series = fn(volume)
        hits = 0
        for j in offsets:
            pv = volume.copy()
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(pv)
            a, b = base_series.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            msk = a.notna()
            if (a[msk] != b[msk]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_145)} of {total}")
    write_shift = _load_mutant(
        "    result = (100.0 * ((fast_mean - slow_mean) / norm_mean)).replace(\n"
        "        [np.inf, -np.inf], np.nan)",
        "    result = (100.0 * ((fast_mean - slow_mean) / norm_mean)).replace(\n"
        "        [np.inf, -np.inf], np.nan).shift(-slow)",
    )
    print(f"write-shift mutant (slow-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_145)} of {total}")

    # The price series is built but never read by this column; printed so
    # the "no price input" claim in Gate D is visible rather than implied.
    print(f"price frame built (n={len(close)}) and NOT passed to g191_145: "
          f"the function signature is "
          f"{list(g191_145.__code__.co_varnames[:g191_145.__code__.co_argcount])}")


if __name__ == "__main__":
    main()
