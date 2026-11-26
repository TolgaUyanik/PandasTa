# -*- coding: utf-8 -*-
"""OBV minus its 5-bar SMA, over average volume -- Reddit (tier 4,
ResearchIntel kb/reddit.db), per issue #177: r/algotrading
rd:algotrading:14rriwv (2023-07-05),
https://www.reddit.com/r/algotrading/comments/14rriwv/ -- "OBV vs SMA(OBV,
5)". The issue cites the formula directly, not a script, so there is no
source line number -- Gate A reads the formula from the issue's own
statement (its own instruction: "Gate A starts from the source formula, not
the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_obv_dev5`, which is
mathematically the same reading but is not what Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster): "ADX >40 and OBV is over
its OBV_SMA. OBV SMA is a simple moving average of OBV on a 5 day count."
Claimed use: SPY put-selling trigger claimed 100% success over 10 years --
NOT independently tested here, and this port ships only the OBV-vs-its-SMA
half of the poster's condition (the ADX>40 half is a different indicator
this fork already has, `pandas_ta.trend.adx`, and combining the two into a
single trigger is a strategy decision, not a feature column). This port
ships existence (the column is causal, scale-free and reachable on real
data), not evidence that any trigger built on it succeeds.

GATE A -- the issue's own formula, its "What" line read literally, with the
denominator the issue's own parenthetical fixes explicitly as the scale-free
form (`(OBV - SMA5(OBV)) / SMA20(volume)`, candidate `rd_obv_dev5`):

    OBV             = pandas_ta.volume.obv(close, volume)
    OBV_SMA5        = SMA(OBV, 5)
    AVG_VOLUME_20   = SMA(volume, 20)
    RD_OBV_DEV5     = (OBV - OBV_SMA5) / AVG_VOLUME_20

The poster's own condition is a boolean ("OBV is over its OBV_SMA"), not a
distance -- it does not fix a scale. The issue's own parenthetical supplies
the scale-free reading (dividing the raw `OBV - OBV_SMA5` distance, which
carries the same units as a cumulative signed-volume sum, by a 20-bar
average volume turns a cumulative-volume-scaled number into a volume-ratio
one). The "5" in `OBV_SMA5` is the poster's own stated window ("a simple
moving average of OBV on a 5 day count"); the "20" for the volume average
is the issue's own parenthetical, not a Gate A judgment call the way
`pvcorr`'s window was (issue #18, no source window at all). Both are offered
as parameters with those defaults, not hard constants -- this fork's
convention for a fixed-suffix port (`osap_retskew_21`, `rd_vwio_10`).

NON-REDUNDANCY WITH `rd_corr_c_obv_20` (issue #168, this fork's other
OBV-built column, `pandas_ta/volume/rd_corr_c_obv_20.py`). That port
correlates the PRICE LEVEL against the OBV LEVEL over a rolling window --
a trend-vs-cumulative-flow relationship. This port reads OBV against ITS
OWN trailing SMA -- a momentum-of-flow relationship with no price term at
all. The issue's own prototype measurement (below) reads the two as
un-correlated: this column's next comparator is `aobv_AOBV_LR_2` (0.7632),
not `rd_corr_c_obv_20`.

CAUSALITY. `OBV(close, volume)` at bar T is a cumulative sum of every signed
volume bar up to and including T -- it never reads a volume or close value
later than T (`pandas_ta.volume.obv`, already causal by construction). The
two SMAs are plain trailing windows ending AT T. `tests/test_rd_obv_dev5.py`
proves this with a future-perturbation probe (bars before a perturbation
point J stay bit-identical regardless of what the frame's tail past J is
changed to) and a look-ahead mutant (`importlib`-read source, the OBV series
shifted one bar toward the future with `.shift(-1)` before the SMAs are
taken, `exec`'d in memory -- never a hand-written copy).

SCALE-FREE. `OBV` depends only on the SIGN of `close.diff()` and on
`volume`'s magnitude (`pandas_ta.volume.obv`): multiplying `close` by any
positive constant leaves `OBV`, and therefore the whole numerator
`OBV - OBV_SMA5`, completely UNCHANGED (the sign of a diff is invariant to a
positive scale of the series it is taken from) -- the denominator
`SMA(volume, 20)` does not read `close` at all, so a price-only rescale
leaves this column untouched for ANY positive factor, not merely a
power-of-two one. Multiplying `volume` by a positive constant `k` scales
`OBV`, `OBV_SMA5` and `SMA(volume, 20)` all by exactly `k` (SMA is linear:
`SMA(k*x) = k*SMA(x)`), so the ratio is unchanged -- bit-identical for a
power-of-two `k` (exact in IEEE float), within tolerance otherwise (each
scaled operand carries its own last-bit rounding).
`tests/test_rd_obv_dev5.py` / `docs/measure_rd_obv_dev5.py` measure a
price-only rescale (x8/x64/x10/x3.7, all expected bit-identical) and a
volume-only rescale (x8/x64 bit-identical, x10/x3.7 tolerance) separately.

Prototype measured this on the screen (2026-10-25, issue #177, NOT re-run in
this session -- quoted, not re-measured). Gate E: max |rho| 0.7877 vs
`Dist_to_FWMA_pct_Pctl` (manifest, n = 392,431), top-5 per-frame max median
0.7932 -- DISCLOSE. Next comparators: `Dist_to_FWMA_pct` 0.7871,
`aobv_AOBV_LR_2` 0.7632. Stage-2 fork overlap (not Gate E): max |rho| 0.8724
vs `szo:SZO_14`, per-frame max median 0.8783 -- not a restatement at the
0.90 line. This session's own Gate E run is owed; see
docs/RdObvDev5Measured.md.
"""
from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series
from pandas_ta.volume.obv import obv


def rd_obv_dev5(close, volume, length=None, vol_length=None, offset=None, **kwargs):
    """Indicator: OBV Deviation from its SMA, over Average Volume (RD_OBV_DEV5)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 5
    vol_length = int(vol_length) if vol_length and vol_length > 0 else 20
    min_bars = max(length, vol_length)
    close = verify_series(close, min_bars)
    volume = verify_series(volume, min_bars)
    offset = get_offset(offset)

    if close is None or volume is None: return

    if not close.index.equals(volume.index):
        raise ValueError(
            "rd_obv_dev5: `close` and `volume` are indexed differently. "
            "An OBV built off two misaligned series is a silent nonsense "
            "number."
        )

    # Calculate Result
    obv_series = obv(close, volume)
    obv_sma = sma(obv_series, length=length)
    avg_volume = sma(volume, length=vol_length)
    if obv_sma is None or avg_volume is None:
        return

    out = (obv_series - obv_sma) / avg_volume
    out = out.replace([float("inf"), float("-inf")], float("nan"))

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = f"RD_OBV_DEV5_{length}_{vol_length}"
    out.category = "volume"

    return out


rd_obv_dev5.__doc__ = \
"""OBV Deviation from its SMA, over Average Volume (RD_OBV_DEV5)

On Balance Volume minus its own 5-bar SMA, divided by a 20-bar average
volume -- a scale-free read of how far OBV's current level sits from its
own recent trailing average. From a Reddit post (tier 4, untested by the
poster), issue #177: "ADX >40 and OBV is over its OBV_SMA. OBV SMA is a
simple moving average of OBV on a 5 day count." Claimed use: SPY
put-selling trigger claimed 100% success over 10 years -- NOT independently
tested here, and this port ships only the OBV-vs-its-SMA half of the
poster's two-part condition (the ADX>40 half is this fork's existing
`pandas_ta.trend.adx`; combining them into one trigger is a strategy
decision, not a feature column).

See the module source above for the full source citation, the Gate A
derivation (why the denominator is a 20-bar average volume, per the issue's
own parenthetical) and the non-redundancy argument against this fork's other
OBV-built column, `rd_corr_c_obv_20` (issue #168). docs/RdObvDev5Measured.md
has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:14rriwv
    (2023-07-05) https://www.reddit.com/r/algotrading/comments/14rriwv/

Calculation:
    Default Inputs:
        length=5, vol_length=20
    OBV             = pandas_ta.volume.obv(close, volume)
    OBV_SMA5        = SMA(OBV, length)
    AVG_VOLUME_20   = SMA(volume, vol_length)
    RD_OBV_DEV5     = (OBV - OBV_SMA5) / AVG_VOLUME_20

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The OBV SMA window. Default: 5
    vol_length (int): The average-volume window in the denominator. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_OBV_DEV5_<length>_<vol_length>. Scale-free by construction
        (a cumulative-signed-volume distance divided by an average volume,
        both of which rescale linearly under a positive volume rescale, and
        the numerator is fully invariant to a price-only rescale since OBV
        depends only on the SIGN of close's diff) -- see
        docs/RdObvDev5Measured.md. NaN for the first
        `max(length, vol_length) - 1` bars (the SMA warm-up) and wherever
        the volume average is exactly 0.
"""
