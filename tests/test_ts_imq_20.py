# -*- coding: utf-8 -*-
"""TS-IMQ-20: `ts_imq_20`, the index mass quantile of 20 |returns| at
q = 0.5 (PandasTa issue #99).

    TS_IMQ_20 = (argmax(cumsum(|r|) / sum(|r|) >= 0.5) + 1) / 20

over the trailing 20 simple returns -- WHERE in the window half of the
absolute-return mass has piled up, as a fraction of the window.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **That the column is a POSITION, not a size, and that this survives a
   rescale.** The statistic divides by the window's own total mass, so
   multiplying every |return| by a positive constant cannot move it --
   measured BIT-IDENTICAL at `r x 2`, `r x 0.5` and `r x 1e-6` on all
   1,480 fired bars of a 1,500-bar walk. It reads Spearman **-0.0156**
   against the same window's return standard deviation. If someone
   "improves" this into a magnitude the test
   `test_the_column_cannot_see_the_size_of_the_returns` fails.
   ⚠ It is NOT shift-invariant: `r + 0.004` moves 639 of 1,480 bars
   (rho 0.8534), which is the column working, not failing -- a shift
   changes which bars carry the mass.

2. **The overlap with the shipped `TFCENTROID_20`, which is the reason this
   port is a disclosure and not a quiet addition.** TSFEL's temporal
   centroid (issue #116, merged 2026-10-30) is the energy-weighted MEAN
   position of the same 20 returns where this is the absolute-mass MEDIAN
   position. Measured Spearman over nine 1,500-bar frames: pooled
   **+0.846649** (n = 13,320), per-frame |rho| median 0.8545, max 0.8857
   (heavy-tailed), min 0.7252 (two-point), **0 of 9 frames at or above
   0.90**. That is DISCLOSE_GAP under `r3-perframe-0.90`, not STRUCK.
   ⚠ SYNTHETIC. No real-frame figure for the pair exists: the 2026-10-24
   screen's fork overlap predates `tf_centroid_20` entering `Category` by
   six days, and Gate E's 687 comparators are the engine's and hold no
   pandas_ta port. Against the fork's other 20-return statistics columns
   the per-frame |rho| is at most 0.1034.

3. **Gate A -- the arithmetic is EXACT, and three independent oracles say
   so.** tsfresh's published expression applied window by window (no shared
   code) is bit-equal on 1,480 of 1,480 bars of each of nine frames; a
   `math.fsum` scalar loop with correctly-rounded partial sums on each of
   those nine; and an EXACT `fractions.Fraction` oracle -- where the partial
   sums, the total and the comparison round not at all -- on **13,320 of
   13,320** bars pooled over all nine. A closed form pins the degenerate
   end: closes that DOUBLE give a return of exactly 1.0 on every bar, so
   the crossing is exactly at `length / 2` (measured 0.5 at `length` 2, 4,
   20 and 60).

4. **That the column IS the screen prototype, bit for bit**, and exactly
   where the two part company. `docs/issues/screen/ind_screen.py`'s
   `roll(ret(c), 20, w_index_mass_quantile)` is retyped here (that tree is
   the owner's and gitignored) and is bit-equal on 1,480 of 1,480 bars of
   each of nine frames, with identical masks, and bit-equal again on a flat
   frame (0 and 0 fired), a ladder (280 and 280) and a quiet frame (580 and
   580). It differs only on the guards this module adds: a 0, negative,
   subnormal or infinite close, and a return past `max / (2 * length)`.

5. **Gate B, by MUTANT.** Prefix truncation cannot see back-dating, so
   causality is tested by future-perturbation over 37 offsets (J = 40..1480)
   on three frames. The real module leaks at **0 of 37** on each, and at
   `length` 5, 60 and 250. Five mutants -- `importlib`-read, string-patched
   and `exec`'d in memory -- are each LIVE and caught at **35 to 37** of the
   37: two back-dated writes, a window rolled one bar forward, a return read
   one bar ahead, and the window TOTAL read from the next window.

6. **Gate D -- bit-identical at x8/x64, and the ONE frame where x10 is
   not.** x8 and x64 are bit-identical on 1,480 of 1,480 bars of each of
   nine frames and at `length` 2 / 5 / 60 / 250 (1,498 / 1,495 / 1,440 /
   1,250 bars, both factors). That one IS asserted as an equality, because
   `8a / 8b` is the same double as `a / b` on any CPU. x10, x3.7 and x0.1
   are bit-identical on eight of the nine frames and NOT on the two-point
   frame, where every |return| is the same size so every window sits on the
   tie: 1,029 / 1,071 / 1,038 of 1,480 bars bit-equal, the rest moving by
   one position (0.050000000000000044, which is `1 / 20` as a float and
   not the decimal 0.05) -- the smallest step the column can take.
   ⚠ Those counts are NOT asserted anywhere: they are this CPU's. What the
   tests pin for a non-power-of-two rescale is the NaN masks, the shared
   bar count, and a tolerance of ONE position; the two-point frame is not
   even required to move, so a numpy change that made it bit-equal would be
   a better outcome and not a red suite.

7. **The value set.** The output is `k / 20` for an integer `k` in 1..20 --
   never 0, never above 1 -- and how many of the 20 levels a frame reaches
   varies enormously: 20 on a heavy-tailed frame, 12 on a walk (only
   [0.25, 0.80]), 8 trending, **2** on a two-point frame. A consumer that
   treats this as a continuum is wrong.

8. **The guards, and that there is deliberately NO dispersion floor.** The
   source's own `s == 0` rule (all-zero returns) is the only degenerate
   case, and 21 identical closes are the only way to reach it. Its siblings
   `ts_medskew_20` and `ts_above_mean_20` refuse a window spanning 4096 ulps
   or less; this one does not, because a degenerate window costs it ONE
   position and not a range: on a 1%-a-bar ladder it reports 280 of 280
   windows as 0.50 (178) or 0.55 (102), where the unfloored `ts_medskew_20`
   statistic spans [-0.3300, +0.3033]. A DOUBLING ladder, whose returns are
   exactly 1.0, reads 0.5 on all 281 -- so the jitter is the data's
   rounding, not the module's.

9. **Locality.** A planted return of 1e+2 .. 1e+300 at bar 200 of a
   2,000-bar frame leaves every one of the 1,780 bars from 220 on
   BIT-IDENTICAL to the unspiked frame, and at 1e+307 (past the bound) it
   empties only the 20 windows holding it. The O(n) global-`cumsum`
   spelling returns NaN on all 1,780 of those bars at 1e+100.

10. **The wiring.** Five touch points, the accessor forwarding `length` and
    `offset` under the right names, and the IDENTITY of the Gate E ledger
    row -- `is99-ts_imq_20-d5aaa69c`, measured 2026-11-14, SHIP at 0.5254
    vs `ATR_Ratio_5_20_Pctl` over n = 391,818 --  which
    `test_the_ledger_row_is_this_modules_gate_e_run` pins, because
    `tests/test_gate_e_ledger.py` checks a row's arithmetic but cannot see
    WHOSE run it came from (the 2026-10-24 screen measured the prototype to
    the same printed digits).

11. **What the source's `+ 1` buys**, against a variant built from scratch
    and not against `module - 1/length`, which would agree with anything:
    without it the column is the 0-BASED position and reads **0.0** on 6
    bars of the heavy-tailed frame, a value every other consumer reads as
    "no mass anywhere". The difference is `1 / length` to within 1.1e-16,
    so the test is a tolerance and not an equality.

NOT pinned here: Gate E itself, which needs the parent engine's comparators
and the 89 frozen BIST frames. The launcher ran it on 2026-11-14 and the
row is in `docs/gate_e_ledger.csv`; what this file pins is the row's
identity, not the measurement. `docs/TsImq20Measured.md` §E carries the
result in full.

Numbers come from `docs/measure_ts_imq_20.py`; the receipt is
`docs/TsImq20Measured.md`. ⚠ Float results move in the last bits between
CPUs, so what is pinned here is structure (a bound, a count of distinct
values, a first fired bar, a sign) or a tolerance, never a Spearman to
1e-6. The figures quoted above are this machine's, and
`docs/measure_ts_imq_20_cpu.py` re-runs this module with numpy's AVX-512 /
AVX2 / FMA3 dispatch disabled.
"""
import importlib
import math
import types
from fractions import Fraction

import numpy as np
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20
from pandas_ta.statistics.ts_above_mean_20 import ts_above_mean_20
from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20
from pandas_ta.statistics.ts_medskew_20 import ts_medskew_20
from pandas_ta.statistics.ts_peaks_20 import ts_peaks_20
from pandas_ta.statistics.ts_imq_20 import MIN_LENGTH, Q, ts_imq_20

_REAL = importlib.import_module("pandas_ta.statistics.ts_imq_20")

LENGTH = 20
FIRED = 1500 - LENGTH


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _window_frame(rs):
    """`len(rs) + 1` closes whose returns are `rs`."""
    body = np.cumprod(1.0 + np.asarray(rs, dtype=float))
    return Series(100.0 * np.concatenate([[1.0], body]))


def _ar1(n=1500, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=1500, seed=9):
    return _walk(n, seed, sigma=0.004, drift=0.01)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A mathematically CONSTANT return, which float64 reproduces only to
    rounding."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _doubling(n=300):
    """Closes that double, so every return is EXACTLY 1.0 and the window's
    values are exactly equal with no rounding anywhere."""
    return Series(2.0 ** np.arange(n, dtype=float))


def _quiet(n=600, seed=31, sigma=1e-6):
    rng = np.random.default_rng(seed)
    return _from_returns(rng.normal(0.0, sigma, n))


def _spiked(k, n=2000, seed=13, sigma=0.01, price=1e-198):
    """2,000 bars priced at 1e-198 so even a 1e+307 planted return keeps the
    close path finite."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    if k is not None:
        r[200] = k
    return Series(price * np.cumprod(1.0 + r))


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5, seed=17),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
}

#: The one frame on which a non-power-of-two price rescale is NOT
#: bit-identical: every |return| is the same size, so every window sits on
#: the `>= 0.5` tie. Named here so the exception is explicit rather than an
#: allowance buried in a bound.
TIE_FRAME = "two-point"
#: The largest difference the column can make: one position.
ONE_POSITION = 1.0 / LENGTH


# ----------------------------------------------------------------- helpers


def _returns_of(close):
    return (close / close.shift(1) - 1.0).to_numpy()


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, bit-equal count, shared count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0, 0.0
    d = (a[m] - b[m]).abs()
    return masks, int((a[m] == b[m]).sum()), int(m.sum()), float(d.max())


# ----------------------------------------------------------------- oracles


def _tsfresh(x, q=Q):
    """tsfresh `feature_calculators.index_mass_quantile`, one window, as the
    published definition states it."""
    x = np.asarray(x)
    abs_x = np.abs(x)
    s = sum(abs_x)
    if s == 0:
        return float("nan")
    mass_centralized = np.cumsum(abs_x) / s
    return (np.argmax(mass_centralized >= q) + 1) / len(x)


def _source_windowed(close, length=LENGTH, q=Q):
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        out[t] = _tsfresh(x, q)
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH, q=Q):
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = [abs(v) for v in r[t - length + 1:t + 1]]
        if not all(math.isfinite(v) for v in x):
            continue
        s = math.fsum(x)
        if s == 0.0:
            continue
        for k in range(length):
            if math.fsum(x[:k + 1]) / s >= q:
                out[t] = (k + 1) / length
                break
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH, q=Q):
    """Every float is a rational, so nothing rounds."""
    r = _returns_of(close)
    qf = Fraction(q)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        xs = [Fraction(abs(float(v))) for v in x]
        s = sum(xs)
        if s == 0:
            continue
        cum = Fraction(0)
        for k, v in enumerate(xs):
            cum += v
            if cum / s >= qf:
                out[t] = (k + 1) / length
                break
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH, q=Q):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_imq_20`, retyped
    (that tree is the owner's and gitignored, so it is copied, not
    imported):

        def _(o, h, l, c, v): return roll(ret(c), 20, w_index_mass_quantile)

        def w_index_mass_quantile(W, q=0.5):
            A = np.abs(W)
            s = A.sum(1, keepdims=True)
            cs = np.cumsum(A, 1) / np.where(s == 0, np.nan, s)
            idx = (cs >= q).argmax(1) + 1.0
            return np.where(np.isnan(cs[:, -1]), np.nan, idx / W.shape[1])
    """
    a = (close / close.shift(1) - 1.0).to_numpy(dtype=float)
    W = sliding_window_view(a, length)
    A = np.abs(W)
    s = A.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        cs = np.cumsum(A, 1) / np.where(s == 0, np.nan, s)
    idx = (cs >= q).argmax(1) + 1.0
    out = np.full(close.size, np.nan)
    out[length - 1:] = np.where(np.isnan(cs[:, -1]), np.nan, idx / W.shape[1])
    return Series(out, index=close.index)


def _global_cumsum_variant(close, length=LENGTH, q=Q):
    """The O(n) spelling the module does NOT use: one global cumulative sum,
    differenced per window."""
    r = _returns_of(close)
    a = np.abs(r)
    bad = ~np.isfinite(a)
    c = np.concatenate([[0.0], np.cumsum(np.where(bad, 0.0, a))])
    badc = np.concatenate([[0], np.cumsum(bad.astype(np.int64))])
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        lo = t - length + 1
        if badc[t + 1] - badc[lo]:
            continue
        s = c[t + 1] - c[lo]
        if not np.isfinite(s) or s <= 0:
            continue
        for k in range(length):
            if (c[lo + k + 1] - c[lo]) / s >= q:
                out[t] = (k + 1) / length
                break
    return Series(out, index=close.index)


def _unfloored_medskew(close, length=LENGTH):
    """`ts_medskew_20`'s statistic with its relative floor removed. Used only
    to show what that floor is for, and why this column does not need one."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        s = np.std(x, ddof=1)
        if s == 0.0:
            continue
        out[t] = (np.mean(x) - np.median(x)) / s
    return Series(out, index=close.index)


# ------------------------------------------------- Gate A: the arithmetic


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_module_is_tsfresh_s_expression_bit_for_bit(frame):
    """Gate A. The published `index_mass_quantile` applied one window at a
    time, sharing no code with the module: 1,480 of 1,480 bars bit-equal on
    each of nine frames, masks identical.

    This is the ONE oracle held to an exact equality, and the reason is
    structural rather than lucky: it accumulates with Python's `sum` and
    `np.cumsum`, both strictly left-to-right, which is the same order and
    therefore the same doubles as the module's two loops. The oracles that
    round DIFFERENTLY -- `math.fsum`, `fractions.Fraction`, and the
    prototype's PAIRWISE `A.sum(1)` -- are held to a tolerance on the tie
    frame instead (see `TIE_FRAME` below)."""
    close = FRAMES[frame]()
    masks, eq, shared, mx = _agree(ts_imq_20(close), _source_windowed(close))
    assert masks
    assert eq == shared == FIRED, (eq, shared)
    assert mx == 0.0


@pytest.mark.parametrize("frame", ["walk", "heavy-tailed", "two-point"])
def test_the_issue_s_on_absolute_returns_is_the_same_column(frame):
    """The issue says "on 20 |returns|" and the source takes `np.abs` of
    what it is handed. Feeding it the already-absolute values is therefore a
    no-op -- measured, not argued."""
    close = FRAMES[frame]()
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(LENGTH - 1, r.size):
        x = np.abs(r[t - LENGTH + 1:t + 1])
        if np.isfinite(x).all():
            out[t] = _tsfresh(x)
    masks, eq, shared, mx = _agree(ts_imq_20(close),
                                   Series(out, index=close.index))
    assert masks and eq == shared == FIRED and mx == 0.0


@pytest.mark.parametrize("frame", sorted(set(FRAMES) - {TIE_FRAME}))
def test_a_correctly_rounded_fsum_loop_agrees(frame):
    """`math.fsum` rounds each partial sum exactly once; the module's
    running `acc` rounds at every step. They agree on every bar.

    The tie frame is excluded on purpose and tested below: the two round
    differently, so bit-equality there is an observation and not a
    contract."""
    close = FRAMES[frame]()
    masks, eq, shared, mx = _agree(ts_imq_20(close), _fsum_windowed(close))
    assert masks and eq == shared == FIRED and mx == 0.0


@pytest.mark.parametrize("frame", sorted(set(FRAMES) - {TIE_FRAME}))
def test_the_exact_rational_oracle_agrees_on_every_bar(frame):
    """The strongest Gate A check here: an oracle in `fractions.Fraction`
    where the partial sums, the total and the `>= 0.5` comparison round not
    at all. Measured 13,320 of 13,320 bars pooled over all NINE frames; the
    equality is asserted on the eight that are not the tie frame."""
    close = FRAMES[frame]()
    masks, eq, shared, mx = _agree(ts_imq_20(close), _exact_windowed(close))
    assert masks and eq == shared == FIRED and mx == 0.0


@pytest.mark.parametrize("oracle", ["fsum", "exact", "prototype"])
def test_the_tie_frame_is_held_to_a_tolerance_and_not_to_the_bits(oracle):
    """The three oracles whose arithmetic rounds DIFFERENTLY from the
    module's -- `math.fsum` (exactly rounded), `fractions.Fraction` (not
    rounded at all) and the prototype's PAIRWISE `A.sum(1)` -- against the
    one frame where that can matter. On the two-point frame every |return|
    is the same size, so every window's cumulative mass lands on the
    `>= 0.5` threshold and a last-bit difference in the total is enough to
    move the crossing by one position; §D2 shows a x10 price rescale doing
    exactly that on 451 of 1,480 bars.

    Measured on this CPU all three are bit-equal on 1,480 of 1,480 bars.
    That is NOT asserted. What is asserted is what a different summation
    order cannot break: identical NaN masks, every fired bar shared, and
    nothing moving by more than ONE position."""
    close = _two_point()
    other = {"fsum": _fsum_windowed, "exact": _exact_windowed,
             "prototype": _prototype}[oracle](close)
    masks, eq, shared, mx = _agree(ts_imq_20(close), other)
    assert masks
    assert shared == FIRED
    assert mx <= ONE_POSITION + 1e-12


@pytest.mark.parametrize("n", [2, 4, 20, 60])
def test_the_closed_form_on_exactly_equal_returns(n):
    """Closes that DOUBLE give a return of exactly 1.0 on every bar, so the
    window's values are exactly equal, the total is exact and the crossing
    is exactly at `ceil(n * q)`. No rounding is involved anywhere, so this
    is an equality and not a tolerance."""
    got = ts_imq_20(_doubling(n + 1), length=n)
    assert float(got.iloc[-1]) == math.ceil(n * Q) / n


def test_the_float_path_matches_the_exact_one_on_threshold_straddles():
    """The one thing float arithmetic can cost here is a TIE -- a window
    whose exact cumulative mass lands within a rounding of half the total,
    where the crossing could be reported one position early. 200 windows
    built to straddle the threshold produce no disagreement; the bound is
    structural, since the two answers can differ by at most one position."""
    rng = np.random.default_rng(5)
    worst = 0.0
    for _ in range(200):
        half = np.abs(rng.normal(0.0, 0.01, LENGTH // 2))
        x = np.concatenate([half, half * (1.0 + rng.normal(0.0, 1e-13,
                                                           LENGTH // 2))])
        close = _window_frame(x * rng.choice([-1.0, 1.0], LENGTH))
        a = float(ts_imq_20(close).iloc[-1])
        b = float(_exact_windowed(close).iloc[-1])
        worst = max(worst, abs(a - b))
    assert worst <= ONE_POSITION + 1e-12


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_every_value_is_k_over_length_and_never_zero(frame):
    """The output is `k / length` for an integer `k` in 1..length. `0` is
    unreachable because of the source's `+ 1`, and values above 1 because
    the crossing cannot be past the last position."""
    col = ts_imq_20(FRAMES[frame]()).dropna()
    scaled = col.to_numpy() * LENGTH
    assert np.allclose(scaled, np.round(scaled), atol=1e-9)
    assert int(np.round(scaled).min()) >= 1
    assert int(np.round(scaled).max()) <= LENGTH


def test_the_found_backstop_is_what_stops_a_q_above_one_reporting_zero():
    """`found` is a labelled backstop with NO witness at `Q = 0.5`: the
    measurement script counts 0 windows of 9 frames where it disagrees with
    `s > 0`, which is arithmetic (the last `acc` is the same double as `s`,
    and `s / s >= 0.5`). It is kept for the case that HAS a witness, and
    this is that case: two mutants, the first raising `Q` past 1 and the
    second ALSO dropping the backstop. With it, the column is empty; without
    it, every bar reports position 0 -- the value `0.0` this column must
    never emit."""
    walk = _walk(300)
    assert int(ts_imq_20(walk).notna().sum()) == 300 - LENGTH

    hi_q = _load_patched([("Q = 0.5", "Q = 1.5")])
    assert int(hi_q.ts_imq_20(walk).notna().sum()) == 0

    no_backstop = _load_patched([
        ("Q = 0.5", "Q = 1.5"),
        ("    reported = (s > 0.0) & found", "    reported = (s > 0.0)")])
    col = no_backstop.ts_imq_20(walk).dropna()
    assert int(col.size) == 300 - LENGTH
    assert float(col.max()) == 0.0


# ------------------------------------------- Gate A: the readings priced


def test_log_returns_are_a_near_copy_and_not_this_column():
    """The source says "returns"; this module uses the SIMPLE return, the
    prototype's `ret`. Log returns agree on 1,440 of 1,480 bars and the rest
    move by one position."""
    walk = _walk()
    c = walk.to_numpy()
    logr = np.concatenate([[np.nan], np.log(c[1:] / c[:-1])])
    out = np.full(logr.size, np.nan)
    for t in range(LENGTH - 1, logr.size):
        x = logr[t - LENGTH + 1:t + 1]
        if np.isfinite(x).all():
            out[t] = _tsfresh(x)
    other = Series(out, index=walk.index)
    masks, eq, shared, mx = _agree(ts_imq_20(walk), other)
    assert masks and eq >= 1400
    assert mx <= ONE_POSITION + 1e-12          # measured: exactly 1 position
    assert _spearman(ts_imq_20(walk), other) > 0.99


def test_the_statistic_of_the_closes_is_a_different_question():
    """Rejected reading: applying the source to the 20 CLOSES rather than to
    their returns. That column is not scale-free (it reads where the price
    LEVEL mass sits) and is near-uncorrelated with this one."""
    walk = _walk()
    c = walk.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(LENGTH - 1, c.size):
        out[t] = _tsfresh(c[t - LENGTH + 1:t + 1])
    assert abs(_spearman(ts_imq_20(walk), Series(out, index=walk.index))) < 0.3


def test_twenty_returns_not_twenty_closes():
    """`length` counts RETURNS, so 20 of them need 21 closes and the first
    value lands at bar 20. The off-by-one a reader makes -- 20 closes, i.e.
    19 returns -- is a different column (rho 0.906 on a walk)."""
    walk = _walk()
    assert int(ts_imq_20(walk).notna().to_numpy().argmax()) == LENGTH
    other = ts_imq_20(walk, length=LENGTH - 1)
    assert 0.85 < _spearman(ts_imq_20(walk), other) < 0.95
    assert _agree(ts_imq_20(walk), other)[3] > 2 * ONE_POSITION


def _no_plus_one_variant(close, length=LENGTH, q=Q):
    """The source expression WITHOUT its `+ 1`: `argmax(...) / len(x)`.
    Built from scratch -- NOT as `base - 1/length`, which would be the
    conclusion subtracted from itself and would pass on a broken module."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = np.abs(r[t - length + 1:t + 1])
        if not np.isfinite(x).all():
            continue
        s = sum(x)
        if s == 0:
            continue
        out[t] = np.argmax(np.cumsum(x) / s >= q) / length
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame,reaches_zero", [("walk", False),
                                                ("heavy-tailed", True)])
def test_what_the_source_s_plus_one_buys(frame, reaches_zero):
    """Priced against a REAL variant, not against a subtraction. Without the
    `+ 1` the column is the 0-based position, so its floor is 0.0 -- a value
    this column must never emit, because 0 means "no mass anywhere" for
    every other reader. On the heavy-tailed frame the variant does reach it
    (6 bars, measured) and the module reads 0.05 there instead; on a walk
    neither gets near the floor. The difference is `1 / length` to within a
    rounding (measured shift in [0.049999999999999933, 0.050000000000000044]
    -- NOT exactly 0.05, which is why this is a tolerance), so a RANK miner
    cannot see it and a threshold rule can."""
    close = FRAMES[frame]()
    mine, no1 = ts_imq_20(close), _no_plus_one_variant(close)
    assert bool((mine.isna() == no1.isna()).all())
    d = (mine - no1).dropna()
    assert abs(float(d.min()) - ONE_POSITION) < 1e-15
    assert abs(float(d.max()) - ONE_POSITION) < 1e-15
    assert float(mine.min()) >= ONE_POSITION
    assert (float(no1.min()) == 0.0) is reaches_zero
    assert _spearman(mine, no1) > 0.999


def test_the_comparison_spelling_does_not_move_the_column():
    """Two spellings the source leaves open. `> q` instead of `>= q`, and
    `acc >= q * s` instead of `acc / s >= q`: both bit-equal on every bar of
    a walk. They are kept as the source writes them anyway."""
    walk = _walk()
    base = ts_imq_20(walk)
    r = _returns_of(walk)
    strict = np.full(r.size, np.nan)
    cross = np.full(r.size, np.nan)
    for t in range(LENGTH - 1, r.size):
        x = np.abs(r[t - LENGTH + 1:t + 1])
        if not np.isfinite(x).all():
            continue
        s = sum(x)
        if s == 0:
            continue
        cum = np.cumsum(x)
        hit = np.flatnonzero(cum / s > Q)
        if hit.size:
            strict[t] = (hit[0] + 1) / LENGTH
        hit = np.flatnonzero(cum >= Q * s)
        if hit.size:
            cross[t] = (hit[0] + 1) / LENGTH
    for other in (strict, cross):
        masks, eq, shared, mx = _agree(base, Series(other, index=walk.index))
        assert masks and eq == shared == FIRED


def test_another_quantile_is_another_column():
    """`q` is fixed at 0.5 by the issue. q = 0.25 and q = 0.75 are related
    but distinct readings (rho ~0.59 on a walk), which is why `q` is a
    module constant and not a silent default a caller could move under a
    column name that does not carry it."""
    walk = _walk()
    base = ts_imq_20(walk)
    for q, centre in ((0.25, 0.28), (0.75, 0.77)):
        other = _source_windowed(walk, q=q)
        assert 0.4 < _spearman(base, other) < 0.8
        assert abs(float(other.mean()) - centre) < 0.05


# --------------------------------------------- the prototype and the shape


@pytest.mark.parametrize("frame", sorted(set(FRAMES) - {TIE_FRAME}))
def test_the_column_is_the_screen_prototype_bit_for_bit(frame):
    """Gate A's other half: the screen's own expression, retyped. Identical
    masks and every fired bar bit-equal on the eight frames where the
    prototype's PAIRWISE total did NOT change the crossing (measured; the
    tie frame is where it can, and it is held to a tolerance above)."""
    close = FRAMES[frame]()
    masks, eq, shared, mx = _agree(ts_imq_20(close), _prototype(close))
    assert masks and eq == shared == FIRED and mx == 0.0


def test_the_prototype_agrees_on_the_degenerate_frames_too():
    """Including the three frames built to break it: a flat frame (both
    empty), a 1%-a-bar ladder (280 and 280) and a quiet 1e-6 frame (580 and
    580). The LADDER is itself a tie case -- a mathematically constant
    return -- so what is asserted there is the counts, the masks and one
    position of tolerance, not the bits."""
    for frame, expected in ((_flat(), 0), (_ladder(), 280), (_quiet(), 580)):
        mine, proto = ts_imq_20(frame), _prototype(frame)
        masks, eq, shared, mx = _agree(mine, proto)
        assert masks and mx <= ONE_POSITION + 1e-12
        assert int(mine.notna().sum()) == int(proto.notna().sum()) == expected


def test_where_the_prototype_and_the_module_part_company():
    """The guards this module adds and the screen has no need of. A bad
    close makes the prototype report windows built on a price a market
    cannot print; a return past `max / (2 * length)` makes it report a
    window whose total is an infinity. Pinned as inequalities so the
    DIRECTION cannot silently reverse."""
    for bad in (0.0, -1.0, 1e-310, np.inf):
        close = _walk(400, seed=3)
        close.iloc[200] = bad
        mine, proto = ts_imq_20(close), _prototype(close)
        assert int(proto.notna().sum()) > int(mine.notna().sum())
    mine, proto = ts_imq_20(_spiked(1e307)), _prototype(_spiked(1e307))
    assert int(proto.notna().sum()) - int(mine.notna().sum()) == LENGTH


@pytest.mark.parametrize("frame,low,high", [
    ("walk", 10, 14), ("heavy-tailed", 18, 20), ("trending", 6, 10),
    ("two-point", 2, 3),
])
def test_how_many_of_the_twenty_levels_a_frame_reaches(frame, low, high):
    """The column is an ORDINAL with at most 20 levels, and how many of them
    a frame reaches varies enormously -- 20 on a heavy-tailed frame, 12 on a
    walk, 8 trending, 2 on a two-point frame, where every |return| is the
    same size so the crossing can only be at position 10 or 11. Bands, not
    exact counts: the last bits move between CPUs."""
    col = ts_imq_20(FRAMES[frame]()).dropna()
    assert low <= int(col.unique().size) <= high


def test_the_level_on_iid_windows_barely_moves_with_the_law():
    """On independent windows the centre is ~0.53 whatever the return law,
    because the column reads a POSITION. The SPREAD is what the tails move:
    the measurement script reads sd 0.0849 for gaussian returns against
    0.1438 for student-t(2) over 20,000 windows. Driven through the SHIPPED
    function, 1,200 windows each."""
    rng = np.random.default_rng(19)
    out = {}
    # Clipped to [-0.5, 0.5] like `_heavy_tailed`: a student-t(2) draw below
    # -1 would make a close non-positive, which the module rightly refuses,
    # and the question here is the LEVEL, not the guard.
    for law, draw in (("gaussian", lambda n: rng.normal(0.0, 0.01, n)),
                      ("t2", lambda n: np.clip(0.01 * rng.standard_t(2.0, n),
                                               -0.5, 0.5))):
        vals = np.array([float(ts_imq_20(_window_frame(draw(LENGTH)))
                               .iloc[-1]) for _ in range(1200)])
        out[law] = (vals.mean(), vals.std())
    for law in out:
        assert 0.48 < out[law][0] < 0.58, (law, out[law])
    assert out["t2"][1] > out["gaussian"][1]


# ------------------------------------------------------ Gate B: the mutants


MUTANTS = {
    "back_date_two": (
        "    out[length - 1:] = np.where(reported, idx / length, np.nan)",
        "    out[length - 3:c.size - 2] = np.where(reported, idx / length,"
        " np.nan)"),
    "back_date_full": (
        "    out[length - 1:] = np.where(reported, idx / length, np.nan)",
        "    out[:rows] = np.where(reported, idx / length, np.nan)"),
    "forward_window": (
        "    aw = sliding_window_view(a, length)",
        "    aw = sliding_window_view(np.roll(a, -1), length)"),
    "forward_return": (
        "        r = (px / px.shift(1) - 1.0).to_numpy()",
        "        r = (px.shift(-1) / px - 1.0).to_numpy()"),
    "future_total": (
        "    acc = np.zeros(rows)",
        "    s = np.roll(s, -1)\n    acc = np.zeros(rows)"),
}
OFFSETS = range(40, 1500, 40)  # 37 offsets
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 37 offsets, at the
#: default `length` -- a BAND, not a target. The floor of 30 is well below
#: the smallest measured (35, `future_total` on the tick-rounded frame) so a
#: last-bit difference on another CPU cannot fail the suite, and well above
#: 0 so a mutant that goes dead does.
CAUGHT = (30, 37)


def _load_patched(pairs):
    """Read the real module's source, apply every (old, new) replacement --
    each of which must be unique -- and `exec` the result in memory."""
    src = open(_REAL.__file__, encoding="utf-8").read()
    for old, new in pairs:
        assert src.count(old) == 1, f"mutation target {old!r} not unique"
        src = src.replace(old, new)
    mod = types.ModuleType("_ts_imq_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _load_mutant(old, new):
    return _load_patched([(old, new)])


def _caught(fn, close, other, **kwargs):
    """Offsets J at which replacing every close from bar J on moves a bar
    BEFORE J -- which a causal column cannot do."""
    base = fn(close, **kwargs)
    hits = []
    for j in OFFSETS:
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
    before J. 0 of 37 offsets on each of three frames."""
    close, other = PAIRS[frame]
    assert _caught(ts_imq_20, close, other) == []


@pytest.mark.parametrize("length", [5, 60, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(ts_imq_20, close, other, length=length) == []
    assert int(ts_imq_20(close, length=length).notna()
               .to_numpy().argmax()) == length


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column -- otherwise the test proves
    nothing -- and be caught by the blind sweep within the measured band.
    `future_total` is the one worth reading: it back-dates nothing and
    moves no index, it simply lets bar T's ratio be divided by the NEXT
    window's total mass, and that is enough to leak."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_imq_20(close).equals(ts_imq_20(close))
    hits = _caught(mod.ts_imq_20, close, other)
    lo, hi = CAUGHT
    assert lo <= len(hits) <= hi, (mutant, frame, len(hits))


def test_the_first_fired_bar_is_length_not_length_minus_one():
    """20 returns need 21 closes, so bar 19's window holds the undefined
    first return. The prototype agrees here."""
    for frame in FRAMES:
        close = FRAMES[frame]()
        col = ts_imq_20(close)
        assert int(col.notna().to_numpy().argmax()) == LENGTH
        assert bool(np.isnan(col.iloc[LENGTH - 1]))
        assert int(_prototype(close).notna().to_numpy().argmax()) == LENGTH


# ------------------------------------------------------- Gate C: it fires


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_column_fires_on_every_frame_and_is_never_constant(frame):
    """Gate D's `0 < fires < n` with the constant case closed: 1,480 of
    1,500 bars on each of nine frames, the 20 missing ones the warm-up, and
    at least two distinct values everywhere."""
    col = ts_imq_20(FRAMES[frame]())
    assert int(col.notna().sum()) == FIRED
    assert int(col.isna().sum()) == LENGTH
    assert int(col.dropna().unique().size) >= 2
    assert int((col.dropna() == 0.0).sum()) == 0


def test_a_flat_frame_fires_on_nothing():
    """The source's own `s == 0` rule. 21 identical closes give 20 returns
    of exactly 0, which have no mass to find a quantile of."""
    assert int(ts_imq_20(_flat()).notna().sum()) == 0
    assert bool(np.isnan(ts_imq_20(_flat(21)).iloc[-1]))


def test_the_warm_up_is_exactly_length_bars_at_every_length():
    for length in (MIN_LENGTH, 5, 20, 60, 250):
        col = ts_imq_20(_walk(), length=length)
        assert int(col.isna().sum()) == length
        assert int(col.notna().sum()) == 1500 - length


# ---------------------------------------------------------- Gate D: scale


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_rescale_is_bit_identical(frame, k):
    """`8a / 8b` is the same double as `a / b`, so the returns -- and
    therefore every later step -- are unchanged. An equality, not a
    tolerance."""
    close = FRAMES[frame]()
    masks, eq, shared, mx = _agree(ts_imq_20(close), ts_imq_20(close * k))
    assert masks and eq == shared == FIRED and mx == 0.0


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 60, 250])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_the_power_of_two_rescale_holds_at_other_lengths(length, k):
    close = _walk()
    masks, eq, shared, mx = _agree(ts_imq_20(close, length=length),
                                   ts_imq_20(close * k, length=length))
    assert masks and eq == shared == 1500 - length and mx == 0.0


@pytest.mark.parametrize("frame", sorted(set(FRAMES) - {TIE_FRAME}))
@pytest.mark.parametrize("k", [10.0, 3.7, 0.1])
def test_an_arbitrary_price_rescale_is_within_one_position(frame, k):
    """Not bit-identical BY CONSTRUCTION -- 10a / 10b need not be a / b --
    and bit-identical IN FACT on eight of the nine frames (1,480 of 1,480
    bars on each, measured here, on this CPU). What is ASSERTED is only what
    survives a different CPU: the NaN masks match exactly, every fired bar
    is shared, nothing moves by more than ONE position, and the great
    majority of bars do not move at all. The bit-equality itself is an
    observation, not a contract -- pinning it is what the two-point frame
    below shows to be wrong."""
    close = FRAMES[frame]()
    masks, eq, shared, mx = _agree(ts_imq_20(close), ts_imq_20(close * k))
    assert masks
    assert shared == FIRED
    assert mx <= ONE_POSITION + 1e-12
    assert eq >= 1400


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1])
def test_the_tie_frame_is_the_one_that_moves_and_it_moves_one_position(k):
    """The honest exception, named rather than hidden. On the two-point
    frame every |return| is the same size, so every window's cumulative mass
    lands on the `>= 0.5` threshold and a last-bit change in the returns
    flips the crossing between position 10 and 11. Measured 1,029 / 1,071 /
    1,038 of 1,480 bars bit-equal at x10 / x3.7 / x0.1 on this CPU; what is
    PINNED is that the masks match and that nothing moves by more than ONE
    position (0.05), which is also the largest step this column can take.
    The "it does move" half is deliberately NOT required: a numpy or pandas
    change that made this frame bit-equal would be a strictly better
    outcome and must not turn the suite red."""
    close = _two_point()
    masks, eq, shared, mx = _agree(ts_imq_20(close), ts_imq_20(close * k))
    assert masks
    assert shared == FIRED
    assert mx <= ONE_POSITION + 1e-12


def test_the_column_cannot_see_the_size_of_the_returns():
    """The statistic divides by the window's own total mass, so a positive
    rescale of the RETURNS cancels exactly. This is stronger than a price
    rescale and is what makes the column a position rather than a
    volatility reading."""
    rng = np.random.default_rng(11)
    r = rng.normal(0.0, 0.015, 1500)
    base = ts_imq_20(_from_returns(r))
    for k in (2.0, 0.5, 1e-6):
        masks, eq, shared, mx = _agree(base, ts_imq_20(_from_returns(r * k)))
        assert masks and eq == shared == FIRED and mx == 0.0
    walk = _walk()
    sd = Series(_returns_of(walk), index=walk.index).rolling(LENGTH).std()
    assert abs(_spearman(ts_imq_20(walk), sd)) < 0.2
    assert abs(_spearman(ts_imq_20(walk), walk)) < 0.2


def test_it_is_not_shift_invariant_and_that_is_the_column_working():
    """A SHIFT of the returns changes which bars carry the mass, so it must
    move the column. 639 of 1,480 bars on a walk at `r + 0.004`."""
    rng = np.random.default_rng(11)
    r = rng.normal(0.0, 0.015, 1500)
    base, other = ts_imq_20(_from_returns(r)), ts_imq_20(_from_returns(r
                                                                       + 0.004))
    moved = int((base.dropna() != other.dropna()).sum())
    assert 300 <= moved <= 900, moved


# -------------------------------------------------------------- the guards


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
@pytest.mark.parametrize("at", [0, 1, 19, 200, 398, 399])
def test_a_bad_close_empties_its_windows_and_no_earlier_bar(bad, at):
    """A close that is not a finite, normal, positive float has no return to
    take. It spoils TWO returns, so it empties the `length + 1` = 21 windows
    holding it -- fewer near either end -- and nothing before it moves."""
    close = _walk(400, seed=3)
    base = ts_imq_20(close)
    spoilt = close.copy()
    spoilt.iloc[at] = bad
    got = ts_imq_20(spoilt)
    expected = {0: 1, 1: 2, 19: 20, 200: 21, 398: 2, 399: 1}[at]
    assert int((base.notna() & got.isna()).sum()) == expected
    assert bool((base.iloc[:at].fillna(-9) == got.iloc[:at].fillna(-9)).all())


def test_the_mass_quantile_of_a_single_spike_is_its_own_position():
    """The closed form at the two ends: 19 zero returns then one 1% move
    puts all the mass on the last bar (1.00), and the mirror puts it all on
    the first (0.05). These are the column's extremes."""
    assert float(ts_imq_20(_window_frame([0.0] * 19 + [0.01])).iloc[-1]) == 1.0
    assert float(ts_imq_20(_window_frame([0.01] + [0.0] * 19)).iloc[-1]) \
        == ONE_POSITION


def test_there_is_no_dispersion_floor_and_the_ladder_shows_why():
    """The decision this module makes differently from its siblings. On a
    1%-a-bar ladder the return is mathematically constant and float64
    reproduces it only to rounding; this column reports all 280 windows as
    0.50 or 0.55 -- the two positions adjacent to the exact answer, ONE
    position of jitter -- where the unfloored `ts_medskew_20` statistic
    spans two thirds of its range and `ts_medskew_20` itself therefore
    refuses every window. Adding that floor here would cost 280 honest
    windows and remove no dishonest ones."""
    lad = _ladder()
    col = ts_imq_20(lad).dropna()
    assert int(col.size) == 280
    assert set(np.round(col.unique() * LENGTH).astype(int)) <= {10, 11}
    assert int(ts_medskew_20(lad).notna().sum()) == 0
    un = _unfloored_medskew(lad).dropna()
    assert int(un.size) == 280
    assert float(un.max()) - float(un.min()) > 0.5


def test_the_jitter_is_the_data_s_rounding_and_not_the_module_s():
    """The same ladder with returns of exactly 1.0 -- closes that double --
    has no rounding to jitter on, and reads 0.5 on every window."""
    col = ts_imq_20(_doubling()).dropna()
    assert int(col.size) == 300 - LENGTH
    assert int(col.unique().size) == 1
    assert float(col.iloc[0]) == 0.5


def test_a_quiet_but_honest_frame_is_reported_and_is_within_one_position():
    """Returns of 1e-6 are tiny but real. The column fires on them and
    agrees with the EXACT rational oracle -- which an absolute ulp floor
    would not have let it do. Measured bit-equal on all 580 bars (§G3);
    ASSERTED to one position, because that oracle does not round where the
    module does."""
    quiet = _quiet()
    col = ts_imq_20(quiet)
    assert int(col.notna().sum()) == 600 - LENGTH
    assert int(col.dropna().unique().size) >= 5
    masks, eq, shared, mx = _agree(col, _exact_windowed(quiet))
    assert masks and shared == 600 - LENGTH
    assert mx <= ONE_POSITION + 1e-12


@pytest.mark.parametrize("k", [1e2, 1e6, 1e8, 1e100, 1e300])
def test_a_planted_spike_does_not_reach_a_later_window(k):
    """Locality. Every window is accumulated from its own `length` values,
    so a 1e+300 return at bar 200 leaves all 1,780 bars from 220 on
    BIT-IDENTICAL to the unspiked frame, and its own 20 windows still
    fire."""
    base, spiked = ts_imq_20(_spiked(None)), ts_imq_20(_spiked(k))
    assert int(spiked.iloc[200:220].notna().sum()) == LENGTH
    assert bool((base.iloc[220:].fillna(-9)
                 == spiked.iloc[220:].fillna(-9)).all())


def test_a_return_past_the_bound_empties_only_its_own_windows():
    """Above `max / (2 * length)` the window total could overflow, so the
    return is dropped. That empties the 20 windows holding it and leaves the
    1,780 later bars bit-identical."""
    base, spiked = ts_imq_20(_spiked(None)), ts_imq_20(_spiked(1e307))
    assert int(spiked.iloc[200:220].notna().sum()) == 0
    assert bool((base.iloc[220:].fillna(-9)
                 == spiked.iloc[220:].fillna(-9)).all())


def test_the_global_cumsum_spelling_is_the_one_that_breaks():
    """Why the module accumulates per window instead of differencing one
    global `np.cumsum`: at a 1e+100 spike the two partial sums cancel to
    exactly zero, every later window reads no mass, and all 1,780 bars from
    220 on come back NaN -- bars on which the module itself is
    bit-identical to the unspiked frame."""
    spiked = _spiked(1e100)
    assert int(_global_cumsum_variant(spiked).iloc[220:].notna().sum()) == 0
    assert int(ts_imq_20(spiked).iloc[220:].notna().sum()) == 1780


def test_a_length_below_the_minimum_falls_back_to_the_default():
    """`length` 1 is identically 1.0 -- one value carries all the mass -- so
    anything under `MIN_LENGTH` falls back to 20 rather than shipping a
    constant column."""
    walk = _walk()
    for bad in (None, 0, 1, -5):
        assert ts_imq_20(walk, length=bad).name == f"TS_IMQ_{LENGTH}"
    assert ts_imq_20(walk, length=MIN_LENGTH).name == f"TS_IMQ_{MIN_LENGTH}"


def test_a_frame_shorter_than_the_window_returns_none():
    assert ts_imq_20(_walk(10)) is None


# ---------------------------------------------------- what it overlaps


def test_the_overlap_with_tfcentroid_is_disclosed_and_under_the_strike():
    """The disclosure this port turns on. `TFCENTROID_20` is the
    energy-weighted MEAN position of the same 20 returns where this is the
    absolute-mass MEDIAN position, so the two must correlate -- measured
    pooled +0.8466 over nine frames, per-frame |rho| median 0.8545, max
    0.8857, 0 of 9 at or above 0.90: DISCLOSE_GAP under `r3-perframe-0.90`,
    not STRUCK. The assertion is the BAND, because the exact figure moves
    with the frame set; what would be a finding is a frame crossing 0.90."""
    rhos = []
    for frame in FRAMES:
        close = FRAMES[frame]()
        rhos.append(abs(_spearman(ts_imq_20(close), tf_centroid_20(close))))
    rhos = np.array(rhos)
    assert rhos.max() < 0.90, rhos.max()
    assert 0.70 < np.median(rhos) < 0.90


@pytest.mark.parametrize("other", ["ts_above_mean_20", "ts_medskew_20",
                                   "ts_cid_ce_20", "ts_peaks_20"])
def test_it_does_not_restate_the_fork_s_other_twenty_return_columns(other):
    """Against the fork's other statistics columns over the same 20 returns
    the per-frame |rho| is at most 0.1034 (`TS_CID_CE_20`). They answer
    different questions: how BIG, how SKEWED, how COMPLEX -- this one
    answers WHERE. The band is 0.25, well clear of the 0.1034 and of any
    last-bit movement, and tight enough that a real restatement fails it."""
    fn = {"ts_above_mean_20": ts_above_mean_20,
          "ts_medskew_20": ts_medskew_20,
          "ts_cid_ce_20": ts_cid_ce_20,
          "ts_peaks_20": ts_peaks_20}[other]
    for frame in FRAMES:
        close = FRAMES[frame]()
        col = fn(close)
        assert abs(_spearman(ts_imq_20(close), col)) < 0.25, (other, frame)


def test_it_does_see_the_recency_of_volatility():
    """The other side of the same coin, and why the screen's top comparators
    are the `ATR_Ratio_5_20` family: against `mean|r| over 5 / mean|r| over
    20` the column reads +0.6121 on a walk. That is the question it
    answers, measured rather than asserted."""
    walk = _walk()
    r = Series(np.abs(_returns_of(walk)), index=walk.index)
    ratio = r.rolling(5).mean() / r.rolling(LENGTH).mean()
    assert 0.4 < _spearman(ts_imq_20(walk), ratio) < 0.8


# ------------------------------------------------------------- the wiring


def _ohlcv(n=300, seed=5):
    close = _walk(n, seed)
    return DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]).to_numpy(),
        "high": (close * 1.01).to_numpy(),
        "low": (close * 0.99).to_numpy(),
        "close": close.to_numpy(),
        "volume": np.full(n, 1000.0),
    }, index=date_range("2020-01-01", periods=n, freq="D"))


def test_the_five_wiring_touch_points():
    """A port that misses one computes correctly and is invisible."""
    assert callable(ta.ts_imq_20)
    assert "ts_imq_20" in ta.Category["statistics"]
    df = _ohlcv()
    got = df.ta.ts_imq_20()
    assert got.name == f"TS_IMQ_{LENGTH}"
    assert got.equals(ts_imq_20(df["close"]))


def test_the_accessor_forwards_its_parameters_under_the_right_names():
    """`hasattr` cannot see a keyword forwarded under the wrong name -- the
    `supertrend` failure mode."""
    df = _ohlcv()
    assert df.ta.ts_imq_20(length=5).name == "TS_IMQ_5"
    assert df.ta.ts_imq_20(length=5).equals(ts_imq_20(df["close"], length=5))
    assert df.ta.ts_imq_20(offset=2).equals(ts_imq_20(df["close"], offset=2))


def test_the_offset_shifts_and_nothing_else():
    walk = _walk(300)
    base, shifted = ts_imq_20(walk), ts_imq_20(walk, offset=3)
    assert shifted.equals(base.shift(3))


def test_fillna_fills_the_warm_up():
    col = ts_imq_20(_walk(300), fillna=-1.0)
    assert int(col.isna().sum()) == 0
    assert float(col.iloc[0]) == -1.0


def test_a_bulk_strategy_sweep_reaches_it():
    """`df.ta.strategy()` sweeps `Category`; a name registered there with no
    accessor raises AttributeError for the whole category run."""
    df = _ohlcv()
    df.ta.strategy("statistics", verbose=False, timed=False)
    assert f"TS_IMQ_{LENGTH}" in df.columns


def test_the_category_name_matches_the_module_and_the_column():
    assert ts_imq_20(_walk(100)).category == "statistics"


def test_the_ledger_row_is_this_modules_gate_e_run():
    """Gate E on this column is the launcher's run on THIS module,
    `is99-ts_imq_20-d5aaa69c` (measured 2026-11-14), and NOT the screen of
    2026-10-24, which measured the prototype. The two agree to the printed
    digits -- pooled 0.5254 against `ATR_Ratio_5_20_Pctl` at n = 391,818 --
    which is exactly why the identity of the row needs pinning:
    `tests/test_gate_e_ledger.py` re-derives a row's `module_sha1` and
    output fingerprint from the tree and checks its verdict arithmetic, but
    it cannot see WHOSE measurement a row came from.

    This test replaced `test_the_gate_e_row_is_owed`, which asserted the row
    was ABSENT and so failed the moment the receipt session recorded it."""
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    rows = [r for r in rows if r["indicator"] == "ts_imq_20"]
    assert len(rows) == 1
    row = rows[0]
    assert row["module"] == "pandas_ta.statistics.ts_imq_20"
    assert row["column"] == f"TS_IMQ_{LENGTH}"
    assert row["run"] == "is99-ts_imq_20-d5aaa69c"
    assert row["verdict"] == "SHIP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    assert float(row["max_abs_rho"]) < 0.76
    assert float(row["perframe_max_median_abs_rho"]) < 0.90
    assert 0 < int(row["non_nan"]) < int(row["pooled_bars"])
