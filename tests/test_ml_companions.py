# -*- coding: utf-8 -*-
"""MLCOL-0: the companion contract, pinned.

Contract: `docs/MLCompanionContract.md`. What these guard, in order of how much
it would hurt to lose:

* **Causality.** Every window is trailing. A whole-series quantile leaks the
  future into every bar, and a STATE column built that way would look
  spectacular in a backtest and be worthless live. Checked by a PREFIX test —
  recomputing on a truncated frame must not change the earlier values — because
  that is the one failure mode a spot-check cannot see.
* **Scale-freedom.** `DIST_PCT` exists because a `PX` parent is a dead feature.
  If the companion is not itself scale-free it has solved nothing.
* **`BARS_SINCE` is NaN before the first fire, not 0.** Zero means "it fired
  here", which is the opposite of "it has never fired" — the same distinction
  `barssince` had to make in `_pine.py`.
* **The companions are NOT in `Category`.** A parent-specific column swept into
  `df.ta.strategy()` would be an unaudited feature with no parent.
"""
import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta


def _frame(n=400, seed=5):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.0, n))
    return DataFrame(
        {"close": close},
        index=date_range("2020-01-01", periods=n, freq="D"))


F = _frame()
CLOSE = F["close"]


def test_state_is_a_five_level_ordinal_not_a_one_hot_set():
    rsi = pandas_ta.rsi(CLOSE, length=14)
    state = pandas_ta.ml_state(rsi, kind="rsi")
    values = set(state.dropna().unique())
    assert values <= {-2.0, -1.0, 0.0, 1.0, 2.0}, values
    assert state.name == f"{rsi.name}_STATE"
    # One column, not four. The contract's reason: a tree splits an ordinal in
    # one node and needs four to reassemble a one-hot set.
    assert isinstance(state, Series)


def test_bounded_state_uses_the_documented_levels_not_quantiles():
    """`rsi` is already scale-free; ranking it re-expresses it rather than
    adding to it. The thresholds must be RSI's own."""
    rsi = pandas_ta.rsi(CLOSE, length=14)
    state = pandas_ta.ml_state(rsi, kind="rsi")
    low2, low1, high1, high2 = pandas_ta.ml.companions.DOCUMENTED_LEVELS["rsi"]
    both = rsi.notna() & state.notna()
    assert (state[both & (rsi >= high2)] == 2).all()
    assert (state[both & (rsi <= low2)] == -2).all()
    assert (state[both & (rsi > low1) & (rsi < high1)] == 0).all()
    # A quantile-based state on a bounded series would put ~25% of bars in each
    # tail; the documented levels must not.
    tail = (state.dropna().abs() >= 1).mean()
    assert tail < 0.45, (
        f"{tail:.0%} of bars are non-neutral; that is a quantile split, not "
        f"RSI's documented levels"
    )


def test_dist_pct_is_scale_free():
    """The whole point of the PX companion. Scale the price by 137 and the
    distance must not move."""
    sma = pandas_ta.sma(CLOSE, length=10)
    dist = pandas_ta.ml_dist_pct(sma, CLOSE)

    scaled_close = CLOSE * 137.0
    scaled_dist = pandas_ta.ml_dist_pct(
        pandas_ta.sma(scaled_close, length=10), scaled_close)

    a, b = dist.to_numpy(), scaled_dist.to_numpy()
    mask = ~(np.isnan(a) | np.isnan(b))
    assert mask.sum() > 100
    assert np.allclose(a[mask], b[mask], rtol=1e-9), (
        f"DIST_PCT moved under a x137 price scale by "
        f"{np.nanmax(np.abs(a[mask] - b[mask])):.3e} -- it is not scale-free, "
        f"which is the only reason it exists"
    )


def test_bars_since_is_nan_before_the_first_fire_not_zero():
    """0 means "it fired on this bar". NaN means "it never has"."""
    flag = Series(np.zeros(50), index=range(50), name="FVG_BULL")
    flag.iloc[20] = 1
    flag.iloc[30] = 1
    since = pandas_ta.ml_bars_since(flag)

    assert since.iloc[:20].isna().all(), "counted before the first fire"
    assert since.iloc[20] == 0, "the firing bar is 0"
    assert since.iloc[21] == 1
    assert since.iloc[29] == 9
    assert since.iloc[30] == 0, "a new fire resets"


def test_bars_since_is_capped():
    """An uncapped counter on a rare flag dominates every split it enters."""
    flag = Series(np.zeros(500), index=range(500), name="RARE")
    flag.iloc[1] = 1
    since = pandas_ta.ml_bars_since(flag, cap=100)
    assert since.max() == 100, since.max()


def test_rate_is_the_trailing_fraction():
    flag = Series(np.zeros(200), index=range(200), name="EV")
    flag.iloc[::4] = 1                      # fires every 4th bar
    rate = pandas_ta.ml_rate(flag, length=60)
    settled = rate.dropna().iloc[80:]
    assert np.allclose(settled, 0.25, atol=0.02), settled.head()
    assert rate.name == "EV_RATE_60"


@pytest.mark.parametrize("build", [
    # `allow_nonstationary` because this parametrisation feeds a raw price
    # series on purpose -- it is testing CAUSALITY, not the PX/DIST_PCT
    # clause, and the guard added for that clause would otherwise reject
    # the fixture rather than the behaviour under test.
    lambda s: pandas_ta.ml_state(s, length=100,
                                 allow_nonstationary=True),
    # NOTE: the flag must be built CAUSALLY too. An earlier version of this
    # parametrisation used `s > s.median()` -- a whole-series statistic -- and
    # the test failed on its own fixture rather than on `ml_rate`. That is the
    # guard working, on the wrong subject.
    lambda s: pandas_ta.ml_rate((s > 100.0).astype(float), length=60),
])
def test_companions_are_causal_by_prefix(build):
    """THE test. Recompute on a truncated frame; earlier values must not move.

    A whole-series quantile is the easy mistake here and it is invisible to a
    spot-check — the column looks fine, and every bar of it knows the future.
    """
    full = build(CLOSE)
    cut = 300
    prefix = build(CLOSE.iloc[:cut])

    a = full.iloc[:cut].to_numpy()
    b = prefix.to_numpy()
    mask = ~(np.isnan(a) | np.isnan(b))
    assert mask.sum() > 50, "not enough overlap to judge causality"
    assert np.allclose(a[mask], b[mask], rtol=1e-9), (
        f"truncating the frame changed {int((~np.isclose(a[mask], b[mask])).sum())} "
        f"earlier values -- the window is not trailing"
    )


def test_companions_are_not_registered_as_indicators():
    """A parent-specific column swept into `df.ta.strategy()` is an unaudited
    feature with no parent. Same reason the `_pine` primitives stay out."""
    registered = {n for names in pandas_ta.Category.values() for n in names}
    leaked = sorted({"ml_state", "ml_dist_pct", "ml_bars_since", "ml_rate"}
                    & registered)
    assert leaked == [], f"companions registered as indicators: {leaked}"

    df = DataFrame()
    exposed = [n for n in ("ml_state", "ml_dist_pct", "ml_bars_since",
                           "ml_rate") if hasattr(df.ta, n)]
    assert exposed == [], f"companions exposed on df.ta: {exposed}"


def test_the_contract_quotes_the_dictionarys_actual_ml_form_counts():
    """The contract said "Measured: 128 PX, 172 SF, 92 BIN, 3 PX2". The
    dictionary it cites says 126/169/90/2 — all four wrong, with the word
    "Measured" attached, in the opening paragraph of the document the rollout is
    templated on. Asserted now, not retyped."""
    import os
    import re
    from collections import Counter

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    doc = open(os.path.join(here, "docs", "IndicatorDictionary.md"),
               encoding="utf8").read()
    body = doc[doc.index("## candles"):]
    tags = Counter(re.findall(r"`[^`]+`\s+(PX2|PX|SF|BIN|ORD|CONST)\b", body))

    contract = open(os.path.join(here, "docs", "MLCompanionContract.md"),
                    encoding="utf8").read()
    wrong = []
    for tag in ("PX", "SF", "BIN", "PX2"):
        match = re.search(rf"\*\*(\d+) `{tag}`\*\*|(\d+) `{tag}`", contract)
        if not match:
            wrong.append((tag, None, tags[tag]))
            continue
        quoted = int(match.group(1) or match.group(2))
        if quoted != tags[tag]:
            wrong.append((tag, quoted, tags[tag]))
    assert wrong == [], (
        f"the contract quotes counts the dictionary does not support "
        f"{{(tag, quoted, actual)}}: {wrong}"
    )


def test_state_on_a_price_level_is_known_to_be_lopsided():
    """The contract must report the MEASURED distribution, not the nominal one.

    A trailing quantile on a non-stationary level puts 31% of bars at |STATE|==2
    against a 5/95 split's implied 10%; on DIST_PCT it is ~10%. The contract now
    says so, and this pins that it keeps saying so.
    """
    import os

    rng = np.random.default_rng(3)
    walk = Series(100 + np.cumsum(rng.normal(0, 1, 1500)),
                  index=date_range("2018-01-01", periods=1500), name="SMA_10")
    # This is the measurement the guard is built ON, so it has to be able
    # to take it: `allow_nonstationary=True` is what the guard rejects
    # without. See test_ml_state_refuses_a_price_level_and_accepts_its
    # _distance for the rejection itself.
    raw_tail = (pandas_ta.ml_state(walk, length=252,
                                   allow_nonstationary=True)
                .dropna().abs() == 2).mean()
    dist = pandas_ta.ml_dist_pct(pandas_ta.sma(walk, length=10), walk)
    dist_tail = (pandas_ta.ml_state(dist, length=252).dropna().abs() == 2).mean()

    assert raw_tail > 0.2, (
        f"the lopsidedness this contract warns about has vanished "
        f"({raw_tail:.1%}); re-measure and update the document"
    )
    assert dist_tail < raw_tail / 2, (
        f"ranking DIST_PCT ({dist_tail:.1%}) no longer improves on ranking the "
        f"raw level ({raw_tail:.1%}) -- the contract's core recommendation"
    )

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contract = open(os.path.join(here, "docs", "MLCompanionContract.md"),
                    encoding="utf8").read()
    assert "does not give the nominal tails" in contract, (
        "the contract no longer discloses the measured state distribution"
    )


def test_an_unknown_bounded_kind_is_rejected_not_silently_inferred():
    """`ml_state(rsi, kind="RSI")` used to fall through to the quantile path."""
    rsi = pandas_ta.rsi(CLOSE, length=14)
    with pytest.raises(ValueError):
        pandas_ta.ml_state(rsi, kind="RSI")
    with pytest.raises(ValueError):
        pandas_ta.ml_state(rsi, kind="not_an_indicator")


def test_the_contract_document_exists_and_names_the_three_shapes():
    """The contract is the deliverable; the code is its implementation."""
    import os

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "docs", "MLCompanionContract.md")
    assert os.path.exists(path), path
    text = open(path, encoding="utf8").read()
    for shape in ("bounded oscillator", "price-scaled overlay", "event flag"):
        assert shape in text, f"the contract does not name the {shape} shape"
    for rule in ("Causal", "Scale-free", "Gate E"):
        assert rule in text, f"the contract does not state the {rule} rule"


def test_ml_state_refuses_a_price_level_and_accepts_its_distance():
    """The contract clause "a `PX` parent's STATE is computed on its `DIST_PCT`,
    never on the raw level" was prose with no enforcement behind it.

    Pinned, in order of how much it would hurt to lose:

    1. The refusal is by MEASUREMENT, not by column name. There is no PX
       registry in the package, and a name check would pass every renamed
       column straight through.
    2. The measured separation is real and reproduces the contract: a price
       level puts ~31% of settled bars at |STATE| == 2 against a nominal 10%,
       its distance ~11%. The contract cites 31.4% / 9.9% on its own frame.
    3. The bounded-`kind` path is NOT touched -- it has documented thresholds
       and no trailing window to distort.
    4. `allow_nonstationary=True` is a real escape hatch, so a genuinely
       stationary but tail-heavy series is not locked out.
    """
    import numpy as np
    from pandas import Series

    import pandas_ta as ta
    from pandas_ta.ml.companions import (
        NONSTATIONARY_TAIL_MULTIPLE, ml_dist_pct, ml_state,
    )

    rng = np.random.default_rng(7)
    close = Series(100 * np.exp(np.cumsum(rng.normal(0, 0.012, 1500))),
                   name="close")
    parent = ta.sma(close, 10)
    parent.name = "SMA_10"

    with pytest.raises(ValueError, match="DIST_PCT"):
        ml_state(parent, length=252)

    # ... and the escape hatch actually escapes
    forced = ml_state(parent, length=252, allow_nonstationary=True)
    assert forced.notna().sum() > 0

    distance = ml_dist_pct(parent, close)
    state = ml_state(distance, length=252)
    settled = state.notna()
    covered = float((state[settled].abs() == 2).sum()) / float(settled.sum())
    assert settled.sum() > 1000
    assert covered <= NONSTATIONARY_TAIL_MULTIPLE * 0.10, (
        f"the distance covered {covered:.1%}, which the guard would reject"
    )
    assert 0.05 <= covered <= 0.20, (
        f"expected the distance near the nominal 10% tail, got {covered:.1%}"
    )
