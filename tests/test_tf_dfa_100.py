# -*- coding: utf-8 -*-
"""TF-DFA-100: `tf_dfa_100`, the detrended fluctuation analysis exponent of
the last 100 daily returns (PandasTa issue #112, TSFEL's `dfa`,
BSD-3-Clause).

    RET   = close / close[1] - 1
    Y     = CUMSUM(RET[T - 99 .. T] - mean(RET[T - 99 .. T]))
    F(s)  = RMS of Y minus a per-box OLS line, over the 100 // s boxes
    TFDFA = OLS slope of log F(s) on log s, for s in (4, 5, 6, 8, 10)

What this file pins, in order of how much it would hurt to lose:

1. **THE ORDERING THE EXPONENT EXISTS FOR, and the centre it is read
   against.** AR(1) returns with phi = +0.6 must read above a Gaussian
   random walk, which must read above AR(1) with phi = -0.6 (measured
   medians 1.0580 / 0.6444 / 0.2913 on 1,500-bar frames). ⚠ And the
   centre is NOT the textbook 0.5: on this box ladder iid normal
   returns read a mean of 0.6289 over 400 disjoint windows, which
   `test_the_iid_centre_is_not_one_half` asserts as a band, because a
   consumer who reads 0.5 as "uncorrelated" will call half of a
   random walk trending. §A5b shows where the bias comes from -- 0.6292
   from 200,000 independent boxes on this ladder against 0.4997 on a
   ladder of 50 .. 320 -- so it is the ladder, not this port.
   ⚠ Also pinned: the column is NOT bounded. The `jump` frame reads
   -0.2197 .. 2.3288, so a negative exponent is reachable on a frame
   with one large price gap in it.

2. **Gate A, the quantity spelled three ways -- and the ONE place this
   port is not the prototype.** The screen prototype (the expression
   Gate E's 0.0979 was measured on) agrees to **4.441e-16** with an
   identical NaN mask, NOT bit for bit, and the difference is one
   spelling: the final dot product. A mutant of the shipped file with
   the prototype's `@` put back is asserted BIT-equal to the prototype,
   which leaves nothing else between them. The module's own spelling is
   a weighted sum because `@` is not stable under the block's SHAPE,
   and this module chunks -- item 6. Two further oracles, measured on
   200-bar frames because an `O(rows * length)` Python loop is only
   affordable there: a scalar loop over the normal equations with
   `math.fsum` agrees to **2.0e-15** absolute (§A2) and a `np.polyfit`
   form to **3.109e-15** (§A3). Two figures, because they are two
   runs -- and each is the WORSE of two CPU dispatches, which is not
   the same dispatch for both: §A2's 2.0e-15 is the default run
   (1.665e-15 with AVX-512/AVX2/FMA3 off) and §A3's 3.109e-15 is the
   AVX-disabled one (2.887e-15 by default). §F2 of
   `docs/TfDfa100Measured.md` lists every figure that moves.
   ⚠ The source itself is NOT readable here.
   `test_the_source_library_is_not_readable_here` asserts that, so the
   limitation fails loudly if the environment ever changes.

3. **No divergence at the empty windows -- and that is a measurement,
   not an inheritance.** `tf_spec_entropy_64` had to diverge from its
   prototype because the prototype's guard was swallowed downstream.
   Here it is not: a window holding a non-finite return, and one whose
   returns are all EQUAL (a flat price, an exact x2 ramp), are NaN in
   both. Pinned as zero bars on which one reads and the other does not.

4. **Gate B: five mutants, and the one the sweep cannot see.** All five
   are read off disk, edited and `exec`'d in memory. Four -- a leading
   return, an early write index, a window rolled one bar forward, and a
   window CENTRED on the current bar (the `bos` failure mode) -- are
   caught at every swept offset on every frame. The fifth back-dates
   the NaN mask by one bar; prefix truncation and the future sweep are
   both blind to back-dating, so it is pinned directly, by planting one
   NaN close and reading where the gap lands.

5. **Gate D: an exact binary rescale of the PRICE is bit-identical.**
   x8, x64, 2**-40, 2**40 and 2**100 on eight frames at the default
   length, and x8 again at five lengths; an inexact factor only to a
   tolerance. A level SHIFT is asserted to MOVE the column, so no
   bit-identity above can pass by the column being constant, and
   `0 < fires < n` is asserted separately.

6. **The arithmetic does not depend on the BLOCK SHAPE, which is what
   makes the chunk loop safe.** `_dfa_alpha` on one row is asserted
   bit-equal to the same row inside a 300-row block, and the column is
   asserted bit-identical at chunk budgets 1, 64, 999 and 10**9. This
   is the test that would have failed before the dot product was
   respelled: with `@`, a small row count gives a different last bit
   -- one row per chunk on the default dispatch, and 1, 2, 5, 7 and 8
   rows with AVX-512/AVX2/FMA3 off (§Z, §Z2) -- and a bar's value would
   then depend on how many bars came after it. ⚠ That `@` measurement
   is NOT asserted here: it runs through BLAS, so another machine's
   BLAS may not reproduce it, and the two dispatches measured here
   already disagree about WHICH row counts break. What is asserted is
   the shipped spelling's shape-stability, which is plain numpy.

7. **What it reads, and what it throws away.** Blind to the size and
   the sign of the returns (bit-identical at x-1, within 1e-12 at x0.5,
   x2, x2**60) and to a constant drift added to them -- so it is not a
   volatility measure. NOT blind to their order: a permutation, a time
   reversal and a rotation each move it, asserted as a floor, because a
   reader who knows the spectral features may assume otherwise.

8. **Gate E is owed.** `test_the_gate_e_row_is_owed_and_not_yet_recorded`
   asserts `docs/gate_e_ledger.csv` carries no row for this indicator,
   which is the state this commit ships in and the receipt session's
   cue.

Every number above is printed by `python docs/measure_tf_dfa_100.py`;
`docs/TfDfa100Measured.md` carries the tables.
"""
import csv
import importlib
import math
from pathlib import Path

import numpy as np
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.statistics.tf_dfa_100 import (
    BOXES, LOG_BOX_CENTRED, LOG_BOX_SS, MIN_LENGTH, _dfa_alpha, tf_dfa_100,
)

N = 400
LEVEL = 100.0
LENGTH = 100
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_dfa_100.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_tf_dfa_100.py`, shortened from
# 1,500 bars to 400 so the module stays fast -- except `_ramp`, which is 200
# bars in both. A figure quoted from that script is therefore a figure about
# 1,500-bar frames (and the 200-bar `ramp`), EXCEPT §A2, §A3 and §Z, which say
# in their own output what they ran on (200 bars and 400,000). Nothing here
# asserts one of the script's counts.


def _series(close):
    return Series(close, index=date_range("2020-01-01", periods=close.size,
                                          freq="h"))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))))


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _series(level * np.exp(x))


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    return np.round(_walk(seed, n, level) / tick) * tick


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)))


def _jump(seed=23, n=N, level=LEVEL):
    c = _walk(seed, n, level)
    return c * Series(np.where(np.arange(n) >= n // 2, 1.5, 1.0), index=c.index)


def _from_returns(r, level=LEVEL):
    """A close path whose `pct_change` IS `r`, so a claim about the RETURN
    process is not confounded by `exp(r) - 1`."""
    return _series(level * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _persistent(seed=29, n=N, level=LEVEL, phi=0.6, sigma=0.01):
    """AR(1) returns, phi > 0: trending, so the exponent must read high."""
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + rng.normal(0.0, sigma)
    return _from_returns(r, level)


def _mean_reverting(seed=31, n=N, level=LEVEL, phi=-0.6, sigma=0.01):
    """AR(1) returns, phi < 0: anti-persistent, so it must read low."""
    return _persistent(seed, n, level, phi, sigma)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _ramp(n=200, level=LEVEL, step=2.0):
    """A geometric ramp whose returns are all EXACTLY 1.0 -- the only non-flat
    way to reach a window with no fluctuation. `step` must be a power of two
    and the frame short, or consecutive ratios differ in their last bits:
    §A1's ramp table measures a 1.0000000001 ramp firing on 24 of 100 bars."""
    return _series(level * step ** np.arange(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump,
    "persistent": _persistent, "mean-reverting": _mean_reverting,
    "flat": _flat, "ramp": _ramp,
}
NAMES = list(FRAMES)
#: The frames whose returns are not all equal, i.e. the ones that fluctuate.
FIRING = [n for n in NAMES if n not in ("flat", "ramp")]
#: The two with no fluctuation at all, which therefore fire nowhere.
EMPTY = ["flat", "ramp"]


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


def _abs(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    return float((a[m] - b[m]).abs().max())


def _windows(close, length=LENGTH):
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)
    return sliding_window_view(r, length)


def _place(close, length, vals):
    out = np.full(close.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


# ----------------------------------------------------------------- oracles


def _prototype(close, length=LENGTH, boxes=BOXES):
    """`docs/issues/screen/ind_screen_r2.py:255-273`, retyped and specialised
    to one `length`, with the screen's `_fin` (+-inf -> NaN) applied as
    `screen()` applies it."""
    W = _windows(close, length)
    with np.errstate(invalid="ignore", divide="ignore"):
        Y = np.cumsum(W - W.mean(1, keepdims=True), 1)
        logF = []
        for s in boxes:
            k = W.shape[1] // s
            Z = Y[:, :k * s].reshape(len(W), k, s)
            t = np.arange(s) - (s - 1) / 2
            b = (Z * t).sum(2, keepdims=True) / (t ** 2).sum()
            R = Z - Z.mean(2, keepdims=True) - b * t
            logF.append(0.5 * np.log(
                np.where((m := (R ** 2).mean((1, 2))) == 0, np.nan, m)))
        L = np.log(np.array(boxes, dtype=float))
        Lc = L - L.mean()
        T = np.column_stack(logF)
        v = (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    return _place(close, length, v).replace([np.inf, -np.inf], np.nan)


def _loop_oracle(close, length=LENGTH, boxes=BOXES):
    """The formula by explicit scalar loops: the profile by a running sum,
    each box detrended through the NORMAL EQUATIONS on `t = 0 .. s-1` rather
    than the module's centred regressor, every sum by `math.fsum`. Shares no
    numpy operation with the module."""
    r = [float(x) for x in close.pct_change(fill_method=None).to_numpy()]
    n = len(r)
    out = [math.nan] * n
    log_box = [math.log(s) for s in boxes]
    lbar = math.fsum(log_box) / len(log_box)
    lden = math.fsum((x - lbar) ** 2 for x in log_box)
    for i in range(length - 1, n):
        w = r[i - length + 1:i + 1]
        if not all(math.isfinite(x) for x in w):
            continue
        mu = math.fsum(w) / length
        profile, acc = [], 0.0
        for x in w:
            acc += x - mu
            profile.append(acc)
        log_f, bad = [], False
        for s in boxes:
            sx = math.fsum(float(t) for t in range(s))
            sxx = math.fsum(float(t) * t for t in range(s))
            total, count = 0.0, 0
            for box in range(length // s):
                seg = profile[box * s:(box + 1) * s]
                sy = math.fsum(seg)
                sxy = math.fsum(float(t) * v for t, v in enumerate(seg))
                slope = (s * sxy - sx * sy) / (s * sxx - sx * sx)
                intercept = (sy - slope * sx) / s
                for t, v in enumerate(seg):
                    e = v - (intercept + slope * t)
                    total += e * e
                    count += 1
            ms = total / count
            if ms <= 0.0:
                bad = True
                break
            log_f.append(0.5 * math.log(ms))
        if bad:
            continue
        fbar = math.fsum(log_f) / len(log_f)
        out[i] = math.fsum((x - lbar) * (y - fbar)
                           for x, y in zip(log_box, log_f)) / lden
    return Series(out, index=close.index, dtype=float)


def _polyfit_oracle(close, length=LENGTH, boxes=BOXES):
    """The same quantity through `np.polyfit`, for the box detrend AND for
    the log-log slope: a third spelling, and one that solves both least
    squares by `lstsq` instead of by a closed form."""
    W = _windows(close, length)
    log_box = np.log(np.array(boxes, dtype=float))
    out = np.full(W.shape[0], np.nan)
    for row in range(W.shape[0]):
        w = W[row]
        if not np.isfinite(w).all():
            continue
        profile = np.cumsum(w - w.mean())
        log_f, bad = [], False
        for s in boxes:
            t = np.arange(s, dtype=float)
            resid = []
            for box in range(length // s):
                seg = profile[box * s:(box + 1) * s]
                resid.append(seg - np.polyval(np.polyfit(t, seg, 1), t))
            ms = float(np.mean(np.concatenate(resid) ** 2))
            if ms <= 0.0:
                bad = True
                break
            log_f.append(0.5 * math.log(ms))
        if bad:
            continue
        out[row] = float(np.polyfit(log_box, np.array(log_f), 1)[0])
    return _place(close, length, out)


# ----------------------------------------------------------------- mutants

RET_LINE = "    r = close.pct_change(fill_method=None).to_numpy(dtype=float)"
OUT_LINE = "            out[length - 1 + a:length - 1 + b] = _dfa_alpha(win[a:b])"
WIN_LINE = "        win = sliding_window_view(r, length)"
MASK_LINE = "    defined = np.isfinite(win).all(axis=1)"
ALPHA_LINE = "    alpha = (centred * LOG_BOX_CENTRED).sum(axis=1) / LOG_BOX_SS"
ALPHA_MATMUL = "    alpha = centred @ LOG_BOX_CENTRED / LOG_BOX_SS"

#: The four a blind future sweep catches.
LOOKAHEAD_MUTANTS = {
    "return-lead": (RET_LINE,
                    "    r = close.shift(-1).pct_change(fill_method=None)"
                    ".to_numpy(dtype=float)"),
    "output-early": (OUT_LINE,
                     "            out[length - 2 + a:length - 2 + b] = "
                     "_dfa_alpha(win[a:b])"),
    "window-ahead": (WIN_LINE,
                     "        win = sliding_window_view(np.roll(r, -1), "
                     "length)"),
    # The `bos` failure mode: a window centred on the current bar.
    "window-centred": (WIN_LINE,
                       "        win = sliding_window_view("
                       "np.roll(r, -(length // 2)), length)"),
}
#: The one it cannot: it back-dates the gap mask instead of a value.
MASK_MUTANT = (MASK_LINE,
               "    defined = np.roll(np.isfinite(win).all(axis=1), -1)")


def _mutant_ns(old, new):
    """The namespace of the SHIPPED source with one edit applied, read off
    disk and exec'd in memory -- so no mutant can drift away from the code it
    claims to edit, and a sweep cannot be fooled by an edit that silently
    failed to apply."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns


def _mutant(old, new):
    return _mutant_ns(old, new)["tf_dfa_100"]


def _mutant_alpha(ladder):
    """`_dfa_alpha` out of a mutant whose `BOXES` is `ladder`: the SHIPPED
    arithmetic on another box ladder, rather than a re-implementation of it
    that would stay green if the real detrend changed."""
    return _mutant_ns("BOXES = (4, 5, 6, 8, 10)",
                      f"BOXES = {tuple(ladder)!r}")["_dfa_alpha"]


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone -- the shape `tests/test_j_acosc.py`
    uses.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test, and getting at it needs `docs/` on `sys.path`, which
    would then shadow every later import in the pytest session with one of the
    scripts in that directory. Re-typing the cut here would pin a COPY of the
    rule rather than the rule, so this compiles the generator's actual
    function and a change to its cut reaches this test."""
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


def _futures(close, j, spread=3.0):
    """Two closes that agree BIT FOR BIT on bars < j and differ wholly on bars
    >= j. Bars < j are multiplied by exactly 1.0, which is exact."""
    n = close.size
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return (close * Series(up, index=close.index),
            close * Series(dn, index=close.index))


def _caught_at(fn, close, j):
    a, b = (fn(f).iloc[:j] for f in _futures(close, j))
    return not _bit_equal(a, b)


OFFSETS = [int(round(x)) for x in np.linspace(LENGTH + 5, N - 5, 8)]


# ------------------------------------------- 1. the ordering and the centre


def test_the_exponent_orders_persistence():
    """The whole point of the column: trending returns above a random walk,
    mean-reverting below it. Measured medians on 1,500-bar frames: 1.0580 /
    0.6444 / 0.2913 (§L2). Asserted as the ORDERING, which is the claim, with
    a gap required so a column that collapsed to noise would fail."""
    median = {name: float(tf_dfa_100(FRAMES[name]()).median())
              for name in ("mean-reverting", "walk", "persistent")}
    assert median["mean-reverting"] + 0.1 < median["walk"]
    assert median["walk"] + 0.1 < median["persistent"]


def test_the_iid_centre_is_not_one_half():
    """⚠ The disclosure that matters most to a consumer. On the shipped box
    ladder the exponent of UNCORRELATED returns is not 0.5: 40,000 iid normal
    returns read a mean of 0.6289 over 400 disjoint windows (§A5), and
    200,000 independent boxes per size imply 0.6292 for this ladder against
    0.4997 for one of 50 .. 320 (§A5b). It is DFA-1's finite-box bias, not a
    defect here, and a model told "0.5 is neutral" would read half of a
    random walk as trending.

    Asserted as a band well clear of 0.5 rather than as the digits, because
    the mean of a Monte Carlo moves with the CPU's last bits.

    ⚠ Both limbs run THIS MODULE's arithmetic. The second one is the whole
    point of the test -- that the offset is the ladder and not the code --
    so it must not be a re-implementation that would stay green after a
    regression in the per-box detrend: it calls `_dfa_alpha` out of a mutant
    whose `BOXES` is the wider ladder (round 1 finding)."""
    rng = np.random.default_rng(1234)
    r = rng.normal(0.0, 0.01, 40_000)
    rows = sliding_window_view(r, LENGTH)[::LENGTH]      # disjoint windows
    alpha = _dfa_alpha(rows)
    alpha = alpha[np.isfinite(alpha)]
    assert alpha.size == 400
    assert 0.58 < float(alpha.mean()) < 0.68
    # The SAME arithmetic on a bigger ladder lands on the textbook value.
    # Measured: mean 0.4902 over 312 disjoint 128-return windows (§A5b).
    wider = (10, 16, 25, 40, 64)
    width = 2 * max(wider)
    other = _mutant_alpha(wider)(sliding_window_view(r, width)[::width])
    other = other[np.isfinite(other)]
    assert other.size > 300
    assert 0.44 < float(other.mean()) < 0.56


@pytest.mark.parametrize("name", FIRING)
def test_every_reading_is_finite_and_inside_a_loose_sanity_band(name):
    """There is no [0, 1] here and no [0, 2] either: the `jump` frame reads
    -0.2197 .. 2.3288 on 1,500 bars (§C). All this asserts is that every
    reading is finite and inside a band far wider than anything measured;
    the unboundedness claim itself is pinned by
    `test_a_price_jump_reaches_further_than_a_walk_does`."""
    v = tf_dfa_100(FRAMES[name]()).dropna()
    assert bool(np.isfinite(v.to_numpy()).all())
    assert float(v.min()) > -5.0 and float(v.max()) < 5.0


def test_a_price_jump_reaches_further_than_a_walk_does():
    """The counterpart of the test above, and the reason "unbounded" is not
    scaremongering: one 50% gap inside the window pushes the exponent outside
    the walk's whole range, in BOTH directions."""
    walk = tf_dfa_100(_walk()).dropna()
    jump = tf_dfa_100(_jump()).dropna()
    assert float(jump.max()) > float(walk.max())
    assert float(jump.min()) < float(walk.min())


# ------------------------------------------------------------------ 2. Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_module_agrees_with_the_screen_prototype(name):
    """Not bit-equality, and the test says so: the module sums the final dot
    product where the prototype writes `@`. Measured over ten 1,500-bar
    frames, 3,209 of 11,200 bars differ by at most 4.441e-16 and the NaN
    masks are identical (§A1). The mask equality is the strict limb -- a
    different reading of an undefined window would show up there."""
    c = FRAMES[name]()
    mod, pro = tf_dfa_100(c), _prototype(c)
    assert bool((mod.isna() == pro.isna()).all())
    if int(mod.notna().sum()):
        assert _abs(mod, pro) < 1e-13


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_only_difference_is_the_dot_product_spelling(name):
    """The limb that makes the previous test an equality rather than a
    tolerance with something hiding in it: put the prototype's `@` back into
    the SHIPPED source and the two are bit-equal, on every frame. Anything
    else that had drifted -- a box size, the tail rule, the centring -- would
    survive the tolerance above and fail here."""
    c = FRAMES[name]()
    assert _bit_equal(_mutant(ALPHA_LINE, ALPHA_MATMUL)(c), _prototype(c))


@pytest.mark.parametrize("length", [MIN_LENGTH, 32, 64, LENGTH, 250])
def test_gate_a_the_prototype_agreement_holds_at_every_length(length):
    for name in ("walk", "trend", "heavy-tailed"):
        c = FRAMES[name]()
        mod = tf_dfa_100(c, length=length)
        pro = _prototype(c, length=length)
        assert bool((mod.isna() == pro.isna()).all())
        assert _abs(mod, pro) < 1e-13


@pytest.mark.parametrize("name", ["walk", "trend", "heavy-tailed",
                                  "persistent", "mean-reverting"])
@pytest.mark.parametrize("length", [MIN_LENGTH, 32])
def test_gate_a_the_formula_by_scalar_loops_agrees(name, length):
    """A spelling that shares nothing with the module: a running sum for the
    profile, the normal equations for each box, `math.fsum` throughout.
    Agreement is a band and not bit-equality, which is the finding rather
    than a weakness -- a different summation order rounds differently.
    Measured worst case 2.0e-15 absolute over 200-bar frames at lengths 20,
    32 and 100 (§A2) -- the default dispatch, which is the worse of the two
    here (1.665e-15 with AVX-512/AVX2/FMA3 off; §F2). This file runs the two
    short lengths, where the Python loop is affordable."""
    c = FRAMES[name](n=200)
    mod = tf_dfa_100(c, length=length)
    orc = _loop_oracle(c, length=length)
    assert int((mod.notna() & orc.notna()).sum()) > 100
    assert _abs(mod, orc) < 1e-11


@pytest.mark.parametrize("name", ["walk", "heavy-tailed", "persistent"])
def test_gate_a_the_same_quantity_through_polyfit_agrees(name):
    """Third spelling: `np.polyfit` for the box detrend and for the log-log
    slope. Measured worst case **3.109e-15** absolute, which is the
    AVX-512/AVX2/FMA3-disabled run; the default dispatch reads 2.887e-15
    (§A3, §F2). The band below is 1e-11, four orders clear of both."""
    c = FRAMES[name](n=200)
    mod, orc = tf_dfa_100(c), _polyfit_oracle(c)
    assert int((mod.notna() & orc.notna()).sum()) == 100
    assert _abs(mod, orc) < 1e-11


def test_the_log_log_regressor_is_the_box_ladder():
    """The constants the slope divides by are derived from `BOXES` and not
    retyped, so changing the ladder cannot leave a stale regressor behind.
    Both limbs matter: the first checks the arithmetic, the second runs a
    MUTANT whose ladder is the integers 4..10 and requires the column to
    move -- without it this test passed on a module whose `BOXES` the slope
    ignored."""
    expected = np.log(np.array(BOXES, dtype=float))
    assert np.allclose(LOG_BOX_CENTRED, expected - expected.mean(), rtol=0,
                       atol=0)
    assert LOG_BOX_SS == float((LOG_BOX_CENTRED ** 2).sum())
    # Sums to zero only up to the rounding of the mean it subtracted, so the
    # bound is that rounding and not a round number: measured 2.220e-16 here
    # and 1.110e-15 with AVX2/AVX-512 dispatch disabled, which is what
    # `docs/measure_tf_dfa_100_cpu.py` runs and what first failed a `< 1e-15`
    # literal.
    assert abs(float(LOG_BOX_CENTRED.sum())) < \
        len(BOXES) * np.finfo(float).eps * float(np.abs(expected).max())

    wider = _mutant("BOXES = (4, 5, 6, 8, 10)",
                    "BOXES = (4, 5, 6, 7, 8, 9, 10)")
    c = _walk()
    assert not _bit_equal(wider(c), tf_dfa_100(c)), "mutant is not live"
    assert _abs(wider(c), tf_dfa_100(c)) > 1e-3


def test_the_boxes_divide_the_window_the_way_the_docstring_says():
    """The tail rule, read off the shipped constants rather than retyped: at
    the default length each box size covers `length // s * s` points and
    drops the rest -- 4 points at box 6 and at box 8, none at 4, 5 or 10
    (§A7)."""
    dropped = {s: LENGTH - (LENGTH // s) * s for s in BOXES}
    assert dropped == {4: 0, 5: 0, 6: 4, 8: 4, 10: 0}
    assert min(LENGTH // s for s in BOXES) >= 2
    assert max(BOXES) * 2 == MIN_LENGTH


def test_the_source_library_is_not_readable_here():
    """⚠ Gate A does NOT read TSFEL's own code: the package is not installed
    in this worktree and web access is unavailable, so the only source text is
    the two lines issue #112 quotes. This test makes that limitation fail
    loudly if the environment ever changes, instead of leaving a docstring
    that quietly became wrong."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfel")


# ------------------------------------------- 3. the windows with no spectrum


@pytest.mark.parametrize("name", EMPTY)
def test_a_window_with_no_fluctuation_is_nan_in_both(name):
    """`length` EQUAL returns -- a flat price, or an exact x2 ramp -- leave
    the detrended fluctuation at exactly zero, so there is no log F(s) to fit
    a line through. This module says so, and so does the prototype: unlike
    `tf_spec_entropy_64`, the prototype's `m == 0` guard is NOT swallowed
    downstream, because a NaN in one of the five points reaches the slope."""
    c = FRAMES[name]()
    mod, pro = tf_dfa_100(c), _prototype(c)
    assert int(mod.notna().sum()) == 0
    assert int(pro.notna().sum()) == 0


@pytest.mark.parametrize("name", FIRING)
def test_a_window_holding_a_non_finite_return_is_nan_in_both(name):
    """`pct_change` makes bar 0 NaN, so every frame has such windows: exactly
    the `length` bars of the warm-up. Both readings agree there too, so this
    port has NO divergence from the prototype's NaN mask -- measured, not
    inherited from the previous TSFEL port, which did have one."""
    c = FRAMES[name]()
    mod, pro = tf_dfa_100(c), _prototype(c)
    assert int((mod.isna() != pro.isna()).sum()) == 0
    assert int(mod.isna().sum()) == LENGTH


def test_an_almost_constant_return_is_a_reading_and_not_a_gap():
    """The guard is EXACT equality of the fluctuation to zero, not a
    dispersion floor. A ramp whose step is not a power of two has returns
    that differ in their last bits, and the column fires on it -- which is
    why the `ramp` frame above uses x2. ⚠ A 1.0000000001 ramp fires on only
    24 of 100 bars (§A1), so "not a power of two" is not the rule either.

    Asserted as "most of them fire" and not as the exact 300: whether a
    window is flat depends on whether 100 consecutive close RATIOS come out
    bit-identical, and both `**` and `pct_change` run through dispatched
    kernels, so an exact count here is a count of last bits (round 1
    finding). The exact side is pinned where it is exact --
    `test_a_window_with_no_fluctuation_is_nan_in_both` requires 0 fires on
    the x2 ramp."""
    c = _series(LEVEL * 1.001 ** np.arange(N))
    assert int(tf_dfa_100(c).notna().sum()) > 0.9 * (N - LENGTH)


# ------------------------------------------------------------------ 4. Gate B


@pytest.mark.parametrize("name", FIRING)
def test_the_module_reads_no_future_bar(name):
    """Perturb every bar from `j` onward, two ways, and the prefix below `j`
    must not move by a bit."""
    c = FRAMES[name]()
    assert sum(_caught_at(tf_dfa_100, c, j) for j in OFFSETS) == 0


@pytest.mark.parametrize("name", FIRING)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    """Weaker than the sweep and kept because it is the check a reader
    expects: the first `j` bars of the column computed on the whole frame must
    equal the column computed on the first `j` bars alone."""
    c = FRAMES[name]()
    full = tf_dfa_100(c)
    for j in OFFSETS:
        assert _bit_equal(full.iloc[:j], tf_dfa_100(c.iloc[:j]))


@pytest.mark.parametrize("budget", [LENGTH, 7 * LENGTH])
def test_prefix_truncation_holds_across_a_chunk_boundary(budget):
    """⚠ The sweep above runs on frames that fit in ONE chunk, so it says
    nothing about the chunk loop -- and the chunk loop is where a value could
    start depending on how many bars came after it (item 6). With the budget
    cut to one and to seven rows the same frame is split many times over, and
    both the prefix equality and equality with the default run must hold."""
    mod = importlib.import_module("pandas_ta.statistics.tf_dfa_100")
    c = _walk()
    base = tf_dfa_100(c)
    old = mod.CHUNK_VALUES
    try:
        mod.CHUNK_VALUES = budget
        full = mod.tf_dfa_100(c)
        assert _bit_equal(full, base)
        for j in OFFSETS:
            assert _bit_equal(full.iloc[:j], mod.tf_dfa_100(c.iloc[:j]))
    finally:
        mod.CHUNK_VALUES = old


@pytest.mark.parametrize("label", list(LOOKAHEAD_MUTANTS))
@pytest.mark.parametrize("name", FIRING)
def test_a_look_ahead_mutant_is_live_and_caught_at_every_offset(label, name):
    """Each mutant must first CHANGE the column (a dead mutant proves
    nothing), then be caught by the same sweep the real module survives."""
    fn = _mutant(*LOOKAHEAD_MUTANTS[label])
    c = FRAMES[name]()
    assert not _bit_equal(fn(c), tf_dfa_100(c)), "mutant is not live"
    assert sum(_caught_at(fn, c, j) for j in OFFSETS) == len(OFFSETS)


@pytest.mark.parametrize("name", FIRING)
def test_the_mask_mutant_is_live_and_the_blind_sweep_misses_it(name):
    """⚠ The finding, not a weakness of the mutant. `np.roll(defined, -1)`
    back-dates the GAP mask by one bar; the bars it moves do not depend on
    the future, so the sweep returns 0 of 8 -- exactly what CLAUDE.md's Gate
    B says prefix work cannot see. It is pinned by the next test instead."""
    fn = _mutant(*MASK_MUTANT)
    c = FRAMES[name]()
    assert not _bit_equal(fn(c), tf_dfa_100(c)), "mutant is not live"
    assert sum(_caught_at(fn, c, j) for j in OFFSETS) == 0


@pytest.mark.parametrize("at", [150, 250, 350])
def test_a_mutant_that_back_dates_the_gap_mask_is_caught_by_a_planted_nan(at):
    """Plant one NaN close and read where the gap lands. The real module
    blanks the windows that CONTAIN the bad return; the mutant blanks the set
    one bar earlier, which is the definition of back-dating."""
    fn = _mutant(*MASK_MUTANT)
    c = _walk()
    c.iloc[at] = np.nan
    real = {int(i) for i in np.flatnonzero(
        tf_dfa_100(c).isna().to_numpy()) if i >= LENGTH}
    mut = {int(i) for i in np.flatnonzero(fn(c).isna().to_numpy())
           if i >= LENGTH}
    assert real and mut
    assert min(real) == at
    assert {b - 1 for b in real} <= mut
    assert min(mut) == at - 1


# ------------------------------------------------------------------ 5. Gate D


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40,
                                    2.0 ** 100])
def test_scale_an_exact_binary_factor_is_bit_identical(name, factor):
    """`(k*a) / (k*b)` is exactly `a / b` when `k` is a power of two, so the
    returns -- and therefore every later bit -- are unchanged."""
    c = FRAMES[name]()
    assert _bit_equal(tf_dfa_100(c), tf_dfa_100(c * factor))


@pytest.mark.parametrize("length", [MIN_LENGTH, 32, 64, LENGTH, 250])
def test_scale_by_eight_is_bit_identical_at_every_length(length):
    for name in FIRING:
        c = FRAMES[name]()
        assert _bit_equal(tf_dfa_100(c, length=length),
                          tf_dfa_100(c * 8.0, length=length))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """Not bit-equal, and the test says so by using a band: the division
    rounds differently, which moves the returns in their last bits. Measured
    at most 8.105e-15 ABSOLUTE on 1,500-bar frames (§D; the default
    dispatch, which is the worse of the two -- 7.994e-15 with
    AVX-512/AVX2/FMA3 off, §F2). The band is on the
    absolute difference and not the relative one, because the exponent passes
    through 0 on the `jump` frame and a relative figure there is a division
    by almost nothing -- 7.295e-13 at the same bar on the default dispatch,
    and 8.952e-13 with AVX-512/AVX2/FMA3 off, which is the one limb of this
    section where the DISABLED run is the worse one."""
    c = FRAMES[name]()
    base, scaled = tf_dfa_100(c), tf_dfa_100(c * factor)
    assert bool((base.isna() == scaled.isna()).all())
    assert _abs(scaled, base) < 1e-11


@pytest.mark.parametrize("shift", [1.0, 50.0, 1e6])
def test_scale_a_level_shift_does_move_the_column(shift):
    """A level shift is NOT a rescale -- it changes the returns -- so the
    column must move. Without this, every bit-identity above would also pass
    on a constant column."""
    c = _walk()
    a, b = tf_dfa_100(c), tf_dfa_100(c + shift)
    assert _differs(a, b) > 0
    assert _abs(a, b) > 0.0


@pytest.mark.parametrize("name", FIRING)
def test_scale_fires_strictly_between_zero_and_n(name):
    c = FRAMES[name]()
    v = tf_dfa_100(c)
    assert 0 < int(v.notna().sum()) < len(v)
    assert int(v.dropna().nunique()) > 1


# ----------------------------------- 6. the block shape, and the chunk loop


@pytest.mark.parametrize("name", ["walk", "heavy-tailed", "jump"])
def test_the_arithmetic_does_not_depend_on_the_block_shape(name):
    """⚠ The precondition the chunk loop rests on, and the reason the final
    dot product is a sum rather than `@`. One row on its own must give the
    same bits as that row inside the whole block; with `@` it does not, at
    one row per chunk on this CPU and at up to eight rows with
    AVX-512/AVX2/FMA3 disabled (§Z, §Z2), and a bar's value would then
    depend on how many bars came after it. Not asserted through `@` itself
    here: that runs through BLAS, whose dispatch is a property of the
    machine, and the two dispatches measured in §Z already disagree about
    which row counts break."""
    win = _windows(FRAMES[name]())
    whole = _dfa_alpha(win)
    for row in range(LENGTH, LENGTH + 40):
        one = _dfa_alpha(win[row:row + 1])
        assert np.array_equal(whole[row:row + 1], one, equal_nan=True)


@pytest.mark.parametrize("budget", [1, 64, 999, 10 ** 9])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every chunk is an independent run of rows and the arithmetic is
    shape-stable, so the budget can only move the peak memory."""
    mod = importlib.import_module("pandas_ta.statistics.tf_dfa_100")
    c = _walk()
    base = tf_dfa_100(c)
    old = mod.CHUNK_VALUES
    try:
        mod.CHUNK_VALUES = budget
        assert _bit_equal(base, mod.tf_dfa_100(c))
    finally:
        mod.CHUNK_VALUES = old


# --------------------------------------------- 7. what it reads and discards


@pytest.mark.parametrize("name", FIRING)
def test_the_row_helper_is_the_modules_arithmetic(name):
    """The precondition the symmetry tests below rest on. They call
    `_dfa_alpha` on explicit return windows, because a claim about rotating
    or rescaling a WINDOW cannot be made through a close path (rebuilding one
    from altered returns rounds). So the helper is pinned to the shipped
    column here, bit for bit, and those claims inherit the pin."""
    c = FRAMES[name]()
    assert _bit_equal(_place(c, LENGTH, _dfa_alpha(_windows(c))),
                      tf_dfa_100(c))


def _random_rows(seed=404, how_many=500):
    rng = np.random.default_rng(seed)
    r = _walk(n=1200).pct_change(fill_method=None).to_numpy()[1:]
    W = sliding_window_view(r, LENGTH)
    return rng, W[rng.integers(0, W.shape[0], how_many)]


def test_it_is_blind_to_the_size_and_the_sign_of_the_returns():
    """Scaling the whole window by `k` multiplies every `F(s)` by `|k|`, which
    shifts every `log F(s)` by the same constant and cancels in the slope.
    Bit-identical at x-1 (the logarithm sees the same number); only within a
    tolerance at x0.5, x2 and x2**60, because `log(k*m)` is not `log k +
    log m` in floating point. That is why this is not a volatility measure."""
    _, rows = _random_rows()
    base = _dfa_alpha(rows)
    assert np.isfinite(base).all()
    assert bool((_dfa_alpha(rows * -1.0) == base).all())
    for factor in (0.5, 2.0, 2.0 ** 60, 3.7, -0.1):
        assert float(np.abs(_dfa_alpha(rows * factor) - base).max()) < 1e-12


def test_it_is_blind_to_a_constant_drift_in_the_returns():
    """Adding a constant to every return is a straight LINE in the profile,
    and every box removes its own line, so the exponent cannot see drift --
    which is also why the window-centring step is a no-op on paper (§A8)."""
    _, rows = _random_rows()
    base = _dfa_alpha(rows)
    for add in (0.001, 0.05, 1.0):
        assert float(np.abs(_dfa_alpha(rows + add) - base).max()) < 1e-12


def test_but_it_is_not_order_blind():
    """⚠ The counterpart, and worth knowing for anyone coming from the
    spectral features, which ARE phase-blind: this one is not. Measured over
    500 windows sampled from a synthetic walk -- no real data appears in
    this port -- a permutation moves it by up to 0.5157, a time reversal
    by 0.3698 and a circular rotation by 0.4282 (§L5); a rotation splices
    the window's two ends together and the profile jumps there. Asserted as
    a floor on the maximum, not as the digits."""
    rng, rows = _random_rows()
    base = _dfa_alpha(rows)
    permuted = _dfa_alpha(np.array([rng.permutation(w) for w in rows]))
    reversed_ = _dfa_alpha(rows[:, ::-1])
    rolled = _dfa_alpha(np.array(
        [np.roll(w, int(k)) for w, k in zip(rows, rng.integers(1, LENGTH,
                                                               rows.shape[0]))]))
    for other in (permuted, reversed_, rolled):
        assert float(np.abs(other - base).max()) > 1e-2


# ------------------------------------------------- warm-up, guards, wiring


@pytest.mark.parametrize("name", FIRING)
def test_the_warm_up_is_length_bars(name):
    """`length` returns need `length + 1` closes, so the first reading is at
    bar `length` and not at `length - 1`."""
    v = tf_dfa_100(FRAMES[name]())
    assert bool(v.iloc[:LENGTH].isna().all())
    assert not math.isnan(float(v.iloc[LENGTH]))


def test_the_shortest_input_that_produces_a_value():
    assert int(tf_dfa_100(_walk(n=LENGTH + 1)).notna().sum()) == 1
    assert tf_dfa_100(_walk(n=LENGTH)) is None


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, 1e-310])
@pytest.mark.parametrize("at", [150, 250, 350])
def test_a_bad_close_empties_a_bounded_run_and_moves_nothing_earlier(value,
                                                                     at):
    """A close that is NaN, infinite or zero makes one or two returns
    non-finite, which empties at most `length + 1` windows -- and never a bar
    before the one it sits on. Measured: 101 for a NaN (it spoils the return
    into the bar and the one out of it) and 100 for the others, where one of
    the two returns stays finite (§G)."""
    base = _walk()
    c = base.copy()
    c.iloc[at] = value
    a, b = tf_dfa_100(base), tf_dfa_100(c)
    av, bv = a.to_numpy(), b.to_numpy()
    newly = int((a.notna() & b.isna()).sum())
    assert 0 < newly <= LENGTH + 1
    moved = (np.isnan(av) != np.isnan(bv)) | (
        ~np.isnan(av) & ~np.isnan(bv) & (av != bv))
    assert int(moved[:at].sum()) == 0


def test_a_negative_close_is_a_price_and_not_a_gap():
    """⚠ The guard is on the RETURN, not on the close: a negative close gives
    a perfectly finite return, so it is read rather than masked. Worth knowing
    before feeding this a spread or a differenced series."""
    base = _walk()
    c = base.copy()
    c.iloc[250] = -1.0
    v = tf_dfa_100(c)
    assert int(v.notna().sum()) == int(tf_dfa_100(base).notna().sum())
    assert _differs(v, tf_dfa_100(base)) > 0


@pytest.mark.parametrize("name", NAMES)
def test_no_floating_point_error_is_reachable(name):
    """Under `errstate(all="raise")`, which is why the module folds +-inf into
    NaN before the subtraction: `inf - inf` is the one input that raises."""
    c = FRAMES[name]()
    with np.errstate(all="raise"):
        tf_dfa_100(c)


INF_FOLD_LINE = "    r = np.where(np.isfinite(r), r, np.nan)"


@pytest.mark.parametrize("value", [np.inf, -np.inf, 0.0])
def test_the_infinity_fold_is_what_keeps_errstate_quiet(value):
    """⚠ The line the module justifies in a comment, pinned by a run instead.
    `inf - inf` is NaN WITH the invalid flag, so a window holding an infinite
    return would raise under `errstate(all="raise")` at the centring step;
    folding +-inf into NaN first makes the same window quiet, because NaN
    arithmetic does not set the flag.

    Two limbs, because the first alone proves nothing: the shipped module
    must not raise, and a MUTANT with the fold deleted must raise on the same
    frame. Without the second limb the test passed on a module that had no
    fold at all (round 2 finding -- nothing in the suite killed that line)."""
    c = _walk()
    # An infinite close makes the return INTO bar 250 infinite; a zero close
    # makes the one out of it infinite. All three reach the same line.
    c.iloc[250] = value
    r = c.pct_change(fill_method=None).to_numpy()
    assert bool(np.isinf(r).any())
    with np.errstate(all="raise"):
        v = tf_dfa_100(c)
    assert int(v.notna().sum()) > 0

    unfolded = _mutant(INF_FOLD_LINE, "    r = r")
    with pytest.raises(FloatingPointError):
        with np.errstate(all="raise"):
            unfolded(c)
    # And the fold changes no VALUE: the rows it touches are blanked by the
    # finiteness mask either way.
    with np.errstate(all="ignore"):
        assert _bit_equal(unfolded(c), tf_dfa_100(c))


@pytest.mark.parametrize("arr", ["all-nan", "all-zero", "all-negative"])
def test_a_degenerate_frame_neither_raises_nor_invents_a_value(arr):
    data = {"all-nan": np.full(N, np.nan), "all-zero": np.zeros(N),
            "all-negative": -np.abs(_walk().to_numpy())}[arr]
    with np.errstate(all="raise"):
        v = tf_dfa_100(_series(data))
    if arr == "all-negative":
        assert int(v.notna().sum()) > 0
    else:
        assert int(v.notna().sum()) == 0


def test_the_input_series_is_not_mutated():
    c = _walk()
    before = c.to_numpy().copy()
    tf_dfa_100(c)
    assert bool((c.to_numpy() == before).all())


@pytest.mark.parametrize("length", [None, 0, 1, MIN_LENGTH - 1])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """Below `2 * max(BOXES)` the largest box would have a single box to
    average over, so the module refuses the value instead of shipping an
    `F(s)` that is one box at the top of the ladder and ten at the bottom."""
    assert tf_dfa_100(_walk(), length=length).name == "TFDFA_100"
    assert tf_dfa_100(_walk(), length=MIN_LENGTH).name == f"TFDFA_{MIN_LENGTH}"


def test_offset_and_fillna():
    c = _walk()
    base = tf_dfa_100(c)
    import pandas as pd
    pd.testing.assert_series_equal(tf_dfa_100(c, offset=1), base.shift(1))
    assert int(tf_dfa_100(c, fillna=0).isna().sum()) == 0


def test_the_five_wiring_touch_points():
    """Module, package export, `Category`, accessor, and this file."""
    from pandas_ta.statistics import tf_dfa_100 as exported
    assert exported is tf_dfa_100
    assert "tf_dfa_100" in ta.Category["statistics"]

    c = _walk()
    df = DataFrame({"close": c})
    out = df.ta.tf_dfa_100()
    assert out.name == "TFDFA_100"
    assert out.category == "statistics"
    import pandas as pd
    pd.testing.assert_series_equal(out, tf_dfa_100(c))
    assert df.ta.tf_dfa_100(length=20).name == "TFDFA_20"


def test_the_docstring_first_paragraph_survives_the_dictionary_cut():
    """CLAUDE.md sends a reader to `docs/IndicatorDictionary.md` first, and
    the generator truncates the first paragraph. The cut is NOT 150
    characters: it is `d[:150].rsplit(" ", 1)[0]`, which drops the trailing
    word whole. Measured slack at the time of writing: 6 characters on a
    144-character paragraph (`python docs/measure_tf_dfa_100.py W`), which
    is tight -- a longer sentence fails here rather than silently losing its
    end in the table. Both disclosures have to fit inside that cut, because
    the dictionary row is the first thing CLAUDE.md sends a reader to and it
    is where "Unbounded" would otherwise be lost (round 3 finding)."""
    desc = _generator_desc()
    body = " ".join(tf_dfa_100.__doc__.split("\n\n")[1].split())
    assert not desc({"desc": body}).endswith("…")
    assert desc({"desc": body}) == body


def test_the_gate_e_row_is_owed_and_not_yet_recorded():
    """This commit ships Gate E OWED: issue-solver runs
    `gate_e_overlap.py` after the session, and a later receipt session
    records the row and replaces this test with one pinning its identity
    (the shape `tests/test_tf_spec_entropy_64.py` ended up in). Until
    then `tests/test_gate_e_ledger.py::
    test_every_indicator_that_needs_a_row_has_one` fails locally and
    skips on CI under `GATE_E_PENDING_OK=1`, which is the documented
    "owed, not failed" state.

    The prototype's figure is NOT this port's: the 2026-10-24 screen
    measured max |rho| 0.0979 against `Swing_Range_pct` over 389,949
    bars on the PROTOTYPE expression, which this module matches to
    4.441e-16 but not bit for bit. Gate C's real-data limb is owed from
    the same run."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "tf_dfa_100"]
    assert rows == []
