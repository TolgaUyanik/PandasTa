# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, DatetimeIndex, Series

from pandas_ta.overlap.sma import sma
from pandas_ta.volatility.bbands import bbands
from pandas_ta.utils import get_offset, verify_series


def tod_profile(close, volume, length=None, bb_length=None, bb_std=None,
                min_samples=None, scope=None, tz=None, offset=None, **kwargs):
    """Indicator: Time-of-Day Volume/Volatility Seasonality Profile (TOD)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    bb_length = int(bb_length) if bb_length and bb_length > 1 else 20
    bb_std = float(bb_std) if bb_std and bb_std > 0 else 2.0
    min_samples = int(min_samples) if min_samples and min_samples > 0 else 5
    scope = scope.lower() if isinstance(scope, str) else "rolling"
    if scope not in ("rolling", "session"):
        scope = "rolling"
    close = verify_series(close, max(length, bb_length))
    volume = verify_series(volume, max(length, bb_length))
    offset = get_offset(offset)

    if close is None or volume is None: return

    _props = f"_{length}_{bb_length}"
    names = [f"TOD_SLOT_RVOL{_props}", f"TOD_SLOT_VVOL{_props}"]

    n = len(close)

    def _all_nan(reason):
        """Degenerate input -- emit the full, stably-named column set filled
        with NaN rather than raising or returning None. See the DEGENERATE
        INPUT section of this module's docstring for why NaN, not raise."""
        d = DataFrame({nm: Series(np.full(n, np.nan), index=close.index)
                       for nm in names})
        d.name = f"TOD{_props}"
        d.category = "volume"
        d.tod_degenerate_reason = reason
        return d

    # ── SLOT KEY (minute-of-day, exactly Pine's `hour(time,tz)*60 + minute(time,tz)`) ──
    try:
        idx = DatetimeIndex(close.index)
    except (TypeError, ValueError):
        return _all_nan("index is not datetime-like")
    if idx.tz is not None and tz is not None:
        idx = idx.tz_convert(tz)
    slot_arr = (idx.hour.values.astype(np.int64) * 60
                + idx.minute.values.astype(np.int64))

    if len(np.unique(slot_arr)) < 2:
        return _all_nan("fewer than 2 distinct minute-of-day slots "
                        "(daily/weekly bars carry one slot; a time-of-day "
                        "profile has nothing to discriminate)")

    # ── PER-BAR RATIOS (Pine `rvolBar` L135 / `volatBar` L140) ──
    bb = bbands(close, length=bb_length, std=bb_std, mamode="sma", ddof=0)
    if bb is None: return _all_nan("bbands returned None")
    bb_width = bb[[c for c in bb.columns if c.startswith("BBB_")][0]]

    if scope == "session":
        # Pine L117-139: sums reset on the day boundary `ta.change(time('1D'))`
        # and the CURRENT bar is added BEFORE the mean is read (L126-133), so
        # the session mean INCLUDES this bar. Replicated exactly; still causal.
        day = Series(idx.normalize(), index=close.index)
        grp = day.ne(day.shift()).cumsum()
        vol_ma = volume.groupby(grp).expanding().mean().reset_index(level=0, drop=True)
        bb_ma = bb_width.groupby(grp).expanding().mean().reset_index(level=0, drop=True)
    else:
        vol_ma = sma(volume, length=length)
        bb_ma = sma(bb_width, length=length)

    rvol_bar = (volume / vol_ma.where(vol_ma > 0)).values.astype(float)
    vvol_bar = (bb_width / bb_ma.where(bb_ma > 0)).values.astype(float)

    # ── PROFILE ACCUMULATION (Pine L145-155) ──
    slot_rvol = np.full(n, np.nan)
    slot_vvol = np.full(n, np.nan)
    _sum_v, _cnt_v, _sum_t, _cnt_t = {}, {}, {}, {}

    def _read_step(i):
        """Read bar i's slot mean from STRICTLY-PRIOR same-slot samples."""
        s = slot_arr[i]
        cv = _cnt_v.get(s, 0)
        if cv >= min_samples:
            slot_rvol[i] = _sum_v[s] / cv
        ct = _cnt_t.get(s, 0)
        if ct >= min_samples:
            slot_vvol[i] = _sum_t[s] / ct

    def _accumulate_step(i):
        """Fold bar i's own ratios into its slot, for FUTURE bars to read."""
        s = slot_arr[i]
        v, t = rvol_bar[i], vvol_bar[i]
        if v == v:
            _sum_v[s] = _sum_v.get(s, 0.0) + v
            _cnt_v[s] = _cnt_v.get(s, 0) + 1
        if t == t:
            _sum_t[s] = _sum_t.get(s, 0.0) + t
            _cnt_t[s] = _cnt_t.get(s, 0) + 1

    for i in range(n):
        # ─── CAUSALITY ORDER (do not swap; tests/test_tod_profile.py mutates
        # exactly these two lines to prove the self-inclusion defect is caught) ───
        _read_step(i)
        _accumulate_step(i)

    slot_rvol = Series(slot_rvol, index=close.index)
    slot_vvol = Series(slot_vvol, index=close.index)

    result = [slot_rvol, slot_vvol]

    # Offset
    if offset != 0:
        result = [r.shift(offset) for r in result]

    # Handle fills
    if "fillna" in kwargs:
        for r in result: r.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for r in result: r.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    for r, nm in zip(result, names):
        r.name = nm
        r.category = "volume"

    df = DataFrame({r.name: r for r in result})
    df.name = f"TOD{_props}"
    df.category = "volume"

    return df


tod_profile.__doc__ = \
"""Time-of-Day Volume/Volatility Seasonality Profile (TOD)

Ports the PROFILE ACCUMULATOR (Pine L101-175) of the TradingView community
indicator "Volume & Volatility Time-of-Day - Seasonality Forecast"
(source file: 291 lines, verified by `wc -l`; slug n16YXPSU, vendored at
Backtesting/docs/TradingView/pine/n16YXPSU-Volume-Volatility-Time-of-Day.pine),
ported into AwakenAnalytics/Backtesting TVPTA-6 (2026-08-14, candidate 16).

The question it answers is not "buy or sell" but "at what TIME OF DAY does
this instrument typically wake up". For every minute-of-day slot it keeps a
running mean of two per-bar ratios -- volume vs its own trailing MA, and
Bollinger-Band width vs its own trailing MA -- and reports, for each bar,
what that bar's slot HISTORICALLY does.

pandas_ta Category: "volume". Justification for the pick over "volatility":
the source's primary metric is relative VOLUME (`rvolBar`, Pine L135) --
it is the first metric computed, the one named first in the title, and 2
of the 4 `metric` options ('Volume', 'Both (avg)', 'Both (max)') consume
it; the BB-width leg is the secondary metric. More decisively, every
sibling in `pandas_ta/volatility/` is a pure price-range measure that
takes NO volume argument, so a volume-consuming function there would be
the larger category violation, whereas `pandas_ta/volume/` already hosts
multi-input composites (`avwap_z` takes hlcv, `tri_dir_pressure` takes
ohlcv). ML-register family (downstream, in the Backtesting repo):
"Temporal" -- see docs/indicators/family-temporal.md. Both are correct at
once; they classify along different axes (inputs vs. what the feature
conditions on), the same split `avwap_z` documents.

🔴 HOURLY-ONLY -- THE ONE THING TO KNOW ABOUT THIS MODULE
    This is the first indicator in this fork that is NOT timeframe-agnostic.
    A time-of-day profile needs at least two distinct times of day. On
    DAILY, weekly or monthly bars every timestamp collapses onto a single
    minute-of-day slot and the profile degenerates to a global expanding
    mean -- which carries no seasonality information whatsoever, and would
    silently masquerade as one.

DEGENERATE INPUT -- returns all-NaN, does NOT raise (deliberate)
    When the index has fewer than 2 distinct minute-of-day slots, or is not
    datetime-like at all, the function returns its full, stably-named column
    set filled with NaN (and stamps the reason on `df.tod_degenerate_reason`).
    Raising was considered and rejected as the LESS conservative option:
    this function is wired into a batch indicator engine that is invoked on
    DAILY frames by the majority of that repo's backtests, so a raise
    converts a research indicator into a hard failure across an unrelated
    pipeline, whereas all-NaN is inert -- the consuming miner drops any
    column exceeding 30% NaN before fitting. All-NaN also keeps the emitted
    column NAMES identical between daily and hourly runs, so the downstream
    column manifest / ML register stay stable and the degeneracy is
    DOCUMENTED in one place rather than being invisible by absence.

TIMEZONE CONVENTION (the source's `tz` input is load-bearing; L51, L111)
    `tz=None` (default): slots are read off the index's own wall clock, with
    NO conversion and NO localization -- a tz-aware index keys on its own
    timezone, a tz-naive index keys on its naive values as given.
    `tz="Area/City"`: a tz-AWARE index is `tz_convert`ed first. A tz-NAIVE
    index IGNORES the argument (it is already assumed to be local wall time)
    rather than being localized, mirroring the convention the consuming repo
    already fixed in its own `bist_calendar.local_dates` -- a bare
    `tz_localize` there would silently shift every bar.
    Getting this wrong shifts every slot, so it is stated rather than
    inferred. Note that for a market whose local zone observes no DST
    (Turkey, permanently UTC+3 since 2016), keying on UTC vs. on
    Europe/Istanbul is a pure RELABELING of slot ids and leaves every output
    column bit-identical -- measured, see tests/test_tod_profile.py
    `test_tz_relabeling_is_bit_identical_for_a_no_dst_zone`. For a market
    that DOES observe DST, a fixed non-local `tz` makes slot ids drift by an
    hour twice a year; pass that market's own zone.

SLOT KEY
    `minute-of-day = hour*60 + minute`, exactly Pine L111, NOT a coarser
    hour-of-day bucket. Measured on the consuming repo's hourly cache (209
    `*_1h.parquet` files, 1,243,275 bars): every bar carries `minute == 30`,
    NOT 0 -- so an hour-of-day-only key would have been an equally valid
    relabeling there, but the minute-of-day key is the source's own and
    stays correct on a feed whose bars do not share one minute offset.

COLUMNS (2) -- exactly the source's own two per-slot outputs
    TOD_SLOT_RVOL_{length}_{bb_length}
        Mean of `volume / MA(volume, length)` over all STRICTLY-PRIOR bars
        sharing this bar's slot. Pine `f_slotRvol(curSlot)` (L158-160, L180).
        ">1 means this time of day typically trades above its own baseline."
    TOD_SLOT_VVOL_{length}_{bb_length}
        Same, for `BBwidth / MA(BBwidth, length)`. Pine `f_slotVolat` (L161-163).
        ">1 means the bands typically expand at this time of day."

WHAT WAS BUILT, MEASURED, AND THEN REMOVED (read before re-adding it)
    An earlier revision of this module also emitted two "seasonality-adjusted"
    columns, TOD_RVOL_REL / TOD_VVOL_REL = the bar's own ratio DIVIDED BY its
    slot's historical mean. They were removed after measurement, not on taste:

      - `TOD_RVOL_REL` scored Spearman **+0.934364** against the consuming
        engine's existing `VOL_RATIO` (n=548,754, pooled over 89 BIST_100
        hourly frames / 556,397 bars). `VOL_RATIO` IS this column's own
        numerator (`volume / SMA(volume,20)`, i.e. Pine `rvolBar`) -- so the
        division by the slot mean barely reorders anything.
      - `TOD_VVOL_REL` scored only 0.669583 against the engine's shipped set
        (vs `CHOP`) -- but **+0.999021** against its OWN numerator
        `BBwidth / SMA(BBwidth,20)`, which simply is not an engine column.
        Its apparently-safe score was an artifact of the comparator's absence,
        not evidence of independent content.

    The generalisation, which is the reason this note exists: the slot mean is
    a slowly-varying, near-constant divisor, so `bar_ratio / slot_mean` is
    close to a monotone rescaling of `bar_ratio` and carries almost none of
    the time-of-day information its name advertises. If a
    volatility-EXPANSION ratio is wanted downstream, add it deliberately as a
    volatility-family column named for what it is -- do not reintroduce it
    under a time-of-day name. Full grid:
    Backtesting/backtest_results/tvpta6/tod_overlap_20260814.md

DELIBERATELY NOT EMITTED, and why
    - The raw per-bar ratios `rvolBar` (L135) and `volatBar` (L140). These
      are INTERMEDIATE quantities in the source -- neither is ever plotted
      or tabulated; only the slot means reach output. `rvolBar` is also
      already computed bit-for-bit by the consuming engine as `VOL_RATIO`
      (`volume / SMA(volume,20)`, indicator_engine.py:494 /
      speedy_indicators.py:429), and its `bbWidth` input is already there as
      `BB_BWidth` (`bbands(Close,20,2)` column 3, speedy_indicators.py:141).
      Re-emitting either would be a pure duplicate.
    - A combined "heat" column (Pine `rNow`/`f_combine`, L164-175, L180).
      Every option is a deterministic pointwise function -- mean or max --
      of the two slot columns already emitted, so it adds no information a
      tree cannot reconstruct from its own two inputs.
    - `bb_std` (Pine `bbMult`, L55) is accepted for fidelity but CANNOT
      affect any output: `bbWidth = 2*mult*stdev/basis*100` is linear in
      `mult`, and every output divides bbWidth by a mean of bbWidth, so the
      factor cancels exactly. Asserted in tests, not assumed.

NOT PORTED (the other two of the source's three systems)
    - The LIVE HEAT renderer (L180-197): `plotshape`/`plot`/`barcolor`/
      `bgcolor` gradient drawing plus the `winStart` marker. Presentation
      only; the underlying `rNow` is the slot means already emitted.
    - The entire `barstate.islast` PANEL (L202-292). A single-snapshot
      dashboard computed once on the final bar, not a per-bar causal series
      -- declined for exactly the reason `volume/avwap_z.py` declined its
      source's Module 2. Its contiguous-slot WINDOW MERGING (L217-241) is
      additionally meaningless at 1h resolution, where every "window" is one
      hour wide by construction.
    - `exclSess` (L59, L141-143, L154-155, L181): an optional HHMM-HHMM
      intraday clock window, evaluated via `time(timeframe.period, exclSess,
      tz)`. This is a SUB-HOURLY session window this fork's daily/hourly
      OHLCV pipeline cannot construct -- the same decline rule written up
      for candidate W74Algwa at `pandas_ta/volume/avwap_z.py` (see its
      "Anchor portability" paragraph). Note the contrast with the `scope`
      parameter below, which IS ported precisely because its `isNewDay =
      ta.change(time('1D'))` (L112) is a DAY BOUNDARY -- answerable from a
      single bar timestamp -- and not a clock window.

BASELINE SCOPE (`scope`, Pine `maScope` L89)
    "rolling" (default, matching the source): each bar is measured against
    `MA(., length)`, a trailing window that spans the session break.
    "session": measured against the running mean since the current day
    opened, reset at the day boundary. Ported because the reset is a day
    boundary (see above). The current bar is INCLUDED in its own session
    mean, replicating Pine L126-133 exactly -- causal, but note the first
    bar of each day necessarily reads 1.0.

CAUSALITY
    A slot's mean is built ONLY from bars strictly BEFORE the current bar.
    The loop reads the slot mean first and folds the current bar into its
    slot second; swapping those two statements produces the self-inclusion
    defect in which a bar leaks its own value into its own baseline. That
    swap is performed as an executable MUTANT in
    tests/test_tod_profile.py::test_self_inclusion_mutant_is_detected, which
    loads this module's own source via `importlib`, reverses exactly the two
    marked lines, and shows REAL and MUTANT disagree -- the source's
    `barstate.isconfirmed` gate (L145) is suggestive of this ordering but is
    not proof of a pandas translation, so it is proven rather than asserted.

EXPANDING-WINDOW WARM-UP
    The slot mean is an EXPANDING mean, so early bars rest on far fewer
    samples than late ones -- a genuine walk-forward artifact. Mitigated by
    `min_samples` (default 5, matching the source's own `minDays` default,
    L58): no value is emitted for a slot until it has accumulated at least
    that many strictly-prior samples. This is a floor, not a cure -- the
    sample count keeps growing thereafter, by construction.

Sources:
    https://www.tradingview.com/script/n16YXPSU/

Calculation:
    Default Inputs:
        length=20, bb_length=20, bb_std=2.0, min_samples=5,
        scope="rolling", tz=None

    slot            = hour(index, tz) * 60 + minute(index, tz)
    bbWidth         = BBB(close, bb_length, bb_std)      # 100*(u-l)/mid
    rvolBar         = volume  / SMA(volume,  length)
    volatBar        = bbWidth / SMA(bbWidth, length)
    # strictly-prior same-slot samples only:
    TOD_SLOT_RVOL   = mean(rvolBar[j]  : j < i, slot[j] == slot[i])
    TOD_SLOT_VVOL   = mean(volatBar[j] : j < i, slot[j] == slot[i])

Args:
    close (pd.Series): Series of 'close's. Must carry a DatetimeIndex.
    volume (pd.Series): Series of 'volume's
    length (int): The trailing MA length both ratios are measured against.
        Pine `maLen`. Default: 20
    bb_length (int): Bollinger length for the width metric. Pine `bbLen`.
        Default: 20
    bb_std (float): Bollinger multiplier. Pine `bbMult`. Cancels out of
        every output (see above). Default: 2.0
    min_samples (int): Strictly-prior same-slot samples a slot needs before
        a value is emitted. Pine `minDays`. Default: 5
    scope (str): "rolling" or "session". Pine `maScope`. Default: "rolling"
    tz (str): Timezone to read slots in; only applied to a tz-AWARE index.
        Default: None (use the index as given)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: TOD_SLOT_RVOL, TOD_SLOT_VVOL columns. All-NaN (never
        raising) on degenerate input -- see above.
"""
