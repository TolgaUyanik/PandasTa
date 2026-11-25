# -*- coding: utf-8 -*-
"""VWD: `vwd`, the volume-weighted MA-difference oscillator (issue #202).

    madif[T] = (SMA(close, 14)[T] - EMA(close, 7)[T]) / EMA(close, 7)[T] * 100
    vp[T]    = (buy - sell) / (buy + sell), buy = V*(C-L)/(H-L),
               sell = V*(H-C)/(H-L)   ==  ((C-L) - (H-C)) / (H-L)
    vs[T]    = SMA(|vp|, 14)[T]
    VWD[T]   = madif[T] * vp[T] * vs[T] * 10

Source: Reddit, tier 4 -- r/TradingView 1gofmli (2024-11-11), as issue
#202 quotes it. Existence, not evidence.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the poster's formula, spelled independently, with vp
   in the LITERAL volume form.** A bar-by-bar oracle -- its own
   `math.fsum` SMAs, its own SMA-seeded EMA recursion over Python floats,
   `buy` and `sell` each carrying V -- agrees on **1,487 of 1,487** fired
   bars of each of six varying frames, identical NaN masks, to
   **2.025e-13** absolute at Spearman 1.0000. Asserted 1e-9 absolute.
   The module's EMA leg is `talib.EMA(close, 7)` to **1.819e-12**, both
   first firing at bar 6 (skips where talib is absent).

2. **"Volume-weighted" in name only, pinned.** V cancels from vp, so the
   module does not read volume. Where V == 0 the literal form is 0/0: one
   zero-volume bar at 700 drops the literal form from 1,487 to **1,473**
   fired bars (bars 700..713) while the module is unaffected.

3. **Which EMA.** The SMA-seeded EMA (this fork's `ema`, TA-Lib's). A bare
   `ewm(span=7)` recursing from bar 0 differs on **53 .. 64** of the 1,487
   bars by more than 1e-9, up to **1.463e-01**, and the last such bar is
   **67 .. 80**: a warm-up transient, Spearman >= 0.999998.

4. **Gate B is the sweep AND the oracle.** The module is caught **0 of
   36** perturbation offsets on each of six frames. Six look-ahead
   mutants read off the shipped source and `exec`'d in memory are each
   caught **36 of 36** on three frames, the smallest first catch moving a
   bar by **7.490e-03**. ⚠ The suffix perturbation scales high, low and
   close by DIFFERENT factors (1.02 / 1.01 / 1.03): vp is invariant under
   a common rescale of a bar, so a uniform rescale caught the `vp-lead`
   and `vs-lead` mutants only by rounding: their prefixes moved by
   1.930e-14 .. 1.703e-13 and 2.359e-16 .. 1.599e-14 over the three swept
   frames (`docs/measure_vwd.py` §B1U).
   Three edits that are wrong without reading a later bar (`vs` lagged,
   EMA at 14, madif over the SMA) score **0 of 36** on the sweep and miss
   the oracle by **3.737e-01 .. 9.068e+00**.

5. **Gates C and D.** Every varying frame fires on **1,487 of 1,500**
   bars from bar 13; 1,487 distinct values on five, 1,469 on `grid`,
   where **19** bars read exactly 0.0 (a tick-rounded close at the exact
   mid-range). Pooled over 8,922 bars: **-5.7406e+01 .. 4.9034e+01**,
   negative on **4,416**. x8/x64 is bit-identical (also with H == L bars
   present); x10/x3.7/x0.1/x1.0000001 agrees to **1.717e-11** absolute
   over 24 cells with every NaN mask matching, asserted 1e-9. A +10 level
   shift moves **1,468 .. 1,487** bars, so the x8 bit-identity is not
   vacuous. A constant close reads exactly 0.0 on all 1,487 bars, so "not
   a constant column" is asserted on the varying frames only.

6. **An H == L bar blanks SLOW bars.** vp is 0/0 there in the source, and
   SMA14 of |vp| needs 14 valid values: 15 such bars on `doji` blank
   **210** bars after the warm-up (1,277 of 1,500 fire).

Every number above is printed by `python docs/measure_vwd.py`; the
asserted bounds (1e-9) are this file's own constants. Gate E is OWED, not
measured here (`docs/VwdMeasured.md` §E).

NOT pinned here: the poster's claim that the column times anything, the
2-sigma band and the RSI filter (none ships), and real-data reachability,
which the Gate E run's sample size reports.
"""
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.vwd import FAST, GAIN, MIN_BARS, PERCENT, SLOW, vwd
from pandas_ta.overlap.ema import ema

ROOT = Path(__file__).resolve().parents[1]

N = 1500
LEVEL = 100.0
COLUMN = "VWD_7_14"
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_vwd.py`, so a number here and a
# number in the receipt are the same measurement.


def _ohlcv(close, seed):
    rng = np.random.default_rng(seed + 9_999)
    idx = date_range("2020-01-01", periods=close.size, freq="h")
    return (Series(close * (1.0 + 0.004 * rng.random(close.size)), index=idx),
            Series(close * (1.0 - 0.004 * rng.random(close.size)), index=idx),
            Series(close, index=idx),
            Series(rng.integers(1_000, 100_000, close.size).astype(float),
                   index=idx))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _ohlcv(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), seed)


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlcv(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))), seed)


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlcv(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    h, l, c, v = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick, v)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlcv(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                  seed)


def _jump(seed=23, n=N, level=LEVEL):
    h, l, c, v = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f, v


def _doji(seed=29, n=N, level=LEVEL, every=100):
    h, l, c, v = _walk(seed, n, level)
    h, l = h.copy(), l.copy()
    at = np.arange(50, n, every)
    h.iloc[at] = c.iloc[at]
    l.iloc[at] = c.iloc[at]
    return h, l, c, v


def _flat(n=N, level=LEVEL):
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one * 1.004, one * 0.996, one.copy(), Series(np.full(n, 1e4), index=idx)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "doji": _doji,
    "flat": _flat,
}
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return vwd(*_frame(name)[:3])


# ---------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


# ---------------------------------------------------------------- oracle


def _oracle(high, low, close, volume, ema_seed="sma"):
    """The poster's formula bar by bar, sharing no code with the module:
    `math.fsum` SMAs, a hand-rolled EMA, and vp in the LITERAL V form."""
    H = [float(x) for x in high.to_numpy(dtype=float)]
    L = [float(x) for x in low.to_numpy(dtype=float)]
    C = [float(x) for x in close.to_numpy(dtype=float)]
    V = [float(x) for x in volume.to_numpy(dtype=float)]
    n = len(C)
    nan = float("nan")
    alpha = 2.0 / (FAST + 1)
    e = [nan] * n
    if ema_seed == "sma":
        e[FAST - 1] = math.fsum(C[:FAST]) / FAST
        start = FAST
    else:
        e[0] = C[0]
        start = 1
    for i in range(start, n):
        e[i] = alpha * C[i] + (1.0 - alpha) * e[i - 1]
    vp = [nan] * n
    for i in range(n):
        if H[i] - L[i] > 0.0:
            buy = V[i] * (C[i] - L[i]) / (H[i] - L[i])
            sell = V[i] * (H[i] - C[i]) / (H[i] - L[i])
            if buy + sell != 0.0:
                vp[i] = (buy - sell) / (buy + sell)
    out = [nan] * n
    for i in range(SLOW - 1, n):
        win = [abs(x) for x in vp[i - SLOW + 1:i + 1]]
        if any(math.isnan(x) for x in win):
            continue
        s = math.fsum(C[i - SLOW + 1:i + 1]) / SLOW
        madif = (s - e[i]) / e[i] * PERCENT
        out[i] = madif * vp[i] * (math.fsum(win) / SLOW) * GAIN
    return Series(out, index=close.index)


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "momentum" / "vwd.py"

CAUSALITY_MUTANTS = [
    ("close-lead", "    c = close.astype(float)",
     "    c = close.astype(float).shift(-1)"),
    ("ema-lead", "    e = ema(c, length=FAST)",
     "    e = ema(c, length=FAST).shift(-1)"),
    ("sma-lead", "    madif = (sma(c, length=SLOW) - e) / e * PERCENT",
     "    madif = (sma(c, length=SLOW).shift(-1) - e) / e * PERCENT"),
    ("vp-lead", "    vp = ((c - l) - (h - c)) / rng.where(rng > 0.0)",
     "    vp = (((c - l) - (h - c)) / rng.where(rng > 0.0)).shift(-1)"),
    ("vs-lead", "    vs = sma(vp.abs(), length=SLOW)",
     "    vs = sma(vp.abs().shift(-1), length=SLOW)"),
    ("output-early", "    vwd = vwd.where(np.isfinite(vwd))",
     "    vwd = vwd.where(np.isfinite(vwd)).shift(-1)"),
]

BLIND_SPOT_MUTANTS = [
    ("vs-lagged", "    vs = sma(vp.abs(), length=SLOW)",
     "    vs = sma(vp.abs(), length=SLOW).shift(1)"),
    ("ema-slow", "    e = ema(c, length=FAST)",
     "    e = ema(c, length=SLOW)"),
    ("over-sma", "    madif = (sma(c, length=SLOW) - e) / e * PERCENT",
     "    madif = (sma(c, length=SLOW) - e) / sma(c, length=SLOW) * PERCENT"),
]

#: Unequal suffix factors for (high, low, close): vp is invariant under a
#: common rescale of one bar, so a uniform one cannot see a vp lead.
FACTORS = (1.02, 1.01, 1.03)


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["vwd"]


def _perturbed(frame, j):
    h, l, c, _ = frame
    at = np.arange(c.size) >= j
    fh, fl, fc = (Series(np.where(at, f, 1.0), index=c.index) for f in FACTORS)
    return h * fh, l * fl, c * fc


def _caught_at(fn, frame, j):
    a = fn(*frame[:3]).iloc[:j]
    b = fn(*_perturbed(frame, j)).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, frame):
    return sum(_caught_at(fn, frame, j) for j in OFFSETS)


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out with
    `ast` so the dictionary's cut rule is pinned rather than copied."""
    import ast
    import re
    path = ROOT / "docs" / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


# -------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    assert "vwd" in ta.Category["momentum"]
    assert hasattr(ta.momentum, "vwd")
    h, l, c, _ = _frame("walk")
    col = vwd(h, l, c)
    assert col.name == COLUMN
    assert col.category == "momentum"
    df = DataFrame({"high": h.to_numpy(), "low": l.to_numpy(),
                    "close": c.to_numpy()})
    out = df.ta.vwd()
    assert out.name == COLUMN
    assert out.equals(vwd(h.reset_index(drop=True), l.reset_index(drop=True),
                          c.reset_index(drop=True)))


def test_the_constants_are_the_posters_numbers():
    assert (FAST, SLOW, PERCENT, GAIN) == (7, 14, 100.0, 10.0)
    assert MIN_BARS == SLOW
    import inspect
    assert list(inspect.signature(vwd).parameters) == [
        "high", "low", "close", "offset", "kwargs"]


@pytest.mark.parametrize("n", [0, 1, 7, 13])
def test_a_frame_below_min_bars_is_refused(n):
    h, l, c, _ = _frame("walk")
    assert vwd(h[:n], l[:n], c[:n]) is None


def test_the_shortest_frame_fires_on_exactly_its_last_bar():
    h, l, c, _ = _frame("walk")
    col = vwd(h[:MIN_BARS], l[:MIN_BARS], c[:MIN_BARS])
    assert int(col.notna().sum()) == 1
    assert bool(col.iloc[-1:].notna().all())


def test_offset_and_fillna():
    h, l, c, _ = _frame("walk")
    base = vwd(h, l, c)
    assert _bit_equal(vwd(h, l, c, offset=2), base.shift(2))
    filled = vwd(h, l, c, fillna=0.0)
    assert int(filled.isna().sum()) == 0


# --------------------------------------------------------------- Gate A


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_the_posters_formula_spelled_independently(name):
    """1,487 of 1,487 bars, identical NaN masks, measured up to 2.025e-13
    absolute, Spearman 1.0000."""
    h, l, c, v = _frame(name)
    a, o = vwd(h, l, c), _oracle(h, l, c, v)
    assert bool((a.isna() == o.isna()).all())
    assert int(a.notna().sum()) == FIRED
    assert _abs(a, o) < 1e-9


def test_gate_a_ema_leg_matches_talib():
    """`talib.EMA(close, 7)`, measured within 1.819e-12, first fire bar 6."""
    if importlib.util.find_spec("talib") is None:
        pytest.skip("talib is a dev-only dependency")
    import talib
    for name in VARYING:
        c = _frame(name)[2]
        a = ema(c, length=FAST)
        t = Series(talib.EMA(c.to_numpy(), FAST), index=c.index)
        assert bool((a.isna() == t.isna()).all())
        assert _abs(a, t) < 1e-9
        assert int(np.flatnonzero(a.notna().to_numpy())[0]) == FAST - 1


@pytest.mark.parametrize("bad", [0.0, float("nan")])
def test_volume_cancels_except_where_it_is_zero(bad):
    """The module does not read volume; the literal form is 0/0 at V == 0
    and NaN at V NaN, either of which blanks bars 700..713 of the literal
    form only (1,473 vs 1,487; §A4)."""
    h, l, c, v = _frame("walk")
    v = v.copy()
    v.iloc[700] = bad
    a, o = vwd(h, l, c), _oracle(h, l, c, v)
    assert int(a.notna().sum()) == FIRED
    assert int(o.notna().sum()) == FIRED - SLOW == 1473
    gone = np.flatnonzero((a.notna() & o.isna()).to_numpy())
    assert gone.tolist() == list(range(700, 700 + SLOW))


def test_an_inverted_range_is_blank_like_a_zero_range():
    """A deliberate deviation, pinned so it is not mistaken for the source:
    H < L is corrupt data, and the source's vp is finite there, but the
    module refuses to read a close location off an inverted range, so one
    swapped bar blanks itself and the next 13, exactly like H == L."""
    h, l, c, _ = _frame("walk")
    h, l = h.copy(), l.copy()
    h.iloc[700], l.iloc[700] = float(l.iloc[700]), float(h.iloc[700])
    col = vwd(h, l, c)
    assert int(col.notna().sum()) == FIRED - SLOW
    assert bool(col.iloc[700:700 + SLOW].isna().all())


@pytest.mark.parametrize("name", VARYING)
def test_a_bare_ewm_is_a_warm_up_transient_not_the_column(name):
    """`ewm(span=7)` from bar 0 differs on 53 .. 64 bars by > 1e-9, the
    last of them at bar 67 .. 80; never later than bar 100."""
    h, l, c, v = _frame(name)
    a, b = vwd(h, l, c), _oracle(h, l, c, v, ema_seed="bare")
    m = a.notna() & b.notna()
    diff = np.flatnonzero(np.abs(a[m].to_numpy() - b[m].to_numpy()) > 1e-9)
    assert 40 < diff.size < 80
    assert int(np.flatnonzero(m.to_numpy())[diff[-1]]) < 100


# --------------------------------------------------------------- Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_not_caught_by_the_future_sweep(name):
    assert _sweep(vwd, _frame(name)) == 0


@pytest.mark.parametrize("name", SWEPT)
@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """Prefix truncation cannot see back-dating; the mutants prove the
    sweep can. 36 of 36 each."""
    assert _sweep(_mutant(old, new), _frame(name)) == len(OFFSETS)


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_loudly_not_marginally(label, old, new):
    """Smallest first catch measured 7.490e-03, against an inexact rescale's
    1.717e-11 -- not a rounding artefact."""
    fn = _mutant(old, new)
    fr = _frame("walk")
    j = OFFSETS[0]
    assert _abs(fn(*fr[:3]).iloc[:j], fn(*_perturbed(fr, j)).iloc[:j]) > 1e-4


@pytest.mark.parametrize("name", SWEPT)
@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS[3:5],
                         ids=[m[0] for m in CAUSALITY_MUTANTS[3:5]])
def test_a_uniform_suffix_rescale_cannot_see_a_vp_lead(label, old, new, name):
    """Why FACTORS are unequal: vp is per-bar scale-invariant, so a uniform
    x1.03 suffix moves the `vp-lead` and `vs-lead` mutants' prefixes by
    rounding only -- measured 1.930e-14 .. 1.703e-13 and 2.359e-16 ..
    1.599e-14 over the three swept frames (§B1U)."""
    fn = _mutant(old, new)
    h, l, c, _ = _frame(name)
    j = OFFSETS[0]
    f = Series(np.where(np.arange(N) >= j, 1.03, 1.0), index=c.index)
    assert _abs(fn(h, l, c).iloc[:j], fn(h * f, l * f, c * f).iloc[:j]) < 1e-9


@pytest.mark.parametrize("label,old,new", BLIND_SPOT_MUTANTS,
                         ids=[m[0] for m in BLIND_SPOT_MUTANTS])
def test_the_sweeps_blind_spot_is_pinned_and_the_oracle_covers_it(label, old,
                                                                  new):
    """0 of 36 on the sweep; the oracle rejects all three by 3.737e-01 ..
    9.068e+00."""
    fn = _mutant(old, new)
    fr = _frame("walk")
    assert _sweep(fn, fr) == 0
    assert _abs(fn(*fr[:3]), _oracle(*fr)) > 1e-2


# --------------------------------------------------------------- Gate C


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    """1,487 of 1,500 from bar 13, no holes, > 1,400 distinct values."""
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert bool(col.iloc[:WARMUP].isna().all())
    assert bool(col.iloc[WARMUP:].notna().all())
    assert col.dropna().nunique() > 1400


def test_the_pooled_range_is_what_the_receipt_says():
    """-5.7406e+01 .. 4.9034e+01 over 8,922 bars, negative on 4,416, exactly
    0.0 on 19 (all on `grid`)."""
    import pandas as pd
    pooled = pd.concat([_col(n).dropna() for n in VARYING])
    assert pooled.size == FIRED * len(VARYING) == 8922
    assert int((pooled < 0).sum()) == 4416
    assert int((pooled == 0.0).sum()) == 19
    assert round(float(pooled.min()), 2) == -57.41
    assert round(float(pooled.max()), 2) == 49.03


def test_an_h_equals_l_bar_blanks_slow_bars():
    """15 H == L bars on `doji` blank 210 = 15 x 14 bars after the warm-up."""
    h, l, c, _ = _frame("doji")
    col = vwd(h, l, c)
    assert int((h == l).sum()) == 15
    assert int(col.iloc[WARMUP:].isna().sum()) == 15 * SLOW == 210
    assert int(col.notna().sum()) == 1277


def test_a_constant_close_reads_exactly_zero():
    """madif is 0 on a constant close, so all 1,487 bars read 0.0: why
    "not a constant column" is asserted on the varying frames only."""
    col = _col("flat")
    assert int(col.notna().sum()) == FIRED
    assert float(col.abs().max()) == 0.0


# --------------------------------------------------------------- Gate D


@pytest.mark.parametrize("name", VARYING + ["doji"])
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    h, l, c, _ = _frame(name)
    assert _bit_equal(vwd(h, l, c), vwd(h * factor, l * factor, c * factor))


@pytest.mark.parametrize("name", VARYING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """24 cells, every mask matching, worst 1.717e-11 absolute."""
    h, l, c, _ = _frame(name)
    base, other = vwd(h, l, c), vwd(h * factor, l * factor, c * factor)
    assert bool((base.isna() == other.isna()).all())
    assert _abs(base, other) < 1e-9


@pytest.mark.parametrize("name", VARYING)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    col = _col(name)
    assert 0 < int(col.notna().sum()) < N
    assert int(col.dropna().nunique()) > 1


@pytest.mark.parametrize("name", VARYING)
def test_a_level_shift_moves_the_column_so_scale_freeness_is_not_vacuous(name):
    """+10 on H, L and C moves 1,468 .. 1,487 of 1,487 bars (madif is a
    ratio of levels, not of differences)."""
    h, l, c, _ = _frame(name)
    base, other = vwd(h, l, c), vwd(h + 10, l + 10, c + 10)
    assert _differing_bars(base, other) > 1400
    assert _abs(base, other) > 1e-1


# -------------------------------------------------- documentation surface


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    body = []
    for line in vwd.__doc__.splitlines()[1:]:
        s = line.strip()
        if s:
            body.append(s)
        elif body:
            break
    full = " ".join(body)
    assert _generator_desc()({"desc": full}) == full


def test_the_receipt_says_gate_e_is_owed():
    text = (ROOT / "docs" / "VwdMeasured.md").read_text(encoding="utf-8")
    assert "Gate E" in text and "OWED" in text
    assert "VWD_7_14" in text
