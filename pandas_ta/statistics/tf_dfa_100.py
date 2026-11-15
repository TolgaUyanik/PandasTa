# -*- coding: utf-8 -*-
"""Detrended Fluctuation Analysis Exponent of Returns (TFDFA) -- port of
TSFEL's `dfa` (BSD-3-Clause), https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py`, as PandasTa issue #112 states it:

    features.py dfa
    (scale-free form: boxes 4..10 (TSFEL: up to n/10, with a plateau cut))

⚠ Those two lines, quoted from the issue, are the WHOLE of the source text
available here. TSFEL is not installed in this worktree, `docs/pine/` does not
carry it, and web access is unavailable, so Gate A does NOT read TSFEL's own
code: `tests/test_tf_dfa_100.py::test_the_source_library_is_not_readable_here`
asserts that, so the limitation fails loudly if the environment ever changes.
What Gate A checks is the quantity those lines name -- the DFA-1 exponent
(Peng et al. 1994): the slope, in log-log, of the root-mean-square
linearly-detrended fluctuation of the return PROFILE against the box size it
is measured over. It is spelled three independent ways (the owner's screen
prototype, a scalar-loop form built from `math.fsum` and the normal
equations, and a `np.polyfit` form) and compared against this module. Nothing
here is evidence about how TSFEL handles an edge the issue does not name --
in particular its "plateau cut", which the issue mentions and the prototype
does not implement.

The scale-free form is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py:255-273` (candidate `tf_dfa_100`, local
to the owner's machine -- `docs/issues/` is gitignored):

    def _dfa(W, boxes=(4, 5, 6, 8, 10)):
        Y = np.cumsum(W - W.mean(1, keepdims=True), 1)
        logF = []
        for s in boxes:
            k = W.shape[1] // s
            Z = Y[:, :k * s].reshape(len(W), k, s)
            t = np.arange(s) - (s - 1) / 2
            b = (Z * t).sum(2, keepdims=True) / (t ** 2).sum()
            R = Z - Z.mean(2, keepdims=True) - b * t
            logF.append(0.5 * np.log(
                np.where((m := (R ** 2).mean((1, 2))) == 0, np.nan, m)))
        L = np.log(np.array(boxes, dtype=float)); Lc = L - L.mean()
        T = np.column_stack(logF)
        return (T - T.mean(1, keepdims=True)) @ Lc / (Lc ** 2).sum()
    roll(ret(c), 100, _dfa)

CALCULATION.  Over the `length` simple returns ending at, and including, the
current bar: subtract the window's mean and cumulatively sum it into the
profile `Y`; for each box size `s` in `BOXES`, cut the first `length // s`
non-overlapping boxes of `Y`, remove a least-squares straight line from each
box on its own, and take `F(s)`, the root mean square of every residual in
every box of that size; then return the ordinary-least-squares slope of
`log F(s)` on `log s` over the five box sizes.

⚠ THE ONE DELIBERATE DIFFERENCE FROM THE PROTOTYPE is the spelling of that
last dot product, and it is a correctness fix rather than a preference. The
prototype writes it as `@`. `@` on a `(rows, 5)` block is not stable under
the block's SHAPE: at small row counts it dispatches differently and the
result moves in its last bit (§Z2 isolates the step; §Z sweeps the budget on
both CPU dispatches -- one row per chunk on the default one, and 1, 2, 5, 7
and 8 rows per chunk with AVX-512/AVX2/FMA3 disabled, which is not monotone
in the row count and so gives no clean threshold). This module walks the window block in chunks, so
with `@` a bar's value would depend on how many bars came AFTER it -- on
which chunk it landed in -- which no causality sweep over a single-chunk
frame can see. Summing the five terms explicitly is shape-stable and depends
on no BLAS. The cost is bit-equality with the prototype: measured over ten
synthetic frames AT THE DEFAULT LENGTH, most of the 11,200 bars both define
agree and about 3,200 differ in their last bit, by at most **4.441e-16**,
with identical NaN masks. (About, because the COUNT is itself a count of
last bits -- 3,209 on the default numpy dispatch and 3,161 with AVX-512,
AVX2 and FMA3 off -- while the 4.441e-16 ceiling and the mask equality
reproduce under both; §F2 of the Measured doc lists every figure that
moves.) Over walk / trend / heavy-tailed at `length` 20, 32, 64, 100 and 250
the ceiling is the same 4.441e-16 and the masks still match -- a separate
table (§A1). A mutant of THIS file with `@` put back is bit-equal to the
prototype on all ten frames, which leaves nothing else between them.

NO DIVERGENCE AT THE EMPTY WINDOWS, unlike `tf_spec_entropy_64`: a window
holding a non-finite return, and one whose returns are all EQUAL (a flat
price, an exact x2 ramp), are NaN here AND in the prototype -- the NaN its
`m == 0` guard injects reaches the slope instead of being swallowed. Measured
as 0 bars on which one reads and the other does not (§A1).

⚠ THE iid CENTRE IS NOT 0.5.  The textbook reading of a DFA exponent is "0.5
is uncorrelated", and on this ladder that is WRONG: 40,000 iid normal returns
read a mean of **0.6289** over 400 disjoint windows (§A5). It is the
estimator's finite-box bias, not a defect in this port -- 200,000 independent
boxes per size give an implied exponent of **0.6292** for the ladder
`(4, 5, 6, 8, 10)`, against 0.5106 for `(10, 16, 25, 40, 64)` and 0.4997 for
`(50, 80, 125, 200, 320)` (§A5b). The ladder is the prototype's, because the
prototype is what the 2026-10-24 screen measured. Read the column against its
own measured centre, never against 0.5.

CAUSALITY.  The window is a plain trailing `sliding_window_view` ending at bar
`T`; nothing is shifted forward. `tests/test_tf_dfa_100.py` proves this by
future-perturbation sweeps, by five mutants read off this file, edited and
exec'd in memory, and by re-running the sweep with the chunk budget cut to
one row per chunk.

SCALE-FREE.  The input is `close.pct_change(fill_method=None)`, a ratio, so a
uniform price rescale cancels before anything else happens: bit-identical
under an exact binary factor (x8, x64, 2**-40, 2**40, 2**100 on eight frames,
and under x8 at `length` 20 / 32 / 64 / 100 / 250), and within 8.105e-15
absolute under an arbitrary one (x10, x3.7, x0.1, x1.0000001) -- the default
dispatch, the worse of the two there (7.994e-15 with AVX-512/AVX2/FMA3 off;
§F2 of the Measured doc tabulates which figures move with the CPU and which
do not). A level SHIFT is not a rescale and moves all 1,400 fired bars, by up
to 4.773e-02.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The box-size ladder, in bars, fixed -- the screen prototype's, and so the
#: ladder Gate E's prototype figure was measured on. It does NOT scale with
#: `length`: at the default 100 the largest box is `length // 10`, which is
#: what the issue quotes TSFEL as using, and at any other `length` it is not.
#: §A5b measures what the ladder costs: this one reads 0.6292 where the
#: textbook exponent of uncorrelated noise is 0.5.
BOXES = (4, 5, 6, 8, 10)
#: Fewest returns a window may hold: two boxes of the largest size. One box
#: would still produce a number -- a straight line through `max(BOXES)`
#: points leaves residuals -- but `F(s)` would then be a single box rather
#: than an average over boxes, so a smaller or missing `length` falls back to
#: the default rather than shipping that.
MIN_LENGTH = 2 * max(BOXES)
#: Doubles of window to detrend at once. The profile has to materialise a
#: `(rows, length)` copy, and the per-box detrend another, so this budget is
#: what keeps the peak off the product `len(close) * length`: the rows per
#: chunk are `CHUNK_VALUES // length`. Measured (§Z), traced peak with the
#: budget against the same run with the budget raised out of reach: 78.0 MB
#: vs 1,369.8 MB at `length` 100 on 400,000 bars, and 73.3 MB vs 1,265.4 MB
#: at `length` 250 on 150,000 -- that pair is the shorter frame because
#: `length` 250 unchunked on 400,000 bars traced 3,377.6 MB and was then
#: OOM-killed on a repeat. It cannot change a value -- every chunk is an
#: independent
#: run of rows, and the arithmetic is shape-stable by construction (see the
#: module docstring on `@`) -- which
#: `tests/test_tf_dfa_100.py::test_the_chunk_budget_cannot_change_a_value`
#: checks at budgets 1, 64, 999 and 10**9.
CHUNK_VALUES = 1 << 21

#: `log s` for each box size, and the centred regressor the slope divides by.
#: Module-level because they depend on `BOXES` alone, not on the data.
LOG_BOX = np.log(np.array(BOXES, dtype=float))
LOG_BOX_CENTRED = LOG_BOX - LOG_BOX.mean()
LOG_BOX_SS = (LOG_BOX_CENTRED ** 2).sum()


def _dfa_alpha(win):
    """DFA-1 exponent of each row of `win`, oldest return first.

    `win` is a `(rows, length)` block of returns. Rows holding a non-finite
    return, and rows whose detrended fluctuation is identically zero at any
    box size, come back as NaN; everything else is the quantity the module
    docstring states.
    """
    rows, length = win.shape
    # The profile. Subtracting the window mean is a no-op in exact arithmetic
    # -- a constant in the returns is a straight LINE in the profile, which
    # every box's own detrend removes -- and it is kept because it is the
    # prototype's expression. Measured cost: at most 1.998e-15 -- the
    # default dispatch, the worse of the two (1.554e-15 with
    # AVX-512/AVX2/FMA3 off; §A8, §F2).
    profile = np.cumsum(win - win.mean(axis=1, keepdims=True), axis=1)
    log_f = np.empty((rows, len(BOXES)), dtype=float)
    defined = np.isfinite(win).all(axis=1)
    for j, size in enumerate(BOXES):
        boxes = length // size
        # The last `length % size` points of the window are dropped, which is
        # the prototype's forward-only pass: 4 of 100 at box 6 and at box 8,
        # none at 4, 5 or 10 (§A7).
        block = profile[:, :boxes * size].reshape(rows, boxes, size)
        # A centred regressor, so the slope is one division and the intercept
        # is the box mean.
        t = np.arange(size) - (size - 1) / 2
        slope = (block * t).sum(axis=2, keepdims=True) / (t ** 2).sum()
        resid = block - block.mean(axis=2, keepdims=True) - slope * t
        mean_square = (resid ** 2).mean(axis=(1, 2))
        # `mean_square` is 0 when the profile is exactly straight inside
        # every box of THIS size. `length` equal returns reach that; whether
        # anything else does is open -- §G tries two block-constant
        # constructions and neither does, because the profile carries the
        # rounding of a cumulative sum. It is NaN only for a window holding
        # a non-finite return. Both are dropped
        # below, so the substituted 1.0 never reaches a shipped value; it is
        # here so `log` cannot warn, not to stand in for anything. `> 0.0` is
        # False for NaN, which is why the NaN case needs no second test.
        defined &= mean_square > 0.0
        log_f[:, j] = 0.5 * np.log(np.where(mean_square > 0.0, mean_square,
                                            1.0))
    # The OLS slope of log_f on log(box). Spelled as an explicit weighted sum
    # rather than as `@`: see the module docstring. This is the whole of the
    # difference from the prototype.
    centred = log_f - log_f.mean(axis=1, keepdims=True)
    alpha = (centred * LOG_BOX_CENTRED).sum(axis=1) / LOG_BOX_SS
    return np.where(defined, alpha, np.nan)


def tf_dfa_100(close, length=None, offset=None, **kwargs):
    """Indicator: Detrended Fluctuation Analysis Exponent (TFDFA)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    # length + 1 closes: the window holds `length` RETURNS, and a return needs
    # a previous close.
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # fill_method=None: a gap must propagate as NaN, never be padded over.
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)
    # Fold +-inf (a zero close in the denominator) into NaN BEFORE the
    # subtraction below. `inf - inf` is the one input that makes this module
    # raise under `np.errstate(all="raise")`; NaN arithmetic does not.
    r = np.where(np.isfinite(r), r, np.nan)
    n = r.size
    out = np.full(n, np.nan)

    if n >= length:
        win = sliding_window_view(r, length)   # (rows, length), oldest first
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length - 1 + a:length - 1 + b] = _dfa_alpha(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"TFDFA_{length}"
    result.category = "statistics"

    return result


tf_dfa_100.__doc__ = \
"""Detrended Fluctuation Analysis Exponent of Returns (TFDFA)

How the fluctuation of the last `length` returns grows with box size:
above the iid centre of 0.63 is trending, below mean-reverting.
Unbounded.

Source: TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py` `dfa`, which PandasTa issue #112
quotes as "features.py dfa" with the scale-free form "boxes 4..10
(TSFEL: up to n/10, with a plateau cut)". ⚠ That is the entire source
text available in this worktree: TSFEL is not installed and web access
is unavailable, so Gate A checks the quantity those lines name -- the
DFA-1 exponent of Peng et al. 1994, spelled as the owner's screen
prototype, as scalar loops over the normal equations, and through
`np.polyfit` -- and NOT TSFEL's own code. See
`docs/TfDfa100Measured.md` §A.

The scale-free form is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py`, candidate `tf_dfa_100`. This
module differs from it in ONE place -- the final dot product is summed
rather than spelled `@`, because `@` is not stable under the block's
shape and this module works in chunks -- which moves about 3,200 of
the 11,200 bars measured over ten frames at the default length by at
most 4.441e-16, and nothing else: a mutant of the shipped file with
`@` put back is bit-equal to the prototype on every frame (§A1).

⚠ **0.5 IS NOT THE NEUTRAL POINT ON THIS LADDER.** The boxes are 4, 5,
6, 8 and 10 bars, where DFA-1's finite-box bias is large: 40,000 iid
normal returns read a mean of 0.6289, and 200,000 independent boxes per
size imply 0.6292 for this ladder against 0.4997 for a ladder of 50 ..
320 (§A5, §A5b). Read it against 0.63, not against 0.5.

⚠ **It is NOT bounded.** Measured over eight 1,500-bar frames the
column runs -0.2197 .. 2.3288, the negative end on a frame with one
large price jump in it. A consumer must not assume [0, 2].

**What moves it.** Measured on 1,500-bar synthetic frames
(`python docs/measure_tf_dfa_100.py L`): AR(1) returns with phi = +0.6
read a median of 1.0580, a Gaussian random walk 0.6444, and AR(1) with
phi = -0.6 reads 0.2913 -- which is the ordering the exponent exists
for. It is blind to the SIZE and the SIGN of the returns (a rescale of
the whole return window shifts every log F(s) by the same constant,
which cancels in the slope: bit-identical at x-1, and within
8.771e-15 at x0.5, x2, x2**60, x3.7 and x-0.1) and to a constant
drift added to them (within 1.554e-15 at +0.001, +0.05 and +1.0).
⚠ Those two bounds are the WORSE of two dispatches: the default run
reads 7.772e-15 and 1.443e-15, and the figures above come from
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, which is
what CI runs on (§L3).

⚠ Unlike a spectral feature, it is NOT blind to the ORDER of the
returns inside the window: over 500 windows sampled from a synthetic
walk a permutation moves it by up to 0.5157, a time reversal by up to
0.3698 and a circular
rotation by up to 0.4282 (§L5).

Calculation:
    Default Inputs:
        length=100, BOXES=(4, 5, 6, 8, 10)
    RET  = close / close[1] - 1
    W    = RET[T - length + 1 .. T]
    Y    = CUMSUM(W - mean(W))                # the profile
    for each box size s:
        k    = length // s                    # boxes, the tail dropped
        F(s) = RMS over the k boxes of (Y - the box's own OLS line)
    TFDFA = OLS slope of log F(s) on log s
    NaN while the window is incomplete, when it holds a non-finite
    return, and when F(s) is 0 at ANY one box size -- the profile
    exactly straight inside every box of that size, which `length`
    equal returns reach; two constructions with merely block-constant
    returns were tried and do NOT reach it (§G)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 20 -- two boxes of the
        largest size -- so a smaller or missing value falls back to the
        default. ⚠ The box ladder does NOT scale with it. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFDFA_{length}, dimensionless, unbounded
"""
