# -*- coding: utf-8 -*-
"""J-ACOSC: `j_acosc`, Bill Williams' acceleration oscillator over close
(PandasTa issue #106).

    mid     = (high + low) / 2
    AO      = SMA(mid, 5) - SMA(mid, 34)
    J_ACOSC = (AO - SMA(AO, 5)) / close

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled THREE ways.** An oracle
   that re-sums every window with `math.fsum` and shares no code with the
   module; the screen prototype; and this fork's OWN shipped `ao` + `sma`.
   All three agree with the module on **1,463 of 1,463** fired bars of
   each of seven frames (10,241 pooled) with identical NaN masks. The
   prototype and the `ao`/`sma` route are asserted BIT-equal -- the same
   operations in the same order, so machine-independent -- and the
   prototype limb is what ties this port to the 2026-10-24 screen's Gate E
   figures. The `fsum` oracle is asserted as a bound, and the ABSOLUTE one
   is the tight one: measured max |diff| 4.536e-16 (4.569e-16 under
   reduced CPU dispatch) against max |rel| 8.784e-11 (3.336e-11), because
   the column cancels down to 1e-16 on some bars and a relative bound
   there is noise.
   ⚠ jesse is NOT installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records it, so the
   claim cannot rot into "checked against jesse"). What Gate A checks is
   the formula issue #106 quotes.

2. **THE SUBTRACTION IS A HIGH-PASS FILTER, and that is the one
   structural thing to know about this column.** `AO - SMA(AO, 5)` is a
   linear FIR filter of `mid` with **38** taps. Pinned as the filter's own
   numbers, computed from `FAST`/`SLOW`/`SIGNAL` so that changing a
   constant fails here: |H(w)| is **0.000000 at DC**, peaks at
   **0.673744** at a period of **11.4939** bars, and reads **0.160000** at
   Nyquist, with sum |tap| = 0.80000000000000004 (0.8 to one ulp). The
   taps convolved against `mid` reproduce the module to 1e-14 absolute on
   every varying frame.
   ⚠ And the disclosure that goes with it: being blind to the price LEVEL
   does not make it independent of `AO`. Against `AO`'s own 1-bar change
   over close it reads Spearman **0.8638 .. 0.9016** over six frames;
   against the `AO / close` LEVEL, only 0.1187 .. 0.3026. The differencing
   IS the column, so "this is more than the Awesome Oscillator" is not an
   argument available at Gate E, where the screen measured the prototype
   at DISCLOSE_GAP -- max |rho| 0.8381 vs `FWMA_Slope_pct_Pctl`,
   n = 391,996, top-5 per-frame max median 0.8431.

3. **Gate B, as a mutant test.** Five look-ahead mutants are read off the
   shipped module's source, edited, and `exec`'d in memory. The module
   itself is caught at **0 of 36** perturbation offsets on each of six
   varying frames; every mutant at **36 of 36** on all six, and none of
   them is caught by being dead: on the `walk` frame every mutant moves
   every shared bar (1,445 of 1,445 for `fast-lead`, 1,462 of 1,462 for
   the other four). The ONE exception across the six frames is
   `divisor-lead` on `grid` at 1,456 of 1,462 -- six bars where the tick
   grid gives two consecutive equal closes, so tomorrow's close IS today's
   (`docs/JAcoscMeasured.md` §B2). Nothing cancels in this formula, so
   unlike `j_gator`'s teeth there is no blind spot to work around.
   ⚠ **Six frames and not seven, measured rather than argued.** The sweep
   multiplies bars >= J by 1.03, so a perturbed `flat` frame is a
   two-level STEP and four of the five mutants are caught on it at 36 of
   36. `divisor-lead` is not, at 0 of 36: a constant price makes `AO`
   exactly 0.0 on every pre-`J` bar, and `0.0 / c` is `0.0` whatever `c`
   is, so a divisor-only look-ahead is unobservable there. Excluding
   `flat` is what lets items above be asserted at full strength rather
   than with a four-of-five exception
   (`test_the_flat_frame_is_excluded_because_divisor_lead_cannot_be_caught_there`,
   §B5).
   The smallest single catch is **5.971e-08** -- two and a half orders
   above the 1.886e-10 an inexact rescale costs (item 5), so the sweep is
   reading a look-ahead and not float dust.
   ⚠ **`fast-lead` is misnamed and the real reach is 18 bars**, not 2:
   the anchor is `_sma`'s only line, so `center=True` centres EVERY mean,
   and pandas centres a window of length `n` by `(n - 1) // 2`, so the
   composite reach is 16 + 2 = 18. That one number explains all three of
   this mutant's anomalies -- it fires bars 19..1481 against the module's
   37..1499, it shares 1,445 = 1,463 - 18 bars, and it is the only mutant
   whose single catch moves more than one bar (18 of them).
   `test_the_fast_lead_mutant_reaches_eighteen_bars_not_two` pins it,
   because the first draft of this port explained it as "two bars at each
   end" and shipped that into four files.

4. **The warm-up is the two windows ADDED, not the longer of them.** The
   signal leg averages `AO`, not the price, so `AO`'s own **33** leading
   NaNs push the column's first fire to bar **37** = `SLOW + SIGNAL - 2`.
   `MIN_BARS` = 38 is a floor on the INPUT: a 37-bar frame returns `None`
   and a 38-bar frame fires on exactly 1 bar. The NaNs are a LEADING
   PREFIX, measured contiguous-from-zero on all seven frames.

5. **Gate D.** `x8`/`x64` are bit-identical on 1,463 of 1,463 bars of each
   of seven frames, and the same rescale REPEATED at price levels 1e-6,
   1e+6 and 1e+100 is bit-identical on 1,463 of 1,463 there too: every
   operation scales by an exact power of two and the final division
   cancels it. ⚠ ACROSS those three levels the column is NOT bit-equal --
   it agrees to 3.9e-15 relative on max |value|, 4.4e-15 under reduced
   CPU dispatch -- because 1e-6, 1e+6 and
   1e+100 are not exact binary multiples, so the three rebuilt price
   paths already differ in their last bits. `x10`, `x3.7`, `x0.1` and
   `x1.0000001` are not exact and
   are asserted as a relative bound (measured max **1.812e-10**,
   **1.886e-10** under reduced CPU dispatch, asserted 1e-7) with NaN masks
   matching -- the column is a difference of differences of nearby rolling
   means, so cancellation amplifies the last bits by orders of magnitude
   more than the inputs lose. `0 < fires < n` holds on all seven.

6. **WHICH SMA, decided and priced.** "SMA" is read as
   `rolling(n).mean()`, pandas' default `min_periods=n`: the prototype's
   spelling and the fork's own `sma`. ⚠ jesse's own source is NOT read
   (see item 1), so the reading rests on the issue's wording and on the
   prototype Gate E measured. Two neighbours are priced. Read as an
   exponential mean of the same period (`alpha = 2/(n+1)`) the same
   formula is a NEARBY column, not a far one -- Spearman 0.8966 .. 0.9277,
   0 bars in common -- which is why the reading is defended by the
   prototype's bit-equality (item 1) rather than by distance.
   `min_periods=1` is not a different column at all on the TAIL: it fires
   from bar 0 (1,500 bars instead of 1,463) and is bit-equal on all 1,463
   bars the module fires on.

7. **The guards, and the cases nothing guards.** A bad close empties its
   own bar and no other (NaN, 0.0, -1.0, ±inf, 1e-310 -- 1 bar each, 0
   other bars moved), which is what the guard buys: unguarded, a zero or
   subnormal close reads `inf` and a NEGATIVE close reads a
   plausible-looking -0.771217. A bad high OR low is NOT absorbed -- this
   is where `j_gator` and this column part company, because
   `rolling(...).mean()` empties a window holding a bad value instead of
   skipping the observation: one plant at bar 700 empties bars **700..737**
   (38 = `SLOW + SIGNAL - 1`) and NO bar before 700 moves. An infinite
   high or low gives a bit-identical column to a NaN one, on both legs and
   both signs, with 0 non-finite readings. ⚠ Bars AFTER the emptied run DO
   move, by up to 9.486e-12 relative (662 of them), and that is pandas'
   rolling accumulator re-summing from scratch rather than contamination.
   ⚠ NOT guarded: a frame whose high/low and close live hundreds of orders
   of magnitude apart overflows the division (23 of 23 fired bars
   infinite) -- bad data rather than a price, and pinned so the disclosure
   cannot rot.

8. **Gate E is DISCLOSE_GAP, and whose measurement the ledger row is.**
   `test_the_gate_e_row_is_this_ports_own_measurement` pins the row to run
   `is106-j_acosc-92ad5686` (2026-11-14, on THIS module): pooled **0.8381**
   against the manifest's `FWMA_Slope_pct_Pctl` at n = 391,996, top-five
   per-frame max median **0.8431** over 89 frames, 687 comparators, no
   waiver. That is the 0.80 .. 0.90 band -- a ship with a note, pinned as
   the band's two BOUNDS rather than as digits. The screen's PROTOTYPE read
   the same digits on 2026-10-24, which is why the row needs its identity
   pinned and not just its arithmetic.
   `test_the_gate_e_run_closes_gate_c_on_real_data` reads Gate C's real
   limb off the same row -- 395,556 of 398,849 bars fire, the 3,293 empty
   ones being exactly `WARMUP * 89`, and NO fired bar reads 0.0, so item
   4's exact-zero `flat` reading is synthetic-only.
   ⚠ Not pinned, because the band does not read it: no single one of the 89
   frames reaches 0.90 on any of the top five comparators (the worst is
   0.8822 on the top one, and 94.38 % of frames pass 0.80 there).

Every number above is printed by `python docs/measure_j_acosc.py` on this
worktree (pandas 2.3.3, numpy 1.26.4), and
`python docs/measure_j_acosc_cpu.py` re-runs this module -- and any named
section -- under numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled.
The full receipt is `docs/JAcoscMeasured.md`.

NOT pinned here: Gate E's own arithmetic (the launcher runs it; 687
comparators over 89 real BIST frames, re-derived by
`tests/test_gate_e_ledger.py`) -- item 8 pins the ROW it produced and the
real-data counts in it. The in-fork overlap figures of item 2 are SYNTHETIC
and are disclosures, not gates: the 687 engine comparators hold no
pandas_ta port, so the Gate E run cannot see them -- which is also why
item 2's invented `fwma` proxy (0.5283 .. 0.6155) understated the engine's
`FWMA_Slope_pct_Pctl` (0.8381) by roughly 0.22.
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
from pandas_ta.momentum.ao import ao as fork_ao
from pandas_ta.momentum.j_acosc import (FAST, MIN_BARS, SIGNAL, SLOW, WARMUP,
                                        j_acosc)
from pandas_ta.overlap.sma import sma as fork_sma

N = 1500
LEVEL = 100.0
COLUMN = "J_ACOSC_5_34_5"
FIRED = N - WARMUP
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where §G plants a bad bar, and the last bar its windows reach.
PLANT = 700
REACH = SLOW + SIGNAL - 1


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_acosc.py`, so a number in this
# file and a number in the receipt are the same measurement.


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


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
}
NAMES = list(FRAMES)
VARYING = [n for n in NAMES if n != "flat"]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _rel(a, b):
    """Max relative difference over the bars both fire on."""
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


# ----------------------------------------------------------------- oracles


def _mean_fsum(x, n):
    """`SMA(x, n)` by an explicit window and `math.fsum` -- correctly
    rounded, and sharing no code with pandas' Kahan-compensated roll-on /
    roll-off accumulator. A window holding a NaN stays NaN, which is
    pandas' `min_periods=n` spelled by hand."""
    out = np.full(x.size, np.nan)
    for i in range(n - 1, x.size):
        w = x[i - n + 1: i + 1]
        if np.isnan(w).any():
            continue
        out[i] = math.fsum(w.tolist()) / n
    return out


def _oracle(high, low, close):
    """The issue's formula, sharing no code with the module."""
    mid = (high.to_numpy(dtype=float) + low.to_numpy(dtype=float)) / 2
    ao = _mean_fsum(mid, FAST) - _mean_fsum(mid, SLOW)
    return Series((ao - _mean_fsum(ao, SIGNAL))
                  / close.to_numpy(dtype=float), index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen.py`, candidate `j_acosc`, retyped
    (that file is gitignored, so it is on the owner's machine only):

        mid = (h + l) / 2
        ao = mean(mid, 5) - mean(mid, 34)
        return (ao - mean(ao, 5)) / c

    with the screen's `def mean(x, n): return x.rolling(n).mean()`."""
    mid = (high + low) / 2
    mean = lambda x, n: x.rolling(n).mean()  # noqa: E731
    ao = mean(mid, 5) - mean(mid, 34)
    return (ao - mean(ao, 5)) / close


def _fork_route(high, low, close):
    """The same formula over the fork's OWN `ao` and `sma`."""
    a = fork_ao(high, low)
    return (a - fork_sma(a, SIGNAL)) / close


def _ema_column(high, low, close):
    """The reading NOT taken: an exponential mean of the same period
    (`alpha = 2/(n+1)`, seeded at bar 0) wherever the formula says SMA."""
    mid = (high + low) / 2
    m = lambda x, n: x.ewm(span=n, adjust=False).mean()  # noqa: E731
    a = m(mid, FAST) - m(mid, SLOW)
    return (a - m(a, SIGNAL)) / close


def _min_periods_one(high, low, close):
    """The reading NOT taken: partial windows, `min_periods=1`."""
    mid = (high + low) / 2
    mean = lambda x, n: x.rolling(n, min_periods=1).mean()  # noqa: E731
    a = mean(mid, FAST) - mean(mid, SLOW)
    return (a - mean(a, SIGNAL)) / close


# -------------------------------------------------------------- the filter


def _taps():
    """The column's FIR taps in `mid`, built from the module's constants:
    `out[T] * close[T] = sum_k h[k] * mid[T - k]`."""
    a = np.zeros(SLOW)
    a[:FAST] += 1.0 / FAST
    a -= 1.0 / SLOW
    signal = np.convolve(a, np.full(SIGNAL, 1.0 / SIGNAL))
    h = np.zeros(signal.size)
    h[:a.size] += a
    h -= signal
    return h


def _gain(h, w):
    k = np.arange(h.size)
    return float(np.abs(np.sum(h * np.exp(-1j * w * k))))


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "momentum" \
    / "j_acosc.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    ("mid-lead", "    mid = (high + low) / 2",
     "    mid = ((high + low) / 2).shift(-1)"),
    ("fast-lead", "    return x.rolling(length).mean()",
     "    return x.rolling(length, center=True).mean()"),
    ("ao-lead", "    acosc = (ao - _sma(ao, SIGNAL)) / c",
     "    acosc = (ao.shift(-1) - _sma(ao, SIGNAL)) / c"),
    ("output-early", "    acosc = (ao - _sma(ao, SIGNAL)) / c",
     "    acosc = ((ao - _sma(ao, SIGNAL)) / c).shift(-1)"),
    ("divisor-lead", "    acosc = (ao - _sma(ao, SIGNAL)) / c",
     "    acosc = (ao - _sma(ao, SIGNAL)) / c.shift(-1)"),
]
#: Not a causality mutant: the close guard, removed, to price what it buys.
CLOSE_GUARD_OFF = (
    "c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))",
    "c = close")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_acosc"]


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test -- and re-typing the cut here would pin a COPY of
    the rule rather than the rule. This compiles the generator's actual
    function, so a change to its cut reaches this test."""
    import ast
    import re
    path = Path(__file__).resolve().parents[1] / "docs" \
        / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?"""
    h, l, c = frame
    f = Series(np.where(np.arange(c.size) >= j, factor, 1.0), index=c.index)
    a = fn(h, l, c).iloc[:j]
    b = fn(h * f, l * f, c * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m] == b[m]).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


# -------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    """The five wiring touch points, through the three call styles."""
    assert "j_acosc" in ta.Category["momentum"]
    frame = _walk()
    col = j_acosc(*frame)
    assert col.name == COLUMN == f"J_ACOSC_{FAST}_{SLOW}_{SIGNAL}"
    assert col.category == "momentum"

    h, l, c = frame
    df = DataFrame({"high": h, "low": l, "close": c})
    assert hasattr(df.ta, "j_acosc")
    via_accessor = df.ta.j_acosc()
    assert via_accessor.name == COLUMN
    assert bool((via_accessor.dropna() == col.dropna()).all())


def test_the_source_library_is_not_installed_here():
    """Gate A is the issue's quoted formula, spelled three ways -- not a
    run of jesse. Pinned so the claim cannot rot into "checked against
    jesse" if the dependency ever appears."""
    assert importlib.util.find_spec("jesse") is None


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS` is a floor on the INPUT, one bar past the warm-up: one
    less and the function declines; at exactly `MIN_BARS` it fires on
    exactly one bar."""
    h, l, c = _walk()
    assert WARMUP == SLOW + SIGNAL - 2 == 37
    assert MIN_BARS == 38
    short = MIN_BARS - 1
    assert j_acosc(h.iloc[:short], l.iloc[:short], c.iloc[:short]) is None
    ok = j_acosc(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS], c.iloc[:MIN_BARS])
    assert int(ok.notna().sum()) == MIN_BARS - WARMUP == 1


def test_offset_and_fillna():
    frame = _walk()
    base = j_acosc(*frame)
    moved = j_acosc(*frame, offset=2)
    assert bool((moved.iloc[2:].dropna()
                 == base.iloc[:-2].dropna().to_numpy()).all())
    filled = j_acosc(*frame, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert int((filled.iloc[:WARMUP] == 0.0).sum()) == WARMUP


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """An explicit window summed with `math.fsum` against the module, on
    1,463 of 1,463 fired bars with identical NaN masks.

    ⚠ BOTH an absolute and a relative bound, and here the ABSOLUTE one is
    the tight one -- the reverse of `j_gator`. Measured max |diff|
    4.536e-16 (4.569e-16 under reduced CPU dispatch) against max |rel|
    8.784e-11 (3.336e-11): the column is a cancelling difference, so some
    bars read 1e-16 and a relative bound on those is measuring float dust.
    The relative limb is also vacuous on the `flat` frame, where the
    oracle is identically 0.0 and `_rel` has nothing to divide by, which is
    the other reason neither bound stands alone.
    """
    frame = FRAMES[name]()
    col, oracle = j_acosc(*frame), _oracle(*frame)
    assert bool((col.isna() == oracle.isna()).all())
    assert int(col.notna().sum()) == FIRED
    m = col.notna() & oracle.notna()
    assert int(m.sum()) == FIRED
    assert float((col[m] - oracle[m]).abs().max()) <= 1e-14
    assert _rel(col, oracle) <= 1e-9, _rel(col, oracle)


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_screen_prototype(name):
    """The prototype and the module perform the SAME operations in the same
    order (pandas' `rolling(n).mean()`), so bit-equality here is
    machine-independent and is asserted as such. This is the limb that ties
    this port to the 2026-10-24 screen's Gate E figures."""
    frame = FRAMES[name]()
    col, proto = j_acosc(*frame), _prototype(*frame)
    assert bool((col.isna() == proto.isna()).all())
    m = col.notna()
    assert int(m.sum()) == FIRED
    assert bool((col[m] == proto[m]).all())


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_forks_own_ao_and_sma(name):
    """The third spelling, and the one that says this port did not invent
    an Awesome Oscillator the fork already ships: `ao(high, low)` is
    `0.5 * (high + low)` through `sma(.., 5)` and `sma(.., 34)`, which is
    the issue's `AO`, and `sma` is the signal leg.

    Bit-equality also pins the reason `_sma` is spelled in the module
    instead of imported: `pandas_ta.overlap.sma` computes exactly
    `rolling(length, min_periods=length).mean()`, so the difference is the
    rename and the re-validation, not the arithmetic."""
    frame = FRAMES[name]()
    col, route = j_acosc(*frame), _fork_route(*frame)
    assert bool((col.isna() == route.isna()).all())
    m = col.notna()
    assert int(m.sum()) == FIRED
    assert bool((col[m] == route[m]).all())


@pytest.mark.parametrize("name", VARYING)
def test_the_ema_reading_is_a_nearby_column_not_a_far_one(name):
    """"SMA" read as an exponential mean of the same period
    (`alpha = 2/(n+1)`) gives a column with 0 bars in common -- and
    Spearman 0.8966 .. 0.9277, which is NEAR.

    That is stated as a bound rather than hidden: this reading is not
    defended by distance, it is defended by
    `test_gate_a_is_bit_equal_to_the_screen_prototype` -- the prototype
    Gate E measured spells `rolling(n).mean()`, and so does the issue's
    word "SMA". Pinned so that a future session cannot cite "the EMA
    reading would be a different column" as a reason, the way `j_gator`
    legitimately can (its figure is 0.5165 .. 0.7075)."""
    frame = FRAMES[name]()
    col, other = j_acosc(*frame), _ema_column(*frame)
    m = col.notna() & other.notna()
    assert int((col[m] == other[m]).sum()) == 0
    rho = _spearman(col, other)
    assert 0.85 < rho < 0.95, rho


@pytest.mark.parametrize("name", VARYING)
def test_min_periods_one_differs_only_on_the_head(name):
    """`min_periods=1` -- partial windows -- is NOT a different column on
    the tail: it fires from bar 0 (1,500 bars against the module's 1,463)
    and is bit-equal on every bar the module fires on.

    So the `min_periods` reading is a warm-up decision and nothing else,
    and the decision taken is the prototype's."""
    frame = FRAMES[name]()
    col, mp1 = j_acosc(*frame), _min_periods_one(*frame)
    assert int(mp1.notna().sum()) == N
    assert int(col.notna().sum()) == FIRED
    m = col.notna()
    assert bool((col[m] == mp1[m]).all())


def test_the_warmup_is_the_two_windows_added():
    """The trap `WARMUP` exists to name: the signal leg averages `AO`, not
    the price, so the two warm-ups ADD. `AO` itself has `SLOW - 1` = 33
    leading NaNs; the column has 37 = `SLOW + SIGNAL - 2`, four more.

    Counted on all seven frames, and the first fired bar is index 37."""
    for name in NAMES:
        frame = FRAMES[name]()
        col = j_acosc(*frame)
        assert int(col.isna().sum()) == WARMUP == 37
        assert int(col.notna().to_numpy().argmax()) == WARMUP
    a = fork_ao(*_walk()[:2])
    assert int(a.isna().sum()) == SLOW - 1 == 33
    assert WARMUP - int(a.isna().sum()) == SIGNAL - 1 == 4


@pytest.mark.parametrize("name", NAMES)
def test_the_nans_are_a_leading_prefix_and_nothing_else(name):
    """Contiguous from bar 0, on every frame: there is no hole anywhere in
    the middle of this column on a clean frame."""
    col = j_acosc(*FRAMES[name]())
    na = np.flatnonzero(col.isna().to_numpy())
    assert na.size == WARMUP
    assert bool((na == np.arange(na.size)).all())


# ----------------------------------------------------------------- the FIR


def test_the_filter_is_a_38_tap_high_pass_blind_to_the_price_level():
    """Item 2's numbers, computed from `FAST`/`SLOW`/`SIGNAL` so that
    changing a constant fails here rather than silently re-describing a
    different column.

    |H(0)| = 0 is asserted as a bound and not as a digit: the taps are
    built from 1/5 and 1/34, which are not exact binary fractions, so
    their sum is 6.939e-18 rather than 0.0 (measured by
    `python docs/measure_j_acosc.py F`). The FLAT frame reading exactly
    0.0 is a separate fact with a separate mechanism, and
    `test_reachability_and_the_flat_frame` pins it: both rolling means of
    a constant ARE that constant, bit for bit, so `AO` is exactly 0.0
    before any tap arithmetic happens."""
    h = _taps()
    assert h.size == SLOW + SIGNAL - 1 == 38
    assert abs(math.fsum(h.tolist())) < 1e-15
    assert _gain(h, 0.0) < 1e-15
    # `sum |tap|` is in item 2's pinned list, so it is pinned and not just
    # printed: measured 0.80000000000000004, i.e. 0.8 to one ulp.
    assert math.isclose(math.fsum(np.abs(h).tolist()), 0.8, rel_tol=1e-12)

    # The two extreme taps, derived from the constants rather than copied:
    # the heaviest is lag 0, `(1/FAST - 1/SLOW) * (1 - 1/SIGNAL)`, and the
    # lightest is lag FAST, where the fast window has just dropped out.
    assert int(h.argmax()) == 0
    assert math.isclose(float(h.max()),
                        (1.0 / FAST - 1.0 / SLOW) * (1.0 - 1.0 / SIGNAL),
                        rel_tol=1e-12)
    assert int(h.argmin()) == FAST == 5
    assert math.isclose(float(h.min()),
                        -1.0 / SLOW - (4.0 * (1.0 / FAST - 1.0 / SLOW)
                                       - 1.0 / SLOW) / SIGNAL,
                        rel_tol=1e-12)

    # Nyquist, also derived: an SMA of ODD length n passes an alternating
    # input at 1/n and an EVEN one kills it, so |H(pi)| is
    # |1/FAST - 0| * |1 - 1/SIGNAL| = 0.16 for (5, 34, 5).
    odd = lambda n: (1.0 / n) if n % 2 else 0.0  # noqa: E731
    assert math.isclose(_gain(h, np.pi),
                        abs(odd(FAST) - odd(SLOW)) * abs(1.0 - odd(SIGNAL)),
                        rel_tol=1e-12)

    w = np.linspace(1e-9, np.pi, 20_001)
    g = np.array([_gain(h, x) for x in w])
    k = int(g.argmax())
    assert math.isclose(g[k], 0.673744, abs_tol=1e-4), g[k]
    assert math.isclose(2 * np.pi / w[k], 11.4939, abs_tol=1e-2)
    # High-pass only in the sense that matters for a feature: the level is
    # removed, and the loudest band is a swing of about a fortnight of
    # daily bars rather than the shortest cycle available.
    assert _gain(h, 0.0) < _gain(h, np.pi) < g[k]


@pytest.mark.parametrize("name", VARYING)
def test_the_taps_are_the_column(name):
    """The filter of item 2 is not a description of the column, it IS the
    column: `h` dotted against the last 38 `mid` values and divided by
    close reproduces the module to 1e-14 absolute.

    A bound and not bit-equality -- a `math.fsum` dot product is not
    pandas' rolling accumulator -- and measured max |diff| 3.938e-16
    (4.036e-16 under reduced CPU dispatch)."""
    h = _taps()
    hi, lo, c = FRAMES[name]()
    mid = ((hi + lo) / 2).to_numpy(dtype=float)
    conv = np.full(mid.size, np.nan)
    for i in range(h.size - 1, mid.size):
        conv[i] = math.fsum((h * mid[i::-1][:h.size]).tolist())
    tap_col = Series(conv / c.to_numpy(dtype=float), index=c.index)
    col = j_acosc(hi, lo, c)
    m = col.notna() & tap_col.notna()
    assert int(m.sum()) == FIRED
    assert float((col[m] - tap_col[m]).abs().max()) <= 1e-14


@pytest.mark.parametrize("name", VARYING)
def test_the_column_is_near_the_ao_1_bar_change_and_far_from_its_level(name):
    """Item 2's disclosure, pinned as the inequality it is: differencing
    the Awesome Oscillator is the whole column.

    Against `AO`'s 1-bar change over close it reads 0.8638 .. 0.9016;
    against the `AO / close` level, 0.1187 .. 0.3026. Asserted as bands
    rather than digits -- the frames are built with `np.exp`, so a
    reduced kernel moves the last digit of a rank correlation -- and the
    point is the ORDER: a session reaching for "this is more than the AO"
    at Gate E has to pass this test first.

    ⚠ Neither comparator is a shipped `Category` column, and neither is
    in Gate E's 687. `AO_5_34` itself is a price LEVEL, which is why the
    level row is divided by close here."""
    frame = FRAMES[name]()
    hi, lo, c = frame
    col = j_acosc(*frame)
    a = fork_ao(hi, lo)
    assert 0.80 < _spearman(col, (a - a.shift(1)) / c) < 0.95
    assert 0.05 < _spearman(col, a / c) < 0.50


# ------------------------------------------------------------------ Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    """Gate B's blind limb: 36 perturbation offsets, and a causal column
    cannot be caught at any of them."""
    assert _sweep(j_acosc, FRAMES[name]()) == 0


@pytest.mark.parametrize("label, old, new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_every_mutant_is_live_before_it_is_caught(label, old, new):
    """A mutant that changes nothing would be caught at 0 of 36 and prove
    nothing. On the `walk` frame each of these moves EVERY bar it shares
    with the module -- measured 1,445 of 1,445 for `fast-lead` (18 fewer
    shared bars than the other four, which is its 18-bar reach; see
    `test_the_fast_lead_mutant_reaches_eighteen_bars_not_two`) and 1,462
    of 1,462 for the other four -- so the sweep result below is about
    causality and not about liveness.

    ⚠ `walk` and not all six, deliberately, because the claim is not true
    of all six: `divisor-lead` on the `grid` frame moves 1,456 of 1,462,
    the six unmoved bars being ones where the tick grid gives two
    consecutive equal closes, so tomorrow's close IS today's
    (`docs/JAcoscMeasured.md` §B2). Liveness only has to be enough to make
    the sweep meaningful, and 1,456 of 1,462 is; what would be dishonest is
    asserting "every bar on every frame" here and letting the exception sit
    in the receipt alone."""
    fn = _mutant(old, new)
    frame = _walk()
    base, mut = j_acosc(*frame), fn(*frame)
    m = base.notna() & mut.notna()
    assert int(m.sum()) > 1_400
    assert int((base[m] != mut[m]).sum()) == int(m.sum())


@pytest.mark.parametrize("name", VARYING)
@pytest.mark.parametrize("label, old, new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """All five look-ahead mutants at 36 of 36 on all six varying frames.

    Nothing cancels in this formula -- it is a sum of taps, not a pair of
    absolute values -- so unlike `j_gator`'s `teeth-lead` there is no
    mechanism that can hide a future read, and the gate is asserted at
    full strength. Why `VARYING` and not `NAMES` is
    `test_the_flat_frame_is_excluded_because_divisor_lead_cannot_be_caught_there`."""
    assert _sweep(_mutant(old, new), FRAMES[name]()) == len(OFFSETS) == 36


def test_the_flat_frame_is_excluded_because_divisor_lead_cannot_be_caught_there():
    """Why the sweep runs on six frames and not seven, measured.

    An earlier draft of this port ARGUED it -- "a perturbation of a
    constant price is still a constant price" -- which is false: `_sweep`
    multiplies bars >= J by 1.03, so a perturbed `flat` frame is a
    two-level STEP. Four of the five mutants are duly caught on it at 36
    of 36.

    `divisor-lead` is the exception, at 0 of 36, and the mechanism is
    specific: on a constant price `AO` is exactly 0.0 on every bar, so
    every pre-`J` numerator is exactly 0.0 and `0.0 / c` is `0.0`
    whatever `c` is -- a divisor-only look-ahead is unobservable through a
    zero numerator. Excluding `flat` is what lets
    `test_each_mutant_is_caught_by_the_future_sweep` assert 36 of 36 for
    all five rather than four-of-five on seven frames.

    The module itself is still asserted clean on `flat` here, so dropping
    the frame from `VARYING` does not drop it from Gate B's causal
    limb. `docs/JAcoscMeasured.md` §B5."""
    flat = _flat()
    assert _sweep(j_acosc, flat) == 0
    caught = {label: _sweep(_mutant(old, new), flat)
              for label, old, new in CAUSALITY_MUTANTS}
    assert caught["divisor-lead"] == 0
    assert all(v == 36 for k, v in caught.items()
               if k != "divisor-lead"), caught


def test_the_fast_lead_mutant_reaches_eighteen_bars_not_two():
    """`fast-lead`'s label is historical and its mechanism was explained
    wrongly in this port's first draft ("`center=True` costs two bars at
    each end"), so the real number is pinned here.

    The anchor is `_sma`'s ONLY line, so the mutation centres every mean --
    fast, slow and signal. pandas centres a window of length `n` by
    `(n - 1) // 2`, so the composite reach is
    `(SLOW - 1)//2 + (SIGNAL - 1)//2` = 16 + 2 = **18**, and that one
    number explains all three of the mutant's anomalies: it fires bars
    19..1481 against the module's 37..1499, it shares 1,445 = 1,463 - 18
    bars, and it moves 18 bars at a single catch where the other four move
    one. The expected reach is DERIVED from the module's constants rather
    than typed, so changing `SLOW` or `SIGNAL` fails here.
    `docs/JAcoscMeasured.md` §B4."""
    reach = (SLOW - 1) // 2 + (SIGNAL - 1) // 2
    assert reach == 18
    frame = _walk()
    fn = _mutant(*[m[1:] for m in CAUSALITY_MUTANTS
                   if m[0] == "fast-lead"][0])
    base, mut = j_acosc(*frame), fn(*frame)
    bi = np.flatnonzero(base.notna().to_numpy())
    mi = np.flatnonzero(mut.notna().to_numpy())
    assert int(bi.max()) - int(mi.max()) == reach
    assert int(bi.min()) - int(mi.min()) == reach
    assert int((base.notna() & mut.notna()).sum()) == FIRED - reach == 1445

    # And the catch: perturbing from bar j moves exactly j-reach .. j-1.
    h, l, c = frame
    j = OFFSETS[0]
    f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0), index=c.index)
    a, b = fn(h, l, c).iloc[:j], fn(h * f, l * f, c * f).iloc[:j]
    m = a.notna() & b.notna()
    moved = np.flatnonzero(m.to_numpy())[(a[m] != b[m]).to_numpy()]
    assert moved.size == reach
    assert (int(moved.min()), int(moved.max())) == (j - reach, j - 1)


def test_a_catch_is_orders_above_the_noise_an_inexact_rescale_costs():
    """What makes the sweep evidence rather than float dust. At the first
    offset of a walk, the smallest single bar a mutant moves is 5.971e-08
    -- `fast-lead`, which moves 18 bars rather than one, so its outermost
    bar is the faintest leak of the five (see
    `test_the_fast_lead_mutant_reaches_eighteen_bars_not_two`); the other
    four move one bar each by 7.515e-05 to 5.142e-03.

    The reference is Gate D's 1.886e-10: the most an inexact price rescale
    moves this column. Pinned as a ratio with two orders of headroom."""
    frame = _walk()
    h, l, c = frame
    j = OFFSETS[0]
    f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0), index=c.index)
    smallest = []
    for _, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        a, b = fn(h, l, c).iloc[:j], fn(h * f, l * f, c * f).iloc[:j]
        m = a.notna() & b.notna()
        d = (a[m] - b[m]).abs()
        hit = d[d > 0.0]
        assert hit.size > 0
        smallest.append(float(hit.min()))
    assert min(smallest) > 100 * 1.886e-10, min(smallest)


# ------------------------------------------------------------------ Gate C


@pytest.mark.parametrize("name", NAMES)
def test_reachability_and_the_flat_frame(name):
    """Every varying frame fires on 1,463 of 1,500 bars with 1,463
    DISTINCT values and no exact zero; the flat frame fires on the same
    1,463 and reads exactly 0.0 on every one of them.

    The flat reading is a VALUE and not missing data, and its mechanism is
    exact: both rolling means of a constant are that constant bit for bit,
    so `AO` is exactly 0.0. The distinct count is asserted as "not all
    equal" plus a floor rather than as the number 1,463, because how many
    values of an `np.exp` path collide in the last bits is a property of
    this machine's kernels.

    ⚠ These counts are SYNTHETIC. The real-data ones came with Gate E and
    are pinned by `test_the_gate_e_run_closes_gate_c_on_real_data`, where
    no fired bar reads 0.0 at all -- the exact 0.0 above is the flat
    frame's and does not occur on 89 frames of BIST daily prices."""
    col = j_acosc(*FRAMES[name]())
    v = col.dropna()
    assert v.size == FIRED
    if name == "flat":
        assert bool((v == 0.0).all())
        assert v.nunique() == 1
    else:
        assert int((v == 0.0).sum()) == 0
        assert v.nunique() > FIRED - 10
        assert float(v.abs().max()) < 0.2


# ------------------------------------------------------------------ Gate D


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    """An exact power of two scales every intermediate exactly and the
    final division cancels it, so this is asserted bit-identical rather
    than within a bound -- 1,463 of 1,463 bars on each of seven frames."""
    frame = FRAMES[name]()
    base, moved = j_acosc(*frame), j_acosc(*_scaled(frame, factor))
    assert bool((base.isna() == moved.isna()).all())
    m = base.notna()
    assert int(m.sum()) == FIRED
    assert bool((base[m] == moved[m]).all())


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """An inexact factor moves the price in its last bits, and this column
    AMPLIFIES that: measured worst 1.812e-10 relative, 1.886e-10 under
    reduced CPU dispatch, against inputs that lose 1e-16.

    Asserted at 1e-7 -- nearly three orders of headroom -- with the NaN
    masks identical, which is the part a tolerance cannot hide."""
    frame = FRAMES[name]()
    base, moved = j_acosc(*frame), j_acosc(*_scaled(frame, factor))
    assert bool((base.isna() == moved.isna()).all())
    assert _rel(base, moved) <= 1e-7, _rel(base, moved)


def test_gate_d_scale_at_extreme_price_levels():
    """The same walk REBUILT at each level, not rescaled: all five columns
    of `docs/JAcoscMeasured.md` §D3, at 1e-6, 1e+6 and 1e+100.

    `fired` = 1,463 and `finite` = 1,463 at each; the x8/x64 bit-identity
    is re-run AT the level rather than inferred from the level-100 run of
    `test_gate_d_scale_x8_x64_is_bit_identical`, 1,463 of 1,463 at each of
    the three.

    And `max |value|` is asserted as an AGREEMENT between the three
    levels, not as a loose `< 0.2` bound: a frame builder that scaled
    badly, or a column that was not homogeneous of degree 0, would drift
    between 1e-6 and 1e+100 and a bound would never see it.

    ⚠ It is a TOLERANCE and not bit-equality, and that was measured the
    hard way -- round 3 asked for bit-equality here and the assertion
    failed. 1e-6, 1e+6 and 1e+100 are not exact binary multiples, so
    `level * np.exp(...)` builds three price paths that already differ in
    their last bits; the division cancels the LEVEL, it cannot cancel a
    difference that is in the prices. Measured pairwise relative spread
    2.908e-16 / 3.926e-15 / 3.635e-15 on max |value| (§D3 prints all 17
    digits of each), and 1.890e-15 / 2.472e-15 / 4.362e-15 under reduced
    CPU dispatch, where the 17-digit values themselves move too. Asserted
    at 1e-9: still three orders inside §D2's 1.886e-10, and six orders
    tighter than the `< 0.2` bound it replaces."""
    maxima = []
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        col = j_acosc(*frame)
        v = col.dropna().to_numpy()
        assert v.size == FIRED
        assert bool(np.isfinite(v).all())
        maxima.append(float(np.abs(v).max()))
        for factor in (8.0, 64.0):
            moved = j_acosc(*_scaled(frame, factor))
            assert bool((col.isna() == moved.isna()).all())
            m = col.notna()
            assert bool((col[m] == moved[m]).all())
    worst = max(abs(a - b) / b for a in maxima for b in maxima)
    assert worst <= 1e-9, (maxima, worst)
    assert maxima[0] < 0.2


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    """`0 < fires < n`, so a constant column cannot pass Gate D -- which
    matters here precisely because the flat frame IS constant (at 0.0) and
    still fires."""
    col = j_acosc(*FRAMES[name]())
    assert 0 < int(col.notna().sum()) < col.size


# ----------------------------------------------------------------- guards


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0, np.inf, -np.inf, 1e-310])
def test_a_bad_close_empties_its_own_bar_and_no_other(bad):
    """The divisor guard's whole contract, measured on six kinds of bad
    close planted at bar 700 of a walk: exactly one bar emptied, zero
    other bars moved -- not "approximately", because the close enters the
    column at its own bar only."""
    frame = _walk()
    h, l, c = frame
    base = j_acosc(*frame)
    c2 = c.copy()
    c2.iloc[PLANT] = bad
    out = j_acosc(h, l, c2)
    assert int((base.notna() & out.isna()).sum()) == 1
    assert bool(out.isna().iloc[PLANT])
    m = base.notna() & out.notna()
    assert int((base[m] != out[m]).sum()) == 0


def test_what_the_close_guard_buys():
    """The guard is not cosmetic, and this is the measurement that says so:
    with it removed, a zero or subnormal close reads `inf` and a NEGATIVE
    close reads -0.771217 -- a plausible-looking number, which is the
    dangerous one for a tree.

    The mutant is the shipped source with the guard line replaced, so this
    cannot drift from what the module actually does."""
    off = _mutant(*CLOSE_GUARD_OFF)
    h, l, c = _walk()
    for bad in (0.0, 1e-310):
        c2 = c.copy()
        c2.iloc[PLANT] = bad
        assert np.isinf(float(off(h, l, c2).iloc[PLANT]))
    c2 = c.copy()
    c2.iloc[PLANT] = -1.0
    value = float(off(h, l, c2).iloc[PLANT])
    assert np.isfinite(value)
    assert math.isclose(value, -0.771217, abs_tol=1e-5), value
    # And the shipped module empties it instead.
    assert bool(j_acosc(h, l, c2).isna().iloc[PLANT])


@pytest.mark.parametrize("bad", [np.inf, -np.inf])
@pytest.mark.parametrize("leg", ["high", "low"])
def test_an_infinite_price_empties_bars_like_a_nan(leg, bad):
    """Measured rather than assumed, and the opposite of `j_gator`'s
    answer: `rolling(...).mean()` EMPTIES a window holding a non-finite
    value, so an infinite high or low gives a column bit-identical to the
    one a NaN gives, with 0 non-finite readings.

    Pinned on both legs and both signs -- `mid` is `(high + low) / 2`, so
    a bad low has to behave like a bad high -- and pinned at all, so that
    a pandas upgrade which starts letting an `inf` through fails loudly
    here instead of silently shipping an infinite feature."""
    h, l, c = _walk()
    parts = {"high": h.copy(), "low": l.copy()}
    parts[leg].iloc[PLANT] = bad
    inf_col = j_acosc(parts["high"], parts["low"], c)
    nan_parts = {"high": h.copy(), "low": l.copy()}
    nan_parts[leg].iloc[PLANT] = np.nan
    nan_col = j_acosc(nan_parts["high"], nan_parts["low"], c)
    assert bool((inf_col.isna() == nan_col.isna()).all())
    m = inf_col.notna()
    assert bool((inf_col[m] == nan_col[m]).all())
    assert int((~np.isfinite(inf_col.dropna().to_numpy())).sum()) == 0


@pytest.mark.parametrize("leg", ["high", "low"])
def test_a_bad_mid_empties_its_windows_and_moves_no_earlier_bar(leg):
    """The reach of one bad `mid` bar, stated exactly: `SLOW + SIGNAL - 1`
    = 38 bars, measured 700..737 for a plant at 700.

    The causal half is the assertion that matters -- NO bar before 700
    moves at all. ⚠ The disclosure is that bars AFTER 737 DO move, by up
    to 9.486e-12 relative (662 of them), which is pandas' rolling
    accumulator re-summing the window from scratch once a NaN has passed
    through rather than contamination from the bad bar; it is bounded here
    at 1e-9 so that a real leak could not hide inside it."""
    h, l, c = _walk()
    base = j_acosc(h, l, c)
    parts = {"high": h.copy(), "low": l.copy()}
    parts[leg].iloc[PLANT] = np.nan
    out = j_acosc(parts["high"], parts["low"], c)

    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert emptied.size == REACH == 38
    assert (int(emptied.min()), int(emptied.max())) == (PLANT,
                                                        PLANT + REACH - 1)

    m = base.notna() & out.notna()
    idx = np.flatnonzero(m.to_numpy())[(base[m] != out[m]).to_numpy()]
    assert int((idx < PLANT).sum()) == 0
    assert bool((idx > PLANT + REACH - 1).all())
    assert _rel(base[m], out[m]) <= 1e-9, _rel(base[m], out[m])


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0, 100.0])
def test_a_degenerate_frame_raises_nothing(value):
    """All-NaN, all-zero, all-negative and all-one-price frames: no float
    error is reachable under `errstate(all="raise")`.

    The last of the four is the one that matters -- a frame of a repeated
    price is a halted instrument, not a pathological input -- and it is
    the only one that fires: 23 of 60 bars, all exactly 0.0. The other
    three fire nowhere, the zero and negative ones because the divisor
    guard empties every bar."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="raise"):
        out = j_acosc(s.copy(), s.copy(), s.copy())
    v = out.dropna()
    if value == 100.0:
        assert v.size == 60 - WARMUP == 23
        assert bool((v == 0.0).all())
    else:
        assert v.size == 0


def test_the_cross_scale_overflow_is_disclosed_and_unguarded():
    """The one non-finite reading this module can produce, pinned so the
    disclosure cannot rot into silence: a frame whose high/low sit at
    1e+300 while the close sits at 1e-300 overflows the division and reads
    `inf` on all 23 of its fired bars.

    That is bad data rather than a price -- the same walk at ONE scale
    fires 1,463 finite bars at 1e-6, 1e+6 and 1e+100, which is
    `test_gate_d_scale_at_extreme_price_levels` -- and the module reports
    it instead of hiding it."""
    h, l, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=h.index)
    out = j_acosc(h, l, tiny)
    v = out.dropna().to_numpy()
    assert v.size == 60 - WARMUP == 23
    assert int(np.isinf(v).sum()) == v.size


# ------------------------------------------------------- docs and the ledger


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows `d[:150].rsplit(' ', 1)[0]`
    of the docstring's first paragraph, which drops the trailing word
    WHOLE. The cut only runs when the paragraph EXCEEDS 150 characters, so
    the budget is 150 and the penalty for passing it is a whole word, not
    a character. The paragraph is 115 characters, i.e. 35 to spare --
    measured by `python docs/measure_j_acosc.py W`, which calls the
    generator's own `desc()` and grows the sentence until it loses a word.
    This test runs the generator's OWN `desc`, lifted out of its source by
    `ast` so that importing it does not run the whole probe: the assertion
    then fails if the generator's cut changes, and not only if this
    sentence grows."""
    doc = j_acosc.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) == 115, len(paragraph)

    desc = _generator_desc()
    assert desc({"desc": paragraph}) == paragraph
    # One character past the 150 budget (36 longer than the paragraph,
    # i.e. one past §W's measured slack of 35), and the generator takes a
    # whole word.
    longer = paragraph[:-1] + "x" * 36 + paragraph[-1:]
    assert len(longer) == 151
    assert desc({"desc": longer}) != longer


def _j_acosc_ledger_row():
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    rows = [r for r in rows if r["indicator"] == "j_acosc"]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_gate_e_row_is_this_ports_own_measurement():
    """The ledger row for `j_acosc` must come from the run on THIS module,
    `is106-j_acosc-92ad5686` (measured 2026-11-14), and NOT from the screen
    of 2026-10-24, which measured the PROTOTYPE. The two agree to every
    digit issue #106 printed -- pooled 0.8381 against the manifest's
    `FWMA_Slope_pct_Pctl` at n = 391,996, top-five per-frame max median
    0.8431 over 89 frames, runners-up `FWMA_Slope_pct` 0.8278 and
    `StochRSI_K` 0.8156 -- which is exactly why the row's identity needs
    pinning: `tests/test_gate_e_ledger.py` re-derives a row's `module_sha1`
    and output fingerprint from the tree and checks its verdict arithmetic,
    but it cannot see WHOSE measurement a row came from. Item 1's §A2 limb
    asserts this module bit-equal to the prototype on all seven frames, so
    the agreement is expected -- and an expected agreement is the easiest
    kind of row to copy over by mistake.

    The verdict is **DISCLOSE_GAP**, the 0.80 .. 0.90 band of
    `r3-perframe-0.90`: a ship with a note, not a strike, so the column
    stays and the row needs no waiver. Both limbs are asserted as BOUNDS
    and not as digits -- pooled in [0.80, 0.90), top-five per-frame max
    median below the 0.90 strike line -- so a re-recorded row that moved
    within the band still has to stay in it.

    This test replaced `test_the_gate_e_row_is_owed`, which asserted the
    row was ABSENT and so failed the moment the receipt session recorded
    it. `docs/JAcoscMeasured.md` §E1 .. §E3 carries the result in full,
    including the part the band does not read: no single one of the 89
    frames reaches 0.90 on ANY of the top five comparators, the worst being
    0.8822 on the top one."""
    row = _j_acosc_ledger_row()
    assert row["module"] == "pandas_ta.momentum.j_acosc"
    assert row["column"] == f"J_ACOSC_{FAST}_{SLOW}_{SIGNAL}"
    assert row["run"] == "is106-j_acosc-92ad5686"
    assert row["verdict"] == "DISCLOSE_GAP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert row["against"] == "FWMA_Slope_pct_Pctl"
    assert row["against_set"] == "manifest"
    assert row["perframe_max_against"] == "FWMA_Slope_pct_Pctl"
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    # DISCLOSE_GAP is 0.80 <= pooled < 0.90, and STRUCK needs a top-5
    # comparator's per-frame median >= 0.90.
    assert 0.80 <= float(row["max_abs_rho"]) < 0.90
    assert float(row["perframe_max_median_abs_rho"]) < 0.90


def test_the_gate_e_run_closes_gate_c_on_real_data():
    """Gate C's real-data limb, read off the SAME ledger row rather than
    retyped: the column fires on 395,556 of the run's 398,849 pooled bars
    over 89 real BIST frames, so `0 < fires < n` holds there and not only
    on the synthetic frames of item 4.

    The 3,293 empty bars are EXACTLY the warm-up -- `WARMUP * 89` with no
    remainder -- which is the real-data form of item 4's synthetic finding
    that the NaNs are a leading prefix of 37 bars and nothing else. Pinned
    as that product rather than as 3,293, so a changed constant fails here.

    `non_zero` equals `non_nan`, i.e. NO fired real bar reads exactly
    0.0. That is the question §E carried before the run: the exact 0.0 of
    item 4's `flat` frame -- where both rolling means equal the constant
    level, so `AO` is exactly 0.0 before any tap arithmetic -- is a
    synthetic reading and does not occur on 89 frames of BIST daily
    prices."""
    row = _j_acosc_ledger_row()
    pooled = int(row["pooled_bars"])
    fires = int(row["non_nan"])
    frames = int(row["n_frames"])
    assert 0 < fires < pooled
    assert pooled - fires == WARMUP * frames
    assert int(row["non_zero"]) == fires
