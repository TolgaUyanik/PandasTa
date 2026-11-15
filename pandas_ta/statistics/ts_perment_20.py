# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# Bandt-Pompe order (embedding dimension) and the lag. The issue fixes both --
# "order 3, 20", `permutation_entropy(tau=1, dimension=3)` -- so neither is a
# parameter here; `DIMENSION` is in the column name so a later order cannot
# quietly reuse it. At `tau = 1` the delay WITHIN a triple and the stride
# BETWEEN consecutive triples are the same number, so the two readings of
# `tau` coincide and this module does not have to choose between them; at any
# other tau they differ, and the issue fixes 1.
DIMENSION = 3
TAU = 1
LEGS = TAU * (DIMENSION - 1)  # closes between the oldest and newest leg
# The six ordinal patterns of three points, encoded as
# `4*(a <= b) + 2*(b <= c) + (a <= c)` on the triple (a, b, c) = closes
# (T-2, T-1, T). Ties are broken by INDEX (the earlier close is the smaller),
# which makes `<=` a strict total order on the three positions -- and under a
# total order two of the eight codes are unrealisable: 6 would need
# a < b < c with a >= c, and 1 would need a >= b >= c with a < c. That those
# two never occur, and that each of the other six is one `argsort(argsort(x))`
# rank vector, is measured exhaustively over all 27 triples drawn from
# {1, 2, 3} in `tests/test_ts_perment_20.py`; `UNREALISABLE` below is read
# only by that test, as the pin for the pair.
#
# The order of this tuple is the order the six terms are ACCUMULATED in, and
# that order is a last bit of the result. It is the order the source's own
# spelling sums them in -- `np.unique(argsort(argsort(X)), axis=0)` returns
# the rank vectors sorted, which is (0,1,2), (0,2,1), (1,0,2), (1,2,0),
# (2,0,1), (2,1,0), i.e. codes 7, 5, 3, 4, 2, 0 -- so the module is bit-equal
# to it rather than merely close (docs/TsPerment20Measured.md, Gate A3).
PATTERNS = (7, 5, 3, 4, 2, 0)
UNREALISABLE = (1, 6)
# One triple is a one-pattern histogram and so a constant 0 everywhere; two is
# the smallest window whose value can vary.
MIN_TRIPLES = 2
MIN_LENGTH = MIN_TRIPLES + LEGS  # 4


def ts_perment_20(close, length=None, offset=None, **kwargs):
    """Indicator: permutation entropy of close (TS_PERMENT)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)

    # The three legs of the triple ending at bar T: closes T-2, T-1, T. Only
    # their ORDER is read, so nothing here is a difference, a ratio or a sum:
    # that is what makes the column invariant to any strictly increasing
    # transform of price rather than merely to a multiplication.
    a, b, z = c[:-LEGS], c[TAU:c.size - TAU], c[LEGS:]
    # A close that is not finite has no place in an ordering: every comparison
    # against a NaN is False, which would silently read as "greater than
    # everything" (code 0). It is masked out instead, below.
    ok = np.isfinite(c)
    valid = ok[:-LEGS] & ok[TAU:c.size - TAU] & ok[LEGS:]
    # A non-positive or subnormal close is NOT rejected: this column takes no
    # ratio and no logarithm, so such a close still has a well-defined place
    # in the ordering. That differs from `ts_binent_20` / `ts_c3_20`, which
    # need a return and so need positivity.
    code = (4 * (a <= b) + 2 * (b <= z) + (a <= z)).astype(np.int8)
    codes = np.where(valid, code, -1)

    # `length` closes hold `length - LEGS` triples, oldest first, so the
    # window ending at bar T reads closes T - length + 1 .. T and the first
    # full window sits at bar `length - 1`.
    triples = length - LEGS
    windows = sliding_window_view(codes, triples)

    # Shannon entropy in nats of the pattern shares. The `where` keeps
    # `log(0)` out of the expression, and an empty pattern then contributes
    # exactly `0 * log(1) = 0`, so it needs no second guard. The six terms
    # are accumulated in PATTERNS order, one at a time.
    h = np.zeros(windows.shape[0])
    for k in PATTERNS:
        p = (windows == k).sum(axis=1) / triples
        h -= p * np.log(np.where(p > 0, p, 1.0))
    # One masked triple empties its whole window: a histogram over fewer than
    # `triples` patterns is a different statistic, not a smaller sample of
    # this one.
    bad = (windows < 0).any(axis=1)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(bad, np.nan, h)
    perment = Series(out, index=close.index)

    # Offset
    if offset != 0:
        perment = perment.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        perment.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    perment.name = f"TS_PERMENT_{length}_{DIMENSION}"
    perment.category = "statistics"

    return perment


ts_perment_20.__doc__ = \
"""Permutation entropy of close (TS_PERMENT)

Bandt-Pompe permutation entropy at order 3: slide a three-close triple over
the window, label each triple by the ORDER of its three closes (six possible
orderings), and take the Shannon entropy in nats of how often each ordering
occurs.

    TS_PERMENT = -sum over the 6 orderings of p * log(p),
                 p = count / (length - 2)

How ordered the recent path is, and nothing about how far it moved: a window
whose 18 triples spread evenly over the six orderings scores at the ceiling,
and a window whose triples all read the same way scores 0.

⚠ **0.0 is BOTH the flat window and the monotone one.** 20 identical closes
and 20 strictly rising closes both read exactly 0.0, because a tie is broken
by index and so reads as a rise (measured: 281 of 281 fired bars exactly 0.0
on each of a flat and a rising 300-bar frame). A strongly trending frame
reads a median of 0.0 (1,236 of 1,481 bars, at a 2.5-sigma-a-bar drift). The
column cannot tell a dead stock from a trending one.

⚠ **It cannot see magnitude at all.** Planting a +10, a +50 and a +1000
sigma return at the same bar of a 1,500-bar walk gives a BIT-IDENTICAL
column (15 bars move in each case): all three put that close above
everything around it, and the ordering is all the column reads. It is not a
volatility feature, not a trend-strength feature and not an outlier
detector.

⚠ **It is NOT the column issue #91's screen measured.** The screen prototype
(`docs/issues/screen/ind_screen.py`, candidate `ts_perment_20`) sums over
`for k in (0, 1, 3, 4, 6, 7)` of its own `4*(a<b) + 2*(b<c) + (a<c)` code.
Two of those codes, 1 and 6, are unrealisable (6 needs `a < b < c` together
with `a >= c`), and two realisable ones, 2 and 5, are missing -- so the
prototype is a FOUR-pattern sum that drops 25.90% of a walk's triples.
`CLAUDE.md` says Gate A starts from the source formula and not from the
prototype, so this module is the six-pattern form; measured against the
prototype it is Spearman 0.5487 on a walk, 0.4817 on a tick-rounded walk and
-0.0296 on a coarse grid. Issue #91's Gate E numbers (max |rho| 0.2046 vs
`psl`) were taken on the prototype and do NOT transfer
(docs/TsPerment20Measured.md).

Source: tsfresh feature_calculators (MIT), `permutation_entropy`, as the
formula is stated by PandasTa issue #91: `permutation_entropy(tau=1,
dimension=3) on 20 closes`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line plus the published Bandt-Pompe
definition, not a read of tsfresh's own code; anything tsfresh does that the
line does not say (how it treats a series shorter than `dimension`, whether
it drops NaNs rather than returning NaN) is unverified here. What IS
independently checked is the DEFINITION of the ordinal pattern, spelled with
numpy's own `argsort`: the 3-bit code above is a bijection with
`argsort(argsort(x))` over all 27 triples drawn from {1, 2, 3} -- every weak
order on three points, ties included -- and tsfresh's own spelling
(`np.unique(argsort(argsort(X)), axis=0)`, then `-sum(p log p)`) run window
by window is bit-equal to this module on 581 of 581 bars of each of four
frames, two of them with ties (docs/TsPerment20Measured.md, Gate A3).

Five readings the wording leaves open, decided and priced in
docs/TsPerment20Measured.md rather than assumed (A5, on a 1,500-bar walk, a
tick-rounded walk and a coarse grid):
* SIX orderings, the realisable ones. Rejected: the prototype's four
  (Spearman 0.5487 / 0.4811 / 0.6067 against this port, measured with the
  tie rule held fixed).
* The entropy is in NATS and unnormalised, tsfresh's form. Dividing by
  `log 6` -- the prototype does -- is a strict rescaling (Spearman exactly
  1.000000), so it is the one choice here a rank miner cannot see.
* Ties are broken by INDEX, the earlier close counting as the smaller, which
  is what the installed numpy's `argsort` does on a 3-element array --
  measured over all 27 triples, not assumed: `argsort`'s default `kind` is
  not documented as stable, so if that ever changes the oracle in
  `tests/test_ts_perment_20.py` fails rather than the module drifting
  silently. Rejected: the prototype's strict-`<` folding.
  Free on a continuous path (bit-equal on 1,481 of 1,481 bars of a walk) and
  decisive on a coarse one (Spearman 0.0384 where 46.33% of triples hold a
  tie).
* The window is 20 CLOSES, so 18 triples, and the first value lands at bar
  19. Rejected: 20 TRIPLES, which needs 22 closes (Spearman 0.8895 / 0.9063
  / 0.9287).
* The input is the CLOSES, the issue's "on 20 closes". Rejected: the 19
  returns of the same window, which is an almost unrelated column
  (Spearman 0.1311 / -0.0538 / 0.0600). `ts_binent_20` and `ts_c3_20` are
  this fork's return-based tsfresh ports; this one is not.

Discrete, and heavily tied: the value is a function of the window's pattern
COUNT VECTOR and nothing else. 5,978 count vectors satisfy the one
structural constraint (consecutive triples share a comparison), carrying
175 distinct values to 1e-12 between 0.0 and the ceiling -- so a rank
statistic over this column carries many tied ranks by construction
(measured: 160 distinct float64 values, 97 of them distinct at 1e-12, over
1,481 bars of a walk). At lengths 6 and 7 the constraint is exhaustively
equal to attainability (63 of 63, 116 of 116); at 20 that is evidence, not
a proof.

The top of the range is **1.7917594692280547**, ONE ULP BELOW `math.log(6)`
= 1.791759469228055, because the six terms are accumulated one ordering at a
time -- so `value <= log 6` holds but `value == log 6` never does. It is
attained: a 20-close window with three triples in each ordering exists and
is pinned in `tests/test_ts_perment_20.py`.

Causal: bar T reads closes T - length + 1 .. T, measured by a
future-perturbation sweep -- 0 of 37 offsets in each of the six
configurations run (three frames at the default, plus `length` 10, 60 and 4
on the walk).
Scale-free: stronger than a scale. The column reads only comparisons, so a
strictly increasing transform of price leaves it bit-identical -- x8, x64,
x1024, x10, x3.7 and x0.1 on 1,481 of 1,481 bars of each of seven frames,
and `log`, `sqrt`, `x**3` and `+1000` on the walk (one frame, which is what
was run). That invariance holds up to a float64 COLLAPSE: a transform that
rounds two distinct closes onto the same double can move the column, and the
tie rule makes the collapse invisible only when the earlier close is the
smaller -- on the frames measured none collapses, which is a measurement and
not a guarantee (docs/TsPerment20Measured.md, Gate D). A DRIFT is not such a
transform at all and does move it (Spearman 0.2108 under +0.004 of log drift
a bar), and neither is ROUNDING to a coarser grid: the same path on a coarse
grid is Spearman 0.3796 against the unrounded one. Price granularity is an
input here.
NaN on the first `length - 1` bars, and on any window holding a close that
is NaN or infinite (such a close has no place in an ordering; it sits in
three triples and so empties exactly `length` bars -- measured). A zero,
negative or subnormal close is NOT rejected, unlike in `ts_binent_20` /
`ts_c3_20`: this column takes no ratio and no logarithm, so such a close
still has a well-defined place in the ordering.

Cost: the module holds one int8 code array of `n - 2` and, per ordering, one
bool array of `(n - length + 1, length - 2)`, so memory is O(n * length) and
the windows themselves are a view. At n = 400,000: ~117-120 ms (best of three
on one machine) and a traced peak of 18.5 MB (measured with tracemalloc).

Calculation:
    Default Inputs:
        length=20   (dimension 3, tau 1, both fixed by issue #91)
    code[T] = 4*(c[T-2] <= c[T-1]) + 2*(c[T-1] <= c[T]) + (c[T-2] <= c[T])
    p[k]    = count of code == k over the window's `length - 2` triples
    TS_PERMENT = -sum(p * log(p)) over the six realisable codes
                 (7, 5, 3, 4, 2, 0 -- the order the source sums them in)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 4 -- a three-close window
        holds ONE triple, whose entropy is the constant 0 -- so a smaller or
        missing value falls back to the default. At 4 the column takes
        exactly two values, 0 and `log 2` (measured). Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_PERMENT_{length}_3, in nats, from 0.0 (every triple the
        same ordering) up to 1.7917594692280547 at length 20
"""
