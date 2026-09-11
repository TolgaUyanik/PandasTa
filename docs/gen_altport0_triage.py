# -*- coding: utf-8 -*-
"""ALTPORT-0: the measurement behind `docs/AltportTriage.md`.

Triage of the 20 `verdict == "port"` rows of `../AlternativeRepos/
altrepo_pandas_ta_classic.csv` (11) and `../AlternativeRepos/altrepo_tti.csv`
(9): for each, is it worth BUILDING, given that the scanners already
established it is not a rename of something shipped.

**The defect this file exists to prevent.** Round 1 of the triage was written
against hand transcriptions of the candidates, computed with FORK helpers
(`ta.linreg`, `ta.rma`, `ta.ema`) and then compared to FORK columns. Three
"identity" numbers came out of that and all three were wrong:

    row  claimed                              actual (upstream package)
    9    fosc == cfo, max abs diff 0.0        max abs diff 9.8601, rho 0.967784
    10   dx   == 100|DMP-DMN|/(DMP+DMN),      max abs diff 24.931, 7.4% of bars
         max abs diff 7.1e-14                 over 1e-9, rho 0.998721
    2    VolatilityChaikins == cvi, diff 0.0  max abs diff 6.3675 (AEFES),
                                              rho 0.999955

A fork transcription compared against a fork column cannot fail. So this
script calls the UPSTREAM packages -- `pandas_ta_classic` and `tti` -- and
compares those to the fork. Only the scale-free FORMS a port would ship in are
hand-written here, and each is derived from the upstream output, never from a
re-implementation of it.

Three real divergences the round-1 transcription hid, all of them Gate A
material:

* `pandas_ta.linreg` runs x = 1..n; `pandas_ta_classic.linreg` runs
  x = 0..n-1. So `pandas_ta.linreg(tsf=True)` == `classic.linreg(tsf=False)`
  and classic's TSF projects one slope-step further, so classic's forecast is
  the LARGER by one slope step and the oscillator is correspondingly smaller:
  ``fosc = cfo - 100*slope/close`` (measured max residual 3.5e-13 over 51,866
  bars). Not a rename -- a different forecast point.
* classic's `ma("rma")` seeds Wilder smoothing with an SMA at bar `length`;
  the fork's `ta.rma` does not. That is the whole of the `dx` gap.
* tti's `VolatilityChaikins` uses `ewm(adjust=False)` seeded at bar 1 and then
  `.round(4)`; classic's `ema` seeds with an SMA. The `.round(4)` alone makes
  "diff exactly 0.0" impossible on its face.

⚠ This script imports `pandas_ta_classic` and `pandas_ta` into ONE process, so
the `df.ta` accessor is registered twice under the same name and whichever
package registers last wins. That is why nothing here goes through `df.ta` --
every call is `ta.<fn>(...)` or `tac.<fn>(...)` against the module. Do NOT
import this from the test suite; `docs/gen_altrepo_pandas_ta_classic.py`
carries the same constraint and the same reason.

⚠ tti reads its own version through `importlib.metadata` and raises when the
distribution is absent, so `version("tti")` is stubbed below, exactly as
`docs/gen_altrepo_tti.py` does it.

Data: BIST daily parquet from the parent repo's cache. The frame is the first
12 `*_1d.parquet` files carrying OHLCV with >= 800 rows, which is a fixed,
named list (see `TICKERS`) so the numbers are reproducible.

Usage:  python docs/gen_altport0_triage.py
"""
import glob
import importlib.metadata as _md
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
CLASSIC = os.path.join(SIBLING, "pandas-ta-classic")
TTI = os.path.join(SIBLING, "trading-technical-indicators")
CACHE = os.path.join(os.path.dirname(FORK), "Backtesting", "datastore", "cache")

for _p, _n in ((CLASSIC, "pandas-ta-classic"), (TTI, "trading-technical-indicators")):
    if not os.path.isdir(_p):
        sys.exit(f"{_n} not found at {_p}")

_real_version = _md.version
_md.version = lambda name: ("0.0.0-local" if name == "tti" else _real_version(name))

sys.path.insert(0, CLASSIC)
sys.path.insert(0, TTI)
sys.path.insert(0, FORK)

import numpy as np                                          # noqa: E402
import pandas as pd                                         # noqa: E402
from scipy.stats import spearmanr                           # noqa: E402

import pandas_ta as ta                                      # noqa: E402
import pandas_ta_classic as tac                             # noqa: E402
import tti.indicators as tti_ind                            # noqa: E402

# The 12 frames, named so the sample is not "whatever glob returned today".
TICKERS = [
    "AEFES_IS", "AGHOL_IS", "AHGAZ_IS", "AKBNK_IS", "AKCNS_IS", "AKFGY_IS",
    "AKFYE_IS", "AKSA_IS", "AKSEN_IS", "ALARK_IS", "ALBRK_IS", "ALFAS_IS",
]
SCALE_FRAME = "AEFES_IS"        # the single frame the x8 checks run on
MIN_BARS = 800


# ----------------------------------------------------------------- data ---
def load_frames():
    out = []
    for t in TICKERS:
        p = os.path.join(CACHE, f"{t}_1d.parquet")
        if not os.path.isfile(p):
            print(f"  MISSING {p}")
            continue
        d = pd.read_parquet(p)
        d.columns = [str(c).lower() for c in d.columns]
        if not {"open", "high", "low", "close", "volume"}.issubset(d.columns):
            print(f"  NO OHLCV {t}")
            continue
        d = d[["open", "high", "low", "close", "volume"]].dropna()
        if len(d) < MIN_BARS:
            print(f"  SHORT {t} ({len(d)})")
            continue
        if not isinstance(d.index, pd.DatetimeIndex):
            d.index = pd.to_datetime(d.index)
        out.append((t, d))
    return out


def _resolve_tickers():
    """Recover the 12 names from the glob, for the docstring's audit trail."""
    names = []
    for p in sorted(glob.glob(os.path.join(CACHE, "*_1d.parquet"))):
        d = pd.read_parquet(p)
        d.columns = [str(c).lower() for c in d.columns]
        if not {"open", "high", "low", "close", "volume"}.issubset(d.columns):
            continue
        if len(d[["open", "high", "low", "close", "volume"]].dropna()) < MIN_BARS:
            continue
        names.append(os.path.basename(p)[: -len("_1d.parquet")])
        if len(names) == 12:
            break
    return names


# ------------------------------------------------------------- upstream ---
def tti_call(cls, d, **kw):
    """Construct a tti indicator and read it back. `fill_missing_values` is
    turned OFF: the default forward-fills the INPUT, which would silently
    change the frame the fork side is measured on."""
    return cls(input_data=d[["open", "high", "low", "close", "volume"]].copy(),
               fill_missing_values=False, **kw).getTiData()


def candidates(d, with_tti=True):
    """Every candidate, from the UPSTREAM package, plus the fork columns each
    is judged against. Scale-free FORMS are derived from upstream output."""
    o, h, l, c, v = d.open, d.high, d.low, d.close, d.volume
    out = {}

    # --- classic, called upstream ------------------------------------
    out["fosc_14"] = tac.fosc(c, length=14)
    out["hvol_20"] = tac.hvol(c, length=20)
    out["avolume_20"] = tac.avolume(c, length=20)
    out["cvi_10"] = tac.cvi(h, l, length=10)
    out["dx_14"] = tac.dx(h, l, c, length=14)
    _adxr = tac.adxr(h, l, c, length=14)
    out["adxr_14"] = _adxr.iloc[:, 0] if isinstance(_adxr, pd.DataFrame) else _adxr
    out["vosc_12_26"] = tac.vosc(v, fast=12, slow=26)
    _msw = tac.msw(c, period=5)
    out["msw_sine_5"] = _msw.iloc[:, 0]
    out["msw_lead_5"] = _msw.iloc[:, 1]
    _ce = tac.ce(h, l, c, length=22, multiplier=3)
    out["ce_long_dist_pct"] = (c - _ce.iloc[:, 0]) / c * 100
    out["smc_sweep"] = tac.smc_sweep(o, h, l, c)

    # --- tti, called upstream ----------------------------------------
    if with_tti:
        _env = tti_call(tti_ind.Envelopes, d)               # period=20, shift=0.10
        out["env_up_dist_pct"] = (c - _env["upper_band"]) / c * 100
        out["mfi_bw"] = tti_call(tti_ind.MarketFacilitationIndex, d)["mfi"]
        # scale-free form: upstream MFI_BW = (h-l)/v; multiply back by v/c to
        # get range-as-%-of-price, then divide by relative volume.
        out["mfi_bw_sf"] = (out["mfi_bw"] * v / c) / (v / v.rolling(20).mean())
        _pb = tti_call(tti_ind.ProjectionBands, d)          # period=14
        out["pb_width_pct"] = (_pb["upper_band"] - _pb["lower_band"]) / c * 100
        out["pb_up_dist_pct"] = (_pb["upper_band"] - c) / c * 100
        out["pb_lo_dist_pct"] = (c - _pb["lower_band"]) / c * 100
        out["posc_14"] = tti_call(tti_ind.ProjectionOscillator, d)["posc"]
        out["rmi_8_4"] = tti_call(tti_ind.RelativeMomentumIndex, d)["rmi"]
        _swi = tti_call(tti_ind.SwingIndex, d)["swi"]
        out["swi_tti"] = _swi
        out["ri_5_3"] = tti_call(tti_ind.RangeIndicator, d)["ri"]
        out["ri_14_3"] = tti_call(tti_ind.RangeIndicator, d, range_period=14,
                                  smoothing_period=3)["ri"]
        out["vch_tti"] = tti_call(tti_ind.VolatilityChaikins, d)["vch"]
        _wad = tti_call(tti_ind.WilliamsAccumulationDistribution, d)["wad"]
        out["wad_bar"] = _wad
        out["wad_bar_sf"] = _wad / ta.true_range(h, l, c)

        # SwingIndex scale-free repair, TWO series that must never share a
        # name (round-2 defect: they did, across two scripts, and a rho
        # measured on one was reported for the other -- pooled max
        # |direct - derived| = 53.23):
        #   _derived: tti's CLAMPED, ROUNDED output with K/3 divided back out.
        #             Not recoverable where the +/-100 clamp bit.
        #   _direct:  50*(num/R) computed from the frame. This is the form a
        #             port would ship, so this is the one Gate E judges.
        a = (h - c.shift(1)).abs()
        b = (l - c.shift(1)).abs()
        K = pd.concat([a, b], axis=1).max(axis=1)
        out["swi_sf_derived"] = _swi / (K / 3.0)
        ycyo = c.shift(1) - o.shift(1)
        _num = (c - c.shift(1)) + 0.5 * (c - o) + 0.25 * ycyo
        _R = pd.concat([a, b, h - l], axis=1).max(axis=1) + 0.25 * ycyo.abs()
        out["swi_sf_direct"] = 50 * (_num / _R)

    # --- fork reference columns --------------------------------------
    out["_CFO_9"] = ta.cfo(c, length=9)
    out["_CFO_14"] = ta.cfo(c, length=14)
    out["_LINREG_SLOPE_14"] = ta.linreg(c, length=14, slope=True)
    _adx = ta.adx(h, l, c, length=14)
    out["_ADX_14"] = _adx["ADX_14"]
    out["_dx_from_shipped"] = (100 * (_adx["DMP_14"] - _adx["DMN_14"]).abs()
                               / (_adx["DMP_14"] + _adx["DMN_14"]))
    out["_NATR_14"] = ta.natr(h, l, c, length=14)
    out["_HARPARK"] = ta.har_park(h, l, c)
    out["_MASSI"] = ta.massi(h, l)
    out["_CHOP_14"] = ta.chop(h, l, c, length=14)
    out["_PVO"] = ta.pvo(v)["PVO_12_26_9"]
    out["_WILLR_14"] = ta.willr(h, l, c, length=14)
    out["_STOCHk"] = ta.stoch(h, l, c)["STOCHk_14_3_3"]
    out["_RSI_14"] = ta.rsi(c, length=14)
    out["_BOP"] = ta.bop(o, h, l, c)
    out["_ER_10"] = ta.er(c, length=10)
    out["_ADo"] = ta.ad(h, l, c, v)
    out["_EOM"] = ta.eom(h, l, c, v)
    out["_CMF"] = ta.cmf(o, h, l, c, v)
    out["_PVR"] = ta.pvr(c, v)
    out["_TR"] = ta.true_range(h, l, c)
    out["_QS_sf"] = ta.qstick(o, c, length=10) / c
    out["_BIAS_SMA_20"] = ta.bias(c, length=20)
    _hts = ta.ht_sine(c)
    for cn in _hts.columns:
        out["_" + cn] = _hts[cn]
    out["_EBSW"] = ta.ebsw(c)
    out["_CKSPl_dist_pct"] = (c - ta.cksp(h, l, c).iloc[:, 0]) / c * 100
    out["_SUPERT_dist_pct"] = (c - ta.supertrend(h, l, c).iloc[:, 0]) / c * 100
    # The engine's REAL Donchian family. `indicator_engine.py:1278-1329` emits
    # dist_low_{5,20,21,60,63,252} and dist_from_high_{5,20,21,60,63,252}; the
    # comment at :1367 says Donchian "deliberately gets NOTHING - its causal
    # form already ships as dist_low_20 / dist_from_high_20". Round 2 grepped
    # for DCU/DCL, found none, and wrote that no donchian-derived column
    # exists. It does, twelve times over, and it is the Gate E adversary for
    # ProjectionBands / ProjectionOscillator. Precedent for what happens next:
    # :1373-1396 records the engine BUILDING, MEASURING and DELETING
    # dist_to_bb_upper_pct / dist_to_bb_lower_pct at r 0.9429 / 0.9379 against
    # exactly these columns.
    eps = 1e-12
    for n in (5, 14, 20):
        rl = l.shift(1).rolling(n, min_periods=max(1, n // 2)).min()
        rh = h.shift(1).rolling(n, min_periods=max(1, n // 2)).max()
        out[f"_dist_low_{n}"] = ((c - rl) / c.clip(lower=eps)).clip(lower=0.0)
        out[f"_dist_from_high_{n}"] = ((c - rh) / c.clip(lower=eps)).clip(upper=0.0)
        # the engine's implied channel width and in-channel position
        out[f"_eng_width_{n}"] = out[f"_dist_low_{n}"] - out[f"_dist_from_high_{n}"]
        out[f"_eng_pos_{n}"] = (out[f"_dist_low_{n}"]
                                / (out[f"_eng_width_{n}"] + eps) * 100)
    _dcu, _dcl = h.rolling(14).max(), l.rolling(14).min()
    out["_donch_width_pct"] = (_dcu - _dcl) / c * 100
    out["_donch_pos"] = 100 * (c - _dcl) / (_dcu - _dcl)

    # liquidity_sweep, for the smc_sweep coincidence test
    _lsh = ta.liquidity_sweep(h, l, c)
    out["_LSH_SWEEP_BULL"] = _lsh.filter(like="SWEEP_BULL").iloc[:, 0]
    out["_LSH_SWEEP_BEAR"] = _lsh.filter(like="SWEEP_BEAR").iloc[:, 0]

    return pd.DataFrame({k: pd.Series(vv, index=c.index) for k, vv in out.items()})


PAIRS = [
    ("fosc_14", "_CFO_14"), ("fosc_14", "_CFO_9"),
    ("avolume_20", "hvol_20"), ("hvol_20", "_NATR_14"), ("hvol_20", "_HARPARK"),
    ("cvi_10", "vch_tti"), ("cvi_10", "_NATR_14"), ("cvi_10", "_MASSI"),
    ("cvi_10", "_CHOP_14"),
    ("dx_14", "_dx_from_shipped"), ("dx_14", "_ADX_14"), ("adxr_14", "_ADX_14"),
    ("vosc_12_26", "_PVO"),
    ("msw_sine_5", "_HT_SINE"), ("msw_sine_5", "_HT_LEADSINE"),
    ("msw_lead_5", "_HT_SINE"), ("msw_sine_5", "_EBSW"),
    ("ce_long_dist_pct", "_CKSPl_dist_pct"), ("ce_long_dist_pct", "_SUPERT_dist_pct"),
    ("env_up_dist_pct", "_BIAS_SMA_20"),
    ("mfi_bw", "_EOM"), ("mfi_bw_sf", "_NATR_14"), ("mfi_bw_sf", "_EOM"),
    ("mfi_bw_sf", "_CMF"), ("mfi_bw_sf", "_PVR"),
    ("pb_width_pct", "_donch_width_pct"), ("pb_up_dist_pct", "_donch_width_pct"),
    # against the engine's REAL production Donchian family
    ("pb_width_pct", "_eng_width_5"), ("pb_width_pct", "_eng_width_14"),
    ("pb_width_pct", "_eng_width_20"),
    ("pb_up_dist_pct", "_dist_from_high_5"), ("pb_up_dist_pct", "_dist_from_high_14"),
    ("pb_lo_dist_pct", "_dist_low_14"), ("pb_lo_dist_pct", "_dist_low_20"),
    ("posc_14", "_WILLR_14"), ("posc_14", "_STOCHk"), ("posc_14", "_donch_pos"),
    ("posc_14", "_eng_pos_14"),
    ("rmi_8_4", "_RSI_14"),
    ("swi_tti", "_BOP"), ("swi_sf_direct", "_BOP"), ("swi_sf_derived", "_BOP"),
    ("swi_sf_direct", "_QS_sf"),
    ("ri_5_3", "_ER_10"), ("ri_5_3", "_CHOP_14"), ("ri_5_3", "_NATR_14"),
    ("wad_bar_sf", "_BOP"), ("wad_bar_sf", "_ADo"), ("wad_bar_sf", "_TR"),
]


def rho(big, a, b):
    s = big[[a, b]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 100:
        return None, len(s)
    return float(spearmanr(s[a], s[b]).statistic), len(s)


def diff(big, a, b):
    s = big[[a, b]].replace([np.inf, -np.inf], np.nan).dropna()
    d = (s[a] - s[b]).abs()
    return float(d.max()), int((d > 1e-9).sum()), len(s)


def main():
    frames = load_frames()
    resolved = _resolve_tickers()
    print(f"glob-resolved first 12: {resolved}")
    # A printed MISSING line is not a guard. Round 2 shipped a wrong TICKERS
    # list, loaded 4 of 12 frames, exited 0 and produced a complete, plausible
    # rho table on the wrong sample. Fail loudly instead.
    loaded = [n for n, _ in frames]
    if loaded != TICKERS or resolved != TICKERS:
        sys.exit("ticker list drifted: TICKERS=%s loaded=%s resolved=%s"
                 % (TICKERS, loaded, resolved))
    print(f"frames: {len(frames)}  bars: {sum(len(d) for _, d in frames)}")

    big = pd.concat([candidates(d) for _, d in frames], axis=0, ignore_index=True)
    print(f"pooled rows: {len(big)}\n")

    print("%-22s %-22s %10s %9s" % ("candidate (upstream)", "vs", "spearman", "n"))
    for a, b in PAIRS:
        if a not in big or b not in big:
            print("MISSING", a, b)
            continue
        r, n = rho(big, a, b)
        print("%-22s %-22s %10s %9d"
              % (a, b, "n/a" if r is None else f"{r:.6f}", n))

    print("\n--- identity checks, UPSTREAM vs FORK -------------------------")
    for a, b in [("fosc_14", "_CFO_14"), ("dx_14", "_dx_from_shipped"),
                 ("cvi_10", "vch_tti")]:
        m, over, n = diff(big, a, b)
        print("%-22s vs %-22s max|d| %12.6g   bars>1e-9 %6d / %d"
              % (a, b, m, over, n))
    print()
    print("--- cvi vs VolatilityChaikins: warm-up transient? ---")
    for name, d in frames:
        cc = candidates(d)
        t = cc[["cvi_10", "vch_tti"]].replace([np.inf, -np.inf], np.nan)
        dd = (t.cvi_10 - t.vch_tti).abs().reset_index(drop=True)
        pos = int(dd.idxmax())
        tail = dd.iloc[100:]
        print("  %-10s max|d| %10.4f at row %4d   max|d| after row 100: %.3e"
              % (name, dd.max(), pos, tail.max()))

    s = big[["avolume_20", "hvol_20"]].replace([np.inf, -np.inf], np.nan).dropna()
    q = (s.avolume_20 / s.hvol_20)
    print("avolume/hvol ratio: min %.12f max %.12f  sqrt(19/20)/100 = %.12f  n=%d"
          % (q.min(), q.max(), np.sqrt(19 / 20) / 100, len(q)))
    for name, d in frames:
        if name == SCALE_FRAME:
            cc = candidates(d)
            for a, b in [("cvi_10", "vch_tti"), ("dx_14", "_dx_from_shipped"),
                         ("fosc_14", "_CFO_14")]:
                t = cc[[a, b]].replace([np.inf, -np.inf], np.nan).dropna()
                dd = (t[a] - t[b]).abs()
                print("  %s only: %-14s vs %-18s max|d| %10.6g  bars>1e-9 %5d / %d"
                      % (name, a, b, dd.max(), int((dd > 1e-9).sum()), len(t)))

    # fosc == cfo + 100*slope/close  (the x-origin difference)
    s = big[["fosc_14", "_CFO_14", "_LINREG_SLOPE_14"]].dropna()
    # slope/close needs close; recompute per frame instead
    resid = []
    for _, d in frames:
        cc = candidates(d, with_tti=False)
        r = cc["fosc_14"] - (cc["_CFO_14"] - 100 * cc["_LINREG_SLOPE_14"] / d.close)
        resid.append(r)
    r = pd.concat(resid).dropna()
    print("fosc - (cfo - 100*slope/close): max|resid| %.6g over %d bars"
          % (r.abs().max(), len(r)))
    # and the linreg x-origin claim itself
    d0 = frames[0][1]
    lf = ta.linreg(d0.close, length=14, tsf=True)
    lc = tac.linreg(d0.close, length=14, tsf=False)
    t = pd.concat([lf, lc], axis=1).dropna()
    print("fork linreg(tsf=True) vs classic linreg(tsf=False) on %s: max|d| %.6g n=%d"
          % (frames[0][0], (t.iloc[:, 0] - t.iloc[:, 1]).abs().max(), len(t)))

    print("\n--- Envelopes: monotone, not affine ---------------------------")
    s = big[["env_up_dist_pct", "_BIAS_SMA_20"]].replace([np.inf, -np.inf], np.nan).dropna()
    print("std(env_dist - 100*bias) = %.4f  (0 would mean an affine shift)"
          % (s.env_up_dist_pct - 100 * s._BIAS_SMA_20).std())

    print("\n--- SwingIndex clamp rate -------------------------------------")
    sw = big["swi_tti"].replace([np.inf, -np.inf], np.nan).dropna()
    print("pooled |swi| >= 100: %.4f%%  (n=%d)" % (100 * (sw.abs() >= 100).mean(), len(sw)))
    for name, d in frames:
        if name == SCALE_FRAME:
            one = candidates(d)["swi_tti"].dropna()
            print("%s: max|swi| = %.4f, clamp rate %.4f%%"
                  % (name, one.abs().max(), 100 * (one.abs() >= 100).mean()))

    print("\n--- posc out of [0,100] ---------------------------------------")
    po = big["posc_14"].replace([np.inf, -np.inf], np.nan).dropna()
    print("%.4f%% of %d bars" % (100 * ((po < 0) | (po > 100)).mean(), len(po)))

    print("\n--- smc_sweep vs liquidity_sweep, +/-1 bar coincidence --------")
    tot_s = tot_hit = tot_l = tot_lhit = 0
    for _, d in frames:
        cc = candidates(d, with_tti=False)
        smc = cc["smc_sweep"].fillna(0)
        lsh = (cc["_LSH_SWEEP_BULL"].fillna(0) + cc["_LSH_SWEEP_BEAR"].fillna(0)) > 0
        w = lsh | lsh.shift(1, fill_value=False) | lsh.shift(-1, fill_value=False)
        sm = smc != 0
        smw = sm | sm.shift(1, fill_value=False) | sm.shift(-1, fill_value=False)
        tot_s += int(sm.sum())
        tot_hit += int((sm & w).sum())
        tot_l += int(lsh.sum())
        tot_lhit += int((lsh & smw).sum())
    print("smc_sweep events: %d, within +/-1 bar of an LSH sweep: %d (%.1f%%)"
          % (tot_s, tot_hit, 100 * tot_hit / max(tot_s, 1)))
    print("LSH sweep events: %d, within +/-1 bar of an smc_sweep: %d (%.1f%%)"
          % (tot_l, tot_lhit, 100 * tot_lhit / max(tot_l, 1)))

    print("\n--- the scanners' own probe frame -----------------------------")
    rng = np.random.default_rng(7)
    n = 260
    cl = 100 + np.cumsum(rng.normal(0, 1.0, n))
    hi = cl + rng.uniform(0.1, 1.5, n)
    lo = cl - rng.uniform(0.1, 1.5, n)
    op = lo + (hi - lo) * rng.uniform(0, 1, n)
    vo = rng.integers(1_000, 100_000, n).astype(float)
    pf = pd.DataFrame({"open": op, "high": hi, "low": lo, "close": cl, "volume": vo},
                      index=pd.date_range("2020-01-01", periods=n, freq="D"))
    for L in (9, 14):
        f = tac.fosc(pf.close, length=L)
        g = ta.cfo(pf.close, length=L)
        s = pd.concat([f, g], axis=1).dropna()
        print("probe frame: fosc_%d vs CFO_%d  rho %.6f  max|d| %.4f  n=%d"
              % (L, L, spearmanr(s.iloc[:, 0], s.iloc[:, 1]).statistic,
                 (s.iloc[:, 0] - s.iloc[:, 1]).abs().max(), len(s)))
    f = tac.fosc(pf.close)          # default 14
    g = ta.cfo(pf.close)            # default 9
    s = pd.concat([f, g], axis=1).dropna()
    print("probe frame: fosc(default 14) vs cfo(default 9)  rho %.6f  n=%d"
          % (spearmanr(s.iloc[:, 0], s.iloc[:, 1]).statistic, len(s)))


if __name__ == "__main__":
    main()
