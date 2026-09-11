# -*- coding: utf-8 -*-
"""MLCOL-1 — the 5 companions that survived, and the reasons 132 did not.

WHAT SHIPPED, AND WHY SO FEW
-----------------------------
137 `PX` columns were proposed for a companion. Five were built:

    HA_high_DIST_PCT            (ha)              screen 0.7035, axis h=1 only
    HW-UPPER_DIST_PCT           (hwc)             screen 0.6103, axis 15/15
    HW-LOWER_DIST_PCT           (hwc)             screen 0.6087, axis 15/15
    LINREG_LOWER_2_DIST_PCT     (linreg_channel)  screen 0.7186, axis 15/15
    THERMO_20_2_0.5_RATIO_PCT   (thermo)          screen 0.4669, axis 15/15

The funnel, all measured: 137 proposed → 82 restate a shipped column at
ρ ≥ 0.90 → 36 land in the disclosure band → 2 parents read the future → 4
cannot be probed → 13 clear Gate E → 6 show incremental evidence → 5 after
removing redundancy *among the survivors*.

WHAT THIS MODULE PINS, in order of how much it would hurt to lose
------------------------------------------------------------------
1. **`HW-MID_DIST_PCT` is deliberately NOT emitted.** Its companion reads
   ρ +0.9257 against `HW-LOWER`'s and +0.9213 against `HW-UPPER`'s. With both
   edges kept it carries nothing independent, and three columns for one
   signal is what the contract's non-redundancy rule forbids. Gate E measured
   every candidate against the SHIPPED set and never against the other
   candidates — so this redundancy was invisible until it was looked for, and
   a test is the only thing that stops someone "completing the set" later.

2. **`thermo`'s companion is a RATIO, not a DISTANCE, and is named for it.**
   `thermo` is a difference parent (it oscillates about zero), so the
   contract's `(close - parent) / close` shape evaluates to ≈1.0 with the
   signal in the fourth decimal. Naming is API here; calling a ratio a
   distance would misdescribe it permanently.

3. **`HA_high_DIST_PCT`'s evidence is single-horizon.** 15/15 beats-null at
   h=1 with mean − 2sd = +0.0036, and at h=5 it beats null on 10/15 with a
   NEGATIVE mean importance. Disclosed, not averaged away.

4. Every companion is scale-free (bit-identical ×8/×64) and causal.

5. `thermo`'s `close` argument is optional and exists only to scale the
   companion. When absent it falls back to hl2 — which is a SUBSTITUTE, not a
   measured equivalence, since the screen used `close`.
"""
import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

import pandas_ta as ta

COMPANIONS = [
    "HA_high_DIST_PCT",
    "HW-UPPER_DIST_PCT",
    "HW-LOWER_DIST_PCT",
    "LINREG_LOWER_2_DIST_PCT",
    "THERMO_20_2_0.5_RATIO_PCT",
]


def _frame(n=600, seed=5):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - abs(rng.normal(0, 0.006, n)))
    return DataFrame({"open": open_, "high": high, "low": low, "close": close,
                      "volume": rng.integers(1e5, 1e6, n).astype(float)},
                     index=date_range("2022-01-01", periods=n, freq="D"))


def _all(d):
    out = {}
    for frame in (ta.ha(d["open"], d["high"], d["low"], d["close"]),
                  ta.hwc(d["close"]),
                  ta.linreg_channel(d["close"]),
                  ta.thermo(d["high"], d["low"], d["close"])):
        for c in frame.columns:
            out[c] = frame[c]
    return out


@pytest.mark.parametrize("name", COMPANIONS)
def test_every_companion_is_emitted(name):
    assert name in _all(_frame()), f"{name} is not emitted"


def test_hw_mid_companion_is_deliberately_absent():
    """Three columns for one signal is what the contract forbids.

    `HW-MID`'s companion is ρ +0.9257 / +0.9213 against the two edges', both
    at or above the revert line. Keeping both edges (0.7306 apart) and
    dropping the hub is the coherent set. Gate E never saw this, because it
    measures each candidate against the SHIPPED set, not against the other
    candidates.
    """
    cols = _all(_frame())
    assert "HW-MID_DIST_PCT" not in cols
    assert "HW-UPPER_DIST_PCT" in cols and "HW-LOWER_DIST_PCT" in cols


def test_the_two_kept_edges_are_not_redundant_with_each_other():
    """If they ever converge, the pair stops being defensible."""
    d = _frame()
    cols = _all(d)
    a = cols["HW-UPPER_DIST_PCT"]
    b = cols["HW-LOWER_DIST_PCT"]
    m = a.notna() & b.notna()
    rho = a[m].corr(b[m], method="spearman")
    assert abs(rho) < 0.90, (
        f"the two kept hwc edges now read rho {rho:+.4f} against each other; "
        "at or above 0.90 only one of them should ship")


def test_thermos_companion_is_named_a_ratio_because_it_is_one():
    """A difference parent takes `parent / close`, not `(close - parent)`."""
    d = _frame()
    out = ta.thermo(d["high"], d["low"], d["close"])
    name = [c for c in out.columns if c.endswith("_RATIO_PCT")]
    assert name, "thermo's companion must be named _RATIO_PCT"
    assert not [c for c in out.columns if c.endswith("_DIST_PCT")], \
        "thermo is a difference parent; a _DIST_PCT name would misdescribe it"
    # and it really is the ratio form: ~parent/close, not ~1.0
    ratio = out[name[0]].dropna()
    assert ratio.abs().median() < 50.0, \
        "the companion looks like a (close - parent)/close form, which for a " \
        "zero-centred parent sits at ~100 and buries the signal"


@pytest.mark.parametrize("name", COMPANIONS)
@pytest.mark.parametrize("k", [8, 64])
def test_companions_are_scale_free(name, k):
    d = _frame()
    e = d.copy()
    for c in ("open", "high", "low", "close"):
        e[c] *= k
    a = np.asarray(_all(d)[name], dtype=float)
    b = np.asarray(_all(e)[name], dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    assert m.any()
    assert float(np.abs(a[m] - b[m]).max()) == 0.0, \
        f"{name} is not bit-identical under x{k}"


@pytest.mark.parametrize("name", COMPANIONS)
def test_companions_fire(name):
    s = _all(_frame())[name].dropna()
    assert len(s) > 0 and s.nunique() > 1, f"{name} is constant or all-NaN"


@pytest.mark.parametrize("cut", [200, 400])
@pytest.mark.parametrize("name", COMPANIONS)
def test_no_companion_reads_the_future(name, cut):
    """Causality is a PRECONDITION here, not a parallel check.

    MLCOL-1's screen found `dpo` (a documented exception) and `ssf` (an
    undocumented BUG, since fixed) by exactly this probe, and axis 3a had
    ranked the leaking `dpo` companion FIRST — dAUC +0.0473 against a field
    scoring ~0.01. A leaking feature is not caught by an incremental axis; it
    is promoted by one.
    """
    d = _frame()
    e = d.copy()
    for c in ("open", "high", "low", "close"):
        e.iloc[cut:, e.columns.get_loc(c)] *= 1.4
    a = np.asarray(_all(d)[name], dtype=float)[:cut]
    b = np.asarray(_all(e)[name], dtype=float)[:cut]
    m = np.isfinite(a) & np.isfinite(b)
    assert m.any()
    assert float(np.abs(a[m] - b[m]).max()) == 0.0, \
        f"{name} leaks the future: perturbing bars >= {cut} moved an earlier bar"


def test_thermo_close_is_optional_and_the_fallback_is_a_substitute():
    """Documented, because the screen measured the `close` form.

    Falling back to hl2 is a substitute nobody measured, not an equivalence.
    The test pins that both paths work and that they are NOT identical, so
    the difference cannot be quietly assumed away.
    """
    d = _frame()
    with_close = ta.thermo(d["high"], d["low"], d["close"])
    without = ta.thermo(d["high"], d["low"])
    col = "THERMO_20_2_0.5_RATIO_PCT"
    assert col in with_close.columns and col in without.columns
    a, b = with_close[col], without[col]
    m = a.notna() & b.notna()
    assert m.any()
    assert float((a[m] - b[m]).abs().max()) > 0.0, \
        "hl2 and close gave identical results, so this fixture cannot " \
        "distinguish them and the caveat is untested"
