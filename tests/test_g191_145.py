# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_145` -- Guotai Junan's (2017, "GTJA191")
alpha `#145`, per issue #78: `(MEAN(V,9)-MEAN(V,26))/MEAN(V,12)*100`. The
Gate A derivation is in the module docstring and `docs/G191145Measured.md`.
Gate E is the launcher's run, not this session's; until it is recorded,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports this indicator as owed, which is expected.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every volume bar from `j`
  onward (another synthetic series), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 25-bar warm-up. One mutant
  (`importlib` source read, `exec`'d in memory, the final write index
  shifted `slow` bars into the future) is shown live (differs from the real
  module) then caught at every offset.
* CORRECTNESS: a 7-bar hand-derived example at `fast=2, slow=4, norm=3`,
  arithmetic written out in the test docstring rather than re-run from the
  module. A second spot check at the shipped defaults against an
  independent per-bar computation using plain numpy slicing, asserted at
  `rel=1e-9` because the two do NOT agree at every bar: on the frame
  `docs/measure_g191_145.py` uses, bar 300 lands bit-identical while bars
  600 and 899 differ by `1.15e-14` and `1.42e-14` (~2e-15 relative), the
  slice-sum order differing from `.rolling().mean()`'s. And a 900-bar
  frame (seed 29) against the prototype's own expression, matched
  BIT-FOR-BIT -- same NaN mask, same bits; the 1,500-bar run reporting
  `max|diff| = 0.0` against the REAL candidate loaded out of
  `docs/issues/screen/ind_screen.py` is that script's, not this file's
  (the screen is gitignored, so a test may not depend on it). There is no
  disclosed interpretation choice in this port, unlike `g191_040`.
* ZERO-DENOMINATOR, all three of its arithmetic cases: with `fast <= norm`
  (the shipped `9 <= 12`) the `norm` window all zero while the `slow`
  window still carries volume (`negative / 0` = `-inf`, which the shipped
  `.replace` maps to NaN); every window all zero (`0 / 0`, already NaN
  before the `.replace` runs); and, reachable ONLY when a caller asks for
  `fast > norm`, a zero `norm` window under a POSITIVE numerator
  (`+inf`). Pinned on three dedicated small fixtures, because the two
  frames whose fire counts are
  actually pinned contain NO zero-volume bar at all (both draw from
  `rng.uniform(1e4, 1e6)`): the 900-bar frame here
  (`test_fires_and_is_not_constant`, `fires == 875 == 900 - 25`, no
  interior gap) and the 1,500-bar frame of `docs/measure_g191_145.py`
  (`fires = 1475 = 1500 - 25`, `zero_volume_bars = 0`). The other
  synthetic frames in these two files are not checked for it, and how
  often it happens on real data is not measured by anything this session
  ran -- that is Gate E's.
* NaN PROPAGATION: a single NaN volume at an INTERIOR bar `t` blanks
  exactly `max(fast, slow, norm) = slow = 26` output bars, `t .. t+25`,
  leaves NO bar newly defined, and moves the surviving bars by float64
  rounding only
  (`max|diff| = 4.97e-14` on the 1,500-bar frame of
  `docs/measure_g191_145.py`; NOT bit-identical, which is why this asserts
  `rtol=1e-9` rather than equality). Near either end the span is shorter,
  because it runs off the frame or overlaps the warm-up: the same script
  measures **5** blanked bars for a hole at 1495 and **11** (`25..35`) for
  one at bar 10.
* SCALE-FREE: volume x8/x64 bit-identical, x10/x3.7 within tolerance (the
  `k` cancels inside the division, for ANY `k > 0`). The column takes no
  price argument at all, which is pinned on the signature and through the
  `df.ta` accessor rather than by rescaling a price the function never
  sees. Plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_145_9_26_12`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_145 import g191_145


def _volume(n=900, seed=97, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


def _walk(n=900, seed=11, sigma=0.015):
    """Synthetic close-price walk. Used only to build a DataFrame for the
    accessor tests -- this column reads no price input."""
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """fast=2, slow=4, norm=3 on volume = [10, 20, 30, 40, 50, 60, 10].

    bar 3: fast=mean(30,40)=35  slow=mean(10,20,30,40)=25  norm=mean(20,30,40)=30
           100*(35-25)/30 =  33.333333
    bar 4: fast=mean(40,50)=45  slow=mean(20,30,40,50)=35  norm=mean(30,40,50)=40
           100*(45-35)/40 =  25.0
    bar 5: fast=mean(50,60)=55  slow=mean(30,40,50,60)=45  norm=mean(40,50,60)=50
           100*(55-45)/50 =  20.0
    bar 6: fast=mean(60,10)=35  slow=mean(40,50,60,10)=40  norm=mean(50,60,10)=40
           100*(35-40)/40 = -12.5

    Bars 0-2 are warm-up: the slow mean needs 4 observations, so the first
    bar at which all three means exist is `max(2,4,3) - 1 = 3`. Bar 6
    exercises the negative branch (a volume drop pulling the fast mean
    below the slow one), which the three strictly-rising bars before it do
    not. Derived by hand, not by re-running the module.
    """
    volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 10.0])
    out = g191_145(volume, fast=2, slow=4, norm=3)

    assert out.iloc[:3].isna().all()
    expected = {3: 100 * 10 / 30, 4: 25.0, 5: 20.0, 6: -12.5}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults against an independent
    per-bar computation using plain numpy slicing, not the module's own
    `.rolling().mean()` calls. `rel=1e-9`, not equality, because the two do
    not agree at every bar: the slice sum accumulates in a different order
    from pandas' rolling mean. Measured on the same three bars by
    `docs/measure_g191_145.py` -- bar 300 happens to land bit-identical
    (`|diff| = 0.0`), bars 600 and 899 do not (`1.15e-14`, `1.42e-14`,
    about 2e-15 relative)."""
    volume = _volume(900, seed=13)
    out = g191_145(volume)
    v = volume.to_numpy(dtype=float)

    def expected_at(t):
        fast_mean = v[t - 8:t + 1].sum() / 9.0
        slow_mean = v[t - 25:t + 1].sum() / 26.0
        norm_mean = v[t - 11:t + 1].sum() / 12.0
        return 100.0 * ((fast_mean - slow_mean) / norm_mean)

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9), f"bar {t}"


def test_matches_the_prototype_expression_bit_for_bit():
    """The issue's own prototype (`docs/issues/screen/ind_screen.py:494-495`)
    is `100 * sdiv(mean(v,9) - mean(v,26), mean(v,12))`, with
    `mean(x,n) = x.rolling(n).mean()` (line 47) and
    `sdiv(a,b) = (a/b).replace([inf,-inf], nan)` (lines 41-42). This port
    has no disclosed interpretation choice, so it must agree with that
    expression EXACTLY, not within a tolerance: same NaN mask, same bits.
    (`g191_040` could not make this claim -- its bar-0 boundary forced a
    deliberate departure.)

    The expression below is RETYPED from those lines, because
    `docs/issues/` is gitignored and a clone running this suite does not
    have it. `docs/measure_g191_145.py` closes that gap where the file IS
    present: it loads `ind_screen.py` by path, calls the registered
    `g191_145` candidate itself, and prints both the port-vs-candidate and
    the retyped-vs-candidate comparisons -- on its 1,500-bar frame all
    three are bit-identical, so the retyping is not hiding a slip."""
    volume = _volume(900, seed=29)
    out = g191_145(volume)

    def mean(x, n):
        return x.rolling(n).mean()

    prototype = 100 * ((mean(volume, 9) - mean(volume, 26))
                       / mean(volume, 12)).replace([np.inf, -np.inf], np.nan)

    assert (out.isna() == prototype.isna()).all()
    m = out.notna()
    assert (out[m] == prototype[m]).all()


def test_zero_volume_window_divides_to_nan():
    """First of the three zero-denominator cases: the `norm` window is
    entirely zero-volume while the `slow` window still carries volume, so
    the numerator is strictly negative and the quotient is `-inf`.

    `volume = [10, 20, 0, 0, 0]`, `fast=2, slow=4, norm=3`. At bar 4 the
    norm window is bars 2-4, all zero, so `norm_mean = 0`; the slow window
    is bars 1-4, mean 5; the fast window is bars 3-4, mean 0. So
    `100 * (0 - 5) / 0 = -inf`, which the shipped
    `.replace([np.inf, -np.inf], np.nan)` turns into NaN. Bar 3 is NOT a
    zero-denominator bar (its norm window still contains bar 1's 20 units)
    and stays finite at -112.5, which is what makes bar 4 attributable to
    the branch rather than to a warm-up gap.

    That the NaN comes from the shipped replace, and not from somewhere
    upstream, is shown with a mutant rather than with a re-typed copy of
    the module's own arithmetic: deleting the `.replace(...)` call leaves
    `-inf` at exactly that bar."""
    volume = Series([10.0, 20.0, 0.0, 0.0, 0.0])
    out = g191_145(volume, fast=2, slow=4, norm=3)

    assert out.iloc[3] == pytest.approx(-112.5, abs=1e-9)
    assert pd.isna(out.iloc[4])

    mod = _load_mutant(*INF_REPLACE_MUTANT)
    raw = mod.g191_145(volume, fast=2, slow=4, norm=3)
    assert raw.iloc[3] == pytest.approx(-112.5, abs=1e-9)
    assert np.isneginf(raw.iloc[4])


def test_all_zero_volume_divides_zero_by_zero_to_nan():
    """Second zero-denominator case, with DIFFERENT arithmetic: every
    window is all-zero, so the numerator is `0 - 0 = 0` as well and the
    quotient is `0/0`, which is already NaN before the shipped `.replace`
    ever runs. Shown by the same mutant: with the replace deleted the bars
    are still NaN, never `+-inf` -- so this case reaches the same output by
    a different route from the other two, which both arrive as an infinity
    the shipped `.replace` then maps."""
    volume = Series([0.0, 0.0, 0.0, 0.0, 0.0])
    out = g191_145(volume, fast=2, slow=4, norm=3)
    assert out.iloc[3:].isna().all()

    mod = _load_mutant(*INF_REPLACE_MUTANT)
    raw = mod.g191_145(volume, fast=2, slow=4, norm=3)
    assert raw.iloc[3:].isna().all()
    assert not np.isinf(raw.to_numpy(dtype=float)).any()


def test_fast_above_norm_can_divide_a_positive_numerator_by_zero():
    """Third zero-denominator case, unreachable at the shipped defaults and
    reachable only because the three windows are caller-settable. With
    `fast > norm` a zero `norm` window no longer forces a zero `fast`
    window, so the numerator can be POSITIVE and the quotient `+inf`
    rather than `-inf`.

    `fast=4, slow=6, norm=2` on `volume = [0, 0, 0, 1000, 1000, 0, 0]`. At
    bar 6: norm window = bars 5-6 = `[0, 0]`, mean 0; fast window = bars
    3-6 = `[1000, 1000, 0, 0]`, mean 500; slow window = bars 1-6 =
    `[0, 0, 1000, 1000, 0, 0]`, mean 333.33. So `100 * (500 - 333.33) / 0
    = +inf`. Bar 5 stays finite, which is what makes bar 6 attributable to
    the branch. The shipped code returns NaN at bar 6; the same mutant --
    the module source with the `.replace(...)` deleted -- leaves `+inf`
    there, so that NaN is attributable to the guard and to nothing else."""
    volume = Series([0.0, 0.0, 0.0, 1000.0, 1000.0, 0.0, 0.0])
    out = g191_145(volume, fast=4, slow=6, norm=2)

    assert out.iloc[5] == pytest.approx(100 * (500 - 1000 / 3) / 500, rel=1e-12)
    assert pd.isna(out.iloc[6])

    mod = _load_mutant(*INF_REPLACE_MUTANT)
    raw = mod.g191_145(volume, fast=4, slow=6, norm=2)
    assert np.isposinf(raw.iloc[6])


def test_a_nan_volume_blanks_only_the_windows_that_contain_it():
    """`rolling(n, min_periods=n)` propagates a NaN into every window that
    contains it, so one NaN volume at an INTERIOR bar `t` blanks
    `max(fast, slow, norm) = slow = 26` output bars, `t .. t+25` -- the
    slow window is the widest, and it is the last to stop reading bar `t`.
    Interior is load-bearing: `docs/measure_g191_145.py` measures the same
    hole at bar 1495 of 1,500 (**5** blanked bars, the rest of the span
    running off the frame) and at bar 10 (**11** blanked bars, `25..35`,
    because `10..24` were already warm-up NaN). Bar 150 of 300 here is
    interior. No bar becomes defined that
    was not, and the bars that stay defined move by float64 rounding only
    (`max|diff| = 4.97e-14` on the 1,500-bar frame of
    `docs/measure_g191_145.py`): pandas' rolling mean accumulates in a
    different order once a NaN sits in the series. They are NOT
    bit-identical, which is why this asserts `rtol=1e-9`."""
    volume = _volume(300, seed=19)
    clean = g191_145(volume)

    holed = volume.copy()
    holed.iloc[150] = np.nan
    out = g191_145(holed)

    newly_nan = [int(i) for i in out.index[out.isna() & clean.notna()]]
    assert newly_nan == list(range(150, 176))  # slow = 26 bars
    assert int((out.notna() & clean.isna()).sum()) == 0  # none newly defined
    unaffected = clean.notna() & out.notna()
    np.testing.assert_allclose(
        out[unaffected].to_numpy(), clean[unaffected].to_numpy(), rtol=1e-9
    )


def test_insufficient_history_returns_none():
    assert g191_145(_volume(25)) is None  # defaults need max(9,26,12) = 26


def test_exact_min_length_fires_at_the_warmup_boundary():
    out = g191_145(_volume(26))  # exactly 26 bars
    assert out is not None
    assert out.iloc[:25].isna().all()
    assert pd.notna(out.iloc[25])


def test_default_name():
    assert g191_145(_volume()).name == "G191_145_9_26_12"


def test_distinct_lengths_produce_distinct_names_and_values():
    volume = _volume(300)
    out1 = g191_145(volume, fast=5, slow=20, norm=10)
    out2 = g191_145(volume, fast=5, slow=20, norm=15)
    assert out1.name == "G191_145_5_20_10"
    assert out2.name == "G191_145_5_20_15"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_the_three_windows_are_not_silently_reordered():
    """`pvo` swaps `fast` and `slow` when a caller inverts them. This port
    deliberately does not (manifest ASSUMPTION A2): the source formula has
    no such rule, and swapping would return the negation of what the caller
    asked for. Pinned so the behaviour cannot drift into a swap unnoticed:
    inverting the two windows negates the column exactly, bar for bar."""
    volume = _volume(300)
    straight = g191_145(volume, fast=5, slow=20, norm=10)
    inverted = g191_145(volume, fast=20, slow=5, norm=10)
    assert inverted.name == "G191_145_20_5_10"
    m = straight.notna() & inverted.notna()
    assert m.sum() > 0
    assert (straight[m] == -inverted[m]).all()


def test_offset_shifts_the_series():
    volume = _volume(200)
    base = g191_145(volume)
    shifted = g191_145(volume, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_both_signs_occur():
    """The column is unbounded in both directions -- unlike `g191_040`,
    which is a ratio of two non-negative sums. A frame on which it never
    went negative would be a frame where the fast mean never dipped below
    the slow one, which would make the sign half of the feature dead."""
    out = g191_145(_volume()).dropna()
    assert (out > 0).any() and (out < 0).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_145")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_145_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


_SHIPPED_WRITE = (
    "    result = (100.0 * ((fast_mean - slow_mean) / norm_mean)).replace(\n"
    "        [np.inf, -np.inf], np.nan)"
)

WRITE_SHIFT_MUTANT = (
    _SHIPPED_WRITE,
    _SHIPPED_WRITE + ".shift(-slow)",  # a slow-bar look-ahead
)

#: Not a causality mutant -- used by the three zero-denominator tests above
#: to show that their NaN is produced by the shipped `inf -> NaN` replace
#: (the first and third cases, `-inf` and `+inf`) or by `0/0` upstream of
#: it (the second).
INF_REPLACE_MUTANT = (
    _SHIPPED_WRITE,
    "    result = (100.0 * ((fast_mean - slow_mean) / norm_mean))",
)

OFFSETS = range(50, 900, 25)  # past the 25-bar warm-up


def _leaks(fn):
    volume = _volume(900)
    other_volume = _volume(900, seed=59)
    base = fn(volume)
    hits = 0
    for j in OFFSETS:
        pv = volume.copy()
        pv.iloc[j:] = other_volume.iloc[j:].values
        out = fn(pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_145) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    volume = _volume(900)
    assert not mod.g191_145(volume).equals(g191_145(volume))  # live
    assert _leaks(mod.g191_145) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    volume = _volume()
    base = g191_145(volume)
    scaled = g191_145(volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    volume = _volume()
    base = g191_145(volume)
    scaled = g191_145(volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-6


def test_no_price_input_so_a_price_scale_cannot_reach_the_column():
    """The function's signature takes volume only, so a price rescale is
    not merely harmless -- it is unreachable. Asserted on the signature
    AND through the `df.ta` accessor, where a price column does exist and
    could in principle be picked up: multiplying every OHLC column by 7.3
    leaves the output bit-identical."""
    argnames = g191_145.__code__.co_varnames[:g191_145.__code__.co_argcount]
    assert argnames == ("volume", "fast", "slow", "norm", "offset")

    close = _walk(300)
    volume = _volume(300)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close, "volume": volume})
    rescaled = df.copy()
    for col in ("open", "high", "low", "close"):
        rescaled[col] = rescaled[col] * 7.3

    base = df.ta.g191_145()
    other = rescaled.ta.g191_145()
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert (base[m] == other[m]).all()


def test_fires_and_is_not_constant():
    volume = _volume()
    out = g191_145(volume)
    fires = int(out.notna().sum())
    assert fires == 875  # 900 - 25
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1
    # no interior gap, and no zero-volume bar on this frame -- which is why
    # the zero-denominator branch needs its own fixtures above.
    assert out.iloc[25:].notna().all()
    assert int((volume == 0).sum()) == 0


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    volume = _volume(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": volume})
    assert "g191_145" in ta.Category["volume"]
    out = df.ta.g191_145()
    assert out.name == "G191_145_9_26_12"
    pd.testing.assert_series_equal(out, g191_145(volume))
    renamed = df.ta.g191_145(fast=5, slow=20, norm=10)
    assert renamed.name == "G191_145_5_20_10"
