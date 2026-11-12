# -*- coding: utf-8 -*-
"""TS-PEAKS-20: `ts_peaks_20`, tsfresh's `number_peaks` of close
(PandasTa issue #92).

    TS_PEAKS_20_2 = how many of a 20-close window's 16 candidate bars are
                    strictly above the two closes before AND the two closes
                    after them

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line plus the
   published `number_peaks` definition.** tsfresh is NOT installed in this
   worktree and web access is unavailable, so "tsfresh (MIT)" is an
   attribution, not an oracle (`test_tsfresh_is_not_installed_here` records
   that, so the claim cannot rot into "checked against tsfresh"). What IS
   checkable is pinned three ways, all bit-equality and not a tolerance:

   * the definition spelled with `np.roll` window by window, sharing no code
     with the module -- **bit-equal on 581 of 581** fired bars of each of
     four 600-bar frames. The `np.roll` spelling wraps, and the wrap is
     pinned never to reach the kept slice: over every (candidate, distance)
     pair of a 20-close window the read index stays inside `[0, 20)`;
   * an independent plain-Python scalar loop -- bit-equal on 581 of 581 bars
     of each of three frames;
   * eight hand-derived windows, including the two that a reader gets wrong:
     a 20-close PLATEAU reads 0.0 (the comparison is strict) and a
     100/101 ZIGZAG reads 0.0 too (no close beats the one two bars away).

2. **That the port is the column issue #92's screen measured, bit-for-bit ON
   CLEAN DATA -- and that this still does not transfer the screen's Gate E
   numbers.**
   The prototype (`docs/issues/screen/ind_screen.py`, candidate
   `ts_peaks_20`) spells the same four comparisons, and the port is
   **bit-equal on 1481 of 1481** bars of each of four frames, against both a
   retyped copy and the owner's own registry entry when that tree is present
   (`test_the_port_is_bit_equal_to_the_screen_prototype`). This is the
   opposite of issue #91's `ts_perment_20`, where the prototype was a
   four-pattern sum and the port deliberately differed.
   ⚠ Those four frames are CLEAN. The prototype reads a NaN comparison as
   "not a peak" and still emits a count, while this port empties the window,
   so the two part company on any frame carrying a non-finite close: measured
   in `docs/measure_ts_peaks_20.py gate_a`, one NaN at bar 200 of a 400-bar
   walk leaves 19 bars where the port is NaN and the prototype emits a
   number, with 361 of 361 agreeing elsewhere. On real data that divergence
   did not occur: Gate E's 1,691 NaN bars are exactly the 19-bar warm-up on
   each of the 89 frames. Gate E on THIS module (`is92-ts_peaks_20-7852eb1c`,
   2026-11-13) reproduced the screen's figure -- 0.24525200672691871 vs
   `BB_Lower`, n = 397,158, per-frame max median 0.23452801812896362, SHIP --
   and that run, not the screen's, is the receipt
   (`test_the_ledger_row_is_this_modules_gate_e_run`).

3. **Gate B, by mutant, on six configurations -- and the designed probe that
   makes it decisive.** Five mutants, each `importlib`-read and `exec`'d in
   memory, over two mechanisms: the write index back-dated by 2 bars and by
   `length - 1` bars, and the read index moved one candidate / half a window
   / one support leg into the future. Over 37 offsets of a blind
   future-perturbation sweep the **real module leaks 0/37 in all six
   configurations** -- three frames at the default, plus `length` 10, 60 and
   5 on the walk.
   ⚠ The blind sweep is WEAK against the one-bar leaks: `forward_flag` is
   caught at only **2-5 of 37** and `forward_leg` at **1-4 of 37**, because
   the peak flag fires on just **13.8-14.9%** of candidates and a tail
   perturbation that flips no flag is invisible. The reason is measured, not
   excused: for `forward_flag` the sweep catches the mutant at offset J **if
   and only if** the perturbation flips the single flag the mutant reads
   illegally (the candidate at bar J-2) -- asserted as a set EQUALITY on
   three frames. So the gate does not rest on the sweep: a DESIGNED probe
   lifts the close at `p + k` above a known peak at bar `p` and checks bar
   `p + k - 1`, strictly before the perturbation -- over 50 peaks of a walk
   the real module leaks **0** and `forward_flag` is caught **50 of 50**,
   `forward_leg` **41 of 50**, the other 9 being peaks that the mutant's own
   flag already reads as false so the lift flips nothing.

4. **Gate D, and that it is stronger than x8.** The column reads only
   comparisons, so it is bit-identical under any strictly increasing
   transform of price and not merely under a multiplication: x8, x64, x1024,
   x10, x3.7 and x0.1 are bit-identical on **1481 of 1481** fired bars of
   each of seven frames, and `log`, `sqrt`, `x**3` and `+1000` on the walk
   (one frame, which is what was run). The invariance holds up to a float64
   COLLAPSE: because the comparison is STRICT, a transform that rounds two
   distinct closes onto the same double can DESTROY a peak -- on these seven
   frames no scaling creates a new adjacent tie (0 under each of x8, x1024,
   x3.7 and x0.1), which is a measurement, not a guarantee. A DRIFT is not
   such a transform and does move the column (Spearman **0.4066**), and
   neither is rounding to a coarser grid (**0.5667**).

5. **What the column is BLIND to, which is the thing most likely to be
   misread.** It cannot see magnitude: a +10, a +50 and a +1000 sigma spike
   planted at the same bar give a **bit-identical** column (16 bars move in
   each case). A flat, a rising, a falling and a zigzag 1,500-bar frame ALL
   read exactly 0.0 on all 1,481 fired bars, and a strongly trending frame
   reads 0.0 on **1,465 of 1,481**. Seven values EXIST at length 20 (0..6);
   at most **6 distinct** appear on any of the seven synthetic frames and the
   ceiling 6 is reached by none of them. Do NOT read this column as
   volatility, as trend strength, or as an outlier detector, and do not
   expect a continuous feature.

6. **The confirmation lag, which is in the definition and not a bug.** A
   peak at bar P is countable only once closes P+1 and P+2 exist, so the
   newest candidate of the window ending at bar T is bar **T-2** and the two
   freshest closes enter only as confirmation. Pinned by
   `test_the_newest_candidate_is_two_bars_old`; dropping the confirmation
   while keeping the same 16 candidate positions (counting a candidate that
   merely tops its two PREDECESSORS) is a different column, Spearman
   **0.000035** on a walk. That variant is NOT a same-bar column: the newest
   candidate is still bar T-2 and today's close is never counted -- bar T
   still produces a value, it just cannot contain itself -- and no test here
   claims otherwise.

7. **The ceiling, 6, and that it is attained.** Two peaks cannot be closer
   than 3 bars -- of two candidates 1 or 2 apart each would have to be
   strictly above the other -- so the count is at most the largest
   pairwise-3-apart subset of the 16 candidate positions. Exhaustively over
   all **65,536** subsets that is **6**, at positions (2, 5, 8, 11, 14, 17),
   and a 20-close witness reading exactly 6.0 is pinned. 20,000 random
   orderings of 20 distinct closes never break the 3-apart spacing.

8. **The guards.** 19 closes at length 20 returns `None` (not a frame of
   NaNs); `length` below 5 falls back to 20, because a four-close window
   holds no candidate at all; at `length=5` the column is exactly {0, 1}; a
   single non-finite INTERIOR close empties exactly **20** bars -- `length`,
   because it invalidates `2 * SUPPORT + 1 = 5` candidates and a window holds
   16 -- and fewer near either end, where the warm-up or the end of the frame
   swallows part of the span (1 / 3 / 6 / 20 / 20 / 3 / 1 bars for a NaN at
   bars 0 / 2 / 5 / 19 / 380 / 397 / 399 of a 400-bar frame, measured);
   a zero, negative or subnormal close is NOT rejected, since nothing here
   takes a ratio or a logarithm.

Numbers come from `docs/measure_ts_peaks_20.py`; the receipt is
`docs/TsPeaks20Measured.md`. Gate C on real data and Gate E come from
issue-solver's run `is92-ts_peaks_20-7852eb1c` (2026-11-13): SHIP, and
`TS_PEAKS_20_2` fires on 397,158 of 398,849 pooled bars, 372,473 of them
non-zero. Counts that depend on the
last bits of a generated frame (Spearman to six places, how many offsets a
mutant is caught at) carry a tolerance -- CI's runner has measured different
last bits for the same seeds (commit 22fe27b).
"""
import importlib
import itertools
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.ts_peaks_20 import ts_peaks_20

LENGTH = 20
SUPPORT = 2
CANDIDATES = LENGTH - 2 * SUPPORT  # 16

_REAL = importlib.import_module("pandas_ta.statistics.ts_peaks_20")

#: A 20-close window attaining the ceiling 6: peaks at window positions
#: 2, 5, 8, 11, 14, 17, the only 6-element pairwise-3-apart subset found by
#: `docs/measure_ts_peaks_20.py`'s exhaustive enumeration.
SIX_WITNESS = [1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0,
               1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 1.0]


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _coarse_grid(n=1500, seed=55, sigma=0.002, decimals=1):
    """A quiet path on a coarse price grid: 51.7% of its candidates tie with
    a neighbour, which is where strict `>` earns its keep."""
    return Series(np.round(_walk(n, seed, sigma).to_numpy(), decimals))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _mean_reverting(n=1500, seed=7, sigma=0.01, phi=-0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return _from_returns(np.clip(r, -0.5, 0.5))


def _trending(n=1500, seed=9, sigma=0.004, drift=0.01):
    return _walk(n, seed, sigma, drift)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _monotone(n=300, step=0.5, price=100.0):
    return Series(price + step * np.arange(n))


def _falling(n=300, step=0.5, price=400.0):
    return Series(price - step * np.arange(n))


def _zigzag(n=300, lo=100.0, hi=101.0):
    return Series(np.where(np.arange(n) % 2 == 0, lo, hi))


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "coarse-grid": _coarse_grid,
    "heavy-tailed": _heavy_tailed,
    "mean-reverting": _mean_reverting,
    "trending": _trending,
    "two-point": _two_point,
}


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _bit_equal(a, b):
    """Bit-equal on the shared fired bars, and the NaN masks agree."""
    if not bool((a.isna() == b.isna()).all()):
        return False, 0, 0
    m = a.notna() & b.notna()
    return bool((a[m] == b[m]).all()), int((a[m] == b[m]).sum()), int(m.sum())


# ------------------------------------------------------------ the oracles


def _peaks_of(w):
    """Window positions that are peaks, by the scalar definition."""
    w = [float(v) for v in w]
    return [j for j in range(SUPPORT, len(w) - SUPPORT)
            if all(w[j] > w[j + d] for d in range(-SUPPORT, SUPPORT + 1)
                   if d != 0)]


def _number_peaks(x, n=SUPPORT):
    """`number_peaks` as the published definition spells it, with `np.roll`:

        x_reduced = x[n:-n]
        res = None
        for i in range(1, n + 1):
            result_first = x_reduced > roll(x, i)[n:-n]
            res = result_first if res is None else res & result_first
            res &= x_reduced > roll(x, -i)[n:-n]
        return sum(res)
    """
    x = np.asarray(x, dtype=float)
    x_reduced = x[n:-n]
    res = None
    for i in range(1, n + 1):
        first = x_reduced > np.roll(x, i)[n:-n]
        res = first if res is None else (res & first)
        res &= x_reduced > np.roll(x, -i)[n:-n]
    return int(np.sum(res))


def _roll_oracle(close, length=LENGTH, n=SUPPORT):
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        out[t] = _number_peaks(w, n)
    return Series(out, index=close.index)


def _scalar_loop(close, length=LENGTH, n=SUPPORT):
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if any(v != v or v in (float("inf"), float("-inf")) for v in w):
            continue
        out[t] = float(len(_peaks_of(w)))
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_peaks_20`, retyped
    verbatim because that tree is gitignored:

        @cand("ts_peaks_20", "confirmed local peaks of close (20, support 2)",
              TS, "number_peaks(x, n=2) on 20 closes; a peak counts once
              confirmed 2 bars later")
        def _(o, h, l, c, v):
            x = c.shift(2)            # candidate peak bar, confirmed today
            pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) & (x > c)
            return pk.astype(float).rolling(16).sum().where(c.shift(19).notna())
    """
    c = close
    x = c.shift(2)
    pk = (x > c.shift(3)) & (x > c.shift(4)) & (x > c.shift(1)) & (x > c)
    return pk.astype(float).rolling(length - 2 * SUPPORT).sum().where(
        c.shift(length - 1).notna())


def _screen_candidate():
    """`REG["ts_peaks_20"]["fn"]` out of the screen's own registry, when this
    worktree has `docs/issues/` (gitignored, so a clone does not)."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "docs" / "issues" / \
        "screen" / "ind_screen.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen", path)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules["_ind_screen"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_peaks_20"]["fn"]


def _variant(close, length=LENGTH, support=SUPPORT, far_only=False,
             non_strict=False, candidates_window=False, share=False,
             mirrored=False, on_returns=False, no_confirm=False):
    """The module's arithmetic with one reading changed, so the cost of each
    decision is a measurement rather than an argument.

    `no_confirm` drops the forward confirmation and nothing else: the
    candidate positions, the window and the warm-up are unchanged, so the
    newest candidate is still bar T-2 and today's close is never counted. It
    is NOT a same-bar column.
    """
    c = close.to_numpy(dtype=float)
    if on_returns:
        r = np.full(c.size, np.nan)
        r[1:] = c[1:] / c[:-1] - 1.0
        c = r
    if mirrored:
        c = -c
    n, pad = c.size, support
    core = c[pad:n - pad]
    ok = np.isfinite(c)
    peak = np.ones(core.size, dtype=bool)
    valid = ok[pad:n - pad].copy()
    for i in ([support] if far_only else list(range(1, support + 1))):
        left, right = c[pad - i:n - pad - i], c[pad + i:n - pad + i]
        with np.errstate(invalid="ignore"):
            if no_confirm:
                hit = core > left
            elif non_strict:
                hit = (core >= left) & (core >= right)
            else:
                hit = (core > left) & (core > right)
        peak &= hit
        valid &= ok[pad - i:n - pad - i] & ok[pad + i:n - pad + i]
    flags = np.where(valid, peak.astype(np.int8), np.int8(-1))
    cands = length if candidates_window else length - 2 * pad
    windows = sliding_window_view(flags, cands)
    counts = windows.sum(axis=1, dtype=np.int64).astype(float)
    if share:
        counts = counts / cands
    bad = (windows < 0).any(axis=1)
    out = np.full(c.size, np.nan)
    out[cands + 2 * pad - 1:] = np.where(bad, np.nan, counts)
    return Series(out, index=close.index)


def _flags_of(c):
    """The per-candidate peak flag array; flag index j is bar j + SUPPORT."""
    n = c.size
    core = c[SUPPORT:n - SUPPORT]
    peak = np.ones(core.size, dtype=bool)
    for i in range(1, SUPPORT + 1):
        peak &= (core > c[SUPPORT - i:n - SUPPORT - i]) & \
            (core > c[SUPPORT + i:n - SUPPORT + i])
    return peak


def _mutant_flags_of(c):
    """`forward_leg`'s own flag: the legs ahead are read one bar too far."""
    n = c.size
    core = c[SUPPORT:n - SUPPORT]
    peak = np.ones(core.size, dtype=bool)
    rolled = np.roll(c, -1)
    for i in range(1, SUPPORT + 1):
        peak &= (core > c[SUPPORT - i:n - SUPPORT - i]) & \
            (core > rolled[SUPPORT + i:n - SUPPORT + i])
    return peak


# --------------------------------------------------------- the attribution


def test_tsfresh_is_not_installed_here():
    """The source is an ATTRIBUTION, not an oracle: tsfresh is absent from
    this worktree and web access is unavailable, so no test in this file may
    claim to have compared against tsfresh's own code. If tsfresh ever is
    installed, this test fails and whoever installed it should add the real
    comparison rather than deleting the honesty.
    """
    with pytest.raises(ImportError):
        importlib.import_module("tsfresh.feature_extraction.feature_calculators")


def test_the_nan_window_test_keeps_its_cheap_spelling():
    """A SOURCE pin, because behaviour cannot carry this one: `bad =
    windows.min(axis=1) < 0` and `bad = (windows < 0).any(axis=1)` return the
    same column, so every OTHER test here (191 of the 192) passes with
    either -- and the `any` form
    materialises a `(rows, length - 4)` bool array, traced at 6.8 MB at
    `length` 20 and 98.7 MB at `length` 250 against 0.8 MB for `min`
    (docs/TsPeaks20Measured.md, Cost). Without this test, "re-readability"
    restores the memory regression AND makes the Cost section's table a lie,
    silently, with a green suite.
    """
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert "    bad = windows.min(axis=1) < 0\n" in src
    # the rejected spelling may appear in a comment, never as the statement
    assert "    bad = (windows < 0)" not in src


def test_the_docstring_states_the_source_and_the_gap():
    doc = ts_peaks_20.__doc__
    assert "tsfresh" in doc and "number_peaks" in doc and "MIT" in doc
    assert "NOT installed" in doc
    assert "issue #92" in doc


# --------------------------------------------------------------- the shape


def test_the_candidate_positions_are_the_sources_x_reduced():
    """`number_peaks` keeps `x[n:-n]`, so a 20-close window has 16 candidates
    at positions 2 .. 17."""
    positions = list(range(SUPPORT, LENGTH - SUPPORT))
    assert positions == list(range(2, 18))
    assert len(positions) == CANDIDATES == 16


def test_the_newest_candidate_is_two_bars_old():
    """The confirmation lag is in the definition: bar T's newest candidate is
    bar T-2, so a high made today cannot be counted today.

    Measured, not asserted: plant a spike at the last bar of a frame and the
    column does not move at all; plant it two bars earlier and the last bar
    moves.
    """
    close = _walk(400, seed=3)
    base = ts_peaks_20(close)
    c = close.to_numpy().copy()
    c[-1] = c.max() * 2.0
    assert ts_peaks_20(Series(c, index=close.index)).equals(base)
    c = close.to_numpy().copy()
    c[-3] = c.max() * 2.0
    moved = ts_peaks_20(Series(c, index=close.index))
    assert not moved.equals(base)
    assert float(moved.iloc[-1]) != float(base.iloc[-1])


def test_np_rolls_wrap_never_reaches_the_kept_slice():
    """The `np.roll` spelling of the oracle wraps; this is why that does not
    contaminate it."""
    bad = [(j, i, k)
           for j in range(SUPPORT, LENGTH - SUPPORT)
           for i in range(1, SUPPORT + 1)
           for k in (j - i, j + i)
           if not 0 <= k < LENGTH]
    assert bad == []


# ------------------------------------------------- Gate A1: hand-derived


HAND = [
    ("plateau: 20 identical closes, strict > means no peak", _flat(LENGTH),
     LENGTH, 0.0, []),
    ("20 strictly rising closes", _monotone(LENGTH), LENGTH, 0.0, []),
    ("20 strictly falling closes", _falling(LENGTH), LENGTH, 0.0, []),
    ("zigzag 100/101: no close beats the one TWO bars away",
     _zigzag(LENGTH), LENGTH, 0.0, []),
    ("the six-peak witness", Series(SIX_WITNESS), LENGTH, 6.0,
     [2, 5, 8, 11, 14, 17]),
    ("length 5, [1,2,5,2,1]: one candidate, a peak",
     Series([1.0, 2.0, 5.0, 2.0, 1.0]), 5, 1.0, [2]),
    ("length 5, [1,2,3,4,5]: one candidate, not a peak",
     Series([1.0, 2.0, 3.0, 4.0, 5.0]), 5, 0.0, []),
    ("length 9, [1,2,9,2,1,2,9,2,1]: two peaks",
     Series([1.0, 2.0, 9.0, 2.0, 1.0, 2.0, 9.0, 2.0, 1.0]), 9, 2.0, [2, 6]),
]


@pytest.mark.parametrize("name,close,length,want,positions", HAND,
                         ids=[h[0] for h in HAND])
def test_hand_derived_windows(name, close, length, want, positions):
    got = ts_peaks_20(close, length=length)
    assert float(got.iloc[length - 1]) == want
    assert _peaks_of(close.to_numpy()[-length:]) == positions
    assert got.name == f"TS_PEAKS_{length}_2"


def test_a_plateau_is_not_a_peak_and_that_is_the_strict_comparison():
    """The single most misreadable case: a window of identical closes reads
    0.0, and a 20-close window with a flat top reads 0.0 too."""
    assert float(ts_peaks_20(_flat(LENGTH), length=LENGTH).iloc[-1]) == 0.0
    w = [1.0] * 8 + [5.0, 5.0] + [1.0] * 10
    assert float(ts_peaks_20(Series(w), length=LENGTH).iloc[-1]) == 0.0
    # one bar of that plateau removed, and it fires
    w = [1.0] * 8 + [5.0, 4.0] + [1.0] * 10
    assert float(ts_peaks_20(Series(w), length=LENGTH).iloc[-1]) == 1.0


# -------------------------------------------- Gate A2: the screen prototype


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "coarse-grid",
                                   "two-point"])
def test_the_port_is_bit_equal_to_the_screen_prototype(frame):
    """Unlike issue #91's `ts_perment_20`, the prototype and the source
    formula agree here: the prototype's four comparisons ARE
    `number_peaks(n=2)`. Measured: bit-equal on 1,481 of 1,481 fired bars of
    each of four frames, and the NaN masks agree.
    """
    close = FRAMES[frame]()
    equal, bits, n = _bit_equal(ts_peaks_20(close), _prototype(close))
    assert equal and bits == n
    assert n == 1481


@pytest.mark.parametrize("frame", ["walk", "coarse-grid"])
def test_the_retyped_prototype_matches_the_owners_registry(frame):
    """The comparison above is against the screen's REAL code when
    `docs/issues/` is present (gitignored, so a clone skips this)."""
    fn = _screen_candidate()
    if fn is None:
        pytest.skip("docs/issues/screen/ind_screen.py is not in this tree")
    close = FRAMES[frame]()
    imported = Series(np.asarray(fn(close, close, close, close, close),
                                 dtype=float), index=close.index)
    equal, bits, n = _bit_equal(ts_peaks_20(close), imported)
    assert equal and bits == n == 1481


def test_the_ledger_row_is_this_modules_gate_e_run():
    """Gate E is this module's own, not the screen's. Issue #92 quoted the
    screen harness's figures on the PROTOTYPE (max |rho| 0.2453 vs
    `BB_Lower`, n = 397,158); issue-solver's run on
    `pandas_ta.statistics.ts_peaks_20` (`is92-ts_peaks_20-7852eb1c`,
    measured 2026-11-13) reproduced them and is what ships.

    Pinned here: exactly one `TS_PEAKS*` row exists, it is SHIP under
    `r3-perframe-0.90`, and it names this module and that run. The numbers
    themselves are checked by `tests/test_gate_e_ledger.py`, which also
    re-derives `module_sha1` and the output fingerprint from the tree -- so
    this test deliberately asserts the row's IDENTITY, which that one does
    not: a row recorded from some other run would satisfy the generic
    checks.
    """
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / \
        "gate_e_ledger.csv"
    rows = [r for r in csv.DictReader(ledger.open(encoding="utf-8"))
            if r["column"].startswith("TS_PEAKS")]
    assert len(rows) == 1
    row = rows[0]
    assert row["indicator"] == "ts_peaks_20"
    assert row["module"] == "pandas_ta.statistics.ts_peaks_20"
    assert row["column"] == "TS_PEAKS_20_2"
    assert row["run"] == "is92-ts_peaks_20-7852eb1c"
    assert row["verdict"] == "SHIP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    assert float(row["max_abs_rho"]) < 0.76
    assert float(row["perframe_max_median_abs_rho"]) < 0.90


def test_the_ledger_row_carries_the_measured_gate_e_numbers():
    """The four figures `docs/TsPeaks20Measured.md` reports in its Gate E
    section, read back out of the ledger so an edit to either one has to
    move both: 0.24525200672691871 vs `BB_Lower` (compute_all) over
    n = 397,158, per-frame max median 0.23452801812896362, and the run's
    real-data reachability counts 397,158 non-NaN / 372,473 non-zero of
    398,849 pooled bars (Gate C).
    """
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / \
        "gate_e_ledger.csv"
    rows = [r for r in csv.DictReader(ledger.open(encoding="utf-8"))
            if r["column"] == "TS_PEAKS_20_2"]
    assert len(rows) == 1
    row = rows[0]
    assert float(row["max_abs_rho"]) == 0.24525200672691871
    assert row["against"] == "BB_Lower"
    assert row["against_set"] == "compute_all"
    assert int(row["n"]) == 397158
    assert float(row["perframe_max_median_abs_rho"]) == 0.23452801812896362
    assert row["perframe_max_against"] == "BB_Lower"
    assert (int(row["non_nan"]), int(row["non_zero"])) == (397158, 372473)
    assert int(row["pooled_bars"]) == 398849
    # The NaN bars are exactly the warm-up: 19 per frame, 89 frames.
    assert int(row["pooled_bars"]) - int(row["non_nan"]) == 19 * 89


# --------------------------------------------------- Gate A3/A4: the oracles


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "coarse-grid",
                                   "two-point"])
def test_the_np_roll_spelling_is_bit_equal(frame):
    close = FRAMES[frame](n=600)
    equal, bits, n = _bit_equal(ts_peaks_20(close), _roll_oracle(close))
    assert equal and bits == n == 581


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "coarse-grid"])
def test_the_scalar_loop_is_bit_equal(frame):
    close = FRAMES[frame](n=600)
    equal, bits, n = _bit_equal(ts_peaks_20(close), _scalar_loop(close))
    assert equal and bits == n == 581


def test_the_oracles_agree_on_a_window_with_ties():
    """A coarse window where several candidates tie with a neighbour -- the
    case the two oracles could disagree on if either used `>=`."""
    w = [1.0, 2.0, 2.0, 1.0, 3.0, 1.0, 1.0, 1.0, 2.0, 2.0,
         2.0, 1.0, 4.0, 1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 1.0]
    assert _number_peaks(w) == len(_peaks_of(w)) == 2
    assert float(ts_peaks_20(Series(w), length=LENGTH).iloc[-1]) == 2.0


# ---------------------------------------------- Gate A5: the open readings


#: (knob, measured Spearman against the port on walk / tick-rounded /
#: coarse-grid). The reading in the module's name is the one kept; each row
#: is the price of the reading REJECTED.
READINGS = [
    ("support on both sides at 1 AND 2, not only at 2",
     dict(far_only=True), (0.767425, 0.750979, 0.607045)),
    ("support 2, not support 1", dict(support=1),
     (0.115928, 0.348537, 0.456213)),
    ("the window is 20 closes, not 20 candidates",
     dict(candidates_window=True), (0.791649, 0.802062, 0.875618)),
    ("peaks of close, not of -close", dict(mirrored=True),
     (0.288630, 0.289679, 0.140968)),
    ("peaks of the closes, not of the returns", dict(on_returns=True),
     (0.096399, 0.187320, 0.259749)),
    ("the 2-bar confirmation, not an unconfirmed count at the same positions",
     dict(no_confirm=True), (0.000035, 0.028300, 0.225866)),
]


@pytest.mark.parametrize("name,knob,rhos", READINGS,
                         ids=[r[0] for r in READINGS])
@pytest.mark.parametrize("frame,slot", [("walk", 0), ("tick-rounded", 1),
                                        ("coarse-grid", 2)])
def test_each_rejected_reading_is_a_different_column(name, knob, rhos,
                                                     frame, slot):
    """Every one of these is a decision the issue's wording leaves open. The
    tolerance is wide (0.06) because the last bits of a generated frame move
    a rank statistic over a 6-valued column; what is pinned is that NONE of
    them restates the port.
    """
    close = FRAMES[frame]()
    rho = _spearman(ts_peaks_20(close), _variant(close, **knob))
    assert abs(rho - rhos[slot]) < 0.06, (name, frame, rho)
    assert abs(rho) < 0.90, (name, frame, rho)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "coarse-grid"])
def test_the_count_and_the_share_are_the_same_ranking(frame):
    """Dividing by the 16 candidates is an exact rescaling, so it is the one
    open reading a rank miner cannot see: Spearman 1.000000 (0.9999999999999999
    on the walk -- pandas' rank correlation, not the column), and the ratio is
    exactly 1/16 bar by bar, which is the claim that actually matters."""
    close = FRAMES[frame]()
    port, share = ts_peaks_20(close), _variant(close, share=True)
    assert _spearman(port, share) > 1.0 - 1e-9
    m = port.notna()
    assert bool(((port[m] / CANDIDATES) == share[m]).all())


@pytest.mark.parametrize("frame", ["walk", "tick-rounded"])
def test_the_strict_comparison_is_free_on_a_continuous_path(frame):
    """`>` vs `>=` costs nothing where no candidate ties: bit-equal on 1,481
    of 1,481 bars."""
    close = FRAMES[frame]()
    equal, bits, n = _bit_equal(ts_peaks_20(close),
                                _variant(close, non_strict=True))
    assert equal and bits == n == 1481


def test_the_strict_comparison_is_decisive_on_a_coarse_grid():
    """And it is load-bearing where candidates DO tie: on a coarse grid
    51.7% of candidates tie with a neighbour within +/-2, and the `>=`
    reading is an unrelated column (Spearman -0.0984, measured)."""
    close = _coarse_grid()
    c = close.to_numpy()
    core = c[SUPPORT:c.size - SUPPORT]
    tied = np.zeros(core.size, dtype=bool)
    for d in (-2, -1, 1, 2):
        tied |= core == c[SUPPORT + d:c.size - SUPPORT + d]
    assert 0.48 < float(tied.mean()) < 0.56
    rho = _spearman(ts_peaks_20(close), _variant(close, non_strict=True))
    assert abs(rho) < 0.30, rho


# ------------------------------------------------------ Gate A6: the ceiling


def test_the_ceiling_is_six_exhaustively():
    """Two peaks cannot be closer than 3 bars, so the count is bounded by the
    largest pairwise-3-apart subset of the 16 candidate positions.
    Enumerated over all 2**16 subsets."""
    by_size = {}
    for mask in range(1 << CANDIDATES):
        chosen = [j for j in range(CANDIDATES) if mask >> j & 1]
        if any(chosen[k + 1] - chosen[k] < 3 for k in range(len(chosen) - 1)):
            continue
        by_size.setdefault(len(chosen), []).append(
            tuple(j + SUPPORT for j in chosen))
    best = max(by_size)
    assert best == 6
    # and it is attained by exactly ONE subset -- counted, not argued
    assert sorted(by_size[best]) == [(2, 5, 8, 11, 14, 17)]


def test_the_ceiling_is_attained_by_a_pinned_witness():
    assert _peaks_of(SIX_WITNESS) == [2, 5, 8, 11, 14, 17]
    assert float(ts_peaks_20(Series(SIX_WITNESS)).iloc[LENGTH - 1]) == 6.0


def test_two_peaks_are_never_closer_than_three_bars():
    """The bound's premise, measured over 20,000 random orderings of 20
    distinct closes rather than argued."""
    rng = np.random.default_rng(2026)
    seen = set()
    for _ in range(20000):
        p = _peaks_of(rng.permutation(np.arange(1.0, LENGTH + 1.0)))
        seen.add(len(p))
        for a, b in itertools.combinations(p, 2):
            assert b - a >= 3, p
    assert max(seen) == 6
    assert seen <= set(range(7))


def test_the_column_takes_at_most_seven_values():
    """0 .. 6, so this is a coarse ordinal column and not a continuous one.
    Measured on seven 1,500-bar frames: at most 6 distinct values, and 6 is
    never reached on any of them."""
    for name, fn in FRAMES.items():
        x = ts_peaks_20(fn()).dropna()
        assert set(x.unique()) <= {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0}, name
        assert x.nunique() <= 6, name
        assert float(x.max()) <= 5.0, name


# ------------------------------------------------------ Gate B: the mutants


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(bad, np.nan, counts)",
    "    out[length - 3:n - 2] = np.where(bad, np.nan, counts)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(bad, np.nan, counts)",
    "    out[:windows.shape[0]] = np.where(bad, np.nan, counts)")
FORWARD_FLAG = (
    "    windows = sliding_window_view(flags, candidates)",
    "    windows = sliding_window_view(np.roll(flags, -1), candidates)")
ROLLED_WINDOW = (
    "    windows = sliding_window_view(flags, candidates)",
    "    windows = sliding_window_view(np.roll(flags, -(length // 2)), "
    "candidates)")
FORWARD_LEG = (
    "        left, right = c[SUPPORT - i:n - SUPPORT - i], c[SUPPORT + i:n - SUPPORT + i]",
    "        left, right = c[SUPPORT - i:n - SUPPORT - i], np.roll(c, -1)[SUPPORT + i:n - SUPPORT + i]")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_flag": FORWARD_FLAG,
    "rolled_window": ROLLED_WINDOW,
    "forward_leg": FORWARD_LEG,
}
OFFSETS = range(40, 1500, 40)
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 37 offsets, at the
#: default length. The bands are what the mechanism measurements below
#: explain; they are NOT a target.
CAUGHT = {
    "back_date_two": (11, 16),
    "back_date_full": (36, 37),
    "forward_flag": (2, 5),
    "rolled_window": (31, 36),
    "forward_leg": (1, 4),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_peaks_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"),
         mod.__dict__)
    return mod


def _caught(fn, close, other):
    base = fn(close)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_the_real_module_leaks_nothing_under_the_mutant_sweep(frame):
    """Gate B's premise: replacing every close from bar J on changes no bar
    before J. 0 of 37 offsets on each of three frames."""
    close, other = PAIRS[frame]
    assert _caught(ts_peaks_20, close, other) == []


@pytest.mark.parametrize("length", [10, 60, 5])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]

    def fn(c):
        return ts_peaks_20(c, length=length)
    assert _caught(fn, close, other) == []
    assert int(fn(close).notna().to_numpy().argmax()) == length - 1


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column (otherwise the test proves
    nothing) and be caught at least once by the blind sweep. The weak ones
    are nailed by `test_the_designed_probe_...` below.
    """
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_peaks_20(close).equals(ts_peaks_20(close))
    hits = _caught(mod.ts_peaks_20, close, other)
    lo, hi = CAUGHT[mutant]
    assert len(hits) >= 1, (mutant, frame)
    assert lo - 3 <= len(hits) <= hi + 1, (mutant, frame, len(hits))


def _prefix_moved(fn, close, perturbed, j):
    a, b = fn(close).iloc[:j], fn(perturbed).iloc[:j]
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


@pytest.mark.parametrize("mutant,k,lo,hi", [("forward_flag", 2, 50, 50),
                                            ("forward_leg", 3, 35, 45)])
def test_the_designed_probe_catches_the_one_bar_leak_mutants(mutant, k, lo,
                                                             hi):
    """The blind sweep is blunt because the peak flag is sparse. This probe
    targets the one close each mutant reads illegally: take a bar `p` that IS
    a peak, lift the close at `p + k` above it, and look at bar `p + k - 1` --
    strictly before the perturbation.

    Measured over the first 50 peaks of a 1,500-bar walk: the real module
    leaks 0, `forward_flag` is caught 50/50 and `forward_leg` 41/50, the
    remaining 9 being peaks that the mutant's OWN flag already reads as false
    (it compares `p` against `p+2` and `p+3`), so the lift flips nothing.

    What is pinned exactly is the part that cannot drift: the real module
    leaks 0, and `caught + already-false == 50` accounts for every probe.
    `forward_leg`'s 41 itself is banded 35..45, because which peaks its own
    flag rejects depends on the generated frame's last bits -- the same
    reason this file's header bands the Spearman figures.
    """
    close = _walk()
    mod = _load_mutant(*MUTANTS[mutant])
    leg_flags = _mutant_flags_of(close.to_numpy())
    peaks = [int(f) + SUPPORT for f in np.flatnonzero(
        _flags_of(close.to_numpy()))]
    big = float(close.max()) * 2.0
    real_hits, mut_hits, probed, dead = 0, 0, 0, 0
    for p in peaks:
        j = p + k
        if j >= len(close) - 2 or p < LENGTH:
            continue
        probed += 1
        if probed > 50:
            break
        pert = close.copy()
        pert.iloc[j] = big
        if _prefix_moved(ts_peaks_20, close, pert, j):
            real_hits += 1
        if _prefix_moved(mod.ts_peaks_20, close, pert, j):
            mut_hits += 1
        elif mutant == "forward_leg" and not leg_flags[p - SUPPORT]:
            # `leg_flags` is forward_leg's OWN flag array, so it may only
            # account for forward_leg's misses.
            dead += 1
    assert probed >= 50
    assert real_hits == 0
    assert lo <= mut_hits <= hi, mut_hits
    assert mut_hits + dead == 50
    if mutant == "forward_flag":
        # nothing to account for: every probe caught it
        assert dead == 0 and mut_hits == 50


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_a_missed_mutant_offset_is_exactly_an_unflipped_flag(frame):
    """WHY the blind sweep misses `forward_flag` at most offsets, as a set
    EQUALITY and not a story: bar T of the mutant reads the candidates at
    bars T-16 .. T-1, so at offset J the only prefix bar that can move is
    J-1, and the only candidate of its window reading the perturbed close J
    is the one at bar J-2. The sweep catches the mutant at J if and only if
    that single flag flips.
    """
    close, other = PAIRS[frame]
    mod = _load_mutant(*FORWARD_FLAG)
    hits = set(_caught(mod.ts_peaks_20, close, other))
    base_flags = _flags_of(close.to_numpy())
    flipped = set()
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        pf = _flags_of(p.to_numpy())
        if bool(base_flags[j - 2 - SUPPORT]) != bool(pf[j - 2 - SUPPORT]):
            flipped.add(j)
    assert hits == flipped


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_the_peak_flag_is_sparse_which_is_what_blunts_the_sweep(frame):
    close, _ = PAIRS[frame]
    density = float(_flags_of(close.to_numpy()).mean())
    assert 0.10 < density < 0.20, density


def test_offset_is_a_delay():
    close = _walk(400, seed=3)
    base = ts_peaks_20(close)
    pd.testing.assert_series_equal(ts_peaks_20(close, offset=2),
                                   base.shift(2).rename(base.name))
    pd.testing.assert_series_equal(ts_peaks_20(close, offset=-2),
                                   base.shift(-2).rename(base.name))


def test_prefix_truncation_alone_would_not_have_proved_this():
    """The weaker check the gate explicitly does not accept, kept so the
    file shows both: truncating the frame leaves every surviving bar
    unchanged, which a back-dating module would also pass."""
    close = _walk(400, seed=3)
    full = ts_peaks_20(close)
    cut = ts_peaks_20(close.iloc[:300])
    pd.testing.assert_series_equal(full.iloc[:300], cut)
    mod = _load_mutant(*BACK_DATE_TWO)
    a, b = mod.ts_peaks_20(close), mod.ts_peaks_20(close.iloc[:300])
    pd.testing.assert_series_equal(a.iloc[:298], b.iloc[:298])


# ------------------------------------------------------- Gate D: the scale


@pytest.mark.parametrize("k", [8.0, 64.0, 1024.0, 10.0, 3.7, 0.1])
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_column_is_bit_identical_under_a_scale(frame, k):
    close = FRAMES[frame]()
    equal, bits, n = _bit_equal(ts_peaks_20(close), ts_peaks_20(close * k))
    assert equal and bits == n == 1481


@pytest.mark.parametrize("length", [5, 10, 60, 250])
def test_the_scale_invariance_holds_at_other_lengths(length):
    close = _walk()
    equal, bits, n = _bit_equal(ts_peaks_20(close, length=length),
                                ts_peaks_20(close * 8.0, length=length))
    assert equal and bits == n == 1500 - length + 1


@pytest.mark.parametrize("name,fn", [("log", np.log), ("sqrt", np.sqrt),
                                     ("cube", lambda x: x ** 3),
                                     ("shift", lambda x: x + 1000.0)])
def test_any_strictly_increasing_transform_leaves_the_column_alone(name, fn):
    """Stronger than Gate D asks: the column reads only comparisons."""
    close = _walk()
    other = Series(fn(close.to_numpy()), index=close.index)
    equal, bits, n = _bit_equal(ts_peaks_20(close), ts_peaks_20(other))
    assert equal and bits == n == 1481


def test_a_scaling_creates_no_new_tie_on_these_frames():
    """The invariance above holds up to a float64 COLLAPSE: because the
    comparison is strict, two distinct closes rounded onto one double would
    destroy a peak. Measured: no scaling tested creates a new adjacent tie on
    any of the seven frames -- a measurement, not a guarantee."""
    for name, maker in FRAMES.items():
        c = maker().to_numpy()
        base_ties = int((c[1:] == c[:-1]).sum())
        for k in (8.0, 1024.0, 3.7, 0.1):
            s = c * k
            assert int((s[1:] == s[:-1]).sum()) == base_ties, (name, k)


def test_a_collapse_would_destroy_a_peak():
    """And what WOULD happen if a transform collapsed two closes: the peak is
    lost. Shown on a hand window rather than hoped about."""
    w = [1.0] * 8 + [5.0, 4.0] + [1.0] * 10
    assert float(ts_peaks_20(Series(w), length=LENGTH).iloc[-1]) == 1.0
    collapsed = list(w)
    collapsed[9] = 5.0          # 4.0 rounds onto the peak
    assert float(ts_peaks_20(Series(collapsed),
                             length=LENGTH).iloc[-1]) == 0.0


def test_a_drift_is_not_a_scale_and_does_move_the_column():
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))),
                     index=close.index)
    rho = _spearman(ts_peaks_20(close), ts_peaks_20(drifted))
    assert abs(rho - 0.406613) < 0.08, rho


def test_rounding_to_a_coarser_grid_moves_the_column():
    """Price granularity is an input: the same path on a coarse grid is a
    different column (Spearman 0.5667 measured)."""
    rho = _spearman(ts_peaks_20(_coarse_grid()),
                    ts_peaks_20(_walk(sigma=0.002, seed=55)))
    assert abs(rho - 0.566696) < 0.08, rho


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_zero_lt_fires_lt_n_so_a_constant_column_cannot_pass(frame):
    close = FRAMES[frame]()
    x = ts_peaks_20(close).dropna()
    assert len(x) == 1481
    assert 0 < len(x) < len(close)
    assert x.nunique() >= 2, frame


# ------------------------------------------------- what the column is blind to


def test_the_column_cannot_see_magnitude():
    """A +10, +50 and +1000 sigma spike at the same bar give a BIT-IDENTICAL
    column: 16 bars move in each case, by the same amounts."""
    close = _walk()
    base = ts_peaks_20(close)
    outs = []
    for size in (10.0, 50.0, 1000.0):
        c = close.to_numpy().copy()
        c[700] = c[700] * (1.0 + size * 0.015)
        outs.append(ts_peaks_20(Series(c, index=close.index)))
    assert outs[0].equals(outs[1]) and outs[0].equals(outs[2])
    m = base.notna() & outs[0].notna()
    assert int((outs[0][m] != base[m]).sum()) == 16


@pytest.mark.parametrize("name,close", [("flat", _flat(1500)),
                                        ("monotone", _monotone(1500)),
                                        ("falling", _falling(1500)),
                                        ("zigzag", _zigzag(1500))])
def test_a_flat_a_trending_and_a_zigzag_frame_all_read_zero(name, close):
    """Four very different frames, one value: 0.0 on all 1,481 fired bars.
    The column is not a volatility or trend-strength feature."""
    x = ts_peaks_20(close).dropna()
    assert len(x) == 1481
    assert x.nunique() == 1 and float(x.iloc[0]) == 0.0


def test_a_strongly_trending_frame_reads_zero_almost_everywhere():
    x = ts_peaks_20(_trending()).dropna()
    assert int((x == 0.0).sum()) >= 1400
    assert float(x.median()) == 0.0
    assert float(x.max()) <= 2.0


def test_the_column_counts_peaks_and_not_troughs():
    """Asymmetric by construction: the mirrored path is a different column."""
    close = _walk()
    rho = _spearman(ts_peaks_20(close), _variant(close, mirrored=True))
    assert abs(rho) < 0.45, rho


def test_the_fork_neighbours_are_not_restated_on_a_walk():
    """A Gate E PRE-CHECK on one synthetic frame, NOT Gate E: the real
    measurement is the launcher's run over 89 BIST frames against 687
    comparators. Max |rho| here is 0.2939 (`chop`), measured."""
    close = _walk()
    port = ts_peaks_20(close)
    others = {
        "entropy": pandas_ta.entropy(close, length=20),
        "psl": pandas_ta.psl(close, length=12),
        "ts_binent_20": pandas_ta.ts_binent_20(close),
        "ts_c3_20": pandas_ta.ts_c3_20(close),
        "ts_perment_20": pandas_ta.ts_perment_20(close),
        "chop": pandas_ta.chop(close, close, close),
        "rsi": pandas_ta.rsi(close),
    }
    worst = 0.0
    for name, other in others.items():
        s = other if isinstance(other, Series) else other.iloc[:, 0]
        worst = max(worst, abs(_spearman(port, s)))
    assert worst < 0.50, worst


# ------------------------------------------------------------- the guards


def test_too_short_a_frame_returns_none():
    close = _walk(400, seed=3)
    assert ts_peaks_20(close.iloc[:LENGTH - 1]) is None
    assert ts_peaks_20(close.iloc[:4], length=5) is None


def test_exactly_length_closes_fire_once():
    close = _walk(400, seed=3)
    out = ts_peaks_20(close.iloc[:LENGTH])
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH - 1


def test_the_warmup_is_length_minus_one():
    close = _walk(400, seed=3)
    out = ts_peaks_20(close)
    assert int(out.notna().to_numpy().argmax()) == LENGTH - 1
    assert int(out.isna().sum()) == LENGTH - 1


@pytest.mark.parametrize("length", [None, 0, 1, 2, 3, 4, -5, 4.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """A four-close window holds NO candidate, so anything under 5 is the
    default 20 rather than an error or an empty column."""
    close = _walk(400, seed=3)
    assert ts_peaks_20(close, length=length).name == "TS_PEAKS_20_2"


@pytest.mark.parametrize("length,name", [(5, "TS_PEAKS_5_2"),
                                         (5.9, "TS_PEAKS_5_2"),
                                         (21, "TS_PEAKS_21_2"),
                                         (40, "TS_PEAKS_40_2")])
def test_the_name_carries_the_length_and_the_support(length, name):
    close = _walk(400, seed=3)
    out = ts_peaks_20(close, length=length)
    assert out.name == name
    assert out.category == "statistics"


def test_at_length_five_the_column_is_binary():
    """One candidate a window, so 0 or 1 -- measured, not reasoned."""
    x = ts_peaks_20(_walk(400, seed=3), length=5).dropna()
    assert sorted(x.unique().tolist()) == [0.0, 1.0]
    assert len(x) == 396


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_a_non_finite_interior_close_empties_exactly_length_bars(bad):
    """It cannot be ordered, so it is refused rather than read as "not a
    peak": it invalidates the 5 candidates it sits in, and a window holds 16,
    so exactly 20 bars go NaN -- bars 200..219 for a close at bar 200.

    `length` bars is the INTERIOR rule only (bar `length - 1` .. `n - length`);
    the edges are pinned by the next test.
    """
    close = _walk(400, seed=3)
    base = ts_peaks_20(close)
    c = close.to_numpy().copy()
    c[200] = bad
    out = ts_peaks_20(Series(c, index=close.index))
    emptied = np.flatnonzero(out.isna().to_numpy() & base.notna().to_numpy())
    assert len(emptied) == LENGTH
    assert int(emptied[0]) == 200 and int(emptied[-1]) == 219


@pytest.mark.parametrize("at,want", [(0, 1), (2, 3), (5, 6), (19, 20),
                                     (380, 20), (397, 3), (399, 1)])
def test_near_either_end_a_non_finite_close_empties_fewer_bars(at, want):
    """The warm-up or the end of the frame swallows part of the span, so the
    "exactly 20" of the previous test is not the rule everywhere -- measured
    on a 400-bar frame, where the interior runs from bar 19 to bar 380."""
    close = _walk(400, seed=3)
    base = ts_peaks_20(close)
    c = close.to_numpy().copy()
    c[at] = np.nan
    out = ts_peaks_20(Series(c, index=close.index))
    emptied = np.flatnonzero(out.isna().to_numpy() & base.notna().to_numpy())
    assert len(emptied) == want


@pytest.mark.parametrize("bad", [0.0, -5.0, 1e-310])
def test_a_zero_or_negative_close_is_not_rejected(bad):
    """Unlike `ts_binent_20` / `ts_c3_20`, which need a return: this column
    takes no ratio and no logarithm, so such a close still compares."""
    close = _walk(400, seed=3)
    c = close.to_numpy().copy()
    c[200] = bad
    out = ts_peaks_20(Series(c, index=close.index))
    assert int(out.notna().sum()) == 381
    assert np.isfinite(float(out.iloc[200]))


def test_fillna_fills():
    close = _walk(400, seed=3)
    assert int(ts_peaks_20(close, fillna=0).isna().sum()) == 0


def test_the_output_is_integer_valued():
    """A float Series, as every pandas_ta column is, but every value is an
    integer: a consumer may cast it."""
    x = ts_peaks_20(_walk()).dropna().to_numpy()
    assert np.array_equal(x, np.round(x))


# ------------------------------------------------------------ the wiring


def test_name_registration_and_accessor():
    """Touch points 2, 3 and 4: the package export, `Category` and the
    `df.ta` accessor."""
    close = _walk(400, seed=3)
    assert "ts_peaks_20" in pandas_ta.Category["statistics"]
    assert callable(pandas_ta.ts_peaks_20)
    df = pd.DataFrame({"close": close.to_numpy()})
    acc = df.ta.ts_peaks_20()
    assert acc.name == "TS_PEAKS_20_2"
    assert acc.equals(ts_peaks_20(df["close"]))
    assert df.ta.ts_peaks_20(length=40).name == "TS_PEAKS_40_2"


def test_the_accessor_forwards_length_and_offset():
    close = _walk(400, seed=3)
    df = pd.DataFrame({"close": close.to_numpy()})
    direct = ts_peaks_20(df["close"], length=30, offset=1)
    assert df.ta.ts_peaks_20(length=30, offset=1).equals(direct)


def test_the_strategy_sweep_emits_the_column():
    """`df.ta.strategy` is what the parent repo runs; a port that misses
    `Category` computes correctly and is invisible."""
    close = _walk(400, seed=3)
    df = pd.DataFrame({"open": close.to_numpy(), "high": close.to_numpy(),
                       "low": close.to_numpy(), "close": close.to_numpy(),
                       "volume": np.full(len(close), 1000.0)})
    df.ta.strategy(pandas_ta.Strategy(
        name="peaks", ta=[{"kind": "ts_peaks_20"}]))
    assert "TS_PEAKS_20_2" in df.columns
