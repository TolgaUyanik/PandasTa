# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's OWN parameter -- the `5` of `SP_Summaries_fft_area_5_1` --
#: so it is a module constant and not a function of `length`: the one-sided
#: frequency axis [0, pi] is cut into this many EQUAL-WIDTH bands, and the
#: column reports the share of total power in band 1 (the lowest).
NBANDS = 5
#: Divisor convention of the z-score catch22/hctsa apply before every
#: feature. 1 is MATLAB `zscore`'s default, and hctsa is MATLAB. INERT here
#: in exact arithmetic: dividing the window by any positive constant scales
#: every bin's power by the same factor, which a power RATIO cannot see.
ZSCORE_DDOF = 1
#: Fewest returns a window may hold. Below 8 the zero-padded spectrum has at
#: most 5 one-sided frequency bins, so band 1 could hold only the DC bin
#: before the data's shape is read at all; a smaller or missing `length`
#: falls back to the default. A module choice, not from the source, and the
#: same floor this fork's other catch22-on-returns ports use.
MIN_LENGTH = 8
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: its spectrum is decided by the rounding of
#: `c / c1 - 1` rather than by shape. NaN instead. The floor is an ABSOLUTE
#: constant because what it bounds is a dimensionless RETURN, the same habit
#: this fork's other catch22-on-returns ports use (`c22_mode_10`,
#: `c22_entropy_pairs`, `c22_ami2`, `c22_dfa`, `c22_periodicity`,
#: `c22_median_freq`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: nfft)` padded slab and a `(rows, nfft / 2 + 1)` complex spectrum, so this
#: budget is what keeps the peak off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def nfft_for(length):
    """`2^nextpow2(length)`: the FFT size hctsa's `'fft'` spectrum pads to
    (128 at the default length 100)."""
    return 1 << int(length - 1).bit_length()


def _low_freq_power_rows(block, nfft):
    """The share of each row's own one-sided FFT power spectrum that lies in
    the lowest of `NBANDS` EQUAL-WIDTH bands cut from the frequency axis
    `[0, pi]` -- band 1, `[0, pi / NBANDS)`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored, zero-padded to `nfft`, and transformed; the
    power `|Y_k|^2` of the `nfft / 2 + 1` one-sided bins `w_k = pi * k /
    (nfft / 2)` is summed over `k = 0 .. floor((nfft / 2) / NBANDS)` -- the
    bins with `w_k < pi / NBANDS` -- and divided by the row's total power.

    `nfft / 2` is always a power of two (`nfft` itself is), and `NBANDS` = 5
    never divides a power of two, so the band-1 cutoff bin is never exactly
    on the boundary frequency `pi / NBANDS`: there is no length at which this
    is a tie.

    Comes back as NaN for a row holding a non-finite return, for a row whose
    standard deviation is at most `NOISE_FLOOR` or is not finite, and for a
    row whose total power is not a finite positive number.
    """
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
    # A `bad` row's output is overwritten by NaN at the end regardless; zero
    # it so the FFT never sees a NaN/inf it would spread through the row.
    z = np.where(bad[:, None], 0.0, z)

    spec = np.fft.rfft(z, n=nfft, axis=1)
    power = spec.real ** 2 + spec.imag ** 2
    total = power.sum(axis=1)
    bad |= ~(total > 0.0) | ~np.isfinite(total)

    k_cut = (nfft // 2) // NBANDS
    low = power[:, :k_cut + 1].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        area = low / total

    return np.where(~bad, area, np.nan)


def c22_low_freq_power(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 share of return power in the lowest fifth of
    frequencies (C22LOWFREQPOWER)"""
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

    nfft = nfft_for(length)
    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // nfft)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _low_freq_power_rows(win[a:b], nfft)

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22LOWFREQPOWER_{length}"
    result.category = "statistics"

    return result


c22_low_freq_power.__doc__ = \
"""catch22 share of return power in the lowest fifth of frequencies (C22LOWFREQPOWER)

Z-score the last `length` daily returns, zero-pad them to the next power of
two, take the one-sided FFT power spectrum, cut the frequency axis `[0, pi]`
into `NBANDS` = 5 EQUAL-WIDTH bands, and report the share of the window's
total spectral power that lies in band 1, the lowest fifth (`[0, pi / 5)`).
High values: the window's variation is slow (trending or positively
autocorrelated returns); low values: most power sits at higher frequencies.

    Z      = (X - mean(X)) / sd(X, ddof=1)
    S_k    = |FFT(Z zero-padded to NFFT)_k|^2,   k = 0 .. NFFT/2
    C22LOWFREQPOWER = (S_0 + .. + S_j) / sum(S),  j = floor((NFFT/2) / 5)

**Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data
Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical Time-series
CHaracteristics"), feature `SP_Summaries_fft_area_5_1` -- hctsa's
`SP_Summaries(y, 'fft')` family, the lowest-fifth power-area readout --
applied by PandasTa issue #141 to the last 100 daily simple returns.** ⚠
catch22 is a subset selected for TIME-SERIES CLASSIFICATION performance on
93 reference problems. That is not return prediction, and nothing here
tests it on BIST: its presence in this fork is existence, not evidence.
Shape features of z-scored returns can pick up BIST tick rounding (many
zero or repeated returns on low-priced stocks); see Gate C and Gate E for
whether a price level or `Volume` tops the attribution comparators.

The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this fork
is MIT: this module was written from the feature's published definition
("share of power in the lowest fifth of frequencies", an FFT spectrum
padded to `2^nextpow2(N)`, as named by the paper and by hctsa's
`SP_Summaries` operation family), never from the reference's source. No
shipped module imports it.

**ONE READING THE DEFINITION LEAVES OPEN, AND WHY IT DOES NOT MATTER.**
"Lowest fifth of frequencies" names the SHARE (1/5 of the axis) but not
whether the 5 bands are cut by equal FREQUENCY WIDTH or by equal BIN COUNT.
This module cuts by equal frequency width -- band 1 is `[0, pi/5)` of the
continuous axis `[0, pi]`, independent of how many bins happen to fall in
it -- because that is what "fifth of frequencies" says most directly.
It turns out the choice is moot: `NFFT / 2` is always a power of two, which
`NBANDS` = 5 never divides, so writing `NFFT/2 = 5q + s` always leaves a
remainder `s` in `{1, 2, 3, 4}`. The equal-width cutoff bin is `j_w =
floor((NFFT/2) / NBANDS) = q`. The standard equal-BIN-COUNT split of the
`NFFT/2 + 1 = 5q + s + 1` one-sided bins (remainder bins go to the earliest
groups) gives band 1 size `ceil((5q + s + 1) / 5)`, which is `q + 1` for
every `s` in `{1, 2, 3, 4}` (the band grows past a whole multiple of 5
either strictly, for `s < 4`, or exactly, for `s = 4`), so its cutoff index
is `j_c = q + 1 - 1 = q = j_w` -- IDENTICAL to the equal-width cutoff, for
every `NFFT` this module can ever produce. (At the default length 100,
`NFFT` = 128, `q` = 12: both conventions cut at bin 12, matching this
module's own A2 test.) The two readings were never reconciled against a
GPL-3.0 source; they did not need to be, because for this feature they are
the same reading.

**Half of the z-score is inert here** in exact arithmetic: the division by
`sd` scales every bin by `1 / sd^2`, which a power RATIO cannot see. The
MEAN removal is not inert: it is what keeps the DC bin (`S_0`) near zero so
that band 1's power reflects the window's low-frequency SHAPE rather than
its drift -- with zero-padding (100 returns in 128 slots) a window's mean
would otherwise leak into the low bins including `S_0` itself.

Calculation:
    Default Inputs:
        length=100, NBANDS=5, ZSCORE_DDOF=1  (NFFT = 128, cutoff bin j = 12)
    r[t]    = close[t] / close[t-1] - 1
    X       = r[T-length+1 .. T]                (the window)
    Z       = (X - mean(X)) / sd(X, ddof=1)
    S       = |rfft(Z, NFFT)|^2,  NFFT = 2^ceil(log2(length))
    j       = floor((NFFT/2) / NBANDS)
    C22LOWFREQPOWER = (S_0 + .. + S_j) / sum(S)

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports use -- so that this column reads SHAPE and not the rounding
of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_low_freq_power.py` section B).

Scale-free: the output is a power RATIO, dimensionless by construction, and
any positive rescale of the returns scales every bin's power alike, which a
ratio of sums cannot see. In floating point it is bit-identical under a
x8/x64 price rescale (the price enters only as `c[t] / c[t-1]`, and `8a /
8b` is the double `a / b`) and measured under an inexact return rescale
(x10, x3.7) -- see `docs/measure_c22_low_freq_power.py` section D and
`tests/test_c22_low_freq_power.py`.

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR whose
ratio overflows to an infinite return; and under the blanking rule above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `MIN_LENGTH` = 8, and a smaller or missing value falls back to the
        default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22LOWFREQPOWER_{length}, a power share in [0, 1]
"""
