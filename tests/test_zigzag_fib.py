# tests/test_zigzag_fib.py
"""zigzag_fib -- % distance to Fibonacci retracement levels of the current
alternating zigzag leg (TVPTA-3, ported from "GCM Fibonacci Engine for
Elliott Waves"). Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=300, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n)
    low = close - rng.rand(n)
    return high, low, close


def test_columns_present_and_named():
    high, low, close = _ohlc()
    out = ta.zigzag_fib(high, low, close, length=5)
    assert list(out.columns) == ["ZZFIB_50_5", "ZZFIB_618_5"]


def test_correctness_hand_computed_up_then_down_leg():
    # Rises to a confirmed peak at index 5 (110, left=right=2, confirms at
    # j=5+2=7), then falls to a confirmed trough at index 10 (low=87,
    # confirms at j=10+2=12). Zigzag alternation: the up-pivot (110) opens
    # the first leg at j=7 (p1=NaN, p2=110); the down-pivot (87) reverses
    # it at j=12 (p1=110, p2=87). Hand-computed at j=12:
    #   diff = p2-p1 = 87-110 = -23
    #   fib50  = p2 - diff*0.5   = 87 - (-11.5)  = 98.5
    #   fib618 = p2 - diff*0.618 = 87 - (-14.214) = 101.214
    #   close[12] = 92 - 1 = 91
    #   ZZFIB_50  = (91-98.5)/91*100  = -8.241758...
    #   ZZFIB_618 = (91-101.214)/91*100 = -11.224176...
    high = pd.Series([100, 101, 102, 103, 104, 110, 104, 103, 102, 101,
                       90, 91, 92, 93, 94, 95, 96, 97, 98, 99], dtype=float)
    low = high - 3.0
    close = high - 1.0

    out = ta.zigzag_fib(high, low, close, length=2)
    assert out["ZZFIB_50_2"].iloc[:12].isna().all()
    assert out["ZZFIB_50_2"].iloc[12] == pytest.approx(-8.241758, abs=1e-5)
    assert out["ZZFIB_618_2"].iloc[12] == pytest.approx(-11.224176, abs=1e-5)


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 220
    out_full = ta.zigzag_fib(high, low, close, length=5)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.zigzag_fib(high_c, low_c, close_c, length=5)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_plateau_does_not_produce_spurious_pivots():
    # Regression, reusing the exact lesson from swing_equilibrium's round-1
    # CRITICAL: a flat run must not confirm every one of its bars as its
    # own pivot. 8-bar 100-plateau between a real 110 high and a real 120
    # high (mirrored on the low side: 80 and 70) -- ZZFIB must hold
    # CONSTANT across the plateau (bars 8-13), not decay bar-by-bar.
    #
    # NOTE, verified numerically before writing this assertion (first
    # draft assumed no reversal ever happens in this fixture -- wrong: the
    # high pivot (110) and low pivot (80) confirm on the SAME bar (index
    # 5, both lag-3-confirmed at j=8), so the zigzag actually opens AND
    # reverses in one bar via two sequential `if` blocks, exactly
    # replicating the source Pine's own two-separate-if-statement
    # structure. That is correct causal behavior, not a bug -- the
    # regression that matters is still "does the value stay flat across
    # the plateau", which it does.
    high = pd.Series([100.0] * 5 + [110.0] + [100.0] * 8 + [120.0] + [100.0] * 15)
    low = pd.Series([90.0] * 5 + [80.0] + [90.0] * 8 + [70.0] + [90.0] * 15)
    close = pd.Series([99.0] * 5 + [109.0] + [99.0] * 8 + [119.0] + [99.0] * 15)

    out = ta.zigzag_fib(high, low, close, length=3)
    assert out["ZZFIB_50_3"].iloc[:8].isna().all()
    plateau = out["ZZFIB_50_3"].iloc[8:14]
    assert plateau.nunique() == 1
    assert plateau.iloc[0] == pytest.approx(4.040404, abs=1e-4)


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "zigzag_fib" in ta.Category["trend"]
    assert callable(getattr(df.ta, "zigzag_fib"))

    module_result = ta.zigzag_fib(high=high, low=low, close=close, length=5)
    accessor_result = df.ta.zigzag_fib(length=5)
    pdt.assert_frame_equal(module_result, accessor_result)
