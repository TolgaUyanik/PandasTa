# -*- coding: utf-8 -*-
"""Volume oscillator 9/26 over 12 -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#145`, per issue #78. Source cited by the issue:

    #145: (MEAN(V,9)-MEAN(V,26))/MEAN(V,12)*100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is taken
directly from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:494-495`):

    @cand("g191_145", "volume oscillator 9/26 over 12", G,
          "#145: (MEAN(V,9)-MEAN(V,26))/MEAN(V,12)*100")
    def _(o, h, l, c, v): return 100 * sdiv(mean(v, 9) - mean(v, 26), mean(v, 12))

GATE A -- DERIVATION, operator by operator, each spelling read directly off
the prototype's own (unambiguous) module source:

* `MEAN(X, n)` = `X.rolling(n).mean()` (`ind_screen.py:47`), a trailing
  `n`-bar SIMPLE moving average -- not an EMA, and not GTJA191's own
  `SMA(A,n,m)` recursion, which the report spells differently (and which
  `ind_screen.py:57-59` renders as `ewm(alpha=m/n)`). This matters: the
  nearest already-shipped column, `pvo`, is the same shape built from
  EMAs, see NON-REDUNDANCY below.
* `V` = volume. **No price input is read at all** -- no `C`, `O`, `H` or
  `L` appears in the formula, so this module's signature takes `volume`
  only, the same shape `g191_080` already ships.
* `/ ... * 100` binds left to right, so the source reads
  `((MEAN(V,9) - MEAN(V,26)) / MEAN(V,12)) * 100`: divide first, scale
  second. The prototype writes the same association the other way round
  (`100 * sdiv(diff, mean(v, 12))`), and the code below follows the
  prototype's `100 * (diff / norm)` -- multiplication is commutative in
  IEEE754, so those two orders are bit-identical, while the third possible
  spelling, `(100 * diff) / norm`, rounds after a different operation and
  is NOT. Measured on the 1,500-bar frame of `docs/measure_g191_145.py`:
  the source's own `((A-B)/C)*100` is **bit-identical** to the shipped
  `100*((A-B)/C)`, and `(100*(A-B))/C` is **not** -- `max|diff| =
  7.11e-15` on that frame. The shipped order is the one the source and the
  prototype agree on, which is why it is written that way rather than as
  the more usual `100.0 * x / y` one-liner.
* `sdiv(a, b) = (a / b).replace([inf, -inf], nan)` (`ind_screen.py:41-42`),
  reused here for the same reason as `g191_080`/`g191_076`/`g191_191`: a
  window of entirely zero volume would otherwise make the ratio `+-inf`
  rather than a defined number. See ZERO-DENOMINATOR below.

No disclosed interpretation choice is needed anywhere in this port: every
operator above has exactly one reading, and the port agrees bit-for-bit
with the prototype on the whole 1,500-bar frame of
`docs/measure_g191_145.py` (`max|diff| = 0.0`, NaN masks equal) -- unlike
`g191_040`, whose bar-0 boundary forced one. That comparison runs against
the REAL candidate, loaded out of `docs/issues/screen/ind_screen.py` by
path and called through its own registry, not against a retyped copy of
it; the script prints the retyped copy's agreement with the real candidate
as well, so a transcription slip cannot masquerade as agreement.

CALCULATION, in the order computed below (`fast=9, slow=26, norm=12`):
    fast_mean = MEAN(V, fast)
    slow_mean = MEAN(V, slow)
    norm_mean = MEAN(V, norm)
    G191_145  = 100 * (fast_mean - slow_mean) / norm_mean, inf -> NaN

CAUSALITY. All three terms are `rolling(n, min_periods=n).mean()`, trailing
`n`-bar windows: the value at bar `t` averages `[t-n+1, t]`, every index
`<= t`. The subtraction, the division and the `* 100` are pointwise on bar
`t` alone. Nothing in the chain reads a bar newer than `t`; there is no
`center=True` anywhere, so the one way this chain can look ahead is writing
the result at the wrong bar. `tests/test_g191_145.py` proves both halves:
future-perturbation (real module, 0 of N offsets leak, over a synthetic
volume series rewritten from an offset onward) and a mutant (`importlib`
source read, `exec`'d in memory, shown live different from the real module)
that shifts the final write index `slow` bars into the future.

WARM-UP. Each mean needs its own `n` valid observations, so the first bar
at which all three are defined is `max(fast, slow, norm) - 1`, i.e. `slow -
1` at the shipped defaults (bar **25**), and `min_length = max(fast, slow,
norm)` = **26** bars of history, enforced by `verify_series`. A `NaN`
volume at bar `t` propagates through `min_periods` into every window
containing it, so it blanks the output over `t .. t + slow - 1` -- which
is `max(fast, slow, norm)` = `slow` = 26 bars **in the interior**, where
that span lies wholly inside the already-firing part of the series, and
fewer near either end. All three cases measured on the 1,500-bar frame of
`docs/measure_g191_145.py`:

* `t = 700` (interior): **26** newly-`NaN` output bars, `700..725`, **0**
  bars newly defined, and of the **1,449** bars that stay defined the
  largest move is `4.97e-14`. They are NOT bit-identical, and the script
  prints that (`bit-identical=False`): pandas' rolling mean accumulates in
  a different order once a `NaN` sits in the series, so the untouched bars
  move by float64 rounding. A rounding difference, not a semantic one.
* `t = 1495` (near the end): **5** newly-`NaN` bars, `1495..1499` -- the
  rest of the 26-bar span runs off the frame.
* `t = 10` (inside the warm-up): **11** newly-`NaN` bars, `25..35` -- bars
  `10..24` were already `NaN`, so only the tail of the span is new.

SCALE-FREE. For ANY `k > 0`, exactly (not merely at powers of two):
`MEAN(k*V, n) = k * MEAN(V, n)` algebraically, so

    100 * (k*fast_mean - k*slow_mean) / (k*norm_mean)
      = 100 * (fast_mean - slow_mean) / norm_mean

-- the `k` cancels inside the division itself. The column reads no price
input at all (see Gate A above), so a close/high/low/open rescale cannot
reach it; there is no comparison operator anywhere in the chain, so unlike
`g191_040` there is no near-tie that a rescale could flip. **What the code
actually computes, measured rather than merely asserted:** on the 1,500-bar
frame of `docs/measure_g191_145.py`, volume x8/x64 land **bit-identical**
(power-of-two multiplication is exact in IEEE754, so pandas' rolling-mean
accumulation is exactly scaled too, and the algebraic cancellation survives
in float64); x10/x3.7 land within float64 rounding tolerance. Measured in
the test file and `docs/measure_g191_145.py`.

ZERO-DENOMINATOR. For a NON-NEGATIVE volume series -- the only input this
column is defined for, and NOT something the function enforces -- `MEAN(V,
norm)` is zero exactly when every one of the `norm` bars in its window has
`V = 0`, since no cancellation can produce a zero mean any other way. That
is a halted or zero-turnover stretch at least `norm` bars long. (Hand this
function a SIGNED volume series instead -- this fork ships `vol_delta` and
`vsumd`, which a caller could pass -- and both that statement and the sign
arguments below stop holding; the `inf -> NaN` guard still fires, but the
three cases below are no longer the only ones.) It splits into THREE cases
with different arithmetic, not one, each measured on its own fixture by
`docs/measure_g191_145.py`:

* `fast <= norm` (true at the shipped defaults, `9 <= 12`), so a zero
  `norm` window forces a zero `fast` window too, and the `slow` window
  still contains some non-zero volume: the numerator is
  `0 - slow_mean < 0` and the quotient is `-inf`, which
  `.replace([np.inf, -np.inf], np.nan)` maps to `NaN`;
* every window is all-zero: the quotient is `0/0`, already `NaN` before
  the `.replace` ever sees it;
* `fast > norm`, which the shipped defaults EXCLUDE but a caller can ask
  for: the zero `norm` window no longer forces a zero `fast` window, so
  the numerator can be POSITIVE and the quotient `+inf`. Measured at
  `fast=4, slow=6, norm=2` on `[0, 0, 0, 1000, 1000, 0, 0]`: bar 6 is
  `NaN` as shipped and `inf` with the `.replace` deleted, while bar 5
  stays finite at `33.333333333333336`.

The column is `NaN` in all three. How often any of them happens on real data is
NOT measured here -- that waits on Gate E, the only real-data run in this
protocol. What IS measured: the two synthetic frames whose fire counts are
pinned never reach the branch, because both draw volume from
`rng.uniform(1e4, 1e6)` and so contain **0** zero-volume bars -- the
1,500-bar frame of `docs/measure_g191_145.py` (`fires = 1475 = 1500 - 25`,
no interior gap) and the 900-bar frame of
`tests/test_g191_145.py::test_fires_and_is_not_constant` (`fires = 875 =
900 - 25`). The other synthetic frames in those two files are not checked
for it. All three cases are therefore pinned on dedicated small fixtures:
`tests/test_g191_145.py::test_zero_volume_window_divides_to_nan`,
`::test_all_zero_volume_divides_zero_by_zero_to_nan` and
`::test_fast_above_norm_can_divide_a_positive_numerator_by_zero`, all
three also printed by `docs/measure_g191_145.py`.

NON-REDUNDANCY (disclosed, and partly unmeasured here). The nearest
already-shipped column is `pvo`'s `PVO_12_26_9` -- and the issue's own
prototype screen named it as the leading Gate E comparator at
max |rho| 0.8359 (compute_all, n = 396,588), per-frame max median 0.8432,
verdict DISCLOSE_GAP. It is the same *shape* -- a fast/slow volume-average
spread, scaled to a percentage -- built three ways differently:

| | `G191_145_9_26_12` | `PVO_12_26_9` |
|---|---|---|
| averaging | simple moving average | exponential moving average |
| fast window | 9 | 12 |
| denominator | `MEAN(V, 12)`, a THIRD independent window | the slow EMA itself, `EMA(V, 26)` |

The third row is the structural difference, not just a parameter one:
`PVO` is `100 * (fast - slow) / slow`, a self-normalised spread bounded
below by `-100`; this column divides by an independent 12-bar mean, so it
is not bounded below at all and its denominator can be zero while its
numerator is not (see ZERO-DENOMINATOR above), which `PVO`'s cannot
(`EMA(V,26) = 0` forces every input to 0). Measured on the 900-bar
synthetic volume frame of `docs/measure_g191_145.py` (seed 13, 875
overlapping bars), Spearman `rho` against each of the three neighbours
that isolate one difference at a time:

    PVO_12_26_9 (the shipped column)                 0.743004
    PVO_9_26_9  (same windows, EMA, self-normalised) 0.686191
    same windows and denominator, but EMA-built      0.682165

So on this frame neither the averaging kernel nor the denominator choice
alone accounts for the gap, and the shipped pair sits well under this
fork's 0.90 restatement line. These are SYNTHETIC numbers on one frame and
decide nothing: real-data overlap against the engine's 687 comparators is
Gate E's, run by the launcher, and the issue's own prototype screen put
that figure at |rho| 0.8359 vs `pvo_PVO_12_26_9` -- DISCLOSE_GAP, a
shipping band.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_145(volume, fast=None, slow=None, norm=None, offset=None, **kwargs):
    """Indicator: Volume Oscillator 9/26 over 12 (G191_145)"""
    # Validate Arguments
    fast = int(fast) if fast and fast > 0 else 9
    slow = int(slow) if slow and slow > 0 else 26
    norm = int(norm) if norm and norm > 0 else 12
    min_length = max(fast, slow, norm)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if volume is None:
        return

    # Calculate Result
    fast_mean = volume.rolling(fast, min_periods=fast).mean()
    slow_mean = volume.rolling(slow, min_periods=slow).mean()
    norm_mean = volume.rolling(norm, min_periods=norm).mean()
    result = (100.0 * ((fast_mean - slow_mean) / norm_mean)).replace(
        [np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_145_{fast}_{slow}_{norm}"
    result.category = "volume"

    return result


g191_145.__doc__ = \
"""Volume Oscillator 9/26 over 12 (G191_145)

Guotai Junan's (2017, "GTJA191") alpha `#145`, per issue #78. The spread
between a fast and a slow SIMPLE moving average of volume, expressed as a
percentage of a third, independent moving average of volume: positive when
recent turnover runs above its own longer-run level, negative when it runs
below. Reads volume only -- no price input. Full Gate A derivation,
causality, scale-free and zero-denominator arguments are in the module
source above; see docs/G191145Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        fast=9, slow=26, norm=12
    fast_mean = volume.rolling(fast).mean()
    slow_mean = volume.rolling(slow).mean()
    norm_mean = volume.rolling(norm).mean()
    G191_145  = 100 * (fast_mean - slow_mean) / norm_mean, inf -> NaN

Args:
    volume (pd.Series): Series of 'volume's
    fast (int): Fast volume-average window. Default: 9
    slow (int): Slow volume-average window. Default: 26
    norm (int): Window of the normalising volume average. Default: 12
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_145_{fast}_{slow}_{norm}, a scale-free (dimensionless)
        percentage, unbounded in both directions. NaN in three places:
        the first `max(fast, slow, norm) - 1` bars (25 at the shipped
        defaults); the bars whose windows contain a NaN volume --
        `max(fast, slow, norm)` = 26 of them in the interior, fewer within
        26 bars of either end, where the span runs off the frame or
        overlaps the warm-up (measured: 5 for a hole at bar 1495 of 1,500,
        11 for one at bar 10); and wherever the `norm`-bar volume mean is
        exactly zero, leaving nothing to divide by -- which, for a
        NON-NEGATIVE volume series, means a halted or zero-turnover
        stretch at least `norm` bars long. Hand it a signed series (this
        fork's `vol_delta` or `vsumd`) and a zero mean can also come from
        cancellation; the module source above says what else stops holding
        then.
"""
