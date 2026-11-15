# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsStrike20Measured.md for `ts_strike_20`
(PandasTa issue #90, TS-STRIKE-20).

Run from the repository root:

    python docs/measure_ts_strike_20.py            # every section
    python docs/measure_ts_strike_20.py gate_b     # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import itertools
import sys
import time
import tracemalloc
import types

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_strike_20 import ts_strike_20

LENGTH = 20
REAL = importlib.import_module("pandas_ta.statistics.ts_strike_20")


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------------ frames


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    """A path whose LOG returns are an AR(1): `rlog[t] = phi*rlog[t-1] + e`.
    Positive `phi` makes above-average returns cluster, which is exactly what
    a longest strike reads; negative `phi` breaks them up."""
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def geometric_ladder(n=300, step=0.01):
    return Series(100.0 * np.exp(np.arange(n) * step))


def alternating(n=1500, small=0.002, large=0.02):
    """Returns alternate up/down every bar: the above-average returns are
    every other one, so no strike can exceed 1."""
    r = np.where(np.arange(n) % 2 == 0, large, -small)
    return Series(100.0 * np.exp(np.cumsum(r)))


def closes_from_returns(r):
    """The 21 closes whose 20 simple returns are `r`, starting at 1.0."""
    return Series(np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r,
                                                                    float))]))


def compare(name, a, b):
    """Bit-equal count, max |difference| and Spearman over the shared non-NaN
    bars, plus whether the NaN masks agree."""
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    rho = float(x.corr(y, method="spearman")) if len(x) > 2 else float("nan")
    print(f"  {name}: n={int(m.sum())} bit-equal={bit}/{int(m.sum())} "
          f"max|diff|={float(diff.max()) if len(x) else float('nan'):.6g} "
          f"spearman={rho:.6f} nan-masks-agree={masks_agree}")
    return float(diff.max()) if len(x) else float("nan"), bit, rho, masks_agree


# ----------------------------------------------------------------- oracles


def longest_run_above_mean(x):
    """An independent spelling of the issue's line:

        max(run lengths of True in groupby(x > mean(x)))

    or 0 when there is no run. Written from the formula issue #90 states;
    tsfresh is NOT installed here and there is no web access, so this is not
    a copy of its code and nothing here describes how tsfresh spells it."""
    x = np.asarray(x, dtype=float)
    flags = x > x.mean()
    runs = [len(list(g)) for v, g in itertools.groupby(flags) if v]
    return float(max(runs)) if runs else 0.0


def oracle_series(close, length=LENGTH):
    """`longest_run_above_mean` applied window by window: a plain Python loop
    over explicit slices, sharing no array machinery with the module and NOT
    its noise floor either. `gate_a` reports, beside the comparison, how many
    windows of the frame reach the floor -- on a frame where none do, the
    agreement is evidence and not a shared branch."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        r = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        if not all(np.isfinite(v) for v in r):
            continue
        out[t] = longest_run_above_mean(r)
    return Series(out, index=close.index)


def screen_candidate():
    """`REG["ts_strike_20"]["fn"]` out of the screen's own registry, when
    this worktree has `docs/issues/` (gitignored, so a clone does not)."""
    import importlib.util
    import os

    path = os.path.join("docs", "issues", "screen", "ind_screen.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_strike_20"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_strike_20`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            return roll(ret(c), 20, w_longest_strike_above_mean)

    with `ret(c) = c / c.shift(1) - 1`,
    `roll(x, n, f) = _from_win(x, n, f(_win(x, n)))`,
    `_win(x, n) = sliding_window_view(x.to_numpy(float), n)` and
    `_from_win` writing the result at `out[n-1:]`, and

        def w_longest_strike_above_mean(W):
            b = W > W.mean(1, keepdims=True)
            cur = np.zeros(len(W)); best = np.zeros(len(W))
            for j in range(W.shape[1]):
                cur = np.where(b[:, j], cur + 1, 0)
                best = np.maximum(best, cur)
            return best
    """
    r = close / close.shift(1) - 1
    a = r.to_numpy(dtype=float)
    W = sliding_window_view(a, length) if len(a) >= length \
        else np.empty((0, length))
    b = W > W.mean(1, keepdims=True)
    cur = np.zeros(len(W))
    best = np.zeros(len(W))
    for j in range(W.shape[1]):
        cur = np.where(b[:, j], cur + 1, 0)
        best = np.maximum(best, cur)
    out = np.full(len(a), np.nan)
    out[length - 1:] = best
    return Series(out, index=close.index)


def variant(close, length=LENGTH, inclusive=False, log_returns=False,
            below=False, normalised=False, guard=True, finite_filter=True):
    """The module's computation with ONE reading changed."""
    c = close.to_numpy(dtype=float)
    if finite_filter:
        c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        r = np.full(c.size, np.nan)
        r[1:] = np.log(c[1:] / c[:-1]) if log_returns else c[1:] / c[:-1] - 1.0
    if finite_filter:
        r = np.where(np.isfinite(r), r, np.nan)
    W = sliding_window_view(r, length)
    mean = W.mean(axis=1)
    span = W.max(axis=1) - W.min(axis=1)
    if below:
        flags = W < mean[:, None]
    elif inclusive:
        flags = W >= mean[:, None]
    else:
        flags = W > mean[:, None]
    cur = np.zeros(W.shape[0])
    best = np.zeros(W.shape[0])
    for j in range(length):
        cur = np.where(flags[:, j], cur + 1.0, 0.0)
        best = np.maximum(best, cur)
    if normalised:
        best = best / length
    out = np.full(c.size, np.nan)
    body = best if not guard else np.where(span > REAL.NOISE_FLOOR, best, 0.0)
    out[length - 1:] = np.where(np.isnan(mean), np.nan, body)
    return Series(out, index=close.index)


# ----------------------------------------------------------------- Gate A


def gate_a():
    head("Gate A1 -- windows whose answer is derived by hand")
    cases = [
        ([0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0], 3.0,
         "three consecutive +1 among five 0: mean 3/8, the +1 are above"),
        ([1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0], 1.0,
         "alternating: mean 1/2, every other return above it"),
        ([0.0] * 8, 0.0,
         "constant returns: mean 0, nothing is STRICTLY above it"),
        ([5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0], 0.0,
         "constant non-zero returns: same, 0 rather than 8"),
        ([1.0] * 7 + [0.0], 7.0,
         "seven +1 then one 0 at length 8: mean 7/8, the run is length-1 = 7"),
        ([0.0] + [1.0] * 7, 7.0,
         "the same run at the other end of the window"),
        ([1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0], 3.0,
         "runs of 2, 3 and 1: the longest is 3"),
    ]
    for r, expected, why in cases:
        n = len(r)
        closes = closes_from_returns(r)
        out = ts_strike_20(closes, length=n)
        got = float(out.iloc[-1])
        print(f"  length={n} returns={r} -> {got:g} (expected {expected:g}) "
              f"[{'OK' if got == expected else 'MISMATCH'}]  {why}")
        print(f"     name={out.name} warm-up NaNs={int(out.isna().sum())} "
              f"(first value at bar {int(out.notna().to_numpy().argmax())})")

    head("Gate A1b -- a hand-derived window at the SHIPPED length 20")
    # Eleven flat closes, then four x2 steps, then five flat: returns are
    # [0]*10 + [1]*4 + [0]*5 -> hmm, build it explicitly instead.
    r = [0.0] * 8 + [1.0] * 5 + [0.0] * 3 + [1.0] * 2 + [0.0] * 2
    assert len(r) == 20
    closes = closes_from_returns(r)
    out = ts_strike_20(closes)
    mean = sum(r) / len(r)
    print(f"  returns {r}")
    print(f"  mean = 7/20 = {mean:g}; the +1 runs are 5 and 2, so the answer "
          f"is 5")
    print(f"  module -> {float(out.iloc[-1]):g}, name {out.name}, "
          f"first value at bar {int(out.notna().to_numpy().argmax())}")

    head("Gate A2 -- the screen prototype")
    close = walk()
    base, proto = ts_strike_20(close), prototype(close)
    compare("retyped prototype", base, proto)
    print(f"  module fires {int(base.notna().sum())} of {len(close)}; "
          f"prototype fires {int(proto.notna().sum())}")
    disagree = np.flatnonzero((base.isna() != proto.isna()).to_numpy())
    print(f"  bars whose NaN flag differs: {disagree.tolist()} "
          f"(module {base.iloc[disagree].tolist()}, "
          f"prototype {proto.iloc[disagree].tolist()})")
    fn = screen_candidate()
    if fn is None:
        print("  docs/issues/screen/ind_screen.py absent -- import skipped")
    else:
        got = fn(close, close * 1.01, close * 0.99, close,
                 Series(np.full(len(close), 1000.0)))
        compare("IMPORTED prototype", base, Series(np.asarray(got, float),
                                                   index=close.index))

    head("Gate A3 -- an independent groupby spelling, window by window")
    print("  the oracle has no noise floor, so the floor cannot be what makes "
          "them agree; the count of windows that reach it is printed beside "
          "each frame")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1(+0.6)", ar1())):
        base, orc = ts_strike_20(frame), oracle_series(frame)
        compare(name, base, orc)
        r = (frame / frame.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        span = W.max(axis=1) - W.min(axis=1)
        print(f"    windows reaching the floor: "
              f"{int((span <= REAL.NOISE_FLOOR).sum())} of {len(span)}")

    head("Gate A4 -- the attainable set")
    print("  every k in 1..length-1 is reachable, by k consecutive +1 "
          "returns among zeros:")
    reached = []
    for k in range(1, LENGTH):
        r = [1.0] * k + [0.0] * (LENGTH - k)
        got = float(ts_strike_20(closes_from_returns(r)).iloc[-1])
        reached.append(got)
        if got != float(k):
            print(f"    k={k}: MISMATCH got {got:g}")
    print(f"    reached {sorted(set(reached))}")
    rng = np.random.default_rng(4242)
    draws = rng.normal(0.0, 0.01, (200000, LENGTH))
    W = draws
    flags = W > W.mean(1, keepdims=True)
    cur = np.zeros(len(W))
    best = np.zeros(len(W))
    for j in range(LENGTH):
        cur = np.where(flags[:, j], cur + 1.0, 0.0)
        best = np.maximum(best, cur)
    vals, counts = np.unique(best, return_counts=True)
    print(f"  200,000 iid gaussian windows: values {vals.astype(int).tolist()}")
    print(f"    counts {counts.tolist()}")
    print(f"    max {int(best.max())}, bars at 0: {int((best == 0).sum())}, "
          f"bars at {LENGTH}: {int((best == LENGTH).sum())}")
    print(f"    mean {best.mean():.4f} median {np.median(best):.1f}")
    print("  value 20 is impossible: at least one sample is <= the mean of "
          "its own window, so the longest run is at most length-1 = 19.")
    print("  value 0 happens when every return in the window is equal: if "
          "they are not, the maximum is strictly above the mean. That proof "
          "covers the UNGUARDED formula; the floor adds the windows whose "
          "returns are equal only to rounding level, measured in the "
          "`noise_floor` section.")

    head("Gate A5 -- the readings the wording leaves open, priced")
    close = walk()
    base = ts_strike_20(close)
    for name, kw in (("inclusive >= instead of >", {"inclusive": True}),
                     ("log returns", {"log_returns": True}),
                     ("longest strike BELOW the mean", {"below": True}),
                     ("divided by length", {"normalised": True})):
        compare(name, base, variant(close, **kw))
    for fname, frame in (("walk", walk()), ("tick-rounded", tick_rounded())):
        r = (frame / frame.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        ties = int((W == W.mean(axis=1, keepdims=True)).sum())
        print(f"  the >= reading differs only on an EXACT tie with the mean, "
              f"of which {fname} has {ties} in {W.size} samples")
    flat = Series(np.full(300, 50.0))
    print(f"  on 300 identical closes the two readings are the opposite ends "
          f"of the scale: port "
          f"{sorted(set(ts_strike_20(flat).dropna().tolist()))} on "
          f"{int(ts_strike_20(flat).notna().sum())} bars, the >= reading "
          f"{sorted(set(variant(flat, inclusive=True, guard=False).dropna().tolist()))}"
          f" (its guard removed, since the floor would mask it)")
    nrm = variant(close, normalised=True)
    m = base.notna() & nrm.notna()
    print(f"  normalised reading: port/20 reproduces it exactly on "
          f"{int(((base[m] / LENGTH) == nrm[m]).sum())} of {int(m.sum())} bars")


# ----------------------------------------------------------------- Gate B

WRITE_SHIFT_MUTANT = (
    "    strike = Series(out, index=close.index)",
    "    strike = Series(out, index=close.index).shift(-length)")
WRITE_EARLY_MUTANT = (
    "    out[length - 1:] = np.where(np.isnan(mean), np.nan,",
    "    out[length - 2:-1] = np.where(np.isnan(mean), np.nan,")
FORWARD_RETURN_MUTANT = (
    "        r[1:] = c[1:] / c[:-1] - 1.0",
    "        r[:-1] = c[1:] / c[:-1] - 1.0")
FORWARD_MEAN_MUTANT = (
    "    above = windows > mean[:, None]",
    "    above = windows > np.roll(mean, -1)[:, None]")
FORWARD_WINDOW_MUTANT = (
    "    current = np.where(above[:, j], current + 1.0, 0.0)",
    "    current = np.where(np.roll(above, -1, axis=0)[:, j], current + 1.0, "
    "0.0)")

FORWARD_SPAN_MUTANT = (
    "    span = windows.max(axis=1) - windows.min(axis=1)",
    "    span = np.roll(windows.max(axis=1) - windows.min(axis=1), -1)")

MUTANTS = [WRITE_SHIFT_MUTANT, WRITE_EARLY_MUTANT, FORWARD_RETURN_MUTANT,
           FORWARD_MEAN_MUTANT, FORWARD_WINDOW_MUTANT]
MUTANT_IDS = ["write_shift", "write_early", "forward_return", "forward_mean",
              "forward_window"]
OFFSETS = range(40, 1500, 40)
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "ar1(+0.6)": (ar1(), ar1(seed=8)),
}


def flat_planted(n=1500, seed=11):
    """A walk with `length + 1` identical closes ending at EACH sweep offset,
    so the window ending at J is degenerate and the noise floor fires there.
    The runs are 21 closes 40 apart, so they do not overlap. This is the frame
    the `forward_span` mutant needs: on a continuous frame the floor never
    fires, so taking `span` from the next window is a no-op there."""
    c = walk(n, seed).to_numpy().copy()
    for j in OFFSETS:
        c[j - LENGTH:j + 1] = c[j - LENGTH]
    return Series(c)


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_strike_20_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def moved_bars(a, b):
    """Bars where two outputs really differ: a plain `a != b` counts
    NaN-against-NaN as a difference, which would inflate every count below by
    the `length` warm-up bars."""
    return int(((a != b) & ~(a.isna() & b.isna())).sum())


def leak_offsets(fn, close, other):
    """The J values at which anything strictly before J moved."""
    base = fn(close)
    hit = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hit.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hit.append(j)
    return hit


def leaks(fn, close, other):
    return len(leak_offsets(fn, close, other))


def gate_b():
    head("Gate B -- future-perturbation sweep, real module and five mutants")
    n = len(list(OFFSETS))
    print(f"  {n} offsets J = {OFFSETS.start}..{max(OFFSETS)} step "
          f"{OFFSETS.step}; a hit means something strictly before J moved")
    for frame in sorted(FRAMES):
        close, other = FRAMES[frame]
        print(f"  {frame}: real module {leaks(ts_strike_20, close, other)}/{n}")
    for mid, mutant in zip(MUTANT_IDS, MUTANTS):
        mod = load_mutant(*mutant)
        for frame in sorted(FRAMES):
            close, other = FRAMES[frame]
            live = not mod.ts_strike_20(close).equals(ts_strike_20(close))
            moved = moved_bars(mod.ts_strike_20(close), ts_strike_20(close))
            hit = leak_offsets(mod.ts_strike_20, close, other)
            missed = [j for j in OFFSETS if j not in hit]
            print(f"  {mid} on {frame}: caught {len(hit)}/{n} "
                  f"(live mutation={live}, bars differing={moved})")
            if missed:
                print(f"    missed J = {missed}")

    head("Gate B -- the same sweep at non-default lengths")
    close, other = FRAMES["walk"]
    for length in (5, 60):
        print(f"  length={length}: real module "
              f"{leaks(lambda c: ts_strike_20(c, length=length), close, other)}"
              f"/{n}, first value at bar "
              f"{int(ts_strike_20(close, length=length).notna().to_numpy().argmax())}")
        for mid, mutant in zip(MUTANT_IDS, MUTANTS):
            mod = load_mutant(*mutant)

            def mutated(c, length=length, mod=mod):
                return mod.ts_strike_20(c, length=length)

            live = not mutated(close).equals(ts_strike_20(close, length=length))
            hit = leak_offsets(mutated, close, other)
            missed = [j for j in OFFSETS if j not in hit]
            print(f"    {mid}: caught {len(hit)}/{n} (live mutation={live})"
                  + (f" missed J = {missed}" if missed else ""))

    head("Gate B -- the sixth mutant: span taken from the next window")
    print("  `span` is the module's other windowed input, and it decides the "
          "guard. On a continuous frame the guard never fires, so this "
          "mutation is a no-op there; it is swept on a walk carrying 21 "
          "identical closes ending at each offset J.")
    frame = flat_planted()
    other = walk(seed=97)
    zeros = int((ts_strike_20(frame) == 0.0).sum())
    print(f"  the frame reads 0 on {zeros} bars (the degenerate windows)")
    mod = load_mutant(*FORWARD_SPAN_MUTANT)
    for name, f in (("walk", FRAMES["walk"][0]), ("flat-planted", frame)):
        a, b = mod.ts_strike_20(f), ts_strike_20(f)
        live = not a.equals(b)
        moved = np.flatnonzero(((a != b) & ~(a.isna() & b.isna())).to_numpy())
        print(f"  on {name}: live mutation={live}, bars differing="
              f"{len(moved)}"
              + (f" at {moved.tolist()}" if len(moved) <= 5 else
                 f", first {moved[:3].tolist()} last {moved[-1]}"))
    print(f"  the walk is {len(FRAMES['walk'][0])} bars long, so its one "
          f"differing bar is its LAST one: np.roll wraps the warm-up window's "
          f"NaN span back round. Not a guard crossing -- which is the point: "
          f"the mutation needs a frame that reaches the floor to say anything")
    hit = leak_offsets(mod.ts_strike_20, frame, other)
    missed = [j for j in OFFSETS if j not in hit]
    print(f"  real module on flat-planted: "
          f"{leaks(ts_strike_20, frame, other)}/{n}")
    print(f"  forward_span on flat-planted: caught {len(hit)}/{n}"
          + (f" missed J = {missed}" if missed else ""))

    head("Gate B -- the mechanism behind every cell under 37/37")
    print("  a one-bar look-ahead can move ONE prefix bar and no other: bar "
          "J-1 is the only bar whose window reaches close[J].")
    for mid, mutant in (("write_early", WRITE_EARLY_MUTANT),
                        ("forward_return", FORWARD_RETURN_MUTANT),
                        ("forward_mean", FORWARD_MEAN_MUTANT),
                        ("forward_window", FORWARD_WINDOW_MUTANT)):
        mod = load_mutant(*mutant)
        for frame in ("walk", "tick-rounded"):
            close, other = FRAMES[frame]
            base = mod.ts_strike_20(close)
            widths = set()
            for j in OFFSETS:
                p = close.copy()
                p.iloc[j:] = other.iloc[j:].values
                out = mod.ts_strike_20(p)
                a, b = base.iloc[:j], out.iloc[:j]
                moved = np.flatnonzero(((a != b) & ~(a.isna() & b.isna()))
                                       .to_numpy())
                widths.add(tuple((moved - j).tolist()))
            print(f"  {mid} on {frame}: the moved prefix bars, as offsets "
                  f"from J: {sorted(widths)}")
    print("  so a cell under 37/37 is an offset where that single bar's "
          "INTEGER did not change; the value it would have to cross is one "
          "unit away, not one ulp.")
    mod = load_mutant(*WRITE_SHIFT_MUTANT)
    close, other = FRAMES["tick-rounded"]
    base = mod.ts_strike_20(close)
    p = close.copy()
    p.iloc[40:] = other.iloc[40:].values
    out = mod.ts_strike_20(p)
    a, b = base.iloc[:40], out.iloc[:40]
    print(f"  write_shift on tick-rounded at J=40: the prefix carries "
          f"{int(a.notna().sum())} non-NaN bars, {int((a == b).sum())} of "
          f"them identical between the two paths -- the whole prefix "
          f"coincided, which is reachable because the column is an integer "
          f"in a narrow range")
    print(f"    prefix values {a.dropna().astype(int).tolist()}")
    print(f"    perturbed     {b.dropna().astype(int).tolist()}")
    real_base, real_pert = ts_strike_20(close), ts_strike_20(p)
    print(f"    the real module's bars 40..59, which those 20 shifted bars "
          f"show: {real_base.iloc[40:60].astype(int).tolist()}")
    print(f"    the same bars on the perturbed path:                      "
          f"{real_pert.iloc[40:60].astype(int).tolist()}")
    print(f"    closes 40..44 unperturbed {close.iloc[40:45].tolist()} vs "
          f"perturbed {p.iloc[40:45].tolist()}")

    head("Gate B -- how often a one-bar leak is visible at all")
    for frame in sorted(FRAMES):
        close, _ = FRAMES[frame]
        base = ts_strike_20(close).to_numpy()
        m = ~np.isnan(base)
        same = int((base[m][1:] == base[m][:-1]).sum())
        print(f"  {frame}: {same} of {int(m.sum()) - 1} consecutive bar pairs "
              f"carry the SAME value, so a one-bar shift is invisible there")

    head("Gate B -- offset is the caller's own look-ahead")
    close = walk(400, seed=3)
    base = ts_strike_20(close)
    for off in (2, -2):
        got = ts_strike_20(close, offset=off)
        print(f"  offset={off}: equals base.shift({off}) -> "
              f"{bool(got.equals(base.shift(off)))}")


# ------------------------------------------------------- the noise floor


def noise_floor():
    head("The noise floor -- an exactly geometric path")
    for name, frame in (("1%-a-bar ladder", geometric_ladder()),
                        ("x1.5 ladder", Series(np.cumprod(np.full(300, 1.5))
                                               * 1e-20))):
        guarded = ts_strike_20(frame)
        unguarded = variant(frame, guard=False)
        gv = sorted(set(guarded.dropna().tolist()))
        uv, uc = np.unique(unguarded.dropna().to_numpy(), return_counts=True)
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}/"
              f"{len(frame)} values {gv}")
        print(f"    unguarded fires {int(unguarded.notna().sum())}/"
              f"{len(frame)} values {uv.astype(int).tolist()} counts "
              f"{uc.tolist()}")
        r = frame / frame.shift(1) - 1.0
        span = (r.rolling(LENGTH).max() - r.rolling(LENGTH).min()).iloc[-1]
        print(f"    the window's return span is {float(span):.3e} vs the "
              f"floor {REAL.NOISE_FLOOR:.3e}; mathematically the returns are "
              f"constant, so the answer is 0")

    head("The noise floor on real-shaped data -- what it costs")
    for name, frame in (("walk", walk(300)), ("tick-rounded",
                                              tick_rounded(300))):
        guarded, unguarded = ts_strike_20(frame), variant(frame, guard=False)
        compare(name, guarded, unguarded)
        print(f"    fires {int(guarded.notna().sum())}/{len(frame)}")

    head("The noise floor against a monotone one-tick-per-bar path")
    print("  these paths have returns that genuinely DECREASE (tick/price "
          "shrinks as price rises), so the mathematical answer is not 0; "
          "where the span is under the floor the column reports 0 anyway.")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = closes / closes.shift(1) - 1.0
        span = float((r.rolling(LENGTH).max()
                      - r.rolling(LENGTH).min()).iloc[-1])
        guarded = ts_strike_20(closes)
        unguarded = variant(closes, guard=False)
        gv = sorted(set(guarded.dropna().tolist()))
        uv = sorted(set(unguarded.dropna().tolist()))
        print(f"  price={price:g} tick={tick:g}: |r| ~ {float(r.iloc[-1]):.3e},"
              f" span {span:.3e} vs floor {REAL.NOISE_FLOOR:.3e}")
        print(f"    guarded values {gv}, unguarded values {uv}")

    head("The noise floor -- a flat run planted in a walk")
    close = walk(400, seed=21)
    base = ts_strike_20(close)
    for identical in (20, 21, 25):
        flat = close.copy()
        flat.iloc[200:200 + identical] = float(close.iloc[200])
        out = ts_strike_20(flat)
        zeros = np.flatnonzero(((out == 0.0) & (base != 0.0)).to_numpy())
        print(f"  {identical} identical closes at bar 200: bars reading 0 "
              f"that did not before: {zeros.tolist()}")


# ---------------------------------------------------------------- Gate C/D


def gate_c_d():
    head("Gate D -- a power-of-two price rescale")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1)):
        close = fn()
        for k in (8.0, 64.0):
            compare(f"{name} x{k:g}", ts_strike_20(close),
                    ts_strike_20(close * k))
    head("Gate D -- non-default lengths")
    close = walk()
    for length in (5, 60):
        for k in (8.0, 64.0):
            compare(f"length={length} x{k:g}",
                    ts_strike_20(close, length=length),
                    ts_strike_20(close * k, length=length))
    head("Gate D -- x10 and x3.7, which the arithmetic does not promise")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1)):
        close = fn()
        for k in (10.0, 3.7):
            compare(f"{name} x{k:g}", ts_strike_20(close),
                    ts_strike_20(close * k))

    head("Invariance to an AFFINE map of the returns themselves")
    print("  the comparison is against the window's OWN mean, so "
          "r -> a*r + b (a > 0) cannot change which samples are above it")
    close = walk()
    base = ts_strike_20(close)
    for factor in (0.5, 3.0):
        r = (close / close.shift(1) - 1.0).to_numpy()
        r[0] = 0.0
        scaled = Series(100.0 * np.cumprod(1.0 + factor * r),
                        index=close.index)
        compare(f"returns x{factor:g}", base, ts_strike_20(scaled))
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))),
                     index=close.index)
    compare("+0.004 log drift a bar", base, ts_strike_20(drifted))

    head("How close any sample gets to its own window mean")
    print("  the output is an integer decided by `r > mean(r)`, so what makes "
          "it stable under a last-bit change is the smallest MARGIN any "
          "sample has to the mean of its window, relative to the window's "
          "return span")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1)):
        r = (fn() / fn().shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r[1:], LENGTH)
        margin = np.abs(W - W.mean(axis=1, keepdims=True))
        rel = margin / (W.max(axis=1, keepdims=True)
                        - W.min(axis=1, keepdims=True))
        print(f"  {name}: smallest |r - mean| {float(margin.min()):.3e}, "
              f"smallest as a fraction of the span {float(rel.min()):.3e}, "
              f"exact ties {int((margin == 0).sum())} of {margin.size}")

    head("Gate C/D -- fires, and is not constant")
    for name, fn in (("walk", walk), ("tick-rounded", tick_rounded),
                     ("ar1(+0.6)", ar1), ("alternating", alternating)):
        out = ts_strike_20(fn())
        vals, counts = np.unique(out.dropna().to_numpy(), return_counts=True)
        print(f"  {name}: fires {int(out.notna().sum())}/{len(out)}, "
              f"non-zero {int((out.dropna() != 0).sum())}, distinct "
              f"{int(out.nunique())}")
        print(f"    values {vals.astype(int).tolist()} counts {counts.tolist()}")

    head("Gate C -- warm-up arithmetic")
    for length in (5, 20, 60):
        out = ts_strike_20(walk(1500, seed=11), length=length)
        print(f"  length={length}: first value at bar "
              f"{int(out.notna().to_numpy().argmax())}, fires "
              f"{int(out.notna().sum())} of 1500 "
              f"(1500 - {length} = {1500 - length})")


# ------------------------------------------------- what the column means


def meaning():
    head("What it orders -- clustering of above-average returns")
    print("  AR(1) log returns, phi from +0.8 to -0.8; a positive phi makes "
          "above-average returns cluster")
    for phi in (0.8, 0.6, 0.3, 0.0, -0.3, -0.6, -0.8):
        out = ts_strike_20(ar1(phi=phi)).dropna()
        print(f"  phi={phi:+.1f}: median {float(out.median()):.1f} "
              f"mean {float(out.mean()):.4f} p10 {float(out.quantile(0.1)):.1f}"
              f" p90 {float(out.quantile(0.9)):.1f}")
    head("The two deterministic extremes")
    out = ts_strike_20(alternating()).dropna()
    print(f"  alternating up/down: values "
          f"{sorted(set(out.tolist()))} on {len(out)} bars")
    ladder = ts_strike_20(geometric_ladder()).dropna()
    print(f"  exactly geometric (constant returns): values "
          f"{sorted(set(ladder.tolist()))} on {len(ladder)} bars")
    print("  a pure TREND with no noise therefore reads 0, not 20: the "
          "column is not a trend feature")

    head("The distribution on iid returns, measured on the walk")
    out = ts_strike_20(walk()).dropna()
    vals, counts = np.unique(out.to_numpy(), return_counts=True)
    for v, c in zip(vals, counts):
        print(f"  {int(v):2d}: {c:5d} bars ({100.0 * c / len(out):5.2f}%)")
    print(f"  median {float(out.median()):.1f} mean {float(out.mean()):.4f}")

    head("One planted outlier")
    close = walk().copy()
    base = ts_strike_20(close)
    arr = close.to_numpy().copy()
    arr[700:] *= 1.5          # one +50% return at bar 700
    spiked = ts_strike_20(Series(arr, index=close.index))
    affected = slice(700, 720)
    print(f"  a single +50% return at bar 700: the 20 windows holding it read "
          f"mean {float(spiked.iloc[affected].mean()):.4f} against the same "
          f"bars' {float(base.iloc[affected].mean()):.4f} without it")
    print(f"    values {sorted(set(spiked.iloc[affected].tolist()))} vs "
          f"{sorted(set(base.iloc[affected].tolist()))}")
    print(f"    the whole frame's mean is {float(base.dropna().mean()):.4f}; "
          f"one outlier SHORTENS the strike, because it pulls the mean above "
          f"the ordinary returns")


def neighbours():
    head("Nearest shipped columns on ONE synthetic walk -- NOT Gate E")
    import pandas_ta as ta  # noqa: F401  (registers the accessors)

    close = walk()
    high, low = close * 1.01, close * 0.99
    base = ts_strike_20(close)
    others = {
        "ts_binent_20": ta.ts_binent_20(close),
        "ts_c3_20": ta.ts_c3_20(close),
        "lean_hurst_100": ta.lean_hurst_100(close),
        "lean_momersion_20": ta.lean_momersion_20(close),
        "tf_centroid_20": ta.tf_centroid_20(close),
        "entropy_20": ta.entropy(close, length=20),
        "skew_20": ta.skew(close, length=20),
        "kurtosis_20": ta.kurtosis(close, length=20),
        "zscore_20": ta.zscore(close, length=20),
        "rsi_14": ta.rsi(close, length=14),
        "chop_14": ta.chop(high, low, close),
        "natr_14": ta.natr(high, low, close, length=14),
    }
    rows = []
    for name, col in others.items():
        if col is None:
            continue
        if isinstance(col, pd.DataFrame):
            col = col.iloc[:, 0]
        m = base.notna() & col.notna()
        rho = float(base[m].corr(col[m], method="spearman"))
        rows.append((abs(rho), name, int(m.sum())))
    for a, name, n in sorted(rows, reverse=True):
        print(f"  |rho| {a:.4f} vs {name} (n={n})")


def guards():
    head("Guard bands")
    close = walk(400, seed=31)
    print(f"  length below the minimum -> the default 20:")
    for length in (None, 0, -5, 2, 0.5, 2.9):
        print(f"    length={length!r} -> {ts_strike_20(close, length=length).name}")
    for length in (3, 5, 50.9, 50):
        out = ts_strike_20(close, length=length)
        print(f"    length={length!r} -> {out.name}, fires "
              f"{int(out.notna().sum())}")
    print("  why the minimum is 3 -- the same computation below it, through "
          "`variant`, since the module itself refuses those lengths:")
    for length in (1, 2, 3):
        out = variant(close, length=length)
        vals, counts = np.unique(out.dropna().to_numpy(), return_counts=True)
        print(f"    length={length}: values {vals.astype(int).tolist()} "
              f"counts {counts.tolist()} over {int(out.notna().sum())} bars")
    print(f"  {LENGTH} closes -> {ts_strike_20(walk(LENGTH))} (None: too "
          f"short for {LENGTH} returns)")
    out = ts_strike_20(walk(LENGTH + 1, seed=2))
    print(f"  {LENGTH + 1} closes -> fires {int(out.notna().sum())} at bar "
          f"{int(out.notna().to_numpy().argmax())}")
    out = ts_strike_20(walk(200, seed=13), fillna=-1.0)
    print(f"  fillna=-1.0 fills {int((out == -1.0).sum())} bars")

    head("A bad close empties the windows that hold it")
    base = ts_strike_20(close)
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = close.copy()
        holed.iloc[200] = bad
        out = ts_strike_20(holed)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        moved = int((base.notna() & out.notna()
                     & (base != out)).iloc[:200].sum())
        print(f"  close[200]={bad!r}: empties {len(emptied)} bars "
              f"{emptied.min() if len(emptied) else '-'}.."
              f"{emptied.max() if len(emptied) else '-'}, bars before 200 "
              f"that moved: {moved}")

    head("An overflowing return pair")
    pair = walk(400, seed=31).copy()
    pair.iloc[200] = 1e-300
    pair.iloc[201] = 1e50
    out = ts_strike_20(pair)
    raw = variant(pair, finite_filter=False)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    print(f"  1e-300 then 1e50: r[201] overflows to +inf, so ONE return is "
          f"spoiled and the module empties {len(emptied)} bars "
          f"({emptied.min()}..{emptied.max()})")
    print(f"  without the finiteness filter the same {len(emptied)} windows "
          f"would read {sorted(set(raw.iloc[emptied].tolist()))} -- an "
          f"infinite mean leaves nothing STRICTLY above it, so the window "
          f"would look like a flat one rather than like missing data")


def cost():
    head("Cost at 400,000 bars")
    close = walk(400000, seed=77)
    t0 = time.perf_counter()
    ts_strike_20(close)
    t1 = time.perf_counter()
    tracemalloc.start()
    ts_strike_20(close)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"  n=400,000: {1000.0 * (t1 - t0):.0f} ms, traced peak "
          f"{peak / 1e6:.1f} MB")
    print(f"  the boolean (n - length + 1, length) array alone is "
          f"{(400000 - LENGTH + 1) * LENGTH / 1e6:.1f} MB")


SECTIONS = {"gate_a": gate_a, "gate_b": gate_b, "noise_floor": noise_floor,
            "gate_c_d": gate_c_d, "meaning": meaning,
            "neighbours": neighbours, "guards": guards, "cost": cost}


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(SECTIONS)
    for name in wanted:
        SECTIONS[name]()
    print()
