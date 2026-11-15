# -*- coding: utf-8 -*-
"""Reproduce every number in docs/TsKurt60Measured.md for `ts_kurt_60`
(PandasTa issue #93, TS-KURT-60).

Run from the repository root:

    python docs/measure_ts_kurt_60.py

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

import pandas_ta
from pandas_ta.statistics.ts_kurt_60 import ts_kurt_60

LENGTH = 60
REAL = importlib.import_module("pandas_ta.statistics.ts_kurt_60")


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
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return from_returns(np.clip(r, -0.5, 0.5))


def two_point(n=1500, seed=4, sigma=0.01):
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


def zigzag_returns(n=1500, size=0.5):
    """Returns take exactly two values, +size and -size, in strict
    alternation: every 60-return window holds 30 of each, which is the
    configuration that attains the column's algebraic MINIMUM."""
    r = np.where(np.arange(n) % 2 == 0, size, -size)
    return from_returns(r)


def one_hot_returns(n=1500, length=LENGTH, size=1.0):
    """Returns are 0 except every `length`-th bar, so the window ending on
    such a bar is one-hot -- the configuration that attains the column's
    algebraic MAXIMUM."""
    r = np.zeros(n)
    r[length::length] = size
    return from_returns(r)


def flat_run_planted(n=400, seed=19, at=200, run=70):
    """A live walk with `run` identical closes planted in it, so some windows
    are degenerate and some are not -- the frame the noise-floor guard and
    its mutant are visible on."""
    close = walk(n, seed=seed).to_numpy().copy()
    close[at:at + run] = close[at]
    return Series(close)


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
          f"bars|diff|>1e-09={int((diff > 1e-9).sum())} spearman={rho_text} "
          f"distinct={int(x.nunique())}/{int(y.nunique())} "
          f"nan-masks-agree={masks_agree}")
    return float(diff.max()), bit, rho, masks_agree


# ----------------------------------------------------------------- Gate A


def bound_max(n):
    """`1 <= m4/m2**2 <= (n**2-3n+3)/(n-1)`, the upper bound attained by a
    one-hot window (`<= n` is true but slack and no window attains it), and
    the sample correction maps the SHARP bound to exactly `n`:

        m4/m2**2 (one-hot, n samples) = (n**2 - 3n + 3) / (n - 1)
        G2 = [(n**2-1) * m4/m2**2 - 3*(n-1)**2] / ((n-2)*(n-3))
           = [(n+1)(n**2-3n+3) - 3(n-1)**2] / ((n-2)*(n-3))
           = n*(n-2)*(n-3) / ((n-2)*(n-3)) = n
    """
    return float(n)


def bound_min(n):
    """`m4 / m2**2 >= 1`, with equality when the window takes two values in
    equal counts, so `g2 >= -2` and

        G2 >= ((n+1)*(-2) + 6) * (n-1) / ((n-2)*(n-3)) = -2*(n-1)/(n-3)
    """
    return -2.0 * (n - 1) / (n - 3)


def screen_candidate():
    """`REG["ts_kurt_60"]["fn"]` out of the screen's own registry, when this
    worktree has `docs/issues/` (gitignored, so a clone does not)."""
    import importlib.util
    import os
    import sys

    # Resolved off this script's own location, not the working directory: a
    # relative path would make "absent in this tree" a false statement when
    # the script is run from anywhere but the repository root.
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "docs", "issues", "screen",
        "ind_screen.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_kurt_60"]["fn"]


def prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_kurt_60`, retyped
    verbatim because that tree is gitignored:

        @cand("ts_kurt_60", "excess kurtosis of returns (60)", TS,
              "kurtosis on 60 returns")
        def _(o, h, l, c, v): return ret(c).rolling(60).kurt()

    with `ret(c) = c / c.shift(1) - 1`."""
    return (close / close.shift(1) - 1).rolling(length).kurt()


def numpy_two_pass(close, length=LENGTH, guard=True, log_returns=False,
                   biased=False, raw=False, closes_window=False):
    """The statistic computed in numpy from the CENTRED moments, two passes
    over the window -- no `rolling.kurt`, no online raw-moment recursion, so
    it shares no arithmetic with the module:

        m2, m4  = mean(d**2), mean(d**4)   with d = r - mean(r)
        g2      = m4 / m2**2 - 3
        G2      = ((n+1)*g2 + 6) * (n-1) / ((n-2)*(n-3))

    The keyword flags switch ONE reading each, so the price of a reading is a
    measurement rather than an argument.
    """
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    r = np.full(c.size, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        if log_returns:
            r[1:] = np.log(c[1:] / c[:-1])
        else:
            r[1:] = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = length - 1 if closes_window else length
    windows = sliding_window_view(r, n)
    mean = windows.mean(axis=1)
    with np.errstate(over="ignore", invalid="ignore"):
        d = windows - mean[:, None]
        m2 = (d * d).mean(axis=1)
        m4 = (d ** 4).mean(axis=1)
        spread = windows.max(axis=1) - windows.min(axis=1)
        if guard:
            m2 = np.where(spread > REAL.NOISE_FLOOR, m2, np.nan)
        else:
            m2 = np.where(m2 != 0.0, m2, np.nan)
        g2 = m4 / (m2 * m2) - 3.0
        value = g2 if biased else (((n + 1.0) * g2 + 6.0) * (n - 1.0)
                                   / ((n - 2.0) * (n - 3.0)))
        if raw:
            value = value + 3.0
    out = np.full(c.size, np.nan)
    out[n - 1:] = np.where(np.isfinite(value), value, np.nan)
    return Series(out, index=close.index)


def series_kurtosis_spelling(close, length=LENGTH):
    """The LITERAL tsfresh spelling: `pandas.Series.kurtosis` applied window by
    window. tsfresh's `feature_calculators.kurtosis(x)` is
    `pandas.Series(x).kurtosis()`, which inside pandas is
    `nanops.nankurt` -- a TWO-PASS centred-moment function, a different
    implementation from the online `rolling.kurt` this module ships. Running it
    is what makes the attribution chain a measurement instead of a claim."""
    r = close / close.shift(1) - 1.0
    return r.rolling(length, min_periods=length).apply(
        lambda w: Series(w).kurtosis(), raw=False)


def unbiased_spelling(close, length=LENGTH):
    """The same G2, spelled from the UNBIASED (ddof=1) variance -- the form
    the textbooks and `scipy.stats.kurtosis(bias=False)` state:

        G2 = n*(n+1)/((n-1)(n-2)(n-3)) * sum(d**4) / s**4
             - 3*(n-1)**2/((n-2)*(n-3))
    """
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    out = np.full(r.size, np.nan)
    n = float(length)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        if not (w.max() - w.min()) > REAL.NOISE_FLOOR:
            continue
        d = w - w.mean()
        s2 = float((d * d).sum()) / (n - 1.0)
        num = n * (n + 1.0) / ((n - 1.0) * (n - 2.0) * (n - 3.0))
        out[t] = (num * float((d ** 4).sum()) / (s2 * s2)
                  - 3.0 * (n - 1.0) ** 2 / ((n - 2.0) * (n - 3.0)))
    return Series(out, index=close.index)


def scalar_loop(close, length=LENGTH):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no rolling window, two passes written out, `math.fsum` so the
    accumulation itself is exact."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    n = float(length)
    for t in range(length, len(c)):
        w = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        if not all(math.isfinite(v) for v in w):
            continue
        if not (max(w) - min(w)) > REAL.NOISE_FLOOR:
            continue
        mean = math.fsum(w) / n
        m2 = math.fsum((v - mean) ** 2 for v in w) / n
        m4 = math.fsum((v - mean) ** 4 for v in w) / n
        g2 = m4 / (m2 * m2) - 3.0
        out[t] = ((n + 1.0) * g2 + 6.0) * (n - 1.0) / ((n - 2.0) * (n - 3.0))
    return Series(out, index=close.index)


def exact_loop(close, length=LENGTH):
    """The same statistic in EXACT rational arithmetic on the same float64
    closes: every close is a rational, so every return, moment and quotient
    is, and the only rounding left is the single conversion of the answer to
    float64. This is the oracle that says which spelling is accurate."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    n = Fraction(length)
    for t in range(length, len(c)):
        w = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        if not float(max(w) - min(w)) > REAL.NOISE_FLOOR:
            continue
        mean = sum(w) / n
        d = [v - mean for v in w]
        m2 = sum(x * x for x in d) / n
        m4 = sum(x ** 4 for x in d) / n
        g2 = m4 / (m2 * m2) - 3
        out[t] = float(((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3)))
    return Series(out, index=close.index)


def gate_a():
    head("Gate A -- correctness against the source formula")

    print("A1. the two windows with an EXACT closed form, at the shipped"
          " default length 60")
    col = ts_kurt_60(one_hot_returns())
    fired = col.dropna()
    print(f"    the one-hot frame plants a +1 return every {LENGTH} bars, so "
          f"EVERY window is one-hot: fired {len(fired)}, "
          f"min={fired.min():.15f} max={fired.max():.15f}, distinct "
          f"{int(fired.nunique())}, max|diff| from the ceiling "
          f"{float((fired - bound_max(LENGTH)).abs().max()):.3e}, above it "
          f"{int((fired > bound_max(LENGTH)).sum())}")
    print(f"    the BIASED ratio's sharp bound is (n^2-3n+3)/(n-1) = "
          f"{(LENGTH ** 2 - 3 * LENGTH + 3) / (LENGTH - 1):.6f} at n={LENGTH},"
          f" not n; the sample correction maps THAT to exactly "
          f"{bound_max(LENGTH):.6f}")
    hot = col.iloc[[b for b in range(LENGTH, 1500) if b % LENGTH == 0]].dropna()
    print(f"    one-hot window (59 returns of 0, one of +1): "
          f"n={len(hot)} min={hot.min():.15f} max={hot.max():.15f} "
          f"ceiling={bound_max(LENGTH):.15f} "
          f"max|diff|={float((hot - bound_max(LENGTH)).abs().max()):.3e} "
          f"bit-equal={int((hot == bound_max(LENGTH)).sum())}/{len(hot)}")
    zig = ts_kurt_60(zigzag_returns()).dropna()
    print(f"    alternating +-0.5 window (30 of each): "
          f"n={len(zig)} min={zig.min():.15f} max={zig.max():.15f} "
          f"floor={bound_min(LENGTH):.15f} "
          f"max|diff|={float((zig - bound_min(LENGTH)).abs().max()):.3e} "
          f"bit-equal={int((zig == bound_min(LENGTH)).sum())}/{len(zig)}")
    print("    the same two bounds at length 4, the smallest window the"
          " estimator is defined on")
    small_hot = ts_kurt_60(Series([1.0, 1.0, 1.0, 1.0, 2.0]), length=4)
    small_zig = ts_kurt_60(from_returns([0.0, 0.5, -0.5, 0.5, -0.5]), length=4)
    print(f"      closes [1,1,1,1,2] -> returns [0,0,0,+1]: "
          f"module={float(small_hot.iloc[-1]):.15f} "
          f"ceiling={bound_max(4):.15f}")
    print(f"      returns [+1/2,-1/2,+1/2,-1/2]:            "
          f"module={float(small_zig.iloc[-1]):.15f} "
          f"floor={bound_min(4):.15f}")
    print("    the bounds per length, against 2,000 student-t(1.5) windows"
          " each")
    rng = np.random.default_rng(17)
    for n in (4, 10, 20, 60, 120, 250):
        draws = rng.standard_t(1.5, size=(2000, n))
        d = draws - draws.mean(axis=1, keepdims=True)
        m2 = (d * d).mean(axis=1)
        m4 = (d ** 4).mean(axis=1)
        g2 = m4 / (m2 * m2) - 3.0
        g = ((n + 1.0) * g2 + 6.0) * (n - 1.0) / ((n - 2.0) * (n - 3.0))
        inside = bool((g >= bound_min(n) - 1e-9).all()
                      and (g <= bound_max(n) + 1e-9).all())
        print(f"      length={n:4d}: floor={bound_min(n):10.6f} "
              f"ceiling={bound_max(n):10.6f} draws span "
              f"[{g.min():.6f}, {g.max():.6f}] -- inside: {inside}")

    print("A2. the screen prototype, `ret(c).rolling(60).kurt()`")
    c = walk()
    fn = screen_candidate()
    if fn is None:
        print("  imported prototype: docs/issues/ absent in this tree")
    else:
        for label, frame in (("walk", c), ("tick-rounded walk",
                                           tick_rounded()),
                             ("student-t path", heavy_tailed())):
            proto = fn(frame, frame, frame, frame,
                       Series(np.ones(len(frame))))
            compare(f"imported prototype, {label}", ts_kurt_60(frame),
                    Series(proto))
    compare("retyped prototype", ts_kurt_60(c), prototype(c))
    compare("retyped prototype, tick-rounded walk",
            ts_kurt_60(tick_rounded()), prototype(tick_rounded()))
    compare("retyped prototype, student-t path",
            ts_kurt_60(heavy_tailed()), prototype(heavy_tailed()))
    print("    where the two part company: the prototype has no NaN"
          " discipline of its own")
    for name, frame in (("flat 300 closes", Series(np.full(300, 100.0))),
                        ("a 70-bar flat run planted in a walk",
                         flat_run_planted()),
                        ("1%-a-bar geometric ladder", geometric_ladder())):
        mine, theirs = ts_kurt_60(frame), prototype(frame)
        extra = int((mine.isna() & theirs.notna()).sum())
        vals = theirs[mine.isna() & theirs.notna()]
        span = (f"[{vals.min():.6f}, {vals.max():.6f}]" if len(vals) else "-")
        print(f"      {name}: port fires {int(mine.notna().sum())}"
              f"/{len(frame)}, prototype {int(theirs.notna().sum())}"
              f"/{len(frame)}; bars the port empties and the prototype does "
              f"not: {extra}, reading {span}")

    print("A3. the definition spelled four other ways -- starting with the"
          " one the SOURCE names, `pandas.Series.kurtosis` (nanops.nankurt),"
          " applied window by window")
    for label, frame in (("walk", c), ("tick-rounded walk", tick_rounded()),
                         ("student-t path", heavy_tailed())):
        compare(f"Series.kurtosis window by window, {label}",
                ts_kurt_60(frame), series_kurtosis_spelling(frame))
    compare("numpy two-pass centred moments", ts_kurt_60(c), numpy_two_pass(c))
    compare("unbiased-variance (ddof=1) spelling", ts_kurt_60(c),
            unbiased_spelling(c))
    short = walk(400, seed=21)
    compare("plain-Python scalar loop, math.fsum (400 bars)",
            ts_kurt_60(short), scalar_loop(short))
    compare("numpy two-pass, tick-rounded walk", ts_kurt_60(tick_rounded()),
            numpy_two_pass(tick_rounded()))
    compare("numpy two-pass, student-t path", ts_kurt_60(heavy_tailed()),
            numpy_two_pass(heavy_tailed()))

    print("A4. who is accurate -- an EXACT rational oracle on the same"
          " float64 closes")
    for label, frame in (("walk", walk(260, seed=31)),
                         ("tick-rounded walk", tick_rounded(260, seed=37)),
                         ("student-t path", heavy_tailed(260, seed=41))):
        exact = exact_loop(frame)
        print(f"    {label}")
        for name, series in (("this module (pandas rolling.kurt)",
                              ts_kurt_60(frame)),
                             ("Series.kurtosis (nanops.nankurt)",
                              series_kurtosis_spelling(frame)),
                             ("numpy two-pass centred moments",
                              numpy_two_pass(frame)),
                             ("plain-Python scalar loop (fsum)",
                              scalar_loop(frame)),
                             ("unbiased-variance spelling",
                              unbiased_spelling(frame))):
            m = exact.notna() & series.notna()
            diff = (series[m] - exact[m]).abs()
            rel = diff / exact[m].abs().clip(lower=1e-30)
            print(f"      {name}: n={int(m.sum())} "
                  f"max|diff|={float(diff.max()):.3e} "
                  f"max rel={float(rel.max()):.3e} "
                  f"bit-equal={int((series[m] == exact[m]).sum())}"
                  f"/{int(m.sum())}")

    print("A5. the readings the wording leaves open, each priced")
    compare("log returns", ts_kurt_60(c), numpy_two_pass(c, log_returns=True))
    lr = numpy_two_pass(c, log_returns=True)
    both = ts_kurt_60(c).notna() & lr.notna()
    worst = (ts_kurt_60(c)[both] - lr[both]).abs().nlargest(10)
    print(f"      the 10 bars of largest log/simple disagreement sit at port "
          f"values "
          f"{[round(float(ts_kurt_60(c).loc[i]), 4) for i in worst.index]}")
    compare("biased g2 (no sample correction)", ts_kurt_60(c),
            numpy_two_pass(c, biased=True))
    g2v = numpy_two_pass(c, biased=True)
    m = ts_kurt_60(c).notna() & g2v.notna()
    rebuilt = (((LENGTH + 1.0) * g2v[m] + 6.0) * (LENGTH - 1.0)
               / ((LENGTH - 2.0) * (LENGTH - 3.0)))
    print(f"      ((n+1)*g2 + 6)*(n-1)/((n-2)*(n-3)) rebuilds the column: "
          f"max|diff|={float((rebuilt - ts_kurt_60(c)[m]).abs().max()):.3e}")
    compare("raw (Pearson) kurtosis, no -3", ts_kurt_60(c),
            numpy_two_pass(c, raw=True))
    compare("60 CLOSES (59 returns) instead of 60 returns", ts_kurt_60(c),
            numpy_two_pass(c, closes_window=True))
    compare("the fork's own `kurtosis` of the CLOSE at length 60",
            ts_kurt_60(c), pandas_ta.kurtosis(c, length=60))
    compare("the fork's own `kurtosis` of the CLOSE at its default 30",
            ts_kurt_60(c), pandas_ta.kurtosis(c, length=30))
    print("      the degenerate window: NaN here, and THREE different values"
          " in the three spellings of the source")
    flat = Series(np.full(300, 100.0))
    for name, series in (("this port", ts_kurt_60(flat)),
                         ("pandas rolling.kurt (the prototype)",
                          prototype(flat)),
                         ("pandas Series.kurtosis, the LITERAL tsfresh"
                          " spelling", series_kurtosis_spelling(flat)),
                         ("numpy two-pass, floor removed",
                          numpy_two_pass(flat, guard=False))):
        fired = series.dropna()
        span = (f"[{fired.min():.6f}, {fired.max():.6f}]" if len(fired)
                else "-")
        print(f"        flat 300 closes, {name}: fires {len(fired)}/300, "
              f"reading {span}")


# ----------------------------------------------------------------- Gate B

BACK_DATE_TWO = (
    "    tskurt = kurt.where(spread > NOISE_FLOOR)",
    "    tskurt = kurt.where(spread > NOISE_FLOOR).shift(-2)")
BACK_DATE_FULL = (
    "    tskurt = kurt.where(spread > NOISE_FLOOR)",
    "    tskurt = kurt.where(spread > NOISE_FLOOR).shift(-(length - 1))")
FORWARD_RETURN = (
    "        r = px / px.shift(1) - 1.0",
    "        r = px.shift(-1) / px - 1.0")
ROLLED_WINDOW = (
    "    kurt = rolling.kurt()",
    "    kurt = r.shift(-(length // 2)).rolling(length, "
    "min_periods=length).kurt()")
CENTERED_WINDOW = (
    "    rolling = r.rolling(length, min_periods=length)",
    "    rolling = r.rolling(length, min_periods=length, center=True)")
FORWARD_SPREAD_ONE = (
    "    spread = rolling.max() - rolling.min()",
    "    spread = (rolling.max() - rolling.min()).shift(-1)")
#: Not a causality mutant: the module WITHOUT its fourth-power guard, used to
#: price that guard in `guards()`.
#: The module WITHOUT its fourth-power guard at all -- both the `r ** 4`
#: array and the mask it feeds -- so `cost()` can price the whole line.
NO_FOURTH_GUARD = (
    """    with np.errstate(over="ignore"):
        fourth = np.square(np.square(r.to_numpy()))
    r = r.where(fourth < np.finfo(float).max / (2 * length))""",
    "    pass  # fourth-power guard removed")
#: The guard spelled with `** 4` instead of two squarings, to price that.
POW_FOURTH = (
    "        fourth = np.square(np.square(r.to_numpy()))",
    "        fourth = r.to_numpy() ** 4")
#: The guard WITHOUT its sum bound -- `isfinite(fourth)` only, which is what a
#: reader would write first and what the two-spike frame below falsifies.
TERM_ONLY_GUARD = (
    "    r = r.where(fourth < np.finfo(float).max / (2 * length))",
    "    r = r.where(np.isfinite(fourth))")

MUTANTS = [BACK_DATE_TWO, BACK_DATE_FULL, FORWARD_RETURN, ROLLED_WINDOW,
           CENTERED_WINDOW]
MUTANT_IDS = ["back_date_two", "back_date_full", "forward_return",
              "rolled_window", "centered_window"]
OFFSETS = range(80, 1500, 40)  # past the 60-bar warm-up
FRAMES = {
    "walk": (walk(), walk(seed=97)),
    "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
    "heavy-tailed": (heavy_tailed(), heavy_tailed(seed=8)),
}


def load_mutant(old, new):
    src = open(REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_kurt_60_mutant")
    mod.__file__ = REAL.__file__
    exec(compile(src.replace(old, new), REAL.__file__, "exec"), mod.__dict__)
    return mod


def caught(fn, close, other, offsets=OFFSETS):
    """Replace every bar from J onward with a different path; return the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = []
    for j in offsets:
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


def gate_b():
    head("Gate B -- causality by mutant")
    total = len(list(OFFSETS))
    print(f"{total} future-perturbation offsets per cell, "
          f"{min(OFFSETS)}..{max(OFFSETS)} step 40")
    for frame, (close, other) in FRAMES.items():
        print(f"  real module on {frame}: leaks "
              f"{len(caught(ts_kurt_60, close, other))}/{total}")
    for index, (old, new) in enumerate(MUTANTS):
        mod = load_mutant(old, new)
        for frame, (close, other) in FRAMES.items():
            moved = not mod.ts_kurt_60(close).equals(ts_kurt_60(close))
            hits = caught(mod.ts_kurt_60, close, other)
            miss = [j for j in OFFSETS if j not in hits]
            print(f"  mutant {MUTANT_IDS[index]} on {frame}: "
                  f"changes-the-column={moved} caught {len(hits)}/{total}"
                  + (f" missed J={miss}" if miss else ""))

    print("  the SIXTH mutant -- the degeneracy guard read one bar into the"
          " future. It is invisible unless the frame has a degenerate window")
    mod = load_mutant(*FORWARD_SPREAD_ONE)
    for frame, (close, other) in FRAMES.items():
        moved = not mod.ts_kurt_60(close).equals(ts_kurt_60(close))
        print(f"    forward_spread_one on {frame}: changes-the-column={moved} "
              f"caught {len(caught(mod.ts_kurt_60, close, other))}/{total}; "
              f"windows the guard empties on this frame "
              f"{int(ts_kurt_60(close).isna().sum()) - LENGTH}")
    planted, other = flat_run_planted(), flat_run_planted(seed=23)
    offsets = range(80, 400, 20)
    moved = not mod.ts_kurt_60(planted).equals(ts_kurt_60(planted))
    print(f"    forward_spread_one on a 70-bar flat run planted in a walk "
          f"(400 bars, {len(list(offsets))} offsets): "
          f"changes-the-column={moved} caught "
          f"{len(caught(mod.ts_kurt_60, planted, other, offsets))}"
          f"/{len(list(offsets))}; real module leaks "
          f"{len(caught(ts_kurt_60, planted, other, offsets))}"
          f"/{len(list(offsets))}; windows the guard empties "
          f"{int(ts_kurt_60(planted).isna().sum()) - LENGTH}")

    print("  non-default lengths, on the walk")
    close, other = FRAMES["walk"]
    for index, (old, new) in enumerate(MUTANTS):
        mod = load_mutant(old, new)
        for length in (20, 120, 4):
            def real(x, length=length):
                return ts_kurt_60(x, length=length)

            def mutated(x, length=length, mod=mod):
                return mod.ts_kurt_60(x, length=length)

            hits = caught(mutated, close, other)
            miss = [j for j in OFFSETS if j not in hits]
            same = real(close).equals(mutated(close))
            print(f"    {MUTANT_IDS[index]} at length={length}: real leaks "
                  f"{len(caught(real, close, other))}/{total}, mutant caught "
                  f"{len(hits)}/{total}"
                  + (f" missed J={miss}" if miss else "")
                  + f"; mutant-equals-real={same}")

    print(f"  offset=2 equals shift(2): "
          f"{bool(ts_kurt_60(close, offset=2).equals(ts_kurt_60(close).shift(2)))}")
    print(f"  offset=-2 equals shift(-2): "
          f"{bool(ts_kurt_60(close, offset=-2).equals(ts_kurt_60(close).shift(-2)))}")


# --------------------------------------------------------------- the floor


def the_floor():
    head("The noise floor -- why pandas' own degenerate test is not enough")
    print(f"  NOISE_ULPS={REAL.NOISE_ULPS} NOISE_FLOOR={REAL.NOISE_FLOOR!r}")
    live = ts_kurt_60(walk()).dropna()
    lo, hi = float(live.min()), float(live.max())
    for name, frame in (("1%-a-bar geometric ladder", geometric_ladder()),
                        ("exact x1.5 ladder",
                         Series(100.0 * 1.5 ** np.arange(300))),
                        ("flat 300 bars", Series(np.full(300, 100.0)))):
        guarded = ts_kurt_60(frame)
        unguarded = prototype(frame).dropna()
        inside = int(((unguarded >= lo) & (unguarded <= hi)).sum())
        span = (f"[{unguarded.min():.4f}, {unguarded.max():.4f}]"
                if len(unguarded) else "-")
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}"
              f"/{len(frame)}, the prototype fires {len(unguarded)}"
              f"/{len(frame)} reading {span}, of which {inside} fall inside a "
              f"real walk's live range [{lo:.4f}, {hi:.4f}]")
    for name, frame in (("walk", walk(300, seed=12)),
                        ("tick-rounded", tick_rounded(300, seed=13))):
        guarded = ts_kurt_60(frame)
        unguarded = prototype(frame)
        print(f"  {name}: guarded fires {int(guarded.notna().sum())}"
              f"/{len(frame)}, masks agree "
              f"{bool((guarded.isna() == unguarded.isna()).all())}")

    print("  where the floor stops reading variation: a flat path with"
          " jitter of the stated size")
    for scale in (1e-16, 1e-14, 1e-12, 1e-11, 1e-9):
        rng = np.random.default_rng(8)
        frame = Series(100.0 * (1.0 + rng.uniform(-scale, scale, 1500)))
        print(f"    jitter +-{scale:.0e}: guarded fires "
              f"{int(ts_kurt_60(frame).notna().sum())}/1500, the prototype "
              f"{int(prototype(frame).notna().sum())}/1500")

    print("  pandas' own degenerate test is ABSOLUTE in the SIZE of the"
          " returns, so it empties a genuinely fine low-volatility path. The"
          " boundary below is measured: `rolling.kurt` ships here as a"
          " compiled extension, and the 1e-14 that the readable two-pass"
          " sibling `nanops` uses on (n-2)(n-3)*sum(d**2) is NOT quotable for"
          " it")
    for sigma in (1e-2, 1e-4, 1e-6, 1e-7, 1e-8):
        frame = walk(300, seed=14, sigma=sigma)
        mine, theirs = ts_kurt_60(frame), prototype(frame)
        scaled = ts_kurt_60(from_returns(
            np.nan_to_num((frame / frame.shift(1) - 1).to_numpy()) * 100.0))
        m = mine.notna() & theirs.notna()
        agree = (float((mine[m] - theirs[m]).abs().max()) if int(m.sum())
                 else float("nan"))
        grown = 1.0 + np.nan_to_num(
            (frame / frame.shift(1) - 1).to_numpy()) * 100.0
        print(f"    return sigma {sigma:.0e}: this port fires "
              f"{int(mine.notna().sum())}/300, pandas rolling.kurt "
              f"{int(theirs.notna().sum())}/300, max|diff| where both fire "
              f"{agree:.3e}; the SAME path with its returns x100 fires "
              f"{int(scaled.notna().sum())}/300 (smallest 1 + 100r on that "
              f"path {float(grown.min()):.4f}, so its rebuilt closes stay "
              f"positive: {bool(grown.min() > 0)})")

    print("  a monotone one-tick-per-bar path, where the returns are"
          " distinct but at rounding level")
    for price, tick in ((50.0, 0.01), (1e6, 0.001), (1e6, 0.01)):
        frame = Series(price + tick * np.arange(300))
        r = (frame / frame.shift(1) - 1).to_numpy()
        span = float(np.nanmax(r[-LENGTH:]) - np.nanmin(r[-LENGTH:]))
        print(f"    price={price:g} tick={tick:g}: |r| ~ "
              f"{abs(float(r[-1])):.3e}, max-min of the last {LENGTH} returns "
              f"= {span:.3e} vs floor {REAL.NOISE_FLOOR:.3e} -> fires "
              f"{int(ts_kurt_60(frame).notna().sum())}/300, the prototype "
              f"{int(prototype(frame).notna().sum())}/300")


# ------------------------------------------------------------- Gates C / D


def gates_cd():
    head("Gates C/D -- reachability and scale-freeness")
    frames = {"walk": walk(), "tick-rounded": tick_rounded(),
              "heavy-tailed": heavy_tailed()}
    for name, close in frames.items():
        col = ts_kurt_60(close)
        fired = col.dropna()
        print(f"  {name}: fires {len(fired)}/{len(close)} "
              f"(0 < fires < n is {0 < len(fired) < len(close)}), distinct "
              f"{int(fired.nunique())}, non-zero among fired "
              f"{int((fired != 0).sum())}, range [{fired.min():.4f}, "
              f"{fired.max():.4f}]")
        for k in (8.0, 64.0):
            scaled = ts_kurt_60(close * k)
            m = col.notna() & scaled.notna()
            print(f"    x{k:g}: masks agree "
                  f"{bool((col.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((col[m] == scaled[m]).sum())}/{int(m.sum())}")
        for k in (10.0, 3.7):
            scaled = ts_kurt_60(close * k)
            m = col.notna() & scaled.notna()
            print(f"    x{k:g}: masks agree "
                  f"{bool((col.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((col[m] == scaled[m]).sum())}/{int(m.sum())}, "
                  f"max|diff| {float((col[m] - scaled[m]).abs().max()):.3e}, "
                  f"spearman "
                  f"{float(col[m].corr(scaled[m], method='spearman')):.6f}")
    print("  non-default lengths, on the walk")
    close = walk()
    for length in (20, 120, 4, 250):
        col = ts_kurt_60(close, length=length)
        for k in (8.0, 64.0):
            scaled = ts_kurt_60(close * k, length=length)
            m = col.notna() & scaled.notna()
            print(f"    length={length} x{k:g}: fires "
                  f"{int(col.notna().sum())}, masks agree "
                  f"{bool((col.isna() == scaled.isna()).all())}, bit-equal "
                  f"{int((col[m] == scaled[m]).sum())}/{int(m.sum())}")
    print("  why the return is spelled as a price RATIO")
    r_ratio = (close / close.shift(1) - 1).to_numpy()
    r_ratio8 = (close * 8 / (close * 8).shift(1) - 1).to_numpy()
    r_log = np.diff(np.log(close.to_numpy()), prepend=np.nan)
    r_log8 = np.diff(np.log((close * 8).to_numpy()), prepend=np.nan)
    print(f"    ratio returns at x8: bit-equal "
          f"{int((r_ratio[1:] == r_ratio8[1:]).sum())}/{len(r_ratio) - 1}")
    print(f"    difference-of-logarithms returns at x8: bit-equal "
          f"{int((r_log[1:] == r_log8[1:]).sum())}/{len(r_log) - 1}")

    print("  invariance to the AMPLITUDE of the returns: the column"
          " standardises, so this is NOT a volatility feature")
    r = np.nan_to_num((close / close.shift(1) - 1).to_numpy())
    base = ts_kurt_60(from_returns(r))
    for k in (0.5, 2.0, 3.0):
        compare(f"returns scaled x{k:g}", base, ts_kurt_60(from_returns(r * k)))
    compare("+0.004 log drift a bar", ts_kurt_60(close),
            ts_kurt_60(close * np.exp(0.004 * np.arange(len(close)))))


# ----------------------------------------------------- what the column is


def meaning():
    head("What the column reads")
    close = walk()
    col = ts_kurt_60(close)
    r = (close / close.shift(1) - 1).to_numpy()
    windows = sliding_window_view(r, LENGTH)
    mean = windows.mean(axis=1)
    sd = windows.std(axis=1, ddof=1)
    srt = np.sort(np.abs(windows - mean[:, None]), axis=1)
    pad = np.full(LENGTH - 1, np.nan)
    top1 = Series(np.concatenate([pad, srt[:, -1] / sd]), index=close.index)
    top2 = Series(np.concatenate([pad, srt[:, -2] / sd]), index=close.index)
    sdev = Series(np.concatenate([pad, sd]), index=close.index)
    m = col.notna() & top1.notna()
    print(f"  spearman vs max|r - mean| / sd of the same window: "
          f"{float(col[m].corr(top1[m], method='spearman')):.4f}")
    print(f"  spearman vs the SECOND largest: "
          f"{float(col[m].corr(top2[m], method='spearman')):.4f}")
    print(f"  spearman vs the window's own sd (the volatility it is NOT): "
          f"{float(col[m].corr(sdev[m], method='spearman')):.4f}")
    print(f"  lag-1 autocorrelation of the column itself: "
          f"{float(col.dropna().autocorr(1)):.4f}; lag {LENGTH}: "
          f"{float(col.dropna().autocorr(LENGTH)):.4f} (consecutive windows "
          f"share {LENGTH - 1} of {LENGTH} returns)")
    print(f"  bounds at length {LENGTH}: floor {bound_min(LENGTH):.6f} "
          f"ceiling {bound_max(LENGTH):.6f}; the walk spans "
          f"[{col.min():.4f}, {col.max():.4f}] = "
          f"{100 * float(col.max()) / bound_max(LENGTH):.1f}% of the ceiling")

    print("  one planted outlier is most of the signal")
    base_col = ts_kurt_60(from_returns(np.nan_to_num(r)))
    for mult in (10.0, 50.0):
        planted_r = np.nan_to_num(r).copy()
        planted_r[700] = mult * float(np.nanstd(r))
        pcol = ts_kurt_60(from_returns(planted_r))
        diff = (pcol - base_col).abs()
        moved = [i for i in range(len(pcol)) if diff.iloc[i] > 1e-9]
        bits = int((diff > 0).sum())
        window = pcol.iloc[700:700 + LENGTH]
        print(f"    a single +{mult:g}-sigma return at bar 700: the {LENGTH} "
              f"windows holding it read median {float(window.median()):.4f} "
              f"and max {float(window.max()):.4f} against the frame's median "
              f"{float(base_col.median()):.4f}; bars moved by more than 1e-9: "
              f"{len(moved)} [{min(moved)}, {max(moved)}] (bars differing at "
              f"all, including last-bit path rounding: {bits})")

    print("  what it orders, as medians over 1,500-bar paths whose returns"
          " differ in SHAPE")
    for name, frame in (("uniform", uniform_returns()),
                        ("gaussian", walk()),
                        ("tick-rounded gaussian", tick_rounded()),
                        ("laplace", laplace_returns()),
                        ("student-t(2)", heavy_tailed()),
                        ("two-point (+-sigma)", two_point())):
        fired = ts_kurt_60(frame).dropna()
        rr = (frame / frame.shift(1) - 1).dropna()
        print(f"    {name}: n={len(fired)} distinct={int(fired.nunique())} "
              f"min={fired.min():.4f} p10={fired.quantile(0.1):.4f} "
              f"median={fired.median():.4f} p90={fired.quantile(0.9):.4f} "
              f"max={fired.max():.4f} (return sd {float(rr.std()):.4f})")

    print("  2,000 independent iid gaussian 60-return windows (what 'normal'"
          " looks like)")
    rng = np.random.default_rng(23)
    draws = rng.normal(0.0, 0.015, size=(2000, LENGTH))
    d = draws - draws.mean(axis=1, keepdims=True)
    m2 = (d * d).mean(axis=1)
    m4 = (d ** 4).mean(axis=1)
    g2 = m4 / (m2 * m2) - 3.0
    g = (((LENGTH + 1.0) * g2 + 6.0) * (LENGTH - 1.0)
         / ((LENGTH - 2.0) * (LENGTH - 3.0)))
    print(f"    median {np.median(g):.4f} mean {g.mean():.4f} sd {g.std():.4f}"
          f" p10 {np.quantile(g, 0.1):.4f} p90 {np.quantile(g, 0.9):.4f} "
          f"share above 1.0: {float((g > 1.0).mean()):.3f}")


def nearest_columns():
    head("Nearest shipped columns on ONE synthetic walk -- NOT Gate E")
    close = walk()
    high, low = close * 1.01, close * 0.99
    col = ts_kurt_60(close)
    others = {
        "kurtosis_30 (of CLOSE)": pandas_ta.kurtosis(close, length=30),
        "kurtosis_60 (of CLOSE)": pandas_ta.kurtosis(close, length=60),
        "skew_30": pandas_ta.skew(close, length=30),
        "osap_retskew_21": pandas_ta.osap_retskew_21(close),
        "ts_c3_20": pandas_ta.ts_c3_20(close),
        "ts_binent_20": pandas_ta.ts_binent_20(close),
        "ts_peaks_20": pandas_ta.ts_peaks_20(close),
        "ts_perment_20": pandas_ta.ts_perment_20(close),
        "entlz_20": pandas_ta.entlz(close),
        "lean_hurst_100": pandas_ta.lean_hurst_100(close),
        "lean_tdd_20": pandas_ta.lean_tdd_20(close),
        "lot_zeroret_60": pandas_ta.lot_zeroret_60(close),
        "natr_14": pandas_ta.natr(high, low, close),
        "rsi_14": pandas_ta.rsi(close),
        "zscore_30": pandas_ta.zscore(close),
    }
    rows = []
    for name, series in others.items():
        if series is None:
            continue
        if hasattr(series, "columns"):
            series = series.iloc[:, 0]
        series = Series(np.asarray(series, dtype=float), index=close.index)
        m = col.notna() & series.notna()
        if int(m.sum()) < 30 or int(series[m].nunique()) < 2:
            continue
        rows.append((abs(float(col[m].corr(series[m], method="spearman"))),
                     name, int(m.sum())))
    for a, name, n in sorted(rows, reverse=True):
        print(f"  |rho| {a:.4f} vs {name} (n={n})")


def guards():
    head("Guards and edges")
    close = walk(400, seed=19)
    print(f"  {LENGTH} closes -> {ts_kurt_60(close.iloc[:LENGTH])}")
    short = ts_kurt_60(close.iloc[:LENGTH + 1])
    print(f"  {LENGTH + 1} closes: fires {int(short.notna().sum())}, first at "
          f"{int(np.argmax(short.notna().to_numpy()))}")
    for value in (None, 0, -5, 3, 0.5, 3.9, 4, 60.9):
        print(f"  length={value} -> {ts_kurt_60(close, length=value).name}")
    print(f"  length=120.9 equals length=120: "
          f"{bool(ts_kurt_60(close, length=120.9).equals(ts_kurt_60(close, length=120)))}")
    print(f"  fillna=-99.0 fills "
          f"{int((ts_kurt_60(close, fillna=-99.0) == -99.0).sum())} bars")
    print("  a bad close, and how many bars it empties")
    base = ts_kurt_60(close)
    for label, value in (("nan", np.nan), ("0.0", 0.0), ("-5.0", -5.0),
                         ("inf", np.inf), ("1e-310", 1e-310)):
        p = close.copy()
        p.iloc[200] = value
        b = ts_kurt_60(p)
        emptied = [i for i in range(len(p))
                   if b.isna().iloc[i] and not base.isna().iloc[i]]
        before = int((base.iloc[:200].dropna()
                      != b.iloc[:200].dropna()).sum())
        print(f"    close[200]={label}: empties {len(emptied)} bars "
              f"[{min(emptied)}, {max(emptied)}], bars before 200 that move "
              f"{before}, non-finite values emitted "
              f"{int(np.isinf(b).sum())}")
    for label, (a, b_) in (("1e-300 then 1e50 (the ratio overflows)",
                            (1e-300, 1e50)),
                           ("1e-200 then 1e-100 (a return of 1e+100, whose "
                            "fourth power overflows)", (1e-200, 1e-100))):
        p = close.copy()
        p.iloc[200] = a
        p.iloc[201] = b_
        guarded = ts_kurt_60(p)
        unguarded = prototype(p)
        emptied = [i for i in range(len(p))
                   if guarded.isna().iloc[i] and not base.isna().iloc[i]]
        bad = unguarded[guarded.isna() & unguarded.notna()]
        print(f"    close[200], close[201] = {label}: empties "
              f"{len(emptied)} bars [{min(emptied)}, {max(emptied)}], "
              f"non-finite values emitted {int(np.isinf(guarded).sum())}; the "
              f"prototype reports on {int(bad.notna().sum())} of them, "
              f"values {sorted(set(np.round(bad.to_numpy(), 4)))[:4]}")
    print("  the fourth-power guard, and what pandas does without it: an"
          " infinite sum of fourth powers never leaves the ONLINE accumulator,"
          " so the contamination is NOT window-local")
    unguarded = load_mutant(*NO_FOURTH_GUARD)
    for exponent in (70, 73, 76, 77, 78, 80, 100):
        p = close.copy()
        p.iloc[200] = 1e-200
        p.iloc[201] = 1e-200 * 10.0 ** exponent
        r = p / p.shift(1) - 1.0
        raw = r.rolling(LENGTH, min_periods=LENGTH).kurt()
        big = float(r.abs().max())
        with np.errstate(over="ignore"):
            fourth = float(np.float64(big) ** 4)  # a Python float ** 4 raises
        guarded = ts_kurt_60(p)
        loose = unguarded.ts_kurt_60(p)
        g_empty = [i for i in range(len(p)) if guarded.isna().iloc[i]
                   and not base.isna().iloc[i]]
        l_empty = [i for i in range(len(p)) if loose.isna().iloc[i]
                   and not base.isna().iloc[i]]
        # The same `rolling.kurt` the module calls, but on the returns AFTER
        # the fourth-power guard: how many +-inf the output mask still meets.
        with np.errstate(over="ignore"):
            keep = np.isfinite(np.nan_to_num(r.to_numpy()) ** 4)
        kept = r.where(keep).rolling(LENGTH, min_periods=LENGTH).kurt()
        print(f"    close[201] = 1e-200 * 1e{exponent}, biggest return "
              f"{big:.2e} (its fourth power {fourth:.2e}): pandas "
              f"rolling.kurt alone is +-inf on {int(np.isinf(raw).sum())} "
              f"bars and NaN on {int(raw.isna().sum())}; WITHOUT the guard the "
              f"module empties {len(l_empty)} bars "
              f"[{min(l_empty)}, {max(l_empty)}], WITH it {len(g_empty)} bars "
              f"[{min(g_empty)}, {max(g_empty)}] (so it fires "
              f"{int(guarded.notna().sum())}/{len(p)} against the clean "
              f"frame's {int(base.notna().sum())}); +-inf left for the output "
              f"mask after a TERM-ONLY guard: {int(np.isinf(kept).sum())}; "
              f"non-finite values the column itself emits: "
              f"{int(np.isinf(guarded).sum())} guarded, "
              f"{int(np.isinf(loose).sum())} unguarded")

    print("  the case a TERM-ONLY `isfinite(fourth)` guard misses: TWO"
          " returns whose fourth powers are each finite and sum past the float"
          " maximum, inside one window")
    term_only = load_mutant(*TERM_ONLY_GUARD)
    two = close.copy()
    for at in (200, 230):
        two.iloc[at] = 1e-200
        two.iloc[at + 1] = 1e-123
    r2 = two / two.shift(1) - 1.0
    with np.errstate(over="ignore"):
        powers = np.sort(r2.abs().to_numpy()) ** 4
    print(f"    the six largest fourth powers on that frame: "
          f"{', '.join(f'{v:.3e}' for v in powers[-6:])}; the float maximum "
          f"is {np.finfo(float).max:.3e}, the shipped per-term ceiling "
          f"max/(2*length) is {np.finfo(float).max / (2 * LENGTH):.3e} (so a "
          f"return of {(np.finfo(float).max / (2 * LENGTH)) ** 0.25:.3e} or "
          f"more is rejected), and the two 1.0e+308 terms are each finite and "
          f"sum past the maximum")
    for name, out in (("the shipped guard (sum bound)", ts_kurt_60(two)),
                      ("a TERM-ONLY isfinite(fourth) guard",
                       term_only.ts_kurt_60(two)),
                      ("no guard at all", unguarded.ts_kurt_60(two))):
        empty = [i for i in range(len(two)) if out.isna().iloc[i]
                 and not base.isna().iloc[i]]
        print(f"    {name}: empties {len(empty)} bars "
              f"[{min(empty)}, {max(empty)}], emits "
              f"{int(np.isinf(out).sum())} non-finite values, fires "
              f"{int(out.notna().sum())}/{len(two)} against the clean frame's "
              f"{int(base.notna().sum())}")


def cost():
    head("Cost")
    for n in (10000, 100000, 400000):
        close = walk(n, seed=29)
        best = min(_timed(close) for _ in range(3))
        tracemalloc.start()
        out = ts_kurt_60(close)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"  n={n}: {best * 1000:.0f} ms, fires "
              f"{int(out.notna().sum())}, traced peak {peak / 1e6:.1f} MB")
    close = walk(400000, seed=29)
    for length in (20, 60, 250):
        best = min(_timed(close, length) for _ in range(3))
        tracemalloc.start()
        ts_kurt_60(close, length=length)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        tracemalloc.start()
        numpy_two_pass(close, length=length)
        npeak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"  n=400000 length={length}: {best * 1000:.0f} ms, traced peak "
              f"{peak / 1e6:.1f} MB; the numpy two-pass oracle peaks at "
              f"{npeak / 1e6:.1f} MB")
    print("  what the fourth-power guard costs: the same call with that whole"
          " block rewritten out in memory, timed back to back with the real"
          " one (best of 9 each, alternating, so neither gets the cold cache)."
          " Absolute times move with machine load -- read the GAPS between the"
          " three rows, not the numbers")
    without = load_mutant(*NO_FOURTH_GUARD)

    def timed(fn):
        start = time.perf_counter()
        fn(close)
        return time.perf_counter() - start

    powform = load_mutant(*POW_FOURTH)
    with_times, without_times, pow_times = [], [], []
    for _ in range(9):
        with_times.append(timed(ts_kurt_60))
        without_times.append(timed(without.ts_kurt_60))
        pow_times.append(timed(powform.ts_kurt_60))
    tracemalloc.start()
    without.ts_kurt_60(close)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    print(f"    n=400000 with the guard:    best {min(with_times) * 1000:.0f}"
          f" ms, worst {max(with_times) * 1000:.0f} ms")
    print(f"    n=400000 without the guard: best "
          f"{min(without_times) * 1000:.0f} ms, worst "
          f"{max(without_times) * 1000:.0f} ms, traced peak "
          f"{peak / 1e6:.1f} MB")
    print(f"    n=400000 with the guard spelled `r ** 4` instead of two "
          f"squarings: best {min(pow_times) * 1000:.0f} ms, worst "
          f"{max(pow_times) * 1000:.0f} ms")
    pair = walk(2000, seed=37)
    compare("the two spellings of the guard agree", ts_kurt_60(pair),
            powform.ts_kurt_60(pair))
    small = walk(2000, seed=31)
    compare("the two forms agree", ts_kurt_60(small), numpy_two_pass(small))


def _timed(close, length=None):
    start = time.perf_counter()
    ts_kurt_60(close, length=length)
    return time.perf_counter() - start


def wiring():
    head("Wiring -- the five touch points")
    close = walk(400, seed=33)
    frame = close.to_frame("close")
    frame["open"] = frame["high"] = frame["low"] = close
    frame["volume"] = 1e6
    print(f"  module-level ta.ts_kurt_60: {pandas_ta.ts_kurt_60(close).name}")
    print(f"  accessor df.ta.ts_kurt_60: {frame.ta.ts_kurt_60().name}")
    print(f"  in Category['statistics']: "
          f"{'ts_kurt_60' in pandas_ta.Category['statistics']}")
    print(f"  the accessor forwards `length`: "
          f"{frame.ta.ts_kurt_60(length=20).name}")
    print(f"  category attribute: {pandas_ta.ts_kurt_60(close).category}")


if __name__ == "__main__":
    gate_a()
    gate_b()
    the_floor()
    gates_cd()
    meaning()
    nearest_columns()
    guards()
    cost()
    wiring()
