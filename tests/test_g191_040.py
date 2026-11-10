# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_040` -- Guotai Junan's (2017, "GTJA191")
alpha `#40`, per issue #77: `SUM(C>C1 ? V : 0, 26) / SUM(C<=C1 ? V : 0, 26)
* 100`. Gate A derivation is in the module docstring and
`docs/G191040Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close/volume bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 26-bar warm-up. One mutant
  (`importlib` source read, `exec`'d in memory, the final write index
  shifted `length` bars into the future) is shown live (differs from the
  real module) then caught at every offset.
* CORRECTNESS: a 9-bar hand-derived example at `length=3` (including a
  flat-day boundary bar, landing in the down-bucket per the issue's own
  `C<=C1` string), checked against an independent per-bar computation. A
  second spot check at the shipped default (`length=26`) against an
  independent per-bar loop using plain numpy.
* The DISCLOSED undefined-direction interpretation, pinned twice on the
  SHIPPED function's own output (never on a re-typed copy of its
  expressions): at `length=3` the first full window, bar 2, touches bar 0,
  where the prototype's `v.where(~up, 0.0)` fabricates a finite `50.0`
  (bar 0 counted as a down-bar, because `C > NaN` is `False` so `~up` is
  `True`) and a mutant with the module's own `.mask(undefined, np.nan)`
  deleted fabricates a different finite `66.666...` (bar 0 contributing 0
  to both buckets); the shipped module returns NaN at that bar and matches
  the prototype at every later bar. The mask covers `close.isna()` too, so
  one NaN close blanks `length + 1 = 27` output bars, leaves NO bar newly
  defined, and moves the surviving bars by float64 rounding only
  (`max|diff| = 5.68e-14` on the 1,500-bar frame of
  `docs/measure_g191_040.py`; NOT bit-identical, which is why the test
  asserts `rtol=1e-9` rather than equality).
* ZERO-DOWN-VOLUME, both of its causes: every bar in the window an up-day,
  OR every non-up bar in the window carrying zero volume (the one a halted
  session produces). Pinned on two dedicated small fixtures, because the
  two frames whose fire counts are actually pinned do not reach the branch
  at `length=26`: the 900-bar frame here (`test_fires_and_is_not_constant`,
  `fires == 874 == 900 - 26`, no interior gap) and the 1,500-bar frame of
  `docs/measure_g191_040.py` (`fires = 1474 = 1500 - 26`, longest up-run
  16 against the 26 needed). The other synthetic frames in these two files
  are not checked for it, and how often it happens on real data is NOT
  measured here; that waits on Gate E.
* SCALE-FREE: VOLUME x8/x64 bit-identical, x10/x3.7 within tolerance (the
  `k` cancels inside the ratio of two linear sums, for ANY `k > 0`); PRICE
  x8/x64/x10/x3.7 ALL bit-identical (only the SIGN of a price difference is
  read, never its magnitude) -- plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_040_26`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_040 import g191_040


def _walk(n=900, seed=11, lo=50.0, hi=150.0):
    """Synthetic close-price random walk."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1.5, n)
    close = lo + np.abs(np.cumsum(steps)) % (hi - lo)
    return Series(close)


def _volume(n=900, seed=97, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


# ------------------------------------------------------------ correctness


def test_hand_derived_nine_bars():
    """length=3: G191_040 = 100 * SUM(up_volume, 3) / SUM(down_volume, 3).

    close  = [100, 105, 103, 103, 108, 95, 110, 100, 120]
    volume = [ 10,  20,  30,  40,  50, 60,  70,  80,  90]
    C1 (shift 1):          NaN, 100, 105, 103, 103, 108,  95, 110, 100
    up (C>C1):              --, True, False, False, True, False, True, False, True
    down (C<=C1):           --, False, True, True, False, True, False, True, False
    up_volume:              NaN,  20,   0,   0,  50,   0,  70,   0,  90
    down_volume:            NaN,   0,  30,  40,   0,  60,   0,  80,   0

    bar3: up=sum(20,0,0)=20   down=sum(0,30,40)=70   100*20/70  = 28.571429
    bar4: up=sum(0,0,50)=50   down=sum(30,40,0)=70   100*50/70  = 71.428571
    bar5: up=sum(0,50,0)=50   down=sum(40,0,60)=100  100*50/100 = 50.000000
    bar6: up=sum(50,0,70)=120 down=sum(0,60,0)=60    100*120/60 = 200.000000
    bar7: up=sum(0,70,0)=70   down=sum(60,0,80)=140  100*70/140 = 50.000000
    bar8: up=sum(70,0,90)=160 down=sum(0,80,0)=80    100*160/80 = 200.000000

    Derived by hand, not by re-running the module. Bar3 exercises the
    flat-day (`C==C1`) boundary inside the summed window, landing in the
    down-bucket per the issue's own `C<=C1` string.
    """
    close = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0, 110.0, 100.0, 120.0])
    volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0])
    out = g191_040(close, volume, length=3)

    assert out.iloc[:3].isna().all()
    expected = {
        3: 100 * 20 / 70, 4: 100 * 50 / 70, 5: 100 * 50 / 100,
        6: 100 * 120 / 60, 7: 100 * 70 / 140, 8: 100 * 160 / 80,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=26) against an
    independent per-bar computation using plain numpy slicing, not the
    module's own `.rolling()` calls."""
    close = _walk(900, seed=5)
    volume = _volume(900, seed=13)
    out = g191_040(close, volume)
    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    length = 26

    def expected_at(t):
        up_sum = 0.0
        down_sum = 0.0
        for i in range(t - length + 1, t + 1):
            if c[i] > c[i - 1]:
                up_sum += v[i]
            else:
                down_sum += v[i]
        return 100 * up_sum / down_sum

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_bar_zero_is_excluded_from_both_buckets_unlike_the_prototype():
    """Pins the disclosed deviation from the prototype
    (`docs/issues/screen/ind_screen.py:350-354`), which computes the down
    bucket as `v.where(~up, 0.0)`: since `C > NaN` is `False`, `~up` is
    `True` at bar 0, so the prototype silently counts bar 0's whole volume
    as DOWN even though its direction is undefined (no prior close).

    Asserted against the SHIPPED function, not against a re-typed copy of
    its own expressions: at `length=3` the window at bar 2 is the first
    full window and it touches bar 0, so the prototype returns a finite
    `100 * 20 / 40 = 50.0` there (bar 0's 10 units of volume fabricated
    into the down bucket) while this port returns NaN. Every later bar,
    whose window excludes bar 0, agrees with the prototype. Removing the
    `.mask(undefined, ...)` from the module makes bar 2 finite and fails
    this test."""
    close = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0])
    volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])

    # the prototype's own formula, verbatim from ind_screen.py:350-354
    up = close > close.shift(1)
    prototype = 100 * volume.where(up, 0.0).rolling(3).sum() \
        / volume.where(~up, 0.0).rolling(3).sum()
    assert prototype.iloc[2] == pytest.approx(100 * 20 / 40, abs=1e-9) == 50.0

    out = g191_040(close, volume, length=3)
    assert pd.isna(out.iloc[2]), "bar 2's window touches bar 0, so it is undefined"
    for t in (3, 4, 5):
        assert out.iloc[t] == pytest.approx(prototype.iloc[t], rel=1e-12), f"bar {t}"


def test_mask_removal_mutant_fabricates_the_bar_zero_window():
    """The pin above, driven from the other side: a mutant with the module's
    own `.mask(undefined, np.nan)` deleted (`importlib` source read,
    `exec`'d in memory) reports a FINITE value at bar 2, so the shipped
    NaN there is produced by that mask and by nothing else.

    The three readings of the same 6-bar fixture at `length=3` all differ,
    which is why the choice is disclosed rather than silent:

    * prototype (`v.where(~up, 0.0)`): `100 * 20 / 40 = 50.0` -- bar 0's
      10 units of volume fabricated into the DOWN bucket.
    * this module with the mask deleted (`C<=C1`, which is False at bar 0
      exactly as `C>C1` is): `100 * 20 / 30 = 66.666...` -- bar 0
      contributes 0 to BOTH buckets, so the window fires on an effectively
      2-bar sample.
    * shipped: NaN -- bar 0 is excluded from both buckets AND from every
      window that reads it.
    """
    close = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0])
    volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])

    mod = _load_mutant(*MASK_REMOVAL_MUTANT)
    mutant_out = mod.g191_040(close, volume, length=3)
    assert mutant_out.iloc[2] == pytest.approx(100 * 20 / 30, rel=1e-12)
    assert pd.isna(g191_040(close, volume, length=3).iloc[2])


def test_zero_volume_down_bars_also_divide_by_zero_to_nan():
    """The denominator is zero whenever the down-bucket SUM is zero, which
    has a second cause besides an all-up window: the window DOES contain a
    non-up bar, but that bar carries zero volume. A halted / zero-turnover
    session prints a flat close, which `C<=C1` puts in the down bucket with
    `V = 0`. `close=[100,101,100,101,102]`, `volume=[10,20,0,30,40]`,
    `length=3`: bar 2 is the only non-up bar and its volume is 0, so the
    windows at bars 3 and 4 both have a zero down-bucket sum -- and bar 2
    IS inside both of them, so this is not the all-up case."""
    close = Series([100.0, 101.0, 100.0, 101.0, 102.0])
    volume = Series([10.0, 20.0, 0.0, 30.0, 40.0])
    out = g191_040(close, volume, length=3)

    assert pd.isna(out.iloc[3])
    assert pd.isna(out.iloc[4])
    # the non-up bar is genuinely in both windows: it is bar 2, and it is
    # a down-bar by the issue's own `C<=C1` string.
    assert close.iloc[2] <= close.iloc[1]
    # and the NaN is the shipped `inf -> NaN` replace, not a warm-up gap:
    # the same mutant with that call deleted leaves +inf at both bars.
    mod = _load_mutant(*INF_REPLACE_MUTANT)
    raw = mod.g191_040(close, volume, length=3)
    assert np.isinf(raw.iloc[3]) and raw.iloc[3] > 0
    assert np.isinf(raw.iloc[4]) and raw.iloc[4] > 0


def test_a_nan_close_blanks_only_the_windows_that_contain_it():
    """`undefined` masks BOTH closes of the comparison, not just the prior
    one. A NaN at `close[t]` makes `C > C1` and `C <= C1` both False (the
    same pandas rule the bar-0 case relies on), which without the
    `close.isna()` half of the mask would silently drop bar `t`'s volume
    from both buckets while its 26 windows kept firing over 25 defined
    bars. It also makes bar `t+1`'s direction undefined (its `C1` is that
    NaN), so `length + 1 = 27` output bars go NaN, no bar becomes defined
    that was not, and the bars that stay defined move by float64 rounding
    only -- `max|diff| = 5.68e-14` on the 1,500-bar frame of
    `docs/measure_g191_040.py`, which is the rolling accumulation order
    changing, not the arithmetic. They are NOT bit-identical, which is why
    this asserts `rtol=1e-9` rather than equality."""
    close = _walk(200, seed=7)
    volume = _volume(200, seed=19)
    clean = g191_040(close, volume)

    holed = close.copy()
    holed.iloc[100] = np.nan
    out = g191_040(holed, volume)

    newly_nan = [int(i) for i in out.index[out.isna() & clean.notna()]]
    assert newly_nan == list(range(100, 127))  # length + 1 = 27 bars
    assert int((out.notna() & clean.isna()).sum()) == 0  # none newly defined
    unaffected = clean.notna() & out.notna()
    np.testing.assert_allclose(
        out[unaffected].to_numpy(), clean[unaffected].to_numpy(), rtol=1e-9
    )


def test_insufficient_history_returns_none():
    close = _walk(26)  # defaults need length + 1 = 27 bars
    volume = _volume(26)
    assert g191_040(close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(27)  # exactly length + 1 = 27 bars
    volume = _volume(27)
    out = g191_040(close, volume)
    assert out is not None
    assert out.iloc[:26].isna().all()
    assert pd.notna(out.iloc[26])


def test_default_name():
    close = _walk()
    volume = _volume()
    out = g191_040(close, volume)
    assert out.name == "G191_040_26"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(300)
    volume = _volume(300)
    out1 = g191_040(close, volume, length=10)
    out2 = g191_040(close, volume, length=20)
    assert out1.name != out2.name
    assert out1.name == "G191_040_10"
    assert out2.name == "G191_040_20"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_offset_shifts_the_series():
    close = _walk(200)
    volume = _volume(200)
    base = g191_040(close, volume)
    shifted = g191_040(close, volume, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_all_up_window_divides_by_zero_down_volume_to_nan():
    """First of the two causes of a zero denominator: every bar in the
    window is an up-day, so nothing lands in the `C<=C1` bucket. Pinned on
    a dedicated fixture of 5 strictly-increasing closes at `length=3`,
    giving two full windows (bars 3 and 4) with zero down-volume, because
    the measured frames do not reach the branch at the shipped
    `length=26`: `test_fires_and_is_not_constant` shows `fires == 874 ==
    900 - 26` on the 900-bar frame (no interior gap), and the longest
    consecutive up-run on the 1,500-bar frame of
    `docs/measure_g191_040.py` is 16 bars against the 26 a rally would
    need. How often it happens on real data is NOT measured here -- that
    is Gate E's.

    That the NaN comes from the shipped `inf -> NaN` replace, and not from
    an upstream warm-up gap, is shown with a mutant rather than with a
    re-typed copy of the module's own buckets: deleting the `.replace(...)`
    call leaves `+inf` at exactly those two bars."""
    close = Series([100.0, 105.0, 110.0, 115.0, 120.0])
    volume = Series([10.0, 20.0, 30.0, 40.0, 50.0])
    out = g191_040(close, volume, length=3)

    assert pd.isna(out.iloc[3])
    assert pd.isna(out.iloc[4])
    mod = _load_mutant(*INF_REPLACE_MUTANT)
    raw = mod.g191_040(close, volume, length=3)
    assert np.isinf(raw.iloc[3]) and raw.iloc[3] > 0
    assert np.isinf(raw.iloc[4]) and raw.iloc[4] > 0


def test_result_is_non_negative():
    """A ratio of two non-negative volume sums, times 100, cannot be
    negative."""
    close = _walk()
    volume = _volume()
    out = g191_040(close, volume)
    fired = out.dropna()
    assert (fired >= 0.0).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_040")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_040_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (100 * numerator / denominator).replace([np.inf, -np.inf], np.nan)",
    "result = (100 * numerator / denominator).replace([np.inf, -np.inf], np.nan).shift(-length)",  # a length-bar look-ahead
)

#: Not a causality mutant -- used by
#: `test_mask_removal_mutant_fabricates_the_bar_zero_window` above to show
#: that the shipped NaN on a window of undefined direction comes from the
#: module's own mask and not from some upstream warm-up accident.
MASK_REMOVAL_MUTANT = (
    "    up_volume = volume.where(close > close_prior, 0.0).mask(undefined, np.nan)\n"
    "    down_volume = volume.where(close <= close_prior, 0.0).mask(undefined, np.nan)",
    "    up_volume = volume.where(close > close_prior, 0.0)\n"
    "    down_volume = volume.where(close <= close_prior, 0.0)",
)

#: Also not a causality mutant -- used by the two zero-denominator tests
#: above to show that their NaN is produced by the shipped `inf -> NaN`
#: replace on the shipped buckets, not by an upstream warm-up gap.
INF_REPLACE_MUTANT = (
    "result = (100 * numerator / denominator).replace([np.inf, -np.inf], np.nan)",
    "result = (100 * numerator / denominator)",
)

OFFSETS = range(50, 900, 25)  # past the 26-bar warm-up


def _leaks(fn):
    close = _walk(900)
    volume = _volume(900)
    other_close = _walk(900, seed=41)
    other_volume = _volume(900, seed=59)
    base = fn(close, volume)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = other_close.iloc[j:].values
        pv.iloc[j:] = other_volume.iloc[j:].values
        out = fn(pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_040) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(900)
    volume = _volume(900)
    assert not mod.g191_040(close, volume).equals(g191_040(close, volume))  # live
    assert _leaks(mod.g191_040) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close = _walk()
    volume = _volume()
    base = g191_040(close, volume)
    scaled = g191_040(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    close = _walk()
    volume = _volume()
    base = g191_040(close, volume)
    scaled = g191_040(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-6


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_any_price_scale_is_bit_identical(k):
    """Only the SIGN of a one-bar price difference is read, never its
    magnitude, so even a non-power-of-two price rescale is exact (unlike
    the volume case, where the arithmetic itself, not just the ratio, is
    scale-invariant only at powers of two)."""
    close = _walk()
    volume = _volume()
    base = g191_040(close, volume)
    scaled = g191_040(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_fires_and_is_not_constant():
    close = _walk()
    volume = _volume()
    out = g191_040(close, volume)
    fires = int(out.notna().sum())
    assert fires == 874  # 900 - 26
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    volume = _volume(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": volume})
    assert "g191_040" in ta.Category["volume"]
    out = df.ta.g191_040()
    assert out.name == "G191_040_26"
    pd.testing.assert_series_equal(out, g191_040(close, volume))
    renamed = df.ta.g191_040(length=10)
    assert renamed.name == "G191_040_10"
