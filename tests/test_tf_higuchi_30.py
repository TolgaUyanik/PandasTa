# -*- coding: utf-8 -*-
"""TF-HIGUCHI-30: `tf_higuchi_30`, the Higuchi fractal dimension of the last
30 closes (PandasTa issue #115, TSFEL's `higuchi_fractal_dimension`,
BSD-3-Clause).

    W         = close[T - 29 .. T]
    L(k)      = mean over m = 0 .. k-1 of
                SUM |W[m + jk] - W[m + (j-1)k]| * 29 / (intervals * k) / k
    TFHIGUCHI = OLS slope of log(L(k) / L(1)) on log(1 / k), k = 1 .. 5

What this file pins, in order of how much it would hurt to lose:

1. **THE ANCHORS, WHICH ARE EXACT FOR ONCE.** An arithmetic ramp has
   Higuchi dimension 1 in exact arithmetic -- every lag-k difference
   is the same number, so `L(k) = step * 29 / k` and the slope on
   `log(1/k)` is 1 -- and the module reads 1.0000000000000002 on
   every bar of such a frame, which `test_a_straight_line_reads_one`
   asserts as a tolerance. A Brownian path (true dimension 1.5) reads
   a mean of **1.5137** over 1,000 disjoint 30-bar windows and iid
   normal noise (true 2.0) reads **1.9978** (§A4); both are asserted
   as bands, because a Monte Carlo mean moves with the CPU's last
   bits. The ordering smooth < walk < iid noise (measured medians
   1.0135 / 1.4725 / 1.9945) is the claim the column exists for.
   ⚠ Also pinned: the column is NOT bounded to [1, 2]. Ten 1,500-bar
   frames run 0.9458 .. 2.1941.

2. **Gate A, the quantity spelled three ways -- and the TWO places
   this port is not the prototype.** The screen prototype (the
   expression Gate E's 0.5231 was measured on) agrees to **4.219e-15**
   with an identical NaN mask, NOT bit for bit, and the difference is
   two spellings: the logarithm is taken of `L(k) / L(1)` rather than
   of `L(k)`, and the final dot product is summed rather than written
   `@`. A mutant of the shipped file with BOTH put back is asserted
   bit-equal to the prototype, which leaves nothing else between them.
   The ratio is a Gate D fix (item 5) and the sum a chunk-safety fix
   (item 6). Two further oracles: Higuchi's own 1-based scalar loop
   built from `math.fsum` agrees to **8.882e-16** (§A2) and an
   `np.linalg.lstsq` form to **3.109e-15** (§A3) -- the latter the
   default dispatch, the worse of the two there (2.442e-15 with
   AVX-512/AVX2/FMA3 off). §F2 of `docs/TfHiguchi30Measured.md`
   tabulates the figures this port quotes, what each reads on the two
   dispatches, and which of the two is quoted.
   ⚠ The source itself is NOT readable here.
   `test_the_source_library_is_not_readable_here` asserts that, so the
   limitation fails loudly if the environment ever changes.

3. **The windows with no curve, and they are the prototype's too.**
   Three measured ways in. A flat window has every `L(k)` at exactly
   zero. A window of period exactly 2 has `L(2)` and `L(4)` at zero
   while `L(1)` is 29 — measured `L = [29, 0, 3.222, 0, 1.16]` on the
   `alternating` frame. A window of period exactly 4 is a DIFFERENT
   case, and the one these docstrings first got wrong: there `L(4)`
   alone is zero and `L(2)` is not — measured
   `L = [43, 14.5, 4.893, 0, 1.7168]`. All three are NaN here AND in
   the prototype, pinned as zero bars on which one reads and the other
   does not. ⚠ A ZERO close is not a gap: nothing is divided by the
   price, so `close = 0` is read like any other level (unlike every
   return-based port in this family).

4. **Gate B: five mutants, and the one the sweep cannot see.** All
   five are read off disk, edited and `exec`'d in memory. Four -- a
   leading close, an early write index, a window rolled one bar
   forward, and a window CENTRED on the current bar (the `bos`
   failure mode) -- are caught at every swept offset on every frame.
   The fifth back-dates the NaN mask by one bar; prefix truncation
   and the future sweep are both blind to back-dating, so it is
   pinned directly, by planting one NaN close and reading where the
   gap lands.

5. **Gate D: an exact binary rescale of the PRICE is bit-identical,
   and that is what the `L(k) / L(1)` spelling buys.** x8, x64,
   2**-40, 2**40 and 2**100 on ten frames at the default length, and
   x8 again at five lengths; an inexact factor only to a tolerance
   (5.906e-14). ⚠ A level SHIFT is NOT the anti-vacuity check it is
   for the return-based ports: this column reads only DIFFERENCES of
   closes, so a shift is invariant in exact arithmetic and moves
   nothing but last bits (4.006e-11 at +1e6). What stands in its
   place is `0 < fires < n` with a non-constant column, asserted
   separately, plus `test_a_different_path_is_a_different_reading`.

6. **The arithmetic does not depend on the BLOCK SHAPE, which is what
   makes the chunk loop safe.** `_higuchi_fd` on one row is asserted
   bit-equal to the same row inside the whole block of a 400-bar frame
   (§Z2 of the receipt runs the same check on a 1,500-bar one), and the
   column
   bit-identical at chunk budgets 1, 64, 999 and 10**9. This is the
   test that would have failed with `@`: 28 of 200 rows computed one
   per block move their last bit under both dispatches (§Z2). ⚠ That
   `@` figure is NOT asserted here -- it runs through BLAS, so another
   machine's BLAS may not reproduce it.

7. **What it reads, and what it throws away.** ⚠ It is TIME-REVERSAL
   BLIND: reversing a window maps each strand's lag-k differences onto
   itself, so the reading is the same in exact arithmetic -- measured
   within **6.661e-16** over 500 sampled windows, 71 of which move a
   last bit because the sums then run backwards, and asserted as that
   tolerance. It is not order blind in general -- a permutation moves
   it by up to 1.0204 and a rotation by up to 0.2771, asserted as
   floors. It is blind to the size and the sign of the window
   (bit-identical at x-1, x0.5, x2, x2**60).

8. **⚠ The overlap with `vhf`, which Gate E's comparator set cannot
   see.** `VHF_28` is `(max - min) / sum|close diff|` over 28 bars,
   and `sum|close diff|` over the window IS this column's `L(1)`.
   Measured on eight 1,500-bar synthetic frames: pooled Spearman
   -0.8901, per-frame |rho| 0.4721 .. 0.8284, median 0.7151 (§L4).
   The 2026-10-24 screen read 0.6496 on 12 real frames. Three tests
   hold the disclosure: the relationship itself (asserted as a band),
   that it survives the dictionary cut, and that the receipt still
   carries the OWED item with its revert rule -- Gate E runs against
   the ENGINE's 687 comparators, so a green row there would not
   settle a fork overlap.

9. **Gate E is owed.** `test_the_gate_e_row_is_owed_and_not_yet_recorded`
   asserts the ledger has no row for `tf_higuchi_30`: issue-solver
   runs Gate E after this session and the receipt session records the
   row, replacing that test. Gate C's real-data limb is owed from the
   same run; everything in this file is synthetic.

Every number above is printed by `python docs/measure_tf_higuchi_30.py`,
and by `python docs/measure_tf_higuchi_30_cpu.py <section>` for the
AVX-disabled dispatch, EXCEPT item 2's Gate E figure of 0.5231, which is
quoted from issue #115 and was measured on the PROTOTYPE by the
2026-10-24 screen -- that script's own docstring names it as one of the
three things it does not print. `docs/TfHiguchi30Measured.md` carries the
tables.
"""
import csv
import importlib
import math
import re
from pathlib import Path

import numpy as np
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series, concat, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.statistics.tf_higuchi_30 import (
    KMAX, LOG_INV_K_CENTRED, LOG_INV_K_SS, MIN_LENGTH, _higuchi_fd,
    tf_higuchi_30,
)

N = 400
LEVEL = 100.0
LENGTH = 30
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_higuchi_30.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_tf_higuchi_30.py`, shortened from
# 1,500 bars to 400 so the module stays fast -- except `ramp`, which is 60
# bars in both. A figure quoted from that script is therefore a figure about
# 1,500-bar frames; nothing here asserts one of its counts.


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


def _noise(seed=41, n=N, level=LEVEL, sigma=0.02):
    """iid closes: the ROUGHEST curve a price can be."""
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(rng.normal(0.0, sigma, n)))


def _smooth(seed=43, n=N, level=LEVEL, span=40):
    """A walk run through a 40-bar moving average: the SMOOTH end. Its first
    `span` bars are constant after the back-fill, so the windows ending there
    read NaN -- which is why the sweep below starts at bar 60."""
    c = _walk(seed, n, level)
    return _series(c.rolling(span).mean().bfill().to_numpy())


def _line(n=N, level=LEVEL, step=2.0):
    """An arithmetic ramp: Higuchi dimension 1, exactly (item 1)."""
    return _series(level + step * np.arange(n, dtype=float))


def _ramp(n=60, level=LEVEL, step=2.0):
    """A geometric ramp. Unlike `tf_dfa_100`'s it FIRES, and it reads a
    CONSTANT: every window is a scaled copy of the one before it, and the
    dimension is scale-free. 60 bars because `100 * 2**i` overflows."""
    return _series(level * step ** np.arange(n, dtype=float))


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _alternating(n=N, level=LEVEL, amp=1.0):
    """Period 2 exactly: every lag-2 and lag-4 difference is zero, so L(2)
    and L(4) are zero and there is no logarithm to take."""
    return _series(level + amp * (np.arange(n) % 2))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "noise": _noise,
    "smooth": _smooth, "line": _line, "ramp": _ramp, "flat": _flat,
    "alternating": _alternating,
}
NAMES = list(FRAMES)
#: Frames on which the column reads somewhere.
FIRING = [n for n in NAMES if n not in ("flat", "alternating")]
#: Frames on which it reads nowhere; §G says why for each.
EMPTY = ["flat", "alternating"]
#: Frames whose readings VARY. `line` and `ramp` are constant by
#: construction, so they cannot carry a "not constant" claim.
VARYING = [n for n in FIRING if n not in ("line", "ramp")]
#: The frames the future sweep runs on: `ramp` is 60 bars, so every offset
#: but the first falls past its end and the two perturbed futures would be
#: identical frames.
SWEPT = [n for n in FIRING if n != "ramp"]
#: The first offset is 60 and not `LENGTH + 5`, because `smooth`'s first 40
#: bars are constant and read NaN, so a prefix cut below bar 40 holds no
#: reading for a mutant to move.
OFFSETS = [int(round(x)) for x in np.linspace(60, N - 5, 6)]


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
    return sliding_window_view(close.to_numpy(dtype=float), length)


def _place(close, length, vals):
    out = np.full(close.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3:
        return float("nan")
    x, y = a[m].rank(), b[m].rank()
    if float(x.std()) == 0.0 or float(y.std()) == 0.0:
        return float("nan")
    return float(x.corr(y))


def _curve(window, kmax=KMAX):
    """`L(k)` for a single window, by the module's own spelling -- used only
    to show WHICH `L(k)` is zero on the empty frames."""
    W = np.asarray(window, dtype=float).reshape(1, -1)
    length = W.shape[1]
    out = []
    for k in range(1, kmax + 1):
        gap = np.abs(W[:, k:] - W[:, :-k])
        strands = [gap[:, m::k].sum(axis=1) * (length - 1)
                   / (gap[:, m::k].shape[1] * k) / k for m in range(k)]
        out.append(float(np.mean(strands, axis=0)[0]))
    return out


# ----------------------------------------------------------------- oracles


def _prototype(close, length=LENGTH, kmax=KMAX):
    """`docs/issues/screen/ind_screen_r2.py:276-293` (candidate
    `tf_higuchi_30`), retyped and specialised to one `length`, with the
    screen's `_fin` (+-inf -> NaN) applied as `screen()` applies it."""
    W = _windows(close, length)
    with np.errstate(invalid="ignore", divide="ignore"):
        Nw = W.shape[1]
        lk = []
        for k in range(1, kmax + 1):
            Lm = []
            for m in range(k):
                idx = np.arange(m, Nw, k)
                n_int = len(idx) - 1
                Lm.append(np.abs(np.diff(W[:, idx], axis=1)).sum(1)
                          * (Nw - 1) / (n_int * k) / k)
            lk.append(np.log(np.mean(Lm, axis=0)))
        x = np.log(1 / np.arange(1, kmax + 1))
        xc = x - x.mean()
        T = np.column_stack(lk)
        v = (T - T.mean(1, keepdims=True)) @ xc / (xc ** 2).sum()
    return _place(close, length, v).replace([np.inf, -np.inf], np.nan)


def _loop_oracle(close, length=LENGTH, kmax=KMAX):
    """Higuchi (1988) by explicit scalar loops, in the paper's own 1-based
    indexing with its `floor((N - m) / k)` interval count: every sum by
    `math.fsum`, the slope through the normal equations. Shares no numpy
    operation with the module."""
    c = [float(x) for x in close.to_numpy(dtype=float)]
    n = len(c)
    out = [math.nan] * n
    xs = [math.log(1.0 / k) for k in range(1, kmax + 1)]
    xbar = math.fsum(xs) / len(xs)
    xden = math.fsum((x - xbar) ** 2 for x in xs)
    for i in range(length - 1, n):
        w = c[i - length + 1:i + 1]                   # w[0] is Higuchi's X(1)
        if not all(math.isfinite(x) for x in w):
            continue
        ys, bad = [], False
        for k in range(1, kmax + 1):
            lms = []
            for m in range(1, k + 1):
                steps = (length - m) // k
                if steps < 1:
                    bad = True
                    break
                total = math.fsum(abs(w[m - 1 + j * k] - w[m - 1 + (j - 1) * k])
                                  for j in range(1, steps + 1))
                lms.append(total * (length - 1) / (steps * k) / k)
            if bad:
                break
            lk = math.fsum(lms) / len(lms)
            if not lk > 0.0:
                bad = True
                break
            ys.append(math.log(lk))
        if bad:
            continue
        ybar = math.fsum(ys) / len(ys)
        out[i] = math.fsum((x - xbar) * (y - ybar)
                           for x, y in zip(xs, ys)) / xden
    return Series(out, index=close.index, dtype=float)


def _lstsq_oracle(close, length=LENGTH, kmax=KMAX):
    """The same quantity through `np.linalg.lstsq` on a design matrix with an
    intercept column -- the shape the published implementations use, and a
    third way of solving the least squares."""
    W = _windows(close, length)
    design = np.column_stack([np.log(1.0 / np.arange(1, kmax + 1)),
                              np.ones(kmax)])
    out = np.full(W.shape[0], np.nan)
    for row in range(W.shape[0]):
        w = W[row]
        if not np.isfinite(w).all():
            continue
        ys, bad = [], False
        for k in range(1, kmax + 1):
            lms = []
            for m in range(k):
                idx = np.arange(m, length, k)
                n_int = len(idx) - 1
                lms.append(float(np.abs(np.diff(w[idx])).sum())
                           * (length - 1) / (n_int * k) / k)
            lk = float(np.mean(lms))
            if not lk > 0.0:
                bad = True
                break
            ys.append(math.log(lk))
        if bad:
            continue
        out[row] = float(np.linalg.lstsq(design, np.array(ys),
                                         rcond=None)[0][0])
    return _place(close, length, out)


# ----------------------------------------------------------------- mutants

CLOSE_LINE = "    c = close.to_numpy(dtype=float)"
FOLD_LINE = "    c = np.where(np.isfinite(c), c, np.nan)"
WIN_LINE = "        win = sliding_window_view(c, length)"
OUT_LINE = "            out[length - 1 + a:length - 1 + b] = _higuchi_fd(win[a:b])"
MASK_LINE = "    defined = np.isfinite(win).all(axis=1)"
CURVE_LINE = "    log_l = np.log(safe / safe[:, :1])"
CURVE_RAW = "    log_l = np.log(safe)"
FD_LINE = "    fd = (centred * LOG_INV_K_CENTRED).sum(axis=1) / LOG_INV_K_SS"
FD_MATMUL = "    fd = centred @ LOG_INV_K_CENTRED / LOG_INV_K_SS"

#: The four a blind future sweep catches.
LOOKAHEAD_MUTANTS = {
    "close-lead": (CLOSE_LINE,
                   "    c = close.shift(-1).to_numpy(dtype=float)"),
    "output-early": (OUT_LINE,
                     "            out[length - 2 + a:length - 2 + b] = "
                     "_higuchi_fd(win[a:b])"),
    "window-ahead": (WIN_LINE,
                     "        win = sliding_window_view(np.roll(c, -1), "
                     "length)"),
    # The `bos` failure mode: a window centred on the current bar.
    "window-centred": (WIN_LINE,
                       "        win = sliding_window_view("
                       "np.roll(c, -(length // 2)), length)"),
}
#: The one it cannot: it back-dates the gap mask instead of a value.
MASK_MUTANT = (MASK_LINE,
               "    defined = np.roll(np.isfinite(win).all(axis=1), -1)")


def _mutant_ns(*edits):
    """The namespace of the SHIPPED source with the edits applied, read off
    disk and exec'd in memory -- so no mutant can drift away from the code it
    claims to edit, and a sweep cannot be fooled by an edit that silently
    failed to apply."""
    src = SOURCE.read_text(encoding="utf-8")
    for old, new in edits:
        assert src.count(old) == 1, \
            f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
        src = src.replace(old, new)
    ns = {}
    exec(compile(src, "<mutant>", "exec"), ns)
    return ns


def _mutant(*edits):
    return _mutant_ns(*edits)["tf_higuchi_30"]


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone -- the shape `tests/test_j_acosc.py`
    uses.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test, and getting at it needs `docs/` on `sys.path`,
    which would then shadow every later import in the pytest session with one
    of the scripts in that directory. Re-typing the cut here would pin a COPY
    of the rule rather than the rule, so this compiles the generator's actual
    function and a change to its cut reaches this test."""
    import ast
    path = ROOT / "docs" / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


def _futures(close, j, spread=3.0):
    """Two closes that agree BIT FOR BIT on bars < j and differ wholly on
    bars >= j. Bars < j are multiplied by exactly 1.0, which is exact."""
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


def _random_rows(seed=404, how_many=500):
    rng = np.random.default_rng(seed)
    W = _windows(_walk(n=1200))
    return rng, W[rng.integers(0, W.shape[0], how_many)]


# ----------------------------------------------- 1. the anchors and the band


def test_a_straight_line_reads_one():
    """⚠ The anchor that makes this port checkable against the DEFINITION and
    not only against another implementation. Every lag-k difference of an
    arithmetic ramp is the same number, so `L(k) = step * (length - 1) / k`,
    `log L(k) = const + log(1/k)`, and the slope on `log(1/k)` is 1 exactly.

    Asserted as a tolerance and not as `== 1.0`: the module reads
    1.0000000000000002 on every bar here (§A4), which is one ulp above one,
    and the last bit is a property of the CPU's `log`."""
    v = tf_higuchi_30(_line()).dropna()
    assert len(v) == N - LENGTH + 1
    assert float((v - 1.0).abs().max()) < 1e-12
    # And it is the SAME number on every bar: a line has no scale.
    assert int(v.nunique()) == 1


def test_a_brownian_path_reads_one_and_a_half():
    """The textbook value for a random walk, and the one a consumer will
    check first. Measured mean 1.5137 (sd 0.1453) over 1,000 disjoint 30-bar
    windows; iid normal noise reads 1.9978 (sd 0.0894) against its textbook
    2.0 (§A4). Both asserted as bands, because a Monte Carlo mean moves with
    the CPU's last bits.

    ⚠ Both limbs run THIS MODULE's arithmetic through `_higuchi_fd`, which
    `test_the_row_helper_is_the_modules_arithmetic` pins to the shipped
    column, so neither can stay green on a re-implementation."""
    rng = np.random.default_rng(2024)
    brownian = np.cumsum(rng.normal(0.0, 1.0, 30_000))
    noise = rng.normal(0.0, 1.0, 30_000)
    for data, lo, hi, n in ((brownian, 1.44, 1.59, 1000),
                            (noise, 1.94, 2.06, 1000)):
        v = _higuchi_fd(sliding_window_view(data, LENGTH)[::LENGTH])
        v = v[np.isfinite(v)]
        assert v.size == n
        assert lo < float(v.mean()) < hi


def test_the_dimension_orders_roughness():
    """The claim the column exists for: a smoothed path below a random walk,
    a random walk below iid noise. Measured medians on 1,500-bar frames:
    1.0135 / 1.4725 / 1.9945 (§A4). Asserted as the ORDERING with a gap, so
    a column collapsed to noise would fail."""
    median = {name: float(tf_higuchi_30(FRAMES[name]()).median())
              for name in ("smooth", "walk", "noise")}
    assert median["smooth"] + 0.1 < median["walk"]
    assert median["walk"] + 0.1 < median["noise"]


@pytest.mark.parametrize("name", FIRING)
def test_every_reading_is_finite_and_inside_a_loose_sanity_band(name):
    """⚠ There is no [1, 2] here: ten 1,500-bar frames run 0.9458 .. 2.1941
    (§C), below 1 on a heavily smoothed path and above 2 on iid noise. All
    this asserts is that every reading is finite and inside a band far wider
    than anything measured; the unboundedness itself is the next test."""
    v = tf_higuchi_30(FRAMES[name]()).dropna()
    assert bool(np.isfinite(v.to_numpy()).all())
    assert float(v.min()) > 0.0 and float(v.max()) < 3.0


def test_the_nominal_one_to_two_range_is_not_a_bound():
    """The counterpart, and the reason "not bounded" is not scaremongering:
    the smoothed frame reaches BELOW 1 and the iid frame ABOVE 2. Asserted as
    the direction of each breach, not as the digits."""
    assert float(tf_higuchi_30(_smooth()).min()) < 1.0
    assert float(tf_higuchi_30(_noise()).max()) > 2.0


# ------------------------------------------------------------------ 2. Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_module_agrees_with_the_screen_prototype(name):
    """Not bit-equality, and the test says so: this module divides by `L(1)`
    before the logarithm and sums the final dot product where the prototype
    logs `L(k)` and writes `@`. Measured over twelve 1,500-bar frames, about
    6,600 of the 13,259 bars both define differ by at most 4.219e-15 and the
    NaN masks are identical (§A1). The mask equality is the strict limb -- a
    different reading of an undefined window would show up there."""
    c = FRAMES[name]()
    mod, pro = tf_higuchi_30(c), _prototype(c)
    assert bool((mod.isna() == pro.isna()).all())
    if int(mod.notna().sum()):
        assert _abs(mod, pro) < 1e-12


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_only_difference_is_the_two_mutant_spellings(name):
    """The limb that makes the test above an equality rather than a tolerance
    with something hiding in it: put the prototype's `np.log(L(k))` and its
    `@` back into the SHIPPED source and the two are bit-equal, on every
    frame. Anything else that had drifted -- a spacing, the strand
    normalisation, the interval count, the regressor -- would survive the
    tolerance above and fail here."""
    c = FRAMES[name]()
    back = _mutant((CURVE_LINE, CURVE_RAW), (FD_LINE, FD_MATMUL))
    assert _bit_equal(back(c), _prototype(c))


@pytest.mark.parametrize("length", [MIN_LENGTH, 20, LENGTH, 60, 250])
def test_gate_a_the_prototype_agreement_holds_at_every_length(length):
    for name in ("walk", "trend", "heavy-tailed"):
        c = FRAMES[name]()
        mod = tf_higuchi_30(c, length=length)
        pro = _prototype(c, length=length)
        assert bool((mod.isna() == pro.isna()).all())
        assert _abs(mod, pro) < 1e-12


@pytest.mark.parametrize("name", ["walk", "trend", "heavy-tailed", "noise",
                                  "smooth", "line"])
@pytest.mark.parametrize("length", [MIN_LENGTH, LENGTH])
def test_gate_a_the_formula_by_scalar_loops_agrees(name, length):
    """A spelling that shares nothing with the module: Higuchi's own 1-based
    indexing, his `floor((N - m) / k)` interval count, `math.fsum`
    throughout, the slope through the normal equations. Agreement is a band
    and not bit-equality, which is the finding rather than a weakness -- a
    different summation order rounds differently. Measured worst case
    8.882e-16 absolute over 300-bar frames (§A2), the same figure under both
    dispatches."""
    c = FRAMES[name](n=300)
    mod = tf_higuchi_30(c, length=length)
    orc = _loop_oracle(c, length=length)
    assert bool((mod.isna() == orc.isna()).all())
    assert int((mod.notna() & orc.notna()).sum()) > 100
    assert _abs(mod, orc) < 1e-11


@pytest.mark.parametrize("name", ["walk", "heavy-tailed", "noise", "grid"])
def test_gate_a_the_same_quantity_through_lstsq_agrees(name):
    """Third spelling: `np.linalg.lstsq` on a design matrix with an intercept
    column, which is how the published implementations fit the line.
    Measured worst case **3.109e-15** absolute, the default dispatch; with
    AVX-512/AVX2/FMA3 off it reads 2.442e-15 (§A3, §F2). The band below is
    1e-11, four orders clear of both."""
    c = FRAMES[name](n=300)
    mod, orc = tf_higuchi_30(c), _lstsq_oracle(c)
    assert int((mod.notna() & orc.notna()).sum()) == 300 - LENGTH + 1
    assert _abs(mod, orc) < 1e-11


def test_the_log_log_regressor_is_the_spacing_ladder():
    """The constants the slope divides by are derived from `KMAX` and not
    retyped, so changing the ladder cannot leave a stale regressor behind.
    Both limbs matter: the first checks the arithmetic, the second runs a
    MUTANT whose `KMAX` is 10 and requires the column to move -- without it
    this test would pass on a module whose `KMAX` the slope ignored."""
    expected = np.log(1.0 / np.arange(1, KMAX + 1))
    assert np.array_equal(LOG_INV_K_CENTRED, expected - expected.mean())
    assert LOG_INV_K_SS == float((LOG_INV_K_CENTRED ** 2).sum())
    # Sums to zero only up to the rounding of the mean it subtracted, so the
    # bound is that rounding and not a round number.
    assert abs(float(LOG_INV_K_CENTRED.sum())) < \
        KMAX * np.finfo(float).eps * float(np.abs(expected).max())

    wider = _mutant(("KMAX = 5", "KMAX = 10"))
    c = _walk()
    assert not _bit_equal(wider(c), tf_higuchi_30(c)), "mutant is not live"
    assert _abs(wider(c), tf_higuchi_30(c)) > 1e-3


def test_the_strands_cover_the_window_the_way_the_docstring_says():
    """The interval counts, read off the shipped `KMAX` and `LENGTH` rather
    than retyped: at the default length the strand `(k, m)` holds
    `len(range(m, 30, k))` points, and the furthest point it reaches is
    `30 - 1 - dropped` (§A5). The minimum interval count is what `MIN_LENGTH`
    exists to protect."""
    counts = {(k, m): len(np.arange(m, LENGTH, k)) - 1
              for k in range(1, KMAX + 1) for m in range(k)}
    assert counts[(1, 0)] == LENGTH - 1 == 29
    assert {counts[(2, m)] for m in range(2)} == {14}
    assert {counts[(3, m)] for m in range(3)} == {9}
    assert {counts[(4, m)] for m in range(4)} == {6, 7}
    assert {counts[(5, m)] for m in range(5)} == {5}
    assert min(counts.values()) >= 1
    # At MIN_LENGTH the last strand still has two points, and one fewer close
    # would leave it with one.
    assert MIN_LENGTH == 2 * KMAX
    assert len(np.arange(KMAX - 1, MIN_LENGTH, KMAX)) == 2
    assert len(np.arange(KMAX - 1, MIN_LENGTH - 1, KMAX)) == 1


def test_the_source_library_is_not_readable_here():
    """⚠ Gate A does NOT read TSFEL's own code: the package is not installed
    in this worktree and web access is unavailable, so the only source text
    is the two lines issue #115 quotes. This test makes that limitation fail
    loudly if the environment ever changes, instead of leaving a docstring
    that quietly became wrong."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfel")


# ------------------------------------------- 3. the windows with no curve


@pytest.mark.parametrize("name", EMPTY)
def test_a_window_with_a_zero_curve_length_is_nan_in_both(name):
    """Two different ways to reach it, and the module and the prototype agree
    on both. A FLAT window has every `L(k)` at zero. A window of period
    exactly 2 has `L(2)` and `L(4)` at zero while `L(1)` is 29 -- measured
    `[29, 0, 3.222, 0, 1.16]` (§G) -- which is the case a guard written as
    "L(1) > 0" alone would have shipped as a reading."""
    c = FRAMES[name]()
    assert int(tf_higuchi_30(c).notna().sum()) == 0
    assert int(_prototype(c).notna().sum()) == 0
    curve = _curve(_windows(c)[0])
    zeros = [k for k, v in zip(range(1, KMAX + 1), curve) if v == 0.0]
    assert zeros == ([1, 2, 3, 4, 5] if name == "flat" else [2, 4])


def test_a_period_four_window_is_a_gap_but_for_a_different_reason():
    """⚠ The case the two docstrings used to lump in with the period-2 one,
    and it is not the same case. On `a, b, c, d, a, b, c, d, ...` only the
    lag-4 differences vanish; the lag-2 ones are `|c - a|` and `|d - b|`,
    which are not zero. Measured over a 30-close window of
    `100, 101, 103, 102`: `L = [43, 14.5, 4.893, 0, 1.7168]` — zero at
    `k = 4` alone (§G). The window is still a gap, because the guard is
    `L(k) > 0` at EVERY spacing, and the prototype agrees."""
    p4 = _series(LEVEL + np.array([0.0, 1.0, 3.0, 2.0])[np.arange(N) % 4])
    assert int(tf_higuchi_30(p4).notna().sum()) == 0
    assert int(_prototype(p4).notna().sum()) == 0
    curve = _curve(_windows(p4)[0])
    assert curve[3] == 0.0, curve
    assert [i for i, v in enumerate(curve) if v == 0.0] == [3], curve


@pytest.mark.parametrize("name", FIRING)
def test_a_window_holding_a_non_finite_close_is_nan_in_both(name):
    """The warm-up is the only gap on a clean frame, and both readings agree
    there: `length - 1` bars."""
    c = FRAMES[name]()
    mod, pro = tf_higuchi_30(c), _prototype(c)
    assert int((mod.isna() != pro.isna()).sum()) == 0
    if name != "smooth":
        assert int(mod.isna().sum()) == LENGTH - 1


def test_a_zero_close_is_a_price_and_not_a_gap():
    """⚠ Worth knowing before reading this like its return-based siblings:
    nothing is divided by the close, so a zero -- or a negative -- price is a
    perfectly ordinary level here and empties no window. `tf_dfa_100` blanks
    100 windows for the same input."""
    base = _walk()
    for value in (0.0, -1.0, 1e-310):
        c = base.copy()
        c.iloc[250] = value
        v = tf_higuchi_30(c)
        assert int(v.notna().sum()) == int(tf_higuchi_30(base).notna().sum())
        assert _differs(v, tf_higuchi_30(base)) > 0


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("at", [150, 250, 350])
def test_a_bad_close_empties_a_bounded_run_and_moves_nothing_earlier(value,
                                                                     at):
    """A NaN or an infinite close empties exactly the `length` windows that
    contain it -- never one before the bar it sits on."""
    base = _walk()
    c = base.copy()
    c.iloc[at] = value
    a, b = tf_higuchi_30(base), tf_higuchi_30(c)
    av, bv = a.to_numpy(), b.to_numpy()
    assert int((a.notna() & b.isna()).sum()) == LENGTH
    moved = (np.isnan(av) != np.isnan(bv)) | (
        ~np.isnan(av) & ~np.isnan(bv) & (av != bv))
    assert int(moved[:at].sum()) == 0


# ------------------------------------------------------------------ 4. Gate B


@pytest.mark.parametrize("name", SWEPT)
def test_the_module_reads_no_future_bar(name):
    """Perturb every bar from `j` onward, two ways, and the prefix below `j`
    must not move by a bit."""
    c = FRAMES[name]()
    assert sum(_caught_at(tf_higuchi_30, c, j) for j in OFFSETS) == 0


@pytest.mark.parametrize("name", FIRING)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    """Weaker than the sweep and kept because it is the check a reader
    expects: the first `j` bars of the column computed on the whole frame
    must equal the column computed on the first `j` bars alone."""
    c = FRAMES[name]()
    full = tf_higuchi_30(c)
    for j in OFFSETS:
        if j > c.size:
            continue
        assert _bit_equal(full.iloc[:j], tf_higuchi_30(c.iloc[:j]))


@pytest.mark.parametrize("budget", [LENGTH, 7 * LENGTH])
def test_prefix_truncation_holds_across_a_chunk_boundary(budget):
    """⚠ The sweep above runs on frames that fit in ONE chunk, so it says
    nothing about the chunk loop -- and the chunk loop is where a value could
    start depending on how many bars came after it (item 6). With the budget
    cut to one and to seven rows the same frame is split many times over, and
    both the prefix equality and equality with the default run must hold."""
    mod = importlib.import_module("pandas_ta.statistics.tf_higuchi_30")
    c = _walk()
    base = tf_higuchi_30(c)
    old = mod.CHUNK_VALUES
    try:
        mod.CHUNK_VALUES = budget
        full = mod.tf_higuchi_30(c)
        assert _bit_equal(full, base)
        for j in OFFSETS:
            assert _bit_equal(full.iloc[:j], mod.tf_higuchi_30(c.iloc[:j]))
    finally:
        mod.CHUNK_VALUES = old


@pytest.mark.parametrize("label", list(LOOKAHEAD_MUTANTS))
@pytest.mark.parametrize("name", SWEPT)
def test_a_look_ahead_mutant_is_live_and_caught_at_every_offset(label, name):
    """Each mutant must first CHANGE the column (a dead mutant proves
    nothing), then be caught by the same sweep the real module survives."""
    fn = _mutant(LOOKAHEAD_MUTANTS[label])
    c = FRAMES[name]()
    assert not _bit_equal(fn(c), tf_higuchi_30(c)), "mutant is not live"
    assert sum(_caught_at(fn, c, j) for j in OFFSETS) == len(OFFSETS)


@pytest.mark.parametrize("name", SWEPT)
def test_the_mask_mutant_is_live_only_on_a_gapped_frame_and_the_sweep_misses_it(
        name):
    """⚠ The finding, not a weakness of the mutant. `np.roll(defined, -1)`
    back-dates the GAP mask by one bar. On a clean frame it is not even live
    -- every window is defined -- and the future sweep returns 0 of 6, which
    is exactly what CLAUDE.md's Gate B says prefix work cannot see. It is
    pinned by the next test instead."""
    fn = _mutant(MASK_MUTANT)
    c = FRAMES[name]()
    assert _bit_equal(fn(c), tf_higuchi_30(c))
    assert sum(_caught_at(fn, c, j) for j in OFFSETS) == 0


@pytest.mark.parametrize("at", [150, 250, 350])
def test_a_mutant_that_back_dates_the_gap_mask_is_caught_by_a_planted_nan(at):
    """Plant one NaN close and read where the gap lands. The real module
    blanks the windows that CONTAIN the bad close; the mutant blanks the set
    one bar earlier, which is the definition of back-dating."""
    fn = _mutant(MASK_MUTANT)
    c = _walk()
    c.iloc[at] = np.nan
    real = {int(i) for i in np.flatnonzero(
        tf_higuchi_30(c).isna().to_numpy()) if i >= LENGTH}
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
    """⚠ The test the `L(k) / L(1)` spelling exists for. A power of two times
    a float is exact, and so is a sum of exactly-scaled floats, so every
    `L(k)` scales by exactly `factor` and the RATIO is unchanged bit for bit.
    With the prototype's `log L(k)` this would be a tolerance, because
    `log(8 L)` is not `log 8 + log L` in floating point and the leftover
    moves with `k`."""
    c = FRAMES[name]()
    assert _bit_equal(tf_higuchi_30(c), tf_higuchi_30(c * factor))


def test_scale_the_prototype_spelling_would_only_be_a_tolerance():
    """The other half of the claim above, and the reason the divergence is a
    FIX and not a preference: a mutant with `np.log(L(k))` put back is NOT
    bit-identical under x8 -- measured here, not asserted."""
    raw = _mutant((CURVE_LINE, CURVE_RAW))
    c = _walk()
    assert not _bit_equal(raw(c), raw(c * 8.0))
    # ... while still being the same quantity, so this is about last bits.
    assert _abs(raw(c), raw(c * 8.0)) < 1e-12


@pytest.mark.parametrize("length", [MIN_LENGTH, 20, LENGTH, 60, 250])
def test_scale_by_eight_is_bit_identical_at_every_length(length):
    for name in FIRING:
        c = FRAMES[name]()
        if c.size < length:
            continue
        assert _bit_equal(tf_higuchi_30(c, length=length),
                          tf_higuchi_30(c * 8.0, length=length))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """Not bit-equal, and the test says so by using a band: the
    multiplication rounds differently, which moves the closes in their last
    bits. Measured at most 5.906e-14 ABSOLUTE on 1,500-bar frames (§D; the
    default dispatch, the worse of the two -- 5.751e-14 with
    AVX-512/AVX2/FMA3 off, §F2)."""
    c = FRAMES[name]()
    base, scaled = tf_higuchi_30(c), tf_higuchi_30(c * factor)
    assert bool((base.isna() == scaled.isna()).all())
    assert _abs(scaled, base) < 1e-11


@pytest.mark.parametrize("shift", [1.0, 50.0, 1e6])
def test_scale_a_level_shift_is_invariant_and_so_cannot_be_the_vacuity_check(
        shift):
    """⚠ The place this port differs from its return-based siblings, and the
    reason the anti-vacuity check had to move. A level shift changes no
    DIFFERENCE of closes in exact arithmetic, so the column is invariant to
    it: measured within 4.006e-11 at +1e6 (§D), which is the rounding of
    `(c + 1e6) - (c' + 1e6)` and not a reading. `tf_dfa_100` asserts the
    opposite -- that a shift MOVES its column -- because a shift changes a
    RETURN. What stands in for it here is the pair below."""
    c = _walk()
    a, b = tf_higuchi_30(c), tf_higuchi_30(c + shift)
    assert bool((a.isna() == b.isna()).all())
    assert _abs(a, b) < 1e-9


@pytest.mark.parametrize("name", VARYING)
def test_scale_fires_strictly_between_zero_and_n_and_is_not_constant(name):
    """The anti-vacuity check, in place of the level shift: every bit-identity
    above would also pass on a constant column."""
    c = FRAMES[name]()
    v = tf_higuchi_30(c)
    assert 0 < int(v.notna().sum()) < len(v)
    assert int(v.dropna().nunique()) > 100


def test_a_different_path_is_a_different_reading():
    """The second half of the anti-vacuity pair: the column must respond to
    the SHAPE of the path even though it ignores its level and its scale. A
    walk, a smoothed walk and iid noise must give three different columns."""
    walk, smooth, noise = (tf_higuchi_30(_walk()), tf_higuchi_30(_smooth()),
                           tf_higuchi_30(_noise()))
    assert _differs(walk, smooth) > 300
    assert _differs(walk, noise) > 300
    assert _differs(smooth, noise) > 300


# ----------------------------------- 6. the block shape, and the chunk loop


@pytest.mark.parametrize("name", ["walk", "heavy-tailed", "jump"])
def test_the_arithmetic_does_not_depend_on_the_block_shape(name):
    """⚠ The precondition the chunk loop rests on, and the reason the final
    dot product is a sum rather than `@`. One row on its own must give the
    same bits as that row inside the whole block; with `@` it does not --
    28 of 200 rows move under both dispatches (§Z2) -- and a bar's value
    would then depend on how many bars came after it. Not asserted through
    `@` itself here: that runs through BLAS, whose dispatch is a property of
    the machine."""
    win = _windows(FRAMES[name]())
    whole = _higuchi_fd(win)
    for row in range(LENGTH, LENGTH + 40):
        one = _higuchi_fd(win[row:row + 1])
        assert np.array_equal(whole[row:row + 1], one, equal_nan=True)


@pytest.mark.parametrize("budget", [1, 64, 999, 10 ** 9])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every chunk is an independent run of rows and the arithmetic is
    shape-stable, so the budget can only move the peak memory. Measured on
    400,000 bars: 57.4 MB at the shipped budget against 298.0 MB
    unbounded (§Z)."""
    mod = importlib.import_module("pandas_ta.statistics.tf_higuchi_30")
    c = _walk()
    base = tf_higuchi_30(c)
    old = mod.CHUNK_VALUES
    try:
        mod.CHUNK_VALUES = budget
        assert _bit_equal(base, mod.tf_higuchi_30(c))
    finally:
        mod.CHUNK_VALUES = old


# --------------------------------------------- 7. what it reads and discards


@pytest.mark.parametrize("name", FIRING)
def test_the_row_helper_is_the_modules_arithmetic(name):
    """The precondition the symmetry tests below rest on. They call
    `_higuchi_fd` on explicit close windows, because a claim about reversing
    or rescaling a WINDOW cannot be made through a whole frame. So the helper
    is pinned to the shipped column here, bit for bit, and those claims
    inherit the pin."""
    c = FRAMES[name]()
    assert _bit_equal(_place(c, LENGTH, _higuchi_fd(_windows(c))),
                      tf_higuchi_30(c))


def test_it_is_blind_to_the_size_and_the_sign_of_the_window():
    """Scaling a window by `k` multiplies every `L(k)` by `|k|`, which cancels
    in the ratio before the logarithm -- so this is not a volatility measure.
    Bit-identical at an exact binary factor and at x-1; only within a
    tolerance at an inexact one (3.997e-15 at x3.7, the AVX-disabled
    dispatch, which is the worse of the two)."""
    _, rows = _random_rows()
    base = _higuchi_fd(rows)
    assert np.isfinite(base).all()
    for factor in (-1.0, 0.5, 2.0, 2.0 ** 60):
        assert bool((_higuchi_fd(rows * factor) == base).all())
    for factor in (3.7, -0.1):
        assert float(np.abs(_higuchi_fd(rows * factor) - base).max()) < 1e-12


def test_it_is_time_reversal_blind():
    """⚠ The symmetry a reader coming from `tf_dfa_100` will not expect.
    Reversing the closes inside a window maps each strand's multiset of
    lag-k differences onto itself, so every `L(k)` is the same number in
    exact arithmetic and the dimension cannot see the arrow of time.

    Asserted as a tolerance and NOT as bit-equality, which is the
    measurement and not a hedge: 71 of the 500 sampled windows DO move,
    by at most 6.661e-16, because the strand sums then run in the
    opposite order (§L; 59 windows and 4.441e-16 on the default numpy
    dispatch, which is why the COUNT is not pinned). The band below is
    five orders clear of that and
    eleven below what a permutation does (1.0204), so a port that broke
    the symmetry could not pass it."""
    _, rows = _random_rows()
    base = _higuchi_fd(rows)
    assert float(np.abs(_higuchi_fd(rows[:, ::-1]) - base).max()) < 1e-11


def test_but_it_is_not_order_blind_in_general():
    """The counterpart: only the reversal is free. Measured over 500 windows
    sampled from a synthetic walk -- no real data appears in this port -- a
    permutation moves it by up to 1.0204 (median 0.5355) and a circular
    rotation by up to 0.2771 (median 0.0613), a rotation splicing the
    window's two ends together. Asserted as floors on the maximum."""
    rng, rows = _random_rows()
    base = _higuchi_fd(rows)
    permuted = _higuchi_fd(np.array([rng.permutation(w) for w in rows]))
    rolled = _higuchi_fd(np.array(
        [np.roll(w, int(k)) for w, k in zip(rows, rng.integers(1, LENGTH,
                                                               rows.shape[0]))]))
    assert float(np.abs(permuted - base).max()) > 0.5
    assert float(np.abs(rolled - base).max()) > 0.1


# ---------------------------------------------------- 8. the `vhf` overlap


@pytest.mark.parametrize("name", ["walk", "trend", "grid", "heavy-tailed",
                                  "noise"])
def test_the_overlap_with_vhf_is_real_and_bounded_where_it_was_measured(name):
    """⚠ The disclosure Gate E's comparator set cannot make: `vhf` is a FORK
    column and Gate E compares against the engine's 687. `VHF_28` is
    `(max - min) / sum|close diff|` over 28 bars and `sum|close diff|` over
    the window IS this column's `L(1)`, so the two are cousins and the sign
    is negative -- a rougher path travels further per unit of range.

    Measured on eight 1,500-bar frames: per-frame |rho| 0.4721 .. 0.8284,
    median 0.7151, pooled -0.8901 (§L4). Asserted per frame, as the sign and
    as a ceiling at the owner's 0.90 line, so a port that became a
    restatement of `vhf` fails here; the pooled figure is not asserted
    because pooling eight different processes inflates it."""
    c = FRAMES[name]()
    rho = _spearman(tf_higuchi_30(c), ta.vhf(c))
    assert rho < 0.0, rho
    assert abs(rho) < 0.90, rho


def test_the_vhf_warning_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows the first paragraph after the
    title, squeezed and truncated. The `vhf` overlap is the one thing a
    reader of the dictionary must see, so it has to fit inside that cut --
    which is a real constraint and not a formality: the paragraph has room
    for one sentence and the warning (measured slack: 17 characters on a
    133-character paragraph, `python docs/measure_tf_higuchi_30.py W`)."""
    desc = _generator_desc()
    body = " ".join(tf_higuchi_30.__doc__.split("\n\n")[1].split())
    cut = desc({"desc": body})
    assert not cut.endswith("…"), cut
    # `desc` also rewrites `|` as `/` so the text cannot break the markdown
    # table it lands in, which is why this is not `cut == body`.
    assert cut == body.replace("|", "/"), cut
    assert "vhf" in cut, cut
    assert "1.5 a random walk" in cut, cut


def test_the_vhf_overlap_measurement_is_still_owed_from_the_gate_e_run():
    """The `vhf` overlap is the one thing Gate E's comparator set cannot see,
    so "the owner's call" needs a trigger or it is never made: the receipt
    session has to check whether `vhf` is among the run's 687 comparators and,
    if it is not, measure rho against `VHF_28` on the same 89 frames and apply
    the same band. This asserts the owed item and its revert rule are still in
    the receipt, so a green Gate E row cannot be recorded without meeting
    them."""
    doc = (ROOT / "docs" / "TfHiguchi30Measured.md").read_text(
        encoding="utf-8")
    # Each string is unique to the OWED block: "VHF_28" and "revert" on their
    # own are satisfied by §L4's table with the block deleted.
    assert "OWED from the Gate E run" in doc
    assert "revert `tf_higuchi_30` if it is" in doc
    assert "r3-perframe-0.90" in doc


# ------------------------------------------------- warm-up, guards, wiring


@pytest.mark.parametrize("name", FIRING)
def test_the_warm_up_is_length_minus_one_bars(name):
    """A window of `length` CLOSES, not of `length` returns, so the first
    reading is at bar `length - 1`."""
    v = tf_higuchi_30(FRAMES[name]())
    assert bool(v.iloc[:LENGTH - 1].isna().all())
    if name != "smooth":          # `smooth` is flat for its first 40 bars
        assert not math.isnan(float(v.iloc[LENGTH - 1]))


def test_the_shortest_input_that_produces_a_value():
    assert int(tf_higuchi_30(_walk(n=LENGTH)).notna().sum()) == 1
    assert tf_higuchi_30(_walk(n=LENGTH - 1)) is None


@pytest.mark.parametrize("name", NAMES)
def test_no_floating_point_error_is_reachable_at_ordinary_magnitudes(name):
    """Under `errstate(all="raise")` on every frame in this file. ⚠ It is a
    claim about ORDINARY price magnitudes: §G measures a frame of +-1e307
    closes whose `L(k)` overflows and which DOES raise, at the sum, before
    any guard can act. The column is NaN there under the default error
    state."""
    c = FRAMES[name]()
    with np.errstate(all="raise"):
        tf_higuchi_30(c)


@pytest.mark.parametrize("where", [(250,), (250, 255)])
def test_the_infinity_fold_is_what_keeps_errstate_quiet(where):
    """⚠ The line the module justifies in a comment, pinned by a run instead.
    An infinite close reaches the invalid flag by TWO different routes, and
    §G measures both on the fold-deleted mutant:

    * ONE infinite close is already enough. `inf - finite` is plain `inf`, so
      the subtraction is quiet, but every `L(k)` of that window is then `inf`
      and `safe / safe[:, :1]` is `inf / inf` -- NaN WITH the invalid flag.
      Measured: `invalid value encountered in divide`. ⚠ That site exists
      only because this port takes the logarithm of the RATIO; the
      prototype's `log L(k)` has no division there, so this is a raise the
      Gate D divergence created and the fold pays for.
    * TWO infinite closes inside one window reach it one step earlier, at
      `inf - inf` in the subtraction itself. Measured: `invalid value
      encountered in subtract`.

    Both are parametrised, so the weaker input -- one close -- is pinned too.

    Two limbs each, because the first alone proves nothing: the shipped
    module must not raise, and a MUTANT with the fold deleted must raise on
    the same frame."""
    c = _walk()
    for at in where:
        c.iloc[at] = np.inf
    with np.errstate(all="raise"):
        v = tf_higuchi_30(c)
    assert int(v.notna().sum()) > 0

    unfolded = _mutant((FOLD_LINE, "    c = c"))
    with pytest.raises(FloatingPointError):
        with np.errstate(all="raise"):
            unfolded(c)
    # And the fold changes no VALUE: the rows it touches are blanked by the
    # finiteness mask either way.
    with np.errstate(all="ignore"):
        assert _bit_equal(unfolded(c), tf_higuchi_30(c))


@pytest.mark.parametrize("arr", ["all-nan", "all-zero", "all-negative",
                                 "all-inf"])
def test_a_degenerate_frame_neither_raises_nor_invents_a_value(arr):
    data = {"all-nan": np.full(N, np.nan), "all-zero": np.zeros(N),
            "all-negative": -np.abs(_walk().to_numpy()),
            "all-inf": np.full(N, np.inf)}[arr]
    with np.errstate(all="raise"):
        v = tf_higuchi_30(_series(data))
    if arr == "all-negative":
        assert int(v.notna().sum()) == N - LENGTH + 1
    else:
        assert int(v.notna().sum()) == 0


def test_the_input_series_is_not_mutated():
    c = _walk()
    before = c.to_numpy().copy()
    tf_higuchi_30(c)
    assert bool((c.to_numpy() == before).all())


@pytest.mark.parametrize("length", [None, 0, 1, MIN_LENGTH - 1])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """Below `2 * KMAX` the last strand at `k = KMAX` would hold a single
    point and no interval at all, so the module refuses the value instead of
    shipping an `L(KMAX)` built from nothing."""
    assert tf_higuchi_30(_walk(), length=length).name == "TFHIGUCHI_30"
    assert tf_higuchi_30(_walk(),
                         length=MIN_LENGTH).name == f"TFHIGUCHI_{MIN_LENGTH}"


def test_offset_and_fillna():
    import pandas as pd
    c = _walk()
    base = tf_higuchi_30(c)
    pd.testing.assert_series_equal(tf_higuchi_30(c, offset=1), base.shift(1))
    filled = tf_higuchi_30(c, fillna=-1.0)
    assert int(filled.isna().sum()) == 0
    assert bool((filled.iloc[:LENGTH - 1] == -1.0).all())


def test_the_five_wiring_touch_points():
    """Module, package export, `Category`, accessor, and this file."""
    import pandas as pd
    from pandas_ta.statistics import tf_higuchi_30 as exported
    assert exported is tf_higuchi_30
    assert ta.tf_higuchi_30 is tf_higuchi_30
    assert "tf_higuchi_30" in ta.Category["statistics"]

    c = _walk()
    df = DataFrame({"close": c})
    out = df.ta.tf_higuchi_30()
    assert out.name == "TFHIGUCHI_30"
    assert out.category == "statistics"
    pd.testing.assert_series_equal(out, tf_higuchi_30(c))
    assert df.ta.tf_higuchi_30(length=20).name == "TFHIGUCHI_20"


def test_the_gate_e_row_is_owed_and_not_yet_recorded():
    """Gate E is run by issue-solver after this session; the receipt session
    records the row and replaces this test."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "tf_higuchi_30"]
    assert rows == []
