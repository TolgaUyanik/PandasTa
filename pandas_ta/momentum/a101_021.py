# -*- coding: utf-8 -*-
"""Mean/std band regime with volume tiebreak -- Kakushadze's (2016, Wilmott,
"101 Formulaic Alphas") Alpha101 `#21`, per issue #45. Source cited by the
issue: Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the
issue as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the formula
used here is the issue's own restatement of Kakushadze's published text, read
as the source per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

Issue #45's stated formula:

    (mean8+std8 < mean2) ? -1 : (mean2 < mean8-std8 ? 1 : (volume/adv20 >= 1 ? 1 : -1))

OPERATORS, each read from the issue's own formula string:

* `mean(x, d)` / `std(x, d)` = rolling mean / rolling standard deviation of
  `x` over a trailing `d`-bar window. **ASSUMPTION, disclosed:** Kakushadze's
  glossary names `stddev` but does not spell out its degrees-of-freedom
  convention, and no other Alpha101 port in this fork (`a101_048`,
  `a101_058`) establishes one -- `std8` here uses pandas' own rolling-std
  default, `ddof=1`, the same reading the issue's own prototype takes
  (`docs/issues/screen/ind_screen.py`'s `std(x, n): return x.rolling(n).std()`,
  plain pandas, no `ddof` override). This is NOT Pine's `ta.stdev(biased=true)`
  convention (`ddof=0`) -- that convention is for Pine sources, and this is
  not one. It also matches this fork's own general `pandas_ta.statistics.stdev`
  operator, which already defaults to `ddof=1`.
* `adv(d)` = `volume.rolling(d).mean()`. **ASSUMPTION, disclosed:**
  Kakushadze's glossary defines `adv(d)` as the average DAILY DOLLAR volume
  (price times volume) over the past `d` days, not plain share volume. But
  the issue's own measured pre-flight states the prototype's `A101_021`
  column is "unchanged under price x8" -- true only if `adv20` carries no
  price term at all, since a price-scaled dollar-volume `adv20` would change
  the `volume/adv20` ratio under a pure price rescale and flip the tiebreak
  branch on some bars. Reading `adv(d)` as a plain volume rolling mean (the
  issue's own prototype's convention: `docs/issues/screen/ind_screen.py`'s
  `relv(v, n=20): return sdiv(v, mean(v, n))`) is the only reading consistent
  with that disclosed invariant, so it is adopted here. It also matches this
  fork's own existing use of the name: `pandas_ta.volume.maxvol_adv`'s `ADV =
  volume.rolling(long).mean()` is already plain share volume, not dollar
  volume, under this exact acronym.

CALCULATION, in the order computed below:
    m8 = MEAN(close, length)        # length=8
    s8 = STDEV(close, length)       # ddof=1 (pandas default; see ASSUMPTION above)
    m2 = MEAN(close, fast_length)   # fast_length=2
    adv = MEAN(volume, adv_length)  # adv_length=20
    r  = volume / adv
    A101_021 = (m8 + s8 < m2) ? -1 : (m2 < m8 - s8 ? 1 : (r >= 1 ? 1 : -1))

CAUSALITY. Every term (`m8`, `s8`, `m2`, `adv`) is a trailing rolling window
reading only `[t-d+1 .. t]`; the branch selection and `r` are then computed
pointwise from those same backward-looking series. Nothing is shifted
forward. `tests/test_a101_021.py` proves this both by future-perturbation
and by a mutant (`importlib` source read, `exec`'d in memory) that shifts
the whole write index `adv_length=20` bars into the future (`result =
result.where(mask).shift(-adv_length)`): shown live, then caught at every
offset past the warm-up. Two weaker mutants were tried first and rejected as
quantisation artefacts of the discretised `{-1, 1}` output, not causality
gaps: a 1-bar look-ahead on `s8` alone caught only 8 of 35 offsets, and
shifting the write index by `length=8` bars caught 32 of 35 -- in both
cases the regime decision at most offsets is far enough from its own
decision boundary that a small perturbation does not flip the sign, so the
leak goes undetected even though it is real. Shifting by the full
`adv_length=20` bars widens the affected window enough to be caught every
time (see `docs/measure_a101_021.py`).

SCALE-FREE. Scaling `close` by a positive constant `k` scales `m8`, `s8` and
`m2` all by the same `k` (rolling mean and std are both linear/positively
homogeneous in their input), so `m8+s8 < m2` and `m2 < m8-s8` are each a
comparison of two quantities scaled by the identical `k > 0` -- their truth
value is unchanged, and the volume-only tiebreak branch is untouched by a
price rescale. Scaling `volume` by `k` scales both `volume` and `adv` in `r
= volume/adv` identically, leaving the ratio -- and hence the `r >= 1`
branch -- unchanged; the price-only branches are untouched by a volume
rescale. The whole chain is scale-free by construction, for a positive
rescale of EITHER `close` OR `volume` independently. Measured in the test
file, not merely asserted. x8/x64 is bit-identical as a mathematical
certainty (power-of-two multiplication is exact in IEEE754, so every scaled
comparison lands on the identical bit pattern). x10/x3.7 is only guaranteed
within the test's 1e-9 tolerance; on the synthetic walk measured in
`docs/measure_a101_021.py` it happens to also come out bit-identical
(max|diff|=0.0), an empirical, seed-dependent result, not a general
guarantee the way x8/x64 is.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def a101_021(close, volume, length=None, fast_length=None, adv_length=None,
             offset=None, **kwargs):
    """Indicator: Mean/Std Band Regime with Volume Tiebreak (A101_021)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 8
    fast_length = int(fast_length) if fast_length and fast_length > 0 else 2
    adv_length = int(adv_length) if adv_length and adv_length > 0 else 20
    min_length = max(length, fast_length, adv_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    if not close.index.equals(volume.index):
        raise ValueError(
            "a101_021: `close` and `volume` are indexed differently. A "
            "volume/adv ratio read off misaligned series is a silent "
            "nonsense number."
        )

    # Calculate Result
    m8 = close.rolling(length).mean()
    s8 = close.rolling(length).std()
    m2 = close.rolling(fast_length).mean()
    adv = volume.rolling(adv_length).mean()
    r = (volume / adv).replace([np.inf, -np.inf], np.nan)

    regime = np.where(
        m8 + s8 < m2, -1.0,
        np.where(m2 < m8 - s8, 1.0, np.where(r >= 1.0, 1.0, -1.0))
    )
    result = Series(regime, index=close.index)
    mask = m8.notna() & s8.notna() & m2.notna() & r.notna()
    result = result.where(mask)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_021_{length}_{fast_length}_{adv_length}"
    result.category = "momentum"

    return result


a101_021.__doc__ = \
"""Mean/Std Band Regime with Volume Tiebreak (A101_021)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#21`, per
issue #45. A short mean (`mean2`) is tested against a band built from a
longer mean and its standard deviation (`mean8 +- std8`): above the band is
bearish (-1), below is bullish (+1), and inside the band the regime falls
back to a volume tiebreak -- current volume at or above its 20-bar average
is bullish (+1), otherwise bearish (-1). Full Gate A derivation, causality
and scale-free arguments are in the module source above; see
docs/A101021Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=8, fast_length=2, adv_length=20
    m8  = MEAN(close, length)
    s8  = STDEV(close, length)        # ddof=1
    m2  = MEAN(close, fast_length)
    adv = MEAN(volume, adv_length)
    r   = volume / adv
    A101_021 = (m8 + s8 < m2) ? -1 : (m2 < m8 - s8 ? 1 : (r >= 1 ? 1 : -1))

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for the band mean/std. Default: 8
    fast_length (int): Rolling window for the short mean. Default: 2
    adv_length (int): Rolling window for the volume average. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_021_{length}_{fast_length}_{adv_length}, a scale-free
        (dimensionless) regime flag taking only the values -1.0 or 1.0. NaN
        for the first max(length, fast_length, adv_length) - 1 bars.
"""
