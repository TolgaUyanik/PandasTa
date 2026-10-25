# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.overlap.dickson_ma` -- the close's percent distance
from the Dickson Moving Average, (EC(30) + HMA(7)) / 2, where EC is Ehlers &
Way's error-correcting EMA.  Issue #147 (BT-DMA-DIST).  Measurements are in
`docs/DicksonMaMeasured.md`; every number quoted here is printed by
`docs/measure_dickson_ma.py`.

⚠ READ THIS FIRST.  EC is NOT an EMA with a fixed gain: every bar it tries
101 gains (-5.0 .. +5.0) and keeps the one whose EC lands closest to the
close.  That search is a discontinuous function of the state, so a test
that only compares tails, or only compares against the module's own
vectorised form, can miss a broken search.  The oracle below is a scalar,
line-for-line transcription of the EasyLanguage listing AS RECALLED (no copy
of the paper was consulted; checking it is owed, docs/DicksonMaMeasured.md),
and the comparison is BIT-FOR-BIT on EC, on data where the search lands both
on the clamp and strictly inside it (so the comparison is not vacuous).  The
oracle shares the recall with the module, so it cannot catch a misremembered
constant.  The clamp dominates: +5 on 97.1-97.4% of bars at the three sigmas
measured, so EC behaves mostly like a fixed fast smoother.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 32 offsets past the warm-up --
  once with another walk's closes, and once with each missing-bar value
  (NaN, 0, -1), so a look-ahead through the missing-bar mask is visible
  too.  Six look-ahead mutants (`importlib` source read, `exec`'d in
  memory) are each proved live, then caught: the EC write back-dated, the
  distance back-dated, the HMA fed tomorrow's close and the EMA fed
  tomorrow's close at 32 of 32; the gain search scored against tomorrow's
  close at 19 of 32 (it reads tomorrow's close only inside the argmin, so
  it can leak only at offsets where the new close changes bar j-1's best
  gain -- read in the code; why 19 was not measured further); the mask
  reading tomorrow's validity at 32 of 32 under each missing-bar value, and
  at 0 under the walk perturbation (pinned: it is why the fills exist).
  NaN masks are compared before values, because a bare `!=` on NaN passes
  a null mutant.
* CORRECTNESS against the oracle: EC bit-identical at lengths 10 / 30 / 50
  (2,697 of 2,697 bars each), including a missing bar; the whole distance
  within 1e-12 (measured 0 / 0 / 4.4e-14 at (30, 7) / (10, 4) / (50, 16));
  a hand-computed second bar; a constant series reads 0 (2.2e-14).
* The HEAD, not only the tail (the Hilbert lesson in CLAUDE.md): starting
  at bar s instead of bar 0 must agree with the full run to 1e-6 from the
  FIRST emitted bar on (measured worst 5.5e-8 / 5.1e-8 / 4.1e-7), over 90
  runs at lengths 30 / 10 / 50 (warm-ups 277 / 92 / 461, pinned as
  literals, not read back from the module).  And the warm-up is not
  padding: emitting from half of it leaves a start-dependent error of 4.7e-5.
* The warm-up counts VALID closes, not bars.
* SCALE-FREE: bit-identical under x8 and x64, within 1e-9 (measured
  6.7e-14 / 4.4e-14) under x10 and x3.7 with matching NaN masks, and
  `0 < fires < n`.
* Bad input: NaN, zero, negative and infinite closes are missing bars
  (identical to NaN), leading NaNs only shift the output, too few valid
  closes returns None, and a non-positive DMA emits NaN, not a sign flip.
* Wiring: `Category`, the accessor, and the column names.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.overlap.dickson_ma import dickson_ma, _ec, _warmup

#: Warm-ups printed by docs/measure_dickson_ma.py, as literals so the oracle and
#: the head test do not borrow the module's own `_warmup`.
WARMUPS = {10: 92, 30: 277, 50: 461}
W = WARMUPS[30]


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# ------------------------------------------------------------- the oracle


def literal_ec(close, length=30, gain_limit=50):
    """Ehlers & Way (S&C, Nov 2010), the EasyLanguage listing line for line
    AS RECALLED (no copy consulted; see docs/DicksonMaMeasured.md, Sources),
    as a scalar loop.  Returns (EC, BestGain) per bar.  Departures, both
    also in the module: EMA and EC are seeded on the first finite close (the
    listing starts both at 0), and LeastError starts at +inf (the listing:
    1000000, a price-unit constant).  Non-finite closes are skipped."""
    c = np.asarray(close, dtype=float)
    alpha = 2 / (length + 1)                                # alpha = 2 / (Length + 1)
    ec_out, gain_out = np.full(len(c), np.nan), np.full(len(c), np.nan)
    ema = ec1 = None
    for t in range(len(c)):
        if not np.isfinite(c[t]):
            continue
        if ec1 is None:
            ema = ec1 = ec_out[t] = c[t]
            continue
        ema = alpha * c[t] + (1 - alpha) * ema              # EMA = alpha*Close + (1 - alpha)*EMA[1]
        least_error, best_gain = np.inf, 0.0                # LeastError = 1000000
        for value1 in range(-gain_limit, gain_limit + 1):   # For Value1 = -GainLimit to GainLimit
            gain = value1 / 10                              # Gain = Value1 / 10
            ec = alpha * (ema + gain * (c[t] - ec1)) + (1 - alpha) * ec1
            error = c[t] - ec                               # Error = Close - EC
            if abs(error) < least_error:                    # If AbsValue(Error) < LeastError
                least_error, best_gain = abs(error), gain
        ec1 = ec_out[t] = alpha * (ema + best_gain * (c[t] - ec1)) + (1 - alpha) * ec1
        gain_out[t] = best_gain
    return ec_out, gain_out


def literal_wma(x, n):
    """Linearly weighted mean of the last n values, newest weighted n."""
    x = np.asarray(x, dtype=float)
    w = np.arange(1, n + 1, dtype=float)
    out = np.full(len(x), np.nan)
    for t in range(n - 1, len(x)):
        out[t] = (x[t - n + 1:t + 1] * w).sum() / w.sum()
    return out


def literal_hma(x, n):
    """Hull: WMA(2 * WMA(n / 2) - WMA(n), sqrt(n)), periods truncated to integers."""
    return literal_wma(2 * literal_wma(x, int(n / 2)) - literal_wma(x, n), int(np.sqrt(n)))


def literal_dist(close, length=30, hull_length=7):
    c = np.asarray(close, dtype=float)
    dma = (literal_ec(c, length)[0] + literal_hma(c, hull_length)) / 2
    out = 100 * (c / dma - 1)
    out[:np.flatnonzero(np.isfinite(c))[WARMUPS[length]]] = np.nan
    return out


# ------------------------------------------------------------ correctness


def test_warmup_at_defaults():
    assert {n: _warmup(n) for n in WARMUPS} == WARMUPS
    out = dickson_ma(_walk())
    assert out.iloc[:W].isna().all()
    assert out.iloc[W:].notna().all()


@pytest.mark.parametrize("length", [10, 30, 50])
def test_ec_matches_the_listing_bit_for_bit(length):
    clamped = interior = 0
    for seed, sigma in ((1, 0.005), (2, 0.02), (3, 0.05)):
        close = _walk(900, seed=seed, sigma=sigma).to_numpy()
        close[600] = np.nan
        ref, gains = literal_ec(close, length)
        assert np.array_equal(_ec(close, length), ref, equal_nan=True)
        g = gains[np.isfinite(gains)]
        clamped += int((np.abs(g) == 5.0).sum())
        interior += int((np.abs(g) < 5.0).sum())
    assert clamped > 0 and interior > 0  # the search was exercised, not just its clamp


@pytest.mark.parametrize("length,hull_length", [(30, 7), (10, 4), (50, 16)])
def test_matches_the_listing_end_to_end(length, hull_length):
    close = _walk(1200)
    close.iloc[700] = np.nan
    got = dickson_ma(close, length, hull_length).to_numpy()
    ref = literal_dist(close, length, hull_length)
    assert (np.isnan(got) == np.isnan(ref)).all()
    assert np.nanmax(np.abs(got - ref)) < 1e-12


def test_hand_computed_second_bar():
    """Bar 2 of closes (10, 11) at length 30: the best gain wants
    1/alpha - alpha = 15.4 > 5, so it clamps at +5 and
    EC = 10 + alpha^2 + 5 * alpha."""
    alpha = 2 / 31
    ec, gains = literal_ec([10.0, 11.0])
    assert gains[1] == 5.0
    assert abs(_ec(np.array([10.0, 11.0]), 30)[1] - (10 + alpha ** 2 + 5 * alpha)) < 1e-12


def test_constant_series_reads_zero():
    out = dickson_ma(Series(np.full(600, 37.5))).dropna()
    assert len(out) == 600 - W
    assert out.abs().max() < 1e-12


# ------------------------------------------------------------- bad input


@pytest.mark.parametrize("bad", [0.0, -1.0, np.inf])
def test_a_bad_close_is_a_missing_bar(bad):
    close = _walk()
    nan_close, bad_close = close.copy(), close.copy()
    nan_close.iloc[600] = np.nan
    bad_close.iloc[600] = bad
    out = dickson_ma(bad_close)
    assert out.equals(dickson_ma(nan_close))
    assert out.iloc[600:608].isna().all()          # HMA(7) spans the hole for 8 bars
    assert np.isfinite(out.iloc[608:].to_numpy()).all()


def test_leading_nans_only_shift_the_output():
    close = _walk()
    padded = pd.concat([Series([np.nan] * 50), close], ignore_index=True)
    out = dickson_ma(padded)
    assert out.first_valid_index() == 50 + W
    assert out.iloc[50:].reset_index(drop=True).equals(dickson_ma(close))


def test_warmup_counts_valid_closes_not_bars():
    close = _walk()
    close.iloc[50:70] = np.nan
    assert dickson_ma(close).first_valid_index() == W + 20


def test_too_few_valid_closes_returns_none():
    assert dickson_ma(Series([np.nan] * 500)) is None
    close = _walk(500)
    close.iloc[:300] = np.nan
    assert dickson_ma(close) is None  # 200 valid closes <= W
    assert dickson_ma(_walk(W)) is None


def test_a_non_positive_dma_emits_nan():
    """A 99.999% one-bar crash held flat drives DMA <= 0 on 1 bar; the
    distance to a non-positive average is undefined, not a sign flip."""
    close = Series(np.r_[np.full(400, 100.0), np.full(20, 0.001)])
    out = dickson_ma(close)
    dma = (_ec(close.to_numpy(), 30) + literal_hma(close, 7)) / 2
    neg = np.flatnonzero(dma <= 0)
    assert len(neg) == 1
    assert out.iloc[neg].isna().all()
    assert out.iloc[W:400].notna().all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.overlap.dickson_ma")


def _load_mutant(edits, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    for old, new in edits:
        assert src.count(old) == 1, f"mutation target {old!r} not unique"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_dma_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "ec_write": [("ec = out[t] = cand[", "ec = out[t - 1] = cand[")],
    "dist_write": [("dma.where(dma > 0) - 1)", "dma.where(dma > 0) - 1).shift(-1)")],
    "hma_input": [("hma(x, length=hull_length)", "hma(x.shift(-1), length=hull_length)")],
    "ema_input": [("ema = alpha * x[t] +", "ema = alpha * x[min(t + 1, len(x) - 1)] +")],
    # the optimiser's classic leak: pick the gain that best fits TOMORROW's close
    "search_target": [("argmin(npabs(x[t] - cand))", "argmin(npabs(x[min(t + 1, len(x) - 1)] - cand))")],
}

#: Reads tomorrow's validity. A perturbation that keeps every close valid
#: cannot see it, so it is tried against the missing-bar FILLS instead.
MASK_MUTANT = [("& (close > 0))", "& (close > 0) & (close.shift(-1) > 0))")]

OFFSETS = range(290, 1200, 29)  # 32 offsets, all past the warm-up
FILLS = [np.nan, 0.0, -1.0]     # missing-bar values written over bars >= j

#: Offsets at which each mutant leaks under the walk perturbation, of 32.
#: `search_target` reads tomorrow's close only inside the argmin, so it can
#: leak only where the new close changes bar j-1's best gain (read in the
#: code; why 19 was not measured further). Pinned, so a change in either
#: direction fails.
CAUGHT = {tag: len(OFFSETS) for tag in MUTANTS}
CAUGHT["search_target"] = 19


def _leaks(fn, fill=None):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.
    Bars >= j become another walk's closes, or `fill` if one is given."""
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values if fill is None else fill
        out = fn(pert)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        if not a.equals(b):
            hits += 1
    return hits


@pytest.mark.parametrize("fill", [None] + FILLS)
def test_real_module_never_reads_the_future(fill):
    assert len(OFFSETS) == 32
    assert _leaks(dickson_ma, fill) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(MUTANTS[tag], tag)
    close = _walk()
    assert not mod.dickson_ma(close).equals(dickson_ma(close))  # live
    assert _leaks(mod.dickson_ma) == CAUGHT[tag]                # caught


@pytest.mark.parametrize("fill", FILLS)
def test_mask_mutant_is_caught(fill):
    mod = _load_mutant(MASK_MUTANT, "mask")
    close = _walk()
    assert not mod.dickson_ma(close).equals(dickson_ma(close))  # live
    assert _leaks(mod.dickson_ma, fill) == len(OFFSETS)         # caught, 32 of 32


def test_mask_mutant_is_invisible_to_the_walk_perturbation():
    """Why FILLS exist: swapping in another all-valid walk never moves the mask."""
    assert _leaks(_load_mutant(MASK_MUTANT, "mask").dickson_ma) == 0


# ------------------------------------------------------- head transient

LENGTHS = [30, 10, 50]


@pytest.mark.parametrize("length", LENGTHS)
def test_head_agrees_with_a_longer_run_from_the_first_emitted_bar(length):
    w = WARMUPS[length]
    worst = 0.0
    for seed in range(10):
        for sigma in (0.005, 0.02, 0.05):
            close = _walk(1500, seed=seed, sigma=sigma)
            full = dickson_ma(close, length)
            for s in (100, 500, 900):
                part = dickson_ma(close.iloc[s:], length)
                i = part.first_valid_index()
                assert i == s + w
                worst = max(worst, (part.loc[i:] - full.loc[i:]).abs().max())
    assert worst < 1e-6


def test_the_warmup_is_not_padding():
    """Emitting from W // 2 would carry a visible transient that a
    tail-only check would not catch."""
    close = _walk(1500, seed=3)
    full = dickson_ma(close)
    mod = _load_mutant([("dist.iloc[:valid[warmup]]", "dist.iloc[:valid[warmup // 2]]")], "half")
    early = mod.dickson_ma(close.iloc[500:])
    i = 500 + W // 2
    assert early.first_valid_index() == i
    assert abs(early.loc[i] - full.loc[i]) > 1e-5  # measured 4.7e-5, vs the 1e-6 the head test asserts


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    assert dickson_ma(close).equals(dickson_ma(close * k))


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = dickson_ma(close), dickson_ma(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_fires_and_is_not_constant():
    x = dickson_ma(_walk(tick=0.05)).dropna()
    assert 0 < int((x > 0).sum()) < len(x)
    assert x.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(700)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "dickson_ma" in ta.Category["overlap"]
    out = df.ta.dickson_ma()
    assert out.name == "DICKSON_DIST_30_7"
    pd.testing.assert_series_equal(out, dickson_ma(close))
    assert df.ta.dickson_ma(length=20, hull_length=9).name == "DICKSON_DIST_20_9"
    assert dickson_ma(close, hull_length=1).name == "DICKSON_DIST_30_7"  # HMA needs >= 2: default
