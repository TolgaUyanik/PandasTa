# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.vpci` -- Buff Dormeier's (TASC, July 2007)
Volume Price Confirmation Indicator, price-normalised, per issue #264:
`(VWMA_20 - SMA_20) / SMA_20 * (VWMA_5 / SMA_5) * (VMA_5 / VMA_20)`. The
Gate A derivation is in the module docstring and `docs/VpciMeasured.md`.
Gate E is the launcher's run, not this session's; until it is recorded,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports this indicator as owed, which is expected.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite close AND volume from bar `j`
  onward, demand bars `[0:j]` bit-identical with matching NaN masks, over
  offsets past the 19-bar warm-up. One mutant (`importlib` source read,
  `exec`'d in memory, the final write shifted ONE bar into the future, the
  smallest look-ahead there is) is shown live, then caught at every offset.
  `docs/measure_vpci.py` measures the same pair on 1,500 bars: real module
  **0 of 35** offsets leak, mutant **35 of 35**.
* CORRECTNESS: a 5-bar hand-derived example at `short=2, long=3`, the
  arithmetic written out in the test docstring (bar 2 is an exact tie,
  `VWMA_3 == SMA_3`, so the column is exactly 0 there). Against the issue's
  formula rebuilt from this package's own `vwma` and `sma` modules (means
  ratio, not the sums ratio the module uses): same NaN mask, `max|diff| =
  3.14e-16` on the 1,500-bar frame of `docs/measure_vpci.py`, 897 of 1,481
  bars bit-identical -- so asserted at `atol=1e-12`, not equality. And three
  bars against a plain-numpy per-bar loop (`|diff|` 1.6e-16 / 0 / 0 there).
* SCALE-FREE: close, volume and both x8/x64 bit-identical; x10/x3.7 within
  tolerance (measured max `|diff|` 6.91e-16 on values of order 1e-2), NaN
  masks matching. Plus `0 < fires < n` and `nunique > 1` (1,481 fires of
  1,500, 1,481 distinct values, 729 positive / 752 negative on the script's
  frame).
* ZERO VOLUME: an all-zero `short` window makes `VWMA_short` `0/0 = NaN`,
  and NaN is all it makes -- no `inf` for non-negative volume. Five zero
  bars at 700..704 of the script's frame blank exactly **1** bar, 704, the
  only bar whose 5-bar window is all zero.
* Wiring: `Category`, the accessor, the column name `VPCI_5_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.overlap.sma import sma
from pandas_ta.overlap.vwma import vwma
from pandas_ta.volume.vpci import vpci


def _frame(n=900, seed=11, sigma=0.015):
    """Tick-rounded (0.01) close, volume rounded to 100 shares."""
    rng = np.random.default_rng(seed)
    close = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), 2)
    volume = np.round(rng.uniform(1e4, 1e6, n), -2)
    return Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def test_hand_derived_five_bars():
    """short=2, long=3; close = [10, 11, 12, 11, 13], volume = [100, 200, 100, 300, 100].

    bar 2: VWMA_3 = (1000+2200+1200)/400 = 11 = SMA_3  -> VPC = 0 -> VPCI = 0
    bar 3: VWMA_3 = (2200+1200+3300)/600 = 67/6, SMA_3 = 34/3
           VPC = (67/6 - 68/6)/(34/3) = -1/68
           VPR = VWMA_2 / SMA_2 = ((1200+3300)/400) / 11.5 = 11.25/11.5 = 45/46
           VM  = VMA_2 / VMA_3 = 200 / 200 = 1
           VPCI = -45/3128
    bar 4: VWMA_3 = (1200+3300+1300)/500 = 11.6, SMA_3 = 12 -> VPC = -1/30
           VPR = ((3300+1300)/400) / 12 = 23/24
           VM  = 200 / (500/3) = 6/5
           VPCI = -1/30 * 23/24 * 6/5 = -23/600
    Derived by hand, not by re-running the module."""
    close = Series([10.0, 11.0, 12.0, 11.0, 13.0])
    volume = Series([100.0, 200.0, 100.0, 300.0, 100.0])
    out = vpci(close, volume, short=2, long=3)
    assert out.iloc[:2].isna().all()
    expected = {2: 0.0, 3: -45 / 3128, 4: -23 / 600}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_matches_the_formula_built_from_vwma_and_sma():
    """The issue's formula through `pandas_ta.overlap.vwma` / `.sma`, which
    form VWMA as a ratio of rolling MEANS (the module uses rolling SUMS).
    Not bit-identical everywhere (897 of 1,481 bars are, on the script's
    frame; max |diff| 3.14e-16), so `atol=1e-12`."""
    close, volume = _frame()
    out = vpci(close, volume)
    ref = ((vwma(close, volume, 20) - sma(close, 20)) / sma(close, 20)
           * (vwma(close, volume, 5) / sma(close, 5))
           * (sma(volume, 5) / sma(volume, 20)))
    assert (out.isna() == ref.isna()).all()
    m = out.notna()
    np.testing.assert_allclose(out[m], ref[m], rtol=0, atol=1e-12)


def test_matches_an_independent_loop_at_defaults():
    close, volume = _frame()
    out = vpci(close, volume)
    c, v = close.to_numpy(), volume.to_numpy()
    for t in (300, 600, 899):
        cw, vw = c[t - 19:t + 1], v[t - 19:t + 1]
        cs, vs = c[t - 4:t + 1], v[t - 4:t + 1]
        vwl = (cw * vw).sum() / vw.sum()
        vws = (cs * vs).sum() / vs.sum()
        exp = ((vwl - cw.mean()) / cw.mean()) * (vws / cs.mean()) * (vs.mean() / vw.mean())
        assert out.iloc[t] == pytest.approx(exp, rel=1e-9, abs=1e-15), f"bar {t}"


def test_all_zero_short_volume_window_is_nan_not_inf():
    """Five zero-volume bars at 700..704 blank exactly bar 704, the only
    bar whose 5-bar window is entirely zero (`0/0`); no `inf` appears."""
    close, volume = _frame(1000)
    clean = vpci(close, volume)
    zv = volume.copy()
    zv.iloc[700:705] = 0.0
    out = vpci(close, zv)
    newly_nan = [int(i) for i in out.index[out.isna() & clean.notna()]]
    assert newly_nan == [704]
    assert not np.isinf(out.to_numpy(dtype=float)).any()


def test_insufficient_history_returns_none():
    close, volume = _frame(19)
    assert vpci(close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close, volume = _frame(20)
    out = vpci(close, volume)
    assert out.iloc[:19].isna().all()
    assert pd.notna(out.iloc[19])


def test_names_encode_parameters():
    close, volume = _frame(200)
    assert vpci(close, volume).name == "VPCI_5_20"
    assert vpci(close, volume, short=3, long=10).name == "VPCI_3_10"


def test_offset_shifts_the_series():
    close, volume = _frame(200)
    pd.testing.assert_series_equal(vpci(close, volume, offset=1),
                                   vpci(close, volume).shift(1), check_names=False)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.vpci")
_SHIPPED_WRITE = "    result = vpc * vpr * vm\n"
WRITE_SHIFT_MUTANT = (_SHIPPED_WRITE, "    result = (vpc * vpr * vm).shift(-1)\n")
OFFSETS = range(40, 900, 25)  # past the 19-bar warm-up


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_vpci_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close, volume = _frame()
    other_c, other_v = _frame(seed=59)
    base = fn(close, volume)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
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
    assert _leaks(vpci) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close, volume = _frame()
    assert not mod.vpci(close, volume).equals(vpci(close, volume))  # live
    assert _leaks(mod.vpci) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


def _scaled(k, what):
    close, volume = _frame()
    c = close * k if what in ("close", "both") else close
    v = volume * k if what in ("volume", "both") else volume
    return vpci(close, volume), vpci(c, v)


@pytest.mark.parametrize("what", ["close", "volume", "both"])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k, what):
    base, scaled = _scaled(k, what)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("what", ["close", "volume", "both"])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k, what):
    base, scaled = _scaled(k, what)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_fires_and_is_not_constant():
    close, volume = _frame()
    out = vpci(close, volume)
    fires = int(out.notna().sum())
    assert fires == 881  # 900 - 19
    assert 0 < fires < len(out)
    d = out.dropna()
    assert d.nunique() > 1
    assert (d > 0).any() and (d < 0).any()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _frame(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": volume})
    assert "vpci" in ta.Category["volume"]
    out = df.ta.vpci()
    assert out.name == "VPCI_5_20"
    pd.testing.assert_series_equal(out, vpci(close, volume))
    assert df.ta.vpci(short=3, long=10).name == "VPCI_3_10"
