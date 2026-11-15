# -*- coding: utf-8 -*-
"""Every measured number in `docs/TfHiguchi30Measured.md` and in the
docstrings of `pandas_ta/statistics/tf_higuchi_30.py` and
`tests/test_tf_higuchi_30.py` is printed by this script, EXCEPT:

* §F1's pytest counts, which come from `python -m pytest` itself;
* §F2's list of dispatchable features still enabled, which
  `docs/measure_tf_higuchi_30_cpu.py` prints;
* the Gate E block (0.5231 vs `mad_pct_Pctl`, 0.5298 per-frame, 0.5207,
  0.5015, 398,849 bars, 687 comparators), which is QUOTED FROM ISSUE #115
  and was measured on the prototype by the 2026-10-24 screen, not here.

    python docs/measure_tf_higuchi_30.py            # every section
    python docs/measure_tf_higuchi_30.py A1 D L     # named sections

Sections: A1 the screen prototype, A2 the scalar-loop oracle, A3 the
`lstsq` oracle, A4 the anchors (what a KNOWN curve must read), A5 the
spacing ladder and the points it drops, A6 the readings this port did NOT
take, B causality, C reachability, D scale, G guards, L what the column
reads, L4 the fork overlap, W the dictionary cut, Z cost and the chunk
budget, Z2 which step is sensitive to the block shape.

⚠ Several sections print last-bit figures that MOVE between CPU dispatches.
Run each of A1, A2, A3, D and L under `docs/measure_tf_higuchi_30_cpu.py` as
well before quoting a bound from them: §F2 of `docs/TfHiguchi30Measured.md`
tabulates which figure moves and which dispatch is the worse one.
"""
from __future__ import annotations

import math
import sys
import tracemalloc
from pathlib import Path
from time import perf_counter

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series, date_range

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pandas_ta.statistics.tf_higuchi_30 import (  # noqa: E402
    KMAX, K_VALUES, LOG_INV_K_CENTRED, LOG_INV_K_SS, MIN_LENGTH, _higuchi_fd,
    tf_higuchi_30,
)

N = 1500
LEVEL = 100.0
LENGTH = 30
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_higuchi_30.py"


# ------------------------------------------------------------------ frames

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
    """iid closes: no memory at all, the ROUGHEST curve a price can be."""
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(rng.normal(0.0, sigma, n)))


def _smooth(seed=43, n=N, level=LEVEL, span=40):
    """A walk run through a long moving average: a nearly differentiable
    curve, which is the SMOOTH end of the dimension."""
    c = _walk(seed, n, level)
    return _series(c.rolling(span).mean().bfill().to_numpy())


def _line(n=N, level=LEVEL, step=2.0):
    """An arithmetic ramp. Its Higuchi dimension is 1 in exact arithmetic --
    see §A4 for the derivation and for what it actually reads."""
    return _series(level + step * np.arange(n, dtype=float))


def _ramp(n=N, level=LEVEL, step=2.0):
    """A geometric ramp. Unlike `tf_dfa_100`'s, this one FIRES: the lagged
    differences of `level * 2**i` are not constant."""
    return _series(level * step ** np.arange(min(n, 60), dtype=float))


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _alternating(n=N, level=LEVEL, amp=1.0):
    """Period 2 exactly: every lag-2 and lag-4 difference is zero, so L(2)
    and L(4) are zero and the column cannot take a logarithm (§G)."""
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
#: Frames on which it reads nowhere, and §G says why for each.
EMPTY = ["flat", "alternating"]


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
    indexing: every sum by `math.fsum`, the slope through the normal
    equations. Shares no numpy operation with the module."""
    c = [float(x) for x in close.to_numpy(dtype=float)]
    n = len(c)
    out = [math.nan] * n
    xs = [math.log(1.0 / k) for k in range(1, kmax + 1)]
    xbar = math.fsum(xs) / len(xs)
    xden = math.fsum((x - xbar) ** 2 for x in xs)
    for i in range(length - 1, n):
        w = c[i - length + 1:i + 1]                   # w[0] is X(1)
        if not all(math.isfinite(x) for x in w):
            continue
        ys, bad = [], False
        for k in range(1, kmax + 1):
            lms = []
            for m in range(1, k + 1):                 # m = 1 .. k
                steps = (length - m) // k             # Higuchi's floor
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
    intercept column -- the shape the published Higuchi implementations use,
    and a third way of solving the least squares."""
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
        out[row] = float(np.linalg.lstsq(design, np.array(ys), rcond=None)[0][0])
    return _place(close, length, out)


# ----------------------------------------------------------------- mutants

CURVE_LINE = "    log_l = np.log(safe / safe[:, :1])"
CURVE_RAW = "    log_l = np.log(safe)"
FD_LINE = "    fd = (centred * LOG_INV_K_CENTRED).sum(axis=1) / LOG_INV_K_SS"
FD_MATMUL = "    fd = centred @ LOG_INV_K_CENTRED / LOG_INV_K_SS"
WIN_LINE = "        win = sliding_window_view(c, length)"
OUT_LINE = "            out[length - 1 + a:length - 1 + b] = _higuchi_fd(win[a:b])"
MASK_LINE = "    defined = np.isfinite(win).all(axis=1)"
FOLD_LINE = "    c = np.where(np.isfinite(c), c, np.nan)"

LOOKAHEAD_MUTANTS = {
    "close-lead": ("    c = close.to_numpy(dtype=float)",
                   "    c = close.shift(-1).to_numpy(dtype=float)"),
    "output-early": (OUT_LINE,
                     "            out[length - 2 + a:length - 2 + b] = "
                     "_higuchi_fd(win[a:b])"),
    "window-ahead": (WIN_LINE,
                     "        win = sliding_window_view(np.roll(c, -1), length)"),
    "window-centred": (WIN_LINE,
                       "        win = sliding_window_view("
                       "np.roll(c, -(length // 2)), length)"),
}
MASK_MUTANT = (MASK_LINE,
               "    defined = np.roll(np.isfinite(win).all(axis=1), -1)")


def _mutant_ns(*edits):
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


def _futures(close, j, spread=3.0):
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


#: The first offset is 60 and not `LENGTH + 5`, because `smooth` is built by
#: a 40-bar rolling mean and its first 40 bars are therefore CONSTANT: the
#: windows ending there have L(1) = 0 and read NaN, so a prefix cut at bar 35
#: holds no reading at all and no mutant can be caught in it (measured: 7 of
#: 8 before this bound, the missing one being offset 35).
OFFSETS = [int(round(x)) for x in np.linspace(60, N - 5, 8)]
#: The frames the future sweep runs on. `ramp` is out: it is 60 bars (a
#: `100 * 2**i` ramp reaches +inf at about bar 1020), so every offset but the
#: first falls past its end and `_futures` returns two identical frames.
SWEPT = [n for n in FIRING if n != "ramp"]


# ---------------------------------------------------------------- sections

def _head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def a1_prototype():
    _head("§A1 — the screen prototype")
    print(f"{'frame':<14}{'bars':>7}{'both':>8}{'differ':>8}"
          f"{'max |diff|':>14}{'mask equal':>12}")
    worst, total_diff, total_both = 0.0, 0, 0
    for name in NAMES:
        c = FRAMES[name]()
        mod, pro = tf_higuchi_30(c), _prototype(c)
        both = int((mod.notna() & pro.notna()).sum())
        d = _differs(mod, pro)
        gap = _abs(mod, pro)
        mask = bool((mod.isna() == pro.isna()).all())
        total_diff += d if both else 0
        total_both += both
        if both and math.isfinite(gap):
            worst = max(worst, gap)
        print(f"{name:<14}{len(c):>7}{both:>8}{d:>8}{gap:>14.3e}"
              f"{str(mask):>12}")
    print(f"\nworst |diff| over every frame: {worst:.6e}")
    print(f"bars both define: {total_both}; bars that differ: {total_diff}")

    print("\nthe two spellings put back (ratio -> raw log, sum -> @):")
    back = _mutant((CURVE_LINE, CURVE_RAW), (FD_LINE, FD_MATMUL))
    for name in NAMES:
        c = FRAMES[name]()
        print(f"  {name:<14} bit-equal to the prototype: "
              f"{_bit_equal(back(c), _prototype(c))}")

    print("\nat other lengths (walk / trend / heavy-tailed):")
    for length in (MIN_LENGTH, 20, LENGTH, 60, 250):
        gaps, masks = [], []
        for name in ("walk", "trend", "heavy-tailed"):
            c = FRAMES[name]()
            mod = tf_higuchi_30(c, length=length)
            pro = _prototype(c, length=length)
            gaps.append(_abs(mod, pro))
            masks.append(bool((mod.isna() == pro.isna()).all()))
        print(f"  length {length:>4}: max |diff| {max(gaps):.3e}, "
              f"masks equal {all(masks)}")


def a2_loops():
    _head("§A2 — Higuchi (1988) by scalar loops, 1-based, math.fsum")
    print(f"{'frame':<14}{'length':>7}{'both':>7}{'max |diff|':>14}"
          f"{'mask equal':>12}")
    worst = 0.0
    for name in ("walk", "trend", "heavy-tailed", "noise", "smooth", "line"):
        for length in (MIN_LENGTH, LENGTH):
            c = FRAMES[name](n=300) if name != "ramp" else FRAMES[name]()
            mod = tf_higuchi_30(c, length=length)
            orc = _loop_oracle(c, length=length)
            both = int((mod.notna() & orc.notna()).sum())
            gap = _abs(mod, orc)
            mask = bool((mod.isna() == orc.isna()).all())
            if both and math.isfinite(gap):
                worst = max(worst, gap)
            print(f"{name:<14}{length:>7}{both:>7}{gap:>14.3e}"
                  f"{str(mask):>12}")
    print(f"\nworst |diff|: {worst:.6e}")


def a3_lstsq():
    _head("§A3 — the same quantity through np.linalg.lstsq")
    print(f"{'frame':<14}{'both':>7}{'max |diff|':>14}{'mask equal':>12}")
    worst = 0.0
    for name in ("walk", "heavy-tailed", "noise", "smooth", "grid"):
        c = FRAMES[name](n=300)
        mod, orc = tf_higuchi_30(c), _lstsq_oracle(c)
        both = int((mod.notna() & orc.notna()).sum())
        gap = _abs(mod, orc)
        if both and math.isfinite(gap):
            worst = max(worst, gap)
        print(f"{name:<14}{both:>7}{gap:>14.3e}"
              f"{str(bool((mod.isna() == orc.isna()).all())):>12}")
    print(f"\nworst |diff|: {worst:.6e}")


def a4_anchors():
    _head("§A4 — the anchors: what a KNOWN curve must read")
    print("A straight line has Higuchi dimension 1 EXACTLY in real "
          "arithmetic:")
    print("  every lag-k difference of an arithmetic ramp is the same number,")
    print("  so L(k) = step * (length - 1) / k, log L(k) = const + log(1/k),")
    print("  and the slope on log(1/k) is 1.")
    line = tf_higuchi_30(_line())
    print(f"  measured on `line`: min {line.min():.17g} "
          f"max {line.max():.17g}")
    print(f"  bars reading EXACTLY 1.0: {int((line == 1.0).sum())} "
          f"of {int(line.notna().sum())}")
    print(f"  worst |reading - 1|: {float((line.dropna() - 1.0).abs().max()):.3e}")

    print("\nmedian reading per frame (1 = smooth, 2 = space-filling):")
    for name in FIRING:
        v = tf_higuchi_30(FRAMES[name]()).dropna()
        print(f"  {name:<14} median {float(v.median()):8.4f}  "
              f"min {float(v.min()):8.4f}  max {float(v.max()):8.4f}  "
              f"n {len(v):>5}")

    print("\nthe ordering the dimension exists for "
          "(smooth < walk < iid noise):")
    med = {n: float(tf_higuchi_30(FRAMES[n]()).median())
           for n in ("smooth", "walk", "noise")}
    print(f"  smooth {med['smooth']:.4f} < walk {med['walk']:.4f} "
          f"< noise {med['noise']:.4f}  "
          f"=> {med['smooth'] < med['walk'] < med['noise']}")

    print("\n⚠ the window is 30 bars and the ladder stops at k = 5, so the "
          "estimator is biased:")
    rng = np.random.default_rng(2024)
    for label, data in (
            ("brownian (true D = 1.5)",
             np.cumsum(rng.normal(0.0, 1.0, 30_000))),
            ("iid normal (true D = 2.0)", rng.normal(0.0, 1.0, 30_000)),
    ):
        rows = sliding_window_view(data, LENGTH)[::LENGTH]
        v = _higuchi_fd(rows)
        v = v[np.isfinite(v)]
        print(f"  {label:<28} mean {v.mean():.4f} over {v.size} disjoint "
              f"windows (sd {v.std():.4f})")
    print("  the same arithmetic on a 300-bar window with k = 1 .. 20:")
    wide = _mutant_ns(("KMAX = 5", "KMAX = 20"))["_higuchi_fd"]
    for label, data in (
            ("brownian (true D = 1.5)",
             np.cumsum(rng.normal(0.0, 1.0, 120_000))),
            ("iid normal (true D = 2.0)", rng.normal(0.0, 1.0, 120_000)),
    ):
        rows = sliding_window_view(data, 300)[::300]
        v = wide(rows)
        v = v[np.isfinite(v)]
        print(f"  {label:<28} mean {v.mean():.4f} over {v.size} disjoint "
              f"windows (sd {v.std():.4f})")


def a5_ladder():
    _head("§A5 — the spacing ladder, and the points each strand drops")
    print(f"length {LENGTH}, k = 1 .. {KMAX}")
    print(f"{'k':>3}{'m':>4}{'points':>8}{'intervals':>11}{'reaches':>9}"
          f"{'dropped':>9}")
    for k in K_VALUES:
        for m in range(k):
            idx = np.arange(m, LENGTH, k)
            print(f"{k:>3}{m:>4}{len(idx):>8}{len(idx) - 1:>11}"
                  f"{int(idx[-1]):>9}{LENGTH - 1 - int(idx[-1]):>9}")
    print("\nthe regressor:")
    print(f"  LOG_INV_K_CENTRED = {np.array2string(LOG_INV_K_CENTRED, precision=6)}")
    print(f"  sum = {float(LOG_INV_K_CENTRED.sum()):.3e}  "
          f"LOG_INV_K_SS = {LOG_INV_K_SS:.17g}")
    print("\na mutant whose KMAX is 10 must MOVE the column:")
    wider = _mutant(("KMAX = 5", "KMAX = 10"))
    c = _walk()
    print(f"  bars moved: {_differs(wider(c), tf_higuchi_30(c))}, "
          f"max |diff| {_abs(wider(c), tf_higuchi_30(c)):.4f}")


def a6_not_taken():
    _head("§A6 — the readings this port did NOT take")
    print("1. TSFEL's own source is not readable here: the package is not")
    print("   installed, `docs/pine/` does not carry it and web access is")
    print("   unavailable. Gate A checks the quantity the issue line NAMES")
    print("   (Higuchi 1988) against the screen prototype and two further")
    print("   spellings -- not TSFEL's code.")
    try:
        import tsfel  # noqa: F401
        print("   ⚠⚠ tsfel IMPORTED -- this claim is now stale, re-measure.")
    except ImportError as exc:
        print(f"   `import tsfel` -> ImportError: {exc}")
    print("2. kmax is 5 because the issue's scale-free form says `k = 1..5`.")
    print("   Published implementations default to 10; what that costs is")
    print("   measured in §A4 and §A5, not assumed.")
    print("3. No real price data is in this worktree, so every figure here")
    print("   is synthetic. Gate C's real limb and Gate E come from the")
    print("   launcher's run.")


def b_causality():
    _head("§B — causality")
    print(f"offsets swept: {OFFSETS}")
    print("\nthe shipped module, perturbing every bar from j onward:")
    for name in SWEPT:
        c = FRAMES[name]()
        caught = sum(_caught_at(tf_higuchi_30, c, j) for j in OFFSETS)
        print(f"  {name:<14} caught {caught} of {len(OFFSETS)}")
    print("\nprefix truncation:")
    for name in FIRING:
        c = FRAMES[name]()
        full = tf_higuchi_30(c)
        ok = all(_bit_equal(full.iloc[:j], tf_higuchi_30(c.iloc[:j]))
                 for j in OFFSETS)
        print(f"  {name:<14} prefix equal at every offset: {ok}")
    print("\nlook-ahead mutants (live? then caught at how many offsets):")
    for label, edit in LOOKAHEAD_MUTANTS.items():
        fn = _mutant(edit)
        for name in SWEPT:
            c = FRAMES[name]()
            live = not _bit_equal(fn(c), tf_higuchi_30(c))
            caught = sum(_caught_at(fn, c, j) for j in OFFSETS)
            print(f"  {label:<16}{name:<14} live {str(live):<6} "
                  f"caught {caught}/{len(OFFSETS)}")
    print("\n§B2 — the mutant the blind sweep cannot see "
          "(it back-dates the GAP MASK):")
    fn = _mutant(MASK_MUTANT)
    for name in SWEPT:
        c = FRAMES[name]()
        live = not _bit_equal(fn(c), tf_higuchi_30(c))
        caught = sum(_caught_at(fn, c, j) for j in OFFSETS)
        print(f"  mask-back-dated {name:<14} live {str(live):<6} "
              f"caught {caught}/{len(OFFSETS)}")
    print("  caught instead by planting one NaN close:")
    for at in (150, 700, 1200):
        c = _walk()
        c.iloc[at] = np.nan
        real = {int(i) for i in np.flatnonzero(tf_higuchi_30(c).isna()
                                               .to_numpy()) if i >= LENGTH}
        mut = {int(i) for i in np.flatnonzero(fn(c).isna().to_numpy())
               if i >= LENGTH}
        print(f"    NaN at {at}: real gap starts {min(real)}, "
              f"mutant gap starts {min(mut)}, "
              f"real shifted one earlier is inside the mutant "
              f"{ {b - 1 for b in real} <= mut }")
    print("\n§B3 — prefix truncation across a chunk boundary:")
    import importlib
    mod = importlib.import_module("pandas_ta.statistics.tf_higuchi_30")
    old = mod.CHUNK_VALUES
    try:
        for budget in (LENGTH, 7 * LENGTH):
            mod.CHUNK_VALUES = budget
            c = _walk()
            full = mod.tf_higuchi_30(c)
            same = _bit_equal(full, tf_higuchi_30(c))
            ok = all(_bit_equal(full.iloc[:j], mod.tf_higuchi_30(c.iloc[:j]))
                     for j in OFFSETS)
            print(f"  budget {budget:>4}: equals the default run {same}, "
                  f"prefix equal at every offset {ok}")
    finally:
        mod.CHUNK_VALUES = old


def c_reach():
    _head("§C — reachability (synthetic frames only)")
    print(f"{'frame':<14}{'bars':>7}{'fires':>7}{'empty':>7}"
          f"{'distinct':>10}{'min':>9}{'max':>9}")
    for name in NAMES:
        c = FRAMES[name]()
        v = tf_higuchi_30(c)
        d = v.dropna()
        lo = f"{float(d.min()):.4f}" if len(d) else "-"
        hi = f"{float(d.max()):.4f}" if len(d) else "-"
        print(f"{name:<14}{len(c):>7}{int(v.notna().sum()):>7}"
              f"{int(v.isna().sum()):>7}{int(d.nunique()):>10}{lo:>9}{hi:>9}")
    print(f"\nwarm-up: the first reading sits at bar {LENGTH - 1} "
          f"(a window of {LENGTH} closes).")
    v = tf_higuchi_30(_walk())
    print(f"  walk: bars 0..{LENGTH - 2} all NaN "
          f"{bool(v.iloc[:LENGTH - 1].isna().all())}, "
          f"bar {LENGTH - 1} reads {float(v.iloc[LENGTH - 1]):.6f}")
    print(f"  shortest input that produces a value: "
          f"{int(tf_higuchi_30(_walk(n=LENGTH)).notna().sum())} at n = "
          f"{LENGTH}; tf_higuchi_30(n={LENGTH - 1}) is "
          f"{tf_higuchi_30(_walk(n=LENGTH - 1))}")


def d_scale():
    _head("§D — scale-free")
    print("exact binary factors (must be BIT-identical):")
    for factor in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40, 2.0 ** 100):
        bad = [n for n in FIRING
               if not _bit_equal(tf_higuchi_30(FRAMES[n]()),
                                 tf_higuchi_30(FRAMES[n]() * factor))]
        print(f"  x{factor:<12.6g} frames not bit-equal: {bad or 'none'}")
    print("\nx8 at every length:")
    for length in (MIN_LENGTH, 20, LENGTH, 60, 250):
        # `ramp` is 60 bars, so it drops out of the two longest lengths.
        usable = [n for n in FIRING if len(FRAMES[n]()) >= length]
        bad = [n for n in usable
               if not _bit_equal(tf_higuchi_30(FRAMES[n](), length=length),
                                 tf_higuchi_30(FRAMES[n]() * 8.0,
                                               length=length))]
        print(f"  length {length:>4}: {len(usable)} frames, not bit-equal: "
              f"{bad or 'none'}")
    print("\ninexact factors (a tolerance, and the NaN masks must match):")
    worst = 0.0
    for factor in (10.0, 3.7, 0.1, 1.0000001):
        gaps, masks = [], []
        for name in FIRING:
            c = FRAMES[name]()
            base, scaled = tf_higuchi_30(c), tf_higuchi_30(c * factor)
            gaps.append(_abs(base, scaled))
            masks.append(bool((base.isna() == scaled.isna()).all()))
        worst = max(worst, max(gaps))
        print(f"  x{factor:<12.6g} max |diff| {max(gaps):.3e}, "
              f"masks equal {all(masks)}")
    print(f"\nworst inexact-rescale |diff|: {worst:.6e}")
    print("\na level SHIFT is invariant in exact arithmetic "
          "(differences do not see it):")
    for shift in (1.0, 50.0, 1e6):
        c = _walk()
        a, b = tf_higuchi_30(c), tf_higuchi_30(c + shift)
        print(f"  +{shift:<10g} bars moved {_differs(a, b):>5}, "
              f"max |diff| {_abs(a, b):.3e}")
    print("\n`0 < fires < n`, and the column is not constant:")
    for name in FIRING:
        v = tf_higuchi_30(FRAMES[name]())
        print(f"  {name:<14} 0 < {int(v.notna().sum())} < {len(v)} "
              f"{0 < int(v.notna().sum()) < len(v)}, distinct "
              f"{int(v.dropna().nunique())}")


def g_guards():
    _head("§G — guards")
    print("a window whose L(k) is exactly zero at any k is a gap:")
    for name in EMPTY:
        c = FRAMES[name]()
        v = tf_higuchi_30(c)
        W = _windows(c)[:1]
        curve = []
        for k in K_VALUES:
            gap = np.abs(W[:, k:] - W[:, :-k])
            strands = [gap[:, m::k].sum(axis=1) * (LENGTH - 1)
                       / (gap[:, m::k].shape[1] * k) / k for m in range(k)]
            curve.append(float(np.mean(strands, axis=0)[0]))
        print(f"  {name:<14} fires {int(v.notna().sum())}; "
              f"L(k) = {['%.6g' % x for x in curve]}")
    print("\nand a window of period exactly 4, which is NOT the same case:")
    p4 = _series(LEVEL + np.array([0.0, 1.0, 3.0, 2.0])[np.arange(300) % 4])
    v4 = tf_higuchi_30(p4)
    W4 = _windows(p4)[:1]
    curve4 = []
    for k in K_VALUES:
        gap = np.abs(W4[:, k:] - W4[:, :-k])
        strands = [gap[:, m::k].sum(axis=1) * (LENGTH - 1)
                   / (gap[:, m::k].shape[1] * k) / k for m in range(k)]
        curve4.append(float(np.mean(strands, axis=0)[0]))
    print(f"  period-4      fires {int(v4.notna().sum())} of {len(v4)}; "
          f"L(k) = {['%.6g' % x for x in curve4]}")
    print(f"  zero at k = "
          f"{[k for k, x in zip(K_VALUES, curve4) if x == 0.0]} -- L(2) is "
          f"NOT zero here, unlike the period-2 frame")

    print("\nprototype agreement on those frames:")
    for name in EMPTY:
        c = FRAMES[name]()
        print(f"  {name:<14} module fires "
              f"{int(tf_higuchi_30(c).notna().sum())}, prototype fires "
              f"{int(_prototype(c).notna().sum())}")
    print(f"  {'period-4':<14} module fires {int(v4.notna().sum())}, "
          f"prototype fires {int(_prototype(p4).notna().sum())}")
    print("\none bad close empties a bounded run and moves nothing earlier:")
    base = _walk()
    for value in (np.nan, np.inf, -np.inf, 0.0, 1e-310):
        for at in (150, 700):
            c = base.copy()
            c.iloc[at] = value
            a, b = tf_higuchi_30(base), tf_higuchi_30(c)
            av, bv = a.to_numpy(), b.to_numpy()
            newly = int((a.notna() & b.isna()).sum())
            moved = (np.isnan(av) != np.isnan(bv)) | (
                ~np.isnan(av) & ~np.isnan(bv) & (av != bv))
            print(f"  {str(value):<10} at {at}: newly empty {newly:>3} "
                  f"(<= {LENGTH}), bars moved before {at}: "
                  f"{int(moved[:at].sum())}")
    print("\nunder np.errstate(all='raise'):")
    for name in NAMES:
        c = FRAMES[name]()
        try:
            with np.errstate(all="raise"):
                tf_higuchi_30(c)
            print(f"  {name:<14} quiet")
        except FloatingPointError as exc:
            print(f"  {name:<14} RAISED {exc}")
    print("  with the +-inf fold deleted:")
    unfolded = _mutant((FOLD_LINE, "    c = c"))
    for label, where in (("one inf close", (700,)),
                         ("two inf closes 5 bars apart", (700, 705))):
        c = _walk()
        for at in where:
            c.iloc[at] = np.inf
        try:
            with np.errstate(all="raise"):
                unfolded(c)
            print(f"    {label:<28} quiet")
        except FloatingPointError as exc:
            print(f"    {label:<28} RAISED {exc}")
        with np.errstate(all="raise"):
            shipped_quiet = tf_higuchi_30(c)
        with np.errstate(all="ignore"):
            print(f"      shipped: quiet, and the fold changes no value: "
                  f"{_bit_equal(unfolded(c), shipped_quiet)}")
    print("\na finite close so large that L(k) OVERFLOWS is a gap, not a "
          "value:")
    huge = _series(1e307 * np.cos(np.arange(300, dtype=float)))
    W = _windows(huge)[:1]
    gap = np.abs(W[:, 1:] - W[:, :-1])
    with np.errstate(all="ignore"):
        v = tf_higuchi_30(huge)
        first_l1 = float(gap.sum(axis=1)[0])
    print(f"  closes +-1e307, every close finite "
          f"{bool(np.isfinite(huge.to_numpy()).all())}; L(1) of the first "
          f"window = {first_l1:.6g}")
    print(f"  fires {int(v.notna().sum())} of {len(v)} -- `inf / inf` is NaN "
          f"and NaN propagates to the slope, so the overflow is a gap")
    withfinite = _mutant((
        "    positive = curve > 0.0",
        "    positive = np.isfinite(curve) & (curve > 0.0)"))
    with np.errstate(all="ignore"):
        print(f"  an explicit `np.isfinite(curve)` limb would add nothing: "
              f"it fires {int(withfinite(huge).notna().sum())} on the same "
              f"frame, so the limb is not in the shipped module")
    print("  ⚠ under np.errstate(all='raise') this frame RAISES, at the "
          "sum and before any guard can act:")
    try:
        with np.errstate(all="raise"):
            tf_higuchi_30(huge)
        print("    quiet")
    except FloatingPointError as exc:
        print(f"    {type(exc).__name__}: {exc}")
    print("    so 'no floating point error is reachable' is a claim about "
          "ordinary price magnitudes, not about every float64 input.")

    print("\ndegenerate frames:")
    for label, data in (("all-nan", np.full(300, np.nan)),
                        ("all-zero", np.zeros(300)),
                        ("all-negative", -np.abs(_walk(n=300).to_numpy())),
                        ("all-inf", np.full(300, np.inf))):
        with np.errstate(all="raise"):
            v = tf_higuchi_30(_series(data))
        print(f"  {label:<14} fires {int(v.notna().sum())}")
    print("\na negative close is a price, not a gap:")
    c = _walk()
    c.iloc[700] = -1.0
    print(f"  fires {int(tf_higuchi_30(c).notna().sum())} vs "
          f"{int(tf_higuchi_30(_walk()).notna().sum())} on the clean frame, "
          f"bars moved {_differs(tf_higuchi_30(c), tf_higuchi_30(_walk()))}")
    print("\nthe input series is not mutated:")
    c = _walk()
    before = c.to_numpy().copy()
    tf_higuchi_30(c)
    print(f"  unchanged: {bool((c.to_numpy() == before).all())}")
    print("\nlength below the minimum falls back to the default:")
    for length in (None, 0, 1, MIN_LENGTH - 1, MIN_LENGTH, 250):
        print(f"  length={str(length):<6} -> "
              f"{tf_higuchi_30(_walk(), length=length).name}")


def l_reads():
    _head("§L — what the column reads, and what it discards")
    print("blind to a positive rescale of the whole window, and to a shift:")
    rng = np.random.default_rng(404)
    W = _windows(_walk(n=1200))
    rows = W[rng.integers(0, W.shape[0], 500)]
    base = _higuchi_fd(rows)
    print(f"  base finite on {int(np.isfinite(base).sum())} of {len(rows)}")
    for factor in (-1.0, 0.5, 2.0, 2.0 ** 60, 3.7, -0.1):
        d = float(np.abs(_higuchi_fd(rows * factor) - base).max())
        bits = bool((_higuchi_fd(rows * factor) == base).all())
        print(f"  x{factor:<10g} max |diff| {d:.3e}  bit-equal {bits}")
    for add in (1.0, 100.0, -50.0):
        d = float(np.abs(_higuchi_fd(rows + add) - base).max())
        print(f"  +{add:<10g} max |diff| {d:.3e}")
    print("\nNOT blind to the order of the closes inside the window:")
    permuted = _higuchi_fd(np.array([rng.permutation(w) for w in rows]))
    reversed_ = _higuchi_fd(rows[:, ::-1])
    rolled = _higuchi_fd(np.array(
        [np.roll(w, int(k)) for w, k in zip(rows, rng.integers(1, LENGTH,
                                                               len(rows)))]))
    for label, other in (("permutation", permuted), ("time reversal",
                                                     reversed_),
                         ("rotation", rolled)):
        print(f"  {label:<16} max |diff| "
              f"{float(np.abs(other - base).max()):.4e}, "
              f"median |diff| "
              f"{float(np.median(np.abs(other - base))):.4e}, "
              f"windows moved by a bit "
              f"{int((other != base).sum())} of {len(rows)}")
    print("\nthe row helper IS the shipped column:")
    for name in FIRING:
        c = FRAMES[name]()
        print(f"  {name:<14} "
              f"{_bit_equal(_place(c, LENGTH, _higuchi_fd(_windows(c))), tf_higuchi_30(c))}")


def l4_fork():
    _head("§L4 — overlap with the fork's own columns (synthetic, pooled)")
    print("⚠ This is NOT Gate E. Gate E is the engine's 687 comparators over")
    print("   89 real BIST frames and the launcher runs it. This section")
    print("   measures the fork columns that are nearest in MEANING, because")
    print("   three of them landed AFTER the 2026-10-24 screen whose stage-2")
    print("   fork overlap the issue quotes (max 0.6496 vs vhf:VHF_28).")
    import pandas_ta as ta
    from pandas import concat
    frames = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump",
              "noise", "smooth"]

    def _candidates(c):
        return {
            "VHF_28": ta.vhf(c),
            "VHF_30": ta.vhf(c, length=30),
            "LEAN_HURST_100": ta.lean_hurst_100(c),
            "LEAN_HURST_30": ta.lean_hurst_100(c, length=30),
            "TFDFA_100": ta.tf_dfa_100(c),
            "TFDFA_30": ta.tf_dfa_100(c, length=30),
            "TFSPECENTROPY_64": ta.tf_spec_entropy_64(c),
            "TS_CID_CE_20": ta.ts_cid_ce_20(c),
            "ENTROPY_10": ta.entropy(c),
            "(TFHIGUCHI_100)": tf_higuchi_30(c, length=100),
        }

    mine, others = [], {}
    for name in frames:
        c = FRAMES[name]()
        mine.append(tf_higuchi_30(c))
        for key, series in _candidates(c).items():
            others.setdefault(key, []).append(
                series if isinstance(series, Series) else series.iloc[:, 0])
    pooled = concat(mine, ignore_index=True)
    print(f"\n{len(frames)} frames, pooled bars {len(pooled)}, "
          f"TFHIGUCHI_30 fires {int(pooled.notna().sum())}")
    print("(TFHIGUCHI_100) is this same column at another length -- context, "
          "not a shipped comparator.")
    print(f"{'comparator':<20}{'pooled rho':>12}{'per-frame median |rho|':>24}")
    rows = []
    for key, parts in others.items():
        other = concat(parts, ignore_index=True)
        rho = _spearman(pooled, other)
        per = [abs(_spearman(a, b)) for a, b in zip(mine, parts)]
        per = [p for p in per if math.isfinite(p)]
        rows.append((abs(rho), key, rho, float(np.median(per)) if per else
                     float("nan")))
    for _, key, rho, med in sorted(rows, reverse=True):
        print(f"{key:<20}{rho:>12.4f}{med:>24.4f}")

    print("\nthe leader, frame by frame "
          "(the pooled figure mixes eight different processes):")
    print(f"{'frame':<14}{'rho vs VHF_28':>15}{'rho vs VHF_30':>15}")
    for name, a in zip(frames, mine):
        print(f"{name:<14}"
              f"{_spearman(a, others['VHF_28'][frames.index(name)]):>15.4f}"
              f"{_spearman(a, others['VHF_30'][frames.index(name)]):>15.4f}")

    print("\nwhy: VHF is `(max - min) / sum|close diff|` over its window, and")
    print("`sum|close diff|` over the window IS this column's L(1). Both are")
    print("path-efficiency measures of the same 28-30 bars, so the sign is")
    print("negative: a rougher path (high dimension) travels further per unit")
    print("of range (low VHF).")


def w_cut():
    _head("§W — the dictionary cut")
    import re
    gen = (ROOT / "docs" / "gen_indicator_dictionary.py").read_text(
        encoding="utf-8")
    limit = int(re.search(r"def desc\(rec, limit=(\d+)\)", gen).group(1))
    first = tf_higuchi_30.__doc__.split("\n\n")[1].strip()
    squeezed = re.sub(r"\s+", " ", first).strip()
    cut = squeezed
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0] + "…"
    print(f"generator limit: {limit}")
    print(f"paragraph length: {len(squeezed)}  slack: {limit - len(squeezed)}")
    print(f"truncated: {cut != squeezed}")
    print(f"what the dictionary row shows:\n  {cut}")


def z_cost():
    _head("§Z — cost, and the chunk budget")
    import importlib
    mod = importlib.import_module("pandas_ta.statistics.tf_higuchi_30")
    c = _walk(n=400_000)
    for budget, label in ((mod.CHUNK_VALUES, "shipped"), (1 << 40, "unbounded")):
        old = mod.CHUNK_VALUES
        try:
            mod.CHUNK_VALUES = budget
            tracemalloc.start()
            t0 = perf_counter()
            v = mod.tf_higuchi_30(c)
            dt = perf_counter() - t0
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"  {label:<10} budget {budget:>14}  "
                  f"{dt:6.2f}s  peak {peak / 1e6:8.1f} MB  "
                  f"fires {int(v.notna().sum())}")
        finally:
            mod.CHUNK_VALUES = old
    print("\nthe budget cannot change a value:")
    c = _walk()
    base = tf_higuchi_30(c)
    old = mod.CHUNK_VALUES
    try:
        for budget in (1, 64, 999, 10 ** 9):
            mod.CHUNK_VALUES = budget
            print(f"  budget {budget:>12}: bit-equal {_bit_equal(base, mod.tf_higuchi_30(c))}")
    finally:
        mod.CHUNK_VALUES = old


def z2_shape():
    _head("§Z2 — which step is sensitive to the block shape")
    win = _windows(_walk())
    whole = _higuchi_fd(win)
    bad = []
    for row in range(LENGTH, LENGTH + 200):
        one = _higuchi_fd(win[row:row + 1])
        if not np.array_equal(whole[row:row + 1], one, equal_nan=True):
            bad.append(row)
    print(f"  shipped spelling: rows whose single-row value differs from the "
          f"whole-block value: {len(bad)}")
    print("\n  the same with the prototype's `@` put back:")
    matmul = _mutant_ns((FD_LINE, FD_MATMUL))["_higuchi_fd"]
    whole_m = matmul(win)
    for chunk in (1, 2, 3, 5, 7, 8, 16):
        moved = 0
        for a in range(LENGTH, LENGTH + 200, chunk):
            block = matmul(win[a:a + chunk])
            if not np.array_equal(whole_m[a:a + chunk], block, equal_nan=True):
                moved += 1
        print(f"    chunk {chunk:>3}: blocks whose value differs from the "
              f"whole-block value: {moved}")


SECTIONS = {
    "A1": a1_prototype, "A2": a2_loops, "A3": a3_lstsq, "A4": a4_anchors,
    "A5": a5_ladder, "A6": a6_not_taken, "B": b_causality, "C": c_reach,
    "D": d_scale, "G": g_guards, "L": l_reads, "L4": l4_fork, "W": w_cut,
    "Z": z_cost, "Z2": z2_shape,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
    for key in want:
        SECTIONS[key]()
