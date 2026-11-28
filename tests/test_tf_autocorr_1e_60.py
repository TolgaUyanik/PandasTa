# -*- coding: utf-8 -*-
"""TF-AUTOCORR-1E-60: `tf_autocorr_1e_60`, the first 1/e crossing of the
autocorrelation of log price over 60 bars (PandasTa issue #114).

    TFAUTOCORR1E_60 = the smallest lag k in 1..20 whose ADJUSTED
                      autocorrelation of the window's 60 log prices is
                      below 1/e, or 21 when no lag in 1..20 is

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line.** TSFEL
   is not a dependency of this package, is NOT installed in this worktree
   and web access is unavailable, so "TSFEL (BSD-3-Clause)" is an
   attribution and not an oracle -- `test_the_source_library_is_not_readable_here`
   asserts that, so the limitation fails loudly if the environment ever
   changes. Nothing in this file describes TSFEL's source text. What IS
   checkable is pinned five ways:

   * the screen prototype of `docs/issues/screen/ind_screen_r2.py`
     (candidate `tf_autocorr_1e_60`, `roll(np.log(c), 60, _acf_first_1e)`),
     retyped here because that file is gitignored, and IMPORTED as well by
     `docs/measure_tf_autocorr_1e_60.py` §A1b when the owner's tree is
     present: bit-equal on EVERY fired bar of four 1,500-bar frames
     (1,441 bars each on this machine);
   * a plain-Python `math.fsum` spelling over explicit slices -- no numpy
     windowing, no noise floor, `math.log` of the absolute price -- written
     from the formula text, bit-equal on every bar of three 400-bar frames
     here (the Python loop is slow) and of four 1,500-bar frames in the
     harness, §A2;
   * `statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False)` applied to
     `log(close)` window by window. statsmodels IS installed here; the test
     skips if it ever is not. This is the one place the "adjusted" reading
     could have been wrong, so it is measured and not assumed;
   * a HAND-DERIVED case in exact rational arithmetic: on an exactly
     geometric path the window's log price is a straight line, whose
     adjusted ACF is a closed form in `fractions.Fraction` with no float
     anywhere. It says the first lag below 1/e is 11 at `length` 40, 12 at
     45, 16 at 60 and none (21) at 100 and 250, and the module reads exactly
     that on every fired bar;
   * the extremes, constructed: a path alternating up and down every bar
     reads the constant 1, and a cosine in log price reads 1 / 2 / 4 / 7 /
     16 at period 4 / 10 / 20 / 40 / 120.

2. **The THREE differences from the prototype, and which of them is only a
   spelling.** The ARITHMETIC difference is one: the prototype reads
   `np.log(close)`, the module cumulates the window's own
   `log(close/close[1])` from zero. The two differ by an additive constant
   that the demeaning removes, and they are bit-equal on every fired bar of
   four frames and at price levels from 1e-6 to 1e9
   (`test_cumulating_the_window_s_own_log_returns_is_invisible`,
   `test_the_two_spellings_agree_at_every_price_level`). What it buys is
   Gate D by CONSTRUCTION: `8a / 8b` is the same double as `a / b`, so an
   exact binary rescale cancels before any transcendental runs.

   The other two are BEHAVIOURAL, on inputs a clean frame never contains,
   and they are pinned rather than argued
   (`test_the_prototype_reports_the_sentinel_where_this_module_reports_nan`,
   `test_the_prototype_has_no_floor_and_reads_rounding_noise`). The
   prototype's only guard is `np.where(var == 0, np.nan, out)`, and a
   window holding a bad close has `var` NaN, not 0 -- so the prototype
   reports the **21 sentinel** on the 60 bars this module empties (a
   SUBNORMAL close reads 1 there instead, `log(1e-310)` being a large
   finite number), with the two bit-equal on all 1,381 bars either side.
   And the prototype has no noise floor: on a price flat at 1e6 stepping
   one double ulp a bar it fires all 1,441 bars reading 17 to 21, where
   this module fires none. "The port and the screened quantity are the same
   column" therefore holds on every window whose closes are finite, normal
   and positive, and is not claimed beyond that.

3. **Gate B, by mutant, on three frames and three lengths.** Six mutants,
   each `importlib`-read and `exec`'d in memory: the column back-dated by
   `length`; the column written one bar early; the log return read one bar
   ahead; the window mean taken from the next window; the lag product taken
   from the next window; and the standard deviation the noise floor reads
   taken from the next window. The real module leaks **0 of 35** offsets of
   a future-perturbation sweep on a walk, a tick-rounded walk and an AR(1)
   path, and 0 of 35 again at `length` 40, 100 and 250. The one-bar mutants
   are caught on 20 to 35 of 35 at the default and as few as 5 of 35 at
   `length` 250, and the cells under 35 are asserted with their MECHANISM
   rather than excused: a one-bar look-ahead can move exactly ONE bar of the
   prefix, J - 1, which `test_a_one_bar_mutant_can_only_move_the_bar_before_the_cut`
   asserts directly, so a miss is an offset where one integer did not
   change. The density behind that is measured too: 1,014 of 1,440
   consecutive bar pairs on the walk carry the same value, and 1,153 of
   1,250 at `length` 250. The sixth mutant needs a frame where the floor
   fires at all, so it is swept on walks carrying 61 identical closes.

4. **Gate D, and that x8 is bit-identical by construction rather than by
   luck.** Bit-identical under x8, x64, 2**-40 and 2**40 on each of four
   frames and at each of `length` 40, 45, 100 and 250 -- sixteen cells each
   way, every one run. x10, x3.7, x0.1 and x1.0000001 come out
   bit-identical too, which the arithmetic does NOT promise for an integer
   decided by a float comparison; what makes it hold is measured and pinned
   -- the smallest margin any window has to 1/e at its deciding lag is
   2.1e-05 on the walk, 1.4e-05 tick-rounded, 5.5e-06 on the AR(1) path and
   6.5e-03 on the cosine, with 0 exact ties in 5,764 windows -- and the
   inexact assertion is deliberately loose (at most one bar may differ)
   because that margin is a measurement on four frames, not a guarantee.
   The column is also bit-identical when the window's log returns are
   rescaled x0.5, x2 or x10, so it is blind to volatility outright; it is
   NOT blind to drift (a +0.004 log drift a bar moves all but 60 of 1,441
   bars, by up to 14 lags).

5. **What the column is.** An INTEGER in [1, 21] that reads how STRAIGHT
   the window is. An exact geometric path reads 16 everywhere; an
   alternating path reads 1; adding drift to an iid walk lifts the median
   from 8 to 16. ⚠ The 21 sentinel means "no crossing in 20 lags" and at
   `length` 60 NOTHING measured here reaches it -- 0 of 5,764 fired bars,
   0 of 4,000 iid-increment windows, 0 of a 30,000-window directed search
   whose best was 18 -- while at `length` 100 and 250 it is ordinary. The
   test pins the reachable range and the absence at the default as a
   measurement on these frames, not as a theorem: the per-lag upper bound
   at lag 20 is 1.0607, well above 1/e, so nothing here rules the sentinel
   out.

6. **The noise floor, and that it is INERT on anything price-shaped.** 0 of
   1,441 windows reach it on each of four frames, and 0 on a monotone
   one-tick-per-bar path even at price 1e9 with a 0.01 tick. What it buys is
   the ULP band, where the unguarded reading is ordinary-looking rather than
   absurd: a price flat at 1e6 stepping one double ulp a bar is
   mathematically an exact geometric ladder and reads 16 unguarded -- the
   top of the trend scale -- and a price flat but for a single 1-ulp step
   reads 1 to 15 unguarded. Both are NaN here, and the COST (those paths
   have a defined mathematical answer that this column refuses) is pinned
   with them.

7. **Five-point wiring** (`Category`, the accessor, the export), the NaN
   behaviour of a bad close (a NaN, zero, negative, infinite or subnormal
   close empties exactly the 60 windows that contain it, a close pair whose
   ratio overflows 59, and nothing before the hole moves), the `length`
   guard band (below 40, including 0, negatives and fractions that truncate
   below 40, falls back to 60) and that the chunk budget cannot change a
   value (budgets 1, 64, 999 and 10**9).

Every number above comes from `docs/measure_tf_autocorr_1e_60.py`, whose run
is transcribed in `docs/TfAutocorr1E60Measured.md`. Counts that are counts of
LAST BITS are asserted as bounds rather than as equalities, because they move
with numpy's kernels; §F of the Measured doc lists what was re-run under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` and what moved
(nothing did). Gate E is owed: the launcher runs `gate_e_overlap.py` after
this session and a later session records the `docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.
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

from .context import pandas_ta as ta
from pandas_ta.statistics.tf_autocorr_1e_60 import (
    MIN_LENGTH, NLAGS, NO_CROSSING, NOISE_FLOOR, THRESHOLD,
    tf_autocorr_1e_60)

LENGTH = 60
_REAL = importlib.import_module("pandas_ta.statistics.tf_autocorr_1e_60")


# ------------------------------------------------------------- frames
def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _sine(n=1500, period=40.0, amp=0.10):
    t = np.arange(n, dtype=float)
    return Series(100.0 * np.exp(amp * np.sin(2 * np.pi * t / period)))


def _ladder(n=1500, step=0.01, start=100.0):
    """An exactly geometric path: log price is a straight line."""
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def _alternating(n=1500, move=0.02):
    r = np.where(np.arange(n) % 2 == 0, move, -move)
    return Series(100.0 * np.exp(np.cumsum(r)))


def _ulp_ladder(price, n, every=1):
    out = np.empty(n)
    v = price
    for i in range(n):
        out[i] = v
        if (i + 1) % every == 0:
            v = np.nextafter(v, np.inf)
    return Series(out)


FRAMES = {
    "walk": _walk(),
    "tick-rounded": _tick_rounded(),
    "ar1": _ar1(),
    "sine": _sine(),
}
FIRED = 1500 - LENGTH + 1          # every bar with a full window


def _both(a, b):
    a = a.to_numpy(dtype=float)
    b = np.asarray(b, dtype=float)
    return a, b, (~np.isnan(a)) & (~np.isnan(b))


def _bit_equal_everywhere(a, b):
    """(masks equal, bars both define, bars that differ)."""
    a, b, m = _both(a, b)
    masks = bool((np.isnan(a) == np.isnan(b)).all())
    return masks, int(m.sum()), int((a[m] != b[m]).sum())


# ------------------------------------------------------------- Gate A
def _proto_acf_first_1e(W, nlags=NLAGS):
    """`_acf_first_1e` of `docs/issues/screen/ind_screen_r2.py:190-201`,
    retyped (that file is gitignored). It carries NO noise floor."""
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


def _proto_column(close, length=LENGTH):
    """The prototype's own line, `roll(np.log(c), 60, _acf_first_1e)`."""
    with np.errstate(divide="ignore", invalid="ignore"):
        a = np.log(close.to_numpy(dtype=float))
    w = sliding_window_view(a, length)
    out = np.full(len(a), np.nan)
    out[length - 1:] = _proto_acf_first_1e(w)
    return Series(out, index=close.index)


def _scalar_column(close, length=LENGTH, nlags=NLAGS):
    """An independent spelling: plain Python, `math.fsum`, explicit slices,
    `math.log` of the ABSOLUTE price, no numpy windowing and no floor."""
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


def _ramp_crossing(n, nlags=NLAGS):
    """The first lag below 1/e for a STRAIGHT LINE of `n` log prices, in
    exact rational arithmetic -- no float anywhere.

    d[t] = t - (n-1)/2; var = mean(d*d); ACF(k) = sum d[t] d[t+k] / (n-k)
    / var. 1/e is a 60-digit rational, which is enough: §A of the Measured
    doc records the smallest margin on these frames as 5.5e-06.
    """
    half = Fraction(n - 1, 2)
    d = [Fraction(t) - half for t in range(n)]
    var = sum(v * v for v in d) / n
    inv_e = Fraction(
        "0.367879441171442321595523770161460867445811131031767834507836")
    for k in range(1, nlags + 1):
        cov = sum(d[t] * d[t + k] for t in range(n - k)) / (n - k)
        if cov / var < inv_e:
            return k
    return nlags + 1


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_bit_equal_to_the_retyped_screen_prototype(frame):
    """Gate A's first oracle. `roll(np.log(c), 60, _acf_first_1e)` is the
    whole of the prototype; the module must reproduce it on every bar both
    define, not merely correlate with it."""
    close = FRAMES[frame]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                _proto_column(close))
    assert masks
    assert both == FIRED
    assert differ == 0


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "ar1"])
def test_bit_equal_to_an_independent_fsum_spelling(frame):
    """Gate A's second oracle, sharing no array machinery and no noise floor
    with the module. A 400-bar frame keeps the Python loop cheap; the full
    1,500-bar run is in `docs/measure_tf_autocorr_1e_60.py` §A2."""
    close = FRAMES[frame].iloc[:400]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                _scalar_column(close))
    assert masks
    assert both == 400 - LENGTH + 1
    assert differ == 0


def test_the_source_library_is_not_readable_here():
    """The attribution is to the feature NAME and the issue's line. If TSFEL
    ever becomes importable, Gate A should be redone against its own code
    and this test is the alarm."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfel")


@pytest.mark.parametrize("frame", ["walk", "ar1"])
def test_statsmodels_adjusted_acf_agrees(frame):
    """The ADJUSTED reading is the one the wording could have got wrong, so
    it is checked against the library that defines it."""
    acf = pytest.importorskip("statsmodels.tsa.stattools").acf
    close = FRAMES[frame].iloc[:500]
    a = np.log(close.to_numpy(dtype=float))
    out = np.full(len(a), np.nan)
    for t in range(LENGTH - 1, len(a)):
        x = a[t - LENGTH + 1:t + 1]
        ac = acf(x, adjusted=True, fft=False, nlags=NLAGS)[1:]
        hit = np.flatnonzero(ac < math.exp(-1.0))
        out[t] = float(hit[0] + 1) if hit.size else float(NO_CROSSING)
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close), out)
    assert masks
    assert both == 500 - LENGTH + 1
    assert differ == 0


@pytest.mark.parametrize("length,expected", [(40, 11), (45, 12), (60, 16),
                                             (100, 21), (250, 21)])
def test_an_exact_geometric_path_matches_the_closed_form(length, expected):
    """The hand-derived case. A geometric path's log price is a straight
    line, whose adjusted ACF has a closed form in exact rationals; the
    module must read it on every fired bar."""
    assert _ramp_crossing(length) == expected
    col = tf_autocorr_1e_60(_ladder(), length=length)
    assert set(np.unique(col.dropna().to_numpy())) == {float(expected)}
    assert int(col.notna().sum()) == 1500 - length + 1


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_the_geometric_reading_does_not_depend_on_the_step(step):
    """16 is the shape of a straight line, not the size of its slope."""
    col = tf_autocorr_1e_60(_ladder(step=step))
    assert set(np.unique(col.dropna().to_numpy())) == {16.0}


def test_an_alternating_path_reads_the_bottom_of_the_scale():
    col = tf_autocorr_1e_60(_alternating())
    assert set(np.unique(col.dropna().to_numpy())) == {1.0}


@pytest.mark.parametrize("period,expected", [(4, 1), (10, 2), (20, 4),
                                             (40, 7), (120, 16)])
def test_a_cosine_in_log_price_reads_its_period(period, expected):
    """One window, built directly, so the reading is the window's own shape
    and not an average over a frame."""
    x = np.cos(2 * np.pi * np.arange(LENGTH) / period)
    col = tf_autocorr_1e_60(Series(np.exp(x)), length=LENGTH)
    assert float(col.iloc[-1]) == float(expected)


def _plain_log_column(close, length=LENGTH):
    """Gate A's fifth spelling: this module's arithmetic, but reading
    `log(close)` directly instead of cumulating the window's own log returns.
    The one difference in the ARITHMETIC, isolated."""
    a = np.log(close.to_numpy(dtype=float))
    x = sliding_window_view(a, length)
    d = x - x.mean(axis=1, keepdims=True)
    var = (d * d).mean(axis=1)
    safe = np.where(var > 0.0, var, 1.0)
    rows = np.full(x.shape[0], float(NO_CROSSING))
    done = np.zeros(x.shape[0], dtype=bool)
    for k in range(1, NLAGS + 1):
        ac = (d[:, :-k] * d[:, k:]).mean(axis=1) / safe
        hit = (ac < THRESHOLD) & ~done
        rows[hit] = k
        done |= hit
    out = np.full(len(a), np.nan)
    out[length - 1:] = np.where(np.sqrt(var) > NOISE_FLOOR, rows, np.nan)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_cumulating_the_window_s_own_log_returns_is_invisible(frame):
    """The one difference in the ARITHMETIC, isolated: the same arithmetic
    reading `log(close)` directly must give the same integers. The other two
    differences are BEHAVIOURAL and are pinned by
    `test_the_prototype_reports_the_sentinel_where_this_module_reports_nan`
    and `test_the_prototype_has_no_floor_and_reads_rounding_noise`."""
    close = FRAMES[frame]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                _plain_log_column(close))
    assert masks
    assert both == FIRED
    assert differ == 0


@pytest.mark.parametrize("price", [1e-6, 1.0, 1e3, 1e6, 1e9])
def test_the_two_spellings_agree_at_every_price_level(price):
    """Where `log(close)` would lose digits to cancellation -- a window of
    width 0.05 around log(1e9) = 20.7 -- and the ratio form never forms the
    large operand at all."""
    close = _walk() * (price / 100.0)
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                _plain_log_column(close))
    assert masks
    assert both == FIRED        # without this, two empty columns would pass
    assert differ == 0


@pytest.mark.parametrize("bad,sentinel", [(np.nan, 21.0), (0.0, 21.0),
                                          (-5.0, 21.0), (np.inf, 21.0),
                                          (1e-310, 1.0)])
def test_the_prototype_reports_the_sentinel_where_this_module_reports_nan(
        bad, sentinel):
    """Behavioural divergence #1, measured rather than asserted in prose.
    The prototype's only guard is `np.where(var == 0, np.nan, out)`; a
    window holding a bad close has `var` NaN, and `NaN == 0` is False, so
    the prototype emits a NUMBER there. A subnormal close is the odd one:
    `log(1e-310)` is a large finite number, so the window is dominated by
    one outlier and the lag-1 autocorrelation collapses to 1 instead."""
    close = _walk().copy()
    close.iloc[700] = bad
    mine = tf_autocorr_1e_60(close).to_numpy(dtype=float)
    theirs = _proto_column(close).to_numpy(dtype=float)
    only_mine = np.isnan(mine) & ~np.isnan(theirs)
    assert int(only_mine.sum()) == LENGTH
    assert int((~np.isnan(mine) & np.isnan(theirs)).sum()) == 0
    assert set(np.unique(theirs[only_mine])) == {sentinel}
    both = ~np.isnan(mine) & ~np.isnan(theirs)
    assert int(both.sum()) == FIRED - LENGTH
    assert int((mine[both] != theirs[both]).sum()) == 0


def test_the_prototype_has_no_floor_and_reads_rounding_noise():
    """Behavioural divergence #2. On a price flat at 1e6 stepping one
    double ulp a bar, the prototype fires every bar off `log(close)`'s
    own rounding; this module fires none. (The unguarded form of THIS
    module reads a constant 16 on the same path -- see
    `test_what_the_floor_buys_on_a_ulp_ladder` -- so the two disagree
    about what the noise says, which is the point of refusing it.)"""
    close = _ulp_ladder(1e6, 1500)
    assert int(tf_autocorr_1e_60(close).notna().sum()) == 0
    theirs = _proto_column(close).dropna().to_numpy()
    assert theirs.size == FIRED
    assert float(theirs.min()) >= 15.0
    assert np.unique(theirs).size >= 2


def _variant(close, length=LENGTH, biased=False, inclusive=False,
             on_returns=False):
    """The module's quantity under one changed reading at a time."""
    c = close.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        g = np.log(c[1:] / c[:-1])
    g = np.where(np.isfinite(g), g, np.nan)
    out = np.full(c.size, np.nan)
    if on_returns:
        x = sliding_window_view(g, length).copy()
        first = length
    else:
        win = sliding_window_view(g, length - 1)
        x = np.concatenate(
            [np.zeros((win.shape[0], 1)), np.cumsum(win, axis=1)], axis=1)
        first = length - 1
    d = x - x.mean(axis=1, keepdims=True)
    var = (d * d).mean(axis=1)
    safe = np.where(var > 0.0, var, 1.0)
    rows = np.full(x.shape[0], float(NO_CROSSING))
    done = np.zeros(x.shape[0], dtype=bool)
    width = x.shape[1]
    for k in range(1, NLAGS + 1):
        s = (d[:, :-k] * d[:, k:]).sum(axis=1)
        ac = (s / (width if biased else (width - k))) / safe
        hit = ((ac <= THRESHOLD) if inclusive else (ac < THRESHOLD)) & ~done
        rows[hit] = k
        done |= hit
    out[first:first + rows.size] = np.where(np.sqrt(var) > NOISE_FLOOR, rows,
                                            np.nan)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "ar1"])
def test_the_biased_reading_is_a_different_column(frame):
    """Reading #1 the wording leaves open, priced. Dividing the lag-k
    products by `length` instead of by `length - k` is NOT a rescaling: it
    disagrees on most bars and by several lags."""
    close = FRAMES[frame]
    mine, other = tf_autocorr_1e_60(close), _variant(close, biased=True)
    a, b, m = _both(mine, other)
    assert int((a[m] == b[m]).sum()) < 0.5 * int(m.sum())
    assert float(np.abs(a[m] - b[m]).max()) >= 5.0
    rho = float(mine[m].corr(other[m], method="spearman"))
    assert 0.95 < rho < 0.995


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_inclusive_reading_is_unreachable_on_these_frames(frame):
    """Reading #2: `<=` against `<`. They differ only on an EXACT tie with
    1/e, of which these frames have none, so the choice is pinned as
    unreachable rather than as cosmetic."""
    close = FRAMES[frame]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                _variant(close,
                                                         inclusive=True))
    assert masks
    assert both == FIRED        # without this, two empty columns would pass
    assert differ == 0


@pytest.mark.parametrize("frame", ["walk", "tick-rounded"])
def test_the_same_construction_on_returns_is_a_constant(frame):
    """Reading #3, and the one that decides the column exists at all: the
    issue puts the ACF on LOG PRICE. The same construction on log RETURNS
    is the constant 1 on an iid-shaped path -- returns are near
    uncorrelated, so lag 1 is already below 1/e -- and would fail Gate D's
    "not constant" outright."""
    other = _variant(FRAMES[frame], on_returns=True).dropna()
    assert other.nunique() == 1
    assert float(other.iloc[0]) == 1.0
    assert tf_autocorr_1e_60(FRAMES[frame]).dropna().nunique() >= 10


# ------------------------------------------------------------- Gate B
WRITE_SHIFT_MUTANT = (
    "    result = Series(out, index=close.index)",
    "    result = Series(out, index=close.index).shift(-length)")
WRITE_EARLY_MUTANT = (
    "            out[length - 1 + a:length - 1 + b] = _first_1e_rows(win[a:b])",
    "            out[length - 2 + a:length - 2 + b] = _first_1e_rows(win[a:b])")
FORWARD_RETURN_MUTANT = (
    "        g = np.log(c[1:] / c[:-1])",
    "        g = np.log(np.roll(c, -1)[1:] / c[:-1])")
FORWARD_MEAN_MUTANT = (
    "    d = x - x.mean(axis=1, keepdims=True)",
    "    d = x - np.roll(x.mean(axis=1, keepdims=True), -1, axis=0)")
FORWARD_PRODUCT_MUTANT = (
    "        acf = (d[:, :-k] * d[:, k:]).mean(axis=1) / safe",
    "        acf = (d[:, :-k] * np.roll(d, -1, axis=0)[:, k:]).mean(axis=1)"
    " / safe")
FORWARD_SD_MUTANT = (
    "    sd = np.sqrt(var)",
    "    sd = np.roll(np.sqrt(var), -1)")

MUTANTS = [WRITE_SHIFT_MUTANT, WRITE_EARLY_MUTANT, FORWARD_RETURN_MUTANT,
           FORWARD_MEAN_MUTANT, FORWARD_PRODUCT_MUTANT]
MUTANT_IDS = ["write_shift", "write_early", "forward_return", "forward_mean",
              "forward_product"]
ONE_BAR_MUTANTS = MUTANTS[1:]
ONE_BAR_IDS = MUTANT_IDS[1:]
OFFSETS = list(range(120, 1500, 40))      # 35 offsets, past the warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "ar1": (_ar1(), _ar1(seed=8)),
}
#: Lower bounds on the offsets each mutant is caught at, NOT the measured
#: counts: a catch is an integer changing, so the exact cell moves with
#: numpy's kernels and with the frame. Measured by
#: `python docs/measure_tf_autocorr_1e_60.py B` on this machine:
#: write_shift 35/35/35, write_early 34/32/35, forward_return 33/28/34,
#: forward_mean 25/20/23, forward_product 31/31/34 (walk / tick-rounded /
#: ar1), with the same figures under
#: `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.
CAUGHT_FLOOR = {"write_shift": 30, "write_early": 25, "forward_return": 20,
                "forward_mean": 15, "forward_product": 25}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_tf_autocorr_1e_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leak_offsets(fn, close, other, offsets=OFFSETS):
    """Replace every bar from J onward with a different path; collect the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hit = []
    for j in offsets:
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


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_real_module_never_reads_the_future(frame):
    close, other = PAIRS[frame]
    assert _leak_offsets(tf_autocorr_1e_60, close, other) == []


@pytest.mark.parametrize("mutant,mid", list(zip(MUTANTS, MUTANT_IDS)),
                         ids=MUTANT_IDS)
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_caught(mutant, mid, frame):
    """Gate B proper. Each mutant moves one write or one read forward by a
    bar; the sweep must see it. The bound is a floor and not the measured
    cell -- see CAUGHT_FLOOR and
    `test_a_one_bar_mutant_can_only_move_the_bar_before_the_cut`."""
    mod = _load_mutant(*mutant)
    close, other = PAIRS[frame]
    caught = len(_leak_offsets(mod.tf_autocorr_1e_60, close, other))
    assert caught >= CAUGHT_FLOOR[mid], f"{mid}/{frame}: {caught}/{len(OFFSETS)}"


@pytest.mark.parametrize("mutant", ONE_BAR_MUTANTS, ids=ONE_BAR_IDS)
def test_a_one_bar_mutant_can_only_move_the_bar_before_the_cut(mutant):
    """The mechanism behind every cell under 35, asserted rather than
    argued. A one-bar look-ahead changes the value of bar J - 1 and of no
    other bar before J, because no earlier bar's window reaches close[J].
    So a missed offset is one where that single INTEGER happened not to
    change -- a limit of the sweep, not a second kind of leak."""
    mod = _load_mutant(*mutant)
    close, other = PAIRS["walk"]
    base = mod.tf_autocorr_1e_60(close)
    seen = set()
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = mod.tf_autocorr_1e_60(p)
        a, b = base.iloc[:j], out.iloc[:j]
        moved = np.flatnonzero(((a != b) & ~(a.isna() & b.isna())).to_numpy())
        seen.add(tuple((moved - j).tolist()))
    assert seen == {(), (-1,)}


@pytest.mark.parametrize("frame,tied_at_least", [("walk", 900),
                                                 ("tick-rounded", 950),
                                                 ("ar1", 930)])
def test_the_column_ties_often_enough_to_hide_a_one_bar_shift(frame,
                                                              tied_at_least):
    """The density behind that mechanism. Measured on this machine: 1,014 /
    1,058 / 1,041 of 1,440 consecutive bar pairs carry the SAME integer, so
    moving a window by one bar frequently changes nothing. Bounds, not the
    cells, because the cells are counts of a float decision."""
    v = tf_autocorr_1e_60(FRAMES[frame]).dropna().to_numpy()
    assert v.size == FIRED
    assert int((v[1:] == v[:-1]).sum()) >= tied_at_least


@pytest.mark.parametrize("length", [40, 100, 250])
def test_the_sweep_at_non_default_lengths(length):
    """`length` is free and the sweep above runs the default only. The real
    module leaks nothing at 40, 100 and 250 as well, and the back-dating
    mutant is still caught almost everywhere. The ONE-bar mutants are not
    asserted here: at `length` 250 the column carries the same value on
    1,153 of 1,250 consecutive bar pairs, and forward_mean falls to 5 of 35
    -- a limit of the sweep that
    `test_a_one_bar_mutant_can_only_move_the_bar_before_the_cut` covers by
    mechanism instead."""
    close, other = PAIRS["walk"]

    def real(c):
        return tf_autocorr_1e_60(c, length=length)

    mod = _load_mutant(*WRITE_SHIFT_MUTANT)

    def mutant(c):
        return mod.tf_autocorr_1e_60(c, length=length)

    assert _leak_offsets(real, close, other) == []
    assert len(_leak_offsets(mutant, close, other)) >= 30


@pytest.mark.parametrize("length,tied_at_least", [(40, 900), (250, 1050)])
def test_the_tie_density_grows_with_length(length, tied_at_least):
    """Why the non-default sweep asserts less. Measured: 1,013 of 1,460
    pairs tie at `length` 40 and 1,153 of 1,250 at `length` 250 -- 69% of
    the pairs against 92%."""
    v = tf_autocorr_1e_60(_walk(), length=length).dropna().to_numpy()
    assert int((v[1:] == v[:-1]).sum()) >= tied_at_least


@pytest.mark.parametrize("plant", [280, 600, 920, 1240])
def test_the_mutant_of_the_floor_s_own_windowed_input_is_caught_too(plant):
    """The sixth mutant. `sd` is the second windowed quantity this module
    builds, and the floor it feeds is a NO-OP on a continuous frame -- so
    it is swept on a walk carrying 61 identical closes ending at `plant`,
    where the floor fires. The real module still leaks nothing there.

    The mutant leaks at EXACTLY one offset, `plant` itself, and that is the
    mechanism rather than a weakness: reading the next window's `sd` can
    only change a bar whose neighbour sits on the other side of the floor,
    which on this frame is the last bar of the planted flat run. Every
    `plant` here is therefore one of the sweep's own offsets; measured over
    all 35, real 0 of 35 and the mutant caught 35 of 35
    (`docs/measure_tf_autocorr_1e_60.py` §B)."""
    assert plant in OFFSETS
    mod = _load_mutant(*FORWARD_SD_MUTANT)
    other = _walk(seed=98)
    c = _walk(seed=21).to_numpy().copy()
    c[plant - LENGTH:plant + 1] = c[plant - LENGTH]
    planted = Series(c)
    assert _leak_offsets(tf_autocorr_1e_60, planted, other) == []
    assert _leak_offsets(mod.tf_autocorr_1e_60, planted, other) == [plant]


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    col = tf_autocorr_1e_60(FRAMES[frame])
    assert int(col.notna().sum()) == FIRED
    assert int(col.notna().to_numpy().argmax()) == LENGTH - 1
    assert bool(col.iloc[:LENGTH - 1].isna().all())


@pytest.mark.parametrize("frame,distinct_at_least,lo,hi",
                         [("walk", 10, 2, 19), ("tick-rounded", 10, 2, 19),
                          ("ar1", 10, 2, 19), ("sine", 2, 5, 12)])
def test_the_column_is_not_constant_and_stays_in_range(frame,
                                                       distinct_at_least,
                                                       lo, hi):
    """Gate D's `0 < fires < n` and Gate C's reachability in one. Measured
    on this machine: 15 / 15 / 15 / 3 distinct values, ranges 3-17 / 2-16 /
    3-17 / 7-9."""
    v = tf_autocorr_1e_60(FRAMES[frame]).dropna().to_numpy()
    assert 0 < v.size < len(FRAMES[frame])
    assert np.unique(v).size >= distinct_at_least
    assert float(v.min()) >= lo and float(v.max()) <= hi
    assert set(np.unique(v)) <= {float(k) for k in range(1, NO_CROSSING + 1)}


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_sentinel_is_not_reached_at_the_default_length(frame):
    """⚠ A MEASUREMENT on these frames, not a theorem. The per-lag upper
    bound at lag 20 is 1.0607, well above 1/e, so a NO_CROSSING window at
    `length` 60 is not ruled out -- it was simply never produced here, by
    any of four frames, 4,000 iid-increment windows or a 30,000-window
    directed search (`docs/measure_tf_autocorr_1e_60.py` §A5b, best 18).
    If this test ever fails, the docstring's warning is what needs fixing,
    not the module."""
    v = tf_autocorr_1e_60(FRAMES[frame]).dropna().to_numpy()
    assert int((v == NO_CROSSING).sum()) == 0


@pytest.mark.parametrize("length", [100, 250])
def test_the_sentinel_is_ordinary_at_a_longer_window(length):
    """NLAGS does not scale with `length`, so a longer window runs out of
    lags. An exact geometric ladder reads 21 at both."""
    assert float(tf_autocorr_1e_60(_ladder(), length=length).dropna().max()) \
        == float(NO_CROSSING)
    assert float(tf_autocorr_1e_60(_walk(), length=length).dropna().max()) \
        == float(NO_CROSSING)


@pytest.mark.parametrize("length,name", [(None, "TFAUTOCORR1E_60"),
                                         (0, "TFAUTOCORR1E_60"),
                                         (-5, "TFAUTOCORR1E_60"),
                                         (1, "TFAUTOCORR1E_60"),
                                         (39, "TFAUTOCORR1E_60"),
                                         (39.9, "TFAUTOCORR1E_60"),
                                         (40, "TFAUTOCORR1E_40"),
                                         (100, "TFAUTOCORR1E_100")])
def test_the_length_guard_band(length, name):
    """`MIN_LENGTH` is two points per lag at the longest lag."""
    assert MIN_LENGTH == 2 * NLAGS
    assert tf_autocorr_1e_60(_walk(), length=length).name == name


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_an_exact_binary_rescale_is_bit_identical(frame, factor):
    """Gate D, and it holds BY CONSTRUCTION: every input to the window is
    `log(c[1:] / c[:-1])`, and `8a / 8b` is the same double as `a / b`."""
    close = FRAMES[frame]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                tf_autocorr_1e_60(close * factor))
    assert masks
    assert both == FIRED
    assert differ == 0


@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("length", [40, 45, 100, 250])
def test_the_scale_invariance_holds_at_non_default_lengths(length, factor):
    """All sixteen cells, not just x8 at each length: the docstrings name
    four factors and four lengths, so four by four is what is run."""
    close = _walk()
    masks, both, differ = _bit_equal_everywhere(
        tf_autocorr_1e_60(close, length=length),
        tf_autocorr_1e_60(close * factor, length=length))
    assert masks
    assert both == 1500 - length + 1
    assert differ == 0


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_an_inexact_rescale_moves_at_most_one_bar(frame, factor):
    """⚠ Deliberately LOOSE. The output is an integer decided by a float
    comparison, so an inexact rescale could in principle flip a near-tie.
    It does not on these frames (0 bars move), and the reason is measured
    rather than assumed -- see
    `test_the_decision_never_runs_near_a_rounding_flip`."""
    close = FRAMES[frame]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                tf_autocorr_1e_60(close * factor))
    assert masks
    assert both == FIRED        # without this, two empty columns would pass
    assert differ <= 1


@pytest.mark.parametrize("frame,margin_at_least", [("walk", 1e-6),
                                                   ("tick-rounded", 1e-6),
                                                   ("ar1", 1e-6),
                                                   ("sine", 1e-4)])
def test_the_decision_never_runs_near_a_rounding_flip(frame, margin_at_least):
    """Why the inexact rescales come out bit-identical. Measured smallest
    |ACF(k) - 1/e| at the deciding lag: 2.1e-05 / 1.4e-05 / 5.5e-06 /
    6.5e-03, with 0 exact ties in 5,764 windows -- orders of magnitude from
    a last-bit decision."""
    close = FRAMES[frame]
    c = close.to_numpy(dtype=float)
    g = np.log(c[1:] / c[:-1])
    win = sliding_window_view(g, LENGTH - 1)
    x = np.concatenate([np.zeros((win.shape[0], 1)), np.cumsum(win, axis=1)],
                       axis=1)
    d = x - x.mean(axis=1, keepdims=True)
    var = (d * d).mean(axis=1)
    best = np.full(win.shape[0], np.inf)
    done = np.zeros(win.shape[0], dtype=bool)
    ties = 0
    for k in range(1, NLAGS + 1):
        ac = (d[:, :-k] * d[:, k:]).mean(axis=1) / var
        live = ~done
        best[live] = np.minimum(best[live], np.abs(ac - THRESHOLD)[live])
        ties += int((ac[live] == THRESHOLD).sum())
        done |= (ac < THRESHOLD)
    assert ties == 0
    assert float(best.min()) > margin_at_least


@pytest.mark.parametrize("factor", [0.5, 2.0, 10.0])
def test_it_is_blind_to_the_amplitude_of_the_log_returns(factor):
    """Not a volatility feature, and not approximately: rescaling every log
    return of the window scales `d` by the same constant, which cancels in
    the ratio ACF(k)/ACF(0). Bit-identical, not close."""
    base = _walk()
    lg = np.log(base.to_numpy())
    other = Series(np.exp(lg[0] + factor * (lg - lg[0])))
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(base),
                                                tf_autocorr_1e_60(other))
    assert masks
    assert both == FIRED        # without this, two empty columns would pass
    assert differ == 0


@pytest.mark.parametrize("drift,moves_at_least", [(0.001, 1000),
                                                  (0.004, 1300),
                                                  (0.02, 1300)])
def test_it_is_not_blind_to_drift(drift, moves_at_least):
    """The other half of the previous test: a constant added to the log
    RETURNS is a straightening of the log PRICE, which is exactly what this
    column reads. Measured: 1,271 / 1,381 / 1,406 of 1,441 bars move."""
    base = _walk()
    lg = np.log(base.to_numpy())
    other = Series(np.exp(lg + drift * np.arange(lg.size)))
    a, b, m = _both(tf_autocorr_1e_60(base), tf_autocorr_1e_60(other))
    assert int((a[m] != b[m]).sum()) >= moves_at_least


@pytest.mark.parametrize("drift,median_at_least", [(0.0, 7), (0.005, 12),
                                                   (0.02, 15)])
def test_drift_raises_the_reading(drift, median_at_least):
    """The ordering the column claims, measured: medians 8 / 14 / 16 at a
    drift of 0 / +0.5% / +2% a bar on an iid walk of sigma 1.5%."""
    rng = np.random.default_rng(31)
    r = rng.normal(drift, 0.015, 1500)
    v = tf_autocorr_1e_60(Series(100 * np.exp(np.cumsum(r)))).dropna()
    assert float(v.median()) >= median_at_least


# ------------------------------------------------------- the noise floor
def _unguarded(close, length=LENGTH):
    """This module with the floor relaxed to "the window varies at all"."""
    mod = _load_mutant("    return np.where(sd > NOISE_FLOOR, out, np.nan)",
                       "    return np.where(sd > 0.0, out, np.nan)")
    return mod.tf_autocorr_1e_60(close, length=length)


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_floor_is_inert_on_anything_price_shaped(frame):
    close = FRAMES[frame]
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                _unguarded(close))
    assert masks
    assert both == FIRED
    assert differ == 0


@pytest.mark.parametrize("price,tick", [(50.0, 0.01), (1e6, 0.01),
                                        (1e6, 1e-3), (1e9, 0.01)])
def test_the_floor_costs_nothing_on_a_one_tick_per_bar_path(price, tick):
    """A monotone one-tick path is a genuine, very small ramp. Even at price
    1e9 with a 0.01 tick -- a log step of 1e-11 -- the window's standard
    deviation is far above the floor, and the column reads the 16 a straight
    line implies."""
    close = Series(price + tick * np.arange(1500, dtype=float))
    col = tf_autocorr_1e_60(close)
    assert int(col.notna().sum()) == FIRED
    assert set(np.unique(col.dropna().to_numpy())) == {16.0}
    masks, both, differ = _bit_equal_everywhere(col, _unguarded(close))
    assert masks and differ == 0


def test_what_the_floor_buys_on_a_ulp_ladder():
    """⚠ The failure the floor exists for is INVISIBLE, not absurd. A price
    flat at 1e6 stepping one double ulp a bar is mathematically an exact
    geometric ladder, and unguarded it reads 16 -- the top of this column's
    trend scale, indistinguishable from a real trend. The COST is the same
    fact read the other way: that mathematical answer is refused."""
    close = _ulp_ladder(1e6, 1500)
    assert int(tf_autocorr_1e_60(close).notna().sum()) == 0
    raw = _unguarded(close).dropna().to_numpy()
    assert raw.size == FIRED
    assert set(np.unique(raw)) == {16.0}


def test_what_the_floor_buys_on_a_single_ulp_step():
    """And a price flat but for ONE 1-ulp step reads a spread of ordinary
    lags unguarded -- measured 1 to 15 over the 59 windows that span the
    step -- where the window carries no information at all."""
    c = np.full(1500, 1e6)
    c[700:] = np.nextafter(1e6, np.inf)
    close = Series(c)
    assert int(tf_autocorr_1e_60(close).notna().sum()) == 0
    raw = _unguarded(close).dropna().to_numpy()
    assert raw.size == LENGTH - 1
    assert float(raw.min()) <= 2.0 and float(raw.max()) >= 10.0


def test_an_exactly_flat_window_is_nan_either_way():
    """Not the floor's doing: the variance is exactly 0, so there is no ACF
    at all."""
    flat = Series(np.full(200, 100.0))
    assert int(tf_autocorr_1e_60(flat).notna().sum()) == 0
    assert int(_unguarded(flat).notna().sum()) == 0


@pytest.mark.parametrize("runlen,extra", [(LENGTH - 1, 0), (LENGTH, 1),
                                          (LENGTH + 1, 2), (LENGTH + 5, 6)])
def test_a_flat_run_planted_in_a_walk_empties_its_own_windows(runlen, extra):
    """`length` identical closes are the smallest run that empties a bar."""
    c = _walk().to_numpy().copy()
    c[600:600 + runlen] = c[600]
    col = tf_autocorr_1e_60(Series(c))
    assert int(col.isna().sum()) - (LENGTH - 1) == extra


# ------------------------------------------------------------- bad data
@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, -np.inf, 1e-310])
def test_a_bad_close_empties_exactly_its_own_windows(bad):
    """A close that is not a finite, normal, positive float is missing, and
    it spoils the `length` windows that contain it -- no more, and nothing
    before it."""
    base = _walk()
    clean = tf_autocorr_1e_60(base)
    c = base.copy()
    c.iloc[700] = bad
    col = tf_autocorr_1e_60(c)
    assert int(col.isna().sum()) - int(clean.isna().sum()) == LENGTH
    head_a, head_b = clean.iloc[:700 - LENGTH], col.iloc[:700 - LENGTH]
    assert bool((head_a.fillna(-1) == head_b.fillna(-1)).all())


def test_a_close_pair_whose_ratio_overflows_empties_one_return():
    """One spoiled log return, so `length - 1` windows rather than
    `length`."""
    base = _walk()
    clean = tf_autocorr_1e_60(base)
    c = base.copy()
    c.iloc[700] = 1e-300
    c.iloc[701] = 1e50
    col = tf_autocorr_1e_60(c)
    assert int(col.isna().sum()) - int(clean.isna().sum()) == LENGTH - 1


@pytest.mark.parametrize("n,fires", [(0, None), (1, None), (59, None),
                                     (60, 1), (61, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = _walk(n=max(n, 2)).iloc[:n] if n else Series([], dtype=float)
    out = tf_autocorr_1e_60(s)
    if fires is None:
        assert out is None
    else:
        assert int(out.notna().sum()) == fires


def test_the_offset_and_the_fill_are_the_house_ones():
    close = _walk()
    base = tf_autocorr_1e_60(close)
    moved = tf_autocorr_1e_60(close, offset=3)
    assert bool((moved.iloc[3:].fillna(-1).to_numpy()
                 == base.iloc[:-3].fillna(-1).to_numpy()).all())
    assert int(tf_autocorr_1e_60(close, fillna=0.0).isna().sum()) == 0


@pytest.mark.parametrize("budget", [1, 64, 999, 10 ** 9])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every chunk is an independent run of rows and the arithmetic is
    row-wise, so where a bar lands must not matter. If it did, no causality
    sweep over a single-chunk frame could see it."""
    close = _walk(n=4000, seed=77)
    mod = _load_mutant("CHUNK_VALUES = 1 << 21", f"CHUNK_VALUES = {budget}")
    masks, both, differ = _bit_equal_everywhere(tf_autocorr_1e_60(close),
                                                mod.tf_autocorr_1e_60(close))
    assert masks
    assert both == 4000 - LENGTH + 1
    assert differ == 0


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert "tf_autocorr_1e_60" in ta.Category["statistics"]
    assert callable(ta.tf_autocorr_1e_60)
    df = pd.DataFrame({"close": _walk().to_numpy()})
    assert hasattr(df.ta, "tf_autocorr_1e_60")
    acc = df.ta.tf_autocorr_1e_60()
    assert acc.name == "TFAUTOCORR1E_60"
    assert int(acc.notna().sum()) == FIRED
    assert acc.category == "statistics"


def test_the_accessor_forwards_its_parameters():
    df = pd.DataFrame({"close": _walk().to_numpy()})
    assert df.ta.tf_autocorr_1e_60(length=100).name == "TFAUTOCORR1E_100"
    base = tf_autocorr_1e_60(Series(df["close"].to_numpy()), length=100)
    got = df.ta.tf_autocorr_1e_60(length=100)
    assert bool((got.fillna(-1).to_numpy() == base.fillna(-1).to_numpy()).all())
