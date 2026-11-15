# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsCidCe20Measured.md for `ts_cid_ce_20`
(PandasTa issue #95, TS-CID-CE-20).

Run from the repository root:

    python docs/measure_ts_cid_ce_20.py           # every section
    python docs/measure_ts_cid_ce_20.py a         # one section

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import math
import time
import tracemalloc
import types
from fractions import Fraction

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20

LENGTH = 20
REAL = importlib.import_module("pandas_ta.statistics.ts_cid_ce_20")


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------- the frames


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.5):
    """A path whose LOG returns are an AR(1), `rlog[t] = phi*rlog[t-1] + eps`,
    whose population lag-1 autocorrelation is exactly `phi`."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def alternating(n=1500, amp=0.01):
    r = np.where(np.arange(n) % 2 == 0, amp, -amp)
    return Series(100.0 * np.cumprod(1.0 + r))


def geometric_ladder(n=300, step=0.01):
    """Mathematically constant returns, which vary at float rounding level."""
    return Series(100.0 * np.exp(np.arange(n) * step))


def mean_dominated(n=400, seed=3, mu=0.01, ratio=1e5):
    """Returns with a large MEAN and a tiny DISPERSION, well above the
    variance floor: the shape on which a variance accumulator cancels."""
    rng = np.random.default_rng(seed)
    r = mu + rng.normal(0.0, abs(mu) / ratio, n)
    return Series(100.0 * np.cumprod(1.0 + r))


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


# ------------------------------------------------- the source, three ways


def tsfresh_cid_ce(x, normalize=True):
    """tsfresh `feature_calculators.cid_ce`, retyped from its published
    definition:

        if normalize:
            s = np.std(x)
            if s != 0:
                x = (x - np.mean(x)) / s
            else:
                return 0.0
        x = np.diff(x)
        return np.sqrt(np.dot(x, x))

    ⚠ tsfresh is NOT installed in this worktree and web access is
    unavailable, so this is the formula the issue states plus the published
    definition of that function, not a read of tsfresh's own code. `np.std`
    is the POPULATION standard deviation (`ddof=0`), and the `s == 0` branch
    returns 0.0 rather than a NaN -- see section A6."""
    x = np.asarray(x, dtype=float)
    if normalize:
        s = np.std(x)
        if s != 0:
            x = (x - np.mean(x)) / s
        else:
            return 0.0
    x = np.diff(x)
    return float(np.sqrt(np.dot(x, x)))


def source_windowed(close, length=LENGTH, guard="floor", log_returns=False,
                    closes_not_returns=False, ddof=0, normalize=True):
    """The source function applied window by window: every window is handed
    to `tsfresh_cid_ce` above, so the z-normalisation happens per return the
    way tsfresh does it and no pandas rolling is involved anywhere. The
    keywords are the rejected readings of section A6."""
    px = close.astype(float)
    if log_returns:
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.log(px / px.shift(1)).to_numpy()
    else:
        with np.errstate(over="ignore"):
            r = (px / px.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    width = length - 1 if closes_not_returns else length
    if len(r) < width + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], width)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        v = W.var(axis=1, ddof=ddof)
        vals = np.array([tsfresh_cid_ce(w, normalize=normalize) for w in W])
        if normalize and ddof:
            # The same quotient taken against the SAMPLE standard deviation:
            # tsfresh_cid_ce always divides by the population one, so rescale.
            vals = vals * np.sqrt(W.var(axis=1, ddof=0)
                                  / W.var(axis=1, ddof=ddof))
    if guard == "floor":                 # this module's guard
        vals = np.where(v > REAL.VAR_FLOOR, vals, np.nan)
    elif guard == "isclose":             # tsfresh's `np.isclose(s, 0)` kin
        vals = np.where(np.isclose(np.sqrt(v), 0.0), np.nan, vals)
    elif guard != "none":                # "none" keeps tsfresh's 0.0 branch
        raise ValueError(guard)
    out[width:] = vals
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH):
    """Plain-Python scalars, `math.fsum` for every sum: no numpy, no pandas
    rolling, and the summation is exact to one rounding."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        x = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        m = math.fsum(x) / length
        v = math.fsum((u - m) ** 2 for u in x) / length
        gap = math.fsum((x[i] - x[i - 1]) ** 2 for i in range(1, length))
        if v > REAL.VAR_FLOOR:
            out[t] = math.sqrt(gap / v)
    return Series(out, index=close.index)


def exact_loop(close, length=LENGTH, bars=None):
    """The EXACT value, in `fractions.Fraction`: every close is a rational, so
    every return and the whole SQUARED statistic is one. The square root and
    the final conversion are the only roundings."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    first = length if bars is None else max(length, len(c) - bars)
    for t in range(first, len(c)):
        x = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        m = sum(x) / length
        v = sum((u - m) ** 2 for u in x) / length
        gap = sum((x[i] - x[i - 1]) ** 2 for i in range(1, length))
        if v != 0:
            out[t] = math.sqrt(Fraction(gap, 1) / v)
    return Series(out, index=close.index)


def znorm_first(close, length=LENGTH):
    """The spelling the module does NOT use: z-normalise the window's returns
    first (`length` divisions) and sum the squared differences of the
    normalised values, which is tsfresh's own order of operations."""
    px = close.astype(float)
    r = (px / px.shift(1) - 1.0).to_numpy()
    out = np.full(len(r), np.nan)
    if len(r) < length + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], length)
    v = W.var(axis=1, ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (W - W.mean(axis=1, keepdims=True)) / np.sqrt(v)[:, None]
        d = np.diff(z, axis=1)
        vals = np.sqrt((d * d).sum(axis=1))
    out[length:] = np.where(v > REAL.VAR_FLOOR, vals, np.nan)
    return Series(out, index=close.index)


def screen_candidate():
    """`REG["ts_cid_ce_20"]["fn"]` out of the screen's own registry, when this
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
    return mod.REG["ts_cid_ce_20"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_cid_ce_20`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            r = ret(c)
            return sdiv(np.sqrt(tsum(delta(r, 1) ** 2, 19)), std(r, 20))

    with `ret(c) = c / c.shift(1) - 1`, `delta(x, n) = x - x.shift(n)`,
    `tsum(x, n) = x.rolling(n).sum()`, `std(x, n) = x.rolling(n).std()` --
    pandas' default `ddof=1`, the SAMPLE standard deviation -- and
    `sdiv(a, b) = (a / b).replace([inf, -inf], nan)`."""
    r = close / close.shift(1) - 1
    num = np.sqrt((r - r.shift(1)).pow(2).rolling(length - 1).sum())
    return (num / r.rolling(length).std()).replace([np.inf, -np.inf], np.nan)


# ----------------------------------------------- the closed-form geometry


def closed_form_bounds(n):
    """The reachable [min, max] of the column at `length = n`, in closed form.

    The squared column is `gap / var` with `gap = sum (x[i] - x[i-1])**2` and
    `var = sum (x[i] - m)**2 / n`, so it is `n` times the Rayleigh quotient of
    the free-end path Laplacian `L` (`x'Lx = gap`) on the subspace orthogonal
    to the all-ones vector. `L`'s eigenvectors are the DCT-II basis
    `v_k[j] = cos(pi*k*(j+1/2)/n)` with eigenvalues `4*sin(pi*k/(2n))**2`, and
    the k = 0 one IS the all-ones vector, so the restricted spectrum is
    exactly k = 1..n-1. Hence

        min = sqrt(n * 4*sin(pi/(2n))**2)        max = sqrt(n * 4*sin(pi*(n-1)/(2n))**2)
    """
    lo = math.sqrt(n * 4.0 * math.sin(math.pi / (2 * n)) ** 2)
    hi = math.sqrt(n * 4.0 * math.sin(math.pi * (n - 1) / (2 * n)) ** 2)
    return lo, hi


def eigen_window(n, k, amp=0.01):
    """The `k`-th DCT-II eigenvector as a window of returns, scaled to `amp`."""
    j = np.arange(n)
    y = np.cos(math.pi * k * (j + 0.5) / n)
    return amp * y / float(np.abs(y).max())


def closes_from_returns(r, first=100.0):
    return Series(np.concatenate([[first], first * np.cumprod(1.0 + r)]))


# ----------------------------------------------------------------- Gate A


def gate_a():
    head("Gate A1. windows with a closed form")
    # An alternating window of two values: every squared difference is the
    # square of the whole range `(2d)**2 = 4*d**2` and the population
    # variance is `d**2`, so the quotient is `4*(length-1)` exactly and the
    # column is `2*sqrt(length-1)` for every `length`.
    out = ts_cid_ce_20(Series([1.0, 2.0, 1.0, 2.0, 1.0]), length=4)
    want = math.sqrt(12.0)
    print(f"  closes [1,2,1,2,1] length=4: name={out.name} "
          f"warmup-nan={bool(out.iloc[:4].isna().all())} "
          f"value={float(out.iloc[4])!r} want=2*sqrt(3)={want!r} "
          f"bit-equal={float(out.iloc[4]) == want}")
    # The closed form depends on the window's PARITY. With `n` returns
    # alternating between the two values `m0 +- d`: an even `n` holds equal
    # counts, so `var = d**2` and the quotient is `4*(n-1)`; an odd `n` holds
    # one more of the first value, so the window mean sits `d/n` off centre,
    # `var = d**2*(n**2-1)/n**2` and the quotient is `4*n**2/(n+1)`.
    for length in (3, 4, 5, 20, 21):
        closes = Series(np.where(np.arange(length + 1) % 2 == 0, 1.0, 2.0))
        got = float(ts_cid_ce_20(closes, length=length).iloc[-1])
        if length % 2 == 0:
            target, form = 2.0 * math.sqrt(length - 1), "2*sqrt(n-1)"
        else:
            target = 2.0 * length / math.sqrt(length + 1.0)
            form = "2*n/sqrt(n+1)"
        print(f"  alternating [1,2,...] length={length}: value={got!r} "
              f"{form}={target!r} bit-equal={got == target}")
    col = ts_cid_ce_20(alternating()).dropna()
    target = 2.0 * math.sqrt(LENGTH - 1)
    print(f"  alternating frame (cumprod closes), length={LENGTH}: "
          f"fires={len(col)} max|value - 2*sqrt(19)|="
          f"{float((col - target).abs().max()):.6e} "
          f"bit-equal={int((col == target).sum())}/{len(col)}")
    # A window of TWO returns is identically 2, which is why MIN_LENGTH is 3.
    two = Series(np.sqrt(np.arange(1, 41, dtype=float)))
    naive = ts_cid_ce_20(two, length=2)
    print(f"  length=2 asked for: name={naive.name} (MIN_LENGTH="
          f"{REAL.MIN_LENGTH} falls back to the default)")
    forced = []
    for t in range(2, 40):
        x = two.to_numpy()[t - 2:t + 1]
        forced.append(tsfresh_cid_ce(x[1:] / x[:-1] - 1.0))
    forced = np.array(forced)
    print(f"  the source on 2-return windows: distinct values="
          f"{len(np.unique(forced))} value={forced[0]!r} "
          f"all-exactly-2.0={bool((forced == 2.0).all())}")

    head("Gate A2. the reachable range, in closed form and attained")
    for length in (3, 4, 10, 20, 60):
        lo, hi = closed_form_bounds(length)
        got_lo = float(ts_cid_ce_20(
            closes_from_returns(eigen_window(length, 1)),
            length=length).iloc[-1])
        got_hi = float(ts_cid_ce_20(
            closes_from_returns(eigen_window(length, length - 1)),
            length=length).iloc[-1])
        print(f"  length={length}: closed form [{lo:.12f}, {hi:.12f}] "
              f"attained [{got_lo:.12f}, {got_hi:.12f}] "
              f"|err|=[{abs(got_lo - lo):.2e}, {abs(got_hi - hi):.2e}] "
              f"alternating 2*sqrt(length-1)="
              f"{2.0 * math.sqrt(length - 1):.12f}")
    lo, hi = closed_form_bounds(LENGTH)
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1", ar1()), ("alternating", alternating())):
        col = ts_cid_ce_20(frame).dropna()
        print(f"  {name}: min={float(col.min()):.6f} max={float(col.max()):.6f}"
              f" inside={bool(float(col.min()) >= lo and float(col.max()) <= hi)}")

    head("Gate A3. the source function, window by window")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1", ar1()), ("mean-dominated", mean_dominated())):
        compare(name, ts_cid_ce_20(frame), source_windowed(frame))

    head("Gate A4. against an exact rational oracle")
    for name, frame in (("walk", walk(340, seed=11)),
                        ("tick-rounded", tick_rounded(340, seed=55)),
                        ("mean-dominated", mean_dominated(340))):
        exact = exact_loop(frame, bars=40)
        m = exact.notna()
        print(f"  {name} ({int(m.sum())} bars):")
        for label, series in (("module", ts_cid_ce_20(frame)),
                              ("fsum loop", scalar_loop(frame)),
                              ("windowed oracle", source_windowed(frame)),
                              ("z-normalise first", znorm_first(frame))):
            diff = float((series[m] - exact[m]).abs().max())
            rel = float(((series[m] - exact[m]) / exact[m]).abs().max())
            print(f"    {label:>18}: max|diff|={diff:.3e} "
                  f"max|rel|={rel:.3e}")

    head("Gate A5. the two spellings of the normalisation")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("mean-dominated", mean_dominated())):
        compare(name, ts_cid_ce_20(frame), znorm_first(frame))

    head("Gate A6. the readings the wording leaves open")
    frame = walk()
    base = ts_cid_ce_20(frame)
    for label, kwargs in (("log returns", {"log_returns": True}),
                          ("20 CLOSES (19 returns)",
                           {"closes_not_returns": True}),
                          ("sample sd (ddof=1)", {"ddof": 1}),
                          ("normalize=False", {"normalize": False})):
        other = source_windowed(frame, **kwargs)
        compare(label, base, other)
    ratio = math.sqrt(LENGTH / (LENGTH - 1.0))
    ddof1 = source_windowed(frame, ddof=1)
    m = base.notna() & ddof1.notna()
    print(f"  sample sd is the same column rescaled by "
          f"sqrt(20/19)={ratio:.12f}: "
          f"max|port - ratio*other|="
          f"{float((base[m] - ratio * ddof1[m]).abs().max()):.3e}")
    nf = source_windowed(frame, normalize=False)
    r = frame / frame.shift(1) - 1.0
    sd = r.rolling(LENGTH, min_periods=LENGTH).std(ddof=0)
    mm = nf.notna() & sd.notna()
    print(f"  normalize=False against the window's own sd: spearman="
          f"{float(nf[mm].corr(sd[mm], method='spearman')):.6f} "
          f"(the normalised column: "
          f"{float(base[mm].corr(sd[mm], method='spearman')):.6f})")

    head("Gate A7. the screen prototype")
    proto = prototype(frame)
    compare("prototype (retyped)", base, proto)
    m = base.notna() & proto.notna()
    print(f"  port / prototype: min={float((base[m] / proto[m]).min()):.12f} "
          f"max={float((base[m] / proto[m]).max()):.12f} "
          f"sqrt(20/19)={ratio:.12f}")
    # The accuracy of THIS comparison, against the prototype itself. The A6
    # line above prints the same quantity against the `ddof=1` window-by-
    # window oracle, which is a different series.
    print(f"  max|port - sqrt(20/19) * prototype|="
          f"{float((base[m] - ratio * proto[m]).abs().max()):.3e}")
    print(f"  first fired bar: port={int(base.notna().to_numpy().argmax())} "
          f"prototype={int(proto.notna().to_numpy().argmax())}")
    fn = screen_candidate()
    if fn is None:
        print("  owner's registry: docs/issues/ absent, retype not checked")
    else:
        h = frame * 1.01
        owner = fn(frame, h, frame * 0.99, frame,
                   Series(np.full(len(frame), 1000.0)))
        compare("owner's registry vs retype", proto, Series(
            np.asarray(owner, dtype=float), index=frame.index))

    head("Gate A8. is tsfresh importable here?")
    try:
        from tsfresh.feature_extraction import feature_calculators
        print("  tsfresh IS importable -- comparing against it directly")
        W = sliding_window_view((frame / frame.shift(1) - 1.0).to_numpy()[1:],
                                LENGTH)
        theirs = np.full(len(frame), np.nan)
        theirs[LENGTH:] = [float(feature_calculators.cid_ce(w, True))
                           for w in W]
        compare("tsfresh itself", base, Series(theirs, index=frame.index))
    except ImportError as exc:
        print(f"  tsfresh is NOT importable ({exc}); the oracle above is the "
              f"retyped published definition")


# ----------------------------------------------------------------- Gate B

WRITE_SHIFT_MUTANT = (
    "    cidce = Series(np.sqrt(quotient.to_numpy()), index=close.index)",
    "    cidce = Series(np.sqrt(quotient.to_numpy()), "
    "index=close.index).shift(-length)")
FORWARD_RETURN_MUTANT = (
    "        r = px / px.shift(1) - 1.0",
    "        r = px.shift(-1) / px - 1.0")
FORWARD_DIFF_MUTANT = (
    "    gap = Series(np.square(r.diff().to_numpy()), index=r.index)",
    "    gap = Series(np.square(r.diff(-1).to_numpy()), index=r.index)")
CENTERED_VAR_MUTANT = (
    "    var = rolling.var(ddof=0)",
    "    var = r.rolling(length, min_periods=length, center=True).var(ddof=0)")
CENTERED_GAP_MUTANT = (
    "    gap = gap.rolling(length - 1, min_periods=length - 1).sum()",
    "    gap = gap.rolling(length - 1, min_periods=length - 1, "
    "center=True).sum()")
CENTERED_SPAN_MUTANT = (
    "    span = rolling.max() - rolling.min()",
    "    span = r.rolling(length, min_periods=length, center=True).max() "
    "- r.rolling(length, min_periods=length, center=True).min()")

MUTANTS = [WRITE_SHIFT_MUTANT, FORWARD_RETURN_MUTANT, FORWARD_DIFF_MUTANT,
           CENTERED_VAR_MUTANT, CENTERED_GAP_MUTANT, CENTERED_SPAN_MUTANT]
MUTANT_IDS = ["write_shift", "forward_return", "forward_diff", "centered_var",
              "centered_gap", "centered_span"]
OFFSETS = range(100, 1500, 40)
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "ar1": (ar1(), ar1(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_cid_ce_20_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def quiet_offsets(fn, close, other):
    """Replace every bar from J onward with a different path; return the J
    values at which NOTHING strictly before J moved, each with whether bar
    J - 1 -- the only bar a one-bar look-ahead can reach -- was NaN in both
    runs."""
    base = fn(close)
    quiet = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        moved = not (a.isna() == b.isna()).all()
        if not moved:
            m = a.notna()
            moved = bool((a[m] != b[m]).any())
        if not moved:
            quiet.append((j, bool(np.isnan(float(a.iloc[-1]))),
                          bool(np.isnan(float(b.iloc[-1])))))
    return quiet


def leaks(fn, close, other):
    return len(list(OFFSETS)) - len(quiet_offsets(fn, close, other))


def gate_b():
    head("Gate B. future-perturbation sweep, real module and six mutants")
    total = len(list(OFFSETS))
    print(f"  {total} offsets J = {OFFSETS.start}..{OFFSETS.stop - 1} "
          f"step {OFFSETS.step}")
    for frame in sorted(FRAMES):
        close, other = FRAMES[frame]
        print(f"  real module, {frame}: leaks={leaks(ts_cid_ce_20, close, other)}"
              f"/{total}")
    for ident, mutant in zip(MUTANT_IDS, MUTANTS):
        mod = load_mutant(*mutant)
        for frame in sorted(FRAMES):
            close, other = FRAMES[frame]
            live = not mod.ts_cid_ce_20(close).equals(ts_cid_ce_20(close))
            print(f"  mutant {ident}, {frame}: live={live} "
                  f"caught={leaks(mod.ts_cid_ce_20, close, other)}/{total}")

    head("Gate B2. the length-dependent mutants at non-default lengths")
    close, other = FRAMES["walk"]
    for ident, mutant in zip(MUTANT_IDS, MUTANTS):
        if ident in ("forward_return",):
            continue
        for length in (3, 250):
            mod = load_mutant(*mutant)

            def real(c, length=length):
                return ts_cid_ce_20(c, length=length)

            def mutated(c, mod=mod, length=length):
                return mod.ts_cid_ce_20(c, length=length)

            quiet = quiet_offsets(mutated, close, other)
            caught = len(list(OFFSETS)) - len(quiet)
            below = [j for j, _, _ in quiet if j <= length]
            both_nan = all(a and b for _, a, b in quiet)
            print(f"  mutant {ident}, length={length}: "
                  f"real-leaks={leaks(real, close, other)} caught={caught}/"
                  f"{len(list(OFFSETS))} live="
                  f"{not mutated(close).equals(real(close))} "
                  f"quiet-below-warmup={below} quiet-all-nan-at-J-1={both_nan}")

    head("Gate B4. what the centred-span mutant does, and where it IS caught")
    # `span` enters nothing but the trust test's two booleans, and on clean
    # data both verdicts are True whichever window the extrema come from, so
    # the look-ahead changes no VALUE -- it only moves the NaN tail, which is
    # why the sweep above reports 0/35. The mutation is observable exactly
    # where the trust test BITES: a frame contaminated by a giant return.
    mod = load_mutant(*CENTERED_SPAN_MUTANT)
    for name, fr in (("walk", walk()), ("tick-rounded", tick_rounded()),
                     ("ar1", ar1())):
        real_col, mut_col = ts_cid_ce_20(fr), mod.ts_cid_ce_20(fr)
        differ = np.flatnonzero(
            ((real_col.notna() != mut_col.notna())
             | (real_col.notna() & mut_col.notna() & (real_col != mut_col)))
            .to_numpy())
        body = [int(i) for i in differ if i < len(fr) - (LENGTH - 1) // 2]
        print(f"  {name}: bars where the mutant differs={len(differ)} "
              f"({int(differ.min())}..{int(differ.max())}) of {len(fr)}; "
              f"outside the last (length-1)//2={(LENGTH - 1) // 2} bars: "
              f"{len(body)} {body[:12]}")
    spiked = walk(1500, seed=21)
    spiked.iloc[150] = float(spiked.iloc[149]) * 1e8
    far = walk(1500, seed=97) * 1e4
    print(f"  spiked frame: real-module leaks="
          f"{leaks(ts_cid_ce_20, spiked, far)}/{len(list(OFFSETS))} "
          f"centred-span leaks={leaks(mod.ts_cid_ce_20, spiked, far)}/"
          f"{len(list(OFFSETS))}")
    detail = [j for j, _, _ in quiet_offsets(mod.ts_cid_ce_20, spiked, far)]
    print(f"  offsets at which it stays quiet on the spiked frame: {detail}")
    real_col = ts_cid_ce_20(spiked)
    print(f"  the spiked frame's trust-test rejections: "
          f"{int(real_col.iloc[170:200].isna().sum())} NaN bars in 170..199")

    head("Gate B3. offset is the caller's own look-ahead")
    close = walk(400, seed=3)
    base = ts_cid_ce_20(close)
    for off in (2, -2):
        got = ts_cid_ce_20(close, offset=off)
        print(f"  offset={off}: equals base.shift({off})="
              f"{bool(got.equals(base.shift(off).rename(got.name)))}")


# --------------------------------------------------------------- Gate C/D


def gate_c_d():
    head("Gate C. reachability on synthetic frames (real data: Gate E's run)")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1", ar1()), ("alternating", alternating())):
        col = ts_cid_ce_20(frame)
        fires = int(col.notna().sum())
        print(f"  {name}: fires={fires}/{len(frame)} "
              f"distinct={int(col.nunique())} "
              f"non-zero={int((col.dropna() != 0).sum())} "
              f"min={float(col.min()):.6f} median={float(col.median()):.6f} "
              f"max={float(col.max()):.6f}")

    head("Gate D. x8 / x64 bit-identical")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1", ar1())):
        base = ts_cid_ce_20(frame)
        for k in (8.0, 64.0):
            scaled = ts_cid_ce_20(frame * k)
            m = base.notna()
            print(f"  {name} x{k:g}: masks-agree="
                  f"{bool((base.isna() == scaled.isna()).all())} "
                  f"bit-equal={int((base[m] == scaled[m]).sum())}/"
                  f"{int(m.sum())}")
    frame = walk()
    for length in (3, 20, 60, 250):
        base = ts_cid_ce_20(frame, length=length)
        m = base.notna()
        bits = [int((base[m] == ts_cid_ce_20(frame * k, length=length)[m]).sum())
                for k in (8.0, 64.0)]
        print(f"  walk length={length}: fires={int(m.sum())} "
              f"bit-equal x8={bits[0]} x64={bits[1]}")

    head("Gate D2. x10 / x3.7 within tolerance")
    for name, frame in (("walk", walk()), ("tick-rounded", tick_rounded()),
                        ("ar1", ar1())):
        base = ts_cid_ce_20(frame)
        for k in (10.0, 3.7):
            compare(f"{name} x{k:g}", base, ts_cid_ce_20(frame * k))

    head("Gate D3. why the return is a ratio and not a difference of logs")
    frame = walk()
    ratio = (frame / frame.shift(1) - 1.0).to_numpy()
    ratio8 = (frame * 8.0 / (frame * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(frame), np.log(frame * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    print(f"  returns bit-equal at x8: ratio={int((ratio[m] == ratio8[m]).sum())}"
          f"/{int(m.sum())} log-difference="
          f"{int((plain[m] == plain8[m]).sum())}/{int(m.sum())}")


# --------------------------------------------------- what the column means


def rescaled_returns(close, k):
    r = (close / close.shift(1) - 1.0).to_numpy()[1:]
    first = float(close.iloc[0])
    return Series(np.concatenate([[first], first * np.cumprod(1.0 + k * r)]))


def meaning():
    head("Meaning 1. invariance to an affine map of the returns")
    frame = walk()
    base = ts_cid_ce_20(frame)
    others = {
        "returns x2": rescaled_returns(frame, 2.0),
        "returns x0.5": rescaled_returns(frame, 0.5),
        "+0.004 log drift a bar": Series(
            frame.to_numpy() * np.exp(0.004 * np.arange(len(frame)))),
    }
    for name, other in others.items():
        compare(name, base, ts_cid_ce_20(other))

    head("Meaning 2. it is not volatility and not direction")
    r = frame / frame.shift(1) - 1.0
    rolling = r.rolling(LENGTH, min_periods=LENGTH)
    for name, other in (("sd of the same window", rolling.std()),
                        ("mean return", rolling.mean()),
                        ("|mean return|", rolling.mean().abs()),
                        ("close / close[-20] - 1", frame / frame.shift(20) - 1)):
        m = base.notna() & other.notna()
        print(f"  {name}: spearman="
              f"{float(base[m].corr(other[m], method='spearman')):.6f}")

    head("Meaning 3. the level and the spread on iid returns")
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(
        rng.normal(0.0, 0.01, (2000, LENGTH + 1)), axis=1))
    est = np.array([float(ts_cid_ce_20(Series(p)).iloc[-1]) for p in paths])
    finite = np.isfinite(est)
    lo, hi = closed_form_bounds(LENGTH)
    print("  the iid RATIO OF EXPECTATIONS of the squared form is "
          f"2*{LENGTH} = {2 * LENGTH} -- E[gap] = 2*(n-1)*sigma**2 and "
          "E[var] = (n-1)*sigma**2/n, distribution-free -- so "
          f"sqrt({2 * LENGTH}) = {math.sqrt(2.0 * LENGTH):.4f} is the level "
          "to compare the median below against; the expectation of the ratio "
          "is NOT the ratio of the expectations, so the direction of the gap "
          "is measured and not derived")
    print(f"  2,000 independent 20-return windows: finite={int(finite.sum())} "
          f"median={float(np.median(est[finite])):.4f} "
          f"mean={float(est[finite].mean()):.4f} "
          f"sd={float(est[finite].std(ddof=1)):.4f}")
    print(f"  p01={float(np.percentile(est[finite], 1)):.4f} "
          f"p10={float(np.percentile(est[finite], 10)):.4f} "
          f"p90={float(np.percentile(est[finite], 90)):.4f} "
          f"p99={float(np.percentile(est[finite], 99)):.4f} "
          f"min={float(est[finite].min()):.4f} "
          f"max={float(est[finite].max()):.4f}")
    print(f"  reachable range [{lo:.4f}, {hi:.4f}]")

    head("Meaning 4. it orders the AR(1) coefficient, downward")
    for phi in (0.5, 0.25, 0.0, -0.25, -0.5):
        col = ts_cid_ce_20(ar1(phi=phi)).dropna()
        print(f"  phi={phi:+.2f}: median={float(col.median()):.4f} "
              f"p10={float(col.quantile(0.1)):.4f} "
              f"p90={float(col.quantile(0.9)):.4f}")
    for length in (20, 60, 200, 1000):
        col = ts_cid_ce_20(ar1(20000, phi=0.5), length=length).dropna()
        norm = float(col.median()) / math.sqrt(2.0 * length)
        print(f"  phi=+0.50 on 20,000 bars, length={length}: "
              f"median={float(col.median()):.4f} "
              f"median/sqrt(2*length)={norm:.4f}")

    head("Meaning 5. it is a slow state, not an event flag")
    col = ts_cid_ce_20(walk()).dropna()
    for lag in (1, 10, 20, 40):
        print(f"  autocorrelation at lag {lag}: {float(col.autocorr(lag)):.4f}")

    head("Meaning 6. the identity against the lag-1 autocorrelation")
    # gap = 2*n*var - y[0]**2 - y[n-1]**2 - 2*S, with y the demeaned window
    # and S the lag-1 product sum, so
    #   column**2 = 2*n - (y[0]**2 + y[n-1]**2)/var - 2*(n-1)*A
    # where A is `ts_ac1_60`'s value on the SAME window length.
    r = frame / frame.shift(1) - 1.0
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    var = roll.var(ddof=0)
    mean = roll.mean()
    y_new = (r - mean) ** 2
    y_old = (r.shift(LENGTH - 1) - mean) ** 2
    ac = ts_ac1_60(frame, length=LENGTH)
    identity = 2.0 * LENGTH - (y_old + y_new) / var - 2.0 * (LENGTH - 1) * ac
    m = base.notna() & identity.notna()
    print(f"  max|column**2 - identity| = "
          f"{float((base[m] ** 2 - identity[m]).abs().max()):.3e} over "
          f"{int(m.sum())} bars")
    for length in (20, 60):
        other = ts_ac1_60(frame, length=length)
        m = base.notna() & other.notna()
        print(f"  spearman against TS_AC1_{length}: "
              f"{float(base[m].corr(other[m], method='spearman')):.6f} "
              f"(pearson {float(base[m].corr(other[m])):.6f}, n={int(m.sum())})")
    for name, fr in (("tick-rounded", tick_rounded()), ("ar1", ar1())):
        b = ts_cid_ce_20(fr)
        for length in (20, 60):
            other = ts_ac1_60(fr, length=length)
            m = b.notna() & other.notna()
            print(f"  {name} against TS_AC1_{length}: spearman="
                  f"{float(b[m].corr(other[m], method='spearman')):.6f}")


# ----------------------------------------------------------------- guards


def module_variant(close, length=LENGTH, overflow=True, trust=True,
                   floor=True):
    """The module with one guard switched off at a time, to price each."""
    px = close.astype(float)
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    if overflow:
        with np.errstate(over="ignore"):
            square = np.square(r.to_numpy())
        r = r.where(square < np.finfo(float).max / (8 * length))
    rolling = r.rolling(length, min_periods=length)
    var = rolling.var(ddof=0)
    with np.errstate(over="ignore"):
        gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(length - 1, min_periods=length - 1).sum()
    keep = var > (REAL.VAR_FLOOR if floor else 0.0)
    if trust:
        span = rolling.max() - rolling.min()
        bound = span * span
        keep = keep & (var <= 0.25 * bound * (1.0 + REAL.NOISE_FLOOR)) \
            & (gap <= (length - 1) * bound * (1.0 + REAL.NOISE_FLOOR))
    with np.errstate(invalid="ignore", divide="ignore"):
        return Series(np.sqrt((gap / var.where(keep)).to_numpy()),
                      index=close.index)


def guards():
    head("Guard 1. the variance floor")
    print(f"  NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR:.6e} "
          f"VAR_FLOOR={REAL.VAR_FLOOR:.6e}")
    for name, frame in (("flat 50.0 x300", Series(np.full(300, 50.0))),
                        ("1%-a-bar geometric ladder", geometric_ladder())):
        guarded = ts_cid_ce_20(frame)
        unguarded = module_variant(frame, floor=False, trust=False)
        src_zero = source_windowed(frame, guard="none")
        print(f"  {name}: module fires={int(guarded.notna().sum())} "
              f"unguarded fires={int(unguarded.notna().sum())} "
              f"unguarded max={float(unguarded.max()):.4f} "
              f"tsfresh's 0.0 branch fires={int(src_zero.notna().sum())} "
              f"of which zero={int((src_zero.dropna() == 0.0).sum())}")
    frame = walk(300, sigma=1e-6)
    ours = ts_cid_ce_20(frame)
    theirs = source_windowed(frame, guard="isclose")
    print(f"  sigma=1e-6 walk: module fires={int(ours.notna().sum())} "
          f"median={float(ours.median()):.4f} | an `isclose(sd, 0)` guard "
          f"fires={int(theirs.notna().sum())}")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        closes = Series(price + tick * np.arange(300))
        r = closes / closes.shift(1) - 1.0
        v = float(r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0).iloc[-1])
        print(f"  one-tick-a-bar ladder price={price:g} tick={tick:g}: "
              f"window var={v:.3e} fires={int(ts_cid_ce_20(closes).notna().sum())}")

    head("Guard 2. tsfresh's 0.0 is below the reachable minimum")
    lo, _ = closed_form_bounds(LENGTH)
    print(f"  reachable minimum at length 20 = {lo:.12f}; tsfresh returns "
          f"0.0 when the window's sd is exactly 0, this module returns NaN")

    head("Guard 3. the accumulator trust test")
    frame = walk(400, seed=21)
    for exponent in (2, 4, 6, 8):
        holed = frame.copy()
        holed.iloc[200] = float(frame.iloc[199]) * 10.0 ** exponent
        tail = slice(222, 400)      # holds no part of the planted return
        strict = ts_cid_ce_20(holed)
        loose = module_variant(holed, trust=False)
        oracle = source_windowed(holed)
        sole = int((strict.isna() & loose.notna()).sum())
        print(f"  planted return 1e+{exponent}: tail NaN strict="
              f"{int(strict.iloc[tail].isna().sum())} loose="
              f"{int(loose.iloc[tail].isna().sum())} oracle="
              f"{int(oracle.iloc[tail].isna().sum())} "
              f"bars NaN only because of the trust test={sole} "
              f"max|loose - oracle| on the tail="
              f"{float((loose.iloc[tail] - oracle.iloc[tail]).abs().max()):.3e}")
    # Why 1e+8 is NaN even without the trust test: the residue the online
    # accumulators keep is larger than the quantity itself, so one of them
    # goes non-positive and the division or the square root has nothing to
    # work with.
    holed = frame.copy()
    holed.iloc[200] = float(frame.iloc[199]) * 1e8
    r = holed / holed.shift(1) - 1.0
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    var = roll.var(ddof=0)
    with np.errstate(over="ignore"):
        gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(LENGTH - 1, min_periods=LENGTH - 1).sum()
    tail = slice(222, 400)
    print(f"  planted 1e+8, bars 222..399: var<=0 on "
          f"{int((var.iloc[tail] <= 0).sum())} bars, "
          f"0 < var <= floor on "
          f"{int(((var.iloc[tail] > 0) & (var.iloc[tail] <= REAL.VAR_FLOOR)).sum())}, "
          f"gap<0 on {int((gap.iloc[tail] < 0).sum())}, "
          f"var>floor and gap>=0 on "
          f"{int(((var.iloc[tail] > REAL.VAR_FLOOR) & (gap.iloc[tail] >= 0)).sum())}")
    # How far the damage reaches, and whether the column ever recovers. The
    # per-return square bound keeps an UNREPRESENTABLE square local; it does
    # nothing about a representable one that ruins the accumulator's
    # conditioning, which is a different failure and is measured here rather
    # than described.
    long_frame = walk(2000, seed=21)
    for exponent in (6, 7, 8, 10):
        holed = long_frame.copy()
        holed.iloc[200] = float(long_frame.iloc[199]) * 10.0 ** exponent
        col = ts_cid_ce_20(holed)
        after = col.iloc[201:]
        nan = np.flatnonzero(after.isna().to_numpy()) + 201
        fired = np.flatnonzero(after.notna().to_numpy()) + 201
        oracle = source_windowed(holed)
        # The error is taken on bars 221.. -- the first window that holds no
        # part of the planted return -- by INDEX, not by position after a
        # mask, so the same bars are compared at every magnitude.
        delta = (col - oracle).abs().iloc[221:]
        print(f"  1e+{exponent} at bar 200 of 2,000: NaN bars after it="
              f"{len(nan)}/1799 "
              f"({int(nan.min()) if len(nan) else -1}.."
              f"{int(nan.max()) if len(nan) else -1}) "
              f"fired={len(fired)} "
              f"({int(fired.min()) if len(fired) else -1}.."
              f"{int(fired.max()) if len(fired) else -1}) "
              f"max|col - oracle| on bars 221..="
              f"{float(delta.max()):.3e} over {int(delta.notna().sum())} bars")
        # The diagnosis itself, with no guard in the way: pandas' online
        # variance of the raw returns, counted where it comes back
        # non-positive. This is the evidence; the sibling row below is not,
        # because it shares this port's floor and trust test verbatim.
        r = holed / holed.shift(1) - 1.0
        with np.errstate(over="ignore"):
            raw_var = r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
        print(f"    unguarded rolling.var(ddof=0) <= 0 on bars 221..: "
              f"{int((raw_var.iloc[221:] <= 0).sum())}/1779; "
              f"non-finite: {int((~np.isfinite(raw_var.iloc[221:])).sum())}")
        ac = ts_ac1_60(holed, length=LENGTH)
        print(f"    the same frame through ts_ac1_60 (same rolling.var, and "
              f"the same floor and trust test, so equal masks are expected): "
              f"NaN bars after bar 200={int(ac.iloc[201:].isna().sum())}/1799")
    # A volatile stretch followed by a frozen one: the online accumulators
    # carry a residue of the volatile squares into windows whose own returns
    # are far smaller than that residue. This is the shape the trust test is
    # for, and the variance floor cannot see it -- the residue is itself far
    # above the floor.
    for sigma_hi, sigma_lo in ((0.3, 1e-9), (0.3, 1e-7), (0.05, 1e-9)):
        rng = np.random.default_rng(5)
        r = np.concatenate([rng.normal(0.0, sigma_hi, 200),
                            rng.normal(0.0, sigma_lo, 200)])
        twoscale = Series(100.0 * np.exp(np.cumsum(r)))
        strict = ts_cid_ce_20(twoscale)
        loose = module_variant(twoscale, trust=False)
        oracle = source_windowed(twoscale)
        quiet = slice(221, 400)
        sole = (strict.isna() & loose.notna()).to_numpy()
        bad = (loose.iloc[quiet] - oracle.iloc[quiet]).abs()
        r = twoscale / twoscale.shift(1) - 1.0
        raw_var = r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
        print(f"  volatile sigma={sigma_hi:g} then frozen sigma={sigma_lo:g}: "
              f"strict fires={int(strict.notna().sum())} loose fires="
              f"{int(loose.notna().sum())} NaN only because of the trust "
              f"test={int(sole.sum())} "
              f"({int(np.flatnonzero(sole).min()) if sole.any() else -1}.."
              f"{int(np.flatnonzero(sole).max()) if sole.any() else -1}) "
              f"max|loose - oracle| on 221.. ="
              f"{float(bad.max()):.3e} oracle median there="
              f"{float(oracle.iloc[quiet].median()):.4f} "
              f"unguarded var<=0 on 221..="
              f"{int((raw_var.iloc[quiet] <= 0).sum())} "
              f"0<var<=floor on 221..="
              f"{int(((raw_var.iloc[quiet] > 0) & (raw_var.iloc[quiet] <= REAL.VAR_FLOOR)).sum())}")
    for name, fr in (("walk", walk()), ("tick-rounded", tick_rounded()),
                     ("ar1", ar1()), ("ar1 phi=-0.5", ar1(phi=-0.5)),
                     ("alternating", alternating()),
                     ("sigma=1e-6 walk", walk(1500, sigma=1e-6)),
                     ("fine-tick ladder", Series(50.0 + 0.01 * np.arange(1500)))):
        strict = ts_cid_ce_20(fr)
        loose = module_variant(fr, trust=False)
        print(f"  {name}: cost of the trust test="
              f"{int((loose.notna() & strict.isna()).sum())} bars "
              f"(fires={int(strict.notna().sum())})")
    # How tight the two bounds are on a frame that attains them.
    fr = alternating()
    r = fr / fr.shift(1) - 1.0
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    span = roll.max() - roll.min()
    gap = Series(np.square(r.diff().to_numpy()),
                 index=r.index).rolling(LENGTH - 1,
                                        min_periods=LENGTH - 1).sum()
    ratio_v = (roll.var(ddof=0) / (0.25 * span * span)).dropna()
    ratio_g = (gap / ((LENGTH - 1) * span * span)).dropna()
    print(f"  alternating frame: var/bound max={float(ratio_v.max()):.12f} "
          f"gap/bound max={float(ratio_g.max()):.12f}")

    head("Guard 3b. is the squared-difference sum ever negative?")
    # The reason the module has no `gap >= 0` test: count the negatives over
    # every frame this script builds, rather than asserting there are none.
    frames = {
        "walk": walk(), "tick-rounded": tick_rounded(), "ar1": ar1(),
        "ar1 phi=-0.5": ar1(phi=-0.5), "alternating": alternating(),
        "sigma=1e-6 walk": walk(1500, sigma=1e-6),
        "geometric ladder": geometric_ladder(),
        "flat": Series(np.full(300, 50.0)),
        "fine-tick ladder": Series(50.0 + 0.01 * np.arange(1500)),
        "mean-dominated": mean_dominated(),
        # NOT the two-scale frame of Guard 3: one generator drawn twice, so
        # the frozen half is the SAME noise at a second scale. It is a
        # different shape, which is the point of counting it here.
        "two-scale, same noise at two scales": Series(100.0 * np.exp(np.cumsum(
            np.concatenate([np.random.default_rng(5).normal(0, 0.3, 200),
                            np.random.default_rng(5).normal(0, 1e-9, 200)])))),
    }
    for exponent in (6, 7, 8, 10):
        holed = walk(2000, seed=21).copy()
        holed.iloc[200] = float(holed.iloc[199]) * 10.0 ** exponent
        frames[f"spike 1e+{exponent}"] = holed
    for idx, value in ((200, 1e-300), (200, 0.0), (200, np.inf)):
        bad = walk(400, seed=21).copy()
        bad.iloc[idx] = value
        frames[f"bad close {value!r}"] = bad
    total_windows = negatives = 0
    for name, fr in frames.items():
        r = fr / fr.shift(1) - 1.0
        r = r.where(np.isfinite(r))
        with np.errstate(over="ignore"):
            square = np.square(r.to_numpy())
        r = r.where(square < np.finfo(float).max / (8 * LENGTH))
        with np.errstate(over="ignore"):
            gap = Series(np.square(r.diff().to_numpy()), index=r.index)
        gap = gap.rolling(LENGTH - 1, min_periods=LENGTH - 1).sum().dropna()
        total_windows += len(gap)
        negatives += int((gap < 0).sum())
    print(f"  {len(frames)} frames, {total_windows} windows: "
          f"negative sums={negatives}")

    head("Guard 4. the per-return square bound")
    ceiling = math.sqrt(np.finfo(float).max / (8 * LENGTH))
    print(f"  the ceiling it puts on a return at length 20: {ceiling:.4e}")
    frame = walk(400, seed=21)
    base = ts_cid_ce_20(frame)
    for planted in ({200: 1e-300}, {200: 1e-200, 230: 1e-200}):
        holed = frame.copy()
        for idx, value in planted.items():
            holed.iloc[idx] = value
        guarded = ts_cid_ce_20(holed)
        unguarded = module_variant(holed, overflow=False)
        lost = np.flatnonzero((base.notna() & guarded.isna()).to_numpy())
        lost_u = np.flatnonzero((base.notna() & unguarded.isna()).to_numpy())
        print(f"  planted {planted}: guarded lost={len(lost)} bars "
              f"({int(lost.min())}..{int(lost.max())}) unguarded lost="
              f"{len(lost_u)} bars ({int(lost_u.min())}..{int(lost_u.max())})")

    head("Guard 5. NaN rules")
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = frame.copy()
        holed.iloc[200] = bad
        out = ts_cid_ce_20(holed)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        moved = base.notna() & out.notna() & (base != out)
        print(f"  close={bad!r}: emptied={len(emptied)} bars "
              f"({int(emptied.min())}..{int(emptied.max())}) "
              f"earlier-bars-moved={int(moved.iloc[:200].sum())}")
    for identical in (19, 20, 21, 25):
        flat = frame.copy()
        flat.iloc[200:200 + identical] = float(frame.iloc[200])
        out = ts_cid_ce_20(flat)
        holes = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        where = f"({int(holes.min())}..{int(holes.max())})" if len(holes) else ""
        print(f"  {identical} identical closes: emptied={len(holes)} bars "
              f"{where}")
    print(f"  warm-up: insufficient history returns None="
          f"{ts_cid_ce_20(walk(LENGTH)) is None}; exactly {LENGTH + 1} closes "
          f"fires={int(ts_cid_ce_20(walk(LENGTH + 1, seed=2)).notna().sum())} "
          f"at bar "
          f"{int(ts_cid_ce_20(walk(LENGTH + 1, seed=2)).notna().to_numpy().argmax())}")

    head("Guard 6. parameters")
    for length in (None, 0, -5, 1, 2, 0.5, 2.9, 3, 50.9):
        out = ts_cid_ce_20(walk(400, seed=31), length=length)
        print(f"  length={length!r}: name={out.name} "
              f"fires={int(out.notna().sum())} "
              f"distinct={int(out.nunique())}")
    close = walk(400, seed=31)
    a, b = ts_cid_ce_20(close, length=10), ts_cid_ce_20(close, length=250)
    m = a.notna() & b.notna()
    print(f"  length 10 vs 250: spearman="
          f"{float(a[m].corr(b[m], method='spearman')):.6f} n={int(m.sum())}")
    print(f"  fillna=-9.0: filled="
          f"{int((ts_cid_ce_20(walk(200, seed=13), fillna=-9.0) == -9.0).sum())}")


# ------------------------------------------------------------------- cost


def timed(close, length):
    tracemalloc.start()
    t0 = time.perf_counter()
    ts_cid_ce_20(close, length=length)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return elapsed, peak


def timed_variant(close, trust):
    t0 = time.perf_counter()
    module_variant(close, trust=trust)
    return time.perf_counter() - t0


def cost():
    head("Cost on 400,000 bars")
    close = walk(400_000, seed=5)
    for run in range(3):
        parts = []
        for length in (3, 20, 60, 250):
            elapsed, peak = timed(close, length)
            parts.append(f"length={length}: {elapsed * 1e3:.0f} ms / "
                         f"{peak / 1e6:.1f} MB")
        print(f"  run {run + 1}: " + "  ".join(parts))
    for run in range(2):
        with_trust = timed_variant(close, True)
        without = timed_variant(close, False)
        print(f"  trust test on/off, run {run + 1}: "
              f"{with_trust * 1e3:.0f} ms vs {without * 1e3:.0f} ms")
    t0 = time.perf_counter()
    tracemalloc.start()
    source_windowed(close)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"  the window-by-window oracle: {(time.perf_counter() - t0):.1f} s "
          f"/ {peak / 1e6:.1f} MB")


if __name__ == "__main__":
    print("pandas_ta.statistics.ts_cid_ce_20 -- measurements for issue #95")
    print(f"NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR:.6e} "
          f"VAR_FLOOR={REAL.VAR_FLOOR:.6e} MIN_LENGTH={REAL.MIN_LENGTH}")
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    sections = {"a": gate_a, "b": gate_b, "cd": gate_c_d, "meaning": meaning,
                "guards": guards, "cost": cost}
    for key, fn in sections.items():
        if only in (None, key):
            fn()
