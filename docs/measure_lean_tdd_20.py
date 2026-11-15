# -*- coding: utf-8 -*-
"""Reproduce every number in docs/LeanTdd20Measured.md for `lean_tdd_20`
(PandasTa issue #87, LEAN-TDD-20).

Run from the repository root:

    python docs/measure_lean_tdd_20.py

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

import pandas_ta as ta
from pandas_ta.statistics.lean_tdd_20 import lean_tdd_20

LENGTH = 20
WARMUP = LENGTH          # bars 0 .. LENGTH-1 are NaN; the first value is at LENGTH


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def tick_rounded(n=1500, seed=55, decimals=2):
    """Prices on a 0.01 grid, as real quotes are: the frame with EXACT ties,
    so returns that are exactly zero. For this column a zero return is not a
    special case -- it contributes a zero square like any up bar -- so the
    grid is here to show that, not to decide a reading."""
    return Series(np.round(walk(n, seed).to_numpy(), decimals))


def rally(n=300, step=1.004):
    """Monotone up: every return is positive, so every window's shortfall is
    zero and the column is EXACTLY zero. The frame that shows the column's
    zero is a reading and not missing data."""
    return Series(100.0 * step ** np.arange(n, dtype=float))


def flat(n=300, level=50.0):
    return Series(np.full(n, float(level)))


def ar1(n=1500, phi=0.0, seed=40, sigma=0.01):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + eps[i]
    return Series(100.0 * np.exp(np.cumsum(r)))


def skewed(n=1500, seed=23, sigma=0.015, sign=-1.0):
    """Returns with the SAME per-bar standard deviation as a gaussian walk
    and a deliberate skew: many small moves one way and occasional large ones
    the other. `sign=-1` puts the big moves on the DOWN side.

    Built from a two-point mixture so the standard deviation is set exactly
    by construction: with probability p the move is `sign * big`, otherwise
    `-sign * small`, with `p * big**2 + (1 - p) * small**2` held at sigma**2
    and the mean at zero. Standardised after the draw so the realised sd of
    the two paths matches to the last digits rather than in expectation."""
    rng = np.random.default_rng(seed)
    p = 0.1
    big = sigma * math.sqrt((1.0 - p) / p)
    small = sigma * math.sqrt(p / (1.0 - p))
    draw = rng.random(n) < p
    r = np.where(draw, sign * big, -sign * small)
    r = (r - r.mean()) / r.std(ddof=0) * sigma
    return Series(100.0 * np.exp(np.cumsum(r)))


def cancellation(n=200, drop=0.5, step=1.001):
    """One huge down bar, then nothing but up bars. Once the big square has
    left the window every square in it is exactly zero, so this is the frame
    on which `rolling.mean`'s add-and-remove accumulation can leave a residue
    either side of zero -- and a NEGATIVE residue would make `sqrt` NaN."""
    c = 100.0 * step ** np.arange(n, dtype=float)
    c[50:] = c[50:] * drop
    return Series(c)


def ohlc(n=1500, seed=11):
    close = walk(n, seed)
    rng = np.random.default_rng(seed + 1)
    spread = close * rng.uniform(0.005, 0.02, n)
    high = close + spread * rng.uniform(0.3, 1.0, n)
    low = close - spread * rng.uniform(0.3, 1.0, n)
    return pd.DataFrame({"open": close.shift(1).fillna(close.iloc[0]),
                         "high": high, "low": low, "close": close,
                         "volume": Series(np.full(n, 1000.0))})


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
    # Spearman to EIGHT decimals on purpose: a last-bit difference breaks
    # exact ties in the column, so a rank correlation that is not exactly 1
    # rounds to 1.000000 at six and would be reported as "identical ranking"
    # when it is not.
    print(f"  {name}: n={int(m.sum())} max|diff|={diff.max():.6e} "
          f"bit-equal={bit}/{int(m.sum())} spearman={rho:.8f} "
          f"nan-masks-agree={masks_agree}")
    return float(diff.max()), bit, rho, masks_agree


# ----------------------------------------------------------------- Gate A

HAND = [
    # closes, length, what the arithmetic says
    ([8.0, 4.0, 2.0, 1.0], 3,
     "three returns of -0.5: mean square 0.25, sqrt EXACTLY 0.5"),
    ([100.0, 50.0, 100.0, 200.0, 100.0], 2,
     "squares nan, .25, 0, 0, .25 -> sqrt(.125), 0 EXACTLY, sqrt(.125)"),
    ([100.0, 50.0, 100.0, 100.0], 3,
     "one shortfall in three returns: sqrt(0.25/3), not sqrt(0.25/1)"),
]


def gate_a_hand():
    head("Gate A1 -- hand-derived windows, exact arithmetic")
    print(f"  expected bar 3 of [8,4,2,1] at length 3: {0.5!r}")
    print(f"  expected sqrt(0.125) = {math.sqrt(0.125)!r}")
    print(f"  expected sqrt(0.25/3) = {math.sqrt(0.25 / 3.0)!r}")
    for closes, length, note in HAND:
        out = lean_tdd_20(Series(closes), length=length)
        print(f"  {closes} length={length} -> {list(out.to_numpy())}")
        print(f"      {note}")
    one = lean_tdd_20(Series([8.0, 4.0, 2.0, 1.0]), length=3)
    print(f"  bit-equal to 0.5 exactly: {float(one.iloc[3]) == 0.5}")
    two = lean_tdd_20(Series([100.0, 50.0, 100.0, 200.0, 100.0]), length=2)
    print("  bit-equal to sqrt(0.125) exactly: "
          f"{float(two.iloc[2]) == math.sqrt(0.125)}, "
          f"{float(two.iloc[4]) == math.sqrt(0.125)}")
    print(f"  the middle window is EXACTLY zero: {float(two.iloc[3]) == 0.0}")
    three = lean_tdd_20(Series([100.0, 50.0, 100.0, 100.0]), length=3)
    print("  bit-equal to sqrt(0.25/3) exactly: "
          f"{float(three.iloc[3]) == math.sqrt(0.25 / 3.0)}")
    print("  the shortfalls-only reading would be sqrt(0.25/1) = 0.5, which "
          f"is {abs(float(three.iloc[3]) - 0.5):.6e} away")


def screen_candidate():
    """`REG["lean_tdd_20"]["fn"]` out of the screen's own registry, when this
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
    return mod.REG["lean_tdd_20"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `lean_tdd_20`, retyped:

        return np.sqrt(mean(ret(c).clip(upper=0) ** 2, 20))

    with the screen's operators `ret(c) = c / c.shift(1) - 1` and
    `mean(x, n) = x.rolling(n).mean()`."""
    c = close.astype(float)
    r = c / c.shift(1) - 1.0
    return np.sqrt((r.clip(upper=0.0) ** 2).rolling(length).mean())


def scalar_loop(close, length=LENGTH):
    """Independent per-window implementation in plain Python scalars: no
    pandas rolling, and the window summed by `math.fsum`, which is EXACT --
    so a difference against the module is the rolling accumulation's, not the
    formula's."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    tiny = 2.2250738585072014e-308  # float64 smallest normal

    def ok(v):
        return math.isfinite(v) and v >= tiny

    def shortfall(a, b):
        """min(b / a - 1, 0)**2 for two closes, or None if either is bad."""
        if not (ok(a) and ok(b)):
            return None
        d = b / a - 1.0
        return (d * d) if d < 0.0 else 0.0

    for t in range(length, len(c)):
        window = [shortfall(c[i - 1], c[i]) for i in range(t - length + 1, t + 1)]
        if any(v is None for v in window):
            continue
        out[t] = math.sqrt(math.fsum(window) / length)
    return Series(out, index=close.index)


def variant(close, length=LENGTH, divisor="window", window="returns",
            warmup="nan", ddof=0, spelling="minimum"):
    """The module's computation with ONE reading changed."""
    px = close.astype(float)
    r = px / px.shift(1) - 1.0
    if spelling == "minimum":
        s = np.minimum(r - 0.0, 0.0)
    elif spelling == "clip":
        s = r.clip(upper=0.0)
    elif spelling == "where":
        s = Series(np.where(r < 0.0, r, 0.0), index=r.index).where(r.notna())
    else:                                     # negated upside of -r
        s = -((-r).clip(lower=0.0))
    sq = s ** 2
    width = length if window == "returns" else length - 1
    mp = 1 if warmup == "partial" else width

    if divisor == "shortfalls":
        # Divide by the COUNT of returns below the target instead of by the
        # window -- the reading this port rejects. It is also exactly the
        # "drop the up bars rather than count them as zeros" reading: an
        # average over only the bars that have a shortfall.
        total = sq.rolling(width, min_periods=mp).sum()
        fell = (r < 0.0).astype(float).rolling(width, min_periods=mp).sum()
        out = np.sqrt(total / fell.where(fell > 0))
        return out.where(r.rolling(width, min_periods=mp).count() == width) \
            if warmup == "nan" else out
    n = width - ddof
    return np.sqrt(sq.rolling(width, min_periods=mp).sum() / n)


def gate_a_oracles():
    head("Gate A2 -- against the screen prototype")
    close = walk()
    base = lean_tdd_20(close)
    print(f"  fired bars: {int(base.notna().sum())} of {len(close)}; "
          f"first value at bar {int(base.notna().to_numpy().argmax())}")
    compare("the prototype retyped here", base, prototype(close))
    fn = screen_candidate()
    if fn is None:
        print("  the screen's own candidate: docs/issues/screen/ind_screen.py "
              "is absent (gitignored), so it was NOT compared in this run")
    else:
        o = close.shift(1).fillna(close.iloc[0])
        v = Series(np.full(len(close), 1000.0), index=close.index)
        got = Series(np.asarray(fn(o, close * 1.01, close * 0.99, close, v),
                                dtype=float), index=close.index)
        compare("the screen's registry candidate `lean_tdd_20`", base, got)

    head("Gate A3 -- against an independent scalar loop (math.fsum, exact)")
    for label, frame in (("walk", walk(400, seed=5)),
                         ("0.01 grid", tick_rounded(400, seed=5)),
                         ("rally", rally(400))):
        b = lean_tdd_20(frame)
        compare(label, b, scalar_loop(frame))
        print(f"      zero share of returns: {zero_share(frame):.4f}; "
              f"exact zeros in the column: "
              f"{int((b.dropna() == 0.0).sum())}/{int(b.notna().sum())}")


def gate_a_readings():
    head("Gate A4 -- the readings the wording leaves open, each priced")
    frames = (("walk", walk()), ("0.01 grid", tick_rounded()))
    for label, close in frames:
        base = lean_tdd_20(close)
        print(f"  -- {label} (zero share {zero_share(close):.4f})")
        compare("divisor = shortfall COUNT, not the window (same reading as "
                "dropping the up bars)",
                base, variant(close, divisor="shortfalls"))
        compare("window holds `length` CLOSES (one return fewer)",
                base, variant(close, window="closes"))
        compare("sample divisor length - 1 (ddof=1)",
                base, variant(close, ddof=1))
        part = variant(close, warmup="partial")
        compare("partial windows during the warm-up", base, part)
        pre = part.iloc[:WARMUP]
        print(f"      the partial reading fills {int(pre.notna().sum())} of "
              f"the {WARMUP} warm-up bars this port leaves NaN")
    print(f"  sqrt(20/19) = {math.sqrt(20.0 / 19.0):.6f} is the constant "
          "factor between the population and sample divisors")

    head("Gate A5 -- the spellings that are NOT readings")
    for label, close in (("walk", walk()), ("0.01 grid", tick_rounded()),
                         ("rally", rally(1500))):
        base = lean_tdd_20(close)
        for name in ("clip", "where", "negated"):
            compare(f"{label}: shortfall spelled `{name}`",
                    base, variant(close, spelling=name))

    head("Gate A6 -- no floor under the square root: what cancellation does")
    for label, close in (("one -50% bar, then only up bars", cancellation()),
                         ("rally", rally()), ("flat", flat())):
        r = close / close.shift(1) - 1.0
        mean_sq = (np.minimum(r, 0.0) ** 2).rolling(
            LENGTH, min_periods=LENGTH).mean()
        done = mean_sq.notna()
        below = mean_sq[done & (mean_sq < 0.0)]
        resid = mean_sq[done & (mean_sq != 0.0)]
        out = lean_tdd_20(close)
        print(f"  {label}: complete windows {int(done.sum())}, "
              f"means < 0: {len(below)}, exactly 0: "
              f"{int((mean_sq[done] == 0.0).sum())}, non-zero: {len(resid)}")
        print(f"      the column: fired {int(out.notna().sum())}, NaN on a "
              f"complete window: {int((done & out.isna()).sum())}, exact "
              f"zeros {int((out.dropna() == 0.0).sum())}, "
              f"min {float(out.min()):.6e}")


# ----------------------------------------------------------------- Gate B

_REAL = importlib.import_module("pandas_ta.statistics.lean_tdd_20")

MUTANTS = {
    "write_shift": (
        "    tdd = np.sqrt(mean_squared)",
        "    tdd = np.sqrt(mean_squared).shift(-length)"),
    "forward_return": (
        "    r = px / px.shift(1) - 1.0",
        "    r = px.shift(-1) / px - 1.0"),
    "forward_square": (
        "    squared = np.minimum(r - TARGET, 0.0) ** 2",
        "    squared = (np.minimum(r - TARGET, 0.0) ** 2).shift(-1)"),
    "centered_mean": (
        "    mean_squared = squared.rolling(length, min_periods=length).mean()",
        "    mean_squared = squared.rolling(length, min_periods=length, "
        "center=True).mean()"),
}
OFFSETS = range(60, 1500, 40)  # past the 20-bar warm-up


def load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lean_tdd_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def moved_before(base, out, j):
    a, b = base.iloc[:j], out.iloc[:j]
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def leaks(fn, close, other):
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        if moved_before(base, fn(p), j):
            hits += 1
    return hits


def halve_tail(close, j):
    """Every close from `j` onward times 0.5. A power of two divides out of
    every later return bit-exactly, so this changes EXACTLY ONE return --
    `r[j]`, which becomes about -0.5 and so is certainly a SHORTFALL. The
    path sweep cannot promise that: a replacement return that is positive
    contributes a zero square exactly as the one it replaced did."""
    p = close.copy()
    p.iloc[j:] = close.iloc[j:].to_numpy() * 0.5
    return p


def flip_leaks(fn, close):
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        if moved_before(base, fn(halve_tail(close, j)), j):
            hits += 1
    return hits


def gate_b():
    head("Gate B -- causality by mutant (path sweep, 36 J values)")
    pairs = {
        "walk": (walk(), walk(seed=97)),
        "walk_vs_rally": (walk(), rally(1500)),
        "0.01 grid": (tick_rounded(), tick_rounded(seed=56)),
        "skewed_down": (skewed(), skewed(seed=24)),
    }
    frames = {"walk": walk(), "rally": rally(1500),
              "0.01 grid": tick_rounded(), "skewed_down": skewed()}
    print(f"  J values swept: {len(list(OFFSETS))}")
    for label, (close, other) in pairs.items():
        print(f"  real module, {label}: "
              f"{leaks(lean_tdd_20, close, other)}/{len(list(OFFSETS))} leaks")
    for name, (old, new) in MUTANTS.items():
        mod = load_mutant(old, new)
        for label, (close, other) in pairs.items():
            live = not mod.lean_tdd_20(close).equals(lean_tdd_20(close))
            print(f"  mutant {name}, {label}: "
                  f"{leaks(mod.lean_tdd_20, close, other)}/"
                  f"{len(list(OFFSETS))} caught (live={live})")

    head("Gate B -- the directed probe: halve the tail, so r[J] is a shortfall")
    for label, close in frames.items():
        r = close / close.shift(1) - 1.0
        changed = others = 0
        for j in OFFSETS:
            pr = halve_tail(close, j) / halve_tail(close, j).shift(1) - 1.0
            if float(pr.iloc[j]) < 0.0 and float(pr.iloc[j]) != float(r.iloc[j]):
                changed += 1
            rest, prest = r.drop(r.index[j]), pr.drop(pr.index[j])
            m = rest.notna()
            others += int((rest[m] != prest[m]).sum())
        print(f"  {label}: r[J] became a shortfall at {changed}/"
              f"{len(list(OFFSETS))} J, other returns moved {others} times")
        print(f"      real module: {flip_leaks(lean_tdd_20, close)}/"
              f"{len(list(OFFSETS))} leaks")
    for name, (old, new) in MUTANTS.items():
        mod = load_mutant(old, new)
        for label, close in frames.items():
            print(f"  mutant {name}, {label}: "
                  f"{flip_leaks(mod.lean_tdd_20, close)}/"
                  f"{len(list(OFFSETS))} caught")

    head("Gate B -- offset is the only caller-reachable look-ahead")
    close = walk(400, seed=3)
    base = lean_tdd_20(close)
    for off in (2, -2):
        same = lean_tdd_20(close, offset=off).equals(base.shift(off))
        print(f"  offset={off} is exactly the default shifted: {same}")


# ----------------------------------------------------------------- Gate C

def describe(label, out, n):
    d = out.dropna()
    fired = int(len(d))
    print(f"  {label}: fired {fired}/{n} distinct {int(d.nunique())} "
          f"zeros {int((d == 0.0).sum())} "
          f"min {float(d.min()):.6f} p10 {float(d.quantile(0.1)):.6f} "
          f"median {float(d.median()):.6f} p90 {float(d.quantile(0.9)):.6f} "
          f"max {float(d.max()):.6f}")


def gate_c():
    head("Gate C -- reachability and what the column reads (synthetic)")
    n = 1500
    # The three sigma rows share seed 11, so they are ONE set of standard
    # normals scaled by sigma -- common random numbers, not three draws.
    # Near-proportionality is then close to an identity, which is why the
    # independent-seed triple below is printed as well.
    for sigma in (0.005, 0.015, 0.045):
        describe(f"gaussian walk, sigma={sigma} (seed 11, common innovations)",
                 lean_tdd_20(walk(n, sigma=sigma)), n)
    for phi in (0.8, 0.4, -0.4, -0.8):
        describe(f"AR(1) returns, phi={phi:+.1f}",
                 lean_tdd_20(ar1(n, phi=phi, seed=40)), n)
    for i, sigma in enumerate((0.005, 0.015, 0.045)):
        describe(f"gaussian walk, sigma={sigma} (seed {101 + i}, independent)",
                 lean_tdd_20(walk(n, seed=101 + i, sigma=sigma)), n)
    describe("0.01 grid", lean_tdd_20(tick_rounded()), n)
    describe("rally (300 bars, every return up)", lean_tdd_20(rally()), 300)
    describe("flat (300 bars)", lean_tdd_20(flat()), 300)

    head("Gate C -- the skew is what it adds over volatility")
    down, up = skewed(sign=-1.0), skewed(sign=+1.0)
    for label, frame in (("big moves DOWN", down), ("big moves UP", up)):
        r = (frame / frame.shift(1) - 1.0).dropna()
        print(f"  {label}: realised sd of returns {float(r.std(ddof=0)):.8f}, "
              f"skew {float(r.skew()):+.4f}")
        describe(f"  {label}", lean_tdd_20(frame), n)
    a, b = lean_tdd_20(down).dropna(), lean_tdd_20(up).dropna()
    print(f"  median down-skew {float(a.median()):.6f} vs up-skew "
          f"{float(b.median()):.6f}: ratio {float(a.median() / b.median()):.4f}")

    head("Gate C -- the iid population value is sigma / sqrt(2)")
    rng = np.random.default_rng(123)
    sigma = 0.01
    paths = 100.0 * np.exp(np.cumsum(
        rng.normal(0.0, sigma, (2000, LENGTH + 1)), axis=1))
    est = np.array([float(lean_tdd_20(Series(p)).iloc[-1]) for p in paths])
    print(f"  windows: {len(est)}, finite {int(np.isfinite(est).sum())}")
    print(f"  population sigma/sqrt(2) = {sigma / math.sqrt(2.0):.6f}")
    print(f"  mean {est.mean():.6f} median {np.median(est):.6f} "
          f"sd {est.std(ddof=0):.6f} p10 {np.quantile(est, 0.1):.6f} "
          f"p90 {np.quantile(est, 0.9):.6f} "
          f"share above the population value "
          f"{float((est > sigma / math.sqrt(2.0)).mean()):.4f}")
    print(f"  zero windows (no down bar in 20): {int((est == 0.0).sum())}")

    head("Gate C -- against realized volatility, and against drift")
    close = walk()
    base = lean_tdd_20(close)
    r = close / close.shift(1) - 1.0
    pop_sd = r.rolling(LENGTH, min_periods=LENGTH).std(ddof=0)
    m = base.notna() & pop_sd.notna()
    print(f"  spearman vs the population sd of the same {LENGTH} returns: "
          f"{float(base[m].corr(pop_sd[m], method='spearman')):.8f} "
          f"(n={int(m.sum())})")
    sd_close = ta.stdev(close, length=LENGTH)
    m2 = base.notna() & sd_close.notna()
    print("  spearman vs `stdev` of the CLOSES (a price-level dispersion, "
          "not a return one): "
          f"{float(base[m2].corr(sd_close[m2], method='spearman')):.6f} "
          f"(n={int(m2.sum())})")
    print("  ratio of the column to sd/sqrt(2), median: "
          f"{float((base[m] / (pop_sd[m] / math.sqrt(2.0))).median()):.6f}")
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    compare("the same walk with +0.004 of log drift a bar",
            base, lean_tdd_20(drifted))

    head("Gate C -- nearest shipped columns on ONE synthetic frame (NOT Gate E)")
    df = ohlc()
    base = lean_tdd_20(df["close"])
    cand = {
        "ui_14": ta.ui(df["close"]),
        "natr_14": ta.natr(df["high"], df["low"], df["close"]),
        "stdev_20": ta.stdev(df["close"], length=LENGTH),
        "zscore_30": ta.zscore(df["close"]),
        "kurtosis_30": ta.kurtosis(df["close"]),
        "skew_30": ta.skew(df["close"]),
        "entropy_20": ta.entropy(df["close"], length=LENGTH),
        "chop_14": ta.chop(df["high"], df["low"], df["close"]),
        "rsi_14": ta.rsi(df["close"]),
        "lean_hurst_100": ta.lean_hurst_100(df["close"]),
        "lot_zeroret_60": ta.lot_zeroret_60(df["close"]),
    }
    rows, constant = [], []
    for label, col in cand.items():
        col = col.iloc[:, 0] if isinstance(col, pd.DataFrame) else col
        m = base.notna() & col.notna()
        if int(col[m].nunique()) < 2:
            constant.append(label)
            continue
        rho = float(base[m].corr(col[m], method="spearman"))
        rows.append((abs(rho), label, rho, int(m.sum())))
    for a, label, rho, k in sorted(rows, reverse=True):
        print(f"  |rho|={a:.4f} ({rho:+.4f}) vs {label} (n={k})")
    for label in constant:
        print(f"  {label}: constant on this frame, no rank correlation "
              "defined")


# ----------------------------------------------------------------- Gate D

def gate_d():
    head("Gate D -- scale-free")
    for label, close in (("walk", walk()), ("0.01 grid", tick_rounded()),
                         ("skewed down", skewed())):
        base = lean_tdd_20(close)
        print(f"  -- {label}, fired {int(base.notna().sum())}")
        for k in (8.0, 64.0, 10.0, 3.7):
            d, bit, rho, masks = compare(f"x{k}", base, lean_tdd_20(close * k))
            m = base.notna()
            rel = float(((base[m] - lean_tdd_20(close * k)[m]).abs()
                         / base[m].where(base[m] > 0)).max())
            print(f"      max relative difference: {rel:.6e}")
    close = walk()
    base = lean_tdd_20(close)
    print(f"  0 < fires < n: 0 < {int(base.notna().sum())} < {len(close)}")
    print(f"  distinct values: {int(base.nunique())}")
    print(f"  exact zeros: {int((base.dropna() == 0.0).sum())}")


# ------------------------------------------------------------ edges, guards

def edges():
    head("Edge cases")
    print(f"  {LENGTH} bars -> {lean_tdd_20(walk(LENGTH))!r}")
    exact = lean_tdd_20(walk(LENGTH + 1, seed=2))
    print(f"  exactly {LENGTH + 1} bars -> fired {int(exact.notna().sum())} "
          f"at bar {int(exact.notna().to_numpy().argmax())}")
    print("  flat 300-bar frame -> fired "
          f"{int(lean_tdd_20(flat()).notna().sum())}, all exactly zero: "
          f"{bool((lean_tdd_20(flat()).dropna() == 0.0).all())}")
    print("  rally 300-bar frame -> fired "
          f"{int(lean_tdd_20(rally()).notna().sum())}, all exactly zero: "
          f"{bool((lean_tdd_20(rally()).dropna() == 0.0).all())}")

    close = walk(400, seed=21)
    base = lean_tdd_20(close)
    for bad in (np.nan, 0.0, -5.0, np.inf, 1e-310):
        holed = close.copy()
        holed.iloc[200] = bad
        out = lean_tdd_20(holed)
        emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
        shared = base.notna() & out.notna()
        moved = shared & (base != out)
        after = np.flatnonzero(moved.to_numpy())
        print(f"  close[200]={bad!r}: emptied {len(emptied)} bars "
              f"{(int(emptied.min()), int(emptied.max())) if len(emptied) else None}; "
              f"other bars that moved {int(moved.sum())}"
              + (f" (bars {[int(v) for v in after]}, max |diff| "
                 f"{float((base[moved] - out[moved]).abs().max()):.3e}, max "
                 "relative "
                 f"{float(((base[moved] - out[moved]).abs() / base[moved]).max()):.3e})"
                 if int(moved.sum()) else ""))

    head("Parameter guards (400-bar frame)")
    close = walk(400, seed=31)
    for length in (None, 0, -5, 1, 0.5, 1.9, 2, 2.9, 50, 399, 400):
        out = lean_tdd_20(close, length=length)
        if out is None:
            print(f"  length={length!r} -> None")
        else:
            print(f"  length={length!r} -> {out.name}, fired "
                  f"{int(out.notna().sum())}")
    print("  length=50.9 is the same column as length=50: "
          f"{lean_tdd_20(close, length=50.9).equals(lean_tdd_20(close, length=50))}")
    a, b = lean_tdd_20(walk(), length=10), lean_tdd_20(walk(), length=60)
    m = a.notna() & b.notna()
    print(f"  spearman(length=10, length=60) = "
          f"{float(a[m].corr(b[m], method='spearman')):.6f} (n={int(m.sum())})")
    filled = lean_tdd_20(walk(200, seed=13), fillna=-1.0)
    print(f"  fillna=-1.0 fills {int((filled == -1.0).sum())} bars "
          f"(warm-up is {WARMUP})")

    head("Wiring")
    df = ohlc(300, seed=17)
    print(f"  in Category['statistics']: "
          f"{'lean_tdd_20' in ta.Category['statistics']}")
    print(f"  df.ta.lean_tdd_20 exists: {hasattr(df.ta, 'lean_tdd_20')}")
    through = df.ta.lean_tdd_20()
    direct = lean_tdd_20(df["close"])
    print(f"  accessor == direct call: {through.equals(direct)}; "
          f"name {through.name}; category {direct.category}")


if __name__ == "__main__":
    gate_a_hand()
    gate_a_oracles()
    gate_a_readings()
    gate_b()
    gate_c()
    gate_d()
    edges()
    print()
