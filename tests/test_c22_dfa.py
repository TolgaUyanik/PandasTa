# -*- coding: utf-8 -*-
"""C22-DFA: `c22_dfa`, catch22's DFA fluctuation scaling break over the last
100 daily returns (issue #128).

Every number here was measured by `docs/measure_c22_dfa.py` on this machine;
the receipt is `docs/C22DfaMeasured.md`. What is pinned, in order of how much
it would hurt to lose:

1. **THE COLUMN IS BIT-EQUAL TO THE REFERENCE, AND THAT IS WHAT SAYS THE
   DEFINITION WAS READ RIGHT.** Over every window of six frames -- 8,400 --
   this port equals the GPL-3.0 reference implementation exactly, with 0
   disagreements, and the same reading predicts it on 3,084 of 3,084 windows
   across all 32 ladder sizes the feature can produce (receipt §P1, §Q7).
   pycatch22 is GPL-3.0 and this fork is MIT, so that comparison lives in
   `docs/measure_c22_dfa.py` sections P and Q, opt-in and measurement only;
   what this module pins instead is every reading the fit settled, so a
   future edit that breaks one fails here rather than silently shipping a
   different column:
   * the sum of SQUARED residuals, not of the two residual norms (moves 100
     of 366 sampled windows);
   * the two pieces SHARE the scale at the break (167 of 366);
   * each piece gets `max(8, round(scales / 4))` scales -- a flat floor of
     6, 7 or 9 moves 181, 147 and 211 of 366;
   * the lag DECIMATES the window keeping its first point (233 of 366 for
     the end-aligned reading, 358 for no decimation);
   * the cumulative sum comes AFTER the decimation (194 of 366);
   * the ladder's top comes from the DECIMATED length (358 of 366);
   * the leftover points come off the TAIL of the profile (247 of 366);
   * `q = 2` and polynomial order 1 (95 and 259 of 366).
2. **It is a RATIO OF SMALL INTEGERS**: six values at the default `length`,
   8/21 .. 13/21. The tests pin the value SET, the derived bounds, and the
   tie share (20.3% to 35.3% on five stochastic frames, 100% on the cosine
   one) -- because the tie share is the ceiling on what any causality sweep
   can see here.
3. **The value at bar T does not read close[T]**, because the decimation
   drops the window's newest return. Pinned by the one-close-at-a-time
   dependency map: bar T moves only from closes in `[T-100, T-1]`, never
   from a close at or after T. That is causality AND staleness, and the
   staleness is a disclosure a consumer needs.
4. **Gate B needs a VIOLENT splice to have power.** Four mutants that look
   like look-aheads are causal for this column (a one-bar window shift still
   ends on a dropped return); the one that is a true one-bar look-ahead
   shifts the window TWO bars and is caught on 5 of 35 offsets by the gentle
   sweep and 28 of 35 by the violent one, where the real module leaks on 0
   of 35 under both.
5. **Two blanking rules**, and the zero-fluctuation one is REACHED on data
   with real variation: bar 754 of a frame whose returns are exactly 0 then
   exactly +1% has `F = 0` at 17 of its 21 scales.
6. **Scale-freeness is total**: the output is an integer choice whose
   runner-up is at least 3.598e-04 away in relative score, so x8, x64,
   2**-40, 2**40, x10, x3.7, x0.1 and x1.0000001 are all bit-identical, at
   three lengths and three price levels.
7. **The iid centre is NOT the middle of the range**: on 400 independent
   normal windows the median is 0.571429 and the commonest value is the top
   candidate 0.619048 (147 of 400).
8. The five wiring touch points, the dictionary row, and the receipt's own
   claims about what is owed.
9. **Gate E is PENDING**, run by issue-solver after the porting session.
   `test_the_gate_e_row_is_owed` asserts there is no ledger row yet, which
   is the receipt session's cue to record one.

Run `python docs/measure_c22_dfa.py` to regenerate every table, and
`python docs/measure_c22_dfa_cpu.py` to re-run this module with AVX-512,
AVX2 and FMA3 dispatch disabled.
"""
import importlib
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

import pandas_ta
import pandas_ta.core  # noqa: F401
from pandas_ta.statistics.c22_dfa import (
    CHUNK_VALUES, LAG, MIN_LENGTH, MIN_POINTS, NOISE_FLOOR, N_TAU_STEPS,
    POLY_ORDER, Q, SCALE_SHARE, TAU_MIN, ZSCORE_DDOF, _prop_rows, c22_dfa,
    min_each_side, prop_bounds, scales)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_dfa")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
N = 1500
#: Significant digits `value_exact` runs its logarithms and straight-line
#: fits at. Pinned equal to the harness's `ORACLE_PREC` by
#: `test_the_measure_script_carries_the_same_mutants`, so the two exact
#: oracles cannot drift in precision.
ORACLE_PREC = 60
NTT = int(scales(LENGTH).size)                       # 21
VALUES = tuple(i / NTT
               for i in range(min_each_side(NTT), NTT - min_each_side(NTT) + 1))


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=55, sigma=0.015, level=2.0):
    return Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=N, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=N, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


def student_t(n=N, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def ladder(n=N, step=0.01, start=100.0):
    """An exactly geometric path: constant returns up to rounding."""
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def kurus_path(n=N, start=100.0, step=0.01):
    """A price rising by exactly one kurus a bar."""
    return Series(start + step * np.arange(n, dtype=float))


def zero_then_up(n=N, at=750, step=0.01):
    """Returns exactly 0 and then exactly +step: the construction that
    reaches an exactly zero fluctuation at a scale (receipt §G3c)."""
    return Series(100.0 * np.cumprod(
        1.0 + np.where(np.arange(n) < at, 0.0, step)))


def ulp_frame(n=N, level=1e6, at=700):
    c = np.full(n, level)
    c[at:] = np.nextafter(level, 2 * level)
    return Series(c)


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
STOCHASTIC = ["walk", "tick-rounded", "penny", "ar1", "student-t"]
_BASE: dict[str, Series] = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_dfa(FRAMES[name])
    return _BASE[name]


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


def diff_bars(a, b, tol=0.0):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(np.abs(x[both] - y[both]) > tol)),
            int(np.sum(np.isnan(x) != np.isnan(y))))


def shipped_on(window):
    w = np.asarray(window, float)
    return float(_prop_rows(w.reshape(1, -1))[0])


# ------------------------------------------- the definition, by hand
def _fit_resid(xs, ys):
    n = len(xs)
    xm = math.fsum(xs) / n
    ym = math.fsum(ys) / n
    sxy = math.fsum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    sxx = math.fsum((x - xm) ** 2 for x in xs)
    b = sxy / sxx
    return [(y - ym) - b * (x - xm) for x, y in zip(xs, ys)]


def fluctuations(window, lag=LAG, decimate="first", cumsum="after",
                 zscore=True, ddof=ZSCORE_DDOF, detrend=POLY_ORDER, q=Q,
                 pool="all", divisor="tau", remainder="tail", taus=None,
                 top="half-decimated", rounding="half-up"):
    """`F(tau)` for every scale, from the definition, in plain Python. One
    knob per reading `docs/measure_c22_dfa.py` section A5 prices; the
    defaults are the shipped ones."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return None
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > 0.0):
        return None
    z = [(v - mean) / sd for v in w] if zscore else list(w)

    def cut(seq):
        if decimate == "first":
            return seq[::lag]
        if decimate == "last":
            return seq[lag - 1::lag]
        return list(seq)

    def running(seq):
        out, acc = [], 0.0
        for v in seq:
            acc += v
            out.append(acc)
        return out

    profile = cut(running(z)) if cumsum == "before" else running(cut(z))
    points = len(profile)
    if taus is None:
        pts = -(-n // lag) if decimate != "none" else n
        hi = (pts if top == "half-decimated" else n) // 2
        taus = []
        for i in range(N_TAU_STEPS):
            x = math.exp(math.log(float(TAU_MIN))
                         + i * (math.log(float(hi)) - math.log(float(TAU_MIN)))
                         / (N_TAU_STEPS - 1))
            if rounding == "half-up":
                v = int(math.floor(x + 0.5))
            elif rounding == "ceil":
                v = int(math.ceil(x))
            else:
                v = int(math.floor(x))
            if v not in taus:
                taus.append(v)
        taus.sort()
    out = []
    for tau in taus:
        boxes = points // tau
        if boxes < 1:
            return None
        xs = list(range(tau))
        skip = 0 if remainder == "tail" else points - boxes * tau
        res = []
        for b in range(boxes):
            seg = profile[skip + b * tau:skip + (b + 1) * tau]
            if detrend == 1:
                res.append(_fit_resid(xs, seg))
            else:
                coef = np.polyfit(np.asarray(xs, float),
                                  np.asarray(seg, float), detrend)
                fit = np.polyval(coef, np.asarray(xs, float))
                res.append([float(a - b2) for a, b2 in zip(seg, fit)])
        if pool == "all":
            flat = [abs(v) ** q for seg in res for v in seg]
            denom = {"tau": boxes * tau, "tau-2": boxes * (tau - 2)}[divisor]
            f = (math.fsum(flat) / denom) ** (1.0 / q)
        else:
            per = [(math.fsum(abs(v) ** q for v in seg) / tau) ** (1.0 / q)
                   for seg in res]
            f = (math.fsum(v ** q for v in per) / len(per)) ** (1.0 / q)
        out.append((tau, f))
    return out


def break_of(curve, min_points=None, score="ss", share=True,
             prop="break/ntt"):
    """The two-piece break of a `[(tau, F)]` curve, with the knobs section A5
    prices. `ss` and `share=True` are the shipped readings."""
    if curve is None:
        return None
    ntt = len(curve)
    if any(not (f > 0.0) or not math.isfinite(f) for _, f in curve):
        return None
    lt = [math.log(float(tau)) for tau, _ in curve]
    lf = [math.log(f) for _, f in curve]
    mp = min_each_side(ntt) if min_points is None else min_points
    cands = list(range(mp, ntt - mp + 1))
    if not cands:
        return None
    best, best_i = None, None
    for i in cands:
        r1 = _fit_resid(lt[:i], lf[:i])
        r2 = _fit_resid(lt[i - 1:], lf[i - 1:]) if share \
            else _fit_resid(lt[i:], lf[i:])
        if score == "ss":
            s = math.fsum(v * v for v in r1) + math.fsum(v * v for v in r2)
        elif score == "norm":
            s = math.sqrt(math.fsum(v * v for v in r1)) \
                + math.sqrt(math.fsum(v * v for v in r2))
        else:
            s = math.sqrt(math.fsum(v * v for v in r1)) / len(r1) \
                + math.sqrt(math.fsum(v * v for v in r2)) / len(r2)
        if best is None or s < best:
            best, best_i = s, i
    if prop == "break/ntt":
        return best_i / ntt
    if prop == "(break-1)/ntt":
        return (best_i - 1) / ntt
    return best_i / (ntt - 1)


def value_def(window, min_points=None, score="ss", share=True,
              prop="break/ntt", **fluct_kw):
    got = break_of(fluctuations(window, **fluct_kw), min_points=min_points,
                   score=score, share=share, prop=prop)
    return float("nan") if got is None else got


def value_exact(window):
    """`(break, ntt, margin)` with the profile and every residual EXACT.

    The output is an INTEGER choice, so an oracle only has to get that
    integer right. The feature is invariant under `a * r + b` for any
    `a != 0` -- `b` is a straight line in the profile and every box's detrend
    removes it, `a` scales every residual alike and shifts `log F` by a
    constant -- so the oracle may work on the RAW window, where the profile,
    the per-box least-squares residuals and `F(tau)**2` are all exact
    `Fraction`s. Only the logarithms and the two straight-line fits are
    inexact, and `margin` says how far the winner is from the runner-up.
    """
    w = [Fraction(float(v)) for v in window]
    n = len(w)
    profile, acc = [], Fraction(0)
    for v in w[::LAG]:
        acc += v
        profile.append(acc)
    points = len(profile)
    taus = [int(t) for t in scales(n)]
    f2 = []
    for tau in taus:
        boxes = points // tau
        xs = [Fraction(i) for i in range(tau)]
        xm = sum(xs) / tau
        sxx = sum((x - xm) ** 2 for x in xs)
        tot = Fraction(0)
        for b in range(boxes):
            seg = profile[b * tau:(b + 1) * tau]
            ym = sum(seg) / tau
            slope = sum((x - xm) * (v - ym) for x, v in zip(xs, seg)) / sxx
            tot += sum(((v - ym) - slope * (x - xm)) ** 2
                       for x, v in zip(xs, seg))
        f2.append(tot / (boxes * tau))
    if any(v <= 0 for v in f2):
        return None
    ntt = len(taus)

    def ss(xs, ys):
        m = len(xs)
        xm = sum(xs) / m
        ym = sum(ys) / m
        b = sum((x - xm) * (v - ym) for x, v in zip(xs, ys)) \
            / sum((x - xm) ** 2 for x in xs)
        return sum(((v - ym) - b * (x - xm)) ** 2 for x, v in zip(xs, ys))

    # `localcontext` and not `getcontext().prec = ...`: the decimal context
    # is process-global, and an oracle has no business leaving 60 digits
    # behind for whatever runs next (the house spelling --
    # `tests/test_ts_cross_mean_20.py::_exact_windowed`).
    with localcontext() as ctx:
        ctx.prec = ORACLE_PREC
        lt = [Decimal(t).ln() for t in taus]
        lf = [(Decimal(v.numerator) / Decimal(v.denominator)).ln() / Decimal(2)
              for v in f2]
        a = min_each_side(ntt)
        scores = [(ss(lt[:i], lf[:i]) + ss(lt[i - 1:], lf[i - 1:]), i)
                  for i in range(a, ntt - a + 1)]
        best = min(scores)
        rest = min(s for s, i in scores if i != best[1])
        return best[1], ntt, float((rest - best[0]) / best[0])


# ------------------------------------------------------------- Gate A
def test_the_ladder_is_a_function_of_the_length_alone():
    """No data enters the scale ladder, so the whole thing is a constant per
    `length`. Measured: 21 scales, the integers 5 .. 25, at the default."""
    assert list(scales(LENGTH)) == list(range(5, 26))
    assert NTT == 21
    assert list(scales(83)) == list(range(5, 22))
    assert scales(67).size == 13
    assert scales(250).size == 38
    assert list(scales(LENGTH)) == list(scales(LENGTH))


def test_the_ladder_does_not_depend_on_the_rounding_convention():
    """`floor(x + 0.5)` is MATLAB's and C's `round`; numpy's goes to the
    nearest EVEN integer. They agree here because no step of the default
    ladder lands closer than 0.0026 to a half (receipt §A3) -- which is
    measured, not assumed, and would change if the ladder did."""
    points = -(-LENGTH // LAG)
    hi = points // 2
    worst = min(
        abs(x - math.floor(x) - 0.5)
        for x in np.exp(np.linspace(math.log(TAU_MIN), math.log(hi),
                                    N_TAU_STEPS)))
    assert worst > 1e-3, worst
    steps = np.exp(np.linspace(math.log(TAU_MIN), math.log(hi), N_TAU_STEPS))
    assert list(np.unique(np.round(steps).astype(int))) == list(scales(LENGTH))


@pytest.mark.parametrize("length,ntt,values", [(83, 17, 2), (100, 21, 6),
                                               (120, 26, 11), (250, 38, 19)])
def test_the_value_set_is_derived_and_small(length, ntt, values):
    """The column is `break / scales` over the splits that leave
    `max(8, round(scales/4))` scales each side, so the value SET is derived.
    Measured at four lengths: 2, 6, 11 and 19 possible values."""
    assert int(scales(length).size) == ntt
    a = min_each_side(ntt)
    assert ntt - 2 * a + 1 == values
    lo, hi = prop_bounds(length)
    assert (lo, hi) == (a / ntt, (ntt - a) / ntt)
    got = set(c22_dfa(FRAMES["walk"], length=length).dropna().to_numpy())
    assert got <= {i / ntt for i in range(a, ntt - a + 1)}
    assert all(lo - 1e-15 <= v <= hi + 1e-15 for v in got)


def test_the_search_range_rule_is_the_one_the_reference_pins():
    """`max(MIN_POINTS, round(scales / SCALE_SHARE))`, which is 8 up to 33
    scales and a quarter of the ladder above that. It reproduces the
    reference's own search range on 32 of 32 ladder sizes and predicts it
    window by window on 3,084 of 3,084 (receipt §Q6, §Q7), where a flat
    floor of 8 fits 18 of 32 ladder sizes and `ceil` 28 of 32."""
    assert (MIN_POINTS, SCALE_SHARE) == (8, 4)
    assert [min_each_side(k) for k in (16, 21, 26, 31, 33)] == [8] * 5
    assert [min_each_side(k) for k in (34, 37, 38, 41, 42, 46, 47)] == \
        [9, 9, 10, 10, 11, 12, 12]
    for k in range(16, 48):
        assert min_each_side(k) == max(8, int(math.floor(k / 4 + 0.5))), k


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_definition_spelled_in_plain_python_agrees(frame):
    """Gate A's first independent limb: the definition re-spelled with
    `math.fsum` and no numpy vectorisation. Measured bit-equal on 200
    windows of each of six frames, max gap 0.0."""
    win, bars = windows(FRAMES[frame])
    ran = 0
    for i in range(0, win.shape[0], 11):
        mine = shipped_on(win[i])
        theirs = value_def(win[i])
        assert mine == theirs, (frame, int(bars[i]), mine, theirs)
        ran += 1
    assert ran >= 120, ran


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_exact_oracle_picks_the_same_break_and_is_not_close(frame):
    """Gate A's strongest limb. The profile, every per-box residual and
    `F(tau)**2` are exact rationals; only the logarithms and the two
    straight-line fits round, in 60 digits. Measured: 90 of 90 sampled
    windows across six frames agree on the break, and the runner-up split
    is at least 3.598e-04 away in relative score -- the slack a reassociated
    numpy reduction would have to close to change an output."""
    win, bars = windows(FRAMES[frame])
    ran = 0
    worst = 1.0
    for i in range(0, win.shape[0], 97):
        got = value_exact(win[i])
        assert got is not None, (frame, int(bars[i]))
        brk, ntt, margin = got
        assert abs(shipped_on(win[i]) - brk / ntt) < 1e-15, \
            (frame, int(bars[i]))
        worst = min(worst, margin)
        ran += 1
    assert ran >= 14, ran
    assert worst > 1e-5, (frame, worst)


@pytest.mark.parametrize("knob,moved", [
    (dict(score="norm"), 100),
    (dict(share=False), 167),
    (dict(min_points=6), 181),
    (dict(min_points=7), 147),
    (dict(min_points=9), 211),
    (dict(decimate="last"), 233),
    (dict(decimate="none"), 358),
    (dict(cumsum="before"), 194),
    (dict(top="half-raw"), 358),
    (dict(rounding="floor"), 221),
    (dict(remainder="head"), 247),
    (dict(divisor="tau-2"), 51),
    (dict(q=1), 95),
    (dict(detrend=2), 259),
    (dict(prop="(break-1)/ntt"), 366),
    (dict(prop="break/(ntt-1)"), 366),
])
def test_every_load_bearing_reading_moves_the_column(knob, moved):
    """Each of these is a defensible reading of the definition that the
    reference's output rules out, and each one CHANGES values -- so none of
    them is a matter of taste. The counts are windows that move, out of 366
    sampled over six frames; they are asserted as a band (half the measured
    count, and never zero) rather than exactly, because what matters is that
    the knob is load-bearing."""
    win_sets = [windows(FRAMES[k])[0] for k in FRAMES]
    seen = hit = 0
    for win in win_sets:
        for i in range(0, win.shape[0], 23):
            mine = shipped_on(win[i])
            theirs = value_def(win[i], **knob)
            if math.isnan(mine):
                continue
            seen += 1
            hit += int(math.isnan(theirs) or mine != theirs)
    assert seen == 366, seen
    assert hit >= max(1, moved // 2), (knob, hit, moved)


@pytest.mark.parametrize("knob", [dict(ddof=0), dict(zscore=False),
                                  dict(pool="perbox"), dict(rounding="ceil")])
def test_the_inert_knobs_are_inert_and_the_reason_is_structural(knob):
    """Four knobs a reader might expect to matter do not, and three of them
    for one reason: the feature is invariant under `a * r + b` for any
    `a != 0`, so the z-score and its divisor cannot move it; for `q = 2` with
    equal box lengths, pooling every residual and averaging the per-box means
    are the same number; and rounding the ladder UP instead of half-away-from
    -zero happens to produce the same 21 integers (which `floor` does NOT --
    that moves 221 of 366, and it is in the load-bearing table above).
    Measured: 0 of 366 windows move for each."""
    moved = seen = 0
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        for i in range(0, win.shape[0], 23):
            mine = shipped_on(win[i])
            if math.isnan(mine):
                continue
            seen += 1
            moved += int(mine != value_def(win[i], **knob))
    assert seen == 366, seen
    assert moved == 0, (knob, moved)


def test_the_fixed_parameters_are_the_features_own():
    """`POLY_ORDER` and `Q` are named constants that the kernel SPELLS OUT
    rather than reads -- one slope and one intercept, and the mean of the
    squared residuals -- because the feature fixes both. They are pinned here
    so a reader cannot change the constant and believe the column followed:
    the harness and the tests above take them as knobs and price order 2 at
    259 of 366 moved windows and `q = 1` at 95."""
    assert (POLY_ORDER, Q) == (1, 2)
    assert (LAG, N_TAU_STEPS, TAU_MIN) == (2, 50, 5)
    assert (MIN_POINTS, SCALE_SHARE, ZSCORE_DDOF) == (8, 4, 1)
    assert NOISE_FLOOR == 4096 * np.finfo(float).eps


def test_the_module_docstring_attributes_the_source():
    doc = c22_dfa.__doc__
    for needle in ("Lubba", "33:1821", "SC_FluctAnal", "GPL-3.0", "#128",
                   "pycatch22"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The reference (pycatch22) is GPL-3.0 and this fork is MIT. The claim
    that has to hold is about the shipped CODE PATH, so this sweeps every
    `.py` file under `pandas_ta/` for an import of it. ⚠ pycatch22 IS
    installed in this worktree, so the guard is not vacuous."""
    hits = []
    files = sorted((ROOT / "pandas_ta").rglob("*.py"))
    for p in files:
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if (s.startswith("import ") or s.startswith("from ")) \
                    and "catch22" in s.replace("c22", ""):
                hits.append((str(p.relative_to(ROOT)), s))
    assert hits == [], hits
    assert len(files) > 300, len(files)


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": ("out[length + a:length + b]",
                         "out[length - 1 + a:length - 1 + b]"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-two-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 2)[:, 2:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
    "chunk-wide-demean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))"),
    "profile-across-rows": (
        "        profile = np.cumsum(y, axis=1)",
        "        profile = np.cumsum(y.ravel()).reshape(y.shape)"),
    "end-aligned-decimation": ("        y = z[:, ::LAG]",
                               "        y = z[:, LAG - 1::LAG]"),
    "norms-not-squares": ("    return (resid * resid).sum(axis=1)",
                          "    return np.sqrt((resid * resid).sum(axis=1))"),
    "no-overflow-guard": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                          "bad |= ~(sd > NOISE_FLOOR)"),
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
    "no-zero-fluctuation-guard": (
        "        bad |= ~(f2 > 0.0).all(axis=1) | ~np.isfinite(f2).all(axis=1)",
        "        bad |= ~np.isfinite(f2).all(axis=1)"),
    "no-either-guard": (
        ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
         "bad |= ~(sd > NOISE_FLOOR)"),
        ("        bad |= ~(f2 > 0.0).all(axis=1) | ~np.isfinite(f2).all(axis=1)",
         "        bad |= np.zeros(rows, dtype=bool)"),
    ),
}
#: The mutants that look like look-aheads and are NOT, because the
#: decimation drops the window's newest return.
CAUSAL_BUT_WRONG = ("write-back-dated", "window-one-ahead", "returns-rolled",
                    "end-aligned-decimation")


def mutant(name):
    """Read this module off disk, edit one write, exec it in memory."""
    edits = MUTANTS[name]
    if isinstance(edits[0], str):
        edits = (edits,)
    src = SRC
    for old, new in edits:
        assert src.count(old) == 1, (name, old, src.count(old))
        src = src.replace(old, new)
    ns = {}
    exec(compile(src, f"<mutant {name}>", "exec"), ns)
    return ns["c22_dfa"]


def test_the_measure_script_carries_the_same_mutants():
    """The receipt's §B2 quotes a run of the harness's own mutant table, so
    the two tables have to be the SAME table -- not merely the same names.
    The harness is imported by path and the dicts are compared whole, so an
    edit string that drifts on one side fails here instead of shipping two
    different Gate Bs that both report green."""
    import importlib.util
    path = ROOT / "docs" / "measure_c22_dfa.py"
    spec = importlib.util.spec_from_file_location("_m_c22dfa", path)
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    assert harness.MUTANTS == MUTANTS
    assert len(MUTANTS) == 15, len(MUTANTS)
    # The two exact oracles must round at the same precision for §A6's
    # margins to be the same measurement. Both sides are NAMED constants and
    # both are compared here, so changing either one alone fails.
    assert harness.ORACLE_PREC == ORACLE_PREC, (harness.ORACLE_PREC,
                                                ORACLE_PREC)
    assert ORACLE_PREC == 60, ORACLE_PREC


def _spliced(close, j, seed=909, vol=0.02, jump=1.0):
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * jump * np.cumprod(
        1.0 + rng.normal(0.0005, vol, c.size - j))
    return Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=35):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=8, vol=0.02, jump=1.0):
    bad = np.asarray(fn(close), float)
    hits = []
    for j in offsets:
        for s in range(splices):
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s,
                                           vol=vol, jump=jump)), float)
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
    assert _leaks(c22_dfa, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_violent_splice_cannot_make_it_leak_either(frame):
    """The same sweep with the instrument turned up: 20% daily volatility and
    a 3x jump at the cut, which scrambles the whole fluctuation curve after
    J instead of nudging it. The real module leaks on 0 of 35 offsets on
    every frame; the one-bar look-ahead mutant is caught on 28 of 35 by this
    instrument and only 5 of 35 by the gentle one."""
    f = FRAMES[frame]
    assert _leaks(c22_dfa, f, _offsets(len(f)), splices=4, vol=0.2,
                  jump=3.0) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_dfa(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


def test_the_dependency_map_is_the_hundred_closes_before_the_bar():
    """The sharpest causality instrument here, because it does not depend on
    the sweep's power: perturb EVERY close of the frame on its own and record
    which closes move bar T. Measured at T = 300, 700 and 1,100 with a x1.5
    perturbation: 55, 92 and 90 closes move the bar, every one of them in
    `[T-100, T-1]`, and 0 at or after T. The count is below 100 because this
    column takes six values and a tie absorbs the rest."""
    f = FRAMES["walk"]
    want = np.asarray(base("walk"), float)
    for T in (300, 700, 1100):
        movers = []
        for j in range(T - 140, min(len(f), T + 120)):
            g = f.to_numpy(dtype=float).copy()
            g[j] *= 1.5
            got = np.asarray(c22_dfa(Series(g, index=f.index)), float)
            if got[T] != want[T] or np.isnan(got[T]) != np.isnan(want[T]):
                movers.append(j)
        assert movers, T
        assert min(movers) >= T - LENGTH, (T, min(movers))
        assert max(movers) <= T - 1, (T, max(movers))
        assert len(movers) >= 30, (T, len(movers))


def test_the_value_at_bar_T_does_not_read_close_T_but_the_mask_does():
    """The lag drops the window's newest return, so the VALUE at bar T is a
    function of closes T-100 .. T-1 and is one bar STALE. Measured:
    perturbing close[T] by a finite factor moves bar T on 0 of 4 sampled
    bars and bar T+1 on 3 of them (the fourth is a tie).

    ⚠ The NaN MASK is the exception, and it is still causal: the finiteness
    check and the noise floor run on the WHOLE undecimated window, so a
    close at T that is NaN or zero blanks bar T -- 4 of 4. That is why a
    single bad close blanks 101 bars starting AT its own bar and not 100
    starting after it, and it is the half a consumer who truncates at T-1
    would notice. Both halves are disclosures, not defects, and the
    docstring carries both."""
    f = FRAMES["walk"]
    want = np.asarray(base("walk"), float)
    moved_T = moved_next = 0
    for T in (200, 500, 900, 1300):
        g = f.to_numpy(dtype=float).copy()
        g[T] *= 1.5
        got = np.asarray(c22_dfa(Series(g, index=f.index)), float)
        moved_T += int(got[T] != want[T])
        moved_next += int(got[T + 1] != want[T + 1])
    assert moved_T == 0, moved_T
    assert moved_next >= 2, moved_next
    for bad in (np.nan, 0.0):
        blanked = 0
        for T in (200, 500, 900, 1300):
            g = f.to_numpy(dtype=float).copy()
            g[T] = bad
            got = np.asarray(c22_dfa(Series(g, index=f.index)), float)
            blanked += int(np.isnan(got[T]) and not np.isnan(want[T]))
        assert blanked == 4, (bad, blanked)
    assert "does not read close[T]" in c22_dfa.__doc__
    assert "MASK" in c22_dfa.__doc__


@pytest.mark.parametrize("name", ["window-two-ahead", "window-ten-ahead"])
def test_the_true_look_ahead_mutants_are_caught(name):
    """These two DO read a future close -- a window shifted two bars ends on
    the return of bar T+1, which the decimation keeps -- and the sweep
    catches them. Measured on the walk frame with the violent splice: 28 of
    35 offsets for the two-bar shift and 35 of 35 for the ten-bar one. The
    bound is 10 rather than 28 because the catch rate is a property of where
    the splices land."""
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=4, vol=0.2,
                  jump=3.0)
    assert len(hits) >= 10, (name, len(hits))


@pytest.mark.parametrize("name", CAUSAL_BUT_WRONG)
def test_four_one_bar_mutants_are_wrong_but_still_causal(name):
    """⚠ The finding that shapes Gate B for this column. Back-dating the
    write, shifting the window one bar ahead, rolling the returns and
    decimating from the newest end all CHANGE the column -- 1,098 to 1,099
    of the walk frame's 1,400 fired bars -- and none of them is a
    look-ahead, because a window shifted one bar forward still ends on the
    return the decimation throws away. So the sweep reports 0 of 35 leaks
    for each, and that is the right answer rather than a blind spot: the
    value-move count proves the edit landed, and the two-bar shift above
    proves the sweep can see a real one."""
    fn = mutant(name)
    got = fn(FRAMES["walk"])
    moved, _ = diff_bars(base("walk"), got)
    assert moved >= 500, (name, moved)
    assert _leaks(fn, FRAMES["walk"], _offsets(1500), splices=4, vol=0.2,
                  jump=3.0) == [], name


def test_the_norms_mutant_changes_values_without_leaking():
    """The fourth value mutant, so that every one of the fifteen has a test
    of its own. Scoring the two residual NORMS instead of their sums of
    squares is the reading this port first got wrong: it moves 391 of the
    walk frame's 1,400 fired bars by up to 0.2381, and it leaks on 0 of the
    12 offsets swept HERE (and 0 of 35 in the harness's §B2 sweep, which is
    where that figure is measured) -- it is a WRONG column, not a non-causal
    one, which is why Gate A pins it
    (`test_every_load_bearing_reading_moves_the_column`) and Gate B does
    not."""
    got = mutant("norms-not-squares")(FRAMES["walk"])
    moved, mask = diff_bars(base("walk"), got)
    assert moved >= 200, moved
    assert mask == 0, mask
    assert _leaks(mutant("norms-not-squares"), FRAMES["walk"],
                  _offsets(1500, count=12), splices=4) == []


@pytest.mark.parametrize("name", ["chunk-wide-demean", "chunk-wide-sd",
                                  "profile-across-rows"])
@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "penny"])
def test_three_cross_row_mutants_are_dead_by_affine_invariance(name, frame):
    """All three ARE reads of other rows, so a sweep should see them, and it
    cannot: they are bit-equal to the real module on all 1,500 bars of three
    frames. The reason is measured rather than excused -- the feature is
    invariant under `a * r + b` for any `a != 0`, and a cross-row cumulative
    sum adds a CONSTANT to a row's profile, which every box's own detrend
    removes. They are counted among the fifteen mutants rather than quietly
    dropped."""
    assert same(base(frame), mutant(name)(FRAMES[frame])), (name, frame)


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    """This mutant back-dates the bad-data MASK instead of a value, so a
    clean frame cannot see it: bit-equal on all 1,500 bars of the walk. On a
    frame with one bad close it moves exactly bar J-1, caught 12 of 12."""
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_dfa(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_dfa(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_tie_share_is_the_ceiling_on_what_a_sweep_can_see(frame):
    """Why the mutant catch rates above are what they are, and why the
    violent splice exists. This column takes six values at the default
    `length`, so neighbouring bars carry the same one on 20.3% to 35.3% of
    pairs over five stochastic frames -- and on 100% of the 20-bar cosine
    frame, which reads 0.380952 on every one of its 1,400 fired bars."""
    a = base(frame).dropna().to_numpy()
    tie = float(np.mean(a[1:] == a[:-1]))
    if frame == "cosine":
        assert tie == 1.0 and len(set(a.tolist())) == 1
        return
    assert 0.10 < tie < 0.60, (frame, tie)
    assert len(set(a.tolist())) == len(VALUES), frame


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    """1,400 of 1,500 on every frame, and the first fired bar is `length`:
    the window ending at bar T holds the returns of bars T-99 .. T, which
    read closes T-100 .. T -- of which the decimation then uses T-100 ..
    T-1."""
    s = base(frame)
    assert int(s.notna().sum()) == N - LENGTH, frame
    assert int(np.argmax(s.notna().to_numpy())) == LENGTH, frame
    assert bool(s.iloc[:LENGTH].isna().all()), frame


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_a_stochastic_frame_reaches_every_value_the_column_has(frame):
    """All six values are reachable, measured on five frames, and the
    histogram leans to the TOP candidate: 0.619048 takes 458 to 553 of the
    1,400 fired bars."""
    a = base(frame).dropna().to_numpy()
    assert set(np.round(a, 12)) == set(np.round(VALUES, 12)), frame
    top = float(np.mean(a == VALUES[-1]))
    assert 0.25 < top < 0.50, (frame, top)


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own warning, checked: a 2-lira stock on a 1-kurus tick
    prints 14.01% of its returns as exactly zero and the column still fires
    on all 1,400 bars, takes all six values, and reads the same median
    (0.571429) as the continuous walk."""
    r = returns(FRAMES["penny"])
    assert float(np.mean(r == 0.0)) > 0.10
    s = base("penny")
    assert int(s.notna().sum()) == N - LENGTH
    assert set(np.round(s.dropna().to_numpy(), 12)) == set(np.round(VALUES, 12))
    assert s.dropna().median() == base("walk").dropna().median()


def test_the_iid_centre_is_not_the_middle_of_the_range():
    """On 400 INDEPENDENT windows of normal returns the median is 0.571429
    and the commonest value is the TOP candidate 0.619048 (147 of 400) --
    an iid fluctuation curve is nearly one straight line, and a two-piece
    fit of one puts its break wherever the residuals are smallest. The
    docstring says so; this pins that it is still true."""
    rng = np.random.default_rng(4242)
    vals = _prop_rows(rng.normal(0.0, 0.01, (400, LENGTH)))
    a = vals[~np.isnan(vals)]
    assert len(a) == 400
    assert float(np.median(a)) > 0.5
    counts = {v: int(np.sum(a == v)) for v in VALUES}
    assert max(counts, key=counts.get) == VALUES[-1], counts
    assert "not the middle of the range" in c22_dfa.__doc__


@pytest.mark.parametrize("length,lo,hi", [(100, 0.50, 0.65),
                                          (250, 0.55, 0.70)])
def test_the_centre_moves_with_the_length(length, lo, hi):
    """The value set is a function of `length` and so is the centre: the
    same 400-window measurement reads a median of 0.571429 at 100 and
    0.605263 at 250. Pinned as bands, because the digits are a property of
    the sample -- but bands that EXCLUDE 3 of the 6 values at 100 and most
    of the 19 at 250, so they can fail. `MIN_LENGTH` is handled by name
    below: a band there could not fail at all, since the column has only two
    values."""
    rng = np.random.default_rng(4242)
    vals = _prop_rows(rng.normal(0.0, 0.01, (400, length)))
    a = vals[~np.isnan(vals)]
    assert lo <= float(np.median(a)) <= hi, (length, float(np.median(a)))


def test_the_centre_at_the_length_floor_is_the_upper_of_its_two_values():
    """At `MIN_LENGTH` the column takes exactly 8/17 and 9/17, so a BAND
    would span its whole range and could never fail -- the vacuous-assertion
    trap. The measured fact is sharper than a band anyway: of 400
    independent normal windows, 215 read 9/17 and 185 read 8/17, so the
    median is 9/17 = 0.529412 and the upper candidate is the commoner
    one."""
    rng = np.random.default_rng(4242)
    vals = _prop_rows(rng.normal(0.0, 0.01, (400, MIN_LENGTH)))
    a = vals[~np.isnan(vals)]
    assert len(a) == 400
    assert set(np.round(a, 12)) <= {round(8 / 17, 12), round(9 / 17, 12)}
    assert float(np.median(a)) == 9 / 17, float(np.median(a))
    assert float(np.mean(a == 9 / 17)) > 0.5


def test_an_ar1_in_returns_does_not_read_like_the_cosine():
    """What the column can and cannot separate, measured rather than hoped:
    a 20-bar cosine in the returns reads one value (0.380952) on all 1,400
    bars while an AR(1) with phi = +0.6 spreads over all six with a median
    of 0.523810. ⚠ It does NOT separate phi = +0.6 from phi = -0.6: both
    read a median of 0.523810, which is in the receipt as a limitation."""
    cos = base("cosine").dropna().to_numpy()
    assert len(set(cos.tolist())) == 1 and cos[0] == VALUES[0]
    a = base("ar1").dropna().to_numpy()
    assert len(set(a.tolist())) == len(VALUES)
    assert float(np.median(a)) == VALUES[3]


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_exact_binary_rescale_is_bit_identical(frame, factor):
    """By construction: the price enters only as `c[t] / c[t-1]`, and
    `8a / 8b` is the double `a / b`."""
    assert same(base(frame), c22_dfa(FRAMES[frame] * factor))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_an_inexact_rescale_is_bit_identical_too(factor):
    """Not luck: the output is an INTEGER choice whose runner-up is at least
    3.598e-04 away in relative score, so a perturbation that does not close
    that gap cannot move it at all. Measured: 0 moved bars and 0 mask
    differences at each factor."""
    assert diff_bars(base("walk"), c22_dfa(FRAMES["walk"] * factor)) == (0, 0)


@pytest.mark.parametrize("level", [1e-6, 1e6, 1e100])
def test_the_scale_invariance_holds_at_every_price_level(level):
    f = FRAMES["walk"] / float(FRAMES["walk"].iloc[0]) * level
    assert diff_bars(base("walk"), c22_dfa(f)) == (0, 0)


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_scale_invariance_holds_at_non_default_lengths(length):
    assert same(c22_dfa(FRAMES["walk"], length=length),
                c22_dfa(FRAMES["walk"] * 8.0, length=length))


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_it_fires_strictly_between_zero_and_n_and_is_not_constant(frame):
    """Gate D's `0 < fires < n`, plus the limb that stops a constant column
    passing it: 1,400 of 1,500 fire and all six values appear."""
    s = base(frame)
    fired = int(s.notna().sum())
    assert 0 < fired < len(s), frame
    assert len(set(s.dropna().to_numpy().tolist())) == len(VALUES), frame


@pytest.mark.parametrize("fn,label", [
    (lambda w: 0.5 * w, "returns x0.5"),
    (lambda w: 2.0 * w, "returns x2"),
    (lambda w: 10.0 * w, "returns x10"),
    (lambda w: -1.0 * w, "returns x-1"),
    (lambda w: w + 0.001, "+0.001 on every return"),
    (lambda w: w + 1.0, "+1.0 on every return"),
])
def test_it_is_blind_to_any_affine_map_of_the_returns(fn, label):
    """`a * r + b` for any `a != 0` leaves the output alone: `b` is a
    straight LINE in the profile, which every box's detrend removes, and `a`
    scales every residual of every box alike, which shifts `log F` by a
    constant and leaves both straight-line fits' residuals untouched. The
    sign flip is included because the fluctuation is even. Measured: 0 of
    200 windows move for each."""
    win, _ = windows(FRAMES["walk"])
    seen = moved = 0
    for i in range(0, win.shape[0], 7):
        a = shipped_on(win[i])
        b = shipped_on(fn(win[i]))
        if math.isnan(a):
            continue
        seen += 1
        moved += int(a != b)
    assert seen == 200, seen
    assert moved == 0, (label, moved)


def test_it_is_not_blind_to_the_order_of_the_returns():
    """The other half of the previous test: reversing the window moves 155
    of 200 and shuffling moves 144, so the column reads the SHAPE of the
    series and not only its distribution."""
    rng = np.random.default_rng(5)
    win, _ = windows(FRAMES["walk"])
    rev = shuf = seen = 0
    for i in range(0, win.shape[0], 7):
        a = shipped_on(win[i])
        if math.isnan(a):
            continue
        seen += 1
        rev += int(shipped_on(win[i][::-1]) != a)
        shuf += int(shipped_on(rng.permutation(win[i])) != a)
    assert seen == 200
    assert rev >= 80, rev
    assert shuf >= 80, shuf


# ------------------------------------------- degenerate frames and NaN
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why():
    """Constant returns up to rounding: the standard deviation of the
    returns is 1.2e-16, below the 9.09e-13 floor, so nothing fires.
    Unguarded it would fire on all 1,400 bars and read five of the six
    values -- the shape of the rounding of `c / c1 - 1`, which a reader
    could not tell from a price-shaped frame."""
    f = ladder()
    assert int(c22_dfa(f).notna().sum()) == 0
    assert float(np.std(returns(f))) < NOISE_FLOOR
    unguarded = mutant("no-floor")(f)
    assert int(unguarded.notna().sum()) == N - LENGTH
    assert len(set(unguarded.dropna().to_numpy().tolist())) >= 3


def test_a_single_ulp_step_never_fires_and_what_that_buys():
    """A price flat at 1e6 except for ONE 1-ulp step: only the 100 bars
    whose window holds the step have any variation at all, and the floor
    blanks them. Unguarded those exactly 100 bars fire."""
    f = ulp_frame()
    assert int(c22_dfa(f).notna().sum()) == 0
    unguarded = mutant("no-floor")(f)
    assert int(unguarded.notna().sum()) == 100


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_floor_is_inert_on_anything_price_shaped(frame):
    """What the floor costs on real-shaped data: nothing. 0 moved bars and 0
    mask differences against the unguarded spelling on each of six frames."""
    assert diff_bars(base(frame), mutant("no-floor")(FRAMES[frame])) == (0, 0)


def test_a_deterministically_smooth_path_still_fires():
    """⚠ The floor does NOT empty a smooth path, and a companion must not
    assume the catch22 ports blank together: a price rising by exactly one
    kurus a bar has a return standard deviation of 3.8e-06, four million
    times the floor, so it fires on all 1,400 bars -- reading 0.380952,
    constant."""
    f = kurus_path()
    s = c22_dfa(f)
    assert float(np.std(returns(f))) > 1e3 * NOISE_FLOOR
    assert int(s.notna().sum()) == N - LENGTH
    assert set(s.dropna().to_numpy()) == {VALUES[0]}


def test_the_zero_fluctuation_guard_is_reached_on_data_with_variation():
    """The second blanking rule, and it is not decoration. On a frame whose
    returns are exactly 0 and then exactly +1%, bar 754's profile is
    straight inside every box of 17 of its 21 scales, so `F = 0` there and
    there is no `log F` to fit. Measured: the guard blanks exactly that one
    bar, which unguarded reads 0.380952."""
    f = zero_then_up()
    shipped = c22_dfa(f)
    unguarded = mutant("no-zero-fluctuation-guard")(f)
    blanked = np.where(shipped.isna().to_numpy()
                       & unguarded.notna().to_numpy())[0]
    blanked = blanked[blanked >= LENGTH]
    assert list(blanked) == [754], list(blanked)
    assert float(np.asarray(unguarded, float)[754]) == VALUES[0]
    curve = fluctuations(returns(f)[754 - LENGTH:754])
    zeros = [tau for tau, v in curve if not (v > 0.0)]
    assert len(zeros) == 17, zeros


def test_the_zero_fluctuation_guard_is_inert_on_price_shaped_frames():
    """... and it costs nothing there: 0 moved bars and 0 mask differences
    on each of six frames."""
    for frame in FRAMES:
        assert diff_bars(base(frame),
                         mutant("no-zero-fluctuation-guard")(FRAMES[frame])) \
            == (0, 0), frame


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -5.0, 1e-310])
def test_a_bad_close_empties_exactly_its_own_windows(bad):
    """A close that is not a finite, normal, positive float has no return to
    take. Measured: 101 bars blanked, 700 .. 800 -- the windows that read
    it."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = bad
    s = c22_dfa(f)
    blank = np.where(s.isna().to_numpy())[0]
    blank = blank[blank >= LENGTH]
    assert list(blank) == list(range(700, 801)), (bad, blank[:5])


def test_a_close_pair_whose_ratio_overflows_empties_its_windows():
    """1e-300 followed by 1e50: the ratio overflows to an infinite return,
    which is bad data in the same way a NaN close is. 100 bars blank."""
    f = FRAMES["walk"].copy()
    f.iloc[700], f.iloc[701] = 1e-300, 1e50
    s = c22_dfa(f)
    blank = np.where(s.isna().to_numpy())[0]
    blank = blank[blank >= LENGTH]
    assert len(blank) == 100, len(blank)


def test_the_overflow_guard_is_redundant_and_the_measurement_says_so():
    """⚠ The `isfinite(sd)` limb is kept and is NOT load-bearing on its own,
    which is the opposite of what the same limb does in `c22_ami2`. A window
    whose sum of squares overflows z-scores to all zeros, so its profile is
    flat and the zero-fluctuation guard blanks it anyway: of the 100 bars a
    close pair of ratio 1e200 blanks, 0 fire with that limb removed and all
    100 fire -- reading 0.380952 -- with BOTH value guards removed."""
    f = FRAMES["walk"].copy()
    f.iloc[700], f.iloc[701] = 1.0, 1e200
    shipped = c22_dfa(f)
    blank = np.where(shipped.isna().to_numpy())[0]
    blank = blank[blank >= LENGTH]
    assert len(blank) == 100, len(blank)
    one = np.asarray(mutant("no-overflow-guard")(f), float)[blank]
    assert int(np.sum(~np.isnan(one))) == 0
    both = np.asarray(mutant("no-either-guard")(f), float)[blank]
    assert int(np.sum(~np.isnan(both))) == 100
    assert set(both[~np.isnan(both)]) == {VALUES[0]}


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    c = np.r_[walk(400).to_numpy(), np.full(N - 400, 100.0)]
    s = c22_dfa(Series(c))
    assert int(s.notna().sum()) == 399
    assert bool(s.iloc[499:].isna().all())


# -------------------------------------------------- arguments, wiring
@pytest.mark.parametrize("n,fires", [(LENGTH, None), (LENGTH + 1, 1),
                                     (LENGTH + 2, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_dfa(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (2, "C22DFA_100", N - LENGTH),
    (82, "C22DFA_100", N - LENGTH),
    (MIN_LENGTH, f"C22DFA_{MIN_LENGTH}", N - MIN_LENGTH),
    (120, "C22DFA_120", N - 120),
])
def test_the_length_guard_band(length, name, fires):
    """A `length` below `MIN_LENGTH` -- the shortest window whose ladder
    gives the break search more than one candidate -- falls back to the
    default rather than shipping a constant column."""
    s = c22_dfa(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires


def test_min_length_is_the_shortest_length_with_a_choice():
    """83, derived rather than written down: at 80 the ladder has 16 scales
    and the search has exactly one candidate (a constant 0.5), at 82 it
    still does, and at 83 it has two."""
    assert MIN_LENGTH == 83
    assert prop_bounds(80) == (0.5, 0.5)
    assert all(math.isnan(v) for v in prop_bounds(67))
    for length in range(LAG, MIN_LENGTH):
        ntt = int(scales(length).size)
        assert ntt == 0 or ntt - 2 * min_each_side(ntt) + 1 < 2, length


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_dfa(FRAMES["walk"], offset=2)
    assert same(s.iloc[2:].to_numpy(), base("walk").iloc[:-2].to_numpy())
    s = c22_dfa(FRAMES["walk"], fillna=-1)
    assert int(np.sum(s.to_numpy() == -1)) == LENGTH


@pytest.mark.parametrize("budget", [LENGTH, 4 * LENGTH, 999, 10 ** 9])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every chunk is an independent run of rows and nothing crosses one, so
    the budget is invisible. Measured bit-equal at 1, 4, 9 and 10,000,000
    rows per chunk."""
    old = MODULE.CHUNK_VALUES
    MODULE.CHUNK_VALUES = budget
    try:
        got = MODULE.c22_dfa(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = old
    assert same(base("walk"), got), budget


def test_the_five_wiring_touch_points():
    assert hasattr(pandas_ta.statistics, "c22_dfa")
    assert "c22_dfa" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_dfa")
    assert (ROOT / "tests" / "test_c22_dfa.py").exists()
    assert (ROOT / "pandas_ta" / "statistics" / "c22_dfa.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"]})
    acc = df.ta.c22_dfa()
    assert acc.name == "C22DFA_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_dfa(length=250, offset=1)
    assert acc.name == "C22DFA_250"
    assert same(acc, c22_dfa(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    line = [ln for ln in text.splitlines() if ln.startswith("| `c22_dfa`")]
    assert len(line) == 1, line
    assert "C22DFA_100" in line[0]
    assert "SF" in line[0]


# ------------------------------------------------------- the receipt
def _receipt():
    return (ROOT / "docs" / "C22DfaMeasured.md").read_text(encoding="utf-8")


def test_the_receipt_says_gate_e_is_pending():
    """Gate E is run by issue-solver after this session, so the receipt must
    SAY so rather than carry a number nobody measured."""
    text = _receipt()
    assert "Gate E: pending, run by issue-solver after this session" in text


def test_the_gate_e_row_is_owed():
    """... and there is no ledger row yet. This test is the receipt
    session's cue: when the launcher's Gate E run is recorded, it is
    replaced by one that pins the row."""
    text = (ROOT / "docs" / "gate_e_ledger.csv").read_text(encoding="utf-8")
    assert "c22_dfa" not in text


def test_the_receipt_states_the_agreement_with_the_reference():
    """The one claim in the receipt that cannot be re-derived from this
    module, so it has to be written down with its numbers."""
    text = _receipt()
    assert "8,400 of 8,400" in text
    assert "3,084 of 3,084" in text
    assert "GPL-3.0" in text


def test_the_receipt_discloses_the_staleness_and_the_coarseness():
    text = _receipt()
    assert "does not read close[T]" in text
    assert "six values" in text


def test_the_receipt_scopes_its_overlap_figures_to_what_they_are():
    """E1/E2 are synthetic-frame Spearmans against this fork's own columns,
    not Gate E, and the receipt has to say which is which -- #112's
    `tf_dfa_100` shipped AFTER the 2026-10-24 screen, so the screen's own
    fork-overlap stage never saw it."""
    text = _receipt()
    assert "not Gate E" in text
    assert "tf_dfa_100" in text or "TFDFA_100" in text
