# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.bos_causal` -- `bos` and `choch` with the
look-ahead taken out (issue #332, which supersedes #7).

⚠ READ THIS FIRST.  This is NOT a Pine port.  Its source is this repo:
`trend/bos.py` + `trend/choch.py` (the event logic, kept) and
`trend/swing_equilibrium.py::_confirm_pivots` (the causal confirmation rule,
kept).  `bos` and `choch` flag a swing with `rolling(L, center=True)`, so a
swing is used `k = (L - 1) // 2` bars before it can be known.  `bos_causal`
registers the swing at bar `j + k`, the first bar at which it is knowable.
It ships beside `bos`/`choch`, which are untouched, under different column
names (`BOSC_*`), so neither the miner's rules on `BOS_BULL` nor the
`Category` sweep see a collision.  Six columns, all 0/1:
`BOSC_BULL_5`, `BOSC_BEAR_5`, `BOSC_HH_5`, `BOSC_LL_5`,
`BOSC_CHOCH_BULL_5`, `BOSC_CHOCH_BEAR_5`.

What these tests actually pin, in order of how much they would hurt to lose:

* CAUSALITY (Gate B), by FUTURE-PERTURBATION: rewrite every bar after `T`,
  demand bars `[0..T]` bit-identical, over 30 values of `T` and
  `swing_length` 4 / 5 / 7 / 9.  Measured on `docs/measure_bos_causal.py`'s
  first frame: `bos_causal` reaches 0 bars ahead at all four lengths; the
  shipped `bos` reaches 1 / 2 / 3 / 4 and `choch` reaches 1 / 2 / 1 / 1 bars
  (the `choch` figure is a lower bound: 40 probe bars, and its trend state
  resets after each break, so a probe can miss a leak).  A MUTANT is built from the real
  module's source via `importlib` (back-dating: flag the swing at `j`
  instead of `j + k` and read `H[t]`, which IS the centred construction),
  `exec`'d into a fresh in-memory module, proved LIVE (it moves the prefix)
  and caught, while the real module is clean.  Truncation alone would not
  see this: a back-dated flag is a pure function of the prefix it already
  has.  The shipped, centred `bos` and `choch` are caught by the same probe.
* GATE A: an independent reference, written from the rule in the issue and
  not from the module: per swing the window is tested with direct
  `all(...)` comparisons (`>=` over the window, strict `>` over the right
  bars, instead of the module's `max` + `any(==)`), events are collected
  into a per-bar list and replayed.  Bit-equal on all six columns over 8
  tick-rounded frames x `swing_length` 4 / 5 / 7 / 9.
* TIES: a double top confirms exactly one swing (the rightmost), and a
  triple top as well -- not zero (the "unique extreme" bug) and not two.
* TIMING: a swing at bar 10 is known at bar 12 (`L = 5`) and not at 10 or
  11; `HIGHER_HIGH` for a later peak at bar 20 fires at 22, not 20.
* REACHABILITY (Gate C): all six columns fire on all 16 frames; pooled
  counts over the 16 x 2000-bar frames (3,743 high/low tie bars):
  BULL 6,258 (19.56%), BEAR 6,658 (20.81%), HH 1,995 (6.23%),
  LL 1,956 (6.11%), CHOCH_BULL 546 (1.71%), CHOCH_BEAR 607 (1.90%).
* SCALE (Gate D): x8 and x64 bit-identical, x10 and x3.7 with 0 mismatching
  cells (tolerance form, NaN masks compared), and `0 < fires < n`.
* WIRING: `df.ta.bos_causal()`, `Category`, `offset`, column names.

Gate E has NOT been run (owed on the way to `dev`).
"""
import importlib
import importlib.util
import types

import numpy as np
import pytest
from pandas import DataFrame

import pandas_ta as ta
from pandas_ta.trend.bos_causal import _confirm, bos_causal

LENGTHS = (4, 5, 7, 9)
COLS = ["BOSC_BULL", "BOSC_BEAR", "BOSC_HH", "BOSC_LL", "BOSC_CHOCH_BULL", "BOSC_CHOCH_BEAR"]


# ----------------------------------------------------------------- data


def _frame(f, n=2000):
    """Tick-rounded synthetic OHLC; same generator as docs/measure_bos_causal.py."""
    rng = np.random.default_rng(332 + f)
    tick = [0.01, 0.05, 0.1, 0.25][f % 4]
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.012 + 0.004 * (f % 3), n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, .006, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, .006, n)))
    r = lambda x: np.round(x / tick) * tick
    return DataFrame(dict(high=r(h), low=r(l), close=r(c)))


def _cols(L):
    return [f"{c}_{L}" for c in COLS]


# ------------------------------------------------------------ reference


def _ref(h, l, c, L):
    """Independent Gate A reference, from the issue's rule."""
    h, l, c = list(h), list(l), list(c)
    n = len(c)
    k = (L - 1) // 2
    left = L - 1 - k
    ev = [[] for _ in range(n)]  # per bar t: ("H"|"L", value)
    for j in range(left, n - k):
        win = range(j - left, j + k + 1)
        if all(h[j] >= h[i] for i in win) and all(h[j] > h[i] for i in range(j + 1, j + k + 1)):
            ev[j + k].append(("H", h[j]))
        if all(l[j] <= l[i] for i in win) and all(l[j] < l[i] for i in range(j + 1, j + k + 1)):
            ev[j + k].append(("L", l[j]))
    out = {c_: [0.0] * n for c_ in COLS}
    sh = sl = None
    trend = 0
    for t in range(n):
        for kind, v in ev[t]:
            if kind == "H":
                if sh is not None:
                    out["BOSC_HH"][t] = float(v > sh)
                    if v < sh:
                        trend = -1
                sh = v
            else:
                if sl is not None:
                    out["BOSC_LL"][t] = float(v < sl)
                    if v > sl:
                        trend = 1
                sl = v
        bull = sh is not None and c[t] > sh
        bear = sl is not None and c[t] < sl
        out["BOSC_BULL"][t] = float(bull)
        out["BOSC_BEAR"][t] = float(bear)
        if bull and trend == -1:
            out["BOSC_CHOCH_BULL"][t] = 1.0
            trend = 0
        if bear and trend == 1:
            out["BOSC_CHOCH_BEAR"][t] = 1.0
            trend = 0
    return out


@pytest.mark.parametrize("L", LENGTHS)
def test_gate_a_matches_the_independent_reference(L):
    for f in range(8):
        d = _frame(f)
        got = bos_causal(d.high, d.low, d.close, swing_length=L)
        assert list(got.columns) == _cols(L)
        ref = _ref(d.high, d.low, d.close, L)
        for c in COLS:
            assert (got[f"{c}_{L}"].to_numpy() == np.array(ref[c])).all(), (f, L, c)


# --------------------------------------------------------------- ties


def test_a_double_top_confirms_exactly_one_swing():
    h = np.array([1, 2, 5, 5, 2, 1, 1, 1, 1, 1], dtype=float)  # L=5: k=2, left=2
    sw = _confirm(h, 5, True)
    # j=3 (the rightmost 5) is known at t=5; j=2 loses to its right-hand tie.
    assert sw[:5].sum() == 0 and sw[5] and int(sw[:7].sum()) == 1


def test_a_triple_top_confirms_exactly_one_swing():
    h = np.array([1, 2, 5, 5, 5, 2, 1, 0.5, 0.4, 0.3], dtype=float)
    sw = _confirm(h, 5, True)
    assert int(sw.sum()) == 1 and sw[6]  # j=4 known at t=6


def test_a_double_bottom_confirms_exactly_one_swing():
    sw = _confirm(np.array([9, 8, 1, 1, 8, 9, 9, 9, 9, 9], dtype=float), 5, False)
    assert int(sw[:7].sum()) == 1 and sw[5]


# ------------------------------------------------------------- timing


def test_swing_is_known_at_j_plus_k_not_before():
    n = 40
    h = np.full(n, 1.0) + 0.001 * np.arange(n) % 0.3
    h[10], h[20] = 5.0, 7.0
    low, c = h - 0.5, h - 0.4
    out = bos_causal(DataFrame({"h": h}).h, DataFrame({"l": low}).l, DataFrame({"c": c}).c)
    hh = out["BOSC_HH_5"].to_numpy()
    assert hh[22] == 1 and hh[20] == 0 and hh[21] == 0  # peak at 20, known at 22
    c2 = c.copy()
    c2[15] = 5.5  # breaks the bar-10 swing, which is known since bar 12
    c2[11] = 5.5  # ... but not yet at 11
    o2 = bos_causal(DataFrame({"h": h}).h, DataFrame({"l": low}).l, DataFrame({"c": c2}).c)
    assert o2["BOSC_BULL_5"].iloc[11] == 0 and o2["BOSC_BULL_5"].iloc[15] == 1


# ---------------------------------------------------------- causality


def _moved(fn, d, L, cols, probes=30):
    """Number of probe bars T whose prefix [0..T] changed when bars > T were rewritten."""
    alt = _frame(99, len(d))
    base = fn(d.high, d.low, d.close, swing_length=L)[cols]
    hit = 0
    for T in np.linspace(60, len(d) - 60, probes).astype(int):
        q = d.copy()
        q.iloc[T + 1:] = alt.iloc[T + 1:].to_numpy()
        got = fn(q.high, q.low, q.close, swing_length=L)[cols]
        if not base.iloc[:T + 1].equals(got.iloc[:T + 1]):
            hit += 1
    return hit


@pytest.mark.parametrize("L", LENGTHS)
def test_future_perturbation_never_moves_the_past(L):
    d = _frame(0)
    assert _moved(bos_causal, d, L, _cols(L)) == 0


def _mutant():
    spec = importlib.util.find_spec("pandas_ta.trend.bos_causal")
    src = spec.loader.get_source("pandas_ta.trend.bos_causal")
    a, b = "out[t] = True", "v = H[t - k]"
    assert src.count(a) == 1 and src.count(b) == 1
    # back-date: flag at j, read bar j's value at the flag bar -- the centred construction
    src = src.replace(a, "out[j] = True").replace(b, "v = H[t]")
    mod = types.ModuleType("bos_causal_mutant")
    exec(compile(src, "bos_causal_mutant", "exec"), mod.__dict__)
    return mod


def test_mutant_backdating_is_caught_and_the_real_module_is_clean():
    mut = _mutant()
    d = _frame(0)
    cols = ["BOSC_HH_5", "BOSC_BULL_5", "BOSC_BEAR_5"]
    assert _moved(bos_causal, d, 5, cols) == 0
    # LIVE: the mutant differs from the real module, and the probe sees it.
    assert not mut.bos_causal(d.high, d.low, d.close)["BOSC_HH_5"].equals(bos_causal(d.high, d.low, d.close)["BOSC_HH_5"])
    assert _moved(mut.bos_causal, d, 5, cols) > 0


@pytest.mark.parametrize("fn,cols", [
    (ta.bos, ["BOS_BULL", "BOS_BEAR", "HIGHER_HIGH", "LOWER_LOW"]),
    (ta.choch, ["CHoCH_BULL", "CHoCH_BEAR"]),
])
def test_mutant_the_shipped_centred_versions_are_caught_by_the_same_probe(fn, cols):
    # choch events are rare (about 1-2% of bars): 30 probes can miss its leak
    assert _moved(fn, _frame(0), 5, cols, probes=300) > 0


# ------------------------------------------------------ reachability


def test_gate_c_every_column_fires_on_every_frame_with_counts():
    tot = {c: 0 for c in COLS}
    for f in range(16):
        d = _frame(f)
        o = bos_causal(d.high, d.low, d.close)
        for c in COLS:
            s = int(o[f"{c}_5"].sum())
            assert 0 < s < len(d), (f, c)
            tot[c] += s
    assert tot == {"BOSC_BULL": 6258, "BOSC_BEAR": 6658, "BOSC_HH": 1995, "BOSC_LL": 1956,
                   "BOSC_CHOCH_BULL": 546, "BOSC_CHOCH_BEAR": 607}


# -------------------------------------------------------------- scale


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_power_of_two_is_bit_identical(k):
    for f in range(4):
        d = _frame(f)
        base = bos_causal(d.high, d.low, d.close)
        assert bos_causal(d.high * k, d.low * k, d.close * k).equals(base)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_tolerance_with_matching_masks(k):
    for f in range(4):
        d = _frame(f)
        base = bos_causal(d.high, d.low, d.close)
        got = bos_causal(d.high * k, d.low * k, d.close * k)
        assert (base.isna().to_numpy() == got.isna().to_numpy()).all()
        assert np.allclose(base.to_numpy(), got.to_numpy(), equal_nan=True)
        assert (base.sum() > 0).all() and (base.sum() < len(d)).all()


# ------------------------------------------------------------- wiring


def test_accessor_category_and_offset():
    d = _frame(0)
    assert "bos_causal" in ta.Category["trend"]
    via = d.ta.bos_causal(append=False)
    assert via.equals(bos_causal(d.high, d.low, d.close))
    sh = bos_causal(d.high, d.low, d.close, offset=2)
    assert sh.iloc[2:].equals(bos_causal(d.high, d.low, d.close).shift(2).iloc[2:])
