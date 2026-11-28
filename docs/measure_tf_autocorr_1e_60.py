# -*- coding: utf-8 -*-
"""Measurement harness for `tf_autocorr_1e_60` (PandasTa issue #114).

Every number in `docs/TfAutocorr1E60Measured.md`, in
`pandas_ta/statistics/tf_autocorr_1e_60.py`'s docstring and in
`tests/test_tf_autocorr_1e_60.py` comes from a run of this file -- EXCEPT the
receipt's section F suite counts, which come from `python -m pytest -q`.

    python docs/measure_tf_autocorr_1e_60.py            # every section
    python docs/measure_tf_autocorr_1e_60.py A D        # named sections

Sections: A (Gate A, oracles), B (Gate B, mutants), C (Gate C,
reachability), D (Gate D, scale), E (in-fork overlap), F (what moves it),
G (the noise floor and what it costs), H (bad data), T (this port's test
module under the current numpy dispatch), Z (chunking and cost).

⚠ Figures that are counts of LAST BITS move with numpy's kernels. Run

    python docs/measure_tf_autocorr_1e_60.py --no-avx A D T

to see what a CI runner without AVX-512 reads: `--no-avx` re-executes this
file with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` set
BEFORE numpy is imported. It is a flag rather than an environment prefix
because the shell this was written under cannot put a variable in front of a
command.
"""
from __future__ import annotations

#: `os` and `sys` are imported HERE, above the rest, because the re-exec
#: below has to run before numpy is imported anywhere in the process.
import os
import sys

#: What a GitHub runner without AVX-512 gives numpy's kernels. `--no-avx`
#: re-executes this file with it set, BEFORE numpy is imported, because the
#: variable is read once at import.
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
import types
from fractions import Fraction

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.tf_autocorr_1e_60 import (  # noqa: E402
    MIN_LENGTH, NLAGS, NO_CROSSING, NOISE_FLOOR, THRESHOLD,
    tf_autocorr_1e_60)

MODULE = importlib.import_module("pandas_ta.statistics.tf_autocorr_1e_60")
LENGTH = 60


# --------------------------------------------------------------- frames
def walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    """A path whose LOG returns are an AR(1)."""
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def ladder(n=1500, step=0.01, start=100.0):
    """An exactly geometric path: log price is a straight line."""
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def alternating(n=1500, up=0.02, down=0.02):
    r = np.where(np.arange(n) % 2 == 0, up, -down)
    return Series(100.0 * np.exp(np.cumsum(r)))


def sine(n=1500, period=40.0, amp=0.10):
    t = np.arange(n, dtype=float)
    return Series(100.0 * np.exp(amp * np.sin(2 * np.pi * t / period)))


def _ulp_ladder(price, n, every=1):
    """A path that steps up by ONE double ulp every `every` bars."""
    out = np.empty(n)
    v = price
    for i in range(n):
        out[i] = v
        if (i + 1) % every == 0:
            v = np.nextafter(v, np.inf)
    return out


def one_tick(n=1500, price=1e6, tick=0.01):
    """A monotone one-tick-per-bar path: genuinely varying, tiny."""
    return Series(price + tick * np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "ar1": ar1(),
    "sine": sine(),
}


def say(*parts):
    print(*parts, flush=True)


def head(title):
    say("")
    say("=" * 72)
    say(title)
    say("=" * 72)


def fired(s):
    return int(s.notna().sum())


# ------------------------------------------------- oracles (Gate A)
def proto_acf_first_1e(W, nlags=NLAGS):
    """The screen prototype's `_acf_first_1e`, retyped from
    `docs/issues/screen/ind_screen_r2.py:190-201` (gitignored, so it cannot be
    imported on a clean checkout). NO noise floor: the prototype has none."""
    with np.errstate(invalid="ignore"):
        D = W - W.mean(1, keepdims=True)
        var = (D ** 2).mean(1)
        out = np.full(len(W), nlags + 1.0)
        done = np.zeros(len(W), dtype=bool)
        for k in range(1, nlags + 1):
            a = (D[:, :-k] * D[:, k:]).mean(1) / np.where(var == 0, np.nan,
                                                          var)
            hit = (a < np.exp(-1)) & ~done
            out[hit] = k
            done |= hit
    return np.where(var == 0, np.nan, out)


def proto_column(close, length=LENGTH, nlags=NLAGS):
    """`roll(np.log(c), 60, _acf_first_1e)` -- the prototype's own line
    (`ind_screen_r2.py:204-206`), with `roll`/`_win`/`_from_win` retyped from
    `ind_screen.py:62-71,175-176`."""
    with np.errstate(divide="ignore", invalid="ignore"):
        a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length) if len(a) >= length else np.empty((0, length))
    out = np.full(len(a), np.nan)
    out[length - 1:] = proto_acf_first_1e(W, nlags)
    return Series(out, index=close.index)


def imported_proto_column(close, length=LENGTH):
    """The owner's own registry entry, when `docs/issues/` is present."""
    here = os.path.dirname(os.path.abspath(__file__))
    screen = os.path.join(here, "issues", "screen")
    if not os.path.isfile(os.path.join(screen, "ind_screen_r2.py")):
        return None
    sys.path.insert(0, screen)
    try:
        r2 = importlib.import_module("ind_screen_r2")
    except Exception as exc:                       # pragma: no cover
        say(f"    import failed: {exc!r}")
        return None
    fn = r2.REG["tf_autocorr_1e_60"]["fn"]
    z = Series(np.zeros(len(close)), index=close.index)
    return Series(np.asarray(fn(z, z, z, close, z), dtype=float),
                  index=close.index)


def scalar_first_1e(close, length=LENGTH, nlags=NLAGS):
    """An independent spelling: plain Python, `math.fsum`, explicit slices,
    `math.log` of the ABSOLUTE price, no numpy windowing and NO noise floor.
    Written from the formula text ("first lag with ACF < 1/e", adjusted), not
    from the module."""
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = [math.nan] * len(c)
    thr = math.exp(-1.0)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if any((not math.isfinite(v)) or v <= 0.0 for v in w):
            continue
        x = [math.log(v) for v in w]
        mu = math.fsum(x) / length
        d = [v - mu for v in x]
        var = math.fsum(v * v for v in d) / length
        if var == 0.0:
            continue
        ans = float(nlags + 1)
        for k in range(1, nlags + 1):
            cov = math.fsum(d[i] * d[i + k]
                            for i in range(length - k)) / (length - k)
            if cov / var < thr:
                ans = float(k)
                break
        out[t] = ans
    return Series(out, index=close.index)


def statsmodels_first_1e(close, length=LENGTH, nlags=NLAGS):
    """`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False)` applied to
    `log(close)` window by window. None when statsmodels is absent."""
    try:
        from statsmodels.tsa.stattools import acf
    except Exception:
        return None
    a = np.log(close.to_numpy(dtype=float))
    out = np.full(len(a), np.nan)
    thr = math.exp(-1.0)
    for t in range(length - 1, len(a)):
        x = a[t - length + 1:t + 1]
        if not np.isfinite(x).all() or x.var() == 0.0:
            continue
        ac = acf(x, adjusted=True, fft=False, nlags=nlags)[1:]
        hit = np.flatnonzero(ac < thr)
        out[t] = float(hit[0] + 1) if hit.size else float(nlags + 1)
    return Series(out, index=close.index)


def plain_log_column(close, length=LENGTH):
    """This module's arithmetic, but reading `log(close)` directly instead of
    cumulating the window's own log returns -- the one difference in the
    ARITHMETIC, isolated. The other two differences from the prototype are
    behavioural and are measured in section A6b."""
    a = np.log(close.to_numpy(dtype=float))
    out = np.full(len(a), np.nan)
    if len(a) >= length:
        x = sliding_window_view(a, length)
        d = x - x.mean(axis=1, keepdims=True)
        var = (d * d).mean(axis=1)
        sd = np.sqrt(var)
        safe = np.where(var > 0.0, var, 1.0)
        rows = np.full(x.shape[0], float(NO_CROSSING))
        done = np.zeros(x.shape[0], dtype=bool)
        for k in range(1, NLAGS + 1):
            ac = (d[:, :-k] * d[:, k:]).mean(axis=1) / safe
            hit = (ac < THRESHOLD) & ~done
            rows[hit] = k
            done |= hit
        out[length - 1:] = np.where(sd > NOISE_FLOOR, rows, np.nan)
    return Series(out, index=close.index)


def unguarded(close, length=LENGTH):
    """This module with the noise floor removed (NaN only when the window is
    exactly flat), to price what the floor buys."""
    src = open(MODULE.__file__, encoding="utf-8").read()
    old = "    return np.where(sd > NOISE_FLOOR, out, np.nan)"
    new = "    return np.where(sd > 0.0, out, np.nan)"
    assert src.count(old) == 1
    mod = types.ModuleType("_tfac_unguarded")
    mod.__file__ = MODULE.__file__
    exec(compile(src.replace(old, new), MODULE.__file__, "exec"), mod.__dict__)
    return mod.tf_autocorr_1e_60(close, length=length)


def window_floor_hits(close, length=LENGTH):
    """How many fired-eligible windows reach the noise floor."""
    c = close.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        g = np.log(c[1:] / c[:-1])
    g = np.where(np.isfinite(g), g, np.nan)
    win = sliding_window_view(g, length - 1)
    x = np.concatenate([np.zeros((win.shape[0], 1)), np.cumsum(win, axis=1)],
                       axis=1)
    d = x - x.mean(axis=1, keepdims=True)
    sd = np.sqrt((d * d).mean(axis=1))
    return int(np.sum(~(sd > NOISE_FLOOR))), int(sd.size)


def agree(a, b):
    """(bit-equal bars, bars both define, masks equal, max |difference|)."""
    a, b = a.to_numpy(dtype=float), np.asarray(b, dtype=float)
    ma, mb = ~np.isnan(a), ~np.isnan(b)
    both = ma & mb
    diff = np.abs(a[both] - b[both])
    return (int((a[both] == b[both]).sum()), int(both.sum()),
            bool((ma == mb).all()),
            float(diff.max()) if diff.size else 0.0)


# ----------------------------------------------------------------- A
def section_a():
    head("A -- Gate A: the formula, against four independent spellings")
    say(f"NLAGS={NLAGS}  NO_CROSSING={NO_CROSSING}  THRESHOLD={THRESHOLD!r}"
        f"  MIN_LENGTH={MIN_LENGTH}  NOISE_FLOOR={NOISE_FLOOR:.3e}")

    say("")
    say("A1. the retyped screen prototype, `roll(np.log(c), 60, _acf_first_1e)`")
    for name, close in FRAMES.items():
        mine = tf_autocorr_1e_60(close)
        theirs = proto_column(close)
        eq, both, masks, mx = agree(mine, theirs)
        hits, total = window_floor_hits(close)
        say(f"    {name:<13} bit-equal {eq}/{both}  masks equal {masks}  "
            f"max|diff| {mx:g}  floor hits {hits}/{total}")

    say("")
    say("A1b. the owner's own registry entry, imported from docs/issues/screen")
    for name, close in FRAMES.items():
        theirs = imported_proto_column(close)
        if theirs is None:
            say(f"    {name:<13} docs/issues/screen/ind_screen_r2.py absent")
            continue
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close), theirs)
        retype = agree(proto_column(close), theirs)
        say(f"    {name:<13} module {eq}/{both} masks {masks}  "
            f"retype-vs-import {retype[0]}/{retype[1]} masks {retype[2]}")

    say("")
    say("A2. a plain-Python `math.fsum` spelling, no numpy, no floor")
    for name, close in FRAMES.items():
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close),
                                    scalar_first_1e(close))
        say(f"    {name:<13} bit-equal {eq}/{both}  masks equal {masks}  "
            f"max|diff| {mx:g}")

    say("")
    say("A3. statsmodels `acf(x, adjusted=True, fft=False)` on log(close)")
    for name, close in FRAMES.items():
        theirs = statsmodels_first_1e(close)
        if theirs is None:
            say("    statsmodels is NOT installed in this worktree")
            break
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close), theirs)
        say(f"    {name:<13} bit-equal {eq}/{both}  masks equal {masks}  "
            f"max|diff| {mx:g}")

    say("")
    say("A4. a hand-derived case: an exactly geometric path, whose log price")
    say("    is a straight line, so the adjusted ACF has a closed form in")
    say("    EXACT rationals (`fractions.Fraction`, no float anywhere).")
    expected = ramp_crossing(LENGTH, NLAGS)
    say(f"    closed form at length={LENGTH}: first lag below 1/e is "
        f"{expected}")
    for ratios in (Fraction(1, 100), Fraction(1, 1000), Fraction(-1, 200)):
        step = float(ratios)
        col = tf_autocorr_1e_60(ladder(step=step))
        vals = np.unique(col.dropna().to_numpy())
        say(f"    ladder step {step:+.4f}: values {vals}  fired {fired(col)}")
    for n in (40, 45, 60, 100, 250):
        exp_n = ramp_crossing(n, NLAGS)
        col = tf_autocorr_1e_60(ladder(), length=n)
        vals = np.unique(col.dropna().to_numpy())
        say(f"    length {n:>3}: closed form {exp_n}, module reads {vals}")

    say("")
    say("A5. the attainable set over 1 .. 21, by construction and by sampling")
    say(f"    alternating path:   "
        f"{np.unique(tf_autocorr_1e_60(alternating()).dropna().to_numpy())}")
    rng = np.random.default_rng(3)
    seen = {}
    for trial in range(4000):
        x = np.cumsum(rng.normal(0.0, 1.0, LENGTH))
        v = _one_window(x)
        seen[v] = seen.get(v, 0) + 1
    say(f"    4,000 iid-increment windows: "
        f"{sorted(int(k) for k in seen)}")
    say(f"      counts {dict(sorted((int(k), v) for k, v in seen.items()))}")
    say("    windows whose log price is a cosine of period P (deterministic):")
    for period in (4, 6, 10, 20, 40, 120, 400):
        x = np.cos(2 * np.pi * np.arange(LENGTH) / period)
        say(f"      P={period:>3}  ->  {_one_window(x):.0f}")

    say("")
    say("A5b. is the NO_CROSSING sentinel reachable at length 60?")
    say("    a single-lag upper bound, exact: max ACF(k) over all demeaned")
    say("    windows is (n / (n - k)) times the top eigenvalue of the lag-k")
    say("    product form restricted to the demeaned subspace.")
    for n in (40, 60, 100, 250):
        say(f"    length {n:>3}: " + "  ".join(
            f"k={k} {max_acf(n, k):.4f}" for k in (1, 10, 20)))
    say("    a NO_CROSSING window needs EVERY lag 1..20 at or above 1/e at")
    say("    once, which no bound here settles. Direct search instead:")
    best, where = search_no_crossing(LENGTH)
    say(f"    best value found over 30,000 smooth random windows: {best:.0f} "
        f"({where})")

    say("")
    say("A6. the one difference in the ARITHMETIC: cumulated window log")
    say("    returns against `log(close)` read directly")
    for name, close in FRAMES.items():
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close),
                                    plain_log_column(close))
        say(f"    {name:<13} bit-equal {eq}/{both}  masks equal {masks}  "
            f"max|diff| {mx:g}")
    say("    and at a price far from 1, where `log(close)` loses digits to")
    say("    cancellation that the ratio form never forms:")
    for price in (1e-6, 1.0, 1e3, 1e6, 1e9):
        close = walk() * (price / 100.0)
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close),
                                    plain_log_column(close))
        say(f"    price~{price:<8g} bit-equal {eq}/{both}  masks equal {masks}"
            f"  max|diff| {mx:g}")

    say("")
    say("A6b. the TWO BEHAVIOURAL divergences from the prototype, which a")
    say("    clean frame cannot show. The prototype's only guard is")
    say("    `np.where(var == 0, np.nan, out)`, and a window holding a bad")
    say("    close has var NaN rather than 0, so `var == 0` is False and the")
    say("    prototype reports the 21 SENTINEL where this module reports NaN.")
    base = walk()
    for label, bad in (("NaN", np.nan), ("zero", 0.0), ("negative", -5.0),
                       ("+inf", np.inf), ("subnormal", 1e-310)):
        c = base.copy()
        c.iloc[700] = bad
        mine, theirs = tf_autocorr_1e_60(c), proto_column(c)
        a = mine.to_numpy(dtype=float)
        b = theirs.to_numpy(dtype=float)
        only_mine = int((np.isnan(a) & ~np.isnan(b)).sum())
        only_theirs = int((~np.isnan(a) & np.isnan(b)).sum())
        m = ~np.isnan(a) & ~np.isnan(b)
        say(f"    close[700] = {label:<10} module NaN where prototype fires: "
            f"{only_mine}  the reverse: {only_theirs}  "
            f"prototype's value there: "
            f"{np.unique(b[np.isnan(a) & ~np.isnan(b)])}  "
            f"bit-equal elsewhere {int((a[m] == b[m]).sum())}/{int(m.sum())}")
    say("    and the second divergence, the noise floor the prototype does")
    say("    not have (see section G for what it buys and costs):")
    ulp = Series(_ulp_ladder(1e6, 1500))
    mine, theirs = tf_autocorr_1e_60(ulp), proto_column(ulp)
    say(f"    1-ulp-per-bar ladder: module fires {fired(mine)}, prototype "
        f"fires {fired(theirs)} with values "
        f"{np.unique(theirs.dropna().to_numpy()).astype(int).tolist()}")

    say("")
    say("A7. the readings the issue's line leaves open, each priced")
    say("    (a) ADJUSTED (divide the lag-k products by length - k, the")
    say("        prototype's `.mean(1)`) against BIASED (divide by length):")
    for name, close in FRAMES.items():
        mine = tf_autocorr_1e_60(close)
        other = variant(close, biased=True)
        eq, both, masks, mx = agree(mine, other)
        m = mine.notna() & other.notna()
        say(f"    {name:<13} bit-equal {eq}/{both}  max|diff| {mx:g}  "
            f"Spearman {float(mine[m].corr(other[m], method='spearman')):+.6f}")
    say("    (b) strict `<` against `<=`:")
    for name, close in FRAMES.items():
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close),
                                    variant(close, inclusive=True))
        say(f"    {name:<13} bit-equal {eq}/{both}  max|diff| {mx:g}")
    say("    (c) the ACF of LOG PRICE (the issue's form) against the ACF of")
    say("        log RETURNS -- a different column entirely:")
    for name, close in FRAMES.items():
        mine = tf_autocorr_1e_60(close)
        other = variant(close, on_returns=True)
        eq, both, masks, mx = agree(mine, other)
        m = mine.notna() & other.notna()
        say(f"    {name:<13} bit-equal {eq}/{both}  "
            f"Spearman {float(mine[m].corr(other[m], method='spearman')):+.6f}")


def variant(close, length=LENGTH, biased=False, inclusive=False,
            on_returns=False):
    """The module's quantity under one changed reading at a time."""
    c = close.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        g = np.log(c[1:] / c[:-1])
    g = np.where(np.isfinite(g), g, np.nan)
    out = np.full(c.size, np.nan)
    if on_returns:
        win = sliding_window_view(g, length)
        x = win.copy()
        first = length            # bar of the first full window of RETURNS
    else:
        win = sliding_window_view(g, length - 1)
        x = np.concatenate(
            [np.zeros((win.shape[0], 1)), np.cumsum(win, axis=1)], axis=1)
        first = length - 1
    d = x - x.mean(axis=1, keepdims=True)
    var = (d * d).mean(axis=1)
    sd = np.sqrt(var)
    safe = np.where(var > 0.0, var, 1.0)
    rows = np.full(x.shape[0], float(NO_CROSSING))
    done = np.zeros(x.shape[0], dtype=bool)
    width = x.shape[1]
    for k in range(1, NLAGS + 1):
        s = (d[:, :-k] * d[:, k:]).sum(axis=1)
        acf = (s / (width if biased else (width - k))) / safe
        hit = ((acf <= THRESHOLD) if inclusive else (acf < THRESHOLD)) & ~done
        rows[hit] = k
        done |= hit
    out[first:first + rows.size] = np.where(sd > NOISE_FLOOR, rows, np.nan)
    return Series(out, index=close.index)


def max_acf(n, k):
    """Largest adjusted ACF(k) any demeaned window of `n` points can have."""
    a = np.zeros((n, n))
    idx = np.arange(n - k)
    a[idx, idx + k] = 0.5
    a[idx + k, idx] = 0.5
    p = np.eye(n) - np.ones((n, n)) / n          # onto the demeaned subspace
    w = np.linalg.eigvalsh(p @ a @ p)
    return float(n / (n - k) * w.max())


def search_no_crossing(n, trials=30_000, seed=99):
    """Hunt for a window reading NO_CROSSING: smooth random log prices built
    from a few low-frequency cosines plus a ramp, which is where a slowly
    decaying ACF lives."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    basis = np.vstack([t / n] + [np.cos(np.pi * (j + 1) * t / n)
                                 for j in range(6)])
    best, where = -1.0, ""
    for i in range(trials):
        w = rng.normal(0.0, 1.0, basis.shape[0])
        w[0] += rng.normal(0.0, 4.0)             # bias toward a trend
        v = _one_window(basis.T @ w * 0.01)
        if v > best:
            best, where = v, f"trial {i}, weights {np.round(w, 3).tolist()}"
    return best, where


def _one_window(x):
    """The module's answer for a single window given as log prices."""
    close = Series(np.exp(np.asarray(x, dtype=float)))
    return float(tf_autocorr_1e_60(close, length=len(close)).iloc[-1])


def ramp_crossing(n, nlags=NLAGS):
    """First lag k whose ADJUSTED ACF of the ramp d_t = t - (n-1)/2 is below
    1/e, in exact rational arithmetic against a rational lower bound on 1/e.

    var = mean(d^2) = (n^2 - 1) / 12; cov(k) = sum_{t} d_t d_{t+k} / (n - k).
    """
    half = Fraction(n - 1, 2)
    d = [Fraction(t) - half for t in range(n)]
    var = sum(v * v for v in d) / n
    # 1/e to 60 digits, as a rational; the comparison below never lands
    # within 1e-40 of it (asserted by the margin printed in section A).
    inv_e = Fraction(
        "0.367879441171442321595523770161460867445811131031767834507836")
    for k in range(1, nlags + 1):
        cov = sum(d[t] * d[t + k] for t in range(n - k)) / (n - k)
        if cov / var < inv_e:
            return k
    return nlags + 1


# ----------------------------------------------------------------- B
WRITE_SHIFT = ("    result = Series(out, index=close.index)",
               "    result = Series(out, index=close.index).shift(-length)")
WRITE_EARLY = ("            out[length - 1 + a:length - 1 + b] = "
               "_first_1e_rows(win[a:b])",
               "            out[length - 2 + a:length - 2 + b] = "
               "_first_1e_rows(win[a:b])")
FORWARD_RETURN = ("        g = np.log(c[1:] / c[:-1])",
                  "        g = np.log(np.roll(c, -1)[1:] / c[:-1])")
FORWARD_MEAN = ("    d = x - x.mean(axis=1, keepdims=True)",
                "    d = x - np.roll(x.mean(axis=1, keepdims=True), -1, "
                "axis=0)")
FORWARD_PRODUCT = ("        acf = (d[:, :-k] * d[:, k:]).mean(axis=1) / safe",
                   "        acf = (d[:, :-k] * np.roll(d, -1, axis=0)"
                   "[:, k:]).mean(axis=1) / safe")
FORWARD_SD = ("    sd = np.sqrt(var)",
              "    sd = np.roll(np.sqrt(var), -1)")

MUTANTS = [("write_shift", WRITE_SHIFT), ("write_early", WRITE_EARLY),
           ("forward_return", FORWARD_RETURN), ("forward_mean", FORWARD_MEAN),
           ("forward_product", FORWARD_PRODUCT)]
OFFSETS = list(range(120, 1500, 40))


def load_mutant(old, new):
    src = open(MODULE.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target not unique: {old!r}"
    mod = types.ModuleType("_tfac_mutant")
    mod.__file__ = MODULE.__file__
    exec(compile(src.replace(old, new), MODULE.__file__, "exec"), mod.__dict__)
    return mod


def leaks(fn, close, other):
    hit = []
    base = fn(close)
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


def flat_planted(j, n=1500, seed=21, runlen=LENGTH + 1):
    """A walk carrying `runlen` identical closes ending at bar j, so the
    noise floor fires on the windows around j."""
    c = walk(n, seed).to_numpy().copy()
    c[j - runlen + 1:j + 1] = c[j - runlen + 1]
    return Series(c)


def section_b():
    head("B -- Gate B: causality, by future-perturbation sweep and mutants")
    say(f"    {len(OFFSETS)} offsets, {OFFSETS[0]} .. {OFFSETS[-1]} step 40")
    pairs = {"walk": (walk(), walk(seed=97)),
             "tick-rounded": (tick_rounded(), tick_rounded(seed=56)),
             "ar1": (ar1(), ar1(seed=8))}
    for name, (close, other) in pairs.items():
        say(f"    real module, {name:<13} leaks "
            f"{len(leaks(tf_autocorr_1e_60, close, other))}/{len(OFFSETS)}")
    for mid, (old, new) in MUTANTS:
        mod = load_mutant(old, new)
        row = []
        for name, (close, other) in pairs.items():
            row.append(f"{name} {len(leaks(mod.tf_autocorr_1e_60, close, other))}"
                       f"/{len(OFFSETS)}")
        say(f"    mutant {mid:<16} " + "  ".join(row))

    say("")
    say("    how far a one-bar look-ahead can reach into the prefix")
    for mid, (old, new) in MUTANTS[1:]:
        mod = load_mutant(old, new)
        close, other = pairs["walk"]
        base = mod.tf_autocorr_1e_60(close)
        seen = set()
        for j in OFFSETS:
            p = close.copy()
            p.iloc[j:] = other.iloc[j:].values
            out = mod.tf_autocorr_1e_60(p)
            a, b = base.iloc[:j], out.iloc[:j]
            moved = np.flatnonzero(
                ((a != b) & ~(a.isna() & b.isna())).to_numpy())
            seen.add(tuple((moved - j).tolist()))
        say(f"    mutant {mid:<16} moved-bar offsets {sorted(seen)[:4]}"
            f"{' ...' if len(seen) > 4 else ''}")

    say("")
    say("    the noise floor's own windowed input (`sd`), swept on frames")
    say("    where the floor actually fires")
    mod = load_mutant(*FORWARD_SD)
    real_hits, mut_hits = 0, 0
    for j in OFFSETS:
        close = flat_planted(j)
        other = walk(seed=98)
        if leaks(tf_autocorr_1e_60, close, other):
            real_hits += 1
        if leaks(mod.tf_autocorr_1e_60, close, other):
            mut_hits += 1
    say(f"    real {real_hits}/{len(OFFSETS)} planted frames leak, "
        f"forward_sd mutant {mut_hits}/{len(OFFSETS)}")

    say("")
    say("    the sweep at non-default lengths, on the walk")
    close, other = pairs["walk"]
    for n in (40, 100, 250):
        def real(c, n=n):
            return tf_autocorr_1e_60(c, length=n)
        row = [f"real {len(leaks(real, close, other))}/{len(OFFSETS)}"]
        for mid, (old, new) in MUTANTS:
            mod = load_mutant(old, new)

            def mut(c, mod=mod, n=n):
                return mod.tf_autocorr_1e_60(c, length=n)
            row.append(f"{mid} {len(leaks(mut, close, other))}/{len(OFFSETS)}")
        say(f"    length {n:>3}  " + "  ".join(row))

    say("")
    say("    tie density -- how often consecutive bars carry the same value,")
    say("    which is the ceiling on what a one-bar sweep can see")
    for name, close in FRAMES.items():
        v = tf_autocorr_1e_60(close).dropna().to_numpy()
        say(f"    {name:<13} {int((v[1:] == v[:-1]).sum())}/{v.size - 1} "
            f"consecutive pairs equal")
    for n in (40, 100, 250):
        v = tf_autocorr_1e_60(walk(), length=n).dropna().to_numpy()
        say(f"    walk length {n:>3}  {int((v[1:] == v[:-1]).sum())}/"
            f"{v.size - 1} consecutive pairs equal")


# ----------------------------------------------------------------- C
def section_c():
    head("C -- Gate C: reachability on synthetic frames")
    for name, close in FRAMES.items():
        col = tf_autocorr_1e_60(close)
        v = col.dropna().to_numpy()
        vals, counts = np.unique(v, return_counts=True)
        say(f"    {name:<13} fired {v.size}/{len(close)}  first bar "
            f"{int(col.notna().to_numpy().argmax())}  "
            f"distinct {vals.size}  min {v.min():.0f} max {v.max():.0f}  "
            f"median {np.median(v):.1f} mean {v.mean():.4f}")
        say(f"      values {dict(zip(vals.astype(int), counts))}")
    say("")
    say("    the NO_CROSSING sentinel, by frame")
    for name, close in FRAMES.items():
        v = tf_autocorr_1e_60(close).dropna().to_numpy()
        say(f"    {name:<13} {int((v == NO_CROSSING).sum())}/{v.size} bars "
            f"read {NO_CROSSING}  ({100.0 * (v == NO_CROSSING).mean():.2f}%)")
    say("")
    say("    non-default lengths on the walk")
    for n in (40, 45, 100, 250):
        col = tf_autocorr_1e_60(walk(), length=n)
        v = col.dropna().to_numpy()
        say(f"    length {n:>3} fired {v.size}  distinct {np.unique(v).size}  "
            f"min {v.min():.0f} max {v.max():.0f} mean {v.mean():.4f}")
    say("")
    say("    on the dictionary generator's OWN probe frame -- the one that")
    say("    decides the SF/ORD tag (`docs/gen_indicator_dictionary.py`:")
    say("    N = 600, rng(7).normal(0, 0.012), rule '<= 12 distinct integers'")
    say("    at line 147)")
    probe = Series(100.0 * np.exp(np.cumsum(
        np.random.default_rng(7).normal(0, 0.012, 600))))
    v = tf_autocorr_1e_60(probe).dropna().to_numpy()
    say(f"    fired {v.size}/600  distinct {np.unique(v).size}  "
        f"values {np.unique(v).astype(int).tolist()}")

    say("")
    say("    guard band: what a short or missing `length` falls back to")
    close = walk()
    for n in (None, 0, -5, 1, 39, 39.9, 40):
        col = tf_autocorr_1e_60(close, length=n)
        say(f"    length={n!r:<6} -> {col.name}")


# ----------------------------------------------------------------- D
def section_d():
    head("D -- Gate D: scale-free")
    say("    exact binary factors; the ratio `8a / 8b` is the same double as")
    say("    `a / b`, so these are bit-identical BY CONSTRUCTION")
    for name, close in FRAMES.items():
        base = tf_autocorr_1e_60(close)
        row = []
        for f in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            eq, both, masks, mx = agree(base, tf_autocorr_1e_60(close * f))
            row.append(f"x{f:<10g} {eq}/{both} masks {masks}")
        say(f"    {name:<13} " + " | ".join(row))
    say("")
    say("    inexact factors (not promised: an integer decided by a float")
    say("    comparison can flip on a last-bit change)")
    for name, close in FRAMES.items():
        base = tf_autocorr_1e_60(close)
        row = []
        for f in (10.0, 3.7, 0.1, 1.0000001):
            eq, both, masks, mx = agree(base, tf_autocorr_1e_60(close * f))
            row.append(f"x{f:<9g} {eq}/{both} masks {masks}")
        say(f"    {name:<13} " + " | ".join(row))
    say("")
    say("    non-default lengths, every exact binary factor")
    for n in (40, 45, 100, 250):
        base = tf_autocorr_1e_60(walk(), length=n)
        row = []
        for f in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            eq, both, masks, mx = agree(base,
                                        tf_autocorr_1e_60(walk() * f, length=n))
            row.append(f"x{f:<10g} {eq}/{both} masks {masks}")
        say(f"    length {n:>3}  " + " | ".join(row))
    say("")
    say("    how near the 1/e decision actually runs: the smallest margin")
    say("    |ACF(k) - 1/e| at the DECIDING lag, over each frame")
    for name, close in FRAMES.items():
        mn, ties, total = decision_margin(close)
        say(f"    {name:<13} min margin {mn:.3e}  exact ties {ties}  "
            f"windows {total}")
    say("")
    say("    0 < fires < n, and not constant")
    for name, close in FRAMES.items():
        col = tf_autocorr_1e_60(close)
        v = col.dropna().to_numpy()
        say(f"    {name:<13} 0 < {v.size} < {len(close)}  "
            f"distinct {np.unique(v).size}")


def decision_margin(close, length=LENGTH):
    """Smallest |ACF(k) - 1/e| at the lag each window's answer turns on."""
    c = close.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        g = np.log(c[1:] / c[:-1])
    g = np.where(np.isfinite(g), g, np.nan)
    win = sliding_window_view(g, length - 1)
    x = np.concatenate([np.zeros((win.shape[0], 1)), np.cumsum(win, axis=1)],
                       axis=1)
    d = x - x.mean(axis=1, keepdims=True)
    var = (d * d).mean(axis=1)
    safe = np.where(var > 0.0, var, 1.0)
    best = np.full(win.shape[0], np.inf)
    done = np.zeros(win.shape[0], dtype=bool)
    ties = 0
    for k in range(1, NLAGS + 1):
        ac = (d[:, :-k] * d[:, k:]).mean(axis=1) / safe
        margin = np.abs(ac - THRESHOLD)
        live = ~done
        best[live] = np.minimum(best[live], margin[live])
        ties += int((ac[live] == THRESHOLD).sum())
        done |= (ac < THRESHOLD)
    ok = np.isfinite(best)
    return float(best[ok].min()), ties, int(ok.sum())


# ----------------------------------------------------------------- E
NEIGHBOURS = [
    ("ts_ac1_60", lambda c: ta.ts_ac1_60(c)),
    ("ts_aggac_60", lambda c: ta.ts_aggac_60(c)),
    ("firstzero_ac", lambda c: ta.firstzero_ac(c)),
    ("diff2_acf1", lambda c: ta.diff2_acf1(c)),
    ("tf_dfa_100", lambda c: ta.tf_dfa_100(c)),
    ("lean_hurst_100", lambda c: ta.lean_hurst_100(c)),
    ("halflife", lambda c: ta.halflife(c)),
    ("lumpiness", lambda c: ta.lumpiness(c)),
    ("ts_cid_ce_20", lambda c: ta.ts_cid_ce_20(c)),
]


def section_e():
    head("E -- in-fork overlap, which Gate E's 687 comparators cannot see")
    say("    Spearman against the Category columns that read the same series'")
    say("    autocorrelation or memory, on four frames. Gate E itself is run")
    say("    by the launcher.")
    for nm, fn in NEIGHBOURS:
        row = []
        for fname, close in FRAMES.items():
            mine = tf_autocorr_1e_60(close)
            try:
                theirs = fn(close)
            except Exception as exc:
                row.append(f"{fname} ERR {exc!r}")
                continue
            if isinstance(theirs, pd.DataFrame):
                theirs = theirs.iloc[:, 0]
            m = mine.notna() & theirs.notna()
            if int(m.sum()) < 50 or theirs[m].nunique() < 2:
                row.append(f"{fname} n/a")
                continue
            rho = float(mine[m].corr(theirs[m], method="spearman"))
            row.append(f"{fname} {rho:+.4f}")
        say(f"    {nm:<16} " + "  ".join(row))
    say("")
    say("    and against ADX, the issue's top Gate E comparator (0.4279 on")
    say("    the prototype, n = 393,598), on the same synthetic frames")
    for fname, close in FRAMES.items():
        df = pd.DataFrame({"high": close * 1.01, "low": close * 0.99,
                           "close": close})
        adx = ta.adx(df["high"], df["low"], df["close"])["ADX_14"]
        mine = tf_autocorr_1e_60(close)
        m = mine.notna() & adx.notna()
        say(f"    {fname:<13} ADX_14 "
            f"{float(mine[m].corr(adx[m], method='spearman')):+.4f} "
            f"(n={int(m.sum())})")


# ----------------------------------------------------------------- F
def section_f():
    head("F -- what moves the column")
    say("    AR(1) log returns: phi, and the median / mean / sd it reads")
    for phi in (0.8, 0.6, 0.3, 0.0, -0.3, -0.6, -0.8):
        v = tf_autocorr_1e_60(ar1(phi=phi, seed=5)).dropna().to_numpy()
        say(f"    phi {phi:+.1f}  median {np.median(v):6.2f}  "
            f"mean {v.mean():7.4f}  sd {v.std():6.4f}  "
            f"=={NO_CROSSING} on {100.0 * (v == NO_CROSSING).mean():5.2f}%")
    say("")
    say("    trend strength: a drift added to an iid walk")
    for drift in (0.0, 0.002, 0.005, 0.01, 0.02):
        rng = np.random.default_rng(31)
        r = rng.normal(drift, 0.015, 1500)
        v = tf_autocorr_1e_60(Series(100 * np.exp(np.cumsum(r)))).dropna().to_numpy()
        say(f"    drift {drift:+.3f}/bar  median {np.median(v):6.2f}  "
            f"mean {v.mean():7.4f}  =={NO_CROSSING} on "
            f"{100.0 * (v == NO_CROSSING).mean():5.2f}%")
    say("")
    say("    a deterministic cosine in log price, by period")
    for period in (8, 15, 30, 60, 120, 400):
        v = tf_autocorr_1e_60(sine(period=period)).dropna().to_numpy()
        vals, counts = np.unique(v, return_counts=True)
        say(f"    period {period:>3}  values {dict(zip(vals.astype(int), counts))}")
    say("")
    say("    blind to AMPLITUDE: the same path with its log returns rescaled")
    base = walk()
    lg = np.log(base.to_numpy())
    for f in (0.5, 2.0, 10.0):
        other = Series(np.exp(lg[0] + f * (lg - lg[0])))
        eq, both, masks, mx = agree(tf_autocorr_1e_60(base),
                                    tf_autocorr_1e_60(other))
        say(f"    log returns x{f:<5g} bit-equal {eq}/{both} masks {masks}")
    say("")
    say("    NOT blind to a constant drift added to the log returns")
    for d in (0.001, 0.004, 0.02):
        other = Series(np.exp(lg + d * np.arange(lg.size)))
        eq, both, masks, mx = agree(tf_autocorr_1e_60(base),
                                    tf_autocorr_1e_60(other))
        say(f"    log drift +{d:<6g} bit-equal {eq}/{both} "
            f"max|diff| {mx:g}")
    say("")
    say("    NOT blind to the ORDER inside the window (it is an ACF)")
    rng = np.random.default_rng(13)
    moved_perm = moved_rev = 0
    n_w = 400
    for _ in range(n_w):
        x = np.cumsum(rng.normal(0.0, 0.01, LENGTH))
        a = _one_window(x)
        g = np.diff(x, prepend=x[0])
        b = _one_window(np.cumsum(rng.permutation(g)))
        c = _one_window(np.cumsum(g[::-1]))
        moved_perm += int(a != b)
        moved_rev += int(a != c)
    say(f"    {moved_perm}/{n_w} windows move under a permutation of the log "
        f"returns, {moved_rev}/{n_w} under a time reversal")
    say("")
    say("    it is a SLOW state: its own autocorrelation on the walk")
    v = tf_autocorr_1e_60(walk()).dropna()
    for lag in (1, 10, 30, 60, 120):
        say(f"    lag {lag:>3}  {float(v.autocorr(lag)):+.4f}")


# ----------------------------------------------------------------- G
def section_g():
    head("G -- the noise floor, and what it costs")
    say(f"    floor: window log-price sd > {NOISE_FLOOR:.3e} "
        f"(= {4096} eps)")
    say("")
    say("    on real-shaped frames it changes nothing")
    for name, close in FRAMES.items():
        eq, both, masks, mx = agree(tf_autocorr_1e_60(close), unguarded(close))
        hits, total = window_floor_hits(close)
        say(f"    {name:<13} guarded vs unguarded {eq}/{both} masks {masks}  "
            f"floor hits {hits}/{total}")
    say("")
    say("    what the floor BUYS: a one-tick-per-bar path at a high price,")
    say("    where the window's log prices vary only at rounding level")
    for price, tick in ((50.0, 0.01), (1e4, 0.01), (1e6, 0.01), (1e6, 1e-3),
                        (1e9, 0.01)):
        close = one_tick(price=price, tick=tick)
        g = np.diff(np.log(close.to_numpy()))
        col, raw = tf_autocorr_1e_60(close), unguarded(close)
        hits, total = window_floor_hits(close)
        gv = np.unique(col.dropna().to_numpy())
        rv = np.unique(raw.dropna().to_numpy())
        say(f"    price {price:<8g} tick {tick:<7g} mean log step "
            f"{g.mean():.3e}  floor hits {hits}/{total}")
        say(f"      guarded values {gv.astype(int) if gv.size else '(none)'}  "
            f"unguarded values {rv.astype(int) if rv.size else '(none)'}")
    say("")
    say("    what the floor REALLY buys: variation at ULP level, which is")
    say("    where the unguarded reading is ordinary-looking rather than")
    say("    absurd")
    flat = np.full(1500, 1e6)
    one = flat.copy()
    one[700:] = np.nextafter(1e6, np.inf)
    paths = {"one 1-ulp step at bar 700": Series(one),
             "1 ulp every bar": Series(_ulp_ladder(1e6, 1500)),
             "1 ulp every 10 bars": Series(_ulp_ladder(1e6, 1500, every=10))}
    for label, close in paths.items():
        col, raw = tf_autocorr_1e_60(close), unguarded(close)
        hits, total = window_floor_hits(close)
        gv = np.unique(col.dropna().to_numpy())
        rv = np.unique(raw.dropna().to_numpy())
        say(f"    {label:<26} floor hits {hits}/{total}")
        say(f"      guarded fired {fired(col)} values "
            f"{gv.astype(int) if gv.size else '(none)'}  |  unguarded fired "
            f"{fired(raw)} values {rv.astype(int) if rv.size else '(none)'}")

    say("")
    say("    an exactly FLAT window is NaN in both forms (variance is 0)")
    flat = Series(np.full(200, 100.0))
    say(f"    flat 200 bars: guarded fired {fired(tf_autocorr_1e_60(flat))}, "
        f"unguarded fired {fired(unguarded(flat))}")
    say("")
    say("    a flat run planted in a walk: how many bars the floor empties")
    for runlen in (LENGTH - 1, LENGTH, LENGTH + 1, LENGTH + 5):
        c = walk().to_numpy().copy()
        c[600:600 + runlen] = c[600]
        col = tf_autocorr_1e_60(Series(c))
        say(f"    run of {runlen:>3} identical closes -> "
            f"{int(col.isna().sum()) - (LENGTH - 1)} extra NaN bars")


# ----------------------------------------------------------------- H
def section_h():
    head("H -- bad data")
    base = walk()
    clean = tf_autocorr_1e_60(base)
    for label, bad in (("NaN", np.nan), ("zero", 0.0), ("negative", -5.0),
                       ("+inf", np.inf), ("subnormal", 1e-310)):
        c = base.copy()
        c.iloc[700] = bad
        col = tf_autocorr_1e_60(c)
        extra = int(col.isna().sum()) - int(clean.isna().sum())
        pre = clean.iloc[:700 - LENGTH]
        post = col.iloc[:700 - LENGTH]
        same = bool((pre.fillna(-1) == post.fillna(-1)).all())
        say(f"    close[700] = {label:<10} extra NaN bars {extra:>3}  "
            f"prefix unchanged {same}")
    say("")
    say("    a close PAIR whose ratio overflows")
    c = base.copy()
    c.iloc[700] = 1e-300
    c.iloc[701] = 1e50
    col = tf_autocorr_1e_60(c)
    say(f"    1e-300 then 1e50: extra NaN bars "
        f"{int(col.isna().sum()) - int(clean.isna().sum())}")
    say("")
    say("    short input")
    for n in (0, 1, 59, 60, 61):
        s = walk(n=max(n, 1)).iloc[:n] if n else Series([], dtype=float)
        out = tf_autocorr_1e_60(s)
        say(f"    {n:>3} closes -> "
            f"{'None' if out is None else f'fired {fired(out)}'}")
    say("")
    say("    the accessor, the Category entry and the export")
    df = pd.DataFrame({"close": walk().to_numpy()})
    acc = df.ta.tf_autocorr_1e_60()
    say(f"    df.ta.tf_autocorr_1e_60() -> {acc.name}, fired {fired(acc)}")
    say(f"    in Category['statistics']: "
        f"{'tf_autocorr_1e_60' in ta.Category['statistics']}")
    say(f"    ta.tf_autocorr_1e_60 is callable: {callable(ta.tf_autocorr_1e_60)}")


# ----------------------------------------------------------------- Z
def section_z():
    head("Z -- chunking and cost")
    close = walk(n=4000, seed=77)
    base = tf_autocorr_1e_60(close)
    for budget in (1, 64, 999, 10 ** 9):
        src = open(MODULE.__file__, encoding="utf-8").read()
        old = "CHUNK_VALUES = 1 << 21"
        mod = types.ModuleType("_tfac_chunk")
        mod.__file__ = MODULE.__file__
        exec(compile(src.replace(old, f"CHUNK_VALUES = {budget}"),
                     MODULE.__file__, "exec"), mod.__dict__)
        eq, both, masks, mx = agree(base, mod.tf_autocorr_1e_60(close))
        say(f"    CHUNK_VALUES={budget:<12} bit-equal {eq}/{both} "
            f"masks {masks}")
    say("")
    say("    peak memory and wall clock at n = 400,000")
    big = walk(n=400_000, seed=5)
    tracemalloc.start()
    t0 = time.perf_counter()
    col = tf_autocorr_1e_60(big)
    dt = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    say(f"    traced peak {peak / 1e6:.1f} MB, {dt * 1e3:.0f} ms, "
        f"fired {fired(col)}/400000")


def section_t():
    """Run this port's own test module in-process.

    The shell this file runs under cannot put a variable in front of a
    command, so `python docs/measure_tf_autocorr_1e_60.py --no-avx T` is how
    `tests/test_tf_autocorr_1e_60.py` gets exercised on the kernels a
    GitHub runner without AVX-512 would pick: the re-exec at the top of this
    file sets NPY_DISABLE_CPU_FEATURES before numpy is ever imported.
    """
    head("T -- tests/test_tf_autocorr_1e_60.py under the current dispatch")
    import pytest
    code = pytest.main(["-q", "tests/test_tf_autocorr_1e_60.py"])
    say(f"    pytest exit code {int(code)}")


SECTIONS = {"A": section_a, "B": section_b, "C": section_c, "D": section_d,
            "E": section_e, "F": section_f, "G": section_g, "H": section_h,
            "T": section_t, "Z": section_z}


def main(argv):
    wanted = [a.upper() for a in argv[1:]] or list(SECTIONS)
    say(f"numpy {np.__version__}  pandas {pd.__version__}")
    say(f"NPY_DISABLE_CPU_FEATURES="
        f"{os.environ.get('NPY_DISABLE_CPU_FEATURES', '(unset)')!r}")
    for key in wanted:
        if key not in SECTIONS:
            say(f"unknown section {key!r}; known: {sorted(SECTIONS)}")
            return 2
        SECTIONS[key]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
