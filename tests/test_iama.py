# tests/test_iama.py
"""iama -- Institutional Adaptive MA distance (TVPTA-6 candidate 12,
ported from "Institutional Moving Averages", 6SVLw0kE). Ports ONLY
`f_ima` (the adaptive-MA engine, Pine L122-133) -- see the module
docstring in pandas_ta/overlap/iama.py for the full NOT-ported list and
the mandatory kama()/vidya() overlap check. Self-contained on synthetic
data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlcv(n=200, seed=0, scale=1.0):
    """Valid-OHLC synthetic fixture with REAL wicks and a REAL open/close
    spread on every bar (not the symmetric High=1.02*Close/Low=0.98*Close/
    Open=Close construction that has bitten prior TVPTA-6 candidates --
    see pressure_pulse's own fixture docstring for the precedent). STRICT
    margins (low < min(o,c) and max(o,c) < high).

    `scale` multiplies the whole OHLC block by a constant -- used by
    test_scale_free_by_construction to prove IAMA_DIST is ratio-invariant,
    not to make this fixture itself degenerate.
    """
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n) * 0.5),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    open_ = close.shift(1).fillna(close.iloc[0]) + rng.randn(n) * 0.3
    body_lo = pd.concat([open_, close], axis=1).min(axis=1)
    body_hi = pd.concat([open_, close], axis=1).max(axis=1)
    low = body_lo - (np.abs(rng.randn(n)) * 0.3 + 0.01)
    high = body_hi + (np.abs(rng.randn(n)) * 0.3 + 0.01)

    open_ *= scale
    high *= scale
    low *= scale
    close *= scale
    body_lo *= scale
    body_hi *= scale

    # Non-negotiable #2: physically valid OHLC in every fixture.
    assert (low < body_lo).all() and (body_hi < high).all(), \
        "fixture bug: OHLC must satisfy low <= min(open,close) and max(open,close) <= high"

    # Non-negotiable #3: canary INSIDE the fixture, not size-gated -- trips
    # on a constant/NaN stub sneaking back in during a refactor.
    assert close.notna().all() and high.notna().all() and low.notna().all(), \
        "fixture bug: NaN stub in OHLC"
    assert close.nunique() > n * 0.5, \
        "fixture bug: close is degenerate/near-constant -- not a real price path"
    assert close.std() > 1e-6, "fixture bug: close has ~zero variance"

    return open_, high, low, close


# ---------------------------------------------------------------------------
# Independent reference implementation. NOT a copy-paste of
# pandas_ta/overlap/iama.py's vectorized numpy code -- a separately-
# derived, plain-Python, per-bar loop transcription of the source .pine's
# own variable names and formulas (docs/TradingView/pine/
# 6SVLw0kE-Institutional-Moving-Averages.pine L98-133), used to
# cross-check the production function's composition (gate (d)). The ATR
# leaf is delegated to this fork's own `atr()` (same primitive production
# calls, `rma()`-backed) rather than hand-re-derived -- Wilder RMA
# correctness is a solved, separately-tested question elsewhere in this
# fork (see pressure_pulse's own test file for that story); re-deriving
# it here would test pandas' `ewm()`, not this indicator's composition.
# ---------------------------------------------------------------------------
def _reference_iama(high, low, close, length=9, k=1.0, atr_length=14,
                     norm_length=50, min_tick=1e-8, rel_floor=2.5e-3):
    from pandas_ta.volatility import atr as _leaf_atr

    n = len(close)
    c = list(close)

    # f_squash(x) = x / (1 + |x|)
    def squash(x):
        return x / (1.0 + abs(x))

    # f_efficiency(s, len): dir = |s - s[len]|, pth = SUM(|s-s[1]|, len)
    # (trailing len-bar window), eff = pth>0 ? min(dir/pth,1) : 0. Both
    # terms undefined (None) until `length` bars of history exist.
    eff = [None] * n
    for i in range(n):
        if i < length:
            continue
        dir_ = abs(c[i] - c[i - length])
        pth = sum(abs(c[j] - c[j - 1]) for j in range(i - length + 1, i + 1))
        eff[i] = 0.0 if pth == 0.0 else min(dir_ / pth, 1.0)

    atr_s = _leaf_atr(pd.Series(list(high)), pd.Series(list(low)), pd.Series(c),
                       length=atr_length, mamode="rma")
    atr_vals = [None if pd.isna(x) else float(x) for x in atr_s]

    atr_avg = [None] * n
    for i in range(n):
        if i < norm_length - 1:
            continue
        window = [atr_vals[j] for j in range(i - norm_length + 1, i + 1)]
        if any(v is None for v in window):
            continue
        atr_avg[i] = sum(window) / norm_length

    vol_ratio = [1.0 if (atr_avg[i] is None or atr_avg[i] <= 0.0) else atr_vals[i] / atr_avg[i]
                 for i in range(n)]

    slope_len = max(1, int(np.floor(length / 3.0 + 0.5)))

    ima = [None] * n
    dist = [None] * n
    for i in range(n):
        prev = ima[i - 1] if i > 0 else None
        if prev is None:
            ima[i] = c[i]
        elif eff[i] is None or atr_vals[i] is None:
            ima[i] = None  # alpha undefined -> na
        else:
            slope_ref = c[i - slope_len] if i - slope_len >= 0 else c[i]
            tick_floor = max(min_tick, rel_floor * abs(c[i]))
            safe_atr = max(atr_vals[i], tick_floor)
            slope = abs(c[i] - slope_ref) / safe_atr
            drive = min(1.0, 0.65 * eff[i] + 0.35 * squash(slope))
            v_adj = min(1.5, max(0.6, vol_ratio[i]))
            fast_a = 2.0 / (max(2.0, length / (2.0 + k)) + 1.0)
            slow_a = 2.0 / (length * (1.0 + k * 0.5) + 1.0)
            alpha = (slow_a + drive * (fast_a - slow_a)) ** 2 * v_adj
            alpha = min(1.0, max(0.001, alpha))
            ima[i] = prev + alpha * (c[i] - prev)
        dist[i] = None if ima[i] is None else (c[i] - ima[i]) / ima[i] * 100.0

    return pd.Series([np.nan if v is None else v for v in dist], index=close.index)


def test_correctness_vs_independent_reference_default_params():
    _, high, low, close = _ohlcv(n=150, seed=1)
    prod = ta.iama(high=high, low=low, close=close)
    ref = _reference_iama(high, low, close)
    pdt.assert_series_equal(prod.reset_index(drop=True), ref.reset_index(drop=True),
                             check_names=False, rtol=1e-8, atol=1e-8)


def test_correctness_vs_independent_reference_custom_params():
    _, high, low, close = _ohlcv(n=150, seed=2)
    prod = ta.iama(high=high, low=low, close=close, length=14, k=0.6,
                    atr_length=10, norm_length=30)
    ref = _reference_iama(high, low, close, length=14, k=0.6,
                           atr_length=10, norm_length=30)
    pdt.assert_series_equal(prod.reset_index(drop=True), ref.reset_index(drop=True),
                             check_names=False, rtol=1e-8, atol=1e-8)


def test_bar_zero_is_closed_form():
    """out[0] = close[0] unconditionally (na(out[-1]) is always true at
    bar 0) -> IAMA_DIST[0] == exactly 0.0 for ANY valid params."""
    _, high, low, close = _ohlcv(n=60, seed=3)
    out = ta.iama(high=high, low=low, close=close, length=5)
    assert out.iloc[0] == pytest.approx(0.0, abs=1e-12)


def test_fixture_nondegenerate_at_literal_defaults():
    _, high, low, close = _ohlcv(n=200, seed=0)
    out = ta.iama(high=high, low=low, close=close)
    n_notna = int(out.notna().sum())
    n_nonzero = int((out.fillna(0.0).abs() > 1e-9).sum())
    print(f"IAMA_DIST @ literal defaults: n={len(out)}, notna={n_notna}, "
          f"nonzero={n_nonzero}, min={out.min():.4f}, max={out.max():.4f}, "
          f"mean={out.mean():.4f}")
    assert n_notna >= 190, f"expected most of 200 bars populated, got {n_notna}"
    assert n_nonzero >= 150, f"expected most bars non-(near-)zero, got {n_nonzero}"
    assert out.std() > 0.1, "output collapsed to a near-constant series"


def test_flat_price_eff_and_slope_are_zero():
    """Deliberately degenerate fixture (flat OHLC) -- NOT the main
    fixture, used specifically to pin f_efficiency's explicit `pth>0 ?
    ... : 0.0` branch and confirm a flat run does not raise/blow up.
    With close constant, dir=0 and pth=0 for every full window -> eff=0
    exactly (the guarded branch, not a 0/0 NaN); slope's numerator is
    also 0 regardless of the ATR floor -> squash(0)=0 -> drive=0. Once
    `ima` locks onto the constant close value, close[t]-ima[t-1]==0 keeps
    it there, so IAMA_DIST is exactly 0.0 wherever defined."""
    n = 60
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(50.0, index=idx)
    high = pd.Series(50.5, index=idx)
    low = pd.Series(49.5, index=idx)
    out = ta.iama(high=high, low=low, close=close, length=9)
    defined = out.dropna()
    assert len(defined) > 0
    assert (defined.abs() < 1e-9).all(), f"expected exactly 0.0 on a flat series, got {defined.unique()}"


def test_scale_free_by_construction():
    """(close-ima)/ima*100 is invariant under multiplying the whole OHLC
    block by a positive constant -- verified by EXECUTION on two
    different scales, not asserted from the algebra alone."""
    _, high1, low1, close1 = _ohlcv(n=150, seed=4, scale=1.0)
    _, high2, low2, close2 = _ohlcv(n=150, seed=4, scale=1000.0)
    out1 = ta.iama(high=high1, low=low1, close=close1)
    out2 = ta.iama(high=high2, low=low2, close=close2)
    pdt.assert_series_equal(out1.reset_index(drop=True), out2.reset_index(drop=True),
                             check_names=False, rtol=1e-6, atol=1e-6)


def test_mutation_only_changes_current_and_later_bars():
    """IIR recursion causality: mutating bar T's close changes bar T and
    every bar strictly AFTER T (via the carried `ima[t-1]` state and the
    backward-looking eff/slope windows that include bar T), and must
    change NOTHING strictly before T.

    The whole bar (open/high/low/close) is shifted by the SAME delta --
    a pure parallel translation -- rather than bumping close alone, which
    would produce a physically invalid bar (close > high) in this exact
    file whose own `_ohlcv` helper asserts strict OHLC validity. iama
    itself only consumes high/low/close, but keeping open in lockstep
    means the mutated frame stays representationally valid throughout,
    not just at fixture-construction time."""
    open_, high, low, close = _ohlcv(n=150, seed=5)
    base = ta.iama(high=high, low=low, close=close)

    mutate_at = 100
    delta = 5.0
    open2, high2, low2, close2 = open_.copy(), high.copy(), low.copy(), close.copy()
    open2.iloc[mutate_at] += delta
    high2.iloc[mutate_at] += delta
    low2.iloc[mutate_at] += delta
    close2.iloc[mutate_at] += delta
    assert low2.iloc[mutate_at] < min(open2.iloc[mutate_at], close2.iloc[mutate_at]) \
        and max(open2.iloc[mutate_at], close2.iloc[mutate_at]) < high2.iloc[mutate_at], \
        "mutated bar must stay physically valid OHLC (parallel shift should guarantee this)"
    out2 = ta.iama(high=high2, low=low2, close=close2)

    before = base.iloc[:mutate_at]
    before2 = out2.iloc[:mutate_at]
    pdt.assert_series_equal(before, before2, check_names=False)

    after = base.iloc[mutate_at:]
    after2 = out2.iloc[mutate_at:]
    diffs = (after != after2) & ~(after.isna() & after2.isna())
    assert diffs.any(), "mutating bar T should change bar T and/or later bars"
    # Tighten beyond "any bar differs": the mutated bar T itself, and the
    # LAST bar of the series (proving the change propagates all the way
    # through the recursion, not just for a few bars before decaying back
    # to coincidence), must both differ.
    first_after = after.iloc[0]
    first_after2 = after2.iloc[0]
    assert not (pd.isna(first_after) and pd.isna(first_after2)) and first_after != first_after2, \
        "mutated bar T itself must differ"
    last_after = after.iloc[-1]
    last_after2 = after2.iloc[-1]
    assert not (pd.isna(last_after) and pd.isna(last_after2)) and last_after != last_after2, \
        "the LAST bar of the series must still differ -- the mutation's effect must propagate " \
        "through the whole recursion, not just touch a few nearby bars"


def test_no_lookahead_truncation():
    """Computing on a prefix of the series must reproduce the full run's
    values over that same prefix exactly -- proves no forward-looking
    dependency. The compared window (100:130) sits well past this
    fixture's own warmup (verified empirically: default params + n=200
    stabilize into a non-oscillating recursion by bar 15, see
    test_fixture_nondegenerate_at_literal_defaults's own printed stats),
    so this is checking real recursive signal, not NaN-vs-NaN warmup."""
    _, high, low, close = _ohlcv(n=200, seed=6)
    full = ta.iama(high=high, low=low, close=close)

    truncated_n = 130
    trunc = ta.iama(high=high.iloc[:truncated_n], low=low.iloc[:truncated_n],
                     close=close.iloc[:truncated_n])

    window = slice(100, 130)
    full_window = full.iloc[window]
    trunc_window = trunc.iloc[window]
    assert full_window.notna().all() and trunc_window.notna().all(), \
        "comparison window must carry real (non-NaN) signal, not warmup"
    assert full_window.std() > 0.1, "comparison window is degenerate/flat"
    pdt.assert_series_equal(full_window, trunc_window, check_names=False)


def test_single_nan_close_raises():
    _, high, low, close = _ohlcv(n=60, seed=7)
    close = close.copy()
    close.iloc[30] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        ta.iama(high=high, low=low, close=close)


def test_inf_high_raises():
    _, high, low, close = _ohlcv(n=60, seed=8)
    high = high.copy()
    high.iloc[10] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        ta.iama(high=high, low=low, close=close)


def test_non_numeric_dtype_raises():
    _, high, low, close = _ohlcv(n=60, seed=9)
    close = close.astype(str)
    with pytest.raises(ValueError, match="numeric"):
        ta.iama(high=high, low=low, close=close)


def test_non_integral_length_raises():
    _, high, low, close = _ohlcv(n=60, seed=10)
    with pytest.raises(ValueError, match="integral"):
        ta.iama(high=high, low=low, close=close, length=9.5)


def test_length_below_pine_minval_raises():
    _, high, low, close = _ohlcv(n=60, seed=11)
    with pytest.raises(ValueError, match=r">= 2"):
        ta.iama(high=high, low=low, close=close, length=1)


def test_k_out_of_pine_bounds_raises():
    _, high, low, close = _ohlcv(n=60, seed=12)
    with pytest.raises(ValueError, match=r"\[0\.1, 3\.0\]"):
        ta.iama(high=high, low=low, close=close, k=5.0)


def test_atr_length_out_of_pine_bounds_raises():
    _, high, low, close = _ohlcv(n=60, seed=13)
    with pytest.raises(ValueError):
        ta.iama(high=high, low=low, close=close, atr_length=1)


def test_norm_length_out_of_pine_bounds_raises():
    _, high, low, close = _ohlcv(n=60, seed=14)
    with pytest.raises(ValueError):
        ta.iama(high=high, low=low, close=close, norm_length=5)


def test_mismatched_lengths_raises():
    _, high, low, close = _ohlcv(n=60, seed=15)
    with pytest.raises(ValueError, match="same length"):
        ta.iama(high=high, low=low, close=close.iloc[:-5])


def test_negative_min_tick_raises():
    _, high, low, close = _ohlcv(n=60, seed=16)
    with pytest.raises(ValueError, match="positive"):
        ta.iama(high=high, low=low, close=close, min_tick=-1.0)


def test_insufficient_history_returns_none():
    _, high, low, close = _ohlcv(n=5, seed=17)
    assert ta.iama(high=high, low=low, close=close, length=9, atr_length=14,
                    norm_length=50) is None


def test_reachability_via_accessor():
    _, high, low, close = _ohlcv(n=150, seed=18)
    df = pd.DataFrame({"High": high, "Low": low, "Close": close})
    direct = ta.iama(high=df["High"], low=df["Low"], close=df["Close"])
    via_accessor = df.ta.iama()
    pdt.assert_series_equal(direct.reset_index(drop=True), via_accessor.reset_index(drop=True),
                             check_names=False)


def test_reachability_via_accessor_custom_params():
    _, high, low, close = _ohlcv(n=150, seed=19)
    df = pd.DataFrame({"High": high, "Low": low, "Close": close})
    direct = ta.iama(high=df["High"], low=df["Low"], close=df["Close"],
                      length=21, k=1.5, atr_length=20, norm_length=60)
    via_accessor = df.ta.iama(length=21, k=1.5, atr_length=20, norm_length=60)
    pdt.assert_series_equal(direct.reset_index(drop=True), via_accessor.reset_index(drop=True),
                             check_names=False)


def test_column_name():
    _, high, low, close = _ohlcv(n=150, seed=20)
    out = ta.iama(high=high, low=low, close=close, length=14, k=0.6,
                   atr_length=10, norm_length=30)
    assert out.name == "IAMA_DIST_14_0.6_10_30"
    assert out.category == "overlap"


def test_offset_shifts_result():
    _, high, low, close = _ohlcv(n=150, seed=21)
    out0 = ta.iama(high=high, low=low, close=close)
    out1 = ta.iama(high=high, low=low, close=close, offset=1)
    shifted = out0.shift(1)
    pdt.assert_series_equal(out1.reset_index(drop=True), shifted.reset_index(drop=True),
                             check_names=False)


def test_fillna_kwarg():
    _, high, low, close = _ohlcv(n=150, seed=22)
    out = ta.iama(high=high, low=low, close=close, fillna=0.0)
    assert not out.isna().any()
