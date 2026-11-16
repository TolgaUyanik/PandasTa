# -*- coding: utf-8 -*-
"""Higuchi Fractal Dimension of Close (TFHIGUCHI) -- port of TSFEL's
`higuchi_fractal_dimension` (BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py`, as PandasTa issue #115 states it:

    features.py higuchi_fractal_dimension
    (scale-free form: k = 1..5)

⚠ Those two lines, quoted from the issue, are the WHOLE of the source text
available here. TSFEL is not installed in this worktree, `docs/pine/` does
not carry it, and web access is unavailable, so Gate A does NOT read TSFEL's
own code:
`tests/test_tf_higuchi_30.py::test_the_source_library_is_not_readable_here`
asserts that, so the limitation fails loudly if the environment ever
changes. What Gate A checks is the quantity those lines name -- Higuchi's
fractal dimension (Higuchi 1988): the slope, in log-log, of the curve length
L(k) of a time series measured at spacing k, against 1/k. It is spelled
three independent ways (the owner's screen prototype, a scalar loop in
Higuchi's own 1-based indexing built from `math.fsum`, and an
`np.linalg.lstsq` form on a design matrix with an intercept) and compared
against this module. Nothing here is evidence about how TSFEL handles an
edge the issue does not name -- in particular its `kmax` default, which
published implementations put at 10 and the issue's scale-free form puts at
5.

The scale-free form is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py:276-293` (candidate `tf_higuchi_30`,
local to the owner's machine -- `docs/issues/` is gitignored):

    def _higuchi(W, kmax=5):
        N = W.shape[1]
        lk = []
        for k in range(1, kmax + 1):
            Lm = []
            for m in range(k):
                idx = np.arange(m, N, k)
                n_int = len(idx) - 1
                Lm.append(np.abs(np.diff(W[:, idx], axis=1)).sum(1)
                          * (N - 1) / (n_int * k) / k)
            lk.append(np.log(np.mean(Lm, axis=0)))
        x = np.log(1 / np.arange(1, kmax + 1)); xc = x - x.mean()
        T = np.column_stack(lk)
        return (T - T.mean(1, keepdims=True)) @ xc / (xc ** 2).sum()
    roll(c, 30, _higuchi)

CALCULATION.  Over the `length` closes ending at, and including, the current
bar: for each spacing `k` in `1 .. KMAX`, walk the window in `k` interleaved
strands (one per starting offset `m = 0 .. k-1`), add up the absolute
differences along each strand, normalise each strand by
`(length - 1) / (intervals * k) / k`, and average the `k` strands into
`L(k)`. Then return the ordinary-least-squares slope of `log L(k)` on
`log(1 / k)`. A straight line gives 1 and a space-filling path gives 2.

⚠ THE ONE DELIBERATE DIFFERENCE FROM THE PROTOTYPE is that this module takes
the logarithm of `L(k) / L(1)` where the prototype takes it of `L(k)`, and
it is a Gate D fix rather than a preference. The slope is unchanged in exact
arithmetic -- dividing every `L(k)` by the same positive number shifts every
`log L(k)` by the same constant, which the centring removes -- but the
RATIO is exactly invariant under a binary rescale of the price where the
LOGARITHM is not: `L(k)` scales by exactly 8 under `close * 8` (a power of
two times a float is exact, and so is a sum of exactly-scaled floats), and
`8L(k) / 8L(1)` is bit-for-bit `L(k) / L(1)`, while `log(8 L(k))` is not
`log 8 + log L(k)` in floating point and the leftover moves with `k`. With
the prototype's spelling Gate D would be a tolerance; with this one it is
bit-equality (§D).

A second, smaller difference: the final dot product is summed explicitly
rather than spelled `@`, because `@` is not stable under the block's SHAPE
and this module walks the window block in chunks, so with `@` a bar's value
would depend on how many bars came after it. Measured, not assumed: with
`@` put back, 28 of 200 rows computed ONE PER BLOCK differ from their value
inside the whole block, while chunks of 2, 3, 5, 7, 8 and 16 all agree with
it on this machine (§Z2). The shipped spelling differs on 0 of those 200
rows. ⚠ That `@` figure runs through BLAS and is a property of this
machine's dispatch, so the test module pins the shipped spelling's
shape-stability and not the `@` count.

The cost of the two respellings is bit-equality with the prototype:
measured over twelve synthetic frames at the default length, about 6,600 of
the 13,259 bars both define differ, by at most **4.219e-15**, with identical
NaN masks. A mutant of THIS file with both spellings put back is bit-equal
to the prototype on all twelve frames, which leaves nothing else between
them. (About, because the COUNT is itself a count of last bits -- 6,687 on
the default numpy dispatch and 6,593 with AVX-512, AVX2 and FMA3 off --
while the mask equality reproduces under both and the ceiling is the
AVX-disabled run's, the worse of the two; the default reads 3.997e-15. §F2
of the Measured doc tabulates the figures this port quotes, what each reads
on the two dispatches, and which of the two is quoted.)

THE ANCHORS ARE EXACT, WHICH IS UNUSUAL FOR THIS KIND OF PORT.  An
arithmetic ramp has Higuchi dimension 1 in exact arithmetic -- every lag-k
difference is the same number, so `L(k) = step * (length - 1) / k` and the
slope on `log(1/k)` is 1 -- and the module reads 1.0000000000000002 on every
one of the 1,471 bars of such a frame. A Brownian path (true dimension 1.5)
reads a mean of 1.5137 over 1,000 disjoint 30-bar windows and iid normal
noise (true dimension 2.0) reads 1.9978 (§A4).

CAUSALITY.  The window is a plain trailing `sliding_window_view` ending at
bar `T`; nothing is shifted forward. `tests/test_tf_higuchi_30.py` proves
this by future-perturbation sweeps, by five mutants read off this file,
edited and exec'd in memory, and -- for the chunk loop, which a single-chunk
sweep cannot see -- by re-running the prefix-truncation limb and the equality
with the default run at chunk budgets of one and seven rows (§B3), on top of
`test_the_arithmetic_does_not_depend_on_the_block_shape`, which is what
actually makes the chunk loop safe. ⚠ The budget sweeps are prefix work, not
a future sweep, and `CLAUDE.md`'s Gate B says prefix truncation alone proves
nothing: the live mutants are the proof, the budget runs are the check that
chunking did not break it.

SCALE-FREE.  Bit-identical under an exact binary factor (x8, x64, 2**-40,
2**40 and 2**100 on ten frames, and under x8 at `length` 10 / 20 / 30 / 60 /
250), and within 5.906e-14 absolute under an arbitrary one (x10, x3.7, x0.1,
x1.0000001). ⚠ A level SHIFT is ALSO invariant here, in exact arithmetic --
the column reads only DIFFERENCES of closes -- so it cannot serve as this
port's anti-vacuity check; that a shift moves nothing is measured (within
4.006e-11 at +1e6) and `0 < fires < n` plus a non-constant column are
asserted instead (§D).

⚠ IT IS TIME-REVERSAL BLIND.  Reversing the closes inside a window maps each
strand's multiset of lag-k differences onto itself, so the dimension cannot
see the arrow of time: measured max |diff| **6.661e-16** over 500 sampled
windows, with 71 of them moving in their LAST BIT because the strand sums
then run in the opposite order (the AVX-disabled dispatch, the worse of the
two; the default run reads 4.441e-16 and 59 windows -- §F2). A permutation
moves it by up to 1.0204 and a
rotation by up to 0.2771, so it is not order blind in general -- only to this
one symmetry (§L).

⚠ IT NEARLY RESTATES `vhf`.  `VHF_28` is `(max - min) / sum|close diff|`
over 28 bars, and `sum|close diff|` over the window IS this column's `L(1)`:
both measure how far a path travels per unit of range. Measured on eight
1,500-bar synthetic frames: pooled Spearman -0.8901, per-frame |rho| 0.4721
.. 0.8284 with a median of 0.7151 (§L4). The 2026-10-24 screen behind the
issue read 0.6496 against the same column on 12 real frames and called it
"not a restatement at the 0.90 line"; this port agrees and discloses the
figure rather than burying it. ⚠ Gate E's comparator set is the engine's,
not the fork's, so a SHIP verdict there does not settle this -- the owed
item and its revert rule are in `docs/TfHiguchi30Measured.md`.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The largest spacing `k` the curve is measured at. Fixed -- the screen
#: prototype's, and so the ladder Gate E's prototype figure was measured on.
KMAX = 5
#: The spacings themselves, `1 .. KMAX`.
K_VALUES = tuple(range(1, KMAX + 1))
#: Fewest closes a window may hold. At `k = KMAX` the last starting offset is
#: `m = KMAX - 1`, and it needs a second point at `m + KMAX`, so the window
#: must reach index `2 * KMAX - 1`.
MIN_LENGTH = 2 * KMAX
#: Doubles of window to walk at once; the rows per chunk are
#: `CHUNK_VALUES // length`.
CHUNK_VALUES = 1 << 21

#: `log(1 / k)` for each spacing, and the centred regressor the slope divides
#: by. Module-level because they depend on `KMAX` alone, not on the data.
LOG_INV_K = np.log(1.0 / np.arange(1, KMAX + 1))
LOG_INV_K_CENTRED = LOG_INV_K - LOG_INV_K.mean()
LOG_INV_K_SS = (LOG_INV_K_CENTRED ** 2).sum()


def _higuchi_fd(win):
    """Higuchi fractal dimension of each row of `win`, oldest close first."""
    rows, length = win.shape
    defined = np.isfinite(win).all(axis=1)
    curve = np.empty((rows, KMAX), dtype=float)
    for j, k in enumerate(K_VALUES):
        # The lag-k differences of the whole window; strand `m` is every
        # k-th one of them, which is a stride and not a copy.
        gap = np.abs(win[:, k:] - win[:, :-k])
        strands = []
        for m in range(k):
            strand = gap[:, m::k]
            # `strand.shape[1]` is Higuchi's interval count for this strand,
            # `len(range(m, length, k)) - 1`.
            strands.append(strand.sum(axis=1) * (length - 1)
                           / (strand.shape[1] * k) / k)
        curve[:, j] = np.mean(strands, axis=0)
    # `curve` is NaN for a window holding a non-finite close, and 0 wherever
    # that spacing's differences all vanish -- a flat window at every k, a
    # period-2 window at k = 2 and 4, a period-4 window at k = 4 ALONE (§G
    # measures all three; the last two are why the guard has to read every
    # spacing and not only L(1)). `NaN > 0` is False, so one comparison
    # covers the non-finite case too. The substituted 1.0 never reaches a
    # shipped value -- every row it touches is dropped by `defined` -- and is
    # here so that neither the division nor `log` can warn, not to stand in
    # for anything.
    positive = curve > 0.0
    defined &= positive.all(axis=1)
    safe = np.where(positive, curve, 1.0)
    # The logarithm is taken of the RATIO, not of L(k): see the module
    # docstring. This is what makes an exact binary rescale bit-identical.
    log_l = np.log(safe / safe[:, :1])
    centred = log_l - log_l.mean(axis=1, keepdims=True)
    fd = (centred * LOG_INV_K_CENTRED).sum(axis=1) / LOG_INV_K_SS
    return np.where(defined, fd, np.nan)


def tf_higuchi_30(close, length=None, offset=None, **kwargs):
    """Indicator: Higuchi Fractal Dimension of Close (TFHIGUCHI)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 30
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # Fold +-inf into NaN BEFORE the differences below. An infinite close
    # reaches the invalid flag two ways: ONE of them makes every L(k) of its
    # window infinite, so the RATIO is `inf / inf` -- a site this port's
    # Gate D divergence created -- and TWO of them inside one window make the
    # subtraction itself `inf - inf`. Both raise under
    # `np.errstate(all="raise")`; NaN arithmetic does not. Measured, with a
    # live mutant on each, in docs/TfHiguchi30Measured.md §G.
    c = np.where(np.isfinite(c), c, np.nan)
    n = c.size
    out = np.full(n, np.nan)

    if n >= length:
        win = sliding_window_view(c, length)   # (rows, length), oldest first
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length - 1 + a:length - 1 + b] = _higuchi_fd(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"TFHIGUCHI_{length}"
    result.category = "statistics"

    return result


tf_higuchi_30.__doc__ = \
"""Higuchi Fractal Dimension of Close (TFHIGUCHI)

How rough the last `length` closes are: 1 is a straight line, 1.5 a
random walk, 2 space-filling. ⚠ Near-restates `vhf` (|rho| 0.72).

Source: TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py` `higuchi_fractal_dimension`,
which PandasTa issue #115 quotes as "features.py
higuchi_fractal_dimension" with the scale-free form "k = 1..5". ⚠ That
is the entire source text available in this worktree: TSFEL is not
installed and web access is unavailable, so Gate A checks the quantity
those lines name -- Higuchi's dimension (Higuchi 1988), spelled as the
owner's screen prototype, as scalar loops in the paper's own 1-based
indexing, and through `np.linalg.lstsq` -- and NOT TSFEL's own code.
See `docs/TfHiguchi30Measured.md` §A.

The scale-free form is the owner's screen prototype,
`docs/issues/screen/ind_screen_r2.py`, candidate `tf_higuchi_30`. This
module differs from it in TWO spellings -- the logarithm is taken of
`L(k) / L(1)` so that an exact binary rescale of the price is
bit-identical rather than merely close, and the final dot product is
summed rather than spelled `@` -- which move about 6,600 of the
13,259 bars measured over twelve frames by at most 4.219e-15, and
nothing else: a mutant of the shipped file with both spellings put
back is bit-equal to the prototype on every frame (§A1).

⚠ **It nearly restates `vhf`.** `VHF_28` is `(max - min) /
sum|close diff|` over 28 bars and `sum|close diff|` IS this column's
`L(1)`. Measured on eight 1,500-bar synthetic frames: pooled Spearman
-0.8901, per-frame |rho| 0.4721 .. 0.8284, median 0.7151 (§L4). The
2026-10-24 screen read 0.6496 on 12 real frames. Do not feed a miner
both without knowing that.

⚠ **It is time-reversal blind.** Reversing the closes inside a window
maps each strand's lag-k differences onto itself: measured within
6.661e-16 over 500 sampled windows (71 of them move a last bit, the
sums running in the opposite order). A permutation moves it by up to
1.0204 and a rotation by up to 0.2771, so it is not order blind in
general (§L).

⚠ **It is not bounded to [1, 2].** Measured over ten 1,500-bar
synthetic frames the column runs 0.9458 .. 2.1941 -- below 1 on a
heavily smoothed path, above 2 on iid noise. A consumer must not
assume the nominal range.

**What moves it.** Measured on 1,500-bar synthetic frames
(`python docs/measure_tf_higuchi_30.py A4`): a 40-bar moving average
reads a median of 1.0135, a Gaussian random walk 1.4725 and iid
log-normal noise 1.9945 -- the ordering the dimension exists for. It
is blind to the SIZE and the SIGN of the window (bit-identical at
x-1, x0.5, x2 and x2**60; within 3.997e-15 at x3.7) and to a level
shift (within 4.006e-11 at +1e6), so it is not a volatility measure.
⚠ Those two bounds are the WORSE of two dispatches: the default run
reads 3.775e-15 and the same 4.006e-11, and the first figure comes
from `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`,
which is what CI runs on (§F2).

Calculation:
    Default Inputs:
        length=30, KMAX=5
    W      = close[T - length + 1 .. T]
    for each spacing k in 1 .. KMAX:
        for each offset m in 0 .. k-1:
            S  = SUM |W[m + jk] - W[m + (j-1)k]| over the strand
            Lm = S * (length - 1) / (intervals * k) / k
        L(k) = mean of the k Lm
    TFHIGUCHI = OLS slope of log(L(k) / L(1)) on log(1 / k)
    NaN while the window is incomplete, when it holds a non-finite
    close, and when L(k) is 0 at ANY spacing. Three measured ways in
    (§G): a flat window, where every L(k) is zero; a window of period
    exactly 2, where L(2) and L(4) are zero while L(1) is 29; and a
    window of period exactly 4, where L(4) ALONE is zero and L(2) is
    not

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 10 -- twice KMAX, so the
        last strand at k = KMAX still has two points -- so a smaller or
        missing value falls back to the default. ⚠ KMAX does NOT scale
        with it. Default: 30
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFHIGUCHI_{length}, dimensionless, nominally 1 .. 2 and
        measured 0.9458 .. 2.1941
"""
