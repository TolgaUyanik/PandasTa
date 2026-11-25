# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's OWN parameter -- the `50` of `SP_Summaries_fft_wq_50` -- so
#: it is a module constant and not a function of `length`: the share of the
#: window's total spectral power that must lie at or below the output
#: frequency.
QUANTILE = 0.5
#: Divisor convention of the z-score catch22/hctsa apply before every
#: feature. 1 is MATLAB `zscore`'s default, and hctsa is MATLAB. INERT here
#: in exact arithmetic: dividing the window by any positive constant scales
#: every bin's power by the same factor, which a power QUANTILE cannot see.
ZSCORE_DDOF = 1
#: Fewest returns a window may hold. Below 8 the zero-padded spectrum has at
#: most 5 frequency bins, so the output could take at most 4 values before
#: the data's shape is read at all; a smaller or missing `length` falls back
#: to the default. A module choice, not from the source.
MIN_LENGTH = 8
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: its spectrum is decided by the rounding of
#: `c / c1 - 1` rather than by shape. NaN instead. The floor is an ABSOLUTE
#: constant because what it bounds is a dimensionless RETURN, the same habit
#: this fork's other catch22-on-returns ports use (`c22_mode_10`,
#: `c22_entropy_pairs`, `c22_ami2`, `c22_dfa`, `c22_periodicity`).
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


def _median_freq_rows(block, nfft):
    """The angular frequency, in radians per bar on `[0, pi]`, below which
    `QUANTILE` of each row's own one-sided power spectrum lies.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored, zero-padded to `nfft`, and transformed; the
    power `|Y_k|^2` of the `nfft / 2 + 1` one-sided bins `w_k = pi * k /
    (nfft / 2)` is accumulated from `k = 0` up, and the output is the FIRST
    `w_k` at which the running sum strictly exceeds `QUANTILE` of the row's
    own total.

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
    cum = np.cumsum(power, axis=1)
    total = cum[:, -1]
    bad |= ~(total > 0.0) | ~np.isfinite(total)

    # First bin whose running sum strictly exceeds the quantile; one always
    # exists for a finite positive total, since the last running sum IS it.
    k = np.argmax(cum > QUANTILE * total[:, None], axis=1)
    w = np.pi * k / (nfft // 2)

    return np.where(~bad, w, np.nan)


def c22_median_freq(close, length=None, offset=None, **kwargs):
    """Indicator: catch22/hctsa median frequency of the return power
    spectrum (C22MEDFREQ)"""
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
            out[length + a:length + b] = _median_freq_rows(win[a:b], nfft)

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22MEDFREQ_{length}"
    result.category = "statistics"

    return result


c22_median_freq.__doc__ = \
"""catch22/hctsa median frequency of the return power spectrum (C22MEDFREQ)

Z-score the last `length` daily returns, zero-pad them to the next power of
two, take the one-sided FFT power spectrum, and report the angular
frequency (radians per bar, on [0, pi]) below which half of the window's
spectral power lies. Low values: the window's variation is slow (trending
or positively autocorrelated returns); high values: it alternates bar to
bar (mean-reverting returns); white noise sits near pi / 2.

    Z      = (X - mean(X)) / sd(X, ddof=1)
    S_k    = |FFT(Z zero-padded to NFFT)_k|^2,   k = 0 .. NFFT/2
    w_k    = pi * k / (NFFT / 2)
    C22MEDFREQ = w_j for the first j with S_0 + .. + S_j > 0.5 * sum(S)

**Source: hctsa's `SP_Summaries(y, 'fft')` output `wq_50`, the
`SP_Summaries_fft_wq_50` feature, as screened by PandasTa issue #138
alongside catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), applied to the last 100 daily simple
returns.** catch22 itself ships two other `SP_Summaries` read-outs of a
Welch spectrum (`welch_rect_area_5_1`, `welch_rect_centroid`); this is the
FFT-spectrum median frequency from the same hctsa operation family. ⚠
catch22 is a subset selected for TIME-SERIES CLASSIFICATION performance on
93 reference problems. That is not return prediction, and nothing here
tests it on BIST: its presence in this fork is existence, not evidence.

The reference implementations (pycatch22 1.0.2, hctsa) are **GPL-3.0** and
this fork is MIT: this module was written from the feature's published
definition (the frequency below which a given fraction of the power
spectrum lies; spectrum from an FFT padded to `2^nextpow2(N)`), never from
the references' source. No shipped module imports either. Two choices the
definition does not pin and this module makes explicitly: the spectrum is
POWER (`|Y|^2`, the feature's name: "half the return POWER"), and the
crossing is the first bin whose running sum STRICTLY exceeds half. Any
constant normalisation of `S` (by `N`, by `2 pi`, by the bin width) cannot
move a quantile and is left out.

**Half of the z-score is inert here** in exact arithmetic: the division by
`sd` scales every bin by `1 / sd^2`, which a power quantile cannot see. The
MEAN removal is not inert: with zero-padding (100 returns in 128 slots) a
window's mean is not a pure k = 0 component, it leaks into the low bins, so
demeaning is what keeps a drifting window from reading as low-frequency.

Calculation:
    Default Inputs:
        length=100, QUANTILE=0.5, ZSCORE_DDOF=1  (NFFT = 128)
    r[t]    = close[t] / close[t-1] - 1
    X       = r[T-length+1 .. T]                (the window)
    Z       = (X - mean(X)) / sd(X, ddof=1)
    S       = |rfft(Z, NFFT)|^2,  NFFT = 2^ceil(log2(length))
    C22MEDFREQ = pi * j / (NFFT/2),  j = first k with cumsum(S)_k > 0.5 * sum(S)

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports on returns use -- so that this column reads SHAPE and not the
rounding of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_median_freq.py` section B).

Scale-free: the output is a frequency, dimensionless by construction, and
any positive rescale of the returns scales every bin's power alike. In
floating point it is bit-identical under a x8/x64 price rescale (the price
enters only as `c[t] / c[t-1]`, and `8a / 8b` is the double `a / b`) and
measured under an inexact return rescale (x10, x3.7) -- see
`docs/measure_c22_median_freq.py` section D and
`tests/test_c22_median_freq.py`.

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
    pd.Series: C22MEDFREQ_{length}, radians per bar on [0, pi], one of
        NFFT/2 + 1 = 65 levels at the default length
"""
