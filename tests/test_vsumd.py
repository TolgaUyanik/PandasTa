# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.vsumd` -- qlib Alpha158's `VSUMD$d`: an
RSI-style balance of volume increases against volume decreases, bounded in
[-1, 1]. Issue #34 (A158GAPS). Measurements in `docs/Alpha158Measured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every volume bar from `j`
  onward, demand bars `[0:j]` bit-identical across ALL columns, over 31
  offsets. A one-bar look-ahead mutant (`importlib` source read, `dv`
  shifted forward, `exec`'d in memory) is proved live, then caught at
  31 of 31.
* SCALE-FREE: the column reads no price, so a price rescale cannot reach
  it. `Sum(up,d) - Sum(down,d) = Sum(dv,d)` telescopes to
  `volume[t]-volume[t-d]`, and `Sum(|dv|,d)` is linear in volume, so the
  ratio is invariant to a volume rescale up to the `+1e-12` floor's
  non-commutation: bit-identical under x8/x64 is NOT quite achieved
  (measured max|diff| ~1e-16, same floor effect as `wvma`), within 1e-9
  under all four factors. Not constant. `0 < fires < n` per column.
* CORRECTNESS against an independent per-bar loop built from the formula,
  a hand-computed 4-bar window, AND the telescoping identity
  `Sum(up,d)-Sum(down,d) == volume.diff(d)` documented in the module.
* Wiring: `Category`, the accessor, and the column names `VSUMD_5` ..
  `VSUMD_60`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.vsumd import vsumd, DEFAULT_LENGTHS


def _walk(n=1200, seed=41):
    """Integer share counts, lognormal (same shape as `volcv`'s fixture)."""
    rng = np.random.default_rng(seed)
    return Series(np.round(rng.lognormal(10.0, 0.6, n)))


# ------------------------------------------------------------ correctness


def test_hand_computed_window():
    v = Series([1000.0, 1200.0, 900.0, 900.0, 1500.0])
    out = vsumd(v, lengths=[4])
    # window = diffs over bars 1..4: +200, -300, 0, +600
    # up = 200, 0, 0, 600 -> sum 800; down = 0, 300, 0, 0 -> sum 300
    # absdv sum = 200+300+0+600 = 1100
    expected = (800.0 - 300.0) / (1100.0 + 1e-12)
    assert out["VSUMD_4"].iloc[4] == pytest.approx(expected, rel=1e-12)


def test_matches_an_independent_loop():
    v = _walk(400).values
    length = 20
    dv_all = np.concatenate([[np.nan], np.diff(v)])
    ref = np.full(len(v), np.nan)
    for t in range(length, len(v)):
        window = dv_all[t - length + 1: t + 1]
        up = np.clip(window, 0, None).sum()
        down = np.clip(-window, 0, None).sum()
        den = np.abs(window).sum() + 1e-12
        ref[t] = (up - down) / den
    out = vsumd(Series(v), lengths=[length])[f"VSUMD_{length}"]
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=1e-9)


def test_telescoping_identity():
    """Sum(Greater(dv,0),d) - Sum(Greater(-dv,0),d) == Sum(dv,d) ==
    volume[t] - volume[t-d] -- the algebraic identity documented in the
    module source, checked against the module's own (non-telescoped)
    computation, not re-derived from it."""
    v = _walk(600, seed=7)
    length = 15
    out = vsumd(v, lengths=[length])[f"VSUMD_{length}"]
    den = v.diff().abs().rolling(length).sum() + 1e-12
    telescoped_num = v.diff(length)
    expected = telescoped_num / den
    m = out.notna()
    np.testing.assert_allclose(out[m].values, expected[m].values, rtol=1e-9)


def test_default_lengths_are_the_alpha158_windows():
    assert DEFAULT_LENGTHS == (5, 10, 20, 30, 60)
    out = vsumd(_walk(200))
    assert list(out.columns) == [f"VSUMD_{d}" for d in (5, 10, 20, 30, 60)]


def test_bounded_in_minus_one_one():
    out = vsumd(_walk()).dropna()
    assert (out.to_numpy() >= -1.0 - 1e-9).all()
    assert (out.to_numpy() <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.vsumd")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_vsumd_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "dv = volume.diff()\n    up = dv.clip(lower=0)",
    "dv = volume.diff().shift(-1)\n    up = dv.clip(lower=0)",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all().all():
        return True
    m = a.notna()
    return bool(((a[m] != b[m]) & m).to_numpy().any())


def _leaks(fn):
    v = _walk()
    base = fn(v)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        for future in (other.iloc[j:].values, v.iloc[j:].values * 1000.0):
            pv = v.copy()
            pv.iloc[j:] = future
            if _moved(base.iloc[:j], fn(pv).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(vsumd) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    v = _walk()
    assert not mod.vsumd(v).equals(vsumd(v))  # live
    assert _leaks(mod.vsumd) == len(OFFSETS)   # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    """Price plays no role in the formula (not merely untested: `vsumd`
    takes no `close` argument), so only the volume axis applies. NOT quite
    bit-identical at x8/x64 -- measured max|diff| ~1.1e-16, the same
    `+1e-12`-floor non-commutation as `wvma` -- well under this 1e-9 bound."""
    v = _walk()
    base, scaled = vsumd(v), vsumd(v * k)
    assert (base.isna() == scaled.isna()).all().all()
    m = base.notna()
    assert ((base[m] - scaled[m]).abs() < 1e-9).to_numpy()[m.to_numpy()].all()


def test_fires_between_zero_and_n():
    out = vsumd(_walk())
    for col in out.columns:
        m = out[col].notna()
        assert 0 < int(m.sum()) < len(out)


def test_column_is_not_constant():
    out = vsumd(_walk())
    for col in out.columns:
        assert out[col].dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    v = _walk(200)
    df = DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": v})
    assert "vsumd" in ta.Category["volume"]
    out = df.ta.vsumd()
    assert out.name == "VSUMD_5-10-20-30-60"
    pd.testing.assert_frame_equal(out, vsumd(v))
    assert list(df.ta.vsumd(lengths=[7]).columns) == ["VSUMD_7"]
