# -*- coding: utf-8 -*-
"""Every number in `docs/TfDfa100Measured.md` and in the docstrings of
`pandas_ta/statistics/tf_dfa_100.py` and `tests/test_tf_dfa_100.py` is printed
by this script.

    python docs/measure_tf_dfa_100.py            # every section
    python docs/measure_tf_dfa_100.py A1 D L     # named sections

Sections: A1 the screen prototype, A2 the scalar-loop oracle, A3 the
`polyfit` oracle, A4 the readings this port did NOT take, A5 the anchors
(what a known process must read), A5B where the ladder's bias comes from,
A6 the return spelling, A7 the tail each box drops, A8 the centring,
B causality, C reachability, D scale, G guards, L what the column reads,
W the dictionary cut, Z cost, Z2 which step is sensitive to the block shape.

⚠ Several sections print last-bit figures that MOVE between CPU dispatches.
Run each of A1, A2, A3, A8, D and L under `docs/measure_tf_dfa_100_cpu.py`
as well before quoting a bound from them: §F2 of `docs/TfDfa100Measured.md`
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

from pandas_ta.statistics.tf_dfa_100 import (  # noqa: E402
    BOXES, LOG_BOX_CENTRED, LOG_BOX_SS, MIN_LENGTH, tf_dfa_100,
)

N = 1500
LEVEL = 100.0
LENGTH = 100
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_dfa_100.py"


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


def _from_returns(r, level=LEVEL):
    """A close path whose `pct_change` IS `r`, so a claim about the RETURN
    process is not confounded by `exp(r) - 1`."""
    return _series(level * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _persistent(seed=29, n=N, level=LEVEL, phi=0.6, sigma=0.01):
    """AR(1) returns with phi > 0: trending, so DFA must read ABOVE 0.5."""
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + rng.normal(0.0, sigma)
    return _from_returns(r, level)


def _mean_reverting(seed=31, n=N, level=LEVEL, phi=-0.6, sigma=0.01):
    """AR(1) returns with phi < 0: anti-persistent, so DFA must read BELOW
    0.5."""
    return _persistent(seed, n, level, phi, sigma)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _ramp(n=200, level=LEVEL, step=2.0):
    """A geometric ramp whose returns are all EXACTLY 1.0: the only non-flat
    way to reach a window with no fluctuation at all. `step` has to be a power
    of two, or consecutive ratios differ in their last bits."""
    return _series(level * step ** np.arange(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump,
    "persistent": _persistent, "mean-reverting": _mean_reverting,
    "flat": _flat, "ramp": _ramp,
}
#: The frames whose returns are not all equal, i.e. the ones that fluctuate.
FIRING = [k for k in FRAMES if k not in ("flat", "ramp")]


# ----------------------------------------------------------------- helpers

def _module():
    """The tf_dfa_100 MODULE, not the function.

    `pandas_ta/statistics/__init__.py` binds the name `tf_dfa_100` on the
    package to the function, so `import pandas_ta.statistics.tf_dfa_100 as m`
    can hand back the function instead (Python resolves `as` by attribute
    first). `import_module` reads `sys.modules` and cannot."""
    import importlib
    return importlib.import_module("pandas_ta.statistics.tf_dfa_100")


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


def _absdiff(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    return float((a[m] - b[m]).abs().max())


def _both(a, b):
    return int((a.notna() & b.notna()).sum())


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


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
    """The formula by explicit scalar loops: the profile by a running sum, the
    box detrend by the NORMAL EQUATIONS on `t = 0 .. s-1` (not the module's
    centred regressor), the fits by `math.fsum`. Shares no numpy operation
    with the module."""
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
            k = length // s
            sx = math.fsum(float(t) for t in range(s))
            sxx = math.fsum(float(t) * t for t in range(s))
            total, count = 0.0, 0
            for box in range(k):
                seg = profile[box * s:(box + 1) * s]
                sy = math.fsum(seg)
                sxy = math.fsum(float(t) * v for t, v in enumerate(seg))
                den = s * sxx - sx * sx
                slope = (s * sxy - sx * sy) / den
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
        num = math.fsum((x - lbar) * (y - fbar)
                        for x, y in zip(log_box, log_f))
        out[i] = num / lden
    return Series(out, index=close.index, dtype=float)


def _polyfit_oracle(close, length=LENGTH, boxes=BOXES):
    """The same quantity through `np.polyfit`, both for the box detrend and
    for the final log-log slope -- a third spelling, and one that solves the
    least squares by `lstsq` rather than by a closed form."""
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
            k = length // s
            resid = []
            t = np.arange(s, dtype=float)
            for box in range(k):
                seg = profile[box * s:(box + 1) * s]
                fit = np.polyfit(t, seg, 1)
                resid.append(seg - np.polyval(fit, t))
            ms = float(np.mean(np.concatenate(resid) ** 2))
            if ms <= 0.0:
                bad = True
                break
            log_f.append(0.5 * math.log(ms))
        if bad:
            continue
        out[row] = float(np.polyfit(log_box, np.array(log_f), 1)[0])
    return _place(close, length, out)


def _alpha_of_rows(win):
    """The module's arithmetic on an explicit (rows, length) block of RETURNS,
    so a claim about the window is not confounded by rebuilding a close path.

    Pinned to the module by
    `tests/test_tf_dfa_100.py::test_the_row_helper_is_the_modules_arithmetic`
    and by §L3 below, which re-checks it before it is used."""
    from pandas_ta.statistics.tf_dfa_100 import _dfa_alpha
    return _dfa_alpha(win)


# ----------------------------------------------------------------- mutants

RET_LINE = "    r = close.pct_change(fill_method=None).to_numpy(dtype=float)"
OUT_LINE = "            out[length - 1 + a:length - 1 + b] = _dfa_alpha(win[a:b])"
WIN_LINE = "        win = sliding_window_view(r, length)"
MASK_LINE = "    defined = np.isfinite(win).all(axis=1)"

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
    "window-centred": (WIN_LINE,
                       "        win = sliding_window_view("
                       "np.roll(r, -(length // 2)), length)"),
}
MASK_MUTANT = (MASK_LINE,
               "    defined = np.roll(np.isfinite(win).all(axis=1), -1)")

#: Not a look-ahead mutant: the spelling of the final dot product. `@` is the
#: prototype's, and it is not stable under the block's SHAPE (§Z2), so with it
#: a bar's value depends on which chunk it landed in (§Z).
ALPHA_LINE = "    alpha = (centred * LOG_BOX_CENTRED).sum(axis=1) / LOG_BOX_SS"
ALPHA_MATMUL = "    alpha = centred @ LOG_BOX_CENTRED / LOG_BOX_SS"


def _mutant_ns(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns


def _mutant(old, new):
    return _mutant_ns(old, new)["tf_dfa_100"]


def _mutant_alpha(ladder):
    """`_dfa_alpha` out of a mutant whose `BOXES` is `ladder` -- the SHIPPED
    arithmetic on another ladder, rather than a re-implementation of it."""
    return _mutant_ns("BOXES = (4, 5, 6, 8, 10)",
                      f"BOXES = {tuple(ladder)!r}")["_dfa_alpha"]


def _futures(close, j, spread=3.0):
    """Two closes that agree BIT FOR BIT below bar `j` and differ wholly from
    `j` on. Bars below `j` are multiplied by exactly 1.0."""
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


# ----------------------------------------------------------------- sections

def section_A1():
    print("\n== A1  the screen prototype, bit for bit ==")
    print("ind_screen_r2.py candidate `tf_dfa_100`, retyped in _prototype().")
    print(f"{'frame':15s} {'bars both':>9s} {'differ':>7s} "
          f"{'max |diff|':>12s} {'only module':>11s} {'only proto':>10s}")
    total_both = total_diff = 0
    for name in FRAMES:
        c = FRAMES[name]()
        mod, pro = tf_dfa_100(c), _prototype(c)
        both = _both(mod, pro)
        diff = int((mod.notna() & pro.notna()
                    & (mod != pro)).sum())
        total_both += both
        total_diff += diff
        print(f"{name:15s} {both:9d} {diff:7d} {_absdiff(mod, pro):12.3e} "
              f"{int((mod.notna() & pro.isna()).sum()):11d} "
              f"{int((pro.notna() & mod.isna()).sum()):10d}")
    print(f"TOTAL bars both define: {total_both}, differing: {total_diff}")

    print("\n-- the ONE difference, isolated: the dot-product spelling --")
    print("The shipped line sums the five terms; the prototype uses `@`.")
    print("A mutant of the shipped source with `@` put back must be BIT-equal")
    print("to the prototype, which leaves nothing else between them.")
    matmul = _mutant(ALPHA_LINE, ALPHA_MATMUL)
    for name in FRAMES:
        c = FRAMES[name]()
        pro = _prototype(c)
        print(f"{name:15s} `@` mutant == prototype, bit for bit: "
              f"{_bit_equal(matmul(c), pro)}")

    print("\n-- the same, at other lengths (walk / trend / heavy-tailed) --")
    print(f"{'length':>6s} {'bars both':>9s} {'differ':>7s} "
          f"{'max |diff|':>12s} {'mask differs':>12s} {'`@` == proto':>12s}")
    for length in (MIN_LENGTH, 32, 64, LENGTH, 250):
        both = diff = mask = 0
        worst, exact = 0.0, True
        for name in ("walk", "trend", "heavy-tailed"):
            c = FRAMES[name]()
            mod = tf_dfa_100(c, length=length)
            pro = _prototype(c, length=length)
            both += _both(mod, pro)
            diff += int((mod.notna() & pro.notna() & (mod != pro)).sum())
            mask += int((mod.isna() != pro.isna()).sum())
            worst = max(worst, _absdiff(mod, pro))
            exact &= _bit_equal(matmul(c, length=length), pro)
        print(f"{length:6d} {both:9d} {diff:7d} {worst:12.3e} {mask:12d} "
              f"{str(exact):>12s}")

    print("\n-- the ramp: a step that is not a power of two is not flat --")
    print(f"{'step':>14s} {'fires':>7s} {'of':>7s}")
    for step in (2.0, 1.5, 1.001, 1.0000000001):
        c = _series(LEVEL * step ** np.arange(200))
        v = tf_dfa_100(c)
        print(f"{step:14.10f} {int(v.notna().sum()):7d} "
              f"{len(v) - LENGTH:7d}")


def section_A2():
    print("\n== A2  the formula by scalar loops (200-bar frames) ==")
    print("Profile by a running sum, each box detrended by the NORMAL")
    print("EQUATIONS on t = 0..s-1, every sum by math.fsum. O(rows*length),")
    print("so 200 bars and the short lengths, not 1,500.")
    print(f"{'frame':15s} {'length':>6s} {'bars both':>9s} {'max rel':>12s} "
          f"{'max abs':>12s}")
    worst = 0.0
    for name in ("walk", "trend", "heavy-tailed", "persistent",
                 "mean-reverting"):
        for length in (20, 32, 100):
            c = FRAMES[name](n=200)
            mod = tf_dfa_100(c, length=length)
            orc = _loop_oracle(c, length=length)
            rel = _rel(mod, orc)
            worst = max(worst, rel)
            print(f"{name:15s} {length:6d} {_both(mod, orc):9d} "
                  f"{rel:12.3e} {_absdiff(mod, orc):12.3e}")
    print(f"worst relative difference: {worst:.3e}")
    print("A different summation order, not a different quantity.")


def section_A3():
    print("\n== A3  the same quantity through np.polyfit (200-bar frames) ==")
    print(f"{'frame':15s} {'bars both':>9s} {'max rel':>12s} {'max abs':>12s}")
    worst = 0.0
    for name in ("walk", "trend", "heavy-tailed", "persistent",
                 "mean-reverting"):
        c = FRAMES[name](n=200)
        mod = tf_dfa_100(c)
        orc = _polyfit_oracle(c)
        rel = _rel(mod, orc)
        worst = max(worst, rel)
        print(f"{name:15s} {_both(mod, orc):9d} {rel:12.3e} "
              f"{_absdiff(mod, orc):12.3e}")
    print(f"worst relative difference: {worst:.3e}")


def section_A4():
    print("\n== A4  the readings this port did NOT take ==")
    print("(a) every integer box 4..10 instead of the prototype's ladder")
    print("(b) the standard forward+backward pass, which uses the tail the")
    print("    forward-only pass drops")
    print(f"{'frame':15s} {'(a) max |d|':>12s} {'(a) rho':>9s} "
          f"{'(b) max |d|':>12s} {'(b) rho':>9s}")
    for name in FIRING:
        c = FRAMES[name]()
        base = tf_dfa_100(c)
        every = _prototype(c, boxes=(4, 5, 6, 7, 8, 9, 10))
        both_ways = _forward_backward(c)
        print(f"{name:15s} {_absdiff(base, every):12.4f} "
              f"{_spearman(base, every):9.4f} "
              f"{_absdiff(base, both_ways):12.4f} "
              f"{_spearman(base, both_ways):9.4f}")
    print("Both are DIFFERENT columns, not a check on this one.")


def _forward_backward(close, length=LENGTH, boxes=BOXES):
    """Standard DFA: boxes from the start AND from the end, so the tail that
    `length // s * s` drops is covered. Not what the prototype does."""
    W = _windows(close, length)
    with np.errstate(invalid="ignore", divide="ignore"):
        Y = np.cumsum(W - W.mean(1, keepdims=True), 1)
        log_f = []
        for s in boxes:
            k = length // s
            parts = []
            for Z in (Y[:, :k * s].reshape(len(W), k, s),
                      Y[:, length - k * s:].reshape(len(W), k, s)):
                t = np.arange(s) - (s - 1) / 2
                b = (Z * t).sum(2, keepdims=True) / (t ** 2).sum()
                parts.append((Z - Z.mean(2, keepdims=True) - b * t) ** 2)
            m = np.concatenate(parts, axis=1).mean((1, 2))
            log_f.append(0.5 * np.log(np.where(m == 0, np.nan, m)))
        L = np.log(np.array(boxes, dtype=float))
        Lc = L - L.mean()
        T = np.column_stack(log_f)
        v = (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    return _place(close, length, v)


def section_A5():
    print("\n== A5  the anchors: what a KNOWN process must read ==")
    print("DFA-1 of the profile of iid returns has a theoretical exponent of")
    print("0.5; positive autocorrelation pushes it up, negative down. These")
    print("are the only external checks available without the source code.")
    rng = np.random.default_rng(1234)
    print(f"{'process':24s} {'windows':>8s} {'mean':>8s} {'sd':>8s} "
          f"{'p05':>8s} {'p95':>8s}")
    cases = {
        "iid normal": rng.normal(0.0, 0.01, 40_000),
        "iid student-t(3)": rng.standard_t(3.0, 40_000) * 0.005,
    }
    ar = np.zeros(40_000)
    noise = rng.normal(0.0, 0.01, 40_000)
    for i in range(1, ar.size):
        ar[i] = 0.6 * ar[i - 1] + noise[i]
    cases["AR(1) phi=+0.6"] = ar
    ar2 = np.zeros(40_000)
    noise2 = rng.normal(0.0, 0.01, 40_000)
    for i in range(1, ar2.size):
        ar2[i] = -0.6 * ar2[i - 1] + noise2[i]
    cases["AR(1) phi=-0.6"] = ar2
    cases["alternating +-1 + noise"] = (
        0.01 * (-1.0) ** np.arange(40_000) + rng.normal(0.0, 0.001, 40_000))
    rw = np.cumsum(rng.normal(0.0, 0.01, 40_000))     # integrated: alpha ~ 1.5
    cases["integrated (cumsum)"] = rw
    for label, r in cases.items():
        rows = sliding_window_view(r, LENGTH)[::LENGTH]   # disjoint windows
        v = _alpha_of_rows(rows)
        v = v[np.isfinite(v)]
        print(f"{label:24s} {v.size:8d} {v.mean():8.4f} {v.std():8.4f} "
              f"{np.quantile(v, 0.05):8.4f} {np.quantile(v, 0.95):8.4f}")
    print("⚠ The sd is the estimator's own noise at 100 points and 5 boxes:")
    print("   a single reading is NOT a confident 0.5-or-not verdict.")
    print("⚠ And the iid CENTRE is not 0.5. §A5b is where that comes from.")


def section_A5b():
    print("\n== A5b  why iid reads above 0.5: the box ladder, not the code ==")
    print("Each box is detrended on its own, and a linear detrend removes")
    print("both the box's starting offset and any constant drift -- so for")
    print("iid returns the boxes are independent draws and E[F(s)^2] can be")
    print("measured directly, with no window and no port in the way.")
    rng = np.random.default_rng(99)
    draws = 200_000

    def implied_alpha(ladder):
        log_box = np.log(np.array(ladder, dtype=float))
        log_f = []
        for s in ladder:
            noise = rng.normal(0.0, 1.0, (draws, s))
            block = np.cumsum(noise, axis=1)
            t = np.arange(s) - (s - 1) / 2
            slope = (block * t).sum(axis=1, keepdims=True) / (t ** 2).sum()
            resid = block - block.mean(axis=1, keepdims=True) - slope * t
            log_f.append(0.5 * math.log(float((resid ** 2).mean())))
        centred = log_box - log_box.mean()
        arr = np.array(log_f)
        return float((arr - arr.mean()) @ centred / (centred ** 2).sum()), arr

    for ladder in (BOXES, (10, 16, 25, 40, 64), (50, 80, 125, 200, 320)):
        alpha, log_f = implied_alpha(ladder)
        print(f"ladder {str(ladder):22s} implied alpha of iid noise: "
              f"{alpha:.4f}")
        print("    E[F(s)]: " + " ".join(f"s={s}:{math.exp(v):.3f}"
                                         for s, v in zip(ladder, log_f)))
    print(f"\n{draws} independent boxes per size. The ladder this port ships")
    print("(4..10) sits where DFA-1's finite-box bias is largest; the same")
    print("arithmetic on larger boxes converges on the textbook 0.5.")

    print("\n-- the same, through the SHIPPED arithmetic on another ladder --")
    print("`_dfa_alpha` out of a mutant whose BOXES is the wider ladder, so")
    print("this limb moves if the per-box detrend moves. Disjoint windows of")
    print("40,000 iid normal returns.")
    iid = np.random.default_rng(1234).normal(0.0, 0.01, 40_000)
    print(f"{'ladder':24s} {'window':>7s} {'windows':>8s} {'mean':>8s} "
          f"{'sd':>8s}")
    for ladder in (BOXES, (10, 16, 25, 40, 64), (50, 80, 125, 200, 320)):
        width = 2 * max(ladder) if ladder != BOXES else LENGTH
        rows = sliding_window_view(iid, width)[::width]
        v = _mutant_alpha(ladder)(rows)
        v = v[np.isfinite(v)]
        print(f"{str(ladder):24s} {width:7d} {v.size:8d} {v.mean():8.4f} "
              f"{v.std():8.4f}")

    print("\n-- the same, through the PROTOTYPE expression on a long frame --")
    rng2 = np.random.default_rng(100)
    c = _from_returns(rng2.normal(0.0, 0.01, 20_000))
    for length, ladder in ((100, BOXES), (1000, (10, 16, 25, 40, 64)),
                           (1000, (20, 32, 50, 80, 100))):
        v = _prototype(c, length=length, boxes=ladder).dropna()
        print(f"length {length:5d} ladder {str(ladder):22s} "
              f"mean {v.mean():7.4f}  median {v.median():7.4f}  "
              f"n {v.size}")
    print("A1 asserts the module IS that expression, bit for bit, so this")
    print("is evidence about the LADDER and not about a second code path.")


def section_A8():
    print("\n== A8  centring the window before the cumulative sum ==")
    print("A constant subtracted from every return is a straight LINE in the")
    print("profile, and the per-box linear detrend removes it exactly -- so")
    print("the centring is a no-op on paper. In floating point it is not,")
    print("and it is kept because it is the prototype's expression.")
    print(f"{'frame':15s} {'bars both':>9s} {'differ':>7s} {'max |diff|':>12s} "
          f"{'max rel':>12s}")
    for name in FIRING:
        c = FRAMES[name]()
        base = tf_dfa_100(c)
        other = _uncentred(c)
        print(f"{name:15s} {_both(base, other):9d} "
              f"{_differs(base, other):7d} {_absdiff(base, other):12.3e} "
              f"{_rel(other, base):12.3e}")


def _uncentred(close, length=LENGTH, boxes=BOXES):
    """The prototype with `W.mean(1)` not subtracted before the cumulative
    sum."""
    W = _windows(close, length)
    with np.errstate(invalid="ignore", divide="ignore"):
        Y = np.cumsum(W, 1)
        log_f = []
        for s in boxes:
            k = length // s
            Z = Y[:, :k * s].reshape(len(W), k, s)
            t = np.arange(s) - (s - 1) / 2
            b = (Z * t).sum(2, keepdims=True) / (t ** 2).sum()
            m = ((Z - Z.mean(2, keepdims=True) - b * t) ** 2).mean((1, 2))
            log_f.append(0.5 * np.log(np.where(m == 0, np.nan, m)))
        L = np.log(np.array(boxes, dtype=float))
        Lc = L - L.mean()
        T = np.column_stack(log_f)
        v = (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    return _place(close, length, v)


def section_A6():
    print("\n== A6  the return spelling ==")
    print("close.pct_change(fill_method=None) vs close / close.shift(1) - 1")
    for name in FIRING:
        c = FRAMES[name]()
        a = c.pct_change(fill_method=None).to_numpy()
        b = (c / c.shift(1) - 1.0).to_numpy()
        same = bool(((np.isnan(a) == np.isnan(b))
                     & (np.isnan(a) | (a == b))).all())
        print(f"{name:15s} bit-identical: {same}")


def section_A7():
    print("\n== A7  the tail each box drops ==")
    print(f"length = {LENGTH}, boxes = {BOXES}")
    print(f"{'box s':>6s} {'k = n//s':>9s} {'covered':>8s} {'dropped':>8s}")
    for s in BOXES:
        k = LENGTH // s
        print(f"{s:6d} {k:9d} {k * s:8d} {LENGTH - k * s:8d}")
    print("\nTaking the LAST k*s points instead of the first is a different")
    print("column (it reads the same window, but weights its end):")
    print(f"{'frame':15s} {'max |diff|':>12s} {'rho':>9s}")
    for name in ("walk", "heavy-tailed", "persistent"):
        c = FRAMES[name]()
        print(f"{name:15s} {_absdiff(tf_dfa_100(c), _tail_aligned(c)):12.4f} "
              f"{_spearman(tf_dfa_100(c), _tail_aligned(c)):9.4f}")


def _tail_aligned(close, length=LENGTH, boxes=BOXES):
    W = _windows(close, length)
    with np.errstate(invalid="ignore", divide="ignore"):
        Y = np.cumsum(W - W.mean(1, keepdims=True), 1)
        log_f = []
        for s in boxes:
            k = length // s
            Z = Y[:, length - k * s:].reshape(len(W), k, s)
            t = np.arange(s) - (s - 1) / 2
            b = (Z * t).sum(2, keepdims=True) / (t ** 2).sum()
            m = ((Z - Z.mean(2, keepdims=True) - b * t) ** 2).mean((1, 2))
            log_f.append(0.5 * np.log(np.where(m == 0, np.nan, m)))
        L = np.log(np.array(boxes, dtype=float))
        Lc = L - L.mean()
        T = np.column_stack(log_f)
        v = (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    return _place(close, length, v)


def section_B():
    print("\n== B  causality ==")
    print(f"offsets swept: {OFFSETS}")
    print("\n-- the real module, and the four look-ahead mutants --")
    print(f"{'frame':15s} {'real':>6s} " +
          " ".join(f"{k:>15s}" for k in LOOKAHEAD_MUTANTS) + f" {'mask':>6s}")
    mutants = {k: _mutant(*v) for k, v in LOOKAHEAD_MUTANTS.items()}
    mask = _mutant(*MASK_MUTANT)
    for name in FIRING:
        c = FRAMES[name]()
        row = [f"{sum(_caught_at(tf_dfa_100, c, j) for j in OFFSETS):6d}"]
        for fn in mutants.values():
            caught = sum(_caught_at(fn, c, j) for j in OFFSETS)
            live = not _bit_equal(fn(c), tf_dfa_100(c))
            row.append(f"{caught:d}/{len(OFFSETS)} live={int(live):d}".rjust(15))
        row.append(f"{sum(_caught_at(mask, c, j) for j in OFFSETS):6d}")
        print(f"{name:15s} " + " ".join(row))
    print("'caught' = the prefix below the perturbation moved. The real")
    print("module must read 0 of 8 everywhere and each live mutant 8 of 8.")

    print("\n-- B2  the mutant the blind sweep cannot see --")
    print("np.roll(defined, -1) back-dates the GAP MASK, and a back-dated")
    print("gap does not depend on the future, so the sweep is blind to it.")
    for name in FIRING[:3]:
        c = FRAMES[name]()
        live = not _bit_equal(mask(c), tf_dfa_100(c))
        print(f"{name:15s} live={live} "
              f"caught={sum(_caught_at(mask, c, j) for j in OFFSETS)}/"
              f"{len(OFFSETS)}")
    print("\nPlanting one NaN close instead, and reading where the gap lands:")
    print(f"{'at':>6s} {'real first gap':>15s} {'mutant first gap':>17s}")
    for at in (200, 600, 1000):
        c = _walk()
        c.iloc[at] = np.nan
        real = [int(i) for i in np.flatnonzero(tf_dfa_100(c).isna().to_numpy())
                if i >= LENGTH]
        mut = [int(i) for i in np.flatnonzero(mask(c).isna().to_numpy())
               if i >= LENGTH]
        print(f"{at:6d} {min(real):15d} {min(mut):17d}")

    print("\n-- B3  prefix truncation ACROSS a chunk boundary --")
    print("The sweep above runs on frames that fit in one chunk, so it says")
    print("nothing about the chunk loop. With the budget cut to a few rows,")
    print("the same frame is split many times over.")
    mod = _module()
    for budget in (LENGTH, 7 * LENGTH, 97 * LENGTH):
        old = mod.CHUNK_VALUES
        try:
            mod.CHUNK_VALUES = budget
            c = _walk()
            full = mod.tf_dfa_100(c)
            ok = all(_bit_equal(full.iloc[:j], mod.tf_dfa_100(c.iloc[:j]))
                     for j in OFFSETS)
            same = _bit_equal(full, tf_dfa_100(c))
        finally:
            mod.CHUNK_VALUES = old
        print(f"budget {budget:6d} ({max(1, budget // LENGTH):4d} rows per "
              f"chunk): prefix-stable {ok}, equals the default run {same}")

    print("\n-- prefix truncation (weaker, and the check a reader expects) --")
    for name in FIRING:
        c = FRAMES[name]()
        full = tf_dfa_100(c)
        ok = all(_bit_equal(full.iloc[:j], tf_dfa_100(c.iloc[:j]))
                 for j in OFFSETS)
        print(f"{name:15s} unchanged at every offset: {ok}")


def section_C():
    print("\n== C  reachability, synthetic frames ==")
    print("⚠ Gate C's real-data limb is owed: it comes off the Gate E run,")
    print("   which issue-solver runs after this session.")
    print(f"{'frame':15s} {'bars':>6s} {'fires':>6s} {'distinct':>8s} "
          f"{'min':>9s} {'median':>9s} {'max':>9s}")
    for name in FRAMES:
        c = FRAMES[name]()
        v = tf_dfa_100(c)
        fired = v.dropna()
        if fired.empty:
            print(f"{name:15s} {len(v):6d} {0:6d} {0:8d} "
                  f"{'-':>9s} {'-':>9s} {'-':>9s}")
            continue
        print(f"{name:15s} {len(v):6d} {int(fired.size):6d} "
              f"{int(fired.nunique()):8d} {fired.min():9.4f} "
              f"{fired.median():9.4f} {fired.max():9.4f}")
    print("\nWarm-up: the first reading is at bar `length`, because `length`")
    print("returns need `length + 1` closes.")
    for name in ("walk", "heavy-tailed"):
        v = tf_dfa_100(FRAMES[name]())
        first = int(np.flatnonzero(v.notna().to_numpy())[0])
        print(f"{name:15s} first fired bar: {first}")


def section_D():
    print("\n== D  scale-free ==")
    print("-- exact binary factors: bit-identical --")
    print(f"{'frame':15s} " + " ".join(f"{f:>12s}" for f in
                                       ("x8", "x64", "2**-40", "2**40",
                                        "2**100")))
    for name in FIRING:
        c = FRAMES[name]()
        base = tf_dfa_100(c)
        row = [f"{str(_bit_equal(base, tf_dfa_100(c * f))):>12s}"
               for f in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40, 2.0 ** 100)]
        print(f"{name:15s} " + " ".join(row))

    print("\n-- x8 at every length --")
    for length in (MIN_LENGTH, 32, 64, LENGTH, 250):
        ok = all(_bit_equal(tf_dfa_100(FRAMES[n](), length=length),
                            tf_dfa_100(FRAMES[n]() * 8.0, length=length))
                 for n in FIRING)
        print(f"length {length:4d}: bit-identical on every firing frame: {ok}")

    print("\n-- inexact factors: a tolerance --")
    print("relative / absolute, because alpha passes through 0 on `jump` and")
    print("a relative figure there is a division by almost nothing.")
    print(f"{'frame':15s} " + " ".join(f"{f:>24s}" for f in
                                       ("x10", "x3.7", "x0.1", "x1.0000001")))
    worst = worst_abs = 0.0
    for name in FIRING:
        c = FRAMES[name]()
        base = tf_dfa_100(c)
        row = []
        for f in (10.0, 3.7, 0.1, 1.0000001):
            scaled = tf_dfa_100(c * f)
            assert bool((base.isna() == scaled.isna()).all())
            rel, absolute = _rel(scaled, base), _absdiff(scaled, base)
            worst = max(worst, rel)
            worst_abs = max(worst_abs, absolute)
            row.append(f"{rel:11.3e} /{absolute:11.3e}")
        print(f"{name:15s} " + " ".join(row))
    print(f"worst relative: {worst:.3e}, worst absolute: {worst_abs:.3e}")

    print("\n-- 0 < fires < n, and the column is not constant --")
    for name in FIRING:
        v = tf_dfa_100(FRAMES[name]())
        print(f"{name:15s} fires {int(v.notna().sum()):5d} of {len(v):5d}, "
              f"distinct {int(v.dropna().nunique()):5d}")

    print("\n-- a level shift is NOT a rescale, and it moves the column --")
    c = _walk()
    base = tf_dfa_100(c)
    for shift in (1.0, 50.0, 1e6):
        other = tf_dfa_100(c + shift)
        print(f"+{shift:<12g} bars moved {_differs(base, other):5d}, "
              f"max |diff| {_absdiff(base, other):.4e}")


def section_G():
    print("\n== G  guards ==")
    print("-- one bad close: how many bars empty, and does anything move "
          "before it --")
    print(f"{'value':>10s} {'at':>6s} {'newly empty':>12s} {'moved before':>13s}")
    base_c = _walk()
    base = tf_dfa_100(base_c)
    for value in (np.nan, np.inf, -np.inf, 0.0, 1e-310):
        for at in (200, 600, 1000):
            c = base_c.copy()
            c.iloc[at] = value
            v = tf_dfa_100(c)
            a, b = base.to_numpy(), v.to_numpy()
            moved = (np.isnan(a) != np.isnan(b)) | (
                ~np.isnan(a) & ~np.isnan(b) & (a != b))
            print(f"{value:>10g} {at:6d} "
                  f"{int((base.notna() & v.isna()).sum()):12d} "
                  f"{int(moved[:at].sum()):13d}")

    print("\n-- can a window be blanked WITHOUT its returns being equal? --")
    print("`mean_square` is the mean over the boxes of ONE size, so on paper")
    print("any window whose profile is exactly straight inside every box of")
    print("one size is blanked, not only a window of `length` equal returns.")
    print("Two constructions tried; NEITHER reaches it, because the profile")
    print("carries the rounding of a cumulative sum of non-dyadic numbers.")
    rng = np.random.default_rng(55)
    cases = {}
    # (1) returns held constant inside each aligned 4-bar block, built
    #     through a close path -- so the ratios are equal only to rounding.
    cases["4-block random"] = _from_returns(
        np.repeat(rng.normal(0.0, 0.01, 400), 4))
    # (2) the same shape with EXACT returns: a price path whose ratio is 2
    #     for four bars and 4 for the next four, so every return is exactly
    #     1.0 or exactly 3.0 and the blocks are bit-equal.
    ratio = np.repeat(np.tile([2.0, 4.0], 30), 4)
    cases["4-block dyadic"] = _series(
        LEVEL * np.concatenate([[1.0], np.cumprod(ratio)]))
    for label, frame in cases.items():
        r = frame.pct_change(fill_method=None).dropna()
        v = tf_dfa_100(frame)
        windows = len(frame) - LENGTH
        print(f"{label:16s} bars {len(frame):5d} windows {windows:5d} "
              f"fires {int(v.notna().sum()):5d} blank "
              f"{windows - int(v.notna().sum()):5d}  distinct returns "
              f"{int(r.nunique()):4d}")
    print("So the only blanking this port has MEASURED is the all-equal")
    print("window, and the docstrings say exactly that.")

    print("\n-- a negative close is a PRICE, not a gap --")
    c = base_c.copy()
    c.iloc[600] = -1.0
    v = tf_dfa_100(c)
    print(f"fires {int(v.notna().sum())} vs {int(base.notna().sum())} "
          f"on the clean frame; bars moved {_differs(base, v)}")

    print("\n-- degenerate frames, under errstate(all='raise') --")
    for label, data in (("all-nan", np.full(N, np.nan)),
                        ("all-zero", np.zeros(N)),
                        ("all-negative", -np.abs(_walk().to_numpy())),
                        ("flat", _flat().to_numpy()),
                        ("x2 ramp", _ramp().to_numpy())):
        with np.errstate(all="raise"):
            v = tf_dfa_100(_series(data))
        print(f"{label:15s} fires {int(v.notna().sum()):5d} of {len(v):5d}")

    print("\n-- every frame under errstate(all='raise') --")
    for name in FRAMES:
        with np.errstate(all="raise"):
            tf_dfa_100(FRAMES[name]())
    print(f"{len(FRAMES)} frames, no floating-point error raised")

    print("\n-- the shortest input that produces a value --")
    print(f"n = length + 1: fires "
          f"{int(tf_dfa_100(_walk(n=LENGTH + 1)).notna().sum())}")
    print(f"n = length:     returns {tf_dfa_100(_walk(n=LENGTH))}")

    print("\n-- a length below the minimum falls back to the default --")
    for length in (None, 0, 1, MIN_LENGTH - 1):
        print(f"length={str(length):>5s} -> "
              f"{tf_dfa_100(_walk(), length=length).name}")
    print(f"length={MIN_LENGTH} -> {tf_dfa_100(_walk(), length=MIN_LENGTH).name}")

    print("\n-- the input series is not mutated --")
    c = _walk()
    before = c.to_numpy().copy()
    tf_dfa_100(c)
    print(f"unchanged: {bool((c.to_numpy() == before).all())}")


def section_L():
    print("\n== L  what the column reads ==")
    print(f"{'frame':15s} {'mean':>9s} {'sd':>9s} {'p01':>9s} {'p50':>9s} "
          f"{'p99':>9s} {'min':>9s} {'max':>9s}")
    for name in FIRING:
        v = tf_dfa_100(FRAMES[name]()).dropna()
        print(f"{name:15s} {v.mean():9.4f} {v.std():9.4f} "
              f"{v.quantile(0.01):9.4f} {v.quantile(0.50):9.4f} "
              f"{v.quantile(0.99):9.4f} {v.min():9.4f} {v.max():9.4f}")

    print("\n-- L2  the ordering the exponent is FOR --")
    print("persistent (AR +0.6) must sit above iid, mean-reverting below.")
    med = {n: float(tf_dfa_100(FRAMES[n]()).median()) for n in
           ("mean-reverting", "walk", "persistent")}
    print(f"mean-reverting {med['mean-reverting']:.4f} < "
          f"walk {med['walk']:.4f} < persistent {med['persistent']:.4f}: "
          f"{med['mean-reverting'] < med['walk'] < med['persistent']}")

    print("\n-- L3  blind to the sign and the size of the RETURNS --")
    print("Scaling the whole return window by k multiplies every F(s) by |k|,")
    print("which shifts log F by a constant and cancels in the slope.")
    rng = np.random.default_rng(404)
    r = _walk().pct_change(fill_method=None).to_numpy()[1:]
    rows = sliding_window_view(r, LENGTH)
    rows = rows[rng.integers(0, rows.shape[0], 500)]
    # the helper is the module's own arithmetic -- re-checked here, not assumed
    direct = _place(_walk(), LENGTH, _alpha_of_rows(_windows(_walk())))
    print(f"row helper is the module, bit for bit: "
          f"{_bit_equal(direct, tf_dfa_100(_walk()))}")
    base = _alpha_of_rows(rows)
    for factor in (-1.0, 0.5, 2.0, 2.0 ** 60):
        other = _alpha_of_rows(rows * factor)
        print(f"x{factor:<10g} bit-identical: "
              f"{bool((other == base).all())}, max |diff| "
              f"{float(np.abs(other - base).max()):.3e}")
    for factor in (3.7, -0.1):
        other = _alpha_of_rows(rows * factor)
        print(f"x{factor:<10g} max |diff| "
              f"{float(np.abs(other - base).max()):.3e}")
    print("\nAdding a CONSTANT to every return (a drift) is removed by the")
    print("centring, to rounding:")
    for add in (0.001, 0.05, 1.0):
        other = _alpha_of_rows(rows + add)
        print(f"+{add:<10g} max |diff| "
              f"{float(np.abs(other - base).max()):.3e}")

    print("\n-- L5  what it is NOT blind to: the ORDER of the returns --")
    permuted = _alpha_of_rows(np.array([rng.permutation(w) for w in rows]))
    reversed_ = _alpha_of_rows(rows[:, ::-1])
    rolled = _alpha_of_rows(np.array(
        [np.roll(w, int(k)) for w, k in zip(rows, rng.integers(1, LENGTH, 500))]))
    print(f"permutation   max |diff| {float(np.abs(permuted - base).max()):.4f}"
          f"  median |diff| {float(np.median(np.abs(permuted - base))):.4f}")
    print(f"time reversal max |diff| {float(np.abs(reversed_ - base).max()):.4f}"
          f"  median |diff| {float(np.median(np.abs(reversed_ - base))):.4f}")
    print(f"rotation      max |diff| {float(np.abs(rolled - base).max()):.4f}"
          f"  median |diff| {float(np.median(np.abs(rolled - base))):.4f}")
    print("⚠ Unlike a spectral magnitude, DFA is NOT phase-blind: a rotation")
    print("   splices the window's two ends together and the profile jumps.")

    print("\n-- L4  against the fork's own persistence columns --")
    from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20
    from pandas_ta.statistics.g191_165 import g191_165
    from pandas_ta.statistics.lean_hurst_100 import lean_hurst_100
    from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
    from pandas_ta.statistics.ts_aggac_60 import ts_aggac_60
    from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20
    others = {
        "lean_hurst_100": lean_hurst_100,
        "g191_165": g191_165,
        "ts_ac1_60": ts_ac1_60,
        "ts_aggac_60": ts_aggac_60,
        "ts_cid_ce_20": ts_cid_ce_20,
        "lean_momersion_20": lean_momersion_20,
    }
    print(f"{'comparator':20s} " + " ".join(f"{n:>14s}" for n in FIRING))
    for label, fn in others.items():
        row = []
        for name in FIRING:
            c = FRAMES[name]()
            out = fn(c)
            if hasattr(out, "columns"):
                out = out.iloc[:, 0]
            row.append(f"{abs(_spearman(tf_dfa_100(c), out)):14.4f}")
        print(f"{label:20s} " + " ".join(row))
    print("⚠ Synthetic frames only, and |rho| per frame. The real comparator")
    print("   sweep is Gate E, which issue-solver runs after this session.")


def section_W():
    print("\n== W  the dictionary cut ==")
    sys.path.insert(0, str(ROOT / "docs"))
    import gen_indicator_dictionary as gen
    body = tf_dfa_100.__doc__.split("\n\n")[1]
    flat = " ".join(body.split())
    cut = gen.desc({"desc": body})
    print(f"first paragraph ({len(flat)} chars):")
    print(repr(flat))
    print(f"\nafter gen.desc(): {cut!r}")
    print(f"truncated: {cut.endswith('…')}")
    slack = 0
    while not gen.desc({"desc": flat + "x" * slack}).endswith("…"):
        slack += 1
        if slack > 400:
            break
    print(f"characters of slack before the cut bites: {slack - 1}")


def section_Z():
    print("\n== Z  cost ==")
    print("⚠ Each row says how many BARS it ran on. The two unchunked rows")
    print("   are not both 400,000: `length` 250 unchunked on 400,000 bars")
    print("   traced 3,377.6 MB on the first run here and was then killed")
    print("   by the OOM killer on a repeat, so it runs on 150,000 instead.")
    mod = _module()
    print(f"{'length':>6s} {'bars':>8s} {'budget':>14s} {'seconds':>8s} "
          f"{'peak MB':>9s}")
    for length, bars, budget in ((LENGTH, 400_000, mod.CHUNK_VALUES),
                                 (LENGTH, 400_000, 1 << 40),
                                 (250, 400_000, mod.CHUNK_VALUES),
                                 (250, 150_000, mod.CHUNK_VALUES),
                                 (250, 150_000, 1 << 40)):
        big = _walk(n=bars)
        old = mod.CHUNK_VALUES
        try:
            mod.CHUNK_VALUES = budget
            tracemalloc.start()
            t0 = perf_counter()
            mod.tf_dfa_100(big, length=length)
            seconds = perf_counter() - t0
            peak = tracemalloc.get_traced_memory()[1] / 1e6
            tracemalloc.stop()
        finally:
            mod.CHUNK_VALUES = old
        del big
        print(f"{length:6d} {bars:8d} {budget:14d} {seconds:8.2f} "
              f"{peak:9.1f}")

    print("\n-- the budget cannot change a value --")
    c = _walk()
    base = tf_dfa_100(c)
    matmul = _mutant(ALPHA_LINE, ALPHA_MATMUL)
    print(f"{'budget':>12s} {'rows/chunk':>10s} {'shipped `sum`':>14s} "
          f"{'the `@` variant':>16s}")
    for budget in (1, 64, 100, 199, 200, 299, 500, 600, 700, 800, 999,
                   10 ** 9):
        old = mod.CHUNK_VALUES
        try:
            mod.CHUNK_VALUES = budget
            shipped = _bit_equal(base, mod.tf_dfa_100(c))
        finally:
            mod.CHUNK_VALUES = old
        src = SOURCE.read_text(encoding="utf-8")
        src = src.replace(ALPHA_LINE, ALPHA_MATMUL).replace(
            "CHUNK_VALUES = 1 << 21", f"CHUNK_VALUES = {budget}")
        ns = {}
        exec(compile(src, "<matmul-mutant>", "exec"), ns)
        print(f"{budget:12d} {max(1, budget // LENGTH):10d} "
              f"{str(shipped):>14s} "
              f"{str(_bit_equal(matmul(c), ns['tf_dfa_100'](c))):>16s}")
    print("⚠ THE REASON THE SHIPPED LINE IS A SUM AND NOT A MATMUL. With")
    print("   `@`, a bar's value depends on how many bars came AFTER it --")
    print("   on which chunk it landed in -- which no causality sweep over")
    print("   a single-chunk frame can see. §Z2 isolates the step.")


def section_Z2():
    print("\n== Z2  which step is sensitive to the BLOCK SHAPE ==")
    print("A chunked run must be bit-identical to an unchunked one, so each")
    print("step is run on the whole block and again on a one-row block, and")
    print("the two are compared on the same row.")
    c = _walk()
    win = _windows(c)
    rows, length = win.shape

    def steps(block):
        out = {}
        profile = np.cumsum(block - block.mean(axis=1, keepdims=True), axis=1)
        out["profile"] = profile
        log_f = np.empty((block.shape[0], len(BOXES)))
        for j, size in enumerate(BOXES):
            boxes = length // size
            z = profile[:, :boxes * size].reshape(block.shape[0], boxes, size)
            t = np.arange(size) - (size - 1) / 2
            slope = (z * t).sum(axis=2, keepdims=True) / (t ** 2).sum()
            out[f"slope s={size}"] = slope
            resid = z - z.mean(axis=2, keepdims=True) - slope * t
            mean_square = (resid ** 2).mean(axis=(1, 2))
            out[f"meansq s={size}"] = mean_square
            log_f[:, j] = 0.5 * np.log(
                np.where(mean_square > 0.0, mean_square, 1.0))
        out["log_f"] = log_f
        centred = log_f - log_f.mean(axis=1, keepdims=True)
        out["centred"] = centred
        out["alpha matmul"] = centred @ LOG_BOX_CENTRED / LOG_BOX_SS
        out["alpha sum"] = (centred * LOG_BOX_CENTRED).sum(axis=1) / LOG_BOX_SS
        return out

    whole = steps(win)
    print(f"{'step':16s} {'rows that differ from the 1-row run':>36s}")
    for key in whole:
        bad = 0
        for row in range(200, 260):
            one = steps(win[row:row + 1])[key]
            if not bool((np.asarray(whole[key][row]) ==
                         np.asarray(one[0])).all()):
                bad += 1
        print(f"{key:16s} {bad:>24d} of 60")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A5B": section_A5b, "A6": section_A6,
    "A7": section_A7, "A8": section_A8, "B": section_B,
    "C": section_C, "D": section_D, "G": section_G, "L": section_L,
    "W": section_W, "Z": section_Z, "Z2": section_Z2,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
        SECTIONS[key]()
