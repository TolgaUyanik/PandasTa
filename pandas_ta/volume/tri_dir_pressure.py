# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pandas import Series
from pandas_ta.utils import get_offset, verify_series

# TVPTA-3 acceptance gates (a)-(f) — all six required before this stub is done:
# (a) Causality: no look-ahead (Pine `offset=`/`[-n]`/`security(..., lookahead_on)`
#     all forbidden; HAUDIT-1 measured a lag0 look-ahead inflates expectancy ~2x)
# (b) Pine->pandas semantics verified against the FORK's source, not memory
#     (grep the target pandas_ta function body for every kwarg name you pass —
#     a wrong name is silently swallowed by **kwargs, never raised)
# (c) Reachable via df.ta.<name>() — core.py registration required, the
#     ichimoku_ml lesson (a file that exists but isn't registered is unreachable)
# (d) Numeric correctness spot-checked against the source .pine's own math,
#     not just "runs without crashing"
# (e) Docstring names source URL + author (this stub is pre-filled — verify
#     it matches the .pine source, don't just trust the CSV join)
# (f) Test asserts real behavior (bounded range, known input->output, or a
#     regression the source's own edge cases would catch) — not just "returns
#     a Series"
#
# This is a partial port. Only the source's per-bar "triangular candle-
# direction score" (Pine `scr()`, L51-78) is ported. NOT ported: the
# Gaussian-kernel shape classifier (`cls()`, L91-158), the synthetic
# template-waveform generator (`tpl()`, L161-180), the phase/state
# machine (`var` buffers `sh`/`sc`/`ph`/`buf`/`pol`/`pc`, L199-260), the
# moving average of the plotted output, the shape-change labels, and all
# drawing/coloring code. See the module docstring below for why.


def tri_dir_pressure(open_, high, low, close, volume=None, use_volume=None,
                      offset=None, **kwargs):
    """Indicator: Triangular Directional Pressure (tri_dir_pressure)

    Ports ONLY the source's `scr(o, h, l, c)` triangular-CDF candle-
    direction score (Pine L51-78) plus its `ps = 2*dm - 1` rescale
    (L76-77). Nothing else from the source is ported — see the module
    docstring for the full list and rationale.
    """
    # Validate Arguments
    open_ = verify_series(open_, 1)
    high = verify_series(high, 1)
    low = verify_series(low, 1)
    close = verify_series(close, 1)
    offset = get_offset(offset)
    if use_volume is None:
        use_volume = True
    if not isinstance(use_volume, (bool, np.bool_)):
        raise ValueError(f"use_volume must be a bool, got {type(use_volume).__name__}: {use_volume!r}")

    if any(s is None for s in [open_, high, low, close]):
        return

    # Dtype checked BEFORE finiteness: `np.isfinite` on an object-dtype
    # Series (e.g. a caller accidentally passing strings) raises a raw
    # TypeError, not the ValueError this validation exists to guarantee
    # (same failure mode this fork's `bpress` port already fixed —
    # `pd.api.types.is_numeric_dtype` handles numpy AND pandas nullable
    # extension dtypes uniformly and returns a bool instead of throwing).
    for name, s in (("open_", open_), ("high", high), ("low", low), ("close", close)):
        if not pd.api.types.is_numeric_dtype(s):
            raise ValueError(f"{name} must be numeric, got dtype {s.dtype}")
        arr = s.to_numpy(dtype="float64", copy=False)
        if not np.isfinite(arr).all():
            raise ValueError(f"{name} contains non-finite values (nan/inf) — tri_dir_pressure requires a fully finite OHLC series")

    if use_volume:
        if volume is None:
            raise ValueError("use_volume=True requires a volume series — pass volume= or set use_volume=False")
        volume = verify_series(volume, 1)
        if volume is None:
            return
        if not pd.api.types.is_numeric_dtype(volume):
            raise ValueError(f"volume must be numeric, got dtype {volume.dtype}")
        varr = volume.to_numpy(dtype="float64", copy=False)
        if not np.isfinite(varr).all():
            raise ValueError("volume contains non-finite values (nan/inf) — tri_dir_pressure requires a fully finite volume series")

    # Calculate Result
    o = open_.to_numpy(dtype="float64", copy=False)
    h = high.to_numpy(dtype="float64", copy=False)
    lo = low.to_numpy(dtype="float64", copy=False)
    c = close.to_numpy(dtype="float64", copy=False)

    rng = h - lo
    # op/md clamp the open/close into [low, high] — a no-op whenever the
    # bar is physically valid OHLC (low <= min(o,c), max(o,c) <= high),
    # kept only as the same defensive guard the source itself applies via
    # math.max(math.min(...)) against a malformed bar.
    op = np.clip(o, lo, h)
    md = np.clip(c, lo, h)

    with np.errstate(divide="ignore", invalid="ignore"):
        # Degenerate bar (high == low): direction from open/close only.
        cdf_degenerate = np.where(c > o, 0.0, np.where(c < o, 1.0, 0.5))

        # md == low: right-triangle CDF with the mode pinned at the low.
        cdf_mode_low = np.where(op <= lo, 0.0, 1.0 - np.square((h - op) / rng))

        # md == high: right-triangle CDF with the mode pinned at the high.
        cdf_mode_high = np.where(op >= h, 1.0, np.square((op - lo) / rng))

        # General case: full triangular CDF with mode strictly inside (lo, h).
        lw = md - lo
        rw = h - md
        cdf_left = np.square(op - lo) / (rng * lw)
        cdf_right = 1.0 - np.square(h - op) / (rng * rw)
        cdf_general = np.select(
            [op <= lo, op <= md, op < h],
            [0.0, cdf_left, cdf_right],
            default=1.0,
        )

        cdf = np.select(
            [rng == 0, md == lo, md == h],
            [cdf_degenerate, cdf_mode_low, cdf_mode_high],
            default=cdf_general,
        )

    dm = 1.0 - cdf
    ps = 2.0 * dm - 1.0

    if use_volume:
        result_arr = varr * ps
    else:
        result_arr = ps

    result = Series(result_arr, index=close.index)

    if offset != 0:
        result = result.shift(offset)

    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    result.name = "TRI_DIR_PRESSURE"
    result.category = "volume"

    return result


tri_dir_pressure.__doc__ = \
"""Triangular Directional Pressure (tri_dir_pressure)

Source: TradingView community indicator "Directional Volume Shapes
(Zeiierman)" by Zeiierman,
https://www.tradingview.com/script/3XE8qqfr-Directional-Volume-Shapes-Zeiierman/
(ported into AwakenAnalytics/Backtesting TVPTA continuation, TVPTA-6
candidate 10)

Pine functions replaced: `scr(o, h, l, c)` (L51-78) and its two-line
rescale `dm = scr(...); ps = 2.0*dm - 1.0` (L76-77). Nothing else.

Deliberately NOT ported, and why: this source's *plotted* output is a
decorative pipeline built on top of `ps` — a Gaussian-kernel-smoothed
distribution-shape classifier (`cls()`, Bell/Bimodal/J-shaped via
skewness + peak-counting over a convolved envelope), a synthetic
template waveform keyed off that shape (`tpl()`), and a phase/cycle
state machine (`var` buffers `sh`/`sc`/`ph`/`buf`/`pol`/`pc`,
`barstate.isfirst` kernel cache) that drives which template bar is
plotted this bar. None of that machinery changes `ps` itself — it only
decides how `ps`'s *history* is redrawn as a stylized column shape. It
is genuinely well-built for its own purpose (visual pattern reading)
but is not a numeric feature: the classifier output is a categorical
string, the template is a fixed synthetic curve keyed off that string
(not measured from price), and the whole pipeline is stateful in ways
that add no information beyond what `ps` already carries bar-by-bar.
This port keeps the one part that IS a real per-bar numeric feature.

Calculation:
    Given a bar's Open/High/Low/Close, treat [Low, High] as the support
    of a triangular probability distribution whose mode sits at
    clip(Close, Low, High) (the source's `md`) — i.e. price is modeled
    as most likely to have traded near the close and less likely near
    the far side of the bar's range. `op = clip(Open, Low, High)`.

    cdf = the triangular distribution's CDF evaluated at `op`:
      - High == Low (degenerate bar): cdf = 0 if Close > Open (bullish),
        1 if Close < Open (bearish), 0.5 if equal.
      - md == Low (mode pinned at the low): cdf = 1 - ((High-op)/rng)^2
        for op > Low, else 0.
      - md == High (mode pinned at the high): cdf = ((op-Low)/rng)^2 for
        op < High, else 1.
      - Otherwise (mode strictly inside the range): the standard
        piecewise-quadratic triangular CDF, split at `op <= md`.

    dm = 1 - cdf            (in [0, 1]; high when the open sat low in
                              the bar's likely-price distribution, i.e.
                              price pushed up toward/through the close)
    ps = 2*dm - 1            (in [-1, 1]; TRI_DIR_PRESSURE when
                              use_volume=False)

    TRI_DIR_PRESSURE = volume * ps  when use_volume=True (default,
    matches the Pine source's own default `vw=true`), else ps.

    use_volume=True multiplies by raw volume, exactly like this fork's
    existing `vol_delta` (`volume*(close-open)/(high-low)`) — both are
    unbounded, ticker-liquidity-scale-dependent flow proxies and should
    not be compared across tickers without normalization. use_volume=
    False is the scale-free form: ps is always exactly bounded to
    [-1, 1] by construction (dm is a CDF value in [0, 1]), independent
    of ticker or era — the part of this port most directly usable for
    mining, and NOT equivalent to vol_delta's un-volume-weighted form
    ((close-open)/(high-low), a straight-line fraction of the bar's
    range) since the two use different (linear vs triangular-CDF)
    models of where price spent its time within the bar. "Not
    equivalent" is a narrow, correct claim, not a claim of
    independence: measured on 57 BIST_100 daily tickers (242,745 bars,
    AwakenAnalytics/Backtesting's backtest_results/tvpta6/
    tri_dir_pressure_overlap_20260813.md), ps vs the linear form
    correlates at pearson=0.840 (R^2=0.706) scale-free, and the
    as-deployed (use_volume=False) column correlates with
    VOL_DELTA_APPROX at spearman=0.760 -- MORE collinear than the
    VOL_DELTA/VOL_DELTA_APPROX pair that fork's own family doc already
    flags as redundant twins to prune (spearman=0.666). Genuinely
    different model, substantially overlapping in practice -- both are
    true, and a caller doing feature selection across this family
    should treat all three columns as one collinearity group, not
    assume this one is independent because its formula is.

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's. Required when
        use_volume=True (the default); ignored when use_volume=False.
    use_volume (bool): Multiply ps by volume. Default: True (matches
        the Pine source's own default `vw=true`).
    offset (int): Periods to offset the result. Default: 0

Returns:
    pd.Series: TRI_DIR_PRESSURE
"""
