# -*- coding: utf-8 -*-
"""TAO-10-5: `tao`, the trend-adjusted stochastic oscillator (PandasTa
issue #266; Kaufman, *Trading Systems and Methods*, 5th ed., 2013, ch. 17,
after E. Marshall Wall, "Rolling with the Punches", *Futures*, July 1996).

    O[T]     = 100 * (close[T] - LL10[T]) / (HH10[T] - LL10[T])  (NaN if HH == LL)
    MAO[T]   = mean(O[T - 4 .. T])
    TAO_10_5 = O[T] - (MAO[T] - 50)

What this file pins, in order of how much it would hurt to lose:

1. **Gate A, the issue's formula by scalar loops.** A fresh 10-bar min /
   max and a fresh five-term mean per bar, sharing no pandas operation
   with the module. NaN masks are asserted IDENTICAL on every frame;
   values agree to 1e-10 points, not bit for bit -- pandas' rolling mean
   is an online accumulator, measured 1.421e-14 .. 4.263e-14 points
   off the loop on 156 .. 951 of 1,487 fired bars per 1,500-bar frame
   (`docs/measure_tao.py` §A1). ⚠ The shipped `stoch` is NOT the
   oscillator used: it divides by `non_zero_range`, so a flat 10-bar
   window reads a number where the issue's definition reads NaN. On a
   moving price the two are bit-identical (0 bars differ on seven
   frames); on a flat one they differ on all 1,487 bars (§A3).
2. **THE BOUND, [-30, 130].** `O` is one of the five terms of its own
   mean, so `O - MAO` lies in [-80, 80]. Pinned bar by bar on every
   frame and ATTAINED exactly (130.0 and -30.0) by a hand frame -- four
   closes at the low of the range, then one at the high, and the mirror.
   The column does overshoot [0, 100] on real-looking paths: 1 .. 21
   bars below 0 or above 100 per 1,500-bar frame, measured range
   -17.4332 .. 119.9993 (§C).
3. **Gate B, causality.** One shared past, two wholly different futures
   (each later OHLC bar scaled by one factor, so it stays a valid bar):
   0 of 1,499 offsets caught on each of the eight 1,500-bar frames (§B).
   FIVE look-ahead mutants are read off the shipped source, `exec`'d in
   memory and asserted LIVE first. Four are caught on 36 of 36 tail
   offsets of every firing frame. ⚠ `hh-lead` (the 10-bar high read one
   bar early) is not: 33 .. 36 of 36 -- plausibly where the future bar's
   high stays under the window's maximum in both futures, leaving HH
   unchanged (the mechanism is not separately measured). It is asserted
   caught on at least half the offsets, not on all. All five are
   invisible on a flat price, where every bar is NaN either way.
4. **Gate D, scale.** x8, x64, 2^-20 and 2^300 are bit-identical on
   every frame; x10, x3.7, x0.1 agree to 1e-9 points (measured at most
   8.242e-13) with identical NaN masks. A level shift cancels too, but
   only to a tolerance (6.354e-09 points at +1e6, §D).
5. **Gate C, reachability.** The warm-up is a CONSTANT 13 bars on every
   moving frame (1,487 of 1,500 fire on seven 1,500-bar frames); a flat
   price fires 0. A flat run of L identical bars blanks nothing for
   L <= 9 and `L - 9 + 4` bars from L = 10 on (5 / 6 / 10 at 10 / 11 /
   15, §C2): each flat 10-bar window is a NaN `O`, which empties the
   five means that contain it.
6. **Gate E is OWED.** No ledger row is recorded here; CI on the way to
   `dev` reports it as a "Gate E owed" skip. The synthetic screen of
   §F: Spearman against `CFO_9` 0.7395 .. 0.8355, `RANK_5` 0.6585 ..
   0.8464, `WILLR_10` 0.5043 .. 0.6200, `STOCHk_14_3_3` 0.0333 .. 0.0788,
   over seven 1,500-bar frames. Real-data Gate C is owed with it.

⚠ Counts of differing bars and Spearman digits are NOT pinned to the
digits measured: the frames use `np.exp` / `np.cumsum`, so a different
numpy kernel moves prices in their last bits. What is pinned is
structure: a bound, a NaN mask, a first fired bar, a tolerance.

Every number quoted in this file comes from `docs/measure_tao.py`.
"""
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.stoch import stoch
from pandas_ta.momentum.tao import tao

N = 400
LEVEL = 100.0
LENGTH = 10
MA_LENGTH = 5
WARMUP = LENGTH + MA_LENGTH - 2
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "momentum" / "tao.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_tao.py`, shortened to 400 bars.


def _index(n):
    return date_range("2020-01-01", periods=n, freq="h")


def _ohlc(close, seed, tick=None):
    rng = np.random.default_rng(seed + 1000)
    n = close.size
    c = np.asarray(close, dtype=float)
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0.0, 0.002, n))
    up = np.abs(rng.normal(0.0, 0.006, n)) * c * (rng.random(n) > 0.2)
    dn = np.abs(rng.normal(0.0, 0.006, n)) * c * (rng.random(n) > 0.2)
    h = np.maximum(o, c) + up
    lo = np.minimum(o, c) - dn
    if tick:
        o, h, lo, c = (np.round(x / tick) * tick for x in (o, h, lo, c))
        h = np.maximum.reduce([h, o, c])
        lo = np.minimum.reduce([lo, o, c])
    return DataFrame({"open": o, "high": h, "low": lo, "close": c},
                     index=_index(n))


def _path(seed, n, mu=0.0, sigma=0.01, t=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(t, n) * sigma * 0.6 if t else rng.normal(mu, sigma, n)
    return LEVEL * np.exp(np.cumsum(r))


def _walk(seed=7, n=N):
    return _ohlc(_path(seed, n), seed)


def _trend(seed=11, n=N):
    return _ohlc(_path(seed, n, mu=0.003, sigma=0.008), seed)


def _range_bound(seed=13, n=N):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(LEVEL * np.exp(x), seed)


def _grid(seed=17, n=N):
    return _ohlc(_path(seed, n), seed, tick=0.01)


def _heavy(seed=19, n=N):
    return _ohlc(_path(seed, n, t=2.0), seed)


def _jump(seed=23, n=N):
    p = _path(seed, n)
    return _ohlc(p * np.where(np.arange(n) >= n // 2, 1.5, 1.0), seed)


def _flat(n=N):
    one = np.full(n, LEVEL)
    return DataFrame({"open": one, "high": one, "low": one, "close": one},
                     index=_index(n))


def _coarse(seed=7, n=N):
    return _ohlc(_path(seed, n, sigma=0.002), seed, tick=0.5)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
FIRING = [n for n in NAMES if n != "flat"]


def _run(df, fn=None, **kw):
    return (fn or tao)(df["high"], df["low"], df["close"], **kw)


# ----------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else 0.0


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


# ----------------------------------------------------------------- oracle


def _oracle(df, length=LENGTH, ma_length=MA_LENGTH, midpoint=50.0):
    """The issue's formula by scalar loops, no pandas operation."""
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = c.size
    o = np.full(n, np.nan)
    out = np.full(n, np.nan)
    for i in range(length - 1, n):
        hh = max(h[i - length + 1:i + 1])
        ll = min(lo[i - length + 1:i + 1])
        if hh != ll:
            o[i] = 100.0 * (c[i] - ll) / (hh - ll)
    for i in range(length + ma_length - 2, n):
        w = o[i - ma_length + 1:i + 1]
        if not np.isnan(w).any():
            total = 0.0
            for x in w:
                total += x
            out[i] = o[i] - (total / ma_length - midpoint)
    return Series(out, index=df.index)


# ----------------------------------------------------------------- mutants

LL_LINE = "    lowest_low = low.rolling(length).min()"
HH_LINE = "    highest_high = high.rolling(length).max()"
OSC_LINE = "    osc = 100 * (close - lowest_low) / rng.where(rng != 0)"
MAO_LINE = "    mao = osc.rolling(ma_length).mean()"
OUT_LINE = "    tao = osc - (mao - midpoint)"

CAUSALITY_MUTANTS = {
    "ll-centred": (LL_LINE,
                   "    lowest_low = low.rolling(length, center=True).min()"),
    "hh-lead": (HH_LINE,
                "    highest_high = high.rolling(length).max().shift(-1)"),
    "close-lead": (OSC_LINE, "    osc = 100 * (close.shift(-1) - lowest_low)"
                             " / rng.where(rng != 0)"),
    "mao-centred": (MAO_LINE,
                    "    mao = osc.rolling(ma_length, center=True).mean()"),
    "output-early": (OUT_LINE,
                     "    tao = (osc - (mao - midpoint)).shift(-1)"),
}
#: The one mutant a future bar can leave invisible (see item 3).
PARTIAL = "hh-lead"


def _mutant(old, new):
    """`tao` with one edit applied to the SHIPPED source, read off disk and
    exec'd in memory, so no mutant drifts from the code it edits."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tao"]


def _futures(df, j, spread=3.0):
    """Two frames bit-equal on bars < j and wholly different from j on:
    each later bar's prices scaled by one per-bar factor (up / down)."""
    n = len(df)
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return df.mul(up, axis=0), df.mul(dn, axis=0)


def _caught_at(fn, df, j):
    a, b = (_run(f, fn).iloc[:j] for f in _futures(df, j))
    return not _bit_equal(a, b)


def _offsets(n=N, how_many=12):
    return list(range(n - how_many, n))


# ------------------------------------------------------------ 1. GATE A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_issue_formula_by_loops_agrees(name):
    """Identical NaN masks, values to 1e-10 points (measured <= 4.263e-14)."""
    df = FRAMES[name]()
    col, orc = _run(df), _oracle(df)
    assert bool((col.isna() == orc.isna()).all())
    assert _abs(col, orc) <= 1e-10


@pytest.mark.parametrize("name", FIRING)
def test_gate_a_tao_is_fifty_plus_the_deviation_from_its_own_mean(name):
    """`O - (MAO - 50)` and `50 + (O - MAO)` are the same column; measured
    1.421e-14 points apart at worst."""
    df = FRAMES[name]()
    ll = df["low"].rolling(LENGTH).min()
    hh = df["high"].rolling(LENGTH).max()
    rng = hh - ll
    o = 100 * (df["close"] - ll) / rng.where(rng != 0)
    alt = 50 + (o - o.rolling(MA_LENGTH).mean())
    assert bool((_run(df).isna() == alt.isna()).all())
    assert _abs(_run(df), alt) <= 1e-10


@pytest.mark.parametrize("name", FIRING)
def test_the_shipped_stoch_raw_k_gives_the_same_column_on_a_moving_price(
        name):
    """`stoch(k=10, smooth_k=1)` is the same %K wherever the range is
    non-zero: bit-identical on every moving frame (§A3)."""
    df = FRAMES[name]()
    k = stoch(df["high"], df["low"], df["close"], k=LENGTH, d=1,
              smooth_k=1).iloc[:, 0]
    via = k - (k.rolling(MA_LENGTH).mean() - 50.0)
    assert _bit_equal(_run(df), via)


def test_but_not_on_a_flat_price_which_is_why_it_is_not_imported():
    """`non_zero_range` adds an epsilon, so a flat window reads a number
    where the issue's definition reads NaN."""
    df = _flat()
    k = stoch(df["high"], df["low"], df["close"], k=LENGTH, d=1,
              smooth_k=1).iloc[:, 0]
    via = k - (k.rolling(MA_LENGTH).mean() - 50.0)
    assert bool(_run(df).isna().all())
    assert int(via.notna().sum()) > 0


# ------------------------------------------------------------ 2. THE BOUND


@pytest.mark.parametrize("name", FIRING)
def test_the_column_stays_in_minus_thirty_to_one_hundred_thirty(name):
    v = _run(FRAMES[name]()).dropna()
    assert v.size > 0
    assert float(v.min()) >= -30.0 - 1e-9
    assert float(v.max()) <= 130.0 + 1e-9


def test_the_bound_is_attained_at_both_ends():
    for rest, last, want in ((0.0, 100.0, 130.0), (100.0, 0.0, -30.0)):
        c = np.array([50.0] * 9 + [rest] * 4 + [last])
        df = DataFrame({"high": np.full(c.size, 100.0),
                        "low": np.full(c.size, 0.0), "close": c},
                       index=_index(c.size))
        assert float(_run(df).iloc[-1]) == pytest.approx(want, abs=1e-12)


def test_the_column_overshoots_zero_to_one_hundred_on_a_walk():
    """The issue says "around [0, 100] (it can overshoot)" -- it does."""
    v = _run(_walk(n=1500)).dropna()
    assert int((v < 0).sum()) > 0 and int((v > 100).sum()) > 0


# ------------------------------------------------------------ 3. GATE B


@pytest.mark.parametrize("name", NAMES)
def test_the_module_reads_no_future_bar(name):
    df = FRAMES[name]()
    assert [j for j in _offsets() if _caught_at(tao, df, j)] == []


@pytest.mark.parametrize("name", NAMES)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    df = FRAMES[name]()
    full = _run(df)
    for k in (N // 2, N - 7):
        assert _bit_equal(_run(df.iloc[:k]), full.iloc[:k])


@pytest.mark.parametrize("label", list(CAUSALITY_MUTANTS))
def test_a_look_ahead_mutant_is_live_before_it_is_swept(label):
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    df = _walk()
    assert _differs(_run(df), _run(df, fn)) > 0


@pytest.mark.parametrize("label",
                         [k for k in CAUSALITY_MUTANTS if k != PARTIAL])
def test_a_look_ahead_mutant_is_caught_on_every_offset(label):
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    for name in FIRING:
        df = FRAMES[name]()
        caught = [j for j in _offsets() if _caught_at(fn, df, j)]
        assert caught == _offsets(), f"{label} on {name}: {len(caught)}"


def test_the_high_lead_mutant_is_caught_on_most_offsets():
    """⚠ Not every offset: 33 .. 36 of 36 measured on 1,500-bar frames."""
    fn = _mutant(*CAUSALITY_MUTANTS[PARTIAL])
    for name in FIRING:
        df = FRAMES[name]()
        caught = [j for j in _offsets() if _caught_at(fn, df, j)]
        assert len(caught) >= len(_offsets()) // 2, f"{name}: {len(caught)}"


def test_the_flat_frame_hides_every_mutant():
    df = _flat()
    for label, (old, new) in CAUSALITY_MUTANTS.items():
        assert _differs(_run(df), _run(df, _mutant(old, new))) == 0, label


# ------------------------------------------------------------ 4. GATE D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -20, 2.0 ** 300])
def test_scale_an_exact_binary_factor_is_bit_identical(name, factor):
    df = FRAMES[name]()
    assert _bit_equal(_run(df), _run(df * factor))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """Measured <= 8.242e-13 points; asserted at 1e-9."""
    df = FRAMES[name]()
    col, other = _run(df), _run(df * factor)
    assert bool((col.isna() == other.isna()).all())
    assert _abs(col, other) <= 1e-9


@pytest.mark.parametrize("shift", [1.0, 50.0, 1e6])
def test_scale_a_level_shift_cancels_to_a_tolerance(shift):
    """Measured 3.837e-13 / 1.307e-12 / 6.354e-09 points."""
    df = _walk()
    col, other = _run(df), _run(df + shift)
    assert bool((col.isna() == other.isna()).all())
    assert _abs(col, other) <= 1e-6


@pytest.mark.parametrize("name", FIRING)
def test_scale_fires_strictly_between_zero_and_n(name):
    col = _run(FRAMES[name]())
    assert 0 < int(col.notna().sum()) < col.size
    assert col.dropna().nunique() > 1


# ------------------------------------------------------------ 5. GATE C


@pytest.mark.parametrize("name", FIRING)
def test_the_warm_up_is_a_constant_13_bars(name):
    col = _run(FRAMES[name]())
    assert bool(col.iloc[:WARMUP].isna().all())
    assert bool(col.iloc[WARMUP:].notna().all())


def test_a_flat_price_never_fires():
    assert bool(_run(_flat()).isna().all())


@pytest.mark.parametrize("patch,emptied", [(5, 0), (9, 0), (10, 5),
                                           (11, 6), (15, 10)])
def test_a_flat_run_empties_only_once_it_fills_a_window(patch, emptied):
    """Planted run of identical bars ending at bar 300 (§C2 at bar 800)."""
    base = _walk()
    end = N - 100
    df = base.copy()
    df.iloc[end - patch + 1:end + 1] = float(base["close"].iloc[end - patch + 1])
    extra = _run(df).isna() & _run(base).notna()
    assert int(extra.sum()) == emptied


def test_the_shortest_input_that_produces_a_value():
    """`verify_series` floors the input at `length + ma_length - 1` = 14."""
    df = _walk(n=WARMUP + 1)
    col = _run(df)
    assert int(col.notna().sum()) == 1
    assert _run(df.iloc[:-1]) is None


def test_the_input_is_not_mutated():
    df = _walk()
    before = df.copy()
    _run(df)
    assert df.equals(before)


# ------------------------------------------------------------ 6. WIRING


def test_the_five_wiring_touch_points():
    df = _walk()
    assert hasattr(ta.momentum, "tao")
    assert "tao" in ta.Category["momentum"]
    assert hasattr(df.ta, "tao")
    col = _run(df)
    assert col.name == "TAO_10_5"
    assert col.category == "momentum"
    assert _bit_equal(df.ta.tao(), col)
    assert SOURCE.exists()


def test_the_accessor_forwards_every_parameter():
    """`hasattr` cannot see a keyword forwarded under the wrong name."""
    df = _walk()
    kw = dict(length=14, ma_length=3, midpoint=40)
    acc = df.ta.tao(**kw)
    assert _bit_equal(acc, _run(df, **kw))
    assert acc.name == "TAO_14_3_40"


def test_the_midpoint_is_a_constant_shift():
    df = _walk()
    a, b = _run(df), _run(df, midpoint=40)
    assert _abs(a - 10.0, b) <= 1e-10


def test_offset_and_fillna():
    df = _walk()
    col = _run(df)
    off = _run(df, offset=2)
    assert _bit_equal(off.iloc[2:].reset_index(drop=True),
                      col.iloc[:-2].reset_index(drop=True))
    filled = _run(df, fillna=-999.0)
    assert int((filled == -999.0).sum()) == int(col.isna().sum())


def test_the_docstring_first_paragraph_survives_the_dictionary_cut():
    """The dictionary shows 150 characters; measured 135."""
    body = []
    for line in tao.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    assert len(" ".join(body)) <= 150
