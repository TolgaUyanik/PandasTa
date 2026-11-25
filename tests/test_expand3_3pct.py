# -*- coding: utf-8 -*-
"""EXPAND3-3PCT: `expand3_3pct`, three bars of 3% expanding highs (+1) or
lows (-1) (Reddit r/TradingView 1jlvqer, tier 4; PandasTa issue #201).

    up[T]   = high[T-2] * 1.03 <= high[T-1] and high[T-1] * 1.03 <= high[T]
    dn[T]   = low[T-2]  * 0.97 >= low[T-1]  and low[T-1]  * 0.97 >= low[T]
    EXPAND3_3.0[T] = up[T] - dn[T]

What this file pins, in order of how much it would hurt to lose:

1. **Gate A, the source's expression by scalar loops.** The oracle below
   uses the float LITERALS 1.03 and 0.97 from the Pine line and plain
   Python comparisons, no pandas operation; it is BIT-EQUAL to the module
   (NaN masks included) on all nine frames, at 1,500 bars
   (`docs/measure_expand3_3pct.py` §A1) and at this file's 400 (§CT).
   Ties fire: a step landing exactly on 3% (100 -> 103 -> 106.09, every
   product an exact float equality, §A3) gives +1, and the mirrored lows
   give -1; both legs on one bar net to 0. The low leg is read as
   `low[1] <= 0.97 * low[2]`; the reciprocal reading
   (`low[1] * 1.03 <= low[2]`, i.e. a 2.913% step) differs on 0 .. 2 bars
   per 1,500-bar frame (§A2).
2. **Gate B, causality.** One shared past, two wholly different futures:
   0 of 1,499 offsets caught on each of the nine 1,500-bar frames (§B).
   FIVE look-ahead mutants are read off the shipped source and `exec`'d in
   memory -- `h2`/`l2` read bar T+1, the `up`/`dn` legs or the output
   written one bar early. ⚠ A ±1 event column is sparse, so a mutant is
   caught only on offsets where a signal is near: on the 400-bar
   `range-bound` frame swept here they are caught on 51 / 44 / 51 / 44 /
   96 of 399 offsets (§B1), and this file pins `> 0`, not the counts.
   Two further mutants (`h1`/`l1` read bar T+1) are live but caught on
   0 .. 3 of 1,499 offsets per frame: the mutated comparison needs bar
   T+1 inside a window as narrow as `[high[T-2]*1.03, high[T]/1.03]`, so
   they are disclosed in §B1, not pinned.
3. **Gate D, scale.** x8, x64, 2^-20 and 2^300 are bit-identical on every
   frame; x10, x3.7 and x0.1 differ on 0 bars of every frame with
   identical NaN masks (§D). A comparison sitting within one ulp of the
   3% step COULD flip under an inexact factor; none did. A +1 level shift
   is not invariant (moves 0 .. 6 bars per frame) -- a percent step is a
   ratio, not a distance.
4. **Gate C, reachability.** The warm-up is a constant 2 bars on every
   frame. On 1,500-bar frames the column fires 9 .. 50 nonzero bars per
   moving frame (`trend` 43 +1 / 0 -1, `range-bound` 30 / 20), never on
   `calm` (0.5% bars) or `flat` (§C). Fires are therefore asserted only on
   the frames where they were measured nonzero.
5. **Gate E is OWED.** Not run on the port; the issue's prototype measured
   max |rho| 0.2935 vs `Dist_to_FWMA_pct` (n = 397,692) -> SHIP, but a
   prototype is not a port. No ledger row yet.

⚠ Counts are NOT pinned to the digits measured: the frames use `np.exp` /
`np.cumsum`, so a different numpy kernel can move a price across a 3%
step. What is pinned is structure: bit-equality to the oracle, a NaN mask,
`> 0` / `== 0` catches, `0 < fires < n`.

Every number quoted in this file comes from `docs/measure_expand3_3pct.py`.
"""
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.trend.expand3_3pct import expand3_3pct

N = 400
LEVEL = 100.0
WARMUP = 2
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "trend" / "expand3_3pct.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_expand3_3pct.py`, at 400 bars.


def _index(n):
    return date_range("2020-01-01", periods=n, freq="min")


def _ohlc(close, seed, wick, tick=None):
    rng = np.random.default_rng(seed + 1_000)
    n = close.size
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, wick, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, wick, n)))
    if tick:
        high, low = (np.round(x / tick) * tick for x in (high, low))
    return DataFrame({"high": high, "low": low}, index=_index(n))


def _path(seed, n, mu=0.0, sigma=0.02, t=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(t, n) * sigma * 0.6 if t else rng.normal(mu, sigma, n)
    return LEVEL * np.exp(np.cumsum(r))


def _walk(seed=7, n=N):
    return _ohlc(_path(seed, n), seed, 0.01)


def _trend(seed=11, n=N):
    return _ohlc(_path(seed, n, mu=0.01, sigma=0.02), seed, 0.01)


def _range_bound(seed=13, n=N):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.03)
    return _ohlc(LEVEL * np.exp(x), seed, 0.01)


def _grid(seed=17, n=N):
    return _ohlc(_path(seed, n), seed, 0.01, tick=0.01)


def _heavy(seed=19, n=N):
    return _ohlc(_path(seed, n, t=2.0), seed, 0.01)


def _jump(seed=23, n=N):
    p = _path(seed, n) * np.where(np.arange(n) >= n // 2, 1.5, 1.0)
    return _ohlc(p, seed, 0.01)


def _calm(seed=29, n=N):
    return _ohlc(_path(seed, n, sigma=0.005), seed, 0.002)


def _coarse(seed=31, n=N):
    return _ohlc(_path(seed, n), seed, 0.01, tick=1.0)


def _flat(n=N):
    v = np.full(n, LEVEL)
    return DataFrame({"high": v, "low": v.copy()}, index=_index(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "calm": _calm,
    "coarse": _coarse, "flat": _flat,
}
NAMES = list(FRAMES)
#: Frames measured with at least one nonzero bar at 400 bars (§CT).
FIRING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump", "coarse"]


def _run(df, fn=None, **kw):
    return (fn or expand3_3pct)(df["high"], df["low"], **kw)


# ----------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


# ----------------------------------------------------------------- oracle


def _oracle(df):
    """The Pine expression by scalar loops, float literals 1.03 / 0.97."""
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    out = np.full(h.size, np.nan)
    for i in range(2, h.size):
        w = (h[i - 2], h[i - 1], h[i], lo[i - 2], lo[i - 1], lo[i])
        if any(np.isnan(x) for x in w):
            continue
        up = h[i - 2] * 1.03 <= h[i - 1] and h[i - 1] * 1.03 <= h[i]
        dn = lo[i - 2] * 0.97 >= lo[i - 1] and lo[i - 1] * 0.97 >= lo[i]
        out[i] = float(up) - float(dn)
    return Series(out, index=df.index)


# ----------------------------------------------------------------- mutants

H2_LINE = "    h2 = high.shift(2)"
L2_LINE = "    l2 = low.shift(2)"
UP_LINE = "    up = (h2 * up_k <= h1) & (h1 * up_k <= high)"
DN_LINE = "    dn = (l2 * dn_k >= l1) & (l1 * dn_k >= low)"
OUT_LINE = "    expand = (up.astype(float) - dn.astype(float)).where(valid)"

CAUSALITY_MUTANTS = {
    "h2-lead": (H2_LINE, "    h2 = high.shift(-1)"),
    "l2-lead": (L2_LINE, "    l2 = low.shift(-1)"),
    "up-early": (UP_LINE, "    up = ((h2 * up_k <= h1) & (h1 * up_k <= high))"
                          ".shift(-1, fill_value=False)"),
    "dn-early": (DN_LINE, "    dn = ((l2 * dn_k >= l1) & (l1 * dn_k >= low))"
                          ".shift(-1, fill_value=False)"),
    "output-early": (OUT_LINE, "    expand = (up.astype(float) - dn.astype(float))"
                               ".where(valid).shift(-1)"),
}


def _mutant(old, new):
    """`expand3_3pct` with one edit applied to the SHIPPED source, read off
    disk and exec'd in memory, so no mutant drifts from the code it edits."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["expand3_3pct"]


def _futures(df, j, spread=3.0):
    """Two frames bit-equal on bars < j and wholly different from j on:
    each later bar's high and low scaled by one per-bar factor (up / down)."""
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


ALL_OFFSETS = list(range(1, N))


# ------------------------------------------------------------ 1. GATE A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_source_expression_by_loops_is_bit_equal(name):
    df = FRAMES[name]()
    assert _bit_equal(_run(df), _oracle(df))


def test_a_step_exactly_on_3pct_fires_and_both_legs_net_to_zero():
    """§A3: 100 * 1.03 == 103.0, 103 * 1.03 == 106.09, 100 * 0.97 == 97.0,
    97 * 0.97 == 94.09 are exact float equalities, and `<=` / `>=` fire."""
    h = Series([100.0, 103.0, 106.09, 106.09])
    lo = Series([100.0, 97.0, 94.09, 94.09])
    one = h * 0 + 1
    assert list(_run(DataFrame({"high": h, "low": h})).iloc[2:]) == [1.0, 0.0]
    assert list(_run(DataFrame({"high": one, "low": lo})).iloc[2:]) == [-1.0, 0.0]
    assert list(_run(DataFrame({"high": h, "low": lo})).iloc[2:]) == [0.0, 0.0]


def test_a_step_just_under_3pct_does_not_fire():
    h = Series([100.0, 103.0, np.nextafter(106.09, 0.0)])
    assert _run(DataFrame({"high": h, "low": h})).iloc[2] == 0.0


def test_a_nan_anywhere_in_the_window_blanks_the_bar():
    df = _walk().copy()
    df.iloc[100, df.columns.get_loc("low")] = np.nan
    col = _run(df)
    assert bool(col.iloc[100:103].isna().all())
    assert int(col.isna().sum()) == WARMUP + 3


# ------------------------------------------------------------ 2. GATE B


@pytest.mark.parametrize("name", NAMES)
def test_the_module_reads_no_future_bar(name):
    df = FRAMES[name]()
    assert [j for j in range(N - 12, N) if _caught_at(expand3_3pct, df, j)] == []


def test_the_module_reads_no_future_bar_at_any_offset():
    df = _range_bound()
    assert [j for j in ALL_OFFSETS if _caught_at(expand3_3pct, df, j)] == []


@pytest.mark.parametrize("name", NAMES)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    df = FRAMES[name]()
    full = _run(df)
    for k in (N // 2, N - 7):
        assert _bit_equal(_run(df.iloc[:k]), full.iloc[:k])


@pytest.mark.parametrize("label", list(CAUSALITY_MUTANTS))
def test_a_look_ahead_mutant_is_live_before_it_is_swept(label):
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    df = _range_bound()
    assert _differs(_run(df), _run(df, fn)) > 0


@pytest.mark.parametrize("label", list(CAUSALITY_MUTANTS))
def test_a_look_ahead_mutant_is_caught(label):
    """Measured 51 / 44 / 51 / 44 / 96 of 399 offsets on this frame (§B1);
    pinned as `> 0` -- a sparse ±1 column is caught only near a signal."""
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    df = _range_bound()
    assert any(_caught_at(fn, df, j) for j in ALL_OFFSETS)


# ------------------------------------------------------------ 3. GATE D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -20, 2.0 ** 300])
def test_scale_an_exact_binary_factor_is_bit_identical(name, factor):
    df = FRAMES[name]()
    assert _bit_equal(_run(df), _run(df * factor))


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """Measured 0 differing bars on every frame (§D); the tolerance is one
    bar, room for a comparison within one ulp of the 3% step to flip."""
    df = FRAMES[name]()
    col, other = _run(df), _run(df * factor)
    assert bool((col.isna() == other.isna()).all())
    assert _differs(col, other) <= 1


@pytest.mark.parametrize("name", FIRING)
def test_scale_fires_strictly_between_zero_and_n(name):
    col = _run(FRAMES[name]())
    assert 0 < int((col.fillna(0) != 0).sum()) < col.size


# ------------------------------------------------------------ 4. GATE C


@pytest.mark.parametrize("name", NAMES)
def test_the_warm_up_is_a_constant_2_bars(name):
    col = _run(FRAMES[name]())
    assert bool(col.iloc[:WARMUP].isna().all())
    assert bool(col.iloc[WARMUP:].notna().all())
    assert set(col.dropna().unique()) <= {-1.0, 0.0, 1.0}


def test_both_signs_fire_on_range_bound():
    """§CT: `range-bound` at 400 bars, 4 bars at +1 and 4 at -1."""
    col = _run(_range_bound())
    assert int((col == 1).sum()) > 0
    assert int((col == -1).sum()) > 0


@pytest.mark.parametrize("name", ["calm", "flat"])
def test_quiet_frames_never_fire(name):
    col = _run(FRAMES[name]())
    assert bool((col.dropna() == 0).all())


def test_the_shortest_input_that_produces_a_value():
    df = _walk(n=3)
    assert int(_run(df).notna().sum()) == 1
    assert _run(df.iloc[:2]) is None


def test_the_input_is_not_mutated():
    df = _walk()
    before = df.copy()
    _run(df)
    assert df.equals(before)


# ------------------------------------------------------------ 5. WIRING


def test_the_five_wiring_touch_points():
    df = _walk()
    assert hasattr(ta.trend, "expand3_3pct")
    assert "expand3_3pct" in ta.Category["trend"]
    assert hasattr(df.ta, "expand3_3pct")
    col = _run(df)
    assert col.name == "EXPAND3_3.0"
    assert col.category == "trend"
    assert _bit_equal(df.ta.expand3_3pct(), col)
    assert SOURCE.exists()


def test_the_accessor_forwards_every_parameter():
    """`hasattr` cannot see a keyword forwarded under the wrong name."""
    df = _range_bound()
    acc = df.ta.expand3_3pct(pct=2)
    assert _bit_equal(acc, _run(df, pct=2))
    assert not _bit_equal(acc, _run(df))
    assert acc.name == "EXPAND3_2.0"


def test_offset_and_fillna():
    df = _walk()
    col = _run(df)
    off = _run(df, offset=2)
    assert _bit_equal(off.iloc[2:].reset_index(drop=True),
                      col.iloc[:-2].reset_index(drop=True))
    filled = _run(df, fillna=-999.0)
    assert int((filled == -999.0).sum()) == int(col.isna().sum())
