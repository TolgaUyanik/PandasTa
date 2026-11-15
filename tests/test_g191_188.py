# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.g191_188` -- Guotai Junan's (2017,
"GTJA191") alpha `#188`, per issue #83:
`(H-L-SMA(H-L,11,2))/SMA(H-L,11,2)*100`. `SMA(A,n,m)` is GTJA's own
recursive EMA (`alpha = m/n`, so `2/11` here), not this fork's plain
simple-moving-average `sma`. The column is today's range as a percent
deviation from an EMA of the range. No `conv` field in the issue's own
`candidates.csv` row (`docs/issues/screen/candidates.csv:65`) -- a ratio of
a quantity to its own EMA is scale-free with no extra division needed. Gate
A derivation is in the module docstring and `docs/G191188Measured.md`. Gate
E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 37 offsets past the 11-bar warm-up. Three
  mutants (`importlib` source read, `exec`'d in memory), each shown live
  (differs from the real module) then caught at every one of the 37
  offsets: shifting the final write index `smooth_length=11` bars into the
  future; building the range from `high.shift(-1) - low.shift(-1)` (one bar
  of look-ahead folded in before the smoothing -- the `bos` look-ahead bug
  class); and reading the smoothed range one bar ahead (`e.shift(-1)`, so
  both the subtraction and the division see tomorrow's EMA). Measured: the
  real module 0 of 37, each mutant 37 of 37.
* CORRECTNESS: an 8-bar hand-derived example at `smooth_length=3,
  smooth_weight=1`, an independent per-bar replay at the shipped defaults
  using plain Python scalars (no `.ewm()`, no `.replace()`; agrees to
  1.243e-14), and the REJECTED reading of the source string's `*100`
  precedence measured rather than dismissed (it is this column divided by
  exactly 10,000: Spearman 1.0, 0 of 1,490 bars bit-equal). `python
  docs/measure_g191_188.py` prints all of it, including the port being
  bit-equal to the owner's own (gitignored) screen candidate on all 1,490
  bars they share.
* THE SMOOTHER'S SPELLING, in the suite rather than only in a script CI
  never runs: `min_periods=smooth_length` is this FORK's convention and the
  prototype omits it, so the port is pinned bit-equal to the
  no-`min_periods` spelling on all 1,490 bars it fires and NaN on exactly
  the 10 the source form defines (1,500 vs 1,490 fires). That also pins
  `adjust=False`: pandas' default `adjust=True` would move every bar, not
  only the masked head.
* SCALE-FREE: `H - L` is linear in a positive price rescale and the GTJA
  `SMA` is a linear recursion in a positive scalar multiple of its input,
  so numerator and denominator scale by the SAME factor and the ratio
  cancels it exactly, with no extra division needed. Measured
  bit-identical under PRICE x8/x64 (power-of-two, exact in IEEE754) and
  within 1.471e-12 under x10/x3.7, NaN masks matching and 0 sign changes.
  Plus `0 < fires < n` (1,490 of 1,500), `nunique > 1` (1,490), and the
  `-100` floor.
* EDGE CASES: a dead bar (`H == L`) returns exactly `-100.0` and empties
  nothing; an all-dead frame fires on 0 of 1,500 bars (`0/0` is NaN
  directly, so the `inf` replacement is not what carries that case); the
  three `smooth_weight` alpha bands, including `smooth_length <= m <
  smooth_length + 1`, which truncates to `alpha = 1.0`, raises nothing, and
  collapses the column to a constant `0.0`; and `smooth_length`'s own three
  unguarded bands (`0 < n < 1` truncates to `0` and raises
  `ZeroDivisionError` in `m / n`; `n < m` gives `alpha > 1` and pandas'
  `ewm` raises `ValueError`; `n == m` gives `alpha = 1.0`, which pandas
  ACCEPTS and which collapses the column to a constant `0.0` without
  raising -- the band the module docstring had wrong until round 4 of
  review).
* Wiring: `Category`, the accessor, the column name `G191_188_11_2`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.g191_188 import g191_188


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    return (Series(high), Series(low))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """high/low over 8 bars (no H==L ties), smooth_length=3,
    smooth_weight=1 (alpha=1/3). min_length = smooth_length = 3, so bars
    0..1 are NaN and bars 2..7 are the first six valid values.

    r = H - L = [4.0, 4.0, 3.0, 6.0, 4.0, 7.0, 4.0, 8.0]
    GTJA SMA(r, 3, 1) = r.ewm(alpha=1/3, adjust=False), masked to NaN until
    bar 2 (min_periods=3):
        e[2..7] = [3.666666666666667, 4.444444444444445, 4.296296296296296,
                   5.19753086419753, 4.79835390946502, 5.86556927297668]
    result[t] = 100 * (r[t] - e[t]) / e[t]:
        result[2..7] = [-18.181818181818187, 34.99999999999999,
                        -6.896551724137921, 34.679334916864626,
                        -16.638078902229843, 36.38914873713752]

    Independently derived and printed by docs/measure_g191_188.py, matching
    the module's float64 output exactly.
    """
    high = Series([12.0, 14.0, 11.0, 18.0, 10.0, 22.0, 9.0, 26.0])
    low = Series([8.0, 10.0, 8.0, 12.0, 6.0, 15.0, 5.0, 18.0])
    out = g191_188(high, low, smooth_length=3, smooth_weight=1)

    assert out.iloc[:2].isna().all()
    expected = {
        2: -18.181818181818187,
        3: 34.99999999999999,
        4: -6.896551724137921,
        5: 34.679334916864626,
        6: -16.638078902229843,
        7: 36.38914873713752,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (smooth_length=11,
    smooth_weight=2) against a per-bar replay in plain Python scalars --
    no `.ewm()`, no `.replace()`, nothing the module itself calls. The
    GTJA recursion is seeded the way `adjust=False` seeds it: `Y` at the
    first valid input IS that input. Measured agreement: 1.243e-14 at the
    worst of the three bars (`docs/measure_g191_188.py`)."""
    high, low = _walk(900, seed=3)
    out = g191_188(high, low)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    alpha = 2 / 11

    def _loop(t):
        y = None
        seen = 0
        for i in range(t + 1):
            ri = h[i] - l[i]
            y = ri if y is None else alpha * ri + (1 - alpha) * y
            seen += 1
        if seen < 11:
            return float("nan")
        rt = h[t] - l[t]
        return 100 * ((rt - y) / y)

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(_loop(t), rel=1e-12), f"bar {t}"


def test_the_rejected_precedence_reading_is_a_constant_rescale():
    """Gate A's one disclosed reading: the source string's tail
    `/SMA(H-L,11,2)*100` could be parsed as `/(SMA(H-L,11,2)*100)`. The
    prototype divides by `e` alone and multiplies the finished ratio
    (`ind_screen.py:563`), which is what ships. The rejected reading is
    measured rather than dismissed: it is this column divided by exactly
    10,000, so a bar can only be bit-equal where it is exactly `0.0` (and
    on this frame none is), yet Spearman is 1.0 and no bar changes sign --
    a pure constant rescale, visible only in the magnitude."""
    high, low = _walk()
    out = g191_188(high, low)
    r = high - low
    e = r.ewm(alpha=2 / 11, adjust=False, min_periods=11).mean()
    rejected = ((r - e) / (e * 100)).replace([np.inf, -np.inf], np.nan)

    m = out.notna() & rejected.notna()
    assert int(m.sum()) == 1490
    # Bit-equal only at an exact zero, of which this frame has none.
    assert int((out[m] == rejected[m]).sum()) == int((out[m] == 0.0).sum())
    assert out[m].corr(rejected[m], method="spearman") == pytest.approx(1.0)
    ratio = out[m] / rejected[m]
    assert float(ratio.min()) == pytest.approx(10000.0, rel=1e-12)
    assert float(ratio.max()) == pytest.approx(10000.0, rel=1e-12)
    assert int(((out[m] > 0) != (rejected[m] > 0)).sum()) == 0


def test_the_forks_min_periods_only_masks_bars_it_does_not_change_them():
    """`min_periods=n` on the GTJA `SMA` is this FORK's convention
    (`pandas_ta/volatility/g191_109.py:101`), not the source's: the
    prototype's own `sma` omits it (`ind_screen.py:57-59`). This is the
    suite's copy of the claim the module docstring makes and
    `docs/measure_g191_188.py` prints -- the script CI never runs. Measured
    on the 1,500-bar walk, the difference is exactly 10 masked bars and
    nothing else: 1,490 non-NaN with it, 1,500 without, bit-equal on all
    1,490. It also pins `adjust=False`: a drift to pandas' default
    `adjust=True` would change every bar, not only the masked head."""
    high, low = _walk()
    out = g191_188(high, low)
    r = high - low
    e_source = r.ewm(alpha=2 / 11, adjust=False).mean()
    source_spelled = 100 * ((r - e_source) / e_source).replace(
        [np.inf, -np.inf], np.nan)

    assert int(out.notna().sum()) == 1490
    assert int(source_spelled.notna().sum()) == 1500
    assert int(source_spelled.notna().idxmax()) == 0   # the source fires at bar 0
    assert int(out.notna().idxmax()) == 10             # + 10 masked bars
    shared = out.notna()
    assert (out[shared] == source_spelled[shared]).all()


def test_insufficient_history_returns_none():
    high, low = _walk(10)  # defaults need smooth_length = 11 bars
    assert g191_188(high, low) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low = _walk(11)  # exactly smooth_length = 11 bars
    out = g191_188(high, low)
    assert out is not None
    assert out.iloc[:10].isna().all()
    assert pd.notna(out.iloc[10])


def test_default_name():
    high, low = _walk()
    out = g191_188(high, low)
    assert out.name == "G191_188_11_2"


def test_distinct_weights_produce_distinct_names_and_values():
    """The name contract, nothing more: two distinct INTEGER weights must
    produce two distinct column names (the name is the only thing mined
    strategy rules in the parent repo match on, CLAUDE.md "Naming is API")
    and, since the weight changes the GTJA `alpha = m/n`, two distinct
    Series of values. No claim is made that this pair ever regressed -- the
    1-vs-3 comparison "never collided either way"
    (`tests/test_g191_146.py:205`); the regression lives in the fractional
    test below."""
    high, low = _walk(300)
    out1 = g191_188(high, low, smooth_length=11, smooth_weight=1)
    out3 = g191_188(high, low, smooth_length=11, smooth_weight=3)
    assert out1.name != out3.name
    assert out1.name == "G191_188_11_1"
    assert out3.name == "G191_188_11_3"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """The regression `g191_146`'s round 1 actually shipped
    (`tests/test_g191_146.py:193-205`): weights stored as `float` for the
    `ewm()` math but truncated to `int` only at the name f-string, so
    `2.1` and `2.4` computed DIFFERENT Series under the IDENTICAL name.
    Here `smooth_weight` is coerced to `int` at validation time, before any
    math runs, so two weights that truncate to the same integer are the
    same parameter all the way through: same name AND bit-identical
    values."""
    high, low = _walk(300)
    out_21 = g191_188(high, low, smooth_weight=2.1)
    out_24 = g191_188(high, low, smooth_weight=2.4)
    assert out_21.name == out_24.name == "G191_188_11_2"
    pd.testing.assert_series_equal(out_21, out_24)


@pytest.mark.parametrize("m", [0.5, 12, 20])
def test_a_weight_that_leaves_alpha_outside_zero_one_raises(m):
    """`int(0.5) == 0` gives `alpha = 0`, and `m >= smooth_length + 1`
    gives `alpha > 1`; pandas' own `ewm` rejects both. Pinned so the
    public docstring's parameter note stays true."""
    high, low = _walk(100)
    with pytest.raises(ValueError):
        g191_188(high, low, smooth_weight=m)


@pytest.mark.parametrize("n,exc", [(0.5, ZeroDivisionError), (1, ValueError)])
def test_a_length_that_breaks_the_alpha_raises(n, exc):
    """`smooth_length` is cast the same way as the weight and has its own
    off-nominal bands, none of them guarded. Two of the three RAISE: `0.5`
    truncates to `0`, so `_gtja_sma`'s `m / n` raises `ZeroDivisionError`
    before pandas is reached; `1` at the default weight 2 gives `alpha = 2`,
    which pandas' `ewm` rejects with `ValueError`. The third band
    (`n == m`, `alpha = 1.0`) does NOT raise and is pinned by the test
    below. Pinned so the public docstring's parameter note stays true."""
    high, low = _walk(100)
    with pytest.raises(exc):
        g191_188(high, low, smooth_length=n)


def test_a_length_equal_to_the_weight_collapses_the_column_to_zero():
    """The band the docstring got WRONG until round 4 of review: `n == m`
    gives `alpha = m/n = 1.0` exactly, which pandas ACCEPTS. So
    `smooth_length=2, smooth_weight=2` raises nothing, the smoother returns
    its own input, `e == r`, and the column is a CONSTANT `0.0` wherever it
    fires -- which CLAUDE.md's ML contract says is not a feature. The
    docstring previously claimed `n <= m` raises; it does not at `n == m`."""
    high, low = _walk(300)
    out = g191_188(high, low, smooth_length=2, smooth_weight=2)
    assert out.name == "G191_188_2_2"
    d = out.dropna()
    assert len(d) > 0
    assert (d == 0.0).all()
    assert d.nunique() == 1


def test_a_weight_of_alpha_one_collapses_the_column_to_zero():
    """The band the docstring would get wrong if nobody ran it:
    `smooth_length <= m < smooth_length + 1` truncates to `alpha = 1.0`,
    which pandas ACCEPTS. The smoother then returns its own input, so
    `e == r`, the numerator is identically zero, and the column is a
    CONSTANT `0.0` wherever it fires -- nothing raises, and a constant
    column is not a feature."""
    high, low = _walk(300)
    out = g191_188(high, low, smooth_weight=11)
    assert out.name == "G191_188_11_11"
    d = out.dropna()
    assert len(d) > 0
    assert (d == 0.0).all()
    assert d.nunique() == 1


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.g191_188")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_188_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "    result = 100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)",
    "    result = (100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)).shift(-smooth_length)",
)
LOOKAHEAD_RANGE_MUTANT = (
    "    r = high - low",
    "    r = high.shift(-1) - low.shift(-1)",  # the `bos` look-ahead bug class
)
LOOKAHEAD_EMA_MUTANT = (
    "    e = _gtja_sma(r, smooth_length, smooth_weight)",
    "    e = _gtja_sma(r, smooth_length, smooth_weight).shift(-1)",
)

OFFSETS = range(50, 1500, 40)  # past the 11-bar warm-up


def _leaks(fn):
    high, low = _walk(1500)
    other_h, other_l = _walk(1500, seed=97)
    base = fn(high, low)
    hits = 0
    for j in OFFSETS:
        ph, pl = high.copy(), low.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        out = fn(ph, pl)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_188) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low = _walk(1500)
    assert not mod.g191_188(high, low).equals(g191_188(high, low))  # live
    assert _leaks(mod.g191_188) == len(list(OFFSETS))  # caught, every offset


def test_lookahead_range_mutant_is_caught():
    mod = _load_mutant(*LOOKAHEAD_RANGE_MUTANT)
    high, low = _walk(1500)
    assert not mod.g191_188(high, low).equals(g191_188(high, low))  # live
    assert _leaks(mod.g191_188) == len(list(OFFSETS))  # caught, every offset


def test_lookahead_ema_mutant_is_caught():
    mod = _load_mutant(*LOOKAHEAD_EMA_MUTANT)
    high, low = _walk(1500)
    assert not mod.g191_188(high, low).equals(g191_188(high, low))  # live
    assert _leaks(mod.g191_188) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low = _walk()
    base = g191_188(high, low)
    scaled = g191_188(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low = _walk()
    base = g191_188(high, low)
    scaled = g191_188(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] - scaled[m]).abs().max() < 1e-9
    assert int(((base[m] > 0) != (scaled[m] > 0)).sum()) == 0


def test_fires_and_is_not_constant():
    high, low = _walk()
    out = g191_188(high, low)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


def test_floored_at_minus_one_hundred():
    """`r >= 0` for valid OHLC data and the EMA of a non-negative series is
    non-negative, so `(r - e)/e >= -1` and the column cannot go below
    `-100`. On the synthetic walk no bar even reaches the floor (no `H == L`
    ties); the floor itself is pinned by the dead-bar test below."""
    high, low = _walk()
    d = g191_188(high, low).dropna()
    assert (d >= -100.0).all()
    assert (d > -100.0).all()


# ------------------------------------------------------------ edge cases


def test_a_dead_bar_returns_exactly_minus_one_hundred():
    """`H == L` makes `r = 0`, which is a valid float and not a NaN, so the
    column returns its floor rather than emptying. Nothing else moves: the
    fire count is unchanged from the untouched frame."""
    high, low = _walk()
    base_fires = int(g191_188(high, low).notna().sum())
    dh, dl = high.copy(), low.copy()
    dl.iloc[700] = dh.iloc[700]
    out = g191_188(dh, dl)
    assert out.iloc[700] == -100.0
    assert int(out.notna().sum()) == base_fires


def test_an_all_dead_frame_is_entirely_nan():
    """When every bar has `H == L` the EMA is `0` too, so the division is
    `0/0` -- NaN directly, not an `inf` the `.replace()` catches. The
    column fires nowhere, which is the honest answer for a frame with no
    range in it."""
    high, _ = _walk()
    out = g191_188(high, high.copy())
    assert int(out.notna().sum()) == 0


def test_a_nan_in_high_empties_one_bar_and_displaces_the_level():
    """pandas' `ewm` SKIPS a NaN input (carrying its previous value
    forward) rather than emptying its output, so only the bar whose own
    `r` is NaN goes NaN while the EMA's level is displaced afterwards.
    Measured locally: 1 bar emptied, 167 displaced starting at bar 701,
    first valid bar still 10 (`docs/measure_g191_188.py`). Where the
    displacement falls below float64 resolution is platform float detail
    (the lesson of `g191_022`'s CI failure, commit `a56d873`), so only the
    emptied bar, the displacement's start and a lower bound are pinned."""
    high, low = _walk()
    base = g191_188(high, low)
    nh = high.copy()
    nh.iloc[700] = np.nan
    out = g191_188(nh, low)
    assert int((base.notna() & out.isna()).sum()) == 1
    assert out.isna().iloc[700]
    both = base.notna() & out.notna()
    moved = base.index[both & (base != out)]
    assert len(moved) >= 100
    assert int(moved[0]) == 701
    assert int(out.notna().idxmax()) == 10
    # Nothing before the poked bar moves at all.
    assert (base.iloc[:700] == out.iloc[:700])[base.iloc[:700].notna()].all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low = _walk(400)
    df = pd.DataFrame({"open": high, "high": high, "low": low, "close": high})
    assert "g191_188" in ta.Category["volatility"]
    out = df.ta.g191_188()
    assert out.name == "G191_188_11_2"
    pd.testing.assert_series_equal(out, g191_188(high, low))
    # both tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_188(smooth_length=5, smooth_weight=1)
    assert renamed.name == "G191_188_5_1"
