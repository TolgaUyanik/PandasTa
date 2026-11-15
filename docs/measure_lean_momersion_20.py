# -*- coding: utf-8 -*-
"""Reproduce every number in docs/LeanMomersion20Measured.md for
`lean_momersion_20` (PandasTa issue #86, LEAN-MOMERSION-20).

Run from the repository root:

    python docs/measure_lean_momersion_20.py

Gates A-D and the synthetic reachability only. Gate E needs the private
Backtesting engine and the 89 frozen ALTPORT-1 BIST frames, which are not in
this worktree; the launcher runs it after the porting session.
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20

LENGTH = 20


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=55, decimals=2):
    """Prices on a 0.01 grid, as real quotes are. The frame that produces
    EXACT ties, so zero returns, so pairs that are neither momentum nor mean
    reversion -- the decision the continuous walk cannot exercise.

    NOTE the seed: this is a SECOND walk (55), not the seed-11 one the
    continuous rows use, so "the walk rounded to 0.01" would be a different
    path and not a within-path comparison. It shares its path with
    `coarse_grid` only."""
    return Series(np.round(walk(n, seed).to_numpy(), decimals))


def coarse_grid(n=1500, seed=55, step=0.5):
    """The seed-55 walk on a coarser grid still: a 0.5-lira tick on a
    ~100-lira price, which makes flat bars common rather than occasional."""
    return Series(np.round(walk(n, seed).to_numpy() / step) * step)


def ulp_walk(n=300, seed=3, start=1.0):
    """A frame whose consecutive closes are ADJACENT doubles: every move is
    one ulp, and it straddles 1.0, so both binades either side are in it.
    The only frame where the x10/x3.7 claim can be attacked -- and not
    through the division: the ratio of two distinct doubles never rounds to
    1.0 (measured in `gate_d`, 0 of 299 moves read as flat here). The attack
    is FUSION, `fl(k*a) == fl(k*b)`, which turns a signed pair flat. No
    price feed produces this frame (one tick over the price is 1e-9 even at
    a price of 1e6 with a 0.001 tick, seven orders above an ulp); it is here
    to bound the claim rather than to assert it."""
    rng = np.random.default_rng(seed)
    steps = rng.choice([-1.0, 1.0], size=n)
    out = np.empty(n)
    v = float(start)
    for i in range(n):
        v = float(np.nextafter(v, np.inf if steps[i] > 0 else -np.inf))
        out[i] = v
    return Series(out)


def ohlc(n=1500, seed=11):
    close = walk(n, seed)
    rng = np.random.default_rng(seed + 1)
    spread = close * rng.uniform(0.005, 0.02, n)
    high = close + spread * rng.uniform(0.3, 1.0, n)
    low = close - spread * rng.uniform(0.3, 1.0, n)
    return high, low, close


def zero_share(close):
    r = close / close.shift(1) - 1.0
    m = r.notna()
    return float((r[m] == 0.0).sum()) / max(int(m.sum()), 1)


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
    """`REG["lean_momersion_20"]["fn"]` out of the screen's own registry, when
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
    return mod.REG["lean_momersion_20"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `lean_momersion_20`,
    retyped verbatim:

        p = ret(c) * delay(ret(c), 1)
        mc, mrc = count(p > 0, 20), count(p < 0, 20)
        return 100 * sdiv(mc, mc + mrc).where(p.shift(19).notna())

    with the screen's operators: `ret(c) = c / c.shift(1) - 1`,
    `count(cond, n) = cond.astype(float).rolling(n).sum()`, and
    `sdiv(a, b) = (a / b).replace([inf, -inf], nan)`.

    Two things it does differently from the module, both measured below: it
    multiplies the RETURNS rather than their signs, and its warm-up mask is
    only the OLDEST pair in the window (`p.shift(length - 1).notna()`), so a
    NaN in the middle of a frame reads as a shorter window instead of a hole.
    """
    c = close.astype(float)
    r = c / c.shift(1) - 1.0
    p = r * r.shift(1)
    mc = (p > 0).astype(float).rolling(length).sum()
    mrc = (p < 0).astype(float).rolling(length).sum()
    out = (mc / (mc + mrc)).replace([np.inf, -np.inf], np.nan)
    return 100 * out.where(p.shift(length - 1).notna())


def scalar_loop(close, length=LENGTH):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no pandas rolling, the counts written out as a loop."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    tiny = 2.2250738585072014e-308  # float64 smallest normal

    def ok(v):
        return math.isfinite(v) and v >= tiny

    def sign_of(a, b):
        """sign(b / a - 1) for two closes, or None if either is unusable."""
        if not (ok(a) and ok(b)):
            return None
        d = b / a - 1.0
        return 0 if d == 0.0 else (1 if d > 0.0 else -1)

    for t in range(length + 1, len(c)):
        mc = mrc = 0
        known = 0
        for i in range(t - length + 1, t + 1):       # the `length` pairs
            s1 = sign_of(c[i - 2], c[i - 1])
            s2 = sign_of(c[i - 1], c[i])
            if s1 is None or s2 is None:
                continue
            known += 1
            if s1 * s2 > 0:
                mc += 1
            elif s1 * s2 < 0:
                mrc += 1
        if known == length and mc + mrc > 0:
            out[t] = 100.0 * mc / (mc + mrc)
    return Series(out, index=close.index)


def variant(close, length=LENGTH, zeros="neither", window="pairs",
            warmup=None, spelling="ratio", pair_form="signs"):
    """The module's own computation with ONE reading changed, to price the
    readings the issue's wording leaves open."""
    px = close.astype(float)
    if spelling == "ratio":
        r = px / px.shift(1) - 1.0
    elif spelling == "log":
        r = np.log(px / px.shift(1))
    elif spelling == "diff":
        r = px.diff()
    else:
        raise ValueError(spelling)
    if pair_form == "signs":
        p = np.sign(r) * np.sign(r).shift(1)
    elif pair_form == "product":          # the prototype's spelling
        p = r * r.shift(1)
    else:
        raise ValueError(pair_form)
    width = length if window == "pairs" else length - 1

    def cnt(mask):
        return mask.astype(float).rolling(width, min_periods=width).sum()

    mc = cnt(p > 0)
    if zeros == "neither":
        mrc = cnt(p < 0)
    elif zeros == "reversion":            # `if (x > 0) MC++ else MRC++`
        mrc = cnt(p.notna() & ~(p > 0))
    else:
        raise ValueError(zeros)
    total = mc + mrc
    # emptying the denominator first means no zero reaches the division
    out = 100.0 * mc / total.where(total > 0)
    out = out.where(cnt(p.notna()) == width)
    if warmup is not None and bool(out.notna().any()):
        first = int(out.notna().to_numpy().argmax())
        out.iloc[:first] = warmup
    return out


HAND = [
    # closes, length, expected column (None = NaN), what it pins
    ([100.0, 101.0, 102.0, 101.0, 103.0, 104.0, 103.0], 4,
     [None, None, None, None, None, 50.0, 25.0],
     "return signs + + - + + -, so pairs + - - + -: a 4-pair window reads "
     "2/4 then 1/4"),
    ([10.0, 11.0, 11.0, 12.0, 13.0, 12.0, 12.0, 13.0], 3,
     [None, None, None, None, 100.0, 50.0, 50.0, 0.0],
     "flat bars: returns + 0 + + - 0 +, so pairs 0 0 + - 0 0 -- a zero pair "
     "is counted NEITHER way, so the denominator shrinks to 1, 2, 2, 1"),
    ([10.0, 11.0, 11.0, 11.0, 11.0], 3,
     [None, None, None, None, None],
     "a window whose every pair is flat has no share to report: NaN, not 50 "
     "and not 0"),
]


def gate_a():
    head("GATE A -- the source formula")
    print("""Lean's C# source is NOT in this worktree (docs/pine/ and web access are
unavailable), so the formula under test is the one issue #86 states:
  MomersionIndicator(20): 100*MC/(MC+MRC),
  MC/MRC = same/opposite-sign consecutive return pairs.""")

    print("\nA1. Hand-derived windows, exact integer arithmetic.")
    for closes, length, want, why in HAND:
        out = lean_momersion_20(Series(closes), length=length)
        got = [None if v != v else float(v) for v in out.to_numpy()]
        print(f"  closes={closes} length={length}")
        print(f"    {why}")
        print(f"    want {want}")
        print(f"    got  {got}   match={got == want}  name={out.name}")

    close = walk()
    base = lean_momersion_20(close)
    n = len(close)
    print(f"\nA2. Against the screen prototype, {n}-bar walk "
          f"({int(base.notna().sum())} fired bars):")
    compare("the prototype retyped here", base, prototype(close))
    fn = screen_candidate()
    if fn is None:
        print("  the screen's own candidate: docs/issues/ is absent in this "
              "worktree (gitignored), so this row is NOT measured here")
    else:
        o = Series(np.full(n, np.nan))
        h, l, c = ohlc(n)
        rng = np.random.default_rng(3)
        v = Series(rng.uniform(1e5, 1e6, n))
        compare("the screen's own `lean_momersion_20` candidate, imported",
                lean_momersion_20(c), fn(o, h, l, c, v).astype(float))

    print("\nA3. Against an independent scalar loop (plain Python, no numpy, "
          "no rolling):")
    short = walk(400, seed=5)
    compare("  400-bar walk", lean_momersion_20(short), scalar_loop(short))
    tick = tick_rounded(400, seed=5)
    print(f"  (and on a tick-rounded frame, {zero_share(tick):.4f} of whose "
          f"returns are exactly zero:)")
    compare("  400-bar tick-rounded walk", lean_momersion_20(tick),
            scalar_loop(tick))

    print("\nA4. The readings the wording leaves open, each priced rather "
          "than dismissed.")
    for label, frame in (("continuous walk (seed 11)", close),
                         ("seed-55 walk at 0.01", tick_rounded()),
                         ("seed-55 walk on a 0.5 grid", coarse_grid())):
        b = lean_momersion_20(frame)
        print(f"  on the {label} ({zero_share(frame):.4f} zero returns, "
              f"{int(b.notna().sum())} fired bars):")
        compare("    rejected: a zero return counts as MEAN REVERSION",
                b, variant(frame, zeros="reversion"))
        compare("    rejected: the window holds `length` RETURNS, not pairs",
                b, variant(frame, window="returns"))
        compare("    spelling: log returns instead of ratio-minus-one",
                b, variant(frame, spelling="log"))
        compare("    spelling: raw price differences instead of returns",
                b, variant(frame, spelling="diff"))
        compare("    spelling: the product of the RETURNS (prototype's)",
                b, variant(frame, pair_form="product"))
    fifty = variant(close, warmup=50.0)
    b = lean_momersion_20(close)
    print(f"  rejected: emit the neutral 50 during the warm-up -- that is "
          f"{int((b.isna() & fifty.notna()).sum())} bars of a CONSTANT at the "
          f"head of the column; after the warm-up the two agree on "
          f"{int((b.notna() & fifty.notna() & (b == fifty)).sum())} of "
          f"{int(b.notna().sum())} bars.")
    print(f"  the smallest nonzero |return| float64 can represent between two "
          f"distinct closes is about eps = {np.finfo(float).eps:.3e}, so the "
          f"product of two returns is bounded away from underflow by ~1e-32: "
          f"the sign spelling and the product spelling cannot disagree through "
          f"underflow, they can only disagree on exact zeros.")


# ----------------------------------------------------------------- Gate B

_REAL = importlib.import_module("pandas_ta.momentum.lean_momersion_20")
MUTANTS = {
    "write-shift (the whole column back-dated by `length`)": (
        "    momersion = values.where(count(pair.notna()) == length)",
        "    momersion = values.where(count(pair.notna()) == length)"
        ".shift(-length)"),
    "forward pair (`np.sign(r).shift(1)` -> `.shift(-1)`)": (
        "    pair = np.sign(r) * np.sign(r).shift(1)",
        "    pair = np.sign(r) * np.sign(r).shift(-1)"),
    "forward return (`px.shift(1)` -> `px.shift(-1)`)": (
        "    r = px / px.shift(1) - 1.0",
        "    r = px.shift(-1) / px - 1.0"),
    "centered rolling count (the one window, centered)": (
        "        return mask.astype(float).rolling(length, min_periods=length).sum()",
        "        return mask.astype(float).rolling(length, min_periods=length, "
        "center=True).sum()"),
}
OFFSETS = range(60, 1500, 40)  # past the 21-bar warm-up


def alternating(n=1500, seed=7, step=0.01, noise=0.001):
    """A hard up/down/up path: pure mean reversion, so the column reads 0 on
    every fired bar. As the perturbation partner it maximises the count a
    future-reading mutant would see, which is what makes a discrete column's
    leak detectable."""
    rng = np.random.default_rng(seed)
    r = np.where(np.arange(n) % 2 == 0, 1.0, -1.0) * step + rng.normal(0.0, noise, n)
    return Series(100.0 * np.exp(np.cumsum(r)))


def load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lean_momersion_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close, other):
    """Future-perturbation sweep: replace every bar from J onward with a
    different path and count the J values at which anything before J moves."""
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


def flip_tail(close, j):
    """Every close from `j` onward multiplied by 0.5 or 2.0 -- whichever
    CHANGES the sign of the return at bar `j`: a reversal where `r[j] != 0`,
    and flat -> up where it is zero. Multiplying by a power of two
    is exact, and it divides out of every later return, so this changes
    EXACTLY ONE return: `r[j]`. A column that reads only the past cannot move
    before bar `j`; a column that reads one bar ahead must move at `j - 1`."""
    k = 0.5 if float(close.iloc[j]) > float(close.iloc[j - 1]) else 2.0
    p = close.copy()
    p.iloc[j:] = close.iloc[j:].to_numpy() * k
    return p


def flip_leaks(fn, close):
    """The directed version of `leaks`: one sign-changed return per J instead of a
    whole replacement path. The path sweep cannot catch a one-bar-ahead
    mutant reliably on a column built from SIGNS -- a fresh random path
    repeats the sign it replaced about half the time, and then the counts do
    not move. This probe removes that coin flip."""
    base = fn(close)
    r = close / close.shift(1) - 1.0
    hits = flipped = 0
    for j in OFFSETS:
        p = flip_tail(close, j)
        pr = p / p.shift(1) - 1.0
        if np.sign(float(pr.iloc[j])) != np.sign(float(r.iloc[j])):
            flipped += 1
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits, flipped


def frame_pairs():
    return {
        "walk": (walk(), walk(seed=97)),
        "walk vs alternating": (walk(), alternating()),
        "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
        "coarse 0.5 grid": (coarse_grid(), coarse_grid(seed=56)),
    }


def flip_bases():
    """The directed probe needs one frame, not a pair, so its frames are the
    four distinct paths rather than `frame_pairs()`' replacements."""
    return {
        "walk": walk(),
        "alternating": alternating(),
        "tick-rounded": tick_rounded(),
        "coarse 0.5 grid": coarse_grid(),
    }


def gate_b():
    head("GATE B -- causality, by mutant")
    total = len(list(OFFSETS))
    print(f"""  future-perturbation sweep over {total} J values (J = {OFFSETS.start}..{max(OFFSETS)} step
  {OFFSETS.step}), on FOUR frame pairs. The column is DISCRETE -- one of at most
  {LENGTH + 1} values per window -- so a mutant that reads the future can be caught by
  coincidence-free detection only if the replacement path changes the COUNTS;
  that is why one pair replaces a walk with a hard alternating path, and two
  pairs are price grids, where zero returns exist at all.""")
    pairs = frame_pairs()
    for label, (a, b) in pairs.items():
        print(f"  real module, {label:20s} leaks at "
              f"{leaks(lean_momersion_20, a, b)}/{total} J "
              f"(fires {int(lean_momersion_20(a).notna().sum())}/{len(a)}, "
              f"{zero_share(a):.4f} zero returns)")
    for name, (old, new) in MUTANTS.items():
        mod = load_mutant(old, new)
        print(f"  mutant: {name}")
        for label, (a, b) in pairs.items():
            live = not mod.lean_momersion_20(a).equals(lean_momersion_20(a))
            print(f"    {label:20s} live={live}  caught at "
                  f"{leaks(mod.lean_momersion_20, a, b)}/{total} J")

    print(f"""
  The one-bar-ahead mutants above are caught on only about half the J values,
  and that is a property of the PROBE, not evidence of a safe mutant: the
  column reads signs, so a fresh random path repeats the sign it replaced
  about half the time and the counts do not move. The directed probe below
  removes the coin flip -- for each J it multiplies the tail by 0.5 or 2.0,
  whichever CHANGES the sign of r[J] (a reversal where r[J] != 0, flat -> up
  where it is zero), which changes exactly one return (powers of two cancel
  out of every later return, bit-exactly):""")
    flip_frames = flip_bases()
    for label, a in flip_frames.items():
        hits, flipped = flip_leaks(lean_momersion_20, a)
        print(f"    real module, {label:20s} leaks at {hits}/{total} J "
              f"(the sign of r[J] actually changed at {flipped}/{total} J)")
    for name, (old, new) in MUTANTS.items():
        mod = load_mutant(old, new)
        print(f"    mutant: {name}")
        for label, a in flip_frames.items():
            hits, _ = flip_leaks(mod.lean_momersion_20, a)
            print(f"      {label:20s} caught at {hits}/{total} J")
    print("""    The coarse grid is the frame where even the directed probe misses some
    J: there a flat bar at J - 1 makes pair[J - 1] zero whichever way r[J]
    points, so the flip is absorbed and the mutant has nothing to show.""")

    print("\n  offset, the caller-reachable look-ahead:")
    short = walk(400, seed=3)
    b = lean_momersion_20(short)
    print(f"    offset=+2 == base.shift(2):  "
          f"{lean_momersion_20(short, offset=2).equals(b.shift(2))}")
    print(f"    offset=-2 == base.shift(-2): "
          f"{lean_momersion_20(short, offset=-2).equals(b.shift(-2))}")


# ----------------------------------------------------------------- Gate C


def describe(name, s, n):
    fires = int(s.notna().sum())
    print(f"  {name}: fires {fires}/{n} nunique={int(s.nunique())} "
          f"min={s.min():.4f} p10={s.quantile(0.1):.4f} "
          f"median={s.median():.4f} p90={s.quantile(0.9):.4f} "
          f"max={s.max():.4f} share>50={float((s > 50).sum()) / max(fires, 1):.4f}")


def ar1_return_path(n, phi, seed, sigma=0.01):
    """Log returns with AR(1) autocorrelation phi: phi > 0 is persistent (a
    move that keeps going, so same-sign pairs), phi < 0 anti-persistent."""
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
    base = lean_momersion_20(close)
    describe("gaussian random walk, iid returns ", base, n)
    # ONE seed for every phi (common random numbers): the same innovations
    # run through each AR(1), so the ordering below is the phi effect and not
    # four unrelated draws.
    for phi in (0.8, 0.4, -0.4, -0.8):
        describe(f"AR(1) returns, phi={phi:+.1f}           ",
                 lean_momersion_20(ar1_return_path(n, phi, 40)), n)
    describe("hard alternating log returns      ", lean_momersion_20(alternating(n)), n)
    for label, frame in (("seed-55 walk at 0.01              ", tick_rounded(n)),
                         ("seed-55 walk on a 0.5 grid        ", coarse_grid(n))):
        describe(label, lean_momersion_20(frame), n)

    print("""  It orders persistence in the right direction, and the ordering is the
  claim. For iid returns the population value is exactly 50 (consecutive
  return signs are independent, so a pair is same-sign with probability
  1/2), and the column is unbiased in the MEDIAN but wide:""")
    rng = np.random.default_rng(123)
    m = 2000
    r = rng.normal(0.0, 0.01, (m, LENGTH + 2))
    paths = 100.0 * np.exp(np.cumsum(r, axis=1))
    est = np.array([float(lean_momersion_20(Series(p)).iloc[-1]) for p in paths])
    print(f"  {m} independent {LENGTH}-pair iid-return windows: mean "
          f"{est.mean():.4f} median {np.median(est):.4f} sd {est.std(ddof=0):.4f} "
          f"p10 {np.quantile(est, 0.1):.4f} p90 {np.quantile(est, 0.9):.4f} "
          f"share>50 {float((est > 50).mean()):.4f} "
          f"finite {int(np.isfinite(est).sum())}/{m}")
    print("""  Drift-invariance is NOT claimed: adding drift to every log return makes
  up-moves more likely, which changes the signs and so the counts. Measured,
  on the same walk with +0.004 of log drift a bar:""")
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(n)))
    compare("  walk vs the same walk with drift", base, lean_momersion_20(drifted))


# ----------------------------------------------------------------- Gate D


def gate_d():
    head("GATE D -- scale-free")
    for label, close in (("continuous walk (seed 11)", walk()),
                         ("seed-55 walk at 0.01", tick_rounded()),
                         ("seed-55 walk on a 0.5 grid", coarse_grid())):
        base = lean_momersion_20(close)
        n = len(close)
        m = base.notna()
        print(f"  {label} ({int(m.sum())} fired bars):")
        for k in (8.0, 64.0, 10.0, 3.7):
            s = lean_momersion_20(close * k)
            print(f"    x{k:g}: nan-masks agree "
                  f"{bool((base.isna() == s.isna()).all())}, bit-identical on "
                  f"{int((base[m] == s[m]).sum())}/{int(m.sum())} bars, "
                  f"max|diff| {float((base[m] - s[m]).abs().max()):.6e}")
        print(f"    0 < fires < n: 0 < {int(m.sum())} < {n}; distinct values "
              f"{int(base.nunique())}; range "
              f"[{base.min():.4f}, {base.max():.4f}]")
    print("""  Bit-identical under x8/x64 because `8a / 8b` is the same double as
  `a / b`. Bit-identical under x10/x3.7 as well, which a continuous column
  would not be: only the SIGN of the return reaches the counts; `fl(k*x)` is
  monotone, so a rescale cannot reorder two closes, and the quotient of two
  DISTINCT doubles never rounds to exactly 1.0 (for adjacent a, b the exact
  ratio is 1 + u/b with u/b in (2^-53, 2^-52], strictly past the midpoint
  between 1.0 and its neighbour), so a sign cannot be destroyed by the
  division either. The one way a sign CAN go is FUSION: `fl(k*a) == fl(k*b)`
  for two distinct closes, which turns a signed pair flat.

  Fusion is not impossible for a non-power-of-two k -- the arithmetic bound
  is weaker than it looks. Two closes g ulps apart land g*k*2^(e-f) ulps
  apart in the product's binade (x in [2^e, 2^(e+1)), k*x in [2^f, 2^(f+1)))
  and the two binade constraints only give k*2^(e-f) in (1/2, 2): at k=10
  with x in [0.8, 1), where 10x lands in [8, 16), it is 10*2^-4 = 0.625, so
  one-ulp neighbours come out 0.625 ulp apart and CAN round together. The
  same k at x in [0.5, 0.8) gives 1.25, so fusion is binade-dependent rather
  than a property of k.

  Only g = 1 can ever fuse, in two steps. The widest fusion window is 1.5
  ulp and it is at a power of two: around d = 2^(f+1), half the spacing below
  (0.5 ulp of the lower binade) plus half the spacing above (1 ulp of it)
  both round to d. The factor stays above 1/2, so the scaled gap is more
  than g/2 ulps and g >= 3 is out. For g = 2: fusing at d needs the lower
  product k*x >= d*(1 - 2^-54), which pushes the factor above 1 - 2^-54, so
  two ulps land more than 2 - 2^-53 ulps apart -- outside even the 1.5-ulp
  window; inside a binade the window is 1 ulp and g = 2 exceeds it already.
  Measured on a frame of adjacent doubles straddling 1.0 -- every move one
  ulp, which no price feed produces:""")
    u = ulp_walk()
    ub = lean_momersion_20(u)
    print(f"    one-ulp walk, {len(u)} bars: {zero_share(u):.4f} of returns "
          f"read as EXACTLY zero although every close differs from the last "
          f"(the ratio cannot round to 1.0); the column fires "
          f"{int(ub.notna().sum())}/{len(u)}")
    for k in (8.0, 64.0, 10.0, 3.7):
        s = lean_momersion_20(u * k)
        m = ub.notna() & s.notna()
        scaled = (u * k).to_numpy()
        fused = int((scaled[1:] == scaled[:-1]).sum())
        print(f"    x{k:g}: {fused:3d} of {len(u) - 1} adjacent close pairs "
              f"FUSED, {zero_share(u * k):.4f} zero returns; nan-masks agree "
              f"{bool((ub.isna() == s.isna()).all())}, bit-identical on "
              f"{int((ub[m] == s[m]).sum())}/{int(m.sum())} shared bars, "
              f"max|diff| "
              f"{(float((ub[m] - s[m]).abs().max()) if int(m.sum()) else float('nan')):.6e}")
    print("""    So the Gate D claim is bounded, and the bound is fusion: bit-identical
    on any frame of normal doubles whose k*close does not overflow and whose
    consecutive closes are at least 2 ulps apart. No real frame comes near
    the 1-ulp case -- one tick over the price is 1e-9 even at a price of 1e6,
    seven orders above the 2.2e-16 relative size of an ulp -- but that step
    is an argument from tick size, not a measurement: no real frame was read
    in this session, and Gate E's run is where real data is seen.""")
    counts = {}
    for t in range(1, LENGTH + 1):
        for mc in range(t + 1):
            counts[round(100.0 * mc / t, 12)] = True
    w = lean_momersion_20(walk()).dropna()
    print(f"  on a frame with no exact ties every pair is signed, so MC + MRC "
          f"is always {LENGTH} and the value is a multiple of "
          f"{100.0 / LENGTH:g}: measured {int(w.nunique())} distinct values, "
          f"all multiples of 5 = {bool(((w % 5.0) == 0.0).all())}. The grid "
          f"frames, which have flat bars, shrink the denominator and so show "
          f"more.")
    print(f"  the column's value set at length={LENGTH} has "
          f"{len(counts)} members (100*MC/(MC+MRC) over every reachable "
          f"MC <= MC+MRC <= {LENGTH}), so a frame showing fewer distinct "
          f"values than that is a property of the frame, not of the column.")


# ------------------------------------------------------------- edge cases


def gate_edges():
    head("EDGE CASES")
    n = 300
    flat = Series(np.full(n, 50.0))
    print(f"  exactly flat frame: fires {int(lean_momersion_20(flat).notna().sum())}"
          f"/{n} (every pair is 0, so MC + MRC == 0)")
    stair = Series(np.repeat(np.arange(1, n // 10 + 1, dtype=float) + 100.0, 10))
    s = lean_momersion_20(stair)
    sr = stair / stair.shift(1) - 1.0
    sp = np.sign(sr) * np.sign(sr).shift(1)
    print(f"  a staircase (one step up every 10 bars, flat between): fires "
          f"{int(s.notna().sum())}/{len(stair)} -- the steps are never "
          f"adjacent, so {int((sp.notna() & (sp != 0)).sum())} of "
          f"{int(sp.notna().sum())} known pairs are signed and every window reads MC + MRC == 0. NaN, "
          f"not a fake 50.")
    one_tick = Series(np.where(np.arange(n) % 2 == 0, 100.00, 100.01))
    o = lean_momersion_20(one_tick)
    print(f"  one-tick alternation 100.00 / 100.01: fires "
          f"{int(o.notna().sum())}/{n}, values {sorted(set(o.dropna()))}")

    close = walk(400, seed=21)
    base = lean_momersion_20(close)
    for label, bad in (("NaN", np.nan), ("zero", 0.0), ("negative", -5.0),
                       ("inf", np.inf), ("subnormal 1e-310", 1e-310)):
        holed = close.copy()
        holed.iloc[200] = bad
        out = lean_momersion_20(holed)
        lost = (base.notna() & out.isna()).to_numpy()
        idx = np.flatnonzero(lost)
        shared = base.notna() & out.notna()
        moved = shared & (base != out)
        print(f"  one {label} close at bar 200: empties {int(lost.sum())} bars"
              + (f" ({int(idx.min())}..{int(idx.max())})" if len(idx) else "")
              + f", other bars that move: {int(moved.sum())}"
              + f", of those before bar 200: {int(moved.iloc[:200].sum())}")
    print(f"    {LENGTH + 2} bars hold the hole's pairs: a bad close kills the "
          f"pair that ends on it and the pair that starts from it, and every "
          f"window containing either.")

    print(f"  {LENGTH + 1} bars returns None: "
          f"{lean_momersion_20(walk(LENGTH + 1)) is None}")
    exact = lean_momersion_20(walk(LENGTH + 2, seed=2))
    print(f"  exactly {LENGTH + 2} bars: fires {int(exact.notna().sum())}"
          f"/{LENGTH + 2}, first at bar "
          f"{int(exact.notna().to_numpy().argmax())}")

    print("\n  the parameter guards:")
    c = walk(400, seed=31)
    for length in (None, 0, -5, 1, 2, 0.5, 2.9, 50):
        o = lean_momersion_20(c, length=length)
        print(f"    length={length!r}: name={None if o is None else o.name}, "
              f"fires {0 if o is None else int(o.notna().sum())}")
    print(f"    length=398 on a 400-bar frame: "
          f"{lean_momersion_20(c, length=398).notna().sum()} fires; "
          f"length=399: {lean_momersion_20(c, length=399) is None} (None)")
    print("  fillna:")
    o = lean_momersion_20(walk(200, seed=13), fillna=-1.0)
    print(f"    fillna=-1.0 fills {int((o == -1.0).sum())} bars "
          f"(the {LENGTH + 1}-bar warm-up)")


# -------------------------------------------------- neighbours (NOT Gate E)


def neighbours():
    head("NEAREST NEIGHBOURS on one synthetic walk -- NOT Gate E")
    import pandas_ta as ta
    high, low, close = ohlc(1500)
    base = lean_momersion_20(close)
    cands = {
        "psl_12 (share of up bars)": ta.psl(close),
        "er_10 (efficiency ratio)": ta.er(close),
        "rsi_14": ta.rsi(close),
        "natr_14": ta.natr(high, low, close),
        "entropy_20": ta.entropy(close),
        "kurtosis_30": ta.kurtosis(close, length=30),
        "skew_30": ta.skew(close, length=30),
        "zscore_30": ta.zscore(close, length=30),
        "cfo_9": ta.cfo(close),
        "lean_hurst_100": ta.lean_hurst_100(close),
        "autocorr_lag1_20 (hand-rolled)":
            ta.log_return(close).rolling(20).corr(ta.log_return(close).shift(1)),
    }
    chop = ta.chop(high, low, close)
    cands["chop_14"] = chop if isinstance(chop, Series) else chop[chop.columns[0]]
    vhf = ta.vhf(close)
    cands["vhf_28"] = vhf if isinstance(vhf, Series) else vhf[vhf.columns[0]]
    rows = []
    for name, s in cands.items():
        s = s.astype(float)
        m = base.notna() & s.notna()
        if int(m.sum()) < 50:
            rows.append((name, float("nan"), int(m.sum())))
            continue
        rows.append((name, abs(float(base[m].corr(s[m], method="spearman"))),
                     int(m.sum())))
    for name, rho, k in sorted(rows, key=lambda r: -(r[1] if r[1] == r[1] else -1)):
        print(f"  |rho| {rho:.4f}  n={k:5d}  {name}")
    print("""  One 1,500-bar synthetic walk against a dozen shipped columns is NOT
  Gate E, which is 687 comparators over 89 frozen BIST frames. It is a smell
  test only; the issue's prototype screen measured 0.2560 vs `chop` pooled.""")


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
