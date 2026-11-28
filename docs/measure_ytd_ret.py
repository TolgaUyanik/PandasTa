# -*- coding: utf-8 -*-
"""Prints the numbers quoted in docs/YtdRetMeasured.md for
`pandas_ta.performance.ytd_ret`. Synthetic frame only: this does not run Gate E
or read real prices. Run from the repo root: python -m docs.measure_ytd_ret"""
import pandas as pd

from tests.test_ytd_ret import (LAST_OPEN, OFFSETS, ONE_BAR_LATE, _frame, _frame_with_a_blank_year,
                                _leaks, _load_mutant, ytd_ret)


def main():
    open_, close = _frame()
    out = ytd_ret(open_, close)
    n = len(out)
    years = out.index.year
    print(f"n={n} years={pd.Series(years).nunique()} non_nan={int(out.notna().sum())}")
    print(f"above={int((out > 0).sum())} below={int((out < 0).sum())} nunique={out.nunique()}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    starts = sum(years[j] != years[j - 1] for j in OFFSETS)
    print(f"gate B: offsets={len(OFFSETS)} on_year_first_bar={starts} real_leaks={_leaks(ytd_ret)} "
          f"last_open_leaks={_leaks(_load_mutant(LAST_OPEN).ytd_ret)} "
          f"one_bar_late_leaks={_leaks(_load_mutant(ONE_BAR_LATE).ytd_ret)}")

    open_, close = _frame_with_a_blank_year()
    out = ytd_ret(open_, close)
    print(f"gate D frame: n={len(out)} nan={int(out.isna().sum())}")

    for k in (8.0, 64.0, 10.0, 3.7):
        s = ytd_ret(open_ * k, close * k)
        m = out.notna()
        print(f"gate D x{k}: bit_identical={bool((out[m] == s[m]).all())} "
              f"max_diff={float((out - s).abs().max())} "
              f"nan_mask_match={bool((out.isna() == s.isna()).all())}")

    overlap()


def overlap():
    """Pre-port equivalence screen (synthetic, not Gate E): 12 business-day frames,
    1,500 bars from 2015-01-01, prices rounded to 0.1 so ties occur; per-frame
    Spearman |rho| of YTD_RET against the nearest shipped families."""
    import numpy as np
    import pandas_ta as ta
    from scipy.stats import spearmanr

    res = {}
    for seed in range(12):
        r = np.random.default_rng(seed)
        n = 1500
        idx = pd.bdate_range("2015-01-01", periods=n)
        c = np.round(np.exp(np.cumsum(r.normal(0, 0.02, n))) * 50, 1)
        o = np.round(np.r_[c[0], c[:-1]] * np.exp(r.normal(0, .005, n)), 1)
        o_, c_ = pd.Series(o, index=idx), pd.Series(c, index=idx)
        y = ytd_ret(o_, c_)
        cands = {"MTD_RET": ta.mtd_ret(o_, c_)}
        for L in (63, 126, 189, 252):
            cands[f"PCTRET_{L}"] = ta.percent_return(c_, L)
        for col, v in ta.ma_disparity(c_).items():
            cands[col] = v
        for k, v in cands.items():
            m = y.notna() & v.notna()
            res.setdefault(k, []).append(abs(spearmanr(y[m], v[m])[0]))
    for k, v in sorted(res.items(), key=lambda kv: -np.median(kv[1])):
        print(f"overlap {k}: median|rho|={np.median(v):.4f} min={min(v):.4f} max={max(v):.4f}")


if __name__ == "__main__":
    main()
