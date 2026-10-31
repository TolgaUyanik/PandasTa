# -*- coding: utf-8 -*-
"""Print the proxy-overlap, Gate C and Gate D numbers in docs/PvcorrMeasured.md.

    python docs/measure_pvcorr_proxy.py

Synthetic GBM walk with a fixed seed -- a PROXY, not Gate E, which needs the
parent repo's production column set. Volume is an independent lognormal
series (no built-in price/volume relationship), so a nonzero `PVCORR`
reading here comes only from sampling noise in finite windows, not a
manufactured correlation.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def walk(n=3000, sigma=0.02, seed=1):
    return pd.Series(100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n))))


def vol(n=3000, seed=2, mu=8.0, sigma=0.5):
    return pd.Series(np.exp(np.random.default_rng(seed).normal(mu, sigma, n)))


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def comparators(c, v):
    h = l = c  # noqa: E741 -- synthetic OHLC, no true range: same precedent as
    # other proxy scripts. `cmf`'s denominator is `high - low`, constant zero
    # on this flat-range synthetic frame, so it is excluded here rather than
    # printed as a NaN row.
    return {
        "MFI_14": ta.mfi(h, l, c, v),
        "EFI_13": ta.efi(c, v), "AMIHUD_21": ta.amihud(c, v),
        "NVI": ta.nvi(c, v), "PVT": ta.pvt(c, v),
        "VOL_ROC_20": v.pct_change(20),
    }


def main():
    c, v = walk(), vol()

    print("== Gate A: hand-constructed exact correlation (independent of pytest)")
    ret = c.pct_change()
    pos = pd.Series(np.nan, index=c.index)
    pos.iloc[0] = 1000.0
    for i in range(1, len(c)):
        pos.iloc[i] = pos.iloc[i - 1] * np.exp(2.0 * ret.iloc[i])
    out_pos = ta.pvcorr(c, pos, length=10).dropna()
    print("  perfectly-correlated construction: max|PVCORR - 1| =", (out_pos - 1.0).abs().max())

    n = 20
    cc, vv = walk(400), vol(400)
    cv, vvv = cc.values, vv.values
    ref = np.full(len(cv), np.nan)
    for t in range(n, len(cv)):
        rets = [cv[i] / cv[i - 1] - 1.0 for i in range(t - n + 1, t + 1)]
        dlogvs = [np.log(vvv[i] / vvv[i - 1]) for i in range(t - n + 1, t + 1)]
        ref[t] = np.corrcoef(rets, dlogvs)[0, 1]
    out = ta.pvcorr(cc, vv, length=n)
    print("  independent np.corrcoef loop: max|diff| =", np.nanmax(np.abs(out.values - ref)))

    p = ta.pvcorr(c, v)
    print("== pvcorr (independent close/volume synthetic)")
    print("n comparable", int(p.notna().sum()))
    for name, x in comparators(c, v).items():
        print(f"  PVCORR_20 vs {name}: {rho(p, x)}")

    print("== Gate C synthetic (1200 bars, seed 11 / 21)")
    c2, v2 = walk(1200, seed=11), vol(1200, seed=21)
    p2 = ta.pvcorr(c2, v2).dropna()
    print("finite", len(p2), "of", len(c2), "nonzero", int((p2 != 0).sum()),
          "pos", int((p2 > 0).sum()), "neg", int((p2 < 0).sum()),
          "nunique", p2.nunique())

    print("== Gate D tolerance (x10, x3.7), same 1200-bar frame")
    for k in (10.0, 3.7):
        d_price = (ta.pvcorr(c2, v2) - ta.pvcorr(c2 * k, v2)).abs().max()
        d_vol = (ta.pvcorr(c2, v2) - ta.pvcorr(c2, v2 * k)).abs().max()
        print(f"  k={k}: price-scaled max|diff| {d_price:.3e}, volume-scaled max|diff| {d_vol:.3e}")

    print("== zero-volume bar")
    v3 = v2.copy()
    v3.iloc[300] = 0.0
    p3 = ta.pvcorr(c2, v3)
    print("any inf:", bool(np.isinf(p3.dropna()).any()),
          "nan count with zero bar vs without:",
          int(p3.isna().sum()), "vs", int(ta.pvcorr(c2, v2).isna().sum()))


if __name__ == "__main__":
    main()
