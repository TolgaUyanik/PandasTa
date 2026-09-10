# -*- coding: utf-8 -*-
"""ALTPORT-2: the measurement behind `docs/AltportPortsMeasured.md`.

Gates A, C, D and the Gate-E carry-over for the three ALTPORT-1 survivors:
`cvi`, `bw_mfi` (Bill Williams' Market Facilitation Index) and `smc_sweep`.

What each stage actually does, and the trap it exists to avoid:

* **Gate A** calls the UPSTREAM package -- `pandas_ta_classic` for `cvi` and
  `smc_sweep`, Bill Williams' definition directly for `bw_mfi` -- and diffs the
  FORK implementation against it.  ALTPORT-0 round 1 produced three false
  identities by transcribing a candidate with fork helpers and comparing it to
  a fork column; that comparison has no failure mode.  Nothing here is a
  transcription: the left side is `pandas_ta.<fn>` as shipped, the right side
  is an upstream call.
  tti's contribution to `bw_mfi` is DECORATIVE.  tti returns
  `(high-low)/volume` and the shipped form multiplies volume back out, so tti
  contributes only `high - low`.  Gate A goes to Bill Williams' definition,
  with tti checked alongside for the record (its `.round(10)` sets a half-ulp
  floor).

* **Gate C** counts, on every usable daily parquet in the parent repo's cache,
  how many bars each shipped column is non-NaN and non-zero on, and for
  `smc_sweep` how many `+1` and `-1` events fire.

* **Gate D** is BIT-IDENTICAL (`== 0.0`, not a tolerance) at O/H/L/C x8 and
  x64.  ALTPORT-1 measured every tti-DERIVED column FAILING this because tti
  rounds to fixed decimals; the fork implementation does not round, so this
  must be re-run here and may not be inherited.

* **Gate E carry-over.** ALTPORT-1 measured Gate E on candidate series built
  from upstream calls (`C_CVI_10`, `C_MFI_BW_SF_20`, `C_SMC_SWEEP`).  Those
  numbers transfer to the ported columns only if the ported columns ARE those
  series.  Stage E diffs each shipped column against the screened form
  verbatim as `measure_altport1_overlap_full.py` builds it.  A max |diff| of
  0.0 is what licences the carry-over; anything else forces a re-measurement.

This script imports `pandas_ta` and `pandas_ta_classic` into ONE process, so
the `df.ta` accessor is registered twice under the same name.  Nothing here
goes through `df.ta` -- every call is `ta.<fn>(...)` / `tac.<fn>(...)` against
the module.  **Do NOT import this from the test suite**: doing so took the
suite to 109 failures once already.

tti reads its own version through `importlib.metadata` and raises when the
distribution is absent, so `version("tti")` is stubbed below, exactly as
`docs/gen_altport0_triage.py` does it.

Usage:  python docs/gen_altport2_ports.py
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

import pandas_ta as ta                                      # noqa: E402
import pandas_ta_classic as tac                             # noqa: E402
import tti.indicators as tti_ind                            # noqa: E402

# ALTPORT-0's named 12 -- fixed, not "whatever glob returned today".
TICKERS = [
    "AEFES_IS", "AGHOL_IS", "AHGAZ_IS", "AKBNK_IS", "AKCNS_IS", "AKFGY_IS",
    "AKFYE_IS", "AKSA_IS", "AKSEN_IS", "ALARK_IS", "ALBRK_IS", "ALFAS_IS",
]
SCALE_FRAME = "AEFES_IS"
MIN_BARS = 800

CVI_LEN = 10
MFI_LEN = 20
SMC_LEN, SMC_WICK = 15, 1.5


def _read(path):
    d = pd.read_parquet(path)
    d.columns = [str(c).lower() for c in d.columns]
    if not {"open", "high", "low", "close", "volume"}.issubset(d.columns):
        return None
    d = d[["open", "high", "low", "close", "volume"]].dropna()
    if len(d) < MIN_BARS:
        return None
    if not isinstance(d.index, pd.DatetimeIndex):
        d.index = pd.to_datetime(d.index)
    return d


def load_named():
    out = []
    for t in TICKERS:
        p = os.path.join(CACHE, f"{t}_1d.parquet")
        d = _read(p) if os.path.isfile(p) else None
        if d is None:
            print(f"  MISSING/UNUSABLE {t}")
            continue
        out.append((t, d))
    return out


def load_all_daily():
    files = sorted(glob.glob(os.path.join(CACHE, "*_1d.parquet")))
    out = []
    for p in files:
        try:
            d = _read(p)
        except Exception:
            d = None
        if d is not None:
            out.append((os.path.basename(p)[:-11], d))
    return len(files), out


# ------------------------------------------------------------ fork columns
def fork_columns(d):
    o, h, l, c, v = (d["open"], d["high"], d["low"], d["close"], d["volume"])
    return {
        f"CVI_{CVI_LEN}_{CVI_LEN}": ta.cvi(h, l, length=CVI_LEN),
        f"MFI_BW_SF_{MFI_LEN}": ta.bw_mfi(h, l, c, v, length=MFI_LEN),
        f"SMC_SWEEP_{SMC_LEN}_{SMC_WICK}": ta.smc_sweep(o, h, l, c,
                                                        length=SMC_LEN,
                                                        wick_mult=SMC_WICK),
    }


def _maxdiff(a, b):
    """max |a - b| over bars where BOTH are finite, plus the compared count
    and whether the NaN masks agree."""
    av = np.asarray(a, dtype=float)
    bv = np.asarray(b, dtype=float)
    fa, fb = np.isfinite(av), np.isfinite(bv)
    m = fa & fb
    n = int(m.sum())
    if n == 0:
        return float("nan"), 0, False
    d = float(np.abs(av[m] - bv[m]).max())
    return d, n, bool((fa == fb).all())


# ------------------------------------------------------------------ Gate A
def gate_a(frames):
    print("\n=== GATE A -- fork vs UPSTREAM ===", flush=True)
    keys = ("cvi", "cvi_warmup", "smc_sweep", "bw_mfi_raw_vs_billwilliams",
            "bw_mfi_raw_vs_tti")
    acc = {k: [0.0, 0, True] for k in keys}
    for t, d in frames:
        o, h, l, c, v = (d["open"], d["high"], d["low"], d["close"], d["volume"])

        # cvi: pandas_ta_classic/volatility/cvi.py
        f = ta.cvi(h, l, length=CVI_LEN)
        u = tac.cvi(h, l, length=CVI_LEN)
        dd, n, mm = _maxdiff(f, u)
        acc["cvi"][0] = max(acc["cvi"][0], dd)
        acc["cvi"][1] += n
        acc["cvi"][2] &= mm
        # the warm-up window on its own, so a head-only divergence cannot hide
        k = 2 * CVI_LEN + 5
        dd2, n2, _ = _maxdiff(f.iloc[:k], u.iloc[:k])
        acc["cvi_warmup"][0] = max(acc["cvi_warmup"][0], dd2)
        acc["cvi_warmup"][1] += n2

        # smc_sweep: pandas_ta_classic/momentum/smc_sweep.py
        f = ta.smc_sweep(o, h, l, c, length=SMC_LEN, wick_mult=SMC_WICK)
        u = tac.smc_sweep(o, h, l, c, length=SMC_LEN, wick_mult=SMC_WICK)
        dd, n, mm = _maxdiff(f, u)
        acc["smc_sweep"][0] = max(acc["smc_sweep"][0], dd)
        acc["smc_sweep"][1] += n
        acc["smc_sweep"][2] &= mm

        # bw_mfi raw vs Bill Williams' definition, from raw OHLCV
        f = ta.bw_mfi(h, l, c, v, length=MFI_LEN, raw=True)
        u = (h - l) / v
        dd, n, mm = _maxdiff(f, u)
        acc["bw_mfi_raw_vs_billwilliams"][0] = max(
            acc["bw_mfi_raw_vs_billwilliams"][0], dd)
        acc["bw_mfi_raw_vs_billwilliams"][1] += n
        acc["bw_mfi_raw_vs_billwilliams"][2] &= mm

        # ... and vs tti, for the record (its .round(10) is the floor)
        tin = pd.DataFrame({"high": h, "low": l, "close": c, "volume": v})
        u = tti_ind.MarketFacilitationIndex(
            input_data=tin, fill_missing_values=False).getTiData()["mfi"]
        dd, n, _ = _maxdiff(f, u)
        acc["bw_mfi_raw_vs_tti"][0] = max(acc["bw_mfi_raw_vs_tti"][0], dd)
        acc["bw_mfi_raw_vs_tti"][1] += n

    for k in keys:
        dd, n, mm = acc[k]
        print(f"  {k:28s} max|diff| = {dd:.6g}   n = {n}   "
              f"nan-masks-match = {mm}")
    return acc


# ------------------------------------------------------------------ Gate C
def gate_c():
    print("\n=== GATE C -- reachability on the real cache ===", flush=True)
    n_files, frames = load_all_daily()
    print(f"  {n_files} *_1d.parquet in cache; {len(frames)} usable "
          f"(OHLCV, >= {MIN_BARS} bars)")
    tot = {}
    fired = {}
    bars = 0
    smc_pos = smc_neg = 0
    for t, d in frames:
        bars += len(d)
        cols = fork_columns(d)
        for name, s in cols.items():
            a = s.to_numpy(dtype=float)
            fin = np.isfinite(a)
            nn = int(fin.sum())
            nz = int((fin & (a != 0)).sum())
            e = tot.setdefault(name, [0, 0])
            e[0] += nn
            e[1] += nz
            fired[name] = fired.get(name, 0) + (1 if nz > 0 else 0)
        s = cols[f"SMC_SWEEP_{SMC_LEN}_{SMC_WICK}"].to_numpy(dtype=float)
        smc_pos += int((s == 1).sum())
        smc_neg += int((s == -1).sum())
    print(f"  pooled bars = {bars}")
    for name in sorted(tot):
        nn, nz = tot[name]
        print(f"  {name:22s} non-NaN {nn:>8}  non-zero {nz:>8}  "
              f"frames firing {fired[name]}/{len(frames)}")
    print(f"  SMC_SWEEP signs: +1 = {smc_pos}   -1 = {smc_neg}   "
          f"density = {100.0 * (smc_pos + smc_neg) / bars:.4f}%")
    return n_files, len(frames), bars, tot, fired, smc_pos, smc_neg


# ------------------------------------------------------------------ Gate D
def gate_d(frames):
    print("\n=== GATE D -- bit-identical under price scaling ===", flush=True)
    rows = []
    for mult in (8, 64):
        worst = {}
        for t, d in frames:
            base = fork_columns(d)
            sd = d.copy()
            sd[["open", "high", "low", "close"]] *= mult
            scaled = fork_columns(sd)
            for name in base:
                a = base[name].to_numpy(float)
                b = scaled[name].to_numpy(float)
                fa, fb = np.isfinite(a), np.isfinite(b)
                m = fa & fb
                dd = float(np.abs(a[m] - b[m]).max()) if m.any() else float("nan")
                e = worst.setdefault(name, [0.0, True, 0])
                e[0] = max(e[0], dd)
                e[1] &= bool((fa == fb).all())
                e[2] += int(m.sum())
        for name in sorted(worst):
            dd, masks, n = worst[name]
            rows.append((name, mult, dd, masks, n))
            print(f"  x{mult:<3d} {name:22s} max|delta| = {dd!r:8s} "
                  f"bit-identical = {dd == 0.0}  nan-masks-match = {masks}  "
                  f"n = {n}")
    # volume scaling, bw_mfi only -- the relative-volume ratio must cancel
    worst_v = 0.0
    nv = 0
    for t, d in frames:
        base = fork_columns(d)[f"MFI_BW_SF_{MFI_LEN}"].to_numpy(float)
        sd = d.copy()
        sd["volume"] = sd["volume"] * 8
        sc = fork_columns(sd)[f"MFI_BW_SF_{MFI_LEN}"].to_numpy(float)
        m = np.isfinite(base) & np.isfinite(sc)
        worst_v = max(worst_v, float(np.abs(base[m] - sc[m]).max()))
        nv += int(m.sum())
    print(f"  vol x8  MFI_BW_SF_{MFI_LEN}   max|delta| = {worst_v!r}  "
          f"bit-identical = {worst_v == 0.0}   n = {nv}")
    return rows, worst_v, nv


# ------------------------------------------------------------------ Gate E
def gate_e_carryover(frames):
    """Is the shipped column the SERIES ALTPORT-1 screened?  If yes the
    measured rho transfers; if no, Gate E must be re-run."""
    print("\n=== GATE E carry-over -- shipped column vs the screened form ===",
          flush=True)
    acc = {"CVI_10_10": [0.0, 0], "MFI_BW_SF_20": [0.0, 0],
           "SMC_SWEEP_15_1.5": [0.0, 0]}
    for t, d in frames:
        o, h, l, c, v = (d["open"], d["high"], d["low"], d["close"], d["volume"])

        dd, n, _ = _maxdiff(ta.cvi(h, l, length=CVI_LEN),
                            tac.cvi(h, l, length=CVI_LEN))
        acc["CVI_10_10"][0] = max(acc["CVI_10_10"][0], dd)
        acc["CVI_10_10"][1] += n

        # measure_altport1_overlap_full.py:329-333, verbatim
        tin = pd.DataFrame({"high": h, "low": l, "close": c, "volume": v})
        mfi = tti_ind.MarketFacilitationIndex(
            input_data=tin, fill_missing_values=False).getTiData()["mfi"]
        screened = (mfi * v / c) / (v / v.rolling(MFI_LEN).mean())
        dd, n, _ = _maxdiff(ta.bw_mfi(h, l, c, v, length=MFI_LEN), screened)
        acc["MFI_BW_SF_20"][0] = max(acc["MFI_BW_SF_20"][0], dd)
        acc["MFI_BW_SF_20"][1] += n

        dd, n, _ = _maxdiff(ta.smc_sweep(o, h, l, c),
                            tac.smc_sweep(o, h, l, c))
        acc["SMC_SWEEP_15_1.5"][0] = max(acc["SMC_SWEEP_15_1.5"][0], dd)
        acc["SMC_SWEEP_15_1.5"][1] += n

    for k in acc:
        dd, n = acc[k]
        print(f"  {k:18s} max|shipped - screened| = {dd:.6g}   n = {n}")
    return acc


if __name__ == "__main__":
    named = load_named()
    print(f"Gate A/D/E frames: {len(named)} tickers, "
          f"{sum(len(d) for _, d in named)} bars")
    gate_a(named)
    gate_e_carryover(named)
    gate_d([(t, d) for t, d in named if t == SCALE_FRAME] or named[:1])
    gate_c()
