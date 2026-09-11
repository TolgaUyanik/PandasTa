# -*- coding: utf-8 -*-
"""MLCOL-0: the ML companion contract, implemented on the three shapes.

Contract: `docs/MLCompanionContract.md`. Three indicators were chosen because
they are the three SHAPES the fork contains. The per-shape counts live in
`docs/MLCompanionContract.md` and are asserted against
`docs/IndicatorDictionary.md` by `tests/test_ml_companions.py`.
⚠ This docstring used to carry its own copy (128/172/92) and every number
was wrong -- the contract was corrected and this copy was not, which is the
exact way the verdict split went stale three times in this repo.

    rsi       bounded scale-free   -> STATE only
    sma       price-level          -> DIST_PCT + STATE
    fvg       event flag           -> BARS_SINCE + RATE

⚠ These are deliberately NOT a uniform triple per parent. A rate of a continuous
column is meaningless; a distance form of an already-bounded oscillator
reintroduces nothing. Emitting three companions for every parent would inflate
the column count by ~600 and hand the miner the same signal three times -- which
`MULTIL-0` measured as the cheapest way to double-weight a feature
(`RSI_14` vs `RSI_28`, rho 0.936, reverted).

⚠ Every window here is TRAILING. A whole-series quantile leaks the future into
every bar.

⚠ Gate E is not waived for a derived column. A companion correlates with its
parent by construction, which is precisely what the revert band exists to catch
-- MLCOL-2 measures each one and deletes the ones in the band.
"""
from numpy import nan
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

__all__ = ["ml_state", "ml_dist_pct", "ml_bars_since", "ml_rate"]

# The ordinal the contract fixes. Five levels, one column: a tree splits an
# ordinal in one node and needs four to reassemble a one-hot set.
DEEPLY_CHEAP, CHEAP, NEUTRAL, EXPENSIVE, DEEPLY_EXPENSIVE = -2, -1, 0, 1, 2

# Documented levels for the bounded oscillators the fork ships. A bounded
# indicator's thresholds are its OWN, not a quantile -- ranking an already
# bounded column re-expresses it rather than adding to it.
# Renamed from `BOUNDED_LEVELS`: `cci` is NOT bounded. Its +/-100/200 are
# CONVENTIONAL levels, so the docstring's "ranking an already bounded column
# re-expresses it" does not justify its entry -- the justification is that the
# levels are documented, which is a different (and sufficient) reason.
DOCUMENTED_LEVELS = {
    "rsi": (20.0, 30.0, 70.0, 80.0),
    "willr": (-90.0, -80.0, -20.0, -10.0),
    "cci": (-200.0, -100.0, 100.0, 200.0),
    "stoch": (10.0, 20.0, 80.0, 90.0),
    "cmo": (-70.0, -50.0, 50.0, 70.0),
    "mfi": (10.0, 20.0, 80.0, 90.0),
}


# The contract's clause "a `PX` parent's STATE is computed on its `DIST_PCT`,
# never on the raw level" was prose with nothing behind it. There is no PX
# registry in the package to check a name against, and a name check would miss
# every caller who renamed a column -- so the guard is the MEASUREMENT the
# contract is built on: a trailing quantile on a non-stationary level puts
# 31.4% of settled bars at |STATE| == 2 where the 5/95 split implies 10%,
# while the same quantile on the distance gives 9.9%. Anything past this
# multiple of nominal is the documented symptom, not a quirk of the data.
NONSTATIONARY_TAIL_MULTIPLE = 2.5


def ml_state(source, kind=None, levels=None, length=None, offset=None,
             allow_nonstationary=False, **kwargs):
    """A 5-level ordinal: -2 deeply cheap ... +2 deeply expensive.

    `kind` names a bounded family in `DOCUMENTED_LEVELS` and uses its DOCUMENTED
    thresholds. Otherwise the thresholds are quantiles of a TRAILING window --
    never of the whole series, which would leak the future into every bar.

    The quantile path REFUSES a price level. Ranking one against its own
    trailing window is the failure the contract exists to prevent, and it is
    caught by its measured signature rather than by the column's name; see
    `NONSTATIONARY_TAIL_MULTIPLE`. Pass `ml_dist_pct(parent, close)` instead,
    or `allow_nonstationary=True` if the series really is stationary.
    """
    source = verify_series(source)
    offset = get_offset(offset)

    if kind is not None and kind not in DOCUMENTED_LEVELS:
        # Silent fallthrough was the bug: `ml_state(rsi, kind="RSI")` -- wrong
        # case, a plausible caller error -- quietly took the quantile branch and
        # returned a plausible-looking column with 51.9% of bars non-neutral
        # instead of RSI's documented levels. The contract says thresholds are
        # written down, not inferred; a silent inference is the opposite.
        raise ValueError(
            f"unknown bounded kind {kind!r}; known: "
            f"{sorted(DOCUMENTED_LEVELS)}. Pass kind=None for the quantile "
            f"path, or add the documented levels for this indicator."
        )
    if kind is not None:
        low2, low1, high1, high2 = levels or DOCUMENTED_LEVELS[kind]
        state = Series(NEUTRAL, index=source.index, dtype="float64")
        state[source <= low1] = CHEAP
        state[source <= low2] = DEEPLY_CHEAP
        state[source >= high1] = EXPENSIVE
        state[source >= high2] = DEEPLY_EXPENSIVE
        state[source.isna()] = nan
        name = f"{source.name}_STATE"
    else:
        length = int(length) if length and length > 0 else 252
        if levels:
            q_low2, q_low1, q_high1, q_high2 = levels
        else:
            q_low2, q_low1, q_high1, q_high2 = 0.05, 0.25, 0.75, 0.95
        window = source.rolling(length, min_periods=max(20, length // 5))
        # `closed="left"` would drop the current bar; Pine and this fork both
        # include it, and including it is causal -- the bar is known when the
        # bar closes.
        state = Series(NEUTRAL, index=source.index, dtype="float64")
        lo2 = window.quantile(q_low2)
        lo1 = window.quantile(q_low1)
        hi1 = window.quantile(q_high1)
        hi2 = window.quantile(q_high2)
        state[source <= lo1] = CHEAP
        state[source <= lo2] = DEEPLY_CHEAP
        state[source >= hi1] = EXPENSIVE
        state[source >= hi2] = DEEPLY_EXPENSIVE
        state[lo1.isna() | source.isna()] = nan
        name = f"{source.name}_STATE"

        # Enforce the contract clause. Only the quantile path can trip it: a
        # bounded `kind` has documented thresholds and no window to distort.
        settled = state.notna()
        if settled.sum() >= 100 and not allow_nonstationary:
            nominal = float(q_low2) + (1.0 - float(q_high2))
            covered = float(
                (state[settled].abs() == 2).sum()) / float(settled.sum())
            if nominal > 0 and covered > NONSTATIONARY_TAIL_MULTIPLE * nominal:
                raise ValueError(
                    f"{source.name!r} puts {covered:.1%} of settled bars at "
                    f"|STATE| == 2 against a nominal {nominal:.1%} -- the "
                    f"signature of ranking a PRICE LEVEL, which sits at its "
                    f"own window extreme constantly. The contract "
                    f"(docs/MLCompanionContract.md) requires a PX parent's "
                    f"STATE to be computed on its DIST_PCT: call "
                    f"ml_dist_pct(parent, close) first and pass THAT. If this "
                    f"series is genuinely stationary and merely tail-heavy, "
                    f"pass allow_nonstationary=True."
                )

    if offset != 0:
        state = state.shift(offset)
    if "fillna" in kwargs:
        state.fillna(kwargs["fillna"], inplace=True)
    state.name = name
    state.category = "ml"
    return state


def ml_dist_pct(source, close, offset=None, **kwargs):
    """`(close - parent) / close` -- the column that makes a `PX` parent usable.

    A price-level column is a dead feature: a tree cannot compare `SMA_10 =
    41.72` to a close that was 12 two years ago. This is the `ichimoku_ml`
    precedent, which turned five price lines into eight scale-free columns.
    """
    source = verify_series(source)
    close = verify_series(close)
    offset = get_offset(offset)

    dist = (close - source) / close.replace(0, nan)
    if offset != 0:
        dist = dist.shift(offset)
    if "fillna" in kwargs:
        dist.fillna(kwargs["fillna"], inplace=True)
    dist.name = f"{source.name}_DIST_PCT"
    dist.category = "ml"
    return dist


def ml_bars_since(source, cap=None, offset=None, **kwargs):
    """Bars since the flag last fired, CAPPED.

    A flag is invisible to a tree on every bar but the one it fires on. The cap
    matters: an uncapped counter on a rarely-firing flag grows without bound and
    dominates every split it appears in.
    """
    source = verify_series(source)
    cap = int(cap) if cap and cap > 0 else 100
    offset = get_offset(offset)

    fired = source.fillna(0).astype(bool)
    groups = fired.cumsum()
    # Bars since the last True, counting the firing bar itself as 0.
    since = fired.groupby(groups).cumcount().astype("float64")
    since[groups == 0] = nan          # never fired yet -- NOT zero
    since = since.clip(upper=cap)

    if offset != 0:
        since = since.shift(offset)
    if "fillna" in kwargs:
        since.fillna(kwargs["fillna"], inplace=True)
    since.name = f"{source.name}_BARS_SINCE"
    since.category = "ml"
    return since


def ml_rate(source, length=None, offset=None, **kwargs):
    """Fraction of the TRAILING `length` bars in which the flag fired.

    The event rate is a different column from the event, and usually the more
    useful one: it says "this regime is active", where the flag says only "it
    happened here".
    """
    source = verify_series(source)
    length = int(length) if length and length > 0 else 60
    offset = get_offset(offset)

    rate = source.fillna(0).astype("float64").rolling(
        length, min_periods=max(5, length // 5)).mean()

    if offset != 0:
        rate = rate.shift(offset)
    if "fillna" in kwargs:
        rate.fillna(kwargs["fillna"], inplace=True)
    rate.name = f"{source.name}_RATE_{length}"
    rate.category = "ml"
    return rate
