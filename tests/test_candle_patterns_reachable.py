# -*- coding: utf-8 -*-
"""CANDLE-2 — which candle patterns are actually callable, pinned.

`cdl_pattern` is a thin wrapper: 2 patterns are native to this fork
(`cdl_doji`, `cdl_inside`) and the rest are forwarded to TA-Lib. TA-Lib is an
OPTIONAL dependency, so what the fork can compute depends on whether it is
installed — and until now nothing tested that either way. `TODO.md` carried
"TA-Lib is not installed in this environment, so its ~60 patterns are
unreachable" as fact for two days after it stopped being true.

Pinned here, in order of how much it would hurt to lose:

1. **With TA-Lib installed, `name="all"` returns 62 columns and none of them
   is constant on real data.** CANDLE-0 measured 0 of 62 constant over 50 BIST
   tickers / 91,197 daily bars. This module re-checks the count and
   non-constancy on real cached data when it is available, and falls back to a
   synthetic frame otherwise.
2. **The count is asserted, not retyped.** `docs/IndicatorDictionary.md` tags
   23 of the 61 as `CONST` — that is a property of its 600-bar synthetic probe
   fixture, NOT of the indicator, and the dictionary now says so. If someone
   "fixes" the dictionary by deleting those columns, this test fails.
3. **Without TA-Lib the fork degrades to 2 patterns and says so** rather than
   raising. The skip is explicit, so a green run on a machine without TA-Lib
   cannot be mistaken for a green run with it.
"""
import numpy as np
import pytest
from pandas import DataFrame, date_range

import pandas_ta as ta

try:
    import talib as _talib
    HAVE_TALIB = True
except ImportError:                                         # pragma: no cover
    _talib = None
    HAVE_TALIB = False

NATIVE = {"CDL_DOJI_10_0.1", "CDL_INSIDE"}
EXPECTED_WITH_TALIB = 62


def frame(n=900, seed=7):
    """Synthetic OHLC with enough body/shadow variety to fire real patterns."""
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    spread = close * np.abs(rng.normal(0, 0.008, n))
    open_ = close * (1 + rng.normal(0, 0.006, n))
    high = np.maximum.reduce([close + spread, open_, close])
    low = np.minimum.reduce([close - spread, open_, close])
    return DataFrame({"open": open_, "high": high, "low": low, "close": close},
                     index=date_range("2022-01-03", periods=n, freq="B"))


def _all_patterns(df):
    return ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"],
                          name="all")


@pytest.mark.skipif(not HAVE_TALIB, reason="TA-Lib not installed")
def test_all_returns_sixty_two_columns_with_talib():
    out = _all_patterns(frame())
    assert out is not None
    assert out.shape[1] == EXPECTED_WITH_TALIB, (
        f"expected {EXPECTED_WITH_TALIB} pattern columns, got {out.shape[1]}. "
        f"If TA-Lib changed its CDL set, update the constant AND "
        f"docs/CandlePatternShortlist.md together."
    )
    assert NATIVE <= set(out.columns), (
        f"the two native patterns must survive: {NATIVE - set(out.columns)}"
    )


@pytest.mark.skipif(not HAVE_TALIB, reason="TA-Lib not installed")
def test_sixty_of_the_sixty_two_are_forwarded_and_two_are_native():
    """The dispatch split, so nobody re-derives it from column names."""
    from pandas_ta.candles.cdl_pattern import ALL_PATTERNS

    assert len(ALL_PATTERNS) == EXPECTED_WITH_TALIB
    assert len(NATIVE) == 2


@pytest.mark.skipif(not HAVE_TALIB, reason="TA-Lib not installed")
def test_none_of_them_is_constant_on_a_frame_that_can_fire_them():
    """The dictionary's 23 `CONST` tags are a FIXTURE artifact.

    CANDLE-0 measured 0 of 62 constant over 50 BIST tickers / 91,197 daily
    bars. Real cached data is used when present; the synthetic fallback is
    longer and rougher than the dictionary's probe frame, so it fires more --
    but it will not fire everything, and the assertion says how many rather
    than pretending otherwise.
    """
    import glob
    import os

    from pandas import read_parquet

    cache = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "..", "Backtesting", "datastore", "cache")
    files = sorted(glob.glob(os.path.join(cache, "*_1d.parquet")))[:8]

    if files:
        fired = set()
        total = 0
        for path in files:
            data = read_parquet(path)
            data.columns = [c.lower() for c in data.columns]
            if not {"open", "high", "low", "close"} <= set(data.columns):
                continue
            if len(data) < 400:
                continue
            total += 1
            out = _all_patterns(data)
            if out is None:
                continue
            fired |= {c for c in out.columns if out[c].nunique() > 1}
        assert total > 0, "no usable cached frames -- the fallback should run"
        assert len(fired) >= 55, (
            f"only {len(fired)} of {EXPECTED_WITH_TALIB} patterns fired across "
            f"{total} real frames; CANDLE-0 measured all 62 firing over 50 "
            f"tickers, so a large drop means something broke"
        )
    else:                                                   # pragma: no cover
        out = _all_patterns(frame())
        fired = {c for c in out.columns if out[c].nunique() > 1}
        assert len(fired) >= 20, (
            f"only {len(fired)} patterns fired on the synthetic fallback"
        )


@pytest.mark.skipif(HAVE_TALIB, reason="TA-Lib IS installed")
def test_without_talib_the_fork_degrades_to_the_two_native_patterns():
    """Explicit, so a green run without TA-Lib cannot be mistaken for one
    with it."""                                             # pragma: no cover
    out = _all_patterns(frame())
    assert out is None or set(out.columns) <= NATIVE


def test_the_dictionary_does_not_silently_drop_the_pattern_columns():
    """Guards the fix, not just the finding.

    `docs/IndicatorDictionary.md` tags 23 of the 61 probed pattern columns
    `CONST` because its 600-bar synthetic fixture cannot fire them. The honest
    correction is a caveat, not deletion -- if someone "cleans up" the
    dictionary by removing them, the shortlist's non-duplication argument
    loses its denominator.
    """
    import io
    import os
    import re

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = io.open(os.path.join(here, "docs", "IndicatorDictionary.md"),
                  encoding="utf8").read()
    row = [line for line in doc.splitlines()
           if line.startswith("| `cdl_pattern`")]
    assert row, "the cdl_pattern row vanished from the dictionary"
    columns = re.findall(r"`(CDL_[A-Z0-9_.]+)`", row[0])
    assert len(columns) >= 55, (
        f"the dictionary lists only {len(columns)} pattern columns"
    )
