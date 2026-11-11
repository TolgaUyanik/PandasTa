# -*- coding: utf-8 -*-
"""LEAN-HURST-100: `lean_hurst_100`, the Hurst exponent in its
lagged-difference form (PandasTa issue #85).

    LEAN_HURST_100_20 = slope of log sd(log(close[t]/close[t-k])) on log k,
                        k = 2 .. 20, over a 100-close window

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line, not
   Lean's code.** QuantConnect Lean's `HurstExponent` C# source is NOT in
   this worktree and web access is unavailable, so "Apache-2.0 Lean" is an
   attribution, not an oracle. What IS checkable is pinned three ways:

   * a window whose slope is **exactly 1/2** in closed form -- closes
     [1, 2, 8, 4, 32] at `length=5, max_lag=3`, where the two-lag fit is a
     difference quotient and the population standard deviations are
     L*sqrt(2/3) and L for L = log 2 (`test_hand_derived_window_is_exactly_a_half`);
   * the screen prototype of `docs/issues/screen/ind_screen.py` (candidate
     `lean_hurst_100`), retyped here because that file is gitignored:
     Spearman 1.000000, max |difference| 1.8e-15, NaN masks equal over
     1,401 fired bars of a 1,500-bar walk;
   * an independent per-window loop in plain Python scalars -- no numpy, no
     pandas rolling: max |difference| 6.7e-16 over 301 bars.

   ⚠ The prototype spells the lagged difference as `x[t+k] - x[t]` of log
   close; this module spells it `log(close[t]/close[t-k])`. The two agree to
   1.8e-15, and the module's spelling is the one that is EXACTLY scale-free
   (item 4). Do not "simplify" it back to a difference of two logarithms.

2. **Gate B, by mutant, on three frames.** Four mutants, each `importlib`-read
   and `exec`'d in memory: the column back-dated by `length`; the lagged
   difference turned forward (`shift(-lag)`); a `center=True` rolling standard
   deviation; and the log-sd row read one bar late. Measured over 34 J values
   of a future-perturbation sweep: the real module leaks at **0/34** and every
   mutant is caught at **34/34**, on a random walk, on a tick-rounded walk and
   on a geometric ladder with one real move in it (the frame where the
   rounding-noise floor decides which windows fire).

3. **The noise floor, and why it is a constant.** `sd == 0` -- the
   prototype's guard -- is not enough: the lagged differences of an exactly
   geometric path are mathematically constant but vary at rounding level in
   float64, so an unguarded fit reads rounding noise and reports a
   PLAUSIBLE-LOOKING number. Measured: a 1%-a-bar ladder fires 201 of 300
   bars unguarded, in [-0.0100, 0.1100]; an exact x1.5 ladder fires 85 of
   300, in [0.2723, 0.5359]. Guarded, both fire 0. The floor is ABSOLUTE
   (4096 eps = 9.1e-13) rather than a rolling scale because the quantity
   floored is a dimensionless log ratio -- so it has no window of its own to
   keep causal. It costs nothing on real-shaped data: 0 bars on a walk and 0
   on a tick-rounded walk, and its crossover sits at about 1e-12 of relative
   jitter, three orders below the smallest variation tick-rounded quotes can
   show (one tick over the price, 1e-9 even at a price of 1e6).

4. **Gate D, and that x8 is bit-identical rather than merely close.** Every
   input is a price RATIO, and `8*a / 8*b` is the same double as `a / b`:
   1,401 of 1,401 bars bit-identical at x8 and x64. The literal
   difference-of-logarithms spelling is NOT: its lag-2 differences are
   bit-equal on only 790 of 1,498 bars at x8. x10 / x3.7 agree to 1.4e-15 /
   2.7e-15 with identical NaN masks.

5. **What the column means, and that its LEVEL is biased.** For iid returns
   the population slope is exactly 0.5, but over 2,000 independent 100-bar
   windows the median is 0.4199 and only 25.65% exceed 0.5, because each lag
   has at most `length - k` OVERLAPPING differences. The ordering is what
   holds: AR(1) return medians 0.7232 / 0.5093 / 0.4301 / 0.3836 / 0.2644 at
   phi = +0.8 / +0.4 / 0 / -0.4 / -0.8. Also drift-invariant to 2.4e-15.

6. **The guard bands, measured rather than asserted.** `length` below 5
   (including 0, negatives and fractions that truncate below 5) falls back to
   100; `max_lag` below 3 falls back to 20; `max_lag` above `length - 2` is
   clamped to it, and the effective value is the one in the column name.

7. **Five-point wiring** (`Category`, the accessor, the export) and the
   NaN behaviour of a bad close: NaN, zero, negative, infinite and subnormal
   closes each empty exactly the 100 windows that contain them, and nothing
   before the hole moves.

Every number above comes from `docs/measure_lean_hurst_100.py`, whose run is
transcribed in `docs/LeanHurst100Measured.md`. Gate E was run by the launcher
on 2026-11-11 (run `is85-lean_hurst_100-f47bf26c`): `LEAN_HURST_100_20` pooled
max |rho| 0.2491 vs `mad_pct`, n = 390,038, per-frame max median 0.2241 over 89
frames, 0 of them at or above 0.90 -- SHIP, recorded in
`docs/gate_e_ledger.csv`.
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.lean_hurst_100 import lean_hurst_100

LENGTH, MAX_LAG = 100, 20
LAGS = range(2, MAX_LAG + 1)


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _ar1_returns(n=1500, phi=0.0, seed=40, sigma=0.01):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + eps[i]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _geometric_with_a_jump(n=1500, step=0.01, jump=0.05, at=700):
    r = np.full(n, step)
    r[at] += jump
    return Series(100.0 * np.exp(np.cumsum(r)))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


# ------------------------------------------------------------- Gate A


def test_hand_derived_window_is_exactly_a_half():
    """close = [1, 2, 8, 4, 32] at length=5, max_lag=3, so only lags 2 and 3
    and the fit is an exact difference quotient. With x = log close =
    [0, L, 3L, 2L, 5L] and L = log 2:

        lag 2 differences: 3L, L, 2L   -> mean 2L, population sd L*sqrt(2/3)
        lag 3 differences: 2L, 4L      -> mean 3L, population sd L
        slope = (log L - log(L*sqrt(2/3))) / (log 3 - log 2)
              = 0.5 * log(1.5) / log(1.5) = 1/2

    Derived by hand, independent of any implementation; the module lands
    1.1e-16 away. Also pins that the four bars before the first full window
    are NaN."""
    out = lean_hurst_100(Series([1.0, 2.0, 8.0, 4.0, 32.0]), length=5, max_lag=3)
    assert out.name == "LEAN_HURST_5_3"
    assert out.iloc[:4].isna().all()
    assert abs(float(out.iloc[4]) - 0.5) < 1e-14


def _prototype(close, length=LENGTH, lags=LAGS):
    """`docs/issues/screen/ind_screen.py` candidate `lean_hurst_100`
    (`w_hurst_lagdiff` + `roll`), retyped because that tree is gitignored:
    the lagged differences of log close INSIDE each window."""
    a = np.log(close).to_numpy(dtype=float)
    W = sliding_window_view(a, length)
    L = np.log(np.array(list(lags), dtype=float))
    with np.errstate(divide="ignore", invalid="ignore"):
        T = np.column_stack([
            np.log(np.where((s := (W[:, k:] - W[:, :-k]).std(1)) == 0, np.nan, s))
            for k in lags])
    Lc = L - L.mean()
    vals = (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    out = np.full(len(a), np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


def test_matches_the_screen_prototype():
    close = _walk()
    base, proto = lean_hurst_100(close), _prototype(close)
    assert (base.isna() == proto.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1401
    assert float((base[m] - proto[m]).abs().max()) < 1e-13
    assert float(base[m].corr(proto[m], method="spearman")) >= 1.0 - 1e-12


def _scalar_loop(close, length=LENGTH, lags=LAGS):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no pandas rolling, every sum written out."""
    c = [float(v) for v in close.to_numpy()]
    ks = list(lags)
    log_k = [math.log(k) for k in ks]
    mean_log_k = sum(log_k) / len(log_k)
    log_k_c = [v - mean_log_k for v in log_k]
    den = sum(v * v for v in log_k_c)
    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        win = c[t - length + 1:t + 1]
        y, ok = [], True
        for k in ks:
            d = [math.log(win[i + k] / win[i]) for i in range(length - k)]
            mu = sum(d) / len(d)
            var = sum((v - mu) ** 2 for v in d) / len(d)
            if math.sqrt(var) <= 9.094947017729282e-13:
                ok = False
                break
            y.append(math.log(math.sqrt(var)))
        if ok:
            mean_y = sum(y) / len(y)
            out[t] = sum((y[j] - mean_y) * log_k_c[j]
                         for j in range(len(ks))) / den
    return Series(out, index=close.index)


def test_matches_an_independent_scalar_loop():
    close = _walk(400, seed=5)
    base, loop = lean_hurst_100(close), _scalar_loop(close)
    assert (base.isna() == loop.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 301
    assert float((base[m] - loop[m]).abs().max()) < 1e-14


def _variant(close, length=LENGTH, lags=LAGS, ddof=0, demean=True,
             cross_window=False):
    """The module's computation with ONE reading changed."""
    px = close.astype(float)
    ks = list(lags)
    log_k = np.log(np.array(ks, dtype=float))
    log_k_c = log_k - log_k.mean()
    cols = []
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in ks:
            d = np.log(px / px.shift(k))
            width = length if cross_window else length - k
            if demean:
                s = d.rolling(width, min_periods=width).std(ddof=ddof)
            else:
                s = np.sqrt((d ** 2).rolling(width, min_periods=width).sum()
                            / (width - ddof))
            cols.append(np.log(s.where(s > 0).to_numpy()))
    T = np.column_stack(cols)
    return Series(((T - T.mean(axis=1, keepdims=True)) * log_k_c).sum(axis=1)
                  / (log_k_c ** 2).sum(), index=close.index)


def test_the_sample_standard_deviation_reading_is_rank_identical_but_not_equal():
    """`ddof=1` is the reading this port rejects. It is NOT cosmetic
    arithmetically -- the divisor changes with k, so the fit tilts -- but on
    a 1,500-bar walk it moves no ranks at all, which is what the reader of
    this test needs to know before arguing about it."""
    close = _walk()
    base, other = lean_hurst_100(close), _variant(close, ddof=1)
    m = base.notna() & other.notna()
    diff = float((base[m] - other[m]).abs().max())
    assert 1e-5 < diff < 1e-2
    assert int((base[m] == other[m]).sum()) == 0
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


@pytest.mark.parametrize("kwargs,lo,hi", [
    ({"demean": False}, 0.2, 0.4),          # root mean square, mean kept
    ({"lags": range(1, MAX_LAG + 1)}, 0.05, 0.2),   # k from 1
    ({"cross_window": True}, 0.2, 0.4),     # `length` differences per lag
])
def test_the_other_rejected_readings_are_different_columns(kwargs, lo, hi):
    """Each is a reading the issue's wording leaves open and this port
    rejects; each moves the column by a visible amount, so the choice is a
    decision and not a formatting detail."""
    close = _walk()
    base, other = lean_hurst_100(close), _variant(close, **kwargs)
    m = base.notna() & other.notna()
    diff = float((base[m] - other[m]).abs().max())
    assert lo < diff < hi
    assert float(base[m].corr(other[m], method="spearman")) < 0.999


def test_the_crossing_window_reading_needs_more_history():
    """The rejected `length`-differences-per-lag reading reaches `max_lag`
    bars further back, so it cannot fire where this column does."""
    close = _walk()
    base = lean_hurst_100(close)
    other = _variant(close, cross_window=True)
    assert int(base.notna().to_numpy().argmax()) == LENGTH - 1
    assert int(other.notna().to_numpy().argmax()) == LENGTH - 1 + MAX_LAG


# ------------------------------------------------------------- Gate B

_REAL = importlib.import_module("pandas_ta.statistics.lean_hurst_100")

WRITE_SHIFT_MUTANT = (
    "    hurst = Series(values, index=close.index)",
    "    hurst = Series(values, index=close.index).shift(-length)")
FORWARD_DIFF_MUTANT = (
    "            diff = np.log(px / px.shift(lag))",
    "            diff = np.log(px / px.shift(-lag))")
CENTERED_SD_MUTANT = (
    "            sd = diff.rolling(width, min_periods=width).std(ddof=0)",
    "            sd = diff.rolling(width, min_periods=width, center=True).std(ddof=0)")
LATE_ROW_MUTANT = (
    "            log_sd[:, j] = np.log(sd.where(sd > NOISE_FLOOR).to_numpy())",
    "            log_sd[:, j] = np.log(sd.where(sd > NOISE_FLOOR).shift(-1).to_numpy())")

MUTANTS = [WRITE_SHIFT_MUTANT, FORWARD_DIFF_MUTANT, CENTERED_SD_MUTANT,
           LATE_ROW_MUTANT]
OFFSETS = range(150, 1500, 40)  # past the 100-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "geometric+jump": (_geometric_with_a_jump(),
                       _geometric_with_a_jump(step=0.013, jump=0.07, at=640)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lean_hurst_100_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn, close, other):
    """Replace every bar from J onward with a different path; count the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
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


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _leaks(lean_hurst_100, close, other) == 0


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("mutant", MUTANTS, ids=["write_shift", "forward_diff",
                                                 "centered_sd", "late_row"])
def test_each_mutant_is_caught_on_each_frame(mutant, frame):
    mod = _load_mutant(*mutant)
    close, other = FRAMES[frame]
    assert not mod.lean_hurst_100(close).equals(lean_hurst_100(close))  # live
    assert _leaks(mod.lean_hurst_100, close, other) == len(list(OFFSETS))


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep above
    covers."""
    close = _walk(400, seed=3)
    base = lean_hurst_100(close)
    pd.testing.assert_series_equal(lean_hurst_100(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(lean_hurst_100(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------- the noise floor


def test_an_exactly_geometric_frame_is_nan_rather_than_rounding_noise():
    """Both ladders have mathematically constant lagged differences, so
    there is no slope to report. Unguarded (`sd > 0`, the prototype's
    guard) they report one anyway, out of float64 rounding, and it looks
    plausible -- which is worse than NaN."""
    n = 300
    for frame in (Series(100.0 * np.exp(np.arange(n) * 0.01)),
                  Series(np.cumprod(np.full(n, 1.5)) * 1e-20)):
        guarded, unguarded = lean_hurst_100(frame), _variant(frame)
        assert int(guarded.notna().sum()) == 0
        assert int(unguarded.notna().sum()) > 50
        assert float(unguarded.abs().max()) < 1.0  # plausible-looking, not wild


def test_an_exactly_flat_frame_is_nan():
    assert int(lean_hurst_100(Series(np.full(300, 50.0))).notna().sum()) == 0


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded])
def test_the_noise_floor_costs_nothing_on_real_shaped_data(frame_fn):
    """The floor must not eat small REAL variation. On a walk and on a
    tick-rounded walk (prices on a 0.01 grid, as quotes are) it changes
    neither a NaN flag nor a value against the unguarded form."""
    frame = frame_fn(300)
    guarded, unguarded = lean_hurst_100(frame), _variant(frame)
    assert int(guarded.notna().sum()) == 201
    assert (guarded.isna() == unguarded.isna()).all()
    m = guarded.notna()
    assert (guarded[m] == unguarded[m]).all()


def test_the_noise_floor_is_an_absolute_constant_not_a_window():
    """It is deliberately NOT a rolling quantity: what it floors is a
    dimensionless log ratio, so a constant works and the floor has no
    window of its own whose causality would need pinning."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(".rolling(") == 1  # one window, so one thing to keep causal


# ------------------------------------------------------------- Gate D


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = lean_hurst_100(close), lean_hurst_100(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1401
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_are_within_tolerance(k):
    close = _walk()
    base, scaled = lean_hurst_100(close), lean_hurst_100(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-13


def test_the_difference_of_logarithms_spelling_would_not_be_bit_identical():
    """Why the module takes ONE logarithm of a ratio. `8*a / 8*b` is the
    same double as `a / b`, but `log(8a) - log(8b)` is not `log(a) - log(b)`:
    on this frame the lag-2 differences come out bit-equal on only part of
    the bars, and the slope inherits that."""
    close = _walk()
    ld = np.log(close)
    plain = (ld - ld.shift(2)).to_numpy()
    scaled = (np.log(close * 8.0) - np.log(close * 8.0).shift(2)).to_numpy()
    m = ~np.isnan(plain)
    assert int((plain[m] == scaled[m]).sum()) < int(m.sum())
    ratio = np.log(close / close.shift(2)).to_numpy()
    ratio8 = np.log(close * 8.0 / (close * 8.0).shift(2)).to_numpy()
    assert (ratio[m] == ratio8[m]).all()


def test_fires_and_is_not_constant():
    close = _walk()
    out = lean_hurst_100(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1401
    assert int(out.nunique()) == 1401


# ------------------------------------------------- what the column means


def test_the_level_is_biased_low_for_iid_returns():
    """The population slope for iid returns is exactly 0.5. On a 100-bar
    window it is not measured as 0.5, and the size of that gap is the
    number a reader needs: median 0.4199 over 2,000 independent windows,
    above 0.5 on about a quarter of them. Pinned loosely (the seed is
    fixed, the bound is not tight) so it documents the bias without
    pinning float noise."""
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (300, LENGTH)),
                                     axis=1))
    est = np.array([float(lean_hurst_100(Series(p)).iloc[-1]) for p in paths])
    assert np.isfinite(est).all()
    assert 0.36 < float(np.median(est)) < 0.47
    assert float((est > 0.5).mean()) < 0.40


def test_it_orders_persistence():
    """AR(1) returns: phi = +0.8 is persistent, -0.8 reverses. The medians
    must come out in that order, which is the column's actual claim."""
    medians = [float(lean_hurst_100(_ar1_returns(phi=phi, seed=40 + i)).median())
               for i, phi in enumerate((0.8, 0.4, 0.0, -0.4, -0.8))]
    assert medians == sorted(medians, reverse=True)
    assert medians[0] > 0.65 > medians[-1]


def test_it_is_invariant_to_drift():
    """A constant added to every log return shifts lag k's differences by
    k*drift and leaves their standard deviation alone, so the slope does
    not move. Equal to 2.4e-15, not bit-equal."""
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    base, out = lean_hurst_100(close), lean_hurst_100(drifted)
    assert (base.isna() == out.isna()).all()
    m = base.notna()
    assert float((base[m] - out[m]).abs().max()) < 1e-13


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    assert lean_hurst_100(_walk(99)) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    out = lean_hurst_100(_walk(100, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH - 1


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data: they empty exactly the 100 windows that contain them. Nothing
    before the hole moves -- the values after it shift in the last bits
    because pandas' rolling standard deviation is an online accumulation,
    which is float noise and not a read of the future (Gate B's sweep is
    the test for that)."""
    close = _walk(400, seed=21)
    base = lean_hurst_100(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = lean_hurst_100(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH
    assert (int(emptied.min()), int(emptied.max())) == (200, 299)
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0
    shared = base.notna() & out.notna()
    assert float((base[shared] - out[shared]).abs().max()) < 1e-14


@pytest.mark.parametrize("length", [None, 0, -5, 4, 0.5, 2.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = lean_hurst_100(_walk(400, seed=31), length=length)
    assert out.name == "LEAN_HURST_100_20"


@pytest.mark.parametrize("max_lag", [None, 0, -1, 2])
def test_a_max_lag_below_three_falls_back_to_the_default(max_lag):
    out = lean_hurst_100(_walk(400, seed=31), max_lag=max_lag)
    assert out.name == "LEAN_HURST_100_20"


@pytest.mark.parametrize("max_lag,effective", [(3, 3), (50, 50), (98, 98),
                                               (99, 98), (200, 98)])
def test_max_lag_is_clamped_to_length_minus_two_and_the_name_says_so(
        max_lag, effective):
    out = lean_hurst_100(_walk(400, seed=31), max_lag=max_lag)
    assert out.name == f"LEAN_HURST_100_{effective}"
    assert int(out.notna().sum()) == 301


def test_a_short_length_clamps_max_lag_too():
    out = lean_hurst_100(_walk(400, seed=31), length=5, max_lag=20)
    assert out.name == "LEAN_HURST_5_3"
    assert int(out.notna().sum()) == 396


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = lean_hurst_100(close, length=50), lean_hurst_100(close, length=200)
    assert a.name == "LEAN_HURST_50_20"
    assert b.name == "LEAN_HURST_200_20"
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert float(a[m].corr(b[m], method="spearman")) < 0.9


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(lean_hurst_100(close, length=50.9),
                                   lean_hurst_100(close, length=50))


def test_fillna_applies():
    close = _walk(200, seed=13)
    out = lean_hurst_100(close, fillna=-1.0)
    assert int((out == -1.0).sum()) == LENGTH - 1


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "lean_hurst_100" in ta.Category["statistics"]
    assert hasattr(df.ta, "lean_hurst_100")
    direct = lean_hurst_100(close)
    through = df.ta.lean_hurst_100()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "LEAN_HURST_100_20"
    assert lean_hurst_100(close).category == "statistics"
