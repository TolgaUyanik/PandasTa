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


def flat_tick(n=N, price=1e6, tick=0.001):
    """A monotone one-tick-per-bar ladder at a price level where the return
    span is below `ts_strike_20`'s NOISE_FLOOR (documented in
    `pandas_ta/statistics/ts_strike_20.py`: price 1e6, 0.001 tick -> span
    2.2e-16, below the 9.09e-13 floor). The returns genuinely DECREASE (a
    fixed tick is a shrinking fraction of a rising price), by ~1e-16 across
    a 100-window -- below one ulp of the price ratio, so float64 quantises
    them onto one or two values. `docs/TsStrike20Measured.md` measures this
    EXACT price/tick pair, *The rounding-noise floor*, and calls reading 0
    here "the floor doing its job": the unguarded reading is not a near-true
    estimate spoiled by noise, it is noise across the whole attainable
    scale -- confirmed below by a worst disagreement of 99, the theoretical
    max on a length-100 window, not a small spread around a true value.
    This is where Gate A's "0 disagree" claim would be silent by
    construction if this frame were absent."""
    return pd.Series(price + tick * np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
    "flat-tick": flat_tick(),
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
    print("on every NON-DEGENERATE frame above -- the candidate IS that column under")
    print("a new name there. The 'flat-tick' row above is the deliberate exception:")
    print("it is designed to trip ts_strike_20's own NOISE_FLOOR, where the shipped")
    print("column and the raw catch22 definition part ways on purpose -- see section A")
    print("and the receipt's section 2 for that measured divergence.")


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

        # The reference does not binarize the RAW window: it z-scores first
        # (catch22's own preprocessing step) and then compares each sample to
        # the MEAN OF THE Z-SCORED SERIES, a fresh naive summation whose
        # residual is a fresh rounding error distinct from the raw window's
        # mean. A sample sitting exactly at the raw mean becomes exactly 0 in
        # z-space, so the sign of that residual -- not a tie-rule choice --
        # decides whether it reads "above" under the SAME strict `>` this
        # fork's module uses.
        std64 = w.std(ddof=0)
        z64 = (w - mu_np) / std64
        z64_mean = z64.mean()
        above_z64 = z64 > z64_mean
        run_z64 = longest_run_at(above_z64)
        print(f"  z-scored (float64) mean={z64_mean:.3e} "
              f"({'negative' if z64_mean < 0 else 'nonnegative'}); "
              f"longest run under z64 > its own mean: {run_z64}")

        w32_z = w.astype(np.float32)
        std32 = w32_z.std(dtype=np.float32, ddof=0)
        z32 = (w32_z - w32_z.mean(dtype=np.float32)) / std32
        z32_mean = z32.mean(dtype=np.float32)
        above_z32 = z32 > z32_mean
        run_z32 = longest_run_at(above_z32)
        print(f"  z-scored (float32) mean={z32_mean:.3e} "
              f"({'negative' if z32_mean < 0 else 'nonnegative'}); "
              f"longest run under z32 > its own mean: {run_z32}")

        above_ge = w >= mu_np
        run_ge = longest_run_at(above_ge)
        tie_count = int((w == mu_np).sum())
        print(f"  trying >= instead of > on the double mean: longest run = "
              f"{run_ge} (vs the module's strict > = {longest_run_at(above_np)}); "
              f"this window has {tie_count} of {len(w)} samples exactly AT the mean")

        ref_value = None
        if importlib.util.find_spec("pycatch22") is not None:
            import pycatch22  # noqa: PLC0415  (opt-in only)
            out = pycatch22.catch22_all(w.tolist(), short_names=True)
            ref_value = out["values"][out["short_names"].index("stretch_high")]
            print(f"  reference stretch_high on this exact window: {ref_value}")
            if run_z64 == ref_value or run_z32 == ref_value:
                print(f"  MATCH: the reference's {ref_value:g} is reproduced by the "
                      "z-scored-mean residual (precision-driven), the SAME strict "
                      "`>` rule this module uses -- not a tie-rule convention "
                      "difference.")
            elif run_ge == ref_value:
                print(f"  MATCH: the reference's {ref_value:g} is reproduced by an "
                      f"INCLUSIVE (>=) tie rule on the raw mean, not by the "
                      f"z-scored-mean residual ({tie_count} of {len(w)} samples sit "
                      "exactly at the raw mean, printed above).")
            else:
                print(f"  NEITHER the z-scored-mean residual ({run_z64}/{run_z32}) "
                      f"nor an inclusive tie rule ({run_ge}) reproduces the "
                      f"reference's {ref_value:g} on this window.")
        else:
            print("  pycatch22 not installed -- skipping the reference comparison.")


SECTIONS = {"A": section_A, "Z": section_Z, "R": section_R, "P": section_P, "D": section_D}

if __name__ == "__main__":
    args = sys.argv[1:] or ["A", "Z", "R"]
    for a in args:
        SECTIONS[a]()
