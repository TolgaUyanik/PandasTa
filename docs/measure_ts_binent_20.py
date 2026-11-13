# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsBinent20Measured.md for `ts_binent_20`
(PandasTa issue #89, TS-BINENT-20).

Run from the repository root:

    python docs/measure_ts_binent_20.py

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import itertools
import math
import types

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_binent_20 import ts_binent_20

LENGTH, BINS = 20, 5
REAL = importlib.import_module("pandas_ta.statistics.ts_binent_20")


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


def from_returns(r):
    """A price path whose SIMPLE returns are exactly `r` where that is
    representable: `close[0] = 100` and `close[t] = close[t-1] * (1 + r[t])`."""
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    """Student-t returns: most windows are dominated by one large move, which
    is the regime binned entropy reads lowest."""
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return from_returns(np.clip(r, -0.5, 0.5))


def two_point(n=1500, seed=4, sigma=0.01):
    """Returns take exactly two values, +sigma and -sigma: the window's min
    and max are those two values, so only the first and last bin are ever
    occupied."""
    rng = np.random.default_rng(seed)
    return from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def uniform_returns(n=1500, seed=5, half=0.02):
    rng = np.random.default_rng(seed)
    return from_returns(rng.uniform(-half, half, n))


def laplace_returns(n=1500, seed=6, scale=0.01):
    rng = np.random.default_rng(seed)
    return from_returns(np.clip(rng.laplace(0.0, scale, n), -0.5, 0.5))


def geometric_ladder(n=300, step=0.01):
    return Series(100.0 * np.exp(np.arange(n) * step))


def compare(name, a, b):
    """Max |difference|, bit-equal count and Spearman over the shared
    non-NaN bars, plus whether the NaN masks agree. Spearman is reported as
    `constant` rather than NaN when one side has a single distinct value --
    that is a finding about the comparator, not a missing number."""
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    constant = int(x.nunique()) < 2 or int(y.nunique()) < 2
    rho = (float("nan") if constant or len(x) < 3
           else float(x.corr(y, method="spearman")))
    rho_text = "constant" if constant else f"{rho:.6f}"
    print(f"  {name}: n={int(m.sum())} max|diff|={float(diff.max()):.6e} "
          f"bit-equal={bit}/{int(m.sum())} "
          f"bars|diff|>1e-12={int((diff > 1e-12).sum())} spearman={rho_text} "
          f"distinct={int(x.nunique())}/{int(y.nunique())} "
          f"nan-masks-agree={masks_agree}")
    return float(diff.max()), bit, rho, masks_agree


# ----------------------------------------------------------------- Gate A


def screen_candidate():
    """`REG["ts_binent_20"]["fn"]` out of the screen's own registry, when this
    worktree has `docs/issues/` (gitignored, so a clone does not)."""
    import importlib.util
    import os
    import sys

    path = os.path.join("docs", "issues", "screen", "ind_screen.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_binent_20"]["fn"]


def prototype(close, length=LENGTH, bins=BINS):
    """`docs/issues/screen/ind_screen.py` candidate `ts_binent_20`, retyped
    verbatim because that tree is gitignored:

        @cand("ts_binent_20", ...)
        def _(o, h, l, c, v): return roll(ret(c), 20, w_binned_entropy)

        def w_binned_entropy(W, bins=5):
            lo = W.min(1, keepdims=True); hi = W.max(1, keepdims=True)
            rng = np.where(hi - lo == 0, np.nan, hi - lo)
            k = np.clip(np.floor((W - lo) / rng * bins), 0, bins - 1)
            h = np.zeros(len(W))
            for b in range(bins):
                p = (k == b).mean(1)
                h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1)), 0)
            return np.where(np.isnan(rng[:, 0]), np.nan, h)

    with `ret(c) = c / c.shift(1) - 1`, `_win` = `sliding_window_view` and
    `_from_win` writing the values at `n - 1:`."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    W = sliding_window_view(r, length)
    lo = W.min(1, keepdims=True)
    hi = W.max(1, keepdims=True)
    rng = np.where(hi - lo == 0, np.nan, hi - lo)
    k = np.clip(np.floor((W - lo) / rng * bins), 0, bins - 1)
    h = np.zeros(len(W))
    for b in range(bins):
        p = (k == b).mean(1)
        h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1)), 0)
    vals = np.where(np.isnan(rng[:, 0]), np.nan, h)
    out = np.full(len(r), np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


def histogram_definition(close, length=LENGTH, bins=BINS):
    """The source line's `binned_entropy(max_bins=bins)` spelled with numpy's
    own `np.histogram`, window by window: the histogram's bin shares, zeros
    replaced by 1 so an empty bin contributes nothing, Shannon entropy in
    nats. An independent implementation of equal-width binning -- it shares
    no window machinery and no bin arithmetic with the module.

    ⚠ This is the standard definition of binned entropy, NOT a read of
    tsfresh's source: tsfresh is not installed in this worktree and web
    access is unavailable."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    out = np.full(len(r), np.nan)
    for t in range(length, len(r)):
        w = r[t - length + 1:t + 1]
        if np.isnan(w).any():
            continue
        hist, _ = np.histogram(w, bins=bins)
        probs = hist / w.size
        probs = np.where(probs == 0.0, 1.0, probs)
        out[t] = float(-np.sum(probs * np.log(probs)))
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH, bins=BINS):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no sliding window, every count written out."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        w = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        lo, hi = min(w), max(w)
        span = hi - lo
        if not span > REAL.NOISE_FLOOR:
            continue
        counts = [0] * bins
        for v in w:
            k = int(math.floor((v - lo) / span * bins))
            counts[0 if k < 0 else (bins - 1 if k > bins - 1 else k)] += 1
        h = 0.0
        for n in counts:
            if n:
                p = n / length
                h -= p * math.log(p)
        out[t] = h
    return Series(out, index=close.index)


def variant(close, length=LENGTH, bins=BINS, log_returns=False,
            quantile_bins=False, normalise=False, degenerate_zero=False,
            guard=True):
    """The module's computation with ONE reading changed. Written as a
    per-window loop so a rejected reading cannot inherit the module's
    vectorised window arithmetic."""
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    r = np.full(c.size, np.nan)
    r[1:] = np.log(c[1:] / c[:-1]) if log_returns else c[1:] / c[:-1] - 1.0
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = r[t - length + 1:t + 1]
        if np.isnan(w).any():
            continue
        lo, hi = float(w.min()), float(w.max())
        span = hi - lo
        alive = span > REAL.NOISE_FLOOR if guard else span != 0.0
        if not alive:
            if degenerate_zero and span == 0.0:
                # numpy widens a zero-width range to [v - 0.5, v + 0.5], so
                # every sample lands in one bin and the entropy is exactly 0.
                out[t] = 0.0
            continue
        if quantile_bins:
            edges = np.quantile(w, np.linspace(0.0, 1.0, bins + 1))
            k = np.clip(np.searchsorted(edges[1:-1], w, side="right"),
                        0, bins - 1)
        else:
            k = np.clip(np.floor((w - lo) / span * bins), 0, bins - 1)
        p = np.array([(k == b).sum() for b in range(bins)], dtype=float) / length
        nz = p[p > 0.0]
        value = float(-(nz * np.log(nz)).sum())
        out[t] = value / math.log(bins) if normalise else value
    return Series(out, index=close.index)


def gate_a():
    head("Gate A -- correctness against the source formula")

    print("A1. hand-derived windows, exact in closed form")
    cases = [
        ("AT THE DEFAULTS (20, 5): 11 closes of 1, then five x1.5 steps, then "
         "five x2 steps -- 20 returns, ten +0, five +1/2, five +1, all exact "
         "in binary. lo=0 hi=1, bins of width 1/5, so k=floor(r*5) is "
         "0 / 2 / 5->4: bins [10,0,5,0,5], p=(1/2,1/4,1/4), "
         "h = (1/2)log2 + log2 = 1.5*log(2)",
         Series([1.0] * 11 + [1.5, 2.25, 3.375, 5.0625, 7.59375]
                + [15.1875, 30.375, 60.75, 121.5, 243.0]), 20, 5,
         1.5 * math.log(2.0)),
        ("close=[1,1,1,1,2] length=4 bins=4: returns [0,0,0,+1], bins "
         "[3,0,0,1], p=(3/4,1/4)",
         Series([1.0, 1.0, 1.0, 1.0, 2.0]), 4, 4,
         -(0.75 * math.log(0.75) + 0.25 * math.log(0.25))),
        ("close=[1,1,2,6,24] length=4 bins=4: returns [0,+1,+2,+3], bins "
         "[1,1,1,1], p=1/4 each",
         Series([1.0, 1.0, 2.0, 6.0, 24.0]), 4, 4, math.log(4.0)),
        ("close=[1,2,1,2,1] length=4 bins=2: returns [+1,-1/2,+1,-1/2], bins "
         "[2,2], p=(1/2,1/2)",
         Series([1.0, 2.0, 1.0, 2.0, 1.0]), 4, 2, math.log(2.0)),
    ]
    for text, close, length, bins, exact in cases:
        out = ts_binent_20(close, length=length, bins=bins)
        got = float(out.iloc[length])
        print(f"    {text}")
        print(f"      name={out.name} warmup_nan="
              f"{int(out.iloc[:length].isna().sum())}/{length} "
              f"module={got:.17g} exact={exact:.17g} "
              f"|diff|={abs(got - exact):.3e}")
    print(f"    the smallest value a NON-degenerate {LENGTH}-return window "
          f"can take is 19/1 across two bins = "
          f"{-(0.95 * math.log(0.95) + 0.05 * math.log(0.05)):.6f}; the "
          f"largest is the even split (four returns per bin), which in "
          f"float64 is one ulp "
          f"ABOVE log(5) -- see the `discreteness` section")

    print("A2. the screen prototype")
    close = walk()
    base = ts_binent_20(close)
    fn = screen_candidate()
    if fn is None:
        print("    docs/issues/screen/ind_screen.py absent -- skipped")
    else:
        volume = Series(np.full(len(close), 1000.0))
        proto = fn(close, close, close, close, volume)
        compare("imported prototype", base, Series(proto, index=close.index))
    compare("retyped prototype", base, prototype(close))

    print("A3. the definition spelled with numpy's own np.histogram")
    compare("np.histogram definition", base, histogram_definition(close))
    print("    the same, on a tick-rounded walk (ties and repeated returns)")
    tick = tick_rounded()
    compare("np.histogram definition", ts_binent_20(tick),
            histogram_definition(tick))

    print("A4. an independent scalar loop")
    short = walk(400, seed=5)
    compare("scalar loop", ts_binent_20(short), scalar_loop(short))

    print("A5. the readings the wording leaves open, each priced")
    for name, kwargs in [
            ("bins=3 instead of 5", {"bins": 3}),
            ("bins=10 instead of 5", {"bins": 10}),
            ("equal-FREQUENCY (quantile) bins", {"quantile_bins": True}),
            ("log returns", {"log_returns": True}),
            ("normalised by log(bins)", {"normalise": True}),
    ]:
        if "bins" in kwargs:
            other = variant(close, **kwargs)
            compare(name, ts_binent_20(close, bins=kwargs["bins"]), other)
            compare(f"  ^ and against the default bins=5", base,
                    ts_binent_20(close, bins=kwargs["bins"]))
        else:
            compare(name, base, variant(close, **kwargs))
    quantile = variant(close, quantile_bins=True).dropna()
    print(f"    the equal-FREQUENCY reading is a CONSTANT column by "
          f"construction -- {BINS} bins of {LENGTH // BINS} samples each give "
          f"p = 1/{BINS} every bar: distinct values "
          f"{int(quantile.nunique())}, bars at exactly log({BINS}) "
          f"{int((quantile - math.log(BINS)).abs().lt(1e-12).sum())}/"
          f"{len(quantile)}")
    factor = math.log(BINS)
    pure = variant(close, normalise=True)
    m = base.notna() & pure.notna()
    print(f"    normalising is a strict rescaling by 1/log(5) = "
          f"{1 / factor:.6f}: max |port / log(5) - normalised| = "
          f"{float((base[m] / factor - pure[m]).abs().max()):.3e}")

    print("A6. the degenerate window: NaN (this port) vs 0 (literal "
          "np.histogram, which widens a zero-width range)")
    # the widening itself, from numpy rather than from a sentence
    hist, edges = np.histogram(np.zeros(LENGTH), bins=BINS)
    print(f"    np.histogram(np.zeros({LENGTH}), bins={BINS}) -> counts "
          f"{list(hist)}, edges [{edges[0]:g} .. {edges[-1]:g}]: a zero-width "
          f"range is widened to [v-0.5, v+0.5] and every sample lands in the "
          f"middle bin, so the literal reading is -1*log(1) = 0")
    for name, frame in [("flat 300 closes", Series(np.full(300, 50.0))),
                        ("21 identical closes inside a 400-bar walk", None)]:
        if frame is None:
            frame = walk(400, seed=21).copy()
            frame.iloc[200:221] = float(frame.iloc[200])
        port = ts_binent_20(frame)
        # the real np.histogram path, which does NOT skip a zero-width window
        literal = histogram_definition(frame)
        zeros = int((literal == 0.0).sum())
        hand = variant(frame, guard=False, degenerate_zero=True)
        agree = bool((literal.isna() == hand.isna()).all()) and bool(
            (literal[literal.notna()] == hand[hand.notna()]).all())
        print(f"    {name}: port fires {int(port.notna().sum())}/{len(frame)}, "
              f"np.histogram reading fires {int(literal.notna().sum())}/"
              f"{len(frame)} of which {zeros} are exactly 0.0 "
              f"(the hand-written `degenerate_zero` variant agrees: {agree})")
    print("    on a continuous walk the two readings cannot differ:")
    compare("literal np.histogram reading", base,
            variant(close, guard=False, degenerate_zero=True))


# ----------------------------------------------------------------- Gate B

BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(np.isnan(width), np.nan, h)",
    "    out[length - 3:c.size - 2] = np.where(np.isnan(width), np.nan, h)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(np.isnan(width), np.nan, h)",
    "    out[:windows.shape[0]] = np.where(np.isnan(width), np.nan, h)")
FORWARD_RETURN = (
    "        r[1:] = c[1:] / c[:-1] - 1.0",
    "        r[:-1] = c[1:] / c[:-1] - 1.0")
ROLLED_WINDOW = (
    "    windows = sliding_window_view(r, length)",
    "    windows = sliding_window_view(np.roll(r, -(length // 2)), length)")
FORWARD_EDGE = (
    "    low = windows.min(axis=1)",
    "    low = np.roll(windows.min(axis=1), -length)")
FORWARD_EDGE_ONE = (
    "    low = windows.min(axis=1)",
    "    low = np.roll(windows.min(axis=1), -1)")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "rolled_window": ROLLED_WINDOW,
    "forward_edge": FORWARD_EDGE,
}
OFFSETS = list(range(40, 1500, 40))
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "heavy-tailed": (heavy_tailed(), heavy_tailed(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_binent_20_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def caught_offsets(fn, close, other):
    """Replace every bar from J onward with a different path; return the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


def leaks(fn, close, other):
    return len(caught_offsets(fn, close, other))


def missed(fn, close, other):
    hit = set(caught_offsets(fn, close, other))
    return [j for j in OFFSETS if j not in hit]


def bin_counts(w, bins=BINS):
    """The bin count vector of one window of returns, the quantity the value
    is a function of."""
    lo, hi = float(np.min(w)), float(np.max(w))
    k = np.clip(np.floor((w - lo) / (hi - lo) * bins), 0, bins - 1)
    return [int((k == b).sum()) for b in range(bins)]


def discrete_absorption():
    """Why a look-ahead mutant is NOT caught at every offset on every frame.
    The value is a function of the window's BIN COUNTS, which is a discrete
    quantity: a perturbation that changes a return without moving any sample
    across a bin edge leaves the value bit-identical. For the
    `forward_return` mutant the only prefix bar that can move at offset J is
    bar J-1, whose window ends at the perturbed return, so the mechanism can
    be shown exactly rather than argued."""
    head("Why a mutant misses an offset -- the column is a count statistic")
    cases = [("tick-rounded", tick_rounded(), tick_rounded(seed=56), LENGTH,
              [120]),
             ("walk, length=5", walk(), walk(seed=97), 5, [200, 400, 1000])]
    for name, close, other, length, offsets in cases:
        for j in offsets:
            p = close.copy()
            p.iloc[j:] = other.iloc[j:].values
            # the mutant stamps the return one bar early, so the window of
            # bar j-1 ends at the return of bar j: the one perturbed input.
            ra = (close / close.shift(1) - 1.0).to_numpy()
            rb = (p / p.shift(1) - 1.0).to_numpy()
            wa = ra[j - length + 1:j + 1]
            wb = rb[j - length + 1:j + 1]
            ca, cb = bin_counts(wa, min(BINS, length)), \
                bin_counts(wb, min(BINS, length))
            print(f"  {name} J={j}: the perturbed return differs "
                  f"({wa[-1]:.6e} -> {wb[-1]:.6e}, |diff| "
                  f"{abs(wb[-1] - wa[-1]):.3e}); bin counts of the window "
                  f"bar {j - 1} would read: {ca} -> {cb}, equal={ca == cb}, "
                  f"same multiset={sorted(ca) == sorted(cb)}")


def gate_b():
    head("Gate B -- causality by mutant")
    print(f"{len(OFFSETS)} future-perturbation offsets per cell, "
          f"{OFFSETS[0]}..{OFFSETS[-1]} step 40")
    for frame, (close, other) in FRAMES.items():
        print(f"  real module on {frame}: leaks "
              f"{leaks(ts_binent_20, close, other)}/{len(OFFSETS)}")
    for name, mutation in MUTANTS.items():
        mod = load_mutant(*mutation)
        for frame, (close, other) in FRAMES.items():
            live = not mod.ts_binent_20(close).equals(ts_binent_20(close))
            miss = missed(mod.ts_binent_20, close, other)
            print(f"  mutant {name} on {frame}: changes-the-column={live} "
                  f"caught {len(OFFSETS) - len(miss)}/{len(OFFSETS)}"
                  + (f" missed J={miss}" if miss else ""))

    print("  a SUBTLE look-ahead, and how often the sweep sees it: the bin "
          "edge taken from the NEXT window (roll -1) instead of a whole "
          "window ahead")
    mod = load_mutant(*FORWARD_EDGE_ONE)
    for frame, (close, other) in FRAMES.items():
        miss = missed(mod.ts_binent_20, close, other)
        r = (close / close.shift(1) - 1.0).to_numpy()
        W = sliding_window_view(r, LENGTH)
        mins = W.min(axis=1)
        same = int((mins[:-1] == mins[1:]).sum())
        print(f"    one-bar edge leak on {frame}: caught "
              f"{len(OFFSETS) - len(miss)}/{len(OFFSETS)}; consecutive "
              f"windows sharing their minimum: {same}/{len(mins) - 1}")

    print("  non-default parameters, on the walk")
    pair = FRAMES["walk"]
    for name, mutation in MUTANTS.items():
        mod = load_mutant(*mutation)
        for length, bins in ((20, 5), (20, 10), (60, 5), (5, 5)):
            def real(c, length=length, bins=bins):
                return ts_binent_20(c, length=length, bins=bins)

            def mutated(c, length=length, bins=bins, mod=mod):
                return mod.ts_binent_20(c, length=length, bins=bins)

            base, mut = real(pair[0]), mutated(pair[0])
            miss = missed(mutated, *pair)
            print(f"    {name} at length={length} bins={bins}: real leaks "
                  f"{leaks(real, *pair)}/{len(OFFSETS)}, mutant caught "
                  f"{len(OFFSETS) - len(miss)}/{len(OFFSETS)}"
                  + (f" missed J={miss}" if miss else "")
                  + f"; mutant-equals-real={bool(mut.equals(base))}; prefix "
                  f"[0:{OFFSETS[0]}] all-NaN real="
                  f"{bool(base.iloc[:OFFSETS[0]].isna().all())} mutant="
                  f"{bool(mut.iloc[:OFFSETS[0]].isna().all())}")

    close = walk(400, seed=3)
    base = ts_binent_20(close)
    print("  offset=2 equals shift(2): "
          f"{base.shift(2).equals(ts_binent_20(close, offset=2))}")
    print("  offset=-2 equals shift(-2): "
          f"{base.shift(-2).equals(ts_binent_20(close, offset=-2))}")


# ------------------------------------------------------------ noise floor


def noise_floor():
    head("The noise floor -- why `max - min != 0` is not enough")
    print(f"  NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR:.17g}")
    for name, frame in [("1%-a-bar geometric ladder", geometric_ladder()),
                        ("exact x1.5 ladder",
                         Series(np.cumprod(np.full(300, 1.5)) * 1e-20)),
                        ("flat 300 bars", Series(np.full(300, 50.0)))]:
        guarded = ts_binent_20(frame)
        unguarded = variant(frame, guard=False)
        fired = unguarded.dropna()
        span = (f"[{float(fired.min()):.4f}, {float(fired.max()):.4f}]"
                if len(fired) else "-")
        # the live range of a real 1,500-bar walk, for comparison: an
        # unguarded value inside it is indistinguishable from a reading
        live = ts_binent_20(walk()).dropna()
        lo, hi = float(live.min()), float(live.max())
        inside = (int(fired.between(lo, hi).sum()) if len(fired) else 0)
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}/"
              f"{len(frame)}, unguarded fires {len(fired)}/{len(frame)}, "
              f"unguarded range {span}, of which {inside} fall inside a real "
              f"walk's live range [{lo:.4f}, {hi:.4f}]")
    for name, frame in [("walk", walk(300)),
                        ("tick-rounded", tick_rounded(300))]:
        guarded, unguarded = ts_binent_20(frame), variant(frame, guard=False)
        same = bool((guarded.isna() == unguarded.isna()).all())
        m = guarded.notna()
        print(f"  {name}: guarded fires {int(m.sum())}/{len(frame)}, "
              f"masks agree {same}, values identical "
              f"{bool((guarded[m] == unguarded[m]).all())}")


def floor_crossover():
    head("Where the noise floor stops reading variation")
    rng = np.random.default_rng(99)
    for jitter in (1e-16, 1e-14, 1e-12, 1e-11, 1e-9):
        r = 0.01 + jitter * rng.standard_normal(1500)
        frame = Series(100.0 * np.exp(np.cumsum(r)))
        guarded = int(ts_binent_20(frame).notna().sum())
        unguarded = int(variant(frame, guard=False).notna().sum())
        print(f"  jitter +-{jitter:.0e}: guarded fires {guarded}/1500, "
              f"unguarded {unguarded}/1500")


def tick_grid_floor():
    """What the floor does to a MONOTONE one-tick-per-bar path. The floor
    bounds the RANGE of the window's returns, which on such a path is far
    smaller than `tick / price`: the returns themselves are about
    `tick / price` but they differ from each other only in the next digits."""
    head("The floor against a monotone one-tick-per-bar path")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = (closes / closes.shift(1) - 1.0).to_numpy()
        w = r[-LENGTH:]
        rng_w = float(w.max() - w.min())
        fires = int(ts_binent_20(closes).notna().sum())
        print(f"  price={price:g} tick={tick:g}: |r| ~ {float(r[-1]):.3e}, "
              f"max-min of the last {LENGTH} returns = {rng_w:.3e} vs floor "
              f"{REAL.NOISE_FLOOR:.3e} -> fires {fires}/{len(closes)}")


# -------------------------------------------------------------- Gates C/D


def gate_c_d():
    head("Gates C/D -- reachability and scale-freeness")
    for name, frame in [("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("heavy-tailed", heavy_tailed())]:
        base = ts_binent_20(frame)
        fires = int(base.notna().sum())
        print(f"  {name}: fires {fires}/{len(frame)} "
              f"(0 < fires < n is {0 < fires < len(frame)}), "
              f"distinct {int(base.nunique())}, "
              f"non-zero among fired {int((base.dropna() != 0).sum())}, "
              f"range [{float(base.min()):.4f}, {float(base.max()):.4f}]")
        for k in (8.0, 64.0):
            scaled = ts_binent_20(frame * k)
            m = base.notna()
            print(f"    x{k:g}: masks agree "
                  f"{bool((base.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((base[m] == scaled[m]).sum())}/{int(m.sum())}")
        for k in (10.0, 3.7):
            scaled = ts_binent_20(frame * k)
            m = base.notna() & scaled.notna()
            print(f"    x{k:g}: masks agree "
                  f"{bool((base.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((base[m] == scaled[m]).sum())}/{int(m.sum())}, "
                  f"max|diff| {float((base[m] - scaled[m]).abs().max()):.3e}")

    print("  non-default parameters, x8/x64 on the walk")
    frame = walk()
    for length, bins in ((20, 10), (60, 5), (5, 5)):
        base = ts_binent_20(frame, length=length, bins=bins)
        m = base.notna()
        for k in (8.0, 64.0):
            scaled = ts_binent_20(frame * k, length=length, bins=bins)
            print(f"    length={length} bins={bins} x{k:g}: fires "
                  f"{int(m.sum())}, masks agree "
                  f"{bool((base.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((base[m] == scaled[m]).sum())}/{int(m.sum())}")

    print("  why the return is spelled as a price RATIO")
    close = walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    print(f"    ratio returns at x8: bit-equal "
          f"{int((ratio[m] == ratio8[m]).sum())}/{int(m.sum())}")
    print(f"    difference-of-logarithms returns at x8: bit-equal "
          f"{int((plain[m] == plain8[m]).sum())}/{int(m.sum())}")


def invariances():
    head("What the column is invariant to, and what that costs")
    close = walk()
    base = ts_binent_20(close)
    print("  the value depends on the window's returns only through an "
          "AFFINE map: bins are laid out between the window's own min and "
          "max, so r -> a*r + b (a > 0) leaves every bin share unchanged.")
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    compare("+0.004 log drift a bar (r -> e^d*r + (e^d - 1), affine)",
            base, ts_binent_20(drifted))
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    for k in (0.5, 3.0):
        compare(f"returns scaled x{k:g} (r -> k*r, affine)",
                ts_binent_20(from_returns(r)), ts_binent_20(from_returns(k * r)))
    print("  so it is NOT a volatility proxy: the same shape at any "
          "amplitude reads the same value.")


def discreteness():
    head("The column's attainable set -- a count statistic, heavily tied")
    attainable = set()
    vectors = 0
    for counts in itertools.product(range(LENGTH + 1), repeat=BINS):
        if sum(counts) != LENGTH or counts[0] < 1 or counts[-1] < 1:
            continue
        vectors += 1
        h = 0.0
        for n in counts:
            if n:
                p = n / LENGTH
                h -= p * math.log(p)
        attainable.add(round(h, 12))
    print(f"  count vectors over {BINS} bins summing to {LENGTH} with the "
          f"first and last bin occupied (the min and max always are): "
          f"{vectors}")
    print(f"  distinct entropy values among them: {len(attainable)}")
    print(f"  min {min(attainable):.6f} max {max(attainable):.6f} "
          f"(log({BINS}) = {math.log(BINS):.6f})")
    # the multiset enumeration is the one the test uses, because it is 53,130
    # candidates rather than 4.1 million; both must give the same set.
    multisets = set()
    for counts in itertools.combinations_with_replacement(
            range(LENGTH + 1), BINS):
        if sum(counts) != LENGTH or sum(1 for n in counts if n) < 2:
            continue
        h = 0.0
        for n in counts:
            if n:
                p = n / LENGTH
                h -= p * math.log(p)
        multisets.add(round(h, 12))
    print(f"  the same set enumerated over count MULTISETS (the entropy is "
          f"symmetric in the counts): {len(multisets)} values, identical set="
          f"{multisets == attainable}")
    # the top of the range in float64, which is NOT math.log(bins)
    even = 0.0
    for _ in range(BINS):
        even -= (1.0 / BINS) * math.log(1.0 / BINS)
    top = float(ts_binent_20(walk()).max())
    ulps = (even - math.log(BINS)) / np.spacing(math.log(BINS))
    print(f"  the even split, four returns per bin, accumulated in the "
          f"module's order, is "
          f"{even:.17g}; math.log({BINS}) is {math.log(BINS):.17g}, i.e. the "
          f"attainable maximum sits {ulps:.0f} ulp ABOVE log({BINS}) in "
          f"float64. The walk's observed maximum is {top:.17g} (equal to the "
          f"accumulated even split: {top == even})")
    print("  ⚠ the 182 is a count of values ROUNDED to 1e-12. The module "
          "accumulates the terms in bin order, so two count vectors that are "
          "permutations of each other land on different last bits and the "
          "RAW float64 output has more distinct values than the entropy "
          "function does:")
    for name, frame in [("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("heavy-tailed", heavy_tailed())]:
        out = ts_binent_20(frame).dropna()
        observed = set(round(float(v), 12) for v in out)
        print(f"  {name}: {len(out)} fired bars take {int(out.nunique())} "
              f"distinct float64 values, {len(observed)} after rounding to "
              f"1e-12, and the rounded ones are all inside the attainable "
              f"set: {observed.issubset(attainable)} (raw values inside it: "
              f"{set(float(v) for v in out).issubset(attainable)})")


def distributions():
    head("Gate C (synthetic) -- the distribution on each path")
    paths = [
        ("uniform returns", uniform_returns()),
        ("gaussian walk", walk()),
        ("tick-rounded walk", tick_rounded()),
        ("laplace returns", laplace_returns()),
        ("student-t(2) returns", heavy_tailed()),
        ("two-point returns (+-sigma)", two_point()),
    ]
    for name, frame in paths:
        out = ts_binent_20(frame).dropna()
        print(f"  {name}: n={len(out)} distinct={int(out.nunique())} "
              f"min={out.min():.4f} p10={np.percentile(out, 10):.4f} "
              f"median={out.median():.4f} p90={np.percentile(out, 90):.4f} "
              f"max={out.max():.4f} spread(max-min)="
              f"{float(out.max() - out.min()):.3e}")


def meaning():
    head("What the column means")
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (2000, LENGTH + 1)),
                                     axis=1))
    est = np.array([float(ts_binent_20(Series(p)).iloc[-1]) for p in paths])
    print(f"  2,000 independent {LENGTH}-return iid gaussian windows: "
          f"median {np.median(est):.4f} mean {est.mean():.4f} "
          f"sd {est.std(ddof=1):.4f} p10 {np.percentile(est, 10):.4f} "
          f"p90 {np.percentile(est, 90):.4f} "
          f"finite {int(np.isfinite(est).sum())}/2000 "
          f"distinct {len(set(np.round(est, 12)))}")

    print("  one outlier is what drives it down: the bins span the window's "
          "own [min, max], so a single large move puts every other return "
          "in the first bin")
    close = walk(400, seed=21)
    base = ts_binent_20(close)
    two_bin = -(0.95 * math.log(0.95) + 0.05 * math.log(0.05))
    r = (close / close.shift(1) - 1.0).to_numpy()
    for size in (10.0, 50.0):
        spiked = close.copy()
        factor = 1.0 + size * float(np.nanstd(r))
        spiked.iloc[200:] = spiked.iloc[200:] * factor
        out = ts_binent_20(spiked)
        touched = out.iloc[200:200 + LENGTH]
        hits = int((touched - two_bin).abs().lt(1e-12).sum())
        print(f"    a single +{size:g}-sigma return at bar 200: the "
              f"{LENGTH} windows holding it read median "
              f"{float(touched.median()):.4f} against the frame's "
              f"{float(base.median()):.4f}; {hits}/{LENGTH} of them are "
              f"exactly the 19/1 two-bin value {two_bin:.6f}")

    print("  it orders concentration, measured as medians over 1,500-bar "
          "paths whose returns differ in SHAPE; the return sd is printed "
          "alongside and does not explain the ordering")
    for name, frame in [("uniform", uniform_returns()),
                        ("gaussian", walk()),
                        ("laplace", laplace_returns()),
                        ("student-t(2)", heavy_tailed()),
                        ("two-point", two_point())]:
        out = ts_binent_20(frame).dropna()
        r = (frame / frame.shift(1) - 1.0).dropna()
        print(f"    {name}: median {float(out.median()):.4f} "
              f"(return sd {float(r.std()):.4f}, excess kurtosis "
              f"{float(r.kurt()):.2f})")


# ------------------------------------------------------------ edge, guards


def guards():
    head("Guards and edges")
    print(f"  {LENGTH} closes -> {ts_binent_20(walk(LENGTH))}")
    out = ts_binent_20(walk(LENGTH + 1, seed=2))
    print(f"  {LENGTH + 1} closes: fires {int(out.notna().sum())}, first at "
          f"{int(out.notna().to_numpy().argmax())}")
    for length in (None, 0, -5, 2, 0.5, 2.9):
        print(f"  length={length!r} -> "
              f"{ts_binent_20(walk(400, seed=31), length=length).name}")
    for bins in (None, 0, 1, -3, 2, 3, 10, 20, 21, 50):
        o = ts_binent_20(walk(400, seed=31), bins=bins)
        print(f"  bins={bins!r} -> {o.name}, fires {int(o.notna().sum())}, "
              f"distinct {int(o.nunique())}")
    print("  length=3 clamps bins to 3: "
          f"{ts_binent_20(walk(400, seed=31), length=3, bins=50).name}")
    print("  why MIN_LENGTH is 3: a window of 2 returns puts its min in the "
          "first bin and its max in the last, one sample each, so the value "
          "cannot vary")
    for length in (2, 3):
        other = variant(walk(400, seed=31), length=length).dropna()
        print(f"    length={length} (computed by the per-window variant, "
              f"which the module refuses below 3): n={len(other)} distinct="
              f"{int(other.nunique())} min={float(other.min()):.6f} "
              f"max={float(other.max()):.6f} log(2)={math.log(2.0):.6f}")
    a = ts_binent_20(walk(400, seed=31), length=50.9)
    b = ts_binent_20(walk(400, seed=31), length=50)
    print(f"  length=50.9 equals length=50: {a.equals(b)}")
    close = walk(400, seed=31)
    x, y = ts_binent_20(close, length=10), ts_binent_20(close, length=60)
    m = x.notna() & y.notna()
    print(f"  length 10 vs 60: names {x.name}/{y.name}, spearman "
          f"{float(x[m].corr(y[m], method='spearman')):.4f}")
    filled = ts_binent_20(walk(200, seed=13), fillna=-1.0)
    print(f"  fillna=-1.0 fills {int((filled == -1.0).sum())} bars")

    print("  bins above `length` would saturate: how different is an "
          "UNCLAMPED bins from the clamp at `length`?")
    for bins in (20, 40, 100):
        other = variant(close, bins=bins)
        clamped = ts_binent_20(close, bins=bins)
        compare(f"    unclamped bins={bins} vs the module (clamped to "
                f"{LENGTH})", clamped, other)

    close = walk(400, seed=21)
    base = ts_binent_20(close)
    print("  a flat run planted inside a live frame: how many closes it takes")
    two_bin = -(0.95 * math.log(0.95) + 0.05 * math.log(0.05))
    for k in (20, 21, 25):
        flat = close.copy()
        flat.iloc[200:200 + k] = float(close.iloc[200])
        out = ts_binent_20(flat)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        where = (f"[{int(emptied.min())}, {int(emptied.max())}]"
                 if len(emptied) else "-")
        at_219 = float(out.iloc[219])
        print(f"    {k} identical closes at 200: empties {len(emptied)} bars "
              f"{where}; bar 219 reads {at_219:.6f} "
              f"(the 19-zeros-and-one-move two-bin value is {two_bin:.6f})")
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = close.copy()
        holed.iloc[200] = bad
        out = ts_binent_20(holed)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        before = base.notna() & out.notna() & (base != out)
        print(f"  close[200]={bad!r}: empties {len(emptied)} bars "
              f"[{int(emptied.min())}, {int(emptied.max())}], bars before 200 "
              f"that move {int(before.iloc[:200].sum())}")

    # A pair of GOOD closes whose RATIO overflows: the one float error left
    # after the close guard. Unguarded, the infinite return would make the
    # window's range infinite, put the nineteen finite samples in the first
    # bin and the infinite one in no bin at all -- a finite value below the
    # two-bin floor.
    holed = close.copy()
    holed.iloc[200] = 1e-300
    holed.iloc[201] = 1e50
    out = ts_binent_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    before = base.notna() & out.notna() & (base != out)
    # `variant` has no isfinite cleanup, so it IS the unguarded path: run it
    # rather than typing the closed form.
    with np.errstate(over="ignore", invalid="ignore"):
        unguarded = variant(holed).iloc[201:221]
    print(f"  close[200]=1e-300, close[201]=1e50 (ratio overflows to inf): "
          f"empties {len(emptied)} bars [{int(emptied.min())}, "
          f"{int(emptied.max())}], bars before 200 that move "
          f"{int(before.iloc[:200].sum())}, lowest fired value "
          f"{float(out.min()):.6f} vs the two-bin floor "
          f"{-(0.95 * math.log(0.95) + 0.05 * math.log(0.05)):.6f}")
    print(f"    unguarded, the same 20 windows report "
          f"[{float(unguarded.min()):.6f}, {float(unguarded.max()):.6f}] "
          f"on {int(unguarded.notna().sum())}/20 bars -- finite, below the "
          f"floor, and nothing downstream would question it")


def neighbours():
    head("Nearest shipped columns on ONE synthetic walk -- NOT Gate E")
    import pandas as pd
    import pandas_ta as ta  # noqa: F401  (registers the accessors)

    close = walk()
    high, low = close * 1.01, close * 0.99
    base = ts_binent_20(close)
    others = {
        "entropy_20": ta.entropy(close, length=20),
        "entlz_20": ta.entlz(close),
        "skew_30": ta.skew(close, length=30),
        "kurtosis_30": ta.kurtosis(close, length=30),
        "zscore_30": ta.zscore(close, length=30),
        "kpss_100": ta.kpss(close),
        "lean_hurst_100": ta.lean_hurst_100(close),
        "lean_momersion_20": ta.lean_momersion_20(close),
        "tf_centroid_20": ta.tf_centroid_20(close),
        "osap_retskew_21": ta.osap_retskew_21(close),
        "ts_c3_20": ta.ts_c3_20(close),
        "cusum_100": ta.cusum(close),
        "rsi_14": ta.rsi(close, length=14),
        "natr_14": ta.natr(high, low, close, length=14),
    }
    rows = []
    for name, col in others.items():
        if col is None:
            print(f"  {name}: returned None -- skipped")
            continue
        if isinstance(col, pd.DataFrame):
            col = col.iloc[:, 0]
        m = base.notna() & col.notna()
        rho = float(base[m].corr(col[m], method="spearman"))
        rows.append((abs(rho), name, int(m.sum())))
    for a, name, n in sorted(rows, reverse=True):
        print(f"  |rho| {a:.4f} vs {name} (n={n})")


def cost():
    """The module materialises one (n - length + 1, length) array of bin
    indices, so its memory is O(n * length) rather than O(n). Measured here
    because the engine calls it per frame and a reader should know the shape
    of the cost."""
    import time
    import tracemalloc

    head("Cost -- the window array is O(n * length)")
    print("  'index array' is arithmetic from the shape; 'traced peak' is "
          "measured with tracemalloc, which numpy's allocator reports into")
    for n in (10_000, 100_000, 400_000):
        frame = walk(n, seed=2)
        tracemalloc.start()
        t0 = time.perf_counter()
        out = ts_binent_20(frame)
        dt = time.perf_counter() - t0
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"  n={n}: {dt * 1000:.0f} ms, fires {int(out.notna().sum())}, "
              f"index array {(n - LENGTH + 1) * LENGTH * 8 / 1e6:.1f} MB "
              f"(computed), traced peak {peak / 1e6:.1f} MB (measured)")


SECTIONS = {
    "gate_a": gate_a,
    "gate_b": gate_b,
    "discrete_absorption": discrete_absorption,
    "noise_floor": noise_floor,
    "floor_crossover": floor_crossover,
    "tick_grid_floor": tick_grid_floor,
    "gate_c_d": gate_c_d,
    "invariances": invariances,
    "discreteness": discreteness,
    "distributions": distributions,
    "meaning": meaning,
    "neighbours": neighbours,
    "guards": guards,
    "cost": cost,
}

if __name__ == "__main__":
    import sys

    wanted = [a for a in sys.argv[1:] if a in SECTIONS] or list(SECTIONS)
    for key in wanted:
        SECTIONS[key]()
    print()
