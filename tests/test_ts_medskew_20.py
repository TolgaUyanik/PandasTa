# -*- coding: utf-8 -*-
"""TS-MEDSKEW-20: `ts_medskew_20`, the mean-minus-median of 20 returns over
their standard deviation (PandasTa issue #98).

    TS_MEDSKEW_20 = (mean(r) - median(r)) / sd(r),  20 simple returns,
                    sd with ddof=1

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **What the column OVERLAPS, which is the reason to read the receipt before
   using it.** This is a NONPARAMETRIC SKEWNESS reading -- Pearson's second
   coefficient without its factor 3 -- and the fork already ships two
   skewness columns. Measured here, on SYNTHETIC frames:

   * against the shipped `TS_ABOVE_MEAN_20` (issue #97, merged 2026-11-13):
     **-0.8885** on a walk, **-0.9025** heavy-tailed, -0.8854 / -0.8824 /
     -0.8894 / -0.8920 on ar1+ / ar1- / tick-rounded / trending. The sign is
     negative because
     that column reads skewness BACKWARDS. The REAL-frame number for this
     pair is the screen's pooled **0.8428** (2026-10-24,
     docs/TsMedskew20Measured.md §O), which is DISCLOSE_GAP and not STRUCK
     under `r3-perframe-0.90` -- but Gate E cannot see the pair at all,
     because its 687 comparators hold no pandas_ta port;
   * against the shipped `OSAP_RETSKEW_21`: +0.6485 on a walk, +0.8028
     heavy-tailed, +0.2000 on the two exponential frames;
   * against the windows' own textbook skewness, over 20,000 independent
     windows: **+0.8803**.

   It is NOT volatility (+0.0800 against the window's return sd), NOT
   direction (-0.1129 against its mean return) and NOT the price level
   (+0.0737).

2. **Gate A, and that the formula under test is the ISSUE's line.** tsfresh
   is NOT installed here and web access is unavailable, so "tsfresh (MIT)"
   is an attribution and not an oracle (`test_tsfresh_is_not_installed_here`
   records that). The named source function, `symmetry_looking`, does not
   contain this expression at all: it compares `|mean - median|` against
   `r * (max - min)` and returns a BOOLEAN. The continuous
   `(mean - median)/std` form is the ISSUE's own wording, and the two are
   different columns -- Spearman **-0.1942** between them, measured. What IS
   checkable is pinned:

   * the issue's formula applied window by window, sharing no code with the
     module -- max |difference| **2.2e-16** over 1,480 bars of each of nine
     frames, NaN masks identical;
   * a `math.fsum` scalar loop -- 1.7e-16 on three of them;
   * an EXACT rational oracle (`fractions.Fraction`), where the mean, the
     median and the variance are computed with no rounding at all -- 3.3e-16
     absolute, 8.5e-14 relative. On a path with `|mean| / sd` = 1e5, where
     the numerator's cancellation is worst, that becomes **4.3e-11**
     absolute and 1.3e-08 relative: the one place this column's arithmetic
     is visibly lossy, and it is pinned so it cannot get worse unnoticed;
   * a CLOSED FORM. One return of `a` among `n - 1` equal ones is exactly
     `sign(a) / sqrt(n)` for any `a` and any `n` (mean `a/n`, median 0, sd
     `a/sqrt(n)`), measured to 2.8e-16 at `n` = 3, 4, 20 and 60.

3. **The range, which is NOT [-1, 1].** `|mean - median| <= sd_pop` is a
   theorem (the median minimises `E|x - a|`, then Jensen), and this column
   divides by the ddof=1 sd, so `|TS_MEDSKEW| <= sqrt((n-1)/n)` = **0.9747**
   at `length` 20. The largest value ANY window built here reaches is
   **0.881631**, by `11` equal low returns and `9` equal high ones -- hit
   both by construction and by the two-point frame, and not beaten by
   1.2 million random windows from six families. The gap between 0.8816 and
   the bound is not closed analytically; the test asserts the THEOREM.

4. **Gate B, by mutant, and the honest account of what the blind sweep
   cannot do here.** Six mutants, each `importlib`-read and `exec`'d in
   memory. Five are live and caught 15-37 of 37 offsets, where the real
   module leaks **0 of 37** on each of three frames and at `length` 5, 60
   and 250.
   ⚠ The sixth is the interesting one. Rolling the floor's `hi`/`lo` by one
   window makes bar T's NaN mask read window T+1 -- a real look-ahead -- and
   on a clean frame it moves exactly ONE bar, the LAST one, which is an
   `np.roll` WRAP and not a look-ahead at all. It scores 0 of 37. Two
   designed frames separate the two halves of the guard: with patches of
   CONSTANT-RATE returns, where the floor is the only thing emptying the
   interior windows, the mutant is caught **35 of 37**; with patches of
   EXACTLY zero returns, where the sd is 0 and the `isfinite` backstop
   empties them whatever the floor says, it is caught **0 of 37**. The real
   module leaks 0 of 37 on both.

5. **Gate D, and that it is stronger than a price rescale.** x8 and x64 are
   bit-identical on 1,480 of 1,480 bars of each of nine frames (the return
   is a price RATIO), and at `length` 3/5/60/250. x10, x3.7 and x0.1 are NOT
   bit-identical by construction and agree to **1.2e-13**, masks exact. The
   statistic is invariant to any affine map of the RETURNS with a positive
   slope -- `r x 2`, `r x 0.5`, `r + 0.004` all agree to 4.0e-14 -- which is
   why it is neither a volatility nor a direction column.
   ⚠ That invariance is the STATISTIC's and not the reported MASK's: the
   floor is scale-invariant but NOT shift-invariant, and a frame whose
   returns span only their own rounding fires on 576 of 600 bars at returns
   of 1e-6 and on **0** after a 0.004 drift.

6. **The guards, each with what it costs.** The RELATIVE floor
   (`spread > 4096 eps * max|r|`) costs 0 body bars on each of nine clean
   frames and empties a constant-return ladder entirely, where the unguarded
   spelling reports 280 windows of pure rounding spanning [-0.33, +0.30]. An
   ABSOLUTE `4096 eps` floor -- the sibling ports' -- would also empty a
   quiet-but-honest frame that this one reports 580 bars of. The per-return
   magnitude bound keeps the squared deviations from overflowing. The
   `isfinite` backstop has NO witness: over 14 frames there is not one bar
   where the floor reports and the value is not finite, and the smallest
   non-zero return a close pair can produce is an ulp of 1.0 -- 2.220e-16
   upwards, **1.110e-16** downwards -- which puts the smallest
   squared-deviation sum the floor can admit at 2.5e-57 against a smallest
   subnormal of 4.9e-324, so the sd cannot underflow.

7. **That the window arithmetic is LOCAL, which the prototype's is not.**
   Every window is reduced from its own 20 values, so a planted return of
   1e+2 .. 1e+300 leaves every later bar within **3.4e-14** of the unspiked
   frame. The screen prototype's `rolling.mean()/.std()` are ONLINE
   accumulators and the same spike moves its later bars by **0.40**.

8. **That it IS the screen prototype otherwise**: identical NaN masks on
   nine frames, max |difference| 5.2e-15, Spearman 1.000000 (0.999696 on the
   two-point frame, where the column is heavily tied). The two part company
   only on the guards -- a constant-return ladder, which the prototype reads
   280 windows of.

Numbers come from `docs/measure_ts_medskew_20.py`; the receipt is
`docs/TsMedskew20Measured.md`. Gate C on real data and Gate E are OWED: the
launcher runs `gate_e_overlap.py` after this session, and
`test_the_gate_e_row_is_still_owed` is the receipt session's cue.
Counts that depend on the last bits of a generated frame carry a band or a
tolerance; the structural facts are pinned exactly.
"""
import importlib
import math
import types
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.osap_retskew_21 import osap_retskew_21
from pandas_ta.statistics.ts_above_mean_20 import ts_above_mean_20
from pandas_ta.statistics.ts_medskew_20 import NOISE_FACTOR, ts_medskew_20

LENGTH = 20

_REAL = importlib.import_module("pandas_ta.statistics.ts_medskew_20")


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _window_frame(rs):
    """`len(rs) + 1` closes whose returns are `rs`."""
    body = np.cumprod(1.0 + np.asarray(rs, dtype=float))
    return Series(100.0 * np.concatenate([[1.0], body]))


def _ar1(n=1500, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=1500, seed=9):
    return _walk(n, seed, sigma=0.004, drift=0.01)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A mathematically CONSTANT return, which float64 reproduces only to
    rounding."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _patches(n=1500, seed=23, sigma=0.015, patch=25, every=40, rate=0.01):
    """A walk interrupted every `every` bars by a `patch`-bar stretch of
    CONSTANT `rate` returns. At `rate` != 0 the floor is what empties those
    interior windows and the value behind them is FINITE; at `rate` = 0 the
    sd is 0 and the `isfinite` backstop empties them instead. The two cases
    catch the floor-index mutant and do not, respectively."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    for start in range(60, n - patch, every):
        r[start:start + patch] = rate
    return _from_returns(r)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5, seed=17),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
}
#: Every frame is 1,500 bars and the first value lands at bar `length`.
FIRED = 1500 - LENGTH
#: `|mean - median| <= sd_pop` and this column divides by the ddof=1 sd.
BOUND = math.sqrt((LENGTH - 1) / LENGTH)       # 0.974679
#: 11 equal low returns and 9 equal high ones -- the largest value any
#: window built in this file or in docs/measure_ts_medskew_20.py reaches.
ATTAINED = 0.881631


def _returns_of(close):
    return (close / close.shift(1) - 1.0).to_numpy()


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0.0
    return masks, int(m.sum()), float((a[m] - b[m]).abs().max())


def _shared(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return 0, 0.0
    return int(m.sum()), float((a[m] - b[m]).abs().max())


# ------------------------------------------------------------ the oracles


def _source_windowed(close, length=LENGTH):
    """The issue's formula applied one window at a time. Shares no code with
    the module: a Python loop, `np.mean`, `np.median`, `np.std(ddof=1)`."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        s = np.std(x, ddof=1)
        if s == 0.0:
            continue
        out[t] = (np.mean(x) - np.median(x)) / s
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH):
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        m = math.fsum(x) / length
        s = math.sqrt(math.fsum((v - m) ** 2 for v in x) / (length - 1))
        if s == 0.0:
            continue
        y = sorted(x)
        med = (y[length // 2] if length % 2
               else 0.5 * (y[length // 2 - 1] + y[length // 2]))
        out[t] = (m - med) / s
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH):
    """Every float return is a rational, so the mean, the median and the
    VARIANCE are exact; only the square root and the final division round."""
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        q = [Fraction(v) for v in x]
        m = sum(q) / length
        var = sum((v - m) ** 2 for v in q) / (length - 1)
        if var == 0:
            continue
        y = sorted(q)
        med = (y[length // 2] if length % 2
               else (y[length // 2 - 1] + y[length // 2]) / 2)
        out[t] = float(m - med) / math.sqrt(float(var))
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_medskew_20`,
    retyped: `sdiv(mean(r, 20) - r.rolling(20).median(), std(r, 20))` with
    `mean`/`std` the ONLINE `rolling.mean()`/`rolling.std()` and
    `sdiv = _fin(a / b)`. No guards of any kind."""
    r = close / close.shift(1) - 1.0
    num = r.rolling(length).mean() - r.rolling(length).median()
    den = r.rolling(length).std()
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    return out.where(np.isfinite(out))


def _unguarded(close, length=LENGTH):
    """This module without its floor and without its backstop."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _absolute_floor(close, length=LENGTH):
    """The floor the sibling tsfresh ports use -- `4096 eps` ABSOLUTE on the
    window's return range -- instead of this module's relative one."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = np.where(
            W.max(axis=1) - W.min(axis=1) > NOISE_FACTOR,
            (mean - np.median(W, axis=1)) / sd, np.nan)
    return Series(out, index=close.index)


# --------------------------------------------------- Gate A: the source


def test_tsfresh_is_not_installed_here():
    """The attribution is an attribution. If tsfresh ever IS installed, this
    fails and whoever sees it should compare against
    `feature_calculators.symmetry_looking` directly -- and will find, per
    `test_the_named_source_function_is_a_different_column`, that the issue's
    continuous form is not what that function computes."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfresh")


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_module_matches_the_source_applied_window_by_window(frame):
    """Gate A1: NaN masks identical and 1,480 of 1,480 bars within 2.2e-16
    on each of nine frames."""
    close = FRAMES[frame]()
    masks, shared, mx = _agree(ts_medskew_20(close), _source_windowed(close))
    assert masks and shared == FIRED, (frame, shared)
    assert mx < 1e-14, (frame, mx)


@pytest.mark.parametrize("frame", ["walk", "heavy-tailed", "right-skewed"])
def test_the_module_matches_an_fsum_scalar_loop(frame):
    """Gate A2: both sums taken by `math.fsum`, which is exact up to one
    rounding, and the median spelt out on a sorted copy."""
    close = FRAMES[frame]()
    masks, shared, mx = _agree(ts_medskew_20(close), _fsum_windowed(close))
    assert masks and shared == FIRED, (frame, shared)
    assert mx < 1e-14, (frame, mx)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "two-point",
                                   "right-skewed"])
def test_the_exact_rational_oracle_agrees(frame):
    """Gate A3. The mean, the median and the variance are computed over
    `fractions.Fraction` with no rounding at all. Measured max |difference|
    3.33e-16 absolute (two-point), 8.520e-14 relative (tick-rounded)."""
    close = FRAMES[frame]()
    a, b = ts_medskew_20(close), _exact_windowed(close)
    masks, shared, mx = _agree(a, b)
    assert masks and shared == FIRED, (frame, shared)
    assert mx < 1e-14, (frame, mx)


def test_the_exact_oracle_on_the_worst_cancellation_this_file_can_build():
    """Gate A3b, and the one place the arithmetic is visibly lossy: returns
    of 0.5 with an sd of 0.5e-5, i.e. `|mean| / sd` = 1e5, so `mean - median`
    cancels five digits. Measured 4.3e-11 absolute and 1.3e-08 relative --
    a factor of 3.9e+05 on an ordinary frame's 1.11e-16 -- between five and
    six orders of magnitude -- and still ten orders below the column's own
    [-0.88, +0.88] range (0.881631 / 4.308e-11 = 2.0e+10). Pinned so it
    cannot get worse unnoticed."""
    rng = np.random.default_rng(99)
    close = _from_returns(0.5 + 0.5e-5 * rng.standard_normal(600))
    a, b = ts_medskew_20(close), _exact_windowed(close)
    masks, shared, mx = _agree(a, b)
    assert masks and shared == 600 - LENGTH, shared
    assert mx < 1e-9, mx


@pytest.mark.parametrize("n", [3, 4, 20, 60])
@pytest.mark.parametrize("a", [0.5, 0.001, -0.5])
def test_one_odd_return_among_equal_ones_is_exactly_one_over_root_n(n, a):
    """Gate A4, a CLOSED FORM rather than a recomputation: `n - 1` equal
    returns and one of `a` give mean `a/n`, median 0 and ddof=1 sd
    `|a|/sqrt(n)`, so the column is `sign(a)/sqrt(n)` whatever `a` is.
    Measured to 2.8e-16."""
    got = float(ts_medskew_20(_window_frame([0.0] * (n - 1) + [a]),
                              length=n).iloc[-1])
    assert abs(got - math.copysign(1.0 / math.sqrt(n), a)) < 1e-14


@pytest.mark.parametrize("returns", [
    [0.01, -0.01] * 10,
    [0.0] * 10 + [0.01] * 10,
    [0.001 * k for k in range(1, 21)],
])
def test_a_window_whose_mean_and_median_agree_reads_zero(returns):
    """The numerator is a difference of two centre readings, so a symmetric
    window reads 0 -- to 2.2e-14 here, because the closes are rebuilt from a
    cumulative product and the returns are not exactly the ones asked for."""
    assert abs(float(ts_medskew_20(_window_frame(returns)).iloc[-1])) < 1e-12


def test_twenty_identical_returns_are_refused_not_read_as_zero():
    """A window with no dispersion has no statistic: 0/0, not 0."""
    assert bool(np.isnan(ts_medskew_20(Series(100.0 * np.ones(21)))
                         .iloc[-1]))


# -------------------------------------------------- Gate A: the readings


def _log_return_variant(close, length=LENGTH):
    r = np.log(close.to_numpy()) - np.log(close.shift(1).to_numpy())
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _ddof0_variant(close, length=LENGTH):
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / length)
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _on_closes_variant(close, length=LENGTH):
    c = close.to_numpy(dtype=float)
    W = sliding_window_view(c, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    out = np.full(c.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _range_variant(close, length=LENGTH):
    """tsfresh's LITERAL `symmetry_looking` quantity: `|mean - median|` over
    `max - min`, which that function compares against `r * (max - min)`."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (np.abs(mean - np.median(W, axis=1))
                            / (W.max(axis=1) - W.min(axis=1)))
    return Series(out, index=close.index)


def test_the_named_source_function_is_a_different_column():
    """⚠ The attribution names `symmetry_looking`, and that function does
    NOT compute this. It compares `|mean - median|` against
    `r * (max - min)` and returns a boolean; the continuous
    `(mean - median)/std` form is issue #98's own wording. Dividing by the
    RANGE instead, and taking the absolute value as that function does,
    gives Spearman -0.1942 against this column on a walk -- a different
    question, not a rescaling."""
    walk = _walk()
    rho = _spearman(ts_medskew_20(walk), _range_variant(walk))
    assert -0.30 < rho < -0.10, rho


def test_log_returns_are_a_near_copy_but_not_this_column():
    """Spearman 0.999961 and max |difference| 0.0109 on a walk: the choice
    is almost invisible to a rank miner and visible to a threshold rule."""
    walk = _walk()
    other = _log_return_variant(walk)
    assert _spearman(ts_medskew_20(walk), other) > 0.999
    shared, mx = _shared(ts_medskew_20(walk), other)
    assert shared == FIRED and 0.005 < mx < 0.05, (shared, mx)


def test_ddof_zero_is_an_exact_rescaling_so_a_rank_miner_cannot_see_it():
    """The population sd is `sqrt((n-1)/n)` times this one, a CONSTANT at a
    fixed `length`, so the ddof choice moves the level and not the order:
    the ratio's min and max are both sqrt(20/19) to 1e-12."""
    walk = _walk()
    base, other = ts_medskew_20(walk), _ddof0_variant(walk)
    m = base.notna() & other.notna()
    ratio = (other[m] / base[m])
    want = math.sqrt(LENGTH / (LENGTH - 1))
    assert abs(float(ratio.min()) - want) < 1e-9
    assert abs(float(ratio.max()) - want) < 1e-9
    assert _spearman(base, other) > 0.9999999


def test_twenty_closes_instead_of_twenty_returns_is_a_different_column():
    """The off-by-one a reader makes, priced so it is not re-argued:
    Spearman 0.918816, max |difference| 0.3371."""
    walk = _walk()
    other = ts_medskew_20(walk, length=LENGTH - 1)
    rho = _spearman(ts_medskew_20(walk), other)
    assert 0.88 < rho < 0.95, rho


def test_the_statistic_of_the_closes_is_a_different_question_entirely():
    """Spearman 0.123198: the same formula on the price LEVEL reads the
    shape of a trend, not of a return distribution."""
    walk = _walk()
    assert abs(_spearman(ts_medskew_20(walk), _on_closes_variant(walk))) < 0.3


def test_the_pearson_second_coefficient_is_the_same_column_times_three():
    """`3 (mean - median)/sd` is the textbook spelling; the issue asks for
    the unmultiplied one. A positive rescaling is rank-identical by
    construction -- asserting the Spearman would pin nothing -- so what is
    pinned is the size of the gap a THRESHOLD rule would see: exactly
    `2 * max|value|`, measured 0.8421 on this walk."""
    walk = _walk()
    base = ts_medskew_20(walk)
    shared, mx = _shared(base, base * 3.0)
    assert shared == FIRED
    assert abs(mx - 0.8421) < 1e-3, mx


def test_throwing_the_sign_away_is_a_different_column():
    """The third of the six open readings, priced rather than argued:
    `|mean - median|`
    over the SAME sd keeps the denominator and loses the direction, giving
    Spearman -0.2068 against this column on a walk. It is bit-equal on the
    642 of 1,480 bars where this column is non-negative -- so that count is
    also how often the column is non-negative on this walk, which is the
    measurement worth having."""
    walk = _walk()
    base = ts_medskew_20(walk)
    other = base.abs()
    rho = _spearman(base, other)
    assert -0.30 < rho < -0.10, rho
    m = base.notna()
    assert 600 < int((base[m] == other[m]).sum()) < 700


# --------------------------------------------------------------- the range


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_column_stays_inside_the_proven_bound(frame):
    """`|mean - median| <= sd_pop` (the median minimises `E|x - a|`, then
    Jensen), and this column divides by the ddof=1 sd, so
    `|value| <= sqrt((n-1)/n)` = 0.9747 at `length` 20."""
    col = ts_medskew_20(FRAMES[frame]()).dropna()
    assert float(col.abs().max()) <= BOUND, float(col.abs().max())


def test_the_largest_value_reached_is_eleven_lows_and_nine_highs():
    """0.881631, hit by construction and by the two-point frame, against the
    0.974679 bound. The gap is NOT closed: 1.2 million random windows from
    six families (docs/measure_ts_medskew_20.py, A6) did not beat it
    either."""
    best = max((abs(float(ts_medskew_20(
        _window_frame([0.0] * k + [0.01] * (LENGTH - k))).iloc[-1])), k)
        for k in range(1, LENGTH))
    assert best[1] == 11
    assert abs(best[0] - ATTAINED) < 1e-5, best
    assert abs(float(ts_medskew_20(_two_point()).abs().max()) - ATTAINED) \
        < 1e-5


def test_a_window_split_ten_ten_reads_zero_not_the_maximum():
    """The neighbour of that maximum, pinned because it is the surprise: at
    `k` = 10 the median sits BETWEEN the two levels and the column is 0."""
    col = ts_medskew_20(_window_frame([0.0] * 10 + [0.01] * 10))
    assert abs(float(col.iloc[-1])) < 1e-12


# ------------------------------------------------------ Gate B: the mutants


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(reported, value, np.nan)",
    "    out[length - 3:c.size - 2] = np.where(reported, value, np.nan)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(reported, value, np.nan)",
    "    out[:windows.shape[0]] = np.where(reported, value, np.nan)")
FORWARD_WINDOW = (
    "    windows = sliding_window_view(r, length)",
    "    windows = sliding_window_view(np.roll(r, -1), length)")
FORWARD_RETURN = (
    "        r = (px / px.shift(1) - 1.0).to_numpy()",
    "        r = (px.shift(-1) / px - 1.0).to_numpy()")
FUTURE_MEDIAN = (
    "        .rolling(length, min_periods=length).median().to_numpy()[length - 1:]",
    "        .rolling(length, min_periods=length).median()"
    ".to_numpy()[length - 1:]\n    median = np.roll(median, -1)")
#: The floor's own index -- the one the blind sweep cannot reach on a clean
#: frame, because `reported` is True on every body window there. It IS a
#: look-ahead (bar T's mask would read window T+1), and it is caught by a
#: designed frame instead -- see the two `_patches` tests below.
SHIFTED_FLOOR = (
    "    hi, lo = windows.max(axis=1), windows.min(axis=1)",
    "    hi, lo = (np.roll(windows.max(axis=1), -1),\n"
    "              np.roll(windows.min(axis=1), -1))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_window": FORWARD_WINDOW,
    "forward_return": FORWARD_RETURN,
    "future_median": FUTURE_MEDIAN,
}
OFFSETS = range(40, 1500, 40)  # 37 offsets
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 37 offsets, at the
#: default `length` -- BANDS, not targets. `future_median` is low because
#: rolling the median by one window changes a bar only when the two windows'
#: medians differ enough to move the bar's value, which a splice far from the
#: bar need not do.
CAUGHT = {
    "back_date_two": (30, 37),
    "back_date_full": (30, 37),
    "forward_window": (30, 37),
    "forward_return": (30, 37),
    "future_median": (8, 37),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_medskew_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, **kwargs):
    """Offsets J at which replacing every close from bar J on moves a bar
    BEFORE J -- which a causal column cannot do."""
    base = fn(close, **kwargs)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p, **kwargs)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_the_real_module_leaks_nothing_under_the_mutant_sweep(frame):
    """Gate B's premise: replacing every close from bar J on changes no bar
    before J. 0 of 37 offsets on each of three frames."""
    close, other = PAIRS[frame]
    assert _caught(ts_medskew_20, close, other) == []


@pytest.mark.parametrize("length", [5, 60, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(ts_medskew_20, close, other, length=length) == []
    assert int(ts_medskew_20(close, length=length).notna()
               .to_numpy().argmax()) == length


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column -- otherwise the test proves
    nothing -- and be caught by the blind sweep within its measured band."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_medskew_20(close).equals(ts_medskew_20(close))
    hits = _caught(mod.ts_medskew_20, close, other)
    lo, hi = CAUGHT[mutant]
    assert lo <= len(hits) <= hi, (mutant, frame, len(hits))


def test_the_floor_index_mutant_is_live_but_invisible_to_the_blind_sweep():
    """The sixth mutant, and the honest account of what Gate B's sweep cannot
    do here. Shifting `hi`/`lo` by one window makes bar T's NaN mask read
    window T+1 -- a look-ahead. On a clean frame it is LIVE and moves exactly
    ONE bar, the LAST one, pinned here as a set so nothing can hide in it:
    that bar is an `np.roll` WRAP (the rolled extrema of window 0, which hold
    the undefined first return, land on the last window) and not a
    look-ahead. The sweep cannot see it, because `_caught` only inspects bars
    BEFORE an offset and the offsets stop at 1,480. So it scores 0 of 37 and
    proves nothing. The next two tests are what catch it."""
    mod = _load_mutant(*SHIFTED_FLOOR)
    for frame, (close, other) in sorted(PAIRS.items()):
        real, mutant = ts_medskew_20(close), mod.ts_medskew_20(close)
        assert not mutant.equals(real), frame          # live
        moved = set(np.flatnonzero(
            (real.isna() != mutant.isna()).to_numpy()
            | (real.fillna(-99.0) != mutant.fillna(-99.0)).to_numpy()).tolist())
        assert moved == {len(close) - 1}, (frame, sorted(moved))
        assert real.notna().iloc[-1] and bool(np.isnan(mutant.iloc[-1]))
        assert _caught(mod.ts_medskew_20, close, other) == [], frame


def test_the_designed_probe_catches_the_floor_index_mutant():
    """A frame where the FLOOR is what empties the interior windows -- a walk
    interrupted every 40 bars by 25 bars of a constant 1% return, 216
    interior empties measured, 213 of which the unguarded spelling reports a
    finite value on. There the shifted mask is inside the sweep's reach: the
    real module still leaks 0 of 37 and the mutant is caught 35."""
    close, other = _patches(), _patches(seed=24)
    col = ts_medskew_20(close)
    interior = int(col.iloc[LENGTH:].isna().sum())
    assert 150 <= interior <= 300, interior
    un = _unguarded(close)
    finite = int(un.iloc[LENGTH:][col.iloc[LENGTH:].isna()].notna().sum())
    assert finite >= 150, finite
    assert _caught(ts_medskew_20, close, other) == []
    mod = _load_mutant(*SHIFTED_FLOOR)
    assert len(_caught(mod.ts_medskew_20, close, other)) >= 20


def test_exactly_zero_patches_do_not_catch_it_and_why():
    """The other half of the same guard, and the reason the probe above uses
    a CONSTANT RATE rather than zero. With exactly-zero returns the window's
    sd is 0, so the value is 0/0 and the `isfinite` backstop empties the bar
    whatever the floor says -- the mutant's shifted mask changes nothing and
    it is caught 0 of 37. A probe built the obvious way would have passed
    this module without testing the floor at all."""
    close, other = _patches(rate=0.0), _patches(seed=24, rate=0.0)
    col = ts_medskew_20(close)
    un = _unguarded(close)
    assert int(col.iloc[LENGTH:].isna().sum()) >= 150
    assert int(un.iloc[LENGTH:][col.iloc[LENGTH:].isna()].notna().sum()) == 0
    mod = _load_mutant(*SHIFTED_FLOOR)
    assert _caught(mod.ts_medskew_20, close, other) == []


def test_the_first_fired_bar_is_length_not_length_minus_one():
    """20 returns need 21 closes, so bar 19's window holds the undefined
    first return. The prototype agrees here -- unlike `ts_above_mean_20`'s,
    whose unguarded mean lets it report at bar 19."""
    col = ts_medskew_20(_walk())
    assert int(col.notna().to_numpy().argmax()) == LENGTH
    assert bool(np.isnan(col.iloc[LENGTH - 1]))
    assert bool(np.isnan(_prototype(_walk()).iloc[LENGTH - 1]))


# ------------------------------------------------------- Gate C / Gate D


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_c_the_column_fires_and_varies(frame):
    """0 < fires < n, more than one distinct value, and not everything zero.

    SYNTHETIC. The real-data counts come from Gate E's run and are OWED --
    see `test_the_gate_e_row_is_still_owed`."""
    col = ts_medskew_20(FRAMES[frame]())
    v = col.dropna()
    assert int(col.notna().sum()) == FIRED
    assert 0 < FIRED < len(col)
    assert int(v.nunique()) > 100, frame
    assert int((v != 0).sum()) >= FIRED - 5, frame


@pytest.mark.parametrize("frame", [_flat(), _ladder()])
def test_a_frame_with_no_dispersion_fires_on_nothing(frame):
    assert int(ts_medskew_20(frame).notna().sum()) == 0


def test_an_exact_zero_is_reachable_on_a_two_point_frame():
    """0.0 is a legitimate reading (mean = median) and not a degenerate
    window: a two-point frame whose window holds ten of each value produces
    it exactly, twice in 1,480 bars here. On a walk it never happens."""
    tp = ts_medskew_20(_two_point()).dropna()
    assert int((tp == 0.0).sum()) >= 1
    assert int((ts_medskew_20(_walk()).dropna() == 0.0).sum()) == 0


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_x8_and_x64_are_bit_identical(frame, k):
    """Gate D: every input is a price RATIO and `8a / 8b` is the same double
    as `a / b`, so a power-of-two rescale cancels exactly."""
    close = FRAMES[frame]()
    base, other = ts_medskew_20(close), ts_medskew_20(close * k)
    assert bool((base.isna() == other.isna()).all())
    m = base.notna()
    assert int(m.sum()) == FIRED
    assert bool((base[m] == other[m]).all()), (frame, k)


@pytest.mark.parametrize("length", [3, 5, 60, 250])
def test_scale_x8_is_bit_identical_at_other_lengths(length):
    close = _walk()
    base, other = (ts_medskew_20(close, length=length),
                   ts_medskew_20(close * 8.0, length=length))
    assert bool((base.isna() == other.isna()).all())
    m = base.notna()
    assert int(m.sum()) == 1500 - length
    assert bool((base[m] == other[m]).all()), length


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("k", [10.0, 3.7, 0.1])
def test_scale_x10_and_x3_7_agree_within_a_tolerance(frame, k):
    """NOT bit-identical by construction -- they perturb the returns in
    their last bits. The NaN masks are asserted exactly, the values to
    1.2e-13 (measured max 1.13e-13), and the rank correlation separately,
    because on the two-point frame the column is heavily tied and a last-bit
    perturbation reorders ties (Spearman 0.9841 there against 1.000000
    everywhere else)."""
    close = FRAMES[frame]()
    base, other = ts_medskew_20(close), ts_medskew_20(close * k)
    assert bool((base.isna() == other.isna()).all())
    shared, mx = _shared(base, other)
    assert shared == FIRED and mx < 1e-12, (frame, k, mx)
    assert _spearman(base, other) > 0.95, (frame, k)


@pytest.mark.parametrize("label,make", [
    ("r x 2", lambda r: 2 * r),
    ("r x 0.5", lambda r: 0.5 * r),
    ("r + 0.004", lambda r: r + 0.004),
])
def test_scale_an_affine_map_of_the_returns_leaves_it_where_it_was(label,
                                                                   make):
    """Stronger than a price rescale, and the reason this is neither a
    volatility nor a direction column: both the numerator and the sd scale
    with the returns, and a shift cancels in `mean - median`. Measured to
    4.0e-14."""
    rng = np.random.default_rng(11)
    r = rng.normal(0.0, 0.015, 1500)
    base = ts_medskew_20(_from_returns(r))
    other = ts_medskew_20(_from_returns(make(r)))
    assert bool((base.isna() == other.isna()).all())
    shared, mx = _shared(base, other)
    assert shared == FIRED and mx < 1e-12, (label, mx)


def test_that_invariance_is_the_statistics_and_not_the_reported_masks():
    """⚠ The floor is scale-invariant but NOT shift-invariant: `hi - lo` is
    unchanged by `r -> r + c` while `4096 eps * max|r|` grows with `c`. A
    frame whose returns span only the closes' own rounding (4.4e-16) fires
    on 576 of 600 bars at returns of 1e-6, where the floor is 9.1e-19, and
    on NONE of them after a 0.004 drift, where it is 3.6e-15."""
    rng = np.random.default_rng(3)
    tiny = 1e-6 + 1e-21 * rng.standard_normal(600)
    assert 500 <= int(ts_medskew_20(_from_returns(tiny)).notna().sum()) <= 580
    assert int(ts_medskew_20(_from_returns(tiny + 0.004)).notna().sum()) == 0


# ------------------------------------------------------------- the guards


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_floor_costs_no_body_bar_on_a_clean_frame(frame):
    close = FRAMES[frame]()
    guarded, unguarded = ts_medskew_20(close), _unguarded(close)
    assert int((guarded.isna() & unguarded.notna()).iloc[LENGTH:].sum()) == 0


def test_the_floor_empties_a_constant_return_ladder_the_unguarded_one_does_not():
    """A 1%-a-bar geometric ladder is a mathematically CONSTANT return that
    float64 reproduces only to rounding. The unguarded spelling reports 280
    windows of pure rounding there, spanning [-0.33, +0.30] -- values
    indistinguishable from a real reading. This module reports none."""
    lad = _ladder()
    assert int(ts_medskew_20(lad).notna().sum()) == 0
    u = _unguarded(lad).dropna()
    assert int(u.size) >= 100
    assert float(u.abs().max()) > 0.05


def test_the_floor_is_relative_and_an_absolute_one_would_be_wrong_here():
    """Returns of 1e-6 spread over 1e-13 are quiet but HONEST -- the median
    window spread is 3.648e-13 against the 4.441e-16 the closes' own
    rounding produces at this return level (Gate D4), a factor of 8.2e+02,
    and the module agrees with the exact rational oracle to 1.3e-09 there.
    Both figures are printed by `docs/measure_ts_medskew_20.py` G3. The
    relative floor
    reports on all 580 body bars; the sibling ports' ABSOLUTE `4096 eps`
    floor reports on none."""
    rng = np.random.default_rng(3)
    quiet = _from_returns(1e-6 + 1e-13 * rng.standard_normal(600))
    assert int(ts_medskew_20(quiet).notna().sum()) == 600 - LENGTH
    assert int(_absolute_floor(quiet).notna().sum()) == 0
    masks, shared, mx = _agree(ts_medskew_20(quiet), _exact_windowed(quiet))
    assert masks and shared == 600 - LENGTH
    assert mx < 1e-7, mx


def test_the_relative_floor_still_refuses_the_mirror_case():
    """Returns of 0.5 spread over 1e-14 are rounding, not data, and both
    floors refuse them."""
    rng = np.random.default_rng(4)
    loud = _from_returns(0.5 + 1e-14 * rng.standard_normal(600))
    assert int(ts_medskew_20(loud).notna().sum()) == 0
    assert int(_absolute_floor(loud).notna().sum()) == 0


def test_the_isfinite_backstop_has_no_witness_and_the_reason_is_arithmetic():
    """Labelled honestly: over every frame this file builds there is not one
    bar where the floor reports and the value is not finite. The reason is
    not luck -- the smallest non-zero return a close pair can produce is an
    ulp of 1.0, 1.110e-16 downwards (2.220e-16 upwards), and the floor only
    admits a window whose spread `s` clears `4096 eps * max|r|`. The two
    extremes of such a window straddle its mean, so one of them is at least
    `s/2` away from it and the squared-deviation SUM is at least `(s/2)**2`
    -- **2.5e-57** at the smallest admissible `s`, against a smallest
    subnormal of 4.9e-324. The backstop costs one pass over `(rows,)` and
    stays, because it is also what empties the exactly-zero windows of
    `test_exactly_zero_patches_do_not_catch_it_and_why`.

    The 14 frames are the nine of `FRAMES`, flat, the ladder, both patch
    frames and the quiet 1e-6 frame -- the same 14 `docs/TsMedskew20Measured.md`
    §G4 sweeps."""
    rmin = min(abs(float(np.nextafter(1.0, 2.0) - 1.0)),
               abs(float(np.nextafter(1.0, 0.0) - 1.0)))
    assert ((NOISE_FACTOR * rmin) / 2) ** 2 > 1e-300
    probes = [f() for f in FRAMES.values()]
    probes += [_flat(), _ladder(), _patches(), _patches(rate=0.0),
               _from_returns(1e-6 + 1e-13
                             * np.random.default_rng(3).standard_normal(600))]
    # Tied to `FRAMES`, so adding a frame without updating the "14 frames"
    # in this file's docstring and in the receipt's §G4 fails here.
    assert len(probes) == len(FRAMES) + 5 == 14
    total = 0
    for close in probes:
        r = _returns_of(close)
        W = sliding_window_view(r, LENGTH)
        mean = W.sum(axis=1) / LENGTH
        sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (LENGTH - 1))
        hi, lo = W.max(axis=1), W.min(axis=1)
        rep = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)
        with np.errstate(invalid="ignore", divide="ignore"):
            v = (mean - np.median(W, axis=1)) / sd
        total += int((rep & ~np.isfinite(v)).sum())
    assert total == 0


@pytest.mark.parametrize("bar,emptied", [(0, 1), (1, 2), (19, 20), (200, 21),
                                         (398, 2), (399, 1)])
def test_a_non_finite_return_empties_its_windows(bar, emptied):
    """A bad close spoils TWO returns, so it empties the `length + 1` = 21
    windows it sits in -- fewer near either end -- and nothing earlier."""
    close = _walk(400)
    base = ts_medskew_20(close)
    holed = close.copy()
    holed.iloc[bar] = np.nan
    col = ts_medskew_20(holed)
    moved = np.flatnonzero((base.isna() != col.isna()).to_numpy())
    assert moved.size == emptied, (bar, moved.size)
    assert int((moved < bar).sum()) == 0


@pytest.mark.parametrize("value", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_close_that_has_no_return_is_treated_as_missing(value):
    """NaN, infinite, zero, negative and subnormal closes are all bad data in
    the same way: 359 of 400 bars fire, which is 400 - 20 warm-up - 21."""
    close = _walk(400)
    close.iloc[200] = value
    assert int(ts_medskew_20(close).notna().sum()) == 359


@pytest.mark.parametrize("mag", [1e2, 1e6, 1e8, 1e100, 1e154, 1e300])
def test_one_enormous_return_stays_local(mag):
    """Every window is reduced from its own `length` values, so one giant
    return cannot reach past the 20 windows that hold it. The tail is NOT
    bit-identical -- a spike rescales every later close by a
    non-power-of-two factor -- but it agrees to 3.4e-14, where the
    prototype's ONLINE accumulators move the same bars by up to 0.42."""
    rng = np.random.default_rng(21)
    r = rng.normal(0.0, 0.015, 2000)
    base = ts_medskew_20(Series(1e-198 * np.cumprod(1.0 + r)))
    spiked = r.copy()
    spiked[200] = mag
    col = ts_medskew_20(Series(1e-198 * np.cumprod(1.0 + spiked)))
    shared, mx = _shared(col.iloc[220:], base.iloc[220:])
    assert shared == 1780 and mx < 1e-12, (mag, shared, mx)
    hold = col.iloc[200:220]
    if mag < 1e153:
        # one return among nineteen ordinary ones: the closed form again
        assert int(hold.notna().sum()) == LENGTH
        assert abs(float(hold.median()) - 1 / math.sqrt(LENGTH)) < 1e-3
    else:
        assert int(hold.notna().sum()) == 0      # above the per-return bound


def test_the_prototypes_online_accumulators_do_not_stay_local():
    """The contrast the test above is read against, and the reason this
    module reduces each window from its own values: the same 1e+8 spike
    moves the prototype's LATER bars by 0.40 -- a third of this column's
    whole range -- on bars its window no longer contains."""
    rng = np.random.default_rng(21)
    r = rng.normal(0.0, 0.015, 2000)
    base = _prototype(Series(1e-198 * np.cumprod(1.0 + r)))
    spiked = r.copy()
    spiked[200] = 1e8
    col = _prototype(Series(1e-198 * np.cumprod(1.0 + spiked)))
    shared, mx = _shared(col.iloc[220:], base.iloc[220:])
    assert shared == 1780 and mx > 1e-3, (shared, mx)


# ------------------------------------------------- the prototype and Gate E


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_port_is_the_screen_prototype_within_a_tolerance(frame):
    """Identical NaN masks on nine frames and max |difference| 5.2e-15, so
    Gate E's statistic -- a Spearman over the bars where both fire -- is
    expected to carry over from the screen's prototype run. The launcher's
    Gate E run on THIS module is still the number that decides ship or
    revert. Spearman is 1.000000 on eight frames and 0.999696 on the
    two-point one, where ties are reordered by the last bits."""
    close = FRAMES[frame]()
    a, b = ts_medskew_20(close), _prototype(close)
    masks, shared, mx = _agree(a, b)
    assert masks and shared == FIRED, (frame, shared)
    assert mx < 1e-12, (frame, mx)
    assert _spearman(a, b) > 0.999, frame


def test_the_prototype_reads_a_constant_return_ladder_and_this_port_does_not():
    """The one place the two part company, and it is the guards: 280 windows
    of pure rounding."""
    lad = _ladder()
    assert int(_prototype(lad).notna().sum()) >= 100
    assert int(ts_medskew_20(lad).notna().sum()) == 0


def _ledger_rows():
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["column"].startswith("TS_ABOVE_MEAN")], \
        "sanity: the ledger should carry the neighbouring ts_above_mean_20 row"
    return rows


def test_the_gate_e_row_is_still_owed():
    """Gate E is the launcher's to run, after this session: this module has
    no ledger row yet, and `tests/test_gate_e_ledger.py` fails locally until
    one is recorded (`GATE_E_PENDING_OK=1` turns that into a skip on the way
    to `dev`). This test is the receipt session's cue -- when the row is
    recorded, replace it with one that pins the row's identity and its
    numbers, as `tests/test_ts_aggac_60.py` does."""
    assert not [r for r in _ledger_rows()
                if r["indicator"] == "ts_medskew_20"]


# ------------------------------------------- what the column actually is


def test_it_is_a_nonparametric_skewness_reading():
    """Spearman +0.8803 against the windows' own textbook sample skewness
    over 20,000 independent windows drawn from a symmetric, a right-skewed
    and a left-skewed law. Computed on the STATISTIC rather than through
    this function -- 20,000 one-window calls would say the same thing
    slowly -- and the bridge is the Gate A agreement above."""
    rng = np.random.default_rng(31)
    med, skw = [], []
    for _ in range(20000):
        t = rng.integers(0, 3)
        x = (rng.standard_normal(LENGTH) if t == 0 else
             rng.standard_exponential(LENGTH) if t == 1 else
             -rng.standard_exponential(LENGTH))
        s = float(np.std(x, ddof=1))
        if s == 0.0:
            continue
        med.append((float(np.mean(x)) - float(np.median(x))) / s)
        skw.append(float(pd.Series(x).skew()))
    rho = float(pd.Series(med).corr(pd.Series(skw), method="spearman"))
    assert 0.85 < rho < 0.92, rho


@pytest.mark.parametrize("frame,lo,hi", [
    ("walk", 0.55, 0.75),
    ("heavy-tailed", 0.72, 0.88),
    ("right-skewed", 0.12, 0.28),
])
def test_the_in_fork_overlap_with_the_shipped_return_skewness(frame, lo, hi):
    """⚠ SYNTHETIC, and the only measurement of this pair that exists: Gate
    E's 687 comparators hold no pandas_ta port, and the screen's real-frame
    fork overlap for this candidate (max |rho| 0.2590 vs `smi:SMI_5_20_5`,
    12 frames, 2026-10-24) predates `osap_retskew_21` entering `Category` by
    nine days, so it cannot bound this pair either."""
    close = FRAMES[frame]()
    rho = _spearman(ts_medskew_20(close), osap_retskew_21(close))
    assert lo < rho < hi, (frame, rho)


@pytest.mark.parametrize("frame,lo,hi", [
    ("walk", -0.92, -0.85),
    ("heavy-tailed", -0.94, -0.86),
    ("two-point", -0.80, -0.65),
    ("right-skewed", -0.47, -0.32),
])
def test_the_in_fork_overlap_with_the_shipped_count_above_mean(frame, lo, hi):
    """⚠ The adverse pair, and the one a reader of this column must know
    about. `TS_ABOVE_MEAN_20` (issue #97) is a BACKWARDS skewness reading
    over the SAME 20 returns, so the sign is negative and the magnitude is
    high: -0.8885 on a walk and -0.9025 heavy-tailed, measured here on
    SYNTHETIC frames. The REAL-frame figure is the screen's pooled 0.8428
    (2026-10-24), which is DISCLOSE_GAP and not STRUCK under
    `r3-perframe-0.90` -- and Gate E cannot re-measure it, because its
    comparator set is the engine's and holds no pandas_ta port. See
    docs/TsMedskew20Measured.md §O."""
    close = FRAMES[frame]()
    rho = _spearman(ts_medskew_20(close), ts_above_mean_20(close))
    assert lo < rho < hi, (frame, rho)


def test_it_is_neither_volatility_nor_direction_nor_the_price_level():
    """+0.0800 against the window's own return sd, -0.1129 against its mean
    return, +0.0737 against the close -- which is what the affine invariance
    of Gate D predicts."""
    close = _walk()
    r = close / close.shift(1) - 1.0
    col = ts_medskew_20(close)
    assert abs(_spearman(col, r.rolling(LENGTH).std())) < 0.25
    assert abs(_spearman(col, r.rolling(LENGTH).mean())) < 0.25
    assert abs(_spearman(col, close)) < 0.25


def test_it_is_a_state_not_an_event_flag():
    """Neighbouring windows share 19 of their 20 returns: autocorrelation
    0.8963 at lag 1, 0.6345 at lag 5, 0.3773 at lag 10, 0.1360 at lag 20."""
    col = ts_medskew_20(_walk())
    assert float(col.autocorr(1)) > 0.8
    assert float(col.autocorr(20)) < 0.3


def test_the_level_is_zero_for_any_symmetric_law_and_moves_with_skew():
    """On independent windows of iid returns the column sits at 0 for a
    symmetric law -- the reflection `x -> 2u - x` preserves it and flips the
    sign -- measured mean -0.0006 (sd 0.1532) over 20,000 gaussian windows
    and -0.0002 (sd 0.1659) for student-t(2). It moves off 0 only with skew:
    +0.2832 for exponential returns, -0.2831 for their mirror."""
    rng = np.random.default_rng(41)

    def level(draw):
        vals = []
        for _ in range(5000):
            x = draw()
            s = float(np.std(x, ddof=1))
            if s:
                vals.append((float(np.mean(x)) - float(np.median(x))) / s)
        return float(np.mean(vals))

    assert abs(level(lambda: rng.standard_normal(LENGTH))) < 0.02
    assert abs(level(lambda: rng.standard_t(2, LENGTH))) < 0.02
    assert level(lambda: rng.standard_exponential(LENGTH)) > 0.2
    assert level(lambda: -rng.standard_exponential(LENGTH)) < -0.2


# ---------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    close = _walk(400)
    out = ts_medskew_20(close)
    assert out.name == f"TS_MEDSKEW_{LENGTH}"
    assert out.category == "statistics"
    assert "ts_medskew_20" in pandas_ta.Category["statistics"]
    df = pd.DataFrame({"close": close})
    df.index = pd.date_range("2020-01-01", periods=len(close), freq="D")
    got = df.ta.ts_medskew_20()
    assert got.name == f"TS_MEDSKEW_{LENGTH}"
    pd.testing.assert_series_equal(got.reset_index(drop=True),
                                   out.reset_index(drop=True))


@pytest.mark.parametrize("length,name", [(None, 20), (0, 20), (2, 20),
                                         (-5, 20), (60, 60)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, name):
    """A window of two returns has its mean equal to its median, so the
    column is identically 0 there; three is the smallest that varies."""
    assert ts_medskew_20(_walk(400), length=length).name \
        == f"TS_MEDSKEW_{name}"


def test_length_two_would_be_identically_zero_which_is_why_it_is_refused():
    """The reason for `MIN_LENGTH`, shown rather than asserted: forced
    through at `length` 2 the statistic is 0 on every bar."""
    r = _returns_of(_walk(400))
    W = sliding_window_view(r[1:], 2)
    mean = W.sum(axis=1) / 2
    assert float(np.abs(mean - np.median(W, axis=1)).max()) == 0.0


def test_length_three_takes_both_signs_and_a_bounded_set():
    """At `length` 3 the bound is sqrt(2/3) = 0.8165 and the one-odd-return
    closed form is 1/sqrt(3) = 0.5774."""
    col = ts_medskew_20(_walk(400), length=3).dropna()
    assert float(col.abs().max()) <= math.sqrt(2 / 3) + 1e-12
    assert float(col.min()) < 0 < float(col.max())


def test_too_short_an_input_returns_none():
    """`length` returns need `length + 1` closes."""
    assert ts_medskew_20(_walk(LENGTH)) is None
    assert int(ts_medskew_20(_walk(LENGTH + 1)).notna().sum()) == 1


def test_offset_and_fillna():
    close = _walk(400)
    base = ts_medskew_20(close)
    pd.testing.assert_series_equal(ts_medskew_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_medskew_20(close, offset=-2),
                                   base.shift(-2), check_names=False)
    filled = ts_medskew_20(close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert bool((filled.iloc[:LENGTH] == 0.0).all())


def test_the_module_does_not_import_the_package_root():
    """The `TypeError: 'module' object is not callable` trap in CLAUDE.md:
    a helper is imported from its own module, never from the package."""
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert "from pandas_ta.statistics import" not in src
    assert "from pandas_ta.overlap import" not in src


def test_the_deviations_are_spelled_column_by_column_not_as_a_matrix():
    """A cost choice, pinned because the two spellings agree to 1.1e-16 and
    only the memory separates them: the `(rows, length)` deviation matrix
    peaks at 812.4 MB at `length` 250 where this form stays at 42.0 MB, and
    `np.median(windows, axis=1)` -- which partitions a copy of the same view
    -- peaks at 825.5 MB there, and is also about three times slower
    (docs/TsMedskew20Measured.md, Cost; the PEAKS are the claim, the
    milliseconds move between runs). If either one-liner is restored,
    re-measure before accepting it."""
    code = [ln for ln in open(_REAL.__file__, encoding="utf-8").read()
            .splitlines() if not ln.lstrip().startswith("#")]
    assert any("d = windows[:, j] - mean" in ln for ln in code)
    assert not any("windows - mean[:, None]" in ln for ln in code)
    assert not any("np.median(windows" in ln for ln in code)
