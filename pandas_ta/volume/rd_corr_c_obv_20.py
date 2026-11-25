# -*- coding: utf-8 -*-
"""Rolling correlation of price and OBV (20) -- Reddit (tier 4, ResearchIntel
kb/reddit.db), per issue #168: r/algotrading rd:algotrading:chnbr1
(2019-07-25, https://www.reddit.com/r/algotrading/comments/chnbr1/) --
"walking correlation of z-scored price and OBV (z-scoring does not change a
Pearson correlation)". The issue cites the formula directly, not a script,
so there is no source line number -- Gate A reads the formula from the
issue's own statement (its own instruction: "Gate A starts from the source
formula, not the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_corr_c_obv_20`, which is
mathematically the same reading but is not what Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster): "Try to normalize
indicators (e.g. z-score) and then just use walking correlation." Claimed
use: detect divergence between price and a volume indicator -- NOT
independently tested here. This port ships existence (the column is causal
and scale-free, and the formula is reproduced), not evidence that it detects
divergence.

GATE A -- the issue's formula:

    RD_CORR_C_OBV_20 = rolling Pearson corr(close, OBV(close, volume), 20)

The issue's own parenthetical -- "z-scoring does not change a Pearson
correlation" -- is correct and is why this port z-scores neither input: a
Pearson correlation is invariant to any affine transform `a*x + b` (`a > 0`)
of either series, and a z-score (`(x - mean) / std`) is exactly such a
transform. Skipping the z-score step is therefore not a deviation from the
poster's formula; it is the same number, reached without a pass the
poster's own wording concedes is a no-op on the output. A GLOBAL (whole-
series, constant mean/std) z-score of each input, not a per-point rolling
one -- a rolling z-score re-centers on a different window at every bar and
is a different, non-affine transform -- so this is what
`tests/test_rd_corr_c_obv_20.py` builds to prove it is not merely asserted:
pre-z-scoring each input with its own GLOBAL mean/std before correlating
matches this module's direct correlation to float tolerance.

Window: 20 bars, fixed by the issue's own title and prototype parameter
(`(20)`), not a Gate A judgment call the way `pvcorr`'s window was (issue
#18, no source window at all). A `length` argument is still offered, as the
fork's convention for a fixed-suffix port (`osap_retskew_21`, `lean_tdd_20`)
is a parameter with that default, not a hard constant.

NON-REDUNDANCY WITH `pvcorr` (issue #18, this fork's other price/volume
correlation; see "Related open issue: #18 PVCORR" in #168). `pvcorr`
correlates the bar RETURN against the log CHANGE in volume -- a
return-vs-flow-change relationship. This port correlates the PRICE LEVEL
against the OBV LEVEL -- a trend-vs-cumulative-flow relationship: OBV is
`signed_volume.cumsum()` (`pandas_ta.volume.obv`), so it accumulates every
prior signed volume bar, not just the current one. The two columns read
different windows of history through different transforms of volume
(instantaneous log-ratio vs. all-time running sum), so the issue's own
Gate E prototype numbers (below) read them as un-correlated with each other
in the stage-2 fork-overlap screen (max |rho| 0.5388 vs `qqe`'s
`QQEl_14_5_4.236`, not `pvcorr`).

CAUSALITY. `OBV(close, volume)` at bar T is a cumulative sum of every signed
volume bar up to and including T -- it never reads a volume or close value
later than T. The rolling correlation window `[T-19, T]` is likewise
backward-only. `tests/test_rd_corr_c_obv_20.py` proves this with a
future-perturbation probe (frames identical up to J; bars before J stay
bit-identical) and a mutant that reads the OBV series one bar ahead
(`.shift(-1)`) before correlating.

SCALE-FREE. `OBV` depends only on the SIGN of `close.diff()` and on
`volume`'s magnitude, so multiplying `close` by any positive constant leaves
`OBV` completely unchanged (the sign of a diff is invariant to a positive
scale), and multiplying `volume` by a positive constant `k` scales `OBV` by
exactly `k` -- an affine rescale with `b=0`. A Pearson correlation is
invariant to both, so the whole column is unaffected, bit-exactly for a
power-of-two `k` and within float tolerance otherwise.
`tests/test_rd_corr_c_obv_20.py` checks both inputs separately at
`k = 8, 64` (bit-identical) and `k = 10, 3.7` (tolerance).

Prototype measured this on the screen (2026-10-25, issue #168, NOT re-run in
this session -- quoted, not re-measured): Gate E max |rho| 0.4032 vs
`Dist_to_BB_Lower_pct` (n = 385,814, per-frame max median 0.4107) -- SHIP.
Stage-2 fork overlap (not Gate E): max |rho| 0.5388 vs `qqe:QQEl_14_5_4.236`.
This session's own Gate E run is owed; see docs/RdCorrCObv20Measured.md.
"""
from pandas_ta.utils import get_offset, verify_series
from pandas_ta.utils._pine import correlation as _rolling_pearson
from pandas_ta.volume.obv import obv


def rd_corr_c_obv_20(close, volume, length=None, offset=None, **kwargs):
    """Indicator: Rolling Correlation of Price and OBV (RD_CORR_C_OBV)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    close = verify_series(close, length)
    volume = verify_series(volume, length)
    offset = get_offset(offset)
    if close is None or volume is None: return

    if not close.index.equals(volume.index):
        raise ValueError(
            "rd_corr_c_obv_20: `close` and `volume` are indexed "
            "differently. A correlation read off two misaligned series is "
            "a silent nonsense number."
        )

    # Calculate Result
    obv_series = obv(close, volume)
    out = _rolling_pearson(close, obv_series, length)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = f"RD_CORR_C_OBV_{length}"
    out.category = "volume"

    return out


rd_corr_c_obv_20.__doc__ = \
"""Rolling Correlation of Price and OBV (RD_CORR_C_OBV)

The rolling Pearson correlation between close and On Balance Volume over a
window: does price trend together with cumulative signed volume, or diverge
from it? From a Reddit post (tier 4, untested by the poster), issue #168:
"Try to normalize indicators (e.g. z-score) and then just use walking
correlation." Claimed use: detect divergence between price and a volume
indicator -- NOT independently tested here.

The poster's own z-score step is skipped: a Pearson correlation is already
invariant to an affine rescale of either input, and a z-score is exactly
such a rescale, so z-scoring first and not z-scoring read the same number.
See the module source above for the full source citation, the Gate A
derivation, and the non-redundancy argument against this fork's other
price/volume correlation, `pvcorr` (issue #18).
docs/RdCorrCObv20Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:chnbr1
    (2019-07-25) https://www.reddit.com/r/algotrading/comments/chnbr1/

Calculation:
    Default Inputs:
        length=20
    OBV             = pandas_ta.volume.obv(close, volume)
    RD_CORR_C_OBV   = close.rolling(length).corr(OBV)

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The rolling window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_CORR_C_OBV_<length>, bounded on [-1, 1]. Scale-free by
        construction (a correlation of a price level and a cumulative
        signed-volume level, both of which rescale affinely under a
        positive price/volume rescale) -- see
        docs/RdCorrCObv20Measured.md.
"""
