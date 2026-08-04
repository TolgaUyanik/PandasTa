# tests/test_pocket_pivot.py
"""pocket_pivot -- Kacher/Morales pocket pivot (TVPTA-3, ported from
"Pocket Pivot (Kacher/Morales) - Custom"). Self-contained on synthetic
data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlcv(n=100, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    open_ = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([close, open_], axis=1).max(axis=1) + rng.rand(n)
    low = pd.concat([close, open_], axis=1).min(axis=1) - rng.rand(n)
    volume = pd.Series(rng.randint(1000, 5000, n).astype(float), index=close.index)
    return open_, high, low, close, volume


def test_columns_present_and_named():
    open_, high, low, close, volume = _ohlcv()
    out = ta.pocket_pivot(close, open_, high, low, volume, length=10, lookback=10)
    assert list(out.columns) == [
        "PPIVOT_10_10", "PPIVOT_VOLRATIO_10_10", "PPIVOT_MAOFFSET_10_10",
    ]


def test_correctness_hand_computed():
    # 12 bars, length=3 (SMA), lookback=3. Down days (bars 1,2: close<open)
    # set a small highest_sell_volume ceiling; bar 5 is an up day (bar 5:
    # close>open) with volume comfortably above that ceiling, AND close is
    # within 4% of its own 3-bar SMA -- a pocket pivot should fire there.
    open_ = pd.Series([10.0, 10.0, 9.5, 9.0, 9.2, 9.3, 9.3, 9.3, 9.3, 9.3, 9.3, 9.3])
    close = pd.Series([10.0, 9.5, 9.0, 9.2, 9.3, 9.6, 9.3, 9.3, 9.3, 9.3, 9.3, 9.3])
    high = pd.concat([open_, close], axis=1).max(axis=1) + 0.1
    low = pd.concat([open_, close], axis=1).min(axis=1) - 0.1
    volume = pd.Series([100.0, 500.0, 400.0, 100.0, 100.0, 900.0,
                         100.0, 100.0, 100.0, 100.0, 100.0, 100.0])

    out = ta.pocket_pivot(close, open_, high, low, volume, length=3, lookback=3)

    # bar 5: close=9.6>open=9.3 -> buy_volume=900. highest_sell_volume =
    # max(sell_volume[2:5]) = max(500 [bar1], 400 [bar2], 0 [bar3, up-ish
    # since close==open -> not < -> 0], 0 [bar4]) restricted to shift(1)
    # over the trailing 3 bars ending bar4 = bars [2,3,4] -> sell_volume
    # there is [400, 0, 0] (bar2 close9.0<open9.5 -> sell; bar3
    # close9.2>open9.0 -> not sell; bar4 close9.3>open9.2 -> not sell) ->
    # highest_sell_volume=400. buy_volume[5]=900 > 400 -> volume_condition True.
    ma5 = (close.iloc[3] + close.iloc[4] + close.iloc[5]) / 3
    offset5 = abs(close.iloc[5] - ma5) / ma5 * 100
    assert out["PPIVOT_MAOFFSET_3_3"].iloc[5] == pytest.approx(offset5)
    assert out["PPIVOT_VOLRATIO_3_3"].iloc[5] == pytest.approx(900.0 / 400.0)
    # offset5 ~= 2.49%, comfortably under the 4.0% default threshold --
    # verified below, but this fixture alone never exercises the FALSE
    # branch of the <= comparison (see test_flag_false_when_price_extended
    # for that -- Fletcher round 1 caught the gap: a formula-recomputed
    # branch condition can't prove the comparison operator is right).
    assert offset5 == pytest.approx(2.491103, abs=1e-5)
    assert offset5 <= 4.0
    assert out["PPIVOT_3_3"].iloc[5] == 1


def test_flag_false_when_price_extended_despite_volume_condition():
    # MINOR regression (Fletcher round 1): same setup as the correctness
    # test above, except bar 5 closes much higher (10.0, not 9.6) so the
    # volume condition is STILL true (buy_volume=900 > highest_sell_
    # volume=400) but price is now far from its own SMA -- PPIVOT must be
    # 0 despite the volume condition passing. Hand-computed, hardcoded
    # oracle, not recomputed from the formula under test:
    #   ma5 = (9.2+9.3+10.0)/3 = 9.5
    #   offset5 = |10.0-9.5|/9.5*100 = 5.263157...% > 4.0% -> PPIVOT=0
    open_ = pd.Series([10.0, 10.0, 9.5, 9.0, 9.2, 9.3])
    close = pd.Series([10.0, 9.5, 9.0, 9.2, 9.3, 10.0])
    high = pd.concat([open_, close], axis=1).max(axis=1) + 0.1
    low = pd.concat([open_, close], axis=1).min(axis=1) - 0.1
    volume = pd.Series([100.0, 500.0, 400.0, 100.0, 100.0, 900.0])

    out = ta.pocket_pivot(close, open_, high, low, volume, length=3, lookback=3)

    assert out["PPIVOT_MAOFFSET_3_3"].iloc[5] == pytest.approx(5.263157, abs=1e-5)
    assert out["PPIVOT_VOLRATIO_3_3"].iloc[5] == pytest.approx(900.0 / 400.0)
    assert out["PPIVOT_3_3"].iloc[5] == 0


def test_no_lookahead():
    open_, high, low, close, volume = _ohlcv()
    T = 60
    out_full = ta.pocket_pivot(close, open_, high, low, volume)

    open_c, high_c, low_c, close_c, volume_c = (
        open_.copy(), high.copy(), low.copy(), close.copy(), volume.copy(),
    )
    close_c.iloc[T + 1:] += 1000.0
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    open_c.iloc[T + 1:] += 1000.0
    volume_c.iloc[T + 1:] *= 5
    out_corrupted = ta.pocket_pivot(close_c, open_c, high_c, low_c, volume_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    open_, high, low, close, volume = _ohlcv()
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })

    assert "pocket_pivot" in ta.Category["volume"]
    assert callable(getattr(df.ta, "pocket_pivot"))

    module_result = ta.pocket_pivot(close=close, open_=open_, high=high, low=low, volume=volume)
    accessor_result = df.ta.pocket_pivot()
    pdt.assert_frame_equal(module_result, accessor_result)
