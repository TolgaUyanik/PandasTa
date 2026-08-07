"""Regression test for the duplicate `supertrend` accessor removed 2026-07-29.

`AnalysisIndicators` defined `supertrend` twice. The second definition took
`period=` and forwarded it to `overlap/supertrend.py`, whose signature is
`length=`; `period` was swallowed by that function's `**kwargs` and the
indicator silently fell back to its default length of 7. Being defined
second, it also shadowed the correct accessor.

This test does NOT use tests/config.py, so it runs without the missing
`data/SPY_D.csv` fixture.
"""
import inspect

import numpy as np
import pandas as pd
import pytest

import pandas_ta as ta
from pandas_ta.core import AnalysisIndicators


def _frame(n=60):
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "open": np.linspace(10, 20, n),
            "high": np.linspace(10.5, 20.5, n),
            "low": np.linspace(9.5, 19.5, n),
            "close": np.linspace(10, 20, n),
            "volume": np.full(n, 1e5),
        },
        index=idx,
    )


def test_surviving_signature_is_the_length_one():
    """The shadowing def took `period=`. Assert the bound signature, not the
    source text: a string count is defeated by different indentation or by
    `AnalysisIndicators.supertrend = ...` assignment."""
    params = inspect.signature(AnalysisIndicators.supertrend).parameters
    assert "length" in params
    assert "period" not in params


def test_length_is_honored():
    df = _frame()
    result = df.ta.supertrend(length=10, multiplier=3)
    assert "SUPERT_10_3.0" in result.columns


def test_accessor_matches_module_function():
    df = _frame()
    accessor = df.ta.supertrend(length=10, multiplier=3)["SUPERT_10_3.0"]
    module = ta.supertrend(
        df["high"], df["low"], df["close"], length=10, multiplier=3
    )["SUPERT_10_3.0"]
    pd.testing.assert_series_equal(accessor, module)


@pytest.mark.parametrize("kwarg", ["period", "mamode", "drift"])
def test_unread_kwargs_raise_instead_of_silently_using_defaults(kwarg):
    """All three were advertised by the removed accessor and are read by
    neither it nor overlap/supertrend.py."""
    df = _frame()
    with pytest.raises(TypeError, match="only length, multiplier and offset"):
        df.ta.supertrend(length=10, multiplier=3, **{kwarg: 10})
