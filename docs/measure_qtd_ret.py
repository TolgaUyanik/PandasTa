# -*- coding: utf-8 -*-
"""Prints the numbers quoted in docs/QtdRetMeasured.md for
`pandas_ta.performance.qtd_ret`. Synthetic frame only: this does not run Gate E
or read real prices. Run from the repo root: python -m docs.measure_qtd_ret"""
import pandas as pd

from tests.test_qtd_ret import (LAST_OPEN, OFFSETS, ONE_BAR_LATE, _frame, _frame_with_a_blank_quarter,
                                _leaks, _load_mutant, _quarter_of, qtd_ret)


def main():
    open_, close = _frame()
    out = qtd_ret(open_, close)
    n = len(out)
    quarters = _quarter_of(out.index)
    print(f"n={n} quarters={pd.Series(quarters).nunique()} non_nan={int(out.notna().sum())}")
    print(f"above={int((out > 0).sum())} below={int((out < 0).sum())} nunique={out.nunique()}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    quarters_idx = _quarter_of(close.index)
    starts = sum(quarters_idx[j] != quarters_idx[j - 1] for j in OFFSETS)
    print(f"gate B: offsets={len(OFFSETS)} on_quarter_first_bar={starts} real_leaks={_leaks(qtd_ret)} "
          f"last_open_leaks={_leaks(_load_mutant(LAST_OPEN).qtd_ret)} "
          f"one_bar_late_leaks={_leaks(_load_mutant(ONE_BAR_LATE).qtd_ret)}")

    open_, close = _frame_with_a_blank_quarter()
    out = qtd_ret(open_, close)
    print(f"gate D frame: n={len(out)} nan={int(out.isna().sum())}")

    for k in (8.0, 64.0, 10.0, 3.7):
        s = qtd_ret(open_ * k, close * k)
        m = out.notna()
        print(f"gate D x{k}: bit_identical={bool((out[m] == s[m]).all())} "
              f"max_diff={float((out - s).abs().max())} "
              f"nan_mask_match={bool((out.isna() == s.isna()).all())}")


if __name__ == "__main__":
    main()
