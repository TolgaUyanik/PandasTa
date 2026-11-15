# -*- coding: utf-8 -*-
"""Reproduce every number in docs/LeanHurst100Measured.md for `lean_hurst_100`
(PandasTa issue #85, LEAN-HURST-100).

Run from the repository root:

    python docs/measure_lean_hurst_100.py

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.lean_hurst_100 import lean_hurst_100

LENGTH, MAX_LAG = 100, 20
LAGS = range(2, MAX_LAG + 1)


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def ohlc(n=1500, seed=11):
    close = walk(n, seed)
    rng = np.random.default_rng(seed + 1)
    spread = close * rng.uniform(0.005, 0.02, n)
    high = close + spread * rng.uniform(0.3, 1.0, n)
    low = close - spread * rng.uniform(0.3, 1.0, n)
    return high, low, close


def compare(name, a, b):
    """Max |difference|, bit-equal count and Spearman over the shared
    non-NaN bars, plus whether the NaN masks agree."""
    masks_agree = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    x, y = a[m], b[m]
    diff = (x - y).abs()
    bit = int((x == y).sum())
    rho = float(x.corr(y, method="spearman")) if len(x) > 2 else float("nan")
    print(f"  {name}: n={int(m.sum())} max|diff|={diff.max():.6e} "
          f"bit-equal={bit}/{int(m.sum())} spearman={rho:.6f} "
          f"nan-masks-agree={masks_agree}")
    return diff.max(), bit, rho, masks_agree


# ----------------------------------------------------------------- Gate A


def screen_candidate():
    """`REG["lean_hurst_100"]["fn"]` out of the screen's own registry, when
    this worktree has `docs/issues/` (gitignored, so a clone does not)."""
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
    return mod.REG["lean_hurst_100"]["fn"]


def prototype(close, length=LENGTH, lags=LAGS):
    """`docs/issues/screen/ind_screen.py` candidate `lean_hurst_100`, retyped
    verbatim (`w_hurst_lagdiff` + `roll` + `_win` + `_from_win`):

        def w_hurst_lagdiff(W, lags=range(2, 21)):
            L = np.log(np.array(list(lags), dtype=float))
            T = np.column_stack([np.log(np.where((s := (W[:, k:] - W[:, :-k]).std(1)) == 0, np.nan, s))
                                 for k in lags])
            Lc = L - L.mean()
            return (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()

        def roll(x, n, f): return _from_win(x, n, f(_win(x, n)))

    It takes the lagged differences of log close INSIDE each window, so it is
    the literal `x[t+k] - x[t]` spelling of the same formula.
    """
    x = np.log(close)
    a = x.to_numpy(dtype=float)
    W = sliding_window_view(a, length) if len(a) >= length else np.empty((0, length))
    L = np.log(np.array(list(lags), dtype=float))
    with np.errstate(divide="ignore", invalid="ignore"):
        T = np.column_stack([
            np.log(np.where((s := (W[:, k:] - W[:, :-k]).std(1)) == 0, np.nan, s))
            for k in lags])
    Lc = L - L.mean()
    vals = (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    out = np.full(len(a), np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH, lags=LAGS, ratios=True):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no pandas rolling, sums written out. `ratios=True` spells the
    lagged difference as log(c[t] / c[t - k]) (the module's spelling);
    `ratios=False` spells it as log(c[t]) - log(c[t - k]) (the prototype's)."""
    c = [float(v) for v in close.to_numpy()]
    ks = list(lags)
    log_k = [math.log(k) for k in ks]
    mean_log_k = sum(log_k) / len(log_k)
    log_k_c = [v - mean_log_k for v in log_k]
    den = sum(v * v for v in log_k_c)
    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        win = c[t - length + 1:t + 1]
        if any(not math.isfinite(v) or v <= 0.0 for v in win):
            continue
        y = []
        ok = True
        for k in ks:
            if ratios:
                d = [math.log(win[i + k] / win[i]) for i in range(length - k)]
            else:
                lw = [math.log(v) for v in win]
                d = [lw[i + k] - lw[i] for i in range(length - k)]
            mu = sum(d) / len(d)
            var = sum((v - mu) ** 2 for v in d) / len(d)
            if var <= 0.0:
                ok = False
                break
            y.append(math.log(math.sqrt(var)))
        if not ok:
            continue
        mean_y = sum(y) / len(y)
        out[t] = sum((y[j] - mean_y) * log_k_c[j] for j in range(len(ks))) / den
    return Series(out, index=close.index)


def variant(close, length=LENGTH, lags=LAGS, ddof=0, demean=True,
            cross_window=False):
    """The module's own computation with ONE reading changed, to price the
    readings the issue's wording leaves open."""
    px = close.astype(float)
    ks = list(lags)
    log_k = np.log(np.array(ks, dtype=float))
    log_k_c = log_k - log_k.mean()
    den = (log_k_c ** 2).sum()
    cols = []
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in ks:
            d = np.log(px / px.shift(k))
            width = length if cross_window else length - k
            if demean:
                s = d.rolling(width, min_periods=width).std(ddof=ddof)
            else:  # root mean square of the differences, mean NOT removed
                s = np.sqrt((d ** 2).rolling(width, min_periods=width).sum()
                            / (width - ddof))
            cols.append(np.log(s.where(s > 0).to_numpy()))
    T = np.column_stack(cols)
    vals = ((T - T.mean(axis=1, keepdims=True)) * log_k_c).sum(axis=1) / den
    return Series(vals, index=close.index)


def gate_a():
    head("GATE A -- the source formula")
    print("""Lean's C# source is NOT in this worktree (docs/pine/ and web access are
unavailable), so the formula under test is the one issue #85 states:
  HurstExponent(100, maxLag 20): slope of log std(x[t+k]-x[t]) on log k,
  k=2..20, x = log close.""")

    print("\nA1. Hand-derived window, closed form.")
    print("""  close = [1, 2, 8, 4, 32], length=5, max_lag=3 (so lags 2 and 3 only,
  and a two-point fit is the exact difference quotient).
  x = log close = [0, L, 3L, 2L, 5L] with L = log 2.
  lag 2 differences: x2-x0=3L, x3-x1=L, x4-x2=2L -> mean 2L,
      population sd = sqrt((L^2 + L^2 + 0)/3) = L*sqrt(2/3)
  lag 3 differences: x3-x0=2L, x4-x1=4L -> mean 3L,
      population sd = sqrt((L^2 + L^2)/2) = L
  slope = (log L - log(L*sqrt(2/3))) / (log 3 - log 2)
        = -log(sqrt(2/3)) / log(1.5) = 0.5*log(1.5)/log(1.5) = 1/2 exactly.""")
    hand = lean_hurst_100(Series([1.0, 2.0, 8.0, 4.0, 32.0]), length=5, max_lag=3)
    print(f"  module: {hand.to_numpy()}")
    print(f"  bar 4 = {float(hand.iloc[4]):.17f}  |value - 0.5| = "
          f"{abs(float(hand.iloc[4]) - 0.5):.6e}")
    print(f"  bars 0..3 all NaN: {bool(hand.iloc[:4].isna().all())}")

    close = walk()
    base = lean_hurst_100(close)
    print(f"\nA2. vs the retyped screen prototype, 1,500-bar walk "
          f"(name={base.name}).")
    compare("prototype (x[t+k]-x[t] of log close, numpy)", base, prototype(close))
    unguarded = variant(close)
    print(f"  the module's rounding-noise floor changes "
          f"{int((base.isna() != unguarded.isna()).sum())} NaN flags and "
          f"{int((base.notna() & unguarded.notna() & (base != unguarded)).sum())} "
          f"values on this frame against the prototype's `sd == 0` guard, so "
          f"it is not what the\n  difference above measures (EDGE CASES prices "
          f"the frames where it does bite).")
    real = screen_candidate()
    if real is None:
        print("  docs/issues/screen/ind_screen.py is not here (it is gitignored, "
              "so a clone does not have it): the retype above is the only "
              "prototype comparison.")
    else:
        h, l, _ = ohlc(1500)
        got = real(close, h, l, close, Series(np.ones(len(close))))
        compare("the screen's own `lean_hurst_100` candidate, imported",
                base, Series(np.asarray(got, dtype=float), index=close.index))

    print("\nA3. vs an independent per-window loop in plain Python scalars, "
          "400 bars.")
    short = walk(400, seed=5)
    sbase = lean_hurst_100(short)
    compare("loop, log(c[t]/c[t-k])  (the module's spelling)",
            sbase, scalar_loop(short, ratios=True))
    compare("loop, log c[t] - log c[t-k] (the prototype's spelling)",
            sbase, scalar_loop(short, ratios=False))

    print("\nA4. The readings the wording leaves open: each rejected variant, "
          "priced.")
    compare("ddof=1 (sample sd) instead of ddof=0",
            base, variant(close, ddof=1))
    compare("root mean square, mean NOT removed",
            base, variant(close, demean=False))
    compare("lags 1..20 instead of 2..20",
            base, variant(close, lags=range(1, MAX_LAG + 1)))
    compare("`length` differences per lag, reaching back past the window",
            base, variant(close, cross_window=True))
    cw = variant(close, cross_window=True)
    print(f"  the crossing-window reading first fires at bar "
          f"{int(cw.notna().to_numpy().argmax())} vs {int(base.notna().to_numpy().argmax())} "
          f"for the port: it reads {MAX_LAG} closes of extra history.")


# ----------------------------------------------------------------- Gate B

_REAL = importlib.import_module("pandas_ta.statistics.lean_hurst_100")
MUTANTS = {
    "write-shift (the whole column back-dated by `length`)": (
        "    hurst = Series(values, index=close.index)",
        "    hurst = Series(values, index=close.index).shift(-length)"),
    "forward difference (`px.shift(lag)` -> `px.shift(-lag)`)": (
        "            diff = np.log(px / px.shift(lag))",
        "            diff = np.log(px / px.shift(-lag))"),
    "centered rolling standard deviation": (
        "            sd = diff.rolling(width, min_periods=width).std(ddof=0)",
        "            sd = diff.rolling(width, min_periods=width, center=True).std(ddof=0)"),
    "the whole log sd row read one bar late": (
        "            log_sd[:, j] = np.log(sd.where(sd > NOISE_FLOOR).to_numpy())",
        "            log_sd[:, j] = np.log(sd.where(sd > NOISE_FLOOR)"
        ".shift(-1).to_numpy())"),
}
OFFSETS = range(150, 1500, 40)  # past the 100-bar warm-up


def near_the_noise_floor(n=1500, amplitude=1e-15, step=0.01, seed=1):
    """A geometric ladder whose steps jitter by about the noise floor itself,
    so `sd > floor` is a near-tie and the floor's own rolling aggregation
    decides which windows fire. The frame that makes the floor-only mutant
    catchable; on a random walk the same comparison is 1e-2 against 1e-18."""
    rng = np.random.default_rng(seed)
    r = step + rng.uniform(-amplitude, amplitude, n)
    return Series(100.0 * np.exp(np.cumsum(r)))


def geometric_with_a_jump(n=1500, step=0.01, jump=0.05, at=700):
    """An exactly geometric ladder -- whose lagged differences vary only at
    rounding level -- with ONE real move in it. Which windows are NaN then
    depends on whether the window holds that move, so the noise floor is
    load-bearing, which it is not on a random walk."""
    r = np.full(n, step)
    r[at] += jump
    return Series(100.0 * np.exp(np.cumsum(r)))


def load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lean_hurst_100_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close=None, other=None, n=1500):
    """Future-perturbation sweep: replace every bar from J onward with a
    different path and count the J values at which anything before J moves."""
    if close is None:
        close, other = walk(n), walk(n, seed=97)
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
    head("GATE B -- causality, by mutant")
    total = len(list(OFFSETS))
    print(f"  future-perturbation sweep over {total} J values "
          f"(J = {OFFSETS.start}..{max(OFFSETS)} step {OFFSETS.step}), on THREE "
          f"frame pairs: a random\n  walk; a geometric ladder with one real move "
          f"in it (where the rounding-noise floor\n  decides which windows are "
          f"NaN); and a tick-rounded walk (prices on a 0.01 grid,\n  as real "
          f"quotes are).")
    walk_pair = (walk(), walk(seed=97))
    geo_pair = (geometric_with_a_jump(), geometric_with_a_jump(step=0.013, jump=0.07, at=640))
    tick_pair = (Series(np.round(walk(seed=55).to_numpy(), 2)),
                 Series(np.round(walk(seed=56).to_numpy(), 2)))
    pairs = {"walk": walk_pair, "geometric+jump": geo_pair,
             "tick-rounded": tick_pair}
    for label, (a, b) in pairs.items():
        print(f"  real module, {label:15s} leaks at "
              f"{leaks(lean_hurst_100, a, b)}/{total} J "
              f"(fires {int(lean_hurst_100(a).notna().sum())}/{len(a)})")
    for name, (old, new) in MUTANTS.items():
        mod = load_mutant(old, new)
        print(f"  mutant: {name}")
        for label, (a, b) in pairs.items():
            live = not mod.lean_hurst_100(a).equals(lean_hurst_100(a))
            print(f"    {label:15s} live={live}  caught at "
                  f"{leaks(mod.lean_hurst_100, a, b)}/{total} J")

    print("\n  offset, the caller-reachable look-ahead:")
    short = walk(400, seed=3)
    b = lean_hurst_100(short)
    later = lean_hurst_100(short, offset=2)
    earlier = lean_hurst_100(short, offset=-2)
    print(f"    offset=+2 == base.shift(2):  {later.equals(b.shift(2))}")
    print(f"    offset=-2 == base.shift(-2): {earlier.equals(b.shift(-2))}")


# ----------------------------------------------------------------- Gate C


def describe(name, s, n):
    fires = int(s.notna().sum())
    print(f"  {name}: fires {fires}/{n} nunique={int(s.nunique())} "
          f"min={s.min():.6f} p10={s.quantile(0.1):.6f} "
          f"median={s.median():.6f} p90={s.quantile(0.9):.6f} "
          f"max={s.max():.6f} share>0.5={float((s > 0.5).sum()) / max(fires, 1):.4f}")
    return s.median()


def ar1_return_path(n, phi, seed, sigma=0.01):
    """Log returns with AR(1) autocorrelation phi: phi > 0 is persistent
    (a trend that keeps going), phi < 0 anti-persistent (it reverses)."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + eps[i]
    return Series(100.0 * np.exp(np.cumsum(r)))


def gate_c():
    head("GATE C -- reachability (synthetic; real data is owed to Gate E's run)")
    n = 1500
    close = walk(n)
    base = lean_hurst_100(close)
    describe("gaussian random walk, iid returns ", base, n)
    for phi in (0.8, 0.4, -0.4, -0.8):
        describe(f"AR(1) returns, phi={phi:+.1f}           ",
                 lean_hurst_100(ar1_return_path(n, phi, 40 + int(10 * phi))), n)
    rng = np.random.default_rng(7)
    alt = Series(100.0 * np.exp(np.cumsum(
        np.where(np.arange(n) % 2 == 0, 1.0, -1.0) * 0.01
        + rng.normal(0.0, 0.001, n))))
    describe("hard alternating log returns      ", lean_hurst_100(alt), n)

    print("""  It orders persistence in the right direction, and the ordering is the
  claim -- the LEVEL is biased low. For iid returns the population slope is
  exactly 0.5 (sd of a k-bar difference is sqrt(k)*sigma), but the window
  only has `length - k` OVERLAPPING differences per lag, so the estimate
  sits below it:""")
    rng = np.random.default_rng(123)
    m = 2000
    r = rng.normal(0.0, 0.01, (m, LENGTH))
    paths = 100.0 * np.exp(np.cumsum(r, axis=1))
    est = np.array([float(lean_hurst_100(Series(p)).iloc[-1]) for p in paths])
    print(f"  {m} independent {LENGTH}-bar iid-return windows: mean "
          f"{est.mean():.4f} median {np.median(est):.4f} sd {est.std(ddof=0):.4f} "
          f"p10 {np.quantile(est, 0.1):.4f} p90 {np.quantile(est, 0.9):.4f} "
          f"share>0.5 {float((est > 0.5).mean()):.4f}")

    print("\n  Drift-invariance: a constant added to every log return shifts each "
          "lag's\n  differences by k*drift and leaves their sd alone, so the slope "
          "should not move.")
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(n)))
    compare("  walk vs the same walk with +0.004 log drift per bar",
            base, lean_hurst_100(drifted))


# ----------------------------------------------------------------- Gate D


def gate_d():
    head("GATE D -- scale-free")
    close = walk()
    base = lean_hurst_100(close)
    n = len(close)
    for k in (8.0, 64.0):
        s = lean_hurst_100(close * k)
        m = base.notna()
        print(f"  x{k:g}: nan-masks agree {bool((base.isna() == s.isna()).all())}, "
              f"bit-identical on {int((base[m] == s[m]).sum())}/{int(m.sum())} bars, "
              f"max|diff| {float((base[m] - s[m]).abs().max()):.6e}")
    for k in (10.0, 3.7):
        s = lean_hurst_100(close * k)
        m = base.notna()
        print(f"  x{k:g}: nan-masks agree {bool((base.isna() == s.isna()).all())}, "
              f"max|diff| {float((base[m] - s[m]).abs().max()):.6e}, "
              f"bit-identical on {int((base[m] == s[m]).sum())}/{int(m.sum())} bars")
    fires = int(base.notna().sum())
    print(f"  0 < fires < n: 0 < {fires} < {n}; distinct values "
          f"{int(base.nunique())}")
    print("  The same column from a x8 frame is bit-identical because every "
          "input is log(close/close.shift(k)) and 8*a / 8*b is the same "
          "double as a / b.")
    ld = np.log(close)
    print("  For contrast, the literal difference-of-logarithms spelling is "
          "NOT bit-stable under x8:")
    for k in (8.0, 64.0):
        d1 = (ld - ld.shift(2)).to_numpy()
        d2 = (np.log(close * k) - np.log(close * k).shift(2)).to_numpy()
        m = ~np.isnan(d1)
        print(f"    x{k:g}: lag-2 log differences bit-equal on "
              f"{int((d1[m] == d2[m]).sum())}/{int(m.sum())} bars, "
              f"max|diff| {np.nanmax(np.abs(d1 - d2)):.6e}")


# ------------------------------------------------------------- edge cases


def gate_edges():
    head("EDGE CASES")
    n = 300
    flat = Series(np.full(n, 50.0))
    print(f"  exactly flat frame: fires {int(lean_hurst_100(flat).notna().sum())}/{n} "
          "(every lag's differences are all 0, so log sd is -inf)")
    print(f"""  The rounding-noise floor: an ABSOLUTE {_REAL.NOISE_ULPS} machine epsilons
  ({_REAL.NOISE_FLOOR:.3e}) on the standard deviation of the lagged differences, which
  are dimensionless log price ratios, so the floor needs no rolling scale and
  has no causality surface of its own. `sd == 0` alone is not enough: the
  lagged differences of an exactly geometric path are mathematically constant,
  but in float64 they vary at rounding level, so an unguarded fit reads
  rounding noise. Each frame below, guarded (the module) vs unguarded
  (`sd > 0` only, which is the prototype's guard):""")
    frames = {
        "geometric, 1% a bar (constant log step)":
            Series(100.0 * np.exp(np.arange(n) * 0.01)),
        "geometric by exact ratio, x1.5 a bar":
            Series(np.cumprod(np.full(n, 1.5)) * 1e-20),
        "one-tick alternation 100.00 / 100.01":
            Series(np.where(np.arange(n) % 2 == 0, 100.00, 100.01)),
        "tick-rounded walk, 2 decimals (small REAL variation)":
            Series(np.round(walk(n, seed=55).to_numpy(), 2)),
        "gaussian random walk":
            walk(n, seed=77),
    }
    for label, frame in frames.items():
        g, u = lean_hurst_100(frame), variant(frame)
        both = g.notna() & u.notna()
        print(f"    {label}:")
        print(f"      guarded   fires {int(g.notna().sum()):4d}/{n}"
              + (f", range [{g.min():.4f}, {g.max():.4f}]"
                 if int(g.notna().sum()) else ""))
        print(f"      unguarded fires {int(u.notna().sum()):4d}/{n}"
              + (f", range [{u.min():.4f}, {u.max():.4f}]"
                 if int(u.notna().sum()) else "")
              + f"; they differ on {int((g.isna() != u.isna()).sum())} bars' "
                f"NaN mask and {int((both & (g != u)).sum())} shared values")
    print("""    Where the floor's crossover sits, on a geometric ladder whose steps
    jitter by a known relative amount (so the variation is REAL but tiny):""")
    for a in (1e-16, 1e-14, 1e-12, 1e-11, 1e-9):
        f = near_the_noise_floor(amplitude=a)
        print(f"      jitter +/-{a:.0e}: guarded fires "
              f"{int(lean_hurst_100(f).notna().sum()):4d}/1500, unguarded "
              f"{int(variant(f).notna().sum()):4d}/1500")
    print("""    So the floor stops reading variation at about 1e-12 in log terms. The
    smallest variation real quotes can show is one tick over the price --
    1e-9 even at a price of 1e6 with a 0.001 tick -- which is three orders
    above that, and the tick-rounded walk row above loses no bars to it.""")

    close = walk(400, seed=21)
    base = lean_hurst_100(close)
    holed = close.copy()
    holed.iloc[200] = np.nan
    out = lean_hurst_100(holed)
    lost = int((base.notna() & out.isna()).sum())
    shared = base.notna() & out.notna()
    moved = shared & (base != out)
    idx = np.flatnonzero(moved.to_numpy())
    print(f"  one NaN close at bar 200: empties {lost} bars (the {LENGTH} "
          f"windows that contain it: "
          f"{int(np.flatnonzero((base.notna() & out.isna()).to_numpy()).min())}"
          f"..{int(np.flatnonzero((base.notna() & out.isna()).to_numpy()).max())})")
    print(f"    shared bars that move at all: {int(moved.sum())}, max|diff| "
          f"{float((base[shared] - out[shared]).abs().max()):.6e}, "
          f"bar range {None if not len(idx) else (int(idx.min()), int(idx.max()))}")
    print(f"    of those, bars BEFORE 200 (which would be a leak): "
          f"{int(moved.iloc[:200].sum())}")
    print("""    pandas' rolling standard deviation is an online accumulation, so a NaN
    in the middle changes the arithmetic PATH of the windows after it, not
    only the ones that contain it. That moves them in the last bits; nothing
    before the hole moves at all.""")
    for label, bad in (("zero", 0.0), ("negative", -5.0), ("inf", np.inf),
                       ("subnormal 1e-310", 1e-310)):
        z = close.copy()
        z.iloc[200] = bad
        o = lean_hurst_100(z)
        print(f"  one {label} close: empties "
              f"{int((base.notna() & o.isna()).sum())} bars")

    print(f"  99 bars returns None: {lean_hurst_100(walk(99)) is None}")
    exact = lean_hurst_100(walk(100, seed=2))
    print(f"  exactly 100 bars: fires {int(exact.notna().sum())}/100, "
          f"first at bar {int(exact.notna().to_numpy().argmax())}")

    print("\n  the parameter guards:")
    c = walk(400, seed=31)
    for length in (None, 0, -5, 4, 5, 0.5, 2.9, 50):
        try:
            o = lean_hurst_100(c, length=length)
        except Exception as exc:  # noqa: BLE001 -- the point is what it does
            print(f"    length={length!r}: raises {type(exc).__name__}: {exc}")
            continue
        print(f"    length={length!r}: name={None if o is None else o.name}, "
              f"fires {0 if o is None else int(o.notna().sum())}")
    for max_lag in (None, 0, 2, 3, 98, 99, 200):
        o = lean_hurst_100(c, max_lag=max_lag)
        print(f"    max_lag={max_lag!r}: name={o.name}, "
              f"fires {int(o.notna().sum())}")
    o = lean_hurst_100(c, length=5, max_lag=20)
    print(f"    length=5, max_lag=20 -> clamped: name={o.name}, "
          f"fires {int(o.notna().sum())}")


# -------------------------------------------------- neighbours (NOT Gate E)


def neighbours():
    head("NEAREST NEIGHBOURS on one synthetic walk -- NOT Gate E")
    import pandas_ta as ta
    high, low, close = ohlc(1500)
    base = lean_hurst_100(close)
    cands = {
        "rsi_14": ta.rsi(close),
        "natr_14": ta.natr(high, low, close),
        "kurtosis_30": ta.kurtosis(close, length=30),
        "skew_30": ta.skew(close, length=30),
        "zscore_30": ta.zscore(close, length=30),
        "entropy_20": ta.entropy(close),
        "kpss_100": ta.kpss(close),
        "cusum_100": ta.cusum(close),
        "stdev_log_return_100": ta.log_return(close).rolling(100).std(),
        "mad_100_pct": ta.mad(close, length=100) / close,
        "cfo_9": ta.cfo(close),
        "ht_dcperiod": ta.ht_dcperiod(close),
    }
    adx = ta.adx(high, low, close)
    cands["adx_14"] = adx[adx.columns[0]]
    rows = []
    for name, s in cands.items():
        s = s.astype(float)
        m = base.notna() & s.notna()
        if int(m.sum()) < 50:
            rows.append((name, float("nan"), int(m.sum())))
            continue
        rows.append((name, abs(float(base[m].corr(s[m], method="spearman"))),
                     int(m.sum())))
    for name, rho, n in sorted(rows, key=lambda r: -(r[1] if r[1] == r[1] else -1)):
        print(f"  |rho| {rho:.4f}  n={n:5d}  {name}")
    print("""  One 1,500-bar synthetic walk against 13 shipped columns is NOT Gate E,
  which is 687 comparators over 89 frozen BIST frames. It is a smell test
  only; the issue's prototype screen measured 0.2491 vs `mad_pct` pooled.""")


def main():
    pd.set_option("display.width", 200)
    print(f"pandas {pd.__version__} / numpy {np.__version__}")
    gate_a()
    gate_b()
    gate_c()
    gate_d()
    gate_edges()
    neighbours()
    head("GATE E")
    print("  pending, run by issue-solver after this session.")


if __name__ == "__main__":
    main()
