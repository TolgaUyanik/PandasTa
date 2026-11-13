# -*- coding: utf-8 -*-
"""TS-CID-CE-20: `ts_cid_ce_20`, tsfresh's CID-CE complexity estimate on
returns (PandasTa issue #95).

    TS_CID_CE_20 = sqrt(sum((x[i] - x[i-1])**2) / v), over a window of 20
                   simple returns, with `v` that window's POPULATION variance
                   -- tsfresh's `cid_ce(x, normalize=True)`, whose
                   z-normalisation is one division here instead of 20

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **That the column is a monotone restatement of the lag-1 return
   autocorrelation at the SAME window, and the overlap that follows from
   it.** Exactly, with `y` the demeaned window:

       TS_CID_CE**2 = 2*length - (y[oldest]**2 + y[newest]**2)/v
                      - 2*(length - 1) * TS_AC1(length)

   which the module reproduces to **2.1e-14** over 1,480 bars. So against
   `ts_ac1_60` run at `length` 20 the Spearman is **-0.977743**, and against
   the SHIPPED `TS_AC1_60` (a 60-return window) **-0.4218** on a walk,
   -0.5342 tick-rounded, -0.4339 on an AR(1) path. Gate E's comparators are
   the engine's 687 columns and cannot see a pandas_ta port, so
   `test_the_identity_against_the_lag_1_autocorrelation` is where this
   overlap is recorded. Two columns of this family at the SAME length would
   double-weight one signal.

2. **Gate A, and that the formula under test is the ISSUE's line.** tsfresh
   is NOT installed in this worktree and web access is unavailable, so
   "tsfresh (MIT)" is an attribution, not an oracle. What IS checkable is
   pinned five ways:

   * two EXACT closed forms for an alternating window -- `2*sqrt(n-1)` at an
     even `n` and `2*n/sqrt(n+1)` at an odd one, both derived -- bit-exact on
     `close = [1, 2, 1, 2, ...]` at `length` 3, 4, 20 and 21 (at 5 the two
     float spellings of the same number differ by one ulp);
   * the reachable **bounds**, [0.701759, 8.916700] at `length` 20, in closed
     form: the squared column is `length` times a Rayleigh quotient of the
     free-end path Laplacian, whose eigenvalues are
     `4*sin(pi*k/(2*length))**2`, and both ends are attained by the module on
     the matching cosine window to 1.8e-15;
   * the source function applied window by window -- every window handed to a
     retype of `cid_ce` itself, so no pandas rolling is involved: max
     |difference| 3.5e-14 on a walk, 2.2e-14 tick-rounded, 4.1e-14 on an
     AR(1) path, 2.9e-10 on a path whose returns have `|mean| / sd` = 1e5;
   * an exact rational oracle in `fractions.Fraction`: 4.4e-15 on a walk
     against a `math.fsum` loop's 4.4e-15, and 1.1e-09 against 1.1e-09 on
     that mean-dominated path -- the error there belongs to the variance
     accumulator, which every spelling shares, and the numerator contains no
     mean at all;
   * the prototype imported from the owner's own registry when the worktree
     has `docs/issues/` -- bit-equal to the retype on 1,480 of 1,480 bars.

3. **That this column IS the screen prototype times one positive constant.**
   The prototype divides by pandas' default SAMPLE standard deviation where
   the source divides by the population one, so it is this column divided by
   `sqrt(20/19)` = **1.025978352085** -- the ratio is that constant at both
   its minimum and its maximum, Spearman **1.000000**, NaN masks identical,
   same first fired bar 20. A Spearman is unmoved by a positive rescaling, so
   issue #95's screen figures (0.2641 vs `chop`) are expected to carry over
   wherever both columns fire; what can still move them is this port's
   guards, which empty windows the prototype reports on.

4. **Gate B, by mutant, on three frames.** Six mutants, each `importlib`-read
   and `exec`'d in memory. Five are caught at **35/35** offsets of a
   future-perturbation sweep on each of a walk, a tick-rounded walk and an
   AR(1) path, where the real module leaks **0/35**. The sixth -- a
   `center=True` on the two extrema -- is caught **0/35** and that is
   asserted with its reason: `span` enters nothing but the trust test's
   booleans, which are True either way on clean data, so the look-ahead
   changes no value (on a walk the mutant differs only on the last
   `(length-1)//2` = 9 bars, the NaN tail). It IS caught 33/35 on a frame
   contaminated by a planted 1e+8 return, where the trust test bites.

5. **The three guards, each of which changes the column.**
   * The variance floor, 4096 eps SQUARED (8.27e-25), and NOT tsfresh's
     `if s == 0: return 0.0`. That branch returns a value **below the
     reachable minimum** of 0.701759, which a tree reads as the calmest
     possible window rather than as missing data: on a flat frame it reports
     0.0 on all 280 windows where this column reports on none. On a
     1%-a-bar geometric ladder, whose returns are mathematically constant but
     vary at rounding level, an unguarded spelling reports 280 windows up to
     **8.6372** -- inside the reachable range, which is worse than a wild
     number.
   * The accumulator trust test. `rolling.var` and `rolling.sum` are ONLINE,
     so a volatile stretch leaves a residue. On a frame that runs at
     sigma = 0.3 for 200 bars and then at sigma = 1e-9, 181 bars are NaN with
     the test and sit up to **6.323** from a per-window oracle whose median
     there is 5.757 without it. It costs **0 bars** on seven clean frames and
     it is NOT a cure at every magnitude: a single planted return of 1e+2,
     1e+4 or 1e+6 passes it, 4.8e-09, 5.6e-05 and 0.786 out.
   * The per-return square bound, which keeps an unrepresentable square local:
     one close of 1e-300 costs 20 bars instead of the frame's whole remainder
     (199), and two of them cost the union of their windows, 40.

   ⚠ And what ONE enormous return does, which
   `test_one_huge_return_empties_or_corrupts_the_rest_of_the_series` exists to
   keep visible. There is no threshold and the mechanism changes with the
   magnitude; measured on a 2,000-bar frame with one return planted at bar
   200, so 1,799 bars follow it:

       1e+6   0 emptied. All 1,799 fire and are up to 0.786 from a
              per-window oracle: silently WRONG, not missing.
       1e+7   1,643 emptied -- by the TRUST TEST, not the floor: pandas'
              unguarded `rolling.var` is POSITIVE on all 1,779 of bars 221..
              156 bars still fire, the last at 1859, up to 3.868 out.
       1e+8   1,779 emptied -- by the FLOOR: the unguarded variance is
              non-positive on all 1,779. The 20 bars that fire are exactly
              201..220, the windows still holding the planted return, and
              nothing fires after bar 220.

   The `var <= 0` count is the evidence that the cause is pandas' ONLINE
   accumulator rather than this module's arithmetic. `ts_ac1_60` empties the
   same bars and that is asserted too, but it is NOT independent: the sibling
   shares this port's floor and trust test verbatim, so equal masks are
   expected by construction.

6. **Gate D, and that x8 is bit-identical rather than merely close.** Every
   input is a price RATIO and `8a / 8b` is the same double as `a / b`: 1,480
   of 1,480 bars bit-identical at x8 and x64 on each of three frames, and
   1,497 / 1,440 / 1,250 at `length` 3 / 60 / 250. x10 / x3.7 agree to
   7.4e-14 with identical NaN masks. The difference-of-logarithms spelling of
   the return would not be (821 of 1,499 bars bit-equal at x8 against
   1,499 of 1,499).

7. **What the column means, and what it is not.** It is invariant to an
   AFFINE map of the returns -- x2, x0.5 and +0.004 of log drift a bar all
   leave it at Spearman 1.000000 and within 1.1e-13 -- so it is NOT
   volatility: Spearman **0.0072** against the same window's standard
   deviation, where tsfresh's `normalize=False` mode reads 0.8243 against it.
   For iid returns it sits near `sqrt(2*length)` = 6.3246 (median 6.2848 over
   2,000 independent windows, sd 0.6723, p10 5.4033, p90 7.1126) and the
   LEVEL grows with the window, so two lengths are not on one scale. What it
   orders is persistence, downward: medians 4.6865 / 5.5166 / 6.2276 /
   6.8905 / 7.5389 at AR(1) `phi` = +0.50 / +0.25 / 0 / -0.25 / -0.50.

8. **The guard bands and the NaN rules.** `length` below 3 (including 0,
   negatives and fractions that truncate below 3) falls back to 20; a window
   of two returns is identically 2, which is why the minimum is 3. A bad
   close -- NaN, zero, negative, infinite or subnormal -- empties exactly the
   21 windows that contain it and moves nothing before it; a flat run needs
   all `length + 1` = 21 closes to empty one bar.

9. **Five-point wiring** (`Category`, the accessor, the export, the name) and
   that Gate E is OWED: `test_the_ledger_has_no_row_for_this_column_yet`
   fails the moment a row appears, which is the receipt session's cue to
   replace it with the row's identity and numbers.

Every number above comes from `docs/measure_ts_cid_ce_20.py`, whose run is
transcribed in `docs/TsCidCe20Measured.md`.

⚠ Gate C in THIS FILE is SYNTHETIC. The real-data counts belong to Gate E's
run, which the launcher makes after this session.
"""
import importlib
import inspect
import math
import types
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20

LENGTH = 20
#: `sqrt(length / (length - 1))`: the prototype's sample standard deviation
#: against the source's population one.
DDOF_RATIO = math.sqrt(LENGTH / (LENGTH - 1.0))

_REAL = importlib.import_module("pandas_ta.statistics.ts_cid_ce_20")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.5):
    """A path whose LOG returns are an AR(1), `rlog[t] = phi*rlog[t-1] + eps`,
    whose population lag-1 autocorrelation is exactly `phi`."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _alternating(n=1500, amp=0.01):
    r = np.where(np.arange(n) % 2 == 0, amp, -amp)
    return Series(100.0 * np.cumprod(1.0 + r))


def _mean_dominated(n=400, seed=3, mu=0.01, ratio=1e5):
    """Returns with a large MEAN and a tiny DISPERSION, well above the
    variance floor: the shape on which a variance accumulator cancels."""
    rng = np.random.default_rng(seed)
    r = mu + rng.normal(0.0, abs(mu) / ratio, n)
    return Series(100.0 * np.cumprod(1.0 + r))


def _two_scale(n_hi=200, n_lo=200, sigma_hi=0.3, sigma_lo=1e-9, seed=5):
    """Volatile, then frozen: the shape the accumulator trust test is for."""
    rng = np.random.default_rng(seed)
    r = np.concatenate([rng.normal(0.0, sigma_hi, n_hi),
                        rng.normal(0.0, sigma_lo, n_lo)])
    return Series(100.0 * np.exp(np.cumsum(r)))


# ------------------------------------------------------------- Gate A


def _tsfresh_cid_ce(x, normalize=True):
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
    unavailable, so this is the issue's line plus that published definition,
    not a read of tsfresh's own code."""
    x = np.asarray(x, dtype=float)
    if normalize:
        s = np.std(x)
        if s != 0:
            x = (x - np.mean(x)) / s
        else:
            return 0.0
    x = np.diff(x)
    return float(np.sqrt(np.dot(x, x)))


def _source_windowed(close, length=LENGTH, guard="floor", log_returns=False,
                     closes_not_returns=False, ddof=0, normalize=True):
    """The source function window by window: each window goes to
    `_tsfresh_cid_ce`, so the z-normalisation happens per return the way
    tsfresh does it and no pandas rolling is involved. The keywords are the
    rejected readings."""
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
        v = W.var(axis=1, ddof=0)
        vals = np.array([_tsfresh_cid_ce(w, normalize=normalize) for w in W])
        if normalize and ddof:
            vals = vals * np.sqrt(v / W.var(axis=1, ddof=ddof))
    if guard == "floor":                 # this module's guard
        vals = np.where(v > _REAL.VAR_FLOOR, vals, np.nan)
    elif guard != "none":                # "none" keeps tsfresh's 0.0 branch
        raise ValueError(guard)          # so a typo cannot mean "unguarded"
    out[width:] = vals
    return Series(out, index=close.index)


def _closed_form_bounds(n):
    """The squared column is `n` times the Rayleigh quotient of the free-end
    path Laplacian `L` (`x'Lx = sum (x[i]-x[i-1])**2`) on the subspace
    orthogonal to the all-ones vector. `L`'s eigenvectors are the DCT-II basis
    `cos(pi*k*(j+1/2)/n)` with eigenvalues `4*sin(pi*k/(2n))**2`, and the
    k = 0 one IS that vector, so the restricted spectrum is k = 1..n-1."""
    lo = math.sqrt(n * 4.0) * math.sin(math.pi / (2 * n))
    hi = math.sqrt(n * 4.0) * math.sin(math.pi * (n - 1) / (2 * n))
    return lo, hi


def _eigen_closes(n, k, amp=0.01, first=100.0):
    j = np.arange(n)
    y = np.cos(math.pi * k * (j + 0.5) / n)
    r = amp * y / float(np.abs(y).max())
    return Series(np.concatenate([[first], first * np.cumprod(1.0 + r)]))


@pytest.mark.parametrize("length,exact", [
    (3, 2.0 * 3 / math.sqrt(4.0)),       # odd:  2*n/sqrt(n+1)
    (4, 2.0 * math.sqrt(3.0)),           # even: 2*sqrt(n-1)
    (20, 2.0 * math.sqrt(19.0)),
    (21, 2.0 * 21 / math.sqrt(22.0)),
])
def test_an_alternating_window_has_an_exact_value(length, exact):
    """`close = [1, 2, 1, 2, ...]` holds returns alternating between +1 and
    -1/2, i.e. between `m0 +- d`. Every squared successive difference is the
    square of the window's whole range, `(2d)**2`:

        even n: equal counts, var = d**2           -> quotient 4*(n-1)
        odd  n: one extra of the first value, the
                mean sits d/n off centre and
                var = d**2*(n**2-1)/n**2           -> quotient 4*n**2/(n+1)

    Both are exact binary fractions before the square root, so the module
    hits the correctly-rounded `sqrt` bit-for-bit. At `length` 5 the two float
    spellings of the same number differ by one ulp, which is why 5 is not in
    this list -- `docs/measure_ts_cid_ce_20.py` prints it."""
    closes = Series(np.where(np.arange(length + 1) % 2 == 0, 1.0, 2.0))
    out = ts_cid_ce_20(closes, length=length)
    assert out.name == f"TS_CID_CE_{length}"
    assert out.iloc[:length].isna().all()
    assert float(out.iloc[length]) == exact


def test_an_alternating_frame_sits_at_the_even_closed_form():
    """The same algebra at `length` 20 on a 1,500-bar frame. The closes are
    built by a cumulative PRODUCT, so the returns are no longer exactly +-amp
    and the value is `2*sqrt(19)` to 1.1e-14 rather than bit-exact on every
    bar -- 520 of 1,480 bars are bit-equal, which is a float detail and is not
    asserted."""
    col = ts_cid_ce_20(_alternating()).dropna()
    assert len(col) == 1480
    assert float((col - 2.0 * math.sqrt(19.0)).abs().max()) < 1e-13


def test_a_two_return_window_is_constant_which_is_why_the_minimum_is_three():
    """With two returns there is one squared difference, `(a-b)**2`, and the
    population variance is `(a-b)**2/4`, so the quotient is 4 and the column
    is exactly 2.0 for every `a != b`. The source function says so on 38
    windows of a non-geometric frame; the module refuses the setting."""
    closes = Series(np.sqrt(np.arange(1, 41, dtype=float)))
    r = closes.to_numpy()
    values = [_tsfresh_cid_ce(r[t - 2:t + 1][1:] / r[t - 2:t + 1][:-1] - 1.0)
              for t in range(2, 40)]
    assert len(values) == 38
    assert set(values) == {2.0}
    assert _REAL.MIN_LENGTH == 3
    assert ts_cid_ce_20(_walk(400, seed=31), length=2).name == "TS_CID_CE_20"


@pytest.mark.parametrize("frame_fn,tol", [(_walk, 1e-12),
                                          (_tick_rounded, 1e-12),
                                          (_ar1, 1e-12),
                                          (_mean_dominated, 1e-8)])
def test_matches_the_source_function_window_by_window(frame_fn, tol):
    """3.5e-14 / 2.2e-14 / 4.1e-14 on the three clean frames and 2.9e-10 on
    the mean-dominated one, where the variance accumulator -- not this
    column's spelling -- is the limit."""
    frame = frame_fn()
    base, other = ts_cid_ce_20(frame), _source_windowed(frame)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) == len(frame) - LENGTH
    assert float((base[m] - other[m]).abs().max()) < tol
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


def _exact(close, length=LENGTH, bars=40):
    """The EXACT value in `fractions.Fraction`: every close is a rational, so
    the whole SQUARED statistic is one. The square root is the only
    rounding."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(max(length, len(c) - bars), len(c)):
        x = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        m = sum(x) / length
        v = sum((u - m) ** 2 for u in x) / length
        gap = sum((x[i] - x[i - 1]) ** 2 for i in range(1, length))
        if v != 0:
            out[t] = math.sqrt(Fraction(gap, 1) / v)
    return Series(out, index=close.index)


def _fsum_loop(close, length=LENGTH):
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        x = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        m = math.fsum(x) / length
        v = math.fsum((u - m) ** 2 for u in x) / length
        gap = math.fsum((x[i] - x[i - 1]) ** 2 for i in range(1, length))
        if v > _REAL.VAR_FLOOR:
            out[t] = math.sqrt(gap / v)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn,tol", [(_walk, 1e-13),
                                          (_mean_dominated, 1e-8)])
def test_the_module_is_as_accurate_as_an_fsum_loop_against_the_exact_value(
        frame_fn, tol):
    """Against the exact rational value of the same closes: on a walk the
    module is 4.4e-15 and the `math.fsum` loop 4.4e-15; on a path whose
    returns have `|mean| / sd` = 1e5 both are 1.1e-09. The second row is the
    load-bearing one -- it says the error there is the VARIANCE's and not this
    spelling's, so there is no better numerator to reach for. The numerator
    holds no mean at all, because a difference of two returns does not contain
    one."""
    close = frame_fn(340)
    exact = _exact(close)
    m = exact.notna()
    assert int(m.sum()) == 40
    module = float((ts_cid_ce_20(close)[m] - exact[m]).abs().max())
    loop = float((_fsum_loop(close)[m] - exact[m]).abs().max())
    assert module < tol
    assert module <= 10.0 * loop


@pytest.mark.parametrize("length,lo,hi", [
    (3, 1.732050807569, 3.000000000000),
    (4, 1.530733729460, 3.695518130045),
    (10, 0.989378428154, 6.246689549346),
    (20, 0.701759486002, 8.916699704700),
    (60, 0.405531539404, 15.486624686178),
])
def test_the_reachable_bounds_are_attained_and_not_exceeded(length, lo, hi):
    """Both ends, in closed form and then attained by the module on the
    matching cosine window. The column cannot be 0 and cannot be unbounded:
    it lives in [0.701759, 8.916700] at `length` 20, which is also why
    tsfresh's `0.0` for a flat window is not a value this column can mean.
    The column also stays inside the bounds on four ordinary frames."""
    assert _closed_form_bounds(length) == pytest.approx((lo, hi), abs=1e-9)
    for k, target in ((1, lo), (length - 1, hi)):
        got = float(ts_cid_ce_20(_eigen_closes(length, k),
                                 length=length).iloc[-1])
        assert got == pytest.approx(target, abs=1e-12)
    # The alternating frame ATTAINS the maximum at `length` 3 (an alternating
    # window is the k = n-1 eigenvector when n = 3), so the frame check needs
    # float slack: it reads 3.000000000000012 there.
    for frame_fn in (_walk, _tick_rounded, _ar1, _alternating):
        col = ts_cid_ce_20(frame_fn(), length=length).dropna()
        assert float(col.min()) >= lo * (1.0 - 1e-12)
        assert float(col.max()) <= hi * (1.0 + 1e-12)


def _prototype(close, length=LENGTH):
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


def test_the_prototype_is_this_column_times_one_constant():
    """The screen measured the same statistic with the SAMPLE standard
    deviation, so the prototype is this column divided by
    `sqrt(20/19)` = 1.025978352085 -- a positive constant, which a Spearman
    cannot see. Measured on a 1,500-bar walk: the ratio is that constant at
    both ends of its range, max |port - sqrt(20/19) * prototype| =
    **2.665e-15** with the factor at full float precision (Gate A7 of
    `docs/measure_ts_cid_ce_20.py`; the 3.642e-14 that A6 prints is the same
    quantity against the `ddof=1` window-by-window oracle, which is a
    different series), Spearman 1.000000, identical NaN masks, same first
    fired bar.

    That is why issue #95's screen figures (Gate E max |rho| 0.2641 vs
    `chop`) are expected to carry over to this column, unlike issue #94's,
    whose prototype was a different statistic. The launcher's run on THIS
    module is still what decides: the guards here empty windows the
    prototype reports on."""
    close = _walk()
    base, proto = ts_cid_ce_20(close), _prototype(close)
    assert (base.isna() == proto.isna()).all()
    m = base.notna() & proto.notna()
    assert int(m.sum()) == 1480
    ratio = base[m] / proto[m]
    assert float(ratio.min()) == pytest.approx(DDOF_RATIO, abs=1e-12)
    assert float(ratio.max()) == pytest.approx(DDOF_RATIO, abs=1e-12)
    # 2.665e-15 measured; the bound is the order, not the digit.
    assert float((base[m] - DDOF_RATIO * proto[m]).abs().max()) < 1e-14
    assert float(base[m].corr(proto[m], method="spearman")) >= 1.0 - 1e-12
    assert int(base.notna().to_numpy().argmax()) == LENGTH
    assert int(proto.notna().to_numpy().argmax()) == LENGTH


@pytest.mark.parametrize("kwargs,lo,hi,rho_lo,rho_hi", [
    ({"log_returns": True}, 1e-3, 1e-1, 0.999, 0.99999),
    ({"closes_not_returns": True}, 0.5, 5.0, 0.9, 0.98),
    ({"ddof": 1}, 1e-2, 1.0, 1.0 - 1e-12, 1.1),
    ({"normalize": False}, 1.0, 20.0, 0.3, 0.8),
])
def test_the_rejected_readings_are_each_priced(kwargs, lo, hi, rho_lo, rho_hi):
    """Each is a reading the issue's wording leaves open and this port
    rejects, so each is measured rather than dismissed: log returns
    (Spearman 0.999909, max |difference| 4.8e-02), 20 CLOSES instead of 20
    returns (0.949216, 1.4179), the prototype's sample standard deviation
    (1.000000, 0.1988 -- a level shift only) and tsfresh's OTHER mode
    `normalize=False` (0.545430, 7.75), which is a volatility reading."""
    close = _walk()
    base, other = ts_cid_ce_20(close), _source_windowed(close, **kwargs)
    m = base.notna() & other.notna()
    diff = float((base[m] - other[m]).abs().max())
    assert lo < diff < hi
    rho = float(base[m].corr(other[m], method="spearman"))
    assert rho_lo <= rho <= rho_hi


def test_normalize_false_is_the_volatility_reading_and_this_one_is_not():
    """The sharpest statement of what the z-normalisation buys. tsfresh's
    `cid_ce(x, normalize=False)` is `sqrt(sum (x[i]-x[i-1])**2)` with no
    divisor, and it reads Spearman 0.8243 against the same window's standard
    deviation; the normalised column reads 0.0072 against it. A consumer
    reaching for "complexity" and getting volatility is the mistake this
    pins."""
    close = _walk()
    base = ts_cid_ce_20(close)
    raw = _source_windowed(close, normalize=False)
    r = close / close.shift(1) - 1.0
    sd = r.rolling(LENGTH, min_periods=LENGTH).std(ddof=0)
    m = base.notna() & raw.notna() & sd.notna()
    assert float(raw[m].corr(sd[m], method="spearman")) > 0.75
    assert abs(float(base[m].corr(sd[m], method="spearman"))) < 0.1


def test_the_two_spellings_of_the_normalisation_agree():
    """The module divides the SUM by the variance once; tsfresh z-normalises
    each of the `length` returns first. The same number to 3.5e-14 at
    Spearman 1.000000, and neither is closer to the exact rational value
    (both 4.4e-15 on a walk) -- so the cheaper spelling is free."""
    close = _walk()
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r[1:], LENGTH)
    v = W.var(axis=1, ddof=0)
    z = (W - W.mean(axis=1, keepdims=True)) / np.sqrt(v)[:, None]
    d = np.diff(z, axis=1)
    vals = np.full(len(r), np.nan)
    vals[LENGTH:] = np.sqrt((d * d).sum(axis=1))
    other = Series(vals, index=close.index)
    base = ts_cid_ce_20(close)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1480
    assert float((base[m] - other[m]).abs().max()) < 1e-12
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


def test_length_is_the_only_parameter():
    """There is no `normalize` keyword and no `lag`: the column's NAME says
    CID-CE of 20 returns, and an unknown keyword would reach `**kwargs` and
    be ignored silently, which is why this is asserted on the SIGNATURE."""
    params = list(inspect.signature(ts_cid_ce_20).parameters)
    assert params == ["close", "length", "offset", "kwargs"]


# ------------------------------------------------------------- Gate B

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
           CENTERED_VAR_MUTANT, CENTERED_GAP_MUTANT]
MUTANT_IDS = ["write_shift", "forward_return", "forward_diff", "centered_var",
              "centered_gap"]
OFFSETS = range(100, 1500, 40)  # past the 20-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "ar1": (_ar1(), _ar1(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_cid_ce_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _quiet_offsets(fn, close, other):
    """Replace every bar from J onward with a different path; return the J
    values at which NOTHING strictly before J moved, each with whether bar
    J - 1 -- the only bar a one-bar look-ahead can reach -- was NaN in both
    runs. Prefix truncation cannot see back-dating, which is why this is a
    perturbation sweep."""
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


def _leaks(fn, close, other):
    return len(list(OFFSETS)) - len(_quiet_offsets(fn, close, other))


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _leaks(ts_cid_ce_20, close, other) == 0


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("mutant", MUTANTS, ids=MUTANT_IDS)
def test_each_mutant_is_caught_on_each_frame(mutant, frame):
    mod = _load_mutant(*mutant)
    close, other = FRAMES[frame]
    assert not mod.ts_cid_ce_20(close).equals(ts_cid_ce_20(close))  # live
    assert _leaks(mod.ts_cid_ce_20, close, other) == len(list(OFFSETS))


@pytest.mark.parametrize("frame,body_bars", [("walk", 0),
                                             ("tick-rounded", 0),
                                             ("ar1", 7)])
def test_the_centred_span_mutant_changes_no_value_on_clean_data(
        frame, body_bars):
    """The sixth mutant, and the one the sweep does NOT catch: 0/35 on each
    clean frame. Not a clean bill -- an explanation, asserted.

    `span` enters nothing but the trust test's two booleans, and that test
    rejects 0 bars of each clean frame
    (`test_the_trust_test_costs_nothing_on_clean_frames`). So on clean data
    the mutation can only ADD NaNs where the centred extrema happen to make
    the verdict False; it can never change a NUMBER, which is what the sweep
    looks for. Asserted: every bar on which the mutant differs is a bar the
    real module reports and the mutant does not. On a walk and a tick-rounded
    walk those are exactly the last `(length-1)//2` = 9 bars (the mutant's own
    NaN tail); on the AR(1) path 7 body bars join them, which is the
    look-ahead showing itself -- and the sweep is still quiet, because the
    perturbed runs do not flip a verdict inside the 9 bars a centred window
    can reach.

    `test_the_centred_span_mutant_is_caught_where_the_trust_test_bites` is
    the case where it IS caught: 33/35, on a frame where the trust test
    actually rejects windows."""
    close, other = FRAMES[frame]
    mod = _load_mutant(*CENTERED_SPAN_MUTANT)
    real_col, mut_col = ts_cid_ce_20(close), mod.ts_cid_ce_20(close)
    assert not mut_col.equals(real_col)                     # live mutation
    assert _leaks(mod.ts_cid_ce_20, close, other) == 0
    reach = (LENGTH - 1) // 2
    assert reach == 9
    # No bar's VALUE moves: every difference is a number turning into a NaN.
    both = real_col.notna() & mut_col.notna()
    assert int((real_col[both] != mut_col[both]).sum()) == 0
    differ = np.flatnonzero((real_col.notna() & mut_col.isna()).to_numpy())
    assert int((real_col.isna() & mut_col.notna()).sum()) == 0
    tail = [int(i) for i in differ if i >= len(close) - reach]
    body = [int(i) for i in differ if i < len(close) - reach]
    assert len(tail) == reach            # the whole NaN tail, every frame
    # Pinned per frame and by EQUALITY: the AR(1) path's 7 bars are the
    # look-ahead showing itself, and the walk's 0 is the claim that it does
    # not there. A one-sided bound would pass if either changed.
    assert len(body) == body_bars


def test_the_centred_span_mutant_is_caught_where_the_trust_test_bites():
    """On a frame with a planted 1e+8 return at bar 150 -- where the trust
    test actually rejects windows -- the centred span lets a FUTURE giant
    return re-admit a bar the real module refuses, and the sweep catches it
    at 33 of 35 offsets while the real module still leaks 0/35. The two quiet
    offsets are J = 100 and 140, both at or below the planted bar."""
    spiked = _walk(1500, seed=21)
    spiked.iloc[150] = float(spiked.iloc[149]) * 1e8
    far = _walk(1500, seed=97) * 1e4
    mod = _load_mutant(*CENTERED_SPAN_MUTANT)
    assert int(ts_cid_ce_20(spiked).iloc[170:200].isna().sum()) == 30
    assert _leaks(ts_cid_ce_20, spiked, far) == 0
    quiet = [j for j, _, _ in _quiet_offsets(mod.ts_cid_ce_20, spiked, far)]
    assert quiet == [100, 140]


NON_DEFAULT = [
    # (mutant, name, length, caught)
    (WRITE_SHIFT_MUTANT, "write_shift", 3, 35),
    (WRITE_SHIFT_MUTANT, "write_shift", 250, 35),
    (FORWARD_DIFF_MUTANT, "forward_diff", 3, 25),
    (FORWARD_DIFF_MUTANT, "forward_diff", 250, 31),
    (CENTERED_VAR_MUTANT, "centered_var", 3, 22),
    (CENTERED_VAR_MUTANT, "centered_var", 250, 31),
    (CENTERED_GAP_MUTANT, "centered_gap", 3, 0),
    (CENTERED_GAP_MUTANT, "centered_gap", 250, 31),
]


@pytest.mark.parametrize("mutant,name,length,caught", NON_DEFAULT,
                         ids=[f"{n}-{le}" for _, n, le, _ in NON_DEFAULT])
def test_the_length_dependent_mutants_at_non_default_lengths(
        mutant, name, length, caught):
    """`length` is user-reachable from 3 upward and the sweep above runs the
    default only. FIVE mutants depend on it -- every one except
    `forward_return` -- and four of them are re-run here at 3 and 250; the
    fifth, `centered_span`, is covered by its own two tests above, and its
    remaining cells (18/35 at `length` 3 and 0/35 at 250) are transcribed in
    `docs/TsCidCe20Measured.md`. The real module leaks 0/35 at every setting.
    SIX of the eight cells here are not 35/35, under three explanations, and
    each explanation is ASSERTED rather than argued:

    * **31/35 at `length` 250** misses exactly the four offsets below a
      250-bar warm-up (J = 100, 140, 180, 220), where the whole prefix is NaN
      and there was nothing to move.
    * **25/35 and 22/35 at `length` 3**: a 3-wide centred window and a
      one-bar-ahead difference both reach exactly one bar, so the only bar
      they can move is J - 1, and at 10 and 13 of the 35 offsets that bar is
      NaN in BOTH runs -- at `length` 3 the column's own NaN rate is high.
      ⚠ A limit of the sweep, not a clean bill: the look-ahead is real and is
      caught at the other offsets.
    * **0/35 for the centred squared-difference sum at `length` 3** is a
      mutation that does nothing: that window is `length - 1` = 2 wide and
      pandas centres by `(window - 1) // 2` = 0 bars, so `center=True` is
      `center=False`."""
    close, other = FRAMES["walk"]
    mod = _load_mutant(*mutant)

    def real(c):
        return ts_cid_ce_20(c, length=length)

    def mutated(c):
        return mod.ts_cid_ce_20(c, length=length)

    assert int(real(close).notna().to_numpy().argmax()) == length
    assert _leaks(real, close, other) == 0
    quiet = _quiet_offsets(mutated, close, other)
    assert len(list(OFFSETS)) - len(quiet) == caught
    if caught == 0:
        assert mutated(close).equals(real(close))  # the mutation is a no-op
        assert (length - 1 - 1) // 2 == 0          # pandas centres by 0 bars
        return
    assert not mutated(close).equals(real(close))  # live mutation
    if caught == 31:
        assert real(close).iloc[:length].isna().all()
        assert [j for j, _, _ in quiet] == [100, 140, 180, 220]
    # Nothing moved because bar J - 1, the only bar reachable, was NaN in
    # both runs -- not because the mutant is causal.
    assert all(clean and perturbed for _, clean, perturbed in quiet)


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep above
    covers."""
    close = _walk(400, seed=3)
    base = ts_cid_ce_20(close)
    pd.testing.assert_series_equal(ts_cid_ce_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_cid_ce_20(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------- the three guards


def test_the_variance_floor_is_an_absolute_constant_not_a_window():
    """It is deliberately NOT a rolling quantity: what it floors is the
    dispersion of dimensionless price ratios, so a constant works and the
    floor has no window of its own whose causality would need pinning. It is
    the SQUARE of the 4096 eps this fork floors a return standard deviation
    with in `statistics/ts_c3_20.py`, because what this column divides by is
    a variance -- the same spelling as `statistics/ts_ac1_60.py`."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    assert _REAL.VAR_FLOOR == _REAL.NOISE_FLOOR ** 2
    src = open(_REAL.__file__, encoding="utf-8").read()
    # Two rolling calls: the `length`-wide object reused for the variance and
    # the two extrema, and the `length - 1`-wide sum of squared successive
    # differences. That is what Gate B's three centred mutants cover.
    assert src.count(".rolling(") == 2


@pytest.mark.parametrize("frame_fn,fires,unguarded_fires,fabricated", [
    (lambda: Series(np.full(300, 50.0)), 0, 0, 0.0),
    (lambda: Series(100.0 * np.exp(np.arange(300) * 0.01)), 0, 280, 8.0),
])
def test_a_window_with_no_dispersion_is_nan_rather_than_a_ratio_of_roundings(
        frame_fn, fires, unguarded_fires, fabricated):
    """A flat frame and a 1%-a-bar geometric ladder both have mathematically
    constant returns, so there is no path length to report. The ladder is the
    case `var != 0` does not catch: its returns vary at float rounding level,
    and an unguarded spelling reports 280 of 300 bars from that rounding
    alone, reaching 8.6372 -- inside the reachable range, which is worse than
    a wild number. The flat frame's variance is exactly 0, so even unguarded
    it reports nothing: the two frames are pinned with their own counts, not
    with one count that would pass either way."""
    frame = frame_fn()
    assert int(ts_cid_ce_20(frame).notna().sum()) == fires
    r = frame / frame.shift(1) - 1.0
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(LENGTH - 1, min_periods=LENGTH - 1).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        unguarded = np.sqrt(gap / roll.var(ddof=0))
    assert int(unguarded.notna().sum()) == unguarded_fires
    if unguarded_fires:
        assert float(unguarded.max()) > fabricated


def test_tsfreshs_zero_for_a_flat_window_is_below_the_reachable_minimum():
    """tsfresh's own guard is `if s == 0: return 0.0`, and 0.0 is NOT a value
    this statistic can take: the reachable minimum at `length` 20 is
    0.701759. A tree reading a column of 0.0s reads "the calmest window ever
    seen", not "missing", so this module returns NaN. Measured on a flat
    frame: tsfresh's branch fills all 280 windows with 0.0 where this column
    reports on none."""
    lo, _ = _closed_form_bounds(LENGTH)
    assert lo == pytest.approx(0.701759486002, abs=1e-9)
    flat = Series(np.full(300, 50.0))
    theirs = _source_windowed(flat, guard="none")
    assert int(theirs.notna().sum()) == 280
    assert float(theirs.dropna().abs().max()) == 0.0
    assert int(ts_cid_ce_20(flat).notna().sum()) == 0


@pytest.mark.parametrize("price,tick,fires", [(50.0, 0.01, 280),
                                              (1e6, 0.001, 0),
                                              (1e6, 0.01, 0)])
def test_the_floor_bounds_the_dispersion_of_the_returns_not_their_size(
        price, tick, fires):
    """What the floor is and is not compared against. A tick grid quantises
    the return LEVEL at `tick / price` but the DISPERSION of consecutive
    returns at about `(tick / price)**2`, so the familiar "one tick over a
    price of 1e6 is 1e-9" is not a comparison against this floor. On a
    monotone one-tick-per-bar path: at price 50 with a 0.01 tick the window
    variance is 4.3e-14 and 280 of 300 bars fire; at price 1e6 with a 0.001
    tick it is 1.2e-32 and none do -- which is the right answer, because a
    window whose returns are that nearly constant has no jaggedness to
    measure."""
    closes = Series(price + tick * np.arange(300))
    r = closes / closes.shift(1) - 1.0
    v = float(r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0).iloc[-1])
    assert int(ts_cid_ce_20(closes).notna().sum()) == fires
    assert (v > _REAL.VAR_FLOOR) == (fires > 0)


def _no_trust_test(close, length=LENGTH):
    """The module without the accumulator trust test, to price it."""
    px = close.astype(float)
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    with np.errstate(over="ignore"):
        square = np.square(r.to_numpy())
    r = r.where(square < np.finfo(float).max / (8 * length))
    rolling = r.rolling(length, min_periods=length)
    var = rolling.var(ddof=0)
    with np.errstate(over="ignore"):
        gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(length - 1, min_periods=length - 1).sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        quotient = gap / var.where(var > _REAL.VAR_FLOOR)
        return Series(np.sqrt(quotient.to_numpy()), index=close.index)


def test_the_trust_test_turns_a_contaminated_accumulator_into_nan():
    """`rolling.var` and `rolling.sum` are ONLINE -- a value is added when it
    enters the window and subtracted when it leaves -- so a volatile stretch
    leaves a residue in both after it has gone. On a frame that runs at
    sigma = 0.3 for 200 bars and then at sigma = 1e-9, the residue is larger
    than the frozen windows' own dispersion: without this test 181 bars from
    219 on report numbers up to 6.323 away from a per-window oracle whose
    median there is 5.757 -- an error the size of the value -- and with it
    they are NaN. The test is exact algebra on the window's own range: a
    population variance cannot exceed `(span/2)**2` and `length - 1` squared
    successive differences cannot exceed `(length - 1) * span**2`.

    What it CANNOT do is recover the value: the per-window oracle still has
    one. The trade is a plausible number for a missing one, which is the
    right way round for an ML feature."""
    frame = _two_scale()
    strict, loose = ts_cid_ce_20(frame), _no_trust_test(frame)
    oracle = _source_windowed(frame)
    sole = (strict.isna() & loose.notna()).to_numpy()
    assert int(sole.sum()) == 181
    assert (int(np.flatnonzero(sole).min()),
            int(np.flatnonzero(sole).max())) == (219, 399)
    assert int(strict.notna().sum()) == 199
    assert int(loose.notna().sum()) == 380
    quiet = slice(221, 400)
    assert int(oracle.iloc[quiet].isna().sum()) == 0
    assert float((loose.iloc[quiet] - oracle.iloc[quiet]).abs().max()) > 1.0


@pytest.mark.parametrize("exponent,expected", [(2, 4.753e-09),
                                               (4, 5.559e-05),
                                               (6, 7.859e-01)])
def test_the_trust_test_is_not_a_cure_at_every_magnitude(exponent, expected):
    """Disclosed rather than implied: a single planted return of 1e+2, 1e+4 or
    1e+6 passes the trust test -- a window that still remembers a wide range
    allows the residue -- and the bars after it still differ from a per-window
    oracle, by 4.8e-09, 5.6e-05 and 0.786. A 100x bar is a thing a market can
    do; 1e+6 is a broken feed. What happens ABOVE 1e+6 is the subject of
    `test_one_huge_return_empties_or_corrupts_the_rest_of_the_series`: at
    1e+7 this test is what empties 1,643 bars, and at 1e+8 the accumulator is
    destroyed outright."""
    frame = _walk(400, seed=21)
    holed = frame.copy()
    holed.iloc[200] = float(frame.iloc[199]) * 10.0 ** exponent
    tail = slice(222, 400)
    col, oracle = ts_cid_ce_20(holed), _source_windowed(holed)
    assert int(col.iloc[tail].isna().sum()) == 0
    gap = float((col.iloc[tail] - oracle.iloc[tail]).abs().max())
    # To the precision the module docstring and the measured doc publish, not
    # inside a wide window: 0.786 at 1e+6 is the figure the "silently WRONG,
    # not missing" reading rests on.
    assert gap == pytest.approx(expected, rel=1e-3)


@pytest.mark.parametrize("frame_fn,fires", [
    (_walk, 1480),
    (_tick_rounded, 1480),
    (_ar1, 1480),
    (lambda: _ar1(phi=-0.5), 1480),
    (_alternating, 1480),
    (lambda: _walk(1500, sigma=1e-6), 1480),
    (lambda: Series(50.0 + 0.01 * np.arange(1500)), 1480),
])
def test_the_trust_test_costs_nothing_on_clean_frames(frame_fn, fires):
    """It must not eat ordinary data, and the alternating frame is the case
    that attains BOTH its bounds EXACTLY (measured ratios
    1.000000000000), which is why the slack is 4096 eps relative rather than
    zero."""
    frame = frame_fn()
    strict, loose = ts_cid_ce_20(frame), _no_trust_test(frame)
    assert int(strict.notna().sum()) == fires
    assert int((loose.notna() & strict.isna()).sum()) == 0


@pytest.mark.parametrize("magnitude,emptied,fired,last_fired,wrong,var_le_0", [
    (1e6, 0, 1799, 1999, 7.859e-01, 0),
    (1e7, 1643, 156, 1859, 3.868e+00, 0),
    (1e8, 1779, 20, 220, None, 1779),
    (1e10, 1780, 19, 219, None, 1779),
])
def test_one_huge_return_empties_or_corrupts_the_rest_of_the_series(
        magnitude, emptied, fired, last_fired, wrong, var_le_0):
    """⚠ The worst thing about this column, and it is pandas' rather than
    this port's: `rolling.var` is ONLINE, so one enormous return does not
    merely spoil its own windows. What happens depends on the magnitude, and
    the row is the claim -- there is no single threshold. Measured on a
    2,000-bar walk with one return planted at bar 200, so 1,799 bars follow
    it:

        1e+6  -> 0 emptied. All 1,799 fire and are up to 0.786 from a
                 per-window oracle: WRONG, not missing. Nothing catches it
                 (see test_the_trust_test_is_not_a_cure_at_every_magnitude).
        1e+7  -> 1,643 emptied, by the TRUST TEST: pandas' unguarded variance
                 is still positive on all 1,779 of bars 221.., so the residue
                 is inside the floor and outside the window's own range. 156
                 bars still fire, the last at 1859, up to 3.868 out.
        1e+8  -> 1,779 emptied, by the FLOOR: the unguarded variance is
                 NON-POSITIVE on all 1,779. The 20 bars that fire are exactly
                 201..220 -- the windows that still hold the planted return --
                 and nothing fires after bar 220.
        1e+10 -> 1,780 emptied, 19 fire (201..219).

    The per-return square bound is no help: it drops a return whose SQUARE is
    unrepresentable (above 1.06e+153), and 1e+8 is representable. The only
    structurally local spelling is a per-window pass, which costs 35.7 s
    against 55-59 ms on 400,000 bars. So this is DISCLOSED, not fixed, and
    pinned here so
    nobody re-discovers it in production.

    The `var <= 0` column is the evidence that the cause is pandas'
    accumulator. `ts_ac1_60` is asserted too, but it is NOT independent -- it
    shares this port's floor and trust test verbatim, so equal masks are
    expected rather than informative."""
    frame = _walk(2000, seed=21)
    holed = frame.copy()
    holed.iloc[200] = float(frame.iloc[199]) * magnitude
    col = ts_cid_ce_20(holed)
    after = col.iloc[201:]
    assert int(after.isna().sum()) == emptied
    assert int(after.notna().sum()) == fired
    assert int(col.notna().to_numpy().nonzero()[0].max()) == last_fired
    # Nothing BEFORE the planted bar moves: the damage is forward-only.
    base = ts_cid_ce_20(frame)
    assert (base.iloc[:200] == col.iloc[:200])[base.iloc[:200].notna()].all()
    # Which guard did it: pandas' own variance, with nothing in front of it.
    r = holed / holed.shift(1) - 1.0
    with np.errstate(over="ignore"):
        raw_var = r.rolling(LENGTH, min_periods=LENGTH).var(ddof=0)
    assert int((raw_var.iloc[221:] <= 0).sum()) == var_le_0
    if wrong is not None:                     # it reports, and it is wrong
        oracle = _source_windowed(holed)
        # On bars 221.. BY INDEX -- the first window holding no part of the
        # planted return -- so every magnitude is scored on the same bars.
        delta = (col - oracle).abs().iloc[221:]
        assert float(delta.max()) == pytest.approx(wrong, rel=1e-3)
    else:
        assert int(col.iloc[221:].notna().sum()) == 0
    sibling = ts_ac1_60(holed, length=LENGTH)
    assert int(sibling.iloc[201:].isna().sum()) == emptied


@pytest.mark.parametrize("planted,emptied,span", [
    ({200: 1e-300}, 20, (201, 220)),
    ({200: 1e-200, 230: 1e-200}, 40, (201, 250)),
])
def test_a_return_over_the_square_bound_is_dropped_rather_than_poisoning_on(
        planted, emptied, span):
    """The overflow bound keeps a giant return's damage to its own windows.
    One close of 1e-300 in a 400-bar walk makes a NEXT return of about
    1e+302, whose square is not representable: guarded, 20 bars go
    (201..220). Two such closes 30 bars apart spoil two returns and cost the
    UNION of their windows, 40 bars (201..250), which is what makes the
    locality structural rather than a one-shape measurement. Unguarded, the
    infinite accumulator never leaves and 199 bars go in both cases -- the
    whole remainder of the frame (measured in
    `docs/measure_ts_cid_ce_20.py`, Guards). The ceiling the bound puts on a
    return is 1.06e+153, which nothing a market can produce reaches."""
    frame = _walk(400, seed=21)
    base = ts_cid_ce_20(frame)
    holed = frame.copy()
    for idx, value in planted.items():
        holed.iloc[idx] = value
    guarded = ts_cid_ce_20(holed)
    lost = np.flatnonzero((base.notna() & guarded.isna()).to_numpy())
    assert len(lost) == emptied
    assert (int(lost.min()), int(lost.max())) == span
    ceiling = np.sqrt(np.finfo(float).max / (8 * LENGTH))
    assert ceiling == pytest.approx(1.0600e153, rel=1e-3)


# ------------------------------------------------------------- Gate C/D


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_cid_ce_20(close), ts_cid_ce_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("length,fires", [(3, 1497), (60, 1440), (250, 1250)])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical_at_other_lengths(
        length, fires, k):
    """The default is not the only reachable setting: `length` is free from 3
    upward."""
    close = _walk()
    base = ts_cid_ce_20(close, length=length)
    scaled = ts_cid_ce_20(close * k, length=length)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == fires
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_are_within_tolerance(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_cid_ce_20(close), ts_cid_ce_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-12
    assert float(base[m].corr(scaled[m], method="spearman")) >= 1.0 - 1e-12


def test_the_difference_of_logarithms_spelling_would_not_be_scale_identical():
    """Why the module spells the return as a price RATIO. `8a / 8b` is the
    same double as `a / b`, but `log(8a) - log(8b)` is not `log(a) - log(b)`:
    on this frame the ratio returns are bit-equal on all 1,499 bars at x8 and
    the difference-of-logarithms returns on 821."""
    close = _walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    assert int(m.sum()) == 1499
    assert (ratio[m] == ratio8[m]).all()
    # 821 locally; the exact count is CPU float detail, so only "some but not
    # all" is pinned.
    assert 0 < int((plain[m] == plain8[m]).sum()) < 1499


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
def test_fires_and_is_not_constant(frame_fn):
    close = frame_fn()
    out = ts_cid_ce_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1480
    assert int(out.nunique()) == 1480
    assert int((out.dropna() != 0).sum()) == 1480


# ------------------------------------------------- what the column means


def test_it_is_invariant_to_an_affine_map_of_the_returns():
    """The strongest property of the column, and the reason it is not a
    volatility reading: the numerator scales by `a**2` under `x -> a*x + b`,
    the variance does too, and the shift cancels in both a difference and a
    deviation. Measured on a walk whose returns are rebuilt at x2 and x0.5,
    and on the same walk given +0.004 of log drift a bar (an affine map of
    the simple returns): Spearman 1.000000 and max |difference| 9.7e-14,
    8.4e-14 and 1.1e-13."""
    close = _walk()
    base = ts_cid_ce_20(close)
    r = (close / close.shift(1) - 1.0).to_numpy()[1:]
    first = float(close.iloc[0])
    others = {
        "x2": Series(np.concatenate([[first],
                                     first * np.cumprod(1.0 + 2.0 * r)])),
        "x0.5": Series(np.concatenate([[first],
                                       first * np.cumprod(1.0 + 0.5 * r)])),
        "drift": Series(close.to_numpy()
                        * np.exp(0.004 * np.arange(len(close)))),
    }
    for other in others.values():
        out = ts_cid_ce_20(other)
        assert (base.isna() == out.isna()).all()
        m = base.notna()
        assert float((base[m] - out[m]).abs().max()) < 1e-12
        assert float(base[m].corr(out[m], method="spearman")) >= 1.0 - 1e-12


def test_it_is_not_volatility_and_not_direction():
    """Pinned where a consumer reads first, because the nearest statistics
    ports are volatility-flavoured and this one is not: Spearman 0.0072
    against the same window's standard deviation, -0.0733 against its mean
    return, -0.0097 against the absolute mean return and -0.0731 against the
    20-bar price change."""
    close = _walk()
    base = ts_cid_ce_20(close)
    r = close / close.shift(1) - 1.0
    rolling = r.rolling(LENGTH, min_periods=LENGTH)
    for other in (rolling.std(), rolling.mean(), rolling.mean().abs(),
                  close / close.shift(LENGTH) - 1.0):
        m = base.notna() & other.notna()
        assert abs(float(base[m].corr(other[m], method="spearman"))) < 0.2


def test_the_level_is_near_sqrt_two_length_for_iid_returns():
    """For iid returns of finite variance the RATIO OF EXPECTATIONS of the
    squared column is exactly `2*length` = 40 -- `E[gap] = 2*(n-1)*sigma**2`
    and `E[var] = (n-1)*sigma**2/n` (arithmetic, not measured, and
    distribution-free: no Gaussian assumption) -- so `sqrt(40)` = 6.3246 is
    the level to compare against. The expectation of a ratio is not the ratio
    of the expectations, so which side the column lands on is MEASURED and not
    derived: `docs/measure_ts_cid_ce_20.py` runs 2,000 independent windows and
    reports median 6.2848, mean 6.2599, sd 0.6723, p10 5.4033, p90 7.1126, min
    3.4785, max 8.0608, finite on 2,000 of 2,000 -- just below it. Pinned
    loosely here on 300 windows. The spread is what a reader needs before
    treating one value as a signal: +-0.9 at the deciles."""
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (300, LENGTH + 1)),
                                     axis=1))
    est = np.array([float(ts_cid_ce_20(Series(p)).iloc[-1]) for p in paths])
    assert np.isfinite(est).all()
    assert 5.8 < float(np.median(est)) < 6.8
    assert 0.4 < float(est.std(ddof=1)) < 1.0
    lo, hi = _closed_form_bounds(LENGTH)
    assert float(est.min()) > lo
    assert float(est.max()) < hi


def test_it_orders_the_ar1_coefficient_downward():
    """The column's actual claim, and its sign. The generator's LOG returns
    are an AR(1) with coefficient `phi`; persistent returns are a SMOOTH path
    and read LOW, alternating ones read HIGH. The medians come out in reverse
    order of `phi`: 4.6865 / 5.5166 / 6.2276 / 6.8905 / 7.5389 at +0.50 /
    +0.25 / 0 / -0.25 / -0.50, with the `phi` = 0 reading near
    `sqrt(2*20)` = 6.3246. The LEVEL grows with the window (measured on a
    20,000-bar `phi` = +0.5 path: 4.8186 / 7.9344 / 14.2868 / 31.6863 at
    `length` 20 / 60 / 200 / 1000, i.e. 0.76 / 0.72 / 0.71 / 0.71 of
    `sqrt(2*length)`), so only the ordering is pinned."""
    medians = [float(ts_cid_ce_20(_ar1(phi=phi)).median())
               for phi in (0.5, 0.25, 0.0, -0.25, -0.5)]
    assert medians == sorted(medians)
    assert medians[0] < 5.0
    assert abs(medians[2] - math.sqrt(2.0 * LENGTH)) < 0.5
    assert medians[-1] > 7.0


def test_it_is_a_slow_state_and_not_an_event_flag():
    """Two consecutive windows share 19 of their 20 returns, so the column
    autocorrelates at 0.8876 at lag 1, 0.3662 at lag 10 and -0.1284 at lag 20
    (measured on a walk)."""
    col = ts_cid_ce_20(_walk()).dropna()
    assert float(col.autocorr(1)) > 0.8
    assert abs(float(col.autocorr(20))) < 0.5


def test_the_identity_against_the_lag_1_autocorrelation():
    """The redundancy disclosure, and the reason it is point 1 of this file.
    With `y` the demeaned window and `v` its population variance,

        sum (y[i]-y[i-1])**2 = 2*length*v - y[oldest]**2 - y[newest]**2
                               - 2 * sum y[i]*y[i-1]

    so the squared column is an AFFINE function of `ts_ac1_60`'s value on the
    same window, up to the two end deviations. Measured: the identity holds to
    2.1e-14 over 1,480 bars, the Spearman against `TS_AC1` at `length` 20 is
    -0.977743, and against the SHIPPED `TS_AC1_60` -0.4218 here (-0.5342
    tick-rounded, -0.4339 on an AR(1) path -- in
    `docs/measure_ts_cid_ce_20.py`).

    Gate E measures against the engine's 687 comparators, which contain no
    pandas_ta port, so nothing downstream will catch this: the two columns
    ship at 20 and 60 returns, and a consumer putting both at the SAME length
    would be double-weighting one signal."""
    close = _walk()
    base = ts_cid_ce_20(close)
    r = close / close.shift(1) - 1.0
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    var, mean = roll.var(ddof=0), roll.mean()
    ends = (r.shift(LENGTH - 1) - mean) ** 2 + (r - mean) ** 2
    ac20 = ts_ac1_60(close, length=LENGTH)
    identity = 2.0 * LENGTH - ends / var - 2.0 * (LENGTH - 1) * ac20
    m = base.notna() & identity.notna()
    assert int(m.sum()) == 1480
    assert float((base[m] ** 2 - identity[m]).abs().max()) < 1e-12
    assert float(base[m].corr(ac20[m], method="spearman")) < -0.95
    ac60 = ts_ac1_60(close)
    m60 = base.notna() & ac60.notna()
    rho60 = float(base[m60].corr(ac60[m60], method="spearman"))
    assert -0.60 < rho60 < -0.30


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    assert ts_cid_ce_20(_walk(LENGTH)) is None


def test_exact_min_history_fires_at_the_warmup_boundary():
    out = ts_cid_ce_20(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH


@pytest.mark.parametrize("length", [None, 0, -5, 1, 2, 0.5, 2.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """A window of two returns is identically 2 -- `(a-b)**2` over
    `(a-b)**2/4` -- so three is the smallest window on which the statistic
    varies, and anything below it is the default instead of a constant
    column."""
    out = ts_cid_ce_20(_walk(400, seed=31), length=length)
    assert out.name == "TS_CID_CE_20"
    assert int(out.notna().sum()) == 380


def test_the_minimum_length_fires_and_varies():
    out = ts_cid_ce_20(_walk(400, seed=31), length=3)
    assert out.name == "TS_CID_CE_3"
    assert int(out.notna().sum()) == 397
    assert int(out.nunique()) > 300
    lo, hi = _closed_form_bounds(3)
    assert float(out.min()) >= lo
    assert float(out.max()) <= hi


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = ts_cid_ce_20(close, length=10), ts_cid_ce_20(close, length=250)
    assert (a.name, b.name) == ("TS_CID_CE_10", "TS_CID_CE_250")
    m = a.notna() & b.notna()
    assert int(m.sum()) == 150
    assert abs(float(a[m].corr(b[m], method="spearman"))) < 0.5


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(ts_cid_ce_20(close, length=50.9),
                                   ts_cid_ce_20(close, length=50))


def test_fillna_applies():
    out = ts_cid_ce_20(_walk(200, seed=13), fillna=-9.0)
    assert int((out == -9.0).sum()) == LENGTH


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data: each empties exactly the 21 windows that contain it, which is the
    `length + 1` closes one value reads (it spoils two returns). Nothing
    before the hole moves."""
    close = _walk(400, seed=21)
    base = ts_cid_ce_20(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = ts_cid_ce_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 220)
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0


@pytest.mark.parametrize("identical,emptied", [(19, 0), (20, 0), (21, 1),
                                               (25, 5)])
def test_a_flat_run_needs_length_plus_one_identical_closes_to_empty_a_bar(
        identical, emptied):
    """The NaN cause that belongs to THIS column rather than to bad data: a
    window of `length` returns has no dispersion when its returns are
    constant to rounding level, and identical closes are one way there (an
    exactly geometric path, whose closes are all distinct, is the other). It
    needs all `length + 1` of them: planted at bar 200 of a 400-bar walk, 19
    and 20 identical closes empty nothing, 21 empty exactly bar 220, 25 empty
    bars 220..224."""
    close = _walk(400, seed=21)
    base = ts_cid_ce_20(close)
    flat = close.copy()
    flat.iloc[200:200 + identical] = float(close.iloc[200])
    out = ts_cid_ce_20(flat)
    holes = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(holes) == emptied
    if emptied:
        assert (int(holes.min()), int(holes.max())) == (220, 220 + emptied - 1)


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "ts_cid_ce_20" in ta.Category["statistics"]
    assert hasattr(df.ta, "ts_cid_ce_20")
    direct = ts_cid_ce_20(close)
    through = df.ta.ts_cid_ce_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "TS_CID_CE_20"
    assert direct.category == "statistics"


def test_the_ledger_has_no_row_for_this_column_yet():
    """Gate E is OWED on this port: the launcher runs
    `gate_e_overlap.py run --module pandas_ta.statistics.ts_cid_ce_20` after
    this session, and `tests/test_gate_e_ledger.py` reports it as owed until
    the row is recorded. This assertion is the receipt session's cue -- it
    fails the moment a row appears, and is to be replaced by the row's
    identity and its numbers, as `tests/test_ts_ac1_60.py` was on issue
    #94."""
    import csv
    import os

    path = os.path.join("docs", "gate_e_ledger.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["column"].startswith("TS_AC1")], \
        "sanity: the ledger should carry the neighbouring ts_ac1_60 row"
    assert [r for r in rows if r["indicator"] == "ts_cid_ce_20"] == []
