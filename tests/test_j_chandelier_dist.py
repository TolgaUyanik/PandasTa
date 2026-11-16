# -*- coding: utf-8 -*-
"""J-CHANDELIER-DIST-22: `j_chandelier_dist`, the distance to the long
Chandelier Exit (PandasTa issue #122).

    tr[T]   = max(high - low, |high - close[T-1]|, |low - close[T-1]|)
    atr[T]  = Wilder(tr, 22), seeded with mean(tr[1..22])
    stop[T] = max(high[T-21..T]) - 3 * atr[T]
    J_CHANDELIER_DIST[T] = (close[T] - stop[T]) / close[T]

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently, with
   TA-Lib as the third speller.** A bar-by-bar oracle -- its own
   true-range loop, its own SMA seed, its own Wilder recursion over plain
   Python floats, its own 22-bar running maximum, sharing no code with the
   module -- agrees on **1,478 of 1,478** fired bars of each of six
   varying frames (8,868 pooled) with identical NaN masks, to **2.5e-16**
   absolute and **4.3e-12** relative. ⚠ NOT bit-equal, and §A1 names why
   rather than widening the bound and moving on: pandas' `ewm(adjust=
   False)` re-associates Wilder's step, and re-associating it by hand in
   the oracle moves the oracle by the same 2.5e-16. Asserted 1e-12
   absolute and 1e-9 relative, both of which a reduced numpy kernel also
   clears. `talib.MAX(high, 22) - 3 * talib.ATR(...)` -- the issue's two
   operators as TA-Lib spells them -- agrees to **2.4e-16** at Spearman
   1.0000 with identical NaN masks (talib 0.7.1); that test SKIPS where
   talib is absent rather than passing silently. `talib.TRANGE` is
   **bit-equal** to this module's true range and `talib.ATR(22)` first
   fires at index 22, so the two structural facts the warm-up rests on are
   run rather than recalled.
   ⚠ Neither jesse nor Skender is installed here and web access is
   unavailable (`test_the_source_libraries_are_not_installed_here` records
   it). What Gate A checks is the formula issue #122 quotes, and nothing in
   this file is a claim about what either library's code calls -- the
   reading of `ATR22` rests on Wilder's 1978 specification and on TA-Lib's
   `ATR`, which this worktree can run.

2. **WHICH ATR, and the alternatives pinned as different columns.** The
   reading taken is Wilder's ATR SEEDED with the mean of the first 22
   true ranges -- TA-Lib's. The **screen prototype's is not**:
   it recurses from bar 0 with no seed, and it disagrees with the shipped
   column on **655 .. 722** of 1,478 bars by up to **2.0e-02**, the last
   disagreement falling at bar **732 .. 808** (and at **717 .. 873** under
   reduced CPU dispatch, which is why the convergence is asserted at bar
   1,000). It also fires one bar
   earlier. This fork's `rma` (`adjust=True`), a plain `SMA(tr, 22)` and
   an `HH22` taken over the CLOSE are the other three readings, each
   pinned as a different column.
   ⚠ This is the one caveat on the screen's Gate E numbers: they were
   measured on the prototype's ATR.

3. **The inline true range is load-bearing, and only on the frames that
   can show it.** `pandas_ta.volatility.true_range` routes `high - low`
   through `non_zero_range`, whose epsilon is ABSOLUTE. On the six varying
   frames -- none of which has a `high == low` bar -- a `true_range`-based
   variant is **bit-equal** to this module, so the copy buys nothing
   there. On a frame with a doji every seventh bar it already fails Gate
   D's x8 cell at a price level of 100, and at 1e-6 it fails x8 and x64 on
   that frame and on a flat one. The module holds in all eight cells.

4. **Gate B is the sweep AND the oracle, because the sweep alone has a
   measured blind spot.** The module is caught at **0 of 36** perturbation
   offsets on every frame. Six look-ahead mutants are read off the shipped
   source, edited and `exec`'d in memory; every one is live and caught on
   **11 to 36** of those 36 offsets, the first catch moving a bar by
   **6.3e-04 .. 3.3e-02**.
   ⚠ A count below 36 is the FORMULA's: `hh` is a 22-bar MAXIMUM, so
   leading it by a bar changes nothing at an offset where the perturbed
   bar is not the one it selects.
   ⚠ **The blind spot, pinned rather than left for a reader to find.**
   Three edits make the true range read the WRONG close -- bar T's own, or
   the one before yesterday's -- or lag the highest high. None reads a
   later bar, so the sweep catches **0 of 36** of them; Gate A's oracle
   rejects all three, by **2.0e-02 .. 3.1e-01**.

5. **Gates C and D.** Every varying frame fires on 1,478 of 1,500 bars
   with 1,478 distinct values; x8/x64 is bit-identical, also at price
   levels 1e-6, 1e+6 and 1e+100; x10/x3.7/x0.1/x1.0000001 within
   **2.467e-11** relative, so the bound is asserted at 1e-9; `0 < fires <
   n`; and a level SHIFT of +10 moves all 1,478 fired bars, so the
   bit-identity is not vacuous. The column reads **-0.3163 .. 0.0639**
   over the six, negative on **3,759 of 8,868** bars and exactly 0.0 on
   none.
   ⚠ A FLAT frame is the exception and is pinned separately: it fires on
   all 1,478 and reads exactly **0.0** on every one, because the stop is
   the high and the high is the close. So "not a constant column" is
   asserted on the varying frames, not on every frame.

6. **A bad price empties DIFFERENT bars in each leg, and one leg empties
   none.** One NaN, +inf or -inf HIGH blanks exactly bars T .. T+21, 22 of
   them; a bad CLOSE blanks exactly its own bar; a bad LOW blanks
   **nothing at all** and still moves a BOUNDED RUN of later bars --
   measured 658, 608 and 400 bars at the three plant points, with the last
   differing bar at 808 for a plant at 100 -- because `low` reaches the
   output only through the true range, `wilder_rma` SKIPS a NaN
   observation instead of blanking it, and the Wilder recursion then
   forgets the perturbation at `(21/22)^k`. A bad close moves 669, 629 and
   399. ⚠ Not "every later bar": at a plant of 100 there are 1,400 later
   bars and 658 of them move. Everything before the planted bar is
   bit-identical in all three cases.

7. **Five guards, each priced separately, and all five load-bearing.** All
   five are no-ops on all nine ordinary frames. On probes built to reach
   them, the three input finite guards move the VALUES and not the NaN
   mask: with one `+inf` planted at bar 700 of a `walk`, removing the high
   guard moves **636** bars by up to 3.463e-04, the low guard **664** by
   1.112e-03 and the close guard **663** by 1.118e-03 -- while `fired` and
   the infinite count are identical either way. ⚠ Those counts are
   dispatch-dependent (**634 / 662 / 664** with AVX-512/AVX2/FMA3 off), so
   what is asserted is the shape: more than 300 bars, by more than 1e-5.
   ⚠ That is the correction an earlier draft of this header got wrong in
   the other direction ("moved nothing"), by reading the equal counts. The
   mechanism is NOT "pandas blanks it anyway": with the guard the bad leg
   is NaN and `max(axis=1)` SKIPS it, so the true range is the largest
   SURVIVING leg; without it the leg is infinite, the true range is
   infinite, and a pandas window DROPS that observation. A planted NaN is
   unaffected, because the guard only maps a non-finite value to the NaN it
   already is.
   The close-is-positive guard is the one that moves the MASK -- it stops a
   close of -50 shipping a sign-flipped reading -- and the final finite
   mask is the only thing between this column and **98 infinite readings of
   120** on a 1e300-stop-over-1e-300-close frame.
   ⚠ Three arithmetic routes to an infinity exist on FINITE inputs. Routes
   2 and 3 reach the output without the mask (97 and 98 readings of the
   probe frames' 120 bars, a length §G3 prints beside the counts); route 1
   does not, and the pandas behaviour that absorbs it is pinned on its own
   so an upgrade that moves it fails here.

8. **Gate E is MEASURED and DISCLOSE_GAP**, run by issue-solver on
   2026-11-16 (`is122-j_chandelier_dist-976ee44b`): max |rho| 0.8609 vs
   the manifest's `Range_Pos_20`, n = 396,891, top-five per-frame max
   median 0.8760 over 89 frames. DISCLOSE_GAP is a ship with a note, not
   a strike, so no column is removed and the row needs no waiver.
   ⚠ Single frames DO cross 0.90 -- 5 of the 89 on each of the top two
   comparators, and all five top comparators have a per-frame maximum of
   0.9119 .. 0.9239 -- but the band reads the MEDIAN, and the worst median
   is 0.8760. `test_the_gate_e_row_is_recorded_and_says_disclose_gap` pins
   the ledger row, including its run id, and
   `test_the_receipt_carries_the_measured_gate_e_numbers` pins the
   receipt. The same run gives Gate C its real-data limb, pinned by
   `test_gate_cs_real_data_limb_is_in_the_receipt`: 396,891 non-NaN of
   398,849 pooled bars, and all 396,891 of them non-zero.

Every number above is printed by `python docs/measure_j_chandelier_dist.py`
and by `python docs/measure_j_chandelier_dist_cpu.py <section>` under
numpy's reduced CPU dispatch -- EXCEPT the Gate E and Gate C real-data
figures of item 8, which come from the launcher's run and are read back out
of `docs/gate_e_ledger.csv` and the run's own CSVs -- and with the
exceptions `docs/JChandelierDistMeasured.md` lists above its §A1, of which
one matters here: the ASSERTED bounds quoted next to a measurement (1e-12
and 1e-9 in item 1, `> 300` bars and `> 1e-5` in item 7) are this file's
own constants rather than run output. The measured figure beside each of
them is a run. `docs/JChandelierDistMeasured.md` carries the tables.

NOT pinned here: Gate E's own arithmetic (the launcher ran it; 687
comparators over 89 real BIST frames, re-derived by
`tests/test_gate_e_ledger.py`). The in-fork overlap figures of §L are SYNTHETIC and are
disclosures, not gates -- and six synthetic frames read HIGH on all three
comparators where both a synthetic and a real figure now exist: +0.0421
(`Range_Pos_20`), +0.0436 (`ICHI_PRICE_VS_KIJUN`) and +0.0579 (`bias`) on
the per-frame median, §E4. ⚠ Those three of §L's eight were never "columns
Gate E cannot see": the port's own run lists all three inside its top
three comparators, so §L previewed the gate rather than being blind to it.
Whether the engine computes any of them through this fork was still not
checked in this repo.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, concat, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.trend.j_chandelier_dist import (MIN_BARS, MULT, PERIOD,
                                               j_chandelier_dist)
from pandas_ta.volatility.true_range import true_range

ROOT = Path(__file__).resolve().parents[1]

N = 1500
LEVEL = 100.0
COLUMN = "J_CHANDELIER_DIST_22_3.0"
#: The first bar that can fire on a clean frame, and so the warm-up: the
#: Wilder seed needs true ranges 1 .. PERIOD and the true range has no bar 0.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Bars a single bad HIGH removes: it is in exactly the PERIOD windows of
#: `high.rolling(PERIOD).max()` that end at T .. T+PERIOD-1. The true range
#: it also spoils costs nothing, because `wilder_rma` skips a NaN rather
#: than blanking it -- which is why a bad LOW blanks none.
EMPTIED_BY_A_BAD_HIGH = PERIOD


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_chandelier_dist.py`, so a number
# in this file and a number in the receipt are the same measurement.


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


def _tied(seed=29, n=N, level=LEVEL, every=7):
    """A walk with a doji every `every` bars -- `high == low == close`, the
    bar `non_zero_range` exists for."""
    h, l, c = _walk(seed, n, level)
    doji = np.arange(n) % every == 0
    return h.where(~doji, c), l.where(~doji, c), c


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising, "tied": _tied,
}
NAMES = list(FRAMES)
#: The six frames whose prices vary in both directions.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: Three of the six, for the sweeps: 6 mutants x 36 offsets x 2 calls each.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return j_chandelier_dist(*_frame(name))


def _scaled(frame, factor):
    high, low, close = frame
    return high * factor, low * factor, close * factor


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


# ---------------------------------------------------------------- oracles


def _oracle(high, low, close):
    """TA-Lib's rule, bar by bar, sharing no code with the module: true
    range undefined at bar 0, the Wilder seed is the mean of true ranges
    1 .. PERIOD, and `hh` is a plain running maximum."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    n = h.size
    nan = float("nan")
    tr = [nan] * n
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = [nan] * n
    if n > PERIOD:
        atr[PERIOD] = sum(tr[1:PERIOD + 1]) / PERIOD
        for i in range(PERIOD + 1, n):
            atr[i] = (tr[i] - atr[i - 1]) / PERIOD + atr[i - 1]
    hh = [nan] * n
    for i in range(PERIOD - 1, n):
        window = h[i - PERIOD + 1:i + 1]
        if not np.isnan(window).any():
            hh[i] = max(window)
    out = [nan] * n
    for i in range(n):
        if hh[i] == hh[i] and atr[i] == atr[i]:
            out[i] = (c[i] - (hh[i] - MULT * atr[i])) / c[i]
    return Series(out, index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate
    `j_chandelier_dist_22`, retyped (that file is gitignored, so it is on
    the owner's machine only):

        (c - (tsmax(h, 22) - 3 * atr_wilder(h, l, c, 22))) / c

    with `ind_screen.py`'s `atr_wilder` -- `ewm(alpha=1/22, adjust=False)`
    over a true range whose bar 0 is `high - low`, and NO SMA seed. ⚠ Not
    the shipped column.
    """
    prev = close.shift()
    tr = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / PERIOD, adjust=False).mean()
    return (close - (high.rolling(PERIOD).max() - MULT * atr)) / close


def _module_true_range(high, low, close):
    prev = close.shift(1)
    tr = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                axis=1).max(axis=1)
    tr.iloc[:1] = np.nan
    return tr


def _alt_sma(high, low, close):
    """`SMA(tr, 22)` instead of Wilder's."""
    tr = _module_true_range(high, low, close)
    return (close - (high.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * tr.rolling(PERIOD, min_periods=PERIOD).mean())
            ) / close


def _alt_hh_close(high, low, close):
    """`HH22` over the CLOSE rather than the high."""
    tr = _module_true_range(high, low, close)
    return (close - (close.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * wilder_rma(tr, length=PERIOD))) / close


def _alt_fork_true_range(high, low, close):
    """The same column with the fork's `true_range` -- i.e. with
    `non_zero_range`'s ABSOLUTE epsilon."""
    tr = true_range(high=high, low=low, close=close)
    return (close - (high.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * wilder_rma(tr, length=PERIOD))) / close


def _overflow_frame(route):
    """One of the three routes by which FINITE inputs can still produce an
    infinity. Same three frames and the same numbering -- the order they
    occur in the chain -- as `docs/measure_j_chandelier_dist.py`'s
    `_OVERFLOW_ROUTES`."""
    idx = date_range("2020-01-01", periods=120, freq="h")
    big = float(np.finfo(float).max)
    n = 120
    if route == "true-range":
        return (Series(np.full(n, big), index=idx),
                Series(np.full(n, -big), index=idx),
                Series(np.where(np.arange(n) % 2 == 0, -big, big), index=idx))
    if route == "stop":
        return (Series(np.full(n, big / 3.0), index=idx),
                Series(np.full(n, -big / 3.0), index=idx),
                Series(np.full(n, 1.0), index=idx))
    if route == "division":
        rng = np.random.default_rng(5)
        return (Series(1e300 * (1.0 + 0.01 * rng.random(n)), index=idx),
                Series(-1e300 * (1.0 + 0.01 * rng.random(n)), index=idx),
                Series(np.full(n, 1e-300), index=idx))
    raise ValueError(route)


def _talib():
    if importlib.util.find_spec("talib") is None:
        pytest.skip("talib is an optional dev dependency and is not installed")
    import talib
    return talib


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "trend" / "j_chandelier_dist.py"

#: (label, old, new). Edits to the SHIPPED source that make the OUTPUT read
#: a bar LATER than T. ⚠ Unlike `j_safezone_dist`, this chain holds no
#: forward `shift` between a price and the output, so a ONE-bar lead is
#: already a look-ahead and no two-bar leads are needed.
CAUSALITY_MUTANTS = [
    ("tr-high-lead",
     "    ranges = concat([high - low, (high - prev).abs(), (low - prev).abs()],",
     "    ranges = concat([high.shift(-1) - low, (high - prev).abs(), (low - prev).abs()],"),
    ("tr-prev-lead",
     "    prev = close.shift(1)",
     "    prev = close.shift(-1)"),
    ("atr-lead",
     "    atr = wilder_rma(tr, length=PERIOD)",
     "    atr = wilder_rma(tr.shift(-1), length=PERIOD)"),
    ("hh-lead",
     "    hh = hi.rolling(PERIOD, min_periods=PERIOD).max()",
     "    hh = hi.shift(-1).rolling(PERIOD, min_periods=PERIOD).max()"),
    ("close-lead",
     "    dist = (px - stop) / px",
     "    dist = (px.shift(-1) - stop) / px.shift(-1)"),
    ("output-early",
     "    dist = dist.where(np.isfinite(dist))",
     "    dist = dist.where(np.isfinite(dist)).shift(-1)"),
]

#: Edits that make the true range read the WRONG close, or lag the highest
#: high, without reading any LATER bar. The suffix sweep is blind to all
#: three; the oracle is not.
BLIND_SPOT_MUTANTS = [
    ("tr-today-close", "    prev = close.shift(1)", "    prev = close"),
    ("tr-two-days-ago", "    prev = close.shift(1)",
     "    prev = close.shift(2)"),
    ("hh-lag",
     "    hh = hi.rolling(PERIOD, min_periods=PERIOD).max()",
     "    hh = hi.shift(1).rolling(PERIOD, min_periods=PERIOD).max()"),
]

#: The five guards, each removable on its own, so each can be priced.
HI_GUARD_OFF = ("    hi = hi.where(np.isfinite(hi))", "    pass")
LO_GUARD_OFF = ("    lo = lo.where(np.isfinite(lo))", "    pass")
CL_GUARD_OFF = ("    cl = cl.where(np.isfinite(cl))", "    pass")
PX_GUARD_OFF = ("    px = cl.where(cl >= np.finfo(float).tiny)",
                "    px = cl")
FINITE_GUARD_OFF = ("    dist = dist.where(np.isfinite(dist))", "    pass")
GUARDS = [("high is finite", HI_GUARD_OFF), ("low is finite", LO_GUARD_OFF),
          ("close is finite", CL_GUARD_OFF),
          ("close is positive+normal", PX_GUARD_OFF),
          ("output is finite", FINITE_GUARD_OFF)]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_chandelier_dist"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on all three legs is not a global rescale -- the column is
    invariant under one of those, which is Gate D -- it is a rescale of a
    SUFFIX, which moves the true range and the highest high at bar j.
    """
    high, low, close = frame
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(high, low, close).iloc[:j]
    b = fn(high * f, low * f, close * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


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
    assert "j_chandelier_dist" in ta.Category["trend"]
    assert hasattr(ta.trend, "j_chandelier_dist")
    high, low, close = _frame("walk")
    col = j_chandelier_dist(high, low, close)
    assert col.name == COLUMN
    assert col.category == "trend"

    df = DataFrame({"high": high.to_numpy(), "low": low.to_numpy(),
                    "close": close.to_numpy()})
    out = df.ta.j_chandelier_dist()
    assert out.name == COLUMN
    assert out.equals(j_chandelier_dist(high.reset_index(drop=True),
                                        low.reset_index(drop=True),
                                        close.reset_index(drop=True)))


def test_the_source_libraries_are_not_installed_here():
    """Gate A reads the issue's QUOTE of jesse and Skender, not their code.
    Recorded as a test so the claim cannot rot into "checked against jesse"
    once someone pip-installs it."""
    assert importlib.util.find_spec("jesse") is None
    assert importlib.util.find_spec("stock_indicators") is None


def test_the_constants_are_the_issues_numbers():
    """"long (22, 3)", and nothing else is configurable."""
    assert (PERIOD, MULT) == (22, 3.0)
    assert MIN_BARS == PERIOD + 1
    assert COLUMN == f"J_CHANDELIER_DIST_{PERIOD}_{MULT}"
    import inspect
    params = list(inspect.signature(j_chandelier_dist).parameters)
    assert params == ["high", "low", "close", "offset", "kwargs"]


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS - 1` is also the index of the first firing bar, so the
    shortest frame that computes fires on exactly one."""
    high, low, close = _frame("walk")
    short = slice(None, MIN_BARS - 1)
    assert j_chandelier_dist(high[short], low[short], close[short]) is None
    exact = slice(None, MIN_BARS)
    col = j_chandelier_dist(high[exact], low[exact], close[exact])
    assert int(col.notna().sum()) == 1
    assert int(col.notna().to_numpy().argmax()) == MIN_BARS - 1


def test_offset_and_fillna():
    frame = _frame("walk")
    base = j_chandelier_dist(*frame)
    assert _bit_equal(j_chandelier_dist(*frame, offset=2), base.shift(2))
    filled = j_chandelier_dist(*frame, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert float(filled.iloc[0]) == 0.0


# -------------------------------------------------------------- Gate A


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """1,478 of 1,478 bars of each frame, identical NaN masks, measured
    2.5e-16 absolute and 4.3e-12 relative. ⚠ Not bit-equal, and the next
    test says why rather than leaving the bound unexplained."""
    frame = _frame(name)
    got, want = j_chandelier_dist(*frame), _oracle(*frame)
    assert bool((got.isna() == want.isna()).all())
    assert int(got.notna().sum()) == FIRED == 1478
    assert _abs(got, want) < 1e-12
    assert _rel(got, want) < 1e-9


@pytest.mark.parametrize("name", VARYING)
def test_the_gate_a_gap_is_the_wilder_step_re_associated(name):
    """WHY Gate A is a bound and not a bit-equality, measured rather than
    waved at: writing Wilder's step as `alpha*tr + (1-alpha)*atr[-1]`
    instead of `atr[-1] + (tr - atr[-1])/22` moves the ORACLE by the same
    order as the module-vs-oracle gap. pandas' `ewm(adjust=False)` uses one
    form and the oracle the other, and that is the whole of the
    disagreement."""
    frame = _frame(name)
    alpha = 1.0 / PERIOD
    h, l, c = (s.to_numpy(dtype=float) for s in frame)
    n = h.size
    tr = [float("nan")] * n
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = [float("nan")] * n
    atr[PERIOD] = sum(tr[1:PERIOD + 1]) / PERIOD
    for i in range(PERIOD + 1, n):
        atr[i] = alpha * tr[i] + (1.0 - alpha) * atr[i - 1]
    hh = Series(h, index=frame[2].index).rolling(
        PERIOD, min_periods=PERIOD).max()
    other = (frame[2] - (hh - MULT * Series(atr, index=frame[2].index))
             ) / frame[2]

    plain = _oracle(*frame)
    module = j_chandelier_dist(*frame)
    # The two oracle spellings disagree by the same order as the module
    # does with either of them, and every gap is in the last bits.
    assert not _bit_equal(plain, other)
    assert _abs(plain, other) < 1e-12
    assert _abs(module, other) <= _abs(module, plain) * 1e3 + 1e-15


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_talibs_max_and_atr(name):
    """`talib.MAX(high, 22) - 3 * talib.ATR(...)` is the issue's two
    operators as TA-Lib spells them, and a bare "ATR" conventionally means
    TA-Lib's Wilder ATR -- which is the reading this module takes.
    Measured 2.4e-16 absolute, Spearman 1.0000, on talib 0.7.1.
    ⚠ NOT a stand-in for jesse's code: jesse is not installed here and this
    file claims nothing about what it calls."""
    lib = _talib()
    high, low, close = _frame(name)
    h, l, c = (s.to_numpy(dtype=float) for s in (high, low, close))
    want = Series((c - (lib.MAX(h, PERIOD) - MULT * lib.ATR(h, l, c, PERIOD)))
                  / c, index=close.index)
    got = j_chandelier_dist(high, low, close)
    assert bool((got.isna() == want.isna()).all())
    assert int(got.notna().sum()) == FIRED
    assert _abs(got, want) < 1e-12
    assert _rel(got, want) < 1e-9


@pytest.mark.parametrize("name", VARYING)
def test_the_screen_prototype_is_a_different_column_on_the_warm_up(name):
    """⚠ The one caveat on the screen's Gate E figures. The prototype's ATR
    recurses from bar 0 with no SMA seed, so it disagrees on 655 .. 722 of
    1,478 bars by up to 2.0e-02, and the last disagreement falls at bar
    732 .. 808 here and at 717 .. 873 with AVX-512/AVX2/FMA3 disabled.
    Asserted as a shape -- it disagrees early, agrees late, and fires one
    bar sooner -- because the exact counts move with the frame AND with
    the numpy dispatch, which is why the convergence bound is taken at bar
    1,000 rather than at the measured last bar."""
    frame = _frame(name)
    got, proto = j_chandelier_dist(*frame), _prototype(*frame)
    assert _differing_bars(got, proto) > 300
    assert _abs(got, proto) > 1e-3
    # ... and the tail has converged: the recursion forgets its seed at
    # (21/22)^k, so by bar 1,000 the two agree to far better than any
    # downstream consumer resolves.
    assert _abs(got.iloc[1000:], proto.iloc[1000:]) < 1e-12
    # The prototype fires one bar earlier, because it needs no seed window.
    assert int(proto.notna().sum()) == FIRED + 1
    assert bool(proto.notna().iloc[WARMUP - 1])
    assert bool(got.isna().iloc[WARMUP - 1])


@pytest.mark.parametrize("name", VARYING)
def test_the_other_atr_readings_are_other_columns(name):
    """An `SMA(tr, 22)` and an `HH22` over the close are the two readings
    the issue's quote leaves open; both are different columns, not
    roundings of this one."""
    frame = _frame(name)
    got = j_chandelier_dist(*frame)
    for alt in (_alt_sma(*frame), _alt_hh_close(*frame)):
        # ⚠ A SHAPE, not a count. §A4 measures 1,477 of 1,478 for the SMA
        # reading and 1,294 .. 1,478 for the close-high one -- a 184-bar
        # spread across frames -- so a near-exact threshold here would be
        # six bars from failing on `grid` and would be a count pinned
        # against this file's own rules.
        assert _differing_bars(got, alt) > 0.8 * FIRED
        assert _abs(got, alt) > 1e-3
        assert 0.90 < _spearman(got, alt) < 1.0


def test_the_warm_up_is_the_chain_of_windows_not_the_number_22():
    """`tr` at 1, `hh` at PERIOD - 1, the Wilder seed at PERIOD, and the
    column with the LATER of the two. Spelled as the chain so a changed
    constant moves it."""
    high, low, close = _frame("walk")
    tr = _module_true_range(high, low, close)
    atr = wilder_rma(tr, length=PERIOD)
    hh = high.rolling(PERIOD, min_periods=PERIOD).max()

    def first(s):
        return int(s.notna().to_numpy().argmax())

    assert first(tr) == 1
    assert first(hh) == PERIOD - 1
    assert first(atr) == PERIOD
    assert first(j_chandelier_dist(high, low, close)) == WARMUP == PERIOD


def test_the_true_range_and_the_seed_are_talibs_run_not_recalled():
    """The two structural facts the warm-up rests on, checked against
    TA-Lib itself rather than against a memory of its lookbacks: `TRANGE`
    has lookback 1 (so bar 0 is undefined) and `ATR(22)` first fires at
    index 22 (so the seed is `mean(tr[1..22])`, not `mean(tr[0..21])`).
    Measured: bit-equal true range, and 1.110e-15 absolute between
    `wilder_rma(tr, 22)` and `talib.ATR`."""
    lib = _talib()
    high, low, close = _frame("walk")
    h, l, c = (s.to_numpy(dtype=float) for s in (high, low, close))
    tr = _module_true_range(high, low, close)
    ref_tr = Series(lib.TRANGE(h, l, c), index=close.index)
    ref_atr = Series(lib.ATR(h, l, c, PERIOD), index=close.index)

    assert int(ref_tr.notna().to_numpy().argmax()) == 1
    assert _bit_equal(tr, ref_tr)
    assert int(ref_atr.notna().to_numpy().argmax()) == PERIOD
    assert _abs(wilder_rma(tr, length=PERIOD), ref_atr) < 1e-12


def test_bar_zeros_true_range_is_undefined_and_that_moves_the_seed():
    """TA-Lib's `TRANGE` has lookback 1 and the prototype's has none. The
    module takes TA-Lib's, so its seed is `mean(tr[1..22])`; restoring bar
    0 moves the first firing bar AND 660 later ones."""
    high, low, close = _frame("walk")
    ship = j_chandelier_dist(high, low, close)
    restored = _mutant("    tr.iloc[:1] = np.nan", "    pass")(
        high, low, close)
    assert int(restored.notna().to_numpy().argmax()) == WARMUP - 1
    assert _differing_bars(ship, restored) > 100
    assert _abs(ship, restored) > 1e-5


# -------------------------------------------------------------- Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    assert _sweep(j_chandelier_dist, _frame(name)) == 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_every_mutant_is_live_before_it_is_caught(label, old, new, name):
    """A mutant that changes nothing would be caught at 0 offsets for the
    honest reason, which would make the sweep look clean and prove nothing.
    """
    frame = _frame(name)
    a, b = j_chandelier_dist(*frame), _mutant(old, new)(*frame)
    m = a.notna() & b.notna()
    assert int(m.sum()) > 0
    assert not bool((a[m].to_numpy() == b[m].to_numpy()).all())


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """⚠ Asserted as "at least one offset", not as 36 of 36, and that is a
    measurement rather than caution: the counts run 11 .. 36 because `hh`
    is a 22-bar MAXIMUM, so leading it changes nothing at an offset where
    the perturbed bar is not the one it selects."""
    assert _sweep(_mutant(old, new), _frame(name)) >= 1


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_loudly_not_marginally(label, old, new):
    """A catch of one bar by 1e-16 would be a rounding accident. Measured
    6.3e-04 .. 3.3e-02 at the first caught offset; asserted at 1e-5, which
    is still six orders above the 2.467e-11 an inexact rescale costs."""
    fn = _mutant(old, new)
    high, low, close = _frame("walk")
    for j in OFFSETS:
        if not _caught_at(fn, (high, low, close), j):
            continue
        f = Series(np.where(np.arange(close.size) >= j, 1.03, 1.0),
                   index=close.index)
        a = fn(high, low, close).iloc[:j]
        b = fn(high * f, low * f, close * f).iloc[:j]
        assert _abs(a, b) > 1e-5
        return
    pytest.fail(f"{label} was never caught, so its loudness is undefined")


@pytest.mark.parametrize("label,old,new", BLIND_SPOT_MUTANTS,
                         ids=[m[0] for m in BLIND_SPOT_MUTANTS])
def test_the_sweeps_blind_spot_is_pinned_and_the_oracle_covers_it(label, old,
                                                                  new):
    """Three edits that read the WRONG close, or lag the highest high. None
    reads a later bar, so the sweep catches none -- pinned in BOTH
    directions, because a sweep that started catching them would mean the
    module's shift structure had changed. Gate A's oracle rejects all
    three."""
    fn = _mutant(old, new)
    for name in ("walk", "heavy-tailed"):
        frame = _frame(name)
        assert _sweep(fn, frame) == 0
        assert not _bit_equal(fn(*frame), _oracle(*frame))
        assert _abs(fn(*frame), _oracle(*frame)) > 1e-3


# ---------------------------------------------------------- Gates C and D


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert bool(col.iloc[:WARMUP].isna().all())
    # Not a constant, and not a handful of repeated values either. ⚠ A
    # SHAPE: the measured value is 1,478 of 1,478 distinct on every one of
    # the six (§C1), and a count pinned ten from its measurement is the
    # thing this file bans elsewhere.
    assert int(col.dropna().nunique()) > 0.9 * FIRED
    assert int((col.dropna() == 0.0).sum()) == 0
    assert int((col.dropna() < 0.0).sum()) > 0


def test_the_pooled_range_is_what_the_receipt_says():
    """-0.3163 .. 0.0639 over the 8,868 fired bars of the six, negative on
    3,759. Asserted as bounds rather than as the digits, which move in the
    last bits between numpy dispatches."""
    pooled = Series(np.concatenate([_col(n).dropna().to_numpy()
                                    for n in VARYING]))
    assert len(pooled) == FIRED * len(VARYING) == 8868
    assert -0.35 < float(pooled.min()) < -0.31
    assert 0.06 < float(pooled.max()) < 0.07
    assert 3500 < int((pooled < 0).sum()) < 4000


def test_a_flat_frame_reads_exactly_zero_rather_than_nothing():
    """⚠ The exception to "not a constant column", and the reason that limb
    is asserted on the varying frames only. With `high == low == close`
    every true range is 0, so the ATR is 0, the stop IS the highest high,
    and the column is exactly 0.0 on all 1,478 bars it fires on."""
    col = _col("flat")
    assert int(col.notna().sum()) == FIRED
    assert int(col.dropna().nunique()) == 1
    assert float(col.dropna().iloc[0]) == 0.0


def test_a_one_way_market_still_fires_and_stays_positive():
    """`rising` has no drawdown at all, so the close never falls three ATRs
    below its 22-bar high: the column fires everywhere and is positive on
    every bar."""
    col = _col("rising")
    assert int(col.notna().sum()) == FIRED
    assert bool((col.dropna() > 0.0).all())


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    frame = _frame(name)
    assert _bit_equal(j_chandelier_dist(*frame),
                      j_chandelier_dist(*_scaled(frame, factor)))


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("level", [LEVEL, 1e-6])
def test_the_inline_true_range_is_what_keeps_gate_d(level, factor):
    """⚠ WHY this module spells its own true range instead of importing the
    fork's. `non_zero_range` adds an ABSOLUTE epsilon to the whole
    `high - low` leg as soon as one bar has `high == low`, so a variant
    built on it stops scaling with the price. On a frame with a doji every
    seventh bar the variant already fails x8 at a price level of 100, and
    at 1e-6 it fails both factors; this module holds in all four cells.
    ⚠ And the honest other half: on the six varying frames, none of which
    has a tied bar, the variant is BIT-EQUAL to this module -- the copy
    buys nothing there (`test_the_fork_true_range_variant_is_bit_equal_
    without_ties`)."""
    high, low, close = _tied()
    frame = ((high, low, close) if level == LEVEL else
             (high / LEVEL * level, low / LEVEL * level,
              close / LEVEL * level))
    assert int((frame[0].to_numpy() == frame[1].to_numpy()).sum()) > 0
    assert _bit_equal(j_chandelier_dist(*frame),
                      j_chandelier_dist(*_scaled(frame, factor)))
    assert not _bit_equal(_alt_fork_true_range(*frame),
                          _alt_fork_true_range(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", VARYING)
def test_the_fork_true_range_variant_is_bit_equal_without_ties(name):
    """The other half of the claim above, so the module's comment cannot
    overstate what the inline copy buys: with no `high == low` bar anywhere
    the epsilon never fires and the two spellings agree bit for bit."""
    frame = _frame(name)
    assert int((frame[0].to_numpy() == frame[1].to_numpy()).sum()) == 0
    assert _bit_equal(j_chandelier_dist(*frame), _alt_fork_true_range(*frame))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """Measured worst cell 2.467e-11 over the 24 (frame, factor) cells.
    Asserted 1e-9, which is more than an order above it, because the figure
    moves between numpy CPU dispatches."""
    frame = _frame(name)
    base = j_chandelier_dist(*frame)
    moved = j_chandelier_dist(*_scaled(frame, factor))
    assert bool((base.isna() == moved.isna()).all())
    assert _rel(moved, base) < 1e-9


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("level", [1e-6, 1e6, 1e100])
def test_gate_d_scale_at_extreme_price_levels(level, factor):
    """⚠ BOTH factors, not just x8, and the headroom is MEASURED rather
    than reasoned: the largest intermediate anywhere in the chain at 1e100
    is 6.438e+101 against DBL_MAX 1.798e+308, a factor of 2.792e+206
    (§D3)."""
    high, low, close = _frame("walk")
    frame = (high / LEVEL * level, low / LEVEL * level,
             close / LEVEL * level)
    base = j_chandelier_dist(*frame)
    assert int(base.notna().sum()) == FIRED
    assert _bit_equal(base, j_chandelier_dist(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    col = _col(name)
    assert 0 < int(col.notna().sum()) < len(col)


@pytest.mark.parametrize("name", VARYING)
def test_a_level_shift_moves_every_fired_bar(name):
    """The check that keeps the x8 bit-identity from being vacuous: the
    column is invariant under a RESCALE and not under a SHIFT, so it reads
    a ratio rather than nothing at all."""
    high, low, close = _frame(name)
    base = j_chandelier_dist(high, low, close)
    moved = j_chandelier_dist(high + 10.0, low + 10.0, close + 10.0)
    m = base.notna() & moved.notna()
    assert int(m.sum()) == FIRED
    assert int((base[m] != moved[m]).sum()) == FIRED


# --------------------------------------------------- guards and bad data


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("j", [100, 700, 1100])
def test_a_bad_high_empties_exactly_the_windows_that_hold_it(value, j):
    """22 bars, T .. T+21: the high reaches the output through
    `rolling(22).max()`, and a NaN is in exactly those 22 windows.
    Everything before T is bit-identical."""
    high, low, close = _frame("walk")
    base = j_chandelier_dist(high, low, close)
    hi = high.copy()
    hi.iloc[j] = value
    col = j_chandelier_dist(hi, low, close)
    gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
    assert gone.tolist() == list(range(j, j + EMPTIED_BY_A_BAD_HIGH))
    assert _bit_equal(base.iloc[:j], col.iloc[:j])


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("j", [100, 700, 1100])
def test_a_bad_close_empties_its_own_bar_and_no_other(value, j):
    high, low, close = _frame("walk")
    base = j_chandelier_dist(high, low, close)
    cl = close.copy()
    cl.iloc[j] = value
    col = j_chandelier_dist(high, low, cl)
    gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
    assert gone.tolist() == [j]
    assert _bit_equal(base.iloc[:j], col.iloc[:j])


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("j", [100, 700])
def test_a_bad_low_empties_nothing_and_is_still_not_harmless(value, j):
    """⚠ The row where this column and its NaN mask separate. `low` reaches
    the output only through the true range, and `wilder_rma` SKIPS a NaN
    observation rather than blanking it, so the ATR carries: no bar is
    emptied and a BOUNDED RUN of later bars reads a different number with
    no NaN to flag it -- measured 658 bars at a plant of 100 (of 1,400
    later bars; the last differing bar is 808) and 608 at 700, because the
    recursion forgets the perturbation at `(21/22)^k`. Both halves
    asserted, because the first alone reads as "a bad low does not
    matter"; the assertion is the shape (`> 100` bars), because the counts
    are a decay length and not a structural fact."""
    high, low, close = _frame("walk")
    base = j_chandelier_dist(high, low, close)
    lo = low.copy()
    lo.iloc[j] = value
    col = j_chandelier_dist(high, lo, close)
    assert int((base.notna() & col.isna()).sum()) == 0
    assert _bit_equal(base.iloc[:j], col.iloc[:j])
    assert _differing_bars(base.iloc[j:], col.iloc[j:]) > 100


@pytest.mark.parametrize("label,edit", GUARDS, ids=[g[0] for g in GUARDS])
@pytest.mark.parametrize("name", NAMES)
def test_every_guard_is_a_no_op_on_an_ordinary_frame(label, edit, name):
    frame = _frame(name)
    assert _bit_equal(j_chandelier_dist(*frame), _mutant(*edit)(*frame))


@pytest.mark.parametrize("leg,label,edit",
                         [("high", "high is finite", HI_GUARD_OFF),
                          ("low", "low is finite", LO_GUARD_OFF),
                          ("close", "close is finite", CL_GUARD_OFF)],
                         ids=["high", "low", "close"])
def test_the_three_input_guards_move_values_not_the_nan_mask(leg, label, edit):
    """⚠ The finding this test exists to stop coming back. §G2's `fired` and
    `inf` columns are IDENTICAL with and without each of these three
    guards, and the columns still differ on 634 … 664 of 1,478 bars
    (dispatch-dependent; 636 / 664 / 663 here, 634 / 662 / 664 with
    AVX-512/AVX2/FMA3 off): with
    the guard the bad leg is NaN and `max(axis=1)` SKIPS it, so the true
    range is the largest SURVIVING leg and the ATR takes it; without it the
    leg is infinite, the true range is infinite, and a pandas window DROPS
    that observation (`test_a_pandas_window_treats_an_infinity_as_a_
    missing_observation`). Pinned in BOTH directions -- equal counts AND
    unequal values -- because reading the equal counts alone is exactly how
    an earlier draft called these three guards decoration.

    A planted NaN is pinned too, and the other way: there the guard IS a
    no-op, because it only maps a non-finite value to the NaN it already
    is.
    """
    high, low, close = _frame("walk")
    bare = _mutant(*edit)

    h, l, c = high.copy(), low.copy(), close.copy()
    {"high": h, "low": l, "close": c}[leg].iloc[700] = np.inf
    with np.errstate(all="ignore"):
        ship, naked = j_chandelier_dist(h, l, c), bare(h, l, c)
    assert int(ship.notna().sum()) == int(naked.notna().sum())
    assert int(np.isinf(ship).sum()) == int(np.isinf(naked).sum()) == 0
    assert _differing_bars(ship, naked) > 300
    assert _abs(ship, naked) > 1e-5

    h, l, c = high.copy(), low.copy(), close.copy()
    {"high": h, "low": l, "close": c}[leg].iloc[700] = np.nan
    assert _bit_equal(j_chandelier_dist(h, l, c), bare(h, l, c))


def test_the_close_positivity_guard_is_the_one_that_bites():
    """A zero close would make the ratio infinite and a negative one flips
    the column's sign. Measured: with the guard removed the -50 bar FIRES
    instead of blanking, which is the sign flip shipping.

    ⚠ And the bar it blanks is the ONLY bar it blanks, not the only bar it
    moves. A zero or negative close is FINITE, so it survives the
    true-range guard and feeds `tr` at bar T and T+1; the ATR carries it
    forward and a bounded run of later bars reads a different number
    (measured 669 bars at a plant of 100 and 629 at 700, of 1,400 and 800
    later bars). The prefix is bit-identical and the suffix is not, and
    both are asserted so the first alone cannot be read as "this bar is
    quarantined".
    """
    high, low, close = _frame("walk")
    base = j_chandelier_dist(high, low, close)
    for bad in (0.0, -50.0):
        cl = close.copy()
        cl.iloc[700] = bad
        col = j_chandelier_dist(high, low, cl)
        gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
        assert gone.tolist() == [700]
        assert _bit_equal(base.iloc[:700], col.iloc[:700])
        assert _differing_bars(base.iloc[701:], col.iloc[701:]) > 100

    cl = close.copy()
    cl.iloc[700] = -50.0
    bare = _mutant(*PX_GUARD_OFF)(high, low, cl)
    assert bool(bare.notna().iloc[700])
    # The sign flip itself: every other fired bar of this frame is a small
    # number of either sign, and this one is the stop over a negative
    # close, which is a large POSITIVE reading.
    assert float(bare.iloc[700]) > 1.0


def test_the_finite_guard_is_not_a_no_op_where_the_division_overflows():
    """The frame where the final mask earns its line: a stop near 1e300
    over a close near 1e-300. Measured 98 infinite readings of 120 without
    it, 0 with it. This is route 3 of §G3's three."""
    frame = _overflow_frame("division")
    with np.errstate(all="ignore"):
        guarded = j_chandelier_dist(*frame)
        bare = _mutant(*FINITE_GUARD_OFF)(*frame)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) > 50


def test_route_2_also_reaches_the_output_without_the_mask():
    """⚠ Three routes, not one, and TWO of them reach the output here --
    unlike `j_safezone_dist`, where pandas' compensated `rolling.sum`
    absorbed two. Route 2 is the stop's own subtraction, `hh - 3 * atr`
    with an ATR near DBL_MAX / 3."""
    frame = _overflow_frame("stop")
    with np.errstate(all="ignore"):
        guarded = j_chandelier_dist(*frame)
        bare = _mutant(*FINITE_GUARD_OFF)(*frame)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) > 50


def test_route_1_never_reaches_the_output():
    """And the one that does not: an infinite true range. It cannot ship an
    infinity because of the pandas behaviour the next test pins."""
    frame = _overflow_frame("true-range")
    with np.errstate(all="ignore"):
        guarded = j_chandelier_dist(*frame)
        bare = _mutant(*FINITE_GUARD_OFF)(*frame)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) == 0
    assert int(guarded.notna().sum()) == 0


def test_a_pandas_window_treats_an_infinity_as_a_missing_observation():
    """The pandas BEHAVIOUR the previous test rests on, pinned separately
    so an upgrade that stops doing it fails HERE rather than shipping an
    infinite feature.

    Measured, and the contrast is the point:

    * one `+inf` at bar 40 of 81 -> the EWM reads 1.0 at bar 40, exactly as
      if the bar had not happened: 0 infinite readings, 0 NaN;
    * one DBL_MAX at the same bar -> 8.171e+306 at bar 40, so a merely
      huge observation flows straight through.

    `wilder_rma` inherits both, with its own 21-bar warm-up of NaNs.
    """
    big = float(np.finfo(float).max)
    with np.errstate(all="ignore"):
        infinite = Series([1.0] * 40 + [np.inf] + [1.0] * 40).ewm(
            alpha=1.0 / PERIOD, adjust=False).mean()
        huge = Series([1.0] * 40 + [big] + [1.0] * 40).ewm(
            alpha=1.0 / PERIOD, adjust=False).mean()
    assert int(np.isinf(infinite).sum()) == 0
    assert int(infinite.isna().sum()) == 0
    assert float(infinite.iloc[40]) == 1.0
    assert float(huge.iloc[40]) > 1e306

    with np.errstate(all="ignore"):
        through_helper = wilder_rma(
            Series([1.0] * 40 + [np.inf] + [1.0] * 40), length=PERIOD)
    assert int(np.isinf(through_helper).sum()) == 0
    assert int(through_helper.isna().sum()) == PERIOD - 1
    assert float(through_helper.iloc[40]) == 1.0


@pytest.mark.parametrize("value", [0.0, -100.0, 5e-310, 1e308])
def test_a_degenerate_frame_raises_nothing_and_ships_nothing_infinite(value):
    """A constant frame of any of these four raises nothing. The first
    three read NOTHING -- the close guard drops a zero, a negative and a
    subnormal -- and 1e308 reads exactly 0.0 on the 38 bars a 60-bar frame
    leaves after the warm-up."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="ignore"):
        col = j_chandelier_dist(s, s, s)
    assert int(np.isinf(col).sum()) == 0
    if value == 1e308:
        assert int(col.notna().sum()) == 60 - PERIOD
        assert int(col.dropna().nunique()) == 1
        assert float(col.dropna().iloc[0]) == 0.0
    else:
        assert int(col.notna().sum()) == 0


@pytest.mark.parametrize("n", [0, 1, 5, MIN_BARS - 1])
def test_a_frame_below_min_bars_is_refused_at_every_length(n):
    s = Series(np.full(n, 100.0),
               index=date_range("2020-01-01", periods=n, freq="h"))
    assert j_chandelier_dist(s, s, s) is None


def test_an_all_nan_frame_is_empty_rather_than_an_error():
    """`wilder_rma` returns None when no window of 22 bars is NaN-free, and
    the module turns that into an empty column rather than letting the None
    escape."""
    s = Series(np.full(100, np.nan),
               index=date_range("2020-01-01", periods=100, freq="h"))
    col = j_chandelier_dist(s, s, s)
    assert col is not None
    assert int(col.notna().sum()) == 0
    assert col.name == COLUMN


# -------------------------------------------------- documentation surface


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/IndicatorDictionary.md` is what CLAUDE.md tells a reader to
    consult before judging a column, and it prints the first paragraph cut
    at 150 characters. A cut sentence there is how a column gets
    misunderstood."""
    doc = j_chandelier_dist.__doc__.splitlines()
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
    assert "Chandelier" in cut and "ATR" in cut


def test_the_receipt_carries_the_measured_gate_e_numbers():
    """The receipt is the deliverable issue #122 asks for, and the Gate E
    run of 2026-11-16 has to live in it rather than only in the ledger."""
    doc = (ROOT / "docs" / "JChandelierDistMeasured.md").read_text(
        encoding="utf-8")
    assert "Gate E: measured 2026-11-16 by issue-solver" in doc
    assert "0.860867110309758" in doc         # the PORT's pooled max
    assert "0.87595405414863" in doc          # its per-frame max median
    assert "Range_Pos_20" in doc
    assert "DISCLOSE_GAP" in doc
    assert "r3-perframe-0.90" in doc
    assert "is122-j_chandelier_dist-976ee44b" in doc
    assert "0.8606" in doc              # the SCREEN's figure, still quoted
    # the "pending" wording this test replaced must be gone as a claim
    assert "Gate E: pending, run by issue-solver" not in doc


def test_the_gate_e_row_is_recorded_and_says_disclose_gap():
    """The receipt session's own cue: the row exists, names the one shipped
    column, and carries the verdict the `r3-perframe-0.90` bands give.

    Pins the run id as well as the arithmetic. This port's figures agree
    with the screen's PROTOTYPE to three digits (§E3), and an expected
    agreement is the easiest kind of row to copy over by mistake, so the
    row has to be THIS run's."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "j_chandelier_dist"]
    assert len(rows) == 1
    row = rows[0]
    assert row["column"] == COLUMN
    assert row["module"] == "pandas_ta.trend.j_chandelier_dist"
    assert row["verdict"] == "DISCLOSE_GAP"
    # the band: 0.80 <= pooled < 0.90, and no top-5 per-frame MEDIAN at 0.90
    assert 0.80 <= float(row["max_abs_rho"]) < 0.90
    assert float(row["perframe_max_median_abs_rho"]) < 0.90
    assert row["against"] == "Range_Pos_20"
    assert row["run"] == "is122-j_chandelier_dist-976ee44b"
    assert row["measured"] == "2026-11-16"
    assert row["waiver"] == ""                   # only STRUCK needs one


def test_gate_cs_real_data_limb_is_in_the_receipt():
    """Gate C's real-data counts come from the same run, and the receipt
    has to state them: a reachability claim measured only on synthetic
    frames is the defect CLAUDE.md names."""
    doc = (ROOT / "docs" / "JChandelierDistMeasured.md").read_text(
        encoding="utf-8")
    assert "396,891" in doc       # non-NaN, and non-zero, of 398,849
    assert "398,849" in doc
    assert "the real-data limb is OWED" not in doc
