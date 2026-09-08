# -*- coding: utf-8 -*-
"""MLCOL: ML companion columns. Contract: `docs/MLCompanionContract.md`.

⚠ These are NOT registered in `Category`. A companion is emitted for a named
parent column, so it has no meaning in a bulk `df.ta.strategy()` sweep that does
not know which parent it belongs to -- the same reason the `_pine` primitives
are deliberately absent from `Category`.
"""
from .companions import ml_bars_since, ml_dist_pct, ml_rate, ml_state

__all__ = ["ml_state", "ml_dist_pct", "ml_bars_since", "ml_rate"]
