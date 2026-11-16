# -*- coding: utf-8 -*-
"""Scratch measurement for Gates B, C and D of `bos_causal` (issue #332). Not a
test; run once to produce the numbers quoted in `docs/BosCausalMeasured.md`.

    python docs/measure_bos_causal.py

Synthetic, tick-rounded frames only. This is NOT Gate E.
"""
import numpy as np
from pandas import DataFrame, concat

import pandas_ta as ta
from pandas_ta.trend.bos_causal import bos_causal

N_FRAMES, N_BARS = 16, 2000


def frame(f, n=N_BARS):
    rng = np.random.default_rng(332 + f)
    tick = [0.01, 0.05, 0.1, 0.25][f % 4]
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.012 + 0.004 * (f % 3), n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, .006, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, .006, n)))
    r = lambda x: np.round(x / tick) * tick
    return DataFrame(dict(high=r(h), low=r(l), close=r(c)))


def reach(fn, df, length, cols, probes=40):
    """Max number of bars a column at bar T reads ahead: smallest d such that rewriting
    bars > T + d never moves bar T. Reported as the largest d that DID move bar T."""
    base = fn(df.high, df.low, df.close, swing_length=length)[cols]
    worst = 0
    rng = np.random.default_rng(1)
    for T in rng.integers(50, len(df) - 60, probes):
        for d in range(0, 8):
            q = df.copy()
            s = slice(T + d + 1, None)
            q.iloc[s, :] = q.iloc[s, :].to_numpy()[::-1] * 1.3
            q["high"] = np.maximum(q.high, np.maximum(q.low, q.close))
            q["low"] = np.minimum(q.low, np.minimum(q.high, q.close))
            alt = fn(q.high, q.low, q.close, swing_length=length)[cols]
            if not base.iloc[:T + 1].equals(alt.iloc[:T + 1]):
                worst = max(worst, d + 1)
    return worst


def overlap(frames, outs):
    """Per-frame median Spearman vs the shipped centred columns, and the rising edge of
    BOSC_BULL/BEAR vs SWINGEQ_BOS_* (left=right=2, the same k and the same tie rule at L=5)."""
    from scipy.stats import spearmanr
    pairs = [("BOSC_BULL_5", "BOS_BULL"), ("BOSC_BEAR_5", "BOS_BEAR"), ("BOSC_HH_5", "HIGHER_HIGH"),
             ("BOSC_LL_5", "LOWER_LOW"), ("BOSC_CHOCH_BULL_5", "CHoCH_BULL"), ("BOSC_CHOCH_BEAR_5", "CHoCH_BEAR")]
    cur = [concat([ta.bos(d.high, d.low, d.close), ta.choch(d.high, d.low, d.close)], axis=1) for d in frames]
    for new, old in pairs:
        r = [spearmanr(o[new], c[old])[0] for o, c in zip(outs, cur)]
        print(f"median per-frame Spearman {new} vs {old}: {np.median(r):.4f}")
    for new, sw in (("BOSC_BULL_5", "SWINGEQ_BOS_BULL_2_2"), ("BOSC_BEAR_5", "SWINGEQ_BOS_BEAR_2_2")):
        mism = 0
        for d, o in zip(frames, outs):
            s = o[new].to_numpy()
            edge = ((s == 1) & (np.r_[0, s[:-1]] == 0)).astype(float)
            mism += int((edge != ta.swing_equilibrium(d.high, d.low, d.close, left=2, right=2)[sw].fillna(0).to_numpy()).sum())
        print(f"rising edge of {new} vs {sw}: {mism} mismatching bars over {len(frames)} frames")


def main():
    frames = [frame(f) for f in range(N_FRAMES)]
    outs = [bos_causal(d.high, d.low, d.close) for d in frames]
    allc = concat(outs)
    print("frames", N_FRAMES, "bars", len(allc), "columns", list(allc.columns))
    for c in allc.columns:
        print(f"  {c:22s} fires {int(allc[c].sum()):6d} / {len(allc)}  ({100 * allc[c].mean():.2f}%)"
              f"  frames firing {sum(int(o[c].sum() > 0) for o in outs)}/{N_FRAMES}")
    tie = sum(int((d.high.diff() == 0).sum() + (d.low.diff() == 0).sum()) for d in frames)
    print("tie bars (high or low == previous):", tie)

    for k in (8.0, 64.0):
        ok = all(bos_causal(d.high * k, d.low * k, d.close * k).equals(o) for d, o in zip(frames, outs))
        print(f"x{k:g} bit identical on all frames:", ok)
    for k in (10.0, 3.7):
        mism = sum(int((bos_causal(d.high * k, d.low * k, d.close * k).to_numpy() != o.to_numpy()).sum())
                   for d, o in zip(frames, outs))
        print(f"x{k:g} mismatching cells:", mism)

    overlap(frames, outs)

    d = frames[0]
    for L in (4, 5, 7, 9):
        print(f"L={L}: bos_causal reach {reach(bos_causal, d, L, list(bos_causal(d.high, d.low, d.close, swing_length=L).columns))}"
              f"  bos reach {reach(ta.bos, d, L, ['BOS_BULL', 'BOS_BEAR', 'HIGHER_HIGH', 'LOWER_LOW'])}"
              f"  choch reach {reach(ta.choch, d, L, ['CHoCH_BULL', 'CHoCH_BEAR'])}")


if __name__ == "__main__":
    main()
