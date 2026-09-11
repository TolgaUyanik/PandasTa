# -*- coding: utf-8 -*-
from numpy import nan, sign, where
from pandas import DataFrame, Series


def _classify_intrabar(lower):
    """Pine's `upAndDownVolumeCalc()` buy/sell switch, vectorised.

    `docs/pine/RA2vGpkA-ta.pine:393-397`:

        close > open     => isBuyVolume := true
        close < open     => isBuyVolume := false
        close > close[1] => isBuyVolume := true
        close < close[1] => isBuyVolume := false

    Two details that a careless port loses, both load-bearing:

    * `isBuyVolume` is declared `var bool isBuyVolume = true` (`:385`), so when
      NONE of the four conditions holds -- `close == open` AND
      `close == close[1]`, a flat intrabar -- it CARRIES THE PREVIOUS BAR'S
      value rather than defaulting either way. Hence the forward-fill, and the
      initial `True`.
    * `close[1]` is the previous LOWER-timeframe bar and is NOT reset at a
      main-timeframe boundary; only the accumulators are (`:387-392`).
    """
    close, open_ = lower["close"], lower["open"]

    direction = Series(nan, index=lower.index, dtype="float64")
    direction = direction.mask(close > open_, 1.0)
    direction = direction.mask(close < open_, -1.0)

    prev = close.shift(1)
    undecided = direction.isna()
    direction = direction.mask(undecided & (close > prev), 1.0)
    direction = direction.mask(undecided & (close < prev), -1.0)

    # the `var` carry, then Pine's initial `true` for a leading flat run
    return direction.ffill().fillna(1.0)


def _anchor_key(lower, anchor):
    if anchor is None:
        raise ValueError(
            "up_and_down_volume: `anchor` is required. Pass the main-timeframe "
            "grouping explicitly -- either a pandas offset alias ('1h', '1D') "
            "or a Series aligned to `lower.index` naming each row's main bar. "
            "This function does NOT fetch data or guess a period; see "
            "docs/LowerTimeframeData.md."
        )
    if isinstance(anchor, str):
        try:
            return lower.index.floor(anchor)
        except (AttributeError, ValueError) as error:
            raise ValueError(
                f"up_and_down_volume: anchor={anchor!r} could not be applied to "
                f"the lower-timeframe index ({type(lower.index).__name__}). A "
                f"string anchor needs a DatetimeIndex."
            ) from error
    if isinstance(anchor, Series):
        if not anchor.index.equals(lower.index):
            raise ValueError(
                "up_and_down_volume: a Series anchor must share the "
                "lower-timeframe frame's index exactly."
            )
        return anchor.to_numpy()
    raise TypeError(
        f"up_and_down_volume: anchor must be a pandas offset string or a "
        f"Series, got {type(anchor).__name__}."
    )


def _check_ltf(key, who):
    """Pine's `checkLTF()` (`RA2vGpkA-ta.pine:410-417`), ported by measurement.

    Pine raises when the requested lower timeframe is not lower than the main
    one. We are handed frames rather than timeframe strings, so the equivalent
    check is on the RESULT: if the anchor produces about one lower-timeframe
    row per main bar, there are no intrabars and the "delta" is just signed
    volume — which arrives silently, with a plausible-looking column.

    Given this fork's own companion note recommends the coarse 1h-under-daily
    pairing (`docs/LowerTimeframeData.md`), an anchor that is too fine is the
    mistake a caller will actually make.
    """
    from pandas import Series as _Series

    counts = _Series(key).value_counts()
    if float(counts.median()) <= 1.0:
        raise ValueError(
            f"{who}: this anchor yields a median of "
            f"{counts.median():.1f} lower-timeframe rows per main bar, so "
            f"there are no intrabars to split and the delta would just be "
            f"signed volume. The anchor must be strictly COARSER than the "
            f"lower-timeframe frame (Pine's checkLTF, "
            f"RA2vGpkA-ta.pine:410-417)."
        )


def _require_frame(lower, who):
    if lower is None:
        raise ValueError(
            f"{who}: the lower-timeframe frame is REQUIRED and was not given. "
            f"This function does not fetch it -- the engine's floor is 1h and "
            f"yfinance serves sub-hourly bars for roughly 60 days only, so the "
            f"caller must decide what history exists. See "
            f"docs/LowerTimeframeData.md."
        )
    missing = [c for c in ("open", "close", "volume") if c not in lower]
    if missing:
        raise ValueError(
            f"{who}: the lower-timeframe frame is missing {missing}. Needs "
            f"open, close and volume."
        )
    if not lower.index.is_monotonic_increasing:
        raise ValueError(
            f"{who}: the lower-timeframe frame must be sorted by time; "
            f"accumulating intrabar volume out of order silently mixes bars."
        )
    return lower


def up_and_down_volume(lower=None, anchor=None, **kwargs):
    """Indicator: Up and Down Volume (UDV)"""
    lower = _require_frame(lower, "up_and_down_volume")
    key = _anchor_key(lower, anchor)
    _check_ltf(key, "up_and_down_volume")

    direction = _classify_intrabar(lower)
    volume = lower["volume"].astype("float64")

    pos = volume.where(direction > 0, 0.0)
    neg = (-volume).where(direction < 0, 0.0)

    # sort=FALSE. `sort=True` orders rows by ANCHOR VALUE, not by time: a
    # label Series like ['b','b','b','a','a','a'] came back `a` first, i.e. the
    # second hour before the first. The docstring advertises arbitrary main-bar
    # labels (session ids, bar numbers), so a caller using them got a silently
    # time-scrambled frame -- and a `.shift(1)` on that is a look-ahead. With
    # sort=False groups emit in order of first appearance, which is
    # chronological because `lower` is required to be time-sorted.
    grouped = DataFrame({"pos": pos, "neg": neg}).groupby(key, sort=False).sum()
    total = volume.groupby(key, sort=False).sum()

    delta = grouped["pos"] + grouped["neg"]

    udv = DataFrame({
        "UDV_POS": grouped["pos"],
        "UDV_NEG": grouped["neg"],
        "UDV_DELTA": delta,
        # The ML-usable column. Raw up/down volume scales with liquidity and is
        # as dead a feature as a price level; the RATIO is bounded on [-1, 1]
        # and comparable across tickers and across eras.
        "UDV_DELTA_PCT": (delta / total.where(total != 0)).fillna(0.0),
    })
    # only meaningful on the string-anchor path; a Series anchor holds the
    # caller's own labels and inheriting "Date" would mislabel them
    if isinstance(anchor, str):
        udv.index.name = lower.index.name
    udv.name = "UDV"
    udv.category = "volume"
    return udv


up_and_down_volume.__doc__ = \
"""Up and Down Volume (UDV)

Splits each main-timeframe bar's volume into buying and selling pressure using
INTRABAR data, by classifying every lower-timeframe bar as an up-bar or a
down-bar and summing its volume into the matching bucket.

Ported from TradingView's `TradingView/ta` library,
`requestUpAndDownVolume()` (`docs/pine/RA2vGpkA-ta.pine:439-442`) and the
`upAndDownVolumeCalc()` helper it wraps (`:381-404`).
**© TradingView, Mozilla Public License 2.0.**

**It does not fetch anything.** Pine's version calls `request.security()`; this
one takes the lower-timeframe frame as an argument and raises if it is absent.
That is deliberate: the engine's floor is 1h and yfinance serves sub-hourly
bars for roughly 60 days only, so how much history exists is the caller's
problem to state, not this function's to hide. See `docs/LowerTimeframeData.md`
for what the current data source can actually feed it.

Columns:
    UDV_POS        total up volume in the bar
    UDV_NEG        total down volume, as a NEGATIVE quantity (Pine's sign)
    UDV_DELTA      UDV_POS + UDV_NEG
    UDV_DELTA_PCT  UDV_DELTA / total volume, bounded [-1, 1]; **0.0 when the
                   bar has no volume**, which is indistinguishable from a
                   perfectly balanced bar

⚠ **Main bars with no lower-timeframe rows produce NO ROW**, not a NaN row —
`groupby` emits only observed keys. On real gappy BIST intrabars (halts,
half-sessions) the result will not align 1:1 with your main frame. Reindex
against it if you need alignment.

⚠ An anchor that is not strictly coarser than the lower frame RAISES, per
Pine's `checkLTF` (`RA2vGpkA-ta.pine:410-417`): one "intrabar" per bar makes
the delta just signed volume.

⚠ **Only `UDV_DELTA_PCT` is a model feature.** The other three scale with
liquidity and are as unusable as a raw price level -- a delta of 41,700 means
nothing without knowing the ticker's turnover. They ship because they are the
Pine contract and because the ratio is derived from them.

Args:
    lower (pd.DataFrame): The lower-timeframe OHLCV frame. REQUIRED; needs
        `open`, `close`, `volume`, a time-sorted index.
    anchor (str | pd.Series): How lower-timeframe rows group into main bars.
        A pandas offset alias ("1h", "1D") floors a DatetimeIndex; a Series
        aligned to `lower.index` names each row's main bar. REQUIRED -- this
        function never guesses a period.

Returns:
    pd.DataFrame: 4 columns, indexed by main-timeframe bar.
"""
