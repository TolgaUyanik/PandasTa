# -*- coding: utf-8 -*-
"""TF-IQR-RET-60: `tf_iqr_ret_60`, the interquartile range of 60 simple
returns -- how wide the middle half of the last 60 daily returns is
(PandasTa issue #117).

    r         = close / close.shift(1) - 1
    s         = the window's 60 returns, SORTED
    TFIQRRET  = (s[44] + 0.25*(s[45] - s[44]))
                - (s[14] + 0.75*(s[15] - s[14]))

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A in three steps, and all three are BIT-equality.** TSFEL is not
   installed in this worktree and web access is unavailable, so the source
   is an attribution and not an oracle
   (`test_the_source_library_is_not_installed_here` records that, so the
   claim cannot rot into "checked against TSFEL"). What IS checkable is
   pinned:

   * pandas' own `roll_quantile` retyped from its documented behaviour --
     sort the window, take the two order statistics around `q * (n - 1)`,
     blend them `vlow + (vhigh - vlow) * frac`, subtract -- sharing no code
     with the module: bit-equal on **1,440 of 1,440** bars of each of ten
     1,500-bar frames, and at `length` 2, 5, 20, 21 and 250;
   * the SOURCE's spelling, `np.percentile(w, 75) - np.percentile(w, 25)`
     applied window by window: also bit-equal on 1,440 of 1,440 of each of
     the ten. ⚠ That is NOT what `ts_q05_60` found, and the reason is
     pinned too: numpy's `_lerp` takes the `b - (b - a)*(1 - t)` branch
     only for `t >= 0.5`, so q0.25 (frac 0.75) takes it and q0.75 (frac
     0.25) does not -- q0.75's spelling IS pandas' already -- and q0.25
     still agrees bit-for-bit SINGLY, so the equality is per quantile and
     not a cancellation in the difference. Four frames here, all ten plus
     five other lengths in the script (28,800 + 14,404 readings).
     ⚠ A measurement, not a theorem: `docs/measure_tf_iqr_ret_60.py A2`
     finds the two ALGEBRAIC FORMS differing on 16 of 20,000 random
     60-draw windows at q0.25 and 17 at q0.75, and on 0 of the 14,400
     windows the ten frames produce. The pandas-versus-numpy count is 16
     and 0, because at q0.75 numpy takes the form that IS pandas';
   * an EXACT rational oracle -- every return is a double, so a rational;
     the sort is exact and both blends and the subtraction are done in
     `fractions.Fraction`, rounded once at the end. Bit-equal on 1,440 of
     1,440 bars of each of four frames here (all ten in the script), max
     0.00 ulp -- where `ts_q05_60` is one ulp out on the same machinery
     (that figure is `docs/TsQ0560Measured.md`'s, not re-measured here).
     `Fraction(0.25)` is `1/4` and `Fraction(0.75)` is `3/4`, which is why.

2. **That the column reads FOUR of the 60 returns and NOTHING else.** `q *
   (length - 1)` is 44.25 and 14.75, so the value is a fixed blend of
   ranks 15, 16, 45 and 46 counting up from the smallest. Shown rather
   than asserted: pushing the other 56 arbitrarily far away while keeping
   each one's rank leaves the value BIT-identical and equal to the closed
   form. Two consequences a consumer must know: it is a MIDDLE reading
   that cannot see the tails at all, and its resolution is high rather
   than coarse -- 714 to 896 distinct values over 1,440 bars on each of
   the nine frames other than `two-point`, against `TS_Q05_60`'s 149 on
   the same walk builder and seed (that figure is
   `docs/TsQ0560Measured.md`'s, not re-measured here).

3. **That it is SIGN-BLIND.** `q75(-x) = -q25(x)`, so negating every
   return leaves the statistic unchanged: a crash and a melt-up of the
   same shape read the same value. Measured on a Student-t(3) frame and
   its exact negation (Spearman 1.000000, max |difference| 5.829e-16), and
   on 300 windows of exact doubles (298 of 300 bit-equal, worst
   2.220e-16). This is the disclosure a reader of `ts_q05_60` -- a signed
   tail statistic on the same 60 returns -- will not expect.

4. **Gate B, by mutant, and an honest account of the one the blind sweep
   cannot catch.** Five mutants are live and caught 24 to 35 of 35
   offsets, where the real module leaks **0 of 35** on each of three
   frames and at `length` 2, 5 and 250.
   ⚠ The sixth is the one worth reading. Shifting the NaN mask's own index
   by one bar makes bar T's mask read whether bar T+1's return is finite --
   a real look-ahead -- and on a clean frame it is not merely invisible but
   **DEAD**: every return there is finite, so the shifted mask admits the
   same bars and the output is bit-identical. What it can move is DERIVED:
   a bad close at J spoils the returns at J and J+1, so the shifted mask
   drops the return at J-1, and the window ending at **J-1** is the only
   one before J that holds it without also holding J. A frame with a bad
   close at every offset catches the mutant **12 of 12** and moves exactly
   bar J-1.

5. **Gate D, which is bit-identity BY CONSTRUCTION, against a level shift
   that is NOT invariant.** Every input is a price ratio and `8a / 8b` is
   the same double as `a / b`, so a x2^k rescale cannot move the sort order
   OR the blends: 1,440 of 1,440 bars on each of ten frames at x8 and x64,
   at `length` 2 / 5 / 20 / 250, and at price levels 1e-6, 1e+6 and 1e+100.
   The check is not vacuous: `close + 1` moves every fired bar.
   ⚠ x10 / x3.7 / x0.1 / x1.0000001 are NOT bit-identical and are held to
   masks plus a relative tolerance (measured max 2.672e-14 across both
   numpy dispatches, asserted at 1e-12). On the
   TWO-POINT frame their Spearman is 0.34 .. 0.74, which is rounding and
   not a scale failure -- the column there is 5 doubles spanning 2.220e-16
   around 0.02 -- so that frame is asserted on the relative difference
   only.

6. **The guards, each with what it costs and what it buys.** A close that
   is NaN, infinite, zero, negative or subnormal empties the 61 windows it
   sits in and NOTHING earlier (30 (value, position) pairs, 0 earlier bars
   moved in all 30); an overflowing ratio empties 60. ⚠ An UNDERFLOWING
   ratio does not, and must not: 1e308 followed by 1e-300 gives exactly
   -1.0, the correctly rounded return. ⚠ And the module's own
   `r.where(np.isfinite(r))` line is DEFENCE IN DEPTH, measured rather
   than assumed: pandas' `rolling.quantile` already blanks a whole window
   holding one infinity, at both quartiles, so a mutant with that line
   deleted is bit-identical on a clean walk, an overflowing frame and the
   1e308 cycle. Two tests pin that, and it is also the mechanism behind the
   sixth mutant of item 4 being dead. ⚠ There is NO dispersion floor,
   unlike `ts_kurt_60` / `ts_medskew_20` / `ts_above_mean_20`, and that is
   a decision this file pins with the exact oracle: a flat frame reads 0.0
   on 240 windows, a 1%-a-bar ladder two values on 240 under the default
   numpy dispatch and one (exactly 0.0) with AVX off, and a quiet 1e-6
   frame 289 values on 540, all of them at 0.00 ulp. The siblings' absolute
   4096-ulp floor would empty 480 of those 1,020 honest windows and 0
   dishonest ones.

7. **The bounds, as a measurement and not a proof.** Non-negative on every
   fired bar of all ten frames and on 2,400 windows built for the only
   collapse in which the two blends could round into each other; exactly
   0.0 on a flat frame; UNBOUNDED above, with 1e+308 reachable on a legal
   frame. The subtraction cannot overflow, because a return is greater
   than -1 whenever both closes are positive and normal.

8. **What the column IS, which is the thing most likely to be misread.** It
   is VOLATILITY: +0.0735 .. +0.9511 against `NATR_60` on ten frames
   (per-frame median 0.5641, pooled 0.7858), so a BIG value means a NOISY
   window. ⚠ It nearly mirrors `ts_q05_60` where volatility is the only
   signal (-0.9364 on the `vol-cycle` frame), and that column was merged
   three weeks AFTER the 2026-10-24 screen that produced this issue, so
   Gate E's comparator set may not carry it: per-frame median |rho|
   0.3246, pooled -0.6238, and the receipt keeps an OWED item with a
   revert rule. It is NOT the spread of the price LEVEL (0.0620 on a
   walk) and it is a slow state (lag-1 autocorrelation 0.9718, lag-60
   0.1849; one bar moves exactly 60 bars).

9. **That it IS the screen prototype**: bit-equal on 1,440 of 1,440 bars of
   each of ten frames with IDENTICAL masks, parting company only where a
   guard fires.

10. **The recorded Gate E row.** Run `is117-tf_iqr_ret_60-7149d122`,
    measured 2026-11-16: SHIP, pooled |rho| 0.6730 vs `natr` over 393,509
    bars, per-frame max median 0.6565, 89 frames, 687 comparators.
    `test_the_gate_e_row_is_recorded_and_ships` pins the row's IDENTITY and
    its BAND rather than its last digits, and reads its `non_nan` /
    `non_zero` / `pooled_bars` as Gate C's real-data limb. The
    `ts_q05_60` overlap on those 89 frames is STILL owed, and
    `test_the_ts_q05_60_overlap_check_is_owed_from_the_gate_e_run` keeps
    its revert rule in the receipt so the SHIP row cannot settle it.

Numbers come from `python docs/measure_tf_iqr_ret_60.py`; the receipt is
`docs/TfIqrRet60Measured.md`.
Counts that depend on the last bits of a generated frame carry a band or a
tolerance; the structural facts are pinned exactly.
"""
import csv
import importlib
import re
import types
import warnings
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from pandas import Series

from .context import pandas_ta  # noqa: F401

from pandas_ta.statistics.quantile import quantile
from pandas_ta.statistics.tf_iqr_ret_60 import (
    MIN_LENGTH,
    Q_HIGH,
    Q_LOW,
    tf_iqr_ret_60,
)
from pandas_ta.statistics.ts_q05_60 import ts_q05_60
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.ui import ui

LENGTH = 60
N = 1500
FIRED = N - LENGTH          # `length` RETURNS, so `length + 1` closes
ROOT = Path(__file__).resolve().parents[1]

_REAL = importlib.import_module("pandas_ta.statistics.tf_iqr_ret_60")


# ------------------------------------------------------------------ frames
# The same builders and seeds as `docs/measure_tf_iqr_ret_60.py`, so a
# figure quoted from that script is a figure about these frames.


def _walk(n=N, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=N, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _ar1(n=N, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=N, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=N, seed=4, sigma=0.01):
    """Every return is +-1%, so the window holds 2 distinct values. The
    Gate D tie frame: the column takes 5 doubles spanning 2.2e-16."""
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


def _vol_cycle(n=N, seed=19, lo=0.004, hi=0.03, period=250):
    """Volatility that breathes, and nothing else moving. Built so the
    overlap sections can read this column's CEILING against every other
    volatility measure -- not as a typical frame."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    sigma = lo + 0.5 * (hi - lo) * (1.0 + np.sin(2 * np.pi * t / period))
    return _from_returns(np.clip(sigma * rng.standard_normal(n), -0.5, 0.5))


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A constant-rate rise. Its return is mathematically constant and
    float64 does not reproduce it exactly, so the column reads a 5.6e-17
    spread where the mathematics says 0."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _quiet(n=600, price=100.0, step=1e-6, seed=13):
    """Honest but tiny returns: 1e-6 a bar."""
    rng = np.random.default_rng(seed)
    return _from_returns(step * rng.standard_normal(n)) * (price / 100.0)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
    "vol-cycle": _vol_cycle,
}
#: The frames the EXACT oracle runs on here. It is a Python loop over
#: `Fraction`, so it is slow; `docs/measure_tf_iqr_ret_60.py` (A3) runs all
#: ten and finds the same bit-equality.
EXACT_FRAMES = ["walk", "tick-rounded", "heavy-tailed", "two-point"]
TIE_FRAME = "two-point"
#: `vol-cycle` is constructed so volatility is the ONLY signal, which is
#: exactly when every volatility measure agrees with every other. It is
#: excluded where a test asserts a CEILING on an overlap, and named in the
#: test that reads its exceptional value.
ORDINARY = [f for f in FRAMES if f != "vol-cycle"]


# ----------------------------------------------------------------- helpers


def _ret(close):
    return close / close.shift(1) - 1.0


def _ohlc(close, band=0.004):
    """Deterministic SYNTHETIC high/low for the neighbours that need them."""
    return close * (1.0 + band), close * (1.0 - band)


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    d = float((a[m] - b[m]).abs().max()) if int(m.sum()) else 0.0
    return masks, int(m.sum()), int((a[m] == b[m]).sum()), d


def _max_rel(a, b):
    m = a.notna() & b.notna() & (b != 0.0)
    if not int(m.sum()):
        return 0.0
    return float(((a[m] - b[m]).abs() / b[m].abs()).max())


def _max_ulps(a, b):
    """max |a - b| in units of the last place of `b`."""
    m = a.notna() & b.notna()
    y = b[m].to_numpy()
    ulp = np.abs(np.nextafter(y, np.inf) - y)
    ulp = np.where(ulp == 0.0, np.finfo(float).tiny, ulp)
    return float((np.abs(a[m].to_numpy() - y) / ulp).max())


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone -- the shape
    `tests/test_tf_higuchi_30.py` uses.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test, and getting at it needs `docs/` on `sys.path`,
    which would then shadow every later import in the pytest session with
    one of the scripts in that directory. Re-typing the cut here would pin
    a COPY of the rule rather than the rule, so this compiles the
    generator's actual function and a change to its cut reaches this
    test."""
    import ast
    path = ROOT / "docs" / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


# ------------------------------------------------------------- the oracles


def _pandas_spelling(close, length=LENGTH, q_lo=Q_LOW, q_hi=Q_HIGH):
    """pandas' `roll_quantile` with `interpolation='linear'`, retyped from
    its documented behaviour and sharing no code with the module."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i_hi, i_lo = q_hi * (length - 1), q_lo * (length - 1)
    hi_k, hi_f = int(i_hi), i_hi % 1
    lo_k, lo_f = int(i_lo), i_lo % 1
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        a, b = s[hi_k], s[min(hi_k + 1, length - 1)]
        hi = a + (b - a) * hi_f
        a, b = s[lo_k], s[min(lo_k + 1, length - 1)]
        lo = a + (b - a) * lo_f
        out[t] = hi - lo
    return Series(out, index=close.index)


def _source_windowed(close, length=LENGTH, q_lo=Q_LOW, q_hi=Q_HIGH):
    """TSFEL's `interq_range`: `np.percentile(signal, 75) -
    np.percentile(signal, 25)`, over the trailing `length` returns, one
    window at a time."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        out[t] = (np.percentile(w, 100.0 * q_hi)
                  - np.percentile(w, 100.0 * q_lo))
    return Series(out, index=close.index)


def _single_quartile_numpy(close, q, length=LENGTH):
    """ONE quartile from `np.percentile`, so the per-quantile comparison
    can tell a cancellation from a real agreement."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if np.isfinite(w).all():
            out[t] = np.percentile(w, 100.0 * q)
    return Series(out, index=close.index)


def _exact(close, length=LENGTH, q_lo=None, q_hi=None):
    """The correctly rounded answer: every return is a double, so a
    rational; the sort is exact, and both blends and the subtraction are
    done in `Fraction` and rounded exactly ONCE, at the end."""
    qh = Fraction(Q_HIGH) if q_hi is None else q_hi
    ql = Fraction(Q_LOW) if q_lo is None else q_lo
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i_hi, i_lo = qh * (length - 1), ql * (length - 1)
    hi_k, hi_f = int(i_hi), i_hi - int(i_hi)
    lo_k, lo_f = int(i_lo), i_lo - int(i_lo)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = sorted(Fraction(float(v)) for v in w)
        hi = s[hi_k] + (s[min(hi_k + 1, length - 1)] - s[hi_k]) * hi_f
        lo = s[lo_k] + (s[min(lo_k + 1, length - 1)] - s[lo_k]) * lo_f
        out[t] = float(hi - lo)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `tf_iqr_ret_60`,
    retyped (that tree is the owner's and gitignored, so it is copied
    rather than imported):
    `ret(c).rolling(60).quantile(0.75) - ret(c).rolling(60).quantile(0.25)`
    with `ret(c) = c / c.shift(1) - 1`. No guards of any kind."""
    r = close / close.shift(1) - 1.0
    return r.rolling(length).quantile(0.75) - r.rolling(length).quantile(0.25)


# -------------------------------------------------- Gate A: the attribution


def test_the_source_library_is_not_installed_here():
    """"TSFEL (BSD-3-Clause), `features.py interq_range`" is an
    ATTRIBUTION. TSFEL is not importable in this worktree and web access is
    unavailable, so no test in this file compares against it; what Gate A
    checks is the published definition of `interq_range` -- `np.percentile(
    signal, 75) - np.percentile(signal, 25)` -- plus the issue's own line.
    This test exists so that the distinction cannot quietly rot."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfel")


# -------------------------------------------------------- Gate A1: the bits


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_a1_bit_equal_to_pandas_own_spelling_retyped(frame):
    """The strongest form Gate A can take on a column with no closed form:
    an independent reimplementation of the arithmetic pandas documents,
    sharing no code with the module, agreeing to the LAST BIT. Measured
    1,440 of 1,440 bars on each of the ten frames."""
    close = FRAMES[frame]()
    masks, shared, same, d = _agree(tf_iqr_ret_60(close),
                                    _pandas_spelling(close))
    assert masks
    assert shared == FIRED
    assert same == shared, (frame, same, shared, d)


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 20, 21, 250])
def test_gate_a1_bit_equal_at_other_lengths(length):
    """`length` 21 and 5 are the cases where both fractions are 0.0, so the
    column reads two returns exactly rather than blending four; 2 is the
    minimum."""
    close = _walk()
    masks, shared, same, d = _agree(tf_iqr_ret_60(close, length=length),
                                    _pandas_spelling(close, length=length))
    assert masks
    assert shared == N - length
    assert same == shared, (length, same, shared, d)


# ------------------------------------------------------- Gate A2: the source


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_a2_the_source_spelling_is_bit_equal(frame):
    """TSFEL's own spelling of the statistic, `np.percentile(w, 75) -
    np.percentile(w, 25)`, window by window. ⚠ `ts_q05_60` found pandas and
    numpy ONE ULP apart on the same machinery; here they agree bit for bit,
    and the next test says why that is not luck."""
    close = FRAMES[frame]()
    mod, src = tf_iqr_ret_60(close), _source_windowed(close)
    masks, shared, same, d = _agree(mod, src)
    assert masks
    assert same == shared == FIRED, (frame, same, shared, d)


@pytest.mark.parametrize("frame", EXACT_FRAMES)
@pytest.mark.parametrize("q", [Q_LOW, Q_HIGH])
def test_gate_a2_each_quartile_alone_is_bit_equal_to_numpy(frame, q):
    """Whether the agreement above is PER QUANTILE or a cancellation in the
    difference. numpy's `_lerp` evaluates `b - (b - a)*(1 - t)` for
    `t >= 0.5` and `a + (b - a)*t` below it, so q0.25 (frac 0.75) and
    q0.75 (frac 0.25) take different branches from each other -- and each
    one still matches pandas' rolling quartile to the last bit, singly."""
    close = FRAMES[frame]()
    roll = _ret(close).rolling(LENGTH, min_periods=LENGTH).quantile(q)
    masks, shared, same, d = _agree(roll, _single_quartile_numpy(close, q))
    assert masks
    assert same == shared == FIRED, (frame, q, same, shared, d)


def test_gate_a2_percentile_quantile_and_series_quantile_agree():
    """And the three spellings of the same number are one number, so the
    oracle above is not sensitive to which one the source is read as."""
    rng = np.random.default_rng(5)
    w = rng.normal(0.0, 0.01, LENGTH)
    a = np.percentile(w, 75.0) - np.percentile(w, 25.0)
    b = float(Series(w).quantile(0.75) - Series(w).quantile(0.25))
    c = float(np.quantile(w, 0.75) - np.quantile(w, 0.25))
    assert a == b == c


# -------------------------------------------------------- Gate A3: the exact


@pytest.mark.parametrize("frame", EXACT_FRAMES)
def test_gate_a3_bit_equal_to_the_exact_rational_oracle(frame):
    """The module rounds seven times -- two subtractions, two
    multiplications, two additions and the final difference -- where the
    oracle rounds once, and still lands on the same double on every one of
    1,440 bars of each of four frames (ten in the script). The reason is
    the next test: `0.25` and `0.75` are exact."""
    close = FRAMES[frame]()
    mod, orc = tf_iqr_ret_60(close), _exact(close)
    masks, shared, same, d = _agree(mod, orc)
    assert masks
    assert shared == FIRED
    assert same == shared, (frame, same, shared, d)
    assert _max_ulps(mod, orc) == 0.0


def test_gate_a3_the_quartiles_are_exact_binary_fractions():
    """Where `ts_q05_60`'s `q` is the double nearest 1/20 and so a
    35-digit rational, these two are exact -- which is why Gate A3 is
    bit-equality here and a one-ulp band there."""
    assert Fraction(Q_LOW) == Fraction(1, 4)
    assert Fraction(Q_HIGH) == Fraction(3, 4)
    assert Fraction(0.05) != Fraction(1, 20)


# ------------------------------------- A4: which returns the column reads


def test_a4_only_four_of_the_sixty_returns_are_read():
    """Push the other 56 arbitrarily far away while keeping every rank, and
    the value does not move a bit -- and equals the closed form
    `(s[44] + 0.25*(s[45]-s[44])) - (s[14] + 0.75*(s[15]-s[14]))`."""
    rng = np.random.default_rng(31)
    base = np.sort(rng.normal(0.0, 0.02, LENGTH))
    read = (14, 15, 44, 45)
    spread = base.copy()
    for i in range(LENGTH):
        if i in read:
            continue
        if i < 14:
            spread[i] = base[14] - (14 - i) * 7.0
        elif i > 45:
            spread[i] = base[45] + (i - 45) * 7.0
        else:
            t = (i - 15) / (44 - 15)
            spread[i] = base[15] + t * (base[44] - base[15])
    assert bool(np.all(np.diff(spread) >= 0)), "the ranks must not move"

    closed = ((base[44] + (base[45] - base[44]) * 0.25)
              - (base[14] + (base[15] - base[14]) * 0.75))
    for w in (base, spread):
        s = np.sort(w)
        v = ((s[44] + (s[45] - s[44]) * 0.25)
             - (s[14] + (s[15] - s[14]) * 0.75))
        assert v == closed
        assert float(Series(w).quantile(0.75)
                     - Series(w).quantile(0.25)) == closed


@pytest.mark.parametrize("length,hi,lo", [
    (MIN_LENGTH, (0, 0.75), (0, 0.25)), (5, (3, 0.0), (1, 0.0)),
    (20, (14, 0.25), (4, 0.75)), (21, (15, 0.0), (5, 0.0)),
    (60, (44, 0.25), (14, 0.75)), (250, (186, 0.75), (62, 0.25))])
def test_a4_which_order_statistics_each_length_reads(length, hi, lo):
    """`length` changes WHICH ranks the column sees, not only how smooth it
    is. At 5 and at 21 both fractions are 0.0, so it reads two returns
    exactly."""
    i_hi, i_lo = Q_HIGH * (length - 1), Q_LOW * (length - 1)
    assert (int(i_hi), i_hi % 1) == hi
    assert (int(i_lo), i_lo % 1) == lo


@pytest.mark.parametrize("frame", ORDINARY)
def test_a4_the_resolution_that_follows(frame):
    """Reading FOUR order statistics rather than two makes this a fine
    ordinal where `ts_q05_60` is a coarse one: 700 to 900 distinct values
    over 1,440 bars on an ordinary frame, against that column's ~149.
    ⚠ The tie frame is the exception and is excluded here -- it holds 5
    doubles spanning 2.2e-16, which `test_gate_d_scale_on_the_tie_frame...`
    and `test_the_tie_frame_is_a_handful_of_nearly_equal_doubles` cover."""
    if frame == TIE_FRAME:
        pytest.skip("the tie frame has its own tests")
    v = tf_iqr_ret_60(FRAMES[frame]()).dropna()
    assert len(v) == FIRED
    assert 600 <= len(set(v)) <= 1000, len(set(v))


def test_the_tie_frame_is_a_handful_of_nearly_equal_doubles():
    """And the two-point frame is where four order statistics still cannot
    help: every window's q25 is -0.01 and its q75 is +0.01, so the column
    sits at 0.02 -- 5 doubles spanning 2.2e-16 on this machine under both
    dispatches. Pinned as a BAND on the count and a bound on the span,
    because the last bits move with the CPU.

    ⚠ The band has NO floor above 1. The ladder's own count collapsed from
    2 doubles to 1 with AVX off, so a frame this close to constant could
    collapse to a single double on a third CPU, and the span and the 0.02
    assertions below both still hold there."""
    v = sorted(set(tf_iqr_ret_60(_two_point()).dropna()))
    assert 1 <= len(v) <= 12, len(v)
    assert (v[-1] - v[0]) / v[0] < 1e-12
    assert abs(v[0] - 0.02) < 1e-12


# ------------------------------------------ A5: what the line leaves open


def test_a5_log_returns_do_not_keep_the_ranks_exactly():
    """⚠ The contrast with `ts_q05_60`, which is rank-identical under a log
    return. A quantile commutes with a monotone transform; a DIFFERENCE of
    two quantiles does not, so the ranks move -- measured Spearman 0.999890
    and up to 1.067e-04 apart."""
    close = _walk()
    lr = np.log(close) - np.log(close.shift(1))
    roll = lr.rolling(LENGTH, min_periods=LENGTH)
    log_iqr = roll.quantile(Q_HIGH) - roll.quantile(Q_LOW)
    mod = tf_iqr_ret_60(close)
    rho = _spearman(mod, log_iqr)
    assert 0.99 < rho < 1.0, rho
    assert 1e-5 < float((mod - log_iqr).abs().max()) < 1e-3


@pytest.mark.parametrize("how,lo,hi", [
    ("lower", 0.96, 0.99), ("higher", 0.97, 0.995),
    ("nearest", 0.98, 0.999), ("midpoint", 0.98, 0.999)])
def test_a5_the_interpolation_alternatives_are_different_columns(how, lo, hi):
    close = _walk()
    roll = _ret(close).rolling(LENGTH, min_periods=LENGTH)
    alt = (roll.quantile(Q_HIGH, interpolation=how)
           - roll.quantile(Q_LOW, interpolation=how))
    rho = _spearman(tf_iqr_ret_60(close), alt)
    assert lo < rho < hi, (how, rho)


def test_the_default_interpolation_is_linear():
    """The module does not spell `interpolation` out, because the keyword
    has moved between pandas versions while the default has not. This pins
    that the default IS what the module means."""
    close = _walk()
    roll = _ret(close).rolling(LENGTH, min_periods=LENGTH)
    dflt = roll.quantile(Q_HIGH) - roll.quantile(Q_LOW)
    lin = (roll.quantile(Q_HIGH, interpolation="linear")
           - roll.quantile(Q_LOW, interpolation="linear"))
    assert dflt.equals(lin)
    assert tf_iqr_ret_60(close).equals(dflt.rename("TFIQRRET_60"))


def test_a5_sixty_returns_and_not_sixty_closes():
    """The off-by-one a reader makes: 60 CLOSES is 59 returns, fires at bar
    59 and is a different column (Spearman 0.983863)."""
    close = _walk()
    roll = _ret(close).rolling(LENGTH - 1, min_periods=LENGTH - 1)
    off = roll.quantile(Q_HIGH) - roll.quantile(Q_LOW)
    mod = tf_iqr_ret_60(close)
    assert int(off.notna().to_numpy().argmax()) == LENGTH - 1
    assert int(mod.notna().to_numpy().argmax()) == LENGTH
    assert 0.97 < _spearman(mod, off) < 1.0


def test_a5_it_is_not_the_spread_of_the_price_level():
    """TSFEL applies `interq_range` to the SIGNAL; the screen applies it to
    the daily RETURNS, and the difference is the whole column. The level
    form is a support-resistance band, not a risk reading -- and it is not
    scale-free at all."""
    def level_iqr(c):
        roll = c.rolling(LENGTH, min_periods=LENGTH)
        return roll.quantile(Q_HIGH) - roll.quantile(Q_LOW)

    close = _walk()
    assert abs(_spearman(tf_iqr_ret_60(close), level_iqr(close))) < 0.30
    # The level form scales WITH the price, so it is not a feature at all;
    # this column is bit-identical under the same x8.
    assert np.isclose(float(level_iqr(close * 8.0).dropna().iloc[-1])
                      / float(level_iqr(close).dropna().iloc[-1]), 8.0)
    assert tf_iqr_ret_60(close).equals(tf_iqr_ret_60(close * 8.0))


@pytest.mark.parametrize("ql,qh,lo,hi", [
    (0.10, 0.90, 0.35, 0.62), (0.05, 0.95, 0.05, 0.28),
    (0.20, 0.80, 0.72, 0.90), (0.30, 0.70, 0.75, 0.92),
    (0.40, 0.60, 0.44, 0.68)])
def test_a5_the_other_quartile_pairs_are_different_columns(ql, qh, lo, hi):
    """0.25 and 0.75 are the statistic the source NAMES, and its
    neighbours are genuinely different columns rather than rescalings --
    none of them above the 0.90 line on a walk."""
    close = _walk()
    roll = _ret(close).rolling(LENGTH, min_periods=LENGTH)
    alt = roll.quantile(qh) - roll.quantile(ql)
    rho = _spearman(tf_iqr_ret_60(close), alt)
    assert lo < rho < hi, (ql, qh, rho)
    assert rho < 0.90


# --------------------------------------------------- A6: the prototype


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_a6_the_column_is_the_screen_prototype_bit_for_bit(frame):
    """What the 2026-10-24 screen measured and what this module computes
    are the same arithmetic, so the screen's Gate E figures are expected to
    carry over to the launcher's run on this module."""
    close = FRAMES[frame]()
    masks, shared, same, d = _agree(tf_iqr_ret_60(close), _prototype(close))
    assert masks
    assert same == shared == FIRED, (frame, same, shared, d)


@pytest.mark.parametrize("label,bad,protofires", [
    ("inf", np.inf, 280), ("zero", 0.0, 280), ("subnormal", 1e-310, 280),
    ("negative", -100.0, 340), ("nan", np.nan, 279)])
def test_a6_the_two_part_company_only_on_the_guards(label, bad, protofires):
    """And where they part, the module is the stricter one. A 400-bar walk
    fires 340 bars; a bad close at 200 empties 61 windows here. The
    prototype empties 60 where the bad close leaves ONE infinite return
    (inf / zero / subnormal), 0 where it leaves two finite but meaningless
    ones (negative), and 61 where pandas' own NaN does the work (nan)."""
    close = _walk(400)
    close.iloc[200] = bad
    assert int(tf_iqr_ret_60(close).notna().sum()) == 340 - (LENGTH + 1)
    assert int(_prototype(close).notna().sum()) == protofires, label


def test_a6_a_nan_close_needs_no_guard_and_a_flat_frame_needs_no_floor():
    """The two cases where the module adds nothing: pandas propagates a NaN
    on its own, and a flat frame has a perfectly good interquartile range
    of zero, so both report the same bars and the same values."""
    close = _walk(400)
    close.iloc[200] = np.nan
    assert int(tf_iqr_ret_60(close).notna().sum()) \
        == int(_prototype(close).notna().sum()) == 340 - (LENGTH + 1)

    flat = _flat()
    masks, shared, same, d = _agree(tf_iqr_ret_60(flat), _prototype(flat))
    assert masks and same == shared == 300 - LENGTH and d == 0.0
    assert sorted(set(tf_iqr_ret_60(flat).dropna())) == [0.0]


# ------------------------------------------------------ Gate B: the mutants


BACK_DATE_TWO = ("    iqr = hi - lo", "    iqr = (hi - lo).shift(-2)")
BACK_DATE_FULL = ("    iqr = hi - lo",
                  "    iqr = (hi - lo).shift(-(length - 1))")
FORWARD_RETURN = ("        r = px / px.shift(1) - 1.0",
                  "        r = px.shift(-1) / px - 1.0")
WINDOW_BLOCK = (
    "    hi = r.rolling(length, min_periods=length).quantile(Q_HIGH)\n"
    "    lo = r.rolling(length, min_periods=length).quantile(Q_LOW)")
CENTERED_WINDOW = (
    WINDOW_BLOCK,
    "    hi = r.rolling(length, min_periods=length, center=True)"
    ".quantile(Q_HIGH)\n"
    "    lo = r.rolling(length, min_periods=length, center=True)"
    ".quantile(Q_LOW)")
ROLLED_WINDOW = (
    WINDOW_BLOCK,
    "    rr = r.shift(-(length // 2))\n"
    "    hi = rr.rolling(length, min_periods=length).quantile(Q_HIGH)\n"
    "    lo = rr.rolling(length, min_periods=length).quantile(Q_LOW)")
#: The NaN mask's own index. A real look-ahead -- bar T's mask would read
#: whether bar T+1's return is finite -- and DEAD on a clean frame, where
#: every return but the first is finite. Caught by a designed frame below.
FORWARD_MASK = ("    r = r.where(np.isfinite(r))",
                "    r = r.where(np.isfinite(r).shift(-1, fill_value=True))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "centered_window": CENTERED_WINDOW,
    "rolled_window": ROLLED_WINDOW,
}
OFFSETS = range(120, N, 40)     # 35 offsets, past the 60-bar warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 35 offsets, as BANDS.
#: ⚠ The low ones are a finding and not a defect in the mutant: splicing a
#: different frame in at J moves bar J-2 or J-1 only if it changes one of
#: the window's four read ranks. `back_date_full` shifts by 59 bars and so
#: always lands on a different window; `centered_window` and
#: `rolled_window` move the whole window by 30.
CAUGHT = {
    "back_date_two": {"walk": (26, 35), "tick-rounded": (20, 35),
                      "heavy-tailed": (24, 35)},
    "back_date_full": {"walk": (30, 35), "tick-rounded": (30, 35),
                       "heavy-tailed": (30, 35)},
    "forward_return": {"walk": (18, 35), "tick-rounded": (18, 35),
                       "heavy-tailed": (18, 35)},
    "centered_window": {"walk": (30, 35), "tick-rounded": (30, 35),
                        "heavy-tailed": (30, 35)},
    "rolled_window": {"walk": (30, 35), "tick-rounded": (30, 35),
                      "heavy-tailed": (30, 35)},
}
BAD_OFFSETS = range(120, N, 120)        # 12 offsets, >= length + 1 apart


def _load_mutant(old, new):
    with open(_REAL.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_tf_iqr_ret_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, offsets=OFFSETS, **kwargs):
    """Offsets J at which replacing every close from bar J on moves a bar
    BEFORE J -- which a causal column cannot do."""
    base = fn(close, **kwargs)
    hits = []
    for j in offsets:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p, **kwargs)
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
    before J. 0 of 35 offsets on each of three frames."""
    close, other = PAIRS[frame]
    assert _caught(tf_iqr_ret_60, close, other) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(tf_iqr_ret_60, close, other, length=length) == []
    assert int(tf_iqr_ret_60(close, length=length).notna()
               .to_numpy().argmax()) == length


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column -- otherwise the test proves
    nothing -- and be caught within its measured band."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.tf_iqr_ret_60(close).equals(tf_iqr_ret_60(close))
    hits = _caught(mod.tf_iqr_ret_60, close, other)
    lo, hi = CAUGHT[mutant][frame]
    assert lo <= len(hits) <= hi, (mutant, frame, len(hits))


def test_the_mask_index_mutant_is_dead_on_a_clean_frame():
    """The sixth mutant, and the honest account of what Gate B's sweep
    cannot do here. Shifting the NaN mask by one bar makes bar T's mask read
    bar T+1's return -- a look-ahead. On a clean frame every return but the
    first is finite, so the shifted mask admits the same bars and the mutant
    produces a BIT-IDENTICAL column: not merely invisible to the sweep but
    dead. The test after this one is what gives it something to change."""
    mod = _load_mutant(*FORWARD_MASK)
    for frame, (close, other) in sorted(PAIRS.items()):
        assert mod.tf_iqr_ret_60(close).equals(tf_iqr_ret_60(close)), frame
        assert _caught(mod.tf_iqr_ret_60, close, other) == [], frame


def _bad_close_frame(seed=23):
    """The DESIGNED probe: a walk with a NaN close at every offset the
    sweep splices at, 120 bars apart so each one empties its 61 windows and
    the frame still fires in between."""
    c = _walk(N, seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = np.nan
    return Series(c)


def test_the_designed_probe_catches_the_mask_index_mutant():
    """What the shifted mask can move is DERIVED and then counted. A bad
    close at J spoils the returns at J and J+1, so the shifted mask drops
    the return at J-1; the window ending at J-1 is the only one before J
    that holds that return without also holding J, so bar J-1 is the only
    bar before J that can move. On a frame with a bad close at every
    offset: the real module still leaks 0 of 12, the mutant is caught 12 of
    12, and the bar it moves is J-1 and nothing else -- checked at ALL
    twelve offsets, and counting a changed VALUE as a move and not only a
    changed NaN mask."""
    close, other = _bad_close_frame(), _walk(N, 97)
    assert 600 < int(tf_iqr_ret_60(close).notna().sum()) < 800
    assert _caught(tf_iqr_ret_60, close, other, BAD_OFFSETS) == []

    mod = _load_mutant(*FORWARD_MASK)
    hits = _caught(mod.tf_iqr_ret_60, close, other, BAD_OFFSETS)
    assert len(hits) == len(list(BAD_OFFSETS))

    base = mod.tf_iqr_ret_60(close)
    for j in BAD_OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        a, b = base.iloc[:j], mod.tf_iqr_ret_60(p).iloc[:j]
        changed = (a.isna() != b.isna()) | ((a - b).abs().fillna(0.0) > 0.0)
        assert np.flatnonzero(changed.to_numpy()).tolist() == [j - 1], j


def test_prefix_truncation_is_clean_but_proves_less_than_the_mutants():
    """Necessary and not sufficient: a prefix cannot see a BACK-DATED
    write, which is why the five mutants above exist. Pinned anyway,
    because a port that fails even this is broken outright."""
    close = PAIRS["walk"][0]
    full = tf_iqr_ret_60(close)
    for j in OFFSETS:
        pre = tf_iqr_ret_60(close.iloc[:j])
        a, b = full.iloc[:j], pre
        assert bool((a.isna() == b.isna()).all()), j
        m = a.notna()
        assert bool((a[m] == b[m]).all()), j


# ------------------------------------------------- Gate C: reachability


def test_the_first_fired_bar_is_length():
    """`length` RETURNS, so `length + 1` closes -- bar 60 and not bar 59.
    The prototype agrees, because it reads the same 60 returns."""
    col = tf_iqr_ret_60(_walk())
    assert int(col.notna().to_numpy().argmax()) == LENGTH
    assert bool(np.isnan(col.iloc[LENGTH - 1]))
    assert int(tf_iqr_ret_60(_walk(n=LENGTH + 1)).notna().sum()) == 1
    assert tf_iqr_ret_60(_walk(n=LENGTH)) is None


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_c_the_column_fires_and_varies(frame):
    v = tf_iqr_ret_60(FRAMES[frame]())
    d = v.dropna()
    assert len(d) == FIRED
    assert 0 < len(d) < len(v)
    assert len(set(d)) > 1, frame


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_c_it_is_non_negative_on_every_frame_measured(frame):
    """`q75 >= q25` holds exactly in real arithmetic; in float the two
    blends could only round into each other where ranks 15..46 collapse
    onto one value, and there both blends return that value exactly. This
    is the measurement, not the proof -- the proof's gap is probed by
    `test_no_negative_reading_in_the_tie_heavy_windows`."""
    d = tf_iqr_ret_60(FRAMES[frame]()).dropna()
    assert bool((d >= 0.0).all()), float(d.min())


def test_no_negative_reading_in_the_tie_heavy_windows():
    """2,400 windows built for the ONLY arrangement in which the two blends
    can round into each other -- 400 with ranks 15..46 tied on one value,
    2,000 rounded onto a grid 10x coarser than the spread. 0 negative."""
    rng = np.random.default_rng(77)
    worst = 0.0
    for _ in range(400):
        base = rng.normal(0.0, 0.01)
        w = np.r_[np.sort(rng.normal(0.0, 0.01, 14)) - 1.0,
                  np.full(32, base),
                  np.sort(rng.normal(0.0, 0.01, 14)) + 1.0]
        s = np.sort(w)
        worst = min(worst, (s[44] + (s[45] - s[44]) * 0.25)
                    - (s[14] + (s[15] - s[14]) * 0.75))
    assert worst == 0.0, worst

    rng = np.random.default_rng(78)
    worst = 0.0
    for _ in range(2000):
        w = np.round(rng.normal(0.0, 1e-8, LENGTH) / 1e-9) * 1e-9
        s = np.sort(w)
        worst = min(worst, (s[44] + (s[45] - s[44]) * 0.25)
                    - (s[14] + (s[15] - s[14]) * 0.75))
    assert worst >= 0.0, worst


def test_a_flat_frame_reads_exactly_zero_and_a_ladder_reads_its_jitter():
    """The two degenerate frames, and why neither needs a floor. A flat
    frame has a genuine interquartile range of 0 and reads exactly that; a
    constant-RATE ladder has a mathematically constant return that float64
    need not reproduce exactly, so the column reads a tiny spread rather
    than an amplified error.

    ⚠ The ladder's reading is DISPATCH-DEPENDENT and that is why BOTH its
    min and its max are bounds and not values: measured max 5.551e-17 over
    two distinct doubles under this machine's default numpy dispatch, and
    exactly 0.0 over one double with `AVX512F AVX512_SKX AVX2 FMA3`
    disabled (`python docs/measure_tf_iqr_ret_60_cpu.py C`). The divide
    that builds the return is the dispatched step; the blend above it is
    three scalar operations. Either reading is honest -- what must hold on
    every CPU is that the column stays at the floor instead of amplifying
    the jitter, so nothing here asserts that some window collapses its read
    ranks exactly."""
    flat = tf_iqr_ret_60(_flat()).dropna()
    assert len(flat) == 300 - LENGTH
    assert sorted(set(flat)) == [0.0]

    lad = tf_iqr_ret_60(_ladder()).dropna()
    assert len(lad) == 300 - LENGTH
    assert 0.0 <= float(lad.min()) < 1e-15
    assert 0.0 <= float(lad.max()) < 1e-15
    assert len(set(lad)) <= 4, sorted(set(lad))


def test_it_is_unbounded_above_and_the_subtraction_cannot_overflow():
    """The upper end. A 90-bar cycle of [1e308, 1e-300, 1e8] closes -- every
    close finite, positive and normal, so no guard fires -- has returns of
    1e308, so the column reads 1e+308. And the subtraction still cannot
    overflow: a return is greater than -1 whenever both closes are positive
    and normal, so the widest span a blend can see is `DBL_MAX + 1`, which
    IS `DBL_MAX`."""
    cyc = Series(np.tile([1e308, 1e-300, 1e8], 30))
    with np.errstate(over="ignore"):
        d = tf_iqr_ret_60(cyc).dropna()
    assert len(d) == 90 - LENGTH
    assert float(d.max()) > 1e300
    assert bool(np.isfinite(d).all())

    mx = float(np.finfo(float).max)
    assert np.isfinite(mx - -1.0)
    assert (mx + (mx - mx) * 0.25) - (-1.0 + (-1.0 - -1.0) * 0.75) == mx


# ------------------------------------------------- Gate D: scale-freedom


@pytest.mark.parametrize("k", [8.0, 64.0])
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_d_scale_x8_and_x64_are_bit_identical(frame, k):
    """Bit-identity BY CONSTRUCTION: `8a / 8b` is the same double as
    `a / b`, so the returns are unchanged and so are the sort order and
    both blends."""
    close = FRAMES[frame]()
    masks, shared, same, d = _agree(tf_iqr_ret_60(close),
                                    tf_iqr_ret_60(close * k))
    assert masks
    assert same == shared == FIRED, (frame, k, same, shared, d)


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 20, 250])
def test_gate_d_scale_x8_at_other_lengths(length):
    close = _walk()
    masks, shared, same, _ = _agree(tf_iqr_ret_60(close, length=length),
                                    tf_iqr_ret_60(close * 8.0, length=length))
    assert masks
    assert same == shared == N - length


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_gate_d_scale_x8_at_extreme_price_levels(price):
    close = _walk()
    base = close * (price / float(close.iloc[0]))
    masks, shared, same, _ = _agree(tf_iqr_ret_60(base),
                                    tf_iqr_ret_60(base * 8.0))
    assert masks
    assert same == shared == FIRED


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "heavy-tailed"])
def test_gate_d_scale_x10_and_x37_hold_masks_and_a_tolerance(frame, k):
    """A non-binary factor perturbs the returns in their last bits, which
    can swap two nearly equal order statistics. The masks must still match
    exactly and the values to a relative tolerance; measured max 2.672e-14,
    asserted at 1e-12."""
    close = FRAMES[frame]()
    a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(close * k)
    masks, shared, _, d = _agree(a, b)
    assert masks
    assert shared == FIRED
    assert _max_rel(a, b) < 1e-12, (frame, k, _max_rel(a, b))
    assert _spearman(a, b) > 0.999


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_on_the_tie_frame_reads_rounding_and_not_a_failure(k):
    """⚠ On the two-point frame the Spearman under a non-binary rescale is
    0.34 .. 0.74, and that is NOT a scale failure: the column there is a
    handful of doubles spanning 2.2e-16 relative, so a rank correlation is
    reading rounding. The assertion is therefore on the RELATIVE difference
    and on the masks, which is what the scale claim actually means."""
    close = FRAMES[TIE_FRAME]()
    a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(close * k)
    masks, shared, _, _ = _agree(a, b)
    assert masks
    assert shared == FIRED
    assert _max_rel(a, b) < 1e-12


@pytest.mark.parametrize("shift", [1.0, 50.0, 1000.0])
def test_gate_d_a_level_shift_is_not_invariant(shift):
    """What keeps Gate D's bit-identity from being vacuous. `close + k` is
    not a rescale: it changes every return, and every fired bar moves.
    Without this limb a column hard-wired to a constant would pass x8."""
    close = _walk()
    a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(close + shift)
    m = a.notna() & b.notna()
    assert int(m.sum()) == FIRED
    assert int((a[m] != b[m]).sum()) == FIRED
    assert float((a[m] - b[m]).abs().max()) > 1e-5


# -------------------------------------------------------------- the guards


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -100.0, 1e-310])
@pytest.mark.parametrize("pos", [0, 1, LENGTH, 200, 399])
def test_a_bad_close_empties_its_windows_and_nothing_earlier(bad, pos):
    """A close that is not finite, normal and positive has no return to
    take, so it spoils the returns at `pos` and `pos + 1` and empties the
    61 windows that hold either -- clipped at the ends of the frame. And it
    moves NO bar before itself, which is the causal half of the claim."""
    base_frame = _walk(400)
    base = tf_iqr_ret_60(base_frame)
    close = base_frame.copy()
    close.iloc[pos] = bad
    with np.errstate(over="ignore"):
        v = tf_iqr_ret_60(close)
    emptied = int(base.notna().sum()) - int(v.notna().sum())
    assert emptied == {0: 1, 1: 2, LENGTH: 61, 200: 61, 399: 1}[pos]
    before = base.iloc[:pos]
    after = v.iloc[:pos]
    assert int(((before != after) & before.notna()).sum()) == 0


def test_an_overflowing_ratio_empties_sixty_windows():
    """ONE spoiled return rather than two: 1e-300 followed by 1e50 is a
    ratio of 1e+350, so the return at that bar is infinite and the one
    after it is finite."""
    base = tf_iqr_ret_60(_walk(400))
    close = _walk(400)
    close.iloc[200] = 1e-300
    close.iloc[201] = 1e50
    with np.errstate(over="ignore"):
        v = tf_iqr_ret_60(close)
    assert int(base.notna().sum()) - int(v.notna().sum()) == LENGTH


def test_pandas_already_blanks_a_window_holding_an_infinity():
    """What the module's `r.where(np.isfinite(r))` line is actually for.
    pandas' own `rolling.quantile` returns NaN for the WHOLE window on a
    single infinity -- at both quartiles, not only the one near it -- so the
    line is defence in depth and not the thing that does the work. Pinned
    because the module's comment says so, and because it is the mechanism
    behind `test_the_mask_index_mutant_is_dead_on_a_clean_frame`."""
    w = np.arange(1.0, LENGTH + 1.0)
    clean = Series(w).rolling(LENGTH, min_periods=LENGTH)
    assert float(clean.quantile(Q_HIGH).iloc[-1]) == 45.25
    assert float(clean.quantile(Q_LOW).iloc[-1]) == 15.75
    for win in (np.r_[np.inf, w[1:]], np.r_[-np.inf, w[1:]],
                np.r_[np.full(16, np.inf), w[16:]]):
        roll = Series(win).rolling(LENGTH, min_periods=LENGTH)
        assert bool(np.isnan(float(roll.quantile(Q_HIGH).iloc[-1])))
        assert bool(np.isnan(float(roll.quantile(Q_LOW).iloc[-1])))


def test_deleting_the_mask_line_changes_nothing_on_this_pandas():
    """The honest form of the claim above: a mutant with the mask line
    removed is BIT-IDENTICAL to the module on a clean walk, on a frame whose
    ratio overflows, and on the 1e308 cycle. The line is kept for intent and
    for pandas versions that might stop blanking such a window -- not
    because it moves a value today. If a future pandas makes this test fail,
    the line started doing work and the module's comment needs rewriting,
    not the test."""
    nomask = _load_mutant("    r = r.where(np.isfinite(r))", "    r = r")
    walk = _walk(400)
    over = walk.copy()
    over.iloc[200], over.iloc[201] = 1e-300, 1e50
    cyc = Series(np.tile([1e308, 1e-300, 1e8], 30))
    for close, fires in ((walk, 340), (over, 280), (cyc, 30)):
        with np.errstate(over="ignore"):
            a, b = tf_iqr_ret_60(close), nomask.tf_iqr_ret_60(close)
        masks, shared, same, d = _agree(a, b)
        assert masks and shared == fires and same == shared and d == 0.0


def test_an_underflowing_ratio_is_kept_because_it_is_correctly_rounded():
    """The asymmetry the module's comment claims, pinned. 1e308 followed by
    1e-300 is a ratio of 1e-608, which flushes to 0.0, so the return is
    exactly -1.0 -- the correctly rounded value of -1 + 1e-608, and kept.
    It is NOT silenced, and the column still fires."""
    assert 1e-300 / 1e308 - 1.0 == -1.0
    assert np.isfinite(1e-300 / 1e308 - 1.0)


@pytest.mark.parametrize("label,fires", [("flat", 240), ("ladder", 240),
                                          ("quiet", 540)])
def test_there_is_no_dispersion_floor_and_the_exact_oracle_says_so(label,
                                                                   fires):
    """The siblings `ts_kurt_60`, `ts_medskew_20` and `ts_above_mean_20`
    refuse a window whose returns span 4096 ulps or less, because each
    divides by a centre or a spread. This column divides by NOTHING, so a
    window with no dispersion has a perfectly good answer -- and the exact
    oracle agrees to 0.00 ulp on all three degenerate frames. The
    siblings' floor would empty the flat and ladder frames entirely: 480
    honest windows, 0 dishonest ones."""
    close = {"flat": _flat(), "ladder": _ladder(), "quiet": _quiet()}[label]
    v = tf_iqr_ret_60(close)
    d = v.dropna()
    assert len(d) == fires
    assert _max_ulps(v, _exact(close)) == 0.0

    r = _ret(close)
    roll = r.rolling(LENGTH, min_periods=LENGTH)
    span = roll.max() - roll.min()
    thr = 4096 * np.finfo(float).eps
    emptied = int((v.notna() & (span <= thr)).sum())
    assert emptied == (fires if label in ("flat", "ladder") else 0)


def test_no_warning_is_raised_on_bad_closes():
    """`errstate(over="ignore")` is scoped to the ratio, and the guard runs
    before it, so none of the SIX bad-close kinds reaches a warning -- the
    same six `test_a_bad_close_empties_its_windows_and_nothing_earlier`
    parametrises. `NaN` is in the list on purpose: it is the one that
    reaches `c >= np.finfo(float).tiny` as a NaN comparison."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        close = _walk(400)
        close.iloc[50] = -np.inf
        close.iloc[100] = np.inf
        close.iloc[150] = 0.0
        close.iloc[200] = -5.0
        close.iloc[250] = 1e-310
        close.iloc[300] = np.nan
        assert int(tf_iqr_ret_60(close).notna().sum()) > 0


def test_the_input_series_is_not_mutated():
    close = _walk()
    before = close.to_numpy().copy()
    tf_iqr_ret_60(close)
    assert bool((close.to_numpy() == before).all())


# ------------------------------------------------ what the column IS


@pytest.mark.parametrize("frame", ORDINARY)
def test_it_is_a_volatility_reading(frame):
    """POSITIVE volatility, which is the sign `ts_q05_60` does not have. A
    band and not a digit, because a synthetic high/low is an assumption and
    the CPU moves the last bits: measured +0.0735 .. +0.9511 against
    `NATR_60` over the ten frames, per-frame median 0.5641."""
    close = FRAMES[frame]()
    high, low = _ohlc(close)
    rho = _spearman(tf_iqr_ret_60(close), natr(high, low, close,
                                               length=LENGTH))
    assert rho > 0.0, (frame, rho)
    assert rho < 0.90, (frame, rho)


def test_the_vol_cycle_frame_is_where_every_volatility_measure_agrees():
    """The ceiling, read on the one frame built so volatility is the ONLY
    signal. There this column, `NATR_60` and `TS_Q05_60` all agree at about
    0.95 -- which says what the frame is, not that the columns are the
    same. It is named here rather than hidden so no other test in this file
    has to carry it."""
    close = _vol_cycle()
    high, low = _ohlc(close)
    mod = tf_iqr_ret_60(close)
    assert _spearman(mod, natr(high, low, close, length=LENGTH)) > 0.90
    assert _spearman(mod, ts_q05_60(close)) < -0.90


@pytest.mark.parametrize("frame", ORDINARY)
def test_it_does_not_restate_ts_q05_60_on_an_ordinary_frame(frame):
    """`TS_Q05_60` reads the 5% quantile of the SAME 60 returns, so it is
    the closest thing in the fork to a restatement -- and it landed on
    2026-11-14, three weeks AFTER the 2026-10-24 screen whose Gate E run
    produced this issue's figures. Measured per-frame -0.9364 .. +0.3075
    with a median |rho| of 0.3246; the -0.9364 is `vol-cycle` and has its
    own test above. Asserted below the owner's 0.90 line on the nine
    ordinary frames, so a port that became a restatement fails here."""
    close = FRAMES[frame]()
    rho = _spearman(tf_iqr_ret_60(close), ts_q05_60(close))
    assert abs(rho) < 0.90, (frame, rho)


@pytest.mark.parametrize("frame", ORDINARY)
def test_it_does_not_restate_the_ulcer_index(frame):
    """The fork's other scale-free downside-risk column over the same
    window. Measured -0.4672 .. +0.6489 over the ten frames."""
    close = FRAMES[frame]()
    assert abs(_spearman(tf_iqr_ret_60(close), ui(close, length=LENGTH))) \
        < 0.90


@pytest.mark.parametrize("frame", ORDINARY)
def test_it_does_not_restate_the_forks_quantile_of_the_price_level(frame):
    """Same pandas machinery, applied to the price LEVEL instead of the
    returns. A quantile of a price level is a support line."""
    close = FRAMES[frame]()
    rho = _spearman(tf_iqr_ret_60(close),
                    quantile(close, length=LENGTH, q=Q_HIGH))
    assert abs(rho) < 0.60, (frame, rho)


def test_it_is_sign_blind():
    """`q75(-x) = -q25(x)`, so negating every return leaves the statistic
    unchanged and a crash reads the same as a melt-up of the same shape.
    Two limbs, because the frame-level one cannot be exact: a price path
    rebuilt from negated returns re-rounds them, so that limb is a
    tolerance (measured max |difference| 5.829e-16, Spearman 1.000000),
    while 300 windows of exact doubles are asserted bit-equal on all but a
    handful (measured 298 of 300, worst 2.220e-16)."""
    rng = np.random.default_rng(41)
    r = np.clip(rng.standard_t(3.0, N) * 0.01, -0.5, 0.5)
    a, b = tf_iqr_ret_60(_from_returns(r)), tf_iqr_ret_60(_from_returns(-r))
    masks, shared, _, d = _agree(a, b)
    assert masks and shared == FIRED
    assert d < 1e-14, d
    assert _spearman(a, b) > 0.9999

    def blend(z):
        return ((z[44] + (z[45] - z[44]) * 0.25)
                - (z[14] + (z[15] - z[14]) * 0.75))

    hits, worst = 0, 0.0
    for _ in range(300):
        w = rng.standard_normal(LENGTH)
        up, down = blend(np.sort(w)), blend(np.sort(-w))
        hits += int(up == down)
        worst = max(worst, abs(up - down))
    assert hits >= 280, hits
    assert worst < 1e-14, worst


def test_the_level_to_expect_on_independent_windows():
    """The estimator's own level, from 20,000 INDEPENDENT windows of 60
    draws: 1.3187 sigma on a gaussian against the distribution's own
    1.3490, 1.6140 on a student-t(2) and 1.0751 on a one-sided exponential.
    Bands, because the draw is a different one on every numpy build."""
    rng = np.random.default_rng(101)

    def iqr_of(W):
        s = np.sort(W, axis=1)
        return ((s[:, 44] + (s[:, 45] - s[:, 44]) * 0.25)
                - (s[:, 14] + (s[:, 15] - s[:, 14]) * 0.75))

    g = iqr_of(rng.standard_normal((20000, LENGTH)))
    assert 1.28 < g.mean() < 1.36, g.mean()
    assert g.mean() < 2 * 0.6744897501960817     # the true quartile spread
    t = iqr_of(rng.standard_t(2.0, (20000, LENGTH)))
    assert 1.50 < t.mean() < 1.75, t.mean()
    e = iqr_of(rng.standard_exponential((20000, LENGTH)))
    assert 1.00 < e.mean() < 1.15, e.mean()
    assert bool((g > 0).all()) and bool((t > 0).all()) and bool((e > 0).all())


def test_it_is_a_slow_state_and_not_an_event_flag():
    """Two consecutive windows share 59 of their 60 returns. Measured
    lag-1 autocorrelation 0.9718, lag-5 0.8801, lag-30 0.5401, lag-60
    0.1849 -- the decay is the window sliding off, not a signal."""
    v = tf_iqr_ret_60(_walk()).dropna()
    assert float(v.autocorr(1)) > 0.95
    assert 0.80 < float(v.autocorr(5)) < 0.95
    assert 0.40 < float(v.autocorr(30)) < 0.70
    assert float(v.autocorr(60)) < 0.40


def test_one_bar_moves_exactly_length_bars():
    """One extreme return enters 60 windows and then leaves. The factor is
    0.5, a POWER OF TWO, so every return after bar 700 is the same double
    and exactly ONE return changes -- which is what makes "exactly 60" a
    structural fact rather than a rounding count."""
    close = _walk()
    spiked = close.copy()
    spiked.iloc[700:] = spiked.iloc[700:] * 0.5
    ra, rb = _ret(close), _ret(spiked)
    m = ra.notna() & rb.notna()
    assert int((ra[m] != rb[m]).sum()) == 1

    a, b = tf_iqr_ret_60(close), tf_iqr_ret_60(spiked)
    m = a.notna() & b.notna()
    moved = np.flatnonzero((a[m] != b[m]).to_numpy())
    idx = a[m].index.to_numpy()[moved]
    assert len(moved) == LENGTH
    assert int(idx.min()) == 700 and int(idx.max()) == 700 + LENGTH - 1


# ---------------------------------------------- the documents and Gate E


def test_the_volatility_warning_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows the first paragraph after
    the title, squeezed and truncated to 150 characters.
    `docs/IndicatorDictionary.md` is where CLAUDE.md sends a reader first,
    so "this is a volatility reading" has to fit inside that cut."""
    desc = _generator_desc()
    body = " ".join(tf_iqr_ret_60.__doc__.split("\n\n")[1].split())
    cut = desc({"desc": body})
    assert not cut.endswith("…"), cut
    # `desc` also rewrites `|` as `/` so the text cannot break the markdown
    # table it lands in, which is why this is not `cut == body`.
    assert cut == body.replace("|", "/"), cut
    assert "VOLATILITY" in cut, cut
    assert "NATR" in cut, cut


def test_the_ts_q05_60_overlap_check_is_owed_from_the_gate_e_run():
    """`ts_q05_60` was merged three weeks after the screen that produced
    this issue's Gate E figures, so Gate E's 687 comparators may not carry
    it and "the owner's call" needs a trigger or it is never made. The
    2026-11-16 receipt session settled only half of it: no `q05` spelling
    appears anywhere in the run's artefacts, and the run's `top25.csv`
    floor is 0.2680 against a synthetic pooled 0.6238, so the comparator
    set almost certainly does not carry it -- and the 89-frame measurement
    against `TS_Q05_60` is still owed to the owner, with the revert rule
    attached. This asserts that owed item and its rule are still in the
    receipt, so the recorded SHIP row cannot quietly settle them."""
    doc = (ROOT / "docs" / "TfIqrRet60Measured.md").read_text(
        encoding="utf-8")
    assert "OWED from the Gate E run" in doc
    assert "revert `tf_iqr_ret_60` if it is" in doc
    assert "r3-perframe-0.90" in doc


def test_the_gate_e_row_is_recorded_and_ships():
    """The Gate E row for this port, recorded 2026-11-16 from run
    `is117-tf_iqr_ret_60-7149d122` (89 ALTPORT-1 frames, 687 comparators,
    canary bit-equal). This pins the row's IDENTITY and its BAND, not its
    digits to the last place: a rho is asserted as an inequality against the
    0.76 ship line, because a re-run on other CPUs moves the last bits.
    Measured here: pooled 0.6730 vs `natr` (n = 393,509), per-frame max
    median 0.6565 -- the highest of the 687 and the same comparator the
    2026-10-24 screen found on the prototype."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "tf_iqr_ret_60"]
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["module"] == "pandas_ta.statistics.tf_iqr_ret_60"
    assert row["column"] == f"TFIQRRET_{LENGTH}"
    assert row["run"] == "is117-tf_iqr_ret_60-7149d122"
    assert row["measured"] == "2026-11-16"
    assert row["verdict"] == "SHIP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert int(row["n_frames"]) == 89
    assert int(row["n_comparators"]) == 687
    # SHIP is `< 0.76` on both limbs of `r3-perframe-0.90`; the measured pair
    # is 0.6730 / 0.6565, so 0.72 leaves room for a CPU to move the last bits
    # and still fails if the column drifts toward the disclosure line.
    assert float(row["max_abs_rho"]) < 0.72
    assert float(row["perframe_max_median_abs_rho"]) < 0.72
    # Gate C's real limb and Gate D's anti-constant limb, on real prices.
    non_nan, pooled = int(row["non_nan"]), int(row["pooled_bars"])
    assert 0 < non_nan < pooled
    # The warm-up is one bar for the first return plus `length - 1` for the
    # first full window -- `length` bars on each of the 89 frames, and nothing
    # else is missing: the column fires wherever a window exists.
    assert pooled - non_nan == 89 * LENGTH
    # Not the constant 0.0 on real data either, and the zeros that do occur
    # are a flat middle half of the window rather than a dead column.
    assert 0 < int(row["non_zero"]) <= non_nan


# ------------------------------------------------------------- the wiring


def test_name_registration_and_accessor():
    """Touch points 2, 3 and 4: the package export, `Category`, and the
    `df.ta` accessor."""
    import pandas as pd

    close = _walk(400)
    assert tf_iqr_ret_60(close).name == f"TFIQRRET_{LENGTH}"
    assert tf_iqr_ret_60(close).category == "statistics"
    assert "tf_iqr_ret_60" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.statistics, "tf_iqr_ret_60")

    df = pd.DataFrame({"close": close.to_numpy()})
    out = df.ta.tf_iqr_ret_60()
    assert out.name == f"TFIQRRET_{LENGTH}"
    assert out.equals(tf_iqr_ret_60(close.reset_index(drop=True)))
    assert df.ta.tf_iqr_ret_60(length=20).name == "TFIQRRET_20"


@pytest.mark.parametrize("length,name", [(None, 60), (0, 60), (1, 60),
                                          (2, 2), (20, 20)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, name):
    """A window of ONE return has q75 == q25, so the column would be the
    constant 0.0 -- not an interquartile range. The module refuses it."""
    assert tf_iqr_ret_60(_walk(400),
                         length=length).name == f"TFIQRRET_{name}"


def test_length_one_would_be_the_constant_zero_which_is_why_it_is_refused():
    """Shown rather than asserted: the thing the fallback prevents."""
    r = _ret(_walk(400))
    roll = r.rolling(1, min_periods=1)
    degenerate = (roll.quantile(Q_HIGH) - roll.quantile(Q_LOW)).dropna()
    assert sorted(set(degenerate)) == [0.0]


def test_too_short_an_input_returns_none():
    assert tf_iqr_ret_60(_walk(n=LENGTH)) is None
    assert tf_iqr_ret_60(_walk(n=LENGTH + 1)) is not None


def test_offset_and_fillna():
    close = _walk(400)
    base = tf_iqr_ret_60(close)
    moved = tf_iqr_ret_60(close, offset=3)
    assert bool((moved.iloc[LENGTH + 3:].to_numpy()
                 == base.iloc[LENGTH:-3].to_numpy()).all())
    filled = tf_iqr_ret_60(close, fillna=-1.0)
    assert int((filled == -1.0).sum()) == LENGTH


def test_the_module_does_not_import_the_package_root():
    """The `aberration` / `zlma` trap in CLAUDE.md: importing a helper from
    the PACKAGE binds the submodule while pandas_ta is still importing
    itself. This module imports from `pandas_ta.utils` only."""
    src = (ROOT / "pandas_ta" / "statistics"
           / "tf_iqr_ret_60.py").read_text(encoding="utf-8")
    assert "from pandas_ta.statistics import" not in src
    assert "import pandas_ta\n" not in src
