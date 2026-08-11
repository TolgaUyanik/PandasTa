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

    def _fit_at_last_point(window):
        x = np.arange(len(window))
        m, b = np.polyfit(x, window, 1)
        return m * (len(window) - 1) + b

    manual = [
        _fit_at_last_point(y[i - length + 1:i + 1])
        for i in range(length - 1, n)
    ]
    manual = pd.Series(manual, index=range(length - 1, n))

    default_diff = (lr_default.iloc[length - 1:].reset_index(drop=True)
                    - manual.reset_index(drop=True)).abs().max()
    tsf_diff = (lr_tsf.iloc[length - 1:].reset_index(drop=True)
                - manual.reset_index(drop=True)).abs().max()

    assert tsf_diff < 1e-9, "tsf=True must match the current-bar OLS fit"
    assert default_diff > 1e-3, (
        "sanity check: the untagged default must NOT match the current-bar "
        "fit, confirming tsf=True is a deliberate, necessary choice"
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
