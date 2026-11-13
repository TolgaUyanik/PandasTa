# -*- coding: utf-8 -*-
"""Smoothed 3-day change of the 6-day bias -- Guotai Junan's (2017,
"GTJA191", internal quant report) alpha `#22`, per issue #82, which
attributes its copy of the report to HKUDS/Vibe-Trading (MIT) -- a copy NOT
read in this session, see the disclosure below. Source cited by the issue:

    #22: SMA((C-MEAN(C,6))/MEAN(C,6) - DELAY(that,3), 12, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:317-321`):

    @cand("g191_022", "smoothed 3-day change of the 6-day bias", G,
          "#22: SMA((C-MEAN(C,6))/MEAN(C,6) - DELAY(that,3), 12, 1)")
    def _(o, h, l, c, v):
        b = (c - mean(c, 6)) / mean(c, 6)
        return sma(b - delay(b, 3), 12, 1)

The issue's string and the prototype agree exactly, including all four
lengths (6, 3, 12, 1) and the `that` back-reference. ONE reading of the
string has to be fixed, and the prototype fixes it the same way:

* **`DELAY(that,3)` refers to the BIAS, not to the whole bracket.** The
  string's `that` is the immediately preceding expression
  `(C-MEAN(C,6))/MEAN(C,6)`, so the smoothed quantity is
  `bias[t] - bias[t-3]`, a 3-bar change OF the bias -- not
  `bias[t] - (bias - DELAY(bias,3))[t-3]`, which a reading of `that` as
  "the whole subtraction" would give (and which is self-referential, hence
  not a reading at all). The prototype names the bias `b` and writes
  `b - delay(b, 3)`, which is the same resolution. The issue's own one-line
  title -- "smoothed 3-day change of the 6-day bias" -- says it a third
  time.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source in this session -- no fork-wide claim about the other `g191_*` ports
is made here, since none was measured:

* `MEAN(x, d)` = a trailing `d`-bar rolling mean, `x.rolling(d).mean()`
  (`ind_screen.py:47`), whose pandas default `min_periods` equals the
  window, so it is NaN for the first `d-1` bars.
* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift (bar
  `t` reads bar `t-n`), never a look-ahead.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision this fork's sibling GTJA ports already document for the same
  operator (`g191_152.py:32-38`), and one the prototype resolves by
  DEFINING its `sma` as the GTJA recursion rather than a plain mean
  (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an
  exponential moving average with `alpha = m/n`. Here it is
  `SMA(.., 12, 1)`, i.e. `alpha = 1/12`. Implemented as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`: `adjust=False`
  reproduces the recursion exactly (pandas' default `adjust=True` instead
  computes a different, non-recursive weighted average over the whole
  history), and `min_periods=n` masks the recursion until it has seen `n`
  of its own valid inputs -- the convention this fork's sibling GTJA ports
  already spell for the identical operator
  (`pandas_ta/volatility/g191_109.py:101`, `g191_152.py:144`, a momentum
  sibling), and the same `min_periods=length` spelling
  `pandas_ta.overlap.rma` uses on its own `ewm` call (`rma.py:16`; note
  that `wilder_rma` does NOT -- `wilder_rma.py:50` is an SMA-SEEDED
  `ewm(alpha=..., adjust=False)` (`wilder_rma.py:47-49`) with no
  `min_periods`, masking its warm-up POSITIONALLY instead
  (`wilder_rma.py:42-44`, `:52-54`), a different convention; the sibling
  ports' docstrings cite it as a `min_periods` precedent anyway, and this
  one does not). The PROTOTYPE's own `sma` omits `min_periods`
  (`ind_screen.py:59`), so the 12-bar tail of this port's warm-up is this
  FORK's convention and not the source's; both spellings are measured in
  `docs/measure_g191_022.py` and reported in `docs/G191022Measured.md`
  rather than argued.
* `C` = close. No other OHLCV field is read.

CALCULATION, in the order computed below (defaults `bias_length=6,
delay_length=3, smooth_length=12, smooth_weight=1`):
    mean6    = MEAN(C, bias_length)
    bias     = (C - mean6) / mean6
    change   = bias - DELAY(bias, delay_length)
    G191_022 = SMA(change, smooth_length, smooth_weight)

WHAT IT MEASURES. `bias` is where today's close sits relative to its own
6-bar mean, as a fraction of that mean -- positive when price leads its
mean, negative when it lags. `change` is how much that lead/lag has moved
over three bars, so it is an ACCELERATION-like quantity: the first
difference of a mean-reversion gap. The final GTJA `SMA` (`alpha = 1/12`,
a slow EMA) smooths it, which both damps the 3-bar differencing noise and
makes the column a persistent signed series rather than a bar-to-bar flip.

THE SHIPPED `bias` IS THE SAME INNER TERM, and this port does not hide it:
`pandas_ta.momentum.bias` at `length=6, mamode="sma"` computes
`(close / SMA(close,6)) - 1`, which is the same mathematical quantity as
`(C - MEAN(C,6))/MEAN(C,6)`. This port spells the SOURCE's subtraction
form, not the helper's division form, because Gate A is settled bit-for-bit
against the issue's own prototype, which writes the subtraction. The two
spellings are not guaranteed bit-equal in float64 (`(a-b)/b` and `a/b - 1`
round differently), so the difference is MEASURED, not asserted:
`docs/measure_g191_022.py` reports the per-bar difference between the two
inner terms and between the two resulting columns, and
`tests/test_g191_022.py::test_the_inner_term_is_the_shipped_bias_to_float_tolerance`
pins it. What this port adds over the shipped `bias` is the 3-bar
differencing and the 12-bar smoothing; the overlap that remains is Gate E's
business, and Gate E is pending. Two synthetic overlap numbers worth
carrying here rather than only in the receipt, both measured on the
1,500-bar walk and NEITHER of them Gate E: Spearman **0.8088** against
`bias:BIAS_SMA_6` (the inner term) and **0.9116** against
`smi:SMIo_5_20_5` -- the comparator issue #82's PROTOTYPE measured at
0.8842 on the 89 real frames. The second one is above the 0.90 strike line
on synthetic data; `docs/G191022Measured.md` states what does and does not
follow from that.

CAUSALITY. `mean6[t]` is a trailing rolling mean over `[t-bias_length+1,
t]`, every index `<= t`. `bias[t] = (C[t]-mean6[t])/mean6[t]` reads bars
`<= t`. `change[t] = bias[t] - bias[t-delay_length]` reads bars `<= t`
(the shift is backward). The final `SMA` is GTJA's own recursion: each step
reads only `change[t]` and its own PRIOR value, so by induction it is a
function of `change[0..t]` only, hence of `C[0..t]` only. Nothing in the
chain is shifted forward anywhere. `tests/test_g191_022.py` proves this
both by future-perturbation (real module: 0 of 37 offsets leak over a
synthetic walk) and by three mutants (`importlib` source read, `exec`'d in
memory), each shown live (differs from the real module) and then caught at
every one of the 37 offsets: shifting the final write index
`smooth_length` bars into the future; computing `mean6` with
`rolling(bias_length, center=True)` instead of the causal trailing window
(the same `bos` look-ahead bug class CLAUDE.md documents); and reading the
`DELAY` forward (`bias.shift(-delay_length)`), which is this formula's own
most plausible sign slip.

WARM-UP. `mean6` is defined from `t >= bias_length - 1`, and so is `bias`.
`change = bias - DELAY(bias, delay_length)` needs both ends, so it is
defined from `t >= bias_length - 1 + delay_length`. The final `SMA`, with
`min_periods=smooth_length`, needs `smooth_length` valid `change` values,
so `G191_022` is defined from
`t >= bias_length + delay_length + smooth_length - 2` -- **19** at the
shipped defaults, i.e. `min_length = bias_length + delay_length +
smooth_length - 1` = **20** bars of history, enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). A rolling mean
is linear, so `mean6 -> k*mean6`, and
`bias = (k*C - k*mean6)/(k*mean6) = (C - mean6)/mean6` -- the `k` cancels
EXACTLY, for ANY positive `k`. Everything downstream (`change`, the final
recursion) is built from `bias` alone, so the whole column is untouched.
Measured on a synthetic walk: `x8`/`x64` land bit-identical
(multiplication by a power of two is exact in IEEE754 and commutes with
rounding, so the rolling sum, the subtraction and the division all scale
exactly), while `x10`/`x3.7` come out within float64 rounding tolerance
(the same arithmetic rounds differently at a non-power-of-two multiplier,
even though the true mathematical ratio is identical). Measured in the test
file and `docs/measure_g191_022.py`, not merely asserted.

A NaN IN `close` is not guarded and does not propagate the way a reader
might expect, so it is measured rather than claimed: a single NaN empties
`bias_length` bars of `mean6`, hence `bias_length + delay_length` bars of
`change`; the GTJA recursion, being a pandas `ewm`, SKIPS a NaN input
(carrying its previous value forward) rather than emptying its output, so
the column itself stays non-NaN past the warm-up while its level is
displaced. `docs/measure_g191_022.py` prints exactly which output bars
move and how many go NaN.
"""
from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_022(close, bias_length=None, delay_length=None, smooth_length=None,
             smooth_weight=None, offset=None, **kwargs):
    """Indicator: Smoothed 3-Day Change Of The 6-Day Bias (G191_022)"""
    # Validate Arguments
    bias_length = int(bias_length) if bias_length and bias_length > 0 else 6
    delay_length = int(delay_length) if delay_length and delay_length > 0 else 3
    smooth_length = int(smooth_length) if smooth_length and smooth_length > 0 else 12
    smooth_weight = int(smooth_weight) if smooth_weight and smooth_weight > 0 else 1
    min_length = bias_length + delay_length + smooth_length - 1
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    mean6 = close.rolling(bias_length).mean()
    bias = (close - mean6) / mean6
    change = bias - bias.shift(delay_length)
    result = _gtja_sma(change, smooth_length, smooth_weight)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = (
        f"G191_022_{bias_length}_{delay_length}_{smooth_length}_{smooth_weight}"
    )
    result.category = "momentum"

    return result


g191_022.__doc__ = \
"""Smoothed 3-Day Change Of The 6-Day Bias (G191_022)

Guotai Junan's (2017, "GTJA191") alpha `#22`, per issue #82. The 6-day bias
`(close - MEAN(close,6)) / MEAN(close,6)` -- where today's close sits
relative to its own 6-bar mean, as a fraction of that mean -- is
differenced over 3 bars and the result smoothed with GTJA's own recursive
`SMA(.., 12, 1)` (an EMA with `alpha = 1/12`). The column is therefore the
smoothed ACCELERATION of a mean-reversion gap, not the gap itself: the
shipped `bias` at `length=6` is the same inner term, and what this adds
over it is the 3-bar differencing and the 12-bar smoothing. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191022Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        bias_length=6, delay_length=3, smooth_length=12, smooth_weight=1
    mean6    = MEAN(close, bias_length)
    bias     = (close - mean6) / mean6
    change   = bias - DELAY(bias, delay_length)
    G191_022 = SMA(change, smooth_length, smooth_weight)   # GTJA SMA, ewm(alpha=smooth_weight/smooth_length)

Args:
    close (pd.Series): Series of 'close's
    bias_length (int): Rolling window of the mean the bias is taken
        against. Default: 6
    delay_length (int): Lag the bias is differenced over. Default: 3
    smooth_length (int): GTJA SMA length (`n`) of the final smoother.
        Default: 12
    smooth_weight (int): GTJA SMA weight (`m`) of the final smoother. The
        source formula and the prototype both fix `m = 1`; other values
        are untested here, and `m` is cast with `int()`, so three bands
        behave differently: `0 < m < 1` truncates to `alpha = 0` and
        `m >= smooth_length + 1` gives `alpha > 1`, both of which pandas'
        own `ewm` rejects with a ValueError; while
        `smooth_length <= m < smooth_length + 1` truncates to
        `alpha = 1.0`, which pandas ACCEPTS -- no smoothing at all, the
        column becomes the raw 3-bar change, and nothing raises.
        `tests/test_g191_022.py::test_a_weight_that_leaves_alpha_outside_zero_one_raises`
        and `::test_a_weight_of_alpha_one_silently_disables_the_smoother`
        pin the three bands. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_022_{bias_length}_{delay_length}_{smooth_length}_
        {smooth_weight}, a scale-free (dimensionless) column taking both
        signs, unbounded in principle but concentrated near zero in
        practice (a slow EMA of a 3-bar difference of a small ratio). NaN
        for the first bias_length + delay_length + smooth_length - 2 bars
        (19 at the shipped defaults).
"""
