# -*- coding: utf-8 -*-
"""Print every number quoted in docs/RangeVolMeasured.md: Gate C (synthetic)
fire/range/distinct counts, Gate D scale tolerances, the clip-engagement
check, the open-quality (issue #14) disclosure for `yang_zhang`, and a proxy
overlap against `natr` / `har_park` -- the issue's own pre-registered guess
to beat (rho >= 0.9).

    python docs/measure_rangevol.py

Synthetic walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set and the 89 real BIST frames (run by the
launcher after this session; see docs/RangeVolMeasured.md, Gate E).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def ohlc(n=1200, seed=11, sigma=0.012, overnight_sigma=0.004, spread_sigma=0.004, tick=0.01, p_flat_open=0.0):
    rng = np.random.default_rng(seed)
    overnight = rng.normal(0.0, overnight_sigma, n)
    overnight[rng.random(n) < p_flat_open] = 0.0
    intraday = rng.normal(0.0, sigma, n)
    open_ = np.empty(n)
    close = np.empty(n)
    cur = 100.0
    for t in range(n):
        o = cur * np.exp(overnight[t])
        c = o * np.exp(intraday[t])
        open_[t], close[t] = o, c
        cur = c
    wick = np.maximum(open_, close) * np.abs(rng.normal(0.0, spread_sigma, n))
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    if tick:
        open_ = np.round(open_ / tick) * tick
        close = np.round(close / tick) * tick
        high = np.maximum(np.round(high / tick) * tick, np.maximum(open_, close))
        low = np.minimum(np.round(low / tick) * tick, np.minimum(open_, close))
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return (pd.Series(open_, index=idx), pd.Series(high, index=idx),
            pd.Series(low, index=idx), pd.Series(close, index=idx))


def rho(a, b):
    m = a.notna() & b.notna()
    if m.sum() < 20:
        return None
    return round(a[m].corr(b[m], method="spearman"), 4)


def _report_scale(name, base, scaled_by):
    for k, out in scaled_by.items():
        m = base.notna() & out.notna()
        nan_match = bool((base.isna() == out.isna()).all())
        maxdiff = float((base[m] - out[m]).abs().max()) if m.any() else float("nan")
        print(f"  {name} x{k}: nan masks match={nan_match} max|diff|={maxdiff:.3e}")


def measure(name, fn):
    print(f"\n== {name}, n=1200 seed=11")
    open_, high, low, close = ohlc()
    out = fn(open_, high, low, close)
    print("  fires (non-NaN):", int(out.notna().sum()), "/", len(out))
    print("  range:", float(out.dropna().min()), float(out.dropna().max()))
    print("  distinct values:", out.dropna().nunique())
    scaled = {k: fn(open_ * k, high * k, low * k, close * k) for k in (8.0, 64.0, 10.0, 3.7)}
    _report_scale(name, out, scaled)
    return out


def measure_clip_engagement():
    print("\n== clip engagement (float-safety only; expected 0 on valid data)")
    open_, high, low, close = ohlc()
    o, h, l, c = open_.values, high.values, low.values, close.values
    ln2 = np.log(2.0)
    gk_terms = 0.5 * np.log(h / l) ** 2 - (2 * ln2 - 1) * np.log(c / o) ** 2
    rs_terms = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    print("  GKVOL per-bar term min:", float(gk_terms.min()), "(negative count:", int((gk_terms < 0).sum()), ")")
    print("  RSVOL per-bar term min:", float(rs_terms.min()), "(negative count:", int((rs_terms < 0).sum()), ")")


def measure_open_quality():
    print("\n== open-quality (issue #14), yang_zhang, n=1200 seed=11, length=20")
    for p in (0.0, 0.5, 0.8, 0.9):
        open_, high, low, close = ohlc(p_flat_open=p)
        out = ta.yang_zhang(open_, high, low, close, length=20)
        o, c = open_.values, close.values
        prev_c = np.r_[np.nan, c[:-1]]
        flat_frac = float(np.mean(np.isclose(o[1:], prev_c[1:])))
        print(f"  p={p}: open==prior_close fraction (post-tick-rounding) = {flat_frac:.4f}, "
              f"YZVOL fires {int(out.notna().sum())}/{len(out)}, range "
              f"[{float(out.dropna().min()):.4f}, {float(out.dropna().max()):.4f}]")


def _load_mutant(module_name, old, new):
    import importlib
    import types
    real = importlib.import_module(module_name)
    src = open(real.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique in {module_name}"
    mod = types.ModuleType(f"_{module_name.rsplit('.', 1)[-1]}_mutant")
    mod.__file__ = real.__file__
    exec(compile(src.replace(old, new), real.__file__, "exec"), mod.__dict__)
    return mod, real


def _leaks(fn, offsets, p_flat_open=0.0):
    open_, high, low, close = ohlc(p_flat_open=p_flat_open)
    base = fn(open_, high, low, close)
    o2, h2, l2, c2 = ohlc(seed=99, p_flat_open=p_flat_open)
    hits = 0
    for j in offsets:
        po, ph, pl, pc = open_.copy(), high.copy(), low.copy(), close.copy()
        po.iloc[j:] = o2.iloc[j:].values
        ph.iloc[j:] = h2.iloc[j:].values
        pl.iloc[j:] = l2.iloc[j:].values
        pc.iloc[j:] = c2.iloc[j:].values
        out = fn(po, ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def measure_mutant_catch_counts():
    print("\n== Gate B mutant catch counts (exact, out of the offsets tested)")
    offsets_31 = range(40, 1100, 35)
    offsets_30 = range(60, 1100, 35)

    mod, real = _load_mutant("pandas_ta.volatility.garman_klass",
                              "variance = per_bar.rolling(length).mean().clip(lower=0.0)",
                              "variance = per_bar.shift(-1).rolling(length).mean().clip(lower=0.0)")
    print("  garman_klass mutant caught:", _leaks(mod.garman_klass, offsets_31), "/", len(offsets_31))

    mod, real = _load_mutant("pandas_ta.volatility.rogers_satchell",
                              "variance = per_bar.rolling(length).mean().clip(lower=0.0)",
                              "variance = per_bar.shift(-1).rolling(length).mean().clip(lower=0.0)")
    print("  rogers_satchell mutant caught:", _leaks(mod.rogers_satchell, offsets_31), "/", len(offsets_31))

    mod, real = _load_mutant("pandas_ta.volatility.yang_zhang",
                              "prev_close = close.shift(1)", "prev_close = close.shift(-1)")
    print("  yang_zhang mutant caught:", _leaks(mod.yang_zhang, offsets_30), "/", len(offsets_30))


def measure_proxy_overlap():
    print("\n== proxy overlap vs natr / har_park (NOT Gate E) -- the issue's own guess to beat (rho >= 0.9)")
    open_, high, low, close = ohlc(seed=1, n=3000, sigma=0.012)
    gk = ta.garman_klass(open_, high, low, close)
    rs = ta.rogers_satchell(open_, high, low, close)
    yz = ta.yang_zhang(open_, high, low, close)
    comparators = {
        "NATR_14": ta.natr(high, low, close),
        "HARPARK_1_5_22_500": ta.har_park(high, low, close),
        "TRUE_RANGE (pct of close)": ta.true_range(high, low, close) / close * 100,
        "RVI_14": ta.rvi(high, low, close),
    }
    for name, x in comparators.items():
        print(f"  GKVOL_20 vs {name}: {rho(gk, x)}")
        print(f"  RSVOL_20 vs {name}: {rho(rs, x)}")
        print(f"  YZVOL_20 vs {name}: {rho(yz, x)}")
    print("  GKVOL_20 vs RSVOL_20:", rho(gk, rs))
    print("  GKVOL_20 vs YZVOL_20:", rho(gk, yz))
    print("  RSVOL_20 vs YZVOL_20:", rho(rs, yz))
    print("  n (GK finite):", int(gk.notna().sum()), "n (RS finite):", int(rs.notna().sum()),
          "n (YZ finite):", int(yz.notna().sum()))


if __name__ == "__main__":
    import platform
    print(f"pandas {pd.__version__}, numpy {np.__version__}, Python {platform.python_version()}")
    measure("GKVOL_20", ta.garman_klass)
    measure("RSVOL_20", ta.rogers_satchell)
    measure("YZVOL_20", ta.yang_zhang)
    measure_clip_engagement()
    measure_open_quality()
    measure_mutant_catch_counts()
    measure_proxy_overlap()
