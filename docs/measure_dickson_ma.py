# -*- coding: utf-8 -*-
"""Print the measured numbers in docs/DicksonMaMeasured.md (the doc marks the
exceptions): warm-up, head transient, Gate A against the literal EasyLanguage
transcription, where the gain search lands, scale tolerance, Gate C
(synthetic) and a proxy overlap.

    python docs/measure_dickson_ma.py

Synthetic GBM walks with fixed seeds -- a PROXY, not Gate E, which runs on the
89 ALTPORT-1 BIST frames in the parent repo. The Gate A oracle is imported from
tests/test_dickson_ma.py so the script and the test check the same thing.
"""
import sys
import timeit
import types
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import pandas_ta as ta
from tests.test_dickson_ma import (FILLS, MASK_MUTANT, MUTANTS, OFFSETS, _leaks, _load_mutant,
                                   literal_dist, literal_ec, literal_hma)
dm = sys.modules["pandas_ta.overlap.dickson_ma"]  # `import ... as` binds the function, not the module

SCREEN = ROOT / "docs" / "issues" / "screen"  # owner's machine only (gitignored)


def walk(n=3000, sigma=0.02, seed=1, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def variant(old, new):
    """The module with one source edit, exec'd in memory (as the tests do)."""
    src = open(dm.__file__, encoding="utf-8").read()
    assert src.count(old) == 1
    mod = types.ModuleType("_dma_variant")
    exec(compile(src.replace(old, new), dm.__file__, "exec"), mod.__dict__)
    return mod.dickson_ma


def comparators(c):
    out = {f"close/EMA_{n} - 1": 100 * (c / ta.ema(c, n) - 1) for n in (5, 10, 20, 30)}
    out.update({f"close/HMA_{n} - 1": 100 * (c / ta.hma(c, n) - 1) for n in (7, 10, 20)})
    out.update({
        "close/EC_30 - 1": 100 * (c / pd.Series(dm._ec(c.to_numpy(), 30), index=c.index) - 1),
        "BIAS_SMA_26": ta.bias(c), "ROC_1": ta.roc(c, 1), "ROC_5": ta.roc(c, 5),
        "ROC_10": ta.roc(c, 10), "PPO_12_26_9": ta.ppo(c).iloc[:, 0], "CMO_14": ta.cmo(c),
        "RSI_14": ta.rsi(c), "PFE_10_5": ta.pfe(c), "KFT_DIST": ta.kalman_trend(c).iloc[:, 0],
    })
    return out


def head_worst(length):
    worst = 0.0
    for seed in range(10):
        for s_ in (0.005, 0.02, 0.05):
            c = walk(1500, sigma=s_, seed=seed)
            full = ta.dickson_ma(c, length)
            for s in (100, 500, 900):
                part = ta.dickson_ma(c.iloc[s:], length)
                i = part.first_valid_index()
                worst = max(worst, (part.loc[i:] - full.loc[i:]).abs().max())
    return worst


def main():
    print(f"numpy {np.__version__}, pandas {pd.__version__}, python {sys.version.split()[0]}")

    print("== warm-up (valid closes) and head worst |diff|, start-at-s vs start-at-0, 90 runs per length")
    for n in (30, 10, 50):
        print(f"  length {n}: warm-up {dm._warmup(n)}  head worst {head_worst(n):.1e}")

    print("== transient at length 30 (unmasked, start-at-s vs start-at-0, same 90 runs, from the first HMA bar)")
    unmasked = variant("dist.iloc[:valid[warmup]]", "dist.iloc[:valid[0]]")
    worst = np.zeros(400)
    for seed in range(10):
        for s_ in (0.005, 0.02, 0.05):
            c = walk(1500, sigma=s_, seed=seed)
            full = unmasked(c).to_numpy()
            for s in (100, 500, 900):
                part = unmasked(c.iloc[s:]).to_numpy()
                worst = np.maximum(worst, np.abs(part[7:407] - full[s + 7:s + 407]))
    tail_max = np.maximum.accumulate(worst[::-1])[::-1]
    a1 = 29 / 31
    for tol in (1e-3, 1e-6):
        print(f"  worst at bar 7 (first HMA bar) {worst[0]:.3f}; first bar (from bar 7) after which it stays"
              f" < {tol:.0e}: {int(np.argmax(tail_max < tol))}; predicted ceil(ln({tol:.0e}/{worst[0]:.3f})"
              f" / ln(29/31)): {int(np.ceil(np.log(tol / worst[0]) / np.log(a1)))}")
    half = variant("dist.iloc[:valid[warmup]]", "dist.iloc[:valid[warmup // 2]]")
    c = walk(1500, seed=3)
    i = 500 + dm._warmup(30) // 2
    print(f"  half warm-up (seed 3, s=500, bar {i}): |diff| {abs(half(c.iloc[500:]).loc[i] - ta.dickson_ma(c).loc[i]):.1e}")

    print("== Gate A: module vs the literal EasyLanguage transcription")
    for n in (10, 30, 50):
        same = total = 0
        for seed, s_ in ((1, 0.005), (2, 0.02), (3, 0.05)):
            x = walk(900, sigma=s_, seed=seed).to_numpy()
            x[600] = np.nan
            got, ref = dm._ec(x, n), literal_ec(x, n)[0]
            ok = np.isfinite(ref)
            same += int((got[ok] == ref[ok]).sum())
            total += int(ok.sum())
        print(f"  EC length {n}: bit-identical {same} / {total} bars")
    for n, h in ((30, 7), (10, 4), (50, 16)):
        c = walk(1200, seed=11)
        c.iloc[700] = np.nan
        got, ref = ta.dickson_ma(c, n, h).to_numpy(), literal_dist(c, n, h)
        print(f"  DIST ({n}, {h}): NaN masks equal {bool((np.isnan(got) == np.isnan(ref)).all())},"
              f" max |diff| {np.nanmax(np.abs(got - ref)):.1e}, n {int(np.isfinite(ref).sum())}")
    a = 2 / 31
    print(f"  hand check, closes (10, 11): EC[1] {dm._ec(np.array([10.0, 11.0]), 30)[1]!r}"
          f" vs 10 + a^2 + 5a = {10 + a * a + 5 * a!r}")
    print(f"  constant 37.5 x 600: max |DIST| {ta.dickson_ma(pd.Series(np.full(600, 37.5))).abs().max():.1e}")

    print("== where the gain search lands (oracle BestGain, 3000 bars per sigma, seed 1, length 30)")
    for s_ in (0.005, 0.02, 0.05):
        g = literal_ec(walk(sigma=s_).to_numpy(), 30)[1]
        g = g[np.isfinite(g)]
        print(f"  sigma {s_}: +5.0 {np.mean(g == 5.0):.1%}  -5.0 {np.mean(g == -5.0):.1%}"
              f"  interior {np.mean(np.abs(g) < 5.0):.1%}  (n {len(g)})")

    print("== Gate B: offsets at which rewriting bars >= j moves a bar < j (of", len(OFFSETS), ")")
    print(f"  real module: {_leaks(ta.dickson_ma)}")
    for tag in sorted(MUTANTS):
        print(f"  mutant {tag}: {_leaks(_load_mutant(MUTANTS[tag], tag).dickson_ma)}")
    mask = _load_mutant(MASK_MUTANT, "mask").dickson_ma
    for fill in FILLS:
        print(f"  bars >= j set to {fill}: real module {_leaks(ta.dickson_ma, fill)},"
              f" mask mutant {_leaks(mask, fill)}, mask mutant under the walk perturbation {_leaks(mask)}")

    print("== non-positive DMA at the defaults: 400 closes at 100, then a one-bar drop held for 20 bars")

    def n_nonpos(f):
        c = pd.Series(np.r_[np.full(400, 100.0), np.full(20, 100.0 * (1 - f))])
        return int(((dm._ec(c.to_numpy(), 30) + literal_hma(c, 7)) / 2 <= 0).sum())

    for lo, hi, step, fmt in ((0.5, 0.998, 0.001, ".3f"), (0.998, 0.99999, 1e-5, ".5f")):
        grid = np.round(np.arange(lo, hi + step / 2, step), 5)
        hits = np.array([n_nonpos(f) for f in grid]) > 0
        k = int(np.argmax(hits)) if hits.any() else None
        where = (f"first hit {grid[k]:{fmt}}" + (f" (previous point {grid[k - 1]:{fmt}} misses)" if k else "")
                 + f", every point above hits: {bool(hits[k:].all())}") if k is not None else "no hit"
        print(f"  drops {grid[0]:{fmt}}-{grid[-1]:{fmt}} step {step:g} ({len(grid)} points): {where}")
    print(f"  the test's 99.999% drop: {n_nonpos(0.99999)} bars <= 0")

    print("== Gate D: max |diff| vs x1 (1200 bars, seed 11, tick 0.05)")
    c = walk(1200, seed=11, tick=0.05)
    base = ta.dickson_ma(c)
    for k in (8.0, 64.0, 10.0, 3.7):
        sc = ta.dickson_ma(c * k)
        print(f"  x{k}: max |diff| {(base - sc).abs().max():.1e}  equals {base.equals(sc)}"
              f"  NaN masks equal {bool((base.isna() == sc.isna()).all())}")

    x = base.dropna()
    print(f"== Gate C synthetic (same walk): bars {len(base)} finite {len(x)} nonzero {int((x != 0).sum())}"
          f" pos {int((x > 0).sum())} neg {int((x < 0).sum())} distinct {x.nunique()}")

    c = walk()
    d = ta.dickson_ma(c)
    print("== proxy overlap (sigma 0.02, seed 1): n comparable", int(d.notna().sum()))
    for name, v in comparators(c).items():
        print(f"  {name:18s} {rho(d, v):8.4f}")

    print("volatility sweep: sigma, max |rho| (comparator)")
    for s_ in (0.005, 0.01, 0.02, 0.05):
        c = walk(sigma=s_)
        d = ta.dickson_ma(c)
        r = {n: rho(d, v) for n, v in comparators(c).items()}
        b = max(r, key=lambda n: abs(r[n]))
        print(f"  {s_}: {r[b]} {b}")

    c = walk(5000)
    runs = timeit.repeat(lambda: ta.dickson_ma(c), number=1, repeat=5)
    print(f"== runtime, 5000 bars, 5 runs: min {min(runs):.2f} s, median {np.median(runs):.2f} s")

    if (SCREEN / "ind_screen_r4.py").exists():  # the round-4 prototype, owner's machine only
        sys.path.insert(0, str(SCREEN))
        import ind_screen_r4 as r4
        print("== cross-check vs the round-4 prototype bt_dma_dist (x100), past the warm-up")
        for seed, s_ in ((1, 0.005), (2, 0.02), (3, 0.05)):
            c = walk(sigma=s_, seed=seed)
            p = 100 * r4.REG["bt_dma_dist"]["fn"](c, c, c, c, c)
            d = ta.dickson_ma(c)
            print(f"  sigma {s_}: max |diff| {(d - p).abs().max():.1e} over {int(d.notna().sum())} bars")


if __name__ == "__main__":
    main()
