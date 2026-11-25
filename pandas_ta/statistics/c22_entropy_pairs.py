# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Symbols of the alphabet. The feature's OWN parameter -- the `3` of
#: `SB_MotifThree_quantile_hh` -- so it is a module constant and not a
#: function of `length`.
NUM_LETTERS = 3
#: Word length this column's entropy is taken over. The feature name's two
#: `h`s: `hh` is the entropy of 2-LETTER words, where `h` alone (not shipped
#: here) would be the entropy of single letters and `hhh` / `hhhh` the
#: entropy of 3- and 4-letter words. A module constant for the same reason as
#: `NUM_LETTERS`.
WORD_LENGTH = 2
#: Divisor convention of the z-score catch22 applies before every feature. 1
#: is MATLAB `zscore`'s default, and hctsa is MATLAB; 0 is the population
#: one. Under the quantile binning below this is INERT whenever `sd` is
#: finite and above `NOISE_FLOOR`: the empirical quantile of an increasing
#: affine map of a sample is the same affine map of the quantile, so every
#: letter boundary moves exactly with the data and no point changes letter --
#: measured, not merely argued, in this module's test suite.
ZSCORE_DDOF = 1
#: Fewest returns a window may hold: as many 2-letter WORDS (`length - 1`) as
#: the alphabet has word types (`NUM_WORD_TYPES`, defined below, = 9), so the
#: window has at least one word per type in principle. A smaller or missing
#: `length` falls back to the default.
MIN_LENGTH = NUM_LETTERS ** WORD_LENGTH + 1
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: the empirical quantiles of a near-constant window
#: are decided by the rounding of `c / c1 - 1` rather than by shape. NaN
#: instead. The floor is an ABSOLUTE constant because what it bounds is a
#: dimensionless RETURN, which has no rolling scale of its own to keep
#: causal; 4096 eps is this fork's existing habit on such a quantity
#: (`statistics/c22_ami2.py`, `statistics/c22_ami_timescale.py`,
#: `statistics/c22_periodicity.py`, `statistics/tf_autocorr_1e_60.py`,
#: `statistics/ts_binent_20.py`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: How many distinct word TYPES the alphabet admits: `NUM_LETTERS **
#: WORD_LENGTH` = 9 two-letter words over a 3-letter alphabet.
NUM_WORD_TYPES = NUM_LETTERS ** WORD_LENGTH
#: The largest the Shannon entropy of a distribution over `NUM_WORD_TYPES`
#: categories can be, reached only by a perfectly uniform one. The shipped
#: column's derived bounds are `[0, MAX_ENTROPY]` -- see this module's
#: __doc__.
MAX_ENTROPY = float(np.log(NUM_WORD_TYPES))
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` z-scored slab and a `(rows, length)` integer letter slab, so this
#: budget is what keeps the peak off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def _entropy_pairs_rows(block):
    """The Shannon entropy, in NATS, of overlapping 2-letter words of a
    quantile-ternary symbolization, per row of `block`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored (inert under this binning, see `ZSCORE_DDOF`
    above); cut into `NUM_LETTERS` = 3 letters at its own 1/3 and 2/3
    empirical quantiles; every consecutive pair of letters is one WORD
    (`length - 1` overlapping words); and the Shannon entropy of the
    observed word-type distribution is returned.

    Comes back as NaN for a row holding a non-finite return and for a row
    whose standard deviation is at most `NOISE_FLOOR` or is not finite -- a
    flat window has no z-score, and a window whose squares overflow has none
    either.
    """
    rows, n = block.shape
    pairs = n - 1

    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)

        # The two INTERIOR quantile cut points of the alphabet, one row at a
        # time: Hazen-interpolated empirical quantiles at 1/3 and 2/3 --
        # MATLAB's own `quantile` convention, since hctsa is MATLAB.
        q = np.quantile(z, [1.0 / 3.0, 2.0 / 3.0], axis=1, method="hazen")
        # Letter k is "how many of the two cut points z stands strictly
        # above": z <= q1 -> 0, q1 < z <= q2 -> 1, z > q2 -> 2.
        letter = (z > q[0][:, None]).astype(np.int64) \
            + (z > q[1][:, None]).astype(np.int64)

    # Overlapping 2-letter words: word[t] = (letter[t], letter[t + 1]), coded
    # as a single integer in 0 .. NUM_WORD_TYPES - 1 (0 .. 8).
    code = letter[:, :-1] * NUM_LETTERS + letter[:, 1:]
    code = code + (np.arange(rows) * NUM_WORD_TYPES)[:, None]
    counts = np.bincount(code.ravel(), minlength=rows * NUM_WORD_TYPES)
    counts = counts.reshape(rows, NUM_WORD_TYPES)

    p = counts / float(pairs)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(p > 0.0, p * np.log(p), 0.0)
    entropy = -term.sum(axis=1)

    return np.where(~bad, entropy, np.nan)


def c22_entropy_pairs(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 entropy of 2-letter words in a 3-quantile return
    alphabet (C22ENTROPYPAIRS)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one: `8a / 8b`
    # is the same double as `a / b`, so a x2**k rescale of the price cancels
    # EXACTLY here and nothing downstream can see it.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _entropy_pairs_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22ENTROPYPAIRS_{length}"
    result.category = "statistics"

    return result


c22_entropy_pairs.__doc__ = \
"""catch22 entropy of 2-letter words in a 3-quantile return alphabet (C22ENTROPYPAIRS)

Cut the last `length` daily returns into 3 roughly-equiprobable letters by
their OWN 1/3 and 2/3 empirical quantiles, read off every overlapping
2-letter word (`length - 1` of them), and report the Shannon entropy of the
observed word-type distribution, in NATS, over the 9 possible word types.

    C22ENTROPYPAIRS = H(word[t] = (letter[t], letter[t + 1]))

**Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data
Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical Time-series
CHaracteristics"), feature `SB_MotifThree_quantile_hh` of catch22 1.0 --
hctsa's `SB_MotifThree(y, 'quantile', 3)`, the `hh` (two-letter-word) output
-- applied by PandasTa issue #133 to the last 100 daily simple returns.**
⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION performance on
93 reference problems. That is not return prediction, and nothing here tests
it on BIST: its presence in this fork is existence, not evidence.

The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this fork
is MIT: this module was written from the paper's description of the feature
family (motif / word statistics of a symbolized series) and from hctsa's
published operation name and parameters, never from the reference's source.
No shipped module imports it (a test asserts that over the whole package);
the one place it is run at all is `docs/measure_c22_entropy_pairs.py`,
opt-in, measurement only, the same use the owner's own screen prototype
makes of it.

**ONE READING THE DEFINITION LEAVES OPEN, AND HOW IT WAS SETTLED.** "Quantile"
names the BINNING rule (cut points at the window's own empirical quantiles)
but not which quantile ESTIMATOR to use at a finite sample -- there is more
than one convention for interpolating between order statistics. The cited
source, hctsa's `SB_MotifThree(y, 'quantile', 3)`, is MATLAB, and MATLAB's own
`quantile` is the Hazen rule (`p_k = (k - 0.5) / n`, "type 5",
`numpy.quantile(method="hazen")`, public from MathWorks' own documentation,
no GPL-3.0 source needed), so this port USES Hazen. The rejected alternative
is `numpy.quantile`'s own default (plotting position `p_k = (k - 1) / (n - 1)`,
"type 7") -- the more common convention, and the one a reader reproducing
"the 1/3 and 2/3 empirical quantiles" from the paper's own words alone would
reach for first, but not the source's: the reference-fit measurement
(`docs/C22EntropyPairsMeasured.md` §P1) found no reason to prefer it over
Hazen either -- its median gap to the GPL-3.0 reference TIES Hazen's and its
max gap is worse (0.0437 vs 0.0202). It is disclosed here rather than picked
silently because a different interpolation convention is a different column
at the margin: see the receipt (§P1) for the measured effect of every
candidate convention tried.

**What is INERT here, measured rather than assumed.** The empirical quantile
of an increasing affine map of a sample is the same affine map of the
quantile of the sample, so z-scoring a window before binning cannot move any
letter boundary relative to the data: on six frames, 0 of 467 sampled windows
move under the population z-score (`ddof` 0), under NO z-score at all, or
under a +1 shift. ⚠ The invariance needs a finite, positive `sd`, which is
why the module still blanks on `NOISE_FLOOR` and on a non-finite `sd`.

Calculation:
    Default Inputs:
        length=100, NUM_LETTERS=3, WORD_LENGTH=2, ZSCORE_DDOF=1
    r[t]    = close[t] / close[t-1] - 1
    X       = r[T-length+1 .. T]                      (the window)
    Z       = (X - mean(X)) / sd(X, ddof=1)            (inert, see above)
    q1, q2  = the 1/3 and 2/3 empirical quantiles of Z, Hazen interpolation
    k[t]    = how many of {q1, q2} that Z[t] stands strictly above
    W       = {(k[t], k[t+1]) : t = 1 .. length - 1}   (length - 1 words)
    p       = word-type frequencies of W over the 9 possible types
    C22ENTROPYPAIRS = -sum over p > 0 of p * log(p)

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports on returns use -- so that this column reads SHAPE and not the
rounding of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep (0 of 35 offsets leak on six frames with eight splices apiece, and 0
of 35 at `length` 10, 120 and 250) and by eleven mutants read off this file,
edited and exec'd in memory; every look-ahead mutant that can move a CLEAN
frame is caught at 10 or more of the 35 offsets, which the sweep can see
despite this column's higher tie rate (8.8% to 62.7% of neighbouring bars
tied across the six synthetic frames, against `c22_ami2`'s 7% to 22%,
because this column is an integer bincount rather than a continuous mutual
information); the one exception, a bad-data-mask mutant that back-dates
which bar a NaN return marks bad, is inert on a clean frame (0 of 35) and
caught 12 of 12 offsets on a dirty one -- see `tests/test_c22_entropy_pairs.py`
and `docs/C22EntropyPairsMeasured.md` §B for the full counts.

Scale-free: the price enters only as `c[t] / c[t-1]`, so `8a / 8b` is the
double `a / b` and a x8/x64/2**-40/2**40 price rescale is bit-identical BY
CONSTRUCTION (measured: all 24 cells across six frames). The quantile cut
points and the letter assignment are both decided by order comparisons on
`Z`, which an increasing rescale of the returns themselves cannot reorder
either: measured 0 bars moved under a x10, x3.7, x0.1 or x1.0000001 RETURN
rescale of the walk frame (not bit-identical by construction, since those
factors are not exact in binary -- see the receipt §D2 for the margin
argument).

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR whose
ratio overflows to an infinite return; on a window whose SUM OF SQUARES
overflows although the returns themselves are finite; and under the
blanking rule above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `NUM_LETTERS ** WORD_LENGTH + 1` = 10 -- so a window has at least as
        many 2-letter words as the alphabet has word types -- and a smaller
        or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22ENTROPYPAIRS_{length}, nats, inside [0, log(9)] = [0,
        2.1972245773362196]
"""
