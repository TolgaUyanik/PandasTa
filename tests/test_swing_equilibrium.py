# tests/test_swing_equilibrium.py
"""swing_equilibrium -- % distance to the midpoint of the last confirmed
swing high/low, plus break-of-structure flags (TVPTA-3, ported from the
TradingView community indicator "Market Structure & 50% Retracement").
Self-contained on synthetic data, no dependency on data/SPY_D.csv.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c) on why that pattern is the anti-pattern).
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
    out = ta.swing_equilibrium(high, low, close, left=5, right=5)
    assert list(out.columns) == [
        "SWINGEQ_5_5", "SWINGEQ_BOS_BULL_5_5", "SWINGEQ_BOS_BEAR_5_5",
    ]


def test_correctness_hand_computed_single_pivot():
    # 10 bars, left=2, right=2 (window=5). high peaks at index 2 (15) then
    # strictly decreases; low troughs at index 2 (5) then strictly
    # increases -- a mirror-image pair, so BOTH the pivot high and pivot
    # low confirm at the SAME bar, hand-traceable:
    #   window [0:5] for high = [10,11,15,12,9], max=15 at pos 2
    #   window [0:5] for low  = [10,9,5,8,11],   min=5  at pos 2
    # both confirm (become visible) at j = 2 + right(2) = 4.
    # No further pivot in either series afterward (strictly monotonic
    # tails), so swing_high=15 / swing_low=5 hold for the rest of the
    # series. close is held constant at the exact midpoint (10), so
    # SWINGEQ = (10 - (15+5)/2) / 10 * 100 = 0.0 exactly from bar 4 on,
    # and BOS never fires (close never crosses either swing level).
    high = pd.Series([10.0, 11.0, 15.0, 12.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0])
    low = pd.Series([10.0, 9.0, 5.0, 8.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0])
    close = pd.Series([10.0] * 10)

    out = ta.swing_equilibrium(high, low, close, left=2, right=2)
    col = "SWINGEQ_2_2"

    assert out[col].iloc[:4].isna().all()
    assert out[col].iloc[4:].apply(lambda v: v == pytest.approx(0.0)).all()
    assert (out["SWINGEQ_BOS_BULL_2_2"] == 0).all()
    assert (out["SWINGEQ_BOS_BEAR_2_2"] == 0).all()


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 220
    out_full = ta.swing_equilibrium(high, low, close, left=5, right=5)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.swing_equilibrium(high_c, low_c, close_c, left=5, right=5)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_bos_bull_fires_on_designed_breakout():
    # Swing high 110 at index 5 (confirmed at j=5+3=8), an 8-bar PLATEAU at
    # 100 (indices 6-13), then a real breakout to close=119 at index 14 --
    # before the swing high updates again (the next pivot, 120, doesn't
    # confirm until j=14+3=17). BOS_BULL must fire on EXACTLY index 14 and
    # nowhere else -- a loose `>= 1` / `any(...)` check (the first draft of
    # this test) can't tell "fired for the right reason" from "fired at
    # all", and would not have caught the plateau tie-break bug below.
    high = pd.Series([100.0] * 5 + [110.0] + [100.0] * 8 + [120.0] + [100.0] * 15)
    low = pd.Series([90.0] * 5 + [80.0] + [90.0] * 8 + [70.0] + [90.0] * 15)
    close = pd.Series([99.0] * 5 + [109.0] + [99.0] * 8 + [119.0] + [99.0] * 15)

    out = ta.swing_equilibrium(high, low, close, left=3, right=3)
    bull_bars = out.index[out["SWINGEQ_BOS_BULL_3_3"] == 1].tolist()
    assert bull_bars == [14]
    assert (out["SWINGEQ_BOS_BEAR_3_3"] == 0).all()


def test_plateau_does_not_produce_spurious_pivots():
    # CRITICAL regression (Fletcher round 1): bare `== window max` confirms
    # EVERY bar of a flat plateau as its own pivot (the plateau's max is
    # tied across all of it), decaying swing_high/low to the trivial flat
    # value and erasing the real, larger 110/-80 swing before the genuine
    # breakout at index 14 -- verified concretely: SWINGEQ went flat at
    # 0.0 across the plateau (indices 12-13) before this fix, instead of
    # holding steady at the value implied by the real 110/80 swing.
    high = pd.Series([100.0] * 5 + [110.0] + [100.0] * 8 + [120.0] + [100.0] * 15)
    low = pd.Series([90.0] * 5 + [80.0] + [90.0] * 8 + [70.0] + [90.0] * 15)
    close = pd.Series([99.0] * 5 + [109.0] + [99.0] * 8 + [119.0] + [99.0] * 15)

    out = ta.swing_equilibrium(high, low, close, left=3, right=3)
    plateau = out["SWINGEQ_3_3"].iloc[8:14]  # bars 8-13: after the 110/80
    # swing confirms (j=8), before the 120/70 swing confirms (j=17) --
    # SWINGEQ must be CONSTANT across this stretch (the swing hasn't
    # actually changed), not decaying toward 0 as the plateau progresses.
    assert plateau.nunique() == 1
    assert plateau.iloc[0] == pytest.approx(4.040404, abs=1e-4)


def test_double_top_confirms_exactly_one_pivot():
    # CRITICAL regression (Fletcher round 2): the round-1 fix over-corrected
    # -- requiring the candidate be the UNIQUE extreme in its window means a
    # genuine 2-bar tie (a double-top/double-bottom, an ordinary pattern,
    # NOT a plateau edge case) confirmed NO pivot at all, silently, for the
    # rest of the series. The correct, deterministic rule is
    # rightmost-tie-wins.
    #
    # MAJOR fix (Fletcher round 3): the first version of this test tied
    # high[1] against high[3] with left=right=2 -- but a candidate at
    # position i needs i >= left to have a full BACKWARD window at all, and
    # index 1 fails that (1 < left=2), so it was never evaluated as a
    # candidate in the first place. The test then had exactly ONE reachable
    # candidate (index 3), which passes under rightmost-tie-wins,
    # leftmost-tie-wins restricted to reachable candidates, or several
    # other wrong rules -- it proved nothing about tie-break DIRECTION.
    # Fixed fixture: BOTH tied bars (indices 2 and 4) satisfy i >= left and
    # have a full window on both sides, so this is a genuine two-live-
    # candidate tie. Hand-verified: window for i=2 is [0:5]=[90,90,105,90,105],
    # max=105 with a LATER tie at i=4 -> i=2 REJECTED. Window for i=4 is
    # [2:7]=[105,90,105,90,90], max=105 with NO later tie -> i=4 CONFIRMED,
    # visible at j=4+right(2)=6. Asserting the exact bar, not just "some
    # bar from some point on", per round 3's fix instruction.
    high = pd.Series([90.0, 90.0, 105.0, 90.0, 105.0, 90.0, 90.0, 90.0])
    low = pd.Series([80.0, 80.0, 65.0, 80.0, 65.0, 80.0, 80.0, 80.0])
    close = (high + low) / 2  # exact midpoint -> SWINGEQ must read 0.0

    out = ta.swing_equilibrium(high, low, close, left=2, right=2)
    assert out["SWINGEQ_2_2"].first_valid_index() == 6
    assert out["SWINGEQ_2_2"].iloc[:6].isna().all()
    assert np.allclose(out["SWINGEQ_2_2"].iloc[6:].to_numpy(), 0.0, atol=1e-9)


def test_nan_gap_does_not_crash_or_spuriously_confirm():
    # Real BIST data has occasional missing bars; a NaN inside a pivot
    # window must not crash the scan or get treated as an extreme.
    high = pd.Series([100.0, 101.0, np.nan, 103.0, 99.0, 98.0, 97.0, 96.0])
    low = high - 5.0
    close = high - 2.5
    # Reaching this line at all (no exception) is half the assertion --
    # the other half is that any value that DID compute is finite, not a
    # NaN-poisoned inf/-inf from an unguarded comparison against NaN.
    out = ta.swing_equilibrium(high, low, close, left=2, right=2)
    assert np.isfinite(out["SWINGEQ_2_2"].dropna().to_numpy()).all()


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "swing_equilibrium" in ta.Category["trend"]
    assert callable(getattr(df.ta, "swing_equilibrium"))

    module_result = ta.swing_equilibrium(high=high, low=low, close=close, left=5, right=5)
    accessor_result = df.ta.swing_equilibrium(left=5, right=5)
    pdt.assert_frame_equal(module_result, accessor_result)
