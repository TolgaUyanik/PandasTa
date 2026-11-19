# -*- coding: utf-8 -*-
"""J-WAE: `j_wae`, Waddah Attar Explosion's power (PandasTa issue #123).

    macd[T] = EMA(close, 20)[T] - EMA(close, 40)[T]     both SMA-seeded
    t1[T]   = (macd[T] - macd[T-1]) * 150
    e1[T]   = BBupper(close, 20, 2)[T] - BBlower(close, 20, 2)[T]
    J_WAE[T] = t1[T] / e1[T]

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently, with this
   fork's own `macd` and `bbands` as the second and third spellers.** A
   bar-by-bar oracle -- its own `math.fsum` SMA seed, its own EMA
   recursion over plain Python floats, its own windowed mean and
   population variance, sharing no code with the module -- agrees on
   **1,460 of 1,460** fired bars of each of six varying frames (8,760
   pooled) with identical NaN masks, to **1.692e-10** absolute and
   **4.302e-11** relative at Spearman 1.0000. ⚠ NOT bit-equal, and the
   gap is ATTRIBUTED rather than excused: it is `e1`, where pandas'
   `rolling.var` is an online update and the oracle's is a two-pass
   `fsum`, and the ratio inherits it. Both EMA legs are bit-equal on two
   of the six frames (`grid`, `heavy-tailed`), and on the other four one
   leg differs by at most 2.842e-14.
   `test_the_gate_a_gap_is_the_rolling_variance` pins that, and it is the
   test whose FIRST draft blamed `t1`'s cancellation and failed, because
   `t1` is bit-equal on five of the six. Asserted 1e-7 absolute and 1e-7
   relative, both of which a reduced numpy kernel also clears.
   `macd(close, fast=20, slow=40)["MACD_20_40_9"]` is **bit-equal** to the
   module's MACD leg and `bbands(close, 20, 2.0)`'s upper minus lower is
   **bit-equal** to its `e1`, so neither half is a retyping of a shipped
   column. `talib.EMA(20) - talib.EMA(40)` is the same leg to
   **1.273e-11**, first firing at the same bar 39 (talib 0.7.1); that test
   SKIPS where talib is absent rather than passing silently.
   ⚠ jesse is not installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records it). What Gate
   A checks is the formula issue #123 quotes, and nothing in this file is
   a claim about what jesse's code does.

2. **WHICH EMA, and the readings not taken pinned as different columns.**
   The reading is the SMA-seeded EMA -- this fork's `ema`, and TA-Lib's.
   **The screen prototype's is not**: it recurses from bar 0 with no seed,
   and it disagrees with the shipped column on **1,399 .. 1,435** of the
   1,460 shared bars by up to **2.664e+00**, with the last disagreement at
   bar 1,499 of 1,500 on all six (1,496 on `range-bound` under numpy's
   reduced CPU dispatch) rather than washing out, and it fires 21
   bars earlier. pandas' `adjust=True` (1,065 .. 1,113 bars, up to
   4.495e+00) and a SAMPLE standard deviation in the width (all 1,460
   bars, up to 3.105e-01) are the other two readings, each pinned as a
   different column.
   ⚠ This is the one caveat on the screen's Gate E numbers: they were
   measured on the prototype's EMA.

3. **The width is the LITERAL band subtraction, not `2 * MULT * sd`.** The
   issue quotes "BB20,2 upper - lower" and this module spells exactly
   that. The algebraic form is a different column in the last bits --
   **1,357 .. 1,410** of 1,460 bars differ, by up to **5.329e-14** -- and
   Where the variance overflows (§G3) the two readings agree: both are
   inf on the overflowing bar and NaN on every later one.

4. **Gate B is the sweep AND the oracle, because the sweep alone has a
   measured blind spot.** The module is caught at **0 of 36** perturbation
   offsets on every one of six frames. Six look-ahead mutants are read off
   the shipped source, edited and `exec`'d in memory; every one is live
   and caught **36 of 36** on three frames, the first catch moving a bar
   by **2.539e-02 .. 1.937e+00**.
   ⚠ **The blind spot, pinned rather than left for a reader to find.**
   Reading the TWO-bar MACD change, lagging the width by a bar, or taking
   a sample standard deviation is wrong without reading any later bar: the
   sweep catches all three **0 of 36** times, and Gate A's oracle rejects
   all three, by **2.929e-01 .. 1.220e+01**.

5. **Gates C and D.** Every varying frame fires on **1,460 of 1,500** bars
   with 1,460 distinct values; x8/x64 is bit-identical, also at price
   levels 1e-6, 1e+6 and 1e+100; x10/x3.7/x0.1/x1.0000001 agrees to
   **5.267e-10** absolute with every NaN mask matching, so the bound is
   asserted at 1e-7; and `0 < fires < n`. The column reads **-8.7671e+00
   .. 1.2263e+01** over the six, negative on **4,297 of 8,760** bars and
   exactly 0.0 on **none**.
   ⚠ **The column is AFFINE-invariant, so the usual non-vacuity check does
   not work here.** A +10 level shift moves it by at most **3.564e-11**:
   every EMA of `close + k` is that EMA plus k, and a standard deviation
   ignores k. What shows the x8 bit-identity is not vacuous is a +1 %
   nudge at ONE bar, which moves **594 .. 800** of the 1,460 fired bars by
   up to **1.040e+00**, starting at the nudged bar.
   ⚠ Two degenerate frames are pinned separately. A CONSTANT close fires
   on **0 of 1,500** bars -- the width is exactly 0.0 on all 1,481 full
   windows. A straight RAMP fires on all 1,460 but reads
   **|value| <= 1.845e-12**, because the MACD of a ramp is constant. So
   "not a constant column" is asserted on the varying frames only.

6. **The close guard bites in the SEED and nowhere else, which is the
   opposite of what it looks like.** One `+inf` at bar 10 or 19 lands in
   an EMA seed -- a mean -- so without the guard the seed is infinite,
   pandas skips it as an observation, and **649** of 1,460 bars differ by
   up to **1.134e+01** with one bar LOST. At bar 39, 631 bars differ by up
   to 4.569e+00 with the masks equal. At bar 700 the two columns are
   **bit-equal**, because `ewm` skips an infinite observation exactly as
   it skips a NaN and a rolling window loses only the windows that contain
   it -- both probed directly, so an upgrade that moves either fails here.
   A planted NaN is unaffected by the guard in every position.

7. **The two output guards are ONE guard in two halves and are priced as
   a pair.** Each alone is a measured no-op on all nine frames: drop
   `e1 > 0` and the finite mask catches the same bars, drop the finite
   mask and `e1 > 0` already blanked them. Dropping BOTH is what ships an
   infinity -- on a `walk` held exactly flat over bars 400..600 the width
   is 0.0 on **182** bars while the EMAs are still converging, and the
   column reads 182 infinite values instead of firing on 1,278.
   ⚠ And the OVERFLOW route is **not reached**: three frames built to
   overflow the division on finite inputs ship 0 infinite readings with
   both guards off, so the finite mask's own load-bearing case is
   UNPROVEN here and this file says so instead of implying a measurement.

8. **Gate E is PENDING.** The launcher runs it after the porting session;
   `test_no_gate_e_row_is_recorded_yet` is the receipt session's cue and
   is expected to be REPLACED, not to keep passing. The screen's
   DISCLOSE_GAP figures (0.8698 vs `BB_PctB_Pctl`, n = 391,907) describe
   the PROTOTYPE, which item 2 measures as a different column.

Every number above is printed by `python docs/measure_j_wae.py` and by
`python docs/measure_j_wae_cpu.py <section>` under numpy's reduced CPU
dispatch, with the exceptions `docs/JWaeMeasured.md` lists above its §A1 --
of which one matters here: an ASSERTED bound quoted next to a measurement
(1e-7 in items 1 and 5) is this file's own constant, not run output. The
measured figure beside it is a run.

NOT pinned here: Gate E's own arithmetic. The in-fork overlap figures of
§L are SYNTHETIC and are a disclosure, not a gate -- `pgo`'s `PGO_14` at a
per-frame median 0.8580 over six frames against the screen's 0.8562 over
12 real ones.
"""
import csv
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.j_wae import (CHANNEL, FAST, MIN_BARS, MULT,
                                      SENSITIVITY, SLOW, j_wae)
from pandas_ta.overlap.ema import ema

ROOT = Path(__file__).resolve().parents[1]

N = 1500
LEVEL = 100.0
COLUMN = "J_WAE_150_20_40_20_2.0"
#: The first bar that can fire on a clean frame, and so the warm-up: the
#: SLOW EMA is SMA-seeded at index SLOW - 1 and `t1` differences it.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_wae.py`, so a number in this
# file and a number in the receipt are the same measurement. The high and
# the low are built even though `j_wae` reads only the close, because the
# frames are shared with `docs/measure_j_chandelier_dist.py`.


def _ohlc(close, seed):
    rng = np.random.default_rng(seed + 9_999)
    idx = date_range("2020-01-01", periods=close.size, freq="h")
    return (Series(close * (1.0 + 0.004 * rng.random(close.size)), index=idx),
            Series(close * (1.0 - 0.004 * rng.random(close.size)), index=idx),
            Series(close, index=idx))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), seed)


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))), seed)


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                 seed)


def _jump(seed=23, n=N, level=LEVEL):
    h, l, c = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f


def _flat(n=N, level=LEVEL):
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


def _rising(n=N, level=LEVEL, step=0.001):
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising,
}
NAMES = list(FRAMES)
#: The six frames whose prices vary in both directions.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: Three of the six, for the sweeps: 6 mutants x 36 offsets x 2 calls each.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _close(name):
    return _frame(name)[2]


def _col(name):
    return j_wae(_close(name))


def _stretch_frame(start=400, stop=601):
    """A `walk` held exactly flat over a stretch: the width is 0.0 once the
    window is inside it, while the two EMAs are still converging."""
    close = _close("walk").copy()
    close.iloc[start:stop] = float(close.iloc[start])
    return close


# ---------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _rel(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


def _last_differing_bar(a, b):
    m = a.notna() & b.notna()
    idx = np.flatnonzero(a[m].to_numpy() != b[m].to_numpy())
    if not idx.size:
        return -1
    return int(np.flatnonzero(m.to_numpy())[idx[-1]])


def _first_fire(col):
    nz = np.flatnonzero(col.notna().to_numpy())
    return int(nz[0]) if nz.size else -1


# ---------------------------------------------------------------- oracles


def _oracle(close):
    """The issue's formula, bar by bar, sharing no code with the module:
    its own `math.fsum` seed, its own EMA recursion, its own windowed mean
    and population variance, and the LITERAL band subtraction."""
    c = [float(x) for x in close.to_numpy(dtype=float)]
    n = len(c)
    nan = float("nan")

    def oracle_ema(length):
        out = [nan] * n
        if n < length:
            return out
        alpha = 2.0 / (length + 1.0)
        out[length - 1] = math.fsum(c[:length]) / length
        for i in range(length, n):
            out[i] = (1.0 - alpha) * out[i - 1] + alpha * c[i]
        return out

    fast, slow = oracle_ema(FAST), oracle_ema(SLOW)
    macd = [fast[i] - slow[i] for i in range(n)]
    out = [nan] * n
    for i in range(1, n):
        if i < CHANNEL:
            continue
        window = c[i - CHANNEL + 1:i + 1]
        mean = math.fsum(window) / CHANNEL
        var = math.fsum((x - mean) ** 2 for x in window) / CHANNEL
        dev = MULT * math.sqrt(var)
        e1 = (mean + dev) - (mean - dev)
        t1 = SENSITIVITY * (macd[i] - macd[i - 1])
        if e1 > 0.0 and t1 == t1 and e1 == e1:
            value = t1 / e1
            if math.isfinite(value):
                out[i] = value
    return Series(out, index=close.index)


def _oracle_legs(close):
    """The oracle's intermediate legs, so the Gate A gap can be ATTRIBUTED
    to one of them rather than guessed at. Same arithmetic as `_oracle`."""
    c = [float(x) for x in close.to_numpy(dtype=float)]
    n = len(c)
    nan = float("nan")

    def oracle_ema(length):
        out = [nan] * n
        alpha = 2.0 / (length + 1.0)
        out[length - 1] = math.fsum(c[:length]) / length
        for i in range(length, n):
            out[i] = (1.0 - alpha) * out[i - 1] + alpha * c[i]
        return out

    fast, slow = oracle_ema(FAST), oracle_ema(SLOW)
    macd = [fast[i] - slow[i] for i in range(n)]
    t1 = [nan] + [SENSITIVITY * (macd[i] - macd[i - 1]) for i in range(1, n)]
    e1 = [nan] * n
    for i in range(CHANNEL - 1, n):
        window = c[i - CHANNEL + 1:i + 1]
        mean = math.fsum(window) / CHANNEL
        var = math.fsum((x - mean) ** 2 for x in window) / CHANNEL
        dev = MULT * math.sqrt(var)
        e1[i] = (mean + dev) - (mean - dev)
    idx = close.index
    return {"ema20": Series(fast, index=idx), "ema40": Series(slow, index=idx),
            "macd": Series(macd, index=idx), "t1": Series(t1, index=idx),
            "e1": Series(e1, index=idx)}


def _t1(close):
    m = ema(close, length=FAST) - ema(close, length=SLOW)
    return SENSITIVITY * (m - m.shift(1))


def _e1(close):
    w = close.rolling(CHANNEL, min_periods=CHANNEL)
    mid, dev = w.mean(), MULT * np.sqrt(w.var(ddof=0))
    return (mid + dev) - (mid - dev)


def _ratio(t1, e1):
    out = t1 / e1.where(e1 > 0.0)
    return out.where(np.isfinite(out))


def _prototype(close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `j_wae`, retyped
    (that file is gitignored, so it is on the owner's machine only):

        m = ema(c, 20) - ema(c, 40)
        sdiv(150 * m.diff(), 4 * c.rolling(20).std(ddof=0))

    with that file's `ema` -- a bare `ewm(span=n, adjust=False)` from bar
    0, with NO SMA seed. ⚠ Not the shipped column."""
    m = (close.ewm(span=FAST, adjust=False).mean()
         - close.ewm(span=SLOW, adjust=False).mean())
    num = SENSITIVITY * m.diff()
    den = 2.0 * MULT * close.rolling(CHANNEL).std(ddof=0)
    return num / den.where(den > 0.0)


def _alt_adjust_true(close):
    m = (close.ewm(span=FAST, adjust=True).mean()
         - close.ewm(span=SLOW, adjust=True).mean())
    return _ratio(SENSITIVITY * (m - m.shift(1)), _e1(close))


def _alt_ddof_one(close):
    w = close.rolling(CHANNEL, min_periods=CHANNEL)
    mid, dev = w.mean(), MULT * np.sqrt(w.var(ddof=1))
    return _ratio(_t1(close), (mid + dev) - (mid - dev))


def _alt_algebraic_width(close):
    w = close.rolling(CHANNEL, min_periods=CHANNEL)
    return _ratio(_t1(close), 2.0 * MULT * np.sqrt(w.var(ddof=0)))


def _overflow_frame(kind, n=120):
    """A frame built to overflow the DIVISION on finite inputs: a higher
    price regime feeding `t1` through the 40-bar EMA while the width is
    computed over a tiny one. Same three as `docs/measure_j_wae.py`."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    rng = np.random.default_rng(5)
    hi, lo = {"tiny-to-subnormal": (1e-10, 1e-320),
              "huge-to-tiny": (1e200, 1e-100),
              "max-to-subnormal": (1e300, 1e-320)}[kind]
    base = np.full(n, lo)
    base[:60] = hi * (1.0 + 0.01 * rng.random(60))
    base[60:] = lo * (1.0 + np.arange(n - 60) % 3)
    return Series(base, index=idx)


def _talib():
    if importlib.util.find_spec("talib") is None:
        pytest.skip("talib is an optional dev dependency and is not installed")
    import talib
    return talib


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "momentum" / "j_wae.py"

#: (label, old, new). Edits to the SHIPPED source that make the OUTPUT read
#: a bar LATER than T.
CAUSALITY_MUTANTS = [
    ("close-lead", "    cl = cl.where(np.isfinite(cl))",
     "    cl = cl.where(np.isfinite(cl)).shift(-1)"),
    ("macd-lead", "    macd = ema(cl, length=FAST) - ema(cl, length=SLOW)",
     "    macd = (ema(cl, length=FAST) - ema(cl, length=SLOW)).shift(-1)"),
    ("t1-lead", "    t1 = SENSITIVITY * (macd - macd.shift(1))",
     "    t1 = SENSITIVITY * (macd.shift(-1) - macd)"),
    ("window-lead", "    window = cl.rolling(CHANNEL, min_periods=CHANNEL)",
     "    window = cl.shift(-1).rolling(CHANNEL, min_periods=CHANNEL)"),
    ("sd-lead", "    sd = np.sqrt(window.var(ddof=0))",
     "    sd = np.sqrt(window.var(ddof=0)).shift(-1)"),
    ("output-early", "    wae = wae.where(np.isfinite(wae))",
     "    wae = wae.where(np.isfinite(wae)).shift(-1)"),
]

#: Edits that are WRONG without reading any later bar. The suffix sweep is
#: blind to all three; Gate A's oracle is not.
BLIND_SPOT_MUTANTS = [
    ("t1-two-bar-change", "    t1 = SENSITIVITY * (macd - macd.shift(1))",
     "    t1 = SENSITIVITY * (macd - macd.shift(2))"),
    ("e1-lagged", "    e1 = (mid + dev) - (mid - dev)",
     "    e1 = ((mid + dev) - (mid - dev)).shift(1)"),
    ("sample-stdev", "    sd = np.sqrt(window.var(ddof=0))",
     "    sd = np.sqrt(window.var(ddof=1))"),
]

#: The three guards, each removable on its own, so each can be priced.
CL_GUARD_OFF = ("    cl = cl.where(np.isfinite(cl))", "    pass")
E1_GUARD_OFF = ("    wae = t1 / e1.where(e1 > 0.0)", "    wae = t1 / e1")
FINITE_GUARD_OFF = ("    wae = wae.where(np.isfinite(wae))", "    pass")
GUARDS = [("close is finite", CL_GUARD_OFF),
          ("width is positive", E1_GUARD_OFF),
          ("output is finite", FINITE_GUARD_OFF)]


def _mutant(*edits):
    """`j_wae` with one or more lines of the SHIPPED source replaced."""
    src = SOURCE.read_text(encoding="utf-8")
    if len(edits) == 2 and isinstance(edits[0], str):
        edits = [edits]
    for old, new in edits:
        assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
        src = src.replace(old, new)
    ns = {}
    exec(compile(src, "<mutant>", "exec"), ns)
    return ns["j_wae"]


def _caught_at(fn, close, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` is a rescale of a SUFFIX, not a global one -- the column is
    invariant under a global rescale, which is Gate D."""
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(close).iloc[:j]
    b = fn(close * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out with
    `ast` and compiled alone. Importing that module runs its whole
    indicator probe, and re-typing the cut here would pin a COPY of the
    rule rather than the rule."""
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
    """The five wiring touch points, through the three call styles."""
    assert "j_wae" in ta.Category["momentum"]
    assert hasattr(ta.momentum, "j_wae")
    close = _close("walk")
    col = j_wae(close)
    assert col.name == COLUMN
    assert col.category == "momentum"

    df = DataFrame({"close": close.to_numpy()})
    out = df.ta.j_wae()
    assert out.name == COLUMN
    assert out.equals(j_wae(close.reset_index(drop=True)))


def test_the_source_library_is_not_installed_here():
    """Gate A reads the issue's QUOTE of jesse, not jesse's code. Recorded
    as a test so the claim cannot rot into "checked against jesse" once
    someone pip-installs it."""
    assert importlib.util.find_spec("jesse") is None


def test_the_constants_are_the_issues_numbers():
    """"(MACD20/40 - MACD20/40[1])*150" over "BB20,2 upper - lower", and
    nothing is configurable."""
    assert (SENSITIVITY, FAST, SLOW, CHANNEL, MULT) == (150, 20, 40, 20, 2.0)
    assert MIN_BARS == SLOW + 1
    assert COLUMN == f"J_WAE_{SENSITIVITY}_{FAST}_{SLOW}_{CHANNEL}_{MULT}"
    import inspect
    params = list(inspect.signature(j_wae).parameters)
    assert params == ["close", "offset", "kwargs"]


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS - 1` is also the index of the first firing bar, so the
    shortest frame that computes fires on exactly one."""
    close = _close("walk")
    assert j_wae(close[:MIN_BARS - 1]) is None
    col = j_wae(close[:MIN_BARS])
    assert int(col.notna().sum()) == 1
    assert int(col.notna().to_numpy().argmax()) == MIN_BARS - 1


@pytest.mark.parametrize("n", [0, 1, 2, 20, 39, 40])
def test_a_frame_below_min_bars_is_refused_at_every_length(n):
    assert j_wae(_close("walk")[:n]) is None


def test_offset_and_fillna():
    close = _close("walk")
    base = j_wae(close)
    assert _bit_equal(j_wae(close, offset=2), base.shift(2))
    filled = j_wae(close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert float(filled.iloc[0]) == 0.0


# --------------------------------------------------------------- Gate A


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """1,460 of 1,460 bars of each frame, identical NaN masks, measured
    1.692e-10 absolute and 4.302e-11 relative at Spearman 1.0000. ⚠ Not
    bit-equal, and the next test says why rather than leaving the bound
    unexplained."""
    close = _close(name)
    got, want = j_wae(close), _oracle(close)
    assert bool((got.isna() == want.isna()).all())
    assert int(got.notna().sum()) == FIRED == 1460
    assert _first_fire(got) == WARMUP == 40
    assert _abs(got, want) < 1e-7
    assert _rel(got, want) < 1e-7
    assert _spearman(got, want) > 0.9999


@pytest.mark.parametrize("name", VARYING)
def test_the_gate_a_gap_is_the_rolling_variance(name):
    """WHY Gate A is a bound and not a bit-equality, measured leg by leg
    rather than waved at. ⚠ It is NOT the EMA: both EMA legs are
    bit-equal to the oracle's hand-rolled recursion on two of the six
    frames (`grid`, `heavy-tailed`), and on the other four one leg differs
    by at most 2.842e-14 -- in every case the leg whose `Series.mean()`
    seed is not equal to the oracle's `math.fsum` seed (§A1b). It is not
    `t1` either: bit-equal on five of the six frames, worst 1.866e-13
    relative. The gap is `e1`: pandas' `rolling.var` is an online update
    and the oracle's is a two-pass `fsum`, measured up to 4.302e-11
    relative -- and the column inherits that, because the ratio divides by
    it."""
    close = _close(name)
    t1_leg = _t1(close)
    legs = {"ema20": ema(close, length=FAST), "ema40": ema(close, length=SLOW),
            "macd": ema(close, length=FAST) - ema(close, length=SLOW),
            "e1": _e1(close)}
    oracle = _oracle_legs(close)
    assert _abs(legs["ema20"], oracle["ema20"]) < 1e-12
    assert _abs(legs["ema40"], oracle["ema40"]) < 1e-12
    assert _abs(legs["macd"], oracle["macd"]) < 1e-12
    e1_rel = _rel(legs["e1"], oracle["e1"])
    column_rel = _rel(j_wae(close), _oracle(close))
    assert e1_rel > 1e-14
    assert _rel(t1_leg, oracle["t1"]) < e1_rel
    assert column_rel <= e1_rel * 2.0 + 1e-15


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("length", [FAST, SLOW])
def test_the_forks_ema_is_still_sma_seeded(name, length):
    """A regression pin on the `ema` the module imports (§A2): at its
    defaults it blanks the first `length - 1` bars and seeds bar
    `length - 1` with the mean of the first `length` closes. That seeding
    is the load-bearing reading of "EMA" here (§A4), so a change to `ema`'s
    defaults must fail in this file, not only move the column."""
    close = _close(name)
    leg = ema(close, length=length)
    assert _first_fire(leg) == length - 1
    assert float(leg.iloc[length - 1]) == float(close.iloc[0:length].mean())


@pytest.mark.parametrize("name", VARYING)
def test_the_macd_leg_is_bit_equal_to_the_forks_macd(name):
    """"MACD20/40" is this fork's own MACD line, not a near relative."""
    from pandas_ta.momentum.macd import macd as fork_macd
    close = _close(name)
    mine = ema(close, length=FAST) - ema(close, length=SLOW)
    theirs = fork_macd(close, fast=FAST, slow=SLOW)[f"MACD_{FAST}_{SLOW}_9"]
    assert _bit_equal(mine, theirs)


@pytest.mark.parametrize("name", VARYING)
def test_the_width_leg_is_bit_equal_to_the_forks_bbands(name):
    """"BB20,2 upper - lower" is this fork's own `bbands`, at its own
    `ddof=0` default, subtracted the way the issue writes it."""
    from pandas_ta.volatility.bbands import bbands
    close = _close(name)
    bb = bbands(close, length=CHANNEL, std=MULT)
    theirs = bb[f"BBU_{CHANNEL}_{MULT}"] - bb[f"BBL_{CHANNEL}_{MULT}"]
    assert _bit_equal(_e1(close), theirs)


@pytest.mark.parametrize("name", VARYING)
def test_the_literal_width_is_not_the_algebraic_one(name):
    """`(mid + dev) - (mid - dev)` is not `2 * MULT * sd` in floating
    point: measured 1,357 .. 1,410 of 1,460 bars differ, by up to
    5.329e-14. The literal form is what the issue quotes."""
    close = _close(name)
    got, alg = j_wae(close), _alt_algebraic_width(close)
    assert _differing_bars(got, alg) > 1000
    assert _abs(got, alg) < 1e-12
    assert _spearman(got, alg) > 0.9999


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_talibs_ema_pair(name):
    """TA-Lib is the third speller of the MACD leg and the evidence that
    "EMA" conventionally means the SMA-seeded one: `talib.EMA` fires at the
    same bar 39 and agrees to 1.273e-11 (talib 0.7.1).
    ⚠ NOT a stand-in for jesse's code: jesse is not installed here."""
    lib = _talib()
    close = _close(name)
    c = close.to_numpy(dtype=float)
    theirs = Series(lib.EMA(c, FAST) - lib.EMA(c, SLOW), index=close.index)
    mine = ema(close, length=FAST) - ema(close, length=SLOW)
    assert bool((mine.isna() == theirs.isna()).all())
    assert _first_fire(theirs) == _first_fire(mine) == SLOW - 1
    assert _abs(mine, theirs) < 1e-8


@pytest.mark.parametrize("name", VARYING)
def test_the_screen_prototypes_ema_is_a_different_column(name):
    """The reading NOT taken, and the caveat on the screen's Gate E
    numbers. No SMA seed: it fires 21 bars earlier and disagrees on
    1,399 .. 1,435 of the 1,460 shared bars by up to 2.664e+00, with the
    last disagreement at bar 1,499 of 1,500 rather than washing out.
    ⚠ The last-differing bar is 1,499 on all six frames here and 1,496 on
    `range-bound` under numpy's reduced CPU dispatch, so what is asserted
    is "still differing near the end", not the index."""
    close = _close(name)
    got, alt = j_wae(close), _prototype(close)
    assert _first_fire(alt) == CHANNEL - 1 < _first_fire(got)
    assert _differing_bars(got, alt) > 1000
    assert _abs(got, alt) > 1e-2
    # it does not converge within the frame
    assert _last_differing_bar(got, alt) > N - 50
    assert _spearman(got, alt) > 0.99


@pytest.mark.parametrize("name", VARYING)
def test_pandas_adjust_true_is_a_different_column(name):
    """1,065 .. 1,113 of 1,460 bars, up to 4.495e+00."""
    close = _close(name)
    got, alt = j_wae(close), _alt_adjust_true(close)
    assert _differing_bars(got, alt) > 800
    assert _abs(got, alt) > 1e-2


@pytest.mark.parametrize("name", VARYING)
def test_a_sample_stdev_is_a_different_column(name):
    """Bollinger's bands take the POPULATION standard deviation, which is
    this fork's `bbands` default. `ddof=1` moves every one of the 1,460
    bars, by up to 3.105e-01, at a median |alt| / |this| of 0.9747 on
    every frame."""
    close = _close(name)
    got, alt = j_wae(close), _alt_ddof_one(close)
    assert _differing_bars(got, alt) == FIRED
    assert _abs(got, alt) > 1e-2
    # a wider divisor, so the column is smaller in magnitude
    ratio = (alt.dropna().abs() / got.dropna().abs()).median()
    assert 0.9 < float(ratio) < 1.0


# --------------------------------------------------------------- Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_not_caught_by_the_future_sweep(name):
    """Perturb every bar from J onward, assert nothing before J moves --
    36 J values on each of six frames, 0 catches."""
    assert _sweep(j_wae, _close(name)) == 0


@pytest.mark.parametrize("name", SWEPT)
@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """Prefix truncation cannot see back-dating, so the sweep is the test
    and the mutants are the proof that the sweep works. 36 of 36 each."""
    fn = _mutant(old, new)
    assert _sweep(fn, _close(name)) == len(OFFSETS)


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_loudly_not_marginally(label, old, new):
    """A catch worth 1e-16 would be a rounding artefact. The smallest first
    catch measured is 2.539e-02, against an inexact rescale's 5.267e-10."""
    fn = _mutant(old, new)
    close = _close("walk")
    j = OFFSETS[0]
    f = Series(np.where(np.arange(close.size) >= j, 1.03, 1.0),
               index=close.index)
    a, b = fn(close).iloc[:j], fn(close * f).iloc[:j]
    m = a.notna() & b.notna()
    assert float((a[m] - b[m]).abs().max()) > 1e-5


@pytest.mark.parametrize("label,old,new", BLIND_SPOT_MUTANTS,
                         ids=[m[0] for m in BLIND_SPOT_MUTANTS])
def test_the_sweeps_blind_spot_is_pinned_and_the_oracle_covers_it(label, old,
                                                                  new):
    """Three edits that are WRONG without reading a later bar. The sweep
    scores 0 of 36 on all three -- that is the limit of a causality test,
    stated here rather than left to be discovered -- and Gate A's oracle
    rejects all three by 2.929e-01 .. 1.220e+01."""
    fn = _mutant(old, new)
    close = _close("walk")
    assert _sweep(fn, close) == 0
    assert not _bit_equal(fn(close), j_wae(close))      # the mutant is live
    assert _abs(fn(close), _oracle(close)) > 1e-2       # and the oracle bites


# --------------------------------------------------------------- Gate C


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    """1,460 of 1,500 bars, a leading warm-up and no holes, and not a
    constant column."""
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert bool(col.iloc[:WARMUP].isna().all())
    assert bool(col.iloc[WARMUP:].notna().all())
    assert col.dropna().nunique() > 1400
    assert float(col.dropna().abs().max()) > 1.0


def test_the_pooled_range_is_what_the_receipt_says():
    """-8.7671e+00 .. 1.2263e+01 over 8,760 fired bars, negative on 4,297
    and exactly 0.0 on none. The bounds are asserted as a shape, because
    the extremes are one frame's."""
    import pandas as pd
    pooled = pd.concat([_col(n).dropna() for n in VARYING])
    assert pooled.size == FIRED * len(VARYING) == 8760
    assert -20.0 < float(pooled.min()) < -5.0
    assert 5.0 < float(pooled.max()) < 20.0
    assert 0.4 < float((pooled < 0).mean()) < 0.6
    assert int((pooled == 0.0).sum()) == 0
    assert float((pooled.abs() <= 10).mean()) > 0.95


def test_a_constant_close_is_blank_rather_than_constant():
    """The one frame shape where this column says nothing: a constant close
    has a Bollinger width of exactly 0.0 on all 1,481 full windows, so the
    `e1 > 0` guard blanks every bar. 0 of 1,500 fire, and that is the
    reason "not a constant column" is asserted on the varying frames."""
    close = _close("flat")
    col = j_wae(close)
    assert col is not None
    assert int(col.notna().sum()) == 0
    assert int((_e1(close) == 0.0).sum()) == N - CHANNEL + 1 == 1481
    assert float(_t1(close).abs().max()) == 0.0


def test_a_straight_ramp_fires_but_reads_zero():
    """A one-way arithmetic ramp: the MACD of a ramp is constant, so `t1`
    is zero up to the last bits. All 1,460 bars fire and every one reads
    |value| <= 1.845e-12 -- a second shape where the column is, in
    substance, saying nothing."""
    col = _col("rising")
    assert int(col.notna().sum()) == FIRED
    assert float(col.dropna().abs().max()) < 1e-9
    assert float(_e1(_close("rising")).min()) > 0.0


# --------------------------------------------------------------- Gate D


@pytest.mark.parametrize("name", VARYING)
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    """Both legs are homogeneous of degree 1 in the price and a power of
    two scales every intermediate exactly, so this is a bit-equality and
    not a tolerance."""
    close = _close(name)
    assert _bit_equal(j_wae(close), j_wae(close * factor))


@pytest.mark.parametrize("name", VARYING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """24 cells, every NaN mask matching, worst 5.267e-10 absolute.
    ⚠ Asserted on the ABSOLUTE gap: this column crosses zero, so a
    relative gap at a bar reading 1e-13 is a division by the cancellation
    rather than a scaling failure (measured 1.535e-07 relative pooled,
    4.964e-10 over the bars reading |value| >= 1e-3)."""
    close = _close(name)
    base, other = j_wae(close), j_wae(close * factor)
    assert bool((base.isna() == other.isna()).all())
    assert _abs(base, other) < 1e-7
    big = base.abs() >= 1e-3
    assert _rel(base[big], other[big]) < 1e-7


@pytest.mark.parametrize("name", VARYING[:3])
@pytest.mark.parametrize("level", [1e-6, 1e6, 1e100])
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_gate_d_scale_at_extreme_price_levels(name, level, factor):
    """The same rescale re-run three orders-of-magnitude regimes apart, so
    the bit-identity is not an artefact of prices near 100. At 1e100 the
    largest intermediate measured is 2.506e+101 against a DBL_MAX of
    1.798e+308."""
    close = _close(name) * (level / LEVEL)
    base = j_wae(close)
    assert int(base.notna().sum()) == FIRED
    assert _bit_equal(base, j_wae(close * factor))


@pytest.mark.parametrize("name", VARYING)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    """`0 < fires < n`, so a constant column cannot pass Gate D by being
    invariant for the wrong reason."""
    col = _col(name)
    assert 0 < int(col.notna().sum()) < N
    assert int(col.dropna().nunique()) > 1


@pytest.mark.parametrize("name", VARYING)
def test_the_column_is_affine_invariant_not_only_scale_free(name):
    """⚠ The usual non-vacuity check does NOT work here, and this test is
    where that is recorded. Every EMA of `close + k` is that EMA plus k
    and a standard deviation ignores k, so a +10 shift moves the column by
    at most 3.564e-11 -- noise, not a response. `test_a_one_bar_nudge_
    moves_the_column` is what shows the x8 bit-identity is not vacuous."""
    close = _close(name)
    base, other = j_wae(close), j_wae(close + 10.0)
    assert bool((base.isna() == other.isna()).all())
    assert _abs(base, other) < 1e-7


@pytest.mark.parametrize("name", VARYING)
def test_a_one_bar_nudge_moves_the_column(name):
    """A +1 % bump at ONE bar, which no rescale and no shift can imitate:
    594 .. 800 of the 1,460 fired bars move, by up to 1.040e+00, and the
    first bar that moves is the nudged one."""
    close = _close(name)
    base = j_wae(close)
    bumped = close.copy()
    bumped.iloc[700] = float(bumped.iloc[700]) * 1.01
    other = j_wae(bumped)
    assert _differing_bars(base, other) > 400
    assert _abs(base, other) > 1e-2
    m = base.notna() & other.notna()
    idx = np.flatnonzero(base[m].to_numpy() != other[m].to_numpy())
    assert int(np.flatnonzero(m.to_numpy())[idx[0]]) == 700


# ---------------------------------------------------------------- guards


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("label,edit", GUARDS, ids=[g[0] for g in GUARDS])
def test_every_guard_is_a_no_op_on_an_ordinary_frame(label, edit, name):
    """None of the three changes a single bit on a well-formed frame, so
    none of them is quietly shaping the column."""
    close = _close(name)
    assert _bit_equal(j_wae(close), _mutant(*edit)(close))


@pytest.mark.parametrize("value", [np.inf, -np.inf])
@pytest.mark.parametrize("bar", [10, 19])
def test_the_close_guard_bites_inside_the_ema_seed(value, bar):
    """An infinite close in the first SLOW bars lands in an EMA SEED --
    a mean -- so without the guard the seed is infinite, pandas skips it
    as an observation and the recursion starts a bar later from a raw
    close. Measured: 649 of 1,460 bars differ by up to 1.134e+01, and one
    bar is LOST (1,459 against 1,460)."""
    close = _close("walk").copy()
    close.iloc[bar] = value
    guarded, unguarded = j_wae(close), _mutant(*CL_GUARD_OFF)(close)
    assert int(guarded.notna().sum()) == FIRED
    assert int(unguarded.notna().sum()) == FIRED - 1
    assert not bool((guarded.isna() == unguarded.isna()).all())
    assert _differing_bars(guarded, unguarded) > 400
    assert _abs(guarded, unguarded) > 1.0


@pytest.mark.parametrize("value", [np.inf, -np.inf])
def test_the_close_guard_is_a_no_op_outside_the_seed(value):
    """⚠ The counter-intuitive half, measured rather than assumed: at bar
    700 the guard changes NOTHING, because pandas' `ewm` skips an infinite
    observation exactly as it skips a NaN and a rolling window loses only
    the windows that contain it. So this guard is not what keeps an
    infinity out of the output -- the two output guards are."""
    close = _close("walk").copy()
    close.iloc[700] = value
    guarded, unguarded = j_wae(close), _mutant(*CL_GUARD_OFF)(close)
    assert _bit_equal(guarded, unguarded)
    assert int(guarded.notna().sum()) == FIRED - CHANNEL


@pytest.mark.parametrize("bar", [10, 19, 700, 1400])
def test_a_nan_close_is_unaffected_by_the_guard(bar):
    """The guard only maps a non-finite value to the NaN it already is."""
    close = _close("walk").copy()
    close.iloc[bar] = np.nan
    assert _bit_equal(j_wae(close), _mutant(*CL_GUARD_OFF)(close))


def test_a_nan_close_costs_a_bounded_run_of_bars_not_the_frame():
    """One NaN at bar 700 removes exactly the CHANNEL windows that hold
    it; the EMA leg loses nothing, because `ewm` skips the observation."""
    close = _close("walk")
    bad = close.copy()
    bad.iloc[700] = np.nan
    col = j_wae(bad)
    assert int(col.notna().sum()) == FIRED - CHANNEL
    assert bool(col.iloc[700:700 + CHANNEL].isna().all())
    assert bool(col.iloc[700 + CHANNEL:].notna().all())


def test_pandas_skips_an_infinite_ewm_observation_and_a_window_recovers():
    """The two pandas behaviours the guard story rests on, probed directly
    so an upgrade that moves either fails HERE rather than silently
    changing the column."""
    import pandas as pd
    probe = pd.Series([1.0, 2.0, np.inf, 4.0, 5.0, 6.0, 7.0])
    ewm = probe.ewm(span=3, adjust=False).mean()
    assert np.isfinite(ewm.to_numpy()).all()
    assert float(ewm.iloc[2]) == float(ewm.iloc[1])     # the inf is skipped
    roll = probe.rolling(3).mean()
    assert bool(roll.iloc[2:5].isna().all())            # only its windows
    assert float(roll.iloc[5]) == 5.0                   # and it recovers


def test_the_two_output_guards_are_load_bearing_as_a_pair():
    """⚠ Each alone is a no-op -- the other catches the same bars -- so
    they are priced together. On a `walk` held exactly flat over bars
    400..600 the width is 0.0 on 182 bars while the EMAs are still
    converging, and with BOTH guards off the column ships 182 infinite
    values instead of firing on 1,278."""
    close = _stretch_frame()
    base = j_wae(close)
    one = _mutant(*E1_GUARD_OFF)(close)
    two = _mutant(*FINITE_GUARD_OFF)(close)
    both = _mutant(E1_GUARD_OFF, FINITE_GUARD_OFF)(close)

    assert _bit_equal(base, one)
    assert _bit_equal(base, two)
    zero_width = int((_e1(close) == 0.0).sum())
    assert zero_width > 150
    assert int(base.notna().sum()) == FIRED - zero_width
    assert int(np.isinf(both.to_numpy()).sum()) == zero_width
    # and the numerator is genuinely non-zero there, so it is a real
    # division by zero rather than a 0/0
    assert float(_t1(close)[_e1(close) == 0.0].abs().min()) > 0.0


@pytest.mark.parametrize("kind", ["tiny-to-subnormal", "huge-to-tiny",
                                  "max-to-subnormal"])
def test_the_overflow_route_is_not_reached(kind):
    """⚠ Stated as the negative it is: three frames built to overflow the
    division on finite inputs ship ZERO infinite readings even with both
    output guards off, so the finite mask's own load-bearing case is
    unproven in this repo. On `huge-to-tiny` and `max-to-subnormal` the
    variance overflows at bar 19 and pandas' rolling variance is NaN on
    all 100 later bars, so those frames fire on 0 bars."""
    close = _overflow_frame(kind)
    both = _mutant(E1_GUARD_OFF, FINITE_GUARD_OFF)(close)
    assert int(np.isinf(both.to_numpy()).sum()) == 0
    assert _bit_equal(j_wae(close), both)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, -1.0])
def test_a_degenerate_frame_raises_nothing_and_ships_nothing_infinite(value):
    """A whole frame of one pathological value: the column must be empty
    or finite, never infinite, and must not raise."""
    idx = date_range("2020-01-01", periods=200, freq="h")
    col = j_wae(Series(np.full(200, value), index=idx))
    assert col is not None
    assert int(np.isinf(col.to_numpy()).sum()) == 0


def test_an_all_nan_frame_is_empty_rather_than_an_error():
    idx = date_range("2020-01-01", periods=200, freq="h")
    col = j_wae(Series(np.full(200, np.nan), index=idx))
    assert col is not None
    assert int(col.notna().sum()) == 0
    assert col.name == COLUMN


# -------------------------------------------------- documentation surface


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/IndicatorDictionary.md` is what CLAUDE.md tells a reader to
    consult before judging a column, and it prints the first paragraph cut
    at 150 characters. A cut sentence there is how a column gets
    misunderstood."""
    doc = j_wae.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        s = line.strip()
        if s:
            body.append(s)
        elif body:
            break
    full = " ".join(body)
    cut = _generator_desc()({"desc": full})
    assert "…" not in cut
    assert cut == full
    assert not cut.rstrip().endswith(":")
    assert "MACD" in cut and "Bollinger" in cut


def test_the_receipt_says_gate_e_is_pending():
    """⚠ Expected to be REPLACED by the receipt session, not to keep
    passing: the launcher runs Gate E after this session and a later
    session writes the measured numbers in."""
    doc = (ROOT / "docs" / "JWaeMeasured.md").read_text(encoding="utf-8")
    assert "Gate E: pending, run by issue-solver after this session" in doc
    assert "0.8698" in doc             # the SCREEN's figure, on the prototype
    assert "BB_PctB_Pctl" in doc
    assert "DISCLOSE_GAP" in doc


def test_no_gate_e_row_is_recorded_yet():
    """The receipt session's cue. `tests/test_gate_e_ledger.py` fails on a
    local run until the row exists -- that is the owed-measurement state
    CLAUDE.md describes, not a defect in this port."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["indicator"] == "j_wae"]
    assert rows == []
