# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/VpciMeasured.md for
`pandas_ta.volume.vpci`. Synthetic frames only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.overlap.sma import sma
from pandas_ta.overlap.vwma import vwma
from pandas_ta.volume.cmf import cmf
from pandas_ta.volume.pvcorr import pvcorr
from pandas_ta.volume.vpci import vpci

_REAL = importlib.import_module("pandas_ta.volume.vpci")

SHIPPED_WRITE = "    result = vpc * vpr * vm\n"


def _frame(n=1500, seed=11, sigma=0.015):
    """Tick-rounded (0.01) close, volume rounded to 100 shares."""
    rng = np.random.default_rng(seed)
    close = np.round(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), 2)
    volume = np.round(rng.uniform(1e4, 1e6, n), -2)
    return Series(close), Series(volume)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_vpci_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman")), int(m.sum())


def main():
    close, volume = _frame()
    out = vpci(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    first_valid = int(out.notna().idxmax())
    d = out.dropna()
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={d.nunique()} "
          f"first_valid_index={first_valid} positive={int((d > 0).sum())} "
          f"negative={int((d < 0).sum())} exact_zero={int((d == 0).sum())}")
    print(f"min={d.min():.6g} max={d.max():.6g} median={d.median():.6g}")

    # Gate D
    m = out.notna()
    for what in ("close", "volume", "both"):
        for k in (8.0, 64.0, 10.0, 3.7):
            c = close * k if what in ("close", "both") else close
            v = volume * k if what in ("volume", "both") else volume
            s = vpci(c, v)
            print(f"x{k} {what}: max|diff|={float((out[m] - s[m]).abs().max()):.3g} "
                  f"nan-mask-match={bool((out.isna() == s.isna()).all())} "
                  f"bit-identical={bool((out[m] == s[m]).all())}")

    # Gate A: hand-derived example, short=2, long=3.
    hc = Series([10.0, 11.0, 12.0, 11.0, 13.0])
    hv = Series([100.0, 200.0, 100.0, 300.0, 100.0])
    print("hand-derived bars 0..4:", list(vpci(hc, hv, short=2, long=3)),
          "expected [nan, nan, 0, -45/3128, -23/600] =",
          [0.0, -45 / 3128, -23 / 600])

    # Gate A: the issue's formula through pandas_ta's own vwma/sma modules.
    ref = ((vwma(close, volume, 20) - sma(close, 20)) / sma(close, 20)
           * (vwma(close, volume, 5) / sma(close, 5))
           * (sma(volume, 5) / sma(volume, 20)))
    both = out.notna() & ref.notna()
    rel = ((out[both] - ref[both]).abs() / ref[both].abs()).replace(np.inf, np.nan)
    print(f"vs vwma/sma reference: mask-equal={bool((out.isna() == ref.isna()).all())} "
          f"n_both={int(both.sum())} max|diff|={float((out[both] - ref[both]).abs().max()):.3g} "
          f"max-rel={float(rel.max()):.3g} "
          f"bit-identical-bars={int((out[both] == ref[both]).sum())}")

    # Gate A: independent per-bar numpy loop.
    c, v = close.to_numpy(), volume.to_numpy()
    for t in (300, 900, 1499):
        cw, vw = c[t - 19:t + 1], v[t - 19:t + 1]
        cs, vs = c[t - 4:t + 1], v[t - 4:t + 1]
        vwl = (cw * vw).sum() / vw.sum()
        vws = (cs * vs).sum() / vs.sum()
        exp = ((vwl - cw.mean()) / cw.mean()) * (vws / cs.mean()) * (vs.mean() / vw.mean())
        got = float(out.iloc[t])
        print(f"independent-loop bar {t}: module={got!r} loop={exp!r} "
              f"|diff|={abs(got - exp):.3g}")

    # Exact zero: constant volume over the long window makes VWMA == SMA.
    cv = Series(np.full(30, 1000.0))
    zc = vpci(close.iloc[:30].reset_index(drop=True), cv)
    print(f"constant volume, 30 bars: defined={int(zc.notna().sum())} "
          f"|max|={float(zc.abs().max()):.3g}")

    # Zero volume: a 5-bar all-zero stretch at bars 700..704.
    zv = volume.copy()
    zv.iloc[700:705] = 0.0
    zo = vpci(close, zv)
    blanked = [int(i) for i in zo.index[zo.isna() & out.notna()]]
    print(f"zero-volume 700..704: {len(blanked)} newly-NaN bars "
          f"{blanked[0]}..{blanked[-1]}; inf={int(np.isinf(zo).sum())}")

    # Gate B
    _, other_v = _frame(seed=59)
    other_c = close * np.exp(np.cumsum(np.random.default_rng(7).normal(0, 0.01, n)))
    offsets = range(100, 1500, 40)

    def leaks(fn):
        base = fn(close, volume)
        hits = 0
        for j in offsets:
            pc, pv = close.copy(), volume.copy()
            pc.iloc[j:] = np.round(other_c.iloc[j:].values, 2)
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(vpci)} of {total}")
    mut = _load_mutant(SHIPPED_WRITE, "    result = (vpc * vpr * vm).shift(-1)\n")
    print(f"write-shift mutant (1-bar look-ahead) leaks: {leaks(mut.vpci)} of {total}")

    # Non-redundancy, one frame
    vpc_only = (vwma(close, volume, 20) - sma(close, 20)) / sma(close, 20)
    high, low = close * 1.005, close * 0.995
    for name, col in (("PVCORR_20", pvcorr(close, volume)),
                      ("CMF_20", cmf(high, low, close, volume)),
                      ("VPC factor alone (not shipped)", vpc_only)):
        r, nn = _spearman(out, col)
        print(f"spearman(VPCI_5_20, {name})={r:.4f} (n={nn})")

    # Non-redundancy, 12 frames: per-frame median |rho|
    rp, rv = [], []
    for seed in range(100, 112):
        c2, v2 = _frame(seed=seed)
        o2 = vpci(c2, v2)
        rp.append(abs(_spearman(o2, pvcorr(c2, v2))[0]))
        rv.append(abs(_spearman(o2, (vwma(c2, v2, 20) - sma(c2, 20)) / sma(c2, 20))[0]))
    print(f"12 frames (seeds 100..111, 1,500 bars): median|rho| PVCORR_20={np.median(rp):.4f} "
          f"(max {max(rp):.4f}); VPC factor alone={np.median(rv):.4f} (min {min(rv):.4f})")


if __name__ == "__main__":
    main()
