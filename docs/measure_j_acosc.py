# -*- coding: utf-8 -*-
"""J-ACOSC (PandasTa issue #106): every number in `docs/JAcoscMeasured.md`.

    python docs/measure_j_acosc.py            # every section, in order
    python docs/measure_j_acosc.py A1 D       # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the
only place a figure in the receipt, the module docstring or
`tests/test_j_acosc.py` may come from.

    mid     = (high + low) / 2
    AO      = SMA(mid, 5) - SMA(mid, 34)
    J_ACOSC = (AO - SMA(AO, 5)) / close

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here depends on the machine, and `docs/measure_j_acosc_cpu.py` re-runs
the sections under numpy's reduced CPU dispatch to show which figures move.
"""
import importlib.util
import math
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, date_range

from pandas_ta.momentum.ao import ao as fork_ao
from pandas_ta.momentum.cmo import cmo
from pandas_ta.momentum.er import er
from pandas_ta.momentum.j_acosc import (FAST, MIN_BARS, SIGNAL, SLOW, WARMUP,
                                        j_acosc)
from pandas_ta.momentum.qqe import qqe
from pandas_ta.momentum.stochrsi import stochrsi
from pandas_ta.overlap.fwma import fwma
from pandas_ta.overlap.sma import sma as fork_sma
from pandas_ta.trend.chop import chop
from pandas_ta.volatility.natr import natr

N = 1500
LEVEL = 100.0


# ------------------------------------------------------------------ frames
# Same builders and seeds as `tests/test_j_acosc.py`, so a number in this
# file and a number in that one are the same measurement.


def _ohlc(close, seed):
    """An OHLC frame around a close path, with `high >= close >= low`.

    The spread is random so that `mid = (high + low) / 2` is NOT the close:
    a frame where it is would hide any confusion between the two.
    """
    rng = np.random.default_rng(seed + 9_999)
    # Hourly, not daily: §Z runs 400,000 bars, and 400,000 DAYS from 2020
    # is past pandas' nanosecond datetime bound. Nothing here reads the
    # index, so the unit is free.
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
    """An Ornstein-Uhlenbeck path: the regime an acceleration oscillator is
    loudest in, because the AO keeps turning."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    """A walk quantised to a tick grid, which is what real prices are."""
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick,
            np.round(l / tick) * tick,
            np.round(c / tick) * tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                 seed)


def _jump(seed=23, n=N, level=LEVEL):
    """A walk with a single x1.5 gap at bar 700 -- the shape that drives the
    fast and slow means furthest apart."""
    h, l, c = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f


def _flat(n=N, level=LEVEL):
    """A constant price. Both means equal the level, `AO` is exactly zero
    and so is the column -- a reading, not missing data."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


FRAMES = {
    "walk": _walk,
    "trend": _trend,
    "range-bound": _range_bound,
    "grid": _grid,
    "heavy-tailed": _heavy,
    "jump": _jump,
    "flat": _flat,
}
#: Every frame but the flat one, whose column is identically 0.0.
VARYING = [n for n in FRAMES if n != "flat"]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _agree(a, b):
    """(masks equal, shared bars, bit-equal bars, max |diff|, max |rel|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0, float("nan"), float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return (masks, int(m.sum()), int((a[m] == b[m]).sum()),
            float(d.max()), float(rel))


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


# ----------------------------------------------------------------- oracles


def _mean_fsum(x, n):
    """`SMA(x, n)` by an explicit window and `math.fsum`.

    Shares no code with pandas: every window is summed from scratch, exactly
    (`fsum` is correctly rounded), instead of pandas' Kahan-compensated
    roll-on/roll-off accumulator. A window holding a NaN stays NaN, which is
    pandas' `min_periods=n` behaviour spelled by hand -- the behaviour the
    signal leg's warm-up depends on.
    """
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
    """The screen prototype, retyped from `docs/issues/screen/ind_screen.py`
    candidate `j_acosc` (that file is gitignored, so it exists only on the
    owner's machine):

        mid = (h + l) / 2
        ao = mean(mid, 5) - mean(mid, 34)
        return (ao - mean(ao, 5)) / c

    with the screen's `def mean(x, n): return x.rolling(n).mean()`.
    """
    mid = (high + low) / 2
    mean = lambda x, n: x.rolling(n).mean()  # noqa: E731
    ao = mean(mid, 5) - mean(mid, 34)
    return (ao - mean(ao, 5)) / close


def _fork_route(high, low, close):
    """The same formula over this fork's OWN shipped pieces: `ao` for the
    Awesome Oscillator and `sma` for the signal leg.

    `ao(high, low)` is `0.5 * (high + low)` through `sma(.., 5)` and
    `sma(.., 34)`, which is the issue's `AO` exactly -- so this is both a
    third Gate A spelling and the check that the port did not invent an
    `AO` the fork already ships.
    """
    a = fork_ao(high, low)
    return (a - fork_sma(a, SIGNAL)) / close


def _ema_column(high, low, close):
    """The reading NOT taken: "SMA" read as an exponential mean of the same
    period (`alpha = 2 / (n + 1)`, i.e. `ewm(span=n)`), seeded at bar 0.

    The issue says SMA and the prototype spells `rolling(n).mean()`, so this
    is not a live candidate -- it is here to price how far the wrong reading
    would be, the way `j_gator`'s §A4 prices its alpha.
    """
    mid = (high + low) / 2
    m = lambda x, n: x.ewm(span=n, adjust=False).mean()  # noqa: E731
    a = m(mid, FAST) - m(mid, SLOW)
    return (a - m(a, SIGNAL)) / close


def _signal_over_mid(high, low, close):
    """The WARM-UP TRAP spelled as a column: the signal averaged over the
    PRICE instead of over `AO`.

    `SMA(mid,5) - SMA(mid,34) - SMA(mid,5)` is not the issue's formula -- it
    is `-SMA(mid,34)`, a price level -- but the shape of the mistake is what
    makes the warm-up `SLOW + SIGNAL - 2` instead of `SLOW - 1`, so the two
    are printed side by side.
    """
    mid = (high + low) / 2
    mean = lambda x, n: x.rolling(n).mean()  # noqa: E731
    a = mean(mid, FAST) - mean(mid, SLOW)
    return (a - mean(mid, SIGNAL)) / close


def _min_periods_one(high, low, close):
    """The reading NOT taken: `min_periods=1`, i.e. partial windows.

    It would fire from bar 0 and make the warm-up disappear; it is a
    DIFFERENT column on the head of the frame and identical after it, which
    is what §A4(c) measures.
    """
    mid = (high + low) / 2
    mean = lambda x, n: x.rolling(n, min_periods=1).mean()  # noqa: E731
    a = mean(mid, FAST) - mean(mid, SLOW)
    return (a - mean(a, SIGNAL)) / close


# -------------------------------------------------------------- the filter


def _taps():
    """The column's 38 FIR taps in `mid`, as a numpy array `h` with
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
    """|H(w)| of the tap vector at angular frequency `w` (radians/bar)."""
    k = np.arange(h.size)
    return np.abs(np.sum(h * np.exp(-1j * w * k)))


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "momentum" \
    / "j_acosc.py"

#: Each entry is (label, what it does, old text, new text). Every one is an
#: edit to the SHIPPED source read off disk, exec'd in memory -- never a
#: re-implementation, which could differ from the module for reasons that
#: have nothing to do with causality.
MUTANTS = [
    ("mid-lead", "the mid price is read one bar ahead",
     "    mid = (high + low) / 2",
     "    mid = ((high + low) / 2).shift(-1)"),
    ("fast-lead", "`_sma` is centred, so EVERY mean is -- the label is"
                  " historical and §B4 measures the real reach",
     "    return x.rolling(length).mean()",
     "    return x.rolling(length, center=True).mean()"),
    ("ao-lead", "the AO leg is read one bar ahead of the signal leg",
     "    acosc = (ao - _sma(ao, SIGNAL)) / c",
     "    acosc = (ao.shift(-1) - _sma(ao, SIGNAL)) / c"),
    ("output-early", "the whole column is written one bar early",
     "    acosc = (ao - _sma(ao, SIGNAL)) / c",
     "    acosc = ((ao - _sma(ao, SIGNAL)) / c).shift(-1)"),
    ("divisor-lead", "the scale-free divisor is tomorrow's close",
     "    acosc = (ao - _sma(ao, SIGNAL)) / c",
     "    acosc = (ao - _sma(ao, SIGNAL)) / c.shift(-1)"),
    ("close-guard-off", "the close guard is removed (NOT a causality"
                        " mutant: §G1's justification for the guard)",
     "c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))",
     "c = close"),
]
#: The three mutants above that replace the same anchor line cannot be
#: applied together; they are applied one at a time, which is the point.
CAUSALITY_LABELS = ["mid-lead", "fast-lead", "ao-lead", "output-early",
                    "divisor-lead"]


def _mutant(old, new):
    """The shipped module, read off disk, one substring replaced, exec'd in
    memory. Refuses an anchor that is not unique, so a mutation cannot
    silently hit a different line after an edit."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_acosc"]


#: The 36 perturbation points of the blind causality sweep: the last 36
#: bars a future can start at. Each one is "change every bar >= J and see
#: whether any bar < J moves".
OFFSETS = list(range(N - 36, N))


def _future_sweep(fn, frame, offsets=None, factor=1.03):
    """How many of `offsets` the function is CAUGHT reading the future at.

    Caught means: perturbing high, low and close at every bar >= J moved at
    least one bar < J. A causal column cannot be caught at any J.
    """
    h, l, c = frame
    base = fn(h, l, c)
    caught = 0
    for j in offsets or OFFSETS:
        f = Series(np.where(np.arange(c.size) >= j, factor, 1.0),
                   index=c.index)
        out = fn(h * f, l * f, c * f)
        a, b = base.iloc[:j], out.iloc[:j]
        if not bool((a.isna() == b.isna()).all()) or \
                not bool((a.dropna() == b.dropna()).all()):
            caught += 1
    return caught


# ---------------------------------------------------------------- sections


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def section_A1():
    _head("A1 Gate A -- the issue's formula, spelled independently")
    print("An explicit window summed with `math.fsum` (correctly rounded)")
    print("against the module, per frame. The two spellings are NOT obliged")
    print("to round the same way: pandas rolls a Kahan-compensated running")
    print("sum on and off the window, this one re-sums each window exactly.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12} {'max |rel|':>11}")
    worst_d = worst_r = 0.0
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, rel = _agree(j_acosc(*frame), _oracle(*frame))
        worst_d = max(worst_d, 0.0 if np.isnan(d) else d)
        worst_r = max(worst_r, 0.0 if np.isnan(rel) else rel)
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} "
              f"{d:>12.3e} {rel:>11.3e}")
    print()
    print(f"worst absolute difference over all frames: {worst_d:.3e}")
    print(f"worst relative difference over all frames: {worst_r:.3e}")
    print("⚠ The relative column is `nan` on `flat`, where the oracle is")
    print("identically 0.0 and there is nothing to divide by -- which is why")
    print("the test asserts BOTH bounds.")


def section_A2():
    _head("A2 Gate A -- the screen prototype, bit for bit")
    print("The prototype shares the module's spelling of SMA (pandas'")
    print("`rolling(n).mean()`), so this limb is EXACT, and it is the limb")
    print("that ties this port to the 2026-10-24 Gate E figures.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, _ = _agree(j_acosc(*frame), _prototype(*frame))
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} {d:>12.3e}")


def section_A3():
    _head("A3 Gate A -- the fork's OWN `ao` and `sma`")
    print("`ao(high, low)` is the issue's AO (`SMA(mid,5) - SMA(mid,34)` on")
    print("`0.5 * (high + low)`) and `sma` is the signal leg. Bit-equality")
    print("here says the port did not invent an AO the fork already ships,")
    print("and that `_sma` is `pandas_ta.overlap.sma` without the rename.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, _ = _agree(j_acosc(*frame),
                                           _fork_route(*frame))
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} {d:>12.3e}")


def section_A4():
    _head("A4 The readings NOT taken, priced")
    for label, fn, note in (
        ("(a) EMA instead of SMA", _ema_column,
         "alpha = 2/(n+1), seeded at bar 0 -- the other thing 'a moving"
         " average of period n' can mean"),
        ("(b) signal over `mid`, not over `AO`", _signal_over_mid,
         "the warm-up trap as a column: it collapses to -SMA(mid,34)/close,"
         " a price level"),
        ("(c) min_periods=1 (partial windows)", _min_periods_one,
         "fires from bar 0; the question is whether the TAIL is the same"
         " column"),
    ):
        print()
        print(label)
        print(f"    {note}")
        print(f"    {'frame':<14} {'rho':>8} {'bars':>6} {'bit-eq':>7} "
              f"{'max |diff|':>12}")
        for name in VARYING:
            frame = FRAMES[name]()
            col, other = j_acosc(*frame), fn(*frame)
            _, shared, same, d, _ = _agree(col, other)
            print(f"    {name:<14} {_spearman(col, other):>8.4f} "
                  f"{shared:>6} {same:>7} {d:>12.3e}")
    print()
    print("(c) again, split head vs tail -- the only question it raises:")
    frame = _walk()
    col, mp1 = j_acosc(*frame), _min_periods_one(*frame)
    tail = col.notna() & mp1.notna()
    print(f"    bars where the module fires: {int(col.notna().sum())}")
    print(f"    bars where min_periods=1 fires: {int(mp1.notna().sum())}")
    print(f"    of the shared {int(tail.sum())}, bit-equal: "
          f"{int((col[tail] == mp1[tail]).sum())}")


def section_B():
    _head("B Gate B -- causality by future perturbation and by mutation")
    print("Caught = perturbing every bar >= J by x1.03 moved a bar < J.")
    print(f"36 offsets per frame, J in [{OFFSETS[0]}, {OFFSETS[-1]}].")
    print()
    print("(a) the SHIPPED module -- must be 0 of 36 everywhere")
    print(f"    {'frame':<14} {'caught':>8}")
    for name in VARYING:
        print(f"    {name:<14} {_future_sweep(j_acosc, FRAMES[name]()):>8}")
    print()
    print("(b) five look-ahead mutants, read off the shipped source and")
    print("    exec'd in memory. Liveness first: a mutant that changes")
    print("    nothing would be caught at 0 of 36 and prove nothing.")
    for label, what, old, new in MUTANTS:
        if label not in CAUSALITY_LABELS:
            continue
        fn = _mutant(old, new)
        print()
        print(f"    {label}: {what}")
        print(f"    {'frame':<14} {'moved':>7} {'of':>7} {'max |diff|':>12} "
              f"{'caught':>7}")
        for name in VARYING:
            frame = FRAMES[name]()
            base, mut = j_acosc(*frame), fn(*frame)
            m = base.notna() & mut.notna()
            moved = int((base[m] != mut[m]).sum())
            d = float((base[m] - mut[m]).abs().max()) if int(m.sum()) else \
                float("nan")
            print(f"    {name:<14} {moved:>7} {int(m.sum()):>7} {d:>12.3e} "
                  f"{_future_sweep(fn, frame):>7}")
    print()
    print("(c) the size of a catch, against the size of a rescale's noise.")
    print("    A catch is a bar BEFORE the perturbation moving at all; the")
    print("    smallest one has to be far above the last-bit noise an")
    print("    inexact rescale costs (§D(b)), or the sweep is reading float")
    print("    dust rather than a look-ahead.")
    frame = _walk()
    h, l, c = frame
    j = OFFSETS[0]
    f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0), index=c.index)
    for label, _, old, new in MUTANTS:
        if label not in CAUSALITY_LABELS:
            continue
        fn = _mutant(old, new)
        a, b = fn(h, l, c).iloc[:j], fn(h * f, l * f, c * f).iloc[:j]
        m = a.notna() & b.notna()
        d = (a[m] - b[m]).abs()
        hit = d[d > 0.0]
        print(f"    {label:<14} bars moved {int(hit.size):>3}  "
              f"smallest move {float(hit.min()) if hit.size else float('nan'):.3e}"
              f"  largest {float(hit.max()) if hit.size else float('nan'):.3e}")
    print()
    print("(d) `fast-lead` is misnamed, and this is what it actually does.")
    print("    The anchor is `_sma`'s only line, so `center=True` centres")
    print("    EVERY mean -- fast, slow AND signal. pandas centres a window")
    print("    of length n by `(n - 1) // 2`, so the composite reach is")
    print(f"    (SLOW - 1)//2 + (SIGNAL - 1)//2 = {(SLOW - 1) // 2} + "
          f"{(SIGNAL - 1) // 2} = {(SLOW - 1) // 2 + (SIGNAL - 1) // 2} bars,")
    print("    which is why it is the one mutant whose single catch moves")
    print("    more than one bar, and why it shares fewer bars than the")
    print("    other four. Measured, not derived:")
    fn = _mutant(*[m for m in MUTANTS if m[0] == "fast-lead"][0][2:])
    base, mut = j_acosc(*frame), fn(*frame)
    bi = np.flatnonzero(base.notna().to_numpy())
    mi = np.flatnonzero(mut.notna().to_numpy())
    shared = int((base.notna() & mut.notna()).sum())
    print(f"    module fires bars {bi.min()}..{bi.max()} ({bi.size})")
    print(f"    mutant fires bars {mi.min()}..{mi.max()} ({mi.size})")
    print(f"    shared {shared}; the module's last {bi.max() - mi.max()} bars")
    print(f"    are NaN in the mutant, and {bi.max() - mi.max()} is the reach")
    print()
    print("(e) WHY the `flat` frame is excluded from (a) and (b), measured")
    print("    rather than argued. The sweep multiplies bars >= J by 1.03,")
    print("    so a perturbed flat frame is a two-level STEP and not a")
    print("    constant -- most mutants are caught on it. The question is")
    print("    whether ALL of them are:")
    flat = _flat()
    print(f"    {'function':<16} {'caught of 36':>13}")
    print(f"    {'the module':<16} {_future_sweep(j_acosc, flat):>13}")
    for label, _, old, new in MUTANTS:
        if label not in CAUSALITY_LABELS:
            continue
        print(f"    {label:<16} {_future_sweep(_mutant(old, new), flat):>13}")


def section_C():
    _head("C Gate C -- reachability on synthetic frames")
    print("Real-data counts are owed with Gate E, which the launcher runs.")
    print()
    print(f"{'frame':<14} {'fired':>6} {'of':>6} {'first':>6} {'distinct':>9} "
          f"{'zeros':>6} {'min':>11} {'max':>11}")
    span_lo, span_hi, pooled, small = np.inf, -np.inf, 0, 0
    for name in FRAMES:
        col = j_acosc(*FRAMES[name]())
        v = col.dropna()
        first = int(col.notna().to_numpy().argmax())
        print(f"{name:<14} {v.size:>6} {col.size:>6} {first:>6} "
              f"{v.nunique():>9} {int((v == 0.0).sum()):>6} "
              f"{v.min():>11.4e} {v.max():>11.4e}")
        span_lo, span_hi = min(span_lo, v.min()), max(span_hi, v.max())
        pooled += v.size
        small += int((v.abs() <= 0.02).sum())
    print()
    print(f"pooled fired bars over the seven frames: {pooled}")
    print(f"span over all of them: {span_lo:.4f} .. {span_hi:.4f}")
    print(f"|value| <= 0.02 on {small} of {pooled}")
    print()
    print("The NaNs are a LEADING PREFIX and nothing else:")
    for name in FRAMES:
        col = j_acosc(*FRAMES[name]())
        na = np.flatnonzero(col.isna().to_numpy())
        contiguous = bool(na.size == 0
                          or (na == np.arange(na.size)).all())
        print(f"    {name:<14} NaNs {na.size:>4}  contiguous-from-zero "
              f"{contiguous}")
    print()
    print("Short frames, i.e. `MIN_BARS` as a floor on the INPUT:")
    h, l, c = _walk()
    short = MIN_BARS - 1
    print(f"    {short} bars -> {j_acosc(h.iloc[:short], l.iloc[:short], c.iloc[:short])}")
    ok = j_acosc(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS], c.iloc[:MIN_BARS])
    print(f"    {MIN_BARS} bars -> fires on {int(ok.notna().sum())} bar(s)")
    print()
    print(f"WARMUP = SLOW + SIGNAL - 2 = {SLOW} + {SIGNAL} - 2 = {WARMUP}, and")
    print("the AO leg alone would be SLOW - 1 = "
          f"{SLOW - 1}:")
    frame = _walk()
    a = fork_ao(frame[0], frame[1])
    print(f"    AO's own leading NaNs: {int(a.isna().sum())}")
    print(f"    the column's:          {int(j_acosc(*frame).isna().sum())}")


def section_D():
    _head("D Gate D -- scale-free")
    print("(a) EXACT factors. Every step is linear in the price and the")
    print("    final division cancels the factor, so x8 and x64 -- exact")
    print("    powers of two -- must be bit-identical.")
    print(f"    {'frame':<14} {'factor':>7} {'masks':>5} {'bars':>6} "
          f"{'bit-eq':>7} {'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        base = j_acosc(*frame)
        for factor in (8.0, 64.0):
            masks, shared, same, d, _ = _agree(
                base, j_acosc(*_scaled(frame, factor)))
            print(f"    {name:<14} {factor:>7.0f} {str(masks):>5} "
                  f"{shared:>6} {same:>7} {d:>12.3e}")
    print()
    print("(b) INEXACT factors, where the price itself loses its last bits.")
    print("    This column is a difference of differences of nearby rolling")
    print("    means, so it AMPLIFIES that loss; the figure below is what")
    print("    `tests/test_j_acosc.py` bounds.")
    print(f"    {'frame':<14} {'factor':>12} {'masks':>5} {'max |rel|':>11}")
    worst = 0.0
    for name in VARYING:
        frame = FRAMES[name]()
        base = j_acosc(*frame)
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            masks, _, _, _, rel = _agree(base,
                                         j_acosc(*_scaled(frame, factor)))
            worst = max(worst, 0.0 if np.isnan(rel) else rel)
            print(f"    {name:<14} {factor:>12.7g} {str(masks):>5} "
                  f"{rel:>11.3e}")
    print()
    print(f"    worst relative difference: {worst:.3e}")
    print()
    print("(c) extreme price LEVELS -- the same walk rebuilt at each level,")
    print("    not a rescale, so this also says the frame builder is sane.")
    print("    The last two columns re-run (a) AT that level, so the x8/x64")
    print("    claim is measured there and not extrapolated from level 100.")
    print(f"    {'level':>10} {'fired':>6} {'finite':>7} "
          f"{'max |value|, all 17 digits':>27} "
          f"{'x8 bit-eq':>10} {'x64 bit-eq':>11}")
    maxima = []
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        col = j_acosc(*frame)
        v = col.dropna().to_numpy()
        eq = []
        for factor in (8.0, 64.0):
            masks, _, same, _, _ = _agree(col, j_acosc(*_scaled(frame,
                                                                factor)))
            eq.append(same if masks else -1)
        maxima.append(float(np.abs(v).max()))
        print(f"    {level:>10.0e} {v.size:>6} {int(np.isfinite(v).sum()):>7} "
              f"{maxima[-1]:>27.17g} {eq[0]:>10} {eq[1]:>11}")
    print()
    print("    ⚠ The `max |value|` column is NOT bit-equal across the three")
    print("    and rounding it to 4 digits hid that. 1e-6, 1e+6 and 1e+100")
    print("    are not exact binary multiples, so `level * np.exp(...)`")
    print("    builds THREE different price paths in their last bits -- the")
    print("    division cancels the level, it cannot cancel a difference")
    print("    that is already in the prices. Measured spread, pairwise")
    print("    relative:")
    for i, j in ((0, 1), (0, 2), (1, 2)):
        print(f"      {maxima[i]:.17g} vs {maxima[j]:.17g}  "
              f"rel {abs(maxima[i] - maxima[j]) / maxima[j]:.3e}")
    print()
    print("(d) `0 < fires < n` on every frame, so a constant column cannot")
    print("    pass this gate:")
    for name in FRAMES:
        col = j_acosc(*FRAMES[name]())
        print(f"    {name:<14} 0 < {int(col.notna().sum())} < {col.size}  "
              f"{0 < int(col.notna().sum()) < col.size}")


def section_F():
    _head("F The filter -- 38 taps in `mid`, summing to zero to within 7e-18")
    h = _taps()
    print(f"tap count: {h.size} = SLOW + SIGNAL - 1 = {SLOW} + {SIGNAL} - 1")
    print(f"sum of taps (fsum): {math.fsum(h.tolist()):.3e}")
    print(f"max tap {h.max():+.6f} at lag {int(h.argmax())}, "
          f"min tap {h.min():+.6f} at lag {int(h.argmin())}")
    print(f"sum |tap|: {math.fsum(np.abs(h).tolist()):.17g}")
    print()
    print("Frequency response |H(w)|, w in radians/bar (period = 2*pi/w):")
    w = np.linspace(1e-9, np.pi, 200_001)
    g = np.array([_gain(h, x) for x in w])
    k = int(g.argmax())
    print(f"    DC       (w = 0)    {_gain(h, 0.0):.6f}")
    print(f"    peak     (w = {w[k]:.6f}, period {2 * np.pi / w[k]:.4f} bars) "
          f"{g[k]:.6f}")
    print(f"    Nyquist  (w = pi)   {_gain(h, np.pi):.6f}")
    print()
    print("The taps ARE the column: convolved against `mid` and divided by")
    print("close, they reproduce the module (bound, not bit-equality -- a")
    print("dot product is not pandas' rolling accumulator).")
    print(f"    {'frame':<14} {'bars':>6} {'bit-eq':>7} {'max |diff|':>12} "
          f"{'max |rel|':>11}")
    for name in VARYING:
        frame = FRAMES[name]()
        hi, lo, c = frame
        mid = ((hi + lo) / 2).to_numpy(dtype=float)
        conv = np.full(mid.size, np.nan)
        for i in range(h.size - 1, mid.size):
            conv[i] = math.fsum((h * mid[i::-1][:h.size]).tolist())
        tap_col = Series(conv / c.to_numpy(dtype=float), index=c.index)
        _, shared, same, d, rel = _agree(j_acosc(*frame), tap_col)
        print(f"    {name:<14} {shared:>6} {same:>7} {d:>12.3e} {rel:>11.3e}")


def section_G():
    _head("G Guards, and the cases nothing guards")
    print("(a) a bad CLOSE empties its own bar and no other. Planted at bar")
    print("    700 of a 1,500-bar walk.")
    frame = _walk()
    base = j_acosc(*frame)
    h, l, c = frame
    print(f"    {'close':>10} {'emptied':>8} {'other bars moved':>18}")
    for bad in (np.nan, 0.0, -1.0, np.inf, -np.inf, 1e-310):
        c2 = c.copy()
        c2.iloc[700] = bad
        out = j_acosc(h, l, c2)
        emptied = int((base.notna() & out.isna()).sum())
        m = base.notna() & out.notna()
        moved = int((base[m] != out[m]).sum())
        print(f"    {bad:>10} {emptied:>8} {moved:>18}")
    print()
    print("(b) what the guard BUYS: the same plants with the guard removed.")
    off = _mutant(*MUTANTS[-1][2:])
    print(f"    {'close':>10} {'reading at bar 700':>22}")
    for bad in (0.0, -1.0, 1e-310):
        c2 = c.copy()
        c2.iloc[700] = bad
        print(f"    {bad:>10} {float(off(h, l, c2).iloc[700]):>22.6g}")
    print()
    print("(c) a bad HIGH or LOW is NOT absorbed -- unlike `j_gator`, whose")
    print("    `ewm` skips the observation. `rolling(...).mean()` propagates")
    print("    a NaN, so one bad bar empties the bars its windows reach.")
    print(f"    {'leg':>6} {'value':>10} {'emptied':>8} {'first':>6} "
          f"{'last':>6} {'moved<700':>10} {'moved>737':>10} "
          f"{'max |rel|':>11} {'non-finite':>11}")
    for leg in ("high", "low"):
        for bad in (np.nan, np.inf, -np.inf):
            parts = {"high": h.copy(), "low": l.copy(), "close": c.copy()}
            parts[leg].iloc[700] = bad
            out = j_acosc(parts["high"], parts["low"], parts["close"])
            empty = np.flatnonzero((base.notna() & out.isna()).to_numpy())
            m = base.notna() & out.notna()
            diff = (base[m] != out[m]).to_numpy()
            idx = np.flatnonzero(m.to_numpy())[diff]
            before = int((idx < 700).sum())
            after = int((idx > 737).sum())
            rel = float(((base[m] - out[m]).abs()
                         / base[m].abs().where(base[m].abs() > 0.0,
                                               np.nan)).max())
            nonfinite = int((~np.isfinite(out.dropna().to_numpy())).sum())
            print(f"    {leg:>6} {bad:>10} {empty.size:>8} "
                  f"{empty.min():>6} {empty.max():>6} {before:>10} "
                  f"{after:>10} {rel:>11.3e} {nonfinite:>11}")
    print()
    print(f"    The reach of one bad `mid` bar is SLOW + SIGNAL - 1 = "
          f"{SLOW + SIGNAL - 1} EMPTIED bars, 700..737 above. ⚠ Bars after")
    print("    737 also MOVE, and that is pandas' rolling accumulator and")
    print("    not contamination: a NaN makes it re-sum the window from")
    print("    scratch, so later windows round differently. The `max |rel|`")
    print("    column is the size of that -- and NO bar before 700 moves,")
    print("    which is the causal statement.")
    print()
    print("(d) a cross-scale frame: high/low at 1e+300, close at 1e-300.")
    hi, lo, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=hi.index)
    out = j_acosc(hi, lo, tiny)
    v = out.dropna().to_numpy()
    print(f"    fired {v.size} of 60, infinite {int(np.isinf(v).sum())}")
    print("    -- bad data rather than a price, unguarded and disclosed.")
    print()
    print("(e) degenerate frames, under `errstate(all='raise')`:")
    for value in (np.nan, 0.0, -5.0, 100.0):
        idx = date_range("2020-01-01", periods=60, freq="h")
        s = Series(np.full(60, value), index=idx)
        with np.errstate(all="raise"):
            out = j_acosc(s.copy(), s.copy(), s.copy())
        v = out.dropna()
        print(f"    all {value:>8}: fired {v.size:>3}, "
              f"all zero {bool((v == 0.0).all()) if v.size else 'n/a'}")


def section_L():
    _head("L What it is nearest to, IN THIS FORK (synthetic, not Gate E)")
    print("⚠ These are synthetic frames and fork columns. Gate E measures")
    print("687 ENGINE comparators over 89 real BIST frames and is the only")
    print("thing that decides the band; none of these columns is in it.")
    print()

    def _cols(frame):
        hi, lo, c = frame
        out = {}
        a = fork_ao(hi, lo)
        out["ao / close (the level this column differences)"] = a / c
        out["ao, 1-bar change / close"] = (a - a.shift(1)) / c
        sr = stochrsi(c)
        out["stochrsi: STOCHRSIk_14_14_3_3"] = sr.iloc[:, 0]
        out["stochrsi: STOCHRSId_14_14_3_3"] = sr.iloc[:, 1]
        out["qqe: QQEs_14_5_4.236"] = qqe(c).iloc[:, 1]
        out["cmo_14"] = cmo(c)
        out["er_10"] = er(c)
        out["chop_14"] = chop(hi, lo, c)
        out["natr_14"] = natr(hi, lo, c)
        f = fwma(c, 10)
        out["⚠ PROXY fwma(10) 1-bar pct change"] = f / f.shift(1) - 1.0
        return out

    names = list(_cols(_walk()))
    print(f"{'comparator':<48} " + " ".join(f"{n[:9]:>9}" for n in VARYING))
    worst = {}
    for label in names:
        row = []
        for name in VARYING:
            frame = FRAMES[name]()
            rho = _spearman(j_acosc(*frame), _cols(frame)[label])
            row.append(rho)
            worst[label] = max(worst.get(label, 0.0),
                               0.0 if np.isnan(rho) else abs(rho))
        print(f"{label:<48} " + " ".join(f"{r:>9.4f}" for r in row))
    print()
    print("max |rho| per comparator, worst first:")
    for label, v in sorted(worst.items(), key=lambda kv: -kv[1]):
        print(f"    {v:.4f}  {label}")
    print()
    print("⚠ The `fwma` row is a PROXY this session invented. The screen's")
    print("top Gate E comparator is the engine's `FWMA_Slope_pct_Pctl`, and")
    print("that definition is NOT readable from this worktree -- no number")
    print("here is evidence about it.")
    print()
    print("The screen's own fork-overlap stage (12 REAL frames, 2026-10-24)")
    print("put `stochrsi:STOCHRSIk_14_14_3_3` nearest at max |rho| 0.8233,")
    print("per-frame max median 0.8245. This table is a different universe")
    print("and neither of them is Gate E.")


def section_W():
    _head("W The docstring's first paragraph against the dictionary's cut")
    print("`docs/gen_indicator_dictionary.py`'s `desc()` keeps a paragraph")
    print("of up to 150 characters whole and otherwise drops the trailing")
    print("WORD. Measured by calling the generator's own function.")
    desc = _generator_desc()
    doc = j_acosc.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    print()
    print(f"paragraph ({len(paragraph)} chars): {paragraph}")
    print(f"desc() returns it whole: {desc({'desc': paragraph}) == paragraph}")
    slack = 0
    while desc({"desc": paragraph[:-1] + "x" * (slack + 1) + paragraph[-1:]}) \
            == paragraph[:-1] + "x" * (slack + 1) + paragraph[-1:]:
        slack += 1
        if slack > 200:
            break
    print(f"characters of slack before a word is lost: {slack}")


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out with
    `ast` -- importing that module runs its whole indicator probe."""
    import ast
    import re
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


def section_Z():
    _head("Z Cost")
    print("⚠ Machine- and run-dependent. Best of 5, printed as a range over")
    print("two repeats so the spread is visible rather than hidden.")
    print()
    print(f"{'bars':>8} {'ms (best of 5, two runs)':>28} {'peak MB':>9}")
    for n in (100_000, 400_000):
        frame = _walk(n=n)
        times = [min(timeit.repeat(lambda: j_acosc(*frame), number=1,
                                   repeat=5)) * 1e3 for _ in range(2)]
        tracemalloc.start()
        j_acosc(*frame)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        print(f"{n:>8} {min(times):>13.1f} .. {max(times):<13.1f} "
              f"{peak:>9.1f}")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "B": section_B, "C": section_C, "D": section_D, "F": section_F,
    "G": section_G, "L": section_L, "W": section_W, "Z": section_Z,
}


if __name__ == "__main__":
    print(f"pandas {pd.__version__}, numpy {np.__version__}")
    print(f"jesse installed: {importlib.util.find_spec('jesse') is not None}")
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
