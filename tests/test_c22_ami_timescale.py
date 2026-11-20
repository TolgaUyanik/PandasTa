# -*- coding: utf-8 -*-
"""C22-AMI-TIMESCALE: `c22_ami_timescale`, catch22's first minimum of the
Gaussian automutual information over the last 100 daily returns (issue #125).

Every number here was measured by `docs/measure_c22_ami_timescale.py` on this
machine; the receipt is `docs/C22AmiTimescaleMeasured.md`. What is pinned, in
order of how much it would hurt to lose:

1. **THE ESTIMATOR.** The Gaussian AMI needs a correlation, and the sources
   leave three readings open: the lagged pair's own PEARSON correlation
   (`corr(x[:-tau], x[tau:])`, each limb demeaned by its own mean), the
   window's BIASED autocorrelation (one mean, one variance, divisor `n`), and
   the ADJUSTED one (divisor `n - k`). This module ships the first, which is
   what hctsa's `CO_AutoMutualInfo(..., 'gaussian')` spells and what the
   reference implementation measurably computes. The other two are REAL
   columns, not rounding: over the 1,400 bars of each of the five
   non-deterministic frames, the biased reading disagrees with this one on 10
   to 51 bars (Spearman +0.974 to +0.993) and the adjusted on 9 to 45
   (+0.980 to +0.995), so a future "fix" that swaps the estimator changes
   shipped values. ⚠ On the cosine frame all three readings coincide (1,400 of
   1,400) -- a clean cycle moves every estimator the same way -- which is
   why `test_the_biased_reading_is_a_different_column` and its adjusted twin
   run on the stochastic frames and not on that one.
2. **The four independent oracles agree bit-for-bit.** An exact
   `fractions.Fraction` oracle that rounds ZERO times (the AMI is strictly
   increasing in `rho**2`, so the first minimum is decided by exact rational
   comparisons), a plain-Python `math.fsum` spelling, `np.corrcoef` and
   `pandas.Series.corr`. 0 disagreements on every window these tests sample.
3. **The quarter-period law.** Returns that are an exact cosine of period P
   read exactly `P / 4` on every fired bar at P = 8, 12, 20, 40 and 80 --
   a CONSTANT column by construction, which is the feature working, not a
   dead column. At P = 120 the window (100 returns) no longer holds a full
   period and the law breaks: 17 distinct values, 21 .. 40.
4. **Causality.** 0 of 35 offsets leak on each of six frames with eight
   splices apiece, and 0 of 35 at `length` 80, 120 and 250. Four look-ahead
   mutants and one back-dating mutant are read off this module's own source,
   edited and exec'd in memory.
   ⚠ A ONE-BAR look-ahead is only detectable on 22 of 35 offsets (walk) and
   16 of 35 (tick-rounded), and on 0 of 35 of a frame where the column is
   constant: the column is a small integer that ties on 78% to 100% of
   neighbouring bar pairs, so most splices cannot witness the shift. The
   ten-bar mutant is caught 35 of 35 on all three swept frames. Prefix
   truncation would prove even less, which is why the mutants are here.
5. **Scale-free by construction, and bit-identically so.** The price enters
   only as the ratio `c[t] / c[t-1]`, so `8a / 8b` IS the double `a / b`:
   x8, x64, x2**-40 and x2**40 are bit-identical on all six frames, at
   `length` 80, 120 and 250, and at price levels 1e-6, 1e+6 and 1e+100.
   x10, x3.7, x0.1 and x1.0000001 moved 0 bars of 8,400 here -- which the
   arithmetic does not promise for an integer decided by float comparisons;
   what makes it hold is the measured margin, the smallest gap in `rho**2`
   between the deciding lag and the neighbour it beats being 3.6e-09.
6. **The clip is load-bearing.** `rho**2` is bounded by 1 by Cauchy-Schwarz,
   and rounding breaks that bound on real input: 218 of 8,000 (window, lag)
   cells of an exact 20-bar cosine come out above 1 (worst 1 + 9e-16) and
   2,319 of 8,000 do on an alternating frame. Without `np.minimum(.., 1.0)`
   those cells hand the scan a NaN.
7. **The degenerate corner is disclosed, not hidden.** On a frame whose
   returns alternate +2% / -2% exactly, the two limbs of every lag are the
   same sequence up to a sign, `rho**2` is 1 to within 7e-16 at all 40 lags,
   and WHICH lag is reported is decided by the last bits: 31 distinct values
   over 1,400 bars, and a x10 rescale moves 1,197 of them. No stochastic
   frame is anywhere near that corner (max `rho**2` 0.53).
8. **Bad data and the three blanking rules.** A close that is NaN, infinite,
   zero, negative or subnormal empties exactly its own 101 windows; a close
   PAIR whose ratio overflows empties 100. A window whose returns do not
   vary beyond 9.09e-13 is blank (the floor); so is one in which either limb
   of some lag is CONSTANT; and so is one whose limb sums of squares
   OVERFLOW although the returns are finite, which a close pair of ratio
   1e200 reaches and one of ratio 1e77 does not. Each of the three is blank
   rather than a value, and the last two were added because the unguarded
   spelling reads the SENTINEL 40 there -- the top of the scale,
   indistinguishable from a real "no dip" -- on 20 bars of a 1-ulp-step
   frame and 100 bars of the 1e200 frame.
9. Gate E is OWED. `tests/test_gate_e_ledger.py` fails until the row is
   recorded, which is the receipt session's cue; the two tests at the bottom
   of this file assert the row is absent and that the receipt says so.

Not pinned on purpose: exact counts of distinct values, exact bars-moved
counts under an inexact rescale, and any rho to 1e-6. Those move with
numpy's CPU dispatch; the tests pin bounds and bands, and the docstrings
state the local figure.
"""
import csv
import importlib
import io
import math
import os
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.c22_ami_timescale import (
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, NO_MINIMUM, TAU_MAX,
    c22_ami_timescale)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_ami_timescale")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100

#: Strides for the oracles that are too slow for all 1,400 windows of a
#: frame. Every count asserted below is a count of what actually ran.
EXACT_STRIDE = 61
PY_STRIDE = 29


# ------------------------------------------------------------- frames
def walk(n=1500, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=1500, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: 21.7% of returns are exactly 0."""
    return Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=1500, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


def student_t(n=1500, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def alternating(n=1500, up=0.02, down=0.02):
    r = np.where(np.arange(n) % 2 == 0, up, -down)
    return Series(100.0 * np.cumprod(1.0 + r))


def ladder(n=1500, step=0.01, start=100.0):
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
#: The five frames whose returns are not deterministic. The cosine frame is
#: CONSTANT by construction (section 3 of this file's docstring), so it is
#: excluded from "not constant" assertions and named in them instead.
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_ami_timescale(FRAMES[name])
    return _BASE[name]


def windows(close, length=LENGTH):
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1.0
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


def diff_bars(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(x[both] != y[both])),
            int(np.sum(np.isnan(x) != np.isnan(y))))


def spearman(a, b):
    x, y = Series(np.asarray(a, float)), Series(np.asarray(b, float))
    m = x.notna() & y.notna()
    rx, ry = x[m].rank(), y[m].rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


# ------------------------------------------------------------- Gate A
def _scan(values, inclusive=False):
    for i in range(1, TAU_MAX - 1):
        if inclusive:
            if values[i] <= values[i - 1] and values[i] <= values[i + 1]:
                return i + 1
        elif values[i] < values[i - 1] and values[i] < values[i + 1]:
            return i + 1
    return TAU_MAX


def fmmi_exact(window):
    """The definition in exact rational arithmetic -- zero roundings."""
    xs = [Fraction(float(v)) for v in window]
    n = len(xs)
    r2 = []
    for k in range(1, TAU_MAX + 1):
        a, b = xs[:n - k], xs[k:]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        da = [x - ma for x in a]
        db = [x - mb for x in b]
        sa = sum(x * x for x in da)
        sb = sum(x * x for x in db)
        if sa == 0 or sb == 0:
            return None
        num = sum(x * y for x, y in zip(da, db))
        r2.append((num * num) / (sa * sb))
    return _scan(r2)


def ami_fsum(window):
    w = [float(v) for v in window]
    n = len(w)
    out = []
    for k in range(1, TAU_MAX + 1):
        a, b = w[:n - k], w[k:]
        ma, mb = math.fsum(a) / len(a), math.fsum(b) / len(b)
        da = [x - ma for x in a]
        db = [x - mb for x in b]
        sa = math.fsum(x * x for x in da)
        sb = math.fsum(x * x for x in db)
        if not (sa > 0.0 and sb > 0.0):
            return None
        r2 = min((math.fsum(x * y for x, y in zip(da, db))
                  / math.sqrt(sa * sb)) ** 2, 1.0)
        out.append(math.inf if r2 >= 1.0 else -0.5 * math.log(1.0 - r2))
    return out


def fmmi_library(window, how="numpy"):
    w = np.asarray(window, float)
    n = w.size
    ami = []
    for k in range(1, TAU_MAX + 1):
        y1, y2 = w[:n - k], w[k:]
        if y1.std() == 0.0 or y2.std() == 0.0:
            return None
        r = (float(np.corrcoef(y1, y2)[0, 1]) if how == "numpy"
             else float(Series(y1).corr(Series(y2))))
        r2 = min(r * r, 1.0)
        ami.append(math.inf if r2 >= 1.0 else -0.5 * math.log(1.0 - r2))
    return _scan(ami)


def rho2_pearson(window, clip=True):
    w = np.asarray(window, float)
    n = w.size
    out = np.empty(TAU_MAX)
    for k in range(1, TAU_MAX + 1):
        a, b = w[:n - k], w[k:]
        da, db = a - a.mean(), b - b.mean()
        den = math.sqrt(float((da * da).sum()) * float((db * db).sum()))
        raw = ((float((da * db).sum()) / den) ** 2 if den > 0.0
               else float("nan"))
        out[k - 1] = min(raw, 1.0) if clip else raw
    return out


def fmmi_biased(window):
    w = np.asarray(window, float)
    n = w.size
    d = w - w.mean()
    ss = float((d * d).sum())
    if ss == 0.0:
        return None
    return _scan([min((float((d[:n - k] * d[k:]).sum()) / ss) ** 2, 1.0)
                  for k in range(1, TAU_MAX + 1)])


def fmmi_adjusted(window):
    w = np.asarray(window, float)
    n = w.size
    d = w - w.mean()
    var = float((d * d).mean())
    if var == 0.0:
        return None
    return _scan([min((float((d[:n - k] * d[k:]).mean()) / var) ** 2, 1.0)
                  for k in range(1, TAU_MAX + 1)])


@pytest.mark.parametrize("frame", ["walk", "penny", "cosine"])
def test_bit_equal_to_the_exact_rational_oracle(frame):
    """Gate A's strongest limb: an oracle that rounds ZERO times.

    `rho**2 = (sum da*db)**2 / (sum da**2 * sum db**2)` over exactly
    representable doubles is a ratio of integers, and the AMI is strictly
    increasing in it, so the first minimum is decided by exact rational
    comparisons. Measured: 0 disagreements on every window of all six frames
    at stride 13 (648 windows); three frames at stride 61 here, for runtime.
    """
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    checked = bad = 0
    for row, bar in zip(win[::EXACT_STRIDE], bars[::EXACT_STRIDE]):
        want = fmmi_exact(row)
        if want is None:
            continue
        checked += 1
        bad += float(want) != out.iloc[bar]
    assert checked >= 20, checked
    assert bad == 0, f"{bad} of {checked} windows disagree with the exact oracle"


@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_equal_to_an_independent_fsum_spelling(frame):
    """A plain-Python spelling that shares no code with the module: explicit
    slices, `math.fsum`, `math.log(1 - r*r)` instead of `np.log1p(-r2)`."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    checked = bad = 0
    for row, bar in zip(win[::PY_STRIDE], bars[::PY_STRIDE]):
        ami = ami_fsum(row)
        if ami is None:
            continue
        checked += 1
        bad += float(_scan(ami)) != out.iloc[bar]
    assert checked >= 40, checked
    assert bad == 0, f"{bad} of {checked} windows disagree with the fsum oracle"


@pytest.mark.parametrize("how", ["numpy", "pandas"])
@pytest.mark.parametrize("frame", ["walk", "ar1", "cosine"])
def test_a_library_correlation_agrees(how, frame):
    """The lagged-pair correlation taken by `np.corrcoef` / `Series.corr`
    rather than by hand. Measured max |rho**2 - library| 2.1e-15."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    checked = bad = 0
    for row, bar in zip(win[::PY_STRIDE], bars[::PY_STRIDE]):
        want = fmmi_library(row, how=how)
        if want is None:
            continue
        checked += 1
        bad += float(want) != out.iloc[bar]
    assert checked >= 40, checked
    assert bad == 0, f"{bad} of {checked} windows disagree with {how}"


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """pycatch22 is GPL-3.0 and this fork is MIT: the port is written from the
    definitions, and no shipped module or test may import the reference.

    ⚠ It IS installed in this worktree (measured 2026-11-20), so this is a
    real guard and not a vacuous one. `docs/measure_c22_ami_timescale.py`
    section P does import it, deliberately and opt-in, to answer one question:
    whether this column is the column the 2026-10-24 screen measured. That
    file is a measurement harness, not shipped code.
    """
    # Both this file and the module name the library in PROSE -- the module's
    # docstring has to attribute it. What must not exist anywhere in the
    # package or in this test module is an import of it, so the check is on
    # import statements and not on the text.
    def imports_it(text):
        return [line.strip() for line in text.splitlines()
                if line.lstrip().startswith(("import ", "from "))
                and "pycatch22" in line]

    assert imports_it(SRC) == []
    assert imports_it(io.open(__file__, encoding="utf8").read()) == []
    offenders = {p.relative_to(ROOT).as_posix(): imports_it(
        p.read_text(encoding="utf-8"))
        for p in (ROOT / "pandas_ta").rglob("*.py")}
    assert {k: v for k, v in offenders.items() if v} == {}
    assert len(offenders) > 300, len(offenders)   # the sweep really ran


@pytest.mark.parametrize("period,expected", [(8, 2), (12, 3), (20, 5),
                                             (40, 10), (80, 20)])
def test_a_cosine_in_returns_reads_a_quarter_of_its_period(period, expected):
    """The interpretation, as a law: `rho(tau)` of a cosine of period P is a
    cosine of the same period, so `rho**2` first dips a quarter of a period
    in. Constant on every fired bar at these five periods."""
    s = c22_ami_timescale(cosine_returns(period=period)).dropna()
    assert s.nunique() == 1, sorted(set(s))
    assert float(s.iloc[0]) == float(expected)


def test_a_period_the_window_cannot_hold_breaks_the_quarter_rule():
    """P = 120 against a 100-return window: the law needs the window to hold
    a full period. Measured: 17 distinct values, 21 .. 40 -- so this is also
    where the sentinel becomes reachable."""
    s = c22_ami_timescale(cosine_returns(period=120)).dropna()
    assert s.nunique() > 5, s.nunique()
    assert s.min() >= 2 and s.max() == NO_MINIMUM
    assert float(NO_MINIMUM) in set(s)


def test_the_sentinel_means_no_dip_and_is_reachable_but_rare():
    """`NO_MINIMUM` is `TAU_MAX`, and it is a sentinel: "no lag in 2 .. 39 is
    below both neighbours". Measured: 0 of 8,400 bars of the six frames reach
    it, and the P = 120 cosine reaches it."""
    assert NO_MINIMUM == TAU_MAX == 40
    reached = sum(int((base(f).dropna() == NO_MINIMUM).sum()) for f in FRAMES)
    assert reached == 0, reached
    assert float(NO_MINIMUM) in set(
        c22_ami_timescale(cosine_returns(period=120)).dropna())


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_output_is_a_whole_number_between_two_and_tau_max(frame):
    """A local minimum needs a neighbour on both sides, so lag 1 is not
    testable and the scan runs 2 .. 39 with TAU_MAX as the fallback."""
    s = base(frame).dropna()
    assert len(s) > 0
    assert s.min() >= 2.0 and s.max() <= float(TAU_MAX)
    assert np.all(s.to_numpy() == np.round(s.to_numpy()))


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_rho2_scan_is_the_same_column_as_the_ami_scan(frame):
    """The monotone equivalence the exact oracle relies on, in floating
    point: scanning `rho**2` and scanning `-0.5*log1p(-rho**2)` pick the same
    lag on all 1,400 windows of each frame. log1p is not strictly monotone on
    doubles, so this is measured rather than assumed."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    bad = 0
    for row, bar in zip(win, bars):
        r2 = rho2_pearson(row)
        if np.isnan(r2).any():
            continue
        bad += float(_scan(r2)) != out.iloc[bar]
    assert bad == 0, bad


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "ar1"])
def test_the_biased_reading_is_a_different_column(frame):
    """The window's BIASED ACF (one mean, one variance) instead of the lagged
    pair's own Pearson correlation. Measured: equal on 1,349 to 1,390 of
    1,400 bars, Spearman +0.974 to +0.993 -- close, and NOT the same column.
    If this ever comes out identical, the module's estimator has been
    swapped."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    mine, theirs = [], []
    for row, bar in zip(win, bars):
        alt = fmmi_biased(row)
        if alt is None or np.isnan(out.iloc[bar]):
            continue
        mine.append(float(out.iloc[bar]))
        theirs.append(float(alt))
    equal = sum(1 for a, b in zip(mine, theirs) if a == b)
    assert len(mine) > 1000
    assert equal < len(mine), "the biased reading is no longer distinguishable"
    assert equal / len(mine) > 0.90, equal / len(mine)
    assert spearman(mine, theirs) > 0.90


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "ar1"])
def test_the_adjusted_reading_is_also_a_different_column(frame):
    """Same for the ADJUSTED ACF (divisor `n - k`): equal on 1,355 to 1,391
    of 1,400 bars, Spearman +0.980 to +0.995."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    mine, theirs = [], []
    for row, bar in zip(win, bars):
        alt = fmmi_adjusted(row)
        if alt is None or np.isnan(out.iloc[bar]):
            continue
        mine.append(float(out.iloc[bar]))
        theirs.append(float(alt))
    equal = sum(1 for a, b in zip(mine, theirs) if a == b)
    assert len(mine) > 1000
    assert equal < len(mine)
    assert equal / len(mine) > 0.90, equal / len(mine)


@pytest.mark.parametrize("frame", ["walk", "penny"])
def test_the_inclusive_reading_is_unreachable_on_these_frames(frame):
    """`<=` where the module has `<`. Kept strict because that is what a
    local minimum means; measured, the difference is unreachable rather than
    cosmetic -- 0 exact ties between neighbouring lags' AMI in the windows
    sampled here."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    ties = checked = 0
    for row, bar in zip(win[::PY_STRIDE], bars[::PY_STRIDE]):
        ami = ami_fsum(row)
        if ami is None:
            continue
        checked += 1
        assert float(_scan(ami, inclusive=True)) == out.iloc[bar]
        ties += sum(1 for i in range(1, TAU_MAX) if ami[i] == ami[i - 1])
    assert checked >= 40
    assert ties == 0, ties


def test_the_clip_is_load_bearing_on_an_exact_cosine():
    """Cauchy-Schwarz bounds `rho**2` by 1; rounding does not. Measured on
    the 20-bar cosine frame: cells above 1 exist, worst 1 + 9e-16, and
    without the clip `log1p` of a number below -1 is NaN."""
    win, _ = windows(cosine_returns(period=20))
    over = nan_cells = cells = 0
    worst = 1.0
    for row in win[::PY_STRIDE]:
        raw = rho2_pearson(row, clip=False)
        cells += int(np.sum(np.isfinite(raw)))
        over += int(np.sum(raw > 1.0))
        worst = max(worst, float(np.nanmax(raw)))
        with np.errstate(invalid="ignore", divide="ignore"):
            nan_cells += int(np.sum(np.isnan(-0.5 * np.log1p(-raw))
                                    & np.isfinite(raw)))
    assert cells > 1000, cells
    assert over > 0, "the clip no longer binds -- re-measure before removing it"
    assert worst > 1.0 and worst < 1.0 + 1e-12, worst
    assert nan_cells == over
    assert "np.minimum" in SRC


def test_the_alternating_frame_is_the_degenerate_corner():
    """Disclosure, pinned. Exactly alternating returns make the two limbs of
    every lag the same sequence up to a sign, so `rho**2` is 1 to within
    7e-16 at all 40 lags and the reported lag is decided by the last bits:
    31 distinct values over 1,400 bars here, and a x10 rescale moves 1,197
    of them. The six realistic frames top out at `rho**2` 0.53."""
    frame = alternating()
    r2 = rho2_pearson(windows(frame)[0][0], clip=False)
    assert float(np.nanmin(r2)) > 1.0 - 1e-12
    s = c22_ami_timescale(frame)
    assert s.dropna().nunique() > 10, s.dropna().nunique()
    moved, mask = diff_bars(s, c22_ami_timescale(frame * 10.0))
    assert moved > 100, moved
    worst = max(float(np.nanmax(rho2_pearson(w, clip=False)))
                for f in ("walk", "ar1", "student-t")
                for w in windows(FRAMES[f])[0][::200])
    assert worst < 0.9, worst


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": ("out[length + a:length + b]",
                         "out[length - 1 + a:length - 1 + b]"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
}


def mutant(name):
    """Read this module off disk, edit one write, exec it in memory."""
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_ami_timescale"]


def _spliced(close, j, seed=909):
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=35):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=8):
    bad = np.asarray(fn(close), float)
    hits = []
    for j in offsets:
        for s in range(splices):
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s)),
                               float)
            if not same(bad[:j], other[:j]):
                hits.append(j)
                break
    return hits


@pytest.mark.parametrize("frame", list(FRAMES))
def test_real_module_never_reads_the_future(frame):
    """Future-perturbation sweep: replace every close from J on and no bar
    before J may move. 0 of 35 offsets leak on each frame, eight splices
    apiece."""
    f = FRAMES[frame]
    assert _leaks(c22_ami_timescale, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_ami_timescale(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled"])
def test_each_mutant_is_caught(name):
    """Each look-ahead mutant must be caught by the same sweep the real
    module passes clean. Measured on the walk frame: 22 of 35 offsets for the
    three one-bar mutants, 35 of 35 for the ten-bar one."""
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=8)
    assert len(hits) >= 10, (name, len(hits))
    if name == "window-ten-ahead":
        assert len(hits) == 35, len(hits)


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
    """A back-dated write moves bar J-1 and bars after it, never bar J-2 or
    earlier for a splice at J... which is exactly what makes it a look-ahead
    of ONE bar. Measured: the first moved bar is J-1 at every offset where
    anything moves."""
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    seen = 0
    for j in _offsets(len(f), count=12):
        other = np.asarray(fn(_spliced(f, j)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            seen += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert seen >= 3, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    """The fifth mutant back-dates the bad-data mask instead of a value, so a
    clean frame cannot see it: bit-equal on all 1,500 bars of the walk. On a
    frame with one bad close it moves exactly bar J-1, caught 12 of 12."""
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_ami_timescale(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_ami_timescale(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_column_ties_often_enough_to_hide_a_one_bar_shift(frame):
    """Why the mutant counts above are not 35 of 35, and why prefix
    truncation would prove nothing here: neighbouring bars carry the same
    small integer 77.6% to 100% of the time (measured)."""
    s = base(frame).dropna().to_numpy()
    tied = float(np.mean(s[1:] == s[:-1]))
    assert tied > 0.70, tied


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    """1,400 of 1,500 on every frame, and the first fired bar is `length`:
    the window ending at bar T holds the returns of bars T-99 .. T, which
    read closes T-100 .. T."""
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().values.argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_column_is_not_constant_on_a_stochastic_frame(frame):
    """Gate D's "not constant" limb. Measured: 6 to 10 distinct values per
    frame, range [2, 11], median 3 (5 on the AR(1) frame). The cosine frame
    IS constant, by construction, and is excluded by name."""
    s = base(frame).dropna()
    assert s.nunique() >= 4, s.nunique()
    assert 0 < int(s.notna().sum()) < len(FRAMES[frame])


def test_the_cosine_frame_is_constant_by_construction_not_by_death():
    """The one frame that fails "not constant" is the one whose answer is a
    constant: a 20-bar cosine reads 5 everywhere, and 5 is `period / 4`."""
    s = base("cosine").dropna()
    assert s.nunique() == 1 and float(s.iloc[0]) == 5.0


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry, checked: a 2-lira stock on a 1-kurus tick
    prints 325 of 1,499 returns (21.7%) as exactly 0.00% and still fires on
    all 1,400 bars with 6 distinct values. Zero returns do not blank a
    window; only a window with NO variation at all does."""
    f = FRAMES["penny"]
    c = f.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.10
    s = base("penny")
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert s.dropna().nunique() >= 4


def test_a_flat_run_empties_its_windows_from_the_lag_40_limb_on():
    """A flat run empties its own windows rather than reading 0 or the
    sentinel -- and it starts doing so EARLIER than a reader expects. The
    closes go flat at bar 400, so the returns of bars 401 on are exactly 0;
    the lag-40 limb of bar T is the returns of bars T-59 .. T, so bar 460 is
    already blank, 40 bars before the whole window is flat."""
    f = Series(np.r_[walk(400).to_numpy(), np.full(300, 50.0)])
    s = c22_ami_timescale(f)
    assert s.iloc[460:].isna().all()
    assert s.iloc[400:460].notna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    """Blank, not a sentinel -- and the mechanism is the FLOOR, not the
    constant-limb rule, which is measured because the obvious story is wrong.
    `start * (1 + step)**k` rounds every power on its own, so the window holds
    3 to 5 DISTINCT returns (no limb is constant) with a standard deviation of
    1e-16 against the 9.09e-13 floor. Unguarded, all three ladders fire all
    1,400 bars and read inside [2, 14] with medians 2 to 3 -- i.e. values
    indistinguishable from a real frame's, off 1e-16 of rounding."""
    f = ladder(step=step)
    assert int(c22_ami_timescale(f).notna().sum()) == 0
    c = f.to_numpy(dtype=float)
    r = (c[1:] / c[:-1] - 1.0)[:LENGTH]
    assert len(set(r)) > 1, "the ladder's returns are identical doubles after all"
    assert float(np.std(r)) < NOISE_FLOOR
    loose = unguarded()(f).dropna()
    assert len(loose) > 1000, len(loose)
    assert 2 <= loose.min() and loose.max() <= 20, (loose.min(), loose.max())


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_exact_binary_rescale_is_bit_identical(frame, factor):
    """Scale-free BY CONSTRUCTION: the price enters only as `c[t]/c[t-1]`,
    and `8a / 8b` is the same double as `a / b`."""
    assert same(base(frame), c22_ami_timescale(FRAMES[frame] * factor))


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_the_scale_invariance_holds_at_non_default_lengths(length, factor):
    f = FRAMES["walk"]
    assert same(c22_ami_timescale(f, length=length),
                c22_ami_timescale(f * factor, length=length))


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_the_scale_invariance_holds_at_every_price_level(price):
    f = walk(level=price)
    assert int(c22_ami_timescale(f).notna().sum()) == len(f) - LENGTH
    assert same(c22_ami_timescale(f), c22_ami_timescale(f * 8.0))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_inexact_rescale_moves_almost_nothing(frame, factor):
    """An INEXACT rescale is not promised to be bit-identical -- the column
    is an integer decided by float comparisons. Measured here: 0 bars moved
    of 8,400, because the smallest margin any window has at its deciding lag
    is 3.6e-09 in `rho**2`. Bounded rather than pinned at 0, since the
    margin, not the arithmetic, is what makes it hold."""
    moved, mask = diff_bars(base(frame),
                            c22_ami_timescale(FRAMES[frame] * factor))
    assert mask == 0, mask
    assert moved <= 5, moved


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_decision_never_runs_near_a_rounding_flip(frame):
    """The margin behind the test above: the gap in `rho**2` between the
    deciding lag and the better of its two neighbours. Measured minimum
    3.6e-09 (penny), 7.3e-08 (walk)."""
    out, (win, bars) = base(frame), windows(FRAMES[frame])
    worst = math.inf
    for row, bar in zip(win[::7], bars[::7]):
        v = out.iloc[bar]
        if np.isnan(v):
            continue
        r2 = rho2_pearson(row)
        i = int(v) - 1
        if 1 <= i <= TAU_MAX - 2:
            worst = min(worst, r2[i - 1] - r2[i], r2[i + 1] - r2[i])
    assert worst > 1e-11, worst


@pytest.mark.parametrize("factor", [0.5, 2.0, 10.0])
def test_it_is_blind_to_the_amplitude_of_the_returns(factor):
    """Not a volatility column: rescaling the whole window's returns is a
    rescale of both limbs, which a correlation cannot see. 0 bars moved."""
    rng = np.random.default_rng(11)
    r = rng.normal(0.0, 0.015, 1500)
    a = Series(100.0 * np.cumprod(1.0 + r))
    b = Series(100.0 * np.cumprod(1.0 + factor * r))
    moved, mask = diff_bars(c22_ami_timescale(a), c22_ami_timescale(b))
    assert mask == 0 and moved <= 5, (moved, mask)


def test_it_is_not_blind_to_the_shape_of_the_returns():
    """The other half of the claim above: the same returns in a different
    ORDER move 1,049 of 1,400 bars."""
    c = FRAMES["walk"].to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1.0
    np.random.default_rng(3).shuffle(r)
    other = Series(100.0 * np.cumprod(np.r_[1.0, 1.0 + r]))
    moved, _ = diff_bars(base("walk"), c22_ami_timescale(other))
    assert moved > 500, moved


# ------------------------------------------------------- the noise floor
def unguarded():
    """This module with the floor removed -- the `bad` mask kept."""
    old = "return np.where(~bad & (sd > NOISE_FLOOR), out, np.nan)"
    new = "return np.where(~bad, out, np.nan)"
    assert SRC.count(old) == 1
    ns = {}
    exec(compile(SRC.replace(old, new), "<unguarded>", "exec"), ns)
    return ns["c22_ami_timescale"]


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_floor_is_inert_on_anything_price_shaped(frame):
    """0 bars differ between guarded and unguarded on all six frames, so the
    floor costs nothing on real shapes."""
    assert same(base(frame), unguarded()(FRAMES[frame]))


def test_what_the_floor_buys_on_a_single_ulp_step():
    """A price flat at 1e6 except for ONE 1-ulp step: 20 windows read the
    SENTINEL 40 without the floor -- the top of the scale, indistinguishable
    from a real "no dip in 40 lags" -- and NaN with it."""
    f = Series(np.r_[np.full(700, 1e6),
                     np.nextafter(np.full(800, 1e6), np.inf)])
    assert int(c22_ami_timescale(f).notna().sum()) == 0
    loose = unguarded()(f).dropna()
    assert len(loose) > 0 and set(loose) == {float(NO_MINIMUM)}


def test_a_one_tick_per_bar_path_is_blank_at_1e6_and_live_at_100():
    """What the floor and the limb guard between them refuse. At price 1e6 a
    1-kurus step is a 1e-11 return: the floor empties it (the unguarded
    spelling fires 1,400 bars). At price 100 the same step is a real 1e-4
    return and every bar fires."""
    big = Series(1e6 + 0.01 * np.arange(1500, dtype=float))
    assert int(c22_ami_timescale(big).notna().sum()) == 0
    assert int(unguarded()(big).notna().sum()) > 1000
    small = Series(100.0 + 0.01 * np.arange(1500, dtype=float))
    assert int(c22_ami_timescale(small).notna().sum()) == 1500 - LENGTH


def test_a_constant_limb_blanks_the_bar_even_when_the_window_varies():
    """The second blanking rule. A window holding 60 identical returns has a
    CONSTANT limb at lag 40, where a correlation does not exist; the bar is
    NaN although the window as a whole varies well above the floor."""
    c = walk(200).to_numpy()
    f = Series(np.r_[c, np.full(80, c[-1])])
    s = c22_ami_timescale(f)
    r = f.to_numpy()[1:] / f.to_numpy()[:-1] - 1.0
    # `close[200] == close[199]`, so the returns of bars 200 .. 279 are 0 --
    # eighty of them.
    # Bar 279's window is the returns of bars 180 .. 279: 20 live ones and 80
    # zeros, so its lag-40 limb (bars 220 .. 279) is constant.
    assert float(np.std(r[179:279])) > NOISE_FLOOR
    assert np.isnan(s.iloc[279])
    # Bar 240's lag-40 limb is the returns of bars 181 .. 240, which still
    # holds live returns, so it fires.
    assert not np.isnan(s.iloc[240])


# ------------------------------------------------------------- bad data
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310])
def test_a_bad_close_empties_exactly_its_own_windows(bad):
    """A close that is not finite, normal and positive has no return to take.
    It kills the returns on both sides of it, so exactly 101 bars go blank:
    700 .. 800 for a bad close at 700."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = bad
    s = c22_ami_timescale(f)
    blank = np.where(np.isnan(s.to_numpy()))[0]
    blank = blank[blank >= LENGTH]
    assert blank.min() == 700 and blank.max() == 800
    assert len(blank) == LENGTH + 1


def test_a_close_pair_whose_ratio_overflows_empties_its_windows():
    """1e-300 followed by 1e100 is a finite, positive, normal pair whose
    ratio is not: 100 bars blank, 701 .. 800."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-300
    f.iloc[701] = 1e100
    s = c22_ami_timescale(f)
    blank = np.where(np.isnan(s.to_numpy()))[0]
    blank = blank[blank >= LENGTH]
    assert blank.min() == 701 and blank.max() == 800
    assert len(blank) == LENGTH


def _without_the_overflow_guard():
    """This module with the `isfinite(den)` limb of the `bad` mask removed."""
    old = "bad |= ~(den > 0.0) | ~np.isfinite(den)"
    new = "bad |= ~(den > 0.0)"
    assert SRC.count(old) == 1
    ns = {}
    exec(compile(SRC.replace(old, new), "<no-overflow-guard>", "exec"), ns)
    return ns["c22_ami_timescale"]


def test_a_finite_but_enormous_return_blanks_rather_than_reading_the_sentinel():
    """The third blanking rule, and the only one whose absence produces a
    plausible WRONG value rather than a NaN.

    `close[700] = 1e-100` followed by `close[701] = 1e100` is a legal pair:
    both finite, positive and normal, and their ratio 1e200 is finite too, so
    the bad-return filter does not catch it. What overflows is the limb's sum
    of squared deviations, and `den` is then +inf with `den > 0.0` still True.
    Measured: the 100 windows holding that return are NaN here, and read the
    SENTINEL 40 with the guard removed."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-100
    f.iloc[701] = 1e100
    with np.errstate(over="ignore", invalid="ignore"):
        s = c22_ami_timescale(f)
        loose = _without_the_overflow_guard()(f)
    blank = np.where(np.isnan(s.to_numpy()))[0]
    blank = blank[blank >= LENGTH]
    assert blank.min() == 701 and blank.max() == 800
    assert len(blank) == LENGTH
    assert int((loose == NO_MINIMUM).sum()) == LENGTH
    assert int(loose.iloc[LENGTH:].isna().sum()) == 0


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_overflow_guard_is_inert_on_every_realistic_frame(frame):
    """It cannot have moved any figure in the receipt's §A-§D, which is why
    those sections were not re-measured after it was added: guarded and
    unguarded are bit-equal on all 1,400 fired bars of each of the six
    frames."""
    assert same(base(frame), _without_the_overflow_guard()(FRAMES[frame]))


@pytest.mark.parametrize("ratio_pair", [(1e-50, 1e27), (1e-20, 1e20)])
def test_the_overflow_guard_is_inert_where_the_sums_stay_finite(ratio_pair):
    """It is a guard on an OVERFLOW, not on a large number: at ratios 1e77 and
    1e40 the sums of squares are 1.0e154 and 1.0e80, both finite, the guarded
    and unguarded spellings are bit-equal, and the 25 bars that read the
    sentinel there are a genuine reading of a window one astronomic return
    dominates."""
    lo, hi = ratio_pair
    f = FRAMES["walk"].copy()
    f.iloc[700] = lo
    f.iloc[701] = hi
    with np.errstate(over="ignore", invalid="ignore"):
        assert same(c22_ami_timescale(f), _without_the_overflow_guard()(f))


@pytest.mark.parametrize("n,fires", [(LENGTH - 1, None), (LENGTH, None),
                                     (LENGTH + 1, 1), (LENGTH + 2, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    """`length` returns need `length + 1` closes."""
    s = c22_ami_timescale(walk(n))
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, 100, 1400), (0, 100, 1400), (1, 100, 1400),
    (MIN_LENGTH - 1, 100, 1400), (MIN_LENGTH, MIN_LENGTH, 1420),
    (250, 250, 1250), (250.7, 250, 1250)])
def test_the_length_guard_band(length, name, fires):
    """Below MIN_LENGTH (two returns per lag at lag 40) the default is used,
    and the column name carries whatever length was honoured."""
    s = c22_ami_timescale(FRAMES["walk"], length=length)
    assert s.name == f"C22AMITIMESCALE_{name}"
    assert int(s.notna().sum()) == fires


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_ami_timescale(FRAMES["walk"], offset=2)
    assert same(s, base("walk").shift(2))
    filled = c22_ami_timescale(FRAMES["walk"], fillna=-1.0)
    assert int(filled.isna().sum()) == 0
    assert int((filled == -1.0).sum()) == LENGTH


@pytest.mark.parametrize("budget", [LENGTH, 4 * LENGTH, 1 << 10])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Windows are walked in chunks to bound the peak; the chunk boundary
    must be invisible, which is also what keeps a per-row demean per-row."""
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        assert same(want, c22_ami_timescale(FRAMES["walk"]))
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    """A port that misses one computes correctly and is invisible."""
    assert callable(pandas_ta.c22_ami_timescale)
    assert "c22_ami_timescale" in pandas_ta.Category["statistics"]
    assert hasattr(DataFrame().ta, "c22_ami_timescale")
    assert (ROOT / "pandas_ta" / "statistics" / "c22_ami_timescale.py").exists()
    assert (ROOT / "tests" / "test_c22_ami_timescale.py").exists()
    s = base("walk")
    assert s.name == f"C22AMITIMESCALE_{LENGTH}"
    assert s.category == "statistics"


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    assert same(df.ta.c22_ami_timescale(), base("walk"))
    assert df.ta.c22_ami_timescale(length=250).name == "C22AMITIMESCALE_250"
    assert same(df.ta.c22_ami_timescale(offset=2), base("walk").shift(2))


def test_the_dictionary_row_describes_this_column():
    """CLAUDE.md sends a reader to `docs/IndicatorDictionary.md` first, so the
    row has to be there and has to name the column."""
    doc = io.open(ROOT / "docs" / "IndicatorDictionary.md",
                  encoding="utf8").read()
    assert "`c22_ami_timescale`" in doc
    assert f"`C22AMITIMESCALE_{LENGTH}`" in doc


def test_the_receipt_states_what_is_owed_and_what_is_disclosed():
    """The receipt is the deliverable the issue asks for. Three things in it
    are load-bearing for a later session: that Gate E is pending, that Gate
    C's real-data limb comes from the same run, and the RULE about issue
    #130's `CO_FirstMin_ac`, whose overlap with this column cannot be
    measured until it exists."""
    doc = io.open(ROOT / "docs" / "C22AmiTimescaleMeasured.md",
                  encoding="utf8").read()
    assert "Gate E: pending, run by issue-solver after this session" in doc
    assert "r3-perframe-0.90" in doc
    assert "#130" in doc
    assert "IN_AutoMutualInfoStats_40_gaussian_fmmi" in doc


def test_gate_e_is_owed_and_the_ledger_has_no_row_yet():
    """Gate E is run by issue-solver after this session, so there is no row
    and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row
    _has_one` reports this indicator. That failure is the receipt session's
    cue; this test is what tells that session the row is still missing."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "c22_ami_timescale"]
    assert rows == [], rows


def test_the_module_docstring_attributes_the_source():
    """The issue asks for the attribution in the docstring, and the licence
    note is part of it."""
    doc = c22_ami_timescale.__doc__
    for token in ("catch22", "Lubba", "2019", "hctsa",
                  "IN_AutoMutualInfoStats_40_gaussian_fmmi", "GPL-3.0"):
        assert token in doc, token
