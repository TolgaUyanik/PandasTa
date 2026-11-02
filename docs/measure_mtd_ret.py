# -*- coding: utf-8 -*-
"""Prints the numbers quoted in docs/MtdRetMeasured.md for
`pandas_ta.performance.mtd_ret`. Synthetic frame only: this does not run Gate E
or read real prices. Run from the repo root: python -m docs.measure_mtd_ret"""
import pandas as pd

from tests.test_mtd_ret import OFFSETS, _frame, _leaks, _load_mutant, mtd_ret


def main():
    open_, close = _frame()
    out = mtd_ret(open_, close)
    n = len(out)
    months = out.index.year * 12 + out.index.month
    print(f"n={n} months={pd.Series(months).nunique()} non_nan={int(out.notna().sum())}")
    print(f"above={int((out > 0).sum())} below={int((out < 0).sum())} nunique={out.nunique()}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    starts = sum(close.index[j].month != close.index[j - 1].month for j in OFFSETS)
    print(f"gate B: offsets={len(OFFSETS)} on_month_first_bar={starts} "
          f"real_leaks={_leaks(mtd_ret)} mutant_leaks={_leaks(_load_mutant().mtd_ret)}")

    for k in (8.0, 64.0, 10.0, 3.7):
        s = mtd_ret(open_ * k, close * k)
        print(f"gate D x{k}: bit_identical={bool((out == s).all())} "
              f"max_diff={float((out - s).abs().max())} "
              f"nan_mask_match={bool((out.isna() == s.isna()).all())}")


if __name__ == "__main__":
    main()
