# -*- coding: utf-8 -*-
"""ALTPORT-0 Gate-D screen: is each candidate's shippable form scale-free?

Gate D proper is `x8`/`x64` bit-identity plus `x10`/`x3.7` within tolerance
plus `0 < fires < n`. This is the cheap half -- O/H/L/C x 8, `max |x8 - x|` --
run at triage time so a candidate that cannot be a feature at all is skipped
before anyone writes it.

Same rule as `gen_altport0_triage.py`: every candidate comes from the UPSTREAM
package (`pandas_ta_classic`, `tti`), never from a transcription. A hand-written
scale-free FORM is derived from upstream output.

⚠ Parameters are load-bearing here and both failing rows are reported at two
parameterisations, because the size of the failure moves with them:
`RangeIndicator` at tti's own defaults (5/3) and at the 14/3 used in the
overlap run; `SwingIndex` has no parameters.

⚠ Imports `pandas_ta` and `pandas_ta_classic` into one process -- see the
warning in `gen_altport0_triage.py`. Nothing goes through `df.ta`.

Usage:  python docs/scalecheck_altport0.py
"""
import importlib.util
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "_altport0", os.path.join(HERE, "gen_altport0_triage.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)

import numpy as np                                          # noqa: E402
import pandas as pd                                         # noqa: E402

ta, tac, tti_ind = _g.ta, _g.tac, _g.tti_ind
tti_call = _g.tti_call

# The shippable scale-free form of every candidate that got past the "is it a
# price level" question, plus the two whose upstream form is suspected of
# failing. Each takes the frame and returns a Series.
FORMS = {
    # classic
    "cvi_10":            lambda d: tac.cvi(d.high, d.low, length=10),
    "hvol_20":           lambda d: tac.hvol(d.close, length=20),
    "msw_sine_5":        lambda d: tac.msw(d.close, period=5).iloc[:, 0],
    "ce_long_dist_pct":  lambda d: (d.close - tac.ce(d.high, d.low, d.close,
                                                     length=22, multiplier=3).iloc[:, 0])
                                   / d.close * 100,
    # tti
    "mfi_bw_raw":        lambda d: tti_call(tti_ind.MarketFacilitationIndex, d)["mfi"],
    "mfi_bw_sf":         lambda d: (tti_call(tti_ind.MarketFacilitationIndex, d)["mfi"]
                                    * d.volume / d.close)
                                   / (d.volume / d.volume.rolling(20).mean()),
    "pb_width_pct":      lambda d: _pb(d, "w"),
    "pb_up_dist_pct":    lambda d: _pb(d, "u"),
    "pb_lo_dist_pct":    lambda d: _pb(d, "l"),
    "posc_14":           lambda d: tti_call(tti_ind.ProjectionOscillator, d)["posc"],
    "wad_bar_raw":       lambda d: tti_call(tti_ind.WilliamsAccumulationDistribution, d)["wad"],
    "wad_bar_sf":        lambda d: tti_call(tti_ind.WilliamsAccumulationDistribution, d)["wad"]
                                   / ta.true_range(d.high, d.low, d.close),
    "swi_tti":           lambda d: tti_call(tti_ind.SwingIndex, d)["swi"],
    "swi_sf_derived":    lambda d: _swi_sf_derived(d),
    "ri_5_3":            lambda d: tti_call(tti_ind.RangeIndicator, d)["ri"],
    "ri_14_3":           lambda d: tti_call(tti_ind.RangeIndicator, d, range_period=14,
                                            smoothing_period=3)["ri"],
}


def _pb(d, which):
    b = tti_call(tti_ind.ProjectionBands, d)
    if which == "w":
        return (b["upper_band"] - b["lower_band"]) / d.close * 100
    if which == "l":
        return (d.close - b["lower_band"]) / d.close * 100
    return (b["upper_band"] - d.close) / d.close * 100


def _swi_sf_derived(d):
    """SwingIndex with Wilder's raw-price K/3 term divided back out of tti's
    CLAMPED, ROUNDED output. NOT the same series as the `swi_sf_direct` that
    `rounding_probe` computes -- pooled max |direct - derived| is 53.23, and
    round 2 reported a rho measured on one under the name of the other. Kept
    here only to show WHY it fails x8 (the clamp), never as the shippable
    form."""
    swi = tti_call(tti_ind.SwingIndex, d)["swi"]
    a = (d.high - d.close.shift(1)).abs()
    b = (d.low - d.close.shift(1)).abs()
    K = pd.concat([a, b], axis=1).max(axis=1)
    return swi / (K / 3.0)


def main():
    frames = dict(_g.load_frames())
    d = frames[_g.SCALE_FRAME]
    print(f"frame: {_g.SCALE_FRAME}  bars: {len(d)}")

    d8 = d.copy()
    for col in ("open", "high", "low", "close"):
        d8[col] = d8[col] * 8.0

    print("\n%-20s %14s %14s  %s" % ("column", "max|x8 - x|", "max|x|", "scale-free?"))
    for name, fn in FORMS.items():
        a, b = fn(d), fn(d8)
        s = pd.concat([pd.Series(a).rename("a"), pd.Series(b).rename("b")], axis=1)
        s = s.replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            print("%-20s %14s" % (name, "EMPTY"))
            continue
        dd = (s.a - s.b).abs().max()
        print("%-20s %14.6g %14.6g  %s"
              % (name, dd, s.a.abs().max(), "YES" if dd < 1e-9 else "NO"))

    print("\n--- msw: where the x8 difference comes from -------------------")
    print("(the `abs(rp) > 0.001` guard is an ABSOLUTE epsilon on a "
          "price-scaled quantity)")
    for mult, label in ((1.0, "x1"), (8.0, "x8")):
        arr = (d.close * mult).to_numpy(float)
        P, tpi = 5, 2 * np.pi
        j = np.arange(P, dtype=float)
        ca, sa = np.cos(tpi * j / P), np.sin(tpi * j / P)
        hits = 0
        for i in range(P, len(arr)):
            w = arr[i - P + 1:i + 1][::-1]
            if abs(float(w @ ca)) <= 0.001:
                hits += 1
        print("  %s: epsilon branch fires %d times of %d bars" % (label, hits, len(arr) - P))
    a = tac.msw(d.close, period=5).iloc[:, 0]
    b = tac.msw(d.close * 8.0, period=5).iloc[:, 0]
    diff = (a - b).abs()
    print("  bars differing by > 1e-9: %d of %d" % (int((diff > 1e-9).sum()), diff.notna().sum()))


def rounding_probe():
    """Separate tti's OUTPUT ROUNDING from real scale-dependence.

    tti rounds every result before returning it -- `.round(4)` on most classes,
    `.round(10)` on MarketFacilitationIndex, whose values are of order 1e-7 so
    that is a several-percent relative quantisation. Rounding a PRICE-scaled
    quantity to a fixed number of decimals is itself scale-dependent, so a form
    DERIVED from tti output can fail an x8 check while the underlying maths is
    invariant. A port would not round. This re-runs the same forms computed
    WITHOUT the rounding step, so the Gate-D verdict lands on the maths.
    """
    frames = dict(_g.load_frames())
    d = frames[_g.SCALE_FRAME]
    d8 = d.copy()
    for col in ("open", "high", "low", "close"):
        d8[col] = d8[col] * 8.0

    def _unrounded(dd):
        o, h, l, c, v = dd.open, dd.high, dd.low, dd.close, dd.volume
        out = {}
        out["mfi_bw_sf"] = ((h - l) / c) / (v / v.rolling(20).mean())

        P = 14
        x = np.arange(P, dtype=float)
        xm = x.mean()
        sxx = ((x - xm) ** 2).sum()

        def sl(s):
            return s.rolling(P).apply(
                lambda y: ((x - xm) * (y - y.mean())).sum() / sxx, raw=True)

        hs, ls = sl(h).to_numpy(float), sl(l).to_numpy(float)
        hv, lv = h.to_numpy(float), l.to_numpy(float)
        ub = np.full(len(hv), np.nan)
        lb = np.full(len(hv), np.nan)
        jj = np.arange(1, P)
        for i in range(P - 1, len(hv)):
            if np.isnan(hs[i]):
                continue
            ub[i] = max(hv[i], float(np.max(jj * hs[i] + hv[i - jj])))
            lb[i] = min(lv[i], float(np.min(jj * ls[i] + lv[i - jj])))
        ub = pd.Series(ub, index=c.index)
        lb = pd.Series(lb, index=c.index)
        out["pb_width_pct"] = (ub - lb) / c * 100
        out["pb_up_dist_pct"] = (ub - c) / c * 100
        out["posc_14"] = 100 * (c - lb) / (ub - lb)

        trh = pd.concat([c.shift(1), h], axis=1).max(axis=1)
        trl = pd.concat([c.shift(1), l], axis=1).min(axis=1)
        dc = c - c.shift(1)
        w = pd.Series(0.0, index=c.index)
        w[dc > 0] = (c - trl)[dc > 0]
        w[dc < 0] = (c - trh)[dc < 0]
        out["wad_bar_sf"] = w / ta.true_range(h, l, c)

        a = (h - c.shift(1)).abs()
        b = (l - c.shift(1)).abs()
        ycyo = c.shift(1) - o.shift(1)
        num = (c - c.shift(1)) + 0.5 * (c - o) + 0.25 * ycyo
        R = pd.concat([a, b, h - l], axis=1).max(axis=1) + 0.25 * ycyo.abs()
        out["swi_sf_direct"] = 50 * (num / R)

        tr = pd.concat([h - l, h - c.shift(1), c.shift(1) - l], axis=1).max(axis=1)
        st = pd.Series(np.where(c > c.shift(1), tr / (c - c.shift(1)), tr), index=c.index)
        for rp, sp in ((5, 3), (14, 3)):
            mn, mx = st.rolling(rp).min(), st.rolling(rp).max()
            rg = mx - mn
            val = pd.Series(np.where(rg > 0, 100 * (st - mn) / rg.replace(0, np.nan),
                                     100 * (st - mn)), index=c.index)
            out["ri_%d_%d" % (rp, sp)] = val.ewm(span=sp, min_periods=sp,
                                                 adjust=False).mean()
        return out

    a, b = _unrounded(d), _unrounded(d8)
    print()
    print("--- same forms, tti output rounding removed -------------------")
    print("%-20s %14s %14s  %s" % ("column", "max|x8 - x|", "max|x|", "scale-free?"))
    for k in a:
        s = pd.concat([a[k].rename("a"), b[k].rename("b")], axis=1)
        s = s.replace([np.inf, -np.inf], np.nan).dropna()
        dd = (s.a - s.b).abs().max()
        print("%-20s %14.6g %14.6g  %s"
              % (k, dd, s.a.abs().max(), "YES" if dd < 1e-9 else "NO"))

    print()
    print("--- faithfulness: transcription vs upstream tti, x1 -----------")
    print("(the unrounded column above is a TRANSCRIPTION, not an upstream")
    print(" call. If these are at tti's .round(4) floor of 5e-05 the")
    print(" transcription is faithful and the rescues are real.)")
    _pbu = tti_call(tti_ind.ProjectionBands, d)
    _o, _h, _l, _c = d.open, d.high, d.low, d.close
    P = 14
    x = np.arange(P, dtype=float)
    xm = x.mean()
    sxx = ((x - xm) ** 2).sum()

    def _sl(s_):
        return s_.rolling(P).apply(
            lambda y: ((x - xm) * (y - y.mean())).sum() / sxx, raw=True)

    hs, ls = _sl(_h).to_numpy(float), _sl(_l).to_numpy(float)
    hv, lv = _h.to_numpy(float), _l.to_numpy(float)
    ub = np.full(len(hv), np.nan)
    lb = np.full(len(hv), np.nan)
    jj = np.arange(1, P)
    for i in range(P - 1, len(hv)):
        if np.isnan(hs[i]):
            continue
        ub[i] = max(hv[i], float(np.max(jj * hs[i] + hv[i - jj])))
        lb[i] = min(lv[i], float(np.min(jj * ls[i] + lv[i - jj])))
    for lbl, mine, theirs in (
            ("ProjectionBands upper", pd.Series(ub, index=_c.index), _pbu["upper_band"]),
            ("ProjectionBands lower", pd.Series(lb, index=_c.index), _pbu["lower_band"])):
        t = pd.concat([mine.rename("a"), theirs.rename("b")], axis=1).dropna()
        print("  %-24s max|transcription - tti| %.6g  n=%d"
              % (lbl, (t.a - t.b).abs().max(), len(t)))
    trh = pd.concat([_c.shift(1), _h], axis=1).max(axis=1)
    trl = pd.concat([_c.shift(1), _l], axis=1).min(axis=1)
    dc = _c - _c.shift(1)
    w = pd.Series(0.0, index=_c.index)
    w[dc > 0] = (_c - trl)[dc > 0]
    w[dc < 0] = (_c - trh)[dc < 0]
    t = pd.concat([w.rename("a"),
                   tti_call(tti_ind.WilliamsAccumulationDistribution, d)["wad"].rename("b")],
                  axis=1).dropna()
    print("  %-24s max|transcription - tti| %.6g  n=%d"
          % ("WilliamsAD bar", (t.a - t.b).abs().max(), len(t)))
    a_ = (_h - _c.shift(1)).abs()
    b_ = (_l - _c.shift(1)).abs()
    ycyo = _c.shift(1) - _o.shift(1)
    num = (_c - _c.shift(1)) + 0.5 * (_c - _o) + 0.25 * ycyo
    K = pd.concat([a_, b_], axis=1).max(axis=1)
    R = pd.concat([a_, b_, _h - _l], axis=1).max(axis=1) + 0.25 * ycyo.abs()
    t = pd.concat([(50 * (num / R) * (K / 3)).clip(-100, 100).rename("a"),
                   tti_call(tti_ind.SwingIndex, d)["swi"].rename("b")], axis=1).dropna()
    print("  %-24s max|transcription - tti| %.6g  n=%d"
          % ("SwingIndex (as written)", (t.a - t.b).abs().max(), len(t)))
    tr = pd.concat([_h - _l, _h - _c.shift(1), _c.shift(1) - _l], axis=1).max(axis=1)
    st = pd.Series(np.where(_c > _c.shift(1), tr / (_c - _c.shift(1)), tr), index=_c.index)
    for rp, sp in ((5, 3), (14, 3)):
        mn, mx = st.rolling(rp).min(), st.rolling(rp).max()
        rg = mx - mn
        val = pd.Series(np.where(rg > 0, 100 * (st - mn) / rg.replace(0, np.nan),
                                 100 * (st - mn)), index=_c.index)
        mine = val.ewm(span=sp, min_periods=sp, adjust=False).mean()
        theirs = tti_call(tti_ind.RangeIndicator, d, range_period=rp,
                          smoothing_period=sp)["ri"]
        t = pd.concat([mine.rename("a"), theirs.rename("b")], axis=1).dropna()
        print("  %-24s max|transcription - tti| %.6g  n=%d"
              % ("RangeIndicator %d/%d" % (rp, sp), (t.a - t.b).abs().max(), len(t)))

    print()
    print("--- why swi_sf_derived fails x8 while swi_sf_direct does not ---")
    sw = tti_call(tti_ind.SwingIndex, d)["swi"]
    sw8 = tti_call(tti_ind.SwingIndex, d8)["swi"]
    print("  |swi| >= 100 (clamped): x1 %d bars, x8 %d bars of %d"
          % (int((sw.abs() >= 100).sum()), int((sw8.abs() >= 100).sum()),
             int(sw.notna().sum())))
    print("  -> the K/3 term is 8x larger at x8, so the +/-100 clamp bites and")
    print("     dividing K/3 back out cannot recover the pre-clamp value.")
    dv = _swi_sf_derived(d)
    di = _unrounded_direct_swi(d)
    t = pd.concat([dv.rename("a"), di.rename("b")], axis=1)
    t = t.replace([np.inf, -np.inf], np.nan).dropna()
    print("  max|direct - derived| on this frame: %.4f  (n=%d) -- two series,"
          % ((t.b - t.a).abs().max(), len(t)))
    print("  and Gate E judges the DIRECT one.")


def _unrounded_direct_swi(d):
    o, h, l, c = d.open, d.high, d.low, d.close
    a = (h - c.shift(1)).abs()
    b = (l - c.shift(1)).abs()
    ycyo = c.shift(1) - o.shift(1)
    num = (c - c.shift(1)) + 0.5 * (c - o) + 0.25 * ycyo
    R = pd.concat([a, b, h - l], axis=1).max(axis=1) + 0.25 * ycyo.abs()
    return 50 * (num / R)


if __name__ == "__main__":
    main()
    rounding_probe()
