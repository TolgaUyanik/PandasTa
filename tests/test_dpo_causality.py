# -*- coding: utf-8 -*-
"""`dpo`'s default is causal. This pins the owner's decision on issue #5.

THE DECISION
------------
Upstream pandas-ta ships `dpo(centered=True)` as the default. Centered DPO
compares `close[T]` with the SMA ending at `T + t` (`t = length // 2 + 1`), so
it reads `t` bars of the future, and its last `t` bars are NaN. `dpo` is in
`Category`, so `df.ta.strategy()` swept that look-ahead column into every
feature set. MLCOL-1's companion screen ranked a companion built on it FIRST
(dAUC +0.0473 against a field at ~0.01) -- leakage is promoted, not rejected.

On 2026-10-26 the owner flipped the default to `centered=False`. The
look-ahead form is still available, but only when asked for by name.

`ta.dpo(close)`'s values CHANGED with this flip. Anything computed from
`DPO_20` before it used the leaking form.
"""
import numpy as np
import pandas as pd
import pytest
from pandas import Series

import pandas_ta as ta


def _frame(n=400, seed=0):
    rng = np.random.default_rng(seed)
    return Series(100 * np.exp(np.cumsum(rng.normal(0, 0.012, n))))


def _moved_before(fn, cut):
    """Max change on bars < cut after altering only bars >= cut."""
    close = _frame()
    perturbed = close.copy()
    perturbed.iloc[cut:] *= 1.5
    a = np.asarray(fn(close), dtype=float)[:cut]
    b = np.asarray(fn(perturbed), dtype=float)[:cut]
    m = np.isfinite(a) & np.isfinite(b)
    assert m.any()
    return float(np.abs(a[m] - b[m]).max())


@pytest.mark.parametrize("length", [10, 20, 33])
@pytest.mark.parametrize("cut", [150, 300, 380])
def test_default_dpo_does_not_read_the_future(length, cut):
    assert _moved_before(lambda c: ta.dpo(c, length=length), cut) == 0.0, (
        f"ta.dpo(close, length={length}) leaks the future at its default")


@pytest.mark.parametrize("cut", [150, 300])
def test_accessor_default_does_not_read_the_future(cut):
    """`df.ta.dpo()` is what `df.ta.strategy()` calls; it has its own default."""
    def via_accessor(c):
        return pd.DataFrame({"close": c}).ta.dpo()
    assert _moved_before(via_accessor, cut) == 0.0


def test_centered_true_still_reads_the_future():
    """The probe must see the leak it guards against -- else it proves nothing.

    Also pins that `centered=True` was not silently removed: it is opt-in,
    not gone.
    """
    assert _moved_before(lambda c: ta.dpo(c, centered=True), 300) > 0.0


def test_default_is_the_uncentered_form():
    close = _frame()
    a = ta.dpo(close)
    b = ta.dpo(close, centered=False)
    assert a.name == "DPO_20"
    assert np.array_equal(a.to_numpy(), b.to_numpy(), equal_nan=True)
    # the causal form has a value on the last bar; the centered one cannot
    assert np.isfinite(a.iloc[-1])
    assert ta.dpo(close, centered=True).iloc[-11:].isna().all()
