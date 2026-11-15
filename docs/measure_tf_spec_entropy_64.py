# -*- coding: utf-8 -*-
"""Every number in `docs/TfSpecEntropy64Measured.md` and in the docstrings of
`pandas_ta/statistics/tf_spec_entropy_64.py` and
`tests/test_tf_spec_entropy_64.py` is printed by this script.

    python docs/measure_tf_spec_entropy_64.py            # every section
    python docs/measure_tf_spec_entropy_64.py A1 D L     # named sections

Sections: A1 prototype, A2 scalar-loop DFT oracle, A3 complex-FFT oracle,
A4 the TSFEL-literal variant, A5 bounds, A6 the return spelling, A7 centring,
B causality, C reachability, D scale, G guards, L what it reads, W the
dictionary cut, Z cost.
"""
from __future__ import annotations

import cmath
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

from pandas_ta.statistics.tf_spec_entropy_64 import (  # noqa: E402
    MIN_LENGTH, tf_spec_entropy_64,
)

N = 1500
LEVEL = 100.0
LENGTH = 64


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
    """A close path whose `pct_change` IS `r`. ⚠ `level * exp(cumsum(r))`
    is not that path: its returns are `exp(r) - 1`, whose harmonics put
    2.341e-05 of entropy into a frame built from a single sine (measured,
    §A5) where this builder puts 1.9e-15."""
    return _series(level * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _sine(bin_=8.0, n=N, length=LENGTH, amp=0.01, level=LEVEL):
    """Returns that are one sinusoid at `bin_` cycles per `length` bars."""
    return _from_returns(amp * np.sin(2 * np.pi * bin_ * np.arange(n) / length),
                         level)


def _cycle(seed=29, n=N, level=LEVEL, bin_=8, length=LENGTH, noise=0.002):
    """Returns carrying one sinusoid exactly on bin `bin_` of a `length`
    window, plus light Gaussian noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    r = 0.01 * np.sin(2 * np.pi * bin_ * t / length) + rng.normal(0.0, noise, n)
    return _from_returns(r, level)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _ramp(n=200, level=LEVEL, step=2.0):
    """A geometric ramp whose returns are all EXACTLY 1.0: the only non-flat
    way to reach a window with no spectrum at all. `step` has to be a power of
    two and the frame short, or the ratio is exact only to the last bits and
    the frame stops testing what it is for -- §A1's ramp table prints that:
    at `step` 1.001 over 1,500 bars the column fires on 1,436 of 1,436."""
    return _series(level * step ** np.arange(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "cycle": _cycle,
    "flat": _flat, "ramp": _ramp,
}
#: The frames whose returns are not all equal, i.e. the ones with a spectrum.
FIRING = [k for k in FRAMES if k not in ("flat", "ramp")]


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
    """Max |a - b| / |b| over the bars both define; NaN if there are none."""
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


def _windows(close, length=LENGTH):
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)
    return r, sliding_window_view(r, length)


def _place(close, length, vals):
    out = np.full(close.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


# ----------------------------------------------------------------- oracles

def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen_r2.py:229-252`, retyped verbatim and
    specialised to one `length`. `_fin` (the screen's +-inf -> NaN fold) is
    applied, as `screen()` does."""
    r, W = _windows(close, length)
    F = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1))[:, 1:]
    P = F ** 2
    s = P.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(s == 0, np.nan, s)
        v = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1)), 0).sum(1) \
            / np.log2(P.shape[1])
    return _place(close, length, v).replace([np.inf, -np.inf], np.nan)


def _loop_oracle(close, length=LENGTH):
    """The formula by explicit scalar loops: the DFT by `cmath.exp` summation,
    the entropy by `math.log2`. Shares no numpy operation with the module."""
    r = [float(x) for x in close.pct_change(fill_method=None).to_numpy()]
    n = len(r)
    nbins = length // 2
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
    r, W = _windows(close, length)
    nbins = length // 2
    D = W - W.mean(1, keepdims=True)
    X = np.fft.fft(D, axis=1)[:, 1:nbins + 1]
    P = (X.real ** 2 + X.imag ** 2)
    tot = P.sum(1)
    ok = np.isfinite(W).all(1) & (tot > 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(tot > 0.0, tot, 1.0)[:, None]
        h = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1.0)), 0.0).sum(1)
        h = h / np.log2(nbins)
    return _place(close, length, np.where(ok, h, np.nan))


def _tsfel_literal(close, length=LENGTH):
    """The reading of the source line that KEEPS the DC bin and normalises by
    the number of NON-ZERO probabilities, instead of dropping the DC bin and
    normalising by a fixed bin count."""
    r, W = _windows(close, length)
    F = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1))
    P = F ** 2
    out = np.full(len(P), np.nan)
    for i, row in enumerate(P):
        if not np.isfinite(row).all():
            continue
        tot = row.sum()
        if tot <= 0.0:
            continue
        pr = row / tot
        pr = pr[pr != 0.0]
        if pr.size < 2:
            continue
        out[i] = float(-(pr * np.log2(pr)).sum() / np.log2(pr.size))
    return _place(close, length, out)


def _entropy_of_returns(r, length=LENGTH):
    """The module's arithmetic applied straight to a RETURN array, so a claim
    about the returns is not confounded by rebuilding a close path."""
    return _entropy_of_rows(
        sliding_window_view(np.asarray(r, dtype=float), length))


def _entropy_of_rows(W):
    """The module's arithmetic on an explicit (rows, length) block."""
    P = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1))[:, 1:] ** 2
    tot = P.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(tot > 0.0, tot, 1.0)[:, None]
        h = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1.0)), 0.0).sum(1)
        h = h / np.log2(P.shape[1])
    return np.where(np.isfinite(W).all(1) & (tot > 0.0), h, np.nan)


def _no_centring(close, length=LENGTH):
    """Drop the redundant mean subtraction and keep only the DC-bin drop."""
    r, W = _windows(close, length)
    F = np.abs(np.fft.rfft(W, axis=1))[:, 1:]
    P = F ** 2
    tot = P.sum(1)
    ok = np.isfinite(W).all(1) & (tot > 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = P / np.where(tot > 0.0, tot, 1.0)[:, None]
        h = -np.where(p > 0, p * np.log2(np.where(p > 0, p, 1.0)), 0.0).sum(1)
        h = h / np.log2(P.shape[1])
    return _place(close, length, np.where(ok, h, np.nan))


# --------------------------------------------------------------- sections

def section_A1():
    print("\n== A1  the screen prototype, bit for bit ==")
    print(f"{'frame':14s} {'bars both':>9s} {'differing':>9s} "
          f"{'proto -0.0':>10s} {'module NaN there':>16s}")
    tot_both = tot_diff = tot_zero = 0
    for name in FRAMES:
        c = FRAMES[name]()
        mod, pro = tf_spec_entropy_64(c), _prototype(c)
        m = mod.notna() & pro.notna()
        both = int(m.sum())
        diff = int((mod[m] != pro[m]).sum())
        # Where the prototype reads an exact (signed) zero and we read NaN.
        z = pro.notna() & (pro == 0.0) & mod.isna()
        nz = int(z.sum())
        tot_both += both
        tot_diff += diff
        tot_zero += nz
        print(f"{name:14s} {both:9d} {diff:9d} {nz:10d} "
              f"{str(bool(mod[z].isna().all()) if nz else '-'):>16s}")
    print(f"TOTAL          {tot_both:9d} {tot_diff:9d} {tot_zero:10d}")
    print(f"bit-equal on every bar both define: {tot_diff == 0}")

    print("\n-- the -0.0 windows, named --")
    c = _walk()
    pro = _prototype(c)
    idx = np.flatnonzero((pro.to_numpy() == 0.0) & ~np.isnan(pro.to_numpy()))
    print(f"walk: prototype reads exactly 0.0 at bar(s) {list(idx)}; "
          f"LENGTH - 1 = {LENGTH - 1}")
    print(f"walk: prototype value there is "
          f"{np.copysign(1.0, pro.iloc[idx[0]]):+.1f} * 0.0")
    for name in ("flat", "ramp"):
        c = FRAMES[name]()
        pro, mod = _prototype(c), tf_spec_entropy_64(c)
        v = pro.dropna()
        print(f"{name}: prototype fires {len(v)} bars, all exactly 0.0: "
              f"{bool((v == 0.0).all())}; module fires {int(mod.notna().sum())}")

    print("\n-- the guard is EXACT equality, not a dispersion floor --")
    for n, step in ((N, 1.001), (400, 1.001), (N, 1.0000000001), (200, 2.0)):
        c = _series(LEVEL * step ** np.arange(n))
        v = tf_spec_entropy_64(c)
        print(f"ramp step {step:<14g} {n:5d} bars: fires "
              f"{int(v.notna().sum()):5d} of {n - LENGTH:5d} possible")

    print("\n-- lengths --")
    for length in (MIN_LENGTH, 5, 8, 20, 64, 250):
        diff = sum(_differs(tf_spec_entropy_64(FRAMES[n](), length=length),
                            _prototype(FRAMES[n](), length=length))
                   for n in FIRING)
        both = sum(int((tf_spec_entropy_64(FRAMES[n](), length=length).notna()
                        & _prototype(FRAMES[n](), length=length).notna()).sum())
                   for n in FIRING)
        print(f"length {length:4d}: {both:6d} bars both define, "
              f"{diff:3d} differing (NaN masks included)")


def section_A2():
    print("\n== A2  the formula by scalar loops (cmath DFT, math.log2) ==")
    print("200-bar frames: the loop oracle is O(rows * length^2) in Python.")
    print(f"{'frame':14s} {'length':>6s} {'bars':>6s} {'max rel':>12s} "
          f"{'max abs':>12s}")
    for length in (8, 16, 64):
        for name in FIRING:
            c = FRAMES[name](n=200) if name != "cycle" else _cycle(n=200)
            mod, orc = tf_spec_entropy_64(c, length=length), \
                _loop_oracle(c, length=length)
            m = mod.notna() & orc.notna()
            print(f"{name:14s} {length:6d} {int(m.sum()):6d} "
                  f"{_rel(mod, orc):12.3e} {_abs(mod, orc):12.3e}")
    print("Masks identical on every frame and length above: ", end="")
    ok = all(bool((tf_spec_entropy_64(FRAMES[n](n=200), length=L).isna()
                   == _loop_oracle(FRAMES[n](n=200), length=L).isna()).all())
             for L in (8, 16, 64) for n in FIRING)
    print(ok)


def section_A3():
    print("\n== A3  the same quantity through numpy's complex fft ==")
    print(f"{'frame':14s} {'bars':>6s} {'differing':>9s} {'max rel':>12s}")
    for name in FRAMES:
        c = FRAMES[name]()
        mod, orc = tf_spec_entropy_64(c), _complex_fft_oracle(c)
        m = mod.notna() & orc.notna()
        print(f"{name:14s} {int(m.sum()):6d} {_differs(mod, orc):9d} "
              f"{_rel(mod, orc):12.3e}")


def section_A4():
    print("\n== A4  the DC-keeping, nonzero-normalised reading ==")
    print("Keeps bin 0 (the rounding residue of the centred sum) and divides")
    print("by log2(#nonzero bins) instead of log2(length // 2).")
    print(f"{'frame':14s} {'bars':>6s} {'max |d|':>10s} {'mean d':>10s} "
          f"{'spearman':>9s} {'bins used':>10s}")
    for name in FIRING:
        c = FRAMES[name]()
        mod, lit = tf_spec_entropy_64(c), _tsfel_literal(c)
        m = mod.notna() & lit.notna()
        d = (mod[m] - lit[m])
        r, W = _windows(c)
        P = np.abs(np.fft.rfft(W - W.mean(1, keepdims=True), axis=1)) ** 2
        rows = P[np.isfinite(P).all(1) & (P.sum(1) > 0)]
        used = np.unique((rows != 0.0).sum(1))
        print(f"{name:14s} {int(m.sum()):6d} {d.abs().max():10.4f} "
              f"{d.mean():10.4f} {_spearman(mod, lit):9.4f} "
              f"{str(used.tolist()):>10s}")
    print(f"this module's bin count is fixed at length // 2 = {LENGTH // 2}")


def section_A5():
    print("\n== A5  the bound [0, 1] ==")
    print(f"{'frame':14s} {'bars':>6s} {'min':>10s} {'max':>10s} "
          f"{'> 1 by':>11s}")
    worst = 0.0
    for name in FIRING:
        c = FRAMES[name]()
        v = tf_spec_entropy_64(c).dropna()
        over = float(max(0.0, v.max() - 1.0))
        worst = max(worst, over)
        print(f"{name:14s} {len(v):6d} {v.min():10.6f} {v.max():10.6f} "
              f"{over:11.3e}")
    print(f"largest excess over 1.0 anywhere above: {worst:.3e}")

    print("\n-- the two extremes, by construction --")
    for b in (1, 2, 8, 16):
        v = tf_spec_entropy_64(_sine(b)).dropna()
        print(f"pure sinusoid on bin {b:2d}: {len(v):5d} bars, "
              f"min {v.min():.3e}, max {v.max():.3e}, "
              f"exactly 0.0 on {int((v == 0.0).sum())} of them")
    print("the same frames built as level * exp(cumsum(r)) instead, whose "
          "returns are exp(r) - 1:")
    for b in (1, 8):
        r = 0.01 * np.sin(2 * np.pi * b * np.arange(N) / LENGTH)
        v = tf_spec_entropy_64(_series(LEVEL * np.exp(np.cumsum(r)))).dropna()
        print(f"  bin {b:2d}: min {v.min():.3e}, max {v.max():.3e}")
    rng = np.random.default_rng(101)
    flat_spec = []
    for trial in range(5):
        r = rng.normal(0.0, 0.01, N)
        c = _series(LEVEL * np.exp(np.cumsum(r)))
        flat_spec.append(float(tf_spec_entropy_64(c).max()))
    print(f"white-noise returns, 5 seeds: max per seed "
          f"{[round(x, 6) for x in flat_spec]}")
    print("a perfectly flat spectrum reads exactly 1.0; the closest reached "
          f"above is {max(flat_spec):.6f}")


def section_A6():
    print("\n== A6  pct_change(fill_method=None) vs c / c.shift(1) - 1 ==")
    for name in FRAMES:
        c = FRAMES[name]()
        a = c.pct_change(fill_method=None).to_numpy()
        b = (c / c.shift(1) - 1).to_numpy()
        same = bool((np.isnan(a) == np.isnan(b)).all()
                    and (a[~np.isnan(a)] == b[~np.isnan(b)]).all())
        print(f"{name:14s} bit-equal returns: {same}")


def section_A7():
    print("\n== A7  centring on / off (both drop the DC bin) ==")
    print(f"{'frame':14s} {'bars':>6s} {'differing':>9s} {'max rel':>12s}")
    worst = 0.0
    for name in FIRING:
        c = FRAMES[name]()
        a, b = tf_spec_entropy_64(c), _no_centring(c)
        worst = max(worst, _rel(a, b))
        print(f"{name:14s} {int((a.notna() & b.notna()).sum()):6d} "
              f"{_differs(a, b):9d} {_rel(a, b):12.3e}")
    print(f"max relative move from dropping the centring: {worst:.3e}")


# ----------------------------------------------------------------- Gate B

SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_spec_entropy_64.py"
RET_LINE = "    r = close.pct_change(fill_method=None).to_numpy(dtype=float)"
OUT_LINE = "            out[length - 1 + a:length - 1 + b] = \\"
WIN_LINE = "        win = sliding_window_view(r, length)   # (rows, length), oldest first"
MASK_LINE = "    ok = np.isfinite(win).all(axis=1) & (total > 0.0)"

MUTANTS = {
    "return-lead": (RET_LINE,
                    "    r = close.shift(-1).pct_change(fill_method=None)"
                    ".to_numpy(dtype=float)"),
    "output-early": (OUT_LINE,
                     "            out[length - 2 + a:length - 2 + b] = \\"),
    "window-ahead": (WIN_LINE,
                     "        win = sliding_window_view(np.roll(r, -1), "
                     "length)"),
    # The `bos` failure mode: a window centred on the current bar rather than
    # ending at it, which reads `length // 2` bars ahead.
    "window-centred": (WIN_LINE,
                       "        win = sliding_window_view("
                       "np.roll(r, -(length // 2)), length)"),
    "mask-shifted": (MASK_LINE,
                     "    ok = np.roll(np.isfinite(win).all(axis=1), -1) "
                     "& (total > 0.0)"),
}


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tf_spec_entropy_64"]


def _futures(close, j, spread=3.0):
    n = close.size
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return close * Series(up, index=close.index), \
        close * Series(dn, index=close.index)


def _caught_at(fn, close, j):
    a, b = (fn(f).iloc[:j] for f in _futures(close, j))
    return not _bit_equal(a, b)


def _offsets(n=N, how_many=12):
    return [int(round(x)) for x in np.linspace(LENGTH + 5, n - 5, how_many)]


def section_B():
    print("\n== B  causality ==")
    offs = _offsets()
    print(f"offsets swept: {offs}")
    print(f"\n{'frame':14s} {'real caught':>11s}")
    for name in FIRING:
        c = FRAMES[name]()
        print(f"{name:14s} "
              f"{sum(_caught_at(tf_spec_entropy_64, c, j) for j in offs):5d}"
              f" / {len(offs)}")

    print(f"\n{'mutant':14s} {'frame':14s} {'live':>5s} {'caught':>8s}")
    for label, (old, new) in MUTANTS.items():
        fn = _mutant(old, new)
        for name in FIRING:
            c = FRAMES[name]()
            live = not _bit_equal(fn(c), tf_spec_entropy_64(c))
            caught = sum(_caught_at(fn, c, j) for j in offs)
            print(f"{label:14s} {name:14s} {str(live):>5s} "
                  f"{caught:4d} / {len(offs)}")

    print("\n-- B2  the gap mask, which the blind sweep cannot see --")
    print("`mask-shifted` back-dates the NaN mask by one bar. Prefix "
          "truncation and the future sweep are both blind to back-dating "
          "(CLAUDE.md Gate B), so it is pinned directly: plant one NaN close "
          "and read where the gap lands.")
    fn = _mutant(*MUTANTS["mask-shifted"])
    print(f"{'plant at':>8s} {'real gap':>14s} {'mutant gap':>14s} "
          f"{'mutant = real - 1':>18s} {'extra bars':>11s}")
    for at in (200, 400, 700, 1000):
        c = _walk()
        c.iloc[at] = np.nan
        real = np.flatnonzero(tf_spec_entropy_64(c).isna().to_numpy())
        mut = np.flatnonzero(fn(c).isna().to_numpy())
        real, mut = set(real[real >= LENGTH]), set(mut[mut >= LENGTH])
        shifted = {b - 1 for b in real}
        extra = sorted(mut - shifted)
        lo, hi = min(real), max(real)
        print(f"{at:8d} {f'{lo}..{hi}':>14s} "
              f"{f'{min(mut)}..{max(shifted)}':>14s} "
              f"{str(shifted <= mut):>18s} {str(extra):>11s}")
    print("The extra bar is the last one: np.roll wraps the warm-up's False "
          "round to the end of the mask.")

    print("\n-- how far each live mutant back-dates the column --")
    c = _walk()
    base = tf_spec_entropy_64(c).to_numpy()
    for label, (old, new) in MUTANTS.items():
        v = _mutant(old, new)(c).to_numpy()
        best, bestk = -1, None
        for k in range(0, 4):
            if k == 0:
                a, b = base, v
            else:
                a, b = base[k:], v[:-k]
            m = ~np.isnan(a) & ~np.isnan(b)
            hits = int((a[m] == b[m]).sum())
            if hits > best:
                best, bestk = hits, k
        print(f"{label:14s} best match at a {bestk}-bar back-date: "
              f"{best} bars bit-equal")


def section_C():
    print("\n== C  reachability (synthetic; the real-data limb is owed with "
          "the Gate E run) ==")
    print(f"{'frame':14s} {'bars':>6s} {'fired':>6s} {'distinct':>9s} "
          f"{'mean':>9s} {'min':>9s} {'max':>9s}")
    for name in FRAMES:
        c = FRAMES[name]()
        v = tf_spec_entropy_64(c)
        d = v.dropna()
        print(f"{name:14s} {len(v):6d} {len(d):6d} {d.nunique():9d} "
              f"{(d.mean() if len(d) else float('nan')):9.4f} "
              f"{(d.min() if len(d) else float('nan')):9.4f} "
              f"{(d.max() if len(d) else float('nan')):9.4f}")
    print(f"\nwarm-up: first fired bar per frame (LENGTH = {LENGTH})")
    for name in FIRING:
        v = tf_spec_entropy_64(FRAMES[name]())
        print(f"{name:14s} {int(v.notna().to_numpy().argmax()):4d}")
    print("\nshortest input that produces a value:")
    c = _walk(n=LENGTH + 1)
    v = tf_spec_entropy_64(c)
    print(f"{LENGTH + 1} closes -> {int(v.notna().sum())} fired bar(s)")
    print(f"{LENGTH} closes -> {tf_spec_entropy_64(_walk(n=LENGTH))}")


def section_D():
    print("\n== D  scale-free ==")
    exact = [8.0, 64.0, 2.0 ** -40, 2.0 ** 40, 2.0 ** 100]
    print("exact binary factors, bit-identical?")
    print(f"{'frame':14s} " + " ".join(f"{f:>12.3e}" for f in exact))
    for name in FIRING:
        c = FRAMES[name]()
        base = tf_spec_entropy_64(c)
        row = [str(_bit_equal(base, tf_spec_entropy_64(c * f))) for f in exact]
        print(f"{name:14s} " + " ".join(f"{x:>12s}" for x in row))

    inexact = [10.0, 3.7, 0.1, 1.0000001]
    print("\ninexact factors, max relative move")
    print(f"{'frame':14s} " + " ".join(f"{f:>12g}" for f in inexact))
    worst = 0.0
    for name in FIRING:
        c = FRAMES[name]()
        base = tf_spec_entropy_64(c)
        row = []
        for f in inexact:
            scaled = tf_spec_entropy_64(c * f)
            assert bool((base.isna() == scaled.isna()).all())
            row.append(_rel(scaled, base))
            worst = max(worst, row[-1])
        print(f"{name:14s} " + " ".join(f"{x:12.3e}" for x in row))
    print(f"largest relative move under an inexact rescale: {worst:.3e}")

    print("\n0 < fires < n on every frame with a spectrum:")
    for name in FIRING:
        v = tf_spec_entropy_64(FRAMES[name]())
        print(f"{name:14s} 0 < {int(v.notna().sum())} < {len(v)}: "
              f"{0 < int(v.notna().sum()) < len(v)}")

    print("\na LEVEL SHIFT is not a rescale (the column must move):")
    for shift in (1.0, 50.0, 1e6):
        c = _walk()
        a, b = tf_spec_entropy_64(c), tf_spec_entropy_64(c + shift)
        print(f"+{shift:>10g}: {_differs(a, b):5d} bars differ, "
              f"max |d| {_abs(a, b):.3e}")

    print("\nat other lengths (x8 bit-identical?):")
    for length in (MIN_LENGTH, 5, 8, 20, 64, 250):
        ok = all(_bit_equal(tf_spec_entropy_64(FRAMES[n](), length=length),
                            tf_spec_entropy_64(FRAMES[n]() * 8.0,
                                               length=length))
                 for n in FIRING)
        print(f"length {length:4d}: {ok}")


def section_G():
    print("\n== G  guards ==")
    base = _walk()
    print(f"{'planted':>12s} {'at bar':>7s} {'emptied':>8s} "
          f"{'earlier moved':>14s}")
    for value in (np.nan, np.inf, -np.inf, 0.0, -1.0, 1e-310):
        for at in (0, 1, LENGTH, 700, N - 1):
            c = base.copy()
            c.iloc[at] = value
            a, b = tf_spec_entropy_64(base), tf_spec_entropy_64(c)
            newly = int((a.notna() & b.isna()).sum())
            av, bv = a.to_numpy(), b.to_numpy()
            pos = np.arange(av.size) < at
            moved = (np.isnan(av) != np.isnan(bv)) | (
                ~np.isnan(av) & ~np.isnan(bv) & (av != bv))
            print(f"{value!r:>12} {at:7d} {newly:8d} "
                  f"{int((moved & pos).sum()):14d}")

    print("\nall-NaN / all-zero / all-negative inputs:")
    for label, arr in (("all-NaN", np.full(N, np.nan)),
                       ("all-zero", np.zeros(N)),
                       ("all-negative", -np.abs(_walk().to_numpy()))):
        c = _series(arr)
        with np.errstate(all="raise"):
            v = tf_spec_entropy_64(c)
        print(f"{label:14s} fired {int(v.notna().sum())} of {len(v)}")

    print("\nevery frame under np.errstate(all='raise'):")
    for name in FRAMES:
        c = FRAMES[name]()
        with np.errstate(all="raise"):
            tf_spec_entropy_64(c)
        print(f"{name:14s} clean")

    print("\nand every planted bad value under np.errstate(all='raise'):")
    for value in (np.nan, np.inf, -np.inf, 0.0, -1.0, 1e-310):
        for at in (0, 1, LENGTH, 700, N - 1):
            c = _walk()
            c.iloc[at] = value
            with np.errstate(all="raise"):
                tf_spec_entropy_64(c)
    print("30 (value, position) pairs: clean")
    print("⚠ without the np.isfinite fold on the returns, the inf pairs raise "
          "'invalid value encountered in subtract' at `win - win.mean(...)`: "
          "inf - inf. Measured before the fold was added.")

    print("\nthe input series is not mutated:")
    c = _walk()
    before = c.to_numpy().copy()
    tf_spec_entropy_64(c)
    print(f"unchanged: {bool((c.to_numpy() == before).all())}")

    print(f"\nlength below MIN_LENGTH ({MIN_LENGTH}) falls back to 64:")
    for length in (None, 0, 1, 2, 3, MIN_LENGTH):
        print(f"length={length!r:>5}: {tf_spec_entropy_64(_walk(), length=length).name}")


def section_L():
    print("\n== L  what the column reads ==")
    print(f"{'frame':14s} {'mean':>9s} {'sd':>9s} {'p05':>9s} {'p95':>9s}")
    for name in FIRING:
        v = tf_spec_entropy_64(FRAMES[name]()).dropna()
        print(f"{name:14s} {v.mean():9.4f} {v.std():9.4f} "
              f"{v.quantile(0.05):9.4f} {v.quantile(0.95):9.4f}")

    print("\n-- L2  a sinusoid on the bin grid and off it --")
    for label, freq in (("bin 8", 8.0), ("bin 8.5", 8.5), ("bin 8.25", 8.25)):
        v = tf_spec_entropy_64(_sine(freq)).dropna()
        print(f"{label:18s} mean {v.mean():.4f}  min {v.min():.4e}  "
              f"max {v.max():.4f}")

    print("\n-- L3  blind to the sign and the size of the returns --")
    print("First the precondition L3 and L5 rest on: `_entropy_of_rows` is a")
    print("COPY of the module's arithmetic, needed because a claim about a")
    print("WINDOW cannot go through a close path (rebuilding one from altered")
    print("returns rounds). Pinned to the module, bit for bit, per frame:")
    for name in FIRING:
        c = FRAMES[name]()
        direct = _place(c, LENGTH, _entropy_of_rows(_windows(c)[1]))
        print(f"  {name:14s} bit-equal to tf_spec_entropy_64: "
              f"{_bit_equal(direct, tf_spec_entropy_64(c))}")
    print("\nOn the ARITHMETIC, with the return array scaled directly "
          "(bit-equal?):")
    r = _walk().pct_change(fill_method=None).to_numpy()
    base = _entropy_of_returns(r)
    for label, factor in (("* -1", -1.0), ("* 0.5", 0.5), ("* 2", 2.0),
                          ("* -3.7", -3.7), ("* 1e6", 1e6)):
        v = _entropy_of_returns(r * factor)
        same = bool((np.isnan(base) == np.isnan(v)).all()
                    and (base[~np.isnan(base)] == v[~np.isnan(v)]).all())
        m = ~np.isnan(base) & ~np.isnan(v)
        rel = float(np.max(np.abs(v[m] - base[m]) / np.abs(base[m])))
        print(f"returns {label:7s} bit-equal {str(same):5s}  "
              f"max rel {rel:.3e}")
    print("⚠ Through a CLOSE path rebuilt from scaled returns it is only")
    print("near-equal, because rebuilding and re-differencing rounds:")
    c = _walk()
    col = tf_spec_entropy_64(c)
    rs = c.pct_change(fill_method=None)
    for label, flipped in (("returns * -1", (1.0 - rs).cumprod() * LEVEL),
                           ("returns * 0.5",
                            (1.0 + 0.5 * rs).cumprod() * LEVEL)):
        other = tf_spec_entropy_64(flipped.fillna(LEVEL))
        print(f"{label:16s} differing bars {_differs(col, other):5d}, "
              f"max |d| {_abs(col, other):.3e}")

    print("\n-- L5  what the magnitude spectrum throws away --")
    print("|rfft| is invariant under a circular rotation of the window and")
    print("under time reversal, so the column cannot see either. On the")
    print("arithmetic, one 1,500-bar walk, 2,000 random rotations:")
    rng = np.random.default_rng(404)
    r = _walk().pct_change(fill_method=None).to_numpy()[1:]
    W = sliding_window_view(r, LENGTH)
    rows = W[rng.integers(0, W.shape[0], 2000)]
    base = _entropy_of_rows(rows)
    rot = _entropy_of_rows(np.array([np.roll(w, int(k)) for w, k
                                     in zip(rows, rng.integers(1, LENGTH,
                                                               2000))]))
    rev = _entropy_of_rows(rows[:, ::-1])
    for label, v in (("rotated", rot), ("reversed", rev)):
        print(f"{label:10s} bit-equal {int((v == base).sum())} / {len(base)}, "
              f"max |d| {float(np.abs(v - base).max()):.3e}")
    print("A PERMUTATION is a different matter -- it is not an |rfft| "
          "symmetry:")
    perm = _entropy_of_rows(np.array([rng.permutation(w) for w in rows]))
    print(f"{'permuted':10s} bit-equal {int((perm == base).sum())} / "
          f"{len(base)}, max |d| {float(np.abs(perm - base).max()):.3e}")

    print("\n-- L4  against the fork's other entropy / spectrum columns --")
    from pandas_ta.statistics.entropy import entropy as ta_entropy
    from pandas_ta.statistics.entlz import entlz as ta_entlz
    from pandas_ta.statistics.ts_binent_20 import ts_binent_20
    from pandas_ta.statistics.ts_perment_20 import ts_perment_20
    from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20
    others = {
        "entropy(10)": lambda c: ta_entropy(c),
        "entlz": lambda c: ta_entlz(c).iloc[:, 0] if hasattr(
            ta_entlz(c), "columns") else ta_entlz(c),
        "ts_binent_20": ts_binent_20,
        "ts_perment_20": ts_perment_20,
        "tf_centroid_20": tf_centroid_20,
    }
    print(f"{'comparator':16s} " + " ".join(f"{n:>13s}" for n in FIRING))
    for label, fn in others.items():
        row = []
        for name in FIRING:
            c = FRAMES[name]()
            try:
                row.append(f"{abs(_spearman(tf_spec_entropy_64(c), fn(c))):13.4f}")
            except Exception as exc:                      # pragma: no cover
                row.append(f"{type(exc).__name__:>13s}")
        print(f"{label:16s} " + " ".join(row))
    print("⚠ synthetic frames only; the real comparator sweep is Gate E.")


def section_W():
    print("\n== W  the dictionary cut ==")
    sys.path.insert(0, str(ROOT / "docs"))
    import gen_indicator_dictionary as gen
    doc = tf_spec_entropy_64.__doc__
    body = doc.split("\n\n")[1]
    rec = {"desc": body}
    cut = gen.desc(rec)
    print(f"first paragraph ({len(' '.join(body.split()))} chars):")
    print(repr(" ".join(body.split())))
    print(f"\nafter gen.desc(): {cut!r}")
    print(f"truncated: {cut.endswith('…')}")
    grown = " ".join(body.split())
    slack = 0
    while not gen.desc({"desc": grown + "x" * slack}).endswith("…"):
        slack += 1
        if slack > 400:
            break
    print(f"characters of slack before the cut bites: {slack - 1}")


def section_M():
    print("\n== M  the running tally in docs/MLCompanionContract.md ==")
    path = ROOT / "docs" / "MLCompanionContract.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    end = 26
    while end < len(lines) and lines[end].strip():
        end += 1
    print(f"the tally paragraph is lines 27..{end} "
          f"({sum(len(x) for x in lines[26:end])} characters)")
    for i in range(26, end):
        print(f"  line {i + 1}: {len(lines[i])} chars")
    tail = "\n".join(lines[26:end])
    print(f"\nlast 700 characters of the paragraph:")
    print(repr(tail[-700:]))
    for marker in ("ts_reoccur_20", "sk_rocwb_ratio", "sk_fcb_pos",
                   "j_acosc", "tf_centroid_20"):
        print(f"  {marker:18s} first at offset {tail.find(marker):6d} "
              f"of {len(tail)}")
    print(f"\nfirst 300 characters of the paragraph:")
    print(repr(tail[:300]))

    print("\n-- what this port adds to the dictionary --")
    print("⚠ The tally's absolute totals (694 tagged columns, 333 `SF`) come")
    print("from a parse this script does not reproduce -- a naive regex over")
    print("the generated tables counts fewer. What is checked here is the")
    print("DELTA, which is what the +1 / +1 claim actually rests on: the")
    print("regenerated dictionary gains exactly one row, carrying exactly")
    print("one column, tagged SF.")
    import re
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    row = [x for x in text.splitlines()
           if x.startswith("| `tf_spec_entropy_64`")]
    print(f"\nrows for this indicator: {len(row)}")
    print(row[0] if row else "MISSING")
    cols = re.findall(r"`([A-Z0-9_.\-+]+)` (PX2|PX|SF|BIN|ORD|CONST|\?\?)",
                      row[0].split("|")[4]) if row else []
    print(f"columns in that row: {cols}")
    line = tail
    print(f"\nnames tf_spec_entropy_64: {'tf_spec_entropy_64' in line}")
    print(f"names TFSPECENT_64:       {'TFSPECENT_64' in line}")


def section_Z():
    import importlib
    # NOT `import pandas_ta.statistics.tf_spec_entropy_64 as mod`: the package
    # re-exports the FUNCTION under that attribute name and shadows the
    # module. `import_module` returns `sys.modules[name]`, which is the module.
    mod = importlib.import_module("pandas_ta.statistics.tf_spec_entropy_64")
    print("\n== Z  cost, on 400,000 bars ==")
    big = _walk(n=400_000)
    budgets = (mod.CHUNK_VALUES, 1 << 40)
    print(f"{'length':>7s} {'best of 3 (s)':>14s} "
          f"{'peak, chunked (MB)':>19s} {'peak, one block (MB)':>21s}")
    times = {}
    for length in (MIN_LENGTH, 20, 64, 250):
        best = min(_timed(big, length) for _ in range(3))
        peaks = []
        for budget in budgets:
            mod.CHUNK_VALUES = budget
            tracemalloc.start()
            mod.tf_spec_entropy_64(big, length=length)
            peaks.append(tracemalloc.get_traced_memory()[1] / 1e6)
            tracemalloc.stop()
        mod.CHUNK_VALUES = budgets[0]
        times[length] = best
        print(f"{length:7d} {best:14.3f} {peaks[0]:19.1f} {peaks[1]:21.1f}")
    print(f"length 250 / length {MIN_LENGTH}: "
          f"{times[250] / times[MIN_LENGTH]:.2f}x")
    print("⚠ wall clock moves between runs and machines; the ordering and "
          "the peak are the claims.")

    print("\nthe budget cannot change a value (default length):")
    c = _walk()
    base = tf_spec_entropy_64(c)
    for budget in (1, 64, 999, 10 ** 9):
        mod.CHUNK_VALUES = budget
        print(f"CHUNK_VALUES = {budget:>11d}: bit-equal "
              f"{_bit_equal(base, mod.tf_spec_entropy_64(c))}")
    mod.CHUNK_VALUES = budgets[0]


def _timed(close, length):
    t0 = perf_counter()
    tf_spec_entropy_64(close, length=length)
    return perf_counter() - t0


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "A6": section_A6, "A7": section_A7, "B": section_B,
    "C": section_C, "D": section_D, "G": section_G, "L": section_L,
    "M": section_M, "W": section_W, "Z": section_Z,
}


def main(argv):
    wanted = [a.upper() for a in argv[1:]] or list(SECTIONS)
    unknown = [w for w in wanted if w not in SECTIONS]
    if unknown:
        raise SystemExit(f"unknown section(s) {unknown}; "
                         f"known: {list(SECTIONS)}")
    print(f"numpy {np.__version__}")
    for w in wanted:
        SECTIONS[w]()


if __name__ == "__main__":
    main(sys.argv)
