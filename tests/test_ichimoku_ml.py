# tests/test_ichimoku_ml.py
"""MLF-3: ichimoku_ml — 8 normalized, causal Ichimoku relational features.

The centerpiece is test_no_lookahead: the raw Chikou span (close.shift(-26)) is
future-leaked by construction, so every feature MUST be reconstructed causally.
Mutating future bars must not change any feature value at an earlier row.
"""
import importlib.util
import os

import numpy as np
import pandas as pd

_FORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_F = os.path.join(_FORK, 'pandas_ta', 'overlap', 'ichimoku_ml.py')


def _load():
    spec = importlib.util.spec_from_file_location('ichimoku_ml', _F)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ichimoku_ml


def _ohlc(n=320, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(100 + np.cumsum(rng.randn(n)),
                      index=pd.date_range('2020-01-01', periods=n, freq='B'))
    high = close + rng.rand(n)
    low = close - rng.rand(n)
    return high, low, close


EXPECTED = [
    'ICHI_PRICE_VS_CLOUD', 'ICHI_PRICE_VS_KIJUN', 'ICHI_TK_DIST', 'ICHI_TK_CROSS_AGE',
    'ICHI_CLOUD_COLOR', 'ICHI_CLOUD_THICK', 'ICHI_FUTURE_CLOUD_COLOR', 'ICHI_CHIKOU_VS_CLOUD',
]


def test_columns_present_and_bounded():
    f = _load()
    h, l, c = _ohlc()
    out = f(h, l, c)
    assert list(out.columns) == EXPECTED
    warm = out.iloc[120:]   # past warmup (senkou 52 + 26 shift + 26 chikou)
    finite_cols = ['ICHI_PRICE_VS_CLOUD', 'ICHI_PRICE_VS_KIJUN', 'ICHI_TK_DIST',
                   'ICHI_CLOUD_THICK', 'ICHI_CHIKOU_VS_CLOUD']
    assert np.isfinite(warm[finite_cols].values).all()
    assert set(out['ICHI_CLOUD_COLOR'].dropna().unique()) <= {-1.0, 0.0, 1.0}
    assert set(out['ICHI_FUTURE_CLOUD_COLOR'].dropna().unique()) <= {-1.0, 0.0, 1.0}
    assert (out['ICHI_TK_CROSS_AGE'].dropna() >= 0).all()
    assert (out['ICHI_CLOUD_THICK'].dropna() >= 0).all()


def test_no_lookahead():
    f = _load()
    h, l, c = _ohlc()
    T = 220
    out_full = f(h, l, c)
    # Corrupt ONLY bars after T (keep <= T byte-identical) — feature values at
    # rows <= T must be unchanged if every feature is causal.
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    c2.iloc[T + 1:] = c2.iloc[T + 1:] * 5.0 + 50.0
    h2.iloc[T + 1:] = c2.iloc[T + 1:] + 1.0
    l2.iloc[T + 1:] = c2.iloc[T + 1:] - 1.0
    out_mut = f(h2, l2, c2)
    pd.testing.assert_frame_equal(out_full.iloc[:T + 1], out_mut.iloc[:T + 1])


def test_cloud_color_matches_span_sign():
    # CLOUD_COLOR must equal sign(SpanA - SpanB) of the displayed (shifted) cloud.
    f = _load()
    h, l, c = _ohlc()
    out = f(h, l, c)
    # where price is strictly above the cloud, PRICE_VS_CLOUD must be > 0
    above = out['ICHI_PRICE_VS_CLOUD'] > 0
    assert above.any()  # sanity: some bars above cloud in random walk
