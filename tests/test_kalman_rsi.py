# tests/test_kalman_rsi.py
"""kalman_rsi -- RSI computed on a Kalman-filtered close (TVPTA-3, ported
from "Kalman Filter-Optimized RSI"). Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _close(n=200, seed=0):
    rng = np.random.RandomState(seed)
    return pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )


def test_bounded_0_100():
    close = _close()
    out = ta.kalman_rsi(close, length=14)
    assert out.name == "KRSI_14"
    # tiny float-precision headroom (observed 100.00000000000001 from the
    # underlying rsi() implementation, not a real out-of-range value)
    assert out.dropna().between(-1e-9, 100 + 1e-9).all()


def test_default_length_matches_source_not_pandas_ta_convention():
    # MAJOR regression (Fletcher round 1): the first draft defaulted to
    # pandas_ta's conventional RSI length (14) without checking what the
    # SOURCE Pine script (fU13VFoj-...pine:9, rsiLength=5) actually uses.
    # This is a port of a specific published indicator -- its default must
    # match the source, not a generic convention.
    close = _close()
    out_default = ta.kalman_rsi(close)
    assert out_default.name == "KRSI_5"
    pdt.assert_series_equal(out_default, ta.kalman_rsi(close, length=5))


def test_correctness_hand_computed_kalman_filter():
    # Constant process_noise/measurement_noise/initial_error, 4 bars.
    # Hand-trace the Kalman recursion itself (not RSI, which is already
    # proven pandas_ta code) to confirm the smoothed price is right before
    # trusting anything downstream.
    #
    # NIT (Fletcher round 2): the call below omits process_noise/
    # measurement_noise/initial_error, so this test ALSO implicitly locks
    # those three defaults to the Pine source's values (0.01/1.0/1.0,
    # hardcoded in `pn, mn, ie` below) -- if one of THOSE defaults ever
    # drifts, this test fails with a cryptic Kalman-price mismatch, not an
    # obvious "default changed" message. Noting it here so a future
    # debugger isn't stuck for ten minutes wondering why the length-5 math
    # doesn't match anymore.
    #
    # CAUGHT BY THIS TEST (not by review): the first draft assumed bar 0
    # is a pure initialization with no Kalman update applied (error stays
    # at initial_error until bar 1). That's wrong -- the source Pine
    # applies the SAME predict/update at every bar including the first
    # (`predictedPrice = na(kalmanPrice[1]) ? close : kalmanPrice[1]`,
    # `predictedError = nz(kalmanError[1], initialError) + processNoise`,
    # both evaluated unconditionally every bar) -- so `error` already
    # shrinks from `initial_error` after bar 0, even though `price` is a
    # no-op there (predicted_price == close[0] == price, so the gain term
    # is multiplied by zero). The implementation already matched Pine;
    # the first draft of THIS test didn't, and the resulting expected
    # values were off by a few percent from bar 1 onward -- exactly the
    # kind of error a hand-trace exists to catch, just aimed the wrong way
    # this time.
    close = pd.Series([100.0, 102.0, 98.0, 101.0])
    pn, mn, ie = 0.01, 1.0, 1.0

    price, error = 100.0, ie  # bar 0's own update, applied uniformly:
    pred_err_0 = error + pn                      # 1.01
    gain_0 = pred_err_0 / (pred_err_0 + mn)       # 0.502488...
    price = price + gain_0 * (100.0 - price)      # no-op: 100.0
    error = (1 - gain_0) * pred_err_0             # 0.502488...

    pred_err_1 = error + pn
    gain_1 = pred_err_1 / (pred_err_1 + mn)
    price_1 = price + gain_1 * (102.0 - price)
    err_1 = (1 - gain_1) * pred_err_1

    pred_err_2 = err_1 + pn
    gain_2 = pred_err_2 / (pred_err_2 + mn)
    price_2 = price_1 + gain_2 * (98.0 - price_1)

    # MINOR fix (Fletcher round 1): this loop and the scalar trace above it
    # are the same recursion written twice -- a regression check that the
    # implementation matches ITS OWN formula restated here, not an
    # independent re-derivation from the Pine source (a shared
    # misunderstanding of the formula would pass both). The actual
    # source-vs-formula check is that the scalar trace above was built by
    # reading fU13VFoj-...pine:25-37 directly. Keeping this loop because it
    # exercises all 4 bars (the scalar trace above only covers 3) and
    # isolates the Kalman step from RSI, not because it's independent.
    vals = close.to_numpy(dtype=float)
    kp = np.full(4, np.nan)
    p, e = vals[0], ie
    for t in range(4):
        predicted_price = p
        predicted_error = e + pn
        g = predicted_error / (predicted_error + mn)
        p = predicted_price + g * (vals[t] - predicted_price)
        e = (1 - g) * predicted_error
        kp[t] = p

    assert kp[0] == pytest.approx(price)
    assert kp[1] == pytest.approx(price_1)
    assert kp[2] == pytest.approx(price_2)

    # And the actual function's KRSI output must equal ta.rsi() run on
    # this exact independently-reconstructed kalman price series.
    out = ta.kalman_rsi(close, length=2)
    expected_rsi = ta.rsi(pd.Series(kp, index=close.index), length=2)
    pdt.assert_series_equal(out, expected_rsi, check_names=False)


def test_no_lookahead():
    close = _close()
    T = 150
    out_full = ta.kalman_rsi(close, length=14)

    corrupted = close.copy()
    corrupted.iloc[T + 1:] += 1000.0
    out_corrupted = ta.kalman_rsi(corrupted, length=14)

    pdt.assert_series_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    close = _close()
    df = pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "kalman_rsi" in ta.Category["momentum"]
    assert callable(getattr(df.ta, "kalman_rsi"))

    module_result = ta.kalman_rsi(close=close, length=14)
    accessor_result = df.ta.kalman_rsi(length=14)
    pdt.assert_series_equal(module_result, accessor_result)
