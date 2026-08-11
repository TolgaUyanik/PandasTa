# tests/test_bpress.py
"""bpress -- TVPTA continuation port of `bubblePressure` from the
TradingView "Bitcoin Critical State Indicator (BCSI)" script (RiUxCPkj,
by BorisTheBlade687, https://www.tradingview.com/script/RiUxCPkj/).

BCSI is a 7-component weighted composite rescaled to a BTC-tuned 0-100
regime gauge; ONLY the `bubblePressure` sub-component (a log-price
rolling-regression residual) is ported here. See pandas_ta/overlap/bpress.py
module docstring for the full list of what was deliberately left out
(cycleScore's BTC-genesis wall-clock modulo, and every other component's
BTC-tuned normalize() bounds) and why.

Reachability tests `import pandas_ta`, NOT
`importlib.util.spec_from_file_location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta


def _close(n=600, seed=0):
    rng = np.random.RandomState(seed)
    return pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )


def _log_linear_close(n=600, growth=0.001, start=100.0):
    """A price series whose log is EXACTLY linear in bar index -- the
    regression residual against this fixture is analytically zero
    everywhere past the warmup window, giving an exact hand-derivable
    expected value (0.0) rather than an approximate one."""
    t = np.arange(n)
    return pd.Series(
        start * np.exp(growth * t),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )


# ---------------------------------------------------------------------------
# (a) Correctness
# ---------------------------------------------------------------------------

def test_pandas_ta_linreg_tsf_matches_current_bar_fit():
    """Pin down the pandas_ta `linreg()` semantics this port depends on.

    Pine's `ta.linreg(src, length, offset=0)` evaluates the trailing OLS
    fit AT the current (rightmost) bar of the window. pandas_ta's own
    `linreg()` parameterizes x as [1..length] (x=length == current bar),
    but its DEFAULT return (tsf=False) is `m*(length-1)+b` -- the fit ONE
    BAR BEHIND the current bar, not at it. Only `tsf=True` (`m*length+b`)
    matches Pine. This test verifies both facts against an independent
    numpy.polyfit reference so the choice in bpress.py is not just
    asserted in a comment -- it is proven per gate (b) of TVPTA-3
    ("Pine->pandas semantics verified against the FORK's source, not
    memory... a wrong kwarg name is silently swallowed by **kwargs").
    """
    from pandas_ta.overlap.linreg import linreg as _linreg

    rng = np.random.RandomState(1)
    n, length = 60, 10
    y = np.cumsum(rng.randn(n)) + 100
    s = pd.Series(y)

    lr_default = _linreg(s, length=length)
    lr_tsf = _linreg(s, length=length, tsf=True)

    def _fit_at_point(window, x_eval):
        x = np.arange(len(window))
        m, b = np.polyfit(x, window, 1)
        return m * x_eval + b

    def _fit_at_last_point(window):
        return _fit_at_point(window, len(window) - 1)

    def _fit_at_prev_point(window):
        return _fit_at_point(window, len(window) - 2)

    manual_current = [
        _fit_at_last_point(y[i - length + 1:i + 1])
        for i in range(length - 1, n)
    ]
    manual_current = pd.Series(manual_current, index=range(length - 1, n))

    manual_prev = [
        _fit_at_prev_point(y[i - length + 1:i + 1])
        for i in range(length - 1, n)
    ]
    manual_prev = pd.Series(manual_prev, index=range(length - 1, n))

    tsf_diff = (lr_tsf.iloc[length - 1:].reset_index(drop=True)
                - manual_current.reset_index(drop=True)).abs().max()
    default_diff = (lr_default.iloc[length - 1:].reset_index(drop=True)
                    - manual_prev.reset_index(drop=True)).abs().max()

    assert tsf_diff < 1e-9, "tsf=True must match the current-bar OLS fit"
    # Strong claim (Fletcher round 1 MINOR): not just "default != current-bar
    # fit" but "default IS EXACTLY the one-bar-behind fit" -- independently
    # re-derived by review at 1.28e-13 on a different seed/window than this
    # test's, confirming the mechanism, not just the symptom.
    assert default_diff < 1e-9, (
        "the untagged default must match the ONE-BAR-BEHIND OLS fit exactly "
        "-- proving *why* tsf=True is required, not just that the default "
        "disagrees with the current-bar fit"
    )


def test_zero_residual_on_exact_log_linear_trend():
    """Hand-derivable fixture: if log(close) is EXACTLY linear in bar
    index, the rolling regression line coincides with log(close) itself
    at every bar past the warmup window, so the residual (bpress) must be
    ~0 everywhere in that region. This is the (a) correctness gate's
    "known input -> known output" case, not just "runs and returns
    something bounded"."""
    length = 500
    close = _log_linear_close(n=600, growth=0.001)
    out = ta.bpress(close, length=length)

    warm = out.iloc[length - 1:]
    assert warm.notna().all()
    assert warm.abs().max() < 1e-9


def test_known_deviation_from_trend():
    """A single-bar deviation from an otherwise perfectly log-linear
    trend produces a residual close to that deviation's log-return, since
    a one-bar bump barely moves a 500-bar OLS fit."""
    length = 500
    close = _log_linear_close(n=600, growth=0.001)
    bumped = close.copy()
    bump_factor = 1.05
    bumped.iloc[-1] = bumped.iloc[-1] * bump_factor

    out = ta.bpress(bumped, length=length)
    # The regression line barely moves from a single new point in a
    # 500-bar window, so the residual is close to log(bump_factor).
    assert out.iloc[-1] == pytest.approx(np.log(bump_factor), abs=5e-3)


# ---------------------------------------------------------------------------
# (b) Causality
# ---------------------------------------------------------------------------

def test_causal_future_mutation_does_not_change_past_output():
    """Actual mutation test (not just 'regression is causal by
    definition'): mutate close AFTER bar k, assert bpress at and before
    bar k is bit-for-bit unchanged."""
    length = 500
    close = _close(n=600)
    out_before = ta.bpress(close, length=length)

    k = 549
    mutated = close.copy()
    mutated.iloc[k + 1:] = mutated.iloc[k + 1:] * 2.0
    out_after = ta.bpress(mutated, length=length)

    pd.testing.assert_series_equal(
        out_before.iloc[:k + 1], out_after.iloc[:k + 1]
    )
    # And the mutated region actually did change -- otherwise this test
    # would trivially pass by the function ignoring its input.
    assert not np.isclose(out_before.iloc[k + 1], out_after.iloc[k + 1])


def test_causal_future_deletion_does_not_change_past_output():
    """Same causality claim, via truncation instead of mutation: dropping
    all bars after bar k must not change bpress computed up to bar k."""
    length = 500
    close = _close(n=600)
    out_full = ta.bpress(close, length=length)

    k = 560
    truncated = close.iloc[: k + 1]
    out_truncated = ta.bpress(truncated, length=length)

    pd.testing.assert_series_equal(out_full.iloc[: k + 1], out_truncated)


# ---------------------------------------------------------------------------
# (c) Reachability
# ---------------------------------------------------------------------------

def test_reachable_via_category_and_accessor():
    assert "bpress" in ta.Category["overlap"]

    close = _close()
    df = pd.DataFrame({"close": close})
    assert callable(getattr(df.ta, "bpress"))

    direct = ta.bpress(close, length=500)
    via_accessor = df.ta.bpress(length=500)
    pd.testing.assert_series_equal(direct, via_accessor)


def test_output_name_encodes_length():
    close = _close()
    out = ta.bpress(close, length=250)
    assert out.name == "BPRESS_250"


# ---------------------------------------------------------------------------
# (d) Scale-free
# ---------------------------------------------------------------------------

def test_scale_invariance():
    """bpress is a log-price residual: log(k*close) = log(close) + log(k),
    and a rolling OLS fit shifts by the same additive constant when its
    input does, so the residual (fit subtracted from log-price) cancels
    the constant exactly. Verified directly across several scale factors,
    not just asserted in the docstring."""
    length = 500
    close = _close()
    base = ta.bpress(close, length=length)

    for k in (0.001, 0.5, 2.0, 1000.0, 1e6):
        scaled = ta.bpress(close * k, length=length)
        pd.testing.assert_series_equal(
            base, scaled, check_exact=False, atol=1e-9
        )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_rejects_non_finite_length():
    close = _close()
    with pytest.raises(ValueError):
        ta.bpress(close, length=float("nan"))
    with pytest.raises(ValueError):
        ta.bpress(close, length=float("inf"))


def test_rejects_non_positive_length():
    close = _close()
    with pytest.raises(ValueError):
        ta.bpress(close, length=0)
    with pytest.raises(ValueError):
        ta.bpress(close, length=-10)


def test_rejects_non_positive_close():
    close = _close(n=600)
    bad = close.copy()
    bad.iloc[10] = 0.0
    with pytest.raises(ValueError):
        ta.bpress(bad, length=500)

    bad2 = close.copy()
    bad2.iloc[10] = -5.0
    with pytest.raises(ValueError):
        ta.bpress(bad2, length=500)


def test_rejects_non_integral_length():
    """Fletcher round 1 MAJOR: a fractional length used to silently
    truncate (`int(500.7) == 500`) while the output Series stayed named
    'BPRESS_500', misreporting the window actually used. Must raise
    instead of coercing."""
    close = _close()
    with pytest.raises(ValueError):
        ta.bpress(close, length=500.7)
    with pytest.raises(ValueError):
        ta.bpress(close, length=500.5)
    # A float with no fractional part is fine -- it's genuinely integral.
    out = ta.bpress(close, length=250.0)
    assert out.name == "BPRESS_250"


def test_rejects_non_numeric_length():
    """Fletcher round 1 MAJOR: a non-numeric length used to leak a raw
    TypeError out of `np.isfinite('500')` instead of the ValueError this
    function's docstring promises -- and since indicator_engine.py wraps
    every call in a bare `except Exception`, that TypeError silently
    dropped the column with no visible failure. Must be ValueError,
    specifically, not merely 'raises something'."""
    close = _close()
    with pytest.raises(ValueError):
        ta.bpress(close, length="500")
    # bool is an int subclass in Python -- `length=True` must not silently
    # become length=1.
    with pytest.raises(ValueError):
        ta.bpress(close, length=True)


def test_rejects_non_finite_close():
    """Fletcher round 1 MINOR: `(close <= 0).any()` never fires on +/-inf
    (inf > 0), yet `log(inf) == inf` poisons every rolling window
    containing it -- silently, with no error, indistinguishable from
    'not enough history yet'. A single inf must be rejected outright."""
    close = _close(n=600)
    with_pos_inf = close.copy()
    with_pos_inf.iloc[300] = np.inf
    with pytest.raises(ValueError):
        ta.bpress(with_pos_inf, length=500)

    with_neg_inf = close.copy()
    with_neg_inf.iloc[300] = -np.inf
    with pytest.raises(ValueError):
        ta.bpress(with_neg_inf, length=500)


def test_rejects_non_numeric_close_dtype():
    """Fletcher round 2 NIT: `np.isinf()` on an object-dtype Series (e.g.
    a caller accidentally passing strings) used to leak a raw TypeError,
    not the ValueError this function's other validation guarantees --
    same class of gap the length-validation MAJOR fix closed. Must be
    ValueError, specifically."""
    bad = pd.Series(["a"] * 600, index=_close(n=600).index, dtype=object)
    with pytest.raises(ValueError):
        ta.bpress(bad, length=500)


def test_nan_close_propagates_but_does_not_raise():
    """Companion to the finite-close test above: NaN (as opposed to inf)
    is legitimate upstream-gap data, not rejected -- but it nulls every
    rolling window that contains it, i.e. `length` bars of output
    (indices `[gap_at, gap_at + length - 1]`), by construction (rolling
    regression sums a NaN in).

    Fletcher round 2 MAJOR: the original fixture (n=700, gap_at=300,
    length=500) made `out.iloc[gap_at:poisoned_end+1]` cover almost the
    ENTIRE 700-row series (poisoned_end=799 > 699), so "poisoned span is
    NaN" was trivially true for ANY reason including "bpress is just
    broken and returns all-NaN" -- and the "resumes after" slice
    (`out.iloc[800:]` on a 700-row Series) was an EMPTY slice, so
    `.notna().all()` passed vacuously, testing nothing. Resized so all
    three regions (pre-gap / poisoned / resumed) are non-empty and
    verified with an exact count guard that an all-NaN output cannot
    satisfy.
    """
    length = 500
    gap_at = 600
    n = 1400
    close = _close(n=n)
    gapped = close.copy()
    gapped.iloc[gap_at] = np.nan

    out = ta.bpress(gapped, length=length)  # must not raise
    assert out is not None

    pre_gap = out.iloc[length - 1:gap_at]
    poisoned = out.iloc[gap_at:gap_at + length]
    tail = out.iloc[gap_at + length:]

    assert len(pre_gap) > 0
    assert len(poisoned) == length
    assert len(tail) > 0

    assert pre_gap.notna().all(), "output before the gap must be clean"
    assert poisoned.isna().all(), "every window containing the NaN must be NaN"
    assert tail.notna().all(), "output must resume once the gap rolls out of every window"

    # Count guard: an all-NaN (or otherwise broken) output cannot satisfy
    # this exact arithmetic, unlike the vacuous slice-based checks alone.
    expected_notna = len(pre_gap) + len(tail)
    assert out.notna().sum() == expected_notna


# ---------------------------------------------------------------------------
# offset / fillna kwargs (Fletcher round 1 NIT: documented and live but
# previously untested; offset in particular could silently break causality
# if a caller passed a negative value, which shifts future data backward).
# ---------------------------------------------------------------------------

def test_offset_shifts_output():
    close = _close()
    base = ta.bpress(close, length=500)
    shifted = ta.bpress(close, length=500, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_negative_offset_shifts_backward_non_causal():
    """A negative offset pulls FUTURE bars' values backward -- explicitly
    non-causal. bpress() does not forbid it (matches every other
    pandas_ta indicator's `offset` kwarg), but it must behave exactly
    like `Series.shift(-1)`, i.e. the caller owns the causality break,
    not a bug in this function."""
    close = _close()
    base = ta.bpress(close, length=500)
    shifted = ta.bpress(close, length=500, offset=-1)
    pd.testing.assert_series_equal(shifted, base.shift(-1), check_names=False)


def test_fillna_kwarg_fills_leading_nan():
    close = _close()
    out = ta.bpress(close, length=500, fillna=0.0)
    assert out.isna().sum() == 0
    assert (out.iloc[:499] == 0.0).all()


def test_fill_method_kwarg():
    """`fill_method` (via `Series.fillna(method=...)`) is a documented,
    live kwarg but was previously untested. Uses a pandas API deprecated
    in >=2.1 and removed in 3.0 -- see the in-source comment in
    bpress.py -- so this test also acts as a canary: it will start
    failing the moment the installed pandas version drops support,
    which is exactly when the migration noted there becomes mandatory."""
    close = _close()
    out = ta.bpress(close, length=500, fill_method="bfill")
    assert out.isna().sum() == 0


def test_returns_none_when_series_shorter_than_length():
    """Fletcher round 2 MINOR: `length > len(close)` returns None via
    `verify_series` (pandas_ta convention) with NO error and NO warning
    from this function -- silent by design, matching every other
    indicator in this module, but easy to miss (a <500-bar ticker's
    BPRESS_500 column just vanishes). Pinned here as documented,
    intentional behavior, not an oversight."""
    close = _close(n=100)
    assert ta.bpress(close, length=500) is None


def test_returns_none_for_absurdly_large_length():
    close = _close(n=700)
    assert ta.bpress(close, length=1e30) is None
