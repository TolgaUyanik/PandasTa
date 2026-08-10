# tests/test_har_park.py
"""har_park -- causal rolling-refit HAR regression on Parkinson volatility
(TVPTA-6, ported from "HAR-Parkinson Volume Forecast"). Self-contained on
synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).

Fletcher round 1 (2026-08-10): the original `test_correctness_against_
independent_ols_refit` copied eleven lines of park_pct/rolling/shift logic
verbatim from the implementation -- it would have stayed green even if
`.shift(1)` were flipped to `.shift(-1)` (textbook look-ahead, exactly what
this candidate was originally deferred over). Replaced with a genuinely
independent causality test (mutate future bars, assert past output is
unchanged) and kept the lstsq check as what it actually is: a solver
correctness check, not a from-scratch reimplementation.
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.volatility.har_park import _parkinson_pct


def _ohlc(n=100, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n) + 0.1
    low = close - rng.rand(n) - 0.1
    return high, low, close


def test_name_and_series():
    high, low, close = _ohlc(n=200)
    out = ta.har_park(high, low, close, fit_window=100)
    assert isinstance(out, pd.Series)
    assert out.name == "HARPARK_1_5_22_100"


def test_accessor_matches_direct_call():
    # Gate (c): reachable via df.ta.har_park(), not just the bare function
    # -- the ichimoku_ml lesson (a file that exists but isn't registered
    # in core.py is unreachable). This file's own module docstring claims
    # reachability is tested; until now nothing here actually asserted it.
    high, low, close = _ohlc(n=200, seed=5)
    df = pd.DataFrame({"high": high, "low": low, "close": close})
    via_accessor = df.ta.har_park(fit_window=100)
    direct = ta.har_park(high, low, close, fit_window=100)
    pd.testing.assert_series_equal(via_accessor, direct)


def test_never_negative_and_clip_actually_engages():
    # Not just "the data we happened to generate never went negative" --
    # a volatility-collapse regime (high vol for 150 bars, then near-zero)
    # empirically drives the RAW forecast below zero (a regression trained
    # on the high-vol regime extrapolates negative from the collapsed
    # inputs), and the clip is verified to actually bind: exact 0.0, not
    # just "small positive."
    n = 250
    rng = np.random.RandomState(9)
    close = pd.Series(100 + np.cumsum(rng.randn(n) * 3), index=pd.date_range("2020-01-01", periods=n, freq="B"))
    high = close.copy()
    low = close.copy()
    high.iloc[:150] = close.iloc[:150] + np.abs(rng.randn(150)) * 5 + 0.5
    low.iloc[:150] = close.iloc[:150] - np.abs(rng.randn(150)) * 5 - 0.5
    high.iloc[150:] = close.iloc[150:] + 0.001
    low.iloc[150:] = close.iloc[150:] - 0.001

    out = ta.har_park(high, low, close, fit_window=100)
    assert (out.dropna() >= 0).all()
    assert (out.dropna() == 0.0).any(), "clip never actually bound on this data -- test is vacuous if this fails"


def test_nan_before_fit_ready_then_finite_throughout():
    # fit_ready requires bar_index > long_length + fit_window//2 + 60 --
    # with fit_window=100, long_length=22 that's bar_index > 132, so the
    # first finite bar is index 133. Was previously checked with a loose
    # `.any()` past bar 150 (passes if even 1 of 100 bars is finite); now
    # `.all()` (every bar from the ready point on must be finite) plus an
    # exact boundary pin so an off-by-one in fit_ready regresses loudly.
    high, low, close = _ohlc(n=250, seed=2)
    out = ta.har_park(high, low, close, fit_window=100)
    assert out.iloc[:133].isna().all()
    assert pd.notna(out.iloc[133])
    assert out.iloc[133:].notna().all()


def test_causal_no_lookahead():
    # The single highest-value correctness check for a candidate deferred
    # specifically for correctness risk: mutate every bar strictly AFTER
    # bar t and assert the output at and before t is bit-identical. This
    # locks the .shift(1) direction and the rolling-window alignment
    # without reusing a single line of the implementation -- a flipped
    # shift() or a training window that leaks x[t] instead of x[t-1]
    # would fail this immediately.
    high, low, close = _ohlc(n=250, seed=6)
    out_before = ta.har_park(high, low, close, fit_window=100)

    t = 200
    high_mut, low_mut, close_mut = high.copy(), low.copy(), close.copy()
    high_mut.iloc[t + 1:] *= 1.5
    low_mut.iloc[t + 1:] *= 0.6
    close_mut.iloc[t + 1:] *= 1.2
    out_after = ta.har_park(high_mut, low_mut, close_mut, fit_window=100)

    pd.testing.assert_series_equal(out_before.iloc[: t + 1], out_after.iloc[: t + 1])


def test_correctness_against_independent_lstsq_solve():
    # Solver correctness check: recompute the regression fit at bar t via
    # numpy.linalg.lstsq on hand-sliced windows, independent of the
    # module's own rolling-sum/normal-equations machinery. This validates
    # the SOLVE step, not the Parkinson formula or the causal direction --
    # see test_causal_no_lookahead above for that, and note this test
    # reuses the park_pct/x1/x2/x3 computation (same formula, deliberately
    # -- the point here is isolating the solver, not re-deriving the
    # formula from scratch).
    high, low, close = _ohlc(n=250, seed=3)
    fit_window = 100
    short_length, medium_length, long_length = 1, 5, 22
    out = ta.har_park(high, low, close, fit_window=fit_window)

    park_pct = _parkinson_pct(high, low)
    x1 = park_pct.rolling(short_length).mean()
    x2 = park_pct.rolling(medium_length).mean()
    x3 = park_pct.rolling(long_length).mean()
    y = park_pct
    p1, p2, p3 = x1.shift(1), x2.shift(1), x3.shift(1)
    valid = p1.notna() & p2.notna() & p3.notna() & y.notna()

    t = 200  # a bar comfortably inside the fit-ready region
    window_valid = valid.iloc[t - fit_window + 1: t + 1]
    X = np.column_stack([
        np.ones(window_valid.sum()),
        p1.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy(),
        p2.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy(),
        p3.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy(),
    ])
    Y = y.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy()
    coeffs, *_ = np.linalg.lstsq(X, Y, rcond=None)
    b0, b1, b2, b3 = coeffs
    expected = max(b0 + b1 * x1.iloc[t] + b2 * x2.iloc[t] + b3 * x3.iloc[t], 0.0)

    assert out.iloc[t] == pytest.approx(expected, rel=1e-6)


def test_offset():
    high, low, close = _ohlc(n=200, seed=4)
    out = ta.har_park(high, low, close, fit_window=100)
    shifted = ta.har_park(high, low, close, fit_window=100, offset=1)
    pd.testing.assert_series_equal(
        shifted.iloc[1:].reset_index(drop=True),
        out.iloc[:-1].reset_index(drop=True),
        check_names=False,
    )


def test_parkinson_formula_matches_hand_computed_value():
    # Fletcher round 1: every prior test re-derived the Parkinson formula
    # inline from the implementation, so a wrong constant (e.g. 2*ln2
    # instead of 4*ln2) would cancel against itself and stay green
    # everywhere. This is the one test with a literal, hand-computed
    # expected value with no shared code: for high=110, low=100,
    # Parkinson % = sqrt(ln(1.1)^2 / (4*ln(2))) * 100 = 5.723959637...
    high = pd.Series([110.0], index=pd.date_range("2020-01-01", periods=1))
    low = pd.Series([100.0], index=pd.date_range("2020-01-01", periods=1))
    out = _parkinson_pct(high, low)
    assert out.iloc[0] == pytest.approx(5.723959637, abs=1e-8)


def test_near_singular_guard_is_scale_relative_not_absolute():
    # Fletcher round 1 CRITICAL-class catch: a first version of the guard
    # used an ABSOLUTE 1e-12 singular-value floor, which tracks matrix
    # MAGNITUDE (this Gram-style matrix scales with fit_window *
    # park_pct^2), not conditioning -- a constant-H/L-ratio (rank-
    # deficient by construction) input at BIST-limit-lock scale (+/-10%)
    # sailed straight through the old guard with garbage, arbitrarily-
    # amplified coefficients. The fix makes the threshold relative to the
    # matrix's own scale (condition-number style). This test pins that at
    # BIST magnitude specifically -- the exact scale the old guard failed
    # at -- not just at a scale small enough to trip an absolute floor.
    n = 300
    close = pd.Series(100 + np.arange(n) * 0.01, index=pd.date_range("2020-01-01", periods=n, freq="B"))
    high = close * 1.10
    low = close * 0.90
    out = ta.har_park(high, low, close, fit_window=100)
    assert out.isna().all(), "constant H/L ratio at BIST-limit-lock magnitude must yield all-NaN (rank-deficient fit), not garbage coefficients"
