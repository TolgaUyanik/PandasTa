# -*- coding: utf-8 -*-
"""`ts_kurt_60` — excess kurtosis of 60 returns (PandasTa issue #93).

What this module pins, in order of how much it would hurt to lose. Every
number here was produced by a run in this repository: `python
docs/measure_ts_kurt_60.py` prints all of them, and
`docs/TsKurt60Measured.md` is the receipt.

1. **The port IS the screened prototype where both fire.** The module keeps
   pandas' `rolling(length).kurt()` as the arithmetic, so it is bit-equal to
   `ret(c).rolling(60).kurt()` on **1440/1440** bars on each of a walk, a
   tick-rounded walk and a student-t path — six comparisons, all six run:
   against the prototype retyped here, and against the owner's own registry
   entry imported from `docs/issues/screen/ind_screen.py` when that
   (gitignored) tree is present. That is why issue #93's screen figures were
   indicative for this column rather than a receipt — and Gate E on THIS
   module (`is93-ts_kurt_60-049a1889`, 2026-11-13) then returned them to
   every digit the issue printed: 0.2501241324996995 vs `ZIGZAG`,
   n = 33,246, per-frame max median 0.2334651987740327, SHIP. That run, not
   the screen's, is the receipt
   (`test_the_ledger_row_is_this_modules_gate_e_run`).

   Where the two part company is the NaN discipline, and it is measured
   rather than glossed: a window of IDENTICAL returns slips through pandas'
   own degenerate test and reads exactly **-3.0** — below this statistic's
   algebraic floor of -2.0702, so not a value the column can otherwise take.
   240 of 300 bars of a flat frame, and 10 bars of a 70-bar flat run planted
   in a walk.

2. **Gate A by closed form and by four independent spellings, starting with
   the one the source names.** tsfresh's `kurtosis` is
   `pandas.Series.kurtosis` = `nanops.nankurt`, a TWO-PASS function and not
   the online one behind `rolling.kurt`; it is run window by window and
   agrees with this column to 5.3e-15 / 4.0e-15 / 8.5e-14 on three frames.
   Then a numpy two-pass form, the textbook `ddof=1` spelling, a plain-Python
   `math.fsum` loop, and an EXACT rational oracle in `fractions.Fraction`.
   Against that oracle the five spellings sit within a factor of 1.5 of each
   other; the `fsum` loop is the closest on all three frames and
   `rolling.kurt` is within 1.31× of it — so the simpler spelling is not
   MATERIALLY less accurate here, which is the claim, not that it is the best.

   The two windows whose value is derivable are pinned: a one-hot window
   reads the ceiling `n` (60.0, module 1.4e-14 under it) and an alternating
   window reads the floor `-2(n-1)/(n-3)` (-2.070175438596491, bit-exact on
   most bars). Both bounds hold at `length` 4 too (4.0 and -6.0, exactly),
   and the sharp bound on the BIASED ratio is `(n²-3n+3)/(n-1)` = 58.016949,
   not `n` — the correction is what maps it to exactly `n`.

   Four open readings are priced, not assumed: simple vs log returns
   (Spearman 0.998596, max |difference| 0.2526), the corrected G2 vs the
   biased g2 (an exact affine map at fixed `length`: Spearman 1.000000 and
   the rebuild agrees to 5.3e-15), excess vs raw (exactly +3), and 60
   RETURNS vs 60 CLOSES (0.992198). It is also NOT the fork's existing
   `kurtosis`, which takes the same moment of the CLOSE: Spearman -0.0847 at
   length 60.

3. **Gate B, by mutant, on three frames and three further lengths.** Five
   mutants, each `importlib`-read and `exec`'d in memory: the column
   back-dated by 2 bars; back-dated by `length - 1`; the return stamped one
   bar early; the window rolled `length // 2` bars into the future; the
   window centred. All **15 cells are 36/36** and the real module leaks
   **0/36** in all six configurations.

   A SIXTH mutant is reported separately because the sweep cannot see it:
   the degeneracy guard read one bar ahead changes the column but is caught
   **0/36** on all three frames, since the guard empties no window there. On
   a frame with a 70-bar flat run planted in it the guard empties 10 windows
   and the mutant is caught. The limit is asserted, so nobody can read the
   0/36 as a pass.

4. **Gate D is stronger than the ×8 line, and its limit is asserted.** Every
   input is a price ratio, so ×8/×64 are bit-identical on 1440/1440 bars of
   each of three frames and at `length` 20/120/250/4. ×10 and ×3.7 are NOT
   bit-identical — a fourth moment amplifies a last-bit change in a return —
   but the NaN masks match and the values agree to 1.2e-13 at Spearman
   1.000000.

5. **What the column is blind to, where a consumer reads first.** It is
   scale-free in the RETURNS, not just in the price: ×0.5/×2/×3 of the
   returns and +0.004 of log drift a bar all leave it at Spearman 1.000000
   (max |difference| 9.3e-14). So it is not volatility (Spearman 0.0505
   against the window's own sd) and close to a single-outlier reading
   (0.8698 against `max|r - mean| / sd`). One +10σ return takes the 60
   windows holding it to a median of 22.1696 against the frame's -0.1283.

6. **The guards, including the one that keeps the NaN damage local.** A bad
   close (NaN, inf, zero, negative, subnormal) empties the 61 windows it sits
   in and moves nothing before it; a close pair whose ratio overflows empties
   60. The fourth-power guard is load-bearing, not belt-and-braces:
   `rolling.kurt` accumulates raw power sums ONLINE, so without that line a
   single 1.0e+102 return empties **199** bars of a 400-bar walk — the whole
   remainder of the frame — against **61** with it. The output `isfinite`
   mask is live even after it, because a return whose own r⁴ is finite can
   overflow the window SUM: measured, 1 bar at `close[201] = 1e-200 * 1e77`.

⚠ Gate C in THIS FILE is synthetic. The real-data counts come from Gate E's
run `is93-ts_kurt_60-049a1889` (2026-11-13) and are pinned from the ledger by
`test_the_ledger_row_carries_the_measured_gate_e_numbers`: `TS_KURT_60` fires
on 393,509 of 398,849 pooled bars, all 393,509 non-zero, and the 5,340 NaN
bars are exactly 60 × 89 — the warm-up, so the degeneracy floor and the
fourth-power guard emptied no window on the 89 BIST frames.
"""
import importlib
import math
import types
from fractions import Fraction

import numpy as np
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.ts_kurt_60 import ts_kurt_60

LENGTH = 60
_REAL = importlib.import_module("pandas_ta.statistics.ts_kurt_60")


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _zigzag_returns(n=1500, size=0.5):
    """Every 60-return window holds 30 of each value, the configuration that
    attains the column's algebraic minimum."""
    return _from_returns(np.where(np.arange(n) % 2 == 0, size, -size))


def _one_hot_returns(n=1500, length=LENGTH, size=1.0):
    """Returns are 0 except every `length`-th bar, so the window ending on
    such a bar is one-hot -- the configuration that attains the maximum."""
    r = np.zeros(n)
    r[length::length] = size
    return _from_returns(r)


def _flat_run_planted(n=400, seed=19, at=200, run=70):
    close = _walk(n, seed=seed).to_numpy().copy()
    close[at:at + run] = close[at]
    return Series(close)


def _flat(n=300, value=100.0):
    return Series(np.full(n, value))


# ----------------------------------------------------------------- oracles


def _bound_max(n):
    """One-hot: `m4/m2**2 = (n**2-3n+3)/(n-1)`, and

        G2 = [(n+1)(n**2-3n+3) - 3(n-1)**2] / ((n-2)(n-3))
           = n(n-2)(n-3) / ((n-2)(n-3)) = n
    """
    return float(n)


def _bound_min(n):
    """Two values in equal counts: `m4/m2**2 = 1`, so `g2 = -2` and
    `G2 = -2(n-1)/(n-3)`."""
    return -2.0 * (n - 1) / (n - 3)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_kurt_60`, retyped
    because that tree is gitignored:

        def _(o, h, l, c, v): return ret(c).rolling(60).kurt()

    with `ret(c) = c / c.shift(1) - 1`."""
    return (close / close.shift(1) - 1).rolling(length).kurt()


def _screen_candidate():
    """The screen's own registry entry, when this worktree has `docs/issues/`
    (gitignored, so a clone does not)."""
    import importlib.util
    import os
    import sys

    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "docs", "issues", "screen",
        "ind_screen.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen_kurt", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen_kurt"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_kurt_60"]["fn"]


def _numpy_two_pass(close, length=LENGTH, guard=True, log_returns=False,
                    biased=False, raw=False, closes_window=False):
    """The statistic from the CENTRED moments in numpy, two passes -- no
    `rolling.kurt` and no online raw-moment recursion, so it shares no
    arithmetic with the module. One keyword switches one reading."""
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    r = np.full(c.size, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        if log_returns:
            r[1:] = np.log(c[1:] / c[:-1])
        else:
            r[1:] = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = length - 1 if closes_window else length
    windows = sliding_window_view(r, n)
    mean = windows.mean(axis=1)
    with np.errstate(over="ignore", invalid="ignore"):
        d = windows - mean[:, None]
        m2 = (d * d).mean(axis=1)
        m4 = (d ** 4).mean(axis=1)
        spread = windows.max(axis=1) - windows.min(axis=1)
        m2 = (np.where(spread > _REAL.NOISE_FLOOR, m2, np.nan) if guard
              else np.where(m2 != 0.0, m2, np.nan))
        g2 = m4 / (m2 * m2) - 3.0
        value = g2 if biased else (((n + 1.0) * g2 + 6.0) * (n - 1.0)
                                   / ((n - 2.0) * (n - 3.0)))
        if raw:
            value = value + 3.0
    out = np.full(c.size, np.nan)
    out[n - 1:] = np.where(np.isfinite(value), value, np.nan)
    return Series(out, index=close.index)


def _series_kurtosis_spelling(close, length=LENGTH):
    """The LITERAL tsfresh spelling: `pandas.Series.kurtosis` window by
    window. tsfresh's `feature_calculators.kurtosis(x)` is
    `pandas.Series(x).kurtosis()`, which inside pandas is `nanops.nankurt` --
    a TWO-PASS centred-moment function, a different implementation from the
    online `rolling.kurt` this module ships."""
    r = close / close.shift(1) - 1.0
    return r.rolling(length, min_periods=length).apply(
        lambda w: Series(w).kurtosis(), raw=False)


def _unbiased_spelling(close, length=LENGTH):
    """The textbook `ddof=1` form:
    `n(n+1)/((n-1)(n-2)(n-3)) * sum(d**4)/s**4 - 3(n-1)**2/((n-2)(n-3))`."""
    r = (close / close.shift(1) - 1).to_numpy(dtype=float)
    out = np.full(r.size, np.nan)
    n = float(length)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        if not (w.max() - w.min()) > _REAL.NOISE_FLOOR:
            continue
        d = w - w.mean()
        s2 = float((d * d).sum()) / (n - 1.0)
        out[t] = (n * (n + 1.0) / ((n - 1.0) * (n - 2.0) * (n - 3.0))
                  * float((d ** 4).sum()) / (s2 * s2)
                  - 3.0 * (n - 1.0) ** 2 / ((n - 2.0) * (n - 3.0)))
    return Series(out, index=close.index)


def _scalar_loop(close, length=LENGTH):
    """Plain Python, `math.fsum` so the accumulation is exact."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    n = float(length)
    for t in range(length, len(c)):
        w = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        if not all(math.isfinite(v) for v in w):
            continue
        if not (max(w) - min(w)) > _REAL.NOISE_FLOOR:
            continue
        mean = math.fsum(w) / n
        m2 = math.fsum((v - mean) ** 2 for v in w) / n
        m4 = math.fsum((v - mean) ** 4 for v in w) / n
        g2 = m4 / (m2 * m2) - 3.0
        out[t] = ((n + 1.0) * g2 + 6.0) * (n - 1.0) / ((n - 2.0) * (n - 3.0))
    return Series(out, index=close.index)


def _exact_loop(close, length=LENGTH):
    """EXACT rational arithmetic on the same float64 closes: the true value
    of these inputs, rounded once at the end."""
    c = [Fraction(float(v)) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    n = Fraction(length)
    for t in range(length, len(c)):
        w = [c[i] / c[i - 1] - 1 for i in range(t - length + 1, t + 1)]
        if not float(max(w) - min(w)) > _REAL.NOISE_FLOOR:
            continue
        mean = sum(w) / n
        d = [v - mean for v in w]
        m2 = sum(x * x for x in d) / n
        m4 = sum(x ** 4 for x in d) / n
        g2 = m4 / (m2 * m2) - 3
        out[t] = float(((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3)))
    return Series(out, index=close.index)


def _shared(a, b):
    m = a.notna() & b.notna()
    return a[m], b[m]


# ------------------------------------------------------------- Gate A


def test_the_one_hot_window_reads_the_ceiling_which_is_exactly_the_length():
    """`1 <= m4/m2**2 <= (n**2-3n+3)/(n-1)` -- 58.016949 at n = 60, attained
    by a one-hot window. `<= n` is also true but slack, and no window attains
    it; the sample correction is what maps the SHARP bound to exactly `n`.

    The frame plants a +1 return every 60 bars, so EVERY 60-return window
    holds exactly one of them and is one-hot: all 1,440 fired bars read
    59.999999999999986, 1.4e-14 under the ceiling (`m2 = 59/3600` is not
    dyadic, so it rounds) and none above it. The 24 windows whose spike is
    their newest return are checked separately, because that is the one
    position a window-indexing bug would move."""
    col = ts_kurt_60(_one_hot_returns())
    fired = col.dropna()
    assert len(fired) == 1440
    assert float((fired - _bound_max(LENGTH)).abs().max()) < 1e-13
    assert bool((fired <= _bound_max(LENGTH)).all())
    assert float(fired.max()) == pytest.approx(_bound_max(LENGTH), abs=1e-12)
    hot = col.iloc[[b for b in range(LENGTH, 1500) if b % LENGTH == 0]].dropna()
    assert len(hot) == 24
    assert float((hot - _bound_max(LENGTH)).abs().max()) < 1e-13


def test_the_alternating_window_reads_the_floor_bit_exactly_on_most_bars():
    """Two values in equal counts give `m4/m2**2 = 1`, so `g2 = -2` and
    `G2 = -2(n-1)/(n-3)` = -2.070175438596491. Every 60-return window of a
    +-0.5 zigzag holds 30 of each, and the module reads the floor on all
    1,440 of them -- bit-exactly on 1,195 (pinned as a majority, since the
    last bit is a CPU-float detail)."""
    zig = ts_kurt_60(_zigzag_returns()).dropna()
    floor = _bound_min(LENGTH)
    assert len(zig) == 1440
    assert float((zig - floor).abs().max()) <= 1e-15
    assert int((zig == floor).sum()) > 1000
    assert bool((zig >= floor - 1e-15).all())


@pytest.mark.parametrize("length", [4, 10, 20, 60, 120, 250])
def test_the_shipped_column_stays_inside_the_two_bounds_at_every_length(
        length):
    """The bounds on the COLUMN, not on the formula: a 3,000-bar
    student-t(1.5) path run through the module at six lengths, asserting that
    the column's own min and max are inside [floor, ceiling]. How CLOSE it
    gets to either is not claimed here -- §A1 of the receipt measures that on
    the two windows built to attain them."""
    rng = np.random.default_rng(17 + length)
    r = np.clip(0.02 * rng.standard_t(1.5, 3000), -0.9, 0.9)
    fired = ts_kurt_60(_from_returns(r), length=length).dropna()
    assert len(fired) == 3000 - length
    assert float(fired.min()) >= _bound_min(length) - 1e-9
    assert float(fired.max()) <= _bound_max(length) + 1e-9


@pytest.mark.parametrize("length", [4, 10, 20, 60, 120, 250])
def test_the_closed_form_bounds_hold_for_the_formula_too(length):
    """The same two bounds checked against the FORMULA on 2,000 independent
    student-t(1.5) windows per length -- no price path, so this one is about
    the algebra and not about the module (the test above is the module's)."""
    rng = np.random.default_rng(17 + length)
    draws = rng.standard_t(1.5, size=(2000, length))
    d = draws - draws.mean(axis=1, keepdims=True)
    m2 = (d * d).mean(axis=1)
    m4 = (d ** 4).mean(axis=1)
    # The sharp bound on the BIASED ratio is (n^2-3n+3)/(n-1), not n: the
    # sample correction is what maps it to exactly n.
    ratio = m4 / (m2 * m2)
    assert ratio.max() <= (length ** 2 - 3 * length + 3) / (length - 1) + 1e-9
    assert ratio.min() >= 1.0 - 1e-9
    g2 = ratio - 3.0
    g = (((length + 1.0) * g2 + 6.0) * (length - 1.0)
         / ((length - 2.0) * (length - 3.0)))
    assert g.min() >= _bound_min(length) - 1e-9
    assert g.max() <= _bound_max(length) + 1e-9


@pytest.mark.parametrize("builder,values,length,expected", [
    # one-hot at n=4: closes [1,1,1,1,2] give returns [0,0,0,+1]
    (Series, [1.0, 1.0, 1.0, 1.0, 2.0], 4, 4.0),
    # alternating at n=4: returns [+1/2,-1/2,+1/2,-1/2]
    (_from_returns, [0.0, 0.5, -0.5, 0.5, -0.5], 4, -6.0),
])
def test_the_two_bounds_are_exact_at_the_smallest_allowed_length(builder,
                                                                 values,
                                                                 length,
                                                                 expected):
    """At length 4 both constructions are exactly representable, so the
    module hits them to the last bit: 4.0 and -6.0, which are `n` and
    `-2(n-1)/(n-3)`."""
    out = ts_kurt_60(builder(values), length=length)
    assert float(out.iloc[-1]) == expected
    assert out.name == f"TS_KURT_{length}"


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _heavy_tailed])
def test_the_port_is_bit_equal_to_the_retyped_screen_prototype(frame_fn):
    """The module keeps pandas' `rolling.kurt`, so where both fire the port
    and `ret(c).rolling(60).kurt()` are the same arithmetic: 1440/1440 bars
    on each of three frames, NaN masks equal."""
    close = frame_fn()
    mine, theirs = ts_kurt_60(close), _prototype(close)
    assert bool((mine.isna() == theirs.isna()).all())
    a, b = _shared(mine, theirs)
    assert len(a) == 1440
    assert int((a == b).sum()) == 1440


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _heavy_tailed])
def test_the_port_is_bit_equal_to_the_screens_own_registry_candidate(frame_fn):
    """Not a retype: `REG["ts_kurt_60"]["fn"]` loaded out of
    `docs/issues/screen/ind_screen.py`, on the same three frames as the
    retyped comparison. Skipped in a clone, where that tree is absent (it is
    gitignored)."""
    fn = _screen_candidate()
    if fn is None:
        pytest.skip("docs/issues/screen/ind_screen.py is not in this tree")
    close = frame_fn()
    theirs = Series(fn(close, close, close, close,
                       Series(np.ones(len(close)))))
    mine = ts_kurt_60(close)
    assert bool((mine.isna() == theirs.isna()).all())
    a, b = _shared(mine, theirs)
    assert len(a) == 1440
    assert int((a == b).sum()) == 1440


@pytest.mark.parametrize("frame_fn,label", [
    (_flat, "flat 300 closes"),
    (_flat_run_planted, "a 70-bar flat run planted in a walk"),
])
def test_the_prototype_reads_minus_three_where_this_port_refuses(frame_fn,
                                                                 label):
    """The one place the two are NOT the same function. A window of IDENTICAL
    returns slips through pandas' own degenerate test and reads exactly
    -3.0 -- below this statistic's floor of -2.0702, so not a value the
    column can otherwise take. Measured: 240 of 300 bars of a flat frame and
    10 bars of the planted frame."""
    close = frame_fn()
    mine, theirs = ts_kurt_60(close), _prototype(close)
    extra = theirs[mine.isna() & theirs.notna()]
    assert len(extra) == (240 if frame_fn is _flat else 10), label
    assert bool((extra == -3.0).all())
    # -3.0 sits BELOW the statistic's own floor, so a consumer could not even
    # have read it as a degenerate flag.
    assert -3.0 < _bound_min(LENGTH)
    assert _bound_min(LENGTH) == pytest.approx(-2.070175438596491, abs=1e-15)


@pytest.mark.parametrize("frame_fn,tolerance", [
    (_walk, 1e-14), (_tick_rounded, 1e-14), (_heavy_tailed, 1e-12),
])
def test_the_function_the_source_names_agrees(frame_fn, tolerance):
    """The oracle it would have been easy not to run: tsfresh's `kurtosis(x)`
    is `pandas.Series(x).kurtosis()`, which inside pandas is
    `nanops.nankurt` -- a TWO-PASS centred-moment function, a different
    implementation from the online one behind `rolling.kurt`. Applied window
    by window it agrees with this column to 5.3e-15 on a walk, 4.0e-15
    tick-rounded and 8.5e-14 on a student-t path, with NaN masks equal.

    Where it does NOT agree is the degenerate window, and that divergence is
    pinned in `test_the_three_spellings_of_the_source_disagree_on_a_flat_frame`
    rather than left to this tolerance."""
    close = frame_fn()
    mine, theirs = ts_kurt_60(close), _series_kurtosis_spelling(close)
    assert bool((mine.isna() == theirs.isna()).all())
    a, b = _shared(mine, theirs)
    assert len(a) == 1440
    assert float((a - b).abs().max()) < tolerance
    assert float(a.corr(b, method="spearman")) == pytest.approx(1.0, abs=1e-9)


def test_the_three_spellings_of_the_source_disagree_on_a_flat_frame():
    """Two spellings of the SAME named source give two different answers on a
    window of identical returns, and neither is NaN: `rolling.kurt` reads
    exactly -3.0 (below this column's floor of -2.0702) and
    `Series.kurtosis` exactly 0.0 (the value a gaussian would score, so
    indistinguishable from an ordinary reading). Both report on 240 of 300
    bars; this column reports on none. That is the argument for the module
    deciding the degenerate case instead of inheriting it.

    The 0.0 is readable in pandas rather than only measured:
    `pandas/core/nanops.py:1361-1370` passes `(n-2)(n-3)*sum(d**2)` through
    `_zero_out_fperr` (line 1581, which zeroes any magnitude below 1e-14) and
    returns 0 for a zero denominator."""
    flat = _flat()
    assert int(ts_kurt_60(flat).notna().sum()) == 0
    rolling_form = _prototype(flat).dropna()
    series_form = _series_kurtosis_spelling(flat).dropna()
    assert len(rolling_form) == 240 and len(series_form) == 240
    assert bool((rolling_form == -3.0).all())
    assert bool((series_form == 0.0).all())
    assert -3.0 < _bound_min(LENGTH) < 0.0


@pytest.mark.parametrize("oracle,frame_fn,tolerance", [
    (_numpy_two_pass, _walk, 1e-14),
    (_numpy_two_pass, _tick_rounded, 1e-14),
    (_numpy_two_pass, _heavy_tailed, 1e-12),
    (_unbiased_spelling, _walk, 1e-14),
])
def test_three_independent_spellings_of_the_definition_agree(oracle, frame_fn,
                                                             tolerance):
    """None of these shares arithmetic with `rolling.kurt`: the first takes
    two passes over the centred moments in numpy, the second is the textbook
    `ddof=1` form. Measured max |difference|: 5.3e-15 / 4.3e-15 / 9.9e-14 /
    6.0e-15, Spearman 1.000000, NaN masks equal."""
    close = frame_fn()
    mine, theirs = ts_kurt_60(close), oracle(close)
    assert bool((mine.isna() == theirs.isna()).all())
    a, b = _shared(mine, theirs)
    assert len(a) == 1440
    assert float((a - b).abs().max()) < tolerance
    assert float(a.corr(b, method="spearman")) == pytest.approx(1.0, abs=1e-9)


def test_a_plain_python_scalar_loop_agrees():
    """No numpy, no rolling window, `math.fsum` so its accumulation is exact.
    340 fired bars of a 400-bar walk, max |difference| 2.8e-15."""
    close = _walk(400, seed=21)
    mine, theirs = ts_kurt_60(close), _scalar_loop(close)
    assert bool((mine.isna() == theirs.isna()).all())
    a, b = _shared(mine, theirs)
    assert len(a) == 340
    assert float((a - b).abs().max()) < 1e-14


#: The module with its fourth-power guard removed entirely, and with only its
#: SUM bound removed. Used to price that guard; neither is a causality mutant.
NO_FOURTH_GUARD = (
    """    with np.errstate(over="ignore"):
        fourth = np.square(np.square(r.to_numpy()))
    r = r.where(fourth < np.finfo(float).max / (2 * length))""",
    "    pass  # fourth-power guard removed")
TERM_ONLY_GUARD = (
    "    r = r.where(fourth < np.finfo(float).max / (2 * length))",
    "    r = r.where(np.isfinite(fourth))")


def _emptied(out, base, n):
    return [i for i in range(n)
            if out.isna().iloc[i] and not base.isna().iloc[i]]


def test_the_fourth_power_guard_is_what_keeps_the_nan_damage_window_local():
    """`rolling.kurt` accumulates the raw power sums ONLINE, so an infinite
    sum of fourth powers never leaves the accumulator and every LATER bar
    comes back NaN. Measured on a 400-bar walk with closes `1e-200` then
    `1e-200 * 1e100` planted at bars 200/201 (returns of 1.0e+100 and
    1.0e+102): without the guard the module empties 199 bars, 201..399 -- the
    whole remainder of the frame -- and with it 61, bars 201..261, which is
    the `length + 1` locality every other NaN case in this module obeys (61
    rather than 60 because the pair spoils two returns).

    Pinned because it is the difference between 'a bad bar costs a window'
    and 'a bad bar costs the rest of the series', and because the guard is a
    few lines a later reader could take for belt-and-braces."""
    close = _walk(400, seed=19)
    base = ts_kurt_60(close)
    p = close.copy()
    p.iloc[200] = 1e-200
    p.iloc[201] = 1e-200 * 1e100
    loose = _load_mutant(*NO_FOURTH_GUARD).ts_kurt_60(p)
    guarded = ts_kurt_60(p)
    assert _emptied(loose, base, len(p)) == list(range(201, 400))
    assert _emptied(guarded, base, len(p)) == list(range(201, 262))
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(loose).sum()) == 0  # the output mask catches both


def test_the_guard_bounds_the_window_SUM_not_just_the_single_term():
    """Why the guard is `fourth < max/(2*length)` and not `isfinite(fourth)`.

    TWO returns of 1.0e+77 planted 30 bars apart share a 60-return window.
    Each one's fourth power is 1.0e+308 -- finite -- so a term-only guard
    keeps both, their sum overflows, and the online accumulator poisons every
    later bar: measured, 199 emptied bars (201..399) against the shipped
    guard's 91 (201..291, the union of the two 61-bar spans). The sum bound
    makes the locality structural: every kept return satisfies
    `r**4 < max/(2*length)`, so a window of `length` of them sums to under
    half the float maximum -- the factor two being headroom for the
    accumulation's rounding and for pandas multiplying `val` four times where
    this tests one power."""
    close = _walk(400, seed=19)
    base = ts_kurt_60(close)
    p = close.copy()
    for at in (200, 230):
        p.iloc[at] = 1e-200
        p.iloc[at + 1] = 1e-123
    with np.errstate(over="ignore"):
        powers = np.sort((p / p.shift(1) - 1.0).abs().to_numpy()) ** 4
    finite = powers[np.isfinite(powers)]
    assert float(finite.max()) == pytest.approx(1.0e308, rel=1e-3)
    assert finite.max() < np.finfo(float).max               # each is finite
    assert finite.max() > np.finfo(float).max / 2           # the sum is not
    # ... and the shipped per-term ceiling rejects them by a wide margin.
    assert finite.max() > np.finfo(float).max / (2 * LENGTH)
    term_only = _load_mutant(*TERM_ONLY_GUARD).ts_kurt_60(p)
    guarded = ts_kurt_60(p)
    assert _emptied(term_only, base, len(p)) == list(range(201, 400))
    assert _emptied(guarded, base, len(p)) == list(range(201, 292))
    assert int(np.isinf(guarded).sum()) == 0


def test_rolling_kurt_is_as_accurate_as_the_alternatives_on_returns():
    """The question the online raw-moment form raises, answered by an EXACT
    rational oracle rather than by argument: every float64 close is a
    rational, so the whole statistic is.

    On a 140-bar walk (80 fired bars) `rolling.kurt` and the numpy two-pass
    form sit within a factor of 1.5 of the true value of their own inputs and
    of each other. The fuller run in docs/measure_ts_kurt_60.py puts the
    plain-Python `fsum` loop -- whose accumulation is exact by construction --
    closest of FIVE spellings on all three frames, with `rolling.kurt` within
    1.31x of it (6.994e-15 vs 6.509e-15 on a walk, 8.341 vs 7.820
    tick-rounded, 6.040e-14 vs 4.619e-14 on the student-t path, where this
    spelling is the WORST of the five). So the claim behind keeping the
    simpler spelling is "not materially less accurate", never "most
    accurate". It says nothing about `rolling.kurt` on a price LEVEL, where
    the same cancellation is a real hazard; this column is of returns."""
    close = _walk(140, seed=31)
    exact = _exact_loop(close)
    mine = ts_kurt_60(close)
    twopass = _numpy_two_pass(close)
    m = exact.notna() & mine.notna()
    assert int(m.sum()) == 80
    mine_err = float((mine[m] - exact[m]).abs().max())
    two_err = float((twopass[m] - exact[m]).abs().max())
    assert mine_err < 1e-13
    assert two_err < 1e-13
    assert mine_err < 10 * two_err and two_err < 10 * mine_err


# -------------------------------------------------- Gate A5, open readings


def test_log_returns_are_a_different_column_and_differ_where_it_matters():
    """Spearman 0.998596 and max |difference| 0.2526 on a walk -- close, but
    not a rank relabelling, and the 10 bars of largest disagreement all sit
    above 1.8, i.e. where this column is interesting."""
    close = _walk()
    mine = ts_kurt_60(close)
    theirs = _numpy_two_pass(close, log_returns=True)
    a, b = _shared(mine, theirs)
    assert float((a - b).abs().max()) == pytest.approx(0.2526, abs=1e-3)
    assert float(a.corr(b, method="spearman")) == pytest.approx(0.998596,
                                                                abs=1e-5)
    worst = (a - b).abs().nlargest(10).index
    assert float(mine.loc[worst].min()) > 1.8


def test_the_bias_correction_is_an_exact_affine_map_of_the_biased_g2():
    """`((n+1)*g2 + 6)*(n-1)/((n-2)*(n-3))` rebuilds the column to 5.3e-15,
    so for a FIXED length the choice is invisible to a rank miner (Spearman
    1.000000) and visible to a threshold (they differ by up to 0.3315)."""
    close = _walk()
    mine = ts_kurt_60(close)
    g2 = _numpy_two_pass(close, biased=True)
    a, b = _shared(mine, g2)
    rebuilt = ((LENGTH + 1.0) * b + 6.0) * (LENGTH - 1.0) / ((LENGTH - 2.0)
                                                             * (LENGTH - 3.0))
    assert float((rebuilt - a).abs().max()) < 1e-13
    assert float(a.corr(b, method="spearman")) == pytest.approx(1.0, abs=1e-9)
    assert float((a - b).abs().max()) == pytest.approx(0.3315, abs=1e-3)


def test_excess_kurtosis_differs_from_the_raw_form_by_exactly_three():
    """The issue says *excess*; the raw (Pearson) form is this column plus a
    constant, so Spearman 1.000000 and a flat 3.0 gap."""
    close = _walk()
    a, b = _shared(ts_kurt_60(close), _numpy_two_pass(close, raw=True))
    assert float((b - a).max()) == pytest.approx(3.0, abs=1e-12)
    assert float((b - a).min()) == pytest.approx(3.0, abs=1e-12)


def test_sixty_returns_not_sixty_closes():
    """The off-by-one a reader makes, priced rather than re-argued: 59
    returns is Spearman 0.992198 against this column, max |difference|
    1.0212, and its NaN mask is one bar shorter."""
    close = _walk()
    mine = ts_kurt_60(close)
    theirs = _numpy_two_pass(close, closes_window=True)
    assert int(mine.isna().sum()) == LENGTH
    assert int(theirs.isna().sum()) == LENGTH - 1
    a, b = _shared(mine, theirs)
    assert float(a.corr(b, method="spearman")) == pytest.approx(0.992198,
                                                                abs=1e-5)
    assert float((a - b).abs().max()) == pytest.approx(1.0212, abs=1e-3)


@pytest.mark.parametrize("length,rho", [(60, -0.0847), (30, -0.1090)])
def test_it_is_not_the_forks_kurtosis_of_the_close(length, rho):
    """`kurtosis` takes the same moment of the price LEVEL, which reads the
    shape of a trend rather than of a return distribution. Spearman -0.0847
    at length 60 and -0.1090 at its default 30, on the same walk."""
    close = _walk()
    a, b = _shared(ts_kurt_60(close), pandas_ta.kurtosis(close, length=length))
    assert float(a.corr(b, method="spearman")) == pytest.approx(rho, abs=1e-4)


# ------------------------------------------------------------- Gate B

BACK_DATE_TWO = (
    "    tskurt = kurt.where(spread > NOISE_FLOOR)",
    "    tskurt = kurt.where(spread > NOISE_FLOOR).shift(-2)")
BACK_DATE_FULL = (
    "    tskurt = kurt.where(spread > NOISE_FLOOR)",
    "    tskurt = kurt.where(spread > NOISE_FLOOR).shift(-(length - 1))")
FORWARD_RETURN = (
    "        r = px / px.shift(1) - 1.0",
    "        r = px.shift(-1) / px - 1.0")
ROLLED_WINDOW = (
    "    kurt = rolling.kurt()",
    "    kurt = r.shift(-(length // 2)).rolling(length, "
    "min_periods=length).kurt()")
CENTERED_WINDOW = (
    "    rolling = r.rolling(length, min_periods=length)",
    "    rolling = r.rolling(length, min_periods=length, center=True)")
FORWARD_SPREAD_ONE = (
    "    spread = rolling.max() - rolling.min()",
    "    spread = (rolling.max() - rolling.min()).shift(-1)")

MUTANTS = [BACK_DATE_TWO, BACK_DATE_FULL, FORWARD_RETURN, ROLLED_WINDOW,
           CENTERED_WINDOW]
MUTANT_IDS = ["back_date_two", "back_date_full", "forward_return",
              "rolled_window", "centered_window"]
OFFSETS = range(80, 1500, 40)  # 36 offsets, past the 60-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_kurt_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, offsets=OFFSETS):
    """Replace every bar from J onward with a different path; return the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = []
    for j in offsets:
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


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _caught(ts_kurt_60, close, other) == []


@pytest.mark.parametrize("index", range(len(MUTANTS)),
                         ids=MUTANT_IDS)
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_each_mutant_is_caught_on_each_frame(index, frame):
    """All fifteen cells are 36/36 -- the column is continuous and every bar
    of the window enters the mean, so there is no discrete absorption of the
    kind `ts_binent_20` and `ts_peaks_20` had to measure around."""
    mod = _load_mutant(*MUTANTS[index])
    close, other = FRAMES[frame]
    assert not mod.ts_kurt_60(close).equals(ts_kurt_60(close))  # live mutant
    assert len(_caught(mod.ts_kurt_60, close, other)) == len(list(OFFSETS))


#: (mutant index, length, caught, missed offsets)
NON_DEFAULT = [
    (0, 20, 36, []), (0, 120, 35, [80]), (0, 4, 36, []),
    (1, 20, 36, []), (1, 120, 36, []), (1, 4, 36, []),
    (2, 20, 36, []), (2, 120, 35, [80]), (2, 4, 36, []),
    (3, 20, 36, []), (3, 120, 34, [80, 120]), (3, 4, 36, []),
    (4, 20, 36, []), (4, 120, 36, []), (4, 4, 36, []),
]


@pytest.mark.parametrize("index,length,caught,miss", NON_DEFAULT,
                         ids=[f"{MUTANT_IDS[i]}-{n}"
                              for i, n, _, _ in NON_DEFAULT])
def test_the_mutants_at_non_default_lengths(index, length, caught, miss):
    """`length` is user-reachable and the sweep above runs the default only.
    The real module leaks 0/36 at every one of them. Three cells are not
    36/36 and all three are at `length=120`, where J = 80 and J = 120 sit
    inside or barely past a 120-bar warm-up -- there is nothing before J for
    either version to have written. Every mutant is still a different column
    from the real one."""
    close, other = FRAMES["walk"]
    mod = _load_mutant(*MUTANTS[index])

    def real(x):
        return ts_kurt_60(x, length=length)

    def mutated(x):
        return mod.ts_kurt_60(x, length=length)

    assert _caught(real, close, other) == []
    assert not real(close).equals(mutated(close))
    hits = _caught(mutated, close, other)
    assert len(hits) == caught
    assert [j for j in OFFSETS if j not in hits] == miss


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_guard_mutant_is_invisible_where_no_window_is_degenerate(frame):
    """The SIXTH mutant: the degeneracy guard read one bar into the future.
    It IS a look-ahead and it does change the column -- but on a walk, a
    tick-rounded walk and a student-t path the guard empties no window at
    all, so the sweep catches it 0/36. Asserted so the 0/36 cannot be read as
    a pass, with the reason (zero degenerate windows) asserted next to it."""
    mod = _load_mutant(*FORWARD_SPREAD_ONE)
    close, other = FRAMES[frame]
    assert not mod.ts_kurt_60(close).equals(ts_kurt_60(close))  # live mutant
    assert int(ts_kurt_60(close).isna().sum()) == LENGTH  # only the warm-up
    assert _caught(mod.ts_kurt_60, close, other) == []


def test_the_guard_mutant_is_caught_on_a_frame_that_has_degenerate_windows():
    """A 70-bar flat run planted in a 400-bar walk: the guard empties 10
    windows there, and the mutant is caught. The real module leaks 0/16 on
    the same frame."""
    mod = _load_mutant(*FORWARD_SPREAD_ONE)
    planted, other = _flat_run_planted(), _flat_run_planted(seed=23)
    offsets = range(80, 400, 20)
    assert int(ts_kurt_60(planted).isna().sum()) - LENGTH == 10
    assert _caught(ts_kurt_60, planted, other, offsets) == []
    assert len(_caught(mod.ts_kurt_60, planted, other, offsets)) >= 1


@pytest.mark.parametrize("offset", [2, -2])
def test_the_offset_keyword_is_the_only_way_to_shift_the_column(offset):
    close, _ = FRAMES["walk"]
    assert ts_kurt_60(close, offset=offset).equals(
        ts_kurt_60(close).shift(offset))


# ------------------------------------------------------------- Gates C / D


@pytest.mark.parametrize("frame_fn,fires,low,high", [
    (_walk, 1440, -1.2434, 2.8643),
    (_tick_rounded, 1440, -1.0483, 2.6676),
    (_heavy_tailed, 1440, 0.3265, 56.2111),
])
def test_reachability_on_synthetic_frames(frame_fn, fires, low, high):
    """Gate C, SYNTHETIC -- the real-data counts are owed with Gate E.
    `0 < fires < n`, the warm-up is exactly `length` bars, and the column is
    continuous: every fired bar takes a distinct value, so no constant column
    can pass here."""
    close = frame_fn()
    col = ts_kurt_60(close)
    fired = col.dropna()
    assert len(fired) == fires
    assert 0 < len(fired) < len(close)
    assert int(col.isna().sum()) == LENGTH
    assert int(fired.nunique()) > 1400
    assert float(fired.min()) == pytest.approx(low, abs=1e-3)
    assert float(fired.max()) == pytest.approx(high, abs=1e-3)
    assert float(fired.max()) <= _bound_max(LENGTH)
    assert float(fired.min()) >= _bound_min(LENGTH)


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _heavy_tailed])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_free_bit_identical_under_powers_of_two(frame_fn, k):
    """Gate D. The return is spelled as a price RATIO, and `8a / 8b` is the
    same double as `a / b`, so a x2^k rescale cancels exactly: 1440/1440 bars
    bit-equal on each of three frames, NaN masks equal."""
    close = frame_fn()
    col, scaled = ts_kurt_60(close), ts_kurt_60(close * k)
    assert bool((col.isna() == scaled.isna()).all())
    a, b = _shared(col, scaled)
    assert len(a) == 1440
    assert int((a == b).sum()) == 1440


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _heavy_tailed])
@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_free_within_tolerance_under_non_dyadic_factors(frame_fn, k):
    """x10 and x3.7 are NOT bit-identical and the arithmetic does not promise
    they would be -- they perturb each return in its last bits and a fourth
    moment amplifies that. The NaN masks still match exactly and the values
    agree to 1.2e-13 at Spearman 1.000000, which is Gate D's tolerance
    reading. Asserted as a limit, not glossed as invariance."""
    close = frame_fn()
    col, scaled = ts_kurt_60(close), ts_kurt_60(close * k)
    assert bool((col.isna() == scaled.isna()).all())
    a, b = _shared(col, scaled)
    assert float((a - b).abs().max()) < 1e-12
    assert float(a.corr(b, method="spearman")) == pytest.approx(1.0, abs=1e-9)
    assert int((a == b).sum()) < len(a)  # the limit itself


@pytest.mark.parametrize("length,fires", [(20, 1480), (120, 1380),
                                          (250, 1250), (4, 1496)])
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_free_at_non_default_lengths(length, fires, k):
    close = _walk()
    col = ts_kurt_60(close, length=length)
    scaled = ts_kurt_60(close * k, length=length)
    assert int(col.notna().sum()) == fires
    assert bool((col.isna() == scaled.isna()).all())
    a, b = _shared(col, scaled)
    assert int((a == b).sum()) == fires


def test_the_ratio_return_is_why_the_rescale_is_bit_identical():
    """`log(c).diff()` would NOT give the x8 rows above: on the same walk it
    is bit-equal on 821 of 1,499 returns against the ratio form's 1,499."""
    close = _walk()
    ratio = (close / close.shift(1) - 1).to_numpy()
    ratio8 = (close * 8 / (close * 8).shift(1) - 1).to_numpy()
    logd = np.diff(np.log(close.to_numpy()), prepend=np.nan)
    logd8 = np.diff(np.log((close * 8).to_numpy()), prepend=np.nan)
    assert int((ratio[1:] == ratio8[1:]).sum()) == 1499
    assert int((logd[1:] == logd8[1:]).sum()) < 1000


@pytest.mark.parametrize("k", [0.5, 2.0, 3.0])
def test_it_is_invariant_to_the_amplitude_of_the_returns_not_just_the_price(k):
    """The column standardises, so it is NOT a volatility feature: scaling
    every return by a positive constant leaves it at Spearman 1.000000 (max
    |difference| 8.5e-14). Where a consumer could mistake it for volatility,
    this is the measurement that says no."""
    r = np.nan_to_num((_walk() / _walk().shift(1) - 1).to_numpy())
    a, b = _shared(ts_kurt_60(_from_returns(r)),
                   ts_kurt_60(_from_returns(r * k)))
    assert float((a - b).abs().max()) < 1e-12
    assert float(a.corr(b, method="spearman")) == pytest.approx(1.0, abs=1e-9)


def test_a_drift_does_not_move_it_either():
    """+0.004 of log drift a bar: Spearman 1.000000, max |difference|
    9.3e-14. The centred moments remove the window mean."""
    close = _walk()
    drifted = close * np.exp(0.004 * np.arange(len(close)))
    a, b = _shared(ts_kurt_60(close), ts_kurt_60(drifted))
    assert float((a - b).abs().max()) < 1e-12
    assert float(a.corr(b, method="spearman")) == pytest.approx(1.0, abs=1e-9)


def test_what_it_actually_orders_is_the_single_largest_move():
    """The warning the docstring leads with, as a measurement: Spearman
    0.8698 against `max|r - mean| / sd` of the same window, 0.7753 against
    the second largest, and 0.0505 against the window's own standard
    deviation."""
    close = _walk()
    col = ts_kurt_60(close)
    r = (close / close.shift(1) - 1).to_numpy()
    windows = sliding_window_view(r, LENGTH)
    sd = windows.std(axis=1, ddof=1)
    srt = np.sort(np.abs(windows - windows.mean(axis=1)[:, None]), axis=1)
    pad = np.full(LENGTH - 1, np.nan)
    top1 = Series(np.concatenate([pad, srt[:, -1] / sd]), index=close.index)
    top2 = Series(np.concatenate([pad, srt[:, -2] / sd]), index=close.index)
    sdev = Series(np.concatenate([pad, sd]), index=close.index)
    a, b = _shared(col, top1)
    assert float(a.corr(b, method="spearman")) == pytest.approx(0.8698,
                                                                abs=1e-4)
    a, b = _shared(col, top2)
    assert float(a.corr(b, method="spearman")) == pytest.approx(0.7753,
                                                                abs=1e-4)
    a, b = _shared(col, sdev)
    assert abs(float(a.corr(b, method="spearman"))) < 0.1


@pytest.mark.parametrize("mult,median", [(10.0, 22.1696), (50.0, 57.1866)])
def test_one_planted_outlier_moves_exactly_sixty_bars_and_dominates_them(
        mult, median):
    """A single +10-sigma return takes the 60 windows holding it to a median
    of 22.1696 against the frame's -0.1283, and a +50-sigma one to 57.1866 --
    95% of the ceiling. Exactly `length` bars move by more than 1e-9, which
    is the span of the window."""
    close = _walk()
    raw = (close / close.shift(1) - 1).to_numpy()
    r = np.nan_to_num(raw)
    base = ts_kurt_60(_from_returns(r))
    planted = r.copy()
    planted[700] = mult * float(np.nanstd(raw))
    col = ts_kurt_60(_from_returns(planted))
    diff = (col - base).abs()
    moved = [i for i in range(len(col)) if diff.iloc[i] > 1e-9]
    assert moved == list(range(700, 700 + LENGTH))
    assert float(col.iloc[700:700 + LENGTH].median()) == pytest.approx(
        median, abs=1e-2)
    assert float(base.median()) == pytest.approx(-0.1283, abs=1e-3)


def test_it_is_a_slow_state_not_an_event_flag():
    """Two consecutive windows share 59 of their 60 returns, so the column
    autocorrelates at 0.9861 at lag 1 and 0.3371 at lag 60."""
    fired = ts_kurt_60(_walk()).dropna()
    assert float(fired.autocorr(1)) == pytest.approx(0.9861, abs=1e-3)
    assert float(fired.autocorr(LENGTH)) == pytest.approx(0.3371, abs=1e-3)


@pytest.mark.parametrize("frame_fn,median", [
    (_two_point, -2.0507), (_heavy_tailed, 9.7454),
])
def test_it_orders_tail_shape_and_not_amplitude(frame_fn, median):
    """The two-point path has the SMALLEST return sd of the six frames
    measured (0.0100) and sits at the floor; the student-t(2) path reads a
    median of 9.7454. Amplitude is not what moves this column."""
    fired = ts_kurt_60(frame_fn()).dropna()
    assert float(fired.median()) == pytest.approx(median, abs=1e-2)


# ---------------------------------------------------------------- the floor


def test_the_noise_floor_is_this_forks_existing_constant():
    """4096 eps on a dimensionless quantity, the same constant
    `ts_binent_20`, `ts_c3_20` and `lean_hurst_100` use."""
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == 4096 * np.finfo(float).eps
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13,
                                              abs=1e-25)
    assert _REAL.MIN_LENGTH == 4
    assert _REAL.EXTRA_CLOSES == 1


def test_a_flat_frame_fires_on_nothing():
    """The floor's headline case. pandas would read -3.0 on 240 of these 300
    bars (see test_the_prototype_reads_minus_three_where_this_port_refuses)."""
    assert int(ts_kurt_60(_flat()).notna().sum()) == 0


@pytest.mark.parametrize("frame_fn", [
    lambda: Series(100.0 * np.exp(np.arange(300) * 0.01)),   # 1%-a-bar ladder
    lambda: Series(100.0 * 1.5 ** np.arange(300)),           # exact x1.5
])
def test_a_geometric_ladder_fires_on_nothing_either(frame_fn):
    """Mathematically constant returns that differ at rounding level in
    float64. Here pandas' own absolute test already empties them -- measured,
    the prototype also fires 0/300 -- so this is the floor agreeing with it
    rather than the floor doing the work."""
    frame = frame_fn()
    assert int(ts_kurt_60(frame).notna().sum()) == 0
    assert int(_prototype(frame).notna().sum()) == 0


def test_the_floor_is_what_empties_a_fine_tick_path_at_a_high_price():
    """The one measured case where the floor and not pandas' test does the
    work on a non-flat frame: price 1e6, tick 0.001, so the returns are
    distinct but their range over 60 bars is 2.2e-16. 0 of 300 bars here
    against the prototype's 47."""
    frame = Series(1e6 + 0.001 * np.arange(300))
    r = (frame / frame.shift(1) - 1).to_numpy()
    span = float(np.nanmax(r[-LENGTH:]) - np.nanmin(r[-LENGTH:]))
    assert span < _REAL.NOISE_FLOOR
    assert int(ts_kurt_60(frame).notna().sum()) == 0
    assert int(_prototype(frame).notna().sum()) == 47


def test_a_coarser_tick_at_a_low_price_still_fires():
    """The floor is not swallowing ordinary data: price 50, tick 0.01, return
    range 2.1e-06, fires 240/300."""
    frame = Series(50.0 + 0.01 * np.arange(300))
    assert int(ts_kurt_60(frame).notna().sum()) == 240


@pytest.mark.parametrize("sigma,fires", [(1e-2, 240), (1e-6, 240),
                                         (1e-7, 47), (1e-8, 0)])
def test_pandas_absolute_degenerate_test_is_inherited_and_disclosed(sigma,
                                                                    fires):
    """pandas' own degenerate test is ABSOLUTE in the SIZE of the returns
    rather than relative to their shape, so this column is scale-free in the
    returns down to about sigma = 1e-6 and not below: a 1e-7-sigma path fires
    on 47 of 300 bars, a 1e-8 one on none, and the same 1e-7 path with its
    returns x100 on 240. Three to four orders of magnitude away from BIST
    daily data; recorded because it is a real limit of the shipped spelling.

    ⚠ The threshold itself is NOT quoted: `rolling.kurt` is
    `pandas/_libs/window/aggregations`, installed here only as a compiled
    `.so`, so these four counts are the measured boundary and not a constant
    read out of pandas. The sibling two-pass function is readable and is
    absolute in the same way (`nanops.py:1361` and `:1581`, 1e-14 on
    `(n-2)(n-3)*sum(d**2)`)."""
    frame = _walk(300, seed=14, sigma=sigma)
    assert int(ts_kurt_60(frame).notna().sum()) == fires
    assert int(_prototype(frame).notna().sum()) == fires  # inherited, not ours


def test_the_low_volatility_limit_is_in_the_returns_not_in_the_price():
    """The same 1e-7-sigma path with its returns multiplied by 100 fires on
    240 of 300 bars, so what the absolute test sees is the return size."""
    frame = _walk(300, seed=14, sigma=1e-7)
    r = np.nan_to_num((frame / frame.shift(1) - 1).to_numpy())
    grown = _from_returns(r * 100.0)
    assert int(ts_kurt_60(frame).notna().sum()) == 47
    assert int(ts_kurt_60(grown).notna().sum()) == 240


# --------------------------------------------------------- guards and edges


def test_a_short_series_is_refused_and_the_next_bar_fires():
    close = _walk(400, seed=19)
    assert ts_kurt_60(close.iloc[:LENGTH]) is None
    short = ts_kurt_60(close.iloc[:LENGTH + 1])
    assert int(short.notna().sum()) == 1
    assert int(np.argmax(short.notna().to_numpy())) == LENGTH


@pytest.mark.parametrize("value,name", [
    (None, "TS_KURT_60"), (0, "TS_KURT_60"), (-5, "TS_KURT_60"),
    (3, "TS_KURT_60"), (0.5, "TS_KURT_60"), (3.9, "TS_KURT_60"),
    (4, "TS_KURT_4"), (60.9, "TS_KURT_60"), (120, "TS_KURT_120"),
])
def test_length_validation_falls_back_below_the_minimum(value, name):
    """Below 4 the bias correction divides by zero or a negative, so a
    smaller or missing value falls back to 60. The effective value is the one
    in the column name."""
    assert ts_kurt_60(_walk(400, seed=19), length=value).name == name


def test_a_fractional_length_is_truncated():
    close = _walk(400, seed=19)
    assert ts_kurt_60(close, length=120.9).equals(
        ts_kurt_60(close, length=120))


def test_fillna_fills_exactly_the_warm_up():
    close = _walk(400, seed=19)
    filled = ts_kurt_60(close, fillna=-99.0)
    assert int((filled == -99.0).sum()) == LENGTH
    assert int(filled.isna().sum()) == 0


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_sixty_one_windows_and_moves_nothing_before_it(
        value):
    """A close that is not a finite, normal, positive float has no return to
    take, so it spoils TWO returns and the 61 windows holding either of
    them -- bars 200..260 for a bad close at bar 200 -- and nothing before
    bar 200 moves."""
    close = _walk(400, seed=19)
    base = ts_kurt_60(close)
    p = close.copy()
    p.iloc[200] = value
    out = ts_kurt_60(p)
    emptied = [i for i in range(len(p))
               if out.isna().iloc[i] and not base.isna().iloc[i]]
    assert emptied == list(range(200, 261))
    assert base.iloc[:200].equals(out.iloc[:200])


def test_a_close_pair_whose_ratio_overflows_empties_sixty_windows():
    """One spoiled return, so 60 windows: `1e-300` then `1e50`. The
    prototype rejects them too -- pandas will not take an infinite sample --
    so this guard is belt and braces on the ratio, not a divergence."""
    close = _walk(400, seed=19)
    base = ts_kurt_60(close)
    p = close.copy()
    p.iloc[200] = 1e-300
    p.iloc[201] = 1e50
    out = ts_kurt_60(p)
    emptied = [i for i in range(len(p))
               if out.isna().iloc[i] and not base.isna().iloc[i]]
    assert emptied == list(range(201, 261))
    assert int(_prototype(p).iloc[201:261].notna().sum()) == 0


def test_pandas_alone_would_ship_an_infinity_on_an_extreme_return():
    """What the two masks are protecting against, measured on the raw pandas
    call with no guard at all: a planted close of `1e-200 * 1e77` gives
    returns of 1.0e+77 and 1.0e+125 and `r.rolling(60).kurt()` comes back
    +inf on 1 bar and NaN on 258 of 400. The shipped column emits neither:
    0 infinities, and its NaN span is the 61 bars
    `test_the_fourth_power_guard_is_what_keeps_the_nan_damage_window_local`
    pins."""
    close = _walk(400, seed=19)
    p = close.copy()
    p.iloc[200] = 1e-200
    p.iloc[201] = 1e-200 * 1e77
    raw = (p / p.shift(1) - 1.0).rolling(LENGTH, min_periods=LENGTH).kurt()
    assert int(np.isinf(raw).sum()) == 1
    assert int(raw.isna().sum()) == 258
    out = ts_kurt_60(p)
    assert int(np.isinf(out).sum()) == 0
    assert int(out.isna().sum()) > int(ts_kurt_60(close).isna().sum())


def test_the_module_keeps_pandas_rolling_kurt_as_the_arithmetic():
    """A source pin, because the alternative spellings are behaviourally
    equivalent to 1e-13 (Gate A3) and only this one is bit-equal to the
    screened prototype. If the moments are ever re-derived in numpy, that
    equality goes and this test says so."""
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert "kurt = rolling.kurt()" in src
    assert "rolling = r.rolling(length, min_periods=length)" in src
    assert "spread = rolling.max() - rolling.min()" in src


# ------------------------------------------------------------- the wiring


def test_the_five_wiring_touch_points():
    close = _walk(400, seed=33)
    frame = DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": 1e6})
    assert pandas_ta.ts_kurt_60(close).name == "TS_KURT_60"
    assert frame.ta.ts_kurt_60().name == "TS_KURT_60"
    assert "ts_kurt_60" in pandas_ta.Category["statistics"]
    assert pandas_ta.ts_kurt_60(close).category == "statistics"


def test_the_accessor_forwards_its_parameters_under_the_right_name():
    """The `supertrend` failure mode: a keyword forwarded under the wrong
    name is invisible to `hasattr`."""
    close = _walk(400, seed=33)
    frame = DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": 1e6})
    assert frame.ta.ts_kurt_60(length=20).name == "TS_KURT_20"
    assert frame.ta.ts_kurt_60(offset=2).equals(
        ts_kurt_60(close, offset=2).rename("TS_KURT_60"))


def _ledger_rows():
    import csv
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "docs", "gate_e_ledger.csv")
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "the ledger is empty"
    return rows


def test_the_ledger_row_is_this_modules_gate_e_run():
    """Gate E is this module's own run, not the screen's. Issue #93 quoted
    the screen harness's figures on the PROTOTYPE (max |rho| 0.2501 vs
    `ZIGZAG`, n = 33,246, per-frame max median 0.2335); issue-solver's run on
    `pandas_ta.statistics.ts_kurt_60` (`is93-ts_kurt_60-049a1889`, measured
    2026-11-13) reproduced them to every digit the issue printed, and that
    run is what ships.

    Pinned here: exactly one `TS_KURT*` row exists, it is SHIP under
    `r3-perframe-0.90` with no waiver, and it names THIS module and THAT
    run. `tests/test_gate_e_ledger.py` checks the numbers generically and
    re-derives `module_sha1` and the output fingerprint from the tree, but it
    cannot see whose run a row came from -- a row recorded from some other
    measurement would satisfy it. Hence the identity assertions.
    """
    rows = [r for r in _ledger_rows() if r["column"].startswith("TS_KURT")]
    assert len(rows) == 1
    row = rows[0]
    assert row["indicator"] == "ts_kurt_60"
    assert row["module"] == "pandas_ta.statistics.ts_kurt_60"
    assert row["column"] == "TS_KURT_60"
    assert row["run"] == "is93-ts_kurt_60-049a1889"
    assert row["verdict"] == "SHIP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    assert float(row["max_abs_rho"]) < 0.76
    assert float(row["perframe_max_median_abs_rho"]) < 0.90


def test_the_ledger_row_carries_the_measured_gate_e_numbers():
    """The figures `docs/TsKurt60Measured.md` reports in its Gate E and
    Gate C sections, read back out of the ledger so an edit to either one has
    to move both: 0.2501241324996995 vs `ZIGZAG` (compute_all) over
    n = 33,246, per-frame max median 0.2334651987740327, and the run's
    real-data reachability counts -- 393,509 non-NaN and 393,509 non-zero of
    398,849 pooled bars, the NaN bars being exactly the 60-bar warm-up on
    each of the 89 frames.

    The last one is the load-bearing claim of the receipt's Gate C: it is
    what says the degeneracy floor and the fourth-power guard emptied no
    window on real BIST data, since any window they emptied would be a NaN
    bar beyond the warm-up.
    """
    rows = [r for r in _ledger_rows() if r["column"] == "TS_KURT_60"]
    assert len(rows) == 1
    row = rows[0]
    assert float(row["max_abs_rho"]) == 0.2501241324996995
    assert row["against"] == "ZIGZAG"
    assert row["against_set"] == "compute_all"
    assert int(row["n"]) == 33246
    assert float(row["perframe_max_median_abs_rho"]) == 0.2334651987740327
    assert row["perframe_max_against"] == "ZIGZAG"
    assert (int(row["non_nan"]), int(row["non_zero"])) == (393509, 393509)
    assert int(row["pooled_bars"]) == 398849
    # The NaN bars are exactly the warm-up: 60 per frame, 89 frames.
    assert int(row["pooled_bars"]) - int(row["non_nan"]) == 60 * 89
