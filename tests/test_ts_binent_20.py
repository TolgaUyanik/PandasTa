# -*- coding: utf-8 -*-
"""TS-BINENT-20: `ts_binent_20`, tsfresh's binned entropy on returns
(PandasTa issue #89).

    TS_BINENT_20_5 = -sum(p * log p), p = share of the 20 returns falling in
                     each of 5 equal-width bins laid across the window's own
                     [min, max]

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **That the column is a DISCRETE count statistic, and what follows from
   that.** The value is a function of the window's bin COUNT VECTOR, nothing
   else. The entropy FUNCTION takes **182** distinct values over the **7,315**
   count vectors a 20-return window can produce, bounded below by the 19/1
   two-bin value **0.198515** and above by the even split (four returns per
   bin), which in
   float64 is **1.6094379124341005** -- one ulp ABOVE `math.log(5)`, because
   the five terms are accumulated one bin at a time, so `value <= log(bins)`
   is false by a last bit (pinned by
   `test_the_top_of_the_range_is_one_ulp_above_log_bins`).
   ⚠ **That 182 counts values rounded to 1e-12, and the module's raw float64
   output has more**, for the same accumulation reason: two count vectors that
   are permutations of each other land on different last bits. Measured per
   frame on 1,480 fired bars: **154 / 136 / 193** distinct float64 values on
   the walk / the tick-rounded walk / the student-t path, collapsing to
   **104 / 85 / 137** at 1e-12, where they are all inside the attainable set
   and the raw values are not. Both counts are asserted, so the rounded and
   the raw can never be quoted as each other again. Three consequences are
   pinned here rather than discovered later: a rank statistic over this column
   carries heavy ties; a last-bit change in a return usually does NOT change
   the value (which is why ×10 and ×3.7 come out bit-identical below); and a
   look-ahead mutant can be absorbed at an offset (item 3).

2. **Gate A, and that the formula under test is the ISSUE's line plus the
   prototype.** tsfresh is NOT installed in this worktree and web access is
   unavailable, so "tsfresh (MIT)" is an attribution, not an oracle. What IS
   checkable is pinned five ways:

   * a window at the SHIPPED defaults whose value is exactly **1.5·log 2** --
     eleven closes of 1, five ×1.5 steps and five ×2 steps, so the 20 returns
     are ten +0, five +1/2 and five +1, the bins are [10,0,5,0,5] and
     `p = (1/2, 1/4, 1/4)`; the module lands **0.0** away
     (`test_the_hand_derived_window_at_the_defaults_is_exactly_one_and_a_half_log_two`);
   * three more hand-derived windows at other settings, all exact;
   * the screen prototype of `docs/issues/screen/ind_screen.py` (candidate
     `ts_binent_20`), retyped here because that file is gitignored:
     **bit-equal on 1,480 of 1,480** fired bars. `docs/measure_ts_binent_20.py`
     also IMPORTS the prototype out of the owner's tree when it is there and
     gets the same 1,480 of 1,480;
   * the DEFINITION of equal-width binning spelled with numpy's own
     `np.histogram`, window by window, sharing no window machinery and no bin
     arithmetic with the module: **bit-equal on 1,480 of 1,480** on a walk AND
     on a tick-rounded walk (where returns repeat and ties matter);
   * an independent per-window loop in plain Python scalars: max |difference|
     **2.2e-16** over 380 bars, 0 bars differing by more than 1e-12. Spearman
     against it is 0.999831 rather than 1.000000 *because* of item 1 -- a
     last-bit difference re-orders tied values; it is not a disagreement about
     any distinct value.

3. **Gate B, by mutant, on three frames and three further parameter
   settings.** Five
   mutants, each `importlib`-read and `exec`'d in memory: the column
   back-dated by 2 bars; the column back-dated by `length - 1`; the return
   stamped one bar early; the window rolled `length // 2` bars into the
   future; the bin's lower edge taken from the window `length` bars ahead.
   Over 37 J values of a future-perturbation sweep the **real module leaks
   0/37 in every one of the 6 configurations run** — three frames at the
   defaults, plus `(20, 10)`, `(60, 5)` and `(5, 5)` on the walk; the
   settings are NOT re-run on the other two frames, so this is 6
   configurations and not a 3×4 cross product. Mutants are caught 37/37 in
   **24 of the 30** mutant cells (5 mutants × 3 frames, plus 5 × 3 further
   settings); the six that are not are asserted rather than excused, under two
   explanations:

   * **four cells at 36/37, all at `length=60`**, miss only J = 40, the one
     sweep offset below a 60-bar warm-up, where both prefixes are entirely
     NaN -- asserted, not argued;
   * **two cells where the discrete column absorbed the change** (the
     forward-return mutant, 36/37 on the tick-rounded frame missing J = 120
     and 34/37 at `length=5` missing J = 200/400/1000). The mechanism is
     measured, not asserted: at those offsets the perturbed return genuinely
     differs (by 9.9e-03 and up to 5.2e-01), and the window's bin counts
     either do not move at all (`[1,6,5,6,2]` both ways) or move to a
     PERMUTATION of themselves (`[4,0,0,0,1] -> [1,0,0,0,4]`) -- and the
     entropy is a symmetric function of the counts, so a permutation is
     bit-identical.

   The same property bounds how sensitive the sweep is, which is why it runs
   three frames: a ONE-BAR edge leak (the lower edge taken from the next
   window instead of a whole window ahead) is caught 37/37 on the walk, 35/37
   on the student-t path and only **5/37** on the tick-rounded frame, where
   1,339 of 1,480 consecutive window pairs share their minimum.

4. **The noise floor, and why it matters more here than for `ts_c3_20`.**
   `max - min != 0` is not enough: the returns of an exactly geometric path
   are mathematically constant but vary at rounding level in float64, and an
   unguarded reading bins that noise into a value that looks **ordinary**.
   Measured: a 1%-a-bar ladder fires 0 of 300 bars guarded and **280
   unguarded, spanning [0.6474, 1.5114]** -- inside the live range of a real
   walk ([0.9262, 1.6094]), so nothing downstream could have spotted them.
   `ts_c3_20`'s unguarded values reached 8.0e+41 and were obvious; these are
   not. The floor is ABSOLUTE (4096 eps = 9.09e-13) because what it floors is
   the range of dimensionless price ratios. On a walk and a tick-rounded walk
   it changes neither a NaN flag nor a value (280 of 300 bars fire on each).

5. **Gate D, and that ×8 is bit-identical rather than merely close.** Every
   input is a price RATIO and `8a / 8b` is the same double as `a / b`: 1,480
   of 1,480 bars bit-identical at ×8 and ×64 on each of three frames, and at
   `bins=10` (1,480), `length=60` (1,440) and `length=5` (1,495). ×10 and
   ×3.7 are bit-identical on these frames TOO -- which the arithmetic does not
   promise and which this file states as a measurement, not a guarantee (item
   1 is the reason). The difference-of-logarithms spelling of the return is
   not scale-identical: bit-equal on 821 of 1,499 bars at ×8 where the ratio
   spelling is bit-equal on all 1,499.

6. **What the column is INVARIANT to, which is the thing most likely to be
   misread.** The bins are anchored on the window's own min and max, so
   `r -> a·r + b` (`a > 0`) leaves every count unchanged. Measured: +0.004 of
   log drift a bar is bit-identical on 1,480 of 1,480 bars, and so is scaling
   the returns themselves by ×0.5 or ×3. It is therefore **not** a volatility
   feature and **not** a trend feature; `ts_c3_20`, the neighbouring returns
   statistic, is NOT drift-invariant (Spearman 0.8013) and a reader should not
   carry either property across.

7. **What it does read: concentration / outlier dominance.** Medians over
   1,500-bar paths whose returns differ in shape: uniform 1.5260, gaussian
   1.4737, laplace 1.3748, student-t(2) 1.2348, two-point (±σ) 0.6881. A
   single planted +50-sigma return reads exactly the 19/1 floor 0.198515 on
   all 20 windows that hold it; a +10-sigma one takes them to a median of
   0.8557 against the frame's 1.4989.

8. **The five readings the wording leaves open, each priced.** Equal-width
   bins, because the equal-FREQUENCY reading is a CONSTANT column (`log 5` on
   1,480 of 1,480 bars -- 5 bins of 4 samples each); `bins=5`, because 3 bins
   is Spearman 0.651029 and 10 bins 0.724187 against it; nats unnormalised,
   because `/log(5)` is a strict rescaling (exact, Spearman 1.000000); simple
   returns, because log returns are Spearman 0.944970 with max |difference|
   0.2502; and NaN for a degenerate window, where a literal `np.histogram`
   reading returns exactly 0 (measured: 280 of 300 bars of a flat frame, all
   exactly 0.0, where this column fires on none).

9. **The guard bands, measured rather than asserted.** `length` below 3
   (including 0, negatives, 2, and fractions that truncate below 3) falls back
   to 20 -- 3 because a 2-return window is the constant `log 2` (measured: 1
   distinct value over 398 windows); `bins` below 2 falls back to 5; `bins`
   above `length` is clamped to `length`, and the effective value is the one in
   the column name.

10. **Five-point wiring** (`Category`, the accessor, the export) and the NaN
    behaviour of a bad close: NaN, zero, negative, infinite and subnormal
    closes each empty exactly the 21 windows that contain them (`length + 1`
    closes per value), and nothing before the hole moves. The other NaN cause
    is a window whose returns span 9.09e-13 or less: 21 identical closes empty
    exactly one bar and 20 empty none -- and bar 219 of that frame reads
    exactly 0.198515, the 19-zeros-and-one-move value, which is the column
    saying "one move, nineteen flat bars" rather than failing.

Every number above comes from `docs/measure_ts_binent_20.py`, whose run is
transcribed in `docs/TsBinent20Measured.md`. Gate E is owed: the launcher runs
`gate_e_overlap.py` after this session and a later session records the
`docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.
"""
import importlib
import itertools
import math
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ts_binent_20 import ts_binent_20

LENGTH, BINS = 20, 5
LOG_BINS = math.log(BINS)
#: 19 returns in one bin and 1 in another -- the least a non-degenerate
#: 20-return window can score, and the value a flat run with one move reads.
TWO_BIN_FLOOR = -(0.95 * math.log(0.95) + 0.05 * math.log(0.05))


def _even_split_top(length=LENGTH, bins=BINS):
    """The top of the attainable range, accumulated bin by bin the way the
    module accumulates it. In float64 this is 1.6094379124341005, which is
    ONE ULP ABOVE `math.log(5)` = 1.6094379124341003 -- so `value <= log(bins)`
    is false by a last bit, and the bound has to be written with the ulp in
    it."""
    h = 0.0
    for _ in range(bins):
        p = (length // bins) / length
        h -= p * math.log(p)
    return h


TOP = _even_split_top()

_REAL = importlib.import_module("pandas_ta.statistics.ts_binent_20")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    """A path whose simple returns are exactly `r` where representable."""
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _uniform_returns(n=1500, seed=5, half=0.02):
    rng = np.random.default_rng(seed)
    return _from_returns(rng.uniform(-half, half, n))


def _laplace_returns(n=1500, seed=6, scale=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(rng.laplace(0.0, scale, n), -0.5, 0.5))


# ------------------------------------------------------------- Gate A


HAND_CASES = [
    # (closes, length, bins, exact value, column name)
    (Series([1.0] * 11 + [1.5, 2.25, 3.375, 5.0625, 7.59375]
            + [15.1875, 30.375, 60.75, 121.5, 243.0]), 20, 5,
     1.5 * math.log(2.0), "TS_BINENT_20_5"),
    (Series([1.0, 1.0, 1.0, 1.0, 2.0]), 4, 4,
     -(0.75 * math.log(0.75) + 0.25 * math.log(0.25)), "TS_BINENT_4_4"),
    (Series([1.0, 1.0, 2.0, 6.0, 24.0]), 4, 4, math.log(4.0), "TS_BINENT_4_4"),
    (Series([1.0, 2.0, 1.0, 2.0, 1.0]), 4, 2, math.log(2.0), "TS_BINENT_4_2"),
]


def test_the_hand_derived_window_at_the_defaults_is_exactly_one_and_a_half_log_two():
    """The shipped parameterisation, derived by hand and exact in binary.
    Eleven closes of 1, then five ×1.5 steps, then five ×2 steps, so the 20
    returns are ten +0, five +1/2 and five +1 -- every one of them exactly
    representable, and so are the closes (3^k / 2^k and its doublings).

        lo = 0, hi = 1, five bins of width 1/5
        k = floor(r * 5) = 0 for +0, 2 for +1/2, 5 -> clipped to 4 for +1
        counts [10, 0, 5, 0, 5], p = (1/2, 1/4, 1/4)
        h = (1/2)log2 + (1/4)log4 + (1/4)log4 = (1/2)log2 + log2 = 1.5·log 2

    Measured: the module is 0.0 away, and bars 0..19 are NaN."""
    closes, length, bins, exact, name = HAND_CASES[0]
    out = ts_binent_20(closes, length=length, bins=bins)
    assert out.name == name
    assert out.iloc[:length].isna().all()
    assert float(out.iloc[length]) == exact


@pytest.mark.parametrize("closes,length,bins,exact,name", HAND_CASES[1:],
                         ids=["three-zeros-and-a-move", "zero-one-two-three",
                              "two-bins-half-and-half"])
def test_more_hand_derived_windows_are_exact(closes, length, bins, exact, name):
    """Three more windows whose bin counts can be written out by hand:
    returns [0,0,0,+1] over 4 bins give counts [3,0,0,1] and
    `-(3/4·log(3/4) + 1/4·log(1/4))`; returns [0,+1,+2,+3] over 4 bins give
    [1,1,1,1] and `log 4`; returns [+1,-1/2,+1,-1/2] over 2 bins give [2,2]
    and `log 2`. Each is exact to the last bit."""
    out = ts_binent_20(closes, length=length, bins=bins)
    assert out.name == name
    assert float(out.iloc[length]) == exact


def _prototype(close, length=LENGTH, bins=BINS):
    """`docs/issues/screen/ind_screen.py` candidate `ts_binent_20`, retyped
    because that tree is gitignored:

        @cand("ts_binent_20", "binned entropy of returns (20, 5 bins)", ...)
        def _(o, h, l, c, v): return roll(ret(c), 20, w_binned_entropy)

        def w_binned_entropy(W, bins=5):
            lo = W.min(1, keepdims=True); hi = W.max(1, keepdims=True)
            rng = np.where(hi - lo == 0, np.nan, hi - lo)
            k = np.clip(np.floor((W - lo) / rng * bins), 0, bins - 1)
            h = np.zeros(len(W))
            for b in range(bins):
                p = (k == b).mean(1)
                h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1)), 0)
            return np.where(np.isnan(rng[:, 0]), np.nan, h)

    with `ret(c) = c / c.shift(1) - 1`, `_win` = `sliding_window_view` and
    `_from_win` writing the values from index `n - 1` on."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    W = sliding_window_view(r, length)
    lo, hi = W.min(1, keepdims=True), W.max(1, keepdims=True)
    rng = np.where(hi - lo == 0, np.nan, hi - lo)
    k = np.clip(np.floor((W - lo) / rng * bins), 0, bins - 1)
    h = np.zeros(len(W))
    for b in range(bins):
        p = (k == b).mean(1)
        h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1)), 0)
    out = np.full(len(r), np.nan)
    out[length - 1:] = np.where(np.isnan(rng[:, 0]), np.nan, h)
    return Series(out, index=close.index)


def test_matches_the_screen_prototype():
    """Bit-equal, not merely close: the module keeps the prototype's own
    arithmetic and its own order of accumulation, and on a continuous walk no
    window reaches the noise floor the prototype does not have."""
    close = _walk()
    base, proto = ts_binent_20(close), _prototype(close)
    assert (base.isna() == proto.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == proto[m]).all()


def _histogram_definition(close, length=LENGTH, bins=BINS):
    """The definition of binned entropy spelled with numpy's own
    `np.histogram`: bin shares, zeros replaced by 1 so an empty bin
    contributes nothing, Shannon entropy in nats. An independent
    implementation of equal-width binning -- no sliding window, no bin
    arithmetic of our own.

    ⚠ This is the standard definition, NOT a read of tsfresh's source:
    tsfresh is not installed in this worktree."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    out = np.full(len(r), np.nan)
    for t in range(length, len(r)):
        w = r[t - length + 1:t + 1]
        if np.isnan(w).any():
            continue
        hist, _ = np.histogram(w, bins=bins)
        probs = np.where(hist == 0, 1.0, hist / w.size)
        out[t] = float(-np.sum(probs * np.log(probs)))
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn,fires", [(_walk, 1480),
                                            (_tick_rounded, 1480)])
def test_matches_the_numpy_histogram_definition(frame_fn, fires):
    """The tick-rounded frame is the one that matters: its returns repeat, so
    samples sit on bin edges and a sloppy edge convention would show up."""
    close = frame_fn()
    base, other = ts_binent_20(close), _histogram_definition(close)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) == fires
    assert (base[m] == other[m]).all()


def _scalar_loop(close, length=LENGTH, bins=BINS):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no sliding window, every count written out."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        w = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        lo, hi = min(w), max(w)
        span = hi - lo
        if not span > _REAL.NOISE_FLOOR:
            continue
        counts = [0] * bins
        for v in w:
            k = int(math.floor((v - lo) / span * bins))
            counts[0 if k < 0 else (bins - 1 if k > bins - 1 else k)] += 1
        h = 0.0
        for n in counts:
            if n:
                p = n / length
                h -= p * math.log(p)
        out[t] = h
    return Series(out, index=close.index)


def test_matches_an_independent_scalar_loop():
    """Max |difference| 2.2e-16 over 380 bars and 0 bars differing by more
    than 1e-12. Spearman is 0.999831 rather than 1.000000 because the column
    ties heavily (93 distinct values here) and a last-bit difference reorders
    tied bars -- so this test pins the VALUES, and the tie behaviour is
    pinned by `test_the_attainable_set_is_182_values_to_1e12`."""
    close = _walk(400, seed=5)
    base, loop = ts_binent_20(close), _scalar_loop(close)
    assert (base.isna() == loop.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 380
    diff = (base[m] - loop[m]).abs()
    assert float(diff.max()) < 1e-15
    assert int((diff > 1e-12).sum()) == 0


def _variant(close, length=LENGTH, bins=BINS, log_returns=False,
             quantile_bins=False, normalise=False, degenerate_zero=False,
             guard=True):
    """The module's computation with ONE reading changed, written as a
    per-window loop so a rejected reading cannot inherit the module's
    vectorised window arithmetic."""
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    r = np.full(c.size, np.nan)
    r[1:] = np.log(c[1:] / c[:-1]) if log_returns else c[1:] / c[:-1] - 1.0
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = r[t - length + 1:t + 1]
        if np.isnan(w).any():
            continue
        lo, hi = float(w.min()), float(w.max())
        span = hi - lo
        alive = span > _REAL.NOISE_FLOOR if guard else span != 0.0
        if not alive:
            if degenerate_zero and span == 0.0:
                out[t] = 0.0
            continue
        if quantile_bins:
            edges = np.quantile(w, np.linspace(0.0, 1.0, bins + 1))
            k = np.clip(np.searchsorted(edges[1:-1], w, side="right"),
                        0, bins - 1)
        else:
            k = np.clip(np.floor((w - lo) / span * bins), 0, bins - 1)
        p = np.array([(k == b).sum() for b in range(bins)],
                     dtype=float) / length
        nz = p[p > 0.0]
        value = float(-(nz * np.log(nz)).sum())
        out[t] = value / math.log(bins) if normalise else value
    return Series(out, index=close.index)


def test_the_equal_frequency_reading_is_a_constant_column():
    """The sharpest of the five open readings: equal-FREQUENCY (quantile)
    bins put `length / bins` = 4 samples in each of the 5 bins by
    construction, so `p = 1/5` on every bar and the value is exactly `log 5`
    everywhere. It is not a different column, it is no column at all -- which
    is why equal-width bins are the reading and why this is a test rather
    than a sentence."""
    close = _walk()
    other = _variant(close, quantile_bins=True).dropna()
    assert len(other) == 1480
    assert int(other.nunique()) == 1
    assert int((other - LOG_BINS).abs().lt(1e-12).sum()) == 1480
    base = ts_binent_20(close)
    m = base.notna()
    assert int(base[m].nunique()) > 1  # the port is not constant


@pytest.mark.parametrize("bins,rho", [(3, 0.651029), (10, 0.724187)])
def test_the_bin_count_is_a_real_choice_not_a_formatting_detail(bins, rho):
    """`bins=5` is the issue's number. 3 and 10 are different columns, which
    is what makes 5 a decision: Spearman 0.651029 and 0.724187 against the
    default on the same 1,500-bar walk."""
    close = _walk()
    base, other = ts_binent_20(close), ts_binent_20(close, bins=bins)
    assert other.name == f"TS_BINENT_20_{bins}"
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1480
    # abs=0.01: CI's runner measured 0.648490 / 0.724440 (CPU float detail)
    assert float(base[m].corr(other[m], method="spearman")) == pytest.approx(
        rho, abs=0.01)


def test_normalising_by_log_bins_is_a_strict_rescaling():
    """Dividing by `log(bins)` would put the column in [0, 1]. It is a strict
    rescaling -- `port / log(5)` reproduces it exactly -- so nothing that
    ranks the column could tell the two apart, and the unnormalised nats are
    kept because that is the standard `binned_entropy` form."""
    close = _walk()
    base, other = ts_binent_20(close), _variant(close, normalise=True)
    m = base.notna() & other.notna()
    assert float((base[m] / LOG_BINS - other[m]).abs().max()) == 0.0
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


def test_log_returns_are_a_different_column():
    """A monotone but NON-affine transform of the returns moves samples
    across bin edges, so this reading matters more here than it would for a
    moment-based column: max |difference| 0.2502, Spearman 0.944970, and 831
    of 1,480 bars still bit-equal (the windows where no sample crossed an
    edge)."""
    close = _walk()
    base, other = ts_binent_20(close), _variant(close, log_returns=True)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1480
    assert 0.2 < float((base[m] - other[m]).abs().max()) < 0.3
    assert int((base[m] == other[m]).sum()) == 831
    assert 0.93 < float(base[m].corr(other[m], method="spearman")) < 0.96


def test_the_degenerate_window_is_nan_where_the_literal_histogram_is_zero():
    """The fifth open reading, with the mechanism taken from numpy rather
    than from a sentence: `np.histogram` widens a zero-width range to
    `[v - 0.5, v + 0.5]`, so a window whose returns are all equal lands
    entirely in the MIDDLE bin and the literal reading is exactly 0. This
    port says NaN: that is the prototype's reading and the one issue #89's
    Gate E numbers were screened with. The literal reading here is the real
    `np.histogram` path (`_histogram_definition`, which does not skip a
    zero-width window), not a hand-written 0.0 -- measured on a flat frame,
    280 of 300 bars, all of them exactly 0.0 -- and on a walk the two
    readings cannot differ at all."""
    # the widening, asserted from numpy
    hist, edges = np.histogram(np.zeros(LENGTH), bins=BINS)
    assert list(hist) == [0, 0, LENGTH, 0, 0]
    assert (edges[0], edges[-1]) == (-0.5, 0.5)

    flat = Series(np.full(300, 50.0))
    literal = _histogram_definition(flat)
    assert int(ts_binent_20(flat).notna().sum()) == 0
    assert int(literal.notna().sum()) == 280
    assert int((literal == 0.0).sum()) == 280
    # and the hand-written variant used elsewhere in this file agrees with it
    hand = _variant(flat, guard=False, degenerate_zero=True)
    assert (hand.isna() == literal.isna()).all()
    assert (hand[hand.notna()] == literal[literal.notna()]).all()

    close = _walk()
    base, other = ts_binent_20(close), _variant(
        close, guard=False, degenerate_zero=True)
    m = base.notna()
    assert (base.isna() == other.isna()).all()
    assert (base[m] == other[m]).all()


def _attainable_values(length=LENGTH, bins=BINS):
    """Every value a window can take: the entropy of a bin count vector
    summing to `length` with at least two bins occupied (the window's min and
    max always sit in different bins once the range is non-zero). Entropy is
    a symmetric function of the counts, so enumerating multisets is enough --
    `docs/measure_ts_binent_20.py` enumerates the 7,315 ORDERED vectors as
    well and gets the same set."""
    values = set()
    for counts in itertools.combinations_with_replacement(
            range(length + 1), bins):
        if sum(counts) != length or sum(1 for n in counts if n) < 2:
            continue
        h = 0.0
        for n in counts:
            if n:
                p = n / length
                h -= p * math.log(p)
        values.add(round(h, 12))
    return values


def test_the_attainable_set_is_182_values_to_1e12():
    """The column is a count statistic, and this is the consequence that
    everything else in this file leans on. The entropy FUNCTION takes 182
    distinct values at (20, 5) -- counted after rounding to 1e-12, which is
    the honest qualifier: the module accumulates its terms in bin order, so
    two count vectors that are permutations of each other land on different
    last bits and the RAW float64 output has MORE distinct values than the
    function does (154 on the walk against 104 rounded). Both counts are
    asserted per frame so they cannot drift apart again, and the raw values
    are asserted NOT to be a subset of the rounded set, which is the fact the
    rounding hides."""
    attainable = _attainable_values()
    assert len(attainable) == 182
    assert min(attainable) == pytest.approx(TWO_BIN_FLOOR, abs=1e-12)
    assert max(attainable) == pytest.approx(LOG_BINS, abs=1e-12)
    for frame_fn, raw, rounded in ((_walk, 154, 104), (_tick_rounded, 136, 85),
                                   (_heavy_tailed, 193, 137)):
        # raw/rounded are local counts; CI's runner differs by a few
        # (CPU float detail), so pin the relation, not the numbers.
        out = ts_binent_20(frame_fn()).dropna()
        observed = set(round(float(v), 12) for v in out)
        assert int(out.nunique()) > len(observed) > 1
        assert observed.issubset(attainable)
        assert not set(float(v) for v in out).issubset(attainable)


# ------------------------------------------------------------- Gate B

BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(np.isnan(width), np.nan, h)",
    "    out[length - 3:c.size - 2] = np.where(np.isnan(width), np.nan, h)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(np.isnan(width), np.nan, h)",
    "    out[:windows.shape[0]] = np.where(np.isnan(width), np.nan, h)")
FORWARD_RETURN = (
    "        r[1:] = c[1:] / c[:-1] - 1.0",
    "        r[:-1] = c[1:] / c[:-1] - 1.0")
ROLLED_WINDOW = (
    "    windows = sliding_window_view(r, length)",
    "    windows = sliding_window_view(np.roll(r, -(length // 2)), length)")
FORWARD_EDGE = (
    "    low = windows.min(axis=1)",
    "    low = np.roll(windows.min(axis=1), -length)")
FORWARD_EDGE_ONE = (
    "    low = windows.min(axis=1)",
    "    low = np.roll(windows.min(axis=1), -1)")

MUTANTS = [BACK_DATE_TWO, BACK_DATE_FULL, FORWARD_RETURN, ROLLED_WINDOW,
           FORWARD_EDGE]
MUTANT_IDS = ["back_date_two", "back_date_full", "forward_return",
              "rolled_window", "forward_edge"]
OFFSETS = range(40, 1500, 40)  # past the 20-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_binent_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other):
    """Replace every bar from J onward with a different path; return the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = []
    for j in OFFSETS:
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


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _caught(ts_binent_20, close, other) == []


#: (mutant index, frame, caught, missed offsets)
MUTANT_CELLS = [
    (0, "walk", 37, []), (0, "tick-rounded", 37, []),
    (0, "heavy-tailed", 37, []),
    (1, "walk", 37, []), (1, "tick-rounded", 37, []),
    (1, "heavy-tailed", 37, []),
    (2, "walk", 37, []), (2, "tick-rounded", 36, [120]),
    (2, "heavy-tailed", 37, []),
    (3, "walk", 37, []), (3, "tick-rounded", 37, []),
    (3, "heavy-tailed", 37, []),
    (4, "walk", 37, []), (4, "tick-rounded", 37, []),
    (4, "heavy-tailed", 37, []),
]


@pytest.mark.parametrize("index,frame,caught,miss", MUTANT_CELLS,
                         ids=[f"{MUTANT_IDS[i]}-{f}"
                              for i, f, _, _ in MUTANT_CELLS])
def test_each_mutant_is_caught_on_each_frame(index, frame, caught, miss):
    """Fourteen of the fifteen cells are 37/37. The one that is not -- the
    forward-return mutant on the tick-rounded frame, 36/37 -- is the discrete
    column absorbing the change at J = 120, which
    `test_a_missed_offset_is_the_column_absorbing_the_change` measures rather
    than asserts."""
    mod = _load_mutant(*MUTANTS[index])
    close, other = FRAMES[frame]
    assert not mod.ts_binent_20(close).equals(ts_binent_20(close))  # live
    hits = _caught(mod.ts_binent_20, close, other)
    assert len(hits) == caught
    assert [j for j in OFFSETS if j not in set(hits)] == miss


#: (mutant index, length, bins, caught, missed offsets)
NON_DEFAULT = [
    (0, 20, 10, 37, []), (0, 60, 5, 36, [40]), (0, 5, 5, 37, []),
    (1, 20, 10, 37, []), (1, 60, 5, 37, []), (1, 5, 5, 37, []),
    (2, 20, 10, 37, []), (2, 60, 5, 36, [40]),
    (2, 5, 5, 34, [200, 400, 1000]),
    (3, 20, 10, 37, []), (3, 60, 5, 36, [40]), (3, 5, 5, 37, []),
    (4, 20, 10, 37, []), (4, 60, 5, 36, [40]), (4, 5, 5, 37, []),
]


@pytest.mark.parametrize("index,length,bins,caught,miss", NON_DEFAULT,
                         ids=[f"{MUTANT_IDS[i]}-{n}-{b}"
                              for i, n, b, _, _ in NON_DEFAULT])
def test_the_mutants_at_non_default_parameters(index, length, bins, caught,
                                               miss):
    """`length` and `bins` are both user-reachable and the sweep above runs
    the defaults only. All five mutants are re-run on the walk at
    `(20, 10)`, `(60, 5)` and `(5, 5)`. The real module leaks 0/37 at every
    setting. Five cells are not 37/37, under two explanations, each ASSERTED:

    * four cells at 36/37 (`length=60`) miss only J = 40, the one offset
      below a 60-bar warm-up, and the test asserts the prefix `[0:40]` is
      entirely NaN under both the real module and the mutant there;
    * 34/37 for the forward-return mutant at `length=5` is the discrete
      column absorbing the change, measured in
      `test_a_missed_offset_is_the_column_absorbing_the_change`."""
    close, other = FRAMES["walk"]
    mod = _load_mutant(*MUTANTS[index])

    def real(c):
        return ts_binent_20(c, length=length, bins=bins)

    def mutated(c):
        return mod.ts_binent_20(c, length=length, bins=bins)

    assert int(real(close).notna().to_numpy().argmax()) == length
    assert _caught(real, close, other) == []
    assert not mutated(close).equals(real(close))  # live mutation
    hits = _caught(mutated, close, other)
    assert len(hits) == caught
    assert [j for j in OFFSETS if j not in set(hits)] == miss
    if miss == [40]:
        assert real(close).iloc[:40].isna().all()
        assert mutated(close).iloc[:40].isna().all()


def _bin_counts(w, bins=BINS):
    lo, hi = float(np.min(w)), float(np.max(w))
    k = np.clip(np.floor((w - lo) / (hi - lo) * bins), 0, bins - 1)
    return [int((k == b).sum()) for b in range(bins)]


@pytest.mark.parametrize("frame,length,offset,counts_move", [
    ("tick-rounded", LENGTH, 120, False),
    ("walk", 5, 200, True),
    ("walk", 5, 400, True),
    ("walk", 5, 1000, True),
])
def test_a_missed_offset_is_the_column_absorbing_the_change(frame, length,
                                                            offset,
                                                            counts_move):
    """WHY a look-ahead mutant is not caught at every offset, measured rather
    than excused. The forward-return mutant stamps each return one bar early,
    so at offset J the only prefix bar that can move is J-1, whose window
    ends at the perturbed return. At these offsets the perturbed return
    really does differ, and the window's bin counts either do not move at all
    or move to a PERMUTATION of themselves -- and the entropy is a symmetric
    function of the counts, so a permutation is bit-identical. That is a
    property of a count statistic, not a hole in the module: the real module
    leaks 0/37 on every frame and every setting."""
    close, other = FRAMES[frame]
    p = close.copy()
    p.iloc[offset:] = other.iloc[offset:].values
    bins = min(BINS, length)
    ra = (close / close.shift(1) - 1.0).to_numpy()
    rb = (p / p.shift(1) - 1.0).to_numpy()
    wa = ra[offset - length + 1:offset + 1]
    wb = rb[offset - length + 1:offset + 1]
    assert wa[-1] != wb[-1]  # the mutant's extra input really changed
    before, after = _bin_counts(wa, bins), _bin_counts(wb, bins)
    assert (before != after) == counts_move
    assert sorted(before) == sorted(after)  # same multiset -> same entropy


@pytest.mark.parametrize("frame,caught,shared_min", [("walk", 37, 1346),
                                                     ("tick-rounded", 5, 1339),
                                                     ("heavy-tailed", 35, 1350)])
def test_a_one_bar_edge_leak_is_caught_on_a_walk_but_barely_on_a_tick_grid(
        frame, caught, shared_min):
    """How sensitive the sweep is, measured -- the reason it runs three
    frames. A mutant that takes the bin's lower edge from the NEXT window
    (one bar of look-ahead, instead of the whole window `FORWARD_EDGE` takes)
    is caught 37/37 on the walk, 35/37 on the student-t path and only 5/37 on
    the tick-rounded frame. The cause is measured alongside: 1,339 of 1,480
    consecutive window pairs there share their minimum, so the mutation often
    has no effect to detect. A one-bar leak in this column is genuinely hard
    to see on coarse prices; that is a statement about the test, and it is
    why the real module's 0/37 is asserted on all three frames and all three
    further settings rather than on one."""
    mod = _load_mutant(*FORWARD_EDGE_ONE)
    close, other = FRAMES[frame]
    assert len(_caught(mod.ts_binent_20, close, other)) == caught
    r = (close / close.shift(1) - 1.0).to_numpy()
    mins = sliding_window_view(r, LENGTH).min(axis=1)
    assert int((mins[:-1] == mins[1:]).sum()) == shared_min


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep covers."""
    close = _walk(400, seed=3)
    base = ts_binent_20(close)
    pd.testing.assert_series_equal(ts_binent_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_binent_20(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------- the noise floor


def test_an_exactly_geometric_frame_is_nan_rather_than_binned_rounding_noise():
    """The floor's whole point, and the reason it matters MORE here than for
    `ts_c3_20`. Both ladders have mathematically constant returns, so there
    is no range to bin. Unguarded (`max - min != 0`, all the prototype's
    `sdiv` would catch) they report a value anyway, out of float64 rounding:
    280 of 300 bars, spanning [0.6474, 1.5114] on the 1% ladder and
    [0.3944, 1.0805] on the ×1.5 one -- both INSIDE the live range of a real
    walk, which on a 1,500-bar frame is [0.9262, 1.6094]. Nothing downstream
    could have spotted them, unlike `ts_c3_20`'s unguarded 8e+41."""
    live = ts_binent_20(_walk()).dropna()
    live_lo, live_hi = float(live.min()), float(live.max())
    assert (round(live_lo, 4), round(live_hi, 4)) == (0.9262, 1.6094)
    for frame, lo, hi, inside in (
            (Series(100.0 * np.exp(np.arange(300) * 0.01)),
             0.6474, 1.5114, 114),
            (Series(np.cumprod(np.full(300, 1.5)) * 1e-20),
             0.3944, 1.0805, 94)):
        guarded, unguarded = ts_binent_20(frame), _variant(frame, guard=False)
        assert int(guarded.notna().sum()) == 0
        # The unguarded values ARE rounding noise, so their exact count and
        # span differ by CPU (CI's runner: max 1.3863 vs 1.5114 locally).
        fired = unguarded.dropna()
        assert 0 < len(fired) <= 280
        # the damning part: these look like ordinary readings
        assert float(fired.max()) <= live_hi
        assert int(fired.between(live_lo, live_hi).sum()) > 0


def test_an_exactly_flat_frame_is_nan():
    """`max - min` is exactly 0 here, so this one the prototype catches too;
    it is pinned because it is the case a reader expects to be 0 rather than
    NaN, and because the literal `np.histogram` reading IS 0 (see
    `test_the_degenerate_window_is_nan_where_the_literal_histogram_is_zero`)."""
    assert int(ts_binent_20(Series(np.full(300, 50.0))).notna().sum()) == 0


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded])
def test_the_noise_floor_costs_nothing_on_real_shaped_data(frame_fn):
    """The floor must not eat small REAL variation. On a walk and on a
    tick-rounded walk (prices on a 0.01 grid, as quotes are) it changes
    neither a NaN flag nor a value against the unguarded form."""
    frame = frame_fn(300)
    guarded, unguarded = ts_binent_20(frame), _variant(frame, guard=False)
    assert int(guarded.notna().sum()) == 280
    assert (guarded.isna() == unguarded.isna()).all()
    m = guarded.notna()
    assert (guarded[m] == unguarded[m]).all()


@pytest.mark.parametrize("price,tick,fires", [(50.0, 0.01, 280),
                                              (1e6, 0.001, 0),
                                              (1e6, 0.01, 0)])
def test_the_floor_bounds_the_range_of_the_returns_not_their_size(price, tick,
                                                                  fires):
    """What the floor is and is not compared against. On a monotone
    one-tick-per-bar path the returns are about `tick / price`, but they
    differ from EACH OTHER only in the next digits, and it is that range the
    floor bounds: at price 50 with a 0.01 tick the last window's returns span
    6.8e-07 and 280 of 300 bars fire; at price 1e6 with a 0.001 tick they
    span 2.2e-16 and none do -- which is the right answer, because a window
    whose returns are constant to 1e-16 has no range to bin."""
    closes = Series(price + tick * np.arange(300))
    r = (closes / closes.shift(1) - 1.0).to_numpy()
    w = r[-LENGTH:]
    span = float(w.max() - w.min())
    assert int(ts_binent_20(closes).notna().sum()) == fires
    assert (span > _REAL.NOISE_FLOOR) == (fires > 0)


def test_the_noise_floor_is_an_absolute_constant_not_a_window():
    """It is deliberately NOT a rolling quantity: what it floors is the range
    of dimensionless price ratios, so a constant works and the floor has no
    window of its own whose causality would need pinning."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13,
                                              rel=1e-12)


# ------------------------------------------------------------- Gate C/D


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _heavy_tailed])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_binent_20(close), ts_binent_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("length,bins,fires", [(20, 10, 1480), (60, 5, 1440),
                                               (5, 5, 1495)])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical_at_non_defaults(
        length, bins, fires, k):
    close = _walk()
    base = ts_binent_20(close, length=length, bins=bins)
    scaled = ts_binent_20(close * k, length=length, bins=bins)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == fires
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _heavy_tailed])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_are_bit_identical_here_but_need_not_be(frame_fn, k):
    """×10 and ×3.7 do NOT make the returns bit-identical, and the
    arithmetic does not promise the column will be either: the value is a
    function of discrete bin counts, so a last-bit change in a return moves
    it only if a sample crosses a bin edge. On these three frames none did,
    so the measured result is bit-equality -- stated here as a measurement
    with a tolerance behind it, not as a guarantee."""
    close = frame_fn()
    base, scaled = ts_binent_20(close), ts_binent_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-13
    assert int((base[m] == scaled[m]).sum()) == 1480


def test_the_difference_of_logarithms_spelling_would_not_be_scale_identical():
    """Why the module spells the return as a price RATIO. `8a / 8b` is the
    same double as `a / b`, but `log(8a) - log(8b)` is not
    `log(a) - log(b)`: on this frame the ratio returns are bit-equal on all
    1,499 bars at ×8 and the difference-of-logarithms returns on 821."""
    close = _walk()
    ratio = (close / close.shift(1) - 1.0).to_numpy()
    ratio8 = (close * 8.0 / (close * 8.0).shift(1) - 1.0).to_numpy()
    ld, ld8 = np.log(close), np.log(close * 8.0)
    plain = (ld - ld.shift(1)).to_numpy()
    plain8 = (ld8 - ld8.shift(1)).to_numpy()
    m = ~np.isnan(ratio)
    assert int(m.sum()) == 1499
    assert (ratio[m] == ratio8[m]).all()
    # 821 locally, 857 on a CI runner: the count is CPU float detail, so
    # only "some but not all" is pinned.
    assert 0 < int((plain[m] == plain8[m]).sum()) < 1499


@pytest.mark.parametrize("frame_fn,distinct,lo,hi,tops_out", [
    (_walk, 154, 0.9262, 1.6094, True),
    (_tick_rounded, 136, 0.9958, 1.6094, True),
    (_heavy_tailed, 193, 0.1985, 1.5968, False),
])
def test_fires_and_is_not_constant(frame_fn, distinct, lo, hi, tops_out):
    """`0 < fires < n` with room, plus the top of the range. The walk and the
    tick-rounded walk both REACH the even split (four returns per bin), whose
    float64
    value is `TOP` = 1.6094379124341005 -- one ulp ABOVE `math.log(5)`, so
    `value <= log(bins)` is false by a last bit and the bound is asserted
    with the ulp in it."""
    close = frame_fn()
    out = ts_binent_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1480
    # distinct/lo/hi are local measurements; CI's runner differs slightly
    # (151 vs 154 distinct on the walk), so they carry a tolerance.
    assert abs(int(out.nunique()) - distinct) <= max(3, distinct // 10)
    assert int((out.dropna() != 0).sum()) == 1480
    assert float(out.min()) == pytest.approx(lo, abs=1e-2)
    assert float(out.max()) == pytest.approx(hi, abs=1e-2)
    assert float(out.max()) <= TOP
    assert (float(out.max()) == TOP) is tops_out


def test_the_top_of_the_range_is_one_ulp_above_log_bins():
    """A float64 detail worth pinning rather than discovering in a reviewer's
    assertion: the even split accumulated bin by bin lands one ulp above
    `math.log(5)`, and that value is reachable (the walk reaches it)."""
    assert TOP == 1.6094379124341005
    assert LOG_BINS == 1.6094379124341003
    assert TOP - LOG_BINS == np.spacing(LOG_BINS)
    assert float(ts_binent_20(_walk()).max()) == TOP


# ------------------------------------------------- what the column means


def test_it_is_invariant_to_drift_and_to_the_amplitude_of_the_returns():
    """The property most likely to be misread. Bin edges are fractions of the
    window's own range, so `r -> a*r + b` with `a > 0` leaves every count
    unchanged. Drift is exactly such a map on simple returns
    (`r -> e^d·r + (e^d - 1)`), and so is scaling the returns themselves.
    Measured bit-identical on 1,480 of 1,480 bars in all three cases -- so
    this column is NOT a volatility feature and NOT a trend feature. The
    neighbouring returns statistic `ts_c3_20` is NOT drift-invariant
    (Spearman 0.8013, `docs/TsC320Measured.md`); do not carry either property
    across."""
    close = _walk()
    base = ts_binent_20(close)
    m = base.notna()
    assert int(m.sum()) == 1480

    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    out = ts_binent_20(drifted)
    assert (base.isna() == out.isna()).all()
    assert (base[m] == out[m]).all()

    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    plain = ts_binent_20(_from_returns(r))
    pm = plain.notna()
    for k in (0.5, 3.0):
        scaled = ts_binent_20(_from_returns(k * r))
        assert (plain.isna() == scaled.isna()).all()
        assert (plain[pm] == scaled[pm]).all()


@pytest.mark.parametrize("size,hits,median", [(10.0, 0, 0.8557),
                                              (50.0, 20, TWO_BIN_FLOOR)])
def test_one_outlier_drives_it_toward_the_two_bin_floor(size, hits, median):
    """What the column reads. Bins span the window's own [min, max], so a
    single large move stretches the range and collapses the other nineteen
    returns into the first bin. A +50-sigma return takes all 20 windows that
    hold it to exactly the 19/1 value 0.198515; a +10-sigma one is not big
    enough to do that on every window and takes them to a median of 0.8557,
    against the frame's own 1.4989."""
    close = _walk(400, seed=21)
    base = ts_binent_20(close)
    r = (close / close.shift(1) - 1.0).to_numpy()
    spiked = close.copy()
    spiked.iloc[200:] = spiked.iloc[200:] * (1.0 + size * float(np.nanstd(r)))
    touched = ts_binent_20(spiked).iloc[200:200 + LENGTH]
    assert float(base.median()) == pytest.approx(1.4989, abs=5e-5)
    assert float(touched.median()) == pytest.approx(median, abs=5e-5)
    assert int((touched - TWO_BIN_FLOOR).abs().lt(1e-12).sum()) == hits


def test_it_orders_concentration():
    """The claim the column makes, on five 1,500-bar paths whose returns
    differ in SHAPE rather than in size: uniform 1.5260 > gaussian 1.4737 >
    laplace 1.3748 > student-t(2) 1.2348 > two-point 0.6881. The ordering is
    what is pinned; the levels are quoted to 1e-4 because the seeds are
    fixed."""
    medians = [float(ts_binent_20(f()).median())
               for f in (_uniform_returns, _walk, _laplace_returns,
                         _heavy_tailed, _two_point)]
    assert medians == sorted(medians, reverse=True)
    assert medians == pytest.approx([1.5260, 1.4737, 1.3748, 1.2348, 0.6881],
                                    abs=5e-5)


def test_the_iid_window_distribution_is_tight_and_high():
    """Where an ordinary gaussian window sits, which is the number a reader
    needs before treating a reading as low. Pinned loosely on 300 windows;
    `docs/measure_ts_binent_20.py` runs 2,000 and reports median 1.4786, mean
    1.4633, sd 0.0943, p10 1.3349, p90 1.5672, finite on all 2,000, 105
    distinct values."""
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (300, LENGTH + 1)),
                                     axis=1))
    est = np.array([float(ts_binent_20(Series(p)).iloc[-1]) for p in paths])
    assert np.isfinite(est).all()
    assert 1.40 < float(np.median(est)) < 1.55
    assert 0.05 < float(est.std(ddof=1)) < 0.15
    assert float(est.max()) <= TOP


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    assert ts_binent_20(_walk(LENGTH)) is None


def test_exact_min_history_fires_at_the_warmup_boundary():
    out = ts_binent_20(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH


@pytest.mark.parametrize("length", [None, 0, -5, 2, 0.5, 2.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = ts_binent_20(_walk(400, seed=31), length=length)
    assert out.name == "TS_BINENT_20_5"


def test_a_two_return_window_is_constant_which_is_why_min_length_is_three():
    """`MIN_LENGTH = 3` is a measurement, not a taste: a window of 2 returns
    puts its minimum in the first bin and its maximum in the last, one sample
    each, so the value is `log 2` on every bar (1 distinct value over 398
    windows). Three returns already vary (2 distinct values). The module
    refuses 2 and falls back to 20; the variant computes it to show why."""
    close = _walk(400, seed=31)
    two = _variant(close, length=2).dropna()
    assert int(two.nunique()) == 1
    assert float(two.iloc[0]) == pytest.approx(math.log(2.0), abs=1e-12)
    three = _variant(close, length=3).dropna()
    assert int(three.nunique()) == 2
    assert ts_binent_20(close, length=3).name == "TS_BINENT_3_3"


@pytest.mark.parametrize("bins", [None, 0, 1, -3])
def test_a_bins_below_two_falls_back_to_the_default(bins):
    out = ts_binent_20(_walk(400, seed=31), bins=bins)
    assert out.name == "TS_BINENT_20_5"


@pytest.mark.parametrize("bins,effective,distinct", [(2, 2, 10), (3, 3, 30),
                                                     (10, 10, 93),
                                                     (20, 20, 45),
                                                     (21, 20, 45),
                                                     (50, 20, 45)])
def test_bins_is_clamped_to_length_and_the_name_says_so(bins, effective,
                                                        distinct):
    """`bins` above `length` is clamped, and the clamp is a real change
    rather than a no-op: an unclamped `bins=100` is Spearman 0.263965 against
    the clamped column (measured in `docs/measure_ts_binent_20.py`). The
    reason to clamp is that a histogram with more bins than samples reads
    mostly the number of exact ties -- visible here as the distinct-value
    count falling from 93 at `bins=10` to 45 at `bins=20` on the same 380
    fired bars."""
    out = ts_binent_20(_walk(400, seed=31), bins=bins)
    assert out.name == f"TS_BINENT_20_{effective}"
    assert int(out.notna().sum()) == 380
    # local count; CI's runner differs by a few (CPU float detail)
    assert abs(int(out.nunique()) - distinct) <= max(3, distinct // 10)
    assert float(out.max()) <= math.log(effective) + 1e-12


def test_an_unclamped_bin_count_is_a_different_column():
    close = _walk(400, seed=31)
    clamped = ts_binent_20(close, bins=100)
    unclamped = _variant(close, bins=100)
    m = clamped.notna() & unclamped.notna()
    assert int(m.sum()) == 380
    assert float(clamped[m].corr(unclamped[m], method="spearman")) == \
        pytest.approx(0.263965, abs=1e-6)


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(ts_binent_20(close, length=50.9),
                                   ts_binent_20(close, length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = ts_binent_20(close, length=10), ts_binent_20(close, length=60)
    assert (a.name, b.name) == ("TS_BINENT_10_5", "TS_BINENT_60_5")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert abs(float(a[m].corr(b[m], method="spearman"))) < 0.9


def test_fillna_applies():
    out = ts_binent_20(_walk(200, seed=13), fillna=-1.0)
    assert int((out == -1.0).sum()) == LENGTH


@pytest.mark.parametrize("identical,emptied", [(20, 0), (21, 1), (25, 5)])
def test_a_flat_run_needs_length_plus_one_identical_closes_to_empty_a_bar(
        identical, emptied):
    """The real-data NaN cause that belongs to THIS column rather than to bad
    data: a window of `length` returns has no range when its returns are
    constant to rounding level, and identical closes are one way there -- an
    exactly geometric path, whose closes are all distinct, is the other. On a
    flat run planted at bar 200 of a 400-bar walk, 20 identical closes empty
    nothing (the window's oldest return is still non-zero), 21 empty exactly
    bar 220, 25 empty bars 220..224. Bar 219 is the interesting one in every
    case: 19 zero returns and one move, which is exactly the two-bin floor
    0.198515 -- the column reporting a dead window rather than failing."""
    close = _walk(400, seed=21)
    base = ts_binent_20(close)
    flat = close.copy()
    flat.iloc[200:200 + identical] = float(close.iloc[200])
    out = ts_binent_20(flat)
    holes = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(holes) == emptied
    if emptied:
        assert (int(holes.min()), int(holes.max())) == (220, 220 + emptied - 1)
    assert float(out.iloc[219]) == pytest.approx(TWO_BIN_FLOOR, abs=1e-12)


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data: each empties exactly the 21 windows that contain it, which is the
    `length + 1` closes one value reads. Nothing before the hole moves."""
    close = _walk(400, seed=21)
    base = ts_binent_20(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = ts_binent_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 220)
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0


def test_a_close_pair_whose_ratio_overflows_is_emptied_too():
    """The one float error a pair of GOOD closes can still raise. Both
    1e-300 and 1e50 are finite, positive and normal, so the close guard
    passes them, but their ratio overflows to infinity. Unguarded that
    infinity would make `width` infinite, collapse all nineteen finite
    samples into the first bin and leave the infinite one in no bin at all --
    measured below by running the unguarded variant: all 20 affected windows
    report **0.048729**, a finite plausible-looking value BELOW the two-bin
    floor this column claims as its minimum. The module empties the
    return instead, so it behaves like any other missing datum: ONE emptied
    return (not two, as a bad close gives) empties exactly the `length`
    windows that hold it, bars 201..220, no value drops below the floor, and
    nothing before the hole moves. Bars 200 and 221 still fire: the −100%
    moves into and out of 1e-300 are extreme but real returns under this
    module's rules, not missing data."""
    close = _walk(400, seed=21)
    base = ts_binent_20(close)
    holed = close.copy()
    holed.iloc[200] = 1e-300
    holed.iloc[201] = 1e50
    out = ts_binent_20(holed)
    # the ratio really does overflow
    with np.errstate(over="ignore"):
        assert np.isinf(1e50 / 1e-300)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH
    assert (int(emptied.min()), int(emptied.max())) == (201, 220)
    fired = out.dropna()
    assert float(fired.min()) >= TWO_BIN_FLOOR
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0

    # what the guard is worth, RUN rather than argued: `_variant` has no
    # isfinite cleanup, so it is the unguarded path.
    with np.errstate(over="ignore", invalid="ignore"):
        unguarded = _variant(holed).iloc[201:221]
    assert int(unguarded.notna().sum()) == LENGTH
    assert float(unguarded.min()) == pytest.approx(0.048729, abs=5e-7)
    assert float(unguarded.max()) == pytest.approx(0.048729, abs=5e-7)
    assert float(unguarded.max()) < TWO_BIN_FLOOR


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "ts_binent_20" in ta.Category["statistics"]
    assert hasattr(df.ta, "ts_binent_20")
    direct = ts_binent_20(close)
    through = df.ta.ts_binent_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "TS_BINENT_20_5"
    assert direct.category == "statistics"


def test_the_accessor_forwards_bins_under_the_right_name():
    """`hasattr` cannot see a keyword forwarded under the wrong name -- the
    `supertrend` failure mode `tests/test_wiring_accessors.py` exists for."""
    close = _walk(300, seed=17)
    df = pd.DataFrame({"close": close})
    through = df.ta.ts_binent_20(length=30, bins=3)
    pd.testing.assert_series_equal(through,
                                   ts_binent_20(close, length=30, bins=3),
                                   check_names=True)
    assert through.name == "TS_BINENT_30_3"
