# -*- coding: utf-8 -*-
"""SK-ROCWB-RATIO (PandasTa issue #109): every number in
`docs/SkRocwbRatioMeasured.md`.

    python docs/measure_sk_rocwb_ratio.py          # every section, in order
    python docs/measure_sk_rocwb_ratio.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_sk_rocwb_ratio.py` may come from.

    ROC[T]  = 100 * (close[T] / close[T - 20] - 1)
    band[T] = sqrt(mean(ROC[T - 4 .. T]^2))        -- an RMS, not a stdev
    SK_ROCWB_RATIO[T] = ROC[T] / band[T]

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here depends on the machine, and `docs/measure_sk_rocwb_ratio_cpu.py`
re-runs the sections under numpy's reduced CPU dispatch to show which
figures move.
"""
import math
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
from pandas import DataFrame, Series, date_range

from pandas_ta.momentum.roc import roc as ta_roc
from pandas_ta.momentum.sk_rocwb_ratio import sk_rocwb_ratio

N = 1500
LEVEL = 100.0
LENGTH = 20
BAND_LENGTH = 5
#: First bar that can carry a value: `length + band_length - 1`.
WARMUP = LENGTH + BAND_LENGTH - 1
#: The bound of §C2: `roc[T]` is one of the `band_length` squared terms.
BOUND = math.sqrt(BAND_LENGTH)
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where §G plants a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Close-only: this column reads nothing else. The builders are
# `docs/measure_sk_fcb_pos.py`'s (issue #108), minus the high/low spread, so
# a frame name means the same path in both receipts.


def _series(close):
    # Hourly, not daily: §Z runs 400,000 bars, and 400,000 DAYS from 2020 is
    # past pandas' nanosecond datetime bound. Nothing here reads the index.
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
    return c * Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _coarse(seed=7, n=N, level=LEVEL, tick=2.0):
    """A walk rounded to a tick COARSER than its own bar-to-bar move.

    The frame that matters most for THIS column, and not for the reason the
    sibling ports keep it. A coarse grid makes `close[T] == close[T - 20]`
    an everyday event, so the ROC is EXACTLY 0 on many bars -- and a window
    of five exact zeros is the only input that makes the band 0 and the
    quotient 0/0. FVGDEAD (`CLAUDE.md`) is this repo's record of a column
    whose behaviour on synthetic continuous floats said nothing about its
    behaviour on rounded prices.
    """
    return np.round(_walk(seed, n, level) / tick) * tick


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
#: `flat` has an exactly-zero ROC on every bar, so the band is 0 and the
#: column never fires on it (§C). Every "every frame" claim about VALUES is
#: over these seven.
FIRING = [n for n in NAMES if n != "flat"]


# ----------------------------------------------------------------- helpers


def _rel(a, b):
    """Max relative difference over the bars both fire on."""
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


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    """Bars where exactly one fires, or both fire and the values differ."""
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


def _fin(x):
    """The screen harness' `_fin` (`docs/issues/screen/ind_screen.py:37`),
    which is the only guard the prototype's `sdiv` applies."""
    return x.replace([np.inf, -np.inf], np.nan)


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ----------------------------------------------------------------- oracles


def _oracle(close, length=LENGTH, band_length=BAND_LENGTH, skender=True):
    """The source formula by explicit scalar loops, sharing no code with the
    module and no pandas operation with it.

    `skender=True` spells the ROC the way Skender's `Roc.Series.cs` states
    it -- `100 * (newPrice - oldPrice) / oldPrice` -- and `skender=False`
    spells it the way this module and the screen prototype do,
    `100 * (close / old - 1)`. The two are the same identity and NOT the
    same floating-point number, which is §A3.

    The band is a fresh five-term sum of squares per bar, not pandas'
    rolling mean, so even the `skender=False` limb is only bit-equal to the
    module if pandas' rolling algorithm agrees with a naive sum -- §A2
    prints whether it does rather than assuming it.

    The `isfinite` mask is the module's own (not the prototype's); without
    it this oracle would be measuring a different guard, not a different
    formula.
    """
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
    """`docs/issues/screen/ind_screen_r2.py`, candidate `sk_rocwb_ratio`,
    retyped (that file is gitignored, so it is on the owner's machine only):

        def mean(x, n): return x.rolling(n).mean()
        def sdiv(a, b): return _fin(a / b)   # +-inf -> NaN

        @cand("sk_rocwb_ratio", ...)
        def _(o, h, l, c, v):
            r = 100 * (c / c.shift(20) - 1)
            return sdiv(r, np.sqrt(mean(r ** 2, 5)))

    ⚠ NOT a second derivation: it is the module's own expression without the
    `isfinite` mask. What it buys is the TIE to the screen's Gate E figures,
    which were measured on exactly this.
    """
    r = 100 * (close / close.shift(length) - 1)
    return _fin(r / np.sqrt((r ** 2).rolling(band_length).mean()))


def _via_roc(close, length=LENGTH, band_length=BAND_LENGTH):
    """The reading NOT taken: the same ratio built on the fork's shipped
    `roc`, which spells the ROC `100 * mom(close, length) / close.shift()`.
    §A3 prices what importing it would have cost."""
    r = ta_roc(close, length)
    return _fin(r / np.sqrt((r ** 2).rolling(band_length).mean()))


def _stdev_band(close, length=LENGTH, band_length=BAND_LENGTH):
    """The reading NOT taken, and the one a reader of the name assumes:
    the band as a STANDARD DEVIATION of the ROC (mean subtracted) instead of
    its root mean square."""
    r = 100 * (close / close.shift(length) - 1)
    return _fin(r / r.rolling(band_length).std(ddof=0))


# ----------------------------------------------------------------- mutants

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "momentum" / "sk_rocwb_ratio.py"

ROC_LINE = "    roc = 100 * (c / c.shift(length) - 1)"
BAND_LINE = "    band = np.sqrt((roc ** 2).rolling(band_length).mean())"
RATIO_LINE = "    ratio = roc / band"

#: (label, old text, new text), each an edit to the SHIPPED file, read off
#: disk and exec'd in memory so no mutant can drift from the source it
#: claims to edit.
CAUSALITY_MUTANTS = [
    ("roc-lead", ROC_LINE, "    roc = 100 * (c / c.shift(-length) - 1)"),
    ("close-lead", ROC_LINE,
     "    roc = 100 * (c.shift(-1) / c.shift(length) - 1)"),
    ("band-centred", BAND_LINE,
     "    band = np.sqrt((roc ** 2).rolling(band_length, center=True)"
     ".mean())"),
    ("band-lead", BAND_LINE,
     "    band = np.sqrt((roc ** 2).rolling(band_length).mean()).shift(-1)"),
    ("output-early", RATIO_LINE, "    ratio = (roc / band).shift(-1)"),
]
#: Not a causality mutant: the `isfinite` mask, removed, to price it (§G2).
MASK_OFF = ("    c = close.where(np.isfinite(close))", "    c = close")
#: Not a causality mutant either: the prototype's `sdiv`, removed, to show
#: what the `+-inf -> NaN` fold catches (§G3).
FIN_OFF = ("    ratio = ratio.replace([np.inf, -np.inf], np.nan)",
           "    ratio = ratio")


def _exec(text):
    ns = {}
    exec(compile(text, "<mutant>", "exec"), ns)
    return ns


def _edited(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    return src.replace(old, new)


def _mutant(old, new):
    """`sk_rocwb_ratio` with one edit applied to the shipped source."""
    return _exec(_edited(old, new))["sk_rocwb_ratio"]


def _futures(close, j, spread=3.0):
    """Two closes that agree BIT FOR BIT on bars < j and differ wholly on
    bars >= j: one with every later bar scaled UP by a per-bar random factor
    in [1, 4], one with every later bar scaled DOWN by its reciprocal.

    Bars < j are multiplied by exactly 1.0, which is exact in binary, so the
    shared prefix is shared to the last bit.
    """
    n = close.size
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return (close * Series(up, index=close.index),
            close * Series(dn, index=close.index))


def _caught_at(fn, close, j):
    """Does bar < j read bar >= j? Two wholly different futures, one shared
    past: a causal column is bit-identical on the shared part."""
    a, b = (fn(f).iloc[:j] for f in _futures(close, j))
    return not _bit_equal(a, b)


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- the source formula by explicit scalar loops")
    print("Skender's `RocWb`: a 20-bar ROC, and a band that is the ROOT MEAN")
    print("SQUARE of the last 5 ROC readings (`sqrt(sum(roc^2) / 5)`), not a")
    print("standard deviation -- nothing is subtracted. The oracle is two")
    print("Python loops over numpy scalars and shares no pandas operation")
    print("with the module; the quotient is the fork's scale-free form.")
    print()
    print("⚠ The ROC is spelled Skender's way here, `100 * (c - c20) / c20`.")
    print("The module spells it `100 * (c / c20 - 1)`, which is the screen")
    print("prototype's spelling and the one Gate E was measured on. Same")
    print("identity, different floating-point number -- that is the point of")
    print("this row, and §A3 takes the gap apart.")
    print()
    print(f"{'frame':>13} {'bars':>6} {'fired':>6} {'bit-equal':>10} "
          f"{'differ':>7} {'max rel':>11} {'max abs':>11} {'spearman':>9}")
    for name in NAMES:
        close = FRAMES[name]()
        col, orc = sk_rocwb_ratio(close), _oracle(close)
        print(f"{name:>13} {close.size:>6} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, orc)):>10} {_differs(col, orc):>7} "
              f"{_rel(col, orc):>11.3e} {_abs(col, orc):>11.3e} "
              f"{_spearman(col, orc):>9.4f}")
    print()
    print("`differ` counts bars where the two disagree at all, including a")
    print("disagreement about whether the bar fires. `fired` is the row §C")
    print("reads for Gate C.")


def section_A2():
    _head("A2 Gate A -- the same loops, the module's spelling of the ROC")
    print("The oracle again, with `100 * (c / c20 - 1)` instead of Skender's")
    print("spelling and nothing else changed. If the module is the formula,")
    print("this is bit-equal to it -- and it also tests one thing a reader")
    print("would not think to ask: whether pandas' rolling mean (an online")
    print("add/remove with Kahan compensation) agrees to the last bit with a")
    print("fresh five-term sum.")
    print()
    print(f"{'frame':>13} {'bit-equal':>10} {'differ':>7} {'max rel':>11}")
    for name in NAMES:
        close = FRAMES[name]()
        col = sk_rocwb_ratio(close)
        orc = _oracle(close, skender=False)
        print(f"{name:>13} {str(_bit_equal(col, orc)):>10} "
              f"{_differs(col, orc):>7} {_rel(col, orc):>11.3e}")
    print()
    print("And the screen prototype, retyped -- the expression Gate E's")
    print("0.8537 was measured on. It is the module's own expression without")
    print("the `isfinite` mask, so bit-equality on a FINITE frame is")
    print("structural; what it buys is the tie to that figure.")
    print()
    print(f"{'frame':>13} {'bit-equal':>10} {'differ':>7}")
    for name in NAMES:
        close = FRAMES[name]()
        print(f"{name:>13} "
              f"{str(_bit_equal(sk_rocwb_ratio(close), _prototype(close))):>10} "
              f"{_differs(sk_rocwb_ratio(close), _prototype(close)):>7}")


def section_A3():
    _head("A3 The two spellings of the ROC, and the shipped `roc`")
    print("`100 * (c / c20 - 1)` loses accuracy where `c` is close to `c20`:")
    print("the quotient rounds to 1 + e and the subtraction keeps whatever")
    print("is left. `100 * (c - c20) / c20`, which is what `pandas_ta.roc`")
    print("computes (`100 * mom(close, length) / close.shift(length)`), does")
    print("the subtraction first. The column divides one such number by a")
    print("root mean square of five of them, so the error does not cancel.")
    print()
    print("⚠ The module does NOT import `roc`, and this table is NOT the")
    print("reason: a gap of 4e-12 at Spearman 1.0000 cannot move a Gate E")
    print("rho reported to four decimals. The reason is PROVENANCE -- the")
    print("screen's 0.8537 was measured on the prototype's spelling, and")
    print("shipping that spelling bit for bit (§A2) makes the port and the")
    print("screened candidate the same object. What this table prices is")
    print("the size of the override's cost, not a risk.")
    print()
    print(f"{'frame':>13} {'differ':>7} {'max rel':>11} {'max abs':>11} "
          f"{'spearman':>9} {'bit-equal':>10}")
    for name in NAMES:
        close = FRAMES[name]()
        col, via = sk_rocwb_ratio(close), _via_roc(close)
        print(f"{name:>13} {_differs(col, via):>7} {_rel(col, via):>11.3e} "
              f"{_abs(col, via):>11.3e} {_spearman(col, via):>9.4f} "
              f"{str(_bit_equal(col, via)):>10}")
    print()
    print("The reading NOT taken: the band as a STANDARD DEVIATION of the")
    print("ROC (ddof=0) rather than its root mean square. A reader who")
    print("knows Bollinger-style bands will assume this one, and it is a")
    print("DIFFERENT COLUMN -- it is not bounded, because the numerator is")
    print("no longer one of the terms of the denominator.")
    print()
    print(f"{'frame':>13} {'differ':>7} {'spearman':>9} {'rms max|x|':>11} "
          f"{'std max|x|':>11}")
    for name in FIRING:
        close = FRAMES[name]()
        col, std = sk_rocwb_ratio(close), _stdev_band(close)
        print(f"{name:>13} {_differs(col, std):>7} "
              f"{_spearman(col, std):>9.4f} "
              f"{float(col.abs().max()):>11.4f} "
              f"{float(std.abs().max()):>11.4f}")


def section_B():
    _head("B Gate B -- the blind causality sweep")
    print("For each boundary j: two closes that agree bit for bit on bars")
    print("< j and differ wholly on bars >= j. A causal column is")
    print("bit-identical on the shared prefix. Every offset of every frame,")
    print("not a sample.")
    print()
    print(f"{'frame':>13} {'offsets':>8} {'caught':>7}")
    offsets = list(range(1, N))
    for name in NAMES:
        close = FRAMES[name]()
        print(f"{name:>13} {len(offsets):>8} "
              f"{_sweep(sk_rocwb_ratio, close, offsets):>7}")


def section_B1():
    _head("B1 Gate B -- five look-ahead mutants, read off the shipped source")
    print("Prefix truncation alone cannot see back-dating, so each mutant is")
    print("an edit to the SHIPPED file, exec'd in memory, and swept by the")
    print("same detector.")
    print()
    print("`live` is the number of the eight frames on which the mutant's")
    print("output differs from the module's at all: a mutant that is not")
    print("live is an edit that failed to take, and a clean sweep against it")
    print("would prove nothing.")
    print()
    header = f"{'mutant':>14} {'live':>5} " + \
        " ".join(f"{n[:9]:>9}" for n in NAMES)
    print(header)
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        live, caught = 0, []
        for name in NAMES:
            close = FRAMES[name]()
            live += int(_differs(sk_rocwb_ratio(close), fn(close)) > 0)
            caught.append(_sweep(fn, close))
        print(f"{label:>14} {live:>5} " + " ".join(f"{c:>9}" for c in caught))
    print()
    print(f"each frame contributes {len(OFFSETS)} offsets "
          f"({OFFSETS[0]} .. {OFFSETS[-1]})")
    print()
    print("⚠ The three mutants that reach into the ROC are caught on 36 of")
    print("36 offsets of every frame, `flat` included. The two that reach")
    print("into the BAND are not, and that is expected rather than")
    print("reassuring: a shifted band multiplies a numerator that is")
    print("EXACTLY 0 on 449 bars of `coarse` and on every bar of `flat`,")
    print("and 0 / anything is 0 either way. §B2 gives each of the two a")
    print("necessary condition and sweeps it densely.")


def _roc_of(close):
    return 100 * (close / close.shift(LENGTH) - 1)


def _nonzero(roc, i):
    v = roc.iloc[i]
    return bool(v == v and v != 0.0)


def _exposed_band_lead(roc, j, n):
    """`band-lead` writes `roc[i] / band[i + 1]`, so the only prefix bar it
    can reach the future with is `j - 1`. It moves only if that numerator
    is non-zero and the bar carries a value at all -- which needs the
    SHIFTED band to exist, `i + 1 >= WARMUP`, not merely the ROC."""
    i = j - 1
    return i + 1 >= WARMUP and i + 1 <= n - 1 and _nonzero(roc, i)


def _exposed_band_centred(roc, j, n):
    """`band-centred` centres the window, so bars `j - 1` and `j - 2` read
    forward. Same necessary condition on each -- a non-zero numerator --
    plus the window has to FIT: five non-NaN ROC readings (`i - 2 >=
    LENGTH`) and no bar past the end of the frame (`i + 2 <= n - 1`),
    which is what makes the last two offsets of a frame different from
    the rest."""
    return any(i - 2 >= LENGTH and i + 2 <= n - 1 and _nonzero(roc, i)
               for i in (j - 1, j - 2))


def section_B2():
    _head("B2 Gate B -- the two band mutants, swept densely")
    print("Both are caught on fewer than 36 of 36 offsets of some frame in")
    print("§B1, so a clean sweep against the MODULE is only as strong as the")
    print("reason for those misses. Each mutant is therefore given a")
    print("NECESSARY condition for being catchable at all, computed from the")
    print("clean frame's ROC rather than argued, and the catches are counted")
    print("inside and outside it over every offset of every frame.")
    print()
    print("`outside` must be 0, or the condition is wrong and this section")
    print("proves nothing. `missed` is exposed-but-not-caught.")
    print()
    # From bar 1, not from the warm-up: the condition has to hold where the
    # bars it talks about do not exist either, and starting the sweep late
    # would make a loose condition look exact.
    offsets = list(range(1, N))
    for label, exposed_at in (("band-lead", _exposed_band_lead),
                              ("band-centred", _exposed_band_centred)):
        _, old, new = next(m for m in CAUSALITY_MUTANTS if m[0] == label)
        fn = _mutant(old, new)
        print(f"{label}: exposed(j) = "
              + ("roc[j - 1] is a non-zero number" if label == "band-lead"
                 else "roc[j - 1] or roc[j - 2] is a non-zero number"))
        print()
        print(f"{'frame':>13} {'offsets':>8} {'exposed':>8} {'caught':>7} "
              f"{'in exposed':>11} {'outside':>8} {'missed':>7}")
        tot = [0, 0, 0, 0, 0]
        for name in NAMES:
            close = FRAMES[name]()
            roc = _roc_of(close)
            n_exp = n_caught = n_in = n_out = 0
            for j in offsets:
                exposed = exposed_at(roc, j, close.size)
                caught = _caught_at(fn, close, j)
                n_exp += exposed
                n_caught += caught
                n_in += caught and exposed
                n_out += caught and not exposed
            tot = [tot[0] + len(offsets), tot[1] + n_exp, tot[2] + n_caught,
                   tot[3] + n_out, tot[4] + (n_exp - n_in)]
            print(f"{name:>13} {len(offsets):>8} {n_exp:>8} {n_caught:>7} "
                  f"{n_in:>11} {n_out:>8} {n_exp - n_in:>7}")
        print()
        print(f"control totals: {tot[0]} offsets, {tot[1]} exposed, "
              f"{tot[2]} caught, {tot[3]} caught outside the condition, "
              f"{tot[4]} exposed-but-missed")
        print()
    print("The module itself over the same dense grid, for comparison: §B,")
    print("0 caught of 1,499 offsets on each of the eight frames.")


def section_C():
    _head("C Gate C -- reachability")
    print("Fired bars, the first fired bar, and the value range per frame.")
    print("The warm-up is NOT data-dependent: the ROC needs `length` bars")
    print(f"and the band `band_length` of those, so bar {WARMUP} is the first")
    print("that can carry a value, on every frame that fires at all.")
    print()
    print(f"{'frame':>13} {'bars':>6} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'min':>10} {'max':>10} {'zeros':>6}")
    for name in NAMES:
        close = FRAMES[name]()
        col = sk_rocwb_ratio(close)
        v = col.dropna()
        first = int(np.flatnonzero(col.notna().to_numpy())[0]) if v.size \
            else -1
        if v.size:
            print(f"{name:>13} {col.size:>6} {v.size:>6} {first:>6} "
                  f"{v.nunique():>9} {v.min():>10.4f} {v.max():>10.4f} "
                  f"{int((v == 0.0).sum()):>6}")
        else:
            print(f"{name:>13} {col.size:>6} {v.size:>6} {first:>6} "
                  f"{0:>9} {'--':>10} {'--':>10} {0:>6}")
    print()
    print("Gate D's constant-column guard, 0 < fires < n, read off the same")
    print("rows: `flat` fires 0 and is the one frame that fails it. That is")
    print("a reading about a constant price -- every ROC is exactly 0, so")
    print("the band is exactly 0 and every bar is 0/0 -- and §C3 shows it is")
    print("ordinary for the bucket rather than a defect.")
    print()
    print("The earliest POSSIBLE fire, on a hand frame of exactly")
    print(f"{WARMUP + 1} bars (the signature's minimum input):")
    close = _series(np.array([100.0 + i for i in range(WARMUP + 1)]))
    col = sk_rocwb_ratio(close)
    print(f"  bars={col.size} fired={int(col.notna().sum())} "
          f"first={int(np.flatnonzero(col.notna().to_numpy())[0])} "
          f"value={float(col.iloc[-1]):.6f}")
    short = sk_rocwb_ratio(close.iloc[:-1])
    print(f"  one bar shorter ({WARMUP} bars): verify_series returns "
          f"{short!r}")


def section_C2():
    _head("C2 THE BOUND -- the section to read first")
    print("`roc[T]` is itself one of the `band_length` terms the band")
    print("averages, so")
    print()
    print("    band[T]^2 = (roc[T]^2 + ... ) / band_length >= roc[T]^2 / 5")
    print("    => |roc[T] / band[T]| <= sqrt(band_length) = "
          f"{BOUND:.7f}")
    print()
    print("The column is therefore BOUNDED, which is unusual for a momentum")
    print("feature and is the reason this form ships rather than the ROC and")
    print("the band as two price-unit series. The bound is checked bar by")
    print("bar below -- both `over` columns must be 0 -- and `closest` is")
    print("the largest |value| / sqrt(5) reached.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'min':>10} {'max':>10} "
          f"{'max |x|':>10} {'closest':>9} {'over strict':>12} "
          f"{'over 1e-12':>11}")
    for name in FIRING:
        close = FRAMES[name]()
        col = sk_rocwb_ratio(close).dropna()
        strict = int((col.abs() > BOUND).sum())
        slack = int((col.abs() > BOUND * (1.0 + 1e-12)).sum())
        print(f"{name:>13} {col.size:>6} {col.min():>10.4f} "
              f"{col.max():>10.4f} {float(col.abs().max()):>10.4f} "
              f"{float(col.abs().max()) / BOUND:>9.4f} {strict:>12} "
              f"{slack:>11}")
    print()
    print()
    print("`closest` is rounded to four decimals, so 1.0000 does not mean")
    print("ATTAINED. For any frame that rounds to 1.0000, the ulp distance")
    print("between its `max |x|` and `math.sqrt(5)`:")
    for name in FIRING:
        col = sk_rocwb_ratio(FRAMES[name]()).dropna()
        peak = float(col.abs().max())
        if round(peak / BOUND, 4) != 1.0:
            continue
        ulps = abs(np.float64(peak).view(np.int64)
                   - np.float64(BOUND).view(np.int64))
        print(f"  {name:>13}: max |x| = {peak!r}, sqrt(5) = {BOUND!r}, "
              f"{ulps} ulps apart")
    print()
    print("Two columns, because `sqrt(5)` is itself a rounded double and the")
    print("test asserts the bound with 1e-12 of slack: `over strict` is how")
    print("many bars exceed `math.sqrt(5)` at all, `over 1e-12` how many")
    print("exceed it by more than that slack. The Returns line of the module")
    print("docstring is only entitled to the closed interval if the strict")
    print("column is 0 everywhere.")
    print()
    print("A random walk approaches the bound without reaching it. The bound")
    print("is ATTAINED when the four previous ROC readings are exactly 0 and")
    print("today's is not -- a flat 20-bar window followed by one move:")
    close = _series(np.array([100.0] * (LENGTH + BAND_LENGTH - 1) + [110.0]))
    col = sk_rocwb_ratio(close)
    last = float(col.iloc[-1])
    print()
    print(f"  closes        : {LENGTH + BAND_LENGTH - 1} x 100.0, then 110.0")
    print(f"  value         : {last!r}")
    print(f"  sqrt(5)       : {BOUND!r}")
    print(f"  value / bound : {last / BOUND!r}")
    print(f"  ulps apart    : "
          f"{abs(np.float64(last).view(np.int64) - np.float64(BOUND).view(np.int64))}")
    print()
    print("The negative end, same frame with the move DOWN:")
    close = _series(np.array([100.0] * (LENGTH + BAND_LENGTH - 1) + [90.0]))
    print(f"  value         : {float(sk_rocwb_ratio(close).iloc[-1])!r}")
    print()
    print("⚠ The bound is on the VALUE, not on the information: a bar at")
    print("+2.2360 means `the other four ROC readings were ~0`, which on a")
    print("tick grid is a statement about rounding rather than about")
    print("momentum. §C4 counts how often a flat window happens.")


def section_C3():
    _head("C3 What the REST of the momentum bucket does on a flat price")
    print("§C says this column fires 0 of 1,500 bars on `flat`. Whether that")
    print("is unusual for the bucket is a claim about 86 other indicators,")
    print("so it is RUN rather than asserted: every name in")
    print("`Category['momentum']` on one flat OHLCV frame, through the")
    print("accessor, with its columns classified.")
    print()
    import pandas_ta as ta
    n = 300
    one = _series(np.full(n, LEVEL))
    df = DataFrame({"open": one, "high": one, "low": one, "close": one,
                    "volume": Series(np.full(n, 1e6), index=one.index)})
    all_nan = zeros = other = 0
    failed = []
    nan_names, other_names = [], []
    for name in sorted(ta.Category["momentum"]):
        try:
            out = getattr(df.ta, name)()
        except Exception as exc:                     # noqa: BLE001
            failed.append(f"{name}: {type(exc).__name__}")
            continue
        if out is None:
            failed.append(f"{name}: None")
            continue
        cols = ({c: out[c] for c in out.columns}
                if isinstance(out, DataFrame) else {out.name: out})
        for col_name, col in cols.items():
            if col.isna().all():
                all_nan += 1
                nan_names.append(col_name)
            elif bool((col.dropna() == 0.0).all()):
                zeros += 1
            else:
                other += 1
                other_names.append(col_name)
    total = all_nan + zeros + other
    print(f"names    : {len(ta.Category['momentum'])}")
    print(f"columns  : {total}")
    print(f"all-NaN  : {all_nan}")
    print(f"all-zero : {zeros}")
    print(f"other    : {other}")
    print(f"failed   : {failed}")
    print()
    print("This column's own column is in the all-NaN group: "
          f"{'SK_ROCWB_RATIO_20_5' in nan_names}")
    print()
    print("A sample of the all-NaN company, so the claim is checkable:")
    print(f"  {sorted(nan_names)[:14]}")


def section_C4():
    _head("C4 The only way this column goes blank: a flat band window")
    print("`band == 0` needs all five squared ROC readings to be 0, and a")
    print("squared ROC is 0 only if the ROC is: `c / c20` is either exactly")
    print("1 or at least one ulp away from it, so a non-zero |ROC| is at")
    print("least ~1.1e-14 and its square is nowhere near underflow. The")
    print("smallest non-zero |ROC| actually seen on these frames is printed")
    print("below. So the column is NaN exactly where the last five 20-bar")
    print("ROC readings are ALL exactly 0, which needs 25 flat bars: a patch")
    print("of L constant closes carries L - 20 zero ROC readings.")
    print()
    print(f"{'frame':>13} {'min |ROC|>0':>12} {'ROC == 0':>9}")
    for name in NAMES:
        close = FRAMES[name]()
        roc = (100 * (close / close.shift(LENGTH) - 1)).abs()
        nz = roc[(roc > 0.0) & roc.notna()]
        print(f"{name:>13} "
              f"{(float(nz.min()) if nz.size else float('nan')):>12.3e} "
              f"{int((roc == 0.0).sum()):>9}")
    print()
    print("Flat patches planted in a walk, each ending at bar 800:")
    print()
    print(f"{'patch':>7} {'emptied':>8} {'first':>6} {'last':>6} "
          f"{'band==0':>8}")
    base = _walk()
    for patch in (20, 23, 24, 25, 29, 40):
        c = base.copy()
        c.iloc[800 - patch + 1:801] = float(base.iloc[800 - patch + 1])
        col = sk_rocwb_ratio(c)
        ref = sk_rocwb_ratio(base)
        extra = col.isna() & ref.notna()
        idx = list(np.flatnonzero(extra.to_numpy()))
        roc = 100 * (c / c.shift(LENGTH) - 1)
        band = np.sqrt((roc ** 2).rolling(BAND_LENGTH).mean())
        print(f"{patch:>7} {len(idx):>8} "
              f"{(idx[0] if idx else -1):>6} {(idx[-1] if idx else -1):>6} "
              f"{int((band == 0.0).sum()):>8}")
    print()
    print("And on the coarse grid, where equal prices 20 bars apart happen")
    print("by rounding rather than by construction:")
    close = _coarse()
    roc = 100 * (close / close.shift(LENGTH) - 1)
    band = np.sqrt((roc ** 2).rolling(BAND_LENGTH).mean())
    col = sk_rocwb_ratio(close)
    print(f"  bars with ROC exactly 0 : {int((roc == 0.0).sum())}")
    print(f"  bars with band 0        : {int((band == 0.0).sum())}")
    print(f"  bars emptied after {WARMUP}  : "
          f"{int(col.iloc[WARMUP:].isna().sum())}")
    print(f"  bars reading exactly 0.0: {int((col == 0.0).sum())}")
    print()
    print("⚠ A bar reading exactly 0.0 is NOT a blank: it is `ROC == 0` with")
    print("a non-zero band, i.e. the price is where it was 20 bars ago while")
    print("the other four readings were not. On a tick grid that is common,")
    print("and it is the same tie-on-rounded-prices effect FVGDEAD cost this")
    print("repo once.")


def section_D():
    _head("D Gate D -- scale invariance")
    print("The input enters only as `close[T] / close[T - 20]`, so a")
    print("positive rescale cancels BEFORE the first arithmetic. x8 and x64")
    print("are exact binary factors and must be bit-identical; x10, x3.7,")
    print("x0.1 and x1.0000001 re-round every price and are compared at a")
    print("tolerance with their NaN masks.")
    print()
    print(f"{'frame':>13} {'factor':>11} {'bit-equal':>10} {'masks':>6} "
          f"{'max rel':>11} {'spearman':>9}")
    for name in FIRING:
        close = FRAMES[name]()
        col = sk_rocwb_ratio(close)
        for factor in (8.0, 64.0, 10.0, 3.7, 0.1, 1.0000001):
            other = sk_rocwb_ratio(close * factor)
            print(f"{name:>13} {factor:>11} {str(_bit_equal(col, other)):>10} "
                  f"{str(bool((col.isna() == other.isna()).all())):>6} "
                  f"{_rel(col, other):>11.3e} {_spearman(col, other):>9.4f}")
    print()
    print("The same walk at three price LEVELS, which is the same")
    print("multiplication with a much longer lever. ⚠ `1e-6 / 100` is NOT")
    print("an exact binary factor, so these are a tolerance row and not a")
    print("bit-equality row; the exact-factor rows above are the ones Gate")
    print("D reads. The point of this one is that nothing OVERFLOWS or")
    print("goes blank 100 orders of magnitude from the test level.")
    print()
    print(f"{'level':>11} {'bit-equal':>10} {'fired':>6} {'max rel':>11} "
          f"{'spearman':>9}")
    close = _walk()
    col = sk_rocwb_ratio(close)
    for level in (1e-6, 1e6, 1e100):
        other = sk_rocwb_ratio(close * (level / LEVEL))
        print(f"{level:>11} {str(_bit_equal(col, other)):>10} "
              f"{int(other.notna().sum()):>6} {_rel(col, other):>11.3e} "
              f"{_spearman(col, other):>9.4f}")
    print()
    print("and the same three as EXACT binary factors, on EVERY frame,")
    print("which must be bit-identical:")
    print()
    print(f"{'frame':>13} " + " ".join(f"{f'x2^{e}':>12}"
                                       for e in (-20, 20, 300)))
    for name in NAMES:
        frame = FRAMES[name]()
        base = sk_rocwb_ratio(frame)
        row = [str(_bit_equal(base, sk_rocwb_ratio(frame * 2.0 ** e)))
               for e in (-20, 20, 300)]
        print(f"{name:>13} " + " ".join(f"{v:>12}" for v in row))
    print()
    print("⚠ A LEVEL SHIFT is NOT invariant, and a reader who has met the")
    print("sibling `sk_fcb_pos` (where it is) must not assume it here: a")
    print("ratio of prices is not a ratio of prices-plus-a-constant.")
    print()
    print(f"{'shift':>11} {'bit-equal':>10} {'max abs':>11} {'max rel':>11} "
          f"{'spearman':>9}")
    for shift in (1.0, 50.0, 1e6):
        other = sk_rocwb_ratio(close + shift)
        print(f"{shift:>11} {str(_bit_equal(col, other)):>10} "
              f"{_abs(col, other):>11.3e} {_rel(col, other):>11.3e} "
              f"{_spearman(col, other):>9.4f}")
    print()
    print("Gate D's other limb, 0 < fires < n, is §C's `fired` column: the")
    print("seven firing frames all fire strictly between 0 and 1,500.")


def section_F():
    _head("F Non-redundancy against the fork's own close-only columns")
    print("⚠ SYNTHETIC and a DISCLOSURE, not a gate: Gate E measures 687")
    print("engine comparators over 89 real BIST frames, and none of them is")
    print("this. What this table is for is the one comparator that is")
    print("structurally close -- the ROC the column is built on -- and the")
    print("one the screen already flagged, a z-score of price.")
    print()
    from pandas_ta.momentum.cmo import cmo
    from pandas_ta.momentum.mom import mom
    from pandas_ta.momentum.rsi import rsi
    from pandas_ta.statistics.zscore import zscore
    others = {
        "ROC_20": lambda c: ta_roc(c, LENGTH),
        "ROC_5": lambda c: ta_roc(c, 5),
        "MOM_20": lambda c: mom(c, LENGTH),
        "RSI_14": lambda c: rsi(c, 14),
        "CMO_14": lambda c: cmo(c, 14),
        "ZS_30": lambda c: zscore(c, 30),
        "ZS_20_of_ROC": lambda c: zscore(ta_roc(c, LENGTH), LENGTH),
    }
    print(f"{'frame':>13} " + " ".join(f"{k:>13}" for k in others))
    for name in FIRING:
        close = FRAMES[name]()
        col = sk_rocwb_ratio(close)
        row = [f"{_spearman(col, fn(close)):>13.4f}" for fn in others.values()]
        print(f"{name:>13} " + " ".join(row))
    print()
    print("The sign is shared with the ROC by construction (the band is")
    print("positive), so a high rank correlation against `ROC_20` is")
    print("expected; what the column adds is the SIZE, normalised. The")
    print("fraction of bars where the two disagree in RANK is what the")
    print("table above measures, and `ZS_20_of_ROC` is the nearest thing")
    print("the fork already ships to this construction.")


def section_G():
    _head("G Guards, each priced")
    print("G1 A bad CLOSE. One bar is replaced at index "
          f"{PLANT} and the column")
    print("is compared with the clean one: `emptied` counts bars that went")
    print("NaN, `moved` counts bars that changed value, and `earlier` counts")
    print("any of either before the plant -- which must be 0.")
    print()
    base = _walk()
    clean = sk_rocwb_ratio(base)
    #: The bars a bad close at PLANT can reach THROUGH THE FORMULA: its own
    #: ROC and the band windows that contain it, then the same 20 bars later.
    REACH = set(range(PLANT, PLANT + BAND_LENGTH)) | \
        set(range(PLANT + LENGTH, PLANT + LENGTH + BAND_LENGTH))
    print(f"{'plant':>12} {'emptied':>8} {'moved':>7} {'earlier':>8} "
          f"{'zeros':>6} {'first':>6} {'last':>6} {'in reach':>9} "
          f"{'beyond':>7} {'max |d| beyond':>15}")
    plants = {
        "NaN": np.nan, "+inf": np.inf, "-inf": -np.inf, "0.0": 0.0,
        "-1.0": -1.0, "1e-310": 1e-310, "1e+300": 1e300,
    }
    columns = {}
    for label, value in plants.items():
        c = base.copy()
        c.iloc[PLANT] = value
        col = sk_rocwb_ratio(c)
        columns[label] = col
        emptied = col.isna() & clean.notna()
        moved = col.notna() & clean.notna() & (col != clean)
        touched = emptied | moved
        idx = list(np.flatnonzero(touched.to_numpy()))
        beyond = [i for i in idx if i not in REACH]
        worst = max((abs(float(col.iloc[i]) - float(clean.iloc[i]))
                     for i in beyond), default=float("nan"))
        new_zeros = int(((col == 0.0) & (clean != 0.0)).sum())
        print(f"{label:>12} {int(emptied.sum()):>8} {int(moved.sum()):>7} "
              f"{int(touched.iloc[:PLANT].sum()):>8} {new_zeros:>6} "
              f"{(idx[0] if idx else -1):>6} {(idx[-1] if idx else -1):>6} "
              f"{len([i for i in idx if i in REACH]):>9} {len(beyond):>7} "
              f"{worst:>15.3e}")
    print()
    print("⚠ Two things in that table are not what a reader expects.")
    print()
    print("One: the reach is NOT the 10 bars the formula implies. `emptied`")
    print("stops inside those 10, but `moved` runs to bar 1024, because")
    print("pandas' rolling mean is an ONLINE add/remove accumulator -- a bar")
    print("that enters and leaves the window changes the running sum's last")
    print("bits for every window after it. The `max |d| beyond` column is")
    print("the size of that: it is a last-bit effect, not a second signal,")
    print("and it is disclosed rather than suppressed because it means a")
    print("single bad tick is not exactly undone 25 bars later.")
    print()
    print("Two: `zeros` is 0 everywhere, including the plants a reader would")
    print("expect it on. An infinite ROC does NOT leave a finite numerator")
    print("over an infinite band reading 0.0, because the same online")
    print("accumulator turns the window NaN once the infinity leaves it")
    print("rather than carrying `inf` through. The bars each plant empties:")
    for label in plants:
        col = columns[label]
        print(f"  {label:>7}: "
              f"{list(np.flatnonzero((col.isna() & clean.notna()).to_numpy()))}")
    print()
    print("G2 The `isfinite` mask, which is a DIVERGENCE from the prototype.")
    print("With it, an infinite close behaves exactly like a NaN one; the")
    print("MASK_OFF mutant below is the module with the mask removed, i.e.")
    print("the prototype's guard set.")
    print()
    off = _mutant(*MASK_OFF)
    nan_c = base.copy()
    nan_c.iloc[PLANT] = np.nan
    nan_col = sk_rocwb_ratio(nan_c)
    print(f"  {'plant':>5} {'masked == NaN column':>21} "
          f"{'unmasked == masked':>19} {'unmasked emptied':>17} "
          f"{'unmasked moved':>15} {'unmasked zeros':>15}")
    for label in ("NaN", "+inf", "-inf"):
        c = base.copy()
        c.iloc[PLANT] = plants[label]
        with_mask, without = sk_rocwb_ratio(c), off(c)
        print(f"  {label:>5} {str(_bit_equal(with_mask, nan_col)):>21} "
              f"{str(_bit_equal(without, with_mask)):>19} "
              f"{int((without.isna() & clean.notna()).sum()):>17} "
              f"{int((without.notna() & clean.notna() & (without != clean)).sum()):>15} "
              f"{int(((without == 0.0) & (clean != 0.0)).sum()):>15}")
    print()
    print("  Which bars each one empties, since the counts alone do not say")
    print("  whether the mask moves the gap or only widens it:")
    for label in ("NaN", "+inf"):
        c = base.copy()
        c.iloc[PLANT] = plants[label]
        for tag, col in (("masked", sk_rocwb_ratio(c)), ("unmasked", off(c))):
            print(f"  {label:>5} {tag:>9}: "
                  f"{list(np.flatnonzero((col.isna() & clean.notna()).to_numpy()))}")
    print()
    print("  ⚠ That is the mask's whole case. Unmasked, the five bars at")
    print("  P + 20 .. P + 24 are NOT empty -- they carry a number computed")
    print("  from an infinite base price, and a number is harder to notice")
    print("  than a gap:")
    c = base.copy()
    c.iloc[PLANT] = np.inf
    unmasked = off(c)
    for i in range(PLANT + LENGTH, PLANT + LENGTH + BAND_LENGTH):
        print(f"    bar {i}: unmasked {float(unmasked.iloc[i]):>10.4f}   "
              f"clean {float(clean.iloc[i]):>10.4f}   masked "
              f"{float(sk_rocwb_ratio(c).iloc[i])!r}")
    print()
    print("  and on FINITE input the mask changes nothing, which is what")
    print("  keeps the tie to the prototype's Gate E figure:")
    print()
    print(f"  {'frame':>13} {'masked == unmasked':>20}")
    for name in NAMES:
        close = FRAMES[name]()
        print(f"  {name:>13} "
              f"{str(_bit_equal(sk_rocwb_ratio(close), off(close))):>20}")
    print()
    print("G3 The `+-inf -> NaN` fold, and why it is a no-op here. `band` is")
    print("0 only when `roc[T]` is 0 with it, so the quotient is 0/0 = NaN")
    print("rather than +-inf; the fold can only fire if some OTHER route")
    print("produces an infinite quotient. The FIN_OFF mutant is the module")
    print("without the fold -- the two must agree everywhere the fold is")
    print("dead, and the count of infinite raw quotients is printed.")
    print()
    nofold = _mutant(*FIN_OFF)
    print(f"  {'frame':>13} {'identical':>10} {'raw +-inf':>10} "
          f"{'band==0':>8} {'roc!=0 & band==0':>18}")
    for name in NAMES:
        close = FRAMES[name]()
        raw = nofold(close)
        roc = 100 * (close / close.shift(LENGTH) - 1)
        band = np.sqrt((roc ** 2).rolling(BAND_LENGTH).mean())
        bad = int(((band == 0.0) & (roc != 0.0)).sum())
        print(f"  {name:>13} "
              f"{str(_bit_equal(raw, sk_rocwb_ratio(close))):>10} "
              f"{int(np.isinf(raw).sum()):>10} {int((band == 0.0).sum()):>8} "
              f"{bad:>18}")
    print()
    print("  And the plants of G1, which are the obvious candidates for a")
    print("  quotient that overflows -- a zero close makes an infinite ROC,")
    print("  a 1e+300 close makes a squared ROC that overflows. Neither")
    print("  reaches the fold, because the band goes infinite or NaN with")
    print("  the numerator rather than against it:")
    for label in ("0.0", "1e+300", "+inf", "-1.0"):
        c = base.copy()
        c.iloc[PLANT] = plants[label]
        raw = nofold(c)
        print(f"  {label:>7}: {int(np.isinf(raw).sum())} infinite raw bars, "
              f"{int(raw.isna().sum())} NaN, fold changes it: "
              f"{not _bit_equal(raw, sk_rocwb_ratio(c))}")
    print()
    print("  ⚠ So the `replace` is DEAD CODE on everything measured here.")
    print("  It is kept because it is the prototype's expression and the")
    print("  prototype is what Gate E was measured on -- removing it would")
    print("  be a change to the column with no measurement behind it.")


def section_W():
    _head("W The five wiring touch points")
    import pandas_ta as ta
    close = _walk(n=400)
    df = DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99,
                    "close": close,
                    "volume": Series(np.full(close.size, 1e6),
                                     index=close.index)})
    col = sk_rocwb_ratio(close)
    print("1 module       : pandas_ta/momentum/sk_rocwb_ratio.py")
    print(f"2 package      : {hasattr(ta.momentum, 'sk_rocwb_ratio')}")
    print(f"3 Category     : "
          f"{'sk_rocwb_ratio' in ta.Category['momentum']} "
          f"(momentum has {len(ta.Category['momentum'])})")
    print(f"4 accessor     : {hasattr(df.ta, 'sk_rocwb_ratio')}")
    print("5 tests        : tests/test_sk_rocwb_ratio.py")
    print()
    acc = df.ta.sk_rocwb_ratio()
    print(f"column name    : {col.name}")
    print(f"category tag   : {col.category}")
    print(f"accessor equal : {_bit_equal(col, acc)}")
    print(f"accessor name  : {acc.name}")
    print(f"Category total : {sum(len(v) for v in ta.Category.values())}")
    print()
    print("`length`, `band_length`, `offset` and `fillna`:")
    named = sk_rocwb_ratio(close, length=10, band_length=3)
    print(f"non-default    : {named.name}, first fired bar "
          f"{int(np.flatnonzero(named.notna().to_numpy())[0])}, "
          f"max |x| {float(named.abs().max()):.4f} "
          f"(bound {math.sqrt(3):.4f})")
    off = sk_rocwb_ratio(close, offset=2)
    print(f"offset=2 shifts: "
          f"{_bit_equal(off.iloc[2:].reset_index(drop=True), col.iloc[:-2].reset_index(drop=True))}")
    filled = sk_rocwb_ratio(close, fillna=-9.0)
    print(f"fillna=-9.0    : {int((filled == -9.0).sum())} bars filled, "
          f"{int(col.isna().sum())} were NaN")
    print()
    print("The dictionary cut. `docs/gen_indicator_dictionary.py`'s `desc`")
    print("shows `d[:150].rsplit(' ', 1)[0]` of the docstring's first")
    print("paragraph, so a paragraph over 150 characters loses a WHOLE word.")
    print("The generator's own `desc` is lifted out of its source with `ast`")
    print("here rather than retyped.")
    print()
    import ast
    import re
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[node], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    desc = ns["desc"]
    body = []
    for line in sk_rocwb_ratio.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    slack = 0
    while desc({"desc": paragraph + "x" * slack}) == paragraph + "x" * slack:
        slack += 1
        if slack > 400:
            break
    print(f"paragraph      : {len(paragraph)} characters")
    print(f"survives whole : {desc({'desc': paragraph}) == paragraph}")
    print(f"slack          : {slack - 1} more characters before a word goes")
    print(f"shown as       : {desc({'desc': paragraph})!r}")


def section_W2():
    _head("W2 The dictionary's ML-form tags, counted")
    print("`docs/MLCompanionContract.md` opens with a census of the tagged")
    print("columns in `docs/IndicatorDictionary.md`. It is parsed from the")
    print("generated file here rather than incremented by hand.")
    print()
    path = ROOT / "docs" / "IndicatorDictionary.md"
    tags = ["PX2", "PX", "SF", "BIN", "ORD", "CONST", "??"]
    counts = {t: 0 for t in tags}
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        # One cell holds every column of the indicator, `<br>`-separated.
        for token in cells[3].replace("<br>", " ").split():
            if token.startswith("`"):
                continue
            if token in counts:
                counts[token] += 1
                total += 1
    print(f"tagged columns : {total}")
    for tag in tags:
        print(f"{tag:>15}: {counts[tag]}")
    print()
    print("⚠ The parse is this file's, not the generator's: what it is for")
    print("is the DELTA (one new `SF` column), and the absolute numbers are")
    print("only usable if they reproduce the contract's current ones.")


def section_Z():
    _head("Z Cost")
    print("Vectorised throughout, no Python loop: isfinite and where, one")
    print("shift, a divide, a subtract, a multiply, a square, one rolling")
    print("mean, a sqrt, a second divide and the replace -- plus a shift")
    print("only when offset != 0. Linear in bars.")
    print()
    print(f"{'bars':>10} {'peak MB':>10} {'peak MB (2nd)':>14} "
          f"{'ms':>8} {'ms (2nd)':>10}")
    for n in (100_000, 400_000):
        close = _walk(n=n)
        peaks = []
        for _ in range(2):
            tracemalloc.start()
            sk_rocwb_ratio(close)
            peaks.append(tracemalloc.get_traced_memory()[1] / 1e6)
            tracemalloc.stop()
        times = [timeit.timeit(lambda: sk_rocwb_ratio(close), number=3) / 3
                 * 1e3 for _ in range(2)]
        print(f"{n:>10} {peaks[0]:>10.1f} {peaks[1]:>14.1f} "
              f"{times[0]:>8.1f} {times[1]:>10.1f}")
    print()
    print("⚠ The wall clock is DISCLOSED, not claimed: two invocations of")
    print("the same section already disagree, and both are printed above so")
    print("the spread is visible rather than averaged away.")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3,
    "B": section_B, "B1": section_B1, "B2": section_B2,
    "C": section_C, "C2": section_C2, "C3": section_C3, "C4": section_C4,
    "D": section_D, "F": section_F, "G": section_G,
    "W": section_W, "W2": section_W2, "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
