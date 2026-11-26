# -*- coding: utf-8 -*-
"""Percentile of the 100-bar high-low range among the last 500 -- Reddit
(tier 4, ResearchIntel kb/reddit.db), per issue #169: r/algotrading
rd:algotrading:1nrkjby (2025-09-27),
https://www.reddit.com/r/algotrading/comments/1nrkjby/ -- "measured the
percent change between highest high and lowest low for about 100 periods.
Then measure that variable's lowest 20th percentile value over 500
periods." The issue cites the formula directly, not a script, so there is
no source line number -- Gate A reads the formula from the issue's own
statement (its own instruction: "Gate A starts from the source formula, not
the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_range100_pct500`, which is
mathematically the same reading but is not what Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster), quoted above. Claimed use:
flags choppy/consolidating markets when the 100-bar range sits in its own
lowest 20th percentile over the trailing 500 bars -- NOT independently
tested here. This port ships existence (the column is causal and
scale-free, and the formula is reproduced), not evidence that it detects
chop.

GATE A -- the issue's formula:

    R                     = (HHV(high, 100) - LLV(low, 100)) / LLV(low, 100)
    RD_RANGE100_PCT500    = percentile rank of R over the trailing 500 bars

The issue itself names the shipped form: "Prototype: ...candidate
rd_range100_pct500 (scale-free form: percentile rank of R over 500 bars)."
The poster's own rule -- "chop if R <= its 20th percentile" -- is a BOOLEAN
threshold test on top of this percentile rank, not a different column; the
issue's own Gate E measurement ran on the percentile rank itself (see the
numbers below), so that is what ships, matching `docs/issues/screen/ind_screen_r6.py`:

    r = sdiv(tsmax(high, 100) - tsmin(low, 100), tsmin(low, 100))
    percentile_rank = r.rolling(500).rank(pct=True, method="max")

`HHV`/`LLV` are Pine's trailing-window highest-high / lowest-low, INCLUSIVE
of the current bar -- `pandas.Series.rolling(100).max()` / `.min()` read the
same window. `method="max"` (the prototype's own choice, carried through
here) assigns a TIED value the highest rank among its ties, so two bars
whose `R` reads identically within the trailing 500-bar window both read
the SAME percentile, at the higher end of the tie -- not an average rank.

Division by `LLV(low, 100)`: the prototype's own `sdiv` helper turns a
division result of +-inf (only reachable if a window's lowest low is
exactly 0.0) into NaN; this module matches that behaviour rather than
leaving a signed infinity in a column downstream code may not expect, since
neither the poster's words nor the prototype state a zero-guard of their
own -- there is nothing to diverge from.

CAUSALITY. `R` at bar T reads only `high[T-99 .. T]` and `low[T-99 .. T]` --
the trailing 100-bar window ending AT T. The percentile rank at bar T reads
only `R[T-499 .. T]` -- the trailing 500-bar window ending AT T, ranking the
CURRENT value of `R` against its own past, never a future one.
`tests/test_rd_range100_pct500.py` proves this with a future-perturbation
probe (frames identical up to J; bars before J stay bit-identical) and a
look-ahead mutant (`importlib` source read, the percentile-rank input
shifted one bar in the direction of the future, `exec`'d in memory -- never
a hand-written copy).

SCALE-FREE. `R` is a ratio of two price-scale quantities (`HHV - LLV` and
`LLV`), so multiplying `high` and `low` together by any positive constant
`k` scales both the numerator and the denominator by `k`, leaving `R`
unchanged -- bit-exactly for a power-of-two `k` (IEEE float multiplication
and division are each exact under a power-of-two factor, and the two `k`s
cancel in the same order of operations either way) and within float
tolerance otherwise. A percentile RANK of an unchanged series is itself
unchanged. `tests/test_rd_range100_pct500.py` checks this at `k = 8, 64`
(bit-identical) and `k = 10, 3.7` (tolerance).

Prototype measured this on the screen (2026-10-25, issue #169, NOT re-run in
this session -- quoted, not re-measured): Gate E max |rho| 0.4037 vs
`natr_Pctl` (n = 345,627, per-frame max median 0.3964) -- SHIP. Stage-2 fork
overlap (not Gate E): max |rho| 0.6868 vs
`range_profile:RPO_VA_WIDTH_PCT_110_80`. This session's own Gate E run is
owed; see docs/RdRange100Pct500Measured.md.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def rd_range100_pct500(high, low, length=None, pctlen=None, offset=None, **kwargs):
    """Indicator: Percentile of the 100-Bar Range Among the Last 500 (RD_RANGE100_PCT500)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 100
    pctlen = int(pctlen) if pctlen and pctlen > 1 else 500
    high = verify_series(high, max(length, pctlen))
    low = verify_series(low, max(length, pctlen))
    offset = get_offset(offset)
    if high is None or low is None: return

    if not high.index.equals(low.index):
        raise ValueError(
            "rd_range100_pct500: `high` and `low` are indexed differently. "
            "A range read off two misaligned series is a silent nonsense "
            "number."
        )

    # Calculate Result
    hh = high.rolling(length).max()
    ll = low.rolling(length).min()
    r = (hh - ll) / ll
    r = r.replace([np.inf, -np.inf], np.nan)
    out = r.rolling(pctlen).rank(pct=True, method="max")

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = f"RD_RANGE100_PCT500_{length}_{pctlen}"
    out.category = "volatility"

    return out


rd_range100_pct500.__doc__ = \
"""Percentile of the 100-Bar Range Among the Last 500 (RD_RANGE100_PCT500)

Where does today's 100-bar high-low range, read as a fraction of its own
low, sit among the last 500 readings of that same ratio? From a Reddit post
(tier 4, untested by the poster), issue #169: "measured the percent change
between highest high and lowest low for about 100 periods. Then measure
that variable's lowest 20th percentile value over 500 periods." Claimed use:
flags choppy/consolidating markets -- NOT independently tested here.

The poster's own threshold ("chop if R <= its 20th percentile") is left to
the caller: this column ships the percentile RANK itself, matching the
issue's own stated scale-free form and the prototype it names
(`docs/issues/screen/ind_screen_r6.py`'s `rd_range100_pct500`). See the
module source above for the full source citation and the Gate A
derivation. docs/RdRange100Pct500Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1nrkjby
    (2025-09-27) https://www.reddit.com/r/algotrading/comments/1nrkjby/

Calculation:
    Default Inputs:
        length=100, pctlen=500
    HHV                   = high.rolling(length).max()
    LLV                   = low.rolling(length).min()
    R                     = (HHV - LLV) / LLV
    RD_RANGE100_PCT500    = R.rolling(pctlen).rank(pct=True, method="max")

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    length (int): The high/low range window. Default: 100
    pctlen (int): The percentile-rank lookback. Default: 500
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_RANGE100_PCT500_<length>_<pctlen>, bounded on [0, 1].
        Scale-free by construction (a ratio of two price-scale quantities,
        itself then ranked, which is invariant to the series' own level) --
        see docs/RdRange100Pct500Measured.md.
"""
