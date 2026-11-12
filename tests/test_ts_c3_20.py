# -*- coding: utf-8 -*-
"""TS-C3-20: `ts_c3_20`, tsfresh's C3 nonlinearity measure on returns
(PandasTa issue #88).

    TS_C3_20_1 = mean(r[t] * r[t-1] * r[t-2]) / sd(r)^3, over a window of
                 20 simple returns (18 triples, sd with ddof=1)

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line.** tsfresh
   is NOT installed in this worktree and web access is unavailable, so
   "tsfresh (MIT)" is an attribution, not an oracle. What IS checkable is
   pinned four ways:

   * a window whose value is **exactly `-1/(3*sqrt(3))`** in closed form --
     closes [1, 2, 1, 2, 1] at `length=4, lag=1`, where the returns are
     [+1, -1/2, +1, -1/2], the two triples are -1/2 and +1/4 (mean -1/8)
     and the sample standard deviation is `sqrt(3)/2`
     (`test_hand_derived_window_is_exactly_minus_one_over_three_root_three`,
     module 2.8e-17 away);
   * the screen prototype of `docs/issues/screen/ind_screen.py` (candidate
     `ts_c3_20`), retyped here because that file is gitignored:
     **bit-equal on 1,480 of 1,480** fired bars of a 1,500-bar walk. The
     measurement script also IMPORTS the prototype out of the owner's tree
     when it is present and gets the same 1,480 of 1,480
     (`docs/measure_ts_c3_20.py`, section A2);
   * the issue's line applied window by window with
     `sliding_window_view`, sharing no window machinery with the module:
     max |difference| 4.5e-15, Spearman 1.000000 over 1,480 bars;
   * an independent per-window loop in plain Python scalars -- no numpy, no
     pandas rolling: max |difference| 6.7e-15 over 380 bars.

2. **Gate B, by mutant, on three frames.** Five mutants, each
   `importlib`-read and `exec`'d in memory: the column back-dated by
   `length`; the triple's two lagged factors turned forward
   (`shift(-lag)`); the return read one bar ahead; a `center=True` rolling
   mean on the numerator; a `center=True` rolling standard deviation.
   Measured over 37 J values of a future-perturbation sweep: the real
   module leaks at **0/37** and every mutant is caught at **37/37**, on a
   random walk, on a tick-rounded walk and on a path built to have a
   non-zero third moment. The sweep is run again at the two non-default
   parameter settings `lag=9` and `length=60` for all three mutants whose
   behaviour depends on a parameter: the real module still leaks **0/37** at
   each, and the mutants are caught 37/37 in six of the nine cells. The
   other three are asserted rather than excused, under two explanations —
   two cells at 36/37 (`length=60`), missing only
   J = 40, the one offset below a 60-bar warm-up where both prefixes are
   entirely NaN, and 0/37 for the centred numerator at `lag=9`, where the
   numerator window is 2 and pandas' centring offset `(window-1)//2` is 0,
   so the mutant is byte-for-byte the real module (asserted with
   `equals()`).

3. **The noise floor, and why it is a constant.** `sd != 0` -- the
   prototype's `sdiv` -- is not enough: the returns of an exactly geometric
   path are mathematically constant but vary at rounding level in float64,
   so an unguarded division reports the ratio of two roundings. Measured: a
   1%-a-bar ladder fires 0 of 300 bars guarded and **280 unguarded, up to
   8.0e+41**; an exact x1.5 ladder reaches 3.3e+47. The floor is ABSOLUTE
   (4096 eps = 9.09e-13) rather than a rolling scale because the quantity
   floored is the standard deviation of dimensionless price ratios, so it
   has no window of its own to keep causal. On the two real-shaped frames
   run here it costs nothing: on a walk and on a tick-rounded walk it
   changes neither a NaN flag nor a value (280 of 300 bars fire on each).
   What it bounds is `sd(r)` and NOT `|r|`, which is a different
   comparison from the usual `tick / price` arithmetic — a monotone
   one-tick-per-bar path at price 50 with a 0.01 tick has `sd(r)` 2.1e-7
   and fires 280 of 300, while at price 1e6 with a 0.001 tick it has
   `sd(r)` 1.1e-16 and fires 0 (both measured in
   `docs/measure_ts_c3_20.py`, and the second is the right answer: such a
   window has no volatility to standardise by).

4. **Gate D, and that x8 is bit-identical rather than merely close.** Every
   input is a price RATIO, and `8a / 8b` is the same double as `a / b`:
   1,480 of 1,480 bars bit-identical at x8 and at x64, on each of three
   frames, and on the walk at `lag=9` (1,480 of 1,480) and `length=60`
   (1,440 of 1,440). The difference-of-logarithms spelling of the return is not --
   bit-equal on 821 of 1,499 bars at x8, where the ratio spelling is
   bit-equal on all 1,499. x10 / x3.7 agree to 1.9e-14 with identical NaN
   masks.

5. **What the column means, and what it does not.** For iid returns the
   population value is exactly 0 and the column is centred there (median
   0.0035 over 2,000 independent 20-return windows) but wide (sd 0.2185,
   p10 -0.2602, p90 0.2725), so a single reading says little. The ordering
   is the claim: on paths whose LOG returns are
   `rlog[t] = eps[t] + a*eps[t-1]*eps[t-2]/sigma`, whose population third
   moment is `a*sigma^3` and whose implied standardised value is
   `a/(1+a^2)^1.5` = 0.3578 at a = +0.5 (arithmetic, not measured), the
   medians are 0.2442 / 0.0077 / -0.2550 at a = +0.5 / 0 / -0.5. The LEVEL
   is shrunk toward zero by the short window and grows with it -- measured
   on a 20,000-bar path at a = +0.5: 0.2748 / 0.3390 / 0.3755 / 0.3977 at
   length 20 / 60 / 200 / 1000 -- so only the ordering is pinned. It is NOT
   drift-invariant
   (Spearman 0.8013 against the same walk given +0.004 of log drift a bar)
   -- the numerator is not demeaned, which is what the source formula says.

6. **The four readings the wording leaves open, each priced.** `ddof=0` is
   a STRICT rescaling by `((n-1)/n)^-1.5` = 1.079977 (max |difference|
   0.0616, Spearman 1.000000, and `port * 1.079977` reproduces it to
   5.6e-16); a numerator averaged over a full `length`-wide window reaches
   2 bars further back and is a different column (0.9937 / 0.9201); log
   returns are a close but distinct column (0.0181 / 0.999842); a divisor
   taken over the 18 returns the triples span rather than all 20 is
   different too (0.6252 / 0.994954).

7. **The guard bands, measured rather than asserted.** `length` below 4
   (including 0, negatives and fractions that truncate below 4) falls back
   to 20; `lag` below 1 falls back to 1; `lag` above `(length - 2) // 2` is
   clamped to it, and the effective value is the one in the column name.

8. **Five-point wiring** (`Category`, the accessor, the export) and the
   NaN behaviour of a bad close: NaN, zero, negative, infinite and
   subnormal closes each empty exactly the 21 windows that contain them
   (`length + 1` closes per value), and nothing before the hole moves. The
   other NaN cause is a window whose returns are constant to rounding level
   (item 3): by identical closes, which needs all `length + 1` of them
   (planted at bar 200 of a 400-bar walk, 20 identical closes empty 0 bars,
   21 empty 1 and 25 empty 5), or by an exactly geometric path, whose
   closes are all distinct.

Every number above comes from `docs/measure_ts_c3_20.py`, whose run is
transcribed in `docs/TsC320Measured.md`. Gate E is owed: the launcher runs
`gate_e_overlap.py` after this session and a later session records the
`docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.
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
from pandas_ta.statistics.ts_c3_20 import ts_c3_20

LENGTH, LAG = 20, 1
TRIPLES = LENGTH - 2 * LAG

_REAL = importlib.import_module("pandas_ta.statistics.ts_c3_20")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _nonlinear(n=1500, seed=7, sigma=0.01, a=0.5):
    """A path whose LOG returns are
    `rlog[t] = eps[t] + a * eps[t-1] * eps[t-2] / sigma`, whose population
    third-order autocorrelation `E[rlog_t rlog_{t-1} rlog_{t-2}]` is
    `a * sigma^3`: the smallest process with a non-zero c3 of the
    generator's log returns that is otherwise a walk. The column reads
    SIMPLE returns, which is not the same series."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = eps.copy()
    r[2:] = eps[2:] + a * eps[1:-1] * eps[:-2] / sigma
    return Series(100.0 * np.exp(np.cumsum(r)))


def _alternating(n=1500, small=0.002, large=0.02):
    r = np.where(np.arange(n) % 2 == 0, large, -small)
    return Series(100.0 * np.exp(np.cumsum(r)))


# ------------------------------------------------------------- Gate A


def test_hand_derived_window_is_exactly_minus_one_over_three_root_three():
    """close = [1, 2, 1, 2, 1] at length=4, lag=1, so the window holds the
    four returns [+1, -1/2, +1, -1/2] and exactly two triples:

        r3*r2*r1 = (+1)(-1/2)(+1)   = -1/2
        r4*r3*r2 = (-1/2)(+1)(-1/2) = +1/4     -> mean -1/8
        sd(ddof=1): mean 1/4, sum sq dev 9/4, var 3/4, sd sqrt(3)/2
        value = (-1/8) / (3/4)^1.5 = -1/(3*sqrt(3)) = -sqrt(3)/9

    Derived by hand, independent of any implementation; the module lands
    2.8e-17 away. Also pins that the four bars before the first full
    window are NaN."""
    out = ts_c3_20(Series([1.0, 2.0, 1.0, 2.0, 1.0]), length=4, lag=1)
    assert out.name == "TS_C3_4_1"
    assert out.iloc[:4].isna().all()
    exact = -1.0 / (3.0 * math.sqrt(3.0))
    assert abs(float(out.iloc[4]) - exact) < 1e-15


def _prototype(close, length=LENGTH, lag=LAG):
    """`docs/issues/screen/ind_screen.py` candidate `ts_c3_20`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v):
            r = ret(c)
            return sdiv(mean(r * delay(r, 1) * delay(r, 2), 18),
                        std(r, 20) ** 3)

    with `ret(c) = c / c.shift(1) - 1`, `delay(x, n) = x.shift(n)`,
    `mean(x, n) = x.rolling(n).mean()`, `std(x, n) = x.rolling(n).std()`
    (pandas' default `ddof=1`) and
    `sdiv(a, b) = (a / b).replace([inf, -inf], nan)`."""
    r = close / close.shift(1) - 1
    num = (r * r.shift(lag) * r.shift(2 * lag)).rolling(length - 2 * lag).mean()
    out = num / r.rolling(length).std() ** 3
    return out.replace([np.inf, -np.inf], np.nan)


def test_matches_the_screen_prototype():
    """Bit-equal, not merely close: the module spells the numerator and the
    divisor in the prototype's own order, and on a continuous walk no
    window reaches the noise floor the prototype does not have."""
    close = _walk()
    base, proto = ts_c3_20(close), _prototype(close)
    assert (base.isna() == proto.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == proto[m]).all()


def _c3_windowed(close, length=LENGTH, lag=LAG):
    """The issue's line applied window by window with
    `sliding_window_view`: inside each window of `length` returns, average
    `x[i] * x[i+lag] * x[i+2*lag]` over the `length - 2*lag` triples that
    fit, then divide by that window's own sample standard deviation cubed.
    No pandas rolling anywhere, so it shares no window machinery with the
    module."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    out = np.full(len(r), np.nan)
    if len(r) < length + 1:
        return Series(out, index=close.index)
    W = sliding_window_view(r[1:], length)
    k = 2 * lag
    num = (W[:, k:] * W[:, lag:W.shape[1] - lag] * W[:, :-k]).mean(axis=1)
    sd = W.std(axis=1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        vals = np.where(sd > _REAL.NOISE_FLOOR, num / sd ** 3, np.nan)
    out[length:] = vals
    return Series(out, index=close.index)


def test_matches_the_issues_line_window_by_window():
    close = _walk()
    base, other = ts_c3_20(close), _c3_windowed(close)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert float((base[m] - other[m]).abs().max()) < 1e-13
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12


def _scalar_loop(close, length=LENGTH, lag=LAG):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no pandas rolling, every sum written out."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        r = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        triples = [r[i] * r[i - lag] * r[i - 2 * lag]
                   for i in range(2 * lag, length)]
        num = sum(triples) / len(triples)
        mu = sum(r) / len(r)
        var = sum((v - mu) ** 2 for v in r) / (len(r) - 1)
        sd = math.sqrt(var)
        if sd > _REAL.NOISE_FLOOR:
            out[t] = num / sd ** 3
    return Series(out, index=close.index)


def test_matches_an_independent_scalar_loop():
    close = _walk(400, seed=5)
    base, loop = ts_c3_20(close), _scalar_loop(close)
    assert (base.isna() == loop.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 380
    assert float((base[m] - loop[m]).abs().max()) < 1e-13


def _variant(close, length=LENGTH, lag=LAG, ddof=1, cross_window=False,
             log_returns=False, sd_window=None, guard=True):
    """The module's computation with ONE reading changed."""
    px = close.astype(float)
    if log_returns:
        r = np.log(px / px.shift(1))
    else:
        r = px / px.shift(1) - 1.0
    triples = length - 2 * lag
    width = length if cross_window else triples
    num = (r * r.shift(lag) * r.shift(2 * lag)) \
        .rolling(width, min_periods=width).mean()
    sd = r.rolling(sd_window or length,
                   min_periods=sd_window or length).std(ddof=ddof)
    denominator = sd.where(sd > _REAL.NOISE_FLOOR) if guard else sd
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / denominator ** 3
    return out.replace([np.inf, -np.inf], np.nan)


def test_the_population_standard_deviation_reading_is_a_strict_rescaling():
    """`ddof=0` is the reading this port rejects, and it is the cheapest of
    the four: `sd(ddof=0) = sd(ddof=1) * sqrt((n-1)/n)`, so dividing by its
    cube multiplies the whole column by `((n-1)/n)^-1.5` = 1.079977 at
    length 20. Every bar moves (0 bit-equal) and no rank does."""
    close = _walk()
    base, other = ts_c3_20(close), _variant(close, ddof=0)
    m = base.notna() & other.notna()
    assert int((base[m] == other[m]).sum()) == 0
    diff = float((base[m] - other[m]).abs().max())
    assert 1e-2 < diff < 1e-1
    assert float(base[m].corr(other[m], method="spearman")) >= 1.0 - 1e-12
    factor = ((LENGTH - 1) / LENGTH) ** -1.5
    assert float((base[m] * factor - other[m]).abs().max()) < 1e-14


@pytest.mark.parametrize("kwargs,lo,hi,rho_hi", [
    ({"cross_window": True}, 0.5, 2.0, 0.95),     # numerator over 20 bars
    ({"log_returns": True}, 1e-3, 0.1, 0.99999),  # log returns
    ({"sd_window": TRIPLES}, 0.3, 1.0, 0.999),    # divisor over 18 returns
])
def test_the_other_rejected_readings_are_different_columns(kwargs, lo, hi,
                                                           rho_hi):
    """Each is a reading the issue's wording leaves open and this port
    rejects; each moves the column by a visible amount, so the choice is a
    decision and not a formatting detail."""
    close = _walk()
    base, other = ts_c3_20(close), _variant(close, **kwargs)
    m = base.notna() & other.notna()
    diff = float((base[m] - other[m]).abs().max())
    assert lo < diff < hi
    assert float(base[m].corr(other[m], method="spearman")) < rho_hi


def test_the_full_window_numerator_reading_needs_more_history():
    """The rejected reading gives every triple a full `length`-wide mean,
    which reaches `2*lag` bars further back, so it cannot fire where this
    column does."""
    close = _walk()
    base, other = ts_c3_20(close), _variant(close, cross_window=True)
    assert int(base.notna().to_numpy().argmax()) == LENGTH
    assert int(other.notna().to_numpy().argmax()) == LENGTH + 2 * LAG


# ------------------------------------------------------------- Gate B

WRITE_SHIFT_MUTANT = (
    "    c3 = numerator / (sd.where(sd > NOISE_FLOOR) ** 3)",
    "    c3 = (numerator / (sd.where(sd > NOISE_FLOOR) ** 3)).shift(-length)")
FORWARD_TRIPLE_MUTANT = (
    "    triple = r * r.shift(lag) * r.shift(2 * lag)",
    "    triple = r * r.shift(-lag) * r.shift(-2 * lag)")
FORWARD_RETURN_MUTANT = (
    "    r = px / px.shift(1) - 1.0",
    "    r = px.shift(-1) / px - 1.0")
CENTERED_MEAN_MUTANT = (
    "    numerator = triple.rolling(triples, min_periods=triples).mean()",
    "    numerator = triple.rolling(triples, min_periods=triples, "
    "center=True).mean()")
CENTERED_SD_MUTANT = (
    "    sd = r.rolling(length, min_periods=length).std(ddof=1)",
    "    sd = r.rolling(length, min_periods=length, center=True).std(ddof=1)")

MUTANTS = [WRITE_SHIFT_MUTANT, FORWARD_TRIPLE_MUTANT, FORWARD_RETURN_MUTANT,
           CENTERED_MEAN_MUTANT, CENTERED_SD_MUTANT]
MUTANT_IDS = ["write_shift", "forward_triple", "forward_return",
              "centered_mean", "centered_sd"]
OFFSETS = range(40, 1500, 40)  # past the 20-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "nonlinear": (_nonlinear(), _nonlinear(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_c3_20_mutant")
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
    assert _leaks(ts_c3_20, close, other) == 0


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("mutant", MUTANTS, ids=MUTANT_IDS)
def test_each_mutant_is_caught_on_each_frame(mutant, frame):
    mod = _load_mutant(*mutant)
    close, other = FRAMES[frame]
    assert not mod.ts_c3_20(close).equals(ts_c3_20(close))  # live mutation
    assert _leaks(mod.ts_c3_20, close, other) == len(list(OFFSETS))


NON_DEFAULT = [
    # (mutant, length, lag, caught)
    (FORWARD_TRIPLE_MUTANT, 20, 1, 37),
    (FORWARD_TRIPLE_MUTANT, 20, 9, 37),
    (FORWARD_TRIPLE_MUTANT, 60, 1, 36),
    (CENTERED_MEAN_MUTANT, 20, 1, 37),
    (CENTERED_MEAN_MUTANT, 20, 9, 0),
    (CENTERED_MEAN_MUTANT, 60, 1, 36),
    (WRITE_SHIFT_MUTANT, 20, 1, 37),
    (WRITE_SHIFT_MUTANT, 20, 9, 37),
    (WRITE_SHIFT_MUTANT, 60, 1, 37),
]


@pytest.mark.parametrize("mutant,length,lag,caught", NON_DEFAULT, ids=[
    f"{name}-{length}-{lag}"
    for name, length, lag in (("forward_triple", 20, 1),
                              ("forward_triple", 20, 9),
                              ("forward_triple", 60, 1),
                              ("centered_mean", 20, 1),
                              ("centered_mean", 20, 9),
                              ("centered_mean", 60, 1),
                              ("write_shift", 20, 1),
                              ("write_shift", 20, 9),
                              ("write_shift", 60, 1))])
def test_the_parameter_dependent_mutants_at_non_default_parameters(
        mutant, length, lag, caught):
    """`lag` is user-reachable up to `(length - 2) // 2` = 9 at length 20 and
    `length` is free, while the sweep above runs the defaults only. The three
    mutants whose behaviour depends on a parameter -- the forward triple (on
    `lag`), the centred numerator mean (on its width `length - 2*lag`) and the
    back-dated column (on `length`) -- are re-run here on the walk. The real
    module leaks 0/37 at every setting. Three of the nine cells are not
    37/37, under two explanations, and each explanation is ASSERTED rather
    than argued:

    * 36/37 misses J = 40, the only offset below a 60-bar warm-up, and the
      test asserts that the prefix [0:40] is entirely NaN under both the real
      module and the mutant there, so there was nothing to move;
    * 0/37 at (20, 9) -- one cell -- is a mutation that does nothing: the
      numerator's window
      is 2 wide and pandas centres by `(window - 1) // 2` = 0 bars, so
      `center=True` is `center=False`. The test asserts the mutant's output
      EQUALS the real module's at that setting, and differs from it at the
      other two -- which also says that a centring bug in the numerator
      introduces no look-ahead when the numerator window is 2."""
    close, other = FRAMES["walk"]
    mod = _load_mutant(*mutant)

    def real(c):
        return ts_c3_20(c, length=length, lag=lag)

    def mutated(c):
        return mod.ts_c3_20(c, length=length, lag=lag)

    assert int(real(close).notna().to_numpy().argmax()) == length
    assert _leaks(real, close, other) == 0
    assert _leaks(mutated, close, other) == caught
    if caught == 0:
        assert mutated(close).equals(real(close))  # the mutation is a no-op
    else:
        assert not mutated(close).equals(real(close))  # live mutation
    if caught == len(list(OFFSETS)) - 1:
        first = OFFSETS[0]
        assert real(close).iloc[:first].isna().all()
        assert mutated(close).iloc[:first].isna().all()


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep above
    covers."""
    close = _walk(400, seed=3)
    base = ts_c3_20(close)
    pd.testing.assert_series_equal(ts_c3_20(close, offset=2), base.shift(2),
                                   check_names=False)
    pd.testing.assert_series_equal(ts_c3_20(close, offset=-2), base.shift(-2),
                                   check_names=False)


# ------------------------------------------------------- the noise floor


def test_an_exactly_geometric_frame_is_nan_rather_than_a_ratio_of_roundings():
    """Both ladders have mathematically constant returns, so there is no
    standardised third moment to report. Unguarded (`sd != 0`, which is all
    the prototype's `sdiv` catches) they report one anyway, out of float64
    rounding: 280 of 300 bars, up to 8.0e+41 and 3.3e+47."""
    for frame, floor in ((Series(100.0 * np.exp(np.arange(300) * 0.01)), 1e30),
                         (Series(np.cumprod(np.full(300, 1.5)) * 1e-20), 1e30)):
        guarded, unguarded = ts_c3_20(frame), _variant(frame, guard=False)
        assert int(guarded.notna().sum()) == 0
        assert int(unguarded.notna().sum()) == 280
        assert float(unguarded.abs().max()) > floor


def test_an_exactly_flat_frame_is_nan():
    """`sd` is exactly 0 here, so this one the prototype catches too; it is
    pinned because it is the case a reader expects to be 0 rather than
    NaN."""
    assert int(ts_c3_20(Series(np.full(300, 50.0))).notna().sum()) == 0


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded])
def test_the_noise_floor_costs_nothing_on_real_shaped_data(frame_fn):
    """The floor must not eat small REAL variation. On a walk and on a
    tick-rounded walk (prices on a 0.01 grid, as quotes are) it changes
    neither a NaN flag nor a value against the unguarded form."""
    frame = frame_fn(300)
    guarded, unguarded = ts_c3_20(frame), _variant(frame, guard=False)
    assert int(guarded.notna().sum()) == 280
    assert (guarded.isna() == unguarded.isna()).all()
    m = guarded.notna()
    assert (guarded[m] == unguarded[m]).all()


@pytest.mark.parametrize("price,tick,fires", [(50.0, 0.01, 280),
                                              (1e6, 0.001, 0),
                                              (1e6, 0.01, 0)])
def test_the_floor_bounds_the_dispersion_of_the_returns_not_their_size(
        price, tick, fires):
    """What the floor is and is not compared against. A tick grid quantises
    the return LEVEL at `tick / price` but the DISPERSION of consecutive
    returns at about `(tick / price)^2`, so the familiar "one tick over the
    price is 1e-9 even at a price of 1e6" is not a comparison against this
    floor. On a monotone one-tick-per-bar path: at price 50 with a 0.01 tick
    `sd(r)` is 2.1e-7 and 280 of 300 bars fire; at price 1e6 with a 0.001
    tick `sd(r)` is 1.1e-16 and none do -- which is the right answer,
    because a window whose returns are constant to 1e-16 has no volatility
    to standardise by."""
    closes = Series(price + tick * np.arange(300))
    r = closes / closes.shift(1) - 1.0
    sd = float(r.rolling(LENGTH, min_periods=LENGTH).std(ddof=1).iloc[-1])
    assert int(ts_c3_20(closes).notna().sum()) == fires
    assert (sd > _REAL.NOISE_FLOOR) == (fires > 0)


def test_the_noise_floor_is_an_absolute_constant_not_a_window():
    """It is deliberately NOT a rolling quantity: what it floors is the
    standard deviation of dimensionless price ratios, so a constant works
    and the floor has no window of its own whose causality would need
    pinning. The module's two rolling calls are the numerator's and the
    divisor's, which is what Gate B's two centred mutants cover."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(".rolling(") == 2


# ------------------------------------------------------------- Gate C/D


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _nonlinear])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_c3_20(close), ts_c3_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("length,lag,fires", [(20, 9, 1480), (60, 1, 1440)])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical_at_non_default_parameters(
        length, lag, fires, k):
    """The defaults are not the only reachable setting: `lag` goes to 9 and
    `length` is free. Measured on the walk at (20, 9) and (60, 1)."""
    close = _walk()
    base = ts_c3_20(close, length=length, lag=lag)
    scaled = ts_c3_20(close * k, length=length, lag=lag)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == fires
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _nonlinear])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_are_within_tolerance(frame_fn, k):
    close = frame_fn()
    base, scaled = ts_c3_20(close), ts_c3_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-13


def test_the_difference_of_logarithms_spelling_would_not_be_scale_identical():
    """Why the module spells the return as a price RATIO. `8a / 8b` is the
    same double as `a / b`, but `log(8a) - log(8b)` is not
    `log(a) - log(b)`: on this frame the ratio returns are bit-equal on all
    1,499 bars at x8 and the difference-of-logarithms returns on 821."""
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


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _nonlinear])
def test_fires_and_is_not_constant(frame_fn):
    close = frame_fn()
    out = ts_c3_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1480
    assert int(out.nunique()) == 1480
    assert int((out.dropna() != 0).sum()) == 1480


# ------------------------------------------------- what the column means


def test_the_level_is_centred_for_iid_returns_and_wide():
    """The population value for iid returns is exactly 0, and the column is
    centred there -- but a 20-return window puts the deciles at about
    +-0.26, which is the number a reader needs before treating one reading
    as a signal. Pinned loosely (the seed is fixed, the bounds are not
    tight) on 300 windows; `docs/measure_ts_c3_20.py` runs 2,000 and
    reports median 0.0035, sd 0.2185, p10 -0.2602, p90 0.2725."""
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (300, LENGTH + 1)),
                                     axis=1))
    est = np.array([float(ts_c3_20(Series(p)).iloc[-1]) for p in paths])
    assert np.isfinite(est).all()
    assert abs(float(np.median(est))) < 0.05
    assert 0.40 < float((est > 0).mean()) < 0.60
    assert 0.15 < float(est.std(ddof=1)) < 0.30


def test_it_orders_the_third_moment():
    """The generator's LOG returns are
    `rlog[t] = eps[t] + a*eps[t-1]*eps[t-2]/sigma`, with population
    `E[rlog_t rlog_{t-1} rlog_{t-2}] = a*sigma^3`, so the medians must come
    out in the order of `a`, which is the column's actual claim. The LEVEL
    is not pinned: it is shrunk toward zero by a 20-bar window (measured on
    a 20,000-bar path at a = +0.5: median 0.2748 at length 20, 0.3390 at 60,
    0.3755 at 200, 0.3977 at 1000, against the generator's implied
    standardised `a/(1+a^2)^1.5` = 0.3578)."""
    medians = [float(ts_c3_20(_nonlinear(a=a)).median())
               for a in (0.5, 0.0, -0.5)]
    assert medians == sorted(medians, reverse=True)
    assert medians[0] > 0.15 > -0.15 > medians[-1]
    assert abs(medians[1]) < 0.05


def test_an_alternating_size_path_reads_one_negative_constant():
    """A deterministic path of one large up move and one small down move,
    repeating: every triple holds two moves of one sign and one of the
    other, so the numerator is negative and the same on every bar. Median
    -0.2487, and the whole column's spread (max - min) is 8.893e-14 over
    1,480 bars -- rounding of the rolling mean, which is why it still shows
    748 distinct float values."""
    out = ts_c3_20(_alternating()).dropna()
    assert float(out.median()) < -0.2
    assert len(out) == 1480
    assert float(out.max() - out.min()) < 1e-12


def test_it_is_not_drift_invariant():
    """Drift moves the returns themselves and the numerator is not
    demeaned, so the column DOES move -- Spearman 0.8013, max |difference|
    0.8121. Pinned because the nearest statistics port, `lean_hurst_100`,
    IS drift-invariant (2.4e-15, measured in `docs/LeanHurst100Measured.md`)
    and a reader should not carry that over; `lean_momersion_20`'s own
    docstring records the same NOT-drift-invariant behaviour this column
    has."""
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    base, out = ts_c3_20(close), ts_c3_20(drifted)
    assert (base.isna() == out.isna()).all()
    m = base.notna()
    assert float((base[m] - out[m]).abs().max()) > 0.5
    assert 0.7 < float(base[m].corr(out[m], method="spearman")) < 0.9


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    assert ts_c3_20(_walk(LENGTH)) is None


def test_exact_min_history_fires_at_the_warmup_boundary():
    out = ts_c3_20(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH


@pytest.mark.parametrize("length", [None, 0, -5, 3, 0.5, 2.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = ts_c3_20(_walk(400, seed=31), length=length)
    assert out.name == "TS_C3_20_1"


@pytest.mark.parametrize("lag", [None, 0, -1])
def test_a_lag_below_one_falls_back_to_the_default(lag):
    out = ts_c3_20(_walk(400, seed=31), lag=lag)
    assert out.name == "TS_C3_20_1"


@pytest.mark.parametrize("lag,effective", [(1, 1), (2, 2), (9, 9), (10, 9),
                                           (50, 9)])
def test_lag_is_clamped_so_two_triples_fit_and_the_name_says_so(lag, effective):
    out = ts_c3_20(_walk(400, seed=31), lag=lag)
    assert out.name == f"TS_C3_20_{effective}"
    assert int(out.notna().sum()) == 380


def test_a_short_length_clamps_lag_too():
    out = ts_c3_20(_walk(400, seed=31), length=4, lag=20)
    assert out.name == "TS_C3_4_1"
    assert int(out.notna().sum()) == 396


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = ts_c3_20(close, length=10), ts_c3_20(close, length=60)
    assert (a.name, b.name) == ("TS_C3_10_1", "TS_C3_60_1")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert float(a[m].corr(b[m], method="spearman")) < 0.9


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(ts_c3_20(close, length=50.9),
                                   ts_c3_20(close, length=50))


def test_fillna_applies():
    out = ts_c3_20(_walk(200, seed=13), fillna=-1.0)
    assert int((out == -1.0).sum()) == LENGTH


@pytest.mark.parametrize("identical,emptied", [(20, 0), (21, 1), (25, 5)])
def test_a_flat_run_needs_length_plus_one_identical_closes_to_empty_a_bar(
        identical, emptied):
    """The real-data NaN cause that belongs to THIS column rather than to bad
    data: a window of `length` returns has no volatility when its returns are
    constant to rounding level, and identical closes are one way there -- an
    exactly geometric path, whose closes are all distinct, is the other
    (pinned by
    `test_an_exactly_geometric_frame_is_nan_rather_than_a_ratio_of_roundings`).
    Identical closes need all `length + 1` of them, which is what this test
    measures: on a flat run
    planted at bar 200 of a 400-bar walk, 20 identical closes empty nothing
    (the window's oldest return is still non-zero), 21 empty exactly bar 220,
    25 empty bars 220..224. This is what bounds the warm-up arithmetic in
    `docs/TsC320Measured.md` §Gate C from being read as a prediction."""
    close = _walk(400, seed=21)
    base = ts_c3_20(close)
    flat = close.copy()
    flat.iloc[200:200 + identical] = float(close.iloc[200])
    out = ts_c3_20(flat)
    holes = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(holes) == emptied
    if emptied:
        assert (int(holes.min()), int(holes.max())) == (220, 220 + emptied - 1)


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data: each empties exactly the 21 windows that contain it, which is the
    `length + 1` closes one value reads. Nothing before the hole moves."""
    close = _walk(400, seed=21)
    base = ts_c3_20(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = ts_c3_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 220)
    before = base.notna() & out.notna() & (base != out)
    assert int(before.iloc[:200].sum()) == 0


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "ts_c3_20" in ta.Category["statistics"]
    assert hasattr(df.ta, "ts_c3_20")
    direct = ts_c3_20(close)
    through = df.ta.ts_c3_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "TS_C3_20_1"
    assert direct.category == "statistics"
