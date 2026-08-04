# tests/test_ribbon_concordance.py
"""ribbon_concordance -- pairwise rank-concordance of an N-MA ribbon
(TVPTA-3-composite, ported from "Ribbon Concordance [RC Tools]"). Self-
contained on synthetic data.

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


def test_name_and_series():
    close = _close()
    out = ta.ribbon_concordance(close, ma_type="ema", base_length=5, spacing=5, ribbon_size=8)
    assert isinstance(out, pd.Series)
    assert out.name == "RIBBONCONC_EMA_5_5_8"


def test_bounded_and_extremes():
    # A strictly monotonically rising series -> every shorter-period SMA
    # sits above every longer-period one -> full bullish alignment -> the
    # raw score is +100 every bar once all 3 MAs have warmed up (no
    # post-smoothing, so the identity holds exactly, not just "near 100").
    close = pd.Series(np.arange(1.0, 101.0))
    out = ta.ribbon_concordance(close, ma_type="sma", base_length=3, spacing=2,
                                 ribbon_size=3, smooth_length=1)
    valid = out.dropna()
    assert len(valid) > 0
    assert valid.to_numpy() == pytest.approx(100.0)


def test_correctness_independent_recompute():
    # smooth_length=3 (the module's actual default) -- Fletcher round 2:
    # smooth_length=1 takes a different code branch (no EMA at all) and
    # is blind to bugs in the smoothing/gating interaction.
    close = _close(n=120)
    smooth_length = 3
    out = ta.ribbon_concordance(close, ma_type="ema", base_length=4, spacing=3,
                                 ribbon_size=4, smooth_length=smooth_length)

    lengths = [4, 7, 10, 13]
    ribbon = [ta.ema(close, length=length) for length in lengths]
    concordance_sum = pd.Series(0.0, index=close.index)
    pair_count = pd.Series(0.0, index=close.index)
    for i in range(len(ribbon) - 1):
        for j in range(i + 1, len(ribbon)):
            vi, vj = ribbon[i], ribbon[j]
            both_valid = vi.notna() & vj.notna()
            sign = pd.Series(0.0, index=close.index)
            sign[both_valid & (vi > vj)] = 1.0
            sign[both_valid & (vi < vj)] = -1.0
            concordance_sum += sign
            pair_count += both_valid.astype(float)
    raw = (concordance_sum / pair_count.replace(0, np.nan)) * 100.0
    # Source order (Fletcher round 2): smooth the UNGATED raw series
    # first, THEN gate the result -- not gate-then-smooth (round 1's
    # fix got this backwards; see test_smoothing_runs_on_ungated_raw_not_post_gate).
    expected = ta.ema(raw, length=smooth_length).where(ribbon[-1].notna())

    pdt.assert_series_equal(out, expected, check_names=False)


def test_no_partial_ribbon_score_before_full_warmup():
    # MAJOR regression (Fletcher round 1): the source explicitly gates
    # its output behind `warmedUp = bar_index >= longestPeriod` -- an
    # earlier version of this port had no such gate and emitted a score
    # as soon as just the two SHORTEST MAs were valid, up to
    # (ribbon_size-1)*spacing bars before the source would ever emit
    # anything.
    close = _close(n=60)
    base_length, spacing, ribbon_size = 4, 3, 4
    longest = base_length + (ribbon_size - 1) * spacing  # 13
    out = ta.ribbon_concordance(close, ma_type="ema", base_length=base_length,
                                 spacing=spacing, ribbon_size=ribbon_size, smooth_length=1)

    # The two shortest MAs (lengths 4 and 7) are both valid well before
    # bar `longest`-1 -- confirm the fixture actually creates the gap
    # this test is checking, then confirm the module output is NaN
    # throughout that gap.
    short_ma_a = ta.ema(close, length=base_length)
    short_ma_b = ta.ema(close, length=base_length + spacing)
    both_short_valid = short_ma_a.notna() & short_ma_b.notna()
    gap = both_short_valid.to_numpy()[: longest - 1]
    assert gap.any(), "fixture must actually produce an early-partial-ribbon window to test the gate"

    assert out.iloc[: longest - 1].isna().all()


def test_smoothing_runs_on_ungated_raw_not_post_gate():
    # MAJOR regression (Fletcher round 2): round 1's warmup-gate fix
    # masked `raw_concordance` to NaN BEFORE feeding it to `ema()`,
    # forcing the EMA to restart cold exactly when the gate opens and
    # discarding all the pre-warmup smoothing history the source's EMA
    # (computed on the ALWAYS-LIVE raw score) would already have
    # accumulated. Requires smooth_length > 1 (the module's own default)
    # to exercise at all -- every other value-asserting test in this file
    # uses smooth_length=1, which takes the no-EMA branch and is
    # structurally blind to this bug. Also requires a fixture whose raw
    # concordance genuinely OSCILLATES before full warmup (a monotonic
    # trend makes masked-vs-unmasked EMA state identical and would not
    # have caught this the first time).
    n = 40
    # Oscillating short-run (bars 0-24) so the two shortest MAs flip
    # order repeatedly before the full 4-MA ribbon (longest length 13)
    # warms up, then a clean trend for the rest.
    vals = []
    for i in range(25):
        vals.append(100.0 + (5.0 if i % 4 < 2 else -5.0))
    vals += [100.0 + i * 2.0 for i in range(1, 16)]
    close = pd.Series(vals)

    base_length, spacing, ribbon_size, smooth_length = 4, 3, 4, 3
    out = ta.ribbon_concordance(close, ma_type="ema", base_length=base_length,
                                 spacing=spacing, ribbon_size=ribbon_size,
                                 smooth_length=smooth_length)

    lengths = [base_length + i * spacing for i in range(ribbon_size)]
    ribbon = [ta.ema(close, length=length) for length in lengths]
    concordance_sum = pd.Series(0.0, index=close.index)
    pair_count = pd.Series(0.0, index=close.index)
    for i in range(len(ribbon) - 1):
        for j in range(i + 1, len(ribbon)):
            vi, vj = ribbon[i], ribbon[j]
            both_valid = vi.notna() & vj.notna()
            sign = pd.Series(0.0, index=close.index)
            sign[both_valid & (vi > vj)] = 1.0
            sign[both_valid & (vi < vj)] = -1.0
            concordance_sum += sign
            pair_count += both_valid.astype(float)
    raw = (concordance_sum / pair_count.replace(0, np.nan)) * 100.0

    # Source-faithful: smooth the UNGATED raw series, gate the result.
    correct = ta.ema(raw, length=smooth_length).where(ribbon[-1].notna())
    # The bug this test targets: gate BEFORE smoothing.
    buggy = ta.ema(raw.where(ribbon[-1].notna()), length=smooth_length)

    first_valid = correct.first_valid_index()
    assert first_valid is not None
    # The fixture must actually make the two orderings disagree -- proves
    # this is a real, exercised discrepancy, not a vacuous comparison.
    assert not np.isclose(correct[first_valid], buggy[first_valid], atol=1e-6), \
        "fixture must produce a genuine pre-smoothing-vs-post-smoothing gate discrepancy"

    pdt.assert_series_equal(out, correct, check_names=False)


def test_full_warmup_matches_longest_ma():
    close = _close(n=60)
    base_length, spacing, ribbon_size = 4, 3, 4
    out = ta.ribbon_concordance(close, ma_type="ema", base_length=base_length,
                                 spacing=spacing, ribbon_size=ribbon_size, smooth_length=1)
    longest_ma = ta.ema(close, length=base_length + (ribbon_size - 1) * spacing)
    pdt.assert_series_equal(out.notna(), longest_ma.notna(), check_names=False)


def test_no_lookahead():
    close = _close()
    T = 100
    out_full = ta.ribbon_concordance(close)

    close_c = close.copy()
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.ribbon_concordance(close_c)

    pdt.assert_series_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    close = _close()
    df = pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "ribbon_concordance" in ta.Category["trend"]
    assert callable(getattr(df.ta, "ribbon_concordance"))

    module_result = ta.ribbon_concordance(close=close)
    accessor_result = df.ta.ribbon_concordance()
    pdt.assert_series_equal(module_result, accessor_result)
