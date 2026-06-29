# -*- coding: utf-8 -*-
"""Ichimoku ML features (ichimoku_ml).

8 normalized, CAUSAL relational features derived from the Ichimoku lines —
the ML-proper form of Ichimoku (the raw lines are absolute price levels a tree
cannot use; see docs/IndicatorMLAudit.md, MLF-3).

The raw Chikou span (`close.shift(-kijun)`) is future-leaked by construction
and is NEVER used. Every feature at bar T uses only data <= T.
"""
import numpy as np
import pandas as pd


def _midprice(high, low, length):
    """Trailing midprice = (rolling max high + rolling min low) / 2."""
    return 0.5 * (high.rolling(length).max() + low.rolling(length).min())


def ichimoku_ml(high, low, close, tenkan=9, kijun=26, senkou=52, **kwargs):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)

    tenkan_sen = _midprice(high, low, tenkan)
    kijun_sen = _midprice(high, low, kijun)
    span_a_raw = 0.5 * (tenkan_sen + kijun_sen)   # unshifted: the cloud kijun bars AHEAD
    span_b_raw = _midprice(high, low, senkou)     # unshifted

    # Displayed cloud at bar T = spans projected forward kijun bars (.shift(+kijun)),
    # so its value at T is derived from data at T-kijun (causal).
    span_a = span_a_raw.shift(kijun)
    span_b = span_b_raw.shift(kijun)
    cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)

    out = pd.DataFrame(index=close.index)
    out['ICHI_PRICE_VS_CLOUD'] = (close - cloud_top) / close
    out['ICHI_PRICE_VS_KIJUN'] = (close - kijun_sen) / close
    out['ICHI_TK_DIST'] = (tenkan_sen - kijun_sen) / close

    # Bars since the last Tenkan/Kijun cross (sign flip of the TK difference).
    tk = tenkan_sen - kijun_sen
    sign_tk = np.sign(tk)
    flip = (sign_tk != sign_tk.shift(1)) & sign_tk.notna() & sign_tk.shift(1).notna()
    out['ICHI_TK_CROSS_AGE'] = tk.groupby(flip.cumsum()).cumcount().astype(float)

    out['ICHI_CLOUD_COLOR'] = np.sign(span_a - span_b)
    out['ICHI_CLOUD_THICK'] = (span_a - span_b).abs() / close
    # Forward cloud color: spans that WILL be plotted kijun bars ahead — fully known
    # at T (a projection of past midprices; no future price). Ichimoku's leading signal.
    out['ICHI_FUTURE_CLOUD_COLOR'] = np.sign(span_a_raw - span_b_raw)
    # Chikou: today's close vs the displayed cloud kijun bars ago. Causal (the
    # leak-safe reconstruction of "lagging span clear of cloud").
    out['ICHI_CHIKOU_VS_CLOUD'] = (close - cloud_top.shift(kijun)) / close

    out.name = f"ICHIMOKUML_{tenkan}_{kijun}_{senkou}"
    out.category = "overlap"
    return out
