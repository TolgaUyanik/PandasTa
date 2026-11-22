# -*- coding: utf-8 -*-
"""Measurement harness for `c22_ami_timescale` (PandasTa issue #125).

Every number in `docs/C22AmiTimescaleMeasured.md`, in
`pandas_ta/statistics/c22_ami_timescale.py`'s docstring and in
`tests/test_c22_ami_timescale.py` comes from a run of this file -- EXCEPT the
receipt's section F suite counts, which come from `python -m pytest -q`.

    python docs/measure_c22_ami_timescale.py            # every section
    python docs/measure_c22_ami_timescale.py A D        # named sections

Sections: A (Gate A, oracles and the readings the source leaves open),
B (Gate B, mutants), C (Gate C, reachability), D (Gate D, scale),
E (in-fork overlap, which Gate E's 687 comparators partly cannot see),
G (the noise floor and what it costs), H (bad data and the wiring),
P (the screened quantity as a black box -- OPT-IN, imports the GPL-3.0
reference), T (this port's test module under the current numpy dispatch),
Z (chunking and cost).

No section except **P** imports the GPL-3.0 reference implementation
(pycatch22), and `DEFAULT_SECTIONS` excludes P, so a bare run does not touch
it: section A9 reports whether the package is installed with
`importlib.util.find_spec`, which locates it without executing it. Nothing
under `pandas_ta/` imports it at all, which
`tests/test_c22_ami_timescale.py::test_the_reference_implementation_is_not_
imported_by_shipped_code` asserts over every `.py` file in the package (A9
reads three files, not the package). Gate A rests on the DEFINITIONS --
Lubba et al. 2019 and the
hctsa operation `IN_AutoMutualInfoStats_40_gaussian_fmmi` the paper names --
re-spelled four independent ways, one of which rounds zero times.

⚠ Figures that are counts of LAST BITS move with numpy's kernels. Run

    python docs/measure_c22_ami_timescale.py --no-avx A D T

to see what a CI runner without AVX-512 reads: `--no-avx` re-executes this
file with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` set
BEFORE numpy is imported. It is a flag rather than an environment prefix
because the shell this was written under cannot put a variable in front of a
command.
"""
from __future__ import annotations

#: `os` and `sys` are imported HERE, above the rest, because the re-exec below
#: has to run before numpy is imported anywhere in the process.
import os
import sys

#: What a GitHub runner without AVX-512 gives numpy's kernels.
CI_CPU = "AVX512F AVX512_SKX AVX2 FMA3"
if "--no-avx" in sys.argv:
    _argv = [a for a in sys.argv if a != "--no-avx"]
    if os.environ.get("NPY_DISABLE_CPU_FEATURES") != CI_CPU:
        os.environ["NPY_DISABLE_CPU_FEATURES"] = CI_CPU
        os.execve(sys.executable, [sys.executable] + _argv, os.environ)
    sys.argv = _argv

import importlib
import math
import time
import tracemalloc
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_ami_timescale import (  # noqa: E402
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, NO_MINIMUM, TAU_MAX,
    c22_ami_timescale)

MODULE = importlib.import_module("pandas_ta.statistics.c22_ami_timescale")
LENGTH = 100
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")

#: Every Nth window, for the oracles that are too slow to run on all 1,400 of
#: every frame. The exact rational oracle is the slowest by far (40 lags x 100
#: products of exact fractions per window), the plain-Python ones next. Every
#: count these sections print is a count of the windows they ACTUALLY ran, so
#: the stride cannot be mistaken for full coverage.
EXACT_STRIDE = 13
PY_STRIDE = 7


# --------------------------------------------------------------- frames
def walk(n=1500, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=1500, seed=55):
    """A 100-lira walk rounded to the kurus: repeated returns, few exact zeros."""
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=1500, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: the issue's own worry.

    The tick is 0.5% of the price, so the return grid is coarse and many bars
    print exactly 0.00% -- the BIST rounding shape that Gate C is told to look
    for.
    """
    return Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    """A path whose SIMPLE returns are an AR(1)."""
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=1500, period=20.0, amp=0.01):
    """Returns are an exact cosine of `period` bars: a deterministic case."""
    t = np.arange(n, dtype=float)
    r = amp * np.cos(2.0 * np.pi * t / period)
    return Series(100.0 * np.cumprod(1.0 + r))


def student_t(n=1500, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def alternating(n=1500, up=0.02, down=0.02):
    r = np.where(np.arange(n) % 2 == 0, up, -down)
    return Series(100.0 * np.cumprod(1.0 + r))


def ladder(n=1500, step=0.01, start=100.0):
    """An exactly geometric path: every return is the same number."""
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def _ulp_ladder(price, n, every=1):
    """A path that steps up by ONE double ulp every `every` bars."""
    out = np.empty(n)
    v = price
    for i in range(n):
        out[i] = v
        if (i + 1) % every == 0:
            v = np.nextafter(v, np.inf)
    return out


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}


def say(*parts):
    print(*parts, flush=True)


def head(title):
    say("")
    say("=" * 72)
    say(title)
    say("=" * 72)


def col(close, **kw):
    return c22_ami_timescale(close, **kw)


def fired(s):
    return int(s.notna().sum())


def same(a, b):
    """Bit-equal, with NaN == NaN."""
    x, y = np.asarray(a, float), np.asarray(b, float)
    if x.shape != y.shape:
        return False
    return bool(np.all((x == y) | (np.isnan(x) & np.isnan(y))))


def diff_bars(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    mask_moved = int(np.sum(np.isnan(x) != np.isnan(y)))
    return int(np.sum(x[both] != y[both])), mask_moved


def spearman(a, b):
    """Spearman rho on the bars where both are present; no scipy needed."""
    x, y = Series(np.asarray(a, float)), Series(np.asarray(b, float))
    m = x.notna() & y.notna()
    if m.sum() < 30:
        return float("nan"), int(m.sum())
    rx, ry = x[m].rank(), y[m].rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan"), int(m.sum())
    return float(np.corrcoef(rx, ry)[0, 1]), int(m.sum())


def windows(close, length=LENGTH):
    """The `length`-return windows the module reads, oldest first, with the
    bar index each one belongs to."""
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1.0
    win = sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


# ------------------------------------------------------- Gate A oracles
def _scan(values, tau_max=TAU_MAX, inclusive=False):
    """The first lag strictly (or weakly) below both of its neighbours.

    `values` is indexed by lag - 1 and is anything MONOTONE INCREASING in the
    AMI: the AMI itself, or `rho**2`.
    """
    for i in range(1, tau_max - 1):
        if inclusive:
            if values[i] <= values[i - 1] and values[i] <= values[i + 1]:
                return i + 1
        elif values[i] < values[i - 1] and values[i] < values[i + 1]:
            return i + 1
    return tau_max


def fmmi_exact(window, tau_max=TAU_MAX):
    """The definition in EXACT rational arithmetic; rounds zero times.

    The Gaussian AMI `-0.5 * ln(1 - rho**2)` is a strictly increasing function
    of `rho**2`, so the first lag strictly below both neighbours in AMI is the
    first lag strictly below both neighbours in `rho**2` -- and with
    `rho**2 = (sum da*db)**2 / (sum da**2 * sum db**2)` over exactly
    representable doubles, that is a ratio of integers, comparable with no
    rounding at all. Returns None where the module blanks the bar.
    """
    xs = [Fraction(float(v)) for v in window]
    n = len(xs)
    r2 = []
    for k in range(1, tau_max + 1):
        a, b = xs[:n - k], xs[k:]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        da = [x - ma for x in a]
        db = [x - mb for x in b]
        sa = sum(x * x for x in da)
        sb = sum(x * x for x in db)
        if sa == 0 or sb == 0:
            return None
        num = sum(x * y for x, y in zip(da, db))
        r2.append((num * num) / (sa * sb))
    return _scan(r2, tau_max)


def _ami_list(window, tau_max=TAU_MAX):
    """`math.fsum` spelling of the AMI, plain Python, `log(1 - r*r)`."""
    w = [float(v) for v in window]
    n = len(w)
    ami = []
    for k in range(1, tau_max + 1):
        a, b = w[:n - k], w[k:]
        ma, mb = math.fsum(a) / len(a), math.fsum(b) / len(b)
        da = [x - ma for x in a]
        db = [x - mb for x in b]
        sa = math.fsum(x * x for x in da)
        sb = math.fsum(x * x for x in db)
        if not (sa > 0.0 and sb > 0.0):
            return None
        num = math.fsum(x * y for x, y in zip(da, db))
        r2 = min((num / math.sqrt(sa * sb)) ** 2, 1.0)
        ami.append(math.inf if r2 >= 1.0 else -0.5 * math.log(1.0 - r2))
    return ami


def fmmi_fsum(window, tau_max=TAU_MAX):
    """The definition as an independent plain-Python spelling."""
    ami = _ami_list(window, tau_max)
    return None if ami is None else _scan(ami, tau_max)


def fmmi_library(window, tau_max=TAU_MAX, how="numpy"):
    """The lagged-pair correlation taken by a LIBRARY rather than by hand:
    `np.corrcoef` or `pandas.Series.corr`."""
    w = np.asarray(window, float)
    n = w.size
    ami = []
    for k in range(1, tau_max + 1):
        y1, y2 = w[:n - k], w[k:]
        if y1.std() == 0.0 or y2.std() == 0.0:
            return None
        if how == "numpy":
            r = float(np.corrcoef(y1, y2)[0, 1])
        else:
            r = float(Series(y1).corr(Series(y2)))
        r2 = min(r * r, 1.0)
        ami.append(math.inf if r2 >= 1.0 else -0.5 * math.log(1.0 - r2))
    return _scan(ami, tau_max)


def fmmi_biased(window, tau_max=TAU_MAX):
    """The reading this port does NOT ship: the window's own BIASED
    autocorrelation function -- one mean, one variance, divisor `n`."""
    w = np.asarray(window, float)
    n = w.size
    d = w - w.mean()
    ss = float((d * d).sum())
    if ss == 0.0:
        return None
    r2 = [min((float((d[:n - k] * d[k:]).sum()) / ss) ** 2, 1.0)
          for k in range(1, tau_max + 1)]
    return _scan(r2, tau_max)


def fmmi_adjusted(window, tau_max=TAU_MAX):
    """The other reading this port does not ship: the ADJUSTED ACF, lag-k
    products averaged over the `n - k` pairs that exist."""
    w = np.asarray(window, float)
    n = w.size
    d = w - w.mean()
    var = float((d * d).mean())
    if var == 0.0:
        return None
    r2 = [min((float((d[:n - k] * d[k:]).mean()) / var) ** 2, 1.0)
          for k in range(1, tau_max + 1)]
    return _scan(r2, tau_max)


def fmmi_inclusive(window, tau_max=TAU_MAX):
    """`<=` where the module has `<`."""
    ami = _ami_list(window, tau_max)
    return None if ami is None else _scan(ami, tau_max, inclusive=True)


def fmmi_rho2(window, tau_max=TAU_MAX):
    """The module's arithmetic, scanning `rho**2` instead of the AMI: the
    monotone-equivalence check, in floating point."""
    w = np.asarray(window, float)
    n = w.size
    r2 = []
    for k in range(1, tau_max + 1):
        a, b = w[:n - k], w[k:]
        da, db = a - a.mean(), b - b.mean()
        den = math.sqrt(float((da * da).sum()) * float((db * db).sum()))
        if den == 0.0:
            return None
        r2.append(min((float((da * db).sum()) / den) ** 2, 1.0))
    return _scan(r2, tau_max)


def rho2_pearson(window, tau_max=TAU_MAX):
    """`rho**2` per lag, the shipped estimator, as an array."""
    w = np.asarray(window, float)
    n = w.size
    out = np.empty(tau_max)
    for k in range(1, tau_max + 1):
        a, b = w[:n - k], w[k:]
        da, db = a - a.mean(), b - b.mean()
        den = math.sqrt(float((da * da).sum()) * float((db * db).sum()))
        out[k - 1] = (min((float((da * db).sum()) / den) ** 2, 1.0)
                      if den > 0.0 else float("nan"))
    return out


def _statsmodels_acf():
    try:
        from statsmodels.tsa.stattools import acf
    except Exception:
        return None
    return acf


def section_A():
    head("A. Gate A -- correctness, against the DEFINITION")

    say("")
    say("A1. The exact rational oracle (fractions.Fraction, zero roundings)")
    say(f"    module vs exact, per frame, every {EXACT_STRIDE}th window:")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        win, bars = win[::EXACT_STRIDE], bars[::EXACT_STRIDE]
        agree = disagree = 0
        bad = []
        for row, bar in zip(win, bars):
            want = fmmi_exact(row)
            got = out.iloc[bar]
            if want is None:
                continue
            if float(want) == got:
                agree += 1
            else:
                disagree += 1
                if len(bad) < 5:
                    bad.append((bar, want, got))
        say(f"    {name:<13} agree {agree:>5} / {agree + disagree:<5} "
            f"disagree {disagree}  {bad if bad else ''}")

    say("")
    say(f"A2. An independent plain-Python `math.fsum` spelling, every "
        f"{PY_STRIDE}th window")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        win, bars = win[::PY_STRIDE], bars[::PY_STRIDE]
        agree = disagree = 0
        for row, bar in zip(win, bars):
            want = fmmi_fsum(row)
            if want is None:
                continue
            agree, disagree = ((agree + 1, disagree) if float(want) == out.iloc[bar]
                               else (agree, disagree + 1))
        say(f"    {name:<13} agree {agree:>5} / {agree + disagree:<5} "
            f"disagree {disagree}")

    say("")
    say(f"A3. The lagged-pair correlation taken by a LIBRARY, every "
        f"{PY_STRIDE}th window")
    for how in ("numpy", "pandas"):
        for name, f in FRAMES.items():
            out = col(f)
            win, bars = windows(f)
            win, bars = win[::PY_STRIDE], bars[::PY_STRIDE]
            agree = disagree = 0
            worst = 0.0
            for row, bar in zip(win, bars):
                want = fmmi_library(row, how=how)
                if want is None:
                    continue
                agree, disagree = ((agree + 1, disagree)
                                   if float(want) == out.iloc[bar]
                                   else (agree, disagree + 1))
                mine = rho2_pearson(row)
                w = np.asarray(row, float)
                theirs = np.array(
                    [float(np.corrcoef(w[:w.size - k], w[k:])[0, 1]) ** 2
                     if how == "numpy" else
                     float(Series(w[:w.size - k]).corr(Series(w[k:]))) ** 2
                     for k in range(1, TAU_MAX + 1)])
                worst = max(worst, float(np.nanmax(np.abs(mine - theirs))))
            say(f"    {how:<7} {name:<13} agree {agree:>4} / "
                f"{agree + disagree:<4} max |rho**2 - library| {worst:.3e}")

    say("")
    say("A4. Deterministic frames, against hand derivation")
    alt = col(alternating())
    r2alt = rho2_pearson(windows(alternating())[0][0])
    say(f"    alternating +-2% -- the DEGENERATE case. The lag-tau limbs of an")
    say(f"    exactly alternating window are the same sequence up to a SIGN, so")
    say(f"    rho**2 is 1 at every lag in exact arithmetic: measured min over")
    say(f"    the 40 lags {r2alt.min():.17g}, max {r2alt.max():.17g}. The AMI is")
    say(f"    then the same +{-0.5 * math.log(1 - r2alt.min()):.1f}-ish at every")
    say(f"    lag and WHICH lag is reported is decided by the last bits:")
    say(f"    {alt.dropna().nunique()} distinct values, "
        f"{sorted(set(alt.dropna()))[:6]} .. "
        f"{sorted(set(alt.dropna()))[-3:]}, over {fired(alt)} fired bars.")
    moved, mask = diff_bars(alt, col(alternating() * 10.0))
    say(f"    A x10 rescale of that frame moves {moved} of {fired(alt)} bars "
        f"(+{mask} mask) -- see section D2 for what it moves on a real shape.")
    lad = col(ladder())
    say(f"    exact geometric ladder: fired {fired(lad)} -- blank by the "
        f"FLOOR and not by the constant-limb rule; section G4 is where that "
        f"is measured rather than assumed")
    for period in (8, 12, 20, 40, 80, 120):
        c = col(cosine_returns(period=period))
        vals = sorted(set(c.dropna()))
        say(f"    cosine returns period {period:>3}: values {vals}  "
            f"(quarter period = {period / 4:g})")
    for phi in (-0.8, -0.4, 0.0, 0.4, 0.8):
        c = col(ar1(phi=phi, seed=5)).dropna()
        say(f"    AR(1) returns phi {phi:+.1f}: median {c.median():.1f} "
            f"range [{c.min():.0f}, {c.max():.0f}] distinct {c.nunique()}")

    say("")
    say("A5. The attainable set, per frame")
    for name, f in FRAMES.items():
        s = col(f).dropna()
        vc = s.value_counts().sort_index()
        say(f"    {name:<13} n {len(s)} distinct {s.nunique():>3} "
            f"range [{s.min():.0f}, {s.max():.0f}] median {s.median():.1f}")
        say(f"    {'':<13} {dict((int(k), int(v)) for k, v in vc.items())}")

    say("")
    say("A6. Spellings that must NOT change the column")
    say("    (a) scanning rho**2 instead of the AMI (monotone equivalence)")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        bad = sum(1 for row, bar in zip(win, bars)
                  if fmmi_rho2(row) is not None
                  and float(fmmi_rho2(row)) != out.iloc[bar])
        say(f"        {name:<13} disagree {bad} / {len(bars)}")
    say("    (b) log1p(-r2) vs log(1 - r2): worst AMI gap")
    for name, f in FRAMES.items():
        win, _ = windows(f)
        worst = 0.0
        for row in win[::29]:
            for r2 in rho2_pearson(row):
                if not np.isfinite(r2):
                    continue
                a = -0.5 * np.log1p(-min(r2, 1.0))
                b = (-0.5 * math.log(1.0 - r2)) if r2 < 1.0 else math.inf
                if math.isfinite(a) and math.isfinite(b):
                    worst = max(worst, abs(a - b))
        say(f"        {name:<13} max |log1p - log| {worst:.3e}")

    say("")
    say("A7. The readings the source leaves open, PRICED")
    say("    (a) the window's BIASED ACF instead of the lagged-pair "
        "correlation")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        mine, theirs = [], []
        for row, bar in zip(win, bars):
            p = fmmi_biased(row)
            if p is None or np.isnan(out.iloc[bar]):
                continue
            mine.append(out.iloc[bar])
            theirs.append(float(p))
        eq = sum(1 for a, b in zip(mine, theirs) if a == b)
        rho, n = spearman(mine, theirs)
        say(f"        {name:<13} equal {eq:>5} / {len(mine):<5} "
            f"({eq / max(1, len(mine)):.1%})  spearman {rho:+.4f} (n={n})")
    acf = _statsmodels_acf()
    if acf is None:
        say("        (statsmodels not importable; the biased reading above is "
            "this file's own spelling only)")
    else:
        import statsmodels
        worst = 0.0
        for name, f in FRAMES.items():
            win, _ = windows(f)
            for row in win[::29]:
                w = np.asarray(row, float)
                d = w - w.mean()
                ss = float((d * d).sum())
                mine = np.array([float((d[:w.size - k] * d[k:]).sum()) / ss
                                 for k in range(1, TAU_MAX + 1)])
                worst = max(worst, float(np.max(np.abs(
                    mine - acf(w, nlags=TAU_MAX, adjusted=False,
                               fft=False)[1:]))))
        say(f"        statsmodels {statsmodels.__version__} confirms that "
            f"biased spelling: max |rho - acf(adjusted=False)| {worst:.3e}")
    say("    (b) the ADJUSTED estimator (divide by n - k)")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        mine, theirs = [], []
        for row, bar in zip(win, bars):
            p = fmmi_adjusted(row)
            if p is None or np.isnan(out.iloc[bar]):
                continue
            mine.append(out.iloc[bar])
            theirs.append(float(p))
        eq = sum(1 for a, b in zip(mine, theirs) if a == b)
        rho, n = spearman(mine, theirs)
        say(f"        {name:<13} equal {eq:>5} / {len(mine):<5} "
            f"({eq / max(1, len(mine)):.1%})  spearman {rho:+.4f} (n={n})")
    say(f"    (c) `<=` instead of `<`, every {PY_STRIDE}th window")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        win, bars = win[::PY_STRIDE], bars[::PY_STRIDE]
        eq = tot = 0
        ties = 0
        for row, bar in zip(win, bars):
            p = fmmi_inclusive(row)
            if p is None or np.isnan(out.iloc[bar]):
                continue
            tot += 1
            eq += float(p) == out.iloc[bar]
            ami = _ami_list(row)
            ties += sum(1 for i in range(1, TAU_MAX)
                        if ami[i] == ami[i - 1])
        say(f"        {name:<13} equal {eq:>5} / {tot:<5}  exact AMI ties "
            f"between neighbouring lags: {ties}")

    say("")
    say("A8. The |rho| = 1 corner, and whether the clip ever binds")
    say("    cells = (window, lag) pairs; `raw` is rho**2 BEFORE the clip")
    probe = dict(FRAMES)
    probe["alternating"] = alternating()
    probe["cosine-120"] = cosine_returns(period=120)
    probe["cosine-20"] = cosine_returns(period=20)
    for name, f in probe.items():
        win, _ = windows(f)
        win = win[::PY_STRIDE]
        cells = over = exact1 = near = 0
        worst = 0.0
        for row in win:
            w = np.asarray(row, float)
            for k in range(1, TAU_MAX + 1):
                a, b = w[:w.size - k], w[k:]
                da, db = a - a.mean(), b - b.mean()
                den = math.sqrt(float((da * da).sum()) * float((db * db).sum()))
                if den == 0.0:
                    continue
                raw = (float((da * db).sum()) / den) ** 2
                cells += 1
                over += raw > 1.0
                exact1 += raw == 1.0
                near += raw > 1.0 - 1e-12
                worst = max(worst, raw)
        say(f"    {name:<13} cells {cells:>6}  raw > 1 (clip binds) {over:>5}"
            f"  raw == 1 (AMI inf) {exact1:>5}  raw > 1-1e-12 {near:>6}"
            f"  max raw {worst:.17g}")

    say("")
    say("A9. The GPL-3.0 reference code")
    # `find_spec` LOCATES the package without executing a line of it, which is
    # what keeps section P the only section that runs GPL-3.0 code -- an
    # `import` here would put that on the default code path.
    try:
        spec = importlib.util.find_spec("pycatch22")
    except Exception as e:                                # pragma: no cover
        spec = None
        say(f"    pycatch22: lookup raised {type(e).__name__}")
    say(f"    pycatch22: "
        f"{f'INSTALLED ({spec.origin})' if spec else 'not importable here'} "
        f"-- located with importlib.util.find_spec, NOT imported")
    me = Path(__file__).resolve()
    for path in (Path(MODULE.__file__),
                 me.parent.parent / "tests" / "test_c22_ami_timescale.py",
                 me):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            imports = [line.strip() for line in text.splitlines()
                       if line.lstrip().startswith(("import ", "from "))
                       and "pycatch22" in line]
            note = ("imported inside section P only, as a BLACK-BOX "
                    "comparison, not as a Gate A oracle" if path == me
                    and imports else "no import at all")
            say(f"    {path.name}: import statements naming pycatch22 "
                f"{imports} -- {note}")
    say("    ⚠ these are THREE files, not a package sweep: the sweep over "
        "every .py file under pandas_ta/ is")
    say("      tests/test_c22_ami_timescale.py::"
        "test_the_reference_implementation_is_not_imported_by_shipped_code")


# ------------------------------------- the screened quantity (MEASURE ONLY)
def section_P():
    """What the 2026-10-24 screen actually measured, as a BLACK BOX.

    ⚠ Read the provenance before the numbers. This module was written from the
    DEFINITIONS -- Lubba et al. 2019 and the hctsa operation
    `IN_AutoMutualInfoStats_40_gaussian_fmmi` -- and frozen before this section
    ran; nothing in `pandas_ta/` imports pycatch22, which
    `tests/test_c22_ami_timescale.py::test_the_reference_implementation_is_
    not_imported_by_shipped_code` asserts over every file in the package.
    This section is the ONLY place in the repository that executes it.
    pycatch22 1.x is GPL-3.0, so it is used HERE exactly as the owner's own
    prototype uses it (`docs/issues/screen/ind_screen_r3.py`: "it is used here
    only to MEASURE, on the owner's machine") -- to answer one question the
    definitions cannot: is the column this port ships the column the screen's
    Gate E numbers were measured on?

    This section is OPT-IN (`python docs/measure_c22_ami_timescale.py P`) and
    skips itself when pycatch22 is not installed.
    """
    head("P. The screened quantity, as a black box (pycatch22, GPL-3.0)")
    try:
        import pycatch22
    except Exception as e:
        say(f"    pycatch22 is not importable here ({type(e).__name__}) -- "
            f"this section did not run")
        return
    say(f"    pycatch22 {getattr(pycatch22, '__version__', '(no __version__)')}"
        f" at {pycatch22.__file__}")
    names = pycatch22.catch22_all([0.0] * LENGTH, short_names=True)["short_names"]
    long_names = pycatch22.catch22_all([0.0] * LENGTH)["names"]
    idx = [i for i, n in enumerate(names) if "ami_timescale" in n.lower()]
    say(f"    short names holding 'ami_timescale': "
        f"{[(i, names[i], long_names[i]) for i in idx]}")
    if not idx:
        say("    ! no such feature in this build -- nothing to compare")
        return
    at = idx[0]
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        win, bars = win[::PY_STRIDE], bars[::PY_STRIDE]
        equal = off_by_one = other = 0
        examples = []
        for row, bar in zip(win, bars):
            mine = out.iloc[bar]
            if np.isnan(mine):
                continue
            theirs = pycatch22.catch22_all(np.asarray(row, float).tolist()
                                           )["values"][at]
            if theirs == mine:
                equal += 1
            elif theirs == mine - 1.0:
                off_by_one += 1
            else:
                other += 1
                if len(examples) < 4:
                    examples.append((int(bar), mine, theirs))
        say(f"    {name:<13} equal {equal:>4}  theirs == mine - 1: "
            f"{off_by_one:>4}  other {other:>4}  {examples if examples else ''}")
    say("")
    say("    P2. Every window where the two disagree, against the three")
    say("        readings the definitions leave open. `gap` is how far this")
    say("        module's rho**2 at THEIR lag is above its own neighbours'")
    say("        minimum -- a near-zero gap means a last-bit flip, a large one")
    say("        means a different estimator.")
    say(f"        {'frame':<13} {'bar':>5} {'mine':>5} {'theirs':>7} "
        f"{'exact':>6} {'biased':>7} {'adjust':>7} {'gap':>11}")
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        for row, bar in zip(win[::PY_STRIDE], bars[::PY_STRIDE]):
            mine = out.iloc[bar]
            if np.isnan(mine):
                continue
            theirs = pycatch22.catch22_all(np.asarray(row, float).tolist()
                                           )["values"][at]
            if theirs == mine:
                continue
            r2 = rho2_pearson(row)
            i = int(theirs) - 1
            gap = (min(r2[i - 1], r2[i + 1]) - r2[i]
                   if 1 <= i <= TAU_MAX - 2 else float("nan"))
            say(f"        {name:<13} {bar:>5} {mine:>5.0f} {theirs:>7.0f} "
                f"{fmmi_exact(row):>6} {fmmi_biased(row):>7} "
                f"{fmmi_adjusted(row):>7} {gap:>11.3e}")

    say("")
    say("    P3. The class the equal-counts above CANNOT see: windows this")
    say("        module BLANKS. The reference scans them anyway, so on frames")
    say("        with flat or suspended runs the two columns differ by")
    say("        construction and not by arithmetic. Every 3rd blank window:")
    flat = Series(np.r_[walk(400).to_numpy(), np.full(300, 50.0)])
    for name, f in (("flat-run", flat), ("penny", FRAMES["penny"]),
                    ("ladder", ladder()), ("walk", FRAMES["walk"])):
        out = col(f)
        win, bars = windows(f)
        total = scored = 0
        vals: dict[float, int] = {}
        for row, bar in zip(win[::3], bars[::3]):
            if not np.isnan(out.iloc[bar]):
                continue
            total += 1
            theirs = pycatch22.catch22_all(np.asarray(row, float).tolist()
                                           )["values"][at]
            if np.isfinite(theirs):
                scored += 1
                vals[theirs] = vals.get(theirs, 0) + 1
        say(f"        {name:<10} blank windows {total:>4}, of which the "
            f"reference scores {scored:>4} as {dict(sorted(vals.items()))}")

    say("")
    say("    the same comparison on the single-feature entry point, if the")
    say("    build exposes one:")
    fn = getattr(pycatch22, "IN_AutoMutualInfoStats_40_gaussian_fmmi", None)
    if fn is None:
        say("    (not exposed in this build)")
        return
    for name, f in FRAMES.items():
        out = col(f)
        win, bars = windows(f)
        win, bars = win[::PY_STRIDE], bars[::PY_STRIDE]
        equal = off_by_one = other = 0
        for row, bar in zip(win, bars):
            mine = out.iloc[bar]
            if np.isnan(mine):
                continue
            theirs = float(fn(np.asarray(row, float).tolist()))
            if theirs == mine:
                equal += 1
            elif theirs == mine - 1.0:
                off_by_one += 1
            else:
                other += 1
        say(f"    {name:<13} equal {equal:>4}  theirs == mine - 1: "
            f"{off_by_one:>4}  other {other:>4}")


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": ("out[length + a:length + b]",
                         "out[length - 1 + a:length - 1 + b]"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "chunk-wide-demean": ("da = a - a.mean(axis=1, keepdims=True)",
                          "da = a - np.nanmean(a)"),
    "chunk-wide-floor": ("d = block - block.mean(axis=1, keepdims=True)",
                         "d = block - np.nanmean(block)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
}


def mutant(name):
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_ami_timescale"]


def _spliced(close, j, seed=909):
    """`close` with every bar from `j` on replaced by a different path."""
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=35):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=1):
    """Offsets at which SOME splice moves a bar STRICTLY BEFORE the splice.

    `splices` different futures are tried at each offset. One is enough for a
    continuous column; this one is a small integer that ties on four bars in
    five, so a single splice leaves a real leak undetected most of the time --
    see B2b.
    """
    base = np.asarray(fn(close), float)
    hits = []
    for j in offsets:
        for s in range(splices):
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s)),
                               float)
            if not same(base[:j], other[:j]):
                hits.append(j)
                break
    return hits


def section_B():
    head("B. Gate B -- causality")
    offsets = {name: _offsets(len(f)) for name, f in FRAMES.items()}

    say("")
    say("B1. The real module, future-perturbation sweep (8 splices each)")
    for name, f in FRAMES.items():
        hits = _leaks(c22_ami_timescale, f, offsets[name], splices=8)
        say(f"    {name:<13} leaks at {len(hits)} / {len(offsets[name])} "
            f"offsets {hits[:6]}")
    for length in (MIN_LENGTH, 120, 250):
        f = FRAMES["walk"]
        hits = _leaks(lambda s: c22_ami_timescale(s, length=length), f,
                      _offsets(len(f), length), splices=8)
        say(f"    walk at length {length:<4} leaks at {len(hits)} / 35 offsets")

    say("")
    say("B2. Mutants read off disk, edited and exec'd in memory")
    say("    `caught` is offsets where SOME of 8 splices moves a pre-splice bar")
    for name in MUTANTS:
        if name == "mask-back-dated":
            continue
        fn = mutant(name)
        for frame in ("walk", "tick-rounded", "cosine"):
            f = FRAMES[frame]
            base = np.asarray(c22_ami_timescale(f), float)
            mine = np.asarray(fn(f), float)
            moved, mask = diff_bars(base, mine)
            hits = _leaks(fn, f, offsets[frame], splices=8)
            one = _leaks(fn, f, offsets[frame], splices=1)
            say(f"    {name:<18} {frame:<13} caught at {len(hits):>2} / "
                f"{len(offsets[frame])} offsets ({len(one)} with ONE splice); "
                f"differs from the real module on {moved} bars (+{mask} mask)")

    say("")
    say("B2b. Why the counts are not 35 of 35, measured")
    say("    A back-dated write can only be seen on a bar whose own value and")
    say("    its neighbour's differ. For a mutant that moves bar J-1 to the")
    say("    window ending at J, a splice at J is invisible whenever the two")
    say("    windows read the same small integer:")
    for frame in ("walk", "tick-rounded", "cosine"):
        s = col(FRAMES[frame]).dropna().to_numpy()
        tied = float(np.mean(s[1:] == s[:-1]))
        say(f"    {frame:<13} neighbouring bars tie {tied:.1%} of the time; if "
            f"the eight splices were independent that would predict ~"
            f"{1 - tied:.0%} of offsets caught by one and ~{1 - tied ** 8:.0%} "
            f"by eight. They are NOT independent -- compare the measured "
            f"counts in B2.")
    say("    and the demean mutants are near-DEAD for a measurable reason:")
    for frame in ("walk", "penny"):
        win, _ = windows(FRAMES[frame])
        w = np.asarray(win, float)
        say(f"    {frame:<13} |window mean| / window sd: median "
            f"{float(np.median(np.abs(w.mean(1)) / w.std(1))):.4f}, max "
            f"{float(np.max(np.abs(w.mean(1)) / w.std(1))):.4f} -- a limb "
            f"demeaned by the block mean instead of its own is almost the same "
            f"limb")

    say("")
    say("B2c. A mutant that moves anything moves only bars at or after J-1")
    for name in ("write-back-dated", "window-one-ahead", "returns-rolled"):
        fn = mutant(name)
        f = FRAMES["walk"]
        worst = []
        base = np.asarray(fn(f), float)          # the MUTANT against itself
        for j in _offsets(len(f), count=12):
            other = np.asarray(fn(_spliced(f, j)), float)
            moved = np.where(~((base[:j] == other[:j])
                               | (np.isnan(base[:j]) & np.isnan(other[:j]))))[0]
            if len(moved):
                worst.append((j, int(moved.min()), int(moved.max()), len(moved)))
        say(f"    {name:<18} offsets that moved a pre-splice bar: {len(worst)};"
            f" (J, first, last, count) {worst[:4]}")

    say("")
    say("B3. The mask mutant is DEAD on a clean frame and live on a dirty one")
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    say(f"    clean walk: bit-equal to the real module: "
        f"{same(c22_ami_timescale(clean), fn(clean))}")
    caught = 0
    tried = []
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_ami_timescale(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        tried.append((j, moved.tolist()[:3], len(moved)))
        caught += len(moved) > 0
    say(f"    bad close at 12 offsets: caught {caught} / 12")
    for j, where, cnt in tried[:4]:
        say(f"        bad bar {j}: {cnt} bars differ, first {where}")

    say("")
    say("B4. Tie density -- why a one-bar shift can hide")
    for name, f in FRAMES.items():
        s = col(f).dropna().to_numpy()
        tied = int(np.sum(s[1:] == s[:-1]))
        say(f"    {name:<13} {tied} / {len(s) - 1} consecutive pairs equal "
            f"({tied / (len(s) - 1):.1%})")


# ------------------------------------------------------------- Gate C
def section_C():
    head("C. Gate C -- reachability")
    say("")
    say("C1. Fires, distinct values, range")
    for name, f in FRAMES.items():
        s = col(f)
        d = s.dropna()
        say(f"    {name:<13} fired {fired(s)} / {len(s)}  distinct "
            f"{d.nunique():>3}  range [{d.min():.0f}, {d.max():.0f}]  "
            f"non-zero {int((d != 0).sum())}  first bar "
            f"{int(s.notna().values.argmax())}")

    say("")
    say("C2. The sentinel and the floor of the scale")
    for name, f in FRAMES.items():
        d = col(f).dropna()
        say(f"    {name:<13} == {NO_MINIMUM} (sentinel): "
            f"{int((d == NO_MINIMUM).sum())}  == 2 (lowest possible): "
            f"{int((d == 2).sum())}  >= 10: {int((d >= 10).sum())}")

    say("")
    say("C3. The issue's own worry: BIST tick rounding")
    for name, f in (("penny", FRAMES["penny"]), ("tick-rounded",
                                                 FRAMES["tick-rounded"]),
                    ("walk", FRAMES["walk"])):
        c = f.to_numpy(dtype=float)
        r = c[1:] / c[:-1] - 1.0
        s = col(f).dropna()
        say(f"    {name:<13} exact-zero returns {int(np.sum(r == 0.0))} / "
            f"{r.size} ({np.mean(r == 0.0):.1%}), distinct returns "
            f"{len(set(r))}, column median {s.median():.1f} distinct "
            f"{s.nunique()}")
    say("    a window whose returns are ALL zero is blank, not 0 -- and the")
    say("    lag-40 limb goes constant 40 bars BEFORE that:")
    flat = Series(np.r_[walk(400).to_numpy(), np.full(300, 50.0)])
    s = col(flat)
    nan_at = np.isnan(s.to_numpy())
    say(f"        400 walk + 300 flat (closes flat from bar 400, returns 0 "
        f"from bar 401): fired {fired(s)} / {len(s)}, blank tail from bar "
        f"{int(np.argmax(nan_at[LENGTH:]) + LENGTH)}")
    for bar in (455, 459, 460, 461, 499, 500):
        say(f"        bar {bar}: {s.iloc[bar]}")

    say("")
    say("C4. Real data -- OWED")
    say("    Gate E's run on the 89 ALTPORT-1 BIST frames is what fills this;")
    say("    the launcher runs it after this session. Everything above is")
    say("    SYNTHETIC.")


# ------------------------------------------------------------- Gate D
def section_D():
    head("D. Gate D -- scale-free")

    say("")
    say("D1. Exact binary rescales -- bit-identical")
    for name, f in FRAMES.items():
        base = col(f)
        cells = []
        for factor in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            cells.append(same(base, col(f * factor)))
        say(f"    {name:<13} x8 x64 x2**-40 x2**40: {cells}")
    for length in (MIN_LENGTH, 120, 250):
        f = FRAMES["walk"]
        base = col(f, length=length)
        cells = [same(base, col(f * factor, length=length))
                 for factor in (8.0, 64.0)]
        say(f"    walk at length {length:<4} x8 x64: {cells}")
    for level in (1e-6, 1e6, 1e100):
        f = walk(level=level)
        say(f"    price level {level:<7g}: x8 {same(col(f), col(f * 8.0))} "
            f"fired {fired(col(f))}")

    say("")
    say("D2. Inexact rescales -- bars moved and NaN masks")
    for name, f in FRAMES.items():
        base = col(f)
        row = []
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            moved, mask = diff_bars(base, col(f * factor))
            row.append(f"x{factor:g}: {moved} bars, {mask} mask")
        say(f"    {name:<13} {'; '.join(row)}")

    say("")
    say("D3. Blind to the AMPLITUDE of the returns, not to their SHAPE")
    for factor in (0.5, 2.0, 10.0):
        base = col(FRAMES["walk"])
        rng = np.random.default_rng(11)
        r = rng.normal(0.0, 0.015, 1500)
        a = Series(100.0 * np.cumprod(1.0 + r))
        b = Series(100.0 * np.cumprod(1.0 + factor * r))
        moved, mask = diff_bars(col(a), col(b))
        say(f"    returns x{factor:<4g}: {moved} bars differ (+{mask} mask) of "
            f"{fired(col(a))} fired")
    say("    and a SHAPE change moves it:")
    base = col(FRAMES["walk"])
    shuffled = FRAMES["walk"].to_numpy(dtype=float).copy()
    r = shuffled[1:] / shuffled[:-1] - 1.0
    np.random.default_rng(3).shuffle(r)
    other = Series(100.0 * np.cumprod(np.r_[1.0, 1.0 + r]))
    moved, mask = diff_bars(base, col(other))
    say(f"        same returns, reshuffled: {moved} bars differ (+{mask} mask)")

    say("")
    say("D4. 0 < fires < n, and not constant")
    for name, f in FRAMES.items():
        s = col(f)
        d = s.dropna()
        say(f"    {name:<13} 0 < {fired(s)} < {len(s)}: "
            f"{0 < fired(s) < len(s)}  distinct {d.nunique()} > 1: "
            f"{d.nunique() > 1}")

    say("")
    say("D5. How close the decision runs to a rounding flip")
    say("    the smallest gap, in rho**2, between the deciding lag and the")
    say("    neighbour it beats:")
    for name, f in FRAMES.items():
        win, bars = windows(f)
        out = col(f)
        worst = math.inf
        for row, bar in zip(win, bars):
            v = out.iloc[bar]
            if np.isnan(v):
                continue
            r2 = rho2_pearson(row)
            i = int(v) - 1
            if i < 1 or i > TAU_MAX - 2:
                continue
            worst = min(worst, r2[i - 1] - r2[i], r2[i + 1] - r2[i])
        say(f"    {name:<13} min gap {worst:.3e}")


# ------------------------------------------------------- in-fork overlap
COMPARATORS = (
    ("ts_ac1_60", lambda c: ta.ts_ac1_60(c)),
    ("ts_aggac_60", lambda c: ta.ts_aggac_60(c)),
    ("firstzero_ac", lambda c: ta.firstzero_ac(c)),
    ("tf_autocorr_1e_60", lambda c: ta.tf_autocorr_1e_60(c)),
    ("tf_dfa_100", lambda c: ta.tf_dfa_100(c)),
    ("halflife", lambda c: ta.halflife(c)),
    ("lean_hurst_100", lambda c: ta.lean_hurst_100(c)),
    ("ts_binent_20", lambda c: ta.ts_binent_20(c)),
    ("ts_c3_20", lambda c: ta.ts_c3_20(c)),
    ("ts_perment_20", lambda c: ta.ts_perment_20(c)),
    ("ts_cid_ce_20", lambda c: ta.ts_cid_ce_20(c)),
    ("diff2_acf1", lambda c: ta.diff2_acf1(c)),
    ("entlz", lambda c: ta.entlz(c)),
    ("tf_spec_entropy_64", lambda c: ta.tf_spec_entropy_64(c)),
    ("tf_centroid_20", lambda c: ta.tf_centroid_20(c)),
)


def _comparator_columns(close):
    """Every comparator column, keyed on the Series' OWN name."""
    cols = {}
    for name, fn in COMPARATORS:
        try:
            got = fn(close)
        except Exception as e:                                # pragma: no cover
            cols[f"{name}:ERROR"] = Series(np.nan, index=close.index)
            say(f"    ! {name} raised {type(e).__name__}: {e}")
            continue
        if got is None:
            continue
        if isinstance(got, DataFrame):
            for c in got.columns:
                cols[f"{name}:{c}"] = got[c]
        else:
            cols[f"{name}:{got.name}"] = got
    return cols


def section_E():
    head("E. In-fork overlap (Gate E itself is run by the launcher)")
    pooled_mine, pooled = [], {}
    per_frame = {}
    for name, f in FRAMES.items():
        mine = col(f)
        cols = _comparator_columns(f)
        row = {}
        for key, s in cols.items():
            rho, n = spearman(mine, s)
            row[key] = (rho, n)
            pooled.setdefault(key, []).append(np.asarray(s, float))
        pooled_mine.append(np.asarray(mine, float))
        per_frame[name] = row
        top = sorted(row.items(), key=lambda kv: -abs(kv[1][0] if kv[1][0] ==
                                                      kv[1][0] else 0))[:5]
        say(f"    {name:<13} top 5 |rho|: " + ", ".join(
            f"{k} {v[0]:+.4f} (n={v[1]})" for k, v in top))

    say("")
    say("E1. Pooled over the frames, and the per-frame median")
    allmine = np.concatenate(pooled_mine)
    rows = []
    for key, chunks in pooled.items():
        rho, n = spearman(allmine, np.concatenate(chunks))
        meds = [abs(per_frame[f][key][0]) for f in FRAMES
                if per_frame[f][key][0] == per_frame[f][key][0]]
        rows.append((abs(rho) if rho == rho else 0.0, key, rho, n,
                     float(np.median(meds)) if meds else float("nan")))
    # Every comparator, not a top-N: a cut here would read as "these are the
    # only ones that matter" when the ranking is by the POOLED figure, which
    # the section goes on to argue is the misleading one.
    worst = (0.0, "", "")
    for _, key, rho, n, med in sorted(rows, reverse=True):
        cells = []
        for fname in FRAMES:
            r = per_frame[fname][key][0]
            cells.append("nan" if r != r else f"{r:+.4f}")
            if r == r and abs(r) > worst[0]:
                worst = (abs(r), key, fname)
        say(f"    {key:<34} pooled {rho:+.4f} (n={n})  per-frame median |rho| "
            f"{med:.4f}  per frame {cells}")
    say(f"    frames, in that order: {list(FRAMES)}")
    say(f"    largest single per-frame |rho| over all "
        f"{len(rows)} x {len(FRAMES)} cells: {worst[0]:.4f} "
        f"({worst[1]} on {worst[2]})")

    say("")
    say("E2. The nearest NOT-YET-SHIPPED relative")
    say("    catch22's CO_FirstMin_ac (issue #130, c22_acf_first_min) is the")
    say("    first minimum of the SIGNED ACF over the same 100 returns. It is")
    say("    not in this tree; measured here as a function, against this")
    say("    column:")
    for name, f in FRAMES.items():
        win, bars = windows(f)
        mine, theirs = [], []
        out = col(f)
        for row, bar in zip(win, bars):
            if np.isnan(out.iloc[bar]):
                continue
            d = np.asarray(row, float) - np.mean(row)
            ss = float((d * d).sum())
            rho = [float((d[:len(d) - k] * d[k:]).sum()) / ss
                   for k in range(1, TAU_MAX + 1)]
            first = TAU_MAX
            for i in range(1, TAU_MAX - 1):
                if rho[i] < rho[i - 1] and rho[i] < rho[i + 1]:
                    first = i + 1
                    break
            mine.append(out.iloc[bar])
            theirs.append(float(first))
        rho, n = spearman(mine, theirs)
        eq = sum(1 for a, b in zip(mine, theirs) if a == b)
        say(f"    {name:<13} spearman {rho:+.4f} (n={n}), equal "
            f"{eq}/{len(mine)} ({eq / max(1, len(mine)):.1%})")


# ------------------------------------------------------- the noise floor
def section_G():
    head("G. The noise floor")
    say(f"    NOISE_FLOOR = {NOISE_FLOOR:.3e} ({MODULE.NOISE_ULPS} eps) on the "
        f"window's return standard deviation")

    say("")
    say("G1. Inert on anything price-shaped")
    old = "return np.where(~bad & (sd > NOISE_FLOOR), out, np.nan)"
    new = "return np.where(~bad, out, np.nan)"
    assert SRC.count(old) == 1
    ns = {}
    exec(compile(SRC.replace(old, new), "<unguarded>", "exec"), ns)
    unguarded = ns["c22_ami_timescale"]
    for name, f in FRAMES.items():
        a, b = col(f), unguarded(f)
        moved, mask = diff_bars(a, b)
        say(f"    {name:<13} guarded vs unguarded: {moved} bars, {mask} mask; "
            f"windows the floor empties: {fired(b) - fired(a)}")
    for price, tick in ((1e6, 0.01), (1e9, 0.01), (100.0, 0.01)):
        f = Series(price + tick * np.arange(1500, dtype=float))
        a, b = col(f), unguarded(f)
        say(f"    one tick per bar at {price:<7g}: fired guarded {fired(a)}, "
            f"unguarded {fired(b)}")

    say("")
    say("G2. What the floor buys")
    f = Series(_ulp_ladder(1e6, 1500))
    a, b = col(f), unguarded(f)
    say(f"    1-ulp-per-bar ladder at 1e6: guarded fires {fired(a)}, "
        f"unguarded fires {fired(b)} reading "
        f"{sorted(set(b.dropna()))[:8]}")
    f = Series(np.r_[np.full(700, 1e6), np.nextafter(np.full(800, 1e6), np.inf)])
    a, b = col(f), unguarded(f)
    say(f"    flat except ONE 1-ulp step: guarded fires {fired(a)}, "
        f"unguarded fires {fired(b)} reading "
        f"{sorted(set(b.dropna()))[:8]}")
    say("")
    say("G3. An exactly flat window is blank either way")
    f = Series(np.full(400, 50.0))
    say(f"    400 identical closes: guarded {fired(col(f))}, unguarded "
        f"{fired(unguarded(f))}")

    say("")
    say("G4. WHICH rule empties a geometric ladder -- the floor or the")
    say("    constant-limb mask? `start * (1+step)**k` rounds each power on")
    say("    its own, so the consecutive ratios are NOT identical doubles:")
    for step in (0.01, 0.001, -0.005):
        f = ladder(step=step)
        c = f.to_numpy(dtype=float)
        r = c[1:] / c[:-1] - 1.0
        w = r[:LENGTH]
        loose = unguarded(f).dropna()
        say(f"    step {step:+.3f}: distinct returns in the first window "
            f"{len(set(w))}, window sd {np.std(w):.3e} "
            f"(floor {NOISE_FLOOR:.3e}); guarded fires {fired(col(f))}, "
            f"unguarded fires {len(loose)} over [{loose.min():.0f}, "
            f"{loose.max():.0f}] with {loose.nunique()} distinct, median "
            f"{loose.median():.0f}")


# --------------------------------------------------------- bad data, wiring
def section_H():
    head("H. Bad data, and the wiring")
    say("")
    say("H1. A bad close empties exactly its own windows")
    for bad in (np.nan, np.inf, 0.0, -5.0, 1e-310):
        f = FRAMES["walk"].copy()
        f.iloc[700] = bad
        s = col(f)
        blank = np.where(np.isnan(s.to_numpy()))[0]
        blank = blank[blank >= LENGTH]
        say(f"    close[700] = {bad!r:<8} blank bars >= {LENGTH}: "
            f"{len(blank)} from {blank.min() if len(blank) else '-'} to "
            f"{blank.max() if len(blank) else '-'}")
    say("")
    say("H2. A close PAIR whose ratio overflows")
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-300
    f.iloc[701] = 1e100
    s = col(f)
    blank = np.where(np.isnan(s.to_numpy()))[0]
    blank = blank[blank >= LENGTH]
    say(f"    1e-300 then 1e100: blank bars >= {LENGTH}: {len(blank)} "
        f"from {blank.min()} to {blank.max()}")
    say("")
    say("H2b. A close pair whose ratio is FINITE but enormous: the sums of")
    say("     squares overflow where the ratio did not. Without the")
    say("     `isfinite(den)` limb of the `bad` mask such a row reads the")
    say("     SENTINEL rather than NaN, which is the one failure the floor")
    say("     section calls dangerous.")
    old = "bad |= ~(den > 0.0) | ~np.isfinite(den)"
    new = "bad |= ~(den > 0.0)"
    assert SRC.count(old) == 1
    ns = {}
    exec(compile(SRC.replace(old, new), "<no-overflow-guard>", "exec"), ns)
    unguarded_overflow = ns["c22_ami_timescale"]
    for lo, hi in ((1e-50, 1e27), (1e-100, 1e100), (1e-20, 1e20)):
        f = FRAMES["walk"].copy()
        f.iloc[700] = lo
        f.iloc[701] = hi
        a, b = col(f), unguarded_overflow(f)
        blank_a = np.where(np.isnan(a.to_numpy()))[0]
        blank_a = blank_a[blank_a >= LENGTH]
        sent_b = int((b == NO_MINIMUM).sum())
        sent_a = int((a == NO_MINIMUM).sum())
        win, _ = windows(f)
        row = win[701 - LENGTH]                  # the window holding r[700]
        da = row[:-1] - row[:-1].mean()
        db = row[1:] - row[1:].mean()
        sa, sb = float((da * da).sum()), float((db * db).sum())
        say(f"     {lo:.0e} then {hi:.0e} (ratio {hi / lo:.0e}): the lag-1 "
            f"limbs of bar 701's window give sums of squares {sa:.3e} and "
            f"{sb:.3e}, product {sa * sb:.3e}")
        say(f"       guarded blanks {len(blank_a)} bars past warm-up"
            f"{f' ({blank_a.min()}..{blank_a.max()})' if len(blank_a) else ''}"
            f" and reports the sentinel on {sent_a}; unguarded blanks "
            f"{len(b) - fired(b) - LENGTH} and reports the sentinel on "
            f"{sent_b}; the two agree: {same(a, b)}")

    say("")
    say("H3. Short inputs")
    for n in (LENGTH - 1, LENGTH, LENGTH + 1, LENGTH + 2):
        f = walk(n)
        s = col(f)
        say(f"    n = {n:<4} -> {'None' if s is None else f'fired {fired(s)}'}")
    say("")
    say("H4. The length guard")
    for length in (None, 0, 1, MIN_LENGTH - 1, MIN_LENGTH, 250, 250.7):
        s = col(walk(1500), length=length)
        say(f"    length={length!r:<6} -> {s.name}  fired {fired(s)}")
    say("")
    say("H5. Offset and fillna")
    base = col(FRAMES["walk"])
    off = col(FRAMES["walk"], offset=2)
    say(f"    offset=2 is the shift of the unshifted column: "
        f"{same(off, base.shift(2))}")
    filled = col(FRAMES["walk"], fillna=-1.0)
    say(f"    fillna=-1 leaves 0 NaNs: {int(filled.isna().sum())}, and "
        f"-1 appears {int((filled == -1.0).sum())} times")
    say("")
    say("H6. The five wiring touch points")
    say(f"    module:   {Path(MODULE.__file__).relative_to(Path(MODULE.__file__).parents[2])}")
    say(f"    package:  {hasattr(ta.statistics, 'c22_ami_timescale')}")
    say(f"    Category: {'c22_ami_timescale' in ta.Category['statistics']}")
    df = DataFrame({"close": FRAMES['walk'].to_numpy()})
    acc = df.ta.c22_ami_timescale()
    say(f"    accessor: {acc.name}, fired {fired(acc)}, bit-equal to the "
        f"function: {same(acc, base)}")
    say(f"    tests:    {(Path(__file__).resolve().parent.parent / 'tests' / 'test_c22_ami_timescale.py').exists()}")
    say(f"    name/category: {base.name} / {base.category}")


# ----------------------------------------------------------- the test module
def section_T():
    head("T. This port's test module under the current numpy dispatch")
    import pytest
    say(f"    numpy {np.__version__}  pandas {pd.__version__}")
    say(f"    NPY_DISABLE_CPU_FEATURES = "
        f"{os.environ.get('NPY_DISABLE_CPU_FEATURES', '(unset)')!r}")
    code = pytest.main(["tests/test_c22_ami_timescale.py", "-q", "--no-header"])
    say(f"    pytest exit code {code}")


# ------------------------------------------------------------ cost
def section_Z():
    head("Z. Chunking and cost")
    say(f"    CHUNK_VALUES = {CHUNK_VALUES} -> step = "
        f"{max(1, CHUNK_VALUES // LENGTH)} rows at length {LENGTH}")
    f = FRAMES["walk"]
    base = col(f)
    for budget in (LENGTH, 4 * LENGTH, 1 << 10, CHUNK_VALUES):
        MODULE.CHUNK_VALUES = budget
        try:
            say(f"    budget {budget:<8} bit-equal to the default: "
                f"{same(base, col(f))}")
        finally:
            MODULE.CHUNK_VALUES = CHUNK_VALUES
    big = walk(400_000, seed=4)
    tracemalloc.start()
    t0 = time.perf_counter()
    s = col(big)
    dt = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    say(f"    n = 400,000: fired {fired(s)}, {dt:.2f}s, traced peak "
        f"{peak / 1e6:.1f} MB")


SECTIONS = {"A": section_A, "B": section_B, "C": section_C, "D": section_D,
            "E": section_E, "G": section_G, "H": section_H, "P": section_P,
            "T": section_T, "Z": section_Z}

#: `P` imports the GPL-3.0 reference library as a black box and is therefore
#: OPT-IN: a bare run does not touch it.
DEFAULT_SECTIONS = [k for k in SECTIONS if k != "P"]


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or DEFAULT_SECTIONS
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
    for key in want:
        SECTIONS[key]()
