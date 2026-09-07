# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.fvg` -- Fair Value Gap, after the FVGDEAD repair.

⚠ READ THIS FIRST, INCLUDING THE CORRECTION. Until 2026-09-07 a zone was
appended and then, in the same loop iteration, retained only while
`close[i] <= low[i]` (bull) -- true on an exact tie only -- so a zone survived
its own formation bar ONLY when the bar closed exactly on its low.

The first write-up of this defect said the two columns were "constant zero by
construction". **That was measured on synthetic frames and is wrong on real
data.** Continuous floats never tie; real prices do -- 86,415 of 408,253 BIST
daily bars (21.17%) close exactly at their high or low -- so the old code fired
18,895 (bull) / 14,320 (bear) times there, a 4.63% / 3.51% rate against the
repaired 22.17% / 19.85%.

The defect is therefore not "dead column" but something subtler and worse to
model on: which zones survived was decided by whether a close happened to tie
the bar's extreme -- tick rounding -- rather than by the structure the column
claims to measure.

What these tests pin, in order of how much it would hurt to lose:

* **The columns fire at all** (`test_zone_columns_fire`), and fire on a
  hand-built frame where the answer is checkable by eye
  (`test_bull_zone_fires_on_a_hand_built_retrace`). This is the regression
  guard: revert the repair and both fail.
* **A zone is never live on its own formation bar**
  (`test_membership_is_never_tested_on_the_formation_bar`) -- the half of the
  repair that is easy to lose while "simplifying" the loop, and the half that
  would silently re-introduce a one-bar lookahead flavour if inverted.
* **Causality**, by mutant (`test_mutant_backdating_is_caught`): the module
  source is read, a write index is shifted one bar earlier, the mutant is
  `exec`'d in memory, and the real module must differ from it. Prefix
  truncation cannot see back-dating, which is why this is done by mutation.
* **Scale invariance** on dyadic factors, bit-identical
  (`test_dyadic_scale_invariance`). Non-dyadic factors are deliberately NOT
  asserted: these columns are strict comparisons of price levels, and on
  408,253 real bars x10/x3.7 flip 63/35 cells (0.004%/0.002%) on exact ties.
* **Formation detection is untouched by the repair**
  (`test_formation_flags_match_the_three_bar_definition`) -- `FVG_BULL` /
  `FVG_BEAR` are recomputed here straight from the definition.
* **`max_zones` is honoured** (`test_max_zones_caps_the_live_zone_set`), which
  it could not be while the zone list was always empty.

Gate numbers from `Backtesting/scripts/analysis/measure_fvg_overlap_full.py`
over 89 BIST_100 frames / 408,253 bars: Gate C 90,506 / 81,021 fires, 89/89
frames, 0 saturated; Gate D 0 differing cells of 1,633,012 on dyadic scales;
Gate E max |rho| 0.6390 (IN_FVG_BULL x FSME_CE_DIST_BULL_5, n=30,667) and
0.5962 (IN_FVG_BEAR x FSME_CE_DIST_BEAR_5, n=22,824) -- under the 0.76 ship line,
with one comparator each above 0.5; against full-coverage comparators the maxima
are 0.3680 and 0.3158. Gate E had to overwrite the pooled engine frame with this
module's output first, because at measurement time the engine still kept its own
unrepaired copy of the loop; its two research copies now delegate here.
"""
import importlib.util
import re

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta

# `pandas_ta.trend.fvg` is the FUNCTION here, not the submodule -- the package
# re-exports it under the same name. Take it from the top level and read the
# module source through `find_spec`, which resolves the file either way.
fvg = pandas_ta.fvg
COLS = ["FVG_BULL", "FVG_BEAR", "IN_FVG_BULL", "IN_FVG_BEAR"]


def _frame(n=1500, seed=3, vol=0.015):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    spread = close * np.abs(rng.normal(0, 0.008, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    high = np.maximum.reduce([close + spread, open_, close])
    low = np.minimum.reduce([close - spread, open_, close])
    return pd.Series(high), pd.Series(low), pd.Series(close)


def test_zone_columns_fire():
    """FVGDEAD regression: both membership columns fire, and neither saturates."""
    high, low, close = _frame()
    out = fvg(high, low, close)
    n = len(close)
    for col in ("IN_FVG_BULL", "IN_FVG_BEAR"):
        fires = int(out[col].sum())
        assert 0 < fires < n, f"{col} fired {fires} times in {n} bars"


def test_bull_zone_fires_on_a_hand_built_retrace():
    """A gap up, then a retrace into it -- checkable by eye, not by fixture luck.

    Bars 0-2 open a bull gap: high[0]=10, low[2]=12, so the zone is [10, 12].
    Price then walks down into the zone and back out. The bars whose close sits
    inside [10, 12] -- and only those -- must set IN_FVG_BULL.
    """
    high = pd.Series([10.0, 13.0, 14.0, 13.5, 12.5, 11.5, 11.0, 13.0])
    low = pd.Series([9.0, 11.5, 12.0, 12.2, 11.0, 10.5, 9.5, 10.0])
    close = pd.Series([9.5, 12.5, 13.5, 12.8, 11.8, 11.0, 9.8, 12.0])
    #                   -     -      -    ^gap zone [10,12] now live
    out = fvg(high, low, close)

    assert out["FVG_BULL"].iloc[2] == 1, "the 3-bar gap itself was not detected"
    assert out["IN_FVG_BULL"].iloc[2] == 0, "zone was live on its own formation bar"
    assert out["IN_FVG_BULL"].iloc[3] == 0, "close 12.8 is above the zone"
    assert out["IN_FVG_BULL"].iloc[4] == 1, "close 11.8 is inside [10, 12]"
    assert out["IN_FVG_BULL"].iloc[5] == 1, "close 11.0 is inside [10, 12]"
    # close 9.8 is below the zone floor: not inside, and the zone is now filled.
    assert out["IN_FVG_BULL"].iloc[6] == 0
    assert out["IN_FVG_BULL"].iloc[7] == 0, "a filled zone must not come back"


def test_membership_is_never_tested_on_the_formation_bar():
    """No bar may be 'inside' a zone that bar itself created.

    Every bar where a formation flag fires is checked: on that same bar the
    corresponding membership column may only be set by an OLDER zone. Asserting
    it directly is impossible from outside, so this uses the strict form -- a
    bar that forms a gap and has no older zone available cannot be inside one.
    """
    high, low, close = _frame(n=800, seed=9)
    out = fvg(high, low, close)
    first_bull = int(out["FVG_BULL"].to_numpy().argmax())
    assert out["FVG_BULL"].iloc[first_bull] == 1
    assert out["IN_FVG_BULL"].iloc[first_bull] == 0, (
        "the FIRST bull gap in the series has no older zone to be inside, so "
        "a fire here means membership was tested against the forming zone"
    )
    first_bear = int(out["FVG_BEAR"].to_numpy().argmax())
    assert out["IN_FVG_BEAR"].iloc[first_bear] == 0

    # The assertions above are all `== 0`, which the PRE-REPAIR module also
    # satisfied on a synthetic frame (it returned zeros everywhere). Pin the
    # other direction on the same series: some bar that forms a gap while an
    # OLDER zone is live must report membership, or this test proves nothing.
    formed = out["FVG_BULL"].to_numpy() == 1
    inside = out["IN_FVG_BULL"].to_numpy() == 1
    assert (formed & inside).any(), (
        "no bar both forms a bull gap and sits inside an older zone -- the "
        "test cannot distinguish 'excluded the forming zone' from 'found no "
        "zone at all'"
    )


def test_formation_flags_match_the_three_bar_definition():
    """`FVG_BULL`/`FVG_BEAR` recomputed from the definition, not from the module."""
    high, low, close = _frame(n=600, seed=4)
    out = fvg(high, low, close)
    n = len(close)
    want_bull = np.zeros(n)
    want_bear = np.zeros(n)
    for i in range(2, n):
        if low.iloc[i] > high.iloc[i - 2]:
            want_bull[i] = 1
        if high.iloc[i] < low.iloc[i - 2]:
            want_bear[i] = 1
    assert np.array_equal(out["FVG_BULL"].to_numpy(), want_bull)
    assert np.array_equal(out["FVG_BEAR"].to_numpy(), want_bear)


@pytest.mark.parametrize("scale", [2.0, 8.0, 64.0, 1024.0])
def test_dyadic_scale_invariance(scale):
    """Bit-identical under exact-in-float64 scaling.

    Non-dyadic factors are excluded on purpose: on 408,253 real bars, x10 and
    x3.7 flip 63 and 35 cells (0.004% / 0.002%) where a strict price comparison
    sits on an exact tie. That is float rounding, not a scale dependency.
    """
    high, low, close = _frame(n=900, seed=6)
    base = fvg(high, low, close)
    scaled = fvg(high * scale, low * scale, close * scale)
    for col in COLS:
        assert np.array_equal(base[col].to_numpy(), scaled[col].to_numpy()), col


def test_max_zones_caps_the_live_zone_set():
    """`max_zones` was a no-op while the zone list was always empty."""
    high, low, close = _frame(n=1200, seed=8)
    wide = fvg(high, low, close, max_zones=50)
    narrow = fvg(high, low, close, max_zones=1)
    assert not wide.equals(narrow), "max_zones changed nothing"
    for col in ("IN_FVG_BULL", "IN_FVG_BEAR"):
        assert narrow[col].sum() <= wide[col].sum(), (
            f"tracking fewer zones cannot increase {col} fires"
        )


def test_mutant_backdating_is_caught():
    """Gate B: a back-dated write must change the output.

    The module source is read, `in_fvg_bull[i] = 1` is shifted to
    `in_fvg_bull[i - 1] = 1` -- a one-bar lookahead -- and the mutant is exec'd
    in memory. If the real module's output equals the mutant's, this test suite
    cannot see back-dating at all and every causality claim here is unfounded.
    """
    spec = importlib.util.find_spec("pandas_ta.trend.fvg")
    src = open(spec.origin, encoding="utf8").read()
    mutated, count = re.subn(r"in_fvg_bull\[i\] = 1",
                             "in_fvg_bull[i - 1] = 1", src)
    assert count == 1, f"expected exactly one write site, patched {count}"

    ns = {"__name__": "fvg_mutant"}
    exec(compile(mutated, "<fvg_mutant>", "exec"), ns)

    high, low, close = _frame(n=700, seed=11)
    real = fvg(high, low, close)["IN_FVG_BULL"].to_numpy()
    mutant = ns["fvg"](high, low, close)["IN_FVG_BULL"].to_numpy()
    assert not np.array_equal(real, mutant), (
        "back-dating the membership write changed nothing -- the column is "
        "either dead again or the test is not exercising it"
    )


def test_offset_shifts_every_column():
    high, low, close = _frame(n=400, seed=12)
    base = fvg(high, low, close)
    shifted = fvg(high, low, close, offset=2)
    pd.testing.assert_frame_equal(shifted, base.shift(2), check_names=False)


def test_accessor_matches_the_standalone_call():
    high, low, close = _frame(n=400, seed=13)
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    pd.testing.assert_frame_equal(
        df.ta.fvg(), fvg(high, low, close), check_names=False
    )
