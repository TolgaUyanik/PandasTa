# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_110` -- Guotai Junan's (2017,
"GTJA191") alpha `#110`, per issue #84:
`SUM(MAX(0,H-C1),20) / SUM(MAX(0,C1-L),20) * 100`. Upside excursion past
yesterday's close over downside excursion past it, in percent; `100` is
balance. No `conv` field in the issue's own `candidates.csv` row
(`docs/issues/screen/candidates.csv:47`) -- a ratio of two price-linear
sums is scale-free with no extra division needed. Gate A derivation is in
the module docstring and `docs/G191110Measured.md`. Gate E ran on this
port on 2026-11-11 (run `is84-g191_110-1dad5ee8`): max |rho| 0.8860 vs
`brar_BR_26` (compute_all, n = 396,399), per-frame max median 0.8819 over
89 frames -- DISCLOSE_GAP, so no column is struck and `G191_110_20` ships
under the bands. The row is in `docs/gate_e_ledger.csv`. The run's own
`top25.csv` carries `brar_BR_26` and no `brar_BR_20`, so the same-length
duplication these tests pin was invisible to that measurement.

What these pin, in order of how much it would hurt to lose:

* THE REDUNDANCY, because it is the reason this column might not survive:
  `brar`'s `BR` is this same formula (`pandas_ta/momentum/brar.py:23-33`),
  and `test_it_restates_brar_br_at_the_same_length` holds the port to
  Spearman 1.0 / `max|diff| <= 4 ulp` against `brar(..., length=20)` (1 ulp
  measured), with the port's own expression re-spelled `brar`'s way
  bit-identical to `BR_20` on all 1,480 shared bars. If someone later
  "fixes" either module into genuine disagreement, this test says so. The
  two are NOT interchangeable even so, and the differences that bite are
  measured in `docs/measure_g191_110.py` rather than listed here: `brar`
  leaves `+-inf` in place, guards history at `length` instead of
  `length + 1`, and double-shifts its own `BR` at a non-zero `offset`
  (`brar.py:38`). `test_the_symmetric_reparametrisation_is_rank_identical`
  pins the other half: `100*up/(up+down)` is Spearman 1.0 against this
  column, so the ratio-vs-RSI choice of scale is invisible to anything
  mining ranks.
* CAUSALITY by future-perturbation: rewrite every high/low/close bar from
  `j` onward (another synthetic walk), demand bars `[0:j]` bit-identical
  with matching NaN masks, over 37 offsets past the 21-bar warm-up. FOUR
  mutants (`importlib` source read, `exec`'d in memory), each shown live
  (differs from the real module) then caught at every one of the 37
  offsets: shifting the final write index `length=20` bars into the future;
  flipping `DELAY` to `close.shift(-1)` so `C1` becomes TOMORROW's close;
  and a `center=True` sum on EACH of the two rolling calls separately, the
  numerator's and the denominator's -- the `bos` look-ahead bug class, and
  one mutant per call so neither arm is proven by analogy. Measured: the
  real module 0 of 37, each mutant 37 of 37. The `offset` parameter, a
  user-reachable way to make THIS column read the future, is pinned
  separately: `offset=+2`/`-2` are exactly the default column shifted later
  and earlier, nothing else. (Not a claim about the package: CLAUDE.md
  names `ichimoku`'s `ICS_26` as an accepted default-parameter look-ahead.)
* CORRECTNESS: an 8-bar hand-derived example at `length=3` (hitting an
  exact `100.0` balance bar, both `MAX(0, .)` floors and a bar whose
  denominator survives on a single tie), and an independent per-bar replay
  at the shipped default in plain Python scalars -- no `.rolling()`, no
  `.clip()`, no `.replace()`; measured diff exactly `0.0` at three bars.
  Plus the readings Gate A had to fix -- three ambiguities, four decisions
  once the `*100` is counted properly -- each measured rather than
  dismissed: the windowed-`TSMAX` reading of `MAX(0, .)` (a DIFFERENT
  column, Spearman 0.449365), the `*100`-on-the-denominator parse (this
  column / 10,000, Spearman 1.0), the `*100`-on-the-numerator parse
  (`brar`'s own: algebraically identical, not bit-identical), and the
  `np.where` spelling of the floor
  (fabricates one output at bar 19 by mapping bar 0's undefined NaN to
  `0.0`). `python docs/measure_g191_110.py` prints all of it, including the
  port being bit-equal to the owner's own (gitignored) screen candidate on
  all 1,480 bars.
* SCALE-FREE: both sums are linear in a positive price rescale and the
  `MAX(0, .)` floor is a scale-invariant comparison, so the ratio cancels
  the factor exactly. Measured bit-identical under PRICE x8/x64
  (power-of-two, exact in IEEE754) and within 1.5e-12 under x10/x3.7, NaN
  masks matching. Because the floors are EXACT comparisons, the branch
  masks are pinned too: 0 bars change branch at any of the four
  multipliers. Plus `0 < fires < n` (1,480 of 1,500) and `nunique > 1`
  (1,480).
* THE VANISHING DENOMINATOR, which is where this column hides information:
  an unbroken 20-bar run of gap-ups makes `SUM(MAX(0,C1-L),20)` exactly 0,
  the ratio `+inf`, and the output NaN -- an extreme reported as missing
  data (`brar` leaves the `inf` in place instead, measured). One bar
  dipping below its prior close rescues exactly the windows containing it
  (10 of 40). A frozen frame is `0/0` with no `inf` at all, and an
  all-gap-down frame is exactly `0.0` on all 20 fired bars.
* `length`'s three unguarded bands: `0` and negatives fall back to the
  default 20, `0 < length < 1` truncates to 0 and ships an ALL-NaN column
  named `G191_110_0` without raising, and `length=1` is legal and
  degenerate (1,045 of 1,500 fires).
* Wiring: `Category`, the accessor, the column name `G191_110_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.brar import brar
from pandas_ta.momentum.g191_110 import g191_110

LENGTH = 20


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    open_ = low + (high - low) * rng2.uniform(0.0, 1.0, n)
    return (Series(high), Series(low), Series(close), Series(open_))


def _gap_up_frame(n=40):
    """Every bar's low sits ABOVE the prior close, so `MAX(0, C1-L)` is 0
    on every bar and the 20-bar denominator is exactly 0."""
    close = 100.0 + np.arange(n, dtype=float)
    return (Series(close + 1.0), Series(close - 0.5), Series(close))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """8 bars at `length=3`, so `min_length = 4` and bars 0..2 are NaN.

    close      = [10, 11,  9, 12, 12, 13, 11, 14]
    C1         = [  -, 10, 11,  9, 12, 12, 13, 11]
    high       = [11, 13, 10, 14, 13, 15, 12, 16]
    low        = [ 9, 10,  8, 11, 11, 12, 10, 13]
    up   = MAX(0, high - C1) = [nan, 3, 0, 5, 1, 3, 0, 5]
    down = MAX(0, C1 - low)  = [nan, 0, 3, 0, 1, 0, 3, 0]

    Both floors fire: bar 2's `high - C1 = -1` and bar 3's `C1 - low = -2`
    are clipped to 0, while bar 1's `C1 - low = 0` is an exact tie that
    stays 0.0 rather than becoming NaN.

    result[t] = 100 * SUM(up, 3)[t] / SUM(down, 3)[t]:
        t=3: 100 * (3+0+5) / (0+3+0) = 266.66666666666663
        t=4: 100 * (0+5+1) / (3+0+1) = 150.0
        t=5: 100 * (5+1+3) / (0+1+0) = 900.0
        t=6: 100 * (1+3+0) / (1+0+3) = 100.0     <- exact balance
        t=7: 100 * (3+0+5) / (0+3+0) = 266.66666666666663

    Independently derived and printed by docs/measure_g191_110.py, matching
    the module's float64 output exactly.
    """
    high = Series([11.0, 13.0, 10.0, 14.0, 13.0, 15.0, 12.0, 16.0])
    low = Series([9.0, 10.0, 8.0, 11.0, 11.0, 12.0, 10.0, 13.0])
    close = Series([10.0, 11.0, 9.0, 12.0, 12.0, 13.0, 11.0, 14.0])
    out = g191_110(high, low, close, length=3)

    assert out.iloc[:3].isna().all()
    expected = {
        3: 266.66666666666663,
        4: 150.0,
        5: 900.0,
        6: 100.0,
        7: 266.66666666666663,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"
    # The balance bar is EXACT, not merely close: 4/4 is representable.
    assert out.iloc[6] == 100.0


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default against a per-bar replay in
    plain Python scalars -- no `.rolling()`, no `.clip()`, no `.replace()`,
    nothing the module itself calls. Measured agreement: exactly `0.0` at
    all three bars (`docs/measure_g191_110.py`)."""
    high, low, close, _ = _walk(900, seed=3)
    out = g191_110(high, low, close)
    h = high.to_numpy(dtype=float)
    lo = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)

    def _loop(t):
        num = den = 0.0
        for i in range(t - LENGTH + 1, t + 1):
            up = h[i] - c[i - 1]
            dn = c[i - 1] - lo[i]
            num += up if up > 0.0 else 0.0
            den += dn if dn > 0.0 else 0.0
        if den == 0.0:
            return float("nan")
        return 100 * (num / den)

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(_loop(t), rel=1e-12), f"bar {t}"


def test_the_rejected_precedence_reading_is_a_constant_rescale():
    """Gate A reading 2: the source string's tail
    `/ SUM(MAX(0,C1-L),20) * 100` could be parsed as `/ (SUM(..) * 100)`.
    The prototype divides first and multiplies the finished ratio
    (`ind_screen.py:463`), which is what ships. The rejected parse is
    measured rather than dismissed: it is this column divided by exactly
    10,000, so no bar is bit-equal, yet Spearman is 1.0 -- a pure constant
    rescale, visible only in the magnitude."""
    high, low, close, _ = _walk()
    out = g191_110(high, low, close)
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    den = (c1 - low).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    rejected = (num / (den * 100)).replace([np.inf, -np.inf], np.nan)

    m = out.notna() & rejected.notna()
    assert int(m.sum()) == 1480
    assert int((out[m] == rejected[m]).sum()) == 0
    assert out[m].corr(rejected[m], method="spearman") == pytest.approx(1.0)
    ratio = out[m] / rejected[m]
    assert float(ratio.min()) == pytest.approx(10000.0, rel=1e-12)
    assert float(ratio.max()) == pytest.approx(10000.0, rel=1e-12)


def test_the_rejected_tsmax_reading_is_a_different_column():
    """Gate A reading 1: `MAX(0, X)` is the POINTWISE floor, not GTJA191's
    windowed `TSMAX`. Unlike the `*100` parse, this one is not cosmetic --
    the windowed reading produces a materially different column (Spearman
    0.449365, `max|diff|` 160.812927, no bar bit-equal), so the reading had
    to be decided rather than shrugged at."""
    high, low, close, _ = _walk()
    out = g191_110(high, low, close)
    c1 = close.shift(1)
    num = (high - c1).rolling(LENGTH, min_periods=LENGTH).max()
    den = (c1 - low).rolling(LENGTH, min_periods=LENGTH).max()
    tsmax = 100 * (num / den).replace([np.inf, -np.inf], np.nan)

    m = out.notna() & tsmax.notna()
    assert int((out[m] == tsmax[m]).sum()) == 0
    rho = float(out[m].corr(tsmax[m], method="spearman"))
    assert rho == pytest.approx(0.449365, abs=5e-6)
    assert float((out[m] - tsmax[m]).abs().max()) > 100.0


def test_the_brar_scalar_placement_is_not_bit_identical():
    """Gate A reading 2, third parse: `(100 * SUM(up)) / SUM(down)` -- the
    scalar on the NUMERATOR, which is what the fork's own `brar` computes
    (`brar.py:32-33`). Algebraically identical to the shipped
    `100 * (SUM(up)/SUM(down))` and NOT identical in float64: measured
    Spearman 1.0, bit-equal on 927 of 1,480 bars, `max|diff|`
    5.684341886080802e-14 (one ulp at this column's maximum; 4 ulp allowed,
    the same bound and the same reason as
    `test_it_restates_brar_br_at_the_same_length`). Pinned so nobody
    "simplifies" one spelling into the other believing it is a no-op."""
    high, low, close, _ = _walk()
    out = g191_110(high, low, close)
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    den = (c1 - low).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    other = ((100 * num) / den).replace([np.inf, -np.inf], np.nan)

    m = out.notna() & other.notna()
    assert int(m.sum()) == 1480
    assert out[m].corr(other[m], method="spearman") == pytest.approx(1.0)
    ulp = float(np.spacing(float(out[m].abs().max())))
    assert float((out[m] - other[m]).abs().max()) <= 4 * ulp
    bit_equal = int((out[m] == other[m]).sum())
    assert 0 < bit_equal < 1480


def test_the_rejected_where_spelling_invents_a_warmup_bar():
    """Gate A reading 3: `.clip(lower=0)` PRESERVES bar 0's NaN (where `C1`
    is undefined); `np.where(x > 0, x, 0.0)` does not -- a NaN fails the
    test and falls to the else branch, fabricating a `0.0` contribution for
    a bar that has none. Measured: the `np.where` form fires on 1,481 bars
    against the port's 1,480 and starts at bar 19 instead of 20, while
    differing on NONE of the bars where both fire. The whole effect is one
    invented output at the warm-up edge -- the kind of bar that silently
    shortens every downstream warm-up."""
    high, low, close, _ = _walk()
    out = g191_110(high, low, close)
    c1 = close.shift(1)
    up = Series(np.where(high - c1 > 0, high - c1, 0.0), index=close.index)
    down = Series(np.where(c1 - low > 0, c1 - low, 0.0), index=close.index)
    num = up.rolling(LENGTH, min_periods=LENGTH).sum()
    den = down.rolling(LENGTH, min_periods=LENGTH).sum()
    where_form = 100 * (num / den).replace([np.inf, -np.inf], np.nan)

    assert int(out.notna().sum()) == 1480
    assert int(where_form.notna().sum()) == 1481
    assert int(out.notna().idxmax()) == 20
    assert int(where_form.notna().idxmax()) == 19
    both = out.notna() & where_form.notna()
    assert int((out[both] != where_form[both]).sum()) == 0


def test_insufficient_history_returns_none():
    high, low, close, _ = _walk(LENGTH)   # defaults need length + 1 = 21
    assert g191_110(high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close, _ = _walk(LENGTH + 1)
    out = g191_110(high, low, close)
    assert out is not None
    assert out.iloc[:LENGTH].isna().all()
    assert pd.notna(out.iloc[LENGTH])
    assert int(out.notna().sum()) == 1


def test_default_name():
    high, low, close, _ = _walk()
    assert g191_110(high, low, close).name == "G191_110_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    """The name contract (CLAUDE.md "Naming is API") plus the obvious
    consequence that the window length changes the values."""
    high, low, close, _ = _walk(300)
    out10 = g191_110(high, low, close, length=10)
    out30 = g191_110(high, low, close, length=30)
    assert out10.name == "G191_110_10"
    assert out30.name == "G191_110_30"
    m = out10.notna() & out30.notna()
    assert (out10[m] != out30[m]).any()


def test_fractional_lengths_that_truncate_the_same_are_identical():
    """The regression `g191_146`'s round 1 actually shipped
    (`tests/test_g191_146.py:193-205`): a parameter kept as `float` for the
    math but truncated to `int` only at the name f-string, so two values
    computed DIFFERENT Series under the IDENTICAL name. Here `length` is
    coerced to `int` at validation time, before any math runs."""
    high, low, close, _ = _walk(300)
    a = g191_110(high, low, close, length=20.4)
    b = g191_110(high, low, close, length=20.9)
    assert a.name == b.name == "G191_110_20"
    pd.testing.assert_series_equal(a, b)


def test_the_length_guards_three_bands():
    """`int(length) if length and length > 0 else 20` leaves three bands,
    none of them raising, all measured:

    * `0` and negatives are falsy / fail `> 0`, so they fall back to the
      default 20 -- bit-identical to the default call.
    * `0 < length < 1` passes the guard and `int()` truncates it to `0`.
      Nothing raises: a zero-width `rolling(0, min_periods=0).sum()` is
      not NaN but `0.0` (measured: `0.0` on all 1,500 bars, 0 NaN), the
      ratio is `0/0`, and an ALL-NaN column ships under the name
      `G191_110_0`.
    * `length=1` is legal and degenerate rather than empty -- a one-bar
      window, so the column fires only where that bar's low broke its prior
      close (1,045 of 1,500 on this frame) and reads exactly `0.0` on the
      430 of those where the bar's high never cleared it. The 430 is a
      count of EXACT zeros (`up == 0` is structural, not a rounding
      outcome); the 616 distinct values the script also prints are not
      pinned here, because a `nunique` over floats turns on last-bit
      equality -- the `g191_022` CI lesson, commit `a56d873`.
    """
    high, low, close, _ = _walk()
    base = g191_110(high, low, close)

    for fallback in (0, -5):
        out = g191_110(high, low, close, length=fallback)
        assert out.name == "G191_110_20"
        pd.testing.assert_series_equal(out, base)

    truncated = g191_110(high, low, close, length=0.5)
    assert truncated.name == "G191_110_0"
    assert int(truncated.notna().sum()) == 0

    one = g191_110(high, low, close, length=1)
    assert one.name == "G191_110_1"
    assert int(one.notna().sum()) == 1045
    assert int((one.dropna() == 0.0).sum()) == 430
    assert int(one.dropna().nunique()) > 1


def test_misaligned_inputs_raise():
    high, low, close, _ = _walk(300)
    shifted = close.copy()
    shifted.index = shifted.index + 1
    with pytest.raises(ValueError):
        g191_110(high, low, shifted)


# ---------------------------------------------------------- redundancy


def test_it_restates_brar_br_at_the_same_length():
    """THE fact this port lives or dies on. `brar`'s `BR` is this formula
    (`pandas_ta/momentum/brar.py:23-33`): `MAX(0, .)` spelled as
    `non_zero_range` plus a negative-clip, the scalar on the numerator, and
    a default length of 26. At the SAME length the two are the same column:
    measured Spearman 1.0, `max|diff|` 5.684341886080802e-14, bit-equal on
    927 of 1,480 bars -- and the port's own expression re-spelled `brar`'s
    way is bit-equal to `BR_20` on ALL 1,480, `max|diff|` exactly 0.0, so
    on this (tie-free) frame the float gap is entirely the `100`'s
    placement. The frame is tie-free by measurement, not by assumption: 0
    bars have `H == C1` and 0 have `C1 == L`, which is the only condition
    under which `non_zero_range`'s epsilon changes anything."""
    high, low, close, open_ = _walk()
    out = g191_110(high, low, close)
    br20 = brar(open_, high, low, close, length=LENGTH)["BR_20"]
    c1 = close.shift(1)

    assert int((high - c1).eq(0).sum()) == 0
    assert int((c1 - low).eq(0).sum()) == 0

    m = out.notna() & br20.notna()
    assert int(m.sum()) == 1480
    assert out[m].corr(br20[m], method="spearman") == pytest.approx(1.0)
    # 1 ulp measured (5.684341886080802e-14 = 2**-44, one ulp at this
    # column's 328.46 maximum); 4 ulp allowed, because the worst case for
    # `100*(a/b)` vs `(100*a)/b` is 2 ulp and the tie-planted frame already
    # reaches 1.1368683772161603e-13 -- a bare 1e-13 literal would go red on
    # a frame with a slightly larger maximum for no mathematical reason.
    ulp = float(np.spacing(float(out[m].abs().max())))
    assert float((out[m] - br20[m]).abs().max()) <= 4 * ulp

    num = (high - c1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    den = (c1 - low).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    brar_spelling = ((100 * num) / den).replace([np.inf, -np.inf], np.nan)
    bm = brar_spelling.notna() & br20.notna()
    assert int(bm.sum()) == 1480
    assert (brar_spelling[bm] == br20[bm]).all()


def test_the_symmetric_reparametrisation_is_rank_identical():
    """`100 * up / (up + down)` -- the RSI-shaped form of the SAME two sums
    -- is a strictly increasing function of `up/down` on `up, down >= 0`,
    so it is a rank-identical restatement: measured Spearman
    `1.0` at full precision (`docs/measure_g191_110.py` prints the `repr`,
    not a `:.6f`). The assertion allows 1e-12 of slack anyway, because a
    Spearman is a Pearson of ranks computed as `sumxy/sqrt(sumxx*sumyy)`
    and `sqrt(x*x) == x` is not an IEEE guarantee -- the `a56d873` lesson
    applied to an exact float equality. The choice between the two forms is
    a choice of SCALE (one is bounded in [0, 100], the other is unbounded
    above), and no rank-based miner can tell them apart."""
    high, low, close, _ = _walk()
    out = g191_110(high, low, close)
    c1 = close.shift(1)
    num = (high - c1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    den = (c1 - low).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
    twin = 100 * (num / (num + den)).replace([np.inf, -np.inf], np.nan)

    m = out.notna() & twin.notna()
    assert int(m.sum()) == 1480
    assert float(out[m].corr(twin[m], method="spearman")) >= 1.0 - 1e-12
    assert float(twin[m].max()) <= 100.0


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_110")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_110_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "    result = 100 * (up_sum / down_sum).replace([np.inf, -np.inf], np.nan)",
    "    result = (100 * (up_sum / down_sum).replace([np.inf, -np.inf], np.nan)).shift(-length)",
)
FORWARD_DELAY_MUTANT = (
    "    prev_close = close.shift(1)",
    "    prev_close = close.shift(-1)",   # C1 becomes TOMORROW's close
)
CENTERED_SUM_MUTANT = (
    "    up_sum = up.rolling(length, min_periods=length).sum()",
    "    up_sum = up.rolling(length, min_periods=length, center=True).sum()",
)
CENTERED_DEN_MUTANT = (
    "    down_sum = down.rolling(length, min_periods=length).sum()",
    "    down_sum = down.rolling(length, min_periods=length, center=True).sum()",
)

OFFSETS = range(50, 1500, 40)  # past the 21-bar warm-up


def _leaks(fn):
    high, low, close, _ = _walk(1500)
    oh, ol, oc, _ = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_110) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close, _ = _walk(1500)
    assert not mod.g191_110(high, low, close).equals(
        g191_110(high, low, close))                        # live
    assert _leaks(mod.g191_110) == len(list(OFFSETS))      # caught, every one


def test_forward_delay_mutant_is_caught():
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    high, low, close, _ = _walk(1500)
    assert not mod.g191_110(high, low, close).equals(
        g191_110(high, low, close))
    assert _leaks(mod.g191_110) == len(list(OFFSETS))


def test_centered_sum_mutant_is_caught():
    mod = _load_mutant(*CENTERED_SUM_MUTANT)
    high, low, close, _ = _walk(1500)
    assert not mod.g191_110(high, low, close).equals(
        g191_110(high, low, close))
    assert _leaks(mod.g191_110) == len(list(OFFSETS))


def test_centered_denominator_sum_mutant_is_caught():
    """The DENOMINATOR's `rolling()` call is a second, identical surface,
    and the numerator mutant above does not cover it: a `center=True` that
    landed on `down_sum` alone would leak just as hard. One mutant per
    rolling call, so neither arm is proven by analogy."""
    mod = _load_mutant(*CENTERED_DEN_MUTANT)
    high, low, close, _ = _walk(1500)
    assert not mod.g191_110(high, low, close).equals(
        g191_110(high, low, close))
    assert _leaks(mod.g191_110) == len(list(OFFSETS))


def test_a_positive_offset_only_delays_and_is_the_forks_convention():
    """`offset` is this fork's standard parameter, and a NEGATIVE offset is
    a user-reachable way to make THIS column read the future. (Not the only
    look-ahead in the package -- CLAUDE.md names `ichimoku`'s `ICS_26`,
    `close.shift(-kijun)` at default parameters, as an accepted exception.)
    Pinned rather than
    assumed: `offset=2` is exactly the default column shifted two bars
    later, with nothing else moved, and `offset=-2` is exactly the default
    shifted two bars EARLIER -- i.e. the look-ahead is the caller's
    explicit request, not a property of the formula, and the Gate B sweep
    above covers the default `offset=0` the registry uses."""
    high, low, close, _ = _walk(400)
    base = g191_110(high, low, close)
    later = g191_110(high, low, close, offset=2)
    earlier = g191_110(high, low, close, offset=-2)
    pd.testing.assert_series_equal(later, base.shift(2), check_names=False)
    pd.testing.assert_series_equal(earlier, base.shift(-2),
                                   check_names=False)
    assert later.name == earlier.name == base.name == "G191_110_20"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, _ = _walk()
    base = g191_110(high, low, close)
    scaled = g191_110(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close, _ = _walk()
    base = g191_110(high, low, close)
    scaled = g191_110(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] - scaled[m]).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_the_clip_branch_masks_do_not_move_under_a_price_scale(k):
    """Both `MAX(0, .)` floors are EXACT comparisons against zero, so a
    rescale moving a bar from one branch to the other would be a real scale
    dependence rather than rounding noise. Measured: 0 bars move, in either
    floor, at any of the four multipliers."""
    high, low, close, _ = _walk()
    c1 = close.shift(1)
    up_pos = (high - c1) > 0
    dn_pos = (c1 - low) > 0
    k_up = (high * k - c1 * k) > 0
    k_dn = (c1 * k - low * k) > 0
    assert int((up_pos != k_up).sum()) == 0
    assert int((dn_pos != k_dn).sum()) == 0


def test_fires_and_is_not_constant():
    """Gate D's `0 < fires < n`. The fire count is structural (the 20-bar
    warm-up, plus any window with a zero denominator -- this frame has
    none), so it is pinned exactly; `nunique` is not, because counting
    distinct float64 values turns on last-bit equality (the `g191_022` CI
    lesson, commit `a56d873`). Measured locally: 1,480 distinct values out
    of 1,480 fires."""
    high, low, close, _ = _walk()
    out = g191_110(high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert fires == 1480
    assert out.dropna().nunique() > 1400


def test_the_column_is_non_negative():
    """Both sums are sums of non-negative terms, so the ratio cannot be
    negative; `100` is the balance point and the column is unbounded above.
    Measured on the walk: min 27.612949, max 328.461817, and the 1,480
    fires split 774 above 100 / 706 below with none exactly on it. The
    split is pinned as a PARTITION (the two counts cover every fired bar
    and none sits exactly on 100) rather than as two integers, since a bar
    landing exactly on 100 would be a last-bit outcome -- the `g191_022` CI
    lesson, commit `a56d873`."""
    high, low, close, _ = _walk()
    d = g191_110(high, low, close).dropna()
    assert (d >= 0.0).all()
    assert len(d) == 1480
    assert int((d > 100).sum()) + int((d < 100).sum()) == 1480
    assert int((d == 100.0).sum()) == 0
    assert float(d.min()) == pytest.approx(27.612949, abs=5e-6)
    assert float(d.max()) == pytest.approx(328.461817, abs=5e-6)


# ------------------------------------------------------------ edge cases


def test_an_unbroken_run_of_gap_ups_is_nan_not_an_extreme():
    """`SUM(MAX(0,C1-L),20) == 0` means no low in 20 bars reached its prior
    close. The ratio is `+inf` and the `.replace()` reports it as MISSING,
    so downstream it is indistinguishable from a short history -- where
    this column throws information away, and it is pinned rather than
    hidden. Measured: the raw ratio is `inf` on 20 of 40 bars and the
    column fires on 0."""
    high, low, close = _gap_up_frame()
    out = g191_110(high, low, close)
    c1 = close.shift(1)
    raw = ((high - c1).clip(lower=0).rolling(LENGTH, min_periods=LENGTH).sum()
           / (c1 - low).clip(lower=0).rolling(LENGTH,
                                              min_periods=LENGTH).sum())
    assert int(np.isinf(raw).sum()) == 20
    assert int(out.notna().sum()) == 0


def test_one_bar_breaking_the_run_rescues_its_windows():
    """A single bar dipping below its prior close gives every window that
    contains it a non-zero denominator. Measured: 10 of 40 bars fire, the
    first at 30 (the poked bar) and the last at 39."""
    high, low, close = _gap_up_frame()
    low.iloc[30] = close.iloc[29] - 1.0
    out = g191_110(high, low, close)
    assert int(out.notna().sum()) == 10
    assert int(out.notna().idxmax()) == 30
    assert pd.notna(out.iloc[39])


def test_a_frozen_frame_is_zero_over_zero_with_no_inf():
    """`H == L == C`, constant: numerator AND denominator are exactly 0, so
    the division is `0/0` -- NaN directly, with no `inf` for the
    `.replace()` to catch. The column fires nowhere, which is the honest
    answer for a tape with no movement in it."""
    close = Series(np.full(40, 100.0))
    out = g191_110(close.copy(), close.copy(), close.copy())
    c1 = close.shift(1)
    raw = ((close - c1).clip(lower=0).rolling(LENGTH,
                                              min_periods=LENGTH).sum()
           / (c1 - close).clip(lower=0).rolling(LENGTH,
                                                min_periods=LENGTH).sum())
    assert int(np.isinf(raw).sum()) == 0
    assert int(out.notna().sum()) == 0


def test_an_all_gap_down_frame_is_exactly_zero():
    """The mirror of the gap-up case, and it does NOT go NaN: no high ever
    clears its prior close (numerator exactly 0) while every low breaks it
    (denominator positive), so the column is exactly `0.0` -- its floor.
    Measured: 20 of 40 bars fire and all 20 are exactly 0.0, which also
    makes the column CONSTANT on such a frame (not a feature, per the ML
    contract)."""
    close = Series(100.0 - np.arange(40, dtype=float))
    high = close + Series(np.r_[0.0, np.full(39, 0.5)])
    low = close - 1.0
    out = g191_110(high, low, close)
    d = out.dropna()
    assert len(d) == 20
    assert (d == 0.0).all()
    assert int(d.nunique()) == 1


def test_a_nan_in_an_input_empties_one_window_and_displaces_nothing():
    """A trailing `rolling().sum()` carries no state past its own window, so
    unlike an `ewm`-based port (measured on the sibling `g191_188`: one NaN
    at 700 displaced 167 later bars) a single NaN empties exactly
    `length` outputs and moves NONE of the others. Measured on the
    1,500-bar walk: one NaN in `high` at 700 empties 20 bars and displaces
    0; one NaN in `close` at 700 also empties 20 (that close is read only as
    bar 701's `C1`)."""
    high, low, close, _ = _walk()
    base = g191_110(high, low, close)

    nh = high.copy()
    nh.iloc[700] = np.nan
    out = g191_110(nh, low, close)
    assert int((base.notna() & out.isna()).sum()) == 20
    both = base.notna() & out.notna()
    assert int((base[both] != out[both]).sum()) == 0
    assert int(out.notna().idxmax()) == 20

    nc = close.copy()
    nc.iloc[700] = np.nan
    out_c = g191_110(high, low, nc)
    assert int((base.notna() & out_c.isna()).sum()) == 20


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, open_ = _walk(400)
    df = pd.DataFrame({"open": open_, "high": high, "low": low,
                       "close": close})
    assert "g191_110" in ta.Category["momentum"]
    out = df.ta.g191_110()
    assert out.name == "G191_110_20"
    pd.testing.assert_series_equal(out, g191_110(high, low, close))
    # the tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) that `hasattr` cannot see.
    renamed = df.ta.g191_110(length=9)
    assert renamed.name == "G191_110_9"
    pd.testing.assert_series_equal(renamed, g191_110(high, low, close,
                                                     length=9))
