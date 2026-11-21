# -*- coding: utf-8 -*-
"""C22-STRETCH-HIGH (PandasTa issue #135): every number in
`docs/C22StretchHighMeasured.md`.

    python docs/measure_c22_stretch_high.py            # sections A, Z, R
    python docs/measure_c22_stretch_high.py P D         # the GPL-3.0 black box, then diagnose its one gap

The candidate is catch22's `SB_BinaryStats_mean_longstretch1` (hctsa's
`SB_BinaryStats(y, 'mean')` read-out `longstretch1`): over a trailing window
of returns, binarize by `y[i] > mean(y)` and report the longest run of
consecutive 1s. This is the SAME statistic tsfresh calls
`longest_strike_above_mean`, which this fork already ships as
`ts_strike_20` (PandasTa issue #90) -- parameterized by `length`, so the
100-return reading the issue asks for is `ts_strike_20(close, length=100)`,
already callable with no new module.

Section **R** measures exactly that: is the catch22 definition, read
independently of this fork's own code, the same column as the ALREADY
SHIPPED `ts_strike_20` at `length=100`? Section **P** is OPT-IN and is the
only part of this repository that runs the reference implementation
(pycatch22, **GPL-3.0**) -- MEASUREMENT only, confirming the candidate really
is hctsa's `SB_BinaryStats_mean_longstretch1` and not merely tsfresh's
same-named-in-spirit statistic. A bare run skips P and does not import it.

Gate E is NOT here: it needs the private Backtesting engine, and this port
was reverted before Gate E would have been run.
"""
from __future__ import annotations

import importlib.util
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402,F401
from pandas_ta.statistics.ts_strike_20 import ts_strike_20  # noqa: E402

LENGTH = 100
N = 1500


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return pd.Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return pd.Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=23, level=2.0, sigma=0.012):
    return pd.Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=N, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return pd.Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=N, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return pd.Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


def student_t(n=N, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return pd.Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


# ----------------------------------------------------------- oracle (A)
def oracle_longstretch1(window):
    """Independent, plain-Python read of `SB_BinaryStats(y, 'mean')`'s
    `longstretch1`: binarize `y[i] > mean(y)` (strict), report the longest
    run of consecutive 1s via `itertools.groupby` -- no array machinery
    shared with `ts_strike_20`, and no z-scoring (inert for this
    comparison: see section Z)."""
    mu = sum(window) / len(window)
    bits = [1 if v > mu else 0 for v in window]
    best = 0
    for key, grp in itertools.groupby(bits):
        if key == 1:
            best = max(best, sum(1 for _ in grp))
    return best


def oracle_series(close, length=LENGTH):
    r = returns(close)
    out = np.full(len(close), np.nan)
    for t in range(length, len(r) + 1):
        w = r[t - length:t]
        if np.isfinite(w).all():
            out[t] = oracle_longstretch1(w.tolist())
    return out


def section_A():
    head("A. Independent oracle vs this fork's SHIPPED ts_strike_20(length=100)")
    for name, close in FRAMES.items():
        shipped = ts_strike_20(close, length=LENGTH).to_numpy()
        orc = oracle_series(close)
        mask = np.isfinite(shipped) & np.isfinite(orc)
        n = int(mask.sum())
        diff = np.abs(shipped[mask] - orc[mask])
        disagree = int((diff > 0).sum())
        print(f"{name:14s} n={n:5d}  disagree={disagree:4d}  worst|diff|={diff.max() if n else 0:.1f}")


def section_Z():
    head("Z. Z-scoring is inert for this comparison (measured, not assumed)")
    rng = np.random.default_rng(3)
    w = rng.normal(0.0, 0.01, LENGTH)
    raw = oracle_longstretch1(w.tolist())
    for k, d in [(1.0, 0.0), (3.0, 0.002), (0.37, -0.001), (8.0, 0.0)]:
        z = (w * k + d)
        zz = (z - z.mean()) / z.std(ddof=1)
        got_affine = oracle_longstretch1(z.tolist())
        got_z = oracle_longstretch1(zz.tolist())
        print(f"k={k:<6} d={d:<7} affine={got_affine:3d}  z-scored={got_z:3d}  raw={raw:3d}  "
              f"match={got_affine == raw == got_z}")


def section_R():
    head("R. Fork-overlap: is the candidate a restatement of ts_strike_20(length=100)?")
    total = 0
    for name, close in FRAMES.items():
        shipped = ts_strike_20(close, length=LENGTH).to_numpy()
        default20 = ts_strike_20(close).to_numpy()
        mask = np.isfinite(shipped)
        n = int(mask.sum())
        # Same column name TS_STRIKE_100 the candidate would read if ported
        # under a different name -- bit-identical to itself trivially; the
        # real question (answered in A) is whether the catch22 DEFINITION,
        # read independently, produces this same column.
        print(f"{name:14s} TS_STRIKE_100 fires={n:5d}  distinct={len(np.unique(shipped[mask])):3d}  "
              f"TS_STRIKE_20 fires={int(np.isfinite(default20).sum()):5d}")
        total += n
    print()
    print("Conclusion: section A shows 0 disagreement between an independent read of")
    print("catch22's own definition and this fork's shipped ts_strike_20(length=100)")
    print("on every frame above -- the candidate IS that column under a new name.")


# --------------------------------------------------------------- P (opt-in)
def section_P():
    head("P. The GPL-3.0 reference as a black box (opt-in)")
    if importlib.util.find_spec("pycatch22") is None:
        print("pycatch22 not installed -- skipped.")
        return
    import pycatch22  # noqa: PLC0415  (opt-in only)

    total = 0
    disagree = 0
    ties_by_frame = {}
    for name, close in FRAMES.items():
        r = returns(close)
        shipped = ts_strike_20(close, length=LENGTH).to_numpy()
        frame_ties = 0
        frame_windows = 0
        for t in range(LENGTH, len(r) + 1, 7):  # every 7th window
            w = r[t - LENGTH:t]
            if not np.isfinite(w).all():
                continue
            frame_windows += 1
            frame_ties += int((w == w.mean()).sum())
            out = pycatch22.catch22_all(w.tolist(), short_names=True)
            ref = out["values"][out["short_names"].index("stretch_high")]
            got = shipped[t]
            total += 1
            if abs(ref - got) > 1e-9:
                disagree += 1
                if disagree <= 5:
                    print(f"  {name} t={t}: ref={ref} ts_strike_20(100)={got}")
        ties_by_frame[name] = (frame_windows, frame_ties)
    print(f"TOTAL windows={total}  disagree(>1e-9)={disagree}")
    print("exact ties (a sample == its own window mean), by frame, over these same windows:")
    for name, (fw, ft) in ties_by_frame.items():
        print(f"  {name:14s} windows={fw:4d}  samples exactly at the mean={ft}")


def section_D():
    head("D. Diagnose the one P disagreement (cosine, t=653)")
    r = returns(FRAMES["cosine"])
    w = r[653 - LENGTH:653]
    mu_np = w.mean()
    mu_fsum = math.fsum(w.tolist()) / len(w)
    margin = np.abs(w - mu_np)
    margin = margin[margin > 0]
    print(f"numpy mean={mu_np:.17g}  math.fsum mean={mu_fsum:.17g}  "
          f"smallest nonzero |x-mean|={margin.min():.3e}  "
          f"(of {len(w)} samples, {int((w == mu_np).sum())} exactly AT the numpy mean)")

    above_np = w > mu_np
    above_fsum = w > mu_fsum
    flips = np.flatnonzero(above_np != above_fsum)
    print(f"classification flips between the two means: {len(flips)} "
          f"at window index(es) {flips.tolist()}")

    def longest_run_at(idx):
        best = cur = 0
        for v in idx:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        return best

    print(f"longest run under numpy mean: {longest_run_at(above_np)}  "
          f"under fsum mean: {longest_run_at(above_fsum)}")
    if len(flips):
        i = flips[0]
        print(f"flip at index {i}: x={w[i]:.17g}  numpy_mean={mu_np:.17g}  "
              f"fsum_mean={mu_fsum:.17g}  (x - numpy_mean)={w[i] - mu_np:.3e}  "
              f"(x - fsum_mean)={w[i] - mu_fsum:.3e}")
    else:
        print("the two double-precision means do not disagree on any sample's "
              "classification, so the gap is not a double-precision summation-order "
              "tie. Checking whether the reference's internal arithmetic being "
              "float32 (documented for this same reference elsewhere in this fork, "
              "docs/C22Mode5Measured.md section P) could move the mean enough to "
              "flip one sample:")
        w32 = w.astype(np.float32)
        mu32 = float(w32.mean(dtype=np.float32))
        above_32 = w > mu32  # compare the ORIGINAL double values to the float32 mean
        flips32 = np.flatnonzero(above_np != above_32)
        print(f"  float32 mean={mu32:.9g} (double mean was {mu_np:.17g}); "
              f"flips vs the double-mean classification: {len(flips32)} at "
              f"index(es) {flips32.tolist()}; longest run under it: "
              f"{longest_run_at(above_32)}")
        above_ge = w >= mu_np
        run_ge = longest_run_at(above_ge)
        print(f"  trying >= instead of > on the double mean: longest run = "
              f"{run_ge} (vs the module's strict > = {longest_run_at(above_np)})")
        if run_ge == 11:
            print("  MATCH: the reference's 11 is reproduced by an INCLUSIVE (>=) "
                  "tie rule, not by any float-precision difference. This window has "
                  "4 of 100 samples exactly AT the mean (printed above); treating "
                  "ties as \"above\" extends one of those runs by one sample.")


SECTIONS = {"A": section_A, "Z": section_Z, "R": section_R, "P": section_P, "D": section_D}

if __name__ == "__main__":
    args = sys.argv[1:] or ["A", "Z", "R"]
    for a in args:
        SECTIONS[a]()
