# -*- coding: utf-8 -*-
"""TS-CROSS-MEAN-20: `ts_cross_mean_20`, tsfresh's `number_crossing_m` over
20 LOG closes with the level set to the window's own mean (PandasTa issue
#100).

    TS_CROSS_MEAN_20 = how many of the 19 adjacent pairs of a 20-close
                       window of log prices sit on opposite sides of that
                       window's own mean log price

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, as BIT-equality and not as a tolerance, because a count is
   either right or wrong.** tsfresh is NOT installed in this worktree and
   web access is unavailable, so "tsfresh (MIT)" is an attribution and not
   an oracle (`test_tsfresh_is_not_installed_here` records that, so the
   claim cannot rot into "checked against tsfresh"). What IS checkable is
   pinned:

   * the source applied window by window, sharing no code with the module
     -- bit-equal on **1,481 of 1,481** bars of each of nine 1,500-bar
     frames, NaN masks identical;
   * a `math.fsum` scalar loop over the C library's `math.log` -- bit-equal
     on three of them;
   * an oracle that decides every comparison at **60 significant digits**
     (`decimal.Decimal.ln`, about 44 beyond a double). This is the only
     check that can see the one thing this column's arithmetic can get
     wrong -- deciding a comparison the wrong way -- and on four frames,
     plus quiet frames priced at 1e+6 and 1e-6 where the cancellation
     between a log close and its window mean is worst, float has not done
     it once.

2. **The range, which is [1, 19] and NOT [0, 19].** The window mean lies
   strictly inside the window's own extremes unless every value is equal,
   so at least one close is above it and at least one is not, and the
   sequence must switch at least once. **0 is arithmetically impossible**
   and means the floor failed -- and the UNGUARDED spelling emits it on all
   281 windows of a 300-bar flat frame. Both ends are reached by
   construction (a monotone window reads 1, an alternating one 19); the
   largest any of the nine frames reaches is 16.

3. **Gate B, by mutant, and an honest account of what the blind sweep
   cannot do here.** Five mutants are live and caught 19-37 of 37 offsets,
   where the real module leaks **0 of 37** on each of three frames and at
   `length` 5, 60 and 250.
   ⚠ The sixth is the one worth reading. Rolling the floor's `hi`/`lo` by
   one window makes bar T's NaN mask read window T+1 -- a real look-ahead
   -- and on a clean frame it is not merely invisible but **DEAD**: the
   floor reports on every window there, so the rolled mask reports too and
   the output is identical. What can move is derived rather than guessed:
   bar T's COUNT reads closes T-19..T, so a splice at J cannot touch it for
   T < J, and window T+1 holds a close at or after J only when T+1 >= J --
   so **bar J-1 is the only bar before J that can move**, and only when the
   floor's verdict on window J flips. A frame built so that every offset
   sits at the end of a 20-bar halt catches the mutant **37 of 37** and
   moves exactly bar J-1; the same frame built the obvious way (25-bar
   halts every 40 bars) catches it 3 of 37.

4. **Gate D, and that NOTHING here is bit-identical by construction.** This
   column takes a LOGARITHM, and `log(8p)` is not `log(8) + log(p)` in
   binary floating point -- so the fork's eight return-based tsfresh ports'
   "`8a / 8b` is the same double as `a / b`" argument is unavailable, and
   so is the "only the ORDER is read" argument that covers the two
   close-based ones (`ts_peaks_20`, `ts_perment_20`). What holds the count
   still is a measured margin: the smallest `|x - mean| / max|x|` over the
   199,981 windows of a 200,000-bar walk is **6.927e-10** against an ulp of
   2.2e-16. With it, x8 and x64 are bit-equal on 1,481 of 1,481 bars of
   each of nine frames, and on 1,498 / 1,496 / 1,441 / 1,251 fired bars at
   `length` 3/5/60/250 on the walk; so are x10, x3.7, x0.1 and x1.0000001.
   Stronger than a rescale: the count reads only the ORDER of the log
   closes against their own mean, so `price ** 2`, `price ** 0.5` and
   `1 / price` are bit-equal too.

5. **The guards, each with what it costs and what it buys.** The RELATIVE
   floor (`spread > 4096 eps * max |log c|`) costs **0** body bars on each
   of nine clean frames and empties a flat frame the unguarded spelling
   reports 281 impossible zeros on. Against the sibling ports' ABSOLUTE
   `4096 eps` floor it is identical on every ordinary frame and differs
   exactly where `|log c|` is far from 1: at a price near 1.0 it reports
   581 bars that the exact oracle confirms and the absolute floor throws
   away all but 44 of. ⚠ The 4096 is a filter and NOT a proof, and that is
   measured per WINDOW on the floor's own axis: bucketing the 5,981
   windows of a ramped-volatility frame by their own
   `(hi - lo) / (eps * max|x|)`, the unguarded count agrees with the
   60-digit oracle on **0.5678** of the windows below 16 ulps, 0.8205 at
   [16, 64), 0.9307 at [64, 256) and 0.9812 at [256, 1024) — the regime
   the floor refuses — and on **0.9972** at [4096, 16384), which the floor
   admits. Five of the six admitted buckets are total and the sixth is
   350 of 351. What makes that residual irrelevant is where real windows
   sit: the worst of the nine frames is **1.27e+13** ulps.

6. **What the column actually is**, which Gate E's 687 comparators can only
   half see: a CHOPPINESS reading (+0.5289 .. +0.6296 against the shipped
   `chop` on six synthetic frames, -0.4813 .. -0.5607 against `vhf`) and a
   window-DISPERSION reading upside down (**-0.6827** against the window's
   own log-close standard deviation), while being nearly blind to realised
   volatility (+0.1045) and to the price level (-0.1178).

7. **That it IS the screen prototype**: bit-equal on 1,481 of 1,481 bars of
   each of nine frames with IDENTICAL NaN masks, parting company only where
   a guard fires.

Numbers come from `docs/measure_ts_cross_mean_20.py`; the receipt is
`docs/TsCrossMean20Measured.md`. Gate E is owed -- issue-solver runs it on
this module after the session that wrote this file, and
`test_the_gate_e_row_is_still_owed` is the receipt session's cue.
Counts that depend on the last bits of a generated frame carry a band or a
tolerance; the structural facts are pinned exactly.
"""
import importlib
import math
import types
from decimal import Decimal, localcontext

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta
from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20
from pandas_ta.statistics.ts_cross_mean_20 import (NOISE_FACTOR,
                                                   ts_cross_mean_20)
from pandas_ta.statistics.ts_peaks_20 import ts_peaks_20
from pandas_ta.statistics.ts_perment_20 import ts_perment_20
from pandas_ta.trend.chop import chop
from pandas_ta.trend.vhf import vhf

LENGTH = 20
N = 1500
FIRED = N - LENGTH + 1          # 20 CLOSES, so the first value is at bar 19

_REAL = importlib.import_module("pandas_ta.statistics.ts_cross_mean_20")


# ------------------------------------------------------------------ frames


def _walk(n=N, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=N, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _ar1(n=N, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=N, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=N, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A constant-rate rise. Its log closes are MONOTONE, so every window
    reads exactly 1 -- a legitimate reading here, unlike in the sibling
    return-based ports where a ladder is degenerate."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _patches(n=N, seed=23, sigma=0.015, patch=25, every=40):
    """A walk interrupted every `every` bars by `patch` bars of an UNCHANGED
    close -- a halted stock, built the obvious way."""
    c = _walk(n, seed, sigma).to_numpy()
    for start in range(every, n - patch, every + patch):
        c[start:start + patch] = c[start]
    return Series(c)


def _halted(n=N, seed=23, sigma=0.015, length=LENGTH, offsets=None):
    """The DESIGNED probe: a walk in which every bar the Gate B sweep
    splices at is the last bar of a `length`-bar halt."""
    c = _walk(n, seed, sigma).to_numpy()
    for j in (OFFSETS if offsets is None else offsets):
        c[j - length + 1:j + 1] = c[j - length + 1]
    return Series(c)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
}


# ----------------------------------------------------------------- helpers


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    return masks, int(m.sum()), int((a[m] == b[m]).sum())


def _ohlc(close, band=0.004):
    """Deterministic SYNTHETIC high/low for the neighbours that need them."""
    return close * (1.0 + band), close * (1.0 - band)


# ------------------------------------------------------------- the oracles


def _source_windowed(close, length=LENGTH):
    """tsfresh's `number_crossing_m(x, m)` retyped and applied one window at
    a time, `m` being that window's own mean. Shares no code with the
    module: a Python loop, `np.mean`, and the source's own
    `np.where(np.diff(positive))[0].size`."""
    a = np.log(close.to_numpy(dtype=float))
    out = np.full(a.size, np.nan)
    for t in range(length - 1, a.size):
        x = a[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        positive = x > np.mean(x)
        out[t] = float(np.where(np.diff(positive))[0].size)
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH):
    """`math.log` -- the C library's, not numpy's -- and `math.fsum`, which
    is exact up to a single final rounding."""
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = np.full(len(c), np.nan)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if not all(math.isfinite(v) and v > 0.0 for v in w):
            continue
        x = [math.log(v) for v in w]
        m = math.fsum(x) / length
        s = [v > m for v in x]
        out[t] = float(sum(1 for a, b in zip(s, s[1:]) if a != b))
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH, prec=60):
    """The answer at `prec` significant digits, about 44 beyond a double:
    every close is a rational, `Decimal.ln()` is correctly rounded at that
    precision, and the mean and comparisons are decided there.

    `localcontext` and not `getcontext().prec = ...`: the decimal context
    is process-global, and an oracle has no business leaving 60 digits
    behind for whatever runs next."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    with localcontext() as ctx:
        ctx.prec = prec
        n = Decimal(length)
        logs = [Decimal(float(v)).ln() if np.isfinite(v) and v > 0.0 else None
                for v in c]
        for t in range(length - 1, c.size):
            x = logs[t - length + 1:t + 1]
            if any(v is None for v in x):
                continue
            m = sum(x) / n
            s = [v > m for v in x]
            out[t] = float(sum(1 for a, b in zip(s, s[1:]) if a != b))
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_cross_mean_20`,
    retyped: `roll(np.log(c), 20, w_crossings_mean)`. No guards of any
    kind, so this is also the UNGUARDED spelling of this module."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    s = W > W.mean(1, keepdims=True)
    out = np.full(a.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _absolute_floor(close, length=LENGTH):
    """This module with the sibling ports' ABSOLUTE `4096 eps` floor on the
    window's log range instead of the relative one."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    s = W > (W.sum(axis=1) / length)[:, None]
    v = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    rep = W.max(axis=1) - W.min(axis=1) > NOISE_FACTOR
    out = np.full(a.size, np.nan)
    out[length - 1:] = np.where(rep, v, np.nan)
    return Series(out, index=close.index)


# ------------------------------------------------------------- the readings


def _on_raw_closes(close, length=LENGTH):
    """The same count on the closes themselves: the threshold becomes the
    window's ARITHMETIC mean instead of its geometric one."""
    a = close.to_numpy(dtype=float)
    W = sliding_window_view(a, length)
    s = W > (W.sum(axis=1) / length)[:, None]
    out = np.full(a.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _on_returns(close, length=LENGTH):
    """The count over 20 simple RETURNS instead of 20 log closes."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r, length)
    s = W > (W.sum(axis=1) / length)[:, None]
    out = np.full(r.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _weak_comparison(close, length=LENGTH):
    """`>=` where the source has `>`."""
    a = np.log(close.to_numpy(dtype=float))
    W = sliding_window_view(a, length)
    s = W >= (W.sum(axis=1) / length)[:, None]
    out = np.full(a.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


def _crossings_of_zero(close, length=LENGTH):
    """`number_crossing_m(x, m=0)` on log RETURNS -- the other way this
    source function is usually called."""
    r = np.log(close / close.shift(1)).to_numpy()
    W = sliding_window_view(r, length)
    s = W > 0.0
    out = np.full(r.size, np.nan)
    out[length - 1:] = (s[:, 1:] != s[:, :-1]).sum(1).astype(float)
    return Series(out, index=close.index)


# --------------------------------------------------- Gate A: the source


def test_tsfresh_is_not_installed_here():
    """The attribution is an attribution. If tsfresh ever IS installed this
    fails, and whoever sees it should compare against
    `feature_calculators.number_crossing_m` directly."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfresh")


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_module_matches_the_source_applied_window_by_window(frame):
    """Gate A1: identical NaN masks and every shared bar BIT-equal, on each
    of nine frames. 1,481 of 1,481 as measured here."""
    close = FRAMES[frame]()
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 _source_windowed(close))
    assert masks and shared == FIRED, (frame, shared)
    assert same == shared, (frame, shared - same)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "heavy-tailed"])
def test_the_module_matches_an_fsum_scalar_loop(frame):
    """Gate A2: a different logarithm (the C library's) and a sum that is
    exact up to one rounding."""
    close = FRAMES[frame]()
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 _fsum_windowed(close))
    assert masks and shared == FIRED, (frame, shared)
    assert same == shared, (frame, shared - same)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "two-point",
                                   "trending"])
def test_the_exact_oracle_agrees_so_no_comparison_was_decided_wrongly(frame):
    """Gate A3. The ONE thing float can get wrong here is which side of the
    mean a close falls on, and only an oracle that rounds nowhere near a
    double can see it. 60 significant digits, every bar."""
    close = FRAMES[frame]()
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 _exact_windowed(close))
    assert masks and shared == FIRED, (frame, shared)
    assert same == shared, (frame, shared - same)


@pytest.mark.parametrize("price,sigma", [(1e6, 1e-7), (1e6, 1e-9),
                                         (1e-6, 1e-7)])
def test_the_exact_oracle_where_the_cancellation_is_worst(price, sigma):
    """Gate A3b. A quiet frame at a price far from 1.0 is where `log c` is
    large and `log c - mean` is tiny, so the subtraction cancels hardest.
    581 of 581 bars exact at 1e+6 and at 1e-6."""
    rng = np.random.default_rng(31)
    close = Series(price * np.exp(np.cumsum(rng.normal(0, sigma, 600))))
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 _exact_windowed(close))
    assert masks and shared == 600 - LENGTH + 1, shared
    assert same == shared, shared - same


# --------------------------------------------------------------- the range


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_column_never_leaves_one_to_length_minus_one(frame):
    """Item 2. 0 is arithmetically impossible and so is `length`: the
    window mean sits strictly inside the window's extremes unless every
    value is equal, and an equal window is refused by the floor."""
    col = ts_cross_mean_20(FRAMES[frame]()).dropna()
    assert int(col.min()) >= 1, (frame, col.min())
    assert int(col.max()) <= LENGTH - 1, (frame, col.max())
    assert bool((col == col.round()).all())


def test_a_monotone_window_reads_one_and_an_alternating_one_reads_nineteen():
    """Both ends, by construction rather than by hope."""
    mono = Series(100.0 * np.exp(np.arange(40, dtype=float) * 0.01))
    alt = Series(100.0 * np.exp(np.array([0.0, 0.01] * 20, dtype=float)))
    assert sorted(ts_cross_mean_20(mono).dropna().unique()) == [1.0]
    assert sorted(ts_cross_mean_20(alt).dropna().unique()) == [19.0]


def test_the_unguarded_spelling_emits_the_impossible_zero():
    """What the floor is FOR. On a 300-bar flat frame the unguarded count
    reads 0 on every one of its 281 windows -- a value this column cannot
    otherwise reach -- and this module reports none of them."""
    flat = _flat()
    assert sorted(set(_prototype(flat).dropna().tolist())) == [0.0]
    assert int(_prototype(flat).notna().sum()) == 281
    assert int(ts_cross_mean_20(flat).notna().sum()) == 0


def test_a_window_of_twenty_identical_closes_does_not_average_to_itself():
    """The arithmetic behind the line above, so it cannot be mistaken for a
    rounding curiosity: numpy's windowed sum of 20 copies of `log(100)`,
    divided by 20, is NOT `log(100)`. Every close then sits on the same
    side of the 'mean', the count is 0, and 0 is impossible."""
    a = np.full(LENGTH, np.log(100.0))
    mean = sliding_window_view(a, LENGTH).sum(axis=1)[0] / LENGTH
    assert mean != np.log(100.0)


# -------------------------------------------------- Gate A: the readings


def test_log_closes_and_raw_closes_are_different_columns():
    """The issue says LOG closes, so the threshold is the window's
    geometric mean. On the raw closes it is the arithmetic mean, which is
    higher: Spearman 0.9906, 1,443 of 1,481 bars bit-equal, and where they
    differ they differ by up to 2 crossings."""
    close = _walk()
    base, other = ts_cross_mean_20(close), _on_raw_closes(close)
    masks, shared, same = _agree(base, other)
    assert masks and shared == FIRED
    assert 0.95 < _spearman(base, other) < 1.0
    assert 1300 <= same < shared, same
    assert float((base - other).abs().max()) <= 4.0


def test_twenty_closes_is_not_twenty_returns():
    """The off-by-one a reader makes, priced so it is not re-argued: the
    same count over 20 simple returns is a different question entirely."""
    close = _walk()
    base, other = ts_cross_mean_20(close), _on_returns(close)
    assert abs(_spearman(base, other)) < 0.5
    assert int(ts_cross_mean_20(close).notna().to_numpy().argmax()) \
        == LENGTH - 1


def test_the_level_mean_is_not_the_level_zero():
    """`number_crossing_m` is usually called with a fixed level. With
    `m = 0` on log returns it counts return SIGN changes, which is a
    different column: Spearman under 0.5 on a walk."""
    close = _walk()
    assert abs(_spearman(ts_cross_mean_20(close),
                         _crossings_of_zero(close))) < 0.5


def test_the_output_is_the_raw_count_and_not_the_share():
    """The output is the source function's own return value, a raw count.
    Dividing by `length - 1` would be an exact, rank-identical rescaling
    that no Gate E Spearman could see -- which is exactly why the choice
    has to be pinned HERE, on the values, rather than by a correlation
    that cannot tell the two apart. A monotone window reads 1.0 and not
    1/19, and every value is a whole number in [1, 19]."""
    mono = Series(100.0 * np.exp(np.arange(40, dtype=float) * 0.01))
    assert sorted(ts_cross_mean_20(mono).dropna().unique()) == [1.0]
    v = ts_cross_mean_20(_walk()).dropna()
    assert bool((v == v.round()).all()) and float(v.min()) >= 1.0


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "two-point"])
def test_a_tie_with_the_window_mean_never_happens_on_a_real_shaped_frame(
        frame):
    """Which is why the strict `>` has to be pinned by construction below:
    0 exact ties in 29,620 window/close pairs per frame."""
    a = np.log(FRAMES[frame]().to_numpy())
    W = sliding_window_view(a, LENGTH)
    assert int((W == (W.sum(axis=1) / LENGTH)[:, None]).sum()) == 0


def test_a_tie_cannot_separate_strict_from_weak_at_length_three():
    """Derived, then checked: a tied value is NOT above the mean, so for
    the two spellings to disagree its two neighbours would both have to be
    -- and with `x1 = m` the three logs sum to `3m`, so `x0 + x2` is
    exactly `2m` and two values both above `m` would sum to MORE. So no
    `length` 3 window can price this choice.

    ⚠ The premise is asserted and not assumed. Closes `[k/p, k, k*p]`
    multiply to `k**3`, so `log(k)` is the exact mean of their three logs
    -- but a bit-exact tie is not automatic (the `length` 4 search in
    docs/measure_ts_cross_mean_20.py exists for that reason), so this
    searches for the integer triples where the tie survives to a double,
    asserts that it found some, and only then compares the spellings. A
    version that skipped the search would pass by testing windows with no
    tie in them."""
    tied = 0
    for k in range(4, 400):
        for p in range(2, 13):
            if k % p:
                continue
            closes = Series([float(k // p), float(k), float(k * p)])
            x = np.log(closes.to_numpy())
            if x[1] != x.sum() / 3.0:
                continue
            tied += 1
            assert float(ts_cross_mean_20(closes, length=3).iloc[-1]) \
                == float(_weak_comparison(closes, length=3).iloc[-1])
    assert tied >= 20, tied


def test_the_strict_comparison_is_pinned_by_a_constructed_tie():
    """`length` 4 is the smallest window where `>` and `>=` can disagree.
    The closes [12, 6, 18, 1] multiply to 6**4, so the exact mean of their
    logs is log(6) -- and here it is also the BIT-EQUAL mean, which is the
    part that cannot be taken on trust. Strict reads 3, `>=` reads 1."""
    closes = Series([12.0, 6.0, 18.0, 1.0])
    x = np.log(closes.to_numpy())
    assert x[1] == x.sum() / 4.0                      # the tie is real
    assert float(ts_cross_mean_20(closes, length=4).iloc[-1]) == 3.0
    assert float(_weak_comparison(closes, length=4).iloc[-1]) == 1.0


# ------------------------------------------------------ Gate B: the mutants


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(reported, count, np.nan)",
    "    out[length - 3:c.size - 2] = np.where(reported, count, np.nan)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(reported, count, np.nan)",
    "    out[:windows.shape[0]] = np.where(reported, count, np.nan)")
FORWARD_WINDOW = (
    "    windows = sliding_window_view(x, length)",
    "    windows = sliding_window_view(np.roll(x, -1), length)")
FORWARD_CLOSE = (
    "    x = np.log(c)",
    "    x = np.log(np.roll(c, -1))")
FUTURE_MEAN = (
    "    mean = windows.sum(axis=1) / length",
    "    mean = np.roll(windows.sum(axis=1) / length, -1)")
#: The floor's own index. A real look-ahead -- bar T's mask would read
#: window T+1 -- and DEAD on a clean frame, because the floor reports on
#: every window there. Caught by a designed frame instead; see below.
SHIFTED_FLOOR = (
    "    hi, lo = windows.max(axis=1), windows.min(axis=1)",
    "    hi, lo = (np.roll(windows.max(axis=1), -1),\n"
    "              np.roll(windows.min(axis=1), -1))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_window": FORWARD_WINDOW,
    "forward_close": FORWARD_CLOSE,
    "future_mean": FUTURE_MEAN,
}
OFFSETS = range(40, N, 40)      # 37 offsets
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 37 offsets, at the
#: default `length` -- BANDS, not targets. `forward_close` and
#: `forward_window` score identically because rolling the closes before the
#: logarithm and rolling the log closes after it are the same edit in two
#: places; both are kept so that both LINES are guarded. `future_mean` is
#: the low one: rolling the mean by one window changes a bar only when the
#: two windows' means straddle a different set of closes.
CAUGHT = {
    "back_date_two": (24, 37),
    "back_date_full": (30, 37),
    "forward_window": (18, 37),
    "forward_close": (18, 37),
    "future_mean": (12, 37),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_cross_mean_20_mutant")
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
    assert _caught(ts_cross_mean_20, close, other) == []


@pytest.mark.parametrize("length", [5, 60, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(ts_cross_mean_20, close, other, length=length) == []
    assert int(ts_cross_mean_20(close, length=length).notna()
               .to_numpy().argmax()) == length - 1


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column -- otherwise the test proves
    nothing -- and be caught by the blind sweep within its measured band."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_cross_mean_20(close).equals(ts_cross_mean_20(close))
    hits = _caught(mod.ts_cross_mean_20, close, other)
    lo, hi = CAUGHT[mutant]
    assert lo <= len(hits) <= hi, (mutant, frame, len(hits))


def test_the_floor_index_mutant_is_dead_on_a_clean_frame():
    """The sixth mutant, and the honest account of what Gate B's sweep
    cannot do here. Shifting `hi`/`lo` by one window makes bar T's NaN mask
    read window T+1 -- a look-ahead. On a clean frame the floor reports on
    EVERY window, so the rolled mask reports too and the mutant produces a
    bit-identical column: not merely invisible to the sweep but dead. The
    two tests after this one are what give it something to change."""
    mod = _load_mutant(*SHIFTED_FLOOR)
    for frame, (close, other) in sorted(PAIRS.items()):
        real, mutant = ts_cross_mean_20(close), mod.ts_cross_mean_20(close)
        assert mutant.equals(real), frame
        assert _caught(mod.ts_cross_mean_20, close, other) == [], frame


def test_the_designed_probe_catches_the_floor_index_mutant():
    """What the shifted floor can move is DERIVED and then counted. Bar T's
    count reads closes T-19..T, so a splice at J cannot touch it for T < J;
    and window T+1 holds a close at or after J only when T+1 >= J. So bar
    J-1 is the only bar before J that can move, and only when the floor's
    verdict on window J flips. On a frame where every offset sits at the
    end of a 20-bar halt, that is exactly what happens: the real module
    still leaks 0 of 37, the mutant is caught 37 of 37, and the bar it
    moves is J-1 and nothing else."""
    close, other = _halted(), _halted(seed=24)
    col, un = ts_cross_mean_20(close), _prototype(close)
    emptied = col.iloc[LENGTH:].isna()
    assert int(emptied.sum()) == len(list(OFFSETS))
    assert int(un.iloc[LENGTH:][emptied].notna().sum()) == int(emptied.sum())
    assert sorted(set(un.iloc[LENGTH:][emptied].dropna().tolist())) == [0.0]

    assert _caught(ts_cross_mean_20, close, other) == []
    mod = _load_mutant(*SHIFTED_FLOOR)
    assert len(_caught(mod.ts_cross_mean_20, close, other)) \
        == len(list(OFFSETS))

    j = list(OFFSETS)[0]
    p = close.copy()
    p.iloc[j:] = other.iloc[j:].values
    a, b = mod.ts_cross_mean_20(close), mod.ts_cross_mean_20(p)
    moved = np.flatnonzero(
        (a.iloc[:j].isna() != b.iloc[:j].isna()).to_numpy()).tolist()
    assert moved == [j - 1], moved


def test_the_obvious_probe_would_have_proved_almost_nothing():
    """The same frame built without the derivation: 25-bar halts every 40
    bars, while the sweep's offsets are multiples of 40, so hardly any
    offset lands on a window the floor empties. 138 bars emptied and the
    mutant caught 3 of 37 -- a probe that looks thorough and is not."""
    close, other = _patches(), _patches(seed=24)
    col, un = ts_cross_mean_20(close), _prototype(close)
    emptied = col.iloc[LENGTH:].isna()
    assert 100 <= int(emptied.sum()) <= 200, int(emptied.sum())
    assert int(un.iloc[LENGTH:][emptied].notna().sum()) == int(emptied.sum())
    assert _caught(ts_cross_mean_20, close, other) == []
    mod = _load_mutant(*SHIFTED_FLOOR)
    assert len(_caught(mod.ts_cross_mean_20, close, other)) <= 10


def test_the_first_fired_bar_is_length_minus_one():
    """20 CLOSES, not 20 returns -- so bar 19 and not bar 20. The prototype
    agrees, because it reads the same 20 closes."""
    col = ts_cross_mean_20(_walk())
    assert int(col.notna().to_numpy().argmax()) == LENGTH - 1
    assert bool(np.isnan(col.iloc[LENGTH - 2]))
    assert int(_prototype(_walk()).notna().to_numpy().argmax()) == LENGTH - 1


# ------------------------------------------------------- Gate C / Gate D


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_c_the_column_fires_and_varies(frame):
    """0 < fires < n, every value non-zero, and not all the same value.
    The exact number of distinct values is CPU-dependent in principle and
    is banded rather than pinned; 10 to 16 as measured here."""
    col = ts_cross_mean_20(FRAMES[frame]())
    v = col.dropna()
    assert int(col.notna().sum()) == FIRED
    assert 0 < FIRED < col.size
    assert int((v == 0).sum()) == 0
    assert 5 <= v.nunique() <= LENGTH - 1, (frame, v.nunique())


def test_a_frame_with_no_dispersion_fires_on_nothing():
    assert int(ts_cross_mean_20(_flat()).notna().sum()) == 0


def test_a_constant_rate_ladder_is_a_reading_and_not_a_degenerate_window():
    """Unlike the sibling return-based ports, where a ladder has constant
    returns and is refused: here its log closes are monotone, so every
    window legitimately reads 1."""
    col = ts_cross_mean_20(_ladder())
    assert int(col.notna().sum()) == 300 - LENGTH + 1
    assert sorted(set(col.dropna().tolist())) == [1.0]


@pytest.mark.parametrize("k", [8.0, 64.0])
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_scale_x8_and_x64_are_bit_identical(frame, k):
    """Gate D, and ⚠ not by construction. `log(8p)` is not
    `log(8) + log(p)` in binary floating point, so this is a MEASUREMENT
    whose margin is pinned by `test_scale_the_margin_that_makes_it_hold`."""
    close = FRAMES[frame]()
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 ts_cross_mean_20(close * k))
    assert masks and shared == FIRED, (frame, k, shared)
    assert same == shared, (frame, k, shared - same)


@pytest.mark.parametrize("length", [3, 5, 60, 250])
def test_scale_x8_is_bit_identical_at_other_lengths(length):
    close = _walk()
    masks, shared, same = _agree(ts_cross_mean_20(close, length=length),
                                 ts_cross_mean_20(close * 8.0, length=length))
    assert masks and shared == N - length + 1, (length, shared)
    assert same == shared, (length, shared - same)


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "two-point"])
def test_scale_x10_and_x3_7_are_bit_identical_too_though_they_need_not_be(
        frame, k):
    close = FRAMES[frame]()
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 ts_cross_mean_20(close * k))
    assert masks and shared == FIRED, (frame, k, shared)
    assert same == shared, (frame, k, shared - same)


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_scale_the_margin_that_makes_it_hold(frame):
    """A count moves only when a perturbation reorders a log close and its
    own window mean. The smallest gap seen on these frames is 4.8e-08 of
    the window's own magnitude, against an ulp of 2.2e-16 -- banded at
    1e-08 so a different CPU's last bits cannot fail it."""
    a = np.log(FRAMES[frame]().to_numpy())
    W = sliding_window_view(a, LENGTH)
    m = (W.sum(axis=1) / LENGTH)[:, None]
    amax = np.maximum(W.max(1), -W.min(1))[:, None]
    assert float((np.abs(W - m) / amax).min()) > 1e-8, frame


def test_scale_is_bit_identical_on_a_two_hundred_thousand_bar_walk():
    """The same claim with 199,981 windows behind it instead of 1,481, and
    the margin that carries it."""
    rng = np.random.default_rng(77)
    big = Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.015, 200000))))
    a = np.log(big.to_numpy())
    W = sliding_window_view(a, LENGTH)
    m = (W.sum(axis=1) / LENGTH)[:, None]
    amax = np.maximum(W.max(1), -W.min(1))[:, None]
    assert float((np.abs(W - m) / amax).min()) > 1e-11
    base = ts_cross_mean_20(big)
    for k in (8.0, 64.0, 10.0):
        masks, shared, same = _agree(base, ts_cross_mean_20(big * k))
        assert masks and same == shared == 200000 - LENGTH + 1, (k, same)


@pytest.mark.parametrize("label,power", [("squared", 2.0),
                                         ("square root", 0.5),
                                         ("reciprocal", -1.0)])
def test_scale_any_monotone_power_of_the_price_leaves_it_where_it_was(
        label, power):
    """Stronger than a rescale, and the reason: the count reads only the
    ORDER of the log closes against their own mean, and `x -> a*x` for any
    non-zero `a` preserves that order (or reverses all of it, which leaves
    the number of SWITCHES untouched)."""
    close = _walk()
    masks, shared, same = _agree(ts_cross_mean_20(close),
                                 ts_cross_mean_20(close ** power))
    assert masks and shared == FIRED
    assert same == shared, (label, shared - same)


def test_it_is_a_state_not_an_event_flag():
    """Neighbouring windows share 19 of their 20 closes."""
    col = ts_cross_mean_20(_walk()).dropna()
    assert 0.7 < float(col.autocorr(1)) < 0.95
    assert 0.1 < float(col.autocorr(5)) < 0.5
    assert abs(float(col.autocorr(20))) < 0.2


# ------------------------------------------------------------- the guards


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_floor_costs_no_bar_at_all_on_a_clean_frame(frame):
    close = FRAMES[frame]()
    assert int(ts_cross_mean_20(close).notna().sum()) \
        == int(_prototype(close).notna().sum()) == FIRED


def test_the_floor_is_relative_and_an_absolute_one_would_throw_away_truth():
    """The departure from the sibling ports' absolute `4096 eps`, priced.
    At a price near 1.0 every `|log c|` is tiny, so the error the floor
    must beat is tiny too -- and the relative floor reports 581 bars that
    an exact 60-digit oracle confirms, where the absolute floor keeps 44.
    On the ordinary frames the two are identical."""
    rng = np.random.default_rng(5)
    close = Series(1.0 * np.exp(np.cumsum(rng.normal(0, 1e-13, 600))))
    rel, ab = ts_cross_mean_20(close), _absolute_floor(close)
    assert int(rel.notna().sum()) == 600 - LENGTH + 1
    assert int(ab.notna().sum()) < 100
    masks, shared, same = _agree(rel, _exact_windowed(close))
    assert masks and same == shared == 600 - LENGTH + 1

    for frame in ["walk", "two-point"]:
        other = FRAMES[frame]()
        assert int(ts_cross_mean_20(other).notna().sum()) \
            == int(_absolute_floor(other).notna().sum())


def test_the_relative_floor_refuses_the_mirror_case_and_is_right_to():
    """The other direction. A frame at price 1e+6 whose log closes span
    only 5e-15 is BELOW the relative floor and above the absolute one --
    and there the unguarded count disagrees with the exact oracle on a
    large share of its windows, so refusing is the right answer."""
    rng = np.random.default_rng(5)
    close = Series(1e6 * np.exp(np.cumsum(rng.normal(0, 1e-15, 600))))
    assert int(ts_cross_mean_20(close).notna().sum()) == 0
    masks, shared, same = _agree(_prototype(close), _exact_windowed(close))
    assert same < shared * 0.8, (same, shared)


def _ramped_vol(n=6000, seed=5, price=100.0, lo=-18.0, hi=-8.0):
    """A frame whose per-bar volatility sweeps from 1e-18 to 1e-08, so its
    windows span the whole range of dispersions the floor has to judge."""
    rng = np.random.default_rng(seed)
    sigma = np.logspace(lo, hi, n)
    return Series(price * np.exp(np.cumsum(rng.normal(0.0, 1.0, n) * sigma)))


@pytest.mark.parametrize("lo,hi,at_most,at_least", [
    (0, 16, 0.70, 0.0),             # float is barely better than a coin
    (16, 64, 0.95, 0.70),
    (64, 256, 0.99, 0.85),
    (256, 1024, 1.0, 0.93),
    (1024, 4096, 1.0, 0.97),        # the last bucket the floor refuses
    (4096, 16384, 1.0, 0.99),       # above the floor
    (16384, np.inf, 1.0, 0.998),    # a band, not a pin on perfection
])
def test_where_the_floor_sits_on_its_own_axis(lo, hi, at_most, at_least):
    """The floor thresholds `(hi - lo) / (eps * max|x|)`, so that is the
    axis the calibration has to be measured on -- PER WINDOW. 5,981 windows
    of a frame whose volatility sweeps 1e-18 .. 1e-08, bucketed by their own
    ratio, with the unguarded float count compared against the 60-digit
    exact one (docs/TsCrossMean20Measured.md G3b):

        [0, 16)        0.5678      [1024, 4096)    1.0000
        [16, 64)       0.8205      [4096, 16384)   0.9972
        [64, 256)      0.9307      [16384, 1e6)    1.0000
        [256, 1024)    0.9812      [1e6, 1e8)      1.0000

    ⚠ Two things are pinned here, and the second is the uncomfortable one.
    Below the floor float gets barely half the counts right, which is what
    the floor is for. ABOVE it -- the last three rows of each of the two
    price columns, six cells in all -- the agreement is total in five and
    350 of 351 in the sixth. So the floor is a strong filter and NOT a
    proof, and every bound here is a band rather than 1.0 so it cannot be
    read as one."""
    close = _ramped_vol()
    a = np.log(close.to_numpy())
    W = sliding_window_view(a, LENGTH)
    amax = np.maximum(W.max(1), -W.min(1))
    ulps = (W.max(1) - W.min(1)) / (np.finfo(float).eps * amax)
    un = _prototype(close).to_numpy()[LENGTH - 1:]
    ex = _exact_windowed(close).to_numpy()[LENGTH - 1:]
    m = (ulps >= lo) & (ulps < hi)
    assert int(m.sum()) >= 100, int(m.sum())
    share = float((un[m] == ex[m]).mean())
    assert at_least <= share <= at_most, (lo, hi, share)


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_ordinary_frames_sit_nine_orders_above_the_floor(frame):
    """Which is what makes the residual error above the floor irrelevant in
    practice: the worst window of any of the nine frames is 1.27e+13 ulps,
    against a floor of 4,096."""
    a = np.log(FRAMES[frame]().to_numpy())
    W = sliding_window_view(a, LENGTH)
    amax = np.maximum(W.max(1), -W.min(1))
    ulps = (W.max(1) - W.min(1)) / (np.finfo(float).eps * amax)
    assert float(ulps.min()) > 1e11, (frame, ulps.min())


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, -1.0,
                                   1e-310])
def test_a_bad_close_empties_its_windows(value):
    """A close that is not a finite, normal, positive float has no
    logarithm worth the name, and it empties exactly the `length` windows
    holding it -- not a silent count of 0."""
    base = ts_cross_mean_20(_walk(400))
    close = _walk(400)
    close.iloc[200] = value
    col = ts_cross_mean_20(close)
    assert int((col.isna() & base.notna()).sum()) == LENGTH
    # No earlier bar moves: the NaN mask is unchanged before bar 200 and
    # every value there is bit-identical (the warm-up bars are NaN in both,
    # so they are compared as masks and not as values).
    head = slice(None, 200)
    assert bool((col.iloc[head].isna() == base.iloc[head].isna()).all())
    seen = base.iloc[head].notna()
    assert bool((col.iloc[head][seen] == base.iloc[head][seen]).all())


@pytest.mark.parametrize("bar,emptied", [(0, 1), (1, 2), (18, 19),
                                         (200, 20), (398, 2), (399, 1)])
def test_a_bad_close_near_either_end_empties_fewer(bar, emptied):
    base = ts_cross_mean_20(_walk(400))
    close = _walk(400)
    close.iloc[bar] = np.nan
    col = ts_cross_mean_20(close)
    assert int((col.isna() & base.notna()).sum()) == emptied


def test_no_warning_is_raised_on_a_frame_full_of_bad_closes():
    """Every non-positive and non-finite close is replaced before `np.log`
    sees it, so there is no `invalid value` or `divide by zero` warning to
    silence -- and no `errstate` in the module hiding one."""
    close = _walk(400)
    close.iloc[::3] = -1.0
    close.iloc[1::3] = 0.0
    with np.errstate(all="raise"):
        out = ts_cross_mean_20(close)
    assert int(out.notna().sum()) == 0


def test_no_magnitude_bound_is_needed_and_the_module_survives_both_extremes():
    """`ts_above_mean_20` needs a per-return magnitude bound because a
    price RATIO is unbounded and a window sum of ratios can overflow. A
    logarithm cannot: every close that survives the mask has
    `|log c| <= 709.79`, so even a 250-wide window sums to at most 1.8e+05.
    Asserted on the MODULE at both ends of the normal double range, not
    only on the two constants -- a frame priced just above the smallest
    normal and one just below the largest both produce ordinary counts."""
    assert abs(math.log(np.finfo(float).tiny)) < 710.0
    assert abs(math.log(np.finfo(float).max)) < 710.0
    for price in (np.finfo(float).tiny * 4.0, np.finfo(float).max / 4.0):
        rng = np.random.default_rng(13)
        close = Series(price * np.exp(np.cumsum(rng.normal(0, 0.015, 400))))
        col = ts_cross_mean_20(close, length=250)
        v = col.dropna()
        assert int(col.notna().sum()) == 400 - 250 + 1
        assert bool(np.isfinite(v).all())
        assert 1 <= float(v.min()) and float(v.max()) <= 249


@pytest.mark.parametrize("mag", [1e2, 1e6, 1e8, 1e100, 1e300])
def test_one_enormous_close_stays_local(mag):
    """Every window is reduced from its own 20 values, so nothing is
    accumulated across windows: a planted close leaves every bar from 220
    on BIT-IDENTICAL, at every magnitude up to 1e+300."""
    base = _walk(2000)
    ref = ts_cross_mean_20(base)
    close = base.copy()
    close.iloc[200] = float(close.iloc[200]) * mag
    col = ts_cross_mean_20(close)
    assert int((col.iloc[220:] == ref.iloc[220:]).sum()) == 1780
    assert set(col.iloc[200:220].dropna().tolist()) <= {1.0, 2.0}


# ------------------------------------------------- the prototype and Gate E


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_port_is_the_screen_prototype_bit_for_bit(frame):
    """Item 7: identical NaN masks and every bar bit-equal, on each of nine
    frames. Gate E's statistic is a Spearman over the bars where both fire,
    so the screen's figures are expected to carry over -- the launcher's run
    on THIS module is still the number that decides."""
    close = FRAMES[frame]()
    masks, shared, same = _agree(ts_cross_mean_20(close), _prototype(close))
    assert masks and shared == FIRED, (frame, shared)
    assert same == shared, (frame, shared - same)


def test_the_two_part_company_exactly_where_a_guard_fires():
    """A flat frame, which the prototype reads 281 impossible zeros on, and
    a NaN close, whose 20 windows the prototype also reads 0 on because a
    NaN mean makes every comparison False."""
    assert int(ts_cross_mean_20(_flat()).notna().sum()) == 0
    assert int(_prototype(_flat()).notna().sum()) == 281

    close = _walk()
    close.iloc[200] = np.nan
    col, pro = ts_cross_mean_20(close), _prototype(close)
    assert int((col.isna() != pro.isna()).sum()) == LENGTH
    assert sorted(set(pro.iloc[200:220].tolist())) == [0.0]


def test_the_gate_e_row_is_still_owed():
    """Gate E is run by issue-solver after this session, so there is no
    ledger row yet. When the receipt session records one, this test is its
    cue: delete it and let `tests/test_gate_e_ledger.py` take over."""
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert not [r for r in rows if r["indicator"] == "ts_cross_mean_20"]


# ------------------------------------------- what the column actually is


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "heavy-tailed",
                                   "trending", "ar1+", "ar1-"])
def test_it_is_a_choppiness_reading(frame):
    """Item 6, on SYNTHETIC frames with SYNTHETIC high/low (close x 1.004
    and close x 0.996), because `chop` needs a range and these frames have
    only closes. Positive against `chop`, negative against `vhf` -- the two
    read choppiness with opposite signs."""
    close = FRAMES[frame]()
    high, low = _ohlc(close)
    base = ts_cross_mean_20(close)
    assert 0.40 < _spearman(base, chop(high, low, close)) < 0.75
    assert -0.75 < _spearman(base, vhf(close)) < -0.35


@pytest.mark.parametrize("frame", ["walk", "trending", "ar1+"])
def test_the_in_fork_overlap_with_the_neighbours_on_the_same_window(frame):
    """`TS_PERMENT_20_3` and `TS_PEAKS_20_2` read the SAME 20 closes and
    are the two columns most at risk of restating this one. They do not:
    +0.21 .. +0.49 and +0.21 .. +0.36 on six frames, nowhere near the 0.90
    line. `LEAN_MOMERSION_20` is the momentum/reversion neighbour and reads
    the other way, -0.17 .. -0.29."""
    close = FRAMES[frame]()
    base = ts_cross_mean_20(close)
    assert 0.15 < _spearman(base, ts_perment_20(close)) < 0.60
    assert 0.15 < _spearman(base, ts_peaks_20(close)) < 0.50
    assert -0.40 < _spearman(base, lean_momersion_20(close)) < -0.10


def test_it_is_dispersion_upside_down_and_not_volatility():
    """The single most important number for a consumer: a window whose log
    closes spread out is a window that trended, and a trending window
    crosses its mean once. -0.6827 against the window's own log-close
    standard deviation, +0.1045 against its realised volatility, -0.1178
    against the close itself."""
    close = _walk()
    base = ts_cross_mean_20(close)
    a = np.log(close.to_numpy())
    W = sliding_window_view(a, LENGTH)
    rwin = sliding_window_view(np.diff(a), LENGTH - 1)

    def _as_series(v):
        return Series(np.concatenate([np.full(LENGTH - 1, np.nan), v]),
                      index=close.index)

    assert -0.80 < _spearman(base, _as_series(W.std(1, ddof=1))) < -0.55
    assert -0.10 < _spearman(base, _as_series(rwin.std(1, ddof=1))) < 0.30
    assert abs(_spearman(base, close)) < 0.30
    assert -0.55 < _spearman(
        base, _as_series(np.abs(W[:, -1] - W[:, 0]))) < -0.25


def test_the_level_to_expect_on_independent_windows():
    """20,000 INDEPENDENT windows, so the relation is not an artefact of
    overlap. A driftless walk sits near 3.7, a strongly trending one near
    1.2, and log closes that are white noise rather than a walk near 9.8.

    ⚠ This pins the STATISTIC, not the shipped function: 20,000 one-window
    calls would be a slow way to say the same thing. What transfers it is
    Gate A1's bit-equality against the source applied window by window."""
    rng = np.random.default_rng(2026)
    walk = np.cumsum(rng.standard_normal((20000, LENGTH)), axis=1)
    drift = np.cumsum(rng.standard_normal((20000, LENGTH)) + 1.0, axis=1)
    noise = rng.standard_normal((20000, LENGTH))

    def _mean_count(W):
        s = W > W.mean(1, keepdims=True)
        return float((s[:, 1:] != s[:, :-1]).sum(1).mean())

    assert 3.2 < _mean_count(walk) < 4.2
    assert 1.0 < _mean_count(drift) < 1.5
    assert 9.0 < _mean_count(noise) < 10.5


# ---------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    close = _walk(400)
    out = ts_cross_mean_20(close)
    assert out.name == f"TS_CROSS_MEAN_{LENGTH}"
    assert out.category == "statistics"
    assert "ts_cross_mean_20" in pandas_ta.Category["statistics"]
    df = pd.DataFrame({"close": close})
    df.index = pd.date_range("2020-01-01", periods=len(close), freq="D")
    got = df.ta.ts_cross_mean_20()
    assert got.name == f"TS_CROSS_MEAN_{LENGTH}"
    pd.testing.assert_series_equal(got.reset_index(drop=True),
                                   out.reset_index(drop=True))


@pytest.mark.parametrize("length,name", [(None, 20), (0, 20), (2, 20),
                                         (-5, 20), (60, 60)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, name):
    assert ts_cross_mean_20(_walk(400), length=length).name \
        == f"TS_CROSS_MEAN_{name}"


def test_length_two_would_be_identically_one_which_is_why_it_is_refused():
    """The reason for `MIN_LENGTH`, shown rather than asserted: of two
    unequal numbers exactly one is above their midpoint, so the single
    adjacent pair always straddles it."""
    a = np.log(_walk(400).to_numpy())
    W = sliding_window_view(a, 2)
    s = W > (W.sum(axis=1) / 2)[:, None]
    assert set(np.unique((s[:, 1:] != s[:, :-1]).sum(1)).tolist()) == {1}


def test_length_three_takes_exactly_one_and_two():
    col = ts_cross_mean_20(_walk(400), length=3).dropna()
    assert sorted(set(col.tolist())) == [1.0, 2.0]


def test_too_short_an_input_returns_none():
    """`length` CLOSES, so `length` of them are enough."""
    assert ts_cross_mean_20(_walk(LENGTH - 1)) is None
    assert int(ts_cross_mean_20(_walk(LENGTH)).notna().sum()) == 1


def test_offset_and_fillna():
    close = _walk(400)
    base = ts_cross_mean_20(close)
    pd.testing.assert_series_equal(ts_cross_mean_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_cross_mean_20(close, offset=-2),
                                   base.shift(-2), check_names=False)
    filled = ts_cross_mean_20(close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert bool((filled.iloc[:LENGTH - 1] == 0.0).all())


def test_the_module_does_not_import_the_package_root():
    """The `TypeError: 'module' object is not callable` trap in CLAUDE.md:
    a helper is imported from its own module, never from the package."""
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert "from pandas_ta.statistics import" not in src
    assert "from pandas_ta.overlap import" not in src


def test_the_count_is_spelled_column_by_column_not_as_a_matrix():
    """A cost choice, pinned because the two spellings agree on every count
    and only the memory separates them: the source's own two lines,
    `above = windows > mean[:, None]` and `above[:, 1:] != above[:, :-1]`,
    peak at 218.8 MB on 400,000 bars at `length` 250 where this form stays
    at 29.2 MB (docs/TsCrossMean20Measured.md, Z). ⚠ TIME is not a reason
    either way, and no direction is claimed from it: which spelling wins
    at a given `length` changed between runs of the same measurement --
    at `length` 60 the winner has gone BOTH WAYS across the runs on
    record. The PEAKS are the claim. If the one-liner is restored,
    re-measure before accepting it."""
    code = [ln for ln in open(_REAL.__file__, encoding="utf-8").read()
            .splitlines() if not ln.lstrip().startswith("#")]
    body = "\n".join(code)
    assert "for j in range(1, length):" in body
    assert "windows > mean[:, None]" not in body

    matrix = _load_mutant(
        "    count = np.zeros(windows.shape[0], dtype=np.int64)\n"
        "    prev = windows[:, 0] > mean\n"
        "    for j in range(1, length):\n"
        "        cur = windows[:, j] > mean\n"
        "        count += cur != prev\n"
        "        prev = cur",
        "    above = windows > mean[:, None]\n"
        "    count = np.count_nonzero(above[:, 1:] != above[:, :-1], axis=1)")
    for length in (3, LENGTH, 60):
        close = _walk()
        masks, shared, same = _agree(
            ts_cross_mean_20(close, length=length),
            matrix.ts_cross_mean_20(close, length=length))
        assert masks and same == shared == N - length + 1, (length, same)
