# -*- coding: utf-8 -*-
"""Run length of consecutive lower highs -- issue #182 (RD-LH-RUN). Reddit,
tier 4 (ResearchIntel kb/reddit.db): rd:Trading:1gcotir (2024-10-26)
https://www.reddit.com/r/Trading/comments/1gcotir/;
rd:algotrading:1b1qx3c (2024-02-27)
https://www.reddit.com/r/algotrading/comments/1b1qx3c/;
rd:algotrading:1gcoq4m (2024-10-26)
https://www.reddit.com/r/algotrading/comments/1gcoq4m/;
rd:Daytrading:1gcos5t (2024-10-26)
https://www.reddit.com/r/Daytrading/comments/1gcos5t/.

POSTER'S WORDS (tier 4, untested by the poster): "After I get at least 4
lower highs in a row, I place an order at the most recent high." Claimed use:
probability of a (long) reversal rises with the number of consecutive lower
highs -- NOT independently tested here; this port ships existence (causal,
scale-free comparison, reachable on real data), not evidence that it predicts
anything.

GATE A -- the issue's own formula, read literally (its own instruction:
"Gate A starts from the source formula, not the prototype";
`docs/issues/screen/ind_screen_r6.py`'s `rd_lh_run` candidate reads the same
way, `run_length(h < h.shift(1))`):

    n_t = n_{t-1} + 1 if high_t < high_{t-1} else 0

Bar 0 has no `high_{-1}` to compare against, so `high_0 < high_{-1}` is
undefined; both this port and the prototype's own `run_length` helper read
that as the ELSE branch (`pandas.Series.shift(1)` puts NaN at bar 0, and
`value < NaN` is `False`, not NaN, in both NumPy and pandas), giving `n_0 = 0`
rather than NaN. This matches the recursion literally: there is no
`n_{-1}` term to propagate from, so the only defined branch at `t = 0` is the
`else`.

This fork already has one other "run length of a condition" port,
`pandas_ta.volatility.range_compress_run` (issue #176), built the same way:
flip the condition, feed it to `pandas_ta.ml.companions.ml_bars_since`, which
is exactly "bars since the flag last fired, counting the firing bar itself as
0" -- precisely the recursion above, with "fired" standing in for "NOT a
lower high" and the gap between firings standing in for the run of lower
highs. Concretely: `lower_high = high < high.shift(1)`; feeding
`~lower_high` to `ml_bars_since` makes every bar that is NOT a lower high
reset the counter to 0 (the firing bar itself), and every lower-high bar
after it increments by 1 from the previous bar's count, in bar order -- the
same recursive dependency on `n_{t-1}` the issue's own formula has, computed
via `groupby(cumsum).cumcount()`, which pandas evaluates strictly in row
order and cannot see a later row while computing an earlier one. Unlike
`range_compress_run`, bar 0 here reads 0, not NaN: `range_compress_run`
blanks bar 0 because ITS condition compares two SUBTRACTED ranges
(`rng < prior`), and `prior` is NaN at bar 0, forcing an explicit NaN
override; this port's condition compares `high` to `high.shift(1)` directly,
which pandas already evaluates to `False` (not NaN) at bar 0, so `~lower_high`
already fires at bar 0 with no override needed -- matching the prototype's
own observed bar-0 value of 0.

`cap` bounds the count the same way `range_compress_run`'s own `cap` does
(ML feature contract: an uncapped counter on a rare, unboundedly-growing
condition dominates every split it appears in) -- not in the issue's own
formula, which is unbounded, but the convention every other "run length"
port in this fork (`range_compress_run`) already ships.

CAUSALITY. `lower_high` at bar T reads only `high[T]` and `high[T-1]` --
exactly one bar back, via `pandas.Series.shift(1)`, which is backward-looking
by construction. `ml_bars_since` (`pandas_ta/ml/companions.py`) then computes
`fired.cumsum()` and a per-group `cumcount()`, both of which pandas evaluates
in row order: bar T's group id and position within it depend only on
`fired[0..T]`, never on `fired[T+1..]`. `tests/test_rd_lh_run.py` proves this
with a future-splice probe (bars before a perturbation point J stay
bit-identical whether or not the frame's tail is replaced by an unrelated
series) and a mutant that reads `high.shift(-1)` in place of `high.shift(1)`
(comparing to the NEXT bar's high instead of the prior one): the real module
leaks 0 bars at every swept J; the mutant is live and leaks at every one.

SCALE-FREE. `lower_high = high < high.shift(1)` is a direct comparison of two
raw price values, not a comparison of a computed DIFFERENCE against zero (the
case `range_compress_run`'s own tie-tolerance argument addresses) -- so for
any positive-constant price rescale, each operand is multiplied by the exact
same factor before the comparison, and a strict `<` between two positively
co-scaled operands only disagrees with the unscaled comparison if the rescale
itself introduces or removes an exact tie through independent rounding of
`high*k` and `high.shift(1)*k`. For an exactly-representable `k` (a power of
two), that rescale is exact (no rounding at all -- a power-of-two multiply
only shifts the float's exponent), so the comparison result is bit-identical
to the unscaled one at every bar, and the downstream `cumsum`/`cumcount` --
pure integer bookkeeping over a bit-identical boolean series -- reproduces an
identical run-length sequence. A non-power-of-two rescale (x10, x3.7) rounds
`high*k` and `high.shift(1)*k` independently, which could in principle flip a
bar that was an EXACT tie in the unscaled series into a strict inequality (or
vice versa); measured on the synthetic GBM walk used throughout
`tests/test_rd_lh_run.py` (`docs/measure_rd_lh_run.py`): 0 exact ties in
`high` at consecutive bars, so 0 mismatches under any of x8/x64/x10/x3.7 --
see docs/RdLhRunMeasured.md for the measured numbers.
"""
from pandas_ta.ml.companions import ml_bars_since
from pandas_ta.utils import get_offset, verify_series


def rd_lh_run(high, cap=None, offset=None, **kwargs):
    """Indicator: Run Length of Consecutive Lower Highs (RD_LH_RUN)"""
    # Validate Arguments
    cap = int(cap) if cap and cap > 0 else 100
    high = verify_series(high, 2)
    offset = get_offset(offset)

    if high is None: return

    # Calculate Result
    lower_high = high < high.shift(1)
    result = ml_bars_since(~lower_high, cap=cap)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            result = result.ffill()
        elif method in ("bfill", "backfill"):
            result = result.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    result.name = f"RD_LH_RUN_{cap}"
    result.category = "trend"

    return result


rd_lh_run.__doc__ = \
"""Run Length of Consecutive Lower Highs (RD_LH_RUN)

How many consecutive bars, ending at this one, have had a high strictly
below the prior bar's high. Resets to 0 on any bar whose high is equal to or
above the prior bar's high; capped at `cap`. A Reddit crowd-talk definition
(tier 4, untested by the poster, issue #182): "After I get at least 4 lower
highs in a row, I place an order at the most recent high" -- claimed use:
probability of a (long) reversal rises with the number of consecutive lower
highs -- NOT independently tested here; this port ships existence (causal,
scale-free, reachable on real data), not evidence it predicts anything. See
the module source above for the full source citation, Gate A derivation and
the causality/scale-free argument; docs/RdLhRunMeasured.md has the measured
numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Trading:1gcotir
    (2024-10-26) https://www.reddit.com/r/Trading/comments/1gcotir/;
    rd:algotrading:1b1qx3c (2024-02-27)
    https://www.reddit.com/r/algotrading/comments/1b1qx3c/;
    rd:algotrading:1gcoq4m (2024-10-26)
    https://www.reddit.com/r/algotrading/comments/1gcoq4m/;
    rd:Daytrading:1gcos5t (2024-10-26)
    https://www.reddit.com/r/Daytrading/comments/1gcos5t/

Calculation:
    Default Inputs:
        cap=100
    lower_high = high < high.shift(1)
    RD_LH_RUN = bars since the last bar that was NOT a lower high
                (the issue's own recursion: n[t] = n[t-1] + 1 if
                lower_high[t] else 0), clipped to cap
    RD_LH_RUN[0] = 0 (no prior bar, so the else branch applies)

Args:
    high (pd.Series): Series of 'high's
    cap (int): Upper clip on the run length. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_LH_RUN_{cap}, a non-negative integer-valued count, 0 at any
        bar that is not a lower high (including bar 0), clipped to `cap`.
"""
