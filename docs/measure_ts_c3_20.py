# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsC320Measured.md for `ts_c3_20`
(PandasTa issue #88, TS-C3-20).

Run from the repository root:

    python docs/measure_ts_c3_20.py

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import math
import types

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_c3_20 import ts_c3_20

LENGTH, LAG = 20, 1
TRIPLES = LENGTH - 2 * LAG
REAL = importlib.import_module("pandas_ta.statistics.ts_c3_20")


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


def nonlinear(n=1500, seed=7, sigma=0.01, a=0.5):
    """A path whose LOG returns are
    `rlog[t] = eps[t] + a * eps[t-1] * eps[t-2] / sigma`, whose population
    third-order autocorrelation `E[rlog_t rlog_{t-1} rlog_{t-2}]` is
    `a * sigma^3`: the smallest process with a non-zero c3 of the
    generator's log returns that is otherwise a walk. The column reads
    SIMPLE returns, which is not the same series."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = eps.copy()
    r[2:] = eps[2:] + a * eps[1:-1] * eps[:-2] / sigma
    return Series(100.0 * np.exp(np.cumsum(r)))


def geometric_ladder(n=300, step=0.01):
    return Series(100.0 * np.exp(np.arange(n) * step))


def alternating(n=1500, small=0.002, large=0.02):
    """Returns alternate between a small and a large move, every other one
    down: a deterministic path whose triples do not average to zero."""
    r = np.where(np.arange(n) % 2 == 0, large, -small)
    return Series(100.0 * np.exp(np.cumsum(r)))


def compare(name, a, b):
    """Max |difference|, bit-equal count and Spearman over the shared
    non-NaN bars, plus whether the NaN masks agree."""
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    rho = float(x.corr(y, method="spearman")) if len(x) > 2 else float("nan")
    print(f"  {name}: n={int(m.sum())} max|diff|={float(diff.max()):.6e} "
          f"bit-equal={bit}/{int(m.sum())} spearman={rho:.6f} "
          f"nan-masks-agree={masks_agree}")
    return float(diff.max()), bit, rho, masks_agree


# ----------------------------------------------------------------- Gate A


def screen_candidate():
    """`REG["ts_c3_20"]["fn"]` out of the screen's own registry, when this
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
    return mod.REG["ts_c3_20"]["fn"]


def prototype(close, length=LENGTH, lag=LAG):
    """`docs/issues/screen/ind_screen.py` candidate `ts_c3_20`, retyped
    verbatim:

        def _(o, h, l, c, v):
            r = ret(c)
            return sdiv(mean(r * delay(r, 1) * delay(r, 2), 18), std(r, 20) ** 3)

    with `ret(c) = c / c.shift(1) - 1`, `delay(x, n) = x.shift(n)`,
    `mean(x, n) = x.rolling(n).mean()`, `std(x, n) = x.rolling(n).std()` and
    `sdiv(a, b) = (a / b).replace([inf, -inf], nan)`."""
    r = close / close.shift(1) - 1
    num = (r * r.shift(lag) * r.shift(2 * lag)).rolling(length - 2 * lag).mean()
    out = num / r.rolling(length).std() ** 3
    return out.replace([np.inf, -np.inf], np.nan)


def c3_windowed(close, length=LENGTH, lag=LAG):
    """The issue's line applied window by window with
    `sliding_window_view`: inside each window of `length` returns, average
    `x[i] * x[i+lag] * x[i+2*lag]` over the `length - 2*lag` triples that
    fit, then divide by the window's own sample standard deviation cubed.
    No pandas rolling anywhere, so it shares no window machinery with the
    module."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    out = np.full(len(r), np.nan)
    if len(r) < length + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], length)
    k = 2 * lag
    num = (W[:, k:] * W[:, lag:W.shape[1] - lag] * W[:, :-k]).mean(axis=1)
    sd = W.std(axis=1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        vals = np.where(sd > REAL.NOISE_FLOOR, num / sd ** 3, np.nan)
    out[length:] = vals
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH, lag=LAG):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no pandas rolling, every sum written out."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        r = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        triples = [r[i] * r[i - lag] * r[i - 2 * lag]
                   for i in range(2 * lag, length)]
        num = sum(triples) / len(triples)
        mu = sum(r) / len(r)
        var = sum((v - mu) ** 2 for v in r) / (len(r) - 1)
        sd = math.sqrt(var)
        if sd > REAL.NOISE_FLOOR:
            out[t] = num / sd ** 3
    return Series(out, index=close.index)


def variant(close, length=LENGTH, lag=LAG, ddof=1, cross_window=False,
            log_returns=False, sd_window=None, guard=True):
    """The module's computation with ONE reading changed."""
    px = close.astype(float)
    if log_returns:
        r = np.log(px / px.shift(1))
    else:
        r = px / px.shift(1) - 1.0
    triples = length - 2 * lag
    width = length if cross_window else triples
    num = (r * r.shift(lag) * r.shift(2 * lag)) \
        .rolling(width, min_periods=width).mean()
    sd = r.rolling(sd_window or length,
                   min_periods=sd_window or length).std(ddof=ddof)
    denominator = sd.where(sd > REAL.NOISE_FLOOR) if guard else sd
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / denominator ** 3
    return out.replace([np.inf, -np.inf], np.nan)


def gate_a():
    head("Gate A -- correctness against the source formula")

    print("A1. hand-derived window, exact in closed form")
    print("    close = [1, 2, 1, 2, 1] at length=4, lag=1")
    print("    returns r = [+1, -1/2, +1, -1/2]")
    print("    triples  = r3*r2*r1 = -1/2 and r4*r3*r2 = +1/4, mean -1/8")
    print("    sd(ddof=1) of r: mean 1/4, sum sq dev 9/4, var 3/4,"
          " sd sqrt(3)/2")
    print("    value = (-1/8) / (3/4)^1.5 = -1/(3*sqrt(3)) = -sqrt(3)/9")
    out = ts_c3_20(Series([1.0, 2.0, 1.0, 2.0, 1.0]), length=4, lag=1)
    exact = -1.0 / (3.0 * math.sqrt(3.0))
    print(f"    name={out.name} warmup_nan={int(out.iloc[:4].isna().sum())}/4")
    print(f"    module={float(out.iloc[4]):.17g} exact={exact:.17g} "
          f"|diff|={abs(float(out.iloc[4]) - exact):.3e}")

    print("A2. the screen prototype, imported from docs/issues/screen "
          "(gitignored)")
    close = walk()
    base = ts_c3_20(close)
    fn = screen_candidate()
    if fn is None:
        print("    docs/issues/screen/ind_screen.py absent -- skipped")
    else:
        o = h = l = close
        proto = fn(o, h, l, close, Series(np.full(len(close), 1000.0)))
        compare("imported prototype", base, Series(proto, index=close.index))
    compare("retyped prototype", base, prototype(close))

    print("A3. the issue's line, applied window by window")
    compare("sliding-window c3", base, c3_windowed(close))

    print("A4. an independent scalar loop")
    short = walk(400, seed=5)
    compare("scalar loop", ts_c3_20(short), scalar_loop(short))

    print("A5. the readings the wording leaves open, each priced")
    for name, kwargs in [
            ("ddof=0 (population sd)", {"ddof": 0}),
            ("numerator over a full `length` window", {"cross_window": True}),
            ("log returns", {"log_returns": True}),
            (f"sd over the {TRIPLES} returns the triples span",
             {"sd_window": TRIPLES}),
    ]:
        other = variant(close, **kwargs)
        compare(name, base, other)
    # sd(ddof=0) = sd(ddof=1) * sqrt((n-1)/n), so dividing by its cube
    # multiplies the column by ((n-1)/n)^-1.5.
    factor = ((LENGTH - 1) / LENGTH) ** -1.5
    print(f"    ddof=0 is a strict rescaling by ((n-1)/n)^-1.5 = {factor:.6f}")
    pop = variant(close, ddof=0)
    m = base.notna() & pop.notna()
    print("    max |port * factor - ddof0| = "
          f"{float((base[m] * factor - pop[m]).abs().max()):.3e}")
    cross = variant(close, cross_window=True)
    print("    first fired bar: port "
          f"{int(base.notna().to_numpy().argmax())}, full-window numerator "
          f"{int(cross.notna().to_numpy().argmax())}")


# ----------------------------------------------------------------- Gate B

WRITE_SHIFT_MUTANT = (
    "    c3 = numerator / (sd.where(sd > NOISE_FLOOR) ** 3)",
    "    c3 = (numerator / (sd.where(sd > NOISE_FLOOR) ** 3)).shift(-length)")
FORWARD_TRIPLE_MUTANT = (
    "    triple = r * r.shift(lag) * r.shift(2 * lag)",
    "    triple = r * r.shift(-lag) * r.shift(-2 * lag)")
FORWARD_RETURN_MUTANT = (
    "    r = px / px.shift(1) - 1.0",
    "    r = px.shift(-1) / px - 1.0")
CENTERED_MEAN_MUTANT = (
    "    numerator = triple.rolling(triples, min_periods=triples).mean()",
    "    numerator = triple.rolling(triples, min_periods=triples, "
    "center=True).mean()")
CENTERED_SD_MUTANT = (
    "    sd = r.rolling(length, min_periods=length).std(ddof=1)",
    "    sd = r.rolling(length, min_periods=length, center=True).std(ddof=1)")

MUTANTS = {
    "write_shift": WRITE_SHIFT_MUTANT,
    "forward_triple": FORWARD_TRIPLE_MUTANT,
    "forward_return": FORWARD_RETURN_MUTANT,
    "centered_mean": CENTERED_MEAN_MUTANT,
    "centered_sd": CENTERED_SD_MUTANT,
}
OFFSETS = list(range(40, 1500, 40))
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "nonlinear": (nonlinear(), nonlinear(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_c3_20_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close, other):
    """Replace every bar from J onward with a different path; count the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def gate_b():
    head("Gate B -- causality by mutant")
    print(f"{len(OFFSETS)} future-perturbation offsets per cell, "
          f"{OFFSETS[0]}..{OFFSETS[-1]} step 40")
    for frame, (close, other) in FRAMES.items():
        print(f"  real module on {frame}: leaks "
              f"{leaks(ts_c3_20, close, other)}/{len(OFFSETS)}")
    for name, mutation in MUTANTS.items():
        mod = load_mutant(*mutation)
        for frame, (close, other) in FRAMES.items():
            live = not mod.ts_c3_20(close).equals(ts_c3_20(close))
            print(f"  mutant {name} on {frame}: changes-the-column={live} "
                  f"caught {leaks(mod.ts_c3_20, close, other)}/{len(OFFSETS)}")

    print("  non-default parameters, the three parameter-dependent mutants")
    walk_pair = FRAMES["walk"]
    for mutant_name in ("forward_triple", "centered_mean", "write_shift"):
        mod = load_mutant(*MUTANTS[mutant_name])
        for length, lag in ((20, 1), (20, 9), (60, 1)):
            def real(c, length=length, lag=lag):
                return ts_c3_20(c, length=length, lag=lag)

            def mutated(c, length=length, lag=lag, mod=mod):
                return mod.ts_c3_20(c, length=length, lag=lag)

            triples = length - 2 * lag
            base, mut = real(walk_pair[0]), mutated(walk_pair[0])
            print(f"    length={length} lag={lag} (triples={triples}): real "
                  f"leaks {leaks(real, *walk_pair)}/{len(OFFSETS)}, "
                  f"{mutant_name} caught "
                  f"{leaks(mutated, *walk_pair)}/{len(OFFSETS)}; "
                  f"mutant-equals-real={bool(mut.equals(base))}; prefix "
                  f"[0:{OFFSETS[0]}] all-NaN real="
                  f"{bool(base.iloc[:OFFSETS[0]].isna().all())} "
                  f"mutant={bool(mut.iloc[:OFFSETS[0]].isna().all())}")

    close = walk(400, seed=3)
    base = ts_c3_20(close)
    print("  offset=2 equals shift(2): "
          f"{base.shift(2).equals(ts_c3_20(close, offset=2))}")
    print("  offset=-2 equals shift(-2): "
          f"{base.shift(-2).equals(ts_c3_20(close, offset=-2))}")


# ------------------------------------------------------------ noise floor


def noise_floor():
    head("The noise floor -- why `sd != 0` is not enough")
    print(f"  NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR:.17g}")
    src = open(REAL.__file__, encoding="utf-8").read()
    print(f"  rolling calls in the module: {src.count('.rolling(')}")
    for name, frame in [("1%-a-bar geometric ladder", geometric_ladder()),
                        ("exact x1.5 ladder",
                         Series(np.cumprod(np.full(300, 1.5)) * 1e-20)),
                        ("flat 300 bars", Series(np.full(300, 50.0)))]:
        guarded = ts_c3_20(frame)
        unguarded = variant(frame, guard=False)
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}/"
              f"{len(frame)}, unguarded fires {int(unguarded.notna().sum())}/"
              f"{len(frame)}, max |unguarded| "
              f"{float(unguarded.abs().max()):.3e}")
    for name, frame in [("walk", walk(300)), ("tick-rounded", tick_rounded(300))]:
        guarded, unguarded = ts_c3_20(frame), variant(frame, guard=False)
        same = bool((guarded.isna() == unguarded.isna()).all())
        m = guarded.notna()
        print(f"  {name}: guarded fires {int(m.sum())}/{len(frame)}, "
              f"masks agree {same}, values identical "
              f"{bool((guarded[m] == unguarded[m]).all())}")


# -------------------------------------------------------------- Gates C/D


def gate_c_d():
    head("Gates C/D -- reachability and scale-freeness")
    for name, frame in [("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("nonlinear", nonlinear())]:
        base = ts_c3_20(frame)
        fires = int(base.notna().sum())
        print(f"  {name}: fires {fires}/{len(frame)} "
              f"(0 < fires < n is {0 < fires < len(frame)}), "
              f"distinct {int(base.nunique())}, "
              f"non-zero among fired {int((base.dropna() != 0).sum())}, "
              f"range [{float(base.min()):.4f}, {float(base.max()):.4f}]")
        for k in (8.0, 64.0):
            scaled = ts_c3_20(frame * k)
            m = base.notna()
            print(f"    x{k:g}: masks agree "
                  f"{bool((base.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((base[m] == scaled[m]).sum())}/{int(m.sum())}")
        for k in (10.0, 3.7):
            scaled = ts_c3_20(frame * k)
            m = base.notna() & scaled.notna()
            print(f"    x{k:g}: masks agree "
                  f"{bool((base.isna() == scaled.isna()).all())}, max|diff| "
                  f"{float((base[m] - scaled[m]).abs().max()):.3e}")

    print("  non-default parameters, x8/x64 on the walk")
    frame = walk()
    for length, lag in ((20, 9), (60, 1)):
        base = ts_c3_20(frame, length=length, lag=lag)
        m = base.notna()
        for k in (8.0, 64.0):
            scaled = ts_c3_20(frame * k, length=length, lag=lag)
            print(f"    length={length} lag={lag} x{k:g}: fires {int(m.sum())},"
                  f" masks agree {bool((base.isna() == scaled.isna()).all())},"
                  f" bit-equal {int((base[m] == scaled[m]).sum())}/"
                  f"{int(m.sum())}")

    print("  why the return is spelled as a price RATIO")
    close = walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld = np.log(close)
    ld8 = np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    print(f"    ratio returns at x8: bit-equal "
          f"{int((ratio[m] == ratio8[m]).sum())}/{int(m.sum())}")
    print(f"    difference-of-logarithms returns at x8: bit-equal "
          f"{int((plain[m] == plain8[m]).sum())}/{int(m.sum())}")


# ------------------------------------------------- what the column means


def meaning():
    head("What the column means")
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (2000, LENGTH + 1)),
                                     axis=1))
    est = np.array([float(ts_c3_20(Series(p)).iloc[-1]) for p in paths])
    print(f"  2,000 independent {LENGTH}-return iid windows (population 0): "
          f"median {np.median(est):.4f} mean {est.mean():.4f} "
          f"sd {est.std(ddof=1):.4f} p10 {np.percentile(est, 10):.4f} "
          f"p90 {np.percentile(est, 90):.4f} "
          f"positive {100 * (est > 0).mean():.2f}% "
          f"finite {int(np.isfinite(est).sum())}/2000")
    for a in (0.5, 0.0, -0.5):
        med = float(ts_c3_20(nonlinear(a=a)).median())
        implied = a / (1.0 + a * a) ** 1.5
        print(f"  nonlinear path a={a:+.1f}: median {med:.4f}, implied "
              f"standardised a/(1+a^2)^1.5 = {implied:.4f} (arithmetic)")
    print("  does the level converge to the implied 0.3578 as the window "
          "grows? (a=+0.5, 20,000 bars)")
    long_path = nonlinear(n=20000, a=0.5, seed=13)
    for length in (20, 60, 200, 1000):
        med = float(ts_c3_20(long_path, length=length).median())
        print(f"    length={length}: median {med:.4f}")
    print(f"  alternating-size path: median "
          f"{float(ts_c3_20(alternating()).median()):.4f}")
    close = walk()
    base = ts_c3_20(close)
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    compare("+0.004 log drift a bar", base, ts_c3_20(drifted))


# ------------------------------------------------------------ edge, guards


def guards():
    head("Guards and edges")
    print(f"  {LENGTH} closes -> {ts_c3_20(walk(LENGTH))}")
    out = ts_c3_20(walk(LENGTH + 1, seed=2))
    print(f"  {LENGTH + 1} closes: fires {int(out.notna().sum())}, first at "
          f"{int(out.notna().to_numpy().argmax())}")
    for length in (None, 0, -5, 3, 0.5, 2.9):
        print(f"  length={length!r} -> {ts_c3_20(walk(400, seed=31), length=length).name}")
    for lag in (None, 0, -1, 2, 9, 10, 50):
        print(f"  lag={lag!r} -> {ts_c3_20(walk(400, seed=31), lag=lag).name}")
    print("  length=4 clamps lag to 1: "
          f"{ts_c3_20(walk(400, seed=31), length=4, lag=20).name}")
    a = ts_c3_20(walk(400, seed=31), length=50.9)
    b = ts_c3_20(walk(400, seed=31), length=50)
    print(f"  length=50.9 equals length=50: {a.equals(b)}")
    close = walk(400, seed=31)
    x, y = ts_c3_20(close, length=10), ts_c3_20(close, length=60)
    m = x.notna() & y.notna()
    print(f"  length 10 vs 60: names {x.name}/{y.name}, spearman "
          f"{float(x[m].corr(y[m], method='spearman')):.4f}")
    filled = ts_c3_20(walk(200, seed=13), fillna=-1.0)
    print(f"  fillna=-1.0 fills {int((filled == -1.0).sum())} bars")
    close = walk(400, seed=21)
    base = ts_c3_20(close)
    print("  a flat run planted inside a live frame: how many closes it takes")
    for k in (20, 21, 25):
        flat = close.copy()
        flat.iloc[200:200 + k] = float(close.iloc[200])
        out = ts_c3_20(flat)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        where = (f"[{int(emptied.min())}, {int(emptied.max())}]"
                 if len(emptied) else "-")
        print(f"    {k} identical closes at 200: empties {len(emptied)} bars "
              f"{where}")
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = close.copy()
        holed.iloc[200] = bad
        out = ts_c3_20(holed)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        before = base.notna() & out.notna() & (base != out)
        print(f"  close[200]={bad!r}: empties {len(emptied)} bars "
              f"[{int(emptied.min())}, {int(emptied.max())}], bars before 200 "
              f"that move {int(before.iloc[:200].sum())}")


def distributions():
    head("Gate C (synthetic) -- the distribution on each path")
    paths = [
        ("nonlinear a=+0.5", nonlinear(a=0.5)),
        ("nonlinear a=0", nonlinear(a=0.0)),
        ("nonlinear a=-0.5", nonlinear(a=-0.5)),
        ("gaussian walk", walk()),
        ("tick-rounded walk", tick_rounded()),
        ("alternating sizes", alternating()),
    ]
    for name, frame in paths:
        out = ts_c3_20(frame).dropna()
        print(f"  {name}: n={len(out)} distinct={int(out.nunique())} "
              f"min={out.min():.4f} p10={np.percentile(out, 10):.4f} "
              f"median={out.median():.4f} p90={np.percentile(out, 90):.4f} "
              f"max={out.max():.4f} share>0={float((out > 0).mean()):.4f} "
              f"spread(max-min)={float(out.max() - out.min()):.3e}")


def floor_crossover():
    head("Where the noise floor stops reading variation")
    rng = np.random.default_rng(99)
    for jitter in (1e-16, 1e-14, 1e-12, 1e-11, 1e-9):
        r = 0.01 + jitter * rng.standard_normal(1500)
        frame = Series(100.0 * np.exp(np.cumsum(r)))
        guarded = int(ts_c3_20(frame).notna().sum())
        unguarded = int(variant(frame, guard=False).notna().sum())
        print(f"  jitter +-{jitter:.0e}: guarded fires {guarded}/1500, "
              f"unguarded {unguarded}/1500")


def tick_grid_floor():
    """What the floor does to a MONOTONE one-tick-per-bar path, which is the
    case the `tick / price` arithmetic is usually quoted about. The floor
    bounds `sd(r)`, not `|r|`: a tick grid quantises the return LEVEL at
    `tick / price` but the DISPERSION of consecutive returns at about
    `(tick / price)^2`, so the two are not the same comparison."""
    head("The floor against a monotone one-tick-per-bar path")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = closes / closes.shift(1) - 1.0
        sd = float(r.rolling(LENGTH, min_periods=LENGTH).std(ddof=1).iloc[-1])
        fires = int(ts_c3_20(closes).notna().sum())
        print(f"  price={price:g} tick={tick:g}: |r| ~ {float(r.iloc[-1]):.3e}, "
              f"sd(r) over {LENGTH} returns = {sd:.3e} vs floor "
              f"{REAL.NOISE_FLOOR:.3e} -> fires {fires}/{len(closes)}")


def neighbours():
    head("Nearest shipped columns on ONE synthetic walk -- NOT Gate E")
    import pandas as pd
    import pandas_ta as ta  # noqa: F401  (registers the accessors)

    close = walk()
    high = close * 1.01
    low = close * 0.99
    volume = Series(np.full(len(close), 1000.0))
    base = ts_c3_20(close)
    others = {
        "skew_30": ta.skew(close, length=30),
        "kurtosis_30": ta.kurtosis(close, length=30),
        "zscore_30": ta.zscore(close, length=30),
        "entropy_20": ta.entropy(close, length=20),
        "kpss_100": ta.kpss(close),
        "lean_hurst_100": ta.lean_hurst_100(close),
        "tf_centroid_20": ta.tf_centroid_20(close),
        "osap_retskew_21": ta.osap_retskew_21(close),
        "cusum_100": ta.cusum(close),
        "rsi_14": ta.rsi(close, length=14),
        "cfo_9": ta.cfo(close, length=9),
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


if __name__ == "__main__":
    gate_a()
    gate_b()
    noise_floor()
    floor_crossover()
    tick_grid_floor()
    gate_c_d()
    distributions()
    meaning()
    neighbours()
    guards()
    print()
