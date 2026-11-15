# -*- coding: utf-8 -*-
"""SK-ROCWB-RATIO: `sk_rocwb_ratio`, the 20-bar ROC over the root mean
square of its own last 5 readings (PandasTa issue #109, Skender
Stock.Indicators' `RocWb`, Apache-2.0).

    ROC[T]              = 100 * (close[T] / close[T - 20] - 1)
    band[T]             = sqrt(mean(ROC[T - 4 .. T]^2))
    SK_ROCWB_RATIO_20_5 = ROC[T] / band[T]

What this file pins, in order of how much it would hurt to lose:

1. **THE BOUND, which is this column's defining property and the whole
   reason the ratio ships instead of Skender's two price-unit series.**
   The band is a ROOT MEAN SQUARE, so `roc[T]` is one of the terms of
   its own denominator and `|x| <= sqrt(band_length)`. Pinned on every
   frame, at five band lengths, and ATTAINED to 0 ulps by a hand frame
   (24 flat closes then one move) in both directions. ⚠ Also pinned is
   what the bound is NOT: the standard-deviation reading of the same
   band, which a reader who knows Bollinger bands will assume, is
   asserted to be a different and UNBOUNDED column.
2. **Gate A, the formula spelled three ways -- and which limb is
   bit-equal.** The screen prototype (the expression Gate E's 0.8537 was
   measured on) is asserted BIT-equal on all eight frames. Two
   independent scalar-loop oracles are asserted equal only to a
   TOLERANCE, and that is the finding rather than a weakness: pandas'
   rolling mean is an online accumulator, so even the loop that spells
   the ROC exactly as the module does differs in the last bits
   (2.335e-14 relative as measured), and Skender's own spelling of the
   ROC, `100 * (c - c20) / c20`, differs by up to 4.007e-12.
   ⚠ The shipped `roc` spells it Skender's way, and this module does not
   import it -- for PROVENANCE (ship the screened expression bit for
   bit), not because 4e-12 at Spearman 1.0000 could move a Gate E rho.
   The test asserts the two agree to 1e-9 and leaves the bit-level
   difference unpinned, because it is a floating-point accident and not
   a contract.
3. **Gate B, causality, including the part a 36-of-36 headline would
   hide.** A sweep that splits a frame into one shared past and two
   WHOLLY different futures catches the module on 0 offsets of every
   frame. FIVE look-ahead mutants are read off the shipped source,
   edited and `exec`'d in memory, and each is asserted LIVE first.
   ⚠ Two of the five -- the ones that shift the BAND -- are NOT caught
   everywhere, and the test says so instead of sampling around it: a
   shifted band multiplies a numerator that is exactly 0 on 449 bars of
   the 2.0-tick frame (343 of which read 0.0 and 106 of which are blank)
   and on every bar of a flat price, and 0 / anything is 0 either way.
   Each is given a necessary condition computed from the frame's own
   ROC, and the test asserts caught-inside and 0 caught-outside.
4. **Gate D, scale.** x8 / x64 and the exact binary factors 2^-20, 2^20
   and 2^300 are bit-identical on every fired bar; x10, x3.7, x0.1 and
   x1.0000001 agree to 1e-7 (measured 1.885e-11) with matching NaN
   masks. ⚠ A LEVEL SHIFT is asserted NOT invariant -- the sibling
   `sk_fcb_pos` is, and assuming it here would be wrong -- while its
   ranks are asserted to survive (Spearman >= 0.999 as measured).
5. **Gate C, reachability, and the one way this column goes blank.** The
   warm-up is a CONSTANT 24 bars, not data-dependent, and every bar
   after it fires on a continuous frame. The exception is exactly five
   consecutive zero ROC readings, which needs 25 constant closes: flat
   patches of 24 and 25 bars are asserted to empty 0 and 1 bars. A flat
   price fires nothing at all, and that is asserted to be ordinary for
   the bucket (42 of 144 momentum columns read all-NaN there) rather
   than a defect.
6. **The guards, each priced, and the one divergence from the
   prototype.** A NaN close empties exactly 10 bars and moves no earlier
   bar; the `isfinite` mask makes an INFINITE close do the same thing
   bit for bit, and the mutant with the mask removed is asserted to
   leave those five bars carrying plausible NUMBERS off an infinite base
   price instead. A zero close is asserted NOT emptied the same way, and
   the `+-inf -> NaN` fold is asserted to be a no-op on every frame --
   dead code kept for fidelity with the measured prototype.
7. **Gate E is OWED, and the test says which session owes it.** No
   ledger row exists yet; `tests/test_gate_e_ledger.py` fails locally
   until the launcher's run is recorded, which is expected and is not a
   reason to hold the indicator out of `Category`.

⚠ **Counts of moved bars, distinct values and Spearman digits are NOT
pinned to the digits measured here.** The frames are built with `np.exp`
and `np.cumsum`, so a reduced numpy kernel moves a price in its last
bits. What is pinned is structure: a bound, a NaN mask, a first fired
bar, a sign, an ordering, or a tolerance with orders of margin.
`python docs/measure_sk_rocwb_ratio_cpu.py` re-runs this module with
numpy's AVX512F / AVX512_SKX / AVX2 / FMA3 dispatch disabled.

Every number quoted in this file comes from `docs/measure_sk_rocwb_ratio.py`.
"""
import csv
import math
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.roc import roc as ta_roc
from pandas_ta.momentum.sk_rocwb_ratio import sk_rocwb_ratio

N = 400
LEVEL = 100.0
LENGTH = 20
BAND_LENGTH = 5
WARMUP = LENGTH + BAND_LENGTH - 1
BOUND = math.sqrt(BAND_LENGTH)
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "momentum" / "sk_rocwb_ratio.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_sk_rocwb_ratio.py`, shortened
# from 1,500 bars to 400 so the module stays fast. A figure quoted from
# that script is therefore a figure about 1,500-bar frames; nothing here
# asserts one of its counts.


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
    return c * Series(np.where(np.arange(n) >= n // 2, 1.5, 1.0),
                      index=c.index)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _coarse(seed=7, n=N, level=LEVEL, tick=2.0):
    """A walk rounded to a tick coarser than its own bar-to-bar move: the
    frame where `close[T] == close[T - 20]` happens by rounding, so the ROC
    is EXACTLY 0 on many bars. FVGDEAD's lesson, spent in advance."""
    return np.round(_walk(seed, n, level) / tick) * tick


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
#: Every bar of `flat` is 0/0, so it carries no value to compare.
FIRING = [n for n in NAMES if n != "flat"]
#: The six frames where every bar after the warm-up fires (§C). ⚠ Not
#: "the frames with no exactly-zero ROC": `grid` carries one such bar
#: (§C4) and still fires 1,476 of 1,476, because one zero ROC blanks
#: nothing -- five in a row do.
CONTINUOUS = [n for n in NAMES if n not in ("flat", "coarse")]


# ----------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _rel(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


def _fin(x):
    return x.replace([np.inf, -np.inf], np.nan)


def _roc_of(close, length=LENGTH):
    return 100 * (close / close.shift(length) - 1)


# ----------------------------------------------------------------- oracles


def _oracle(close, length=LENGTH, band_length=BAND_LENGTH, skender=True):
    """The formula by explicit scalar loops, sharing no pandas operation
    with the module. `skender=True` spells the ROC `100 * (c - c20) / c20`,
    the way Skender's `Roc` states it and the way `pandas_ta.roc` computes
    it; `skender=False` spells it the module's way."""
    c = close.where(np.isfinite(close)).to_numpy(dtype=float)
    n = c.size
    roc = np.full(n, np.nan)
    out = np.full(n, np.nan)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        for i in range(length, n):
            old = c[i - length]
            roc[i] = (100.0 * (c[i] - old) / old if skender
                      else 100.0 * (c[i] / old - 1.0))
        for i in range(length + band_length - 1, n):
            total = 0.0
            for p in range(i - band_length + 1, i + 1):
                total += roc[p] * roc[p]
            out[i] = roc[i] / np.sqrt(total / band_length)
    return _fin(Series(out, index=close.index))


def _prototype(close, length=LENGTH, band_length=BAND_LENGTH):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `sk_rocwb_ratio`:

        r = 100 * (c / c.shift(20) - 1)
        return sdiv(r, np.sqrt(mean(r ** 2, 5)))
    """
    r = 100 * (close / close.shift(length) - 1)
    return _fin(r / np.sqrt((r ** 2).rolling(band_length).mean()))


def _via_roc(close, length=LENGTH, band_length=BAND_LENGTH):
    """The same ratio built on the shipped `roc`, which the module
    deliberately does not import."""
    r = ta_roc(close, length)
    return _fin(r / np.sqrt((r ** 2).rolling(band_length).mean()))


def _stdev_band(close, length=LENGTH, band_length=BAND_LENGTH):
    """The band as a STANDARD DEVIATION instead of a root mean square."""
    r = 100 * (close / close.shift(length) - 1)
    return _fin(r / r.rolling(band_length).std(ddof=0))


# ----------------------------------------------------------------- mutants

ROC_LINE = "    roc = 100 * (c / c.shift(length) - 1)"
BAND_LINE = "    band = np.sqrt((roc ** 2).rolling(band_length).mean())"
RATIO_LINE = "    ratio = roc / band"

CAUSALITY_MUTANTS = {
    "roc-lead": (ROC_LINE, "    roc = 100 * (c / c.shift(-length) - 1)"),
    "close-lead": (ROC_LINE,
                   "    roc = 100 * (c.shift(-1) / c.shift(length) - 1)"),
    "band-centred": (BAND_LINE,
                     "    band = np.sqrt((roc ** 2)"
                     ".rolling(band_length, center=True).mean())"),
    "band-lead": (BAND_LINE,
                  "    band = np.sqrt((roc ** 2).rolling(band_length)"
                  ".mean()).shift(-1)"),
    "output-early": (RATIO_LINE, "    ratio = (roc / band).shift(-1)"),
}
#: The two that shift the BAND, which a zero numerator can hide.
BAND_MUTANTS = ["band-centred", "band-lead"]
MASK_OFF = ("    c = close.where(np.isfinite(close))", "    c = close")
FIN_OFF = ("    ratio = ratio.replace([np.inf, -np.inf], np.nan)",
           "    ratio = ratio")


def _mutant(old, new):
    """`sk_rocwb_ratio` with one edit applied to the SHIPPED source, read
    off disk and exec'd in memory -- so no mutant can drift away from the
    code it claims to edit, and a prefix-truncation test cannot be fooled
    by an edit that silently failed to apply."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["sk_rocwb_ratio"]


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


def _nonzero(roc, i):
    v = roc.iloc[i]
    return bool(v == v and v != 0.0)


def _exposed(label, roc, j, n):
    """A NECESSARY condition for a band mutant to be catchable at boundary
    `j`, computed from the clean frame rather than argued.

    `band-lead` writes `roc[i] / band[i + 1]`, so the only prefix bar that
    reads the future is `i = j - 1`; `band-centred` centres the window, so
    bars `j - 1` and `j - 2` do. Either way the bar moves only if its own
    numerator is a non-zero number AND the bar carries a value at all --
    which needs the SHIFTED band to exist (`i + 1 >= WARMUP`, not merely
    `roc[i]`), and which at the END of a frame it may not, because a
    centred window runs off the edge."""
    if label == "band-lead":
        i = j - 1
        return i + 1 >= WARMUP and i + 1 <= n - 1 and _nonzero(roc, i)
    return any(i - 2 >= LENGTH and i + 2 <= n - 1 and _nonzero(roc, i)
               for i in (j - 1, j - 2))


def _offsets(n=N, how_many=12):
    """A spread of boundaries in the tail, where a window reaches back
    over the whole warm-up."""
    return list(range(n - how_many, n))


# ------------------------------------------------------- 1. THE BOUND


@pytest.mark.parametrize("name", FIRING)
def test_the_column_never_leaves_plus_minus_sqrt_band_length(name):
    """`roc[T]` is one of the five squared terms of its own denominator,
    so `|x| <= sqrt(5)`. Asserted bar by bar, with a relative slack of
    1e-12 for the last bit of a square root -- `docs/measure_sk_rocwb_ratio.py`
    §C2 measures 0 bars over the bound on 1,500-bar frames."""
    col = sk_rocwb_ratio(FRAMES[name]()).dropna()
    assert col.size > 0
    assert float(col.abs().max()) <= BOUND * (1.0 + 1e-12)


@pytest.mark.parametrize("band_length", [2, 3, 5, 7, 10])
def test_the_bound_follows_band_length(band_length):
    """The bound is `sqrt(band_length)`, not the constant 2.236: a shorter
    band is a tighter column."""
    col = sk_rocwb_ratio(_walk(), band_length=band_length).dropna()
    assert col.size > 0
    assert float(col.abs().max()) <= math.sqrt(band_length) * (1.0 + 1e-12)


def test_the_bound_is_attained_by_a_flat_window_then_one_move():
    """The four previous ROC readings exactly 0 and today's not: the band
    is `|roc| / sqrt(5)` and the quotient is the bound itself. Measured at
    0 ulps from `sqrt(5)`; asserted at 1e-12 relative, since a square root
    may round differently on another CPU."""
    up = sk_rocwb_ratio(_series(np.array([100.0] * WARMUP + [110.0])))
    down = sk_rocwb_ratio(_series(np.array([100.0] * WARMUP + [90.0])))
    assert float(up.iloc[-1]) == pytest.approx(BOUND, rel=1e-12)
    assert float(down.iloc[-1]) == pytest.approx(-BOUND, rel=1e-12)


def test_the_band_is_a_root_mean_square_and_not_a_standard_deviation():
    """The reading a reader of "band" assumes is a DIFFERENT column: with
    the mean subtracted the numerator is no longer one of the denominator's
    terms, so it is unbounded. Measured |x| up to 138.9931 against this
    column's 2.2361."""
    for name in FIRING:
        close = FRAMES[name]()
        assert _differs(sk_rocwb_ratio(close), _stdev_band(close)) > 0
    worst = max(float(_stdev_band(FRAMES[n]()).abs().max()) for n in FIRING)
    assert worst > 5.0 * BOUND


def test_zero_is_a_value_and_not_a_gap():
    """`ROC == 0` with a non-zero band reads exactly 0.0 -- the price is
    where it was 20 bars ago. On a tick grid that is common (343 bars of
    the 1,500-bar coarse frame), and it must not be confused with the
    all-zero-window case, which is NaN."""
    close = _coarse()
    col = sk_rocwb_ratio(close)
    roc = _roc_of(close)
    band = np.sqrt((roc ** 2).rolling(BAND_LENGTH).mean())
    both = (roc == 0.0) & (band > 0.0)
    assert int(both.sum()) > 0
    assert bool((col[both] == 0.0).all())
    assert bool(col[(band == 0.0) & band.notna()].isna().all())


# ------------------------------------------------------------ 2. GATE A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_module_is_the_screen_prototype_bit_for_bit(name):
    """The expression the 2026-10-24 catalog screen measured at Gate E
    (0.8537 vs `zscore`). It is this module's own expression without the
    `isfinite` mask, so on a finite frame the equality is structural --
    what it buys is the tie to that figure."""
    close = FRAMES[name]()
    assert _bit_equal(sk_rocwb_ratio(close), _prototype(close))


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_source_formula_by_loops_agrees(name):
    """Skender's own algebra by two Python loops: `100 * (c - c20) / c20`
    and a FRESH five-term sum of squares. Not bit-equal and not asserted
    to be -- measured 4.007e-12 relative, asserted at 1e-9 -- because the
    two spellings of a percent change are not the same double."""
    close = FRAMES[name]()
    col, orc = sk_rocwb_ratio(close), _oracle(close)
    assert bool((col.isna() == orc.isna()).all())
    assert _rel(col, orc) <= 1e-9 or np.isnan(_rel(col, orc))


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_same_loops_with_the_modules_spelling_agree(name):
    """The same loops with the ROC spelled the module's way. Still not
    bit-equal, and that is the finding: pandas' rolling mean is an online
    add/remove accumulator, so it does not agree to the last bit with a
    fresh five-term sum (measured 2.335e-14 relative)."""
    close = FRAMES[name]()
    col, orc = sk_rocwb_ratio(close), _oracle(close, skender=False)
    assert bool((col.isna() == orc.isna()).all())
    assert _rel(col, orc) <= 1e-11 or np.isnan(_rel(col, orc))


@pytest.mark.parametrize("name", FIRING)
def test_the_shipped_roc_is_a_different_column_by_a_measurable_amount(name):
    """Why this module does not import `pandas_ta.roc`: it spells the ROC
    Skender's way, so the ratio built on it is this column moved by up to
    4.007e-12 relative -- off the expression Gate E was measured on. The
    agreement is pinned at 1e-9; the disagreement is NOT pinned, because
    which bars differ is a floating-point accident."""
    close = FRAMES[name]()
    col, via = sk_rocwb_ratio(close), _via_roc(close)
    assert bool((col.isna() == via.isna()).all())
    assert _rel(col, via) <= 1e-9
    assert _spearman(col, via) >= 0.999


# ------------------------------------------------------------ 3. GATE B


@pytest.mark.parametrize("name", NAMES)
def test_the_module_reads_no_future_bar(name):
    """One shared past, two wholly different futures: a causal column is
    bit-identical on the shared prefix. `docs/measure_sk_rocwb_ratio.py` §B
    runs every boundary of every 1,500-bar frame and catches 0."""
    close = FRAMES[name]()
    assert [j for j in _offsets() if _caught_at(sk_rocwb_ratio, close, j)] \
        == []


@pytest.mark.parametrize("name", NAMES)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    """The weaker check, kept because it is the one a reader expects:
    computing on the first k bars reproduces the first k bars. It cannot
    see back-dating, which is what the mutants above are for."""
    close = FRAMES[name]()
    full = sk_rocwb_ratio(close)
    for k in (N // 2, N - 7):
        assert _bit_equal(sk_rocwb_ratio(close.iloc[:k]), full.iloc[:k])


@pytest.mark.parametrize("label", list(CAUSALITY_MUTANTS))
def test_a_look_ahead_mutant_is_live_before_it_is_swept(label):
    """A mutant that does not change the output is an edit that failed to
    apply, and a clean sweep against it would prove nothing."""
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    close = _walk()
    assert _differs(sk_rocwb_ratio(close), fn(close)) > 0


@pytest.mark.parametrize("label",
                         [k for k in CAUSALITY_MUTANTS
                          if k not in BAND_MUTANTS])
def test_a_mutant_that_reaches_into_the_roc_is_caught_everywhere(label):
    """The three edits that move the ROC itself are caught on every
    boundary of every frame -- `flat` included, because an all-NaN column
    and a column with values are not bit-equal either."""
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    for name in NAMES:
        close = FRAMES[name]()
        caught = [j for j in _offsets() if _caught_at(fn, close, j)]
        assert caught == _offsets(), f"{label} on {name}: {len(caught)}"


@pytest.mark.parametrize("label", BAND_MUTANTS)
def test_a_band_mutant_is_caught_exactly_where_its_numerator_is_not_zero(
        label):
    """⚠ These two are NOT caught everywhere, and the test pins the reason
    rather than hiding it behind a kinder frame. A shifted band multiplies
    a numerator that is exactly 0 on 449 bars of the 1,500-bar coarse
    frame and on every bar of a flat price, and `0 / anything` is 0 either
    way. The condition is COMPUTED from the frame's own ROC: `band-lead`
    can only move bar `j - 1`, `band-centred` bars `j - 1` and `j - 2`.
    Over all 11,992 offsets of the eight 1,500-bar frames §B2 measures 0
    catches outside the condition and 0 exposed-but-missed."""
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    for name in NAMES:
        close = FRAMES[name]()
        roc = _roc_of(close)
        for j in _offsets():
            exposed = _exposed(label, roc, j, close.size)
            assert _caught_at(fn, close, j) == exposed, \
                f"{label} on {name} at {j}: exposed={exposed}"


def test_the_flat_frame_hides_a_band_mutant_entirely():
    """The sharp end of the paragraph above, stated as its own fact: on a
    flat price every ROC is 0, so both band mutants are invisible. A Gate
    B argument that rested on one frame could rest on this one and prove
    nothing."""
    close = _flat()
    for label in BAND_MUTANTS:
        fn = _mutant(*CAUSALITY_MUTANTS[label])
        assert _differs(sk_rocwb_ratio(close), fn(close)) == 0


# ------------------------------------------------------------ 4. GATE D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -20, 2.0 ** 20,
                                    2.0 ** 300])
def test_scale_an_exact_binary_factor_is_bit_identical(name, factor):
    """The price enters only as `close[T] / close[T - 20]`, so a power of
    two cancels exactly -- at 2^300 as well as at 8."""
    close = FRAMES[name]()
    assert _bit_equal(sk_rocwb_ratio(close), sk_rocwb_ratio(close * factor))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """x10 and x3.7 re-round every price. Measured 1.885e-11 relative at
    worst; asserted at 1e-7, four orders of margin, because the quotient
    of two small numbers amplifies a last-bit move."""
    close = FRAMES[name]()
    col, other = sk_rocwb_ratio(close), sk_rocwb_ratio(close * factor)
    assert bool((col.isna() == other.isna()).all())
    assert _rel(col, other) <= 1e-7


@pytest.mark.parametrize("shift", [1.0, 50.0, 1e6])
def test_scale_a_level_shift_is_not_invariant(shift):
    """⚠ The sibling `sk_fcb_pos` is shift-invariant and this column is
    NOT: a ratio of prices is not a ratio of prices-plus-a-constant.
    Measured 9.437e-04 .. 4.491e-02 absolute on a walk at level 100. The
    ranks survive (Spearman 1.0000 / 1.0000 / 0.9999), which is asserted
    too, so the disclosure is the size of the move and not a hint that the
    column falls apart."""
    close = _walk()
    col, other = sk_rocwb_ratio(close), sk_rocwb_ratio(close + shift)
    assert _differs(col, other) > 0
    assert _spearman(col, other) >= 0.99


@pytest.mark.parametrize("name", FIRING)
def test_scale_fires_strictly_between_zero_and_n(name):
    """Gate D's constant-column guard: a column that never fires, or one
    that is constant, cannot pass a rescale test by being trivial."""
    col = sk_rocwb_ratio(FRAMES[name]())
    fired = int(col.notna().sum())
    assert 0 < fired < col.size
    assert col.dropna().nunique() > 1


# ------------------------------------------------------------ 5. GATE C


@pytest.mark.parametrize("name", CONTINUOUS)
def test_the_warm_up_is_a_constant_24_bars(name):
    """Not data-dependent, unlike the fractal ports: `length` bars for the
    ROC and `band_length` of those for the band."""
    col = sk_rocwb_ratio(FRAMES[name]())
    assert bool(col.iloc[:WARMUP].isna().all())
    assert bool(col.iloc[WARMUP:].notna().all())


def test_the_shortest_input_that_produces_a_value():
    """`verify_series` floors the input at `length + band_length` = 25
    bars, which is exactly the shortest frame that can carry one value."""
    close = _series(np.array([100.0 + i for i in range(WARMUP + 1)]))
    col = sk_rocwb_ratio(close)
    assert col.size == WARMUP + 1
    assert int(col.notna().sum()) == 1
    assert sk_rocwb_ratio(close.iloc[:-1]) is None


def test_a_flat_price_never_fires_and_that_is_a_reading():
    """Every ROC is exactly 0, so the band is 0 and every bar is 0/0. §C3
    ran the whole bucket on a flat frame: 42 of 144 momentum columns read
    all-NaN there. This test re-runs the handful it can afford, so the
    claim is not only a cross-reference."""
    close = _flat()
    assert bool(sk_rocwb_ratio(close).isna().all())
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close,
                    "volume": Series(np.full(close.size, 1e6),
                                     index=close.index)})
    for peer in ("cmo", "er", "cci"):
        out = getattr(df.ta, peer)()
        assert bool(out.isna().all()), peer


@pytest.mark.parametrize("patch,emptied", [(20, 0), (24, 0), (25, 1),
                                           (29, 5)])
def test_a_flat_patch_empties_only_once_it_covers_a_whole_band_window(
        patch, emptied):
    """`band == 0` needs five consecutive exactly-zero ROC readings, and a
    patch of L constant closes carries L - 20 of them -- so 24 flat bars
    empty nothing and 25 empty one bar."""
    base = _walk()
    end = N - 40
    c = base.copy()
    c.iloc[end - patch + 1:end + 1] = float(base.iloc[end - patch + 1])
    extra = sk_rocwb_ratio(c).isna() & sk_rocwb_ratio(base).notna()
    assert int(extra.sum()) == emptied


# ------------------------------------------------------------ 6. GUARDS


def _plant(value, at=None):
    base = _walk()
    at = N - 80 if at is None else at
    c = base.copy()
    c.iloc[at] = value
    return base, c, at


def test_a_nan_close_empties_exactly_ten_bars_and_moves_nothing_earlier():
    """Its own ROC and the four band windows that contain it, then the
    same five 20 bars later. ⚠ Bars AFTER that move in their last bits --
    pandas' rolling mean is an online accumulator -- which is asserted to
    be last-bit-sized rather than asserted away."""
    base, c, at = _plant(np.nan)
    clean, col = sk_rocwb_ratio(base), sk_rocwb_ratio(c)
    emptied = list(np.flatnonzero((col.isna() & clean.notna()).to_numpy()))
    assert emptied == list(range(at, at + BAND_LENGTH)) + \
        list(range(at + LENGTH, at + LENGTH + BAND_LENGTH))
    assert _bit_equal(col.iloc[:at], clean.iloc[:at])
    tail = col.notna() & clean.notna()
    late = tail & (col.index > col.index[at + LENGTH + BAND_LENGTH])
    assert float((col[late] - clean[late]).abs().max()) < 1e-10


def test_an_infinite_close_is_the_nan_close_bit_for_bit():
    """What the `isfinite` mask buys. Both signs."""
    base, nan_c, at = _plant(np.nan)
    for value in (np.inf, -np.inf):
        _, c, _ = _plant(value)
        assert _bit_equal(sk_rocwb_ratio(c), sk_rocwb_ratio(nan_c))


def test_without_the_mask_a_mutant_leaves_numbers_where_the_gap_belongs():
    """The mask's whole case, as a mutant of the shipped source: remove it
    and an infinite close empties only the five bars around itself, while
    the five at P + 20 .. P + 24 carry plausible NUMBERS computed off an
    infinite base price (-2.2216 where the clean column reads 0.4980 on
    the 1,500-bar walk). A number is harder to notice than a gap."""
    base, c, at = _plant(np.inf)
    unmasked = _mutant(*MASK_OFF)(c)
    masked, clean = sk_rocwb_ratio(c), sk_rocwb_ratio(base)
    late = range(at + LENGTH, at + LENGTH + BAND_LENGTH)
    assert bool(masked.iloc[list(late)].isna().all())
    assert bool(unmasked.iloc[list(late)].notna().all())
    assert bool((unmasked.iloc[list(late)] != clean.iloc[list(late)]).all())


@pytest.mark.parametrize("value,emptied", [(0.0, 5), (1e-310, 5),
                                           (1e300, 5), (-1.0, 0)])
def test_a_finite_but_absurd_close_is_not_masked(value, emptied):
    """A zero, subnormal, enormous or negative close is a finite price, so
    the mask does not touch it: it empties 5 bars instead of 10, or none
    at all. ⚠ None of them leaves a quiet 0.0 -- measured 0 new bars
    reading exactly 0.0 on all four."""
    base, c, at = _plant(value)
    clean, col = sk_rocwb_ratio(base), sk_rocwb_ratio(c)
    assert int((col.isna() & clean.notna()).sum()) == emptied
    assert int(((col == 0.0) & (clean != 0.0)).sum()) == 0
    assert _bit_equal(col.iloc[:at], clean.iloc[:at])


@pytest.mark.parametrize("name", NAMES)
def test_the_infinity_fold_is_a_no_op_on_every_frame(name):
    """`band == 0` forces `roc[T] == 0` with it, so the quotient is 0/0 =
    NaN and never +-inf. The `replace` is dead code, kept because it is
    the prototype's expression and the prototype is what Gate E measured;
    this test is what would notice if that ever stopped being true."""
    close = FRAMES[name]()
    raw = _mutant(*FIN_OFF)(close)
    assert int(np.isinf(raw).sum()) == 0
    assert _bit_equal(raw, sk_rocwb_ratio(close))


def test_the_input_series_is_not_mutated():
    close = _walk()
    before = close.to_numpy(dtype=float).copy()
    sk_rocwb_ratio(close)
    assert bool((close.to_numpy(dtype=float) == before).all())


# ------------------------------------------------------------ 7. WIRING


def test_the_five_wiring_touch_points():
    close = _walk()
    df = DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99,
                    "close": close,
                    "volume": Series(np.full(close.size, 1e6),
                                     index=close.index)})
    assert hasattr(ta.momentum, "sk_rocwb_ratio")
    assert "sk_rocwb_ratio" in ta.Category["momentum"]
    assert hasattr(df.ta, "sk_rocwb_ratio")
    col = sk_rocwb_ratio(close)
    assert col.name == "SK_ROCWB_RATIO_20_5"
    assert col.category == "momentum"
    assert _bit_equal(df.ta.sk_rocwb_ratio(), col)
    assert SOURCE.exists()


def test_the_accessor_forwards_both_lengths():
    """`hasattr` cannot see a keyword forwarded under the wrong name --
    the `supertrend` failure mode of WIRING-1."""
    close = _walk()
    df = DataFrame({"close": close})
    assert _bit_equal(df.ta.sk_rocwb_ratio(length=10, band_length=3),
                      sk_rocwb_ratio(close, length=10, band_length=3))
    assert df.ta.sk_rocwb_ratio(length=10,
                                band_length=3).name == "SK_ROCWB_RATIO_10_3"


def test_non_default_lengths_name_and_bound_themselves():
    col = sk_rocwb_ratio(_walk(), length=10, band_length=3)
    assert col.name == "SK_ROCWB_RATIO_10_3"
    assert int(np.flatnonzero(col.notna().to_numpy())[0]) == 12
    assert float(col.abs().max()) <= math.sqrt(3) * (1.0 + 1e-12)


def test_offset_and_fillna():
    close = _walk()
    col = sk_rocwb_ratio(close)
    off = sk_rocwb_ratio(close, offset=2)
    assert _bit_equal(off.iloc[2:].reset_index(drop=True),
                      col.iloc[:-2].reset_index(drop=True))
    filled = sk_rocwb_ratio(close, fillna=-9.0)
    assert int((filled == -9.0).sum()) == int(col.isna().sum())


def test_the_source_library_is_not_readable_here():
    """Gate A's attribution is to the ISSUE's naming of Skender's `RocWb`,
    not to a reading of `RocWb.Series.cs`, because that file is not
    reachable from this worktree. The two routes that could actually make
    it readable are pinned -- a vendored C# tree and the `docs/pine/`
    corpus -- so the claim cannot quietly become "checked against
    Skender". A Python-import check is deliberately NOT one of them:
    Stock.Indicators is a NuGet package, so no `import` could ever succeed
    and the assertion would be decoration. The third route, web access, a
    test cannot see; the module docstring says so."""
    assert not (ROOT / "docs" / "pine").exists()
    sources = []
    stack = [ROOT]
    while stack:
        for entry in stack.pop().iterdir():
            if entry.is_dir():
                if entry.name not in (".git", "__pycache__", ".pytest_cache"):
                    stack.append(entry)
            elif entry.suffix in (".cs", ".pine"):
                sources.append(entry)
    assert sources == []


def test_the_docstring_first_paragraph_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows `d[:150].rsplit(' ', 1)[0]`
    of the first paragraph, so a paragraph over 150 characters loses a
    whole word in the dictionary. Measured 138 characters, 12 to spare."""
    body = []
    for line in sk_rocwb_ratio.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) <= 150


def test_the_gate_e_row_is_owed_and_not_yet_recorded():
    """⚠ Gate E is run by issue-solver AFTER this session, so
    `docs/gate_e_ledger.csv` carries no row for this indicator and
    `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
    fails locally (it is a skip in CI, which sets `GATE_E_PENDING_OK=1`).
    That is the expected state of this commit, and this test is the thing
    the receipt session replaces with one pinning the recorded row's
    identity -- the shape issue #107 and #108 used."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "sk_rocwb_ratio"]
    assert rows == []
