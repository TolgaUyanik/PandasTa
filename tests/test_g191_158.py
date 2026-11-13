# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.g191_158` -- Guotai Junan's (2017,
"GTJA191") alpha `#158`, per issue #81:
`((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C = (H-L)/C`, the source's own reduction,
matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:517-518`). Gate A derivation -- including
what the LITERAL spelling would cost -- is in the module docstring and
`docs/G191158Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these tests pin, in order of how much it would hurt to lose:

* THE REDUCTION IS THE WHOLE PORT. `SMA(C,15,2)` appears twice in the
  source numerator and cancels. The literal spelling is computed here in
  BOTH spellings of the GTJA `SMA` and compared to the shipped column:
  with this fork's `min_periods=n` (as `g191_109.py:101` and
  `g191_146.py:106-111` write it; no fork-wide count is claimed anywhere in
  this port, see the module docstring for why) the two are BIT-EQUAL on all
  1,486 bars both define and the
  literal form is NaN for 14 bars the shipped column fires on; with the
  PROTOTYPE's own `sma`, which omits `min_periods`, the literal form has
  no warm-up at all and is bit-equal on all 1,500 bars. So the warm-up is
  this fork's convention, not the source's, and it is not allowed to carry
  the decision. On a sigma-0.20 stress frame, where the smoother lags far
  behind the bar, some bars do move and the movement is float dust
  (measured: 50 of 1,486, max |relative diff| 5.54e-15; asserted loosely,
  since pinning `ewm`'s last bit for a spelling this module does not ship
  would break on a pandas bump).
* CAUSALITY by future-perturbation: rewrite every high/low/close bar from
  `j` onward (another synthetic walk), demand bars `[0:j]` bit-identical
  with matching NaN masks, over 37 offsets. Two mutants (`importlib` source
  read, `exec`'d in memory), each shown live (differs from the real module)
  then caught at every offset: shifting the final write index one bar into
  the future, and reading the NEXT bar's range (`high.shift(-1) -
  low.shift(-1)`) -- the same `bos` look-ahead bug class CLAUDE.md
  documents. The column has no memory at all, so a leak can only be
  written in deliberately, which is exactly what the mutants do.
* THE ZERO-RANGE FLOOR. `H == L` gives exactly `0.0`, not NaN. The
  continuous-float walk never reaches it (0 of 1,500), so the tie case is
  pinned on a TICK-ROUNDED frame where it does: 107 of 1,500 bars, and the
  column is exactly `0.0` on those 107 and only those.
* THE RELATIONSHIP TO `bw_mfi`, the fork's nearest column:
  `MFI_BW_SF_20 = ((H-L)/C) / (V/SMA(V,20))` is this column divided by
  relative volume, so on CONSTANT volume the two are bit-identical from bar
  19 (1,481 of 1,481 overlapping bars, max |diff| 0.0). Measured, because
  "nearly the same" is the kind of claim this repo writes before measuring
  it. The 0.8252 real-frame bound is the owner's stage-2 screen's, quoted
  in `docs/G191158Measured.md`, not this file's.
* CORRECTNESS: a hand-derived 6-bar example with the arithmetic written
  out, plus an independent per-bar replay (plain Python scalars, no pandas
  arithmetic) at four bars of a 900-bar frame.
* SCALE-FREE: bit-identical under price x8/x64 (power-of-two, exact in
  IEEE754), within float64 tolerance under x10/x3.7, NaN masks matching,
  and `volume` is not an argument at all.
* NO WARM-UP: bar 0 fires, `min_length = 1`, and only an EMPTY input
  returns `None`. `nunique > 1` rules out a constant column; CLAUDE.md's
  `0 < fires < n` has a vacuous upper half here (fires == n on clean
  data), which the module docstring discloses rather than dresses up.
* Wiring: `Category`, the accessor, the column name `G191_158`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.g191_158 import g191_158


def _walk(n=1500, seed=11, sigma=0.015):
    """High/low/close walk with `low <= close <= high` at every bar."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


def _tick_walk(n=1500, seed=23, price=10.0, sigma=0.0025, tick=0.01):
    """The same walk ROUNDED to a tick, so `high == low` bars exist.

    Same frame as `docs/measure_g191_158.py:_tick_walk`."""
    rng = np.random.default_rng(seed)
    close = price * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    close, high, low = (np.round(x / tick) * tick for x in (close, high, low))
    high, low = np.maximum(high, close), np.minimum(low, close)
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """No window and no warm-up, so every bar is checkable by hand:

    high  = [10, 13, 12, 16, 11, 21]
    low   = [ 8,  9,  8, 11,  7, 15]
    close = [ 9, 12,  9, 15,  8, 20]

    bar 0: (10 -  8) /  9 = 2/9  = 0.2222222222222222
    bar 1: (13 -  9) / 12 = 4/12 = 0.3333333333333333
    bar 2: (12 -  8) /  9 = 4/9  = 0.4444444444444444
    bar 3: (16 - 11) / 15 = 5/15 = 0.3333333333333333
    bar 4: (11 -  7) /  8 = 4/8  = 0.5
    bar 5: (21 - 15) / 20 = 6/20 = 0.3
    """
    high = Series([10.0, 13.0, 12.0, 16.0, 11.0, 21.0])
    low = Series([8.0, 9.0, 8.0, 11.0, 7.0, 15.0])
    close = Series([9.0, 12.0, 9.0, 15.0, 8.0, 20.0])

    out = g191_158(high, low, close)

    assert out.notna().all()  # no warm-up: bar 0 included
    assert out.iloc[0] == pytest.approx(2.0 / 9.0, abs=1e-15)
    assert out.iloc[1] == pytest.approx(4.0 / 12.0, abs=1e-15)
    assert out.iloc[2] == pytest.approx(4.0 / 9.0, abs=1e-15)
    assert out.iloc[3] == pytest.approx(5.0 / 15.0, abs=1e-15)
    assert out.iloc[4] == 0.5  # exactly
    assert out.iloc[5] == pytest.approx(6.0 / 20.0, abs=1e-15)


def test_matches_a_per_bar_scalar_replay():
    """Four bars of a 900-bar frame replayed over plain numpy scalars -- no
    pandas arithmetic, no vectorisation, bar 0 included since there is no
    warm-up to skip.

    Not an INDEPENDENT oracle, and it is not called one: for a one-line
    expression the scalar replay is the same expression retyped, so what it
    rules out is a pandas-side surprise (an alignment slip, a dtype
    promotion), not a wrong formula. Gate A's actual oracles are the 6-bar
    hand table above and the REAL screen candidate in
    `docs/measure_g191_158.py`."""
    high, low, close = _walk(900, seed=5)
    out = g191_158(high, low, close)
    hh, ll, cc = (s.to_numpy(dtype=float) for s in (high, low, close))

    for t in (0, 300, 600, 899):
        assert out.iloc[t] == (hh[t] - ll[t]) / cc[t], f"bar {t}"  # bit-exact


def test_matches_the_prototype_expression_bit_for_bit():
    """The issue's own prototype (`docs/issues/screen/ind_screen.py:517-518`)
    is one line:

        def _(o, h, l, c, v): return (h - l) / c

    This port computes the same expression, so bit-equality here is a
    TRANSCRIPTION check and nothing more -- it cannot fail unless the port
    stopped being that expression. The expression is RETYPED because
    `docs/issues/` is gitignored and a clone running this suite does not
    have it; `docs/measure_g191_158.py` closes that gap where the file IS
    present, loading the REAL candidate out of the screen's own registry
    (measured there: `max|diff| = 0.0`, 1,500 of 1,500 bars bit-equal).
    The comparison that carries actual weight is against the source's
    LITERAL spelling, below."""
    high, low, close = _walk(900, seed=29)
    out = g191_158(high, low, close)

    prototype = (high - low) / close

    assert (out.isna() == prototype.isna()).all()
    assert (out == prototype).all()


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n
    -- `ind_screen.py:57-59`, spelled as `pandas_ta/volatility/g191_109.py:101`
    spells it."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def _literal(high, low, close, n=15, m=2):
    """The source string's LITERAL spelling, before its own reduction:
    `((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C`, with the GTJA `SMA` spelled this
    FORK's way (`min_periods=n`)."""
    s = _gtja_sma(close, n, m)
    return ((high - s) - (low - s)) / close


def _literal_source_sma(high, low, close, n=15, m=2):
    """The same literal spelling with the GTJA `SMA` spelled the
    PROTOTYPE's way -- `x.ewm(alpha=m/n, adjust=False).mean()`, with NO
    `min_periods` (`ind_screen.py:57-59`). The warm-up `_literal` carries
    is this fork's convention, not the source's, so both are measured."""
    s = close.ewm(alpha=m / n, adjust=False).mean()
    return ((high - s) - (low - s)) / close


def test_the_literal_spelling_agrees_within_float_noise():
    """The port's one decision: ship the source's own reduced right-hand
    side `(H-L)/C` rather than the literal `((H-S)-(L-S))/C`.

    What the two spellings actually cost, both measured here:

    * ROUNDING: nothing, on this walk. The two forms are BIT-EQUAL on
      every bar both define -- `H`, `L` and `S` sit within a factor of 2
      of each other here (max ratio 1.096357, measured in
      `docs/measure_g191_158.py`), so by Sterbenz neither `H-S` nor `L-S`
      loses a bit. Not identical in general: see the stress frame in the
      next test.
    * WARM-UP: 14 bars, and ONLY under this fork's `min_periods=n`
      spelling of the GTJA `SMA`. The prototype's own `sma`
      (`ind_screen.py:59`) omits `min_periods`, and with it the literal
      form fires from bar 0 and is bit-equal to the shipped column on all
      1,500 bars -- asserted below, because the 14 bars are this fork's
      convention and must not be sold as the source's.
    """
    high, low, close = _walk()
    out = g191_158(high, low, close)
    lit = _literal(high, low, close)

    assert int(out.notna().sum()) == 1500
    assert int(lit.notna().sum()) == 1486
    assert lit.iloc[:14].isna().all() and lit.iloc[14:].notna().all()

    both = out.notna() & lit.notna()
    assert int(both.sum()) == 1486
    assert (out[both] == lit[both]).all()  # bit-equal, measured

    # the same spelling with the SOURCE's own smoother: no warm-up at all,
    # and bit-equal everywhere -- so the choice of spelling buys nothing
    # numerically and the reduction is justified by the source's own
    # statement of it, not by this warm-up.
    lit_src = _literal_source_sma(high, low, close)
    assert int(lit_src.notna().sum()) == 1500
    assert (out == lit_src).all()


def test_the_literal_spelling_is_not_bit_equal_in_general():
    """A frame built to break the bit-equality above, so "the cancellation
    is exact" is never claimed from one walk: sigma 0.20, where
    `SMA(C,15,2)` lags far behind the bar (max ratio between `H`/`L` and
    `S` 6.801292, past Sterbenz's factor of 2) and `H-S` / `L-S` stop being
    subtractions of two nearby numbers.

    Measured in this environment (pandas 2.3.3 / numpy 1.26.4,
    `docs/measure_g191_158.py`): 50 of the 1,486 shared bars differ, max
    |diff| 5.83e-16, max |relative diff| 5.54e-15. The assertions below are
    deliberately LOOSER than those numbers -- pinning the exact 50 would
    pin `Series.ewm`'s accumulation order for a spelling this module does
    not ship, and a pandas bump would then fail a test about
    `(high - low) / close`. What is pinned is the shape of the claim: some
    bars move, and the movement is float dust. The direction (the reduced
    form is the more accurate of the two) stays DERIVED, not measured:
    IEEE754 subtraction is correctly rounded, so `H-L` is one correct
    rounding against the literal form's three."""
    high, low, close = _walk(1500, seed=4, sigma=0.20)
    out, lit = g191_158(high, low, close), _literal(high, low, close)

    both = out.notna() & lit.notna()
    assert int(both.sum()) == 1486
    differing = int((out[both] != lit[both]).sum())
    assert 0 < differing < 1486
    diff = (out[both] - lit[both]).abs()
    assert float(diff.max()) < 1e-14
    assert float((diff / out[both].abs()).max()) < 1e-14


def test_a_zero_range_bar_is_exactly_zero():
    """`H == L` -- a limit move, a halt, an untraded day -- is this column's
    floor and must be exactly `0.0`, not NaN: `0.0` is the true range.
    Pinned on a 4-bar fixture AND on the tick-rounded frame, where 107 of
    1,500 bars tie and the column is `0.0` on those 107 and only those."""
    high = Series([10.0, 12.0, 12.0, 14.0])
    low = Series([8.0, 12.0, 10.0, 11.0])
    close = Series([9.0, 12.0, 11.0, 13.0])
    out = g191_158(high, low, close)
    assert out.iloc[1] == 0.0  # exactly, not approximately
    assert out.notna().all()

    th, tl, tc = _tick_walk()
    tout = g191_158(th, tl, tc)
    ties = th == tl
    assert int(ties.sum()) == 107
    assert ((tout == 0.0) == ties).all()
    assert int((tout != 0.0).sum()) == 1393


def test_the_column_is_non_negative_on_ohlc_consistent_data():
    """`high >= low` and `close > 0` make the column non-negative. The
    premise is asserted on the frame rather than assumed, and the column is
    then checked bar by bar on both the continuous and the tick-rounded
    walk."""
    for high, low, close in (_walk(), _tick_walk()):
        assert (high >= low).all() and (close > 0).all()  # the premise
        out = g191_158(high, low, close)
        assert (out >= 0.0).all()


def test_a_zero_close_is_not_guarded():
    """A decision on record, not a surprise: the prototype divides with a
    bare `/` (`ind_screen.py:518`) where it uses the screen's `sdiv`
    (inf -> NaN) on other candidates, and `g191_003` divides by `close`
    unguarded for the same reason -- a zero close is not an OHLC bar this
    fork models. So a zero close yields `+inf`, and a zero close on a
    zero-range bar yields NaN (`0/0`)."""
    high = Series([10.0, 12.0, 11.0])
    low = Series([8.0, 9.0, 11.0])
    close = Series([9.0, 0.0, 0.0])

    out = g191_158(high, low, close)

    assert out.iloc[0] == pytest.approx(2.0 / 9.0, abs=1e-15)
    assert np.isinf(out.iloc[1]) and out.iloc[1] > 0
    assert pd.isna(out.iloc[2])  # 0 / 0


@pytest.mark.parametrize("field", ["high", "low", "close"])
def test_a_nan_in_any_input_nans_exactly_that_bar(field):
    """The public docstring's NaN claim, measured instead of assumed: with
    no window and no recursion a NaN cannot spread, so one NaN in one input
    empties that bar and no other. Checked for each of the three inputs --
    the whole NaN surface of this column, next to the `offset` case
    (`test_offset_shifts_the_column`) and the `0/0` case
    (`test_a_zero_close_is_not_guarded`)."""
    high, low, close = _walk()
    base = g191_158(high, low, close)
    parts = {"high": high.copy(), "low": low.copy(), "close": close.copy()}
    parts[field].iloc[700] = np.nan

    poked = g191_158(**parts)

    moved = list(poked.index[poked.isna() != base.isna()])
    assert moved == [700]
    assert pd.isna(poked.iloc[700])
    assert (poked.drop(700) == base.drop(700)).all()  # nothing else moved


def test_misaligned_indexes_raise():
    high, low, close = _walk(100)
    shifted = close.copy()
    shifted.index = pd.RangeIndex(1, 101)
    with pytest.raises(ValueError, match="indexed differently"):
        g191_158(high, low, shifted)


def test_only_an_empty_input_returns_none():
    """`min_length = 1`: there is no window to warm up, so a 1-bar frame is
    enough and only an empty one is refused."""
    high, low, close = _walk(1)
    out = g191_158(high, low, close)
    assert out is not None and len(out) == 1 and out.notna().all()

    empty = Series([], dtype="float64")
    assert g191_158(empty, empty, empty) is None


def test_default_name():
    high, low, close = _walk()
    assert g191_158(high, low, close).name == "G191_158"


def test_offset_shifts_the_column():
    """The only tunable the module takes, pinned in BOTH directions.
    `offset=1` moves the column forward one bar and NaNs bar 0; `offset=-1`
    moves it BACKWARD, NaNs the last bar, and makes the column read the
    next bar's range -- the one non-causal door this module has, open only
    because the caller asked. Stated in the public docstring's Returns, so
    both halves are asserted here rather than one."""
    high, low, close = _walk(200)
    base = g191_158(high, low, close)

    forward = g191_158(high, low, close, offset=1)
    assert pd.isna(forward.iloc[0])
    assert (forward.iloc[1:].to_numpy() == base.iloc[:-1].to_numpy()).all()

    backward = g191_158(high, low, close, offset=-1)
    assert pd.isna(backward.iloc[-1])
    assert (backward.iloc[:-1].to_numpy() == base.iloc[1:].to_numpy()).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.g191_158")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_158_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_DIV = "result = (high - low) / close"
WRITE_SHIFT_MUTANT = (
    SHIPPED_DIV,
    "result = ((high - low) / close).shift(-1)",
)
FUTURE_RANGE_MUTANT = (
    SHIPPED_DIV,
    # the `bos` look-ahead bug class: tomorrow's range on today's bar
    "result = (high.shift(-1) - low.shift(-1)) / close",
)

OFFSETS = range(50, 1500, 40)


def _leaks(fn):
    high, low, close = _walk(1500)
    other_h, other_l, other_c = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
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
    assert _leaks(g191_158) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close = _walk(1500)
    assert not mod.g191_158(high, low, close).equals(g191_158(high, low, close))  # live
    assert _leaks(mod.g191_158) == len(list(OFFSETS))  # caught, every offset


def test_future_range_mutant_is_caught():
    mod = _load_mutant(*FUTURE_RANGE_MUTANT)
    high, low, close = _walk(1500)
    assert not mod.g191_158(high, low, close).equals(g191_158(high, low, close))  # live
    assert _leaks(mod.g191_158) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_every_bar_and_is_not_constant():
    """No warm-up, so `fires == n` and CLAUDE.md's `0 < fires < n` is
    vacuous in its upper half here (disclosed in the module docstring, not
    worked around). What that clause is for -- a constant or all-NaN
    column -- is pinned by the distinct-value count instead: 1,500 of
    1,500 bars fire, all 1,500 values distinct on the continuous walk, and
    458 distinct on the tick-rounded one, where the tick quantises them."""
    high, low, close = _walk()
    out = g191_158(high, low, close)
    assert int(out.notna().sum()) == len(out) == 1500
    assert int(out.dropna().nunique()) == 1500
    assert float(out.min()) > 0.0  # no zero-range bar on continuous floats

    th, tl, tc = _tick_walk()
    tout = g191_158(th, tl, tc)
    assert int(tout.notna().sum()) == 1500
    assert int(tout.dropna().nunique()) == 458


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close = _walk()
    base = g191_158(high, low, close)
    scaled = g191_158(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base == scaled).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close = _walk()
    base = g191_158(high, low, close)
    scaled = g191_158(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-14


def test_volume_scale_cannot_move_the_column_because_volume_is_not_read():
    """Structural, and checked through the ACCESSOR rather than argued: the
    module takes no `volume` argument, and `df.ta.g191_158()` on a frame
    whose volume is multiplied by 8 returns the bit-identical column. The
    `volume` column still has to be present for the frame to be an OHLCV
    frame, which is why this is worth a test at all."""
    high, low, close = _walk(400)
    assert "volume" not in g191_158.__code__.co_varnames[:g191_158.__code__.co_argcount]
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                       "volume": Series(np.full(400, 1e6), index=close.index)})
    x8 = df.copy()
    x8["volume"] *= 8.0
    assert (df.ta.g191_158() == x8.ta.g191_158()).all()


# ---------------------------------------------------------- non-redundancy


def test_bw_mfi_is_this_column_divided_by_relative_volume():
    """The fork's nearest column, measured instead of described.
    `bw_mfi`'s shipped default is
    `MFI_BW_SF_20 = ((high-low)/close) / (volume/SMA(volume,20))`
    (`pandas_ta/volume/bw_mfi.py:47`) -- this column divided by relative
    volume. On CONSTANT volume that factor is exactly `1.0` once its own
    20-bar average exists, so the two columns are bit-identical from bar
    19: 1,481 of 1,481 overlapping bars here, `max|diff| = 0.0`.

    This is the premise behind the disclosure in
    `docs/G191158Measured.md`; what keeps the two apart on real data is
    volume NOT being constant (the owner's stage-2 screen measured the
    candidate's highest fork overlap at |rho| 0.8252, against `har_park`,
    over 12 BIST frames), and the varying-volume synthetic number
    (rho 0.6922) is in `docs/measure_g191_158.py`."""
    high, low, close = _walk()
    own = g191_158(high, low, close)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                       "volume": Series(np.full(len(close), 1e6), index=close.index)})
    bw = df.ta.bw_mfi()

    assert int(bw.notna().idxmax()) == 19
    m = own.notna() & bw.notna()
    assert int(m.sum()) == 1481
    assert (own[m] == bw[m]).all()  # bit-identical, not "close"


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _walk(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close})
    assert "g191_158" in ta.Category["volatility"]
    out = df.ta.g191_158()
    assert out.name == "G191_158"
    pd.testing.assert_series_equal(out, g191_158(high, low, close))
    # the one kwarg forwarded under its own name -- the "supertrend failure
    # mode" (CLAUDE.md) `hasattr` cannot see.
    shifted = df.ta.g191_158(offset=2)
    assert shifted.iloc[:2].isna().all()
    assert (shifted.iloc[2:].to_numpy() == out.iloc[:-2].to_numpy()).all()
