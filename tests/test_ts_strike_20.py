# -*- coding: utf-8 -*-
"""TS-STRIKE-20: `ts_strike_20`, tsfresh's longest strike above the mean on
returns (PandasTa issue #90).

    TS_STRIKE_20 = longest run of consecutive returns STRICTLY above the
                   mean of the 20 trailing simple returns

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line.** tsfresh
   is NOT installed in this worktree and web access is unavailable, so
   "tsfresh (MIT)" is an attribution, not an oracle. What IS checkable is
   pinned four ways:

   * eight windows whose answer is derived by hand at `length` 8 and 20 --
     runs at either end of the window, interleaved runs of 2 / 3 / 1, the
     alternating window that can only score 1, and the constant window that
     scores 0 rather than `length`
     (`test_hand_derived_windows`, `test_a_hand_derived_window_at_length_20`);
   * the screen prototype of `docs/issues/screen/ind_screen.py` (candidate
     `ts_strike_20`), retyped here because that file is gitignored:
     **bit-equal on 1,480 of 1,480** fired bars of a 1,500-bar walk. The
     measurement script also IMPORTS the prototype out of the owner's tree
     when it is present and gets the same 1,480 of 1,480
     (`docs/measure_ts_strike_20.py`, section A2). The one difference is a
     WARM-UP bar, pinned in its own test: the prototype emits 0.0 at bar 19,
     whose window holds the undefined first return, and this module emits
     NaN there, so the prototype fires 1,481 bars and this module 1,480;
   * an `itertools.groupby` run-length pass over `r > mean(r)`, applied window
     by window in a plain Python loop over explicit slices -- no numpy
     windowing, no vectorised run counting, and no constant borrowed from the
     module: bit-equal on 1,480 of 1,480 bars of a walk, of a tick-rounded
     walk and of an AR(1) path. The spelling is chosen for that independence;
     whether tsfresh spells it this way is UNVERIFIED here (not installed, no
     web access), and nothing in this file describes tsfresh's source text;
   * the attainable set, constructed: every k from 1 to 19 is reached by a
     window of k consecutive +1 returns among zeros; `length` itself is
     unreachable, because at least one sample of a window is always at or
     below that window's own mean; and 0 means the returns are all equal, or
     equal to rounding level -- the floor case, pinned by
     `test_what_the_floor_costs_on_a_monotone_one_tick_per_bar_path`.
     200,000 iid gaussian windows produce 1..12 and never 0 or 20.

2. **Gate B, by mutant, on three frames.** Five mutants, each
   `importlib`-read and `exec`'d in memory: the column back-dated by
   `length`; the column written one bar early; the return read one bar
   ahead; the window mean taken from the next window; the above/below
   pattern taken from the next window. A **sixth** covers the module's other
   windowed input, the `span` that decides the guard; it is a no-op on a
   continuous frame (the floor never fires there), so it is swept on a walk
   carrying 21 identical closes ending at each offset, where the real module
   still leaks 0 of 37 and the mutant is caught 37 of 37
   (`test_the_span_that_decides_the_guard_is_causal_too`). Measured over 37 J
   values of a
   future-perturbation sweep, the real module leaks **0/37** on a walk, on a
   tick-rounded walk, on an AR(1) path, and again at `length=5` and
   `length=60`. The mutants are caught on **33 to 37** of 37, and the cells
   under 37 are asserted with their mechanism rather than excused: a one-bar
   look-ahead can move exactly ONE bar of the prefix (J - 1, the only bar
   whose window reaches `close[J]`), which this file asserts directly, so a
   miss is an offset where that single INTEGER did not change. The column
   is integer-valued and heavily tied -- 1,153 of 1,479 consecutive bar
   pairs on the walk carry the same value -- which is a limit of the sweep,
   stated as such.

3. **The noise floor, and why the unguarded failure is invisible rather
   than absurd.** The returns of an exactly geometric path are
   mathematically constant, so the answer is 0, but in float64 they differ
   in their last bits: unguarded, a 1%-a-bar ladder reads 1, 2, 3 or 4 on
   all 280 of its fired bars and an exact x1.5 ladder reads 1, 2, 3, 5 or 8
   -- every one of those values inside the live range of a real walk (1 to
   9), which is the form the test asserts, since the exact values and counts
   are float64 noise and move with numpy's kernels (measured: the 1%-a-bar
   ladder's counts are 85 / 64 / 80 / 51 here and 87 / 75 / 73 / 45 under
   `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`), where
   `ts_c3_20`'s unguarded failure reached 8e+41 and could not be missed. The
   floor is ABSOLUTE (4096 eps = 9.09e-13) because what it bounds is the
   range of dimensionless price ratios, which has no window of its own to
   keep causal. On real-shaped frames it costs nothing (280 of 300 bars
   fire on a walk and on a tick-rounded walk, bit-equal to the unguarded
   form). What it DOES cost is pinned too: on a monotone one-tick-per-bar
   path at price 1e6 with a 0.01 tick the mathematical answer is around 10
   and the column reports 0.

4. **Gate D, and that x8 is bit-identical rather than merely close.** Every
   input is a price RATIO, and `8a / 8b` is the same double as `a / b`:
   1,480 of 1,480 bars bit-identical at x8 and at x64 on each of three
   frames, 1,495 of 1,495 at `length=5` and 1,440 of 1,440 at `length=60`.
   x10 and x3.7 are bit-identical on these frames too, which the arithmetic
   does NOT promise for an integer decided by a float comparison; what makes
   it hold is measured and pinned -- the smallest margin any sample has to
   its own window's mean is 1.2e-06 on the walk and 5.2e-08 on the AR(1)
   path, with 0 exact ties in 29,600 samples, so no last-bit change can flip
   a comparison. The x10/x3.7 assertion is deliberately loose (at most one
   bar may differ) because that margin is a measurement on three frames, not
   a guarantee.

5. **What the column is, and what it is not.** It is INVARIANT to any
   affine map of the returns -- bit-identical under a x0.5 and a x3 rescale
   of the returns themselves and under +0.004 of log drift a bar -- so it is
   neither a volatility nor a trend feature. The two deterministic extremes
   say it plainly: a pure geometric trend has constant returns and reads 0,
   and a path alternating up and down every bar reads a constant 1. What it
   orders is the CLUSTERING of above-average returns, measured on AR(1)
   log-return paths: mean 6.5392 / 5.5128 / 4.3872 / 3.6520 / 3.1297 /
   2.7081 / 2.3223 at phi = +0.8 / +0.6 / +0.3 / 0 / -0.3 / -0.6 / -0.8.
   One outlier SHORTENS the strike, because it drags the mean above the
   ordinary returns.

6. **The five readings the wording leaves open, each priced.** The `>=`
   reading is bit-equal on 1,480 of 1,480 bars of a walk (0 exact ties with
   the mean in 29,600 samples) and yet reads 20 against this column's 0 on a
   window of equal returns -- maximal disagreement on the one case real data
   reaches; log returns are a close but distinct column (bit-equal on 1,455
   of 1,480, Spearman 0.988879); the below-mean mirror is a different column
   (346 of 1,480, Spearman 0.109170); dividing by `length` is a strict
   rescaling (`port / 20` reproduces it on 1,480 of 1,480, Spearman
   1.000000); a degenerate window reads 0 rather than NaN.

7. **The guard bands, measured rather than asserted.** `length` below 3
   (including 0, negatives and fractions that truncate below 3) falls back
   to 20; the minimum is 3 because `length=1` is the constant 0 and
   `length=2` the constant 1.

8. **Five-point wiring** (`Category`, the accessor, the export) and the NaN
   behaviour of a bad close: NaN, zero, negative, infinite and subnormal
   closes each empty exactly the 21 windows that contain them (`length + 1`
   closes per value), a close pair whose ratio overflows empties 20, and
   nothing before the hole moves. A merely DEGENERATE window is not NaN: it
   reads 0, and that needs all `length + 1` closes identical (planted at bar
   200 of a 400-bar walk, 20 identical closes make no bar read 0, 21 make
   bar 220 read 0 and 25 make bars 220..224).

Every number above comes from `docs/measure_ts_strike_20.py`, whose run is
transcribed in `docs/TsStrike20Measured.md`. Gate E is owed: the launcher
runs `gate_e_overlap.py` after this session and a later session records the
`docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.
"""
import importlib
import itertools
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ts_strike_20 import ts_strike_20

LENGTH = 20

_REAL = importlib.import_module("pandas_ta.statistics.ts_strike_20")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    """A path whose LOG returns are an AR(1). A positive `phi` makes
    above-average returns cluster, which is what a longest strike reads."""
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _alternating(n=1500, small=0.002, large=0.02):
    r = np.where(np.arange(n) % 2 == 0, large, -small)
    return Series(100.0 * np.exp(np.cumsum(r)))


def _closes_from_returns(r):
    """The `len(r) + 1` closes whose simple returns are exactly `r`."""
    return Series(np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r,
                                                                    float))]))


# ------------------------------------------------------------- Gate A


HAND = [
    ([0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0], 3.0,
     "three consecutive +1 among five 0: the mean is 3/8 and only the +1 are "
     "above it"),
    ([1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0], 1.0,
     "alternating: the mean is 1/2, every other return is above it, so no "
     "run reaches 2"),
    ([0.0] * 8, 0.0,
     "constant returns: the mean IS every return, nothing is STRICTLY above "
     "it, so 0 -- not 8"),
    ([5.0] * 8, 0.0,
     "constant and non-zero: the same answer, which is what makes 0 mean "
     "'flat' rather than 'no data'"),
    ([1.0] * 7 + [0.0], 7.0,
     "seven +1 then one 0: the mean is 7/8 and the run is length-1 = 7, the "
     "largest value a window of 8 can take"),
    ([0.0] + [1.0] * 7, 7.0, "the same run at the other end of the window"),
    ([1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0], 3.0,
     "runs of 2, 3 and 1 above a mean of 6/8: the LONGEST is 3"),
]


@pytest.mark.parametrize("returns,expected,why", HAND,
                         ids=[h[2].split(":")[0] for h in HAND])
def test_hand_derived_windows(returns, expected, why):
    """Each window's answer is derived by hand from the returns, with no
    implementation involved; the closes are reconstructed from them by
    `cumprod(1 + r)`, so the module's own return arithmetic is what maps one
    to the other."""
    n = len(returns)
    out = ts_strike_20(_closes_from_returns(returns), length=n)
    assert out.name == f"TS_STRIKE_{n}"
    assert out.iloc[:n].isna().all()
    assert float(out.iloc[n]) == expected, why


def test_a_hand_derived_window_at_length_20():
    """The same exercise at the SHIPPED length. Returns are eight 0, five +1,
    three 0, two +1, two 0: the mean is 7/20 = 0.35, the two runs above it
    are 5 and 2, so the answer is 5."""
    returns = [0.0] * 8 + [1.0] * 5 + [0.0] * 3 + [1.0] * 2 + [0.0] * 2
    assert len(returns) == LENGTH
    out = ts_strike_20(_closes_from_returns(returns))
    assert out.name == "TS_STRIKE_20"
    assert int(out.notna().to_numpy().argmax()) == LENGTH
    assert float(out.iloc[LENGTH]) == 5.0


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_strike_20`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            return roll(ret(c), 20, w_longest_strike_above_mean)

    with `ret(c) = c / c.shift(1) - 1`, `_win(x, n)` a
    `sliding_window_view` of the whole return array, `_from_win` writing the
    result at `out[n-1:]`, and

        def w_longest_strike_above_mean(W):
            b = W > W.mean(1, keepdims=True)
            cur = np.zeros(len(W)); best = np.zeros(len(W))
            for j in range(W.shape[1]):
                cur = np.where(b[:, j], cur + 1, 0)
                best = np.maximum(best, cur)
            return best
    """
    a = (close / close.shift(1) - 1).to_numpy(dtype=float)
    W = sliding_window_view(a, length)
    b = W > W.mean(1, keepdims=True)
    cur = np.zeros(len(W))
    best = np.zeros(len(W))
    for j in range(W.shape[1]):
        cur = np.where(b[:, j], cur + 1, 0)
        best = np.maximum(best, cur)
    out = np.full(len(a), np.nan)
    out[length - 1:] = best
    return Series(out, index=close.index)


def test_matches_the_screen_prototype_on_every_fired_bar():
    close = _walk()
    base, proto = ts_strike_20(close), _prototype(close)
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == proto[m]).all()


def test_the_prototype_fires_one_extra_warmup_bar_and_this_module_does_not():
    """The ONE difference, pinned so it cannot drift into a correctness
    claim. The prototype windows the whole return array, including the
    undefined first return, so its first window (bar 19) has a NaN mean,
    every comparison against it is False and it reports a strike of 0. This
    module reports NaN there, because that window has no 20th return."""
    close = _walk()
    base, proto = ts_strike_20(close), _prototype(close)
    differ = np.flatnonzero((base.isna() != proto.isna()).to_numpy())
    assert differ.tolist() == [LENGTH - 1]
    assert np.isnan(float(base.iloc[LENGTH - 1]))
    assert float(proto.iloc[LENGTH - 1]) == 0.0
    assert int(base.notna().sum()) == 1480
    assert int(proto.notna().sum()) == 1481


def _longest_run_above_mean(x):
    """`max(run lengths of True in groupby(x > mean(x)))`, 0 when there is no
    run. An independent spelling of the issue's line -- not a copy of
    tsfresh's code, which this session cannot read."""
    x = np.asarray(x, dtype=float)
    runs = [len(list(g)) for v, g in itertools.groupby(x > x.mean()) if v]
    return float(max(runs)) if runs else 0.0


def _groupby_oracle(close, length=LENGTH):
    """`_longest_run_above_mean` applied window by window in a plain Python
    loop over explicit slices: no numpy windowing, no vectorised run counting,
    and NO noise floor -- it shares nothing with the module, not even
    `NOISE_FLOOR`. The test below asserts separately that the floor never
    fires on these frames, so bit-equality is evidence rather than a shared
    branch."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        r = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        out[t] = _longest_run_above_mean(r)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
def test_matches_an_independent_groupby_spelling_window_by_window(frame_fn):
    close = frame_fn()
    base, oracle = ts_strike_20(close), _groupby_oracle(close)
    assert (base.isna() == oracle.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == oracle[m]).all()
    # The module's one addition to the oracle is the noise floor, and on these
    # frames it cannot be what makes them agree: it never fires.
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r[1:], LENGTH)
    span = W.max(axis=1) - W.min(axis=1)
    assert int((span <= _REAL.NOISE_FLOOR).sum()) == 0
    assert len(span) == 1480


@pytest.mark.parametrize("k", list(range(1, LENGTH)))
def test_every_run_length_from_one_to_length_minus_one_is_reachable(k):
    """`k` consecutive +1 returns among `20 - k` zeros has mean `k/20`, so
    exactly those `k` are above it. This is what makes the column's range
    `{0} + {1 .. 19}` a construction rather than an observation."""
    returns = [1.0] * k + [0.0] * (LENGTH - k)
    assert float(ts_strike_20(_closes_from_returns(returns)).iloc[LENGTH]) \
        == float(k)


def test_the_length_itself_is_unreachable_and_zero_means_constant_returns():
    """Two statements about the attainable set, one proved by construction
    and one measured. A window's samples cannot ALL be strictly above their
    own mean, so `length` is unreachable; and if the samples are not all
    equal then the maximum IS strictly above the mean, so 0 means equal
    returns. Measured here on 20,000 iid gaussian windows (the receipt runs
    200,000 and gets values 1..12, mean 3.6379)."""
    rng = np.random.default_rng(4242)
    W = rng.normal(0.0, 0.01, (20000, LENGTH))
    flags = W > W.mean(1, keepdims=True)
    cur = np.zeros(len(W))
    best = np.zeros(len(W))
    for j in range(LENGTH):
        cur = np.where(flags[:, j], cur + 1.0, 0.0)
        best = np.maximum(best, cur)
    assert int(best.max()) < LENGTH
    assert int((best == 0.0).sum()) == 0
    assert int((best == float(LENGTH)).sum()) == 0
    assert 3.0 < float(best.mean()) < 4.5


def _variant(close, length=LENGTH, inclusive=False, log_returns=False,
             below=False, normalised=False, guard=True, finite_filter=True):
    """The module's computation with ONE reading changed."""
    c = close.to_numpy(dtype=float)
    if finite_filter:
        c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        r = np.full(c.size, np.nan)
        r[1:] = np.log(c[1:] / c[:-1]) if log_returns else c[1:] / c[:-1] - 1.0
    if finite_filter:
        r = np.where(np.isfinite(r), r, np.nan)
    W = sliding_window_view(r, length)
    mean = W.mean(axis=1)
    span = W.max(axis=1) - W.min(axis=1)
    if below:
        flags = W < mean[:, None]
    elif inclusive:
        flags = W >= mean[:, None]
    else:
        flags = W > mean[:, None]
    cur = np.zeros(W.shape[0])
    best = np.zeros(W.shape[0])
    for j in range(length):
        cur = np.where(flags[:, j], cur + 1.0, 0.0)
        best = np.maximum(best, cur)
    if normalised:
        best = best / length
    body = best if not guard else np.where(span > _REAL.NOISE_FLOOR, best, 0.0)
    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(np.isnan(mean), np.nan, body)
    return Series(out, index=close.index)


def test_the_variant_harness_reproduces_the_module_when_nothing_is_changed():
    """`_variant` is the oracle the four rejected readings are priced
    against, so it has to be the module at its defaults."""
    close = _walk()
    pd.testing.assert_series_equal(_variant(close), ts_strike_20(close),
                                   check_names=False)


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded])
def test_the_inclusive_reading_is_bit_equal_here_only_because_ties_are_absent(
        frame_fn):
    """`>=` instead of `>` is the cheapest-looking rejected reading and the
    most dangerous one. On continuous-ish frames it is bit-equal, because an
    exact tie with the window mean never happens -- which this test
    MEASURES rather than assumes."""
    close = frame_fn()
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r[1:], LENGTH)
    assert int((W == W.mean(axis=1, keepdims=True)).sum()) == 0
    assert W.size == 29600
    base, other = ts_strike_20(close), _variant(close, inclusive=True)
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == other[m]).all()


def test_the_inclusive_reading_disagrees_maximally_on_a_flat_window():
    """And here is why it is still the wrong reading: on `length + 1`
    identical closes every return EQUALS the mean, so `>=` marks all 20 and
    reports the top of the scale where this column reports the bottom. The
    guard is removed from the variant because the floor would mask the
    difference."""
    flat = Series(np.full(300, 50.0))
    port = ts_strike_20(flat)
    other = _variant(flat, inclusive=True, guard=False)
    assert int(port.notna().sum()) == 280
    assert sorted(set(port.dropna().tolist())) == [0.0]
    assert sorted(set(other.dropna().tolist())) == [float(LENGTH)]


@pytest.mark.parametrize("kwargs,bit_equal,max_diff,rho_lo,rho_hi", [
    ({"log_returns": True}, 1455, 3.0, 0.95, 0.9999),
    ({"below": True}, 346, 6.0, -1.0, 0.5),
])
def test_the_other_rejected_readings_are_different_columns(
        kwargs, bit_equal, max_diff, rho_lo, rho_hi):
    """Log returns change the window MEAN, which is what the comparison is
    against, so a monotone transform of the returns is not a no-op here; and
    the below-mean mirror is close to independent of this column."""
    close = _walk()
    base, other = ts_strike_20(close), _variant(close, **kwargs)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1480
    assert int((base[m] == other[m]).sum()) == bit_equal
    assert float((base[m] - other[m]).abs().max()) == max_diff
    rho = float(base[m].corr(other[m], method="spearman"))
    assert rho_lo < rho < rho_hi


def test_dividing_by_length_is_a_strict_rescaling():
    """The reading this port rejects for being cosmetic, and the test says
    exactly how cosmetic: every bar moves and no rank does."""
    close = _walk()
    base, other = ts_strike_20(close), _variant(close, normalised=True)
    m = base.notna() & other.notna()
    assert int((base[m] == other[m]).sum()) == 0
    assert int(((base[m] / LENGTH) == other[m]).sum()) == 1480
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


# ------------------------------------------------------------- Gate B

WRITE_SHIFT_MUTANT = (
    "    strike = Series(out, index=close.index)",
    "    strike = Series(out, index=close.index).shift(-length)")
WRITE_EARLY_MUTANT = (
    "    out[length - 1:] = np.where(np.isnan(mean), np.nan,",
    "    out[length - 2:-1] = np.where(np.isnan(mean), np.nan,")
FORWARD_RETURN_MUTANT = (
    "        r[1:] = c[1:] / c[:-1] - 1.0",
    "        r[:-1] = c[1:] / c[:-1] - 1.0")
FORWARD_MEAN_MUTANT = (
    "    above = windows > mean[:, None]",
    "    above = windows > np.roll(mean, -1)[:, None]")
FORWARD_WINDOW_MUTANT = (
    "    current = np.where(above[:, j], current + 1.0, 0.0)",
    "    current = np.where(np.roll(above, -1, axis=0)[:, j], current + 1.0, "
    "0.0)")
FORWARD_SPAN_MUTANT = (
    "    span = windows.max(axis=1) - windows.min(axis=1)",
    "    span = np.roll(windows.max(axis=1) - windows.min(axis=1), -1)")

MUTANTS = [WRITE_SHIFT_MUTANT, WRITE_EARLY_MUTANT, FORWARD_RETURN_MUTANT,
           FORWARD_MEAN_MUTANT, FORWARD_WINDOW_MUTANT]
MUTANT_IDS = ["write_shift", "write_early", "forward_return", "forward_mean",
              "forward_window"]
ONE_BAR_MUTANTS = [WRITE_EARLY_MUTANT, FORWARD_RETURN_MUTANT,
                   FORWARD_MEAN_MUTANT, FORWARD_WINDOW_MUTANT]
ONE_BAR_IDS = ["write_early", "forward_return", "forward_mean",
               "forward_window"]
OFFSETS = range(40, 1500, 40)  # past the 20-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "ar1": (_ar1(), _ar1(seed=8)),
}

#: (mutant id, frame, offsets caught of 37). Measured by
#: `python docs/measure_ts_strike_20.py gate_b`; the cells under 37 are
#: explained by `test_a_one_bar_mutant_can_only_move_the_bar_before_the_cut`
#: and by the tie density below, not waved away.
CAUGHT = {
    ("write_shift", "walk"): 37, ("write_shift", "tick-rounded"): 36,
    ("write_shift", "ar1"): 37,
    ("write_early", "walk"): 36, ("write_early", "tick-rounded"): 33,
    ("write_early", "ar1"): 37,
    ("forward_return", "walk"): 36,
    ("forward_return", "tick-rounded"): 33, ("forward_return", "ar1"): 37,
    ("forward_mean", "walk"): 36, ("forward_mean", "tick-rounded"): 34,
    ("forward_mean", "ar1"): 37,
    ("forward_window", "walk"): 36,
    ("forward_window", "tick-rounded"): 33, ("forward_window", "ar1"): 37,
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_strike_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leak_offsets(fn, close, other):
    """Replace every bar from J onward with a different path; collect the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hit = []
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


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _leak_offsets(ts_strike_20, close, other) == []


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("mutant,mid", list(zip(MUTANTS, MUTANT_IDS)),
                         ids=MUTANT_IDS)
def test_each_mutant_is_caught_on_each_frame(mutant, mid, frame):
    """Every cell is pinned at its MEASURED count rather than at 37, because
    an integer column with this many ties can absorb a one-bar leak at a
    given offset; what the file does not do is leave that unexplained -- see
    the two tests below. The counts are stable across machines because every
    comparison behind them has a margin of at least 5.2e-08 to the mean
    (`test_no_sample_sits_within_rounding_of_its_own_window_mean`), so no
    cell turns on a last bit."""
    mod = _load_mutant(*mutant)
    close, other = FRAMES[frame]
    assert not mod.ts_strike_20(close).equals(ts_strike_20(close))
    assert len(_leak_offsets(mod.ts_strike_20, close, other)) \
        == CAUGHT[(mid, frame)]


@pytest.mark.parametrize("mutant", ONE_BAR_MUTANTS, ids=ONE_BAR_IDS)
@pytest.mark.parametrize("frame", ["walk", "tick-rounded"])
def test_a_one_bar_mutant_can_only_move_the_bar_before_the_cut(mutant, frame):
    """The mechanism behind every cell under 37, asserted rather than
    argued. A one-bar look-ahead changes the value of bar J - 1 and of no
    other bar before J, because no earlier bar's window reaches `close[J]`.
    So a missed offset is one where that single integer happened not to
    change -- a limit of the sweep, not a second kind of leak."""
    mod = _load_mutant(*mutant)
    close, other = FRAMES[frame]
    base = mod.ts_strike_20(close)
    seen = set()
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = mod.ts_strike_20(p)
        a, b = base.iloc[:j], out.iloc[:j]
        moved = np.flatnonzero(((a != b) & ~(a.isna() & b.isna())).to_numpy())
        seen.add(tuple((moved - j).tolist()))
    assert seen == {(), (-1,)}


@pytest.mark.parametrize("frame,tied", [("walk", 1153),
                                        ("tick-rounded", 1079),
                                        ("ar1", 910)])
def test_the_column_ties_often_enough_to_hide_a_one_bar_shift(frame, tied):
    """The density behind that mechanism, measured: most consecutive bar
    pairs carry the SAME integer, so moving a window by one bar frequently
    changes nothing. This is the number that makes 33/37 a property of the
    column rather than a weak test."""
    close, _ = FRAMES[frame]
    base = ts_strike_20(close).to_numpy()
    m = ~np.isnan(base)
    assert int((base[m][1:] == base[m][:-1]).sum()) == tied
    assert int(m.sum()) == 1480


#: (length, mutant id, offsets caught of 37), measured on the walk.
NON_DEFAULT = [
    (5, "write_shift", 37), (5, "write_early", 36),
    (5, "forward_return", 36), (5, "forward_mean", 36),
    (5, "forward_window", 36),
    (60, "write_shift", 37), (60, "write_early", 33),
    (60, "forward_return", 33), (60, "forward_mean", 34),
    (60, "forward_window", 33),
]


@pytest.mark.parametrize("length,mid,caught", NON_DEFAULT,
                         ids=[f"{m}-{n}" for n, m, _ in NON_DEFAULT])
def test_the_sweep_at_non_default_lengths(length, mid, caught):
    """`length` is free, and the sweep above runs the default only. The real
    module leaks 0/37 at `length=5` and `length=60` as well, and the mutants
    stay in the same 33-37 band."""
    mutant = MUTANTS[MUTANT_IDS.index(mid)]
    close, other = FRAMES["walk"]
    mod = _load_mutant(*mutant)

    def real(c):
        return ts_strike_20(c, length=length)

    def mutated(c):
        return mod.ts_strike_20(c, length=length)

    assert int(real(close).notna().to_numpy().argmax()) == length
    assert _leak_offsets(real, close, other) == []
    assert not mutated(close).equals(real(close))
    assert len(_leak_offsets(mutated, close, other)) == caught


def _flat_planted(n=1500, seed=11):
    """A walk carrying `length + 1` identical closes ending at EACH sweep
    offset, so the window ending at J is degenerate and the noise floor fires
    there. The runs are 21 closes 40 apart, so they do not overlap."""
    c = _walk(n, seed).to_numpy().copy()
    for j in OFFSETS:
        c[j - LENGTH:j + 1] = c[j - LENGTH]
    return Series(c)


def test_the_span_that_decides_the_guard_is_causal_too():
    """`span` is the module's second windowed input and the five mutants above
    do not touch it, so it gets its own. Taking it from the NEXT window is a
    no-op on a continuous frame -- the floor never fires there, measured as 0
    of 1,480 windows in
    `test_matches_an_independent_groupby_spelling_window_by_window` -- so the
    sweep runs on a walk with 21 identical closes ending at each offset, where
    37 bars read 0. There the real module still leaks 0 of 37 and the mutant
    is caught 37 of 37."""
    frame, other = _flat_planted(), _walk(seed=97)
    assert int((ts_strike_20(frame) == 0.0).sum()) == 37
    mod = _load_mutant(*FORWARD_SPAN_MUTANT)
    assert not mod.ts_strike_20(frame).equals(ts_strike_20(frame))
    assert _leak_offsets(ts_strike_20, frame, other) == []
    assert len(_leak_offsets(mod.ts_strike_20, frame, other)) == len(
        list(OFFSETS))


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep above
    covers."""
    close = _walk(400, seed=3)
    base = ts_strike_20(close)
    pd.testing.assert_series_equal(ts_strike_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_strike_20(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------- the noise floor


@pytest.mark.parametrize("frame", [
    Series(100.0 * np.exp(np.arange(300) * 0.01)),
    Series(np.cumprod(np.full(300, 1.5)) * 1e-20),
], ids=["1%-a-bar ladder", "x1.5 ladder"])
def test_an_exactly_geometric_frame_reads_zero_rather_than_a_run_of_noise(
        frame):
    """Both ladders have mathematically constant returns, so the answer is 0.
    Unguarded they report a run anyway, out of float64 rounding -- on EVERY
    fired bar -- and unlike `ts_c3_20`'s 8e+41, every value they report is an
    ORDINARY one that nothing downstream could flag: each one is a value the
    same column takes on a real walk, which is what the last assertion
    compares against rather than a hard-coded list.

    What is pinned here is structural, because the detail is not portable:
    the unguarded reading is float64 noise, so WHICH noise value a bar gets
    depends on numpy's kernels. Measured on this machine, the 1%-a-bar ladder
    reads 1, 2, 3, 4 with counts 85 / 64 / 80 / 51, and with
    `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` the same four
    values with counts 87 / 75 / 73 / 45. The x1.5 ladder came out identical
    both ways (1, 2, 3, 5, 8; 234 / 25 / 18 / 1 / 2). The value SET held in
    both runs too, but it is no more guaranteed than the counts, so neither
    is asserted."""
    guarded = ts_strike_20(frame)
    unguarded = _variant(frame, guard=False)
    assert int(guarded.notna().sum()) == 280
    assert sorted(set(guarded.dropna().tolist())) == [0.0]
    assert (guarded.isna() == unguarded.isna()).all()
    noise = unguarded.dropna().to_numpy()
    # The guard is not cosmetic: unguarded, pure rounding plants a strike on
    # every bar that fires.
    assert int((noise > 0.0).sum()) == 280
    # And every one of those is a value a real frame produces, so nothing
    # downstream could tell the noise from a reading.
    live = set(ts_strike_20(_walk()).dropna().tolist())
    assert set(noise.tolist()) <= live


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded])
def test_the_noise_floor_costs_nothing_on_real_shaped_data(frame_fn):
    """The floor must not eat small REAL variation. On a walk and on a
    tick-rounded walk (prices on a 0.01 grid, as quotes are) it changes
    neither a NaN flag nor a value against the unguarded form."""
    frame = frame_fn(300)
    guarded, unguarded = ts_strike_20(frame), _variant(frame, guard=False)
    assert int(guarded.notna().sum()) == 280
    assert (guarded.isna() == unguarded.isna()).all()
    m = guarded.notna()
    assert (guarded[m] == unguarded[m]).all()


@pytest.mark.parametrize("price,tick,guarded_values,unguarded_values", [
    (50.0, 0.01, [10.0], [10.0]),
    (1e6, 0.001, [0.0], [float(v) for v in range(LENGTH)]),
    (1e6, 0.01, [0.0], [8.0, 9.0, 10.0, 11.0]),
])
def test_what_the_floor_costs_on_a_monotone_one_tick_per_bar_path(
        price, tick, guarded_values, unguarded_values):
    """The honest cost of the floor, pinned rather than argued away. These
    paths have returns that genuinely DECREASE -- a fixed tick is a
    shrinking fraction of a rising price -- so about half the window sits
    above its mean and the mathematical answer is near 10, not 0. At price
    50 with a 0.01 tick the window's return span clears the floor and the
    column reads 10. At price 1e6 it does not, and the column reads 0 --
    while the unguarded form spreads over EVERY value from 0 to 19 at a
    0.001 tick, which is what makes 0 the better answer there even though it
    is not the mathematical one."""
    closes = Series(price + tick * np.arange(300))
    r = closes / closes.shift(1) - 1.0
    span = float((r.rolling(LENGTH).max() - r.rolling(LENGTH).min()).iloc[-1])
    guarded, unguarded = ts_strike_20(closes), _variant(closes, guard=False)
    assert (span > _REAL.NOISE_FLOOR) == (guarded_values != [0.0])
    assert sorted(set(guarded.dropna().tolist())) == guarded_values
    assert sorted(set(unguarded.dropna().tolist())) == unguarded_values


def test_the_noise_floor_is_an_absolute_constant_and_the_module_has_no_rolling():
    """It is deliberately NOT a rolling quantity: what it floors is the
    range of dimensionless price ratios, so a constant works and the floor
    has no window of its own whose causality would need pinning. The module
    takes its windows from one `sliding_window_view` and nothing else, which
    is what Gate B's window mutants cover."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(".rolling(") == 0
    assert src.count("sliding_window_view(") == 1


@pytest.mark.parametrize("identical,zeroed", [(20, []), (21, [220]),
                                              (25, [220, 221, 222, 223, 224])])
def test_a_flat_run_needs_length_plus_one_identical_closes_to_read_zero(
        identical, zeroed):
    """The degenerate case on real-shaped data, and the one NaN cause this
    column does NOT have. A window of 20 returns is constant only when all
    21 closes behind it are identical, and then it reads 0 rather than
    NaN: on a flat run planted at bar 200 of a 400-bar walk, 20 identical
    closes make no bar read 0 (the window's oldest return is still
    non-zero), 21 make bar 220 read 0 and 25 make bars 220..224."""
    close = _walk(400, seed=21)
    base = ts_strike_20(close)
    flat = close.copy()
    flat.iloc[200:200 + identical] = float(close.iloc[200])
    out = ts_strike_20(flat)
    assert int(out.isna().sum()) == int(base.isna().sum())
    assert np.flatnonzero(((out == 0.0) & (base != 0.0)).to_numpy()).tolist() \
        == zeroed


# ------------------------------------------------------------- Gate C/D


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_strike_20(close), ts_strike_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("length,fires", [(5, 1495), (60, 1440)])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical_at_other_lengths(
        length, fires, k):
    close = _walk()
    base = ts_strike_20(close, length=length)
    scaled = ts_strike_20(close * k, length=length)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == fires
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _ar1])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_move_at_most_one_bar(frame_fn, k):
    """x10 and x3.7 came out bit-identical on all three frames (measured),
    but the arithmetic does not promise it: the output is an integer decided
    by a float comparison, so a last-bit change in a rescaled return could
    flip a sample that sits within rounding of its window mean. The bound is
    therefore loose on purpose -- the measurement is in
    `docs/TsStrike20Measured.md` and the margin that explains it is the next
    test."""
    close = frame_fn()
    base, scaled = ts_strike_20(close), ts_strike_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int((base[m] != scaled[m]).sum()) <= 1


@pytest.mark.parametrize("frame_fn,smallest", [(_walk, 1.2e-06),
                                               (_tick_rounded, 7.6e-08),
                                               (_ar1, 5.2e-08)])
def test_no_sample_sits_within_rounding_of_its_own_window_mean(frame_fn,
                                                               smallest):
    """Why the integer column survives a rescale at all, measured instead of
    hoped: the closest any sample comes to the mean of its own window is
    1.2e-06 / 7.7e-08 / 5.2e-08 on the three frames, several orders of
    magnitude above a float64 ulp of those returns, and there is not one
    exact tie in 29,600 samples."""
    close = frame_fn()
    r = (close / close.shift(1) - 1.0).to_numpy()
    W = sliding_window_view(r[1:], LENGTH)
    margin = np.abs(W - W.mean(axis=1, keepdims=True))
    assert W.size == 29600
    assert int((margin == 0.0).sum()) == 0
    assert float(margin.min()) > smallest


@pytest.mark.parametrize("factor", [0.5, 3.0])
def test_an_affine_rescale_of_the_returns_is_bit_identical(factor):
    """The property that makes this neither a volatility nor a trend
    feature: every sample is compared with the mean of its own window, so
    `r -> a*r + b` with `a > 0` cannot change which samples are above it."""
    close = _walk()
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    scaled = Series(100.0 * np.cumprod(1.0 + factor * r), index=close.index)
    base, out = ts_strike_20(close), ts_strike_20(scaled)
    assert (base.isna() == out.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == out[m]).all()


def test_log_drift_is_an_affine_map_of_the_returns_and_changes_nothing():
    """Multiplying the closes by `exp(d*t)` maps `r -> e^d * r + (e^d - 1)`,
    which is affine with a positive slope, so the column is bit-identical --
    pinned because the two nearest statistics ports behave differently:
    `ts_c3_20` is NOT drift-invariant (Spearman 0.801318) and
    `lean_hurst_100` is invariant only to 2.4e-15. Those two figures are
    borrowed, not re-run here: both come from `docs/TsC320Measured.md`
    §Invariances, measured in issue #88's session."""
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))),
                     index=close.index)
    base, out = ts_strike_20(close), ts_strike_20(drifted)
    assert (base.isna() == out.isna()).all()
    m = base.notna()
    assert (base[m] == out[m]).all()


@pytest.mark.parametrize("frame_fn,distinct,lo,hi", [
    (_walk, 9, 1, 9), (_tick_rounded, 9, 1, 9), (_ar1, 11, 2, 12),
])
def test_fires_and_is_not_constant(frame_fn, distinct, lo, hi):
    close = frame_fn()
    out = ts_strike_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1480
    assert int((out.dropna() != 0).sum()) == 1480
    assert int(out.nunique()) == distinct
    assert (float(out.min()), float(out.max())) == (float(lo), float(hi))


def test_an_alternating_path_is_a_constant_one_and_says_so():
    """The column CAN be constant on a frame, and this is the frame: returns
    that alternate up and down every bar put every other return above the
    mean, so no run reaches 2. Pinned because it is the honest limit of the
    column -- a frame with no clustering carries no information here."""
    out = ts_strike_20(_alternating()).dropna()
    assert len(out) == 1480
    assert sorted(set(out.tolist())) == [1.0]


@pytest.mark.parametrize("length", [5, 20, 60])
def test_the_warmup_is_exactly_length_bars(length):
    out = ts_strike_20(_walk(1500, seed=11), length=length)
    assert int(out.notna().to_numpy().argmax()) == length
    assert int(out.notna().sum()) == 1500 - length


# ------------------------------------------------- what the column means


def test_it_orders_the_clustering_of_above_average_returns():
    """The column's actual claim. On AR(1) log-return paths the means must
    come out in the order of `phi`: measured 6.5392 / 5.5128 / 4.3872 /
    3.6520 / 3.1297 / 2.7081 / 2.3223 at phi = +0.8 / +0.6 / +0.3 / 0 /
    -0.3 / -0.6 / -0.8. The MEDIANS tie (6 / 5 / 4 / 3 / 3 / 3 / 2), which
    is why the means are what is pinned -- an integer column with nine
    reachable values cannot separate neighbouring cases by its median."""
    means = [float(ts_strike_20(_ar1(phi=phi)).mean())
             for phi in (0.8, 0.6, 0.3, 0.0, -0.3, -0.6, -0.8)]
    assert means == sorted(means, reverse=True)
    assert 6.0 < means[0] < 7.0
    assert 3.4 < means[3] < 3.9
    assert 2.0 < means[-1] < 2.6


def test_a_pure_geometric_trend_reads_zero_not_the_maximum():
    """The trap this column sets for a reader who takes "longest strike
    above the mean" for a trend measure: a path that rises by exactly 1% a
    bar has CONSTANT returns, so nothing is above their mean and the answer
    is 0 -- the bottom of the scale, not the top."""
    out = ts_strike_20(Series(100.0 * np.exp(np.arange(300) * 0.01)))
    assert int(out.notna().sum()) == 280
    assert sorted(set(out.dropna().tolist())) == [0.0]


def test_one_outlier_shortens_the_strike():
    """And the second trap: a single huge return drags the window mean above
    the ordinary returns, so FEWER of them are above it. Measured: the 20
    windows holding a planted +50% return average 1.95 where the same bars
    averaged 2.05 without it, against a frame mean of 3.6912."""
    close = _walk()
    base = ts_strike_20(close)
    arr = close.to_numpy().copy()
    arr[700:] *= 1.5
    spiked = ts_strike_20(Series(arr, index=close.index))
    window = slice(700, 720)
    assert float(spiked.iloc[window].mean()) < float(base.iloc[window].mean())
    assert sorted(set(spiked.iloc[window].tolist())) == [1.0, 2.0]
    assert 3.5 < float(base.dropna().mean()) < 3.9


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    assert ts_strike_20(_walk(LENGTH)) is None


def test_exact_min_history_fires_at_the_warmup_boundary():
    out = ts_strike_20(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH


@pytest.mark.parametrize("length", [None, 0, -5, 2, 0.5, 2.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = ts_strike_20(_walk(400, seed=31), length=length)
    assert out.name == "TS_STRIKE_20"


@pytest.mark.parametrize("length,constant", [(1, 0.0), (2, 1.0)])
def test_why_the_minimum_length_is_three(length, constant):
    """The lengths the module refuses, computed through the variant harness
    to show what they would be: `length=1` is a window that IS its own mean,
    so nothing is above it and the column is 0 everywhere; `length=2` puts
    exactly one of the two above the mean, so it is 1 everywhere. Neither
    carries information, which is what `MIN_LENGTH` encodes."""
    close = _walk(400, seed=31)
    out = _variant(close, length=length)
    assert sorted(set(out.dropna().tolist())) == [constant]
    assert int(out.notna().sum()) == 400 - length


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = ts_strike_20(close, length=10), ts_strike_20(close, length=60)
    assert (a.name, b.name) == ("TS_STRIKE_10", "TS_STRIKE_60")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert float(a[m].corr(b[m], method="spearman")) < 0.9


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(ts_strike_20(close, length=50.9),
                                   ts_strike_20(close, length=50))


def test_fillna_applies():
    out = ts_strike_20(_walk(200, seed=13), fillna=-1.0)
    assert int((out == -1.0).sum()) == LENGTH


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data: each empties exactly the 21 windows that contain it, which is the
    `length + 1` closes one value reads. Nothing before the hole moves."""
    close = _walk(400, seed=21)
    base = ts_strike_20(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = ts_strike_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 220)
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0


def test_an_overflowing_return_pair_is_emptied_rather_than_read_as_flat():
    """A close pair whose RATIO overflows -- 1e-300 followed by 1e50 -- is
    bad data with no return to take, and it has to be emptied rather than
    compared: an infinite return makes the window mean infinite, nothing is
    STRICTLY above it, and the window would read 0, which is this column's
    value for a FLAT window. One spoiled return, so 20 windows."""
    close = _walk(400, seed=31)
    base = ts_strike_20(close)
    pair = close.copy()
    pair.iloc[200] = 1e-300
    pair.iloc[201] = 1e50
    out = ts_strike_20(pair)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH
    assert (int(emptied.min()), int(emptied.max())) == (201, 220)
    raw = _variant(pair, finite_filter=False)
    assert sorted(set(raw.iloc[emptied].tolist())) == [0.0]


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "ts_strike_20" in ta.Category["statistics"]
    assert hasattr(df.ta, "ts_strike_20")
    direct = ts_strike_20(close)
    through = df.ta.ts_strike_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "TS_STRIKE_20"
    assert direct.category == "statistics"
