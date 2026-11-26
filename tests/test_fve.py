# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.fve` -- Markos Katsanos's (TASC, April 2003)
Finite Volume Elements with the owner's fixed 0.3% cutoff, per issue #260:
`100 * sum_22(VE) / sum_22(volume)`, `VE = +-volume` when
`MF = (close - (high+low)/2) + diff(HLC3)` clears `0.003 * close`, else 0.
The Gate A derivation is in the module docstring and `docs/FveMeasured.md`.
Gate E is the launcher's run, not this session's; until it is recorded,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports this indicator as owed, which is expected.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite high, low, close AND volume from
  bar `j` onward, demand bars `[0:j]` bit-identical with matching NaN masks,
  over offsets past the 22-bar warm-up. One mutant (`importlib` source read,
  `exec`'d in memory, the final write shifted ONE bar into the future, the
  smallest look-ahead there is) is shown live, then caught at every offset.
  `docs/measure_fve.py` measures the same pair on 1,500 bars: real module
  **0 of 35** offsets leak, mutant **35 of 35**.
* CORRECTNESS: a 5-bar hand-derived example at `length=3`, the arithmetic
  written out in the test docstring; bar 3 has `MF = 0`, inside the band, so
  its `VE` is 0. Against an independent per-bar loop of the issue's
  definition: bit-identical on all 1,478 defined bars of the script's
  1,500-bar frame (`max|diff| = 0`), and here asserted on every defined bar
  of the 900-bar frame. The band's strict inequality is pinned on its own.
* SCALE-FREE: prices (high, low, close together), volume and both at x8/x64
  bit-identical; x10/x3.7 within tolerance, NaN masks matching. Measured on
  the script's frame, x10 and x3.7 were bit-identical too (`max|diff| = 0`,
  no `VE` sign flipped), but nothing guarantees that, so the test asserts
  `< 1e-9`. Plus `0 < fires < n` and `nunique > 1` (1,478 fires of 1,500,
  1,478 distinct values, 718 positive / 760 negative on the script's frame;
  878 of 900 here).
* ZERO VOLUME: an all-zero 22-bar window makes both sums 0 and the column
  NaN, never `inf`. Twenty-two zero bars at 700..721 blank exactly **1**
  bar, 721, the only bar whose window is entirely zero (measured on the
  script's frame and on this file's 900-bar frame).
* Wiring: `Category`, the accessor, the column name `FVE_22`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.fve import fve


def _frame(n=900, seed=11, sigma=0.015):
    """Tick-rounded (0.01) OHLC, about 20% of closes pinned to the high or
    low (exact ties), volume rounded to 100 shares. Same as docs/measure_fve.py."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * np.exp(np.abs(rng.normal(0.0, 0.006, n)))
    low = close * np.exp(-np.abs(rng.normal(0.0, 0.006, n)))
    pin = rng.random(n)
    close = np.where(pin < 0.1, high, np.where(pin < 0.2, low, close))
    high, low, close = (np.round(x, 2) for x in (high, low, close))
    volume = np.round(rng.uniform(1e4, 1e6, n), -2)
    return Series(high), Series(low), Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def test_hand_derived_five_bars():
    """length=3, cutoff=0.003.
    high  = [11, 12, 12, 12, 13], low = [9, 10, 10, 10, 11]
    close = [10, 11.8, 11, 11, 12.5], volume = [100, 200, 300, 400, 500]

    TP = [10, 33.8/3, 11, 11, 36.5/3]
    bar 1: MF = (11.8 - 11) + (33.8/3 - 10) = 0.8 + 3.8/3 > 0.0354 -> VE = +200
    bar 2: MF = (11 - 11) + (11 - 33.8/3) = -0.8/3 < -0.033      -> VE = -300
    bar 3: MF = 0 + 0 = 0, inside the band                       -> VE = 0
    bar 4: MF = (12.5 - 12) + (36.5/3 - 11) = 0.5 + 3.5/3 > 0.0375 -> VE = +500
    bar 0's MF is NaN (no TP_{-1}), so bars 0..2 are NaN.
    bar 3: 100 * (200 - 300 + 0) / 900 = -100/9
    bar 4: 100 * (-300 + 0 + 500) / 1200 = 50/3
    Derived by hand, not by re-running the module."""
    high = Series([11.0, 12.0, 12.0, 12.0, 13.0])
    low = Series([9.0, 10.0, 10.0, 10.0, 11.0])
    close = Series([10.0, 11.8, 11.0, 11.0, 12.5])
    volume = Series([100.0, 200.0, 300.0, 400.0, 500.0])
    out = fve(high, low, close, volume, length=3)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(-100 / 9, abs=1e-12)
    assert out.iloc[4] == pytest.approx(50 / 3, abs=1e-12)


def test_band_is_strict_on_both_sides():
    """MF exactly at +-cutoff*close is a 0, as the issue's 'else 0' reads.
    Flat bars (high == low == close) make MF = TP change = close change;
    close 100 -> 101 -> 100 gives MF = +1, -1 against a band of 0.01 * close
    = 1.01 / 1.00: bar 1 (MF 1 < 1.01) is 0, bar 2 (MF -1 == -1.00) is 0."""
    close = Series([100.0, 101.0, 100.0])
    vol = Series([10.0, 20.0, 30.0])
    out = fve(close, close, close, vol, length=2, cutoff=0.01)
    assert out.iloc[2] == 0.0
    # cutoff 0.0099: bar 1 (1 > 0.9999) is +20, bar 2 (-1 < -0.99) is -30;
    # 100 * (20 - 30) / 50 = -20.
    assert fve(close, close, close, vol, length=2, cutoff=0.0099).iloc[2] == pytest.approx(-20.0)


def _loop(h, l, c, v, t, length=22, cutoff=0.003):
    num = den = 0.0
    for i in range(t - length + 1, t + 1):
        tp, tp1 = (h[i] + l[i] + c[i]) / 3, (h[i - 1] + l[i - 1] + c[i - 1]) / 3
        mf = (c[i] - (h[i] + l[i]) / 2) + (tp - tp1)
        num += v[i] if mf > cutoff * c[i] else (-v[i] if mf < -cutoff * c[i] else 0.0)
        den += v[i]
    return 100 * num / den


def test_matches_an_independent_loop_on_every_bar():
    h, l, c, v = _frame()
    out = fve(h, l, c, v)
    assert out.iloc[:22].isna().all()
    arrs = [x.to_numpy() for x in (h, l, c, v)]
    for t in range(22, len(out)):
        assert out.iloc[t] == pytest.approx(_loop(*arrs, t), rel=0, abs=1e-9), f"bar {t}"


def test_all_zero_volume_window_is_nan_not_inf():
    h, l, c, v = _frame()
    clean = fve(h, l, c, v)
    zv = v.copy()
    zv.iloc[700:722] = 0.0
    out = fve(h, l, c, zv)
    newly_nan = [int(i) for i in out.index[out.isna() & clean.notna()]]
    assert newly_nan == [721]
    assert not np.isinf(out.to_numpy(dtype=float)).any()


def test_insufficient_history_returns_none():
    assert fve(*_frame(22)) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    out = fve(*_frame(23))
    assert out.iloc[:22].isna().all()
    assert pd.notna(out.iloc[22])


def test_names_encode_parameters():
    data = _frame(200)
    assert fve(*data).name == "FVE_22"
    assert fve(*data, length=10).name == "FVE_10"
    assert fve(*data, cutoff=0.005).name == "FVE_22_0.005"
    # cutoff=0 is the no-dead-zone variant, not a silent fallback to 0.003.
    no_band = fve(*data, cutoff=0)
    assert no_band.name == "FVE_22_0.0"
    assert not no_band.equals(fve(*data))


def test_offset_shifts_the_series():
    data = _frame(200)
    pd.testing.assert_series_equal(fve(*data, offset=1), fve(*data).shift(1), check_names=False)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.fve")
_SHIPPED_WRITE = "    result = 100 * vesum / vsum.where(vsum != 0)\n"
WRITE_SHIFT_MUTANT = (_SHIPPED_WRITE,
                      "    result = (100 * vesum / vsum.where(vsum != 0)).shift(-1)\n")
OFFSETS = range(40, 900, 25)  # past the 22-bar warm-up


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_fve_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    base_in = _frame()
    other = _frame(seed=59)
    base = fn(*base_in)
    hits = 0
    for j in OFFSETS:
        pert = [x.copy() for x in base_in]
        for dst, src in zip(pert, other):
            dst.iloc[j:] = src.iloc[j:].values
        out = fn(*pert)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(fve) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    data = _frame()
    assert not mod.fve(*data).equals(fve(*data))  # live
    assert _leaks(mod.fve) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


def _scaled(k, what):
    h, l, c, v = _frame()
    hs, ls, cs = (x * k if what in ("price", "both") else x for x in (h, l, c))
    vs = v * k if what in ("volume", "both") else v
    return fve(h, l, c, v), fve(hs, ls, cs, vs)


@pytest.mark.parametrize("what", ["price", "volume", "both"])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k, what):
    base, scaled = _scaled(k, what)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("what", ["price", "volume", "both"])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k, what):
    base, scaled = _scaled(k, what)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = fve(*_frame())
    fires = int(out.notna().sum())
    assert fires == 878  # 900 - 22
    assert 0 < fires < len(out)
    d = out.dropna()
    assert d.nunique() > 1
    assert (d > 0).any() and (d < 0).any()
    assert d.abs().max() <= 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    h, l, c, v = _frame(200)
    df = pd.DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": v})
    assert "fve" in ta.Category["volume"]
    out = df.ta.fve()
    assert out.name == "FVE_22"
    pd.testing.assert_series_equal(out, fve(h, l, c, v))
    assert df.ta.fve(length=10, cutoff=0.005).name == "FVE_10_0.005"
