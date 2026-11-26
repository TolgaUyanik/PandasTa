# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/FveMeasured.md for
`pandas_ta.volume.fve`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.volume.cmf import cmf
from pandas_ta.volume.fve import fve
from pandas_ta.volume.g191_040 import g191_040
from pandas_ta.volume.vzo import vzo

_REAL = importlib.import_module("pandas_ta.volume.fve")

SHIPPED_WRITE = "    result = 100 * vesum / vsum.where(vsum != 0)\n"


def _frame(n=1500, seed=11, sigma=0.015):
    """Tick-rounded (0.01) OHLC, about 20% of closes pinned to the high or
    low (exact ties), volume rounded to 100 shares. Same as tests/test_fve.py."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * np.exp(np.abs(rng.normal(0.0, 0.006, n)))
    low = close * np.exp(-np.abs(rng.normal(0.0, 0.006, n)))
    pin = rng.random(n)
    close = np.where(pin < 0.1, high, np.where(pin < 0.2, low, close))
    high, low, close = (np.round(x, 2) for x in (high, low, close))
    volume = np.round(rng.uniform(1e4, 1e6, n), -2)
    return Series(high), Series(low), Series(close), Series(volume)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_fve_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _loop(h, l, c, v, t, length=22, cutoff=0.003):
    """Independent per-bar reading of the issue's definition."""
    num = den = 0.0
    for i in range(t - length + 1, t + 1):
        tp, tp1 = (h[i] + l[i] + c[i]) / 3, (h[i - 1] + l[i - 1] + c[i - 1]) / 3
        mf = (c[i] - (h[i] + l[i]) / 2) + (tp - tp1)
        num += v[i] if mf > cutoff * c[i] else (-v[i] if mf < -cutoff * c[i] else 0.0)
        den += v[i]
    return 100 * num / den


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")), int(m.sum())


def main():
    h, l, c, v = _frame()
    out = fve(h, l, c, v)
    n = len(out)
    d = out.dropna()
    fires = len(d)
    tp = (h + l + c) / 3
    mf = (c - (h + l) / 2) + tp.diff()
    inside = int((mf.abs() <= 0.003 * c).sum())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={d.nunique()} "
          f"first_valid_index={int(out.notna().idxmax())} positive={int((d > 0).sum())} "
          f"negative={int((d < 0).sum())} exact_zero={int((d == 0).sum())}")
    print(f"min={d.min():.6g} max={d.max():.6g} median={d.median():.6g}")
    print(f"VE: +{int((mf > 0.003 * c).sum())} / -{int((mf < -0.003 * c).sum())} / "
          f"0 (inside band) {inside} of {int(mf.notna().sum())} defined MF bars; "
          f"close pinned to high or low: {int(((c == h) | (c == l)).sum())}")

    # Gate D
    m = out.notna()
    for what in ("price", "volume", "both"):
        for k in (8.0, 64.0, 10.0, 3.7):
            hs, ls, cs = (x * k if what in ("price", "both") else x for x in (h, l, c))
            vs = v * k if what in ("volume", "both") else v
            s = fve(hs, ls, cs, vs)
            print(f"x{k} {what}: max|diff|={float((out[m] - s[m]).abs().max()):.3g} "
                  f"nan-mask-match={bool((out.isna() == s.isna()).all())} "
                  f"bit-identical={bool((out[m] == s[m]).all())}")

    # Gate A: hand-derived example, length=3.
    hh = Series([11.0, 12.0, 12.0, 12.0, 13.0])
    hl = Series([9.0, 10.0, 10.0, 10.0, 11.0])
    hc = Series([10.0, 11.8, 11.0, 11.0, 12.5])
    hv = Series([100.0, 200.0, 300.0, 400.0, 500.0])
    print("hand-derived bars 0..4:", list(fve(hh, hl, hc, hv, length=3)),
          "expected [nan, nan, nan, -100/9, 50/3] =", [-100 / 9, 50 / 3])

    # Gate A: independent per-bar loop.
    ha, la, ca, va = (x.to_numpy() for x in (h, l, c, v))
    diffs = []
    for t in range(22, n):
        diffs.append(abs(float(out.iloc[t]) - _loop(ha, la, ca, va, t)))
    diffs = np.array(diffs)
    print(f"independent loop, bars 22..{n - 1}: max|diff|={diffs.max():.3g} "
          f"bit-identical={int((diffs == 0).sum())} of {len(diffs)}")

    # Zero volume
    zv = v.copy()
    zv.iloc[700:722] = 0.0
    zo = fve(h, l, c, zv)
    blanked = [int(i) for i in zo.index[zo.isna() & out.notna()]]
    print(f"zero-volume 700..721: {len(blanked)} newly-NaN bars {blanked}; "
          f"inf={int(np.isinf(zo).sum())}")

    # Gate B
    oh, ol, oc, ov = _frame(seed=59)
    offsets = range(100, 1500, 40)

    def leaks(fn):
        base = fn(h, l, c, v)
        hits = 0
        for j in offsets:
            ph, pl, pc, pv = h.copy(), l.copy(), c.copy(), v.copy()
            for dst, src in ((ph, oh), (pl, ol), (pc, oc), (pv, ov)):
                dst.iloc[j:] = src.iloc[j:].values
            o = fn(ph, pl, pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(fve)} of {total}")
    mut = _load_mutant(SHIPPED_WRITE, "    result = (100 * vesum / vsum.where(vsum != 0)).shift(-1)\n")
    print(f"write-shift mutant (1-bar look-ahead) leaks: {leaks(mut.fve)} of {total}")

    # Non-redundancy, one frame
    for name, col in (("G191_040_26", g191_040(c, v)), ("G191_040_22", g191_040(c, v, length=22)),
                      ("VZO_14", vzo(c, v)), ("CMF_20", cmf(h, l, c, v))):
        r, nn = _spearman(out, col)
        print(f"spearman(FVE_22, {name})={r:.4f} (n={nn})")

    # Non-redundancy, 12 frames: per-frame median |rho|
    res = {"G191_040_26": [], "G191_040_22": [], "VZO_14": [], "CMF_20": []}
    for seed in range(100, 112):
        h2, l2, c2, v2 = _frame(seed=seed)
        o2 = fve(h2, l2, c2, v2)
        res["G191_040_26"].append(abs(_spearman(o2, g191_040(c2, v2))[0]))
        res["G191_040_22"].append(abs(_spearman(o2, g191_040(c2, v2, length=22))[0]))
        res["VZO_14"].append(abs(_spearman(o2, vzo(c2, v2))[0]))
        res["CMF_20"].append(abs(_spearman(o2, cmf(h2, l2, c2, v2))[0]))
    for k, r in res.items():
        print(f"12 frames (seeds 100..111, 1,500 bars): median|rho| {k}={np.median(r):.4f} "
              f"(min {min(r):.4f}, max {max(r):.4f})")


if __name__ == "__main__":
    main()
