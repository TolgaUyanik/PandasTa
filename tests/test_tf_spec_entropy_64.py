# -*- coding: utf-8 -*-
"""TF-SPEC-ENTROPY-64: `tf_spec_entropy_64`, the normalised entropy of the
power spectrum of the last 64 daily returns (PandasTa issue #111, TSFEL's
`spectral_entropy`, BSD-3-Clause).

    RET       = close / close[1] - 1
    W         = RET[T - 63 .. T] - mean(RET[T - 63 .. T])
    P         = abs(rfft(W))[1:] ** 2            # 32 bins, DC dropped
    TFSPECENT = -SUM(P/SUM(P) * log2(P/SUM(P))) / log2(32)

What this file pins, in order of how much it would hurt to lose:

1. **THE BOUND AND WHAT SITS AT EACH END, which is the whole reason a
   spectral entropy is a feature rather than a spectrum.** The column
   lives in `[0, 1]`: 1 is a flat spectrum, 0 is all the power in one
   bin. Pinned as a bound on every frame and at six lengths, and both
   ends are pinned by construction -- a sinusoid exactly on a bin reads
   below 1e-20 (measured 1.309e-27 .. 3.311e-25 over bins 1, 2, 8 and 16
   of 1,500-bar frames) and a Gaussian walk's returns read above 0.75
   and below 1.0.
   ⚠ Also pinned is what the bound is NOT: the value never reaches
   exactly 0.0 and never reaches exactly 1.0 on any frame here -- on the
   seven firing frames in `test_the_column_stays_inside_zero_and_one`,
   and on the four sinusoid frames, whose values are 1e-27-small, in
   `test_a_sinusoid_on_a_bin_is_the_zero_end`. A consumer must not test
   this column for equality with either end.

2. **Gate A, the quantity spelled three ways -- and which limb is
   bit-equal.** (Three, not four: §A4's DC-keeping variant is the
   reading this port did NOT take, not a third oracle for the one it
   did.) The screen prototype (the expression Gate E's 0.0284 was
   measured on) is asserted BIT-equal on every bar both define. Two
   independent oracles -- a scalar-loop DFT built from `cmath` and
   `math.log2`, and numpy's COMPLEX `fft` instead of `rfft` -- are
   asserted equal only to a tolerance, and that is the finding rather
   than a weakness: an FFT is a different summation order per spelling.
   The two figures have DIFFERENT provenance and the assertions are
   bands either way: the complex-FFT oracle differs by up to 8.022e-16,
   from §A3 on 1,500-bar frames, and the loop oracle by up to
   6.476e-15, from §A2 at `length` 64 on **200-bar** frames (§A2 cannot
   be a 1,500-bar run -- it is `O(rows * length^2)` in Python). This
   file's loop-oracle test uses those same 200 bars, at `length` 8 and
   16, where §A2 prints 6.275e-15 and 3.639e-15.
   ⚠ The source itself is NOT readable here.
   `test_the_source_library_is_not_readable_here` asserts that, so the
   limitation fails loudly if the environment ever changes.

3. **The two divergences from the prototype, which are the two windows
   that have no spectrum.** The prototype reads **-0.0** -- a legible
   entropy -- for a window holding a non-finite return and for one whose
   returns are all equal, because the NaN its `s == 0` guard injects is
   swallowed by the `p > 0` mask on the next line. This module reads NaN
   for both. Pinned as exactly one bar per ordinary frame (the warm-up
   bar `length - 1`), as every bar of a flat frame, and as every bar of
   an exact x2 ramp.

4. **Gate B: five mutants, and the one the sweep cannot see.** All five
   are read off disk, edited and `exec`'d in memory. Four of them --
   a leading return, an early write index, a window rolled one bar
   forward, and a window CENTRED on the current bar (the `bos` failure
   mode) -- are caught at every swept offset on every frame. The fifth
   back-dates the NaN mask by one bar; prefix truncation and the future
   sweep are both blind to back-dating, so it is pinned directly, by
   planting one NaN close and reading where the gap lands.

5. **Gate D: an exact binary rescale is bit-identical, an inexact one is
   not.** Two separate claims, and the file asserts them separately: x8,
   x64, 2**-40, 2**40 and 2**100 are bit-identical on seven frames at the
   DEFAULT length, and x8 again at six lengths. x10, x3.7, x0.1 and
   x1.0000001 only to a tolerance. A
   level SHIFT is asserted to MOVE the column, so the scale test cannot
   pass by the column being constant, and `0 < fires < n` is asserted
   separately.

6. **What the magnitude spectrum throws away.** `abs(rfft(.))` has no
   phase, so rotating a window circularly or reversing it end to end
   leaves the value equal to within **1e-14 -- asserted here, over 500
   windows**; §L5 measures 4.441e-16 over 2,000. A general
   PERMUTATION is not one of those symmetries and is asserted to move
   the column, so "phase-blind" cannot be read as "order-blind".

7. **The leakage artefact.** There is no window function, because TSFEL
   applies none. A sinusoid at bin 8.5 reads an order of magnitude more
   entropy than the same sinusoid at bin 8 -- asserted as an ordering,
   not as a value, because it is the column's main artefact and a reader
   who does not know it will read "no cycle" where there is one.

8. **The chunk budget cannot change a value.** `CHUNK_VALUES` bounds the
   peak memory off `len(close) * length`; the column is asserted
   bit-identical at budgets 1, 64, 999 and 10**9.

9. **Gate E is owed.** `test_the_gate_e_row_is_owed_and_not_yet_recorded`
   asserts `docs/gate_e_ledger.csv` carries no row for this indicator,
   which is the state this commit ships in and the receipt session's cue.

Every number above is printed by `python docs/measure_tf_spec_entropy_64.py`;
`docs/TfSpecEntropy64Measured.md` carries the tables.
"""
import cmath
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
from pandas_ta.statistics.tf_spec_entropy_64 import (
    MIN_LENGTH, tf_spec_entropy_64,
)

N = 400
LEVEL = 100.0
LENGTH = 64
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_spec_entropy_64.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_tf_spec_entropy_64.py`, shortened
# from 1,500 bars to 400 so the module stays fast -- except `_ramp`, which is
# 200 bars in both, because its step has to be a power of two over a short
# frame or its returns are equal only to the last bits. A figure quoted from
# that script is therefore a figure about 1,500-bar frames (and 200-bar
# `ramp`) -- EXCEPT §A2 and §Z,
# which say in their own output what they ran on (200 bars and 400,000), and
# which this file quotes with that size named. Nothing here asserts one of
# the script's counts.


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
    """A close path whose `pct_change` IS `r`. ⚠ `level * exp(cumsum(r))` is
    not that path -- its returns are `exp(r) - 1`, whose harmonics put real
    entropy into a frame built from a single sine."""
    return _series(level * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _sine(bin_=8.0, n=N, length=LENGTH, amp=0.01, level=LEVEL):
    return _from_returns(amp * np.sin(2 * np.pi * bin_ * np.arange(n) / length),
                         level)


def _cycle(seed=29, n=N, level=LEVEL, bin_=8, length=LENGTH, noise=0.002):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return _from_returns(
        0.01 * np.sin(2 * np.pi * bin_ * t / length) + rng.normal(0.0, noise, n),
        level)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _ramp(n=200, level=LEVEL, step=2.0):
    """A geometric ramp whose returns are all EXACTLY 1.0 -- the only non-flat
    way to reach a window with no spectrum. `step` must be a power of two and
    the frame short, or the ratio is exact only to the last bits."""
    return _series(level * step ** np.arange(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "cycle": _cycle,
    "flat": _flat, "ramp": _ramp,
}
NAMES = list(FRAMES)
#: The frames whose returns are not all equal, i.e. the ones with a spectrum.
FIRING = [n for n in NAMES if n not in ("flat", "ramp")]
#: The two that have no spectrum at all, and so fire nowhere.
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


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen_r2.py:229-252`, retyped and specialised
    to one `length`, with the screen's `_fin` (+-inf -> NaN) applied as
    `screen()` applies it."""
    W = _windows(close, length)
    F = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1))[:, 1:]
    P = F ** 2
    s = P.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(s == 0, np.nan, s)
        v = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1)), 0).sum(1) \
            / np.log2(P.shape[1])
    return _place(close, length, v).replace([np.inf, -np.inf], np.nan)


def _loop_oracle(close, length=LENGTH):
    """The formula by explicit scalar loops: the DFT by `cmath.exp`
    summation, the entropy by `math.log2`. Shares no numpy operation with the
    module."""
    r = [float(x) for x in close.pct_change(fill_method=None).to_numpy()]
    n, nbins = len(r), length // 2
    norm = math.log2(nbins)
    out = [math.nan] * n
    for i in range(length - 1, n):
        w = r[i - length + 1:i + 1]
        if not all(math.isfinite(x) for x in w):
            continue
        mu = math.fsum(w) / length
        d = [x - mu for x in w]
        power = []
        for k in range(1, nbins + 1):
            acc = 0j
            for t, x in enumerate(d):
                acc += x * cmath.exp(-2j * math.pi * k * t / length)
            power.append(abs(acc) ** 2)
        total = math.fsum(power)
        if total <= 0.0:
            continue
        h = 0.0
        for q in power:
            pr = q / total
            if pr > 0.0:
                h -= pr * math.log2(pr)
        out[i] = h / norm
    return Series(out, index=close.index, dtype=float)


def _complex_fft_oracle(close, length=LENGTH):
    """The same quantity through numpy's COMPLEX `fft`, keeping bins
    `1 .. length // 2`, instead of through `rfft`."""
    W = _windows(close, length)
    nbins = length // 2
    X = np.fft.fft(W - W.mean(1, keepdims=True), axis=1)[:, 1:nbins + 1]
    P = X.real ** 2 + X.imag ** 2
    tot = P.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(tot > 0.0, tot, 1.0)[:, None]
        h = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1.0)), 0.0).sum(1)
        h = h / np.log2(nbins)
    ok = np.isfinite(W).all(1) & (tot > 0.0)
    return _place(close, length, np.where(ok, h, np.nan))


def _entropy_of_rows(W):
    """The module's arithmetic on an explicit (rows, length) block, so a claim
    about the WINDOW is not confounded by rebuilding a close path.

    ⚠ This is a COPY of the module's arithmetic, and a copy that only claims
    to be one is worth nothing: add a window function to `_spectral_entropy`
    and every test built on this helper would stay green while the shipped
    docstring became false. `test_the_row_helper_is_the_modules_arithmetic`
    pins it to the module, and section 6's tests depend on that test holding.
    """
    P = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1))[:, 1:] ** 2
    tot = P.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(tot > 0.0, tot, 1.0)[:, None]
        h = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1.0)), 0.0).sum(1)
        h = h / np.log2(P.shape[1])
    return np.where(np.isfinite(W).all(1) & (tot > 0.0), h, np.nan)


# ----------------------------------------------------------------- mutants

RET_LINE = "    r = close.pct_change(fill_method=None).to_numpy(dtype=float)"
OUT_LINE = "            out[length - 1 + a:length - 1 + b] = \\"
WIN_LINE = ("        win = sliding_window_view(r, length)   "
            "# (rows, length), oldest first")
MASK_LINE = "    ok = np.isfinite(win).all(axis=1) & (total > 0.0)"
NORM_LINE = "        norm = np.log2(length // 2)"

#: The four a blind future sweep catches.
LOOKAHEAD_MUTANTS = {
    "return-lead": (RET_LINE,
                    "    r = close.shift(-1).pct_change(fill_method=None)"
                    ".to_numpy(dtype=float)"),
    "output-early": (OUT_LINE,
                     "            out[length - 2 + a:length - 2 + b] = \\"),
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
               "    ok = np.roll(np.isfinite(win).all(axis=1), -1) "
               "& (total > 0.0)")


def _mutant(old, new):
    """`tf_spec_entropy_64` with one edit applied to the SHIPPED source, read
    off disk and exec'd in memory -- so no mutant can drift away from the code
    it claims to edit, and a sweep cannot be fooled by an edit that silently
    failed to apply."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tf_spec_entropy_64"]


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


# ------------------------------------------------------------- 1. the bound


@pytest.mark.parametrize("name", FIRING)
def test_the_column_stays_inside_zero_and_one(name):
    """`-SUM(p log2 p)` is at most `log2(K)` for `K` bins, so dividing by
    `log2(K)` bounds the column at 1; every term is non-negative, so 0 is the
    floor. Both limbs are float-exact claims here rather than tolerances:
    measured over seven 1,500-bar frames the largest excess over 1.0 is
    0.000e+00 (§A5)."""
    v = tf_spec_entropy_64(FRAMES[name]()).dropna()
    assert len(v)
    assert float(v.min()) >= 0.0
    assert float(v.max()) <= 1.0
    # Strictly inside, on every firing frame and not only on the walk: a
    # consumer must not test this column for equality with either end.
    assert not bool((v == 0.0).any())
    assert not bool((v == 1.0).any())


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 8, 20, LENGTH, 250])
def test_the_bound_holds_at_every_length(length):
    for name in FIRING:
        v = tf_spec_entropy_64(FRAMES[name](), length=length).dropna()
        assert len(v)
        assert 0.0 <= float(v.min()) and float(v.max()) <= 1.0


def test_a_sinusoid_on_a_bin_is_the_zero_end():
    """One sinusoid exactly on a bin puts every unit of power in that bin, so
    the entropy collapses. Pinned as a bound (1e-20) and not as a value: the
    measured range over bins 1, 2, 8 and 16 on 1,500-bar frames is
    1.309e-27 .. 3.311e-25, which is float noise and will differ by CPU."""
    for b in (1, 2, 8, 16):
        v = tf_spec_entropy_64(_sine(b)).dropna()
        assert len(v)
        assert float(v.max()) < 1e-20
        # Not exactly 0.0 either, so item 1's "on any frame here" covers the
        # sinusoid frames and not only the seven firing ones.
        assert not bool((v == 0.0).any())


def test_a_random_walk_is_the_one_end_without_reaching_it():
    """White-ish returns spread their power nearly evenly, so the column sits
    near the top of its range -- but never AT it, which is the part a consumer
    can get wrong. Measured mean 0.8837 on the 1,500-bar walk (§L); this
    400-bar frame is asserted only to sit in a band."""
    v = tf_spec_entropy_64(_walk()).dropna()
    assert len(v)
    assert 0.75 < float(v.min())
    assert float(v.max()) < 1.0
    assert not (v == 0.0).any()
    assert not (v == 1.0).any()


# ------------------------------------------------------------------ 2. Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_module_is_the_screen_prototype_bit_for_bit(name):
    """Every bar both define, bit for bit -- the module's arithmetic IS the
    prototype's, which is why Gate E's prototype figure transfers. The bars
    only the prototype defines are item 3 below, and are excluded here by
    `notna() & notna()` rather than ignored."""
    c = FRAMES[name]()
    mod, pro = tf_spec_entropy_64(c), _prototype(c)
    m = mod.notna() & pro.notna()
    assert bool((mod[m] == pro[m]).all())


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 8, 20, LENGTH, 250])
def test_gate_a_the_prototype_agreement_holds_at_every_length(length):
    for name in FIRING:
        c = FRAMES[name]()
        mod = tf_spec_entropy_64(c, length=length)
        pro = _prototype(c, length=length)
        m = mod.notna() & pro.notna()
        assert int(m.sum()) > 0
        assert bool((mod[m] == pro[m]).all())


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("length", [8, 16])
def test_gate_a_the_formula_by_scalar_loops_agrees(name, length):
    """A `cmath` DFT and `math.log2`, sharing no numpy operation with the
    module. Only a TOLERANCE: an FFT sums the taps in a different order from a
    naive DFT, so the two cannot be bit-equal. The band is 1e-10, four orders
    above the 6.476e-15 §A2's 200-bar frames print at `length` 64 -- these are
    the same 200 bars at `length` 8 and 16 -- because the digit moves with the
    CPU's kernels."""
    c = FRAMES[name](n=200)
    mod, orc = (tf_spec_entropy_64(c, length=length),
                _loop_oracle(c, length=length))
    assert bool((mod.isna() == orc.isna()).all())
    assert int((mod.notna()).sum()) > 0
    assert _rel(mod, orc) < 1e-10


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_same_quantity_through_the_complex_fft_agrees(name):
    """`np.fft.fft` keeping bins 1..32 instead of `np.fft.rfft`: a different
    numpy code path for the same transform. Tolerance, for the same reason."""
    c = FRAMES[name]()
    mod, orc = tf_spec_entropy_64(c), _complex_fft_oracle(c)
    assert bool((mod.isna() == orc.isna()).all())
    if name in EMPTY:                      # no shared bar to compare
        assert int(mod.notna().sum()) == 0
    else:
        assert _rel(mod, orc) < 1e-10


def test_the_normaliser_is_the_entropy_of_a_flat_spectrum():
    """`log2(length // 2)` -- `log2` of the number of bins kept AFTER the DC
    bin is dropped, which is the entropy of a perfectly flat spectrum and so
    the only divisor that puts the ceiling at exactly 1.

    Two limbs, because the first alone proves nothing about this module: the
    bin count is checked against the shape `rfft` actually returns rather than
    a retyped constant, and then a MUTANT that divides by `log2(length)`
    instead is required to move the column by exactly the ratio of the two
    logs. Without the mutant limb this test passed unchanged when the module's
    divisor was wrong (round 2 finding)."""
    for length in (MIN_LENGTH, 5, 8, 20, LENGTH, 250):
        bins = np.fft.rfft(np.zeros(length)).size - 1
        assert bins == length // 2
        assert bins >= 2, "log2(bins) would be 0 or undefined"

    wrong = _mutant(NORM_LINE, "        norm = np.log2(length)")
    c = _walk()
    base, other = tf_spec_entropy_64(c), wrong(c)
    assert not _bit_equal(base, other), "mutant is not live"
    m = base.notna() & other.notna()
    expected = math.log2(LENGTH) / math.log2(LENGTH // 2)
    assert float(((base[m] / other[m]) - expected).abs().max()) < 1e-12


def test_the_source_library_is_not_readable_here():
    """⚠ Gate A does NOT read TSFEL's own code: the package is not installed
    in this worktree and web access is unavailable, so the only source text is
    the one line issue #111 quotes. This test makes that limitation fail
    loudly if the environment ever changes, instead of leaving a docstring
    that quietly became wrong."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfel")


# ----------------------------------------------- 3. the two divergences


@pytest.mark.parametrize("name", FIRING)
def test_the_prototype_reads_minus_zero_where_this_module_reads_nan(name):
    """A window holding a non-finite return. `pct_change` makes bar 0 NaN, so
    every frame has exactly one -- the warm-up bar `length - 1`. The
    prototype's `np.where(s == 0, np.nan, s)` does not reach it: the NaN is
    swallowed by `p > 0` and the window comes out as -0.0."""
    c = FRAMES[name]()
    mod, pro = tf_spec_entropy_64(c), _prototype(c)
    only_pro = pro.notna() & mod.isna()
    assert int(only_pro.sum()) == 1
    assert int(np.flatnonzero(only_pro.to_numpy())[0]) == LENGTH - 1
    assert float(pro[only_pro].iloc[0]) == 0.0
    assert math.copysign(1.0, float(pro[only_pro].iloc[0])) == -1.0


@pytest.mark.parametrize("name", EMPTY)
def test_a_window_with_no_spectrum_is_nan_here_and_minus_zero_there(name):
    """`length` EQUAL returns -- a flat price, or an exact x2 ramp -- leave the
    centred window identically zero, so there is no spectrum to take the
    entropy of. This module says so; the prototype reads -0.0 on every one of
    those bars."""
    c = FRAMES[name]()
    mod, pro = tf_spec_entropy_64(c), _prototype(c)
    assert int(mod.notna().sum()) == 0
    fired = pro.dropna()
    assert len(fired) > 0
    assert bool((fired == 0.0).all())


def test_an_almost_constant_return_is_a_reading_and_not_a_gap():
    """The guard is EXACT equality of the centred window to zero, not a
    dispersion floor. A ramp whose step is not a power of two has returns that
    differ in their last bits, and the column fires on it -- which is why the
    `ramp` frame above uses x2."""
    c = _series(LEVEL * 1.001 ** np.arange(N))
    v = tf_spec_entropy_64(c)
    assert int(v.notna().sum()) == N - LENGTH


# ------------------------------------------------------------------ 4. Gate B


@pytest.mark.parametrize("name", FIRING)
def test_the_module_reads_no_future_bar(name):
    """Perturb every bar from `j` onward, two ways, and the prefix below `j`
    must not move by a bit."""
    c = FRAMES[name]()
    assert sum(_caught_at(tf_spec_entropy_64, c, j) for j in OFFSETS) == 0


@pytest.mark.parametrize("name", FIRING)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    """Weaker than the sweep and kept because it is the check a reader
    expects: the first `j` bars of the column computed on the whole frame must
    equal the column computed on the first `j` bars alone."""
    c = FRAMES[name]()
    full = tf_spec_entropy_64(c)
    for j in OFFSETS:
        assert _bit_equal(full.iloc[:j], tf_spec_entropy_64(c.iloc[:j]))


@pytest.mark.parametrize("label", list(LOOKAHEAD_MUTANTS))
@pytest.mark.parametrize("name", FIRING)
def test_a_look_ahead_mutant_is_live_and_caught_at_every_offset(label, name):
    """Each mutant must first CHANGE the column (a dead mutant proves
    nothing), then be caught by the same sweep the real module survives."""
    fn = _mutant(*LOOKAHEAD_MUTANTS[label])
    c = FRAMES[name]()
    assert not _bit_equal(fn(c), tf_spec_entropy_64(c)), "mutant is not live"
    assert sum(_caught_at(fn, c, j) for j in OFFSETS) == len(OFFSETS)


@pytest.mark.parametrize("name", FIRING)
def test_the_mask_mutant_is_live_and_the_blind_sweep_misses_it(name):
    """⚠ The finding, not a weakness of the mutant. `np.roll(ok, -1)`
    back-dates the GAP mask by one bar; the bars it moves do not depend on the
    future, so the sweep returns 0 of 8 -- exactly what CLAUDE.md's Gate B
    says prefix work cannot see. It is pinned by the next test instead."""
    fn = _mutant(*MASK_MUTANT)
    c = FRAMES[name]()
    assert not _bit_equal(fn(c), tf_spec_entropy_64(c)), "mutant is not live"
    assert sum(_caught_at(fn, c, j) for j in OFFSETS) == 0


@pytest.mark.parametrize("at", [100, 200, 300])
def test_a_mutant_that_back_dates_the_gap_mask_is_caught_by_a_planted_nan(at):
    """Plant one NaN close and read where the gap lands. The real module
    blanks the windows that CONTAIN the bad return; the mutant blanks the set
    one bar earlier, which is the definition of back-dating."""
    fn = _mutant(*MASK_MUTANT)
    c = _walk()
    c.iloc[at] = np.nan
    real = {int(i) for i in np.flatnonzero(
        tf_spec_entropy_64(c).isna().to_numpy()) if i >= LENGTH}
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
    assert _bit_equal(tf_spec_entropy_64(c), tf_spec_entropy_64(c * factor))


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 8, 20, LENGTH, 250])
def test_scale_by_eight_is_bit_identical_at_every_length(length):
    for name in FIRING:
        c = FRAMES[name]()
        assert _bit_equal(tf_spec_entropy_64(c, length=length),
                          tf_spec_entropy_64(c * 8.0, length=length))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """Not bit-equal, and the test says so by using a band: the division
    rounds differently, which moves the returns in their last bits. Measured
    at most 3.090e-14 relative on 1,500-bar frames (§D)."""
    c = FRAMES[name]()
    base, scaled = tf_spec_entropy_64(c), tf_spec_entropy_64(c * factor)
    assert bool((base.isna() == scaled.isna()).all())
    assert _rel(scaled, base) < 1e-9


@pytest.mark.parametrize("shift", [1.0, 50.0, 1e6])
def test_scale_a_level_shift_does_move_the_column(shift):
    """A level shift is NOT a rescale -- it changes the returns -- so the
    column must move. Without this, every bit-identity above would also pass
    on a constant column."""
    c = _walk()
    a, b = tf_spec_entropy_64(c), tf_spec_entropy_64(c + shift)
    assert _differs(a, b) > 0
    assert _abs(a, b) > 0.0


@pytest.mark.parametrize("name", FIRING)
def test_scale_fires_strictly_between_zero_and_n(name):
    c = FRAMES[name]()
    v = tf_spec_entropy_64(c)
    assert 0 < int(v.notna().sum()) < len(v)
    assert int(v.dropna().nunique()) > 1


# ----------------------------------------- 6. what the spectrum throws away


@pytest.mark.parametrize("name", FIRING)
def test_the_row_helper_is_the_modules_arithmetic(name):
    """The precondition the three symmetry tests below rest on. They read
    `_entropy_of_rows`, a copy of the module's arithmetic, because a claim
    about rotating or reversing a WINDOW cannot be made through a close path
    (rebuilding one from altered returns rounds). So the copy is pinned to the
    module here, bit for bit, and the symmetry claims inherit that pin instead
    of inheriting a docstring's word."""
    c = FRAMES[name]()
    direct = _place(c, LENGTH, _entropy_of_rows(_windows(c)))
    assert _bit_equal(direct, tf_spec_entropy_64(c))


def _random_rows(seed=404, how_many=500):
    rng = np.random.default_rng(seed)
    r = _walk().pct_change(fill_method=None).to_numpy()[1:]
    W = sliding_window_view(r, LENGTH)
    return rng, W[rng.integers(0, W.shape[0], how_many)]


def test_it_is_blind_to_phase_rotation_and_to_time_reversal():
    """`abs(rfft(x))` is unchanged by a circular rotation and by reversing the
    window, so the column cannot say WHERE in the window a pattern sat or
    which way round it ran. Asserted as a tolerance and not as bit-equality:
    the FFT takes a different numeric path on a rotated input, which measures
    as at most 4.441e-16 over 2,000 windows (§L5)."""
    rng, rows = _random_rows()
    base = _entropy_of_rows(rows)
    shifts = rng.integers(1, LENGTH, rows.shape[0])
    rotated = _entropy_of_rows(
        np.array([np.roll(w, int(k)) for w, k in zip(rows, shifts)]))
    reversed_ = _entropy_of_rows(rows[:, ::-1])
    assert np.isfinite(base).all()
    assert float(np.abs(rotated - base).max()) < 1e-14
    assert float(np.abs(reversed_ - base).max()) < 1e-14


def test_but_it_is_not_order_blind_a_permutation_moves_it():
    """The counterpart, so "phase-blind" cannot be read as "order-blind": a
    general permutation is not an `abs(rfft(.))` symmetry and moves the column
    by up to 0.135 (§L5)."""
    rng, rows = _random_rows()
    base = _entropy_of_rows(rows)
    permuted = _entropy_of_rows(np.array([rng.permutation(w) for w in rows]))
    assert float(np.abs(permuted - base).max()) > 1e-3


def test_it_is_blind_to_the_sign_and_the_size_of_the_returns():
    """Scaling the whole window by an exact binary factor, or by -1, leaves
    every normalised probability unchanged, so the value is bit-identical.
    That is why this is not a volatility measure."""
    _, rows = _random_rows()
    base = _entropy_of_rows(rows)
    for factor in (-1.0, 0.5, 2.0):
        assert bool((_entropy_of_rows(rows * factor) == base).all())


# --------------------------------------------------------- 7. the leakage


def test_a_cycle_off_the_bin_grid_reads_far_more_entropy_than_on_it():
    """⚠ The column's main artefact, asserted as an ORDERING rather than as a
    value. TSFEL applies no window function and neither does this port, so a
    cycle whose period does not divide `length` leaks across the bins and
    reads as noise: measured mean 0.4303 at bin 8.5 and 0.2429 at bin 8.25
    against ~1e-27 at bin 8 (§L2)."""
    on = tf_spec_entropy_64(_sine(8.0)).dropna()
    quarter = tf_spec_entropy_64(_sine(8.25)).dropna()
    half = tf_spec_entropy_64(_sine(8.5)).dropna()
    assert float(on.max()) < 1e-20
    assert float(quarter.min()) > 0.1
    assert float(half.min()) > float(quarter.max())


# ---------------------------------------------------------- 8. the budget


@pytest.mark.parametrize("budget", [1, 64, 999, 10 ** 9])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every chunk is an independent run of rows, so the budget can only move
    the peak memory, never a value."""
    mod = importlib.import_module("pandas_ta.statistics.tf_spec_entropy_64")
    c = _walk()
    base = tf_spec_entropy_64(c)
    old = mod.CHUNK_VALUES
    try:
        mod.CHUNK_VALUES = budget
        assert _bit_equal(base, mod.tf_spec_entropy_64(c))
    finally:
        mod.CHUNK_VALUES = old


# ------------------------------------------------- warm-up, guards, wiring


@pytest.mark.parametrize("name", FIRING)
def test_the_warm_up_is_length_bars(name):
    """`length` returns need `length + 1` closes, so the first reading is at
    bar `length` and not at `length - 1`."""
    v = tf_spec_entropy_64(FRAMES[name]())
    assert bool(v.iloc[:LENGTH].isna().all())
    assert not math.isnan(float(v.iloc[LENGTH]))


def test_the_shortest_input_that_produces_a_value():
    assert int(tf_spec_entropy_64(_walk(n=LENGTH + 1)).notna().sum()) == 1
    assert tf_spec_entropy_64(_walk(n=LENGTH)) is None


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, 1e-310])
@pytest.mark.parametrize("at", [100, 200, 300])
def test_a_bad_close_empties_a_bounded_run_and_moves_nothing_earlier(value,
                                                                     at):
    """A close that is NaN, infinite or zero makes one or two returns
    non-finite, which empties at most `length + 1` windows -- and never a bar
    before the one it sits on."""
    base = _walk()
    c = base.copy()
    c.iloc[at] = value
    a, b = tf_spec_entropy_64(base), tf_spec_entropy_64(c)
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
    c.iloc[200] = -1.0
    v = tf_spec_entropy_64(c)
    assert int(v.notna().sum()) == int(tf_spec_entropy_64(base).notna().sum())
    assert _differs(v, tf_spec_entropy_64(base)) > 0


@pytest.mark.parametrize("name", NAMES)
def test_no_floating_point_error_is_reachable(name):
    """Under `errstate(all="raise")`, which is why the module folds +-inf into
    NaN before the centring: `inf - inf` is the one input that raises."""
    c = FRAMES[name]()
    with np.errstate(all="raise"):
        tf_spec_entropy_64(c)


@pytest.mark.parametrize("arr", ["all-nan", "all-zero", "all-negative"])
def test_a_degenerate_frame_neither_raises_nor_invents_a_value(arr):
    data = {"all-nan": np.full(N, np.nan), "all-zero": np.zeros(N),
            "all-negative": -np.abs(_walk().to_numpy())}[arr]
    with np.errstate(all="raise"):
        v = tf_spec_entropy_64(_series(data))
    if arr == "all-negative":
        assert int(v.notna().sum()) > 0
    else:
        assert int(v.notna().sum()) == 0


def test_the_input_series_is_not_mutated():
    c = _walk()
    before = c.to_numpy().copy()
    tf_spec_entropy_64(c)
    assert bool((c.to_numpy() == before).all())


@pytest.mark.parametrize("length", [None, 0, 1, 2, 3])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """At `length` 2 or 3 the normaliser `log2(length // 2)` is `log2(1) = 0`
    and every window would be 0/0, so the module refuses the value instead of
    emitting a column of NaN."""
    assert tf_spec_entropy_64(_walk(), length=length).name == "TFSPECENT_64"
    assert tf_spec_entropy_64(_walk(), length=MIN_LENGTH).name == \
        f"TFSPECENT_{MIN_LENGTH}"


def test_offset_and_fillna():
    c = _walk()
    base = tf_spec_entropy_64(c)
    import pandas as pd
    pd.testing.assert_series_equal(tf_spec_entropy_64(c, offset=1),
                                   base.shift(1))
    assert int(tf_spec_entropy_64(c, fillna=0).isna().sum()) == 0


def test_the_five_wiring_touch_points():
    """Module, package export, `Category`, accessor, and this file."""
    from pandas_ta.statistics import tf_spec_entropy_64 as exported
    assert exported is tf_spec_entropy_64
    assert "tf_spec_entropy_64" in ta.Category["statistics"]

    c = _walk()
    df = DataFrame({"close": c})
    out = df.ta.tf_spec_entropy_64()
    assert out.name == "TFSPECENT_64"
    assert out.category == "statistics"
    import pandas as pd
    pd.testing.assert_series_equal(out, tf_spec_entropy_64(c))
    assert df.ta.tf_spec_entropy_64(length=20).name == "TFSPECENT_20"


def test_the_docstring_first_paragraph_survives_the_dictionary_cut():
    """CLAUDE.md sends a reader to `docs/IndicatorDictionary.md` first, and
    the generator truncates the first paragraph. The cut is NOT 150
    characters: it is `d[:150].rsplit(" ", 1)[0]`, which drops the trailing
    word whole. Measured slack at the time of writing: 12 characters
    (`python docs/measure_tf_spec_entropy_64.py W`)."""
    desc = _generator_desc()
    body = " ".join(tf_spec_entropy_64.__doc__.split("\n\n")[1].split())
    assert not desc({"desc": body}).endswith("…")
    assert desc({"desc": body}) == body


def test_the_gate_e_row_is_owed_and_not_yet_recorded():
    """⚠ Gate E is run by issue-solver AFTER this session, so
    `docs/gate_e_ledger.csv` carries no row for this indicator and
    `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
    fails locally (it is a skip in CI, which sets `GATE_E_PENDING_OK=1`).
    That is the expected state of this commit, and this test is the thing the
    receipt session replaces with one pinning the recorded row's identity."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "tf_spec_entropy_64"]
    assert rows == []
